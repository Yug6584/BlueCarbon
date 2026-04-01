"""
File Chunk Matcher - Precisely match uploaded files with their stored chunks
"""
import re
from typing import List, Dict, Tuple


class FileChunkMatcher:
    """Handles precise matching of uploaded files with their vector store chunks"""
    
    def __init__(self):
        self.debug_mode = True  # Enable for troubleshooting
    
    def find_chunks_for_file(self, filename: str, all_chunks: List[Dict]) -> List[Dict]:
        """
        Find all chunks belonging to a specific file
        
        Args:
            filename: Original uploaded filename (e.g., "report.pdf")
            all_chunks: All chunks from vector store
            
        Returns:
            List of chunks that belong to this file only
        """
        if self.debug_mode:
            print(f"🔍 FileChunkMatcher: Looking for chunks for '{filename}'")
        
        base_filename = self.normalize_filename(filename)
        matched_chunks = []
        
        for chunk in all_chunks:
            source_file = chunk.get('source_file', '')
            
            if self._is_match(source_file, filename, base_filename):
                matched_chunks.append(chunk)
                if self.debug_mode:
                    print(f"  ✅ MATCHED: {source_file}")
        
        if self.debug_mode:
            print(f"📊 Found {len(matched_chunks)} chunks for '{filename}'")
        
        return matched_chunks
    
    def normalize_filename(self, filename: str) -> str:
        """
        Normalize filename for matching
        
        Removes:
        - Path prefixes (uploads/, data/)
        - File extensions (.pdf, .docx)
        - Processing suffixes (_1, _2, etc.)
        
        Example: "uploads/report_1.pdf" → "report"
        """
        # Remove path
        name = filename.split('/')[-1] if '/' in filename else filename
        
        # Remove extension
        name = re.sub(r'\.(pdf|docx|txt|csv)$', '', name, flags=re.IGNORECASE)
        
        # Remove processing suffix (_N)
        name = re.sub(r'_\d+$', '', name)
        
        return name
    
    def _is_match(self, source_file: str, original_filename: str, base_filename: str) -> bool:
        """
        Check if source_file matches the target filename
        
        Handles:
        - Exact matches: "report.pdf" == "report.pdf"
        - Suffix matches: "report.pdf" matches "report_1.pdf", "report_2.pdf"
        - Path variations: "report.pdf" matches "uploads/report.pdf"
        
        Prevents false matches:
        - "report.pdf" does NOT match "report2.pdf"
        - "report.pdf" does NOT match "other_report.pdf"
        """
        # Strategy 1: Exact filename match
        if original_filename in source_file or source_file.endswith(original_filename):
            return True
        
        # Strategy 2: Base filename with suffix
        source_base = self.normalize_filename(source_file)
        
        # Must match base exactly
        if source_base != base_filename:
            return False
        
        # Check if source has valid suffix pattern
        # Extract the part after base_filename in source_file
        source_name = source_file.split('/')[-1]  # Get filename without path
        source_name_no_ext = re.sub(r'\.(pdf|docx|txt|csv)$', '', source_name, flags=re.IGNORECASE)
        
        # Check suffix
        if source_name_no_ext == base_filename:
            # Exact match (no suffix)
            return True
        elif source_name_no_ext.startswith(base_filename + '_'):
            # Has suffix - check if it's a valid processing suffix (_N)
            suffix = source_name_no_ext[len(base_filename):]
            if re.match(r'^_\d+$', suffix):
                return True
        
        return False
    
    def validate_no_cross_contamination(self, 
                                       filename: str, 
                                       matched_chunks: List[Dict],
                                       all_filenames: List[str]) -> bool:
        """
        Validate that matched chunks don't belong to other files
        
        Args:
            filename: Target filename
            matched_chunks: Chunks matched for this file
            all_filenames: All uploaded filenames in session
            
        Returns:
            True if no cross-contamination detected
        """
        base_filename = self.normalize_filename(filename)
        other_bases = [self.normalize_filename(f) for f in all_filenames if f != filename]
        
        for chunk in matched_chunks:
            source_file = chunk.get('source_file', '')
            source_base = self.normalize_filename(source_file)
            
            # Check if this chunk belongs to another file
            if source_base in other_bases:
                print(f"⚠️ CROSS-CONTAMINATION: Chunk '{source_file}' matched for '{filename}' but belongs to another file!")
                return False
        
        return True


# Singleton instance
_file_chunk_matcher = None

def get_file_chunk_matcher() -> FileChunkMatcher:
    """Get singleton instance of FileChunkMatcher"""
    global _file_chunk_matcher
    if _file_chunk_matcher is None:
        _file_chunk_matcher = FileChunkMatcher()
    return _file_chunk_matcher
