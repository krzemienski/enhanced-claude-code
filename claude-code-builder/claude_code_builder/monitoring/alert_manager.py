"""Alert management system for threshold-based notifications."""

import logging
import threading
import time
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .performance_monitor import PerformanceAlert, MetricType
from .cost_monitor import CostAlert
from .error_tracker import ErrorStats, ErrorSeverity

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of alerts."""
    PERFORMANCE = "performance"
    COST = "cost"
    ERROR = "error"
    SYSTEM = "system"
    CUSTOM = "custom"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertChannel(Enum):
    """Alert delivery channels."""
    LOG = "log"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CONSOLE = "console"
    FILE = "file"


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    alert_type: AlertType
    severity: AlertSeverity
    condition: str  # JSON condition string
    message_template: str
    channels: List[AlertChannel]
    enabled: bool = True
    cooldown_minutes: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert instance."""
    id: str
    rule_name: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: datetime
    source_data: Dict[str, Any]
    execution_id: Optional[str] = None
    phase_id: Optional[str] = None
    task_id: Optional[str] = None
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertChannelConfig:
    """Configuration for alert channels."""
    channel: AlertChannel
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """Manages alert rules, evaluation, and delivery."""
    
    def __init__(self):
        """Initialize the alert manager."""
        self.alert_rules: Dict[str, AlertRule] = {}
        self.channel_configs: Dict[AlertChannel, AlertChannelConfig] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.lock = threading.RLock()
        
        # Alert state tracking
        self.last_evaluation_times: Dict[str, datetime] = {}
        self.alert_counts: Dict[str, int] = {}
        
        # Evaluation thread
        self.evaluation_active = False
        self.evaluation_thread: Optional[threading.Thread] = None
        self.evaluation_interval = 30  # seconds
        
        # Alert handlers
        self.alert_handlers: Dict[AlertChannel, Callable] = {
            AlertChannel.LOG: self._handle_log_alert,
            AlertChannel.CONSOLE: self._handle_console_alert,
            AlertChannel.FILE: self._handle_file_alert,
            AlertChannel.EMAIL: self._handle_email_alert,
            AlertChannel.WEBHOOK: self._handle_webhook_alert
        }
        
        # Setup default channel configs
        self._setup_default_channels()
        
        # Setup default rules
        self._setup_default_rules()
        
        logger.info("Alert Manager initialized")
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add or update an alert rule."""
        with self.lock:
            self.alert_rules[rule.name] = rule
            logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove an alert rule."""
        with self.lock:
            if rule_name in self.alert_rules:
                del self.alert_rules[rule_name]
                logger.info(f"Removed alert rule: {rule_name}")
                return True
            return False
    
    def configure_channel(self, config: AlertChannelConfig) -> None:
        """Configure an alert channel."""
        with self.lock:
            self.channel_configs[config.channel] = config
            logger.info(f"Configured alert channel: {config.channel.value}")
    
    def start_evaluation(self) -> None:
        """Start alert rule evaluation."""
        with self.lock:
            if self.evaluation_active:
                logger.warning("Alert evaluation already active")
                return
            
            self.evaluation_active = True
            self.evaluation_thread = threading.Thread(
                target=self._evaluation_loop,
                daemon=True
            )
            self.evaluation_thread.start()
            
            logger.info("Alert evaluation started")
    
    def stop_evaluation(self) -> None:
        """Stop alert rule evaluation."""
        with self.lock:
            if not self.evaluation_active:
                return
            
            self.evaluation_active = False
            
            if self.evaluation_thread and self.evaluation_thread.is_alive():
                self.evaluation_thread.join(timeout=5.0)
            
            logger.info("Alert evaluation stopped")
    
    def trigger_alert(
        self,
        rule_name: str,
        source_data: Dict[str, Any],
        execution_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        override_message: Optional[str] = None
    ) -> Optional[Alert]:
        """Manually trigger an alert."""
        with self.lock:
            if rule_name not in self.alert_rules:
                logger.error(f"Alert rule not found: {rule_name}")
                return None
            
            rule = self.alert_rules[rule_name]
            
            if not rule.enabled:
                logger.debug(f"Alert rule disabled: {rule_name}")
                return None
            
            # Check cooldown
            if self._is_in_cooldown(rule_name):
                logger.debug(f"Alert rule in cooldown: {rule_name}")
                return None
            
            # Create alert
            alert = self._create_alert(
                rule, source_data, execution_id, phase_id, task_id, override_message
            )
            
            # Process alert
            self._process_alert(alert)
            
            return alert
    
    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """Acknowledge an alert."""
        with self.lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.acknowledged = True
                alert.metadata["acknowledged_by"] = user
                alert.metadata["acknowledged_at"] = datetime.now().isoformat()
                
                logger.info(f"Alert acknowledged: {alert_id} by {user}")
                return True
            
            return False
    
    def resolve_alert(self, alert_id: str, user: str = "system") -> bool:
        """Resolve an alert."""
        with self.lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                alert.metadata["resolved_by"] = user
                alert.metadata["resolved_at"] = datetime.now().isoformat()
                
                # Move to history
                self.alert_history.append(alert)
                del self.active_alerts[alert_id]
                
                logger.info(f"Alert resolved: {alert_id} by {user}")
                return True
            
            return False
    
    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None
    ) -> List[Alert]:
        """Get active alerts with optional filtering."""
        with self.lock:
            alerts = list(self.active_alerts.values())
            
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            
            if alert_type:
                alerts = [a for a in alerts if a.alert_type == alert_type]
            
            return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def get_alert_history(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Alert]:
        """Get alert history."""
        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            filtered_alerts = [
                alert for alert in self.alert_history
                if alert.timestamp >= cutoff
            ]
            
            return sorted(filtered_alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
    
    def get_alert_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics."""
        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            # Get recent alerts (active + history)
            recent_alerts = (
                [a for a in self.active_alerts.values() if a.timestamp >= cutoff] +
                [a for a in self.alert_history if a.timestamp >= cutoff]
            )
            
            # Calculate stats
            stats = {
                "total_alerts": len(recent_alerts),
                "active_alerts": len(self.active_alerts),
                "alerts_by_severity": {},
                "alerts_by_type": {},
                "alert_rate": len(recent_alerts) / hours if hours > 0 else 0,
                "top_rules": {}
            }
            
            # Group by severity
            for severity in AlertSeverity:
                count = sum(1 for a in recent_alerts if a.severity == severity)
                stats["alerts_by_severity"][severity.value] = count
            
            # Group by type
            for alert_type in AlertType:
                count = sum(1 for a in recent_alerts if a.alert_type == alert_type)
                stats["alerts_by_type"][alert_type.value] = count
            
            # Top rules
            rule_counts = {}
            for alert in recent_alerts:
                rule_counts[alert.rule_name] = rule_counts.get(alert.rule_name, 0) + 1
            
            stats["top_rules"] = dict(
                sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            )
            
            return stats
    
    def evaluate_performance_alert(self, perf_alert: PerformanceAlert) -> None:
        """Evaluate a performance alert against rules."""
        source_data = {
            "metric_type": perf_alert.metric_type.value,
            "current_value": perf_alert.current_value,
            "threshold_value": perf_alert.threshold_value,
            "severity": perf_alert.severity,
            "source": perf_alert.source
        }
        
        # Check relevant rules
        for rule_name, rule in self.alert_rules.items():
            if (rule.alert_type == AlertType.PERFORMANCE and
                rule.enabled and
                self._evaluate_condition(rule.condition, source_data)):
                
                self.trigger_alert(
                    rule_name,
                    source_data,
                    execution_id=perf_alert.execution_id
                )
    
    def evaluate_cost_alert(self, cost_alert: CostAlert) -> None:
        """Evaluate a cost alert against rules."""
        source_data = {
            "category": cost_alert.category.value,
            "current_cost": cost_alert.current_cost,
            "budget_limit": cost_alert.budget_limit,
            "percentage_used": cost_alert.percentage_used,
            "level": cost_alert.level.value
        }
        
        # Check relevant rules
        for rule_name, rule in self.alert_rules.items():
            if (rule.alert_type == AlertType.COST and
                rule.enabled and
                self._evaluate_condition(rule.condition, source_data)):
                
                self.trigger_alert(
                    rule_name,
                    source_data,
                    execution_id=cost_alert.execution_id
                )
    
    def evaluate_error_stats(self, error_stats: ErrorStats) -> None:
        """Evaluate error statistics against rules."""
        source_data = {
            "total_errors": error_stats.total_errors,
            "error_rate": error_stats.error_rate,
            "critical_errors": error_stats.errors_by_severity.get(ErrorSeverity.CRITICAL, 0),
            "high_errors": error_stats.errors_by_severity.get(ErrorSeverity.HIGH, 0)
        }
        
        # Check relevant rules
        for rule_name, rule in self.alert_rules.items():
            if (rule.alert_type == AlertType.ERROR and
                rule.enabled and
                self._evaluate_condition(rule.condition, source_data)):
                
                self.trigger_alert(rule_name, source_data)
    
    def _evaluation_loop(self) -> None:
        """Main alert evaluation loop."""
        logger.info("Alert evaluation loop started")
        
        while self.evaluation_active:
            try:
                # Evaluate time-based rules here if needed
                # For now, alerts are triggered by external events
                
                time.sleep(self.evaluation_interval)
                
            except Exception as e:
                logger.error(f"Error in alert evaluation loop: {e}")
                time.sleep(self.evaluation_interval)
        
        logger.info("Alert evaluation loop stopped")
    
    def _create_alert(
        self,
        rule: AlertRule,
        source_data: Dict[str, Any],
        execution_id: Optional[str],
        phase_id: Optional[str],
        task_id: Optional[str],
        override_message: Optional[str]
    ) -> Alert:
        """Create an alert from a rule."""
        alert_id = self._generate_alert_id(rule.name)
        
        # Format message
        if override_message:
            message = override_message
        else:
            message = self._format_message(rule.message_template, source_data)
        
        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            alert_type=rule.alert_type,
            severity=rule.severity,
            message=message,
            timestamp=datetime.now(),
            source_data=source_data,
            execution_id=execution_id,
            phase_id=phase_id,
            task_id=task_id,
            metadata=rule.metadata.copy()
        )
        
        return alert
    
    def _process_alert(self, alert: Alert) -> None:
        """Process and deliver an alert."""
        # Add to active alerts
        self.active_alerts[alert.id] = alert
        
        # Update tracking
        self.last_evaluation_times[alert.rule_name] = alert.timestamp
        self.alert_counts[alert.rule_name] = self.alert_counts.get(alert.rule_name, 0) + 1
        
        # Get rule
        rule = self.alert_rules[alert.rule_name]
        
        # Deliver through configured channels
        for channel in rule.channels:
            if channel in self.channel_configs and self.channel_configs[channel].enabled:
                try:
                    handler = self.alert_handlers.get(channel)
                    if handler:
                        handler(alert, self.channel_configs[channel])
                except Exception as e:
                    logger.error(f"Error delivering alert via {channel.value}: {e}")
        
        logger.info(f"Processed alert: {alert.id} - {alert.message}")
    
    def _is_in_cooldown(self, rule_name: str) -> bool:
        """Check if rule is in cooldown period."""
        if rule_name not in self.last_evaluation_times:
            return False
        
        rule = self.alert_rules[rule_name]
        last_time = self.last_evaluation_times[rule_name]
        cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
        
        return datetime.now() - last_time < cooldown_delta
    
    def _evaluate_condition(self, condition: str, data: Dict[str, Any]) -> bool:
        """Evaluate an alert condition."""
        try:
            # Parse condition as JSON
            condition_obj = json.loads(condition)
            
            # Simple condition evaluation
            if "field" in condition_obj and "operator" in condition_obj and "value" in condition_obj:
                field = condition_obj["field"]
                operator = condition_obj["operator"]
                value = condition_obj["value"]
                
                if field not in data:
                    return False
                
                field_value = data[field]
                
                if operator == "gt":
                    return field_value > value
                elif operator == "gte":
                    return field_value >= value
                elif operator == "lt":
                    return field_value < value
                elif operator == "lte":
                    return field_value <= value
                elif operator == "eq":
                    return field_value == value
                elif operator == "ne":
                    return field_value != value
                elif operator == "contains":
                    return value in str(field_value)
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _format_message(self, template: str, data: Dict[str, Any]) -> str:
        """Format alert message template with data."""
        try:
            return template.format(**data)
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return template
    
    def _generate_alert_id(self, rule_name: str) -> str:
        """Generate unique alert ID."""
        import hashlib
        timestamp = datetime.now().isoformat()
        content = f"{rule_name}:{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _handle_log_alert(self, alert: Alert, config: AlertChannelConfig) -> None:
        """Handle log alert delivery."""
        log_level = getattr(logging, alert.severity.value.upper(), logging.INFO)
        logger.log(log_level, f"ALERT [{alert.severity.value.upper()}]: {alert.message}")
    
    def _handle_console_alert(self, alert: Alert, config: AlertChannelConfig) -> None:
        """Handle console alert delivery."""
        severity_colors = {
            AlertSeverity.INFO: "\033[36m",      # Cyan
            AlertSeverity.WARNING: "\033[33m",   # Yellow
            AlertSeverity.CRITICAL: "\033[31m",  # Red
            AlertSeverity.EMERGENCY: "\033[35m"  # Magenta
        }
        
        color = severity_colors.get(alert.severity, "")
        reset = "\033[0m"
        
        print(f"{color}[ALERT {alert.severity.value.upper()}]{reset} {alert.message}")
    
    def _handle_file_alert(self, alert: Alert, config: AlertChannelConfig) -> None:
        """Handle file alert delivery."""
        file_path = config.config.get("file_path", "alerts.log")
        
        try:
            with open(file_path, "a") as f:
                f.write(f"{alert.timestamp.isoformat()} [{alert.severity.value.upper()}] {alert.message}\n")
        except Exception as e:
            logger.error(f"Error writing alert to file: {e}")
    
    def _handle_email_alert(self, alert: Alert, config: AlertChannelConfig) -> None:
        """Handle email alert delivery."""
        email_config = config.config
        
        if not all(k in email_config for k in ["smtp_host", "smtp_port", "from_email", "to_emails"]):
            logger.error("Incomplete email configuration")
            return
        
        try:
            msg = MIMEMultipart()
            msg["From"] = email_config["from_email"]
            msg["To"] = ", ".join(email_config["to_emails"])
            msg["Subject"] = f"Alert: {alert.rule_name} [{alert.severity.value.upper()}]"
            
            body = f"""
Alert Details:
- Rule: {alert.rule_name}
- Severity: {alert.severity.value.upper()}
- Type: {alert.alert_type.value}
- Timestamp: {alert.timestamp.isoformat()}
- Message: {alert.message}

Source Data: {json.dumps(alert.source_data, indent=2)}
            """
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(email_config["smtp_host"], email_config["smtp_port"]) as server:
                if email_config.get("use_tls", False):
                    server.starttls()
                
                if "username" in email_config and "password" in email_config:
                    server.login(email_config["username"], email_config["password"])
                
                server.send_message(msg)
                
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
    
    def _handle_webhook_alert(self, alert: Alert, config: AlertChannelConfig) -> None:
        """Handle webhook alert delivery."""
        webhook_config = config.config
        
        if "url" not in webhook_config:
            logger.error("Webhook URL not configured")
            return
        
        try:
            import requests
            
            payload = {
                "alert_id": alert.id,
                "rule_name": alert.rule_name,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "source_data": alert.source_data,
                "execution_id": alert.execution_id,
                "phase_id": alert.phase_id,
                "task_id": alert.task_id
            }
            
            headers = webhook_config.get("headers", {"Content-Type": "application/json"})
            timeout = webhook_config.get("timeout", 10)
            
            response = requests.post(
                webhook_config["url"],
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}")
    
    def _setup_default_channels(self) -> None:
        """Setup default channel configurations."""
        default_channels = [
            AlertChannelConfig(AlertChannel.LOG, enabled=True),
            AlertChannelConfig(AlertChannel.CONSOLE, enabled=True),
            AlertChannelConfig(
                AlertChannel.FILE,
                enabled=False,
                config={"file_path": "alerts.log"}
            )
        ]
        
        for config in default_channels:
            self.channel_configs[config.channel] = config
    
    def _setup_default_rules(self) -> None:
        """Setup default alert rules."""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.WARNING,
                condition='{"field": "current_value", "operator": "gte", "value": 90}',
                message_template="High CPU usage: {current_value:.1f}%",
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE],
                cooldown_minutes=5
            ),
            AlertRule(
                name="high_memory_usage",
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.WARNING,
                condition='{"field": "current_value", "operator": "gte", "value": 90}',
                message_template="High memory usage: {current_value:.1f}%",
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE],
                cooldown_minutes=5
            ),
            AlertRule(
                name="budget_exceeded",
                alert_type=AlertType.COST,
                severity=AlertSeverity.CRITICAL,
                condition='{"field": "percentage_used", "operator": "gte", "value": 90}',
                message_template="Budget alert: {percentage_used:.1f}% used (${current_cost:.2f} / ${budget_limit:.2f})",
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE],
                cooldown_minutes=15
            ),
            AlertRule(
                name="high_error_rate",
                alert_type=AlertType.ERROR,
                severity=AlertSeverity.WARNING,
                condition='{"field": "error_rate", "operator": "gte", "value": 5}',
                message_template="High error rate: {error_rate:.2f} errors/minute",
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE],
                cooldown_minutes=10
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.name] = rule