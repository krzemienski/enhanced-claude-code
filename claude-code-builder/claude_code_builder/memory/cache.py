"""Performance-optimized caching system for memory operations."""

import logging
import threading
import time
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict, defaultdict
import hashlib
import weakref
import gc

logger = logging.getLogger(__name__)


class CachePolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    SIZE = "size"  # Size-based eviction
    ADAPTIVE = "adaptive"  # Adaptive policy based on usage patterns


class CacheLevel(Enum):
    """Cache hierarchy levels."""
    L1_MEMORY = "l1_memory"  # Fast in-memory cache
    L2_COMPRESSED = "l2_compressed"  # Compressed memory cache
    L3_DISK = "l3_disk"  # Disk-based cache


@dataclass
class CacheEntry:
    """Individual cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    priority: int = 1
    compressed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0
    avg_access_time_ms: float = 0.0
    last_cleanup: Optional[datetime] = None


@dataclass
class CacheConfig:
    """Cache configuration parameters."""
    max_size_mb: int = 256
    max_entries: int = 10000
    default_ttl_seconds: int = 3600
    policy: CachePolicy = CachePolicy.ADAPTIVE
    compression_threshold_kb: int = 64
    cleanup_interval_seconds: int = 300
    persistence_enabled: bool = False
    persistence_path: Optional[str] = None
    preload_enabled: bool = False


class MultiLevelCache:
    """High-performance multi-level caching system."""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """Initialize the multi-level cache."""
        self.config = config or CacheConfig()
        self.lock = threading.RLock()
        
        # Cache levels
        self._l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._l2_cache: Dict[str, bytes] = {}  # Compressed storage
        self._l3_cache: Dict[str, str] = {}    # Disk references
        
        # Cache statistics per level
        self._l1_stats = CacheStats()
        self._l2_stats = CacheStats()
        self._l3_stats = CacheStats()
        
        # Access patterns for adaptive policy
        self._access_patterns: Dict[str, List[float]] = defaultdict(list)
        self._frequency_tracker: Dict[str, int] = defaultdict(int)
        
        # Background cleanup
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        
        # Weak references for automatic cleanup
        self._weak_refs: Dict[str, weakref.ref] = {}
        
        # Performance monitoring
        self._performance_metrics = {
            "total_operations": 0,
            "avg_latency_ms": 0.0,
            "peak_memory_mb": 0.0,
            "compression_ratio": 0.0
        }
        
        # Start background tasks
        self._start_background_tasks()
        
        logger.info("Multi-level cache initialized")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with multi-level lookup."""
        start_time = time.time()
        
        with self.lock:
            try:
                # L1 Cache lookup (fastest)
                if key in self._l1_cache:
                    entry = self._l1_cache[key]
                    
                    # Check TTL
                    if self._is_expired(entry):
                        self._remove_from_l1(key)
                        self._l1_stats.misses += 1
                    else:
                        # Update access information
                        entry.last_accessed = datetime.now()
                        entry.access_count += 1
                        
                        # Move to end (LRU)
                        self._l1_cache.move_to_end(key)
                        
                        # Update access patterns
                        self._update_access_patterns(key)
                        
                        self._l1_stats.hits += 1
                        self._update_performance_metrics(start_time)
                        
                        logger.debug(f"L1 cache hit: {key}")
                        return entry.value
                
                # L2 Cache lookup (compressed)
                if key in self._l2_cache:
                    compressed_data = self._l2_cache[key]
                    
                    try:
                        # Decompress and deserialize
                        value = self._decompress_entry(compressed_data)
                        
                        # Promote to L1
                        self._promote_to_l1(key, value)
                        
                        self._l2_stats.hits += 1
                        self._update_performance_metrics(start_time)
                        
                        logger.debug(f"L2 cache hit: {key}")
                        return value
                    
                    except Exception as e:
                        logger.error(f"L2 cache corruption for key {key}: {e}")
                        del self._l2_cache[key]
                        self._l2_stats.misses += 1
                
                # L3 Cache lookup (disk-based)
                if key in self._l3_cache and self.config.persistence_enabled:
                    file_path = self._l3_cache[key]
                    
                    try:
                        value = self._load_from_disk(file_path)
                        
                        # Promote to higher levels
                        self._promote_to_l1(key, value)
                        
                        self._l3_stats.hits += 1
                        self._update_performance_metrics(start_time)
                        
                        logger.debug(f"L3 cache hit: {key}")
                        return value
                    
                    except Exception as e:
                        logger.error(f"L3 cache error for key {key}: {e}")
                        del self._l3_cache[key]
                        self._l3_stats.misses += 1
                
                # Cache miss
                self._l1_stats.misses += 1
                self._update_performance_metrics(start_time)
                
                logger.debug(f"Cache miss: {key}")
                return default
            
            except Exception as e:
                logger.error(f"Cache get error for key {key}: {e}")
                return default
    
    def put(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        priority: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Put value into cache with intelligent placement."""
        start_time = time.time()
        
        with self.lock:
            try:
                # Calculate value size
                size_bytes = self._calculate_size(value)
                
                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    access_count=1,
                    size_bytes=size_bytes,
                    ttl_seconds=ttl_seconds or self.config.default_ttl_seconds,
                    priority=priority,
                    metadata=metadata or {}
                )
                
                # Determine optimal cache level
                target_level = self._determine_cache_level(entry)
                
                if target_level == CacheLevel.L1_MEMORY:
                    self._put_l1(key, entry)
                elif target_level == CacheLevel.L2_COMPRESSED:
                    self._put_l2(key, entry)
                elif target_level == CacheLevel.L3_DISK:
                    self._put_l3(key, entry)
                
                # Update access patterns
                self._update_access_patterns(key)
                
                self._update_performance_metrics(start_time)
                
                logger.debug(f"Cache put: {key} -> {target_level.value}")
            
            except Exception as e:
                logger.error(f"Cache put error for key {key}: {e}")
    
    def invalidate(self, key: str) -> bool:
        """Remove key from all cache levels."""
        with self.lock:
            removed = False
            
            if key in self._l1_cache:
                del self._l1_cache[key]
                self._l1_stats.entry_count -= 1
                removed = True
            
            if key in self._l2_cache:
                del self._l2_cache[key]
                self._l2_stats.entry_count -= 1
                removed = True
            
            if key in self._l3_cache:
                file_path = self._l3_cache[key]
                try:
                    self._remove_from_disk(file_path)
                except Exception as e:
                    logger.warning(f"Failed to remove disk cache file {file_path}: {e}")
                del self._l3_cache[key]
                self._l3_stats.entry_count -= 1
                removed = True
            
            # Clean up tracking data
            if key in self._access_patterns:
                del self._access_patterns[key]
            if key in self._frequency_tracker:
                del self._frequency_tracker[key]
            if key in self._weak_refs:
                del self._weak_refs[key]
            
            if removed:
                logger.debug(f"Invalidated cache key: {key}")
            
            return removed
    
    def clear(self, level: Optional[CacheLevel] = None) -> None:
        """Clear cache at specified level or all levels."""
        with self.lock:
            if level is None or level == CacheLevel.L1_MEMORY:
                self._l1_cache.clear()
                self._l1_stats = CacheStats()
            
            if level is None or level == CacheLevel.L2_COMPRESSED:
                self._l2_cache.clear()
                self._l2_stats = CacheStats()
            
            if level is None or level == CacheLevel.L3_DISK:
                for file_path in self._l3_cache.values():
                    try:
                        self._remove_from_disk(file_path)
                    except Exception:
                        pass
                self._l3_cache.clear()
                self._l3_stats = CacheStats()
            
            if level is None:
                self._access_patterns.clear()
                self._frequency_tracker.clear()
                self._weak_refs.clear()
            
            logger.info(f"Cleared cache level: {level.value if level else 'all'}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        with self.lock:
            total_hits = self._l1_stats.hits + self._l2_stats.hits + self._l3_stats.hits
            total_misses = self._l1_stats.misses + self._l2_stats.misses + self._l3_stats.misses
            total_requests = total_hits + total_misses
            
            overall_hit_rate = (total_hits / total_requests) if total_requests > 0 else 0.0
            
            return {
                "overall": {
                    "hit_rate": overall_hit_rate,
                    "total_requests": total_requests,
                    "total_hits": total_hits,
                    "total_misses": total_misses
                },
                "l1_memory": {
                    "hits": self._l1_stats.hits,
                    "misses": self._l1_stats.misses,
                    "entries": len(self._l1_cache),
                    "size_mb": sum(entry.size_bytes for entry in self._l1_cache.values()) / (1024 * 1024),
                    "hit_rate": self._l1_stats.hits / (self._l1_stats.hits + self._l1_stats.misses) if (self._l1_stats.hits + self._l1_stats.misses) > 0 else 0.0
                },
                "l2_compressed": {
                    "hits": self._l2_stats.hits,
                    "misses": self._l2_stats.misses,
                    "entries": len(self._l2_cache),
                    "size_mb": sum(len(data) for data in self._l2_cache.values()) / (1024 * 1024),
                    "hit_rate": self._l2_stats.hits / (self._l2_stats.hits + self._l2_stats.misses) if (self._l2_stats.hits + self._l2_stats.misses) > 0 else 0.0
                },
                "l3_disk": {
                    "hits": self._l3_stats.hits,
                    "misses": self._l3_stats.misses,
                    "entries": len(self._l3_cache),
                    "hit_rate": self._l3_stats.hits / (self._l3_stats.hits + self._l3_stats.misses) if (self._l3_stats.hits + self._l3_stats.misses) > 0 else 0.0
                },
                "performance": self._performance_metrics
            }
    
    def preload(self, keys: List[str], loader_func: Callable[[str], Any]) -> int:
        """Preload cache with data from loader function."""
        if not self.config.preload_enabled:
            return 0
        
        loaded_count = 0
        
        for key in keys:
            try:
                if not self._exists_in_any_level(key):
                    value = loader_func(key)
                    if value is not None:
                        self.put(key, value)
                        loaded_count += 1
            except Exception as e:
                logger.warning(f"Failed to preload key {key}: {e}")
        
        logger.info(f"Preloaded {loaded_count} cache entries")
        return loaded_count
    
    def optimize(self) -> None:
        """Optimize cache performance based on access patterns."""
        with self.lock:
            # Analyze access patterns
            hot_keys = self._identify_hot_keys()
            cold_keys = self._identify_cold_keys()
            
            # Promote hot keys to L1
            for key in hot_keys:
                if key in self._l2_cache or key in self._l3_cache:
                    value = self.get(key)  # This will promote to L1
            
            # Demote cold keys from L1
            for key in cold_keys:
                if key in self._l1_cache:
                    self._demote_from_l1(key)
            
            # Adjust cache sizes based on usage
            self._adjust_cache_sizes()
            
            logger.info("Cache optimization completed")
    
    def _determine_cache_level(self, entry: CacheEntry) -> CacheLevel:
        """Determine optimal cache level for entry."""
        # High priority or frequently accessed -> L1
        if entry.priority > 5 or self._frequency_tracker.get(entry.key, 0) > 10:
            return CacheLevel.L1_MEMORY
        
        # Large entries -> L2 (compressed)
        if entry.size_bytes > self.config.compression_threshold_kb * 1024:
            return CacheLevel.L2_COMPRESSED
        
        # Default to L1 for now, adaptive policy will adjust
        return CacheLevel.L1_MEMORY
    
    def _put_l1(self, key: str, entry: CacheEntry) -> None:
        """Put entry in L1 cache."""
        # Check if we need to evict
        if len(self._l1_cache) >= self.config.max_entries:
            self._evict_l1()
        
        # Remove from other levels if present
        if key in self._l2_cache:
            del self._l2_cache[key]
        if key in self._l3_cache:
            del self._l3_cache[key]
        
        self._l1_cache[key] = entry
        self._l1_stats.entry_count += 1
        self._l1_stats.size_bytes += entry.size_bytes
    
    def _put_l2(self, key: str, entry: CacheEntry) -> None:
        """Put entry in L2 cache (compressed)."""
        compressed_data = self._compress_entry(entry)
        self._l2_cache[key] = compressed_data
        self._l2_stats.entry_count += 1
        self._l2_stats.size_bytes += len(compressed_data)
    
    def _put_l3(self, key: str, entry: CacheEntry) -> None:
        """Put entry in L3 cache (disk)."""
        if self.config.persistence_enabled and self.config.persistence_path:
            file_path = self._save_to_disk(key, entry)
            self._l3_cache[key] = file_path
            self._l3_stats.entry_count += 1
    
    def _evict_l1(self) -> None:
        """Evict entry from L1 cache based on policy."""
        if not self._l1_cache:
            return
        
        if self.config.policy == CachePolicy.LRU:
            # Remove least recently used (first item)
            key, entry = self._l1_cache.popitem(last=False)
        elif self.config.policy == CachePolicy.LFU:
            # Remove least frequently used
            key = min(self._l1_cache.keys(), key=lambda k: self._l1_cache[k].access_count)
            entry = self._l1_cache.pop(key)
        elif self.config.policy == CachePolicy.TTL:
            # Remove expired entries first
            now = datetime.now()
            expired_keys = [
                k for k, v in self._l1_cache.items()
                if self._is_expired(v)
            ]
            if expired_keys:
                key = expired_keys[0]
                entry = self._l1_cache.pop(key)
            else:
                # Fall back to LRU
                key, entry = self._l1_cache.popitem(last=False)
        else:  # ADAPTIVE or SIZE
            # Use adaptive policy
            key = self._adaptive_eviction()
            entry = self._l1_cache.pop(key)
        
        # Try to demote to L2 if valuable
        if entry.priority > 1 or entry.access_count > 1:
            self._put_l2(key, entry)
        
        self._l1_stats.evictions += 1
        self._l1_stats.size_bytes -= entry.size_bytes
        
        logger.debug(f"Evicted from L1: {key}")
    
    def _adaptive_eviction(self) -> str:
        """Adaptive eviction based on access patterns."""
        # Score each entry based on multiple factors
        scores = {}
        
        for key, entry in self._l1_cache.items():
            score = 0.0
            
            # Recency score (higher is better)
            age_seconds = (datetime.now() - entry.last_accessed).total_seconds()
            score += 1.0 / (1.0 + age_seconds / 3600)  # Decay over hours
            
            # Frequency score
            score += min(entry.access_count / 100.0, 1.0)
            
            # Priority score
            score += entry.priority / 10.0
            
            # Size penalty (larger entries are more likely to be evicted)
            score -= entry.size_bytes / (1024 * 1024)  # MB penalty
            
            scores[key] = score
        
        # Return key with lowest score
        return min(scores.keys(), key=lambda k: scores[k])
    
    def _promote_to_l1(self, key: str, value: Any) -> None:
        """Promote value to L1 cache."""
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            size_bytes=self._calculate_size(value)
        )
        
        self._put_l1(key, entry)
    
    def _demote_from_l1(self, key: str) -> None:
        """Demote entry from L1 to L2."""
        if key in self._l1_cache:
            entry = self._l1_cache.pop(key)
            self._put_l2(key, entry)
            self._l1_stats.entry_count -= 1
            self._l1_stats.size_bytes -= entry.size_bytes
    
    def _compress_entry(self, entry: CacheEntry) -> bytes:
        """Compress cache entry for L2 storage."""
        import pickle
        import gzip
        
        pickled_data = pickle.dumps(entry.value)
        return gzip.compress(pickled_data, compresslevel=6)
    
    def _decompress_entry(self, compressed_data: bytes) -> Any:
        """Decompress entry from L2 storage."""
        import pickle
        import gzip
        
        decompressed_data = gzip.decompress(compressed_data)
        return pickle.loads(decompressed_data)
    
    def _save_to_disk(self, key: str, entry: CacheEntry) -> str:
        """Save entry to disk for L3 storage."""
        import os
        import pickle
        
        if not self.config.persistence_path:
            raise ValueError("Persistence path not configured")
        
        # Create cache directory if it doesn't exist
        cache_dir = Path(self.config.persistence_path)
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate safe filename
        safe_key = hashlib.sha256(key.encode()).hexdigest()
        file_path = cache_dir / f"{safe_key}.cache"
        
        with open(file_path, 'wb') as f:
            pickle.dump(entry.value, f)
        
        return str(file_path)
    
    def _load_from_disk(self, file_path: str) -> Any:
        """Load entry from disk."""
        import pickle
        
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    
    def _remove_from_disk(self, file_path: str) -> None:
        """Remove file from disk."""
        import os
        
        if os.path.exists(file_path):
            os.remove(file_path)
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes."""
        import sys
        
        if hasattr(value, '__sizeof__'):
            return sys.getsizeof(value)
        else:
            return len(str(value).encode())
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        if entry.ttl_seconds is None:
            return False
        
        age_seconds = (datetime.now() - entry.created_at).total_seconds()
        return age_seconds > entry.ttl_seconds
    
    def _exists_in_any_level(self, key: str) -> bool:
        """Check if key exists in any cache level."""
        return (key in self._l1_cache or 
                key in self._l2_cache or 
                key in self._l3_cache)
    
    def _update_access_patterns(self, key: str) -> None:
        """Update access patterns for adaptive policy."""
        current_time = time.time()
        
        # Track access frequency
        self._frequency_tracker[key] += 1
        
        # Track access timing patterns
        if key not in self._access_patterns:
            self._access_patterns[key] = []
        
        self._access_patterns[key].append(current_time)
        
        # Keep only recent patterns (last 100 accesses or 1 hour)
        cutoff_time = current_time - 3600  # 1 hour ago
        self._access_patterns[key] = [
            t for t in self._access_patterns[key]
            if t > cutoff_time
        ][-100:]  # Keep last 100
    
    def _identify_hot_keys(self) -> List[str]:
        """Identify frequently accessed keys."""
        # Sort by frequency and recent access
        frequency_scores = {}
        
        for key, count in self._frequency_tracker.items():
            recent_accesses = len(self._access_patterns.get(key, []))
            frequency_scores[key] = count + recent_accesses * 2
        
        # Return top 10% most accessed keys
        sorted_keys = sorted(frequency_scores.keys(), 
                           key=lambda k: frequency_scores[k], 
                           reverse=True)
        
        hot_count = max(1, len(sorted_keys) // 10)
        return sorted_keys[:hot_count]
    
    def _identify_cold_keys(self) -> List[str]:
        """Identify rarely accessed keys."""
        current_time = time.time()
        cold_keys = []
        
        for key, entry in self._l1_cache.items():
            last_access_time = entry.last_accessed.timestamp()
            age_seconds = current_time - last_access_time
            
            # Consider cold if not accessed in last hour and low frequency
            if (age_seconds > 3600 and 
                entry.access_count < 3 and
                self._frequency_tracker.get(key, 0) < 2):
                cold_keys.append(key)
        
        return cold_keys
    
    def _adjust_cache_sizes(self) -> None:
        """Adjust cache sizes based on usage patterns."""
        # This could implement dynamic size adjustment
        # For now, it's a placeholder for future optimization
        pass
    
    def _update_performance_metrics(self, start_time: float) -> None:
        """Update performance metrics."""
        latency_ms = (time.time() - start_time) * 1000
        
        self._performance_metrics["total_operations"] += 1
        
        # Update average latency
        total_ops = self._performance_metrics["total_operations"]
        current_avg = self._performance_metrics["avg_latency_ms"]
        self._performance_metrics["avg_latency_ms"] = (
            (current_avg * (total_ops - 1) + latency_ms) / total_ops
        )
    
    def _start_background_tasks(self) -> None:
        """Start background cleanup and optimization tasks."""
        self._cleanup_thread = threading.Thread(
            target=self._background_cleanup,
            daemon=True
        )
        self._cleanup_thread.start()
    
    def _background_cleanup(self) -> None:
        """Background cleanup task."""
        while not self._stop_cleanup.wait(self.config.cleanup_interval_seconds):
            try:
                self._cleanup_expired_entries()
                self._optimize_if_needed()
                gc.collect()  # Force garbage collection
            except Exception as e:
                logger.error(f"Background cleanup error: {e}")
    
    def _cleanup_expired_entries(self) -> None:
        """Clean up expired entries from all levels."""
        with self.lock:
            # L1 cleanup
            expired_l1 = [
                key for key, entry in self._l1_cache.items()
                if self._is_expired(entry)
            ]
            for key in expired_l1:
                self._remove_from_l1(key)
            
            if expired_l1:
                logger.debug(f"Cleaned up {len(expired_l1)} expired L1 entries")
    
    def _optimize_if_needed(self) -> None:
        """Run optimization if certain conditions are met."""
        total_entries = len(self._l1_cache) + len(self._l2_cache) + len(self._l3_cache)
        
        # Optimize if cache is getting full
        if total_entries > self.config.max_entries * 0.8:
            self.optimize()
    
    def _remove_from_l1(self, key: str) -> None:
        """Remove key from L1 cache."""
        if key in self._l1_cache:
            entry = self._l1_cache.pop(key)
            self._l1_stats.entry_count -= 1
            self._l1_stats.size_bytes -= entry.size_bytes
    
    def close(self) -> None:
        """Close cache and cleanup resources."""
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)
        
        # Clear all caches
        self.clear()
        
        logger.info("Cache closed")


# Convenience function for global cache instance
_global_cache: Optional[MultiLevelCache] = None


def get_global_cache() -> MultiLevelCache:
    """Get or create global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = MultiLevelCache()
    return _global_cache


def set_global_cache(cache: MultiLevelCache) -> None:
    """Set global cache instance."""
    global _global_cache
    _global_cache = cache