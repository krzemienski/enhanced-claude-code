"""Memory and Context System for advanced state management and recovery."""

from .store import (
    PersistentMemoryStore,
    MemoryEntry,
    MemoryQuery,
    MemoryStats,
    MemoryType,
    MemoryPriority
)

from .context_accumulator import (
    ContextAccumulator,
    AccumulatedContext,
    ContextFragment,
    ContextType,
    ContextScope
)

from .error_context import (
    ErrorContextManager,
    ErrorContext,
    ErrorPattern,
    ErrorSeverity,
    ErrorCategory,
    RecoveryStrategy
)

from .query_engine import (
    MemoryQueryEngine,
    QueryFilter,
    QueryResult,
    QueryType,
    SortBy,
    SemanticMatch
)

from .serializer import (
    StateSerializer,
    SerializedState,
    StateSnapshot,
    SerializationConfig,
    SerializationFormat,
    CompressionLevel
)

from .cache import (
    MultiLevelCache,
    CacheEntry,
    CacheConfig,
    CachePolicy,
    CacheLevel,
    CacheStats,
    get_global_cache,
    set_global_cache
)

from .recovery import (
    ContextRecoveryManager,
    RecoveryPoint,
    RecoveryPlan,
    RecoveryResult,
    RecoveryStrategy as RecoveryStrategy_,
    RecoveryPriority
)

__all__ = [
    # Store components
    "PersistentMemoryStore",
    "MemoryEntry",
    "MemoryQuery", 
    "MemoryStats",
    "MemoryType",
    "MemoryPriority",
    
    # Context accumulation
    "ContextAccumulator",
    "AccumulatedContext",
    "ContextFragment",
    "ContextType",
    "ContextScope",
    
    # Error context
    "ErrorContextManager",
    "ErrorContext",
    "ErrorPattern",
    "ErrorSeverity",
    "ErrorCategory",
    "RecoveryStrategy",
    
    # Query engine
    "MemoryQueryEngine",
    "QueryFilter",
    "QueryResult",
    "QueryType",
    "SortBy",
    "SemanticMatch",
    
    # Serialization
    "StateSerializer",
    "SerializedState",
    "StateSnapshot",
    "SerializationConfig",
    "SerializationFormat",
    "CompressionLevel",
    
    # Caching
    "MultiLevelCache",
    "CacheEntry",
    "CacheConfig",
    "CachePolicy",
    "CacheLevel",
    "CacheStats",
    "get_global_cache",
    "set_global_cache",
    
    # Recovery
    "ContextRecoveryManager",
    "RecoveryPoint",
    "RecoveryPlan", 
    "RecoveryResult",
    "RecoveryStrategy_",
    "RecoveryPriority"
]

# Version information
__version__ = "3.0.0"