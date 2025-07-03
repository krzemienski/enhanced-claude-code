"""Memory and context management models."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from pathlib import Path
import json
import pickle
from enum import Enum

from .base import SerializableModel, TimestampedModel, IdentifiedModel
from ..exceptions import MemoryError
from ..utils.constants import MAX_MEMORY_ENTRIES


class MemoryType(Enum):
    """Types of memory entries."""
    
    CONTEXT = "context"
    ERROR = "error"
    RESULT = "result"
    CHECKPOINT = "checkpoint"
    DECISION = "decision"
    LEARNING = "learning"
    METRIC = "metric"


@dataclass
class ContextEntry(SerializableModel, TimestampedModel, IdentifiedModel):
    """Context information stored in memory."""
    
    entry_type: MemoryType
    phase: Optional[str] = None
    task: Optional[str] = None
    key: str = ""
    value: Any = None
    
    # Metadata
    tags: Set[str] = field(default_factory=set)
    references: List[str] = field(default_factory=list)
    importance: float = 1.0
    
    # Expiration
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def validate(self) -> None:
        """Validate context entry."""
        if not self.key:
            raise MemoryError("Context entry must have a key")
        
        if not 0 <= self.importance <= 10:
            raise MemoryError("Importance must be between 0 and 10")
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def access(self) -> Any:
        """Access the entry value and update metadata."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        return self.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data["entry_type"] = self.entry_type.value
        data["tags"] = list(self.tags)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEntry":
        """Create from dictionary."""
        if "entry_type" in data and isinstance(data["entry_type"], str):
            data["entry_type"] = MemoryType(data["entry_type"])
        if "tags" in data and isinstance(data["tags"], list):
            data["tags"] = set(data["tags"])
        return super().from_dict(data)


@dataclass
class ErrorLog(SerializableModel, TimestampedModel, IdentifiedModel):
    """Error information with context."""
    
    error_type: str
    error_message: str
    phase: Optional[str] = None
    task: Optional[str] = None
    
    # Error details
    traceback: Optional[str] = None
    error_code: Optional[str] = None
    severity: str = "error"
    
    # Context at time of error
    context: Dict[str, Any] = field(default_factory=dict)
    system_state: Dict[str, Any] = field(default_factory=dict)
    
    # Recovery information
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_actions: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Validate error log."""
        valid_severities = ["debug", "info", "warning", "error", "critical"]
        if self.severity not in valid_severities:
            raise MemoryError(f"Invalid severity: {self.severity}")
    
    def add_recovery_action(self, action: str) -> None:
        """Add recovery action taken."""
        self.recovery_actions.append(action)
        self.recovery_attempted = True


@dataclass
class MemoryQuery:
    """Query for searching memory."""
    
    entry_types: Optional[List[MemoryType]] = None
    phases: Optional[List[str]] = None
    tasks: Optional[List[str]] = None
    tags: Optional[Set[str]] = None
    key_pattern: Optional[str] = None
    
    # Time filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    accessed_after: Optional[datetime] = None
    
    # Other filters
    min_importance: Optional[float] = None
    max_results: int = 100
    order_by: str = "created_at"
    descending: bool = True
    
    def matches(self, entry: ContextEntry) -> bool:
        """Check if entry matches query criteria."""
        # Type filter
        if self.entry_types and entry.entry_type not in self.entry_types:
            return False
        
        # Phase filter
        if self.phases and entry.phase not in self.phases:
            return False
        
        # Task filter
        if self.tasks and entry.task not in self.tasks:
            return False
        
        # Tag filter
        if self.tags and not entry.tags.intersection(self.tags):
            return False
        
        # Key pattern filter
        if self.key_pattern and self.key_pattern not in entry.key:
            return False
        
        # Time filters
        if self.created_after and entry.created_at < self.created_after:
            return False
        if self.created_before and entry.created_at > self.created_before:
            return False
        if self.accessed_after and (not entry.last_accessed or entry.last_accessed < self.accessed_after):
            return False
        
        # Importance filter
        if self.min_importance and entry.importance < self.min_importance:
            return False
        
        return True


@dataclass
class MemoryStore(SerializableModel):
    """Persistent memory storage."""
    
    entries: List[ContextEntry] = field(default_factory=list)
    errors: List[ErrorLog] = field(default_factory=list)
    
    # Indices for fast lookup
    _entry_index: Dict[str, ContextEntry] = field(default_factory=dict)
    _key_index: Dict[str, List[ContextEntry]] = field(default_factory=dict)
    _phase_index: Dict[str, List[ContextEntry]] = field(default_factory=dict)
    _task_index: Dict[str, List[ContextEntry]] = field(default_factory=dict)
    _tag_index: Dict[str, List[ContextEntry]] = field(default_factory=dict)
    
    # Configuration
    max_entries: int = MAX_MEMORY_ENTRIES
    auto_cleanup: bool = True
    cleanup_threshold: float = 0.9
    
    def __post_init__(self):
        """Initialize memory store."""
        self._rebuild_indices()
    
    def _rebuild_indices(self):
        """Rebuild all indices."""
        self._entry_index.clear()
        self._key_index.clear()
        self._phase_index.clear()
        self._task_index.clear()
        self._tag_index.clear()
        
        for entry in self.entries:
            self._index_entry(entry)
    
    def _index_entry(self, entry: ContextEntry):
        """Add entry to indices."""
        # ID index
        self._entry_index[entry.id] = entry
        
        # Key index
        if entry.key not in self._key_index:
            self._key_index[entry.key] = []
        self._key_index[entry.key].append(entry)
        
        # Phase index
        if entry.phase:
            if entry.phase not in self._phase_index:
                self._phase_index[entry.phase] = []
            self._phase_index[entry.phase].append(entry)
        
        # Task index
        if entry.task:
            if entry.task not in self._task_index:
                self._task_index[entry.task] = []
            self._task_index[entry.task].append(entry)
        
        # Tag index
        for tag in entry.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(entry)
    
    def _unindex_entry(self, entry: ContextEntry):
        """Remove entry from indices."""
        # ID index
        self._entry_index.pop(entry.id, None)
        
        # Key index
        if entry.key in self._key_index:
            self._key_index[entry.key].remove(entry)
            if not self._key_index[entry.key]:
                del self._key_index[entry.key]
        
        # Phase index
        if entry.phase and entry.phase in self._phase_index:
            self._phase_index[entry.phase].remove(entry)
            if not self._phase_index[entry.phase]:
                del self._phase_index[entry.phase]
        
        # Task index
        if entry.task and entry.task in self._task_index:
            self._task_index[entry.task].remove(entry)
            if not self._task_index[entry.task]:
                del self._task_index[entry.task]
        
        # Tag index
        for tag in entry.tags:
            if tag in self._tag_index:
                self._tag_index[tag].remove(entry)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]
    
    def add(
        self,
        key: str,
        value: Any,
        entry_type: MemoryType = MemoryType.CONTEXT,
        **kwargs
    ) -> ContextEntry:
        """Add entry to memory."""
        # Check capacity
        if len(self.entries) >= self.max_entries:
            if self.auto_cleanup:
                self._cleanup()
            else:
                raise MemoryError(f"Memory store full ({self.max_entries} entries)")
        
        # Create entry
        entry = ContextEntry(
            key=key,
            value=value,
            entry_type=entry_type,
            **kwargs
        )
        
        entry.validate()
        
        # Add to store
        self.entries.append(entry)
        self._index_entry(entry)
        
        return entry
    
    def get(self, entry_id: str) -> Optional[ContextEntry]:
        """Get entry by ID."""
        entry = self._entry_index.get(entry_id)
        if entry and not entry.is_expired():
            return entry
        return None
    
    def get_by_key(self, key: str, phase: Optional[str] = None) -> Optional[ContextEntry]:
        """Get most recent entry by key."""
        entries = self._key_index.get(key, [])
        
        # Filter by phase if specified
        if phase:
            entries = [e for e in entries if e.phase == phase]
        
        # Return most recent non-expired entry
        for entry in reversed(entries):
            if not entry.is_expired():
                return entry
        
        return None
    
    def query(self, query: MemoryQuery) -> List[ContextEntry]:
        """Query memory with filters."""
        # Start with all entries or filtered set
        candidates = self.entries
        
        # Use indices for initial filtering if possible
        if query.phases and len(query.phases) == 1:
            candidates = self._phase_index.get(query.phases[0], [])
        elif query.tasks and len(query.tasks) == 1:
            candidates = self._task_index.get(query.tasks[0], [])
        elif query.tags and len(query.tags) == 1:
            candidates = self._tag_index.get(list(query.tags)[0], [])
        
        # Apply query filters
        results = [
            entry for entry in candidates
            if query.matches(entry) and not entry.is_expired()
        ]
        
        # Sort results
        if query.order_by == "created_at":
            results.sort(key=lambda e: e.created_at, reverse=query.descending)
        elif query.order_by == "importance":
            results.sort(key=lambda e: e.importance, reverse=query.descending)
        elif query.order_by == "access_count":
            results.sort(key=lambda e: e.access_count, reverse=query.descending)
        
        # Limit results
        return results[:query.max_results]
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        **kwargs
    ) -> ErrorLog:
        """Log an error with context."""
        error_log = ErrorLog(
            error_type=error_type,
            error_message=error_message,
            **kwargs
        )
        
        error_log.validate()
        self.errors.append(error_log)
        
        return error_log
    
    def get_phase_context(self, phase: str) -> Dict[str, Any]:
        """Get all context for a phase."""
        entries = self._phase_index.get(phase, [])
        context = {}
        
        for entry in entries:
            if not entry.is_expired():
                context[entry.key] = entry.value
        
        return context
    
    def get_task_context(self, task: str) -> Dict[str, Any]:
        """Get all context for a task."""
        entries = self._task_index.get(task, [])
        context = {}
        
        for entry in entries:
            if not entry.is_expired():
                context[entry.key] = entry.value
        
        return context
    
    def _cleanup(self):
        """Clean up old/expired entries."""
        # Remove expired entries
        expired = [e for e in self.entries if e.is_expired()]
        for entry in expired:
            self.remove(entry.id)
        
        # If still over threshold, remove least important/accessed
        if len(self.entries) > self.max_entries * self.cleanup_threshold:
            # Score entries by importance and access
            scored_entries = [
                (e, e.importance * (1 + e.access_count))
                for e in self.entries
            ]
            scored_entries.sort(key=lambda x: x[1])
            
            # Remove lowest scored entries
            remove_count = len(self.entries) - int(self.max_entries * 0.7)
            for entry, _ in scored_entries[:remove_count]:
                self.remove(entry.id)
    
    def remove(self, entry_id: str) -> bool:
        """Remove entry from memory."""
        entry = self._entry_index.get(entry_id)
        if entry:
            self.entries.remove(entry)
            self._unindex_entry(entry)
            return True
        return False
    
    def clear(self, entry_type: Optional[MemoryType] = None):
        """Clear memory entries."""
        if entry_type:
            # Clear specific type
            self.entries = [e for e in self.entries if e.entry_type != entry_type]
            self._rebuild_indices()
        else:
            # Clear all
            self.entries.clear()
            self.errors.clear()
            self._entry_index.clear()
            self._key_index.clear()
            self._phase_index.clear()
            self._task_index.clear()
            self._tag_index.clear()
    
    def save_to_file(self, path: Path, format: str = "json"):
        """Save memory to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            with open(path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2, default=str)
        elif format == "pickle":
            with open(path, 'wb') as f:
                pickle.dump(self, f)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @classmethod
    def load_from_file(cls, path: Path, format: str = "json") -> "MemoryStore":
        """Load memory from file."""
        if format == "json":
            with open(path, 'r') as f:
                data = json.load(f)
            return cls.from_dict(data)
        elif format == "pickle":
            with open(path, 'rb') as f:
                return pickle.load(f)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "total_entries": len(self.entries),
            "total_errors": len(self.errors),
            "entries_by_type": {
                entry_type.value: sum(1 for e in self.entries if e.entry_type == entry_type)
                for entry_type in MemoryType
            },
            "unique_keys": len(self._key_index),
            "phases_tracked": len(self._phase_index),
            "tasks_tracked": len(self._task_index),
            "unique_tags": len(self._tag_index),
            "memory_usage": len(self.entries) / self.max_entries * 100,
            "expired_entries": sum(1 for e in self.entries if e.is_expired()),
            "average_importance": sum(e.importance for e in self.entries) / len(self.entries) if self.entries else 0,
            "total_access_count": sum(e.access_count for e in self.entries)
        }
    
    def validate(self) -> None:
        """Validate memory store."""
        # Validate all entries
        for entry in self.entries:
            entry.validate()
        
        # Validate all errors
        for error in self.errors:
            error.validate()
        
        # Validate configuration
        if self.max_entries < 1:
            raise MemoryError("Max entries must be at least 1")
        
        if not 0 <= self.cleanup_threshold <= 1:
            raise MemoryError("Cleanup threshold must be between 0 and 1")