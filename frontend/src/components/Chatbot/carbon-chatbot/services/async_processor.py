import uuid
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from models.response_models import ProcessingStatus
from services.file_processor import get_file_processor
from services.embedding_service import get_embedding_processor
from services.vector_store import get_vector_store
from config import Config

class AsyncFileProcessor:
    """Asynchronous file processing system with task tracking and status updates"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or Config.MAX_WORKERS
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Task tracking
        self.tasks = {}
        self.task_lock = threading.Lock()
        
        # Services
        self.file_processor = get_file_processor()
        self.embedding_processor = get_embedding_processor()
        self.vector_store = get_vector_store()
        
        print(f"🚀 AsyncFileProcessor initialized with {self.max_workers} workers")
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        return str(uuid.uuid4())
    
    def _update_task_status(self, task_id: str, status: str, progress: float = 0.0,
                           chunks_processed: int = 0, total_chunks: int = 0,
                           error_message: str = None, filename: str = ""):
        """Update task status thread-safely"""
        with self.task_lock:
            if task_id not in self.tasks:
                self.tasks[task_id] = ProcessingStatus(
                    task_id=task_id,
                    status=status,
                    progress=progress,
                    chunks_processed=chunks_processed,
                    total_chunks=total_chunks,
                    filename=filename
                )
            else:
                task = self.tasks[task_id]
                task.status = status
                task.progress = progress
                task.chunks_processed = chunks_processed
                if total_chunks > 0:
                    task.total_chunks = total_chunks
                if error_message:
                    task.error_message = error_message
                if status == "completed":
                    task.completed_at = datetime.now()
    
    def _process_file_task(self, task_id: str, file_path: str, filename: str) -> Dict[str, Any]:
        """Background task for processing a single file"""
        try:
            print(f"📄 Starting async processing: {filename}")
            
            # Update status to processing
            self._update_task_status(task_id, "processing", 0.0, filename=filename)
            
            # Step 1: Extract text with relevance checking (30% of progress)
            print(f"🔍 Extracting text from {filename} with AI relevance checking...")
            
            # Import groq client for AI relevance checking
            try:
                from services.groq_service import get_groq_client
                groq_client = get_groq_client()
            except:
                groq_client = None
            
            extraction_result = self.file_processor.extract_text_with_ocr(
                file_path, skip_relevance_check=False, groq_client=groq_client
            )
            
            if not extraction_result['success']:
                error_msg = extraction_result.get('error', 'Text extraction failed')
                
                # Check if it's a relevance issue
                if 'not relevant' in error_msg.lower():
                    relevance_info = extraction_result.get('relevance_info', {})
                    detailed_error = f"Document not relevant to blue carbon topics. {relevance_info.get('reason', '')}"
                else:
                    detailed_error = error_msg
                
                self._update_task_status(
                    task_id, "failed", 0.0, 
                    error_message=detailed_error,
                    filename=filename
                )
                return {'success': False, 'error': detailed_error}
            
            self._update_task_status(task_id, "processing", 30.0, filename=filename)
            
            # Step 2: Create chunks (50% of progress)
            print(f"📝 Creating chunks from {filename}...")
            chunks = self._create_chunks_from_pages(extraction_result['pages'], filename)
            
            if not chunks:
                self._update_task_status(
                    task_id, "failed", 30.0,
                    error_message="No text chunks could be created",
                    filename=filename
                )
                return {'success': False, 'error': 'No text chunks created'}
            
            self._update_task_status(
                task_id, "processing", 50.0, 
                total_chunks=len(chunks), filename=filename
            )
            
            # Step 3: Generate embeddings (80% of progress)
            print(f"🧠 Generating embeddings for {len(chunks)} chunks...")
            
            def embedding_progress(processed, total):
                progress = 50.0 + (processed / total) * 30.0  # 50% to 80%
                self._update_task_status(
                    task_id, "processing", progress, 
                    chunks_processed=processed, total_chunks=total,
                    filename=filename
                )
            
            enhanced_chunks = self.embedding_processor.embed_chunks_with_metadata(
                chunks, progress_callback=embedding_progress
            )
            
            self._update_task_status(
                task_id, "processing", 80.0, 
                chunks_processed=len(enhanced_chunks), total_chunks=len(chunks),
                filename=filename
            )
            
            # Step 4: Update vector store (100% of progress)
            print(f"💾 Updating vector store with {len(enhanced_chunks)} chunks...")
            self._update_vector_store(enhanced_chunks)
            
            # Complete
            self._update_task_status(
                task_id, "completed", 100.0,
                chunks_processed=len(enhanced_chunks), total_chunks=len(chunks),
                filename=filename
            )
            
            # Update session manager if we have session info
            try:
                from services.session_manager import get_session_manager
                session_manager = get_session_manager()
                
                # Extract base filename (remove _N suffix if present)
                import re
                base_filename = re.sub(r'_\d+\.pdf$', '.pdf', filename)
                
                print(f"📎 Looking for sessions with file: {filename} or {base_filename}")
                
                # Find sessions that have this file and update status
                # This is a simple approach - in production you'd pass session_id to the task
                all_sessions = session_manager.get_all_sessions(limit=100)
                for session in all_sessions:
                    session_files = session_manager.get_session_files(session['session_id'])
                    for file_info in session_files:
                        db_filename = file_info['filename']
                        # Match either exact filename or base filename
                        if db_filename == filename or db_filename == base_filename or base_filename in db_filename:
                            session_manager.update_file_processing_status(
                                session['session_id'], db_filename, 'completed', len(enhanced_chunks)
                            )
                            print(f"📎 Updated session {session['session_id']} file status: {db_filename} -> completed")
                            break
            except Exception as e:
                print(f"⚠️ Could not update session file status: {e}")
            
            print(f"✅ Async processing completed: {filename} ({len(enhanced_chunks)} chunks)")
            
            return {
                'success': True,
                'chunks_processed': len(enhanced_chunks),
                'total_pages': extraction_result['total_pages'],
                'processing_time': extraction_result['processing_time'],
                'filename': filename
            }
            
        except Exception as e:
            print(f"❌ Async processing error for {filename}: {e}")
            self._update_task_status(
                task_id, "failed", 0.0,
                error_message=str(e), filename=filename
            )
            return {'success': False, 'error': str(e)}
    
    def _create_chunks_from_pages(self, pages_data: list, filename: str) -> list:
        """Create semantic chunks from extracted pages"""
        chunks = []
        chunk_id_counter = 0
        
        for page_data in pages_data:
            page_text = page_data.get('text', '').strip()
            if not page_text or len(page_text) < 50:  # Skip very short pages
                continue
            
            page_number = page_data.get('page_number', 1)
            
            # Split page into semantic chunks
            sentences = page_text.split('. ')
            current_chunk = ""
            
            for sentence in sentences:
                # Add sentence to current chunk
                test_chunk = current_chunk + sentence + ". "
                
                # If chunk is getting too long, save it and start new one
                if len(test_chunk) > Config.CHUNK_SIZE:
                    if current_chunk.strip():
                        chunks.append({
                            'id': f"{filename}_chunk_{chunk_id_counter}",
                            'text': current_chunk.strip(),
                            'source_file': f"uploads/{filename}",  # Include uploads path for session matching
                            'page_number': page_number,
                            'chunk_id': f"chunk_{chunk_id_counter}",
                            'extraction_method': page_data.get('extraction_method', 'unknown'),
                            'metadata': {
                                'file_path': f"uploads/{filename}",
                                'page_number': page_number,
                                'chunk_index': chunk_id_counter,
                                'char_count': len(current_chunk.strip())
                            }
                        })
                        chunk_id_counter += 1
                    
                    # Start new chunk with overlap
                    current_chunk = sentence + ". "
                else:
                    current_chunk = test_chunk
            
            # Add remaining text as final chunk for this page
            if current_chunk.strip():
                chunks.append({
                    'id': f"{filename}_chunk_{chunk_id_counter}",
                    'text': current_chunk.strip(),
                    'source_file': f"uploads/{filename}",  # Include uploads path for session matching
                    'page_number': page_number,
                    'chunk_id': f"chunk_{chunk_id_counter}",
                    'extraction_method': page_data.get('extraction_method', 'unknown'),
                    'metadata': {
                        'file_path': f"uploads/{filename}",
                        'page_number': page_number,
                        'chunk_index': chunk_id_counter,
                        'char_count': len(current_chunk.strip())
                    }
                })
                chunk_id_counter += 1
        
        return chunks
    
    def _update_vector_store(self, enhanced_chunks: list):
        """Update vector store with new chunks"""
        try:
            # Extract embeddings and metadata
            embeddings = [chunk['embedding'] for chunk in enhanced_chunks]
            metadata = []
            
            for chunk in enhanced_chunks:
                metadata.append({
                    'text': chunk['text'],
                    'source_file': chunk['source_file'],  # Already includes uploads/ path
                    'page_number': chunk['page_number'],
                    'chunk_id': chunk['chunk_id'],
                    'metadata': chunk.get('metadata', {}),
                    'source_type': 'uploaded'  # Mark as uploaded file
                })
            
            # Load existing data if available
            try:
                existing_embeddings = self.vector_store.embeddings
                existing_metadata = self.vector_store.metadata
                
                # Combine with new data
                all_embeddings = existing_embeddings + embeddings
                all_metadata = existing_metadata + metadata
                
            except (AttributeError, TypeError):
                # No existing data
                all_embeddings = embeddings
                all_metadata = metadata
            
            # Rebuild index with all data
            self.vector_store.build_index(all_embeddings, all_metadata)
            
            # Save updated index
            self.vector_store.save_index(
                str(Config.VECTORSTORE_DIR / "faiss_index.bin"),
                str(Config.VECTORSTORE_DIR / "metadata.json"),
                str(Config.VECTORSTORE_DIR / "embeddings.pkl")
            )
            
            print(f"💾 Vector store updated with {len(enhanced_chunks)} new chunks")
            
        except Exception as e:
            print(f"❌ Vector store update error: {e}")
            raise
    
    def process_file_async(self, file_path: str) -> str:
        """Start asynchronous file processing and return task ID"""
        task_id = self._generate_task_id()
        filename = Path(file_path).name
        
        # Submit task to executor
        future = self.executor.submit(self._process_file_task, task_id, file_path, filename)
        
        # Initialize task status
        self._update_task_status(task_id, "queued", 0.0, filename=filename)
        
        print(f"📋 Queued async processing: {filename} (Task ID: {task_id})")
        
        return task_id
    
    def get_processing_status(self, task_id: str) -> Optional[ProcessingStatus]:
        """Get processing status for a task"""
        with self.task_lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, ProcessingStatus]:
        """Get all task statuses"""
        with self.task_lock:
            return self.tasks.copy()
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a processing task (if possible)"""
        with self.task_lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status in ["queued", "processing"]:
                    task.status = "cancelled"
                    task.error_message = "Task cancelled by user"
                    return True
        return False
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self.task_lock:
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in ["completed", "failed", "cancelled"] and 
                    task.completed_at and task.completed_at < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            if tasks_to_remove:
                print(f"🧹 Cleaned up {len(tasks_to_remove)} old tasks")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        with self.task_lock:
            total_tasks = len(self.tasks)
            completed_tasks = len([t for t in self.tasks.values() if t.status == "completed"])
            failed_tasks = len([t for t in self.tasks.values() if t.status == "failed"])
            processing_tasks = len([t for t in self.tasks.values() if t.status == "processing"])
            
            return {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'processing_tasks': processing_tasks,
                'success_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                'max_workers': self.max_workers
            }
    
    def shutdown(self):
        """Shutdown the async processor"""
        print("🛑 Shutting down AsyncFileProcessor...")
        self.executor.shutdown(wait=True)

# Global instance
_async_processor = None

def get_async_processor() -> AsyncFileProcessor:
    """Get global async processor instance"""
    global _async_processor
    if _async_processor is None:
        _async_processor = AsyncFileProcessor()
    return _async_processor