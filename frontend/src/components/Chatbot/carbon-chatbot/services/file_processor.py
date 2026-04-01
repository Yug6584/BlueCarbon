import fitz  # PyMuPDF
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from models.response_models import ProcessingStatus, Chunk
from config import Config

# OCR imports (optional)
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
    print("OCR capabilities available")
except ImportError:
    OCR_AVAILABLE = False
    # OCR not available - text PDFs will work fine

class HighPerformanceFileProcessor:
    """Ultra-fast document processing with OCR fallback and parallel processing"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or Config.MAX_WORKERS
        self.ocr_enabled = Config.OCR_ENABLED and OCR_AVAILABLE
        self.ocr_language = Config.OCR_LANGUAGE
        
        # Processing statistics
        self.stats = {
            'files_processed': 0,
            'pages_processed': 0,
            'ocr_pages': 0,
            'total_processing_time': 0.0,
            'errors': 0
        }
        
        # Thread-safe status tracking
        self.processing_status = {}
        self.status_lock = threading.Lock()
        
        print(f"🚀 HighPerformanceFileProcessor initialized")
        print(f"   Max workers: {self.max_workers}")
        print(f"   OCR enabled: {self.ocr_enabled}")
    
    def _is_scanned_pdf(self, doc: fitz.Document, sample_pages: int = 3) -> bool:
        """Detect if PDF is scanned by analyzing text content"""
        total_chars = 0
        pages_checked = 0
        
        for page_num in range(min(sample_pages, len(doc))):
            try:
                page = doc[page_num]
                text = page.get_text()
                total_chars += len(text.strip())
                pages_checked += 1
            except Exception:
                continue
        
        if pages_checked == 0:
            return True  # Assume scanned if can't extract text
        
        avg_chars_per_page = total_chars / pages_checked
        # If less than 50 characters per page on average, likely scanned
        return avg_chars_per_page < 50
    
    def _extract_text_pymupdf(self, file_path: str) -> Tuple[List[Dict[str, Any]], bool]:
        """Extract text using PyMuPDF with scanned PDF detection"""
        try:
            doc = fitz.open(file_path)
            pages_data = []
            is_scanned = False
            
            # Check if document is scanned
            if self.ocr_enabled:
                is_scanned = self._is_scanned_pdf(doc)
                if is_scanned:
                    print(f"📄 Detected scanned PDF: {Path(file_path).name}")
            
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    
                    # Try text extraction first
                    text = page.get_text()
                    
                    # If text is too short and OCR is available, use OCR
                    if len(text.strip()) < 50 and self.ocr_enabled and not is_scanned:
                        print(f"🔍 Page {page_num + 1} has minimal text, checking if OCR needed...")
                        # This page might be scanned even if document isn't fully scanned
                        is_scanned = True
                    
                    if text.strip():  # If we got text, use it
                        pages_data.append({
                            'page_number': page_num + 1,
                            'text': text.strip(),
                            'extraction_method': 'pymupdf',
                            'char_count': len(text.strip())
                        })
                    else:
                        # No text found, mark for OCR if available
                        pages_data.append({
                            'page_number': page_num + 1,
                            'text': '',
                            'extraction_method': 'none',
                            'char_count': 0,
                            'needs_ocr': self.ocr_enabled
                        })
                
                except Exception as e:
                    print(f"⚠️ Error extracting page {page_num + 1}: {e}")
                    pages_data.append({
                        'page_number': page_num + 1,
                        'text': '',
                        'extraction_method': 'error',
                        'error': str(e),
                        'needs_ocr': self.ocr_enabled
                    })
            
            doc.close()
            return pages_data, is_scanned
            
        except Exception as e:
            print(f"❌ PyMuPDF extraction error: {e}")
            return [], False
    
    def _extract_text_ocr(self, file_path: str, pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract text using OCR for scanned pages"""
        if not self.ocr_enabled:
            return pages_data
        
        try:
            print(f"🔍 Starting OCR processing for {Path(file_path).name}")
            
            # Convert PDF to images
            images = convert_from_path(file_path, dpi=200, thread_count=self.max_workers)
            
            # Process pages that need OCR
            for i, page_data in enumerate(pages_data):
                if (page_data.get('needs_ocr', False) or 
                    page_data.get('char_count', 0) < 50):
                    
                    try:
                        if i < len(images):
                            # Perform OCR on the image
                            ocr_text = pytesseract.image_to_string(
                                images[i], 
                                lang=self.ocr_language,
                                config='--psm 6'  # Uniform block of text
                            )
                            
                            if ocr_text.strip():
                                page_data['text'] = ocr_text.strip()
                                page_data['extraction_method'] = 'ocr'
                                page_data['char_count'] = len(ocr_text.strip())
                                self.stats['ocr_pages'] += 1
                                print(f"✅ OCR extracted {len(ocr_text.strip())} chars from page {i + 1}")
                            else:
                                print(f"⚠️ OCR found no text on page {i + 1}")
                    
                    except Exception as e:
                        print(f"❌ OCR error on page {i + 1}: {e}")
                        page_data['ocr_error'] = str(e)
            
            return pages_data
            
        except Exception as e:
            print(f"❌ OCR processing error: {e}")
            return pages_data
    
    def scan_pdf_for_topic_relevance(self, file_path: str, groq_client=None) -> Dict[str, Any]:
        """AI-powered scan of PDF for blue carbon topic relevance before full processing"""
        print(f"🔍 Scanning PDF for topic relevance: {Path(file_path).name}")
        
        try:
            doc = fitz.open(file_path)
            
            # Extract text from first 3 pages for quick analysis
            sample_text = ""
            pages_scanned = 0
            
            for page_num in range(min(3, len(doc))):
                try:
                    page = doc[page_num]
                    text = page.get_text()
                    
                    if len(text.strip()) < 50 and self.ocr_enabled:
                        # Try OCR on this page if text is minimal
                        try:
                            from pdf2image import convert_from_path
                            import pytesseract
                            
                            images = convert_from_path(file_path, first_page=page_num+1, last_page=page_num+1, dpi=150)
                            if images:
                                ocr_text = pytesseract.image_to_string(images[0], lang=self.ocr_language)
                                if len(ocr_text.strip()) > len(text.strip()):
                                    text = ocr_text
                        except Exception as ocr_error:
                            print(f"⚠️ OCR scan failed for page {page_num+1}: {ocr_error}")
                    
                    sample_text += f" {text}"
                    pages_scanned += 1
                    
                    # Stop if we have enough text for analysis
                    if len(sample_text) > 2000:
                        break
                        
                except Exception as e:
                    print(f"⚠️ Error scanning page {page_num+1}: {e}")
                    continue
            
            doc.close()
            
            if not sample_text.strip():
                return {
                    'is_relevant': False,
                    'confidence': 0.0,
                    'reason': 'No readable text found in document',
                    'sample_text_length': 0,
                    'pages_scanned': pages_scanned
                }
            
            # AI-powered relevance analysis
            if groq_client:
                relevance_result = self._ai_analyze_relevance(sample_text, Path(file_path).name, groq_client)
            else:
                relevance_result = self._keyword_analyze_relevance(sample_text, Path(file_path).name)
            
            relevance_result.update({
                'sample_text_length': len(sample_text),
                'pages_scanned': pages_scanned,
                'total_pages': len(fitz.open(file_path))
            })
            
            return relevance_result
            
        except Exception as e:
            print(f"❌ PDF relevance scan failed: {e}")
            return {
                'is_relevant': True,  # Default to relevant if scan fails
                'confidence': 0.5,
                'reason': f'Scan failed: {str(e)}, proceeding with processing',
                'sample_text_length': 0,
                'pages_scanned': 0
            }
    
    def _ai_analyze_relevance(self, text: str, filename: str, groq_client) -> Dict[str, Any]:
        """AI-powered analysis of document relevance to blue carbon topics"""
        try:
            analysis_prompt = f"""
Analyze this document content to determine if it's relevant to blue carbon ecosystems and coastal conservation:

Filename: {filename}
Document content: {text[:2000]}...

Blue carbon topics include:
- Mangroves, seagrass beds, salt marshes, kelp forests
- Coastal carbon sequestration and storage
- Marine ecosystem restoration and conservation
- Climate change mitigation through coastal ecosystems
- Blue carbon methodologies and carbon markets
- Coastal wetland management and policy
- Marine biodiversity and ecosystem services
- Environmental monitoring and assessment
- Land use and coastal management
- Satellite imagery and remote sensing for coastal areas
- Ecological surveys and biodiversity studies
- Climate impact assessments
- Conservation planning and management

IMPORTANT: Be VERY GENEROUS in determining relevance. Consider:
- Environmental documents that could relate to coastal areas
- Scientific studies that might have coastal/marine components
- Land use documents that could include coastal zones
- Any document that mentions water, coastal, marine, environmental, or ecological topics
- Research papers on environmental topics
- Government reports on environmental management

Analysis required:
1. Is this document relevant to blue carbon topics? (YES/NO)
2. Confidence level (0.0 to 1.0)
3. Key relevant topics found
4. Brief reasoning

Format your response as:
RELEVANT: YES/NO
CONFIDENCE: 0.X
TOPICS: topic1, topic2, topic3
REASONING: brief explanation
"""
            
            response = groq_client.complete(analysis_prompt)
            
            # Parse AI response
            is_relevant = "YES" in response.split("RELEVANT:")[1].split("\n")[0].upper() if "RELEVANT:" in response else False
            
            confidence = 0.5
            if "CONFIDENCE:" in response:
                try:
                    conf_str = response.split("CONFIDENCE:")[1].split("\n")[0].strip()
                    confidence = float(''.join(c for c in conf_str if c.isdigit() or c == '.'))
                    confidence = max(0.0, min(1.0, confidence))
                except:
                    pass
            
            topics = []
            if "TOPICS:" in response:
                topics_str = response.split("TOPICS:")[1].split("\n")[0].strip()
                topics = [t.strip() for t in topics_str.split(",") if t.strip()]
            
            reasoning = "AI analysis completed"
            if "REASONING:" in response:
                reasoning = response.split("REASONING:")[1].strip()
            
            print(f"🤖 AI relevance analysis: {'✅ Relevant' if is_relevant else '❌ Not relevant'} (confidence: {confidence:.1%})")
            
            return {
                'is_relevant': is_relevant,
                'confidence': confidence,
                'topics_found': topics,
                'reason': reasoning,
                'analysis_method': 'ai_powered'
            }
            
        except Exception as e:
            print(f"⚠️ AI relevance analysis failed: {e}")
            return self._keyword_analyze_relevance(text, filename)
    
    def _keyword_analyze_relevance(self, text: str, filename: str) -> Dict[str, Any]:
        """Fallback keyword-based relevance analysis - VERY GENEROUS"""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Blue carbon keywords with weights
        primary_keywords = {
            'blue carbon': 3.0,
            'mangrove': 2.5,
            'seagrass': 2.5,
            'salt marsh': 2.5,
            'carbon sequestration': 2.0,
            'coastal ecosystem': 2.0,
            'marine ecosystem': 2.0
        }
        
        secondary_keywords = {
            'coastal': 1.5,
            'marine': 1.5,
            'wetland': 1.5,
            'carbon storage': 1.5,
            'restoration': 1.0,
            'conservation': 1.0,
            'climate change': 1.0,
            'ecosystem services': 1.0,
            'biodiversity': 1.0,
            'environmental': 1.0,
            'water': 0.8,
            'ocean': 1.2,
            'sea': 1.0,
            'beach': 0.8,
            'shore': 0.8,
            'habitat': 1.0,
            'ecology': 1.0,
            'satellite': 0.8,
            'remote sensing': 1.0,
            'land use': 0.8,
            'monitoring': 0.8,
            'assessment': 0.8,
            'survey': 0.8,
            'analysis': 0.5,
            'study': 0.5,
            'research': 0.5
        }
        
        # Calculate relevance score
        relevance_score = 0.0
        found_keywords = []
        
        # Check primary keywords
        for keyword, weight in primary_keywords.items():
            if keyword in text_lower or keyword in filename_lower:
                relevance_score += weight
                found_keywords.append(keyword)
        
        # Check secondary keywords
        for keyword, weight in secondary_keywords.items():
            if keyword in text_lower or keyword in filename_lower:
                relevance_score += weight
                found_keywords.append(keyword)
        
        # Normalize score
        max_possible_score = sum(primary_keywords.values()) + sum(secondary_keywords.values())
        confidence = min(relevance_score / max_possible_score * 3, 1.0)  # Scale to 0-1, more generous
        
        # VERY LOW threshold - accept almost anything that could be environmental
        is_relevant = confidence >= 0.05 or len(found_keywords) >= 1
        
        # If still not relevant, check for any environmental indicators
        if not is_relevant:
            environmental_indicators = ['pdf', 'report', 'data', 'document', 'file', 'study', 'analysis']
            if any(indicator in filename_lower for indicator in environmental_indicators):
                is_relevant = True
                confidence = 0.3
                found_keywords.append('document_type')
        
        reason = f"Found {len(found_keywords)} relevant keywords: {', '.join(found_keywords[:5])}" if found_keywords else "Accepting as potentially relevant document"
        
        print(f"📊 Generous keyword analysis: {'✅ Relevant' if is_relevant else '❌ Not relevant'} (confidence: {confidence:.1%})")
        
        return {
            'is_relevant': is_relevant,
            'confidence': confidence,
            'topics_found': found_keywords,
            'reason': reason,
            'analysis_method': 'generous_keyword_based'
        }

    def extract_text_with_ocr(self, file_path: str, skip_relevance_check: bool = False, groq_client=None) -> Dict[str, Any]:
        """Complete text extraction with OCR fallback and optional relevance checking"""
        start_time = time.time()
        
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': 'File not found',
                'pages': [],
                'processing_time': 0
            }
        
        try:
            # Phase 0: Topic relevance scan (if not skipped)
            relevance_info = None
            if not skip_relevance_check:
                relevance_info = self.scan_pdf_for_topic_relevance(file_path, groq_client)
                
                if not relevance_info['is_relevant']:
                    return {
                        'success': False,
                        'error': 'Document not relevant to blue carbon topics',
                        'relevance_info': relevance_info,
                        'pages': [],
                        'processing_time': time.time() - start_time,
                        'filename': Path(file_path).name
                    }
            
            # Phase 1: PyMuPDF extraction
            pages_data, is_scanned = self._extract_text_pymupdf(file_path)
            
            # Phase 2: OCR for scanned pages
            if is_scanned or any(p.get('needs_ocr', False) for p in pages_data):
                pages_data = self._extract_text_ocr(file_path, pages_data)
            
            # Calculate statistics
            total_chars = sum(p.get('char_count', 0) for p in pages_data)
            successful_pages = len([p for p in pages_data if p.get('char_count', 0) > 0])
            
            processing_time = time.time() - start_time
            
            # Update stats
            self.stats['files_processed'] += 1
            self.stats['pages_processed'] += len(pages_data)
            self.stats['total_processing_time'] += processing_time
            
            result = {
                'success': True,
                'pages': pages_data,
                'total_pages': len(pages_data),
                'successful_pages': successful_pages,
                'total_characters': total_chars,
                'is_scanned': is_scanned,
                'processing_time': processing_time,
                'filename': Path(file_path).name,
                'relevance_info': relevance_info
            }
            
            print(f"📊 Extraction complete: {successful_pages}/{len(pages_data)} pages, {total_chars} chars in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.stats['errors'] += 1
            
            print(f"❌ Text extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'pages': [],
                'processing_time': processing_time,
                'filename': Path(file_path).name,
                'relevance_info': relevance_info
            }
    
    def process_multiple_files(self, file_paths: List[str], progress_callback=None) -> List[Dict[str, Any]]:
        """Process multiple files in parallel"""
        if not file_paths:
            return []
        
        start_time = time.time()
        results = []
        processed_count = 0
        
        print(f"📁 Processing {len(file_paths)} files with {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all file processing jobs
            future_to_file = {
                executor.submit(self.extract_text_with_ocr, file_path): file_path 
                for file_path in file_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    result['file_path'] = file_path
                    results.append(result)
                    processed_count += 1
                    
                    if progress_callback:
                        progress_callback(processed_count, len(file_paths))
                    
                    print(f"✅ Completed {processed_count}/{len(file_paths)}: {Path(file_path).name}")
                    
                except Exception as e:
                    print(f"❌ Error processing {file_path}: {e}")
                    results.append({
                        'success': False,
                        'error': str(e),
                        'file_path': file_path,
                        'filename': Path(file_path).name
                    })
                    processed_count += 1
        
        total_time = time.time() - start_time
        successful_files = len([r for r in results if r.get('success', False)])
        
        print(f"🎯 Batch processing complete: {successful_files}/{len(file_paths)} files in {total_time:.2f}s")
        
        return results
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing performance statistics"""
        avg_time_per_file = (
            self.stats['total_processing_time'] / self.stats['files_processed']
            if self.stats['files_processed'] > 0 else 0
        )
        
        avg_time_per_page = (
            self.stats['total_processing_time'] / self.stats['pages_processed']
            if self.stats['pages_processed'] > 0 else 0
        )
        
        return {
            'files_processed': self.stats['files_processed'],
            'pages_processed': self.stats['pages_processed'],
            'ocr_pages': self.stats['ocr_pages'],
            'total_processing_time': round(self.stats['total_processing_time'], 2),
            'average_time_per_file': round(avg_time_per_file, 2),
            'average_time_per_page': round(avg_time_per_page, 2),
            'errors': self.stats['errors'],
            'ocr_enabled': self.ocr_enabled,
            'max_workers': self.max_workers
        }
    
    def update_processing_status(self, task_id: str, status: str, progress: float = 0.0, 
                               chunks_processed: int = 0, error_message: str = None):
        """Update processing status for async operations"""
        with self.status_lock:
            if task_id not in self.processing_status:
                self.processing_status[task_id] = ProcessingStatus(
                    task_id=task_id,
                    status=status,
                    progress=progress,
                    chunks_processed=chunks_processed
                )
            else:
                self.processing_status[task_id].status = status
                self.processing_status[task_id].progress = progress
                self.processing_status[task_id].chunks_processed = chunks_processed
                if error_message:
                    self.processing_status[task_id].error_message = error_message
    
    def get_processing_status(self, task_id: str) -> Optional[ProcessingStatus]:
        """Get processing status for a task"""
        with self.status_lock:
            return self.processing_status.get(task_id)

# Global instance
_file_processor = None

def get_file_processor() -> HighPerformanceFileProcessor:
    """Get global file processor instance"""
    global _file_processor
    if _file_processor is None:
        _file_processor = HighPerformanceFileProcessor()
    return _file_processor