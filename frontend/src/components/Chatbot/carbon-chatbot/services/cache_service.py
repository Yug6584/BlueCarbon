import json
import time
import hashlib
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import threading
from config import Config

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    # Redis not available - using in-memory cache (this is fine)

class MultiLevelCache:
    """High-performance multi-level caching system with Redis and in-memory fallback"""
    
    def __init__(self, use_redis: bool = True):
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.ttl = Config.CACHE_TTL
        
        # In-memory cache as fallback/L1 cache
        self._memory_cache = {}
        self._cache_timestamps = {}
        self._cache_lock = threading.RLock()
        
        # Redis connection (L2 cache)
        self.redis_client = None
        if self.use_redis:
            try:
                self.redis_client = redis.Redis(
                    host=Config.REDIS_HOST,
                    port=Config.REDIS_PORT,
                    db=Config.REDIS_DB,
                    password=Config.REDIS_PASSWORD,
                    decode_responses=True,
                    socket_timeout=1.0,
                    socket_connect_timeout=1.0
                )
                # Test connection
                self.redis_client.ping()
                print(f"✅ Redis cache connected: {Config.REDIS_HOST}:{Config.REDIS_PORT}")
            except Exception as e:
                # Redis connection failed - using memory cache (this is fine)
                self.redis_client = None
                self.use_redis = False
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'redis_hits': 0,
            'memory_hits': 0,
            'sets': 0,
            'evictions': 0
        }
        
        print(f"🚀 MultiLevelCache initialized (Redis: {self.use_redis})")
    
    def _generate_key(self, key: str, prefix: str = "") -> str:
        """Generate cache key with optional prefix"""
        if prefix:
            key = f"{prefix}:{key}"
        # Hash long keys to avoid Redis key length limits
        if len(key) > 200:
            key = hashlib.md5(key.encode()).hexdigest()
        return key
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage"""
        try:
            return json.dumps(value, default=str)
        except Exception as e:
            print(f"Serialization error: {e}")
            return json.dumps(str(value))
    
    def _deserialize_value(self, value: str) -> Any:
        """Deserialize value from storage"""
        try:
            return json.loads(value)
        except Exception as e:
            print(f"Deserialization error: {e}")
            return value
    
    def _cleanup_memory_cache(self):
        """Clean up expired entries from memory cache"""
        current_time = time.time()
        expired_keys = []
        
        with self._cache_lock:
            for key, timestamp in self._cache_timestamps.items():
                if current_time - timestamp > self.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._memory_cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
                self.stats['evictions'] += 1
    
    def get(self, key: str, prefix: str = "") -> Optional[Any]:
        """Get value from cache (L1 memory -> L2 Redis)"""
        cache_key = self._generate_key(key, prefix)
        
        # Check L1 cache (memory) first
        with self._cache_lock:
            if cache_key in self._memory_cache:
                timestamp = self._cache_timestamps.get(cache_key, 0)
                if time.time() - timestamp < self.ttl:
                    self.stats['hits'] += 1
                    self.stats['memory_hits'] += 1
                    return self._memory_cache[cache_key]
                else:
                    # Expired, remove from memory cache
                    self._memory_cache.pop(cache_key, None)
                    self._cache_timestamps.pop(cache_key, None)
        
        # Check L2 cache (Redis)
        if self.redis_client:
            try:
                redis_value = self.redis_client.get(cache_key)
                if redis_value is not None:
                    value = self._deserialize_value(redis_value)
                    
                    # Store in L1 cache for faster future access
                    with self._cache_lock:
                        self._memory_cache[cache_key] = value
                        self._cache_timestamps[cache_key] = time.time()
                    
                    self.stats['hits'] += 1
                    self.stats['redis_hits'] += 1
                    return value
            except Exception as e:
                print(f"Redis get error: {e}")
        
        # Cache miss
        self.stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any, prefix: str = "", ttl: Optional[int] = None) -> bool:
        """Set value in cache (both L1 and L2)"""
        cache_key = self._generate_key(key, prefix)
        cache_ttl = ttl or self.ttl
        
        try:
            # Store in L1 cache (memory)
            with self._cache_lock:
                self._memory_cache[cache_key] = value
                self._cache_timestamps[cache_key] = time.time()
                
                # Periodic cleanup
                if len(self._memory_cache) % 100 == 0:
                    self._cleanup_memory_cache()
            
            # Store in L2 cache (Redis)
            if self.redis_client:
                try:
                    serialized_value = self._serialize_value(value)
                    self.redis_client.setex(cache_key, cache_ttl, serialized_value)
                except Exception as e:
                    print(f"Redis set error: {e}")
            
            self.stats['sets'] += 1
            return True
            
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str, prefix: str = "") -> bool:
        """Delete value from cache"""
        cache_key = self._generate_key(key, prefix)
        
        # Remove from L1 cache
        with self._cache_lock:
            self._memory_cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)
        
        # Remove from L2 cache
        if self.redis_client:
            try:
                self.redis_client.delete(cache_key)
            except Exception as e:
                print(f"Redis delete error: {e}")
        
        return True
    
    def clear(self, prefix: str = "") -> bool:
        """Clear cache entries with optional prefix"""
        if prefix:
            # Clear specific prefix
            if self.redis_client:
                try:
                    pattern = f"{prefix}:*"
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
                except Exception as e:
                    print(f"Redis clear error: {e}")
            
            # Clear from memory cache
            with self._cache_lock:
                keys_to_remove = [k for k in self._memory_cache.keys() if k.startswith(f"{prefix}:")]
                for key in keys_to_remove:
                    self._memory_cache.pop(key, None)
                    self._cache_timestamps.pop(key, None)
        else:
            # Clear all
            if self.redis_client:
                try:
                    self.redis_client.flushdb()
                except Exception as e:
                    print(f"Redis flush error: {e}")
            
            with self._cache_lock:
                self._memory_cache.clear()
                self._cache_timestamps.clear()
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_requests': total_requests,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': round(hit_rate, 2),
            'memory_hits': self.stats['memory_hits'],
            'redis_hits': self.stats['redis_hits'],
            'sets': self.stats['sets'],
            'evictions': self.stats['evictions'],
            'memory_cache_size': len(self._memory_cache),
            'redis_available': self.use_redis
        }

class SpecializedCaches:
    """Specialized cache managers for different data types"""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding for text"""
        key = hashlib.md5(text.encode()).hexdigest()
        return self.cache.get(key, prefix="embedding")
    
    def set_embedding(self, text: str, embedding: List[float]) -> bool:
        """Cache embedding for text"""
        key = hashlib.md5(text.encode()).hexdigest()
        return self.cache.set(key, embedding, prefix="embedding")
    
    def get_response(self, query: str, context_type: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached response"""
        key = hashlib.md5(f"{query}_{context_type}_{session_id}".encode()).hexdigest()
        return self.cache.get(key, prefix="response")
    
    def set_response(self, query: str, context_type: str, session_id: str, response: Dict[str, Any]) -> bool:
        """Cache response"""
        key = hashlib.md5(f"{query}_{context_type}_{session_id}".encode()).hexdigest()
        return self.cache.set(key, response, prefix="response")
    
    def get_chunks(self, query: str, top_k: int) -> Optional[List[Dict[str, Any]]]:
        """Get cached retrieval results"""
        key = hashlib.md5(f"{query}_{top_k}".encode()).hexdigest()
        return self.cache.get(key, prefix="chunks")
    
    def set_chunks(self, query: str, top_k: int, chunks: List[Dict[str, Any]]) -> bool:
        """Cache retrieval results"""
        key = hashlib.md5(f"{query}_{top_k}".encode()).hexdigest()
        return self.cache.set(key, chunks, prefix="chunks")
    
    def get_web_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached web search results"""
        key = hashlib.md5(query.encode()).hexdigest()
        return self.cache.get(key, prefix="websearch")
    
    def set_web_search(self, query: str, results: List[Dict[str, Any]]) -> bool:
        """Cache web search results"""
        key = hashlib.md5(query.encode()).hexdigest()
        # Cache web results for longer (they change less frequently)
        return self.cache.set(key, results, prefix="websearch", ttl=7200)  # 2 hours

# Global cache instances
_cache = None
_specialized_caches = None

def get_cache() -> MultiLevelCache:
    """Get global cache instance"""
    global _cache
    if _cache is None:
        _cache = MultiLevelCache()
    return _cache

def get_specialized_caches() -> SpecializedCaches:
    """Get specialized cache managers"""
    global _specialized_caches
    if _specialized_caches is None:
        _specialized_caches = SpecializedCaches(get_cache())
    return _specialized_caches