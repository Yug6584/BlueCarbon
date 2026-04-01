import time
import numpy as np
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from sentence_transformers import SentenceTransformer
import threading
from config import Config

class BatchEmbeddingProcessor:
    """High-performance batch embedding processor with parallel processing"""
    
    def __init__(self, model_name: str = None, max_workers: int = None):
        self.model_name = model_name or Config.EMBEDDING_MODEL
        self.max_workers = max_workers or Config.MAX_WORKERS
        self.batch_size = Config.BATCH_SIZE
        
        # Thread-local storage for models to avoid conflicts
        self._local = threading.local()
        
        print(f"🚀 Initializing BatchEmbeddingProcessor with {self.max_workers} workers")
        
    def _get_model(self):
        """Get thread-local embedding model"""
        if not hasattr(self._local, 'model'):
            print(f"Loading embedding model {self.model_name} for thread {threading.current_thread().name}")
            self._local.model = SentenceTransformer(self.model_name)
        return self._local.model
    
    def embed_single_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a single batch of texts"""
        try:
            model = self._get_model()
            embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return embeddings.tolist()
        except Exception as e:
            print(f"Error in batch embedding: {e}")
            return [[0.0] * 384] * len(texts)  # Return zero embeddings as fallback
    
    def embed_texts_parallel(self, texts: List[str], progress_callback=None) -> List[List[float]]:
        """Embed texts using parallel batch processing"""
        if not texts:
            return []
        
        start_time = time.time()
        total_texts = len(texts)
        
        # Split texts into batches
        batches = [texts[i:i + self.batch_size] for i in range(0, len(texts), self.batch_size)]
        
        print(f"📊 Processing {total_texts} texts in {len(batches)} batches using {self.max_workers} workers")
        
        all_embeddings = []
        processed_count = 0
        
        # Process batches in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batch jobs
            future_to_batch = {
                executor.submit(self.embed_single_batch, batch): i 
                for i, batch in enumerate(batches)
            }
            
            # Collect results in order
            batch_results = [None] * len(batches)
            
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_embeddings = future.result()
                    batch_results[batch_idx] = batch_embeddings
                    processed_count += len(batch_embeddings)
                    
                    if progress_callback:
                        progress_callback(processed_count, total_texts)
                    
                    print(f"✅ Completed batch {batch_idx + 1}/{len(batches)} ({processed_count}/{total_texts} texts)")
                    
                except Exception as e:
                    print(f"❌ Error processing batch {batch_idx}: {e}")
                    # Use zero embeddings as fallback
                    batch_size = len(batches[batch_idx])
                    batch_results[batch_idx] = [[0.0] * 384] * batch_size
        
        # Flatten results maintaining order
        for batch_result in batch_results:
            if batch_result:
                all_embeddings.extend(batch_result)
        
        processing_time = time.time() - start_time
        speed_improvement = (total_texts / processing_time) if processing_time > 0 else 0
        
        print(f"🎯 Batch embedding completed: {total_texts} texts in {processing_time:.2f}s ({speed_improvement:.1f} texts/sec)")
        
        return all_embeddings
    
    def embed_chunks_with_metadata(self, chunks: List[Dict[str, Any]], progress_callback=None) -> List[Dict[str, Any]]:
        """Embed chunks and add embeddings to metadata"""
        if not chunks:
            return []
        
        # Extract texts for embedding
        texts = [chunk.get('text', '') for chunk in chunks]
        
        # Get embeddings in parallel
        embeddings = self.embed_texts_parallel(texts, progress_callback)
        
        # Add embeddings to chunks
        enhanced_chunks = []
        for i, chunk in enumerate(chunks):
            enhanced_chunk = chunk.copy()
            enhanced_chunk['embedding'] = embeddings[i] if i < len(embeddings) else [0.0] * 384
            enhanced_chunk['embedding_model'] = self.model_name
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks
    
    def benchmark_performance(self, test_texts: List[str]) -> Dict[str, float]:
        """Benchmark embedding performance"""
        print("🔬 Running embedding performance benchmark...")
        
        # Test serial processing (single thread)
        start_time = time.time()
        model = self._get_model()
        serial_embeddings = model.encode(test_texts, convert_to_numpy=True, show_progress_bar=False)
        serial_time = time.time() - start_time
        
        # Test parallel processing
        start_time = time.time()
        parallel_embeddings = self.embed_texts_parallel(test_texts)
        parallel_time = time.time() - start_time
        
        # Calculate metrics
        speedup = serial_time / parallel_time if parallel_time > 0 else 0
        serial_speed = len(test_texts) / serial_time if serial_time > 0 else 0
        parallel_speed = len(test_texts) / parallel_time if parallel_time > 0 else 0
        
        results = {
            'serial_time': serial_time,
            'parallel_time': parallel_time,
            'speedup': speedup,
            'serial_speed': serial_speed,
            'parallel_speed': parallel_speed,
            'texts_processed': len(test_texts)
        }
        
        print(f"📈 Benchmark Results:")
        print(f"   Serial: {serial_time:.2f}s ({serial_speed:.1f} texts/sec)")
        print(f"   Parallel: {parallel_time:.2f}s ({parallel_speed:.1f} texts/sec)")
        print(f"   Speedup: {speedup:.1f}x")
        
        return results

# Global instance for reuse
_embedding_processor = None

def get_embedding_processor() -> BatchEmbeddingProcessor:
    """Get global embedding processor instance"""
    global _embedding_processor
    if _embedding_processor is None:
        _embedding_processor = BatchEmbeddingProcessor()
    return _embedding_processor