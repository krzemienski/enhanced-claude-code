"""Cost tracking models for Claude Code Builder."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from .base import SerializableModel, TimestampedModel
from ..utils.constants import (
    COST_CLAUDE_CODE,
    COST_RESEARCH,
    COST_PLANNING,
    COST_EXECUTION,
    COST_TESTING,
    COST_VALIDATION
)


class CostCategory(Enum):
    """Cost tracking categories."""
    
    CLAUDE_CODE = COST_CLAUDE_CODE
    RESEARCH = COST_RESEARCH
    PLANNING = COST_PLANNING
    EXECUTION = COST_EXECUTION
    TESTING = COST_TESTING
    VALIDATION = COST_VALIDATION
    
    @classmethod
    def from_string(cls, value: str) -> "CostCategory":
        """Create category from string."""
        for category in cls:
            if category.value == value:
                return category
        raise ValueError(f"Invalid cost category: {value}")


@dataclass
class CostEntry(SerializableModel, TimestampedModel):
    """Individual cost entry."""
    
    category: CostCategory = CostCategory.CLAUDE_CODE
    amount: float = 0.0
    description: str = ""
    phase: Optional[str] = None
    task: Optional[str] = None
    
    # API details
    api_calls: int = 0
    tokens_used: int = 0
    model: Optional[str] = None
    
    # Time tracking
    duration: Optional[timedelta] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate cost entry."""
        if self.amount < 0:
            raise ValueError("Cost amount cannot be negative")
        
        if self.api_calls < 0:
            raise ValueError("API calls cannot be negative")
        
        if self.tokens_used < 0:
            raise ValueError("Tokens used cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data["category"] = self.category.value
        if self.duration:
            data["duration"] = self.duration.total_seconds()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostEntry":
        """Create from dictionary."""
        # Convert category string to enum
        if "category" in data and isinstance(data["category"], str):
            data["category"] = CostCategory.from_string(data["category"])
        
        # Convert duration
        if "duration" in data and isinstance(data["duration"], (int, float)):
            data["duration"] = timedelta(seconds=data["duration"])
        
        return super().from_dict(data)


@dataclass
class CostBreakdown:
    """Cost breakdown by category."""
    
    category: CostCategory
    total: float = 0.0
    count: int = 0
    api_calls: int = 0
    tokens_used: int = 0
    average_cost: float = 0.0
    
    # Time tracking
    total_duration: timedelta = timedelta()
    average_duration: timedelta = timedelta()
    
    # Details
    entries: List[CostEntry] = field(default_factory=list)
    
    def add_entry(self, entry: CostEntry) -> None:
        """Add cost entry to breakdown."""
        if entry.category != self.category:
            raise ValueError(f"Entry category {entry.category} doesn't match breakdown category {self.category}")
        
        self.entries.append(entry)
        self.total += entry.amount
        self.count += 1
        self.api_calls += entry.api_calls
        self.tokens_used += entry.tokens_used
        
        if entry.duration:
            self.total_duration += entry.duration
        
        # Update averages
        self.average_cost = self.total / self.count if self.count > 0 else 0
        self.average_duration = self.total_duration / self.count if self.count > 0 else timedelta()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "total": self.total,
            "count": self.count,
            "api_calls": self.api_calls,
            "tokens_used": self.tokens_used,
            "average_cost": self.average_cost,
            "total_duration": self.total_duration.total_seconds(),
            "average_duration": self.average_duration.total_seconds(),
            "entries": [entry.to_dict() for entry in self.entries]
        }


@dataclass
class CostTracker(SerializableModel):
    """Main cost tracking system."""
    
    entries: List[CostEntry] = field(default_factory=list)
    breakdowns: Dict[CostCategory, CostBreakdown] = field(default_factory=dict)
    
    # Totals
    total_cost: float = 0.0
    total_api_calls: int = 0
    total_tokens: int = 0
    total_duration: timedelta = timedelta()
    
    # Budget tracking
    budget: Optional[float] = None
    budget_alerts: List[float] = field(default_factory=lambda: [0.5, 0.75, 0.9, 1.0])
    alerts_triggered: List[float] = field(default_factory=list)
    
    # Session info
    session_id: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
    started_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Initialize breakdowns for all categories."""
        for category in CostCategory:
            if category not in self.breakdowns:
                self.breakdowns[category] = CostBreakdown(category=category)
    
    def add_cost(
        self,
        category: CostCategory,
        amount: float,
        description: str,
        **kwargs
    ) -> CostEntry:
        """Add a cost entry."""
        entry = CostEntry(
            category=category,
            amount=amount,
            description=description,
            **kwargs
        )
        
        entry.validate()
        
        # Add to entries list
        self.entries.append(entry)
        
        # Update breakdown
        if category not in self.breakdowns:
            self.breakdowns[category] = CostBreakdown(category=category)
        self.breakdowns[category].add_entry(entry)
        
        # Update totals
        self.total_cost += amount
        self.total_api_calls += entry.api_calls
        self.total_tokens += entry.tokens_used
        if entry.duration:
            self.total_duration += entry.duration
        
        # Check budget alerts
        self._check_budget_alerts()
        
        return entry
    
    def _check_budget_alerts(self) -> Optional[float]:
        """Check if any budget alerts should be triggered."""
        if not self.budget:
            return None
        
        usage_ratio = self.total_cost / self.budget
        
        for threshold in self.budget_alerts:
            if usage_ratio >= threshold and threshold not in self.alerts_triggered:
                self.alerts_triggered.append(threshold)
                return threshold
        
        return None
    
    def get_category_total(self, category: CostCategory) -> float:
        """Get total cost for a category."""
        return self.breakdowns.get(category, CostBreakdown(category=category)).total
    
    def get_category_breakdown(self, category: CostCategory) -> CostBreakdown:
        """Get breakdown for a category."""
        return self.breakdowns.get(category, CostBreakdown(category=category))
    
    def get_phase_costs(self, phase: str) -> List[CostEntry]:
        """Get all costs for a specific phase."""
        return [entry for entry in self.entries if entry.phase == phase]
    
    def get_task_costs(self, task: str) -> List[CostEntry]:
        """Get all costs for a specific task."""
        return [entry for entry in self.entries if entry.task == task]
    
    def get_budget_usage(self) -> float:
        """Get budget usage percentage."""
        if not self.budget:
            return 0.0
        return (self.total_cost / self.budget) * 100
    
    def get_remaining_budget(self) -> Optional[float]:
        """Get remaining budget."""
        if not self.budget:
            return None
        return max(0, self.budget - self.total_cost)
    
    def get_cost_per_hour(self) -> float:
        """Calculate average cost per hour."""
        elapsed = datetime.utcnow() - self.started_at
        hours = elapsed.total_seconds() / 3600
        return self.total_cost / hours if hours > 0 else 0
    
    def get_tokens_per_dollar(self) -> float:
        """Calculate tokens per dollar efficiency."""
        return self.total_tokens / self.total_cost if self.total_cost > 0 else 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "duration": (datetime.utcnow() - self.started_at).total_seconds(),
            "total_cost": self.total_cost,
            "total_api_calls": self.total_api_calls,
            "total_tokens": self.total_tokens,
            "cost_per_hour": self.get_cost_per_hour(),
            "tokens_per_dollar": self.get_tokens_per_dollar(),
            "budget": self.budget,
            "budget_usage": self.get_budget_usage(),
            "remaining_budget": self.get_remaining_budget(),
            "categories": {
                category.value: {
                    "total": breakdown.total,
                    "count": breakdown.count,
                    "average": breakdown.average_cost,
                    "percentage": (breakdown.total / self.total_cost * 100) if self.total_cost > 0 else 0
                }
                for category, breakdown in self.breakdowns.items()
                if breakdown.count > 0
            }
        }
    
    def export_csv(self) -> str:
        """Export costs to CSV format."""
        lines = [
            "Timestamp,Category,Phase,Task,Description,Amount,API Calls,Tokens,Duration"
        ]
        
        for entry in self.entries:
            duration = entry.duration.total_seconds() if entry.duration else 0
            lines.append(
                f"{entry.created_at.isoformat()},"
                f"{entry.category.value},"
                f"{entry.phase or ''},"
                f"{entry.task or ''},"
                f'"{entry.description}",'
                f"{entry.amount:.4f},"
                f"{entry.api_calls},"
                f"{entry.tokens_used},"
                f"{duration}"
            )
        
        return "\n".join(lines)
    
    def validate(self) -> None:
        """Validate cost tracker."""
        # Validate all entries
        for entry in self.entries:
            entry.validate()
        
        # Validate budget alerts
        for alert in self.budget_alerts:
            if not 0 <= alert <= 1:
                raise ValueError(f"Budget alert {alert} must be between 0 and 1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "breakdowns": {
                category.value: breakdown.to_dict()
                for category, breakdown in self.breakdowns.items()
            },
            "total_cost": self.total_cost,
            "total_api_calls": self.total_api_calls,
            "total_tokens": self.total_tokens,
            "total_duration": self.total_duration.total_seconds(),
            "budget": self.budget,
            "budget_alerts": self.budget_alerts,
            "alerts_triggered": self.alerts_triggered,
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "summary": self.get_summary()
        }