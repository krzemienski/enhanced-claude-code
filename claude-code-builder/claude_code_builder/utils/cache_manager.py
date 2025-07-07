"""Cache management utilities for Claude Code Builder."""
import time
import pickle
import json
import hashlib
from pathlib import Path
from typing import Any, Optional, Dict, List, Union, Callable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import threading
from collections import OrderedDict

from ..exceptions.base import ClaudeCodeBuilderError
from ..logging.logger import get_logger
from .path_utils import get_cache_dir, normalize_path
from .file_handler import FileHandler

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Single cache entry."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    size: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self) -> None:
        """Update access time and count."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class CacheManager:
    """Manages various types of caches."""
    
    def __init__(
        self,
        name: str = "default",
        max_size: Optional[int] = None,
        ttl: Optional[int] = None,
        persist: bool = False,
        cache_dir: Optional[Path] = None
    ):
        """Initialize cache manager.
        
        Args:
            name: Cache name
            max_size: Maximum cache size (entries)
            ttl: Default time-to-live in seconds
            persist: Persist cache to disk
            cache_dir: Cache directory
        """
        self.name = name
        self.max_size = max_size
        self.default_ttl = ttl
        self.persist = persist
        
        # Setup cache directory
        if cache_dir:
            self.cache_dir = normalize_path(cache_dir)
        else:
            self.cache_dir = get_cache_dir() / name
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # File handler for persistence
        self.file_handler = FileHandler()
        
        # Load persisted cache if exists
        if self.persist:
            self._load_cache()
    
    def get(
        self,
        key: str,
        default: Optional[T] = None
    ) -> Optional[T]:
        """Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                return default
            
            # Check expiration
            if entry.is_expired():
                self._remove_entry(key)
                return default
            
            # Update access info
            entry.touch()
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            
            return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        with self._lock:
            # Calculate expiration
            expires_at = None
            if ttl is not None or self.default_ttl is not None:
                ttl_seconds = ttl if ttl is not None else self.default_ttl
                expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            
            # Calculate size
            try:
                size = len(pickle.dumps(value))
            except:
                size = 0
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=expires_at,
                size=size
            )
            
            # Add to cache
            self._cache[key] = entry
            
            # Enforce size limit
            if self.max_size and len(self._cache) > self.max_size:
                self._evict_oldest()
            
            # Persist if enabled
            if self.persist:
                self._save_cache()
    
    def delete(self, key: str) -> bool:
        """Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted
        """
        with self._lock:
            return self._remove_entry(key)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            
            if self.persist:
                self._save_cache()
            
            logger.info(f"Cleared cache: {self.name}")
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists and not expired
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                return False
            
            if entry.is_expired():
                self._remove_entry(key)
                return False
            
            return True
    
    def size(self) -> int:
        """Get number of cache entries."""
        with self._lock:
            return len(self._cache)
    
    def memory_size(self) -> int:
        """Get total memory size of cache in bytes."""
        with self._lock:
            return sum(entry.size for entry in self._cache.values())
    
    def keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            # Clean expired entries first
            self._clean_expired()
            return list(self._cache.keys())
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Cache statistics
        """
        with self._lock:
            total_entries = len(self._cache)
            total_size = sum(entry.size for entry in self._cache.values())
            total_accesses = sum(entry.access_count for entry in self._cache.values())
            
            expired_count = sum(1 for entry in self._cache.values() if entry.is_expired())
            
            return {
                'name': self.name,
                'entries': total_entries,
                'size_bytes': total_size,
                'max_size': self.max_size,
                'total_accesses': total_accesses,
                'expired_entries': expired_count,
                'persist': self.persist,
                'cache_dir': str(self.cache_dir)
            }
    
    def cached(
        self,
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None
    ):
        """Decorator for caching function results.
        
        Args:
            ttl: Time-to-live in seconds
            key_func: Function to generate cache key
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default key generation
                    key_parts = [func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = ':'.join(key_parts)
                
                # Check cache
                result = self.get(cache_key)
                if result is not None:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
                
                # Call function
                logger.debug(f"Cache miss for {func.__name__}")
                result = func(*args, **kwargs)
                
                # Cache result
                self.set(cache_key, result, ttl=ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def memoize(self, func: Callable[..., T]) -> Callable[..., T]:
        """Simple memoization decorator.
        
        Args:
            func: Function to memoize
            
        Returns:
            Memoized function
        """
        return self.cached()(func)
    
    def _remove_entry(self, key: str) -> bool:
        """Remove entry from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if removed
        """
        if key in self._cache:
            del self._cache[key]
            
            if self.persist:
                self._save_cache()
            
            return True
        
        return False
    
    def _evict_oldest(self) -> None:
        """Evict oldest entry (LRU)."""
        if self._cache:
            # Remove first item (oldest)
            key = next(iter(self._cache))
            self._remove_entry(key)
            logger.debug(f"Evicted cache entry: {key}")
    
    def _clean_expired(self) -> None:
        """Remove all expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            self._remove_entry(key)
        
        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired entries")
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        cache_file = self.cache_dir / f"{self.name}.cache"
        
        try:
            # Convert to serializable format
            cache_data = {
                'version': '1.0',
                'name': self.name,
                'entries': {}
            }
            
            for key, entry in self._cache.items():
                # Skip expired entries
                if entry.is_expired():
                    continue
                
                cache_data['entries'][key] = {
                    'value': entry.value,
                    'created_at': entry.created_at.isoformat(),
                    'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
                    'access_count': entry.access_count,
                    'last_accessed': entry.last_accessed.isoformat(),
                    'size': entry.size
                }
            
            # Save using pickle for complex objects
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.debug(f"Saved cache to {cache_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        cache_file = self.cache_dir / f"{self.name}.cache"
        
        if not cache_file.exists():
            return
        
        try:
            # Load cache data
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Validate version
            if cache_data.get('version') != '1.0':
                logger.warning("Incompatible cache version")
                return
            
            # Restore entries
            for key, entry_data in cache_data.get('entries', {}).items():
                entry = CacheEntry(
                    key=key,
                    value=entry_data['value'],
                    created_at=datetime.fromisoformat(entry_data['created_at']),
                    expires_at=datetime.fromisoformat(entry_data['expires_at']) if entry_data['expires_at'] else None,
                    access_count=entry_data['access_count'],
                    last_accessed=datetime.fromisoformat(entry_data['last_accessed']),
                    size=entry_data['size']
                )
                
                # Skip expired entries
                if not entry.is_expired():
                    self._cache[key] = entry
            
            logger.info(f"Loaded {len(self._cache)} entries from cache")
            
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save cache if persistent."""
        if self.persist:
            self._save_cache()


# Global cache instances
_caches: Dict[str, CacheManager] = {}


def get_cache(
    name: str = "default",
    **kwargs
) -> CacheManager:
    """Get or create a cache instance.
    
    Args:
        name: Cache name
        **kwargs: Cache configuration
        
    Returns:
        Cache manager instance
    """
    if name not in _caches:
        _caches[name] = CacheManager(name=name, **kwargs)
    
    return _caches[name]


def clear_all_caches() -> None:
    """Clear all cache instances."""
    for cache in _caches.values():
        cache.clear()
    
    logger.info("Cleared all caches")


def cache_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all caches.
    
    Returns:
        Cache statistics by name
    """
    return {
        name: cache.stats()
        for name, cache in _caches.items()
    }