"""
Enhanced PDF Extractor - Better text extraction with pdfplumber
"""
import pdfplumber
import PyPDF2
import re
from typing import Dict, List, Any, Tuple
from pathlib import Path


class EnhancedPDFExtractor:
    """Extract text from PDFs with better quality and structure preservation"""
    
    def __init__(self):
        self.chunk_size = 800  # Characters per chunk
        self.overlap_size = 100  # Overlap between chunks for context
    
    def extract_text(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text with structure preservation
        
        Returns:
            {
                'text': str,  # Complete text
                'pages': List[Dict],  # Per-page content
                'metadata': Dict,  # PDF metadata
                'quality_score': float  # 0-1 extraction quality
            }
        """
        try:
            # Try pdfplumber first (better quality)
            result = self._extract_with_pdfplumber(pdf_path)
            if result['quality_score'] > 0.5:
                print(f"✅ Extracted with pdfplumber: {len(result['text'])} chars, quality: {result['quality_score']:.2f}")
                return result
        except Exception as e:
            print(f"⚠️ pdfplumber failed: {e}, falling back to PyPDF2")
        
        # Fallback to PyPDF2
        try:
            result = self._extract_with_pypdf2(pdf_path)
            print(f"✅ Extracted with PyPDF2: {len(result['text'])} chars, quality: {result['quality_score']:.2f}")
            return result
        except Exception as e:
            print(f"❌ Both extraction methods failed: {e}")
            return {
                'text': '',
                'pages': [],
                'metadata': {},
                'quality_score': 0.0
            }
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """Extract using pdfplumber (better for tables and layouts)"""
        pages_content = []
        all_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            metadata = pdf.metadata or {}
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text
                text = page.extract_text() or ""
                
                # Extract tables
                tables = page.extract_tables()
                
                # Combine text and tables
                page_content = {
                    'page_number': page_num,
                    'text': text,
                    'tables': tables,
                    'char_count': len(text)
                }
                
                pages_content.append(page_content)
                all_text.append(text)
        
        complete_text = "\n\n".join(all_text)
        quality_score = self._calculate_quality_score(complete_text, len(pages_content))
        
        return {
            'text': complete_text,
            'pages': pages_content,
            'metadata': metadata,
            'quality_score': quality_score
        }
    
    def _extract_with_pypdf2(self, pdf_path: str) -> Dict[str, Any]:
        """Fallback extraction using PyPDF2"""
        pages_content = []
        all_text = []
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            metadata = pdf_reader.metadata or {}
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text() or ""
                
                page_content = {
                    'page_number': page_num,
                    'text': text,
                    'tables': [],
                    'char_count': len(text)
                }
                
                pages_content.append(page_content)
                all_text.append(text)
        
        complete_text = "\n\n".join(all_text)
        quality_score = self._calculate_quality_score(complete_text, len(pages_content))
        
        return {
            'text': complete_text,
            'pages': pages_content,
            'metadata': metadata,
            'quality_score': quality_score
        }
    
    def _calculate_quality_score(self, text: str, page_count: int) -> float:
        """
        Calculate extraction quality score (0-1)
        
        Factors:
        - Text length (more is better)
        - Character variety (not just garbage)
        - Paragraph structure
        """
        if not text or page_count == 0:
            return 0.0
        
        # Average characters per page
        chars_per_page = len(text) / page_count
        
        # Score based on chars per page (typical page has 2000-3000 chars)
        length_score = min(chars_per_page / 2000, 1.0)
        
        # Check for variety (not just repeated characters)
        unique_chars = len(set(text))
        variety_score = min(unique_chars / 50, 1.0)  # At least 50 unique chars
        
        # Check for structure (paragraphs, sentences)
        has_structure = bool(re.search(r'\n\n|\. [A-Z]', text))
        structure_score = 1.0 if has_structure else 0.5
        
        # Combined score
        quality = (length_score * 0.5 + variety_score * 0.3 + structure_score * 0.2)
        
        return min(quality, 1.0)
    
    def create_smart_chunks(self, text: str, page_numbers: List[int] = None) -> List[Dict]:
        """
        Create chunks that preserve context with overlap
        
        Returns:
            [
                {
                    'text': str,
                    'page_number': int,
                    'chunk_index': int,
                    'overlap': str  # Overlapping text for context
                }
            ]
        """
        if not text:
            return []
        
        chunks = []
        chunk_index = 0
        position = 0
        
        while position < len(text):
            # Extract chunk
            chunk_end = position + self.chunk_size
            chunk_text = text[position:chunk_end]
            
            # Try to break at paragraph boundary
            if chunk_end < len(text):
                # Look for paragraph break
                para_break = chunk_text.rfind('\n\n')
                if para_break > self.chunk_size * 0.7:  # At least 70% of chunk size
                    chunk_end = position + para_break
                    chunk_text = text[position:chunk_end]
                else:
                    # Look for sentence break
                    sentence_break = chunk_text.rfind('. ')
                    if sentence_break > self.chunk_size * 0.7:
                        chunk_end = position + sentence_break + 1
                        chunk_text = text[position:chunk_end]
            
            # Get overlap for context (last 100 chars of previous chunk)
            overlap = ""
            if position > 0:
                overlap_start = max(0, position - self.overlap_size)
                overlap = text[overlap_start:position]
            
            # Determine page number (simplified - would need better logic)
            page_num = 1 if not page_numbers else page_numbers[min(chunk_index, len(page_numbers) - 1)]
            
            chunks.append({
                'text': chunk_text.strip(),
                'page_number': page_num,
                'chunk_index': chunk_index,
                'overlap': overlap.strip()
            })
            
            # Move position (with overlap)
            position = chunk_end
            chunk_index += 1
        
        print(f"📝 Created {len(chunks)} smart chunks with {self.overlap_size}-char overlap")
        return chunks


# Singleton instance
_enhanced_pdf_extractor = None

def get_enhanced_pdf_extractor() -> EnhancedPDFExtractor:
    """Get singleton instance of EnhancedPDFExtractor"""
    global _enhanced_pdf_extractor
    if _enhanced_pdf_extractor is None:
        _enhanced_pdf_extractor = EnhancedPDFExtractor()
    return _enhanced_pdf_extractor
