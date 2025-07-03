"""Recovery system for handling execution failures and resumption."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json

from ..models.project import ProjectSpec
from ..models.phase import Phase, Task, TaskStatus, TaskResult
from ..exceptions import ValidationError
from .checkpoint import CheckpointManager, CheckpointData

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Strategies for recovering from failures."""
    RETRY_FAILED = "retry_failed"
    SKIP_FAILED = "skip_failed"
    RESTART_PHASE = "restart_phase"
    RESTART_ALL = "restart_all"
    MANUAL = "manual"
    ADAPTIVE = "adaptive"


class FailureType(Enum):
    """Types of failures that can occur."""
    TASK_FAILURE = "task_failure"
    PHASE_FAILURE = "phase_failure"
    DEPENDENCY_FAILURE = "dependency_failure"
    RESOURCE_FAILURE = "resource_failure"
    TIMEOUT = "timeout"
    SYSTEM_ERROR = "system_error"
    USER_ABORT = "user_abort"


@dataclass
class FailureContext:
    """Context information about a failure."""
    failure_type: FailureType
    timestamp: datetime
    phase_id: Optional[str] = None
    task_id: Optional[str] = None
    error_message: str = ""
    error_details: Dict[str, Any] = field(default_factory=dict)
    recovery_attempts: int = 0
    recoverable: bool = True


@dataclass
class RecoveryPlan:
    """Plan for recovering from a failure."""
    strategy: RecoveryStrategy
    checkpoint_id: Optional[str] = None
    resume_from_phase: Optional[str] = None
    resume_from_task: Optional[str] = None
    skip_phases: List[str] = field(default_factory=list)
    skip_tasks: List[str] = field(default_factory=list)
    retry_tasks: List[str] = field(default_factory=list)
    modifications: Dict[str, Any] = field(default_factory=dict)
    estimated_time: Optional[float] = None


class RecoveryManager:
    """Manages failure recovery and execution resumption."""
    
    def __init__(self, checkpoint_manager: CheckpointManager):
        """Initialize the recovery manager."""
        self.checkpoint_manager = checkpoint_manager
        
        # Recovery configuration
        self.max_recovery_attempts = 3
        self.failure_threshold = 5  # Max failures before stopping
        
        # Failure tracking
        self.failure_history: List[FailureContext] = []
        self.recovery_history: List[Tuple[FailureContext, RecoveryPlan]] = []
        
        # Recovery strategies
        self.strategy_handlers = {
            RecoveryStrategy.RETRY_FAILED: self._recover_retry_failed,
            RecoveryStrategy.SKIP_FAILED: self._recover_skip_failed,
            RecoveryStrategy.RESTART_PHASE: self._recover_restart_phase,
            RecoveryStrategy.RESTART_ALL: self._recover_restart_all,
            RecoveryStrategy.MANUAL: self._recover_manual,
            RecoveryStrategy.ADAPTIVE: self._recover_adaptive
        }
        
        logger.info("Recovery Manager initialized")
    
    def analyze_failure(
        self,
        error: Exception,
        project: ProjectSpec,
        execution_context: Dict[str, Any],
        phase: Optional[Phase] = None,
        task: Optional[Task] = None
    ) -> FailureContext:
        """Analyze a failure and determine its type and recoverability."""
        # Determine failure type
        failure_type = self._determine_failure_type(error)
        
        # Create failure context
        failure_context = FailureContext(
            failure_type=failure_type,
            timestamp=datetime.now(),
            phase_id=phase.id if phase else None,
            task_id=task.id if task else None,
            error_message=str(error),
            error_details={
                "error_type": type(error).__name__,
                "project_id": project.config.id,
                "execution_id": execution_context.execution_id
            }
        )
        
        # Determine recoverability
        failure_context.recoverable = self._is_recoverable(
            failure_context, error
        )
        
        # Add to history
        self.failure_history.append(failure_context)
        
        logger.info(
            f"Analyzed failure: {failure_type.value} - "
            f"Recoverable: {failure_context.recoverable}"
        )
        
        return failure_context
    
    def create_recovery_plan(
        self,
        failure_context: FailureContext,
        project: ProjectSpec,
        checkpoint_data: Optional[CheckpointData] = None,
        strategy: Optional[RecoveryStrategy] = None
    ) -> RecoveryPlan:
        """Create a recovery plan for a failure."""
        # Check recovery attempts
        if failure_context.recovery_attempts >= self.max_recovery_attempts:
            raise RecoveryError(
                f"Maximum recovery attempts ({self.max_recovery_attempts}) exceeded"
            )
        
        # Determine strategy if not specified
        if not strategy:
            strategy = self._select_recovery_strategy(
                failure_context, project, checkpoint_data
            )
        
        logger.info(f"Creating recovery plan with strategy: {strategy.value}")
        
        # Get strategy handler
        handler = self.strategy_handlers.get(strategy)
        if not handler:
            raise RecoveryError(f"Unknown recovery strategy: {strategy}")
        
        # Create plan
        recovery_plan = handler(failure_context, project, checkpoint_data)
        
        # Record in history
        self.recovery_history.append((failure_context, recovery_plan))
        
        return recovery_plan
    
    def execute_recovery(
        self,
        recovery_plan: RecoveryPlan,
        project: ProjectSpec,
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a recovery plan."""
        logger.info(f"Executing recovery plan: {recovery_plan.strategy.value}")
        
        result = {
            "strategy": recovery_plan.strategy.value,
            "started_at": datetime.now().isoformat(),
            "modifications": {}
        }
        
        try:
            # Load checkpoint if specified
            if recovery_plan.checkpoint_id:
                checkpoint_data = self.checkpoint_manager.restore_checkpoint(
                    recovery_plan.checkpoint_id
                )
                result["checkpoint_restored"] = recovery_plan.checkpoint_id
                
                # Restore project state
                project = self._restore_project_state(
                    project, checkpoint_data
                )
            
            # Apply modifications
            if recovery_plan.modifications:
                project = self._apply_modifications(
                    project, recovery_plan.modifications
                )
                result["modifications"] = recovery_plan.modifications
            
            # Update execution context
            execution_context = self._prepare_recovery_context(
                execution_context, recovery_plan
            )
            
            result["status"] = "ready"
            result["resume_point"] = {
                "phase": recovery_plan.resume_from_phase,
                "task": recovery_plan.resume_from_task
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Recovery execution failed: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
            return result
    
    def can_recover(
        self,
        failure_context: FailureContext
    ) -> bool:
        """Check if recovery is possible for a failure."""
        # Check if failure is recoverable
        if not failure_context.recoverable:
            return False
        
        # Check failure threshold
        recent_failures = [
            f for f in self.failure_history
            if (datetime.now() - f.timestamp).total_seconds() < 3600
        ]
        
        if len(recent_failures) >= self.failure_threshold:
            logger.warning(
                f"Failure threshold exceeded: {len(recent_failures)} failures in last hour"
            )
            return False
        
        # Check recovery attempts
        if failure_context.recovery_attempts >= self.max_recovery_attempts:
            return False
        
        return True
    
    def get_recovery_suggestions(
        self,
        failure_context: FailureContext,
        project: ProjectSpec
    ) -> List[Dict[str, Any]]:
        """Get recovery suggestions for a failure."""
        suggestions = []
        
        # Retry suggestion
        if failure_context.failure_type in [
            FailureType.TASK_FAILURE,
            FailureType.TIMEOUT
        ]:
            suggestions.append({
                "strategy": RecoveryStrategy.RETRY_FAILED,
                "description": "Retry the failed task/phase",
                "confidence": 0.8,
                "estimated_time": 300  # 5 minutes
            })
        
        # Skip suggestion
        if failure_context.task_id:
            suggestions.append({
                "strategy": RecoveryStrategy.SKIP_FAILED,
                "description": "Skip the failed task and continue",
                "confidence": 0.6,
                "warnings": ["May cause dependency issues"]
            })
        
        # Restart phase suggestion
        if failure_context.phase_id:
            suggestions.append({
                "strategy": RecoveryStrategy.RESTART_PHASE,
                "description": "Restart the entire phase",
                "confidence": 0.7,
                "estimated_time": 1800  # 30 minutes
            })
        
        # Adaptive suggestion
        suggestions.append({
            "strategy": RecoveryStrategy.ADAPTIVE,
            "description": "Use adaptive recovery based on failure analysis",
            "confidence": 0.9,
            "recommended": True
        })
        
        return suggestions
    
    def _determine_failure_type(self, error: Exception) -> FailureType:
        """Determine the type of failure from an exception."""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        if "timeout" in error_message:
            return FailureType.TIMEOUT
        elif "dependency" in error_message:
            return FailureType.DEPENDENCY_FAILURE
        elif "resource" in error_message or "memory" in error_message:
            return FailureType.RESOURCE_FAILURE
        elif "abort" in error_message or "cancel" in error_message:
            return FailureType.USER_ABORT
        elif error_type in ["SystemError", "OSError", "IOError"]:
            return FailureType.SYSTEM_ERROR
        else:
            return FailureType.TASK_FAILURE
    
    def _is_recoverable(
        self,
        failure_context: FailureContext,
        error: Exception
    ) -> bool:
        """Determine if a failure is recoverable."""
        # Non-recoverable failure types
        non_recoverable = [
            FailureType.USER_ABORT,
            FailureType.DEPENDENCY_FAILURE
        ]
        
        if failure_context.failure_type in non_recoverable:
            return False
        
        # Check specific error types
        non_recoverable_errors = [
            "PermissionError",
            "AuthenticationError",
            "InvalidProjectSpecError"
        ]
        
        if type(error).__name__ in non_recoverable_errors:
            return False
        
        return True
    
    def _select_recovery_strategy(
        self,
        failure_context: FailureContext,
        project: ProjectSpec,
        checkpoint_data: Optional[CheckpointData]
    ) -> RecoveryStrategy:
        """Select the best recovery strategy."""
        # If no checkpoint available, limited options
        if not checkpoint_data:
            if failure_context.failure_type == FailureType.TASK_FAILURE:
                return RecoveryStrategy.RETRY_FAILED
            else:
                return RecoveryStrategy.RESTART_ALL
        
        # Adaptive strategy for most cases
        return RecoveryStrategy.ADAPTIVE
    
    def _recover_retry_failed(
        self,
        failure_context: FailureContext,
        project: ProjectSpec,
        checkpoint_data: Optional[CheckpointData]
    ) -> RecoveryPlan:
        """Create plan to retry failed tasks."""
        plan = RecoveryPlan(strategy=RecoveryStrategy.RETRY_FAILED)
        
        if checkpoint_data:
            plan.checkpoint_id = checkpoint_data.metadata.id
        
        if failure_context.task_id:
            plan.retry_tasks = [failure_context.task_id]
            plan.resume_from_task = failure_context.task_id
        elif failure_context.phase_id:
            plan.resume_from_phase = failure_context.phase_id
        
        plan.estimated_time = 300  # 5 minutes
        
        return plan
    
    def _recover_skip_failed(
        self,
        failure_context: FailureContext,
        project: ProjectSpec,
        checkpoint_data: Optional[CheckpointData]
    ) -> RecoveryPlan:
        """Create plan to skip failed tasks."""
        plan = RecoveryPlan(strategy=RecoveryStrategy.SKIP_FAILED)
        
        if checkpoint_data:
            plan.checkpoint_id = checkpoint_data.metadata.id
        
        if failure_context.task_id:
            plan.skip_tasks = [failure_context.task_id]
            # Find next task
            plan.resume_from_task = self._find_next_task(
                project, failure_context.phase_id, failure_context.task_id
            )
        
        return plan
    
    def _recover_restart_phase(
        self,
        failure_context: FailureContext,
        project: ProjectSpec,
        checkpoint_data: Optional[CheckpointData]
    ) -> RecoveryPlan:
        """Create plan to restart the phase."""
        plan = RecoveryPlan(strategy=RecoveryStrategy.RESTART_PHASE)
        
        if failure_context.phase_id:
            # Find checkpoint before this phase
            phase_checkpoints = self.checkpoint_manager.list_checkpoints(
                project_id=project.config.id,
                tags=[f"phase_{failure_context.phase_id}"]
            )
            
            if phase_checkpoints:
                # Use checkpoint from before the phase
                plan.checkpoint_id = phase_checkpoints[0].id
            
            plan.resume_from_phase = failure_context.phase_id
        
        return plan
    
    def _recover_restart_all(
        self,
        failure_context: FailureContext,
        project: ProjectSpec,
        checkpoint_data: Optional[CheckpointData]
    ) -> RecoveryPlan:
        """Create plan to restart entire execution."""
        plan = RecoveryPlan(strategy=RecoveryStrategy.RESTART_ALL)
        
        # Start from beginning
        if project.phases:
            plan.resume_from_phase = project.phases[0].id
        
        # Clear all progress
        plan.modifications["clear_progress"] = True
        
        return plan
    
    def _recover_manual(
        self,
        failure_context: FailureContext,
        project: ProjectSpec,
        checkpoint_data: Optional[CheckpointData]
    ) -> RecoveryPlan:
        """Create plan for manual recovery."""
        plan = RecoveryPlan(strategy=RecoveryStrategy.MANUAL)
        
        # Provide information for manual intervention
        plan.modifications["manual_steps"] = [
            "Review the failure context",
            "Identify root cause",
            "Apply manual fixes",
            "Resume execution"
        ]
        
        return plan
    
    def _recover_adaptive(
        self,
        failure_context: FailureContext,
        project: ProjectSpec,
        checkpoint_data: Optional[CheckpointData]
    ) -> RecoveryPlan:
        """Create adaptive recovery plan based on failure analysis."""
        plan = RecoveryPlan(strategy=RecoveryStrategy.ADAPTIVE)
        
        # Analyze failure patterns
        similar_failures = self._find_similar_failures(failure_context)
        
        # Determine best approach
        if len(similar_failures) > 2:
            # Recurring failure - try different approach
            if failure_context.task_id:
                plan.skip_tasks = [failure_context.task_id]
                plan.modifications["alternative_approach"] = True
        else:
            # First time failure - retry with modifications
            if failure_context.failure_type == FailureType.TIMEOUT:
                plan.modifications["increase_timeout"] = True
            elif failure_context.failure_type == FailureType.RESOURCE_FAILURE:
                plan.modifications["reduce_parallelism"] = True
            
            plan.retry_tasks = [failure_context.task_id] if failure_context.task_id else []
        
        # Use best checkpoint
        if checkpoint_data:
            plan.checkpoint_id = checkpoint_data.metadata.id
        
        return plan
    
    def _restore_project_state(
        self,
        project: ProjectSpec,
        checkpoint_data: CheckpointData
    ) -> ProjectSpec:
        """Restore project state from checkpoint."""
        # Restore project fields from checkpoint
        project_state = checkpoint_data.project_state
        
        # Update project status and metadata
        if "status" in project_state:
            project.status = TaskStatus(project_state["status"])
        
        if "metadata" in project_state:
            project.metadata.update(project_state["metadata"])
        
        return project
    
    def _apply_modifications(
        self,
        project: ProjectSpec,
        modifications: Dict[str, Any]
    ) -> ProjectSpec:
        """Apply modifications to project configuration."""
        if "increase_timeout" in modifications:
            # Increase timeouts for all tasks
            for phase in project.phases:
                for task in phase.tasks:
                    task.metadata["timeout"] = task.metadata.get("timeout", 600) * 1.5
        
        if "reduce_parallelism" in modifications:
            # Reduce concurrent execution
            project.metadata["max_concurrent_tasks"] = 1
        
        if "clear_progress" in modifications:
            # Clear all progress markers
            project.metadata["completed_phases"] = []
            project.metadata["completed_tasks"] = []
        
        return project
    
    def _prepare_recovery_context(
        self,
        context: Dict[str, Any],
        recovery_plan: RecoveryPlan
    ) -> Dict[str, Any]:
        """Prepare execution context for recovery."""
        # Add recovery information
        context.metadata["recovery"] = {
            "strategy": recovery_plan.strategy.value,
            "checkpoint_id": recovery_plan.checkpoint_id,
            "skip_tasks": recovery_plan.skip_tasks,
            "retry_tasks": recovery_plan.retry_tasks
        }
        
        # Update resume points
        if recovery_plan.resume_from_phase:
            context.metadata["resume_from_phase"] = recovery_plan.resume_from_phase
        
        if recovery_plan.resume_from_task:
            context.metadata["resume_from_task"] = recovery_plan.resume_from_task
        
        return context
    
    def _find_next_task(
        self,
        project: ProjectSpec,
        phase_id: str,
        task_id: str
    ) -> Optional[str]:
        """Find the next task after a given task."""
        # Find the phase
        phase = next((p for p in project.phases if p.id == phase_id), None)
        if not phase:
            return None
        
        # Find task index
        task_index = next(
            (i for i, t in enumerate(phase.tasks) if t.id == task_id),
            -1
        )
        
        if task_index >= 0 and task_index < len(phase.tasks) - 1:
            return phase.tasks[task_index + 1].id
        
        return None
    
    def _find_similar_failures(
        self,
        failure_context: FailureContext
    ) -> List[FailureContext]:
        """Find similar failures in history."""
        similar = []
        
        for historical_failure in self.failure_history:
            if historical_failure == failure_context:
                continue
            
            # Check similarity
            if (
                historical_failure.failure_type == failure_context.failure_type and
                historical_failure.phase_id == failure_context.phase_id and
                historical_failure.task_id == failure_context.task_id
            ):
                similar.append(historical_failure)
        
        return similar