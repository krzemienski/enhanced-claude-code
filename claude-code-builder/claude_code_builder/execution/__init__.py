"""Execution System Core for Claude Code Builder.

This module provides the main execution engine with phase management,
task running, checkpoint/recovery, and validation capabilities.
"""

from .orchestrator import (
    ExecutionOrchestrator, 
    OrchestrationConfig, 
    OrchestrationState,
    ExecutionMode
)
from .phase_executor import (
    PhaseExecutor,
    PhaseExecutionConfig,
    PhaseExecutionState,
    TaskExecutionStrategy
)
from .task_runner import (
    TaskRunner,
    TaskRunnerConfig,
    TaskExecutionContext,
    TaskType
)
from .checkpoint import (
    CheckpointManager,
    CheckpointMetadata,
    CheckpointData
)
from .recovery import (
    RecoveryManager,
    RecoveryStrategy,
    RecoveryPlan,
    FailureContext,
    FailureType
)
from .validator import (
    ExecutionValidator,
    ValidationConfig,
    ValidationReport
)
from .state_manager import (
    StateManager,
    StateType,
    StateEntry,
    StateSnapshot
)

__all__ = [
    # Orchestrator
    "ExecutionOrchestrator",
    "OrchestrationConfig",
    "OrchestrationState",
    "ExecutionMode",
    
    # Phase Executor
    "PhaseExecutor",
    "PhaseExecutionConfig",
    "PhaseExecutionState",
    "TaskExecutionStrategy",
    
    # Task Runner
    "TaskRunner",
    "TaskRunnerConfig",
    "TaskExecutionContext",
    "TaskType",
    
    # Checkpoint
    "CheckpointManager",
    "CheckpointMetadata",
    "CheckpointData",
    
    # Recovery
    "RecoveryManager",
    "RecoveryStrategy",
    "RecoveryPlan",
    "FailureContext",
    "FailureType",
    
    # Validator
    "ExecutionValidator",
    "ValidationConfig",
    "ValidationReport",
    
    # State Manager
    "StateManager",
    "StateType",
    "StateEntry",
    "StateSnapshot",
]