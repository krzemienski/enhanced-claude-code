"""Data models for Claude Code Builder."""

from .base import (
    BaseModel,
    SerializableModel,
    TimestampedModel,
    IdentifiedModel,
    VersionedModel,
    Repository,
    InMemoryRepository,
    Result,
    Event,
    EventBus
)

from .project import (
    Technology,
    Feature,
    APIEndpoint,
    ProjectMetadata,
    BuildRequirements,
    SecurityRequirements,
    PerformanceRequirements,
    ProjectSpec,
    BuildConfig
)

from .phase import (
    TaskStatus,
    PhaseStatus,
    TaskResult,
    Task,
    Dependency,
    Phase
)

from .cost import (
    CostCategory,
    CostEntry,
    CostBreakdown,
    CostTracker
)

from .memory import (
    MemoryType,
    ContextEntry,
    ErrorLog,
    MemoryQuery,
    MemoryStore
)

from .validation import (
    ValidationLevel,
    ValidationType,
    ValidationIssue,
    ValidationRule,
    ValidationResult,
    ValidationConfig,
    BUILTIN_RULES
)

from .research import (
    ResearchStatus,
    ConfidenceLevel,
    ResearchSource,
    ResearchFinding,
    ResearchQuery,
    AgentResponse,
    ResearchResult
)

from .testing import (
    TestStage,
    TestStatus,
    TestAssertion,
    TestMetrics,
    TestCase,
    TestPlan,
    TestResult
)

from .monitoring import (
    LogLevel,
    MetricType,
    AlertStatus,
    LogEntry,
    Metric,
    ProgressTracker,
    Alert,
    MonitoringDashboard
)

__all__ = [
    # Base models
    "BaseModel",
    "SerializableModel",
    "TimestampedModel",
    "IdentifiedModel",
    "VersionedModel",
    "Repository",
    "InMemoryRepository",
    "Result",
    "Event",
    "EventBus",
    
    # Project models
    "Technology",
    "Feature",
    "APIEndpoint",
    "ProjectMetadata",
    "BuildRequirements",
    "SecurityRequirements",
    "PerformanceRequirements",
    "ProjectSpec",
    "BuildConfig",
    
    # Phase models
    "TaskStatus",
    "PhaseStatus",
    "TaskResult",
    "Task",
    "Dependency",
    "Phase",
    
    # Cost models
    "CostCategory",
    "CostEntry",
    "CostBreakdown",
    "CostTracker",
    
    # Memory models
    "MemoryType",
    "ContextEntry",
    "ErrorLog",
    "MemoryQuery",
    "MemoryStore",
    
    # Validation models
    "ValidationLevel",
    "ValidationType",
    "ValidationIssue",
    "ValidationRule",
    "ValidationResult",
    "ValidationConfig",
    "BUILTIN_RULES",
    
    # Research models
    "ResearchStatus",
    "ConfidenceLevel",
    "ResearchSource",
    "ResearchFinding",
    "ResearchQuery",
    "AgentResponse",
    "ResearchResult",
    
    # Testing models
    "TestStage",
    "TestStatus",
    "TestAssertion",
    "TestMetrics",
    "TestCase",
    "TestPlan",
    "TestResult",
    
    # Monitoring models
    "LogLevel",
    "MetricType",
    "AlertStatus",
    "LogEntry",
    "Metric",
    "ProgressTracker",
    "Alert",
    "MonitoringDashboard"
]