"""Monitoring models for real-time tracking."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import json

from .base import SerializableModel, TimestampedModel
from ..exceptions import MonitoringError


class LogLevel(Enum):
    """Log severity levels."""
    
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    
    def get_priority(self) -> int:
        """Get numeric priority (higher = more severe)."""
        priorities = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50
        }
        return priorities.get(self, 0)


class MetricType(Enum):
    """Types of metrics to track."""
    
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"
    PERCENTAGE = "percentage"


class AlertStatus(Enum):
    """Alert status levels."""
    
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class LogEntry(SerializableModel, TimestampedModel):
    """Structured log entry."""
    
    # All fields must have defaults due to TimestampedModel inheritance
    level: LogLevel = LogLevel.INFO
    message: str = ""
    source: str = ""
    
    # Context
    phase: Optional[str] = None
    task: Optional[str] = None
    component: Optional[str] = None
    
    # Additional data
    data: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Error information
    error_type: Optional[str] = None
    error_code: Optional[str] = None
    traceback: Optional[str] = None
    
    def validate(self) -> None:
        """Validate log entry."""
        if not self.message:
            raise MonitoringError("Log entry must have a message")
        
        if not self.source:
            raise MonitoringError("Log entry must have a source")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data["level"] = self.level.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogEntry":
        """Create from dictionary."""
        if "level" in data and isinstance(data["level"], str):
            data["level"] = LogLevel(data["level"])
        return super().from_dict(data)
    
    def format(self, include_data: bool = False) -> str:
        """Format log entry for display."""
        parts = [
            self.created_at.strftime("%H:%M:%S.%f")[:-3],
            f"[{self.level.value.upper()}]",
            f"[{self.source}]"
        ]
        
        if self.component:
            parts.append(f"[{self.component}]")
        
        if self.phase:
            parts.append(f"<{self.phase}>")
        
        if self.task:
            parts.append(f"({self.task})")
        
        parts.append(self.message)
        
        if include_data and self.data:
            parts.append(json.dumps(self.data, indent=2))
        
        return " ".join(parts)


@dataclass
class Metric:
    """Performance or business metric."""
    
    name: str
    metric_type: MetricType
    value: float = 0.0
    unit: str = ""
    
    # Metadata
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Time window
    timestamp: datetime = field(default_factory=datetime.utcnow)
    window: Optional[timedelta] = None
    
    # Thresholds
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    target_value: Optional[float] = None
    
    def validate(self) -> None:
        """Validate metric."""
        if not self.name:
            raise MonitoringError("Metric must have a name")
        
        if self.min_threshold is not None and self.max_threshold is not None:
            if self.min_threshold >= self.max_threshold:
                raise MonitoringError("Min threshold must be less than max threshold")
    
    def is_within_bounds(self) -> bool:
        """Check if metric is within defined thresholds."""
        if self.min_threshold is not None and self.value < self.min_threshold:
            return False
        if self.max_threshold is not None and self.value > self.max_threshold:
            return False
        return True
    
    def get_health_score(self) -> float:
        """Calculate health score (0-1) based on thresholds."""
        if self.target_value is not None:
            # Distance from target
            distance = abs(self.value - self.target_value)
            max_distance = max(
                abs(self.min_threshold - self.target_value) if self.min_threshold else 0,
                abs(self.max_threshold - self.target_value) if self.max_threshold else 0
            )
            if max_distance > 0:
                return 1 - (distance / max_distance)
        
        # Within bounds check
        return 1.0 if self.is_within_bounds() else 0.0


@dataclass
class ProgressTracker(SerializableModel):
    """Track progress of operations."""
    
    operation: str
    total_steps: int
    current_step: int = 0
    
    # Progress details
    current_phase: Optional[str] = None
    current_task: Optional[str] = None
    status_message: str = ""
    
    # Time tracking
    started_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Step history
    step_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance
    steps_per_second: float = 0.0
    estimated_completion: Optional[datetime] = None
    
    def validate(self) -> None:
        """Validate progress tracker."""
        if not self.operation:
            raise MonitoringError("Progress tracker must have an operation name")
        
        if self.total_steps < 1:
            raise MonitoringError("Total steps must be at least 1")
        
        if self.current_step < 0 or self.current_step > self.total_steps:
            raise MonitoringError("Current step must be between 0 and total steps")
    
    def update(
        self,
        step: Optional[int] = None,
        phase: Optional[str] = None,
        task: Optional[str] = None,
        message: Optional[str] = None
    ) -> None:
        """Update progress."""
        if step is not None:
            self.current_step = min(step, self.total_steps)
        
        if phase is not None:
            self.current_phase = phase
        
        if task is not None:
            self.current_task = task
        
        if message is not None:
            self.status_message = message
        
        self.updated_at = datetime.utcnow()
        
        # Record in history
        self.step_history.append({
            "step": self.current_step,
            "phase": self.current_phase,
            "task": self.current_task,
            "message": self.status_message,
            "timestamp": self.updated_at.isoformat()
        })
        
        # Calculate performance
        elapsed = (self.updated_at - self.started_at).total_seconds()
        if elapsed > 0 and self.current_step > 0:
            self.steps_per_second = self.current_step / elapsed
            
            # Estimate completion
            if self.steps_per_second > 0:
                remaining_steps = self.total_steps - self.current_step
                remaining_seconds = remaining_steps / self.steps_per_second
                self.estimated_completion = self.updated_at + timedelta(seconds=remaining_seconds)
    
    def complete(self) -> None:
        """Mark operation as complete."""
        self.current_step = self.total_steps
        self.completed_at = datetime.utcnow()
        self.status_message = "Completed"
        self.update()
    
    def get_progress_percentage(self) -> float:
        """Get progress as percentage."""
        return (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0
    
    def get_elapsed_time(self) -> timedelta:
        """Get elapsed time."""
        end_time = self.completed_at or datetime.utcnow()
        return end_time - self.started_at
    
    def get_eta(self) -> Optional[timedelta]:
        """Get estimated time to completion."""
        if self.completed_at:
            return timedelta()
        
        if self.estimated_completion:
            remaining = self.estimated_completion - datetime.utcnow()
            return remaining if remaining > timedelta() else timedelta()
        
        return None
    
    def format_status(self) -> str:
        """Format current status for display."""
        parts = [
            f"{self.operation}:",
            f"{self.get_progress_percentage():.1f}%",
            f"({self.current_step}/{self.total_steps})"
        ]
        
        if self.current_phase:
            parts.append(f"[{self.current_phase}]")
        
        if self.current_task:
            parts.append(f"- {self.current_task}")
        
        if self.status_message:
            parts.append(f"- {self.status_message}")
        
        eta = self.get_eta()
        if eta:
            parts.append(f"(ETA: {eta.total_seconds():.0f}s)")
        
        return " ".join(parts)


@dataclass
class Alert:
    """System alert or notification."""
    
    alert_id: str
    title: str
    message: str
    severity: LogLevel
    source: str
    
    # Alert metadata
    alert_type: str = "threshold"
    metric_name: Optional[str] = None
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    
    # Status
    status: AlertStatus = AlertStatus.ACTIVE
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Actions
    suggested_actions: List[str] = field(default_factory=list)
    auto_resolve: bool = True
    auto_resolve_timeout: timedelta = timedelta(hours=1)
    
    # Notification
    notify_channels: List[str] = field(default_factory=list)
    notified: bool = False
    
    def acknowledge(self, user: str = "system") -> None:
        """Acknowledge alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()
    
    def resolve(self, resolution: str = "") -> None:
        """Resolve alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        if resolution:
            self.message += f"\nResolution: {resolution}"
    
    def suppress(self, duration: timedelta) -> None:
        """Suppress alert for duration."""
        self.status = AlertStatus.SUPPRESSED
        self.auto_resolve_timeout = duration
    
    def should_auto_resolve(self) -> bool:
        """Check if alert should auto-resolve."""
        if not self.auto_resolve or self.status != AlertStatus.ACTIVE:
            return False
        
        elapsed = datetime.utcnow() - self.triggered_at
        return elapsed >= self.auto_resolve_timeout


@dataclass
class MonitoringDashboard(SerializableModel):
    """Real-time monitoring dashboard."""
    
    name: str
    refresh_interval: timedelta = timedelta(seconds=1)
    
    # Data streams
    log_buffer: deque = field(default_factory=lambda: deque(maxlen=1000))
    metrics: Dict[str, Metric] = field(default_factory=dict)
    progress_trackers: Dict[str, ProgressTracker] = field(default_factory=dict)
    alerts: List[Alert] = field(default_factory=list)
    
    # Filters
    log_level_filter: Optional[LogLevel] = None
    component_filter: Optional[str] = None
    phase_filter: Optional[str] = None
    
    # Display settings
    show_logs: bool = True
    show_metrics: bool = True
    show_progress: bool = True
    show_alerts: bool = True
    max_log_lines: int = 50
    
    # Update callbacks
    update_callbacks: List[Callable] = field(default_factory=list)
    
    # Statistics
    total_logs: int = 0
    error_count: int = 0
    warning_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def validate(self) -> None:
        """Validate dashboard configuration."""
        if not self.name:
            raise MonitoringError("Dashboard must have a name")
        
        if self.refresh_interval.total_seconds() < 0.1:
            raise MonitoringError("Refresh interval must be at least 0.1 seconds")
    
    def add_log(self, log_entry: LogEntry) -> None:
        """Add log entry to dashboard."""
        log_entry.validate()
        
        # Apply filters
        if self.log_level_filter and log_entry.level.get_priority() < self.log_level_filter.get_priority():
            return
        
        if self.component_filter and log_entry.component != self.component_filter:
            return
        
        if self.phase_filter and log_entry.phase != self.phase_filter:
            return
        
        # Add to buffer
        self.log_buffer.append(log_entry)
        self.total_logs += 1
        
        # Update counters
        if log_entry.level == LogLevel.ERROR:
            self.error_count += 1
        elif log_entry.level == LogLevel.WARNING:
            self.warning_count += 1
        
        self.last_updated = datetime.utcnow()
        self._trigger_update()
    
    def update_metric(self, metric: Metric) -> None:
        """Update or add metric."""
        metric.validate()
        self.metrics[metric.name] = metric
        
        # Check for threshold violations
        if not metric.is_within_bounds():
            self._create_metric_alert(metric)
        
        self.last_updated = datetime.utcnow()
        self._trigger_update()
    
    def update_progress(self, tracker_id: str, tracker: ProgressTracker) -> None:
        """Update progress tracker."""
        tracker.validate()
        self.progress_trackers[tracker_id] = tracker
        self.last_updated = datetime.utcnow()
        self._trigger_update()
    
    def add_alert(self, alert: Alert) -> None:
        """Add new alert."""
        self.alerts.append(alert)
        
        # Auto-resolve old alerts
        self._check_auto_resolve()
        
        self.last_updated = datetime.utcnow()
        self._trigger_update()
    
    def _create_metric_alert(self, metric: Metric) -> None:
        """Create alert for metric threshold violation."""
        alert = Alert(
            alert_id=f"metric_{metric.name}_{datetime.utcnow().timestamp()}",
            title=f"Metric {metric.name} out of bounds",
            message=f"{metric.name} = {metric.value} {metric.unit}",
            severity=LogLevel.WARNING,
            source="metric_monitor",
            alert_type="metric_threshold",
            metric_name=metric.name,
            actual_value=metric.value
        )
        
        if metric.min_threshold is not None and metric.value < metric.min_threshold:
            alert.threshold_value = metric.min_threshold
            alert.message += f" (below minimum {metric.min_threshold})"
        elif metric.max_threshold is not None and metric.value > metric.max_threshold:
            alert.threshold_value = metric.max_threshold
            alert.message += f" (above maximum {metric.max_threshold})"
        
        self.add_alert(alert)
    
    def _check_auto_resolve(self) -> None:
        """Check and resolve alerts that should auto-resolve."""
        for alert in self.alerts:
            if alert.should_auto_resolve():
                alert.resolve("Auto-resolved after timeout")
    
    def _trigger_update(self) -> None:
        """Trigger update callbacks."""
        for callback in self.update_callbacks:
            try:
                callback(self)
            except Exception:
                # Don't let callback errors stop monitoring
                pass
    
    def get_recent_logs(self, limit: Optional[int] = None) -> List[LogEntry]:
        """Get recent log entries."""
        limit = limit or self.max_log_lines
        return list(self.log_buffer)[-limit:]
    
    def get_active_alerts(self) -> List[Alert]:
        """Get active alerts."""
        return [
            alert for alert in self.alerts
            if alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]
        ]
    
    def get_metrics_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all metrics."""
        return {
            name: {
                "value": metric.value,
                "unit": metric.unit,
                "health": metric.get_health_score(),
                "in_bounds": metric.is_within_bounds(),
                "type": metric.metric_type.value
            }
            for name, metric in self.metrics.items()
        }
    
    def get_overall_health(self) -> float:
        """Calculate overall system health (0-1)."""
        factors = []
        
        # Factor in metrics health
        if self.metrics:
            metric_health = sum(m.get_health_score() for m in self.metrics.values()) / len(self.metrics)
            factors.append(metric_health)
        
        # Factor in error rate
        if self.total_logs > 0:
            error_rate = self.error_count / self.total_logs
            factors.append(1 - min(error_rate * 10, 1))  # 10% errors = 0 health
        
        # Factor in active alerts
        active_alerts = len(self.get_active_alerts())
        alert_factor = 1 - min(active_alerts / 10, 1)  # 10+ alerts = 0 health
        factors.append(alert_factor)
        
        # Factor in progress
        if self.progress_trackers:
            avg_progress = sum(
                t.get_progress_percentage() for t in self.progress_trackers.values()
            ) / len(self.progress_trackers) / 100
            factors.append(avg_progress)
        
        return sum(factors) / len(factors) if factors else 1.0
    
    def format_summary(self) -> str:
        """Format dashboard summary."""
        health = self.get_overall_health()
        active_alerts = self.get_active_alerts()
        
        lines = [
            f"Dashboard: {self.name}",
            f"Health: {health:.0%} {'🟢' if health > 0.8 else '🟡' if health > 0.5 else '🔴'}",
            f"Logs: {self.total_logs} total, {self.error_count} errors, {self.warning_count} warnings",
            f"Alerts: {len(active_alerts)} active",
            f"Metrics: {len(self.metrics)}",
            f"Progress: {len(self.progress_trackers)} operations"
        ]
        
        return " | ".join(lines)