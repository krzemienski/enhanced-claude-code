"""Monitoring dashboard for real-time visualization."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import threading
import time

from .stream_parser import StreamParser, LogEntry, LogEventType
from .progress_tracker import ProgressTracker, ProjectProgress, ETACalculation
from .cost_monitor import CostMonitor, CostSummary
from .performance_monitor import PerformanceMonitor, SystemResources, PerformanceStats
from .error_tracker import ErrorTracker, ErrorStats
from .alert_manager import AlertManager, Alert, AlertSeverity

logger = logging.getLogger(__name__)


@dataclass
class DashboardConfig:
    """Dashboard configuration."""
    refresh_interval: float = 1.0  # seconds
    history_hours: int = 24
    max_log_entries: int = 1000
    enable_real_time: bool = True
    theme: str = "dark"  # dark, light
    layout: str = "default"  # default, compact, detailed


@dataclass
class DashboardMetrics:
    """Combined dashboard metrics."""
    timestamp: datetime
    project_progress: Optional[ProjectProgress] = None
    cost_summary: Optional[CostSummary] = None
    system_resources: Optional[SystemResources] = None
    error_stats: Optional[ErrorStats] = None
    active_alerts: List[Alert] = field(default_factory=list)
    recent_logs: List[LogEntry] = field(default_factory=list)
    throughput: Dict[str, float] = field(default_factory=dict)
    eta: Optional[ETACalculation] = None


class MonitoringDashboard:
    """Real-time monitoring dashboard."""
    
    def __init__(
        self,
        stream_parser: StreamParser,
        progress_tracker: ProgressTracker,
        cost_monitor: CostMonitor,
        performance_monitor: PerformanceMonitor,
        error_tracker: ErrorTracker,
        alert_manager: AlertManager,
        config: Optional[DashboardConfig] = None
    ):
        """Initialize the monitoring dashboard."""
        self.stream_parser = stream_parser
        self.progress_tracker = progress_tracker
        self.cost_monitor = cost_monitor
        self.performance_monitor = performance_monitor
        self.error_tracker = error_tracker
        self.alert_manager = alert_manager
        self.config = config or DashboardConfig()
        
        # Dashboard state
        self.current_metrics: Optional[DashboardMetrics] = None
        self.metrics_history: List[DashboardMetrics] = []
        self.lock = threading.RLock()
        
        # Update thread
        self.update_active = False
        self.update_thread: Optional[threading.Thread] = None
        
        # Current execution tracking
        self.current_execution_id: Optional[str] = None
        
        # Dashboard data
        self.log_buffer: List[LogEntry] = []
        self.performance_charts: Dict[str, List[Tuple[datetime, float]]] = {}
        self.cost_charts: List[Tuple[datetime, float]] = []
        
        logger.info("Monitoring Dashboard initialized")
    
    def start(self, execution_id: Optional[str] = None) -> None:
        """Start the dashboard updates."""
        with self.lock:
            if self.update_active:
                logger.warning("Dashboard already active")
                return
            
            self.current_execution_id = execution_id
            self.update_active = True
            self.update_thread = threading.Thread(
                target=self._update_loop,
                daemon=True
            )
            self.update_thread.start()
            
            logger.info("Dashboard started")
    
    def stop(self) -> None:
        """Stop the dashboard updates."""
        with self.lock:
            if not self.update_active:
                return
            
            self.update_active = False
            
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread.join(timeout=5.0)
            
            logger.info("Dashboard stopped")
    
    def set_execution_id(self, execution_id: str) -> None:
        """Set the current execution ID to track."""
        with self.lock:
            self.current_execution_id = execution_id
            logger.info(f"Dashboard tracking execution: {execution_id}")
    
    def get_current_metrics(self) -> Optional[DashboardMetrics]:
        """Get current dashboard metrics."""
        with self.lock:
            return self.current_metrics
    
    def get_metrics_history(self, hours: int = 1) -> List[DashboardMetrics]:
        """Get historical dashboard metrics."""
        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            return [
                metrics for metrics in self.metrics_history
                if metrics.timestamp >= cutoff
            ]
    
    def get_summary_data(self) -> Dict[str, Any]:
        """Get summary data for display."""
        with self.lock:
            if not self.current_metrics:
                return {}
            
            metrics = self.current_metrics
            summary = {
                "timestamp": metrics.timestamp.isoformat(),
                "execution_id": self.current_execution_id
            }
            
            # Project progress
            if metrics.project_progress:
                summary["progress"] = {
                    "overall_percent": metrics.project_progress.progress_percent,
                    "current_phase": metrics.project_progress.current_phase.value,
                    "phases_completed": metrics.project_progress.phases_completed,
                    "phases_total": metrics.project_progress.phases_total,
                    "status": metrics.project_progress.status.value if hasattr(metrics.project_progress.status, 'value') else str(metrics.project_progress.status)
                }
                
                if metrics.eta:
                    summary["progress"]["eta"] = {
                        "seconds": metrics.eta.eta_seconds,
                        "datetime": metrics.eta.eta_datetime.isoformat(),
                        "confidence": metrics.eta.confidence,
                        "method": metrics.eta.method
                    }
            
            # Cost information
            if metrics.cost_summary:
                summary["cost"] = {
                    "total": metrics.cost_summary.total_cost,
                    "currency": metrics.cost_summary.currency,
                    "categories": {
                        cat.value: amount for cat, amount in metrics.cost_summary.category_costs.items()
                    }
                }
            
            # System resources
            if metrics.system_resources:
                summary["system"] = {
                    "cpu_percent": metrics.system_resources.cpu_percent,
                    "memory_percent": metrics.system_resources.memory_percent,
                    "memory_available_gb": metrics.system_resources.memory_available,
                    "disk_usage_percent": metrics.system_resources.disk_usage_percent,
                    "disk_free_gb": metrics.system_resources.disk_free
                }
            
            # Error information
            if metrics.error_stats:
                summary["errors"] = {
                    "total": metrics.error_stats.total_errors,
                    "rate": metrics.error_stats.error_rate,
                    "by_severity": {
                        sev.value: count for sev, count in metrics.error_stats.errors_by_severity.items()
                    }
                }
            
            # Alerts
            summary["alerts"] = {
                "total": len(metrics.active_alerts),
                "by_severity": {}
            }
            
            for severity in AlertSeverity:
                count = sum(1 for alert in metrics.active_alerts if alert.severity == severity)
                summary["alerts"]["by_severity"][severity.value] = count
            
            # Throughput
            summary["throughput"] = metrics.throughput
            
            return summary
    
    def get_chart_data(self, chart_type: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get chart data for visualization."""
        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            if chart_type == "progress":
                return self._get_progress_chart_data(cutoff)
            elif chart_type == "cost":
                return self._get_cost_chart_data(cutoff)
            elif chart_type == "cpu":
                return self._get_performance_chart_data("cpu_usage", cutoff)
            elif chart_type == "memory":
                return self._get_performance_chart_data("memory_usage", cutoff)
            elif chart_type == "errors":
                return self._get_error_chart_data(cutoff)
            else:
                return []
    
    def get_recent_logs(self, count: int = 50) -> List[Dict[str, Any]]:
        """Get recent log entries."""
        with self.lock:
            recent_logs = self.log_buffer[-count:] if self.log_buffer else []
            
            return [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "level": entry.level.value,
                    "event_type": entry.event_type.value,
                    "message": entry.message,
                    "source": entry.source,
                    "execution_id": entry.execution_id,
                    "phase_id": entry.phase_id,
                    "task_id": entry.task_id
                }
                for entry in recent_logs
            ]
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts for display."""
        with self.lock:
            if not self.current_metrics:
                return []
            
            return [
                {
                    "id": alert.id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "acknowledged": alert.acknowledged,
                    "alert_type": alert.alert_type.value
                }
                for alert in self.current_metrics.active_alerts
            ]
    
    def export_dashboard_data(self) -> Dict[str, Any]:
        """Export complete dashboard data."""
        with self.lock:
            return {
                "config": {
                    "refresh_interval": self.config.refresh_interval,
                    "history_hours": self.config.history_hours,
                    "theme": self.config.theme,
                    "layout": self.config.layout
                },
                "current_metrics": self.get_summary_data(),
                "recent_logs": self.get_recent_logs(100),
                "active_alerts": self.get_active_alerts(),
                "charts": {
                    "progress": self.get_chart_data("progress", 2),
                    "cost": self.get_chart_data("cost", 2),
                    "cpu": self.get_chart_data("cpu", 2),
                    "memory": self.get_chart_data("memory", 2),
                    "errors": self.get_chart_data("errors", 2)
                },
                "export_timestamp": datetime.now().isoformat()
            }
    
    def _update_loop(self) -> None:
        """Main dashboard update loop."""
        logger.info("Dashboard update loop started")
        
        while self.update_active:
            try:
                # Collect current metrics
                metrics = self._collect_metrics()
                
                # Update dashboard state
                with self.lock:
                    self.current_metrics = metrics
                    self.metrics_history.append(metrics)
                    
                    # Cleanup old history
                    cutoff = datetime.now() - timedelta(hours=self.config.history_hours)
                    self.metrics_history = [
                        m for m in self.metrics_history
                        if m.timestamp >= cutoff
                    ]
                    
                    # Update chart data
                    self._update_chart_data(metrics)
                    
                    # Update log buffer
                    self._update_log_buffer()
                
                # Sleep until next update
                time.sleep(self.config.refresh_interval)
                
            except Exception as e:
                logger.error(f"Error in dashboard update loop: {e}")
                time.sleep(self.config.refresh_interval)
        
        logger.info("Dashboard update loop stopped")
    
    def _collect_metrics(self) -> DashboardMetrics:
        """Collect current metrics from all monitors."""
        timestamp = datetime.now()
        
        # Get project progress
        project_progress = None
        eta = None
        if self.current_execution_id:
            project_progress = self.progress_tracker.get_project_progress(
                self.current_execution_id
            )
            if project_progress:
                eta = self.progress_tracker.calculate_eta(self.current_execution_id)
        
        # Get cost summary
        cost_summary = self.cost_monitor.get_current_costs(self.current_execution_id)
        
        # Get system resources
        system_resources = self.performance_monitor.get_current_system_resources()
        
        # Get error stats
        error_stats = self.error_tracker.get_error_stats(
            hours=1,
            execution_id=self.current_execution_id
        )
        
        # Get active alerts
        active_alerts = self.alert_manager.get_active_alerts()
        
        # Get recent logs
        recent_logs = self.log_buffer[-50:] if self.log_buffer else []
        
        # Get throughput metrics
        throughput = {}
        if self.current_execution_id:
            throughput = self.progress_tracker.get_throughput_metrics(
                self.current_execution_id
            )
        
        return DashboardMetrics(
            timestamp=timestamp,
            project_progress=project_progress,
            cost_summary=cost_summary,
            system_resources=system_resources,
            error_stats=error_stats,
            active_alerts=active_alerts,
            recent_logs=recent_logs,
            throughput=throughput,
            eta=eta
        )
    
    def _update_chart_data(self, metrics: DashboardMetrics) -> None:
        """Update chart data with new metrics."""
        timestamp = metrics.timestamp
        
        # Progress chart
        if metrics.project_progress:
            if "progress" not in self.performance_charts:
                self.performance_charts["progress"] = []
            self.performance_charts["progress"].append(
                (timestamp, metrics.project_progress.progress_percent)
            )
        
        # Cost chart
        if metrics.cost_summary:
            self.cost_charts.append((timestamp, metrics.cost_summary.total_cost))
        
        # System resource charts
        if metrics.system_resources:
            for metric_name, value in [
                ("cpu_usage", metrics.system_resources.cpu_percent),
                ("memory_usage", metrics.system_resources.memory_percent),
                ("disk_usage", metrics.system_resources.disk_usage_percent)
            ]:
                if metric_name not in self.performance_charts:
                    self.performance_charts[metric_name] = []
                self.performance_charts[metric_name].append((timestamp, value))
        
        # Cleanup old chart data
        cutoff = timestamp - timedelta(hours=self.config.history_hours)
        for chart_name in self.performance_charts:
            self.performance_charts[chart_name] = [
                (ts, value) for ts, value in self.performance_charts[chart_name]
                if ts >= cutoff
            ]
        
        self.cost_charts = [
            (ts, value) for ts, value in self.cost_charts
            if ts >= cutoff
        ]
    
    def _update_log_buffer(self) -> None:
        """Update log buffer with recent entries."""
        # This would typically integrate with the stream parser
        # For now, we'll use the parser's statistics
        stats = self.stream_parser.get_stats()
        
        # Keep buffer size manageable
        if len(self.log_buffer) > self.config.max_log_entries:
            self.log_buffer = self.log_buffer[-self.config.max_log_entries//2:]
    
    def _get_progress_chart_data(self, cutoff: datetime) -> List[Dict[str, Any]]:
        """Get progress chart data."""
        if "progress" not in self.performance_charts:
            return []
        
        return [
            {
                "timestamp": ts.isoformat(),
                "value": value
            }
            for ts, value in self.performance_charts["progress"]
            if ts >= cutoff
        ]
    
    def _get_cost_chart_data(self, cutoff: datetime) -> List[Dict[str, Any]]:
        """Get cost chart data."""
        return [
            {
                "timestamp": ts.isoformat(),
                "value": value
            }
            for ts, value in self.cost_charts
            if ts >= cutoff
        ]
    
    def _get_performance_chart_data(
        self,
        metric_name: str,
        cutoff: datetime
    ) -> List[Dict[str, Any]]:
        """Get performance chart data."""
        if metric_name not in self.performance_charts:
            return []
        
        return [
            {
                "timestamp": ts.isoformat(),
                "value": value
            }
            for ts, value in self.performance_charts[metric_name]
            if ts >= cutoff
        ]
    
    def _get_error_chart_data(self, cutoff: datetime) -> List[Dict[str, Any]]:
        """Get error trend chart data."""
        # Get error trend from error tracker
        error_trend = self.error_tracker.get_error_trend(
            hours=int((datetime.now() - cutoff).total_seconds() / 3600),
            bucket_minutes=10
        )
        
        return [
            {
                "timestamp": ts.isoformat(),
                "value": count
            }
            for ts, count in error_trend
            if ts >= cutoff
        ]


class DashboardRenderer:
    """Renders dashboard data for different output formats."""
    
    def __init__(self, dashboard: MonitoringDashboard):
        """Initialize the dashboard renderer."""
        self.dashboard = dashboard
    
    def render_text_summary(self) -> str:
        """Render a text summary of the dashboard."""
        summary = self.dashboard.get_summary_data()
        
        if not summary:
            return "No dashboard data available"
        
        lines = []
        lines.append("=== Monitoring Dashboard ===")
        lines.append(f"Timestamp: {summary.get('timestamp', 'Unknown')}")
        
        if "progress" in summary:
            progress = summary["progress"]
            lines.append(f"\n--- Project Progress ---")
            lines.append(f"Overall: {progress.get('overall_percent', 0):.1f}%")
            lines.append(f"Phase: {progress.get('current_phase', 'Unknown')}")
            lines.append(f"Phases: {progress.get('phases_completed', 0)}/{progress.get('phases_total', 0)}")
            lines.append(f"Status: {progress.get('status', 'Unknown')}")
            
            if "eta" in progress:
                eta = progress["eta"]
                lines.append(f"ETA: {eta.get('seconds', 0):.0f}s ({eta.get('confidence', 0):.1%} confidence)")
        
        if "cost" in summary:
            cost = summary["cost"]
            lines.append(f"\n--- Cost Information ---")
            lines.append(f"Total: ${cost.get('total', 0):.4f} {cost.get('currency', 'USD')}")
        
        if "system" in summary:
            system = summary["system"]
            lines.append(f"\n--- System Resources ---")
            lines.append(f"CPU: {system.get('cpu_percent', 0):.1f}%")
            lines.append(f"Memory: {system.get('memory_percent', 0):.1f}% ({system.get('memory_available_gb', 0):.1f}GB free)")
            lines.append(f"Disk: {system.get('disk_usage_percent', 0):.1f}% ({system.get('disk_free_gb', 0):.1f}GB free)")
        
        if "errors" in summary:
            errors = summary["errors"]
            lines.append(f"\n--- Error Information ---")
            lines.append(f"Total: {errors.get('total', 0)} (Rate: {errors.get('rate', 0):.2f}/min)")
        
        if "alerts" in summary:
            alerts = summary["alerts"]
            lines.append(f"\n--- Active Alerts ---")
            lines.append(f"Total: {alerts.get('total', 0)}")
        
        return "\n".join(lines)
    
    def render_json(self) -> str:
        """Render dashboard data as JSON."""
        return json.dumps(self.dashboard.export_dashboard_data(), indent=2)
    
    def render_compact_status(self) -> str:
        """Render a compact status line."""
        summary = self.dashboard.get_summary_data()
        
        if not summary:
            return "Dashboard: No data"
        
        parts = []
        
        if "progress" in summary:
            progress = summary["progress"]
            parts.append(f"Progress: {progress.get('overall_percent', 0):.1f}%")
        
        if "cost" in summary:
            cost = summary["cost"]
            parts.append(f"Cost: ${cost.get('total', 0):.4f}")
        
        if "system" in summary:
            system = summary["system"]
            parts.append(f"CPU: {system.get('cpu_percent', 0):.0f}%")
            parts.append(f"Mem: {system.get('memory_percent', 0):.0f}%")
        
        if "alerts" in summary:
            alerts = summary["alerts"]
            total_alerts = alerts.get('total', 0)
            if total_alerts > 0:
                parts.append(f"Alerts: {total_alerts}")
        
        return " | ".join(parts)