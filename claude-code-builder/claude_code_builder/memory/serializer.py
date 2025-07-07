"""State serialization and deserialization for context persistence."""

import logging
import json
import pickle
import gzip
import base64
from typing import Dict, Any, List, Optional, Union, Type, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict, is_dataclass
from pathlib import Path
from enum import Enum
import hashlib
import threading

logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    COMPRESSED_JSON = "compressed_json"
    COMPRESSED_PICKLE = "compressed_pickle"
    BINARY = "binary"


class CompressionLevel(Enum):
    """Compression levels for serialized data."""
    NONE = 0
    FAST = 1
    BALANCED = 6
    MAXIMUM = 9


@dataclass
class SerializationConfig:
    """Configuration for serialization behavior."""
    format: SerializationFormat = SerializationFormat.COMPRESSED_JSON
    compression_level: CompressionLevel = CompressionLevel.BALANCED
    include_metadata: bool = True
    encrypt: bool = False
    encryption_key: Optional[str] = None
    max_size_mb: int = 100
    chunk_size_kb: int = 1024
    preserve_types: bool = True


@dataclass
class SerializedState:
    """Container for serialized state with metadata."""
    data: Union[str, bytes]
    format: SerializationFormat
    metadata: Dict[str, Any]
    checksum: str
    size_bytes: int
    created_at: datetime
    version: str = "1.0"


@dataclass
class StateSnapshot:
    """Complete state snapshot with versioning."""
    id: str
    timestamp: datetime
    component: str
    state_data: Any
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateSerializer:
    """Advanced state serialization with multiple format support."""
    
    def __init__(self, config: Optional[SerializationConfig] = None):
        """Initialize the state serializer."""
        self.config = config or SerializationConfig()
        self.lock = threading.RLock()
        
        # Type registry for custom serialization
        self._type_registry: Dict[str, Callable] = {}
        self._deserializer_registry: Dict[str, Callable] = {}
        
        # Statistics
        self.stats = {
            "serializations": 0,
            "deserializations": 0,
            "compression_ratio": 0.0,
            "avg_serialize_time_ms": 0.0,
            "avg_deserialize_time_ms": 0.0,
            "errors": 0
        }
        
        # Register default type handlers
        self._register_default_handlers()
        
        logger.info("State Serializer initialized")
    
    def serialize_state(
        self,
        state: Any,
        config: Optional[SerializationConfig] = None
    ) -> SerializedState:
        """Serialize state object to specified format."""
        start_time = datetime.now()
        effective_config = config or self.config
        
        try:
            with self.lock:
                # Preprocess state
                processed_state = self._preprocess_state(state, effective_config)
                
                # Serialize based on format
                if effective_config.format == SerializationFormat.JSON:
                    serialized_data = self._serialize_json(processed_state, effective_config)
                elif effective_config.format == SerializationFormat.PICKLE:
                    serialized_data = self._serialize_pickle(processed_state, effective_config)
                elif effective_config.format == SerializationFormat.COMPRESSED_JSON:
                    serialized_data = self._serialize_compressed_json(processed_state, effective_config)
                elif effective_config.format == SerializationFormat.COMPRESSED_PICKLE:
                    serialized_data = self._serialize_compressed_pickle(processed_state, effective_config)
                elif effective_config.format == SerializationFormat.BINARY:
                    serialized_data = self._serialize_binary(processed_state, effective_config)
                else:
                    raise ValueError(f"Unsupported serialization format: {effective_config.format}")
                
                # Calculate checksum
                checksum = self._calculate_checksum(serialized_data)
                
                # Create metadata
                metadata = self._create_metadata(state, effective_config, start_time)
                
                # Create serialized state
                serialized_state = SerializedState(
                    data=serialized_data,
                    format=effective_config.format,
                    metadata=metadata,
                    checksum=checksum,
                    size_bytes=len(serialized_data) if isinstance(serialized_data, (str, bytes)) else 0,
                    created_at=start_time
                )
                
                # Update statistics
                self._update_serialize_stats(start_time, serialized_state)
                
                logger.debug(f"Serialized state: {serialized_state.size_bytes} bytes, format: {effective_config.format.value}")
                
                return serialized_state
        
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Serialization error: {e}")
            raise
    
    def deserialize_state(
        self,
        serialized_state: SerializedState,
        expected_type: Optional[Type] = None
    ) -> Any:
        """Deserialize state from serialized format."""
        start_time = datetime.now()
        
        try:
            with self.lock:
                # Verify checksum
                if not self._verify_checksum(serialized_state):
                    raise ValueError("Checksum verification failed")
                
                # Deserialize based on format
                if serialized_state.format == SerializationFormat.JSON:
                    state = self._deserialize_json(serialized_state.data)
                elif serialized_state.format == SerializationFormat.PICKLE:
                    state = self._deserialize_pickle(serialized_state.data)
                elif serialized_state.format == SerializationFormat.COMPRESSED_JSON:
                    state = self._deserialize_compressed_json(serialized_state.data)
                elif serialized_state.format == SerializationFormat.COMPRESSED_PICKLE:
                    state = self._deserialize_compressed_pickle(serialized_state.data)
                elif serialized_state.format == SerializationFormat.BINARY:
                    state = self._deserialize_binary(serialized_state.data)
                else:
                    raise ValueError(f"Unsupported deserialization format: {serialized_state.format}")
                
                # Post-process state
                processed_state = self._postprocess_state(state, serialized_state.metadata)
                
                # Type validation
                if expected_type and not isinstance(processed_state, expected_type):
                    logger.warning(f"Type mismatch: expected {expected_type}, got {type(processed_state)}")
                
                # Update statistics
                self._update_deserialize_stats(start_time)
                
                logger.debug(f"Deserialized state: {type(processed_state)}")
                
                return processed_state
        
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Deserialization error: {e}")
            raise
    
    def create_snapshot(
        self,
        component: str,
        state: Any,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StateSnapshot:
        """Create a complete state snapshot."""
        snapshot_id = self._generate_snapshot_id(component, state)
        
        snapshot = StateSnapshot(
            id=snapshot_id,
            timestamp=datetime.now(),
            component=component,
            state_data=state,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        return snapshot
    
    def serialize_snapshot(
        self,
        snapshot: StateSnapshot,
        config: Optional[SerializationConfig] = None
    ) -> SerializedState:
        """Serialize a complete snapshot."""
        # Convert snapshot to dict for serialization
        snapshot_dict = {
            "id": snapshot.id,
            "timestamp": snapshot.timestamp.isoformat(),
            "component": snapshot.component,
            "state_data": snapshot.state_data,
            "dependencies": snapshot.dependencies,
            "tags": snapshot.tags,
            "metadata": snapshot.metadata
        }
        
        return self.serialize_state(snapshot_dict, config)
    
    def deserialize_snapshot(self, serialized_state: SerializedState) -> StateSnapshot:
        """Deserialize a complete snapshot."""
        snapshot_dict = self.deserialize_state(serialized_state)
        
        return StateSnapshot(
            id=snapshot_dict["id"],
            timestamp=datetime.fromisoformat(snapshot_dict["timestamp"]),
            component=snapshot_dict["component"],
            state_data=snapshot_dict["state_data"],
            dependencies=snapshot_dict.get("dependencies", []),
            tags=snapshot_dict.get("tags", []),
            metadata=snapshot_dict.get("metadata", {})
        )
    
    def save_to_file(
        self,
        serialized_state: SerializedState,
        file_path: Path,
        create_backup: bool = True
    ) -> None:
        """Save serialized state to file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if requested
        if create_backup and file_path.exists():
            backup_path = file_path.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            file_path.rename(backup_path)
        
        # Save state with metadata
        file_data = {
            "serialized_state": {
                "data": base64.b64encode(serialized_state.data).decode() if isinstance(serialized_state.data, bytes) else serialized_state.data,
                "format": serialized_state.format.value,
                "metadata": serialized_state.metadata,
                "checksum": serialized_state.checksum,
                "size_bytes": serialized_state.size_bytes,
                "created_at": serialized_state.created_at.isoformat(),
                "version": serialized_state.version
            },
            "file_metadata": {
                "saved_at": datetime.now().isoformat(),
                "serializer_version": "1.0",
                "python_version": ".".join(str(v) for v in __import__("sys").version_info[:3])
            }
        }
        
        with open(file_path, 'w') as f:
            json.dump(file_data, f, indent=2)
        
        logger.info(f"Serialized state saved to {file_path}")
    
    def load_from_file(self, file_path: Path) -> SerializedState:
        """Load serialized state from file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Serialized state file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            file_data = json.load(f)
        
        state_data = file_data["serialized_state"]
        
        # Decode base64 data if necessary
        data = state_data["data"]
        if state_data["format"] in ["compressed_json", "compressed_pickle", "binary"]:
            data = base64.b64decode(data.encode())
        
        serialized_state = SerializedState(
            data=data,
            format=SerializationFormat(state_data["format"]),
            metadata=state_data["metadata"],
            checksum=state_data["checksum"],
            size_bytes=state_data["size_bytes"],
            created_at=datetime.fromisoformat(state_data["created_at"]),
            version=state_data.get("version", "1.0")
        )
        
        logger.info(f"Serialized state loaded from {file_path}")
        
        return serialized_state
    
    def register_type_handler(
        self,
        type_name: str,
        serializer: Callable,
        deserializer: Callable
    ) -> None:
        """Register custom type serialization handlers."""
        self._type_registry[type_name] = serializer
        self._deserializer_registry[type_name] = deserializer
        logger.debug(f"Registered type handler for: {type_name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get serialization statistics."""
        return self.stats.copy()
    
    def _preprocess_state(self, state: Any, config: SerializationConfig) -> Any:
        """Preprocess state before serialization."""
        if config.preserve_types:
            return self._preserve_types(state)
        return state
    
    def _postprocess_state(self, state: Any, metadata: Dict[str, Any]) -> Any:
        """Post-process state after deserialization."""
        if metadata.get("preserve_types", False):
            return self._restore_types(state, metadata.get("type_info", {}))
        return state
    
    def _preserve_types(self, obj: Any) -> Any:
        """Preserve type information for complex objects."""
        if is_dataclass(obj):
            return {
                "__type__": "dataclass",
                "__class__": f"{obj.__class__.__module__}.{obj.__class__.__qualname__}",
                "__data__": asdict(obj)
            }
        elif isinstance(obj, datetime):
            return {
                "__type__": "datetime",
                "__data__": obj.isoformat()
            }
        elif isinstance(obj, Enum):
            return {
                "__type__": "enum",
                "__class__": f"{obj.__class__.__module__}.{obj.__class__.__qualname__}",
                "__data__": obj.value
            }
        elif isinstance(obj, dict):
            return {k: self._preserve_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._preserve_types(item) for item in obj]
        else:
            return obj
    
    def _restore_types(self, obj: Any, type_info: Dict[str, Any]) -> Any:
        """Restore type information for complex objects."""
        if isinstance(obj, dict) and "__type__" in obj:
            obj_type = obj["__type__"]
            
            if obj_type == "datetime":
                return datetime.fromisoformat(obj["__data__"])
            elif obj_type == "dataclass":
                # This would require importing the class - simplified for now
                return obj["__data__"]
            elif obj_type == "enum":
                # This would require importing the enum class - simplified for now
                return obj["__data__"]
        elif isinstance(obj, dict):
            return {k: self._restore_types(v, type_info) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._restore_types(item, type_info) for item in obj]
        
        return obj
    
    def _serialize_json(self, state: Any, config: SerializationConfig) -> str:
        """Serialize to JSON format."""
        return json.dumps(state, default=self._json_serializer, indent=2 if config.include_metadata else None)
    
    def _serialize_pickle(self, state: Any, config: SerializationConfig) -> bytes:
        """Serialize to pickle format."""
        return pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL)
    
    def _serialize_compressed_json(self, state: Any, config: SerializationConfig) -> bytes:
        """Serialize to compressed JSON format."""
        json_data = self._serialize_json(state, config)
        return gzip.compress(json_data.encode(), compresslevel=config.compression_level.value)
    
    def _serialize_compressed_pickle(self, state: Any, config: SerializationConfig) -> bytes:
        """Serialize to compressed pickle format."""
        pickle_data = self._serialize_pickle(state, config)
        return gzip.compress(pickle_data, compresslevel=config.compression_level.value)
    
    def _serialize_binary(self, state: Any, config: SerializationConfig) -> bytes:
        """Serialize to binary format."""
        # Use pickle as base for binary serialization
        return self._serialize_pickle(state, config)
    
    def _deserialize_json(self, data: str) -> Any:
        """Deserialize from JSON format."""
        return json.loads(data)
    
    def _deserialize_pickle(self, data: bytes) -> Any:
        """Deserialize from pickle format."""
        return pickle.loads(data)
    
    def _deserialize_compressed_json(self, data: bytes) -> Any:
        """Deserialize from compressed JSON format."""
        decompressed = gzip.decompress(data)
        return self._deserialize_json(decompressed.decode())
    
    def _deserialize_compressed_pickle(self, data: bytes) -> Any:
        """Deserialize from compressed pickle format."""
        decompressed = gzip.decompress(data)
        return self._deserialize_pickle(decompressed)
    
    def _deserialize_binary(self, data: bytes) -> Any:
        """Deserialize from binary format."""
        return self._deserialize_pickle(data)
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for complex types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    def _calculate_checksum(self, data: Union[str, bytes]) -> str:
        """Calculate checksum for data integrity."""
        if isinstance(data, str):
            data = data.encode()
        return hashlib.sha256(data).hexdigest()
    
    def _verify_checksum(self, serialized_state: SerializedState) -> bool:
        """Verify data integrity using checksum."""
        calculated_checksum = self._calculate_checksum(serialized_state.data)
        return calculated_checksum == serialized_state.checksum
    
    def _create_metadata(
        self,
        state: Any,
        config: SerializationConfig,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Create metadata for serialized state."""
        metadata = {
            "serializer_version": "1.0",
            "format": config.format.value,
            "compression_level": config.compression_level.value,
            "preserve_types": config.preserve_types,
            "created_at": start_time.isoformat(),
            "state_type": type(state).__name__
        }
        
        if config.include_metadata:
            metadata.update({
                "state_size_estimate": len(str(state)),
                "serialization_config": asdict(config)
            })
        
        return metadata
    
    def _generate_snapshot_id(self, component: str, state: Any) -> str:
        """Generate unique snapshot ID."""
        content = f"{component}:{type(state).__name__}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _register_default_handlers(self) -> None:
        """Register default type handlers."""
        # Path serialization
        self.register_type_handler(
            "pathlib.Path",
            lambda p: str(p),
            lambda s: Path(s)
        )
        
        # Set serialization
        self.register_type_handler(
            "set",
            lambda s: list(s),
            lambda l: set(l)
        )
    
    def _update_serialize_stats(self, start_time: datetime, serialized_state: SerializedState) -> None:
        """Update serialization statistics."""
        self.stats["serializations"] += 1
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Update average
        total_time = self.stats["avg_serialize_time_ms"] * (self.stats["serializations"] - 1)
        self.stats["avg_serialize_time_ms"] = (total_time + execution_time) / self.stats["serializations"]
    
    def _update_deserialize_stats(self, start_time: datetime) -> None:
        """Update deserialization statistics."""
        self.stats["deserializations"] += 1
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Update average
        total_time = self.stats["avg_deserialize_time_ms"] * (self.stats["deserializations"] - 1)
        self.stats["avg_deserialize_time_ms"] = (total_time + execution_time) / self.stats["deserializations"]