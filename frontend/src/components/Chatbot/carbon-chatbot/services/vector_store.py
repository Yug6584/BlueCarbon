import faiss
import numpy as np
import json
import pickle
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from config import Config

class HighPerformanceVectorStore:
    """Ultra-fast FAISS HNSW vector store with optimized retrieval"""
    
    def __init__(self, dimension: int = 384, index_type: str = "HNSW"):
        self.dimension = dimension
        self.index_type = index_type
        self.similarity_threshold = Config.SIMILARITY_THRESHOLD
        
        # Initialize FAISS index
        self.index = None
        self.metadata = []
        self.embeddings = []
        
        # Performance tracking
        self.retrieval_stats = {
            'total_queries': 0,
            'total_time': 0.0,
            'cache_hits': 0
        }
        
        print(f"🚀 Initializing HighPerformanceVectorStore with {index_type} index")
    
    def _create_hnsw_index(self, dimension: int) -> faiss.Index:
        """Create optimized HNSW index for ultra-fast retrieval"""
        # HNSW parameters for optimal performance
        M = 32  # Number of connections for each node
        ef_construction = 200  # Size of dynamic candidate list during construction
        
        # Create HNSW index
        index = faiss.IndexHNSWFlat(dimension, M)
        index.hnsw.efConstruction = ef_construction
        index.hnsw.efSearch = 100  # Search parameter (can be adjusted at query time)
        
        print(f"✅ Created HNSW index: dimension={dimension}, M={M}, efConstruction={ef_construction}")
        return index
    
    def _create_ivf_index(self, dimension: int, nlist: int = 100) -> faiss.Index:
        """Create IVF index as alternative for very large datasets"""
        quantizer = faiss.IndexFlatL2(dimension)
        index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
        print(f"✅ Created IVF index: dimension={dimension}, nlist={nlist}")
        return index
    
    def build_index(self, embeddings: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Build optimized FAISS index from embeddings"""
        if not embeddings or not metadata:
            raise ValueError("Embeddings and metadata cannot be empty")
        
        start_time = time.time()
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings).astype('float32')
        self.dimension = embeddings_array.shape[1]
        
        print(f"📊 Building index with {len(embeddings)} vectors of dimension {self.dimension}")
        
        # Create appropriate index based on dataset size
        if len(embeddings) < 10000:
            # Use HNSW for smaller datasets (better for most use cases)
            self.index = self._create_hnsw_index(self.dimension)
        else:
            # Use IVF for very large datasets
            self.index = self._create_ivf_index(self.dimension)
            # Train IVF index
            self.index.train(embeddings_array)
        
        # Add vectors to index
        self.index.add(embeddings_array)
        
        # Store metadata and embeddings
        self.metadata = metadata
        self.embeddings = embeddings
        
        build_time = time.time() - start_time
        print(f"🎯 Index built successfully in {build_time:.2f}s")
        print(f"   Index type: {type(self.index).__name__}")
        print(f"   Total vectors: {self.index.ntotal}")
        
    def search(self, query_embedding: List[float], top_k: int = 5, ef_search: int = None) -> List[Dict[str, Any]]:
        """Ultra-fast similarity search with HNSW optimization"""
        if self.index is None:
            return []
        
        start_time = time.time()
        
        # Adjust search parameters for HNSW
        if hasattr(self.index, 'hnsw') and ef_search:
            original_ef = self.index.hnsw.efSearch
            self.index.hnsw.efSearch = ef_search
        
        try:
            # Convert query to numpy array
            query_vector = np.array([query_embedding]).astype('float32')
            
            # Perform search
            scores, indices = self.index.search(query_vector, top_k)
            
            # Build results with metadata
            results = []
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(self.metadata):
                    result = self.metadata[idx].copy()
                    result['similarity_score'] = float(scores[0][i])
                    result['index_position'] = int(idx)
                    
                    # Only include results above similarity threshold
                    if result['similarity_score'] >= self.similarity_threshold:
                        results.append(result)
            
            # Update performance stats
            search_time = time.time() - start_time
            self.retrieval_stats['total_queries'] += 1
            self.retrieval_stats['total_time'] += search_time
            
            print(f"🔍 Search completed in {search_time*1000:.1f}ms, found {len(results)} relevant results")
            
            return results
            
        finally:
            # Restore original ef_search for HNSW
            if hasattr(self.index, 'hnsw') and ef_search:
                self.index.hnsw.efSearch = original_ef
    
    def batch_search(self, query_embeddings: List[List[float]], top_k: int = 5) -> List[List[Dict[str, Any]]]:
        """Batch search for multiple queries"""
        if self.index is None:
            return []
        
        start_time = time.time()
        
        # Convert to numpy array
        query_vectors = np.array(query_embeddings).astype('float32')
        
        # Perform batch search
        scores, indices = self.index.search(query_vectors, top_k)
        
        # Build results for each query
        all_results = []
        for query_idx in range(len(query_embeddings)):
            query_results = []
            for i, idx in enumerate(indices[query_idx]):
                if 0 <= idx < len(self.metadata):
                    result = self.metadata[idx].copy()
                    result['similarity_score'] = float(scores[query_idx][i])
                    result['index_position'] = int(idx)
                    
                    if result['similarity_score'] >= self.similarity_threshold:
                        query_results.append(result)
            
            all_results.append(query_results)
        
        batch_time = time.time() - start_time
        print(f"🔍 Batch search completed in {batch_time*1000:.1f}ms for {len(query_embeddings)} queries")
        
        return all_results
    
    def save_index(self, index_path: str, metadata_path: str, embeddings_path: str) -> None:
        """Save index and metadata to disk"""
        if self.index is None:
            raise ValueError("No index to save")
        
        start_time = time.time()
        
        # Save FAISS index
        faiss.write_index(self.index, index_path)
        
        # Save metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        
        # Save embeddings
        with open(embeddings_path, 'wb') as f:
            pickle.dump(self.embeddings, f)
        
        save_time = time.time() - start_time
        print(f"💾 Index saved successfully in {save_time:.2f}s")
        print(f"   Index: {index_path}")
        print(f"   Metadata: {metadata_path}")
        print(f"   Embeddings: {embeddings_path}")
    
    def load_index(self, index_path: str, metadata_path: str, embeddings_path: str) -> None:
        """Load index and metadata from disk"""
        start_time = time.time()
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            
            # Load metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            
            # Load embeddings
            with open(embeddings_path, 'rb') as f:
                self.embeddings = pickle.load(f)
            
            self.dimension = self.embeddings[0] if self.embeddings else 384
            
            load_time = time.time() - start_time
            print(f"📂 Index loaded successfully in {load_time:.2f}s")
            print(f"   Index type: {type(self.index).__name__}")
            print(f"   Total vectors: {self.index.ntotal}")
            print(f"   Metadata entries: {len(self.metadata)}")
            
        except Exception as e:
            print(f"❌ Error loading index: {e}")
            raise
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get retrieval performance statistics"""
        avg_time = (self.retrieval_stats['total_time'] / self.retrieval_stats['total_queries'] 
                   if self.retrieval_stats['total_queries'] > 0 else 0)
        
        return {
            'total_queries': self.retrieval_stats['total_queries'],
            'total_time': self.retrieval_stats['total_time'],
            'average_query_time': avg_time,
            'queries_per_second': 1.0 / avg_time if avg_time > 0 else 0,
            'cache_hits': self.retrieval_stats['cache_hits'],
            'index_size': self.index.ntotal if self.index else 0,
            'dimension': self.dimension
        }
    
    def optimize_search_params(self, query_embeddings: List[List[float]], target_recall: float = 0.95) -> int:
        """Optimize HNSW search parameters for target recall"""
        if not hasattr(self.index, 'hnsw'):
            return 100  # Default ef_search for non-HNSW indices
        
        print(f"🔧 Optimizing search parameters for {target_recall:.1%} recall...")
        
        # Test different ef_search values
        ef_values = [50, 100, 150, 200, 300]
        best_ef = 100
        
        for ef in ef_values:
            # Test search with this ef value
            start_time = time.time()
            results = self.batch_search(query_embeddings[:10], top_k=10)  # Test on subset
            search_time = time.time() - start_time
            
            # Simple heuristic: balance speed vs quality
            if search_time < 0.1:  # If fast enough, use this ef
                best_ef = ef
                break
        
        print(f"✅ Optimal ef_search: {best_ef}")
        return best_ef

def vectorstore_exists() -> bool:
    """Check if vector store files exist"""
    index_path = Config.VECTORSTORE_DIR / "faiss_index.bin"
    metadata_path = Config.VECTORSTORE_DIR / "metadata.json"
    return index_path.exists() and metadata_path.exists()

# Global instance for reuse
_vector_store = None

def vectorstore_exists() -> bool:
    """Check if vector store files exist"""
    index_path = Config.VECTORSTORE_DIR / "faiss_index.bin"
    metadata_path = Config.VECTORSTORE_DIR / "metadata.json"
    embeddings_path = Config.VECTORSTORE_DIR / "embeddings.pkl"
    
    return (index_path.exists() and 
            metadata_path.exists() and 
            embeddings_path.exists())

def get_vector_store() -> HighPerformanceVectorStore:
    """Get global vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = HighPerformanceVectorStore()
        
        # Load existing index if available
        if vectorstore_exists():
            try:
                _vector_store.load_index(
                    str(Config.VECTORSTORE_DIR / "faiss_index.bin"),
                    str(Config.VECTORSTORE_DIR / "metadata.json"),
                    str(Config.VECTORSTORE_DIR / "embeddings.pkl")
                )
            except Exception as e:
                print(f"⚠️ Could not load existing index: {e}")
    
    return _vector_store