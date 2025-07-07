"""Persistent memory storage for context preservation and learning."""

import logging
import sqlite3
import json
import pickle
import gzip
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path
import threading
import hashlib
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory entries."""
    CONTEXT = "context"
    ERROR = "error"
    PATTERN = "pattern"
    SOLUTION = "solution"
    LEARNING = "learning"
    CONFIG = "config"
    TEMPLATE = "template"
    CACHE = "cache"


class MemoryPriority(Enum):
    """Memory priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MemoryEntry:
    """Individual memory entry."""
    id: str
    memory_type: MemoryType
    key: str
    data: Any
    timestamp: datetime
    priority: MemoryPriority = MemoryPriority.MEDIUM
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0


@dataclass
class MemoryQuery:
    """Query specification for memory retrieval."""
    memory_type: Optional[MemoryType] = None
    key_pattern: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    priority_min: Optional[MemoryPriority] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    limit: int = 100
    include_expired: bool = False


@dataclass
class MemoryStats:
    """Memory storage statistics."""
    total_entries: int
    entries_by_type: Dict[MemoryType, int] = field(default_factory=dict)
    entries_by_priority: Dict[MemoryPriority, int] = field(default_factory=dict)
    total_size_bytes: int = 0
    oldest_entry: Optional[datetime] = None
    newest_entry: Optional[datetime] = None
    expired_entries: int = 0


class PersistentMemoryStore:
    """Persistent memory storage with SQLite backend."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the memory store."""
        if db_path is None:
            db_path = Path.home() / ".claude_code_builder" / "memory" / "memory.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Initialize database
        self._init_database()
        
        # Configuration
        self.max_size_mb = 1000  # 1GB max size
        self.cleanup_interval_hours = 24
        self.default_ttl_hours = 168  # 7 days
        self.compression_threshold = 1024  # Compress entries > 1KB
        
        # Cache for frequent operations
        self._cache: Dict[str, MemoryEntry] = {}
        self._cache_max_size = 1000
        self._lock = threading.RLock()
        
        # Performance tracking
        self.stats = {
            "reads": 0,
            "writes": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        logger.info(f"Memory Store initialized at {self.db_path}")
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def store(
        self,
        key: str,
        data: Any,
        memory_type: MemoryType = MemoryType.CONTEXT,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_hours: Optional[int] = None
    ) -> str:
        """Store data in memory."""
        with self._lock:
            # Generate unique ID
            entry_id = self._generate_id(key, memory_type)
            
            # Calculate expiration
            expires_at = None
            if ttl_hours is not None:
                expires_at = datetime.now() + timedelta(hours=ttl_hours)
            elif self.default_ttl_hours > 0:
                expires_at = datetime.now() + timedelta(hours=self.default_ttl_hours)
            
            # Serialize data
            serialized_data = self._serialize_data(data)
            
            # Create memory entry
            entry = MemoryEntry(
                id=entry_id,
                memory_type=memory_type,
                key=key,
                data=data,
                timestamp=datetime.now(),
                priority=priority,
                tags=tags or [],
                metadata=metadata or {},
                expires_at=expires_at,
                size_bytes=len(serialized_data)
            )
            
            # Store in database
            self._store_entry(entry, serialized_data)
            
            # Update cache
            self._cache[entry_id] = entry
            self._manage_cache_size()
            
            # Update stats
            self.stats["writes"] += 1
            
            logger.debug(f"Stored memory entry: {entry_id} ({entry.size_bytes} bytes)")
            
            return entry_id
    
    def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve memory entry by ID."""
        with self._lock:
            # Check cache first
            if entry_id in self._cache:
                entry = self._cache[entry_id]
                self._update_access_stats(entry)
                self.stats["cache_hits"] += 1
                self.stats["reads"] += 1
                return entry
            
            # Load from database
            entry = self._load_entry(entry_id)
            if entry:
                # Update cache
                self._cache[entry_id] = entry
                self._manage_cache_size()
                
                # Update access stats
                self._update_access_stats(entry)
                
                self.stats["cache_misses"] += 1
            
            self.stats["reads"] += 1
            return entry
    
    def retrieve_by_key(
        self,
        key: str,
        memory_type: Optional[MemoryType] = None
    ) -> Optional[MemoryEntry]:
        """Retrieve memory entry by key."""
        entries = self.query(MemoryQuery(
            key_pattern=f"^{key}$",
            memory_type=memory_type,
            limit=1
        ))
        
        return entries[0] if entries else None
    
    def query(self, query: MemoryQuery) -> List[MemoryEntry]:
        """Query memory entries."""
        with self._lock:
            return self._query_entries(query)
    
    def update(
        self,
        entry_id: str,
        data: Optional[Any] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: Optional[MemoryPriority] = None
    ) -> bool:
        """Update an existing memory entry."""
        with self._lock:
            entry = self.retrieve(entry_id)
            if not entry:
                return False
            
            # Update fields
            if data is not None:
                entry.data = data
                entry.size_bytes = len(self._serialize_data(data))
            
            if tags is not None:
                entry.tags = tags
            
            if metadata is not None:
                entry.metadata.update(metadata)
            
            if priority is not None:
                entry.priority = priority
            
            # Update timestamp
            entry.timestamp = datetime.now()
            
            # Store updated entry
            serialized_data = self._serialize_data(entry.data)
            self._store_entry(entry, serialized_data)
            
            # Update cache
            self._cache[entry_id] = entry
            
            logger.debug(f"Updated memory entry: {entry_id}")
            
            return True
    
    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        with self._lock:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM memory_entries WHERE id = ?", (entry_id,))
            
            deleted = cursor.rowcount > 0
            self.connection.commit()
            
            # Remove from cache
            if entry_id in self._cache:
                del self._cache[entry_id]
            
            if deleted:
                logger.debug(f"Deleted memory entry: {entry_id}")
            
            return deleted
    
    def cleanup_expired(self) -> int:
        """Clean up expired memory entries."""
        with self._lock:
            now = datetime.now()
            cursor = self.connection.cursor()
            
            # Delete expired entries
            cursor.execute(
                "DELETE FROM memory_entries WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now.isoformat(),)
            )
            
            deleted_count = cursor.rowcount
            self.connection.commit()
            
            # Clean cache
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.expires_at and entry.expires_at < now
            ]
            for key in expired_keys:
                del self._cache[key]
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired memory entries")
            
            return deleted_count
    
    def get_stats(self) -> MemoryStats:
        """Get memory storage statistics."""
        with self._lock:
            cursor = self.connection.cursor()
            
            # Total entries
            cursor.execute("SELECT COUNT(*) as count FROM memory_entries")
            total_entries = cursor.fetchone()["count"]
            
            # Entries by type
            cursor.execute("""
                SELECT memory_type, COUNT(*) as count 
                FROM memory_entries 
                GROUP BY memory_type
            """)
            entries_by_type = {
                MemoryType(row["memory_type"]): row["count"]
                for row in cursor.fetchall()
            }
            
            # Entries by priority
            cursor.execute("""
                SELECT priority, COUNT(*) as count 
                FROM memory_entries 
                GROUP BY priority
            """)
            entries_by_priority = {
                MemoryPriority(row["priority"]): row["count"]
                for row in cursor.fetchall()
            }
            
            # Size statistics
            cursor.execute("SELECT SUM(size_bytes) as total_size FROM memory_entries")
            total_size = cursor.fetchone()["total_size"] or 0
            
            # Date range
            cursor.execute("""
                SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest 
                FROM memory_entries
            """)
            date_row = cursor.fetchone()
            oldest = None
            newest = None
            if date_row["oldest"]:
                oldest = datetime.fromisoformat(date_row["oldest"])
            if date_row["newest"]:
                newest = datetime.fromisoformat(date_row["newest"])
            
            # Expired entries
            now = datetime.now()
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM memory_entries 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (now.isoformat(),))
            expired_count = cursor.fetchone()["count"]
            
            return MemoryStats(
                total_entries=total_entries,
                entries_by_type=entries_by_type,
                entries_by_priority=entries_by_priority,
                total_size_bytes=total_size,
                oldest_entry=oldest,
                newest_entry=newest,
                expired_entries=expired_count
            )
    
    def export_data(
        self,
        export_path: Path,
        query: Optional[MemoryQuery] = None
    ) -> None:
        """Export memory data to file."""
        with self._lock:
            # Get entries to export
            if query:
                entries = self.query(query)
            else:
                entries = self.query(MemoryQuery(limit=1000000))  # Export all
            
            # Prepare export data
            export_data = {
                "metadata": {
                    "export_time": datetime.now().isoformat(),
                    "total_entries": len(entries),
                    "stats": asdict(self.get_stats())
                },
                "entries": [
                    {
                        "id": entry.id,
                        "memory_type": entry.memory_type.value,
                        "key": entry.key,
                        "data": entry.data,
                        "timestamp": entry.timestamp.isoformat(),
                        "priority": entry.priority.value,
                        "tags": entry.tags,
                        "metadata": entry.metadata,
                        "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                        "access_count": entry.access_count,
                        "last_accessed": entry.last_accessed.isoformat() if entry.last_accessed else None,
                        "size_bytes": entry.size_bytes
                    }
                    for entry in entries
                ]
            }
            
            # Write to file (compressed if large)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            if len(json.dumps(export_data, default=str).encode()) > 1024 * 1024:  # > 1MB
                with gzip.open(export_path.with_suffix(".json.gz"), "wt") as f:
                    json.dump(export_data, f, indent=2, default=str)
            else:
                with open(export_path, "w") as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported {len(entries)} memory entries to {export_path}")
    
    def import_data(self, import_path: Path) -> int:
        """Import memory data from file."""
        with self._lock:
            # Load data
            if import_path.suffix == ".gz":
                with gzip.open(import_path, "rt") as f:
                    import_data = json.load(f)
            else:
                with open(import_path, "r") as f:
                    import_data = json.load(f)
            
            imported_count = 0
            
            # Import entries
            for entry_data in import_data.get("entries", []):
                try:
                    # Create memory entry
                    entry = MemoryEntry(
                        id=entry_data["id"],
                        memory_type=MemoryType(entry_data["memory_type"]),
                        key=entry_data["key"],
                        data=entry_data["data"],
                        timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                        priority=MemoryPriority(entry_data["priority"]),
                        tags=entry_data["tags"],
                        metadata=entry_data["metadata"],
                        expires_at=datetime.fromisoformat(entry_data["expires_at"]) if entry_data["expires_at"] else None,
                        access_count=entry_data.get("access_count", 0),
                        last_accessed=datetime.fromisoformat(entry_data["last_accessed"]) if entry_data.get("last_accessed") else None,
                        size_bytes=entry_data.get("size_bytes", 0)
                    )
                    
                    # Store entry
                    serialized_data = self._serialize_data(entry.data)
                    self._store_entry(entry, serialized_data)
                    
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"Error importing entry {entry_data.get('id', 'unknown')}: {e}")
            
            logger.info(f"Imported {imported_count} memory entries from {import_path}")
            
            return imported_count
    
    def _init_database(self) -> None:
        """Initialize database schema."""
        cursor = self.connection.cursor()
        
        # Memory entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL,
                key TEXT NOT NULL,
                data BLOB NOT NULL,
                timestamp TEXT NOT NULL,
                priority INTEGER NOT NULL,
                tags TEXT NOT NULL,
                metadata TEXT NOT NULL,
                expires_at TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                size_bytes INTEGER DEFAULT 0
            )
        """)
        
        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_entries(memory_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_key ON memory_entries(key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_entries(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON memory_entries(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON memory_entries(expires_at)")
        
        self.connection.commit()
    
    def _generate_id(self, key: str, memory_type: MemoryType) -> str:
        """Generate unique ID for memory entry."""
        content = f"{memory_type.value}:{key}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for storage."""
        serialized = pickle.dumps(data)
        
        # Compress if large
        if len(serialized) > self.compression_threshold:
            serialized = gzip.compress(serialized)
        
        return serialized
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from storage."""
        try:
            # Try to decompress first
            try:
                data = gzip.decompress(data)
            except gzip.BadGzipFile:
                pass  # Not compressed
            
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Error deserializing data: {e}")
            return None
    
    def _store_entry(self, entry: MemoryEntry, serialized_data: bytes) -> None:
        """Store entry in database."""
        cursor = self.connection.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO memory_entries
            (id, memory_type, key, data, timestamp, priority, tags, metadata,
             expires_at, access_count, last_accessed, size_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.memory_type.value,
            entry.key,
            serialized_data,
            entry.timestamp.isoformat(),
            entry.priority.value,
            json.dumps(entry.tags),
            json.dumps(entry.metadata),
            entry.expires_at.isoformat() if entry.expires_at else None,
            entry.access_count,
            entry.last_accessed.isoformat() if entry.last_accessed else None,
            entry.size_bytes
        ))
        
        self.connection.commit()
    
    def _load_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Load entry from database."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM memory_entries WHERE id = ?", (entry_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        # Deserialize data
        data = self._deserialize_data(row["data"])
        if data is None:
            return None
        
        return MemoryEntry(
            id=row["id"],
            memory_type=MemoryType(row["memory_type"]),
            key=row["key"],
            data=data,
            timestamp=datetime.fromisoformat(row["timestamp"]),
            priority=MemoryPriority(row["priority"]),
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            access_count=row["access_count"],
            last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else None,
            size_bytes=row["size_bytes"]
        )
    
    def _query_entries(self, query: MemoryQuery) -> List[MemoryEntry]:
        """Execute query against database."""
        cursor = self.connection.cursor()
        
        # Build SQL query
        sql_parts = ["SELECT * FROM memory_entries WHERE 1=1"]
        params = []
        
        # Filter by type
        if query.memory_type:
            sql_parts.append("AND memory_type = ?")
            params.append(query.memory_type.value)
        
        # Filter by key pattern
        if query.key_pattern:
            sql_parts.append("AND key GLOB ?")
            params.append(query.key_pattern)
        
        # Filter by priority
        if query.priority_min:
            sql_parts.append("AND priority >= ?")
            params.append(query.priority_min.value)
        
        # Filter by date range
        if query.since:
            sql_parts.append("AND timestamp >= ?")
            params.append(query.since.isoformat())
        
        if query.until:
            sql_parts.append("AND timestamp <= ?")
            params.append(query.until.isoformat())
        
        # Filter expired
        if not query.include_expired:
            now = datetime.now()
            sql_parts.append("AND (expires_at IS NULL OR expires_at > ?)")
            params.append(now.isoformat())
        
        # Order and limit
        sql_parts.append("ORDER BY timestamp DESC LIMIT ?")
        params.append(query.limit)
        
        # Execute query
        sql = " ".join(sql_parts)
        cursor.execute(sql, params)
        
        # Convert rows to entries
        entries = []
        for row in cursor.fetchall():
            data = self._deserialize_data(row["data"])
            if data is not None:
                entry = MemoryEntry(
                    id=row["id"],
                    memory_type=MemoryType(row["memory_type"]),
                    key=row["key"],
                    data=data,
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    priority=MemoryPriority(row["priority"]),
                    tags=json.loads(row["tags"]),
                    metadata=json.loads(row["metadata"]),
                    expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                    access_count=row["access_count"],
                    last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else None,
                    size_bytes=row["size_bytes"]
                )
                
                # Filter by tags if specified
                if query.tags:
                    if not any(tag in entry.tags for tag in query.tags):
                        continue
                
                entries.append(entry)
        
        return entries
    
    def _update_access_stats(self, entry: MemoryEntry) -> None:
        """Update access statistics for an entry."""
        entry.access_count += 1
        entry.last_accessed = datetime.now()
        
        # Update in database
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE memory_entries 
            SET access_count = ?, last_accessed = ?
            WHERE id = ?
        """, (entry.access_count, entry.last_accessed.isoformat(), entry.id))
        
        self.connection.commit()
    
    def _manage_cache_size(self) -> None:
        """Manage cache size by evicting old entries."""
        if len(self._cache) > self._cache_max_size:
            # Remove least recently accessed entries
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].last_accessed or datetime.min
            )
            
            # Remove oldest 20%
            remove_count = len(self._cache) - int(self._cache_max_size * 0.8)
            for i in range(remove_count):
                entry_id, _ = sorted_entries[i]
                del self._cache[entry_id]
    
    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')