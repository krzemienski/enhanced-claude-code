"""Real-time cost monitoring and budget tracking."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
import json

logger = logging.getLogger(__name__)


class CostCategory(Enum):
    """Cost categories for tracking."""
    API_CALLS = "api_calls"
    COMPUTE_TIME = "compute_time"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    EXTERNAL_SERVICES = "external_services"
    RESEARCH_APIS = "research_apis"
    AI_INFERENCE = "ai_inference"
    OTHER = "other"


class AlertLevel(Enum):
    """Cost alert levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class CostEntry:
    """Individual cost entry."""
    timestamp: datetime
    category: CostCategory
    amount: float
    currency: str = "USD"
    description: str = ""
    service: str = ""
    execution_id: Optional[str] = None
    phase_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostBudget:
    """Budget configuration."""
    total_budget: float
    category_budgets: Dict[CostCategory, float] = field(default_factory=dict)
    daily_budget: Optional[float] = None
    hourly_budget: Optional[float] = None
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "warning": 0.7,  # 70% of budget
        "critical": 0.9,  # 90% of budget
        "emergency": 0.95  # 95% of budget
    })
    currency: str = "USD"


@dataclass
class CostSummary:
    """Cost summary for a period."""
    total_cost: float
    category_costs: Dict[CostCategory, float] = field(default_factory=dict)
    service_costs: Dict[str, float] = field(default_factory=dict)
    hourly_costs: List[Tuple[datetime, float]] = field(default_factory=list)
    currency: str = "USD"
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


@dataclass
class CostAlert:
    """Cost alert notification."""
    timestamp: datetime
    level: AlertLevel
    category: CostCategory
    message: str
    current_cost: float
    budget_limit: float
    percentage_used: float
    execution_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CostMonitor:
    """Monitors and tracks costs in real-time."""
    
    def __init__(self, budget: Optional[CostBudget] = None):
        """Initialize the cost monitor."""
        self.budget = budget or CostBudget(total_budget=100.0)
        self.cost_entries: List[CostEntry] = []
        self.alerts: List[CostAlert] = []
        self.lock = threading.RLock()
        
        # Tracking state
        self.execution_costs: Dict[str, float] = {}  # execution_id -> total cost
        self.category_totals: Dict[CostCategory, float] = {}
        self.service_totals: Dict[str, float] = {}
        
        # Rate limiting and estimation
        self.api_call_counts: Dict[str, int] = {}  # service -> count
        self.api_costs: Dict[str, float] = {  # service -> cost per call
            "anthropic_claude": 0.001,
            "openai_gpt4": 0.002,
            "perplexity": 0.0005,
            "github": 0.0001,
            "general": 0.001
        }
        
        # Time-based tracking
        self.hourly_costs: Dict[str, float] = {}  # hour_key -> cost
        self.daily_costs: Dict[str, float] = {}  # date_key -> cost
        
        logger.info("Cost Monitor initialized")
    
    def set_budget(self, budget: CostBudget) -> None:
        """Set or update budget configuration."""
        with self.lock:
            self.budget = budget
            self._check_budget_alerts()
        
        logger.info(f"Budget updated: ${budget.total_budget} {budget.currency}")
    
    def record_cost(
        self,
        amount: float,
        category: CostCategory,
        description: str = "",
        service: str = "",
        execution_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CostEntry:
        """Record a cost entry."""
        with self.lock:
            entry = CostEntry(
                timestamp=datetime.now(),
                category=category,
                amount=amount,
                currency=self.budget.currency,
                description=description,
                service=service,
                execution_id=execution_id,
                phase_id=phase_id,
                task_id=task_id,
                metadata=metadata or {}
            )
            
            self.cost_entries.append(entry)
            self._update_totals(entry)
            self._check_budget_alerts()
            
            logger.debug(
                f"Recorded cost: ${amount:.4f} for {category.value} "
                f"({description or service})"
            )
            
            return entry
    
    def record_api_call(
        self,
        service: str,
        cost_per_call: Optional[float] = None,
        execution_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CostEntry:
        """Record an API call cost."""
        # Get cost per call
        if cost_per_call is None:
            cost_per_call = self.api_costs.get(service, self.api_costs["general"])
        
        # Update call count
        self.api_call_counts[service] = self.api_call_counts.get(service, 0) + 1
        
        # Record cost
        return self.record_cost(
            amount=cost_per_call,
            category=CostCategory.API_CALLS,
            description=f"API call to {service}",
            service=service,
            execution_id=execution_id,
            phase_id=phase_id,
            task_id=task_id,
            metadata={
                **(metadata or {}),
                "call_count": self.api_call_counts[service]
            }
        )
    
    def record_compute_time(
        self,
        duration_seconds: float,
        cost_per_second: float = 0.0001,
        execution_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CostEntry:
        """Record compute time cost."""
        amount = duration_seconds * cost_per_second
        
        return self.record_cost(
            amount=amount,
            category=CostCategory.COMPUTE_TIME,
            description=f"Compute time: {duration_seconds:.2f}s",
            execution_id=execution_id,
            phase_id=phase_id,
            task_id=task_id,
            metadata={
                **(metadata or {}),
                "duration_seconds": duration_seconds,
                "cost_per_second": cost_per_second
            }
        )
    
    def get_current_costs(self, execution_id: Optional[str] = None) -> CostSummary:
        """Get current cost summary."""
        with self.lock:
            if execution_id:
                # Filter for specific execution
                entries = [e for e in self.cost_entries if e.execution_id == execution_id]
            else:
                entries = self.cost_entries
            
            return self._calculate_cost_summary(entries)
    
    def get_costs_for_period(
        self,
        start_time: datetime,
        end_time: datetime,
        execution_id: Optional[str] = None
    ) -> CostSummary:
        """Get cost summary for a specific time period."""
        with self.lock:
            # Filter entries by time period
            entries = [
                e for e in self.cost_entries
                if start_time <= e.timestamp <= end_time
            ]
            
            # Filter by execution if specified
            if execution_id:
                entries = [e for e in entries if e.execution_id == execution_id]
            
            summary = self._calculate_cost_summary(entries)
            summary.period_start = start_time
            summary.period_end = end_time
            
            return summary
    
    def get_hourly_costs(
        self,
        hours: int = 24,
        execution_id: Optional[str] = None
    ) -> List[Tuple[datetime, float]]:
        """Get hourly cost breakdown."""
        with self.lock:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # Group costs by hour
            hourly_totals: Dict[str, float] = {}
            
            for entry in self.cost_entries:
                if start_time <= entry.timestamp <= end_time:
                    if execution_id and entry.execution_id != execution_id:
                        continue
                    
                    hour_key = entry.timestamp.strftime("%Y-%m-%d %H:00")
                    hourly_totals[hour_key] = hourly_totals.get(hour_key, 0) + entry.amount
            
            # Convert to sorted list of tuples
            result = []
            for hour_key, cost in sorted(hourly_totals.items()):
                hour_dt = datetime.strptime(hour_key, "%Y-%m-%d %H:00")
                result.append((hour_dt, cost))
            
            return result
    
    def get_execution_cost(self, execution_id: str) -> float:
        """Get total cost for a specific execution."""
        with self.lock:
            return self.execution_costs.get(execution_id, 0.0)
    
    def estimate_remaining_cost(
        self,
        execution_id: str,
        progress_percent: float,
        method: str = "linear"
    ) -> float:
        """Estimate remaining cost for an execution."""
        current_cost = self.get_execution_cost(execution_id)
        
        if progress_percent <= 0:
            return current_cost  # Can't estimate without progress
        
        if progress_percent >= 100:
            return 0.0  # Execution complete
        
        if method == "linear":
            # Simple linear extrapolation
            total_estimated = current_cost / (progress_percent / 100.0)
            return total_estimated - current_cost
        
        elif method == "historical":
            # Use historical cost patterns
            return self._estimate_historical_cost(execution_id, progress_percent)
        
        else:
            return current_cost  # Default to current cost
    
    def check_budget_status(self) -> Dict[str, Any]:
        """Check current budget status."""
        with self.lock:
            total_spent = sum(self.category_totals.values())
            
            status = {
                "total_budget": self.budget.total_budget,
                "total_spent": total_spent,
                "remaining": self.budget.total_budget - total_spent,
                "percentage_used": (total_spent / self.budget.total_budget) * 100,
                "currency": self.budget.currency,
                "status": "ok"
            }
            
            # Determine status
            percentage = status["percentage_used"]
            if percentage >= self.budget.alert_thresholds["emergency"] * 100:
                status["status"] = "emergency"
            elif percentage >= self.budget.alert_thresholds["critical"] * 100:
                status["status"] = "critical"
            elif percentage >= self.budget.alert_thresholds["warning"] * 100:
                status["status"] = "warning"
            
            # Add category breakdown
            status["categories"] = {}
            for category in CostCategory:
                spent = self.category_totals.get(category, 0.0)
                budget = self.budget.category_budgets.get(category, 0.0)
                
                status["categories"][category.value] = {
                    "spent": spent,
                    "budget": budget,
                    "remaining": budget - spent if budget > 0 else None,
                    "percentage": (spent / budget) * 100 if budget > 0 else None
                }
            
            return status
    
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        hours: int = 24
    ) -> List[CostAlert]:
        """Get recent cost alerts."""
        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            recent_alerts = [
                alert for alert in self.alerts
                if alert.timestamp >= cutoff
            ]
            
            if level:
                recent_alerts = [
                    alert for alert in recent_alerts
                    if alert.level == level
                ]
            
            return sorted(recent_alerts, key=lambda a: a.timestamp, reverse=True)
    
    def export_cost_data(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Export cost data for analysis."""
        with self.lock:
            # Filter entries by time if specified
            entries = self.cost_entries
            if start_time:
                entries = [e for e in entries if e.timestamp >= start_time]
            if end_time:
                entries = [e for e in entries if e.timestamp <= end_time]
            
            # Convert to serializable format
            export_data = {
                "metadata": {
                    "export_time": datetime.now().isoformat(),
                    "period_start": start_time.isoformat() if start_time else None,
                    "period_end": end_time.isoformat() if end_time else None,
                    "total_entries": len(entries),
                    "currency": self.budget.currency
                },
                "budget": {
                    "total_budget": self.budget.total_budget,
                    "category_budgets": {
                        cat.value: amount for cat, amount in self.budget.category_budgets.items()
                    },
                    "alert_thresholds": self.budget.alert_thresholds
                },
                "entries": [
                    {
                        "timestamp": entry.timestamp.isoformat(),
                        "category": entry.category.value,
                        "amount": entry.amount,
                        "description": entry.description,
                        "service": entry.service,
                        "execution_id": entry.execution_id,
                        "phase_id": entry.phase_id,
                        "task_id": entry.task_id,
                        "metadata": entry.metadata
                    }
                    for entry in entries
                ],
                "summary": self._calculate_cost_summary(entries).__dict__
            }
            
            return export_data
    
    def _update_totals(self, entry: CostEntry) -> None:
        """Update running totals."""
        # Update category totals
        if entry.category not in self.category_totals:
            self.category_totals[entry.category] = 0.0
        self.category_totals[entry.category] += entry.amount
        
        # Update service totals
        if entry.service:
            if entry.service not in self.service_totals:
                self.service_totals[entry.service] = 0.0
            self.service_totals[entry.service] += entry.amount
        
        # Update execution totals
        if entry.execution_id:
            if entry.execution_id not in self.execution_costs:
                self.execution_costs[entry.execution_id] = 0.0
            self.execution_costs[entry.execution_id] += entry.amount
        
        # Update time-based totals
        hour_key = entry.timestamp.strftime("%Y-%m-%d %H")
        date_key = entry.timestamp.strftime("%Y-%m-%d")
        
        self.hourly_costs[hour_key] = self.hourly_costs.get(hour_key, 0) + entry.amount
        self.daily_costs[date_key] = self.daily_costs.get(date_key, 0) + entry.amount
    
    def _check_budget_alerts(self) -> None:
        """Check for budget threshold violations."""
        total_spent = sum(self.category_totals.values())
        percentage_used = (total_spent / self.budget.total_budget) * 100
        
        # Check total budget thresholds
        for threshold_name, threshold_percent in self.budget.alert_thresholds.items():
            if percentage_used >= threshold_percent * 100:
                # Check if we already have a recent alert for this threshold
                recent_alert = any(
                    alert.level.value == threshold_name and
                    (datetime.now() - alert.timestamp).total_seconds() < 3600  # 1 hour
                    for alert in self.alerts
                )
                
                if not recent_alert:
                    alert = CostAlert(
                        timestamp=datetime.now(),
                        level=AlertLevel(threshold_name),
                        category=CostCategory.OTHER,
                        message=f"Total budget {threshold_name}: {percentage_used:.1f}% used",
                        current_cost=total_spent,
                        budget_limit=self.budget.total_budget,
                        percentage_used=percentage_used
                    )
                    
                    self.alerts.append(alert)
                    logger.warning(f"Budget alert: {alert.message}")
        
        # Check category budget thresholds
        for category, budget_amount in self.budget.category_budgets.items():
            spent = self.category_totals.get(category, 0.0)
            if spent > budget_amount:
                percentage = (spent / budget_amount) * 100
                
                # Check if we already have a recent alert for this category
                recent_alert = any(
                    alert.category == category and
                    (datetime.now() - alert.timestamp).total_seconds() < 3600
                    for alert in self.alerts
                )
                
                if not recent_alert:
                    alert = CostAlert(
                        timestamp=datetime.now(),
                        level=AlertLevel.WARNING,
                        category=category,
                        message=f"{category.value} budget exceeded: {percentage:.1f}%",
                        current_cost=spent,
                        budget_limit=budget_amount,
                        percentage_used=percentage
                    )
                    
                    self.alerts.append(alert)
                    logger.warning(f"Category budget alert: {alert.message}")
    
    def _calculate_cost_summary(self, entries: List[CostEntry]) -> CostSummary:
        """Calculate cost summary from entries."""
        total_cost = sum(entry.amount for entry in entries)
        
        # Group by category
        category_costs = {}
        for category in CostCategory:
            category_costs[category] = sum(
                entry.amount for entry in entries
                if entry.category == category
            )
        
        # Group by service
        service_costs = {}
        for entry in entries:
            if entry.service:
                if entry.service not in service_costs:
                    service_costs[entry.service] = 0.0
                service_costs[entry.service] += entry.amount
        
        # Calculate hourly breakdown
        hourly_costs = []
        hourly_totals = {}
        for entry in entries:
            hour_key = entry.timestamp.strftime("%Y-%m-%d %H:00")
            hourly_totals[hour_key] = hourly_totals.get(hour_key, 0) + entry.amount
        
        for hour_key, cost in sorted(hourly_totals.items()):
            hour_dt = datetime.strptime(hour_key, "%Y-%m-%d %H:00")
            hourly_costs.append((hour_dt, cost))
        
        return CostSummary(
            total_cost=total_cost,
            category_costs=category_costs,
            service_costs=service_costs,
            hourly_costs=hourly_costs,
            currency=self.budget.currency
        )
    
    def _estimate_historical_cost(
        self,
        execution_id: str,
        progress_percent: float
    ) -> float:
        """Estimate remaining cost using historical patterns."""
        # This would use historical data to predict costs
        # For now, use simple linear estimation
        current_cost = self.get_execution_cost(execution_id)
        
        if progress_percent <= 0:
            return current_cost
        
        total_estimated = current_cost / (progress_percent / 100.0)
        return total_estimated - current_cost