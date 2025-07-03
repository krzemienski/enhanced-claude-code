"""Context management for Claude Code SDK sessions."""

import json
import logging
from typing import Dict, Any, List, Optional, Set, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
import hashlib

from ..models.base import BaseModel
from ..models.memory import MemoryEntry, MemoryStore
from ..exceptions.base import SDKError

logger = logging.getLogger(__name__)


@dataclass
class ContextEntry:
    """Represents a context entry."""
    key: str
    value: Any
    category: str
    timestamp: datetime
    priority: int = 0
    persistent: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority,
            "persistent": self.persistent,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEntry":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            category=data["category"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=data.get("priority", 0),
            persistent=data.get("persistent", False),
            metadata=data.get("metadata", {})
        )


class ContextManager:
    """Manages context for Claude Code sessions."""
    
    # Context categories
    CATEGORIES = {
        "project": "Project-specific information",
        "files": "File-related context",
        "commands": "Command history and results",
        "errors": "Error context and recovery",
        "memory": "Long-term memory entries",
        "custom": "Custom user context"
    }
    
    def __init__(self, max_entries: int = 1000, max_size: int = 10_000_000):
        """
        Initialize context manager.
        
        Args:
            max_entries: Maximum number of context entries
            max_size: Maximum total size in bytes
        """
        self.max_entries = max_entries
        self.max_size = max_size
        self.contexts: Dict[str, Dict[str, ContextEntry]] = {}
        self.entry_sizes: Dict[str, int] = {}
        self.total_size = 0
    
    def create_session_context(self, session_id: str) -> None:
        """
        Create context for a new session.
        
        Args:
            session_id: Session ID
        """
        if session_id not in self.contexts:
            self.contexts[session_id] = {}
            logger.info(f"Created context for session {session_id}")
    
    def add_context(
        self,
        session_id: str,
        key: str,
        value: Any,
        category: str = "custom",
        priority: int = 0,
        persistent: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add context entry for a session.
        
        Args:
            session_id: Session ID
            key: Context key
            value: Context value
            category: Context category
            priority: Priority (higher = more important)
            persistent: Whether to persist across sessions
            metadata: Additional metadata
        """
        if session_id not in self.contexts:
            self.create_session_context(session_id)
        
        # Create entry
        entry = ContextEntry(
            key=key,
            value=value,
            category=category,
            timestamp=datetime.now(),
            priority=priority,
            persistent=persistent,
            metadata=metadata or {}
        )
        
        # Calculate size
        entry_size = len(json.dumps(entry.to_dict()))
        
        # Check size limits
        if self.total_size + entry_size > self.max_size:
            self._evict_entries(session_id, entry_size)
        
        # Store entry
        full_key = f"{session_id}:{key}"
        self.contexts[session_id][key] = entry
        self.entry_sizes[full_key] = entry_size
        self.total_size += entry_size
        
        logger.debug(f"Added context {key} for session {session_id}")
    
    def get_context(
        self,
        session_id: str,
        key: Optional[str] = None,
        category: Optional[str] = None
    ) -> Union[Any, Dict[str, Any]]:
        """
        Get context for a session.
        
        Args:
            session_id: Session ID
            key: Specific key to retrieve
            category: Filter by category
            
        Returns:
            Context value(s)
        """
        if session_id not in self.contexts:
            return {} if key is None else None
        
        session_context = self.contexts[session_id]
        
        # Get specific key
        if key:
            entry = session_context.get(key)
            return entry.value if entry else None
        
        # Filter by category
        if category:
            filtered = {
                k: e.value
                for k, e in session_context.items()
                if e.category == category
            }
            return filtered
        
        # Return all context
        return {k: e.value for k, e in session_context.items()}
    
    def update_context(
        self,
        session_id: str,
        key: str,
        value: Any,
        merge: bool = False
    ) -> None:
        """
        Update existing context.
        
        Args:
            session_id: Session ID
            key: Context key
            value: New value
            merge: Whether to merge with existing value
        """
        if session_id not in self.contexts or key not in self.contexts[session_id]:
            # Add as new context
            self.add_context(session_id, key, value)
            return
        
        entry = self.contexts[session_id][key]
        
        # Merge if requested and value is dict
        if merge and isinstance(entry.value, dict) and isinstance(value, dict):
            entry.value.update(value)
        else:
            entry.value = value
        
        entry.timestamp = datetime.now()
        
        # Update size
        full_key = f"{session_id}:{key}"
        old_size = self.entry_sizes.get(full_key, 0)
        new_size = len(json.dumps(entry.to_dict()))
        
        self.total_size = self.total_size - old_size + new_size
        self.entry_sizes[full_key] = new_size
        
        logger.debug(f"Updated context {key} for session {session_id}")
    
    def remove_context(
        self,
        session_id: str,
        key: Optional[str] = None,
        category: Optional[str] = None
    ) -> None:
        """
        Remove context entries.
        
        Args:
            session_id: Session ID
            key: Specific key to remove
            category: Remove all entries in category
        """
        if session_id not in self.contexts:
            return
        
        session_context = self.contexts[session_id]
        
        if key:
            # Remove specific key
            if key in session_context:
                full_key = f"{session_id}:{key}"
                size = self.entry_sizes.get(full_key, 0)
                del session_context[key]
                del self.entry_sizes[full_key]
                self.total_size -= size
                logger.debug(f"Removed context {key} for session {session_id}")
        
        elif category:
            # Remove by category
            keys_to_remove = [
                k for k, e in session_context.items()
                if e.category == category
            ]
            for k in keys_to_remove:
                full_key = f"{session_id}:{k}"
                size = self.entry_sizes.get(full_key, 0)
                del session_context[k]
                del self.entry_sizes[full_key]
                self.total_size -= size
            
            logger.debug(f"Removed {len(keys_to_remove)} entries from category {category}")
    
    def merge_contexts(
        self,
        source_session: str,
        target_session: str,
        overwrite: bool = False
    ) -> None:
        """
        Merge context from one session to another.
        
        Args:
            source_session: Source session ID
            target_session: Target session ID
            overwrite: Whether to overwrite existing keys
        """
        if source_session not in self.contexts:
            return
        
        if target_session not in self.contexts:
            self.create_session_context(target_session)
        
        source_context = self.contexts[source_session]
        target_context = self.contexts[target_session]
        
        for key, entry in source_context.items():
            if key not in target_context or overwrite:
                # Clone entry
                new_entry = ContextEntry(
                    key=entry.key,
                    value=entry.value,
                    category=entry.category,
                    timestamp=entry.timestamp,
                    priority=entry.priority,
                    persistent=entry.persistent,
                    metadata=entry.metadata.copy()
                )
                
                target_context[key] = new_entry
                
                # Update sizes
                full_key = f"{target_session}:{key}"
                size = len(json.dumps(new_entry.to_dict()))
                self.entry_sizes[full_key] = size
                self.total_size += size
        
        logger.info(f"Merged context from {source_session} to {target_session}")
    
    def get_persistent_context(self) -> Dict[str, Any]:
        """Get all persistent context entries."""
        persistent = {}
        
        for session_id, session_context in self.contexts.items():
            for key, entry in session_context.items():
                if entry.persistent:
                    persistent[f"{session_id}:{key}"] = {
                        "value": entry.value,
                        "category": entry.category,
                        "metadata": entry.metadata
                    }
        
        return persistent
    
    def restore_persistent_context(
        self,
        session_id: str,
        persistent_context: Dict[str, Any]
    ) -> None:
        """
        Restore persistent context for a session.
        
        Args:
            session_id: Session ID
            persistent_context: Persistent context to restore
        """
        if session_id not in self.contexts:
            self.create_session_context(session_id)
        
        for full_key, data in persistent_context.items():
            # Extract original session and key
            parts = full_key.split(":", 1)
            if len(parts) == 2:
                _, key = parts
                self.add_context(
                    session_id=session_id,
                    key=key,
                    value=data["value"],
                    category=data["category"],
                    persistent=True,
                    metadata=data.get("metadata", {})
                )
    
    def _evict_entries(self, session_id: str, needed_size: int) -> None:
        """
        Evict entries to make room.
        
        Args:
            session_id: Session ID
            needed_size: Size needed
        """
        # Get all non-persistent entries sorted by priority and age
        candidates = []
        
        for sid, session_context in self.contexts.items():
            for key, entry in session_context.items():
                if not entry.persistent:
                    candidates.append((
                        sid,
                        key,
                        entry.priority,
                        entry.timestamp,
                        self.entry_sizes.get(f"{sid}:{key}", 0)
                    ))
        
        # Sort by priority (ascending) and timestamp (ascending)
        candidates.sort(key=lambda x: (x[2], x[3]))
        
        # Evict until enough space
        freed_size = 0
        for sid, key, _, _, size in candidates:
            if freed_size >= needed_size:
                break
            
            self.remove_context(sid, key)
            freed_size += size
    
    def create_context_snapshot(self, session_id: str) -> Dict[str, Any]:
        """
        Create a snapshot of session context.
        
        Args:
            session_id: Session ID
            
        Returns:
            Context snapshot
        """
        if session_id not in self.contexts:
            return {}
        
        snapshot = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "entries": {}
        }
        
        for key, entry in self.contexts[session_id].items():
            snapshot["entries"][key] = entry.to_dict()
        
        return snapshot
    
    def restore_context_snapshot(
        self,
        session_id: str,
        snapshot: Dict[str, Any]
    ) -> None:
        """
        Restore context from snapshot.
        
        Args:
            session_id: Session ID
            snapshot: Context snapshot
        """
        if session_id not in self.contexts:
            self.create_session_context(session_id)
        
        # Clear existing context
        self.contexts[session_id].clear()
        
        # Restore entries
        for key, entry_data in snapshot.get("entries", {}).items():
            entry = ContextEntry.from_dict(entry_data)
            self.contexts[session_id][key] = entry
            
            # Update sizes
            full_key = f"{session_id}:{key}"
            size = len(json.dumps(entry_data))
            self.entry_sizes[full_key] = size
            self.total_size += size
    
    def get_context_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get context statistics."""
        if session_id:
            if session_id not in self.contexts:
                return {"error": "Session not found"}
            
            session_context = self.contexts[session_id]
            session_size = sum(
                self.entry_sizes.get(f"{session_id}:{k}", 0)
                for k in session_context.keys()
            )
            
            return {
                "session_id": session_id,
                "entry_count": len(session_context),
                "total_size": session_size,
                "categories": {
                    cat: len([e for e in session_context.values() if e.category == cat])
                    for cat in self.CATEGORIES.keys()
                },
                "persistent_count": len([
                    e for e in session_context.values() if e.persistent
                ])
            }
        
        # Global stats
        return {
            "total_sessions": len(self.contexts),
            "total_entries": sum(len(ctx) for ctx in self.contexts.values()),
            "total_size": self.total_size,
            "max_entries": self.max_entries,
            "max_size": self.max_size,
            "utilization": self.total_size / self.max_size if self.max_size > 0 else 0
        }
    
    def clear_session_context(self, session_id: str) -> None:
        """Clear all context for a session."""
        if session_id in self.contexts:
            # Update sizes
            for key in self.contexts[session_id].keys():
                full_key = f"{session_id}:{key}"
                if full_key in self.entry_sizes:
                    self.total_size -= self.entry_sizes[full_key]
                    del self.entry_sizes[full_key]
            
            # Clear context
            self.contexts[session_id].clear()
            logger.info(f"Cleared context for session {session_id}")
    
    def generate_context_summary(self, session_id: str) -> str:
        """
        Generate a summary of session context.
        
        Args:
            session_id: Session ID
            
        Returns:
            Context summary
        """
        if session_id not in self.contexts:
            return f"No context found for session {session_id}"
        
        session_context = self.contexts[session_id]
        
        summary = f"=== Context Summary for Session {session_id} ===\n\n"
        
        # Group by category
        by_category = {}
        for entry in session_context.values():
            if entry.category not in by_category:
                by_category[entry.category] = []
            by_category[entry.category].append(entry)
        
        # Summarize each category
        for category, entries in by_category.items():
            summary += f"{category.title()}:\n"
            
            # Sort by priority and timestamp
            entries.sort(key=lambda e: (-e.priority, -e.timestamp.timestamp()))
            
            for entry in entries[:5]:  # Top 5 per category
                value_str = str(entry.value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                
                summary += f"  - {entry.key}: {value_str}"
                if entry.persistent:
                    summary += " [P]"
                summary += "\n"
            
            if len(entries) > 5:
                summary += f"  ... and {len(entries) - 5} more\n"
            
            summary += "\n"
        
        return summary