"""Base model classes for Claude Code Builder."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, Optional, TypeVar, Generic, List
from uuid import uuid4
import json
from pathlib import Path

T = TypeVar('T')


class BaseModel(ABC):
    """Abstract base class for all models."""
    
    @abstractmethod
    def validate(self) -> None:
        """Validate the model data."""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        """Create model from dictionary."""
        pass
    
    def to_json(self, indent: int = 2) -> str:
        """Convert model to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> "BaseModel":
        """Create model from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def save(self, path: Path) -> None:
        """Save model to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(self.to_json())
    
    @classmethod
    def load(cls, path: Path) -> "BaseModel":
        """Load model from file."""
        with open(path, 'r') as f:
            return cls.from_json(f.read())


@dataclass
class TimestampedModel:
    """Mixin for models with timestamps."""
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


@dataclass
class IdentifiedModel:
    """Mixin for models with unique identifiers."""
    
    id: str = field(default_factory=lambda: str(uuid4()))
    
    def __hash__(self) -> int:
        """Make model hashable by ID."""
        return hash(self.id)
    
    def __eq__(self, other: Any) -> bool:
        """Compare models by ID."""
        if not isinstance(other, IdentifiedModel):
            return False
        return self.id == other.id


@dataclass
class VersionedModel:
    """Mixin for models with version tracking."""
    
    version: int = 1
    
    def increment_version(self) -> None:
        """Increment the version number."""
        self.version += 1


@dataclass
class SerializableModel(BaseModel):
    """Base class for serializable dataclass models."""
    
    def validate(self) -> None:
        """Default validation (can be overridden)."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SerializableModel":
        """Create dataclass from dictionary."""
        # Handle datetime fields
        for field_name, field_type in cls.__annotations__.items():
            if field_type == datetime and field_name in data:
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])
        return cls(**data)


class Repository(Generic[T], ABC):
    """Abstract base class for repositories."""
    
    @abstractmethod
    def get(self, id: str) -> Optional[T]:
        """Get item by ID."""
        pass
    
    @abstractmethod
    def list(self, **filters) -> List[T]:
        """List items with optional filters."""
        pass
    
    @abstractmethod
    def create(self, item: T) -> T:
        """Create new item."""
        pass
    
    @abstractmethod
    def update(self, item: T) -> T:
        """Update existing item."""
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete item by ID."""
        pass
    
    @abstractmethod
    def exists(self, id: str) -> bool:
        """Check if item exists."""
        pass


class InMemoryRepository(Repository[T]):
    """In-memory implementation of repository."""
    
    def __init__(self):
        """Initialize repository."""
        self._items: Dict[str, T] = {}
    
    def get(self, id: str) -> Optional[T]:
        """Get item by ID."""
        return self._items.get(id)
    
    def list(self, **filters) -> List[T]:
        """List items with optional filters."""
        items = list(self._items.values())
        
        # Apply filters
        for key, value in filters.items():
            items = [
                item for item in items
                if hasattr(item, key) and getattr(item, key) == value
            ]
        
        return items
    
    def create(self, item: T) -> T:
        """Create new item."""
        if hasattr(item, 'id'):
            self._items[item.id] = item
        else:
            raise ValueError("Item must have an 'id' attribute")
        return item
    
    def update(self, item: T) -> T:
        """Update existing item."""
        if hasattr(item, 'id'):
            if item.id not in self._items:
                raise KeyError(f"Item with id {item.id} not found")
            self._items[item.id] = item
        else:
            raise ValueError("Item must have an 'id' attribute")
        return item
    
    def delete(self, id: str) -> bool:
        """Delete item by ID."""
        if id in self._items:
            del self._items[id]
            return True
        return False
    
    def exists(self, id: str) -> bool:
        """Check if item exists."""
        return id in self._items
    
    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()
    
    def count(self) -> int:
        """Count total items."""
        return len(self._items)


@dataclass
class Result(Generic[T]):
    """Generic result wrapper for operations."""
    
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def ok(cls, data: T, **details) -> "Result[T]":
        """Create successful result."""
        return cls(success=True, data=data, details=details)
    
    @classmethod
    def fail(cls, error: str, **details) -> "Result[T]":
        """Create failed result."""
        return cls(success=False, error=error, details=details)
    
    def unwrap(self) -> T:
        """Unwrap the data or raise exception."""
        if self.success and self.data is not None:
            return self.data
        raise ValueError(self.error or "No data available")
    
    def unwrap_or(self, default: T) -> T:
        """Unwrap the data or return default."""
        if self.success and self.data is not None:
            return self.data
        return default


@dataclass
class Event:
    """Base class for events."""
    
    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data
        }


class EventBus:
    """Simple event bus for decoupled communication."""
    
    def __init__(self):
        """Initialize event bus."""
        self._handlers: Dict[str, List[callable]] = {}
    
    def subscribe(self, event_type: str, handler: callable) -> None:
        """Subscribe to event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler: callable) -> None:
        """Unsubscribe from event type."""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
    
    def publish(self, event: Event) -> None:
        """Publish event to subscribers."""
        if event.event_type in self._handlers:
            for handler in self._handlers[event.event_type]:
                try:
                    handler(event)
                except Exception:
                    # Log error but don't stop other handlers
                    pass
    
    def clear(self) -> None:
        """Clear all subscriptions."""
        self._handlers.clear()