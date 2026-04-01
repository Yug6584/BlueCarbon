"""
Context Builder - Optimize context for Llama model
"""
from typing import List, Dict, Any


class ContextBuilder:
    """Build optimal context for Llama model from PDF chunks"""
    
    def __init__(self, max_chars: int = 20000):
        self.max_chars = max_chars
    
    def build_context(self, 
                     query: str,
                     file_chunks: List[Dict],
                     filename: str = None) -> str:
        """
        Build optimized context for Llama
        
        Returns formatted context string with:
        - File metadata
        - Relevant chunks in order
        - Clear section markers
        """
        if not file_chunks:
            return ""
        
        # Rank chunks by relevance
        ranked_chunks = self.rank_chunks(query, file_chunks)
        
        # Build context with clear structure
        context_parts = []
        
        # Add file header
        if filename:
            context_parts.append(f"=== DOCUMENT: {filename} ===\n")
        
        # Add chunks with page markers
        current_page = None
        total_chars = 0
        
        for chunk in ranked_chunks:
            page_num = chunk.get('page_number', 0)
            text = chunk.get('text', '')
            
            # Check if we're exceeding max chars
            if total_chars + len(text) > self.max_chars:
                # Try to fit partial chunk
                remaining = self.max_chars - total_chars
                if remaining > 200:  # Only if we can fit meaningful content
                    text = text[:remaining] + "..."
                else:
                    break
            
            # Add page marker if page changed
            if page_num != current_page:
                context_parts.append(f"\n=== PAGE {page_num} ===\n")
                current_page = page_num
            
            context_parts.append(text)
            context_parts.append("\n\n")
            
            total_chars += len(text)
        
        context = "".join(context_parts)
        
        print(f"📄 Built context: {len(context)} chars from {len(ranked_chunks)} chunks")
        
        return context
    
    def rank_chunks(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """
        Rank chunks by relevance
        
        Uses:
        - Semantic similarity (from vector store)
        - Page order
        - Keyword matching
        """
        # Sort by similarity score (descending) then page number (ascending)
        ranked = sorted(
            chunks,
            key=lambda x: (
                -x.get('similarity_score', 0.0),  # Higher similarity first
                x.get('page_number', 999)  # Earlier pages first
            )
        )
        
        # Boost chunks with query keywords
        query_keywords = set(query.lower().split())
        
        for chunk in ranked:
            text_lower = chunk.get('text', '').lower()
            keyword_matches = sum(1 for kw in query_keywords if kw in text_lower)
            
            # Boost similarity score based on keyword matches
            if keyword_matches > 0:
                chunk['similarity_score'] = chunk.get('similarity_score', 0.0) + (keyword_matches * 0.05)
        
        # Re-sort after boosting
        ranked = sorted(
            ranked,
            key=lambda x: (
                -x.get('similarity_score', 0.0),
                x.get('page_number', 999)
            )
        )
        
        return ranked
    
    def summarize_for_large_context(self, chunks: List[Dict], max_chunks: int = 20) -> List[Dict]:
        """
        Intelligently select chunks when context is too large
        
        Strategy:
        - Keep highest relevance chunks
        - Ensure page coverage
        - Maintain context flow
        """
        if len(chunks) <= max_chunks:
            return chunks
        
        # Take top chunks by relevance
        top_chunks = chunks[:max_chunks]
        
        # Sort by page order for coherent reading
        top_chunks = sorted(top_chunks, key=lambda x: x.get('page_number', 0))
        
        print(f"📊 Summarized: Selected {len(top_chunks)} most relevant chunks from {len(chunks)}")
        
        return top_chunks


# Singleton instance
_context_builder = None

def get_context_builder() -> ContextBuilder:
    """Get singleton instance of ContextBuilder"""
    global _context_builder
    if _context_builder is None:
        _context_builder = ContextBuilder()
    return _context_builder
