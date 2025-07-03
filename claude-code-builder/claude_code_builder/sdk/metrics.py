"""Performance metrics tracking for Claude Code SDK."""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics

from ..models.base import BaseModel
from ..models.cost import CostEstimate, CostCategory

logger = logging.getLogger(__name__)


@dataclass
class CommandMetrics:
    """Metrics for a single command execution."""
    command: str
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark command as complete."""
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.success = success
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "command": self.command,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata
        }


@dataclass
class SessionMetrics:
    """Aggregated metrics for a session."""
    session_id: str
    start_time: datetime
    total_commands: int = 0
    successful_commands: int = 0
    failed_commands: int = 0
    total_duration: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    commands_per_minute: float = 0.0
    average_duration: float = 0.0
    error_rate: float = 0.0
    
    def update(self, command_metrics: CommandMetrics) -> None:
        """Update session metrics with command results."""
        self.total_commands += 1
        
        if command_metrics.success:
            self.successful_commands += 1
        else:
            self.failed_commands += 1
        
        if command_metrics.duration:
            self.total_duration += command_metrics.duration
        
        self.total_input_tokens += command_metrics.input_tokens
        self.total_output_tokens += command_metrics.output_tokens
        self.total_tokens += command_metrics.total_tokens
        self.total_cost += command_metrics.cost
        
        # Calculate derived metrics
        elapsed_minutes = (datetime.now() - self.start_time).total_seconds() / 60
        if elapsed_minutes > 0:
            self.commands_per_minute = self.total_commands / elapsed_minutes
        
        if self.total_commands > 0:
            self.average_duration = self.total_duration / self.total_commands
            self.error_rate = self.failed_commands / self.total_commands


class SDKMetrics:
    """Tracks performance metrics for Claude Code SDK operations."""
    
    def __init__(self, window_size: int = 100):
        """
        Initialize metrics tracker.
        
        Args:
            window_size: Size of sliding window for rate calculations
        """
        self.window_size = window_size
        self.active_commands: Dict[str, CommandMetrics] = {}
        self.completed_commands: List[CommandMetrics] = []
        self.session_metrics: Dict[str, SessionMetrics] = {}
        self.token_rates: deque = deque(maxlen=window_size)
        self.response_times: deque = deque(maxlen=window_size)
        self.cost_by_model: Dict[str, float] = defaultdict(float)
        self.start_time = datetime.now()
    
    def record_command_start(self, session_id: str, command: str) -> str:
        """
        Record the start of a command.
        
        Args:
            session_id: Session ID
            command: Command being executed
            
        Returns:
            Command ID for tracking
        """
        command_id = f"{session_id}:{datetime.now().timestamp()}"
        
        metrics = CommandMetrics(
            command=command,
            session_id=session_id,
            start_time=datetime.now()
        )
        
        self.active_commands[command_id] = metrics
        
        # Initialize session metrics if needed
        if session_id not in self.session_metrics:
            self.session_metrics[session_id] = SessionMetrics(
                session_id=session_id,
                start_time=datetime.now()
            )
        
        logger.debug(f"Started tracking command: {command_id}")
        return command_id
    
    def record_command_completion(
        self,
        session_id: str,
        command: str,
        duration: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """
        Record command completion.
        
        Args:
            session_id: Session ID
            command: Command that completed
            duration: Execution duration in seconds
            success: Whether command succeeded
            error: Error message if failed
        """
        # Find matching active command
        command_id = None
        for cid, metrics in self.active_commands.items():
            if metrics.session_id == session_id and metrics.command == command:
                command_id = cid
                break
        
        if not command_id:
            # Create new metrics if not found
            metrics = CommandMetrics(
                command=command,
                session_id=session_id,
                start_time=datetime.now() - timedelta(seconds=duration)
            )
        else:
            metrics = self.active_commands.pop(command_id)
        
        # Update metrics
        metrics.complete(success=success, error=error)
        metrics.duration = duration
        
        # Store completed command
        self.completed_commands.append(metrics)
        
        # Update session metrics
        if session_id in self.session_metrics:
            self.session_metrics[session_id].update(metrics)
        
        # Update response times
        self.response_times.append(duration)
        
        logger.debug(f"Completed command: {command} in {duration:.2f}s")
    
    def record_command_error(
        self,
        session_id: str,
        command: str,
        error: str
    ) -> None:
        """
        Record a command error.
        
        Args:
            session_id: Session ID
            command: Command that failed
            error: Error message
        """
        self.record_command_completion(
            session_id=session_id,
            command=command,
            duration=0.0,
            success=False,
            error=error
        )
    
    def record_token_usage(
        self,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "claude-3-opus-20240229"
    ) -> None:
        """
        Record token usage.
        
        Args:
            session_id: Session ID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model used
        """
        total_tokens = input_tokens + output_tokens
        
        # Find active command for this session
        for command_id, metrics in self.active_commands.items():
            if metrics.session_id == session_id:
                metrics.input_tokens += input_tokens
                metrics.output_tokens += output_tokens
                metrics.total_tokens += total_tokens
                
                # Calculate cost (example rates)
                model_costs = {
                    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
                    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
                    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125}
                }
                
                costs = model_costs.get(model, model_costs["claude-3-opus-20240229"])
                cost = (input_tokens / 1000) * costs["input"] + (output_tokens / 1000) * costs["output"]
                
                metrics.cost += cost
                self.cost_by_model[model] += cost
                break
        
        # Record token rate
        self.token_rates.append({
            "timestamp": datetime.now(),
            "tokens": total_tokens,
            "session_id": session_id
        })
    
    def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Get metrics for a specific session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session metrics
        """
        if session_id not in self.session_metrics:
            return {
                "session_id": session_id,
                "error": "Session not found"
            }
        
        metrics = self.session_metrics[session_id]
        
        return {
            "session_id": session_id,
            "start_time": metrics.start_time.isoformat(),
            "total_commands": metrics.total_commands,
            "successful_commands": metrics.successful_commands,
            "failed_commands": metrics.failed_commands,
            "total_duration": metrics.total_duration,
            "total_tokens": metrics.total_tokens,
            "total_cost": metrics.total_cost,
            "commands_per_minute": metrics.commands_per_minute,
            "average_duration": metrics.average_duration,
            "error_rate": metrics.error_rate,
            "active_commands": len([
                c for c in self.active_commands.values()
                if c.session_id == session_id
            ])
        }
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global SDK metrics."""
        total_commands = len(self.completed_commands)
        total_errors = sum(1 for c in self.completed_commands if not c.success)
        
        # Calculate token rates
        recent_tokens = [
            r for r in self.token_rates
            if (datetime.now() - r["timestamp"]).total_seconds() < 300  # Last 5 minutes
        ]
        
        tokens_per_minute = 0.0
        if recent_tokens:
            total_recent_tokens = sum(r["tokens"] for r in recent_tokens)
            elapsed_minutes = 5.0  # We're looking at last 5 minutes
            tokens_per_minute = total_recent_tokens / elapsed_minutes
        
        # Calculate average response time
        avg_response_time = statistics.mean(self.response_times) if self.response_times else 0.0
        
        # Calculate p95 response time
        p95_response_time = 0.0
        if self.response_times:
            sorted_times = sorted(self.response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p95_response_time = sorted_times[p95_index]
        
        return {
            "uptime": (datetime.now() - self.start_time).total_seconds(),
            "total_commands": total_commands,
            "total_errors": total_errors,
            "error_rate": total_errors / total_commands if total_commands > 0 else 0.0,
            "active_sessions": len(self.session_metrics),
            "active_commands": len(self.active_commands),
            "tokens_per_minute": tokens_per_minute,
            "average_response_time": avg_response_time,
            "p95_response_time": p95_response_time,
            "total_cost": sum(self.cost_by_model.values()),
            "cost_by_model": dict(self.cost_by_model)
        }
    
    def get_command_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get command history.
        
        Args:
            session_id: Filter by session ID
            limit: Maximum number of commands to return
            
        Returns:
            List of command metrics
        """
        commands = self.completed_commands
        
        if session_id:
            commands = [c for c in commands if c.session_id == session_id]
        
        # Sort by start time descending
        commands.sort(key=lambda c: c.start_time, reverse=True)
        
        return [c.to_dict() for c in commands[:limit]]
    
    def get_performance_summary(self) -> str:
        """Get a human-readable performance summary."""
        global_metrics = self.get_global_metrics()
        
        summary = "=== Claude Code SDK Performance Summary ===\n\n"
        
        uptime_hours = global_metrics["uptime"] / 3600
        summary += f"Uptime: {uptime_hours:.1f} hours\n"
        summary += f"Total Commands: {global_metrics['total_commands']}\n"
        summary += f"Error Rate: {global_metrics['error_rate']:.1%}\n"
        summary += f"Active Sessions: {global_metrics['active_sessions']}\n"
        summary += f"Active Commands: {global_metrics['active_commands']}\n\n"
        
        summary += "Performance Metrics:\n"
        summary += f"  Tokens/minute: {global_metrics['tokens_per_minute']:.0f}\n"
        summary += f"  Avg Response Time: {global_metrics['average_response_time']:.2f}s\n"
        summary += f"  P95 Response Time: {global_metrics['p95_response_time']:.2f}s\n\n"
        
        summary += "Cost Breakdown:\n"
        summary += f"  Total Cost: ${global_metrics['total_cost']:.4f}\n"
        for model, cost in global_metrics["cost_by_model"].items():
            summary += f"  {model}: ${cost:.4f}\n"
        
        return summary
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.active_commands.clear()
        self.completed_commands.clear()
        self.session_metrics.clear()
        self.token_rates.clear()
        self.response_times.clear()
        self.cost_by_model.clear()
        self.start_time = datetime.now()
        
        logger.info("Reset all SDK metrics")
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for persistence."""
        return {
            "start_time": self.start_time.isoformat(),
            "completed_commands": [c.to_dict() for c in self.completed_commands],
            "session_metrics": {
                sid: {
                    "session_id": m.session_id,
                    "start_time": m.start_time.isoformat(),
                    "total_commands": m.total_commands,
                    "successful_commands": m.successful_commands,
                    "failed_commands": m.failed_commands,
                    "total_duration": m.total_duration,
                    "total_tokens": m.total_tokens,
                    "total_cost": m.total_cost
                }
                for sid, m in self.session_metrics.items()
            },
            "cost_by_model": dict(self.cost_by_model)
        }