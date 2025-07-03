"""Performance monitoring and metrics collection."""

import logging
import psutil
import time
import threading
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics."""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    DISK_IO = "disk_io"
    EXECUTION_TIME = "execution_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    API_LATENCY = "api_latency"
    QUEUE_SIZE = "queue_size"
    CUSTOM = "custom"


class AlertThresholdType(Enum):
    """Types of alert thresholds."""
    ABSOLUTE = "absolute"
    PERCENTAGE = "percentage"
    RATE_OF_CHANGE = "rate_of_change"
    STANDARD_DEVIATION = "standard_deviation"


@dataclass
class MetricSample:
    """Individual metric sample."""
    timestamp: datetime
    metric_type: MetricType
    value: float
    unit: str
    source: str = ""
    execution_id: Optional[str] = None
    phase_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricThreshold:
    """Performance threshold configuration."""
    metric_type: MetricType
    threshold_type: AlertThresholdType
    warning_value: float
    critical_value: float
    unit: str
    enabled: bool = True
    cooldown_seconds: int = 300  # 5 minutes


@dataclass
class PerformanceAlert:
    """Performance alert."""
    timestamp: datetime
    metric_type: MetricType
    current_value: float
    threshold_value: float
    severity: str  # warning, critical
    message: str
    source: str = ""
    execution_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemResources:
    """Current system resource usage."""
    cpu_percent: float
    memory_percent: float
    memory_available: float
    disk_usage_percent: float
    disk_free: float
    network_sent: float
    network_recv: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceStats:
    """Performance statistics."""
    metric_type: MetricType
    count: int
    min_value: float
    max_value: float
    mean_value: float
    median_value: float
    std_deviation: float
    percentile_95: float
    percentile_99: float
    unit: str
    period_start: datetime
    period_end: datetime


class PerformanceMonitor:
    """Monitors system and application performance metrics."""
    
    def __init__(self, sample_interval: float = 1.0):
        """Initialize the performance monitor."""
        self.sample_interval = sample_interval
        self.samples: List[MetricSample] = []
        self.alerts: List[PerformanceAlert] = []
        self.thresholds: Dict[MetricType, MetricThreshold] = {}
        self.lock = threading.RLock()
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Resource tracking
        self.last_network_io = psutil.net_io_counters()
        self.last_disk_io = psutil.disk_io_counters()
        self.last_sample_time = time.time()
        
        # Custom metrics
        self.custom_metrics: Dict[str, Callable[[], float]] = {}
        
        # Alert state tracking
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Default thresholds
        self._setup_default_thresholds()
        
        logger.info("Performance Monitor initialized")
    
    def start_monitoring(self) -> None:
        """Start continuous performance monitoring."""
        with self.lock:
            if self.monitoring_active:
                logger.warning("Performance monitoring already active")
                return
            
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitor_thread.start()
            
            logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        with self.lock:
            if not self.monitoring_active:
                return
            
            self.monitoring_active = False
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5.0)
            
            logger.info("Performance monitoring stopped")
    
    def add_threshold(self, threshold: MetricThreshold) -> None:
        """Add or update a performance threshold."""
        with self.lock:
            self.thresholds[threshold.metric_type] = threshold
            logger.info(f"Added threshold for {threshold.metric_type.value}")
    
    def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        unit: str,
        source: str = "",
        execution_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MetricSample:
        """Record a custom metric sample."""
        with self.lock:
            sample = MetricSample(
                timestamp=datetime.now(),
                metric_type=metric_type,
                value=value,
                unit=unit,
                source=source,
                execution_id=execution_id,
                phase_id=phase_id,
                task_id=task_id,
                metadata=metadata or {}
            )
            
            self.samples.append(sample)
            self._check_thresholds(sample)
            self._cleanup_old_samples()
            
            logger.debug(f"Recorded metric: {metric_type.value} = {value} {unit}")
            
            return sample
    
    def record_execution_time(
        self,
        operation: str,
        duration_seconds: float,
        execution_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> MetricSample:
        """Record execution time metric."""
        return self.record_metric(
            metric_type=MetricType.EXECUTION_TIME,
            value=duration_seconds,
            unit="seconds",
            source=operation,
            execution_id=execution_id,
            phase_id=phase_id,
            task_id=task_id,
            metadata={"operation": operation}
        )
    
    def record_api_latency(
        self,
        service: str,
        latency_ms: float,
        execution_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MetricSample:
        """Record API latency metric."""
        return self.record_metric(
            metric_type=MetricType.API_LATENCY,
            value=latency_ms,
            unit="milliseconds",
            source=service,
            execution_id=execution_id,
            metadata={**(metadata or {}), "service": service}
        )
    
    def record_throughput(
        self,
        operation: str,
        items_per_second: float,
        execution_id: Optional[str] = None,
        phase_id: Optional[str] = None
    ) -> MetricSample:
        """Record throughput metric."""
        return self.record_metric(
            metric_type=MetricType.THROUGHPUT,
            value=items_per_second,
            unit="items/second",
            source=operation,
            execution_id=execution_id,
            phase_id=phase_id,
            metadata={"operation": operation}
        )
    
    def record_error_rate(
        self,
        operation: str,
        error_percentage: float,
        execution_id: Optional[str] = None,
        phase_id: Optional[str] = None
    ) -> MetricSample:
        """Record error rate metric."""
        return self.record_metric(
            metric_type=MetricType.ERROR_RATE,
            value=error_percentage,
            unit="percentage",
            source=operation,
            execution_id=execution_id,
            phase_id=phase_id,
            metadata={"operation": operation}
        )
    
    def get_current_system_resources(self) -> SystemResources:
        """Get current system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / (1024**3)  # GB
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free = disk.free / (1024**3)  # GB
            
            # Network I/O
            network = psutil.net_io_counters()
            network_sent = network.bytes_sent / (1024**2)  # MB
            network_recv = network.bytes_recv / (1024**2)  # MB
            
            return SystemResources(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available=memory_available,
                disk_usage_percent=disk_usage_percent,
                disk_free=disk_free,
                network_sent=network_sent,
                network_recv=network_recv
            )
            
        except Exception as e:
            logger.error(f"Error getting system resources: {e}")
            return SystemResources(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available=0.0,
                disk_usage_percent=0.0,
                disk_free=0.0,
                network_sent=0.0,
                network_recv=0.0
            )
    
    def get_performance_stats(
        self,
        metric_type: MetricType,
        hours: int = 1,
        execution_id: Optional[str] = None
    ) -> Optional[PerformanceStats]:
        """Get performance statistics for a metric type."""
        with self.lock:
            # Filter samples
            cutoff = datetime.now() - timedelta(hours=hours)
            filtered_samples = [
                sample for sample in self.samples
                if (sample.metric_type == metric_type and
                    sample.timestamp >= cutoff and
                    (execution_id is None or sample.execution_id == execution_id))
            ]
            
            if not filtered_samples:
                return None
            
            values = [sample.value for sample in filtered_samples]
            
            return PerformanceStats(
                metric_type=metric_type,
                count=len(values),
                min_value=min(values),
                max_value=max(values),
                mean_value=statistics.mean(values),
                median_value=statistics.median(values),
                std_deviation=statistics.stdev(values) if len(values) > 1 else 0.0,
                percentile_95=self._percentile(values, 95),
                percentile_99=self._percentile(values, 99),
                unit=filtered_samples[0].unit,
                period_start=cutoff,
                period_end=datetime.now()
            )
    
    def get_metric_history(
        self,
        metric_type: MetricType,
        hours: int = 1,
        execution_id: Optional[str] = None
    ) -> List[Tuple[datetime, float]]:
        """Get metric history as time series."""
        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            filtered_samples = [
                sample for sample in self.samples
                if (sample.metric_type == metric_type and
                    sample.timestamp >= cutoff and
                    (execution_id is None or sample.execution_id == execution_id))
            ]
            
            return [(sample.timestamp, sample.value) for sample in filtered_samples]
    
    def get_alerts(
        self,
        hours: int = 24,
        severity: Optional[str] = None
    ) -> List[PerformanceAlert]:
        """Get recent performance alerts."""
        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            filtered_alerts = [
                alert for alert in self.alerts
                if alert.timestamp >= cutoff
            ]
            
            if severity:
                filtered_alerts = [
                    alert for alert in filtered_alerts
                    if alert.severity == severity
                ]
            
            return sorted(filtered_alerts, key=lambda a: a.timestamp, reverse=True)
    
    def register_custom_metric(
        self,
        name: str,
        collector_func: Callable[[], float]
    ) -> None:
        """Register a custom metric collector function."""
        self.custom_metrics[name] = collector_func
        logger.info(f"Registered custom metric: {name}")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("Performance monitoring loop started")
        
        while self.monitoring_active:
            try:
                current_time = time.time()
                
                # Collect system metrics
                self._collect_system_metrics()
                
                # Collect custom metrics
                self._collect_custom_metrics()
                
                # Wait for next sample
                elapsed = time.time() - current_time
                sleep_time = max(0, self.sample_interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.sample_interval)
        
        logger.info("Performance monitoring loop stopped")
    
    def _collect_system_metrics(self) -> None:
        """Collect system performance metrics."""
        try:
            current_time = time.time()
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            self.record_metric(
                MetricType.CPU_USAGE,
                cpu_percent,
                "percentage",
                "system"
            )
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.record_metric(
                MetricType.MEMORY_USAGE,
                memory.percent,
                "percentage",
                "system"
            )
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.record_metric(
                MetricType.DISK_USAGE,
                disk_percent,
                "percentage",
                "system"
            )
            
            # Network I/O rates
            network = psutil.net_io_counters()
            time_delta = current_time - self.last_sample_time
            
            if time_delta > 0 and hasattr(self, 'last_network_io'):
                sent_rate = (network.bytes_sent - self.last_network_io.bytes_sent) / time_delta
                recv_rate = (network.bytes_recv - self.last_network_io.bytes_recv) / time_delta
                
                self.record_metric(
                    MetricType.NETWORK_IO,
                    sent_rate / 1024,  # KB/s
                    "KB/s",
                    "network_sent"
                )
                
                self.record_metric(
                    MetricType.NETWORK_IO,
                    recv_rate / 1024,  # KB/s
                    "KB/s",
                    "network_recv"
                )
            
            self.last_network_io = network
            
            # Disk I/O rates
            disk_io = psutil.disk_io_counters()
            if disk_io and time_delta > 0 and hasattr(self, 'last_disk_io'):
                read_rate = (disk_io.read_bytes - self.last_disk_io.read_bytes) / time_delta
                write_rate = (disk_io.write_bytes - self.last_disk_io.write_bytes) / time_delta
                
                self.record_metric(
                    MetricType.DISK_IO,
                    read_rate / 1024,  # KB/s
                    "KB/s",
                    "disk_read"
                )
                
                self.record_metric(
                    MetricType.DISK_IO,
                    write_rate / 1024,  # KB/s
                    "KB/s",
                    "disk_write"
                )
            
            if disk_io:
                self.last_disk_io = disk_io
            
            self.last_sample_time = current_time
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _collect_custom_metrics(self) -> None:
        """Collect custom metrics."""
        for name, collector_func in self.custom_metrics.items():
            try:
                value = collector_func()
                self.record_metric(
                    MetricType.CUSTOM,
                    value,
                    "custom",
                    name,
                    metadata={"custom_metric": name}
                )
            except Exception as e:
                logger.error(f"Error collecting custom metric {name}: {e}")
    
    def _check_thresholds(self, sample: MetricSample) -> None:
        """Check if sample violates any thresholds."""
        threshold = self.thresholds.get(sample.metric_type)
        if not threshold or not threshold.enabled:
            return
        
        # Check cooldown
        alert_key = f"{sample.metric_type.value}_{sample.source}"
        last_alert = self.last_alert_times.get(alert_key)
        if last_alert:
            cooldown_delta = timedelta(seconds=threshold.cooldown_seconds)
            if datetime.now() - last_alert < cooldown_delta:
                return
        
        # Check thresholds
        alert_severity = None
        threshold_value = None
        
        if threshold.threshold_type == AlertThresholdType.ABSOLUTE:
            if sample.value >= threshold.critical_value:
                alert_severity = "critical"
                threshold_value = threshold.critical_value
            elif sample.value >= threshold.warning_value:
                alert_severity = "warning"
                threshold_value = threshold.warning_value
        
        elif threshold.threshold_type == AlertThresholdType.PERCENTAGE:
            # For percentage thresholds, assume 100 is the maximum
            percentage = (sample.value / 100.0) * 100
            if percentage >= threshold.critical_value:
                alert_severity = "critical"
                threshold_value = threshold.critical_value
            elif percentage >= threshold.warning_value:
                alert_severity = "warning"
                threshold_value = threshold.warning_value
        
        if alert_severity:
            alert = PerformanceAlert(
                timestamp=datetime.now(),
                metric_type=sample.metric_type,
                current_value=sample.value,
                threshold_value=threshold_value,
                severity=alert_severity,
                message=f"{sample.metric_type.value} {alert_severity}: {sample.value:.2f} {sample.unit} (threshold: {threshold_value:.2f})",
                source=sample.source,
                execution_id=sample.execution_id,
                metadata=sample.metadata
            )
            
            self.alerts.append(alert)
            self.last_alert_times[alert_key] = datetime.now()
            
            logger.warning(f"Performance alert: {alert.message}")
    
    def _setup_default_thresholds(self) -> None:
        """Setup default performance thresholds."""
        default_thresholds = [
            MetricThreshold(
                MetricType.CPU_USAGE,
                AlertThresholdType.ABSOLUTE,
                warning_value=80.0,
                critical_value=95.0,
                unit="percentage"
            ),
            MetricThreshold(
                MetricType.MEMORY_USAGE,
                AlertThresholdType.ABSOLUTE,
                warning_value=85.0,
                critical_value=95.0,
                unit="percentage"
            ),
            MetricThreshold(
                MetricType.DISK_USAGE,
                AlertThresholdType.ABSOLUTE,
                warning_value=80.0,
                critical_value=90.0,
                unit="percentage"
            ),
            MetricThreshold(
                MetricType.ERROR_RATE,
                AlertThresholdType.ABSOLUTE,
                warning_value=5.0,
                critical_value=10.0,
                unit="percentage"
            )
        ]
        
        for threshold in default_thresholds:
            self.thresholds[threshold.metric_type] = threshold
    
    def _cleanup_old_samples(self) -> None:
        """Clean up old metric samples."""
        # Keep only last 24 hours of samples
        cutoff = datetime.now() - timedelta(hours=24)
        self.samples = [
            sample for sample in self.samples
            if sample.timestamp >= cutoff
        ]
        
        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (percentile / 100.0)
        floor_k = int(k)
        ceil_k = floor_k + 1
        
        if ceil_k >= len(sorted_values):
            return sorted_values[-1]
        
        d0 = sorted_values[floor_k] * (ceil_k - k)
        d1 = sorted_values[ceil_k] * (k - floor_k)
        
        return d0 + d1