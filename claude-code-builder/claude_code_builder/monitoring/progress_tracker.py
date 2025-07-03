"""Progress tracking with ETA calculation for real-time monitoring."""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics
import threading

from ..models.project import Project, BuildPhase, BuildTask, BuildStatus
from ..models.context import ExecutionContext

logger = logging.getLogger(__name__)


class ProgressPhase(Enum):
    """Progress tracking phases."""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    FINISHING = "finishing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskProgress:
    """Progress information for a single task."""
    task_id: str
    task_name: str
    status: BuildStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress_percent: float = 0.0
    estimated_duration: Optional[float] = None
    actual_duration: Optional[float] = None
    subtasks_completed: int = 0
    subtasks_total: int = 0
    errors: int = 0
    warnings: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhaseProgress:
    """Progress information for a build phase."""
    phase_id: str
    phase_name: str
    status: BuildStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress_percent: float = 0.0
    tasks_completed: int = 0
    tasks_total: int = 0
    task_progress: Dict[str, TaskProgress] = field(default_factory=dict)
    estimated_duration: Optional[float] = None
    actual_duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectProgress:
    """Overall project progress information."""
    project_id: str
    project_name: str
    execution_id: str
    status: BuildStatus
    current_phase: ProgressPhase
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress_percent: float = 0.0
    phases_completed: int = 0
    phases_total: int = 0
    phase_progress: Dict[str, PhaseProgress] = field(default_factory=dict)
    estimated_total_duration: Optional[float] = None
    estimated_remaining_duration: Optional[float] = None
    actual_duration: Optional[float] = None
    throughput_tasks_per_minute: float = 0.0
    cost_estimate: float = 0.0
    cost_actual: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ETACalculation:
    """Estimated Time of Arrival calculation."""
    eta_seconds: float
    eta_datetime: datetime
    confidence: float  # 0.0 to 1.0
    method: str  # Method used for calculation
    factors: Dict[str, Any] = field(default_factory=dict)


class ProgressTracker:
    """Tracks execution progress and calculates ETAs."""
    
    def __init__(self):
        """Initialize the progress tracker."""
        self.project_progress: Dict[str, ProjectProgress] = {}
        self.historical_data: Dict[str, List[float]] = {}  # Task durations
        self.performance_samples: List[Tuple[datetime, float]] = []  # Timestamp, progress
        self.lock = threading.RLock()
        
        # ETA calculation parameters
        self.eta_window_size = 10  # Number of samples for ETA calculation
        self.min_samples_for_eta = 3  # Minimum samples before calculating ETA
        self.smoothing_factor = 0.3  # For exponential smoothing
        
        # Performance tracking
        self.performance_history: Dict[str, List[float]] = {
            "task_duration": [],
            "phase_duration": [],
            "throughput": []
        }
        
        logger.info("Progress Tracker initialized")
    
    def start_project_tracking(
        self,
        project: Project,
        execution_id: str,
        context: ExecutionContext
    ) -> ProjectProgress:
        """Start tracking progress for a project."""
        with self.lock:
            project_progress = ProjectProgress(
                project_id=project.config.id,
                project_name=project.config.name,
                execution_id=execution_id,
                status=BuildStatus.RUNNING,
                current_phase=ProgressPhase.INITIALIZING,
                start_time=datetime.now(),
                phases_total=len(project.phases),
                estimated_total_duration=self._estimate_total_duration(project)
            )
            
            # Initialize phase progress
            for phase in project.phases:
                phase_progress = PhaseProgress(
                    phase_id=phase.id,
                    phase_name=phase.name,
                    status=BuildStatus.PENDING,
                    tasks_total=len(phase.tasks),
                    estimated_duration=self._estimate_phase_duration(phase)
                )
                
                # Initialize task progress
                for task in phase.tasks:
                    task_progress = TaskProgress(
                        task_id=task.id,
                        task_name=task.name,
                        status=BuildStatus.PENDING,
                        estimated_duration=self._estimate_task_duration(task)
                    )
                    phase_progress.task_progress[task.id] = task_progress
                
                project_progress.phase_progress[phase.id] = phase_progress
            
            self.project_progress[execution_id] = project_progress
            
            logger.info(f"Started tracking project: {project.config.name}")
            
            return project_progress
    
    def update_phase_progress(
        self,
        execution_id: str,
        phase_id: str,
        status: BuildStatus,
        progress_percent: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update progress for a phase."""
        with self.lock:
            if execution_id not in self.project_progress:
                logger.warning(f"No tracking for execution: {execution_id}")
                return
            
            project_progress = self.project_progress[execution_id]
            
            if phase_id not in project_progress.phase_progress:
                logger.warning(f"No tracking for phase: {phase_id}")
                return
            
            phase_progress = project_progress.phase_progress[phase_id]
            
            # Update phase status
            old_status = phase_progress.status
            phase_progress.status = status
            
            if metadata:
                phase_progress.metadata.update(metadata)
            
            # Handle status transitions
            if old_status != status:
                if status == BuildStatus.RUNNING and not phase_progress.start_time:
                    phase_progress.start_time = datetime.now()
                elif status in [BuildStatus.COMPLETED, BuildStatus.FAILED, BuildStatus.CANCELLED]:
                    phase_progress.end_time = datetime.now()
                    if phase_progress.start_time:
                        phase_progress.actual_duration = (
                            phase_progress.end_time - phase_progress.start_time
                        ).total_seconds()
                        self._record_phase_duration(phase_id, phase_progress.actual_duration)
            
            # Update progress percentage
            if progress_percent is not None:
                phase_progress.progress_percent = min(100.0, max(0.0, progress_percent))
            else:
                # Calculate based on task completion
                phase_progress.progress_percent = self._calculate_phase_progress(phase_progress)
            
            # Update project progress
            self._update_project_progress(execution_id)
            
            logger.debug(f"Updated phase {phase_id} progress: {phase_progress.progress_percent:.1f}%")
    
    def update_task_progress(
        self,
        execution_id: str,
        phase_id: str,
        task_id: str,
        status: BuildStatus,
        progress_percent: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update progress for a task."""
        with self.lock:
            if execution_id not in self.project_progress:
                logger.warning(f"No tracking for execution: {execution_id}")
                return
            
            project_progress = self.project_progress[execution_id]
            
            if phase_id not in project_progress.phase_progress:
                logger.warning(f"No tracking for phase: {phase_id}")
                return
            
            phase_progress = project_progress.phase_progress[phase_id]
            
            if task_id not in phase_progress.task_progress:
                logger.warning(f"No tracking for task: {task_id}")
                return
            
            task_progress = phase_progress.task_progress[task_id]
            
            # Update task status
            old_status = task_progress.status
            task_progress.status = status
            
            if metadata:
                task_progress.metadata.update(metadata)
            
            # Handle status transitions
            if old_status != status:
                if status == BuildStatus.RUNNING and not task_progress.start_time:
                    task_progress.start_time = datetime.now()
                elif status in [BuildStatus.COMPLETED, BuildStatus.FAILED, BuildStatus.CANCELLED]:
                    task_progress.end_time = datetime.now()
                    if task_progress.start_time:
                        task_progress.actual_duration = (
                            task_progress.end_time - task_progress.start_time
                        ).total_seconds()
                        self._record_task_duration(task_id, task_progress.actual_duration)
            
            # Update progress percentage
            if progress_percent is not None:
                task_progress.progress_percent = min(100.0, max(0.0, progress_percent))
            
            # Update counters
            if status == BuildStatus.COMPLETED:
                if old_status != BuildStatus.COMPLETED:
                    phase_progress.tasks_completed += 1
            elif old_status == BuildStatus.COMPLETED and status != BuildStatus.COMPLETED:
                phase_progress.tasks_completed = max(0, phase_progress.tasks_completed - 1)
            
            # Update phase and project progress
            self._update_project_progress(execution_id)
            
            logger.debug(f"Updated task {task_id} progress: {task_progress.progress_percent:.1f}%")
    
    def calculate_eta(
        self,
        execution_id: str,
        method: str = "auto"
    ) -> Optional[ETACalculation]:
        """Calculate estimated time of arrival."""
        with self.lock:
            if execution_id not in self.project_progress:
                return None
            
            project_progress = self.project_progress[execution_id]
            
            if project_progress.progress_percent >= 100.0:
                return ETACalculation(
                    eta_seconds=0.0,
                    eta_datetime=datetime.now(),
                    confidence=1.0,
                    method="completed"
                )
            
            # Choose calculation method
            if method == "auto":
                method = self._select_best_eta_method(project_progress)
            
            if method == "linear":
                return self._calculate_linear_eta(project_progress)
            elif method == "historical":
                return self._calculate_historical_eta(project_progress)
            elif method == "velocity":
                return self._calculate_velocity_eta(project_progress)
            elif method == "hybrid":
                return self._calculate_hybrid_eta(project_progress)
            else:
                return self._calculate_linear_eta(project_progress)
    
    def get_project_progress(self, execution_id: str) -> Optional[ProjectProgress]:
        """Get current project progress."""
        with self.lock:
            return self.project_progress.get(execution_id)
    
    def get_throughput_metrics(self, execution_id: str) -> Dict[str, float]:
        """Get throughput metrics."""
        with self.lock:
            project_progress = self.project_progress.get(execution_id)
            if not project_progress:
                return {}
            
            # Calculate tasks per minute
            if project_progress.start_time:
                elapsed = (datetime.now() - project_progress.start_time).total_seconds() / 60
                total_completed_tasks = sum(
                    phase.tasks_completed for phase in project_progress.phase_progress.values()
                )
                tasks_per_minute = total_completed_tasks / elapsed if elapsed > 0 else 0.0
            else:
                tasks_per_minute = 0.0
            
            return {
                "tasks_per_minute": tasks_per_minute,
                "phases_per_hour": self._calculate_phases_per_hour(project_progress),
                "average_task_duration": self._get_average_task_duration(),
                "average_phase_duration": self._get_average_phase_duration()
            }
    
    def record_performance_sample(
        self,
        execution_id: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Record a performance sample for ETA calculation."""
        with self.lock:
            if execution_id not in self.project_progress:
                return
            
            project_progress = self.project_progress[execution_id]
            timestamp = timestamp or datetime.now()
            
            self.performance_samples.append((timestamp, project_progress.progress_percent))
            
            # Keep only recent samples
            if len(self.performance_samples) > self.eta_window_size * 2:
                self.performance_samples = self.performance_samples[-self.eta_window_size:]
    
    def _estimate_total_duration(self, project: Project) -> float:
        """Estimate total project duration."""
        total_estimate = 0.0
        
        for phase in project.phases:
            phase_estimate = self._estimate_phase_duration(phase)
            total_estimate += phase_estimate
        
        # Add buffer for overhead
        return total_estimate * 1.2
    
    def _estimate_phase_duration(self, phase: BuildPhase) -> float:
        """Estimate phase duration based on tasks."""
        # Get historical data if available
        historical_avg = self._get_historical_phase_duration(phase.id)
        if historical_avg:
            return historical_avg
        
        # Estimate based on task complexity
        base_duration = 60.0  # 1 minute base
        complexity_multiplier = phase.metadata.get("complexity", 1)
        task_count = len(phase.tasks)
        
        return base_duration * complexity_multiplier * (1 + task_count * 0.5)
    
    def _estimate_task_duration(self, task: BuildTask) -> float:
        """Estimate task duration."""
        # Get historical data if available
        historical_avg = self._get_historical_task_duration(task.id)
        if historical_avg:
            return historical_avg
        
        # Estimate based on task type and complexity
        base_durations = {
            "code": 30.0,
            "file": 10.0,
            "test": 45.0,
            "research": 60.0,
            "validation": 20.0
        }
        
        base = base_durations.get(task.type, 30.0)
        complexity = task.metadata.get("complexity", 1)
        
        return base * complexity
    
    def _calculate_phase_progress(self, phase_progress: PhaseProgress) -> float:
        """Calculate phase progress based on task completion."""
        if phase_progress.tasks_total == 0:
            return 100.0 if phase_progress.status == BuildStatus.COMPLETED else 0.0
        
        total_progress = sum(
            task.progress_percent for task in phase_progress.task_progress.values()
        )
        
        return total_progress / phase_progress.tasks_total
    
    def _update_project_progress(self, execution_id: str) -> None:
        """Update overall project progress."""
        project_progress = self.project_progress[execution_id]
        
        # Update phases completed count
        project_progress.phases_completed = sum(
            1 for phase in project_progress.phase_progress.values()
            if phase.status == BuildStatus.COMPLETED
        )
        
        # Calculate overall progress
        if project_progress.phases_total == 0:
            project_progress.progress_percent = 100.0
        else:
            total_progress = sum(
                phase.progress_percent for phase in project_progress.phase_progress.values()
            )
            project_progress.progress_percent = total_progress / project_progress.phases_total
        
        # Update throughput
        project_progress.throughput_tasks_per_minute = self._calculate_current_throughput(
            project_progress
        )
        
        # Calculate remaining duration
        eta = self.calculate_eta(execution_id)
        if eta:
            project_progress.estimated_remaining_duration = eta.eta_seconds
        
        # Record performance sample
        self.record_performance_sample(execution_id)
    
    def _calculate_linear_eta(self, project_progress: ProjectProgress) -> ETACalculation:
        """Calculate ETA using linear progression."""
        if not project_progress.start_time or project_progress.progress_percent <= 0:
            return ETACalculation(
                eta_seconds=0.0,
                eta_datetime=datetime.now(),
                confidence=0.0,
                method="linear"
            )
        
        elapsed = (datetime.now() - project_progress.start_time).total_seconds()
        rate = project_progress.progress_percent / elapsed if elapsed > 0 else 0
        
        if rate <= 0:
            return ETACalculation(
                eta_seconds=float('inf'),
                eta_datetime=datetime.max,
                confidence=0.0,
                method="linear"
            )
        
        remaining_percent = 100.0 - project_progress.progress_percent
        eta_seconds = remaining_percent / rate
        
        confidence = min(0.9, project_progress.progress_percent / 100.0)
        
        return ETACalculation(
            eta_seconds=eta_seconds,
            eta_datetime=datetime.now() + timedelta(seconds=eta_seconds),
            confidence=confidence,
            method="linear",
            factors={"rate": rate, "elapsed": elapsed}
        )
    
    def _calculate_velocity_eta(self, project_progress: ProjectProgress) -> ETACalculation:
        """Calculate ETA using recent velocity."""
        if len(self.performance_samples) < self.min_samples_for_eta:
            return self._calculate_linear_eta(project_progress)
        
        # Get recent samples
        recent_samples = self.performance_samples[-self.eta_window_size:]
        
        if len(recent_samples) < 2:
            return self._calculate_linear_eta(project_progress)
        
        # Calculate velocity (progress per second)
        time_diffs = []
        progress_diffs = []
        
        for i in range(1, len(recent_samples)):
            time_diff = (recent_samples[i][0] - recent_samples[i-1][0]).total_seconds()
            progress_diff = recent_samples[i][1] - recent_samples[i-1][1]
            
            if time_diff > 0:
                time_diffs.append(time_diff)
                progress_diffs.append(progress_diff)
        
        if not time_diffs:
            return self._calculate_linear_eta(project_progress)
        
        # Calculate average velocity
        total_time = sum(time_diffs)
        total_progress = sum(progress_diffs)
        velocity = total_progress / total_time if total_time > 0 else 0
        
        if velocity <= 0:
            return ETACalculation(
                eta_seconds=float('inf'),
                eta_datetime=datetime.max,
                confidence=0.0,
                method="velocity"
            )
        
        remaining_percent = 100.0 - project_progress.progress_percent
        eta_seconds = remaining_percent / velocity
        
        # Calculate confidence based on velocity consistency
        velocity_variance = statistics.variance(
            [p / t for p, t in zip(progress_diffs, time_diffs)]
        ) if len(progress_diffs) > 1 else 0
        
        confidence = max(0.1, min(0.95, 1.0 / (1.0 + velocity_variance)))
        
        return ETACalculation(
            eta_seconds=eta_seconds,
            eta_datetime=datetime.now() + timedelta(seconds=eta_seconds),
            confidence=confidence,
            method="velocity",
            factors={"velocity": velocity, "variance": velocity_variance}
        )
    
    def _calculate_historical_eta(self, project_progress: ProjectProgress) -> ETACalculation:
        """Calculate ETA using historical data."""
        # Use estimated total duration if available
        if project_progress.estimated_total_duration:
            elapsed = 0.0
            if project_progress.start_time:
                elapsed = (datetime.now() - project_progress.start_time).total_seconds()
            
            remaining = project_progress.estimated_total_duration - elapsed
            remaining = max(0, remaining)
            
            confidence = 0.7  # Medium confidence for historical estimates
            
            return ETACalculation(
                eta_seconds=remaining,
                eta_datetime=datetime.now() + timedelta(seconds=remaining),
                confidence=confidence,
                method="historical",
                factors={"estimated_total": project_progress.estimated_total_duration}
            )
        
        return self._calculate_linear_eta(project_progress)
    
    def _calculate_hybrid_eta(self, project_progress: ProjectProgress) -> ETACalculation:
        """Calculate ETA using hybrid approach."""
        linear_eta = self._calculate_linear_eta(project_progress)
        velocity_eta = self._calculate_velocity_eta(project_progress)
        historical_eta = self._calculate_historical_eta(project_progress)
        
        # Weight the estimates
        weights = {
            "linear": 0.3,
            "velocity": 0.5,
            "historical": 0.2
        }
        
        # Adjust weights based on confidence
        total_confidence = (
            linear_eta.confidence * weights["linear"] +
            velocity_eta.confidence * weights["velocity"] +
            historical_eta.confidence * weights["historical"]
        )
        
        if total_confidence > 0:
            weighted_eta = (
                linear_eta.eta_seconds * linear_eta.confidence * weights["linear"] +
                velocity_eta.eta_seconds * velocity_eta.confidence * weights["velocity"] +
                historical_eta.eta_seconds * historical_eta.confidence * weights["historical"]
            ) / total_confidence
        else:
            weighted_eta = linear_eta.eta_seconds
        
        return ETACalculation(
            eta_seconds=weighted_eta,
            eta_datetime=datetime.now() + timedelta(seconds=weighted_eta),
            confidence=min(0.95, total_confidence),
            method="hybrid",
            factors={
                "linear": linear_eta.eta_seconds,
                "velocity": velocity_eta.eta_seconds,
                "historical": historical_eta.eta_seconds
            }
        )
    
    def _select_best_eta_method(self, project_progress: ProjectProgress) -> str:
        """Select the best ETA calculation method."""
        # Use velocity if we have enough samples
        if len(self.performance_samples) >= self.min_samples_for_eta:
            return "velocity"
        
        # Use historical if we have estimates
        if project_progress.estimated_total_duration:
            return "historical"
        
        # Default to linear
        return "linear"
    
    def _record_task_duration(self, task_id: str, duration: float) -> None:
        """Record task duration for historical analysis."""
        if task_id not in self.historical_data:
            self.historical_data[task_id] = []
        
        self.historical_data[task_id].append(duration)
        self.performance_history["task_duration"].append(duration)
        
        # Keep only recent history
        if len(self.historical_data[task_id]) > 10:
            self.historical_data[task_id] = self.historical_data[task_id][-10:]
    
    def _record_phase_duration(self, phase_id: str, duration: float) -> None:
        """Record phase duration for historical analysis."""
        phase_key = f"phase_{phase_id}"
        if phase_key not in self.historical_data:
            self.historical_data[phase_key] = []
        
        self.historical_data[phase_key].append(duration)
        self.performance_history["phase_duration"].append(duration)
        
        # Keep only recent history
        if len(self.historical_data[phase_key]) > 5:
            self.historical_data[phase_key] = self.historical_data[phase_key][-5:]
    
    def _get_historical_task_duration(self, task_id: str) -> Optional[float]:
        """Get average historical task duration."""
        if task_id in self.historical_data and self.historical_data[task_id]:
            return statistics.mean(self.historical_data[task_id])
        return None
    
    def _get_historical_phase_duration(self, phase_id: str) -> Optional[float]:
        """Get average historical phase duration."""
        phase_key = f"phase_{phase_id}"
        if phase_key in self.historical_data and self.historical_data[phase_key]:
            return statistics.mean(self.historical_data[phase_key])
        return None
    
    def _calculate_current_throughput(self, project_progress: ProjectProgress) -> float:
        """Calculate current tasks per minute."""
        if not project_progress.start_time:
            return 0.0
        
        elapsed_minutes = (datetime.now() - project_progress.start_time).total_seconds() / 60
        if elapsed_minutes <= 0:
            return 0.0
        
        total_completed_tasks = sum(
            phase.tasks_completed for phase in project_progress.phase_progress.values()
        )
        
        return total_completed_tasks / elapsed_minutes
    
    def _calculate_phases_per_hour(self, project_progress: ProjectProgress) -> float:
        """Calculate phases per hour."""
        if not project_progress.start_time:
            return 0.0
        
        elapsed_hours = (datetime.now() - project_progress.start_time).total_seconds() / 3600
        if elapsed_hours <= 0:
            return 0.0
        
        return project_progress.phases_completed / elapsed_hours
    
    def _get_average_task_duration(self) -> float:
        """Get average task duration from history."""
        if self.performance_history["task_duration"]:
            return statistics.mean(self.performance_history["task_duration"])
        return 0.0
    
    def _get_average_phase_duration(self) -> float:
        """Get average phase duration from history."""
        if self.performance_history["phase_duration"]:
            return statistics.mean(self.performance_history["phase_duration"])
        return 0.0