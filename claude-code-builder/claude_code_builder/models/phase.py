"""Phase and task models for project execution."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum

from .base import SerializableModel, TimestampedModel, IdentifiedModel
from ..exceptions import ValidationError
from ..utils.constants import (
    TASK_PENDING,
    TASK_IN_PROGRESS,
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_SKIPPED,
    TASK_BLOCKED
)


class TaskStatus(Enum):
    """Task execution status."""
    
    PENDING = TASK_PENDING
    IN_PROGRESS = TASK_IN_PROGRESS
    COMPLETED = TASK_COMPLETED
    FAILED = TASK_FAILED
    SKIPPED = TASK_SKIPPED
    BLOCKED = TASK_BLOCKED
    
    def is_terminal(self) -> bool:
        """Check if status is terminal (no further progress)."""
        return self in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]
    
    def is_active(self) -> bool:
        """Check if status indicates active work."""
        return self == TaskStatus.IN_PROGRESS


class PhaseStatus(Enum):
    """Phase execution status."""
    
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    
    def is_terminal(self) -> bool:
        """Check if status is terminal."""
        return self in [PhaseStatus.COMPLETED, PhaseStatus.FAILED, PhaseStatus.SKIPPED]


@dataclass
class TaskResult:
    """Result of task execution."""
    
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    duration: Optional[timedelta] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "artifacts": self.artifacts,
            "metrics": self.metrics,
            "duration": self.duration.total_seconds() if self.duration else None
        }


@dataclass
class Task(SerializableModel, TimestampedModel, IdentifiedModel):
    """Individual task within a phase."""
    
    name: str
    description: str
    command: Optional[str] = None
    function: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[TaskResult] = None
    
    # Execution details
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[timedelta] = None
    
    # Task metadata
    critical: bool = True
    weight: float = 1.0
    estimated_duration: Optional[timedelta] = None
    tags: Set[str] = field(default_factory=set)
    
    def validate(self) -> None:
        """Validate task configuration."""
        if not self.name:
            raise ValidationError("Task name is required")
        
        if not self.command and not self.function:
            raise ValidationError("Task must have either command or function")
        
        if self.weight < 0:
            raise ValidationError("Task weight must be non-negative")
        
        if self.retry_count > self.max_retries:
            raise ValidationError("Retry count exceeds maximum retries")
    
    def can_execute(self, completed_tasks: Set[str]) -> bool:
        """Check if task can be executed based on dependencies."""
        return all(dep in completed_tasks for dep in self.dependencies)
    
    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.update_timestamp()
    
    def complete(self, result: TaskResult) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
        self.result = result
        self.completed_at = datetime.utcnow()
        self.update_timestamp()
    
    def skip(self, reason: str) -> None:
        """Mark task as skipped."""
        self.status = TaskStatus.SKIPPED
        self.result = TaskResult(
            success=True,
            output=f"Skipped: {reason}"
        )
        self.completed_at = datetime.utcnow()
        self.update_timestamp()
    
    def block(self, reason: str) -> None:
        """Mark task as blocked."""
        self.status = TaskStatus.BLOCKED
        self.result = TaskResult(
            success=False,
            error=f"Blocked: {reason}"
        )
        self.update_timestamp()
    
    def reset(self) -> None:
        """Reset task to pending state."""
        self.status = TaskStatus.PENDING
        self.result = None
        self.started_at = None
        self.completed_at = None
        self.retry_count = 0
        self.update_timestamp()
    
    def get_duration(self) -> Optional[timedelta]:
        """Get task execution duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.result and self.result.duration:
            return self.result.duration
        return None
    
    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return (
            self.status == TaskStatus.FAILED and
            self.retry_count < self.max_retries and
            self.critical
        )


@dataclass
class Dependency:
    """Dependency between phases or tasks."""
    
    source_id: str
    target_id: str
    dependency_type: str = "finish_to_start"
    lag_time: timedelta = timedelta()
    required: bool = True
    
    def validate(self) -> None:
        """Validate dependency."""
        valid_types = ["finish_to_start", "start_to_start", "finish_to_finish", "start_to_finish"]
        if self.dependency_type not in valid_types:
            raise ValidationError(f"Invalid dependency type: {self.dependency_type}")


@dataclass
class Phase(SerializableModel, TimestampedModel, IdentifiedModel):
    """Execution phase containing multiple tasks."""
    
    name: str
    description: str
    objective: str
    tasks: List[Task] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    status: PhaseStatus = PhaseStatus.PENDING
    
    # Execution details
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    planned_duration: Optional[timedelta] = None
    actual_duration: Optional[timedelta] = None
    
    # Phase metadata
    complexity: int = 3
    priority: int = 5
    deliverables: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    rollback_strategy: Optional[str] = None
    
    # Progress tracking
    progress: float = 0.0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    
    # Resource allocation
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    required_tools: List[str] = field(default_factory=list)
    required_services: List[str] = field(default_factory=list)
    
    # Internal indices
    _task_index: Optional[Dict[str, Task]] = field(default=None, init=False)
    
    def __post_init__(self):
        """Initialize phase."""
        super().__init__()
        self._build_task_index()
    
    def _build_task_index(self):
        """Build task index for fast lookup."""
        self._task_index = {task.id: task for task in self.tasks}
    
    def validate(self) -> None:
        """Validate phase configuration."""
        if not self.name:
            raise ValidationError("Phase name is required")
        
        if not self.objective:
            raise ValidationError("Phase objective is required")
        
        if not 1 <= self.complexity <= 10:
            raise ValidationError("Phase complexity must be between 1 and 10")
        
        if not 1 <= self.priority <= 10:
            raise ValidationError("Phase priority must be between 1 and 10")
        
        # Validate tasks
        task_ids = set()
        for task in self.tasks:
            task.validate()
            if task.id in task_ids:
                raise ValidationError(f"Duplicate task ID: {task.id}")
            task_ids.add(task.id)
        
        # Validate task dependencies
        for task in self.tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    raise ValidationError(
                        f"Task '{task.name}' depends on unknown task '{dep}'"
                    )
        
        # Validate dependencies
        for dep in self.dependencies:
            dep.validate()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        if self._task_index is None:
            self._build_task_index()
        return self._task_index.get(task_id)
    
    def add_task(self, task: Task) -> None:
        """Add task to phase."""
        self.tasks.append(task)
        if self._task_index is not None:
            self._task_index[task.id] = task
        self.update_timestamp()
    
    def remove_task(self, task_id: str) -> bool:
        """Remove task from phase."""
        task = self.get_task(task_id)
        if task:
            self.tasks.remove(task)
            if self._task_index is not None:
                del self._task_index[task_id]
            self.update_timestamp()
            return True
        return False
    
    def get_executable_tasks(self) -> List[Task]:
        """Get tasks that can be executed now."""
        completed_task_ids = {
            task.id for task in self.tasks
            if task.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]
        }
        
        return [
            task for task in self.tasks
            if task.status == TaskStatus.PENDING and
            task.can_execute(completed_task_ids)
        ]
    
    def start(self) -> None:
        """Start phase execution."""
        self.status = PhaseStatus.EXECUTING
        self.started_at = datetime.utcnow()
        self.update_timestamp()
    
    def complete(self) -> None:
        """Complete phase execution."""
        self.status = PhaseStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.actual_duration = self.get_duration()
        self.update_timestamp()
    
    def fail(self, error: str) -> None:
        """Mark phase as failed."""
        self.status = PhaseStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.actual_duration = self.get_duration()
        self.update_timestamp()
    
    def update_progress(self) -> None:
        """Update phase progress based on task completion."""
        total_weight = sum(task.weight for task in self.tasks)
        if total_weight == 0:
            self.progress = 0.0
            return
        
        completed_weight = sum(
            task.weight for task in self.tasks
            if task.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]
        )
        
        self.progress = completed_weight / total_weight
        
        # Update task counts
        self.completed_tasks = sum(
            1 for task in self.tasks
            if task.status == TaskStatus.COMPLETED
        )
        self.failed_tasks = sum(
            1 for task in self.tasks
            if task.status == TaskStatus.FAILED
        )
        self.skipped_tasks = sum(
            1 for task in self.tasks
            if task.status == TaskStatus.SKIPPED
        )
        
        self.update_timestamp()
    
    def get_duration(self) -> Optional[timedelta]:
        """Get phase execution duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def is_complete(self) -> bool:
        """Check if phase is complete."""
        return self.status in [PhaseStatus.COMPLETED, PhaseStatus.FAILED, PhaseStatus.SKIPPED]
    
    def can_start(self, completed_phases: Set[str]) -> bool:
        """Check if phase can start based on dependencies."""
        for dep in self.dependencies:
            if dep.required and dep.source_id not in completed_phases:
                return False
        return True
    
    def estimate_remaining_time(self) -> Optional[timedelta]:
        """Estimate remaining time for phase completion."""
        if self.is_complete():
            return timedelta()
        
        remaining_tasks = [
            task for task in self.tasks
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]
        ]
        
        if not remaining_tasks:
            return timedelta()
        
        # Estimate based on task weights and estimated durations
        total_estimate = timedelta()
        for task in remaining_tasks:
            if task.estimated_duration:
                total_estimate += task.estimated_duration
            else:
                # Default estimate: 1 minute per weight unit
                total_estimate += timedelta(minutes=task.weight)
        
        return total_estimate
    
    def get_critical_path(self) -> List[Task]:
        """Get critical path of tasks."""
        # Simplified critical path - tasks with no parallel alternatives
        critical_tasks = []
        
        # Build dependency graph
        dependents: Dict[str, Set[str]] = {task.id: set() for task in self.tasks}
        for task in self.tasks:
            for dep in task.dependencies:
                dependents[dep].add(task.id)
        
        # Find tasks with no dependents (end tasks)
        end_tasks = [
            task for task in self.tasks
            if not dependents[task.id]
        ]
        
        # Trace back from end tasks
        visited = set()
        
        def trace_critical(task_id: str):
            if task_id in visited:
                return
            visited.add(task_id)
            
            task = self.get_task(task_id)
            if task:
                critical_tasks.append(task)
                for dep in task.dependencies:
                    trace_critical(dep)
        
        for task in end_tasks:
            trace_critical(task.id)
        
        return list(reversed(critical_tasks))
    
    def to_gantt_data(self) -> Dict[str, Any]:
        """Convert phase to Gantt chart data."""
        return {
            "id": self.id,
            "name": self.name,
            "start": self.started_at.isoformat() if self.started_at else None,
            "end": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress * 100,
            "tasks": [
                {
                    "id": task.id,
                    "name": task.name,
                    "start": task.started_at.isoformat() if task.started_at else None,
                    "end": task.completed_at.isoformat() if task.completed_at else None,
                    "status": task.status.value,
                    "dependencies": task.dependencies
                }
                for task in self.tasks
            ]
        }