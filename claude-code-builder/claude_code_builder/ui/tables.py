"""
Table components for Claude Code Builder UI.
"""
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.table import Table
from rich.console import Console
from rich.text import Text
from rich.box import Box, ROUNDED, SIMPLE, DOUBLE, ASCII
from rich.align import Align

from ..models.phase import Phase, Task, TaskStatus, PhaseStatus
from ..models.project import ProjectSpec, Feature, Technology
from ..models.cost import CostBreakdown, CostTracker
from ..models.monitoring import Metric, MetricType


@dataclass
class TableConfig:
    """Configuration for table appearance."""
    box_style: Box = ROUNDED
    show_header: bool = True
    show_footer: bool = False
    show_edge: bool = True
    show_lines: bool = False
    pad_edge: bool = True
    expand: bool = False
    width: Optional[int] = None
    min_width: Optional[int] = None
    title_style: str = "bold blue"
    header_style: str = "bold cyan"
    row_styles: Optional[List[str]] = None
    highlight: bool = True


class PhaseTable:
    """Table for displaying phase information."""
    
    def __init__(self, console: Optional[Console] = None, config: Optional[TableConfig] = None):
        """Initialize phase table."""
        self.console = console or Console()
        self.config = config or TableConfig()
        
    def create_summary_table(self, phases: List[Phase]) -> Table:
        """Create a summary table of all phases."""
        table = Table(
            title="Phase Summary",
            box=self.config.box_style,
            show_header=self.config.show_header,
            show_footer=self.config.show_footer,
            show_edge=self.config.show_edge,
            show_lines=self.config.show_lines,
            pad_edge=self.config.pad_edge,
            expand=self.config.expand,
            width=self.config.width,
            min_width=self.config.min_width,
            title_style=self.config.title_style,
            header_style=self.config.header_style,
            row_styles=self.config.row_styles or ["none", "dim"],
            highlight=self.config.highlight
        )
        
        # Add columns
        table.add_column("Phase", style="bold", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Tasks", justify="center")
        table.add_column("Progress", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("Cost", justify="right")
        
        # Add rows
        for phase in phases:
            status_icon, status_style = self._get_status_display(phase.status)
            
            # Calculate task progress
            if phase.tasks:
                completed = sum(1 for t in phase.tasks if t.status == TaskStatus.COMPLETED)
                total = len(phase.tasks)
                progress = f"{completed}/{total}"
                progress_pct = (completed / total) * 100
                progress_text = Text(f"{progress} ({progress_pct:.0f}%)")
                if progress_pct == 100:
                    progress_text.stylize("green")
                elif progress_pct > 0:
                    progress_text.stylize("yellow")
            else:
                progress_text = Text("0/0", style="dim")
                
            # Format duration
            duration = phase.metadata.get('duration', 0)
            duration_text = self._format_duration(duration)
            
            # Format cost
            cost = phase.metadata.get('cost', 0.0)
            cost_text = Text(f"${cost:.2f}", style="cyan")
            
            table.add_row(
                f"{phase.phase_number}",
                phase.name,
                Text(f"{status_icon} {phase.status.value}", style=status_style),
                str(len(phase.tasks)),
                progress_text,
                duration_text,
                cost_text
            )
            
        return table
        
    def create_detail_table(self, phase: Phase) -> Table:
        """Create a detailed table for a single phase."""
        table = Table(
            title=f"Phase {phase.phase_number}: {phase.name}",
            box=self.config.box_style,
            show_header=self.config.show_header,
            expand=self.config.expand,
            title_style=self.config.title_style,
            header_style=self.config.header_style
        )
        
        # Add columns
        table.add_column("Property", style="bold cyan", no_wrap=True)
        table.add_column("Value")
        
        # Status
        status_icon, status_style = self._get_status_display(phase.status)
        table.add_row("Status", Text(f"{status_icon} {phase.status.value}", style=status_style))
        
        # Description
        table.add_row("Description", phase.description or "No description")
        
        # Task Summary
        if phase.tasks:
            task_summary = self._get_task_summary(phase.tasks)
            table.add_row("Tasks", task_summary)
        else:
            table.add_row("Tasks", Text("No tasks defined", style="dim"))
            
        # Dependencies
        if phase.dependencies:
            deps = ", ".join(f"Phase {d}" for d in phase.dependencies)
            table.add_row("Dependencies", deps)
        else:
            table.add_row("Dependencies", Text("None", style="dim"))
            
        # Metadata
        for key, value in phase.metadata.items():
            if key not in ['duration', 'cost']:  # These are shown separately
                table.add_row(key.title(), str(value))
                
        # Duration
        duration = phase.metadata.get('duration', 0)
        table.add_row("Duration", self._format_duration(duration))
        
        # Cost
        cost = phase.metadata.get('cost', 0.0)
        table.add_row("Cost", Text(f"${cost:.2f}", style="cyan"))
        
        return table
        
    def _get_status_display(self, status: PhaseStatus) -> Tuple[str, str]:
        """Get icon and style for status."""
        status_displays = {
            PhaseStatus.PENDING: ("⏸", "dim"),
            PhaseStatus.PLANNING: ("📋", "blue"),
            PhaseStatus.EXECUTING: ("▶", "yellow"),
            PhaseStatus.COMPLETED: ("✓", "green"),
            PhaseStatus.FAILED: ("✗", "red"),
            PhaseStatus.SKIPPED: ("⏭", "dim yellow")
        }
        return status_displays.get(status, ("?", "white"))
        
    def _get_task_summary(self, tasks: List[Task]) -> Text:
        """Get task summary text."""
        status_counts = {}
        for task in tasks:
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
        parts = []
        for status, count in status_counts.items():
            color = {
                'pending': 'dim',
                'running': 'yellow',
                'completed': 'green',
                'failed': 'red',
                'skipped': 'dim yellow'
            }.get(status, 'white')
            parts.append(f"[{color}]{count} {status}[/{color}]")
            
        return Text.from_markup(", ".join(parts))
        
    def _format_duration(self, seconds: float) -> Text:
        """Format duration in human-readable format."""
        if seconds < 60:
            return Text(f"{seconds:.1f}s", style="dim")
        elif seconds < 3600:
            minutes = seconds / 60
            return Text(f"{minutes:.1f}m", style="dim")
        else:
            hours = seconds / 3600
            return Text(f"{hours:.1f}h", style="dim")


class TaskTable:
    """Table for displaying task information."""
    
    def __init__(self, console: Optional[Console] = None, config: Optional[TableConfig] = None):
        """Initialize task table."""
        self.console = console or Console()
        self.config = config or TableConfig()
        
    def create_task_list(self, tasks: List[Task]) -> Table:
        """Create a table listing all tasks."""
        table = Table(
            title="Task List",
            box=self.config.box_style,
            show_header=self.config.show_header,
            expand=self.config.expand,
            title_style=self.config.title_style,
            header_style=self.config.header_style,
            row_styles=["none", "dim"],
            highlight=self.config.highlight
        )
        
        # Add columns
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Name", style="cyan")
        table.add_column("Type", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Priority", justify="center")
        table.add_column("Dependencies", style="dim")
        
        # Add rows
        for task in tasks:
            status_icon = {
                TaskStatus.PENDING: "⏸",
                TaskStatus.RUNNING: "▶",
                TaskStatus.COMPLETED: "✓",
                TaskStatus.FAILED: "✗",
                TaskStatus.SKIPPED: "⏭"
            }.get(task.status, "?")
            
            status_style = {
                TaskStatus.PENDING: "dim",
                TaskStatus.RUNNING: "yellow",
                TaskStatus.COMPLETED: "green",
                TaskStatus.FAILED: "red",
                TaskStatus.SKIPPED: "dim yellow"
            }.get(task.status, "white")
            
            priority_style = {
                "low": "dim",
                "medium": "white",
                "high": "yellow",
                "critical": "red"
            }.get(task.metadata.get('priority', 'medium'), "white")
            
            deps = ", ".join(task.dependencies) if task.dependencies else "-"
            
            table.add_row(
                task.id[:8],
                task.name,
                task.type,
                Text(f"{status_icon} {task.status.value}", style=status_style),
                Text(task.metadata.get('priority', 'medium'), style=priority_style),
                deps
            )
            
        return table


class CostTable:
    """Table for displaying cost information."""
    
    def __init__(self, console: Optional[Console] = None, config: Optional[TableConfig] = None):
        """Initialize cost table."""
        self.console = console or Console()
        self.config = config or TableConfig()
        
    def create_cost_breakdown(self, tracker: CostTracker) -> Table:
        """Create a cost breakdown table."""
        table = Table(
            title="Cost Breakdown",
            box=self.config.box_style,
            show_header=self.config.show_header,
            show_footer=True,
            expand=self.config.expand,
            title_style=self.config.title_style,
            header_style=self.config.header_style
        )
        
        # Add columns
        table.add_column("Category", style="bold cyan")
        table.add_column("Tokens", justify="right")
        table.add_column("Rate", justify="right")
        table.add_column("Cost", justify="right", style="green")
        
        # Add rows for each category
        total_cost = 0.0
        for category, breakdown in tracker.breakdowns.items():
            if breakdown.count > 0:  # Only show categories with entries
                tokens = breakdown.tokens_used
                # Calculate rate based on total cost and tokens
                rate = breakdown.total / breakdown.tokens_used if breakdown.tokens_used > 0 else 0.0
                cost = breakdown.total
                total_cost += cost
                
                table.add_row(
                    category.value.replace('_', ' ').title(),
                    f"{tokens:,}",
                    f"${rate:.6f}/token" if tokens > 0 else "-",
                    f"${cost:.2f}"
                )
            
        # Add footer with total
        table.add_row(
            Text("TOTAL", style="bold"),
            "",
            "",
            Text(f"${total_cost:.2f}", style="bold green"),
            end_section=True
        )
        
        return table
        
    def create_phase_costs(self, phases: List[Phase]) -> Table:
        """Create a table of costs by phase."""
        table = Table(
            title="Phase Costs",
            box=self.config.box_style,
            show_header=self.config.show_header,
            show_footer=True,
            expand=self.config.expand,
            title_style=self.config.title_style,
            header_style=self.config.header_style
        )
        
        # Add columns
        table.add_column("Phase", style="bold")
        table.add_column("Name", style="cyan")
        table.add_column("Estimated", justify="right")
        table.add_column("Actual", justify="right")
        table.add_column("Variance", justify="right")
        
        # Track totals
        total_estimated = 0.0
        total_actual = 0.0
        
        # Add rows
        for phase in phases:
            estimated = phase.metadata.get('estimated_cost', 0.0)
            actual = phase.metadata.get('cost', 0.0)
            variance = actual - estimated
            
            total_estimated += estimated
            total_actual += actual
            
            # Style variance
            if variance > 0:
                variance_text = Text(f"+${variance:.2f}", style="red")
            elif variance < 0:
                variance_text = Text(f"-${abs(variance):.2f}", style="green")
            else:
                variance_text = Text("$0.00", style="dim")
                
            table.add_row(
                f"{phase.phase_number}",
                phase.name,
                f"${estimated:.2f}",
                f"${actual:.2f}",
                variance_text
            )
            
        # Add footer
        total_variance = total_actual - total_estimated
        if total_variance > 0:
            total_variance_text = Text(f"+${total_variance:.2f}", style="bold red")
        elif total_variance < 0:
            total_variance_text = Text(f"-${abs(total_variance):.2f}", style="bold green")
        else:
            total_variance_text = Text("$0.00", style="bold dim")
            
        table.add_row(
            Text("TOTAL", style="bold"),
            "",
            Text(f"${total_estimated:.2f}", style="bold"),
            Text(f"${total_actual:.2f}", style="bold"),
            total_variance_text,
            end_section=True
        )
        
        return table


class MetricsTable:
    """Table for displaying metrics information."""
    
    def __init__(self, console: Optional[Console] = None, config: Optional[TableConfig] = None):
        """Initialize metrics table."""
        self.console = console or Console()
        self.config = config or TableConfig()
        
    def create_metrics_summary(self, metrics: Dict[str, Metric]) -> Table:
        """Create a metrics summary table."""
        table = Table(
            title="Metrics Summary",
            box=self.config.box_style,
            show_header=self.config.show_header,
            expand=self.config.expand,
            title_style=self.config.title_style,
            header_style=self.config.header_style
        )
        
        # Add columns
        table.add_column("Metric", style="bold cyan")
        table.add_column("Type", justify="center")
        table.add_column("Value", justify="right")
        table.add_column("Unit", style="dim")
        
        # Group metrics by type
        grouped = {}
        for name, metric in metrics.items():
            metric_type = metric.type.value
            if metric_type not in grouped:
                grouped[metric_type] = []
            grouped[metric_type].append((name, metric))
            
        # Add rows by type
        for metric_type in ['counter', 'gauge', 'timer', 'histogram']:
            if metric_type in grouped:
                for name, metric in grouped[metric_type]:
                    # Format value based on type
                    if metric_type == 'timer':
                        value = f"{metric.value:.2f}"
                        unit = "seconds"
                    elif metric_type == 'counter':
                        value = f"{int(metric.value):,}"
                        unit = "count"
                    elif metric_type == 'gauge':
                        if 'memory' in name.lower():
                            value = f"{metric.value:.1f}"
                            unit = "MB"
                        elif 'cost' in name.lower():
                            value = f"${metric.value:.2f}"
                            unit = ""
                        else:
                            value = f"{metric.value:.2f}"
                            unit = metric.metadata.get('unit', '')
                    else:
                        value = f"{metric.value:.2f}"
                        unit = metric.metadata.get('unit', '')
                        
                    table.add_row(
                        name,
                        metric_type,
                        value,
                        unit
                    )
                    
        return table
        
    def create_performance_table(self, metrics: Dict[str, Metric]) -> Table:
        """Create a performance metrics table."""
        table = Table(
            title="Performance Metrics",
            box=self.config.box_style,
            show_header=self.config.show_header,
            expand=self.config.expand,
            title_style=self.config.title_style,
            header_style=self.config.header_style
        )
        
        # Add columns
        table.add_column("Operation", style="bold cyan")
        table.add_column("Count", justify="right")
        table.add_column("Avg Time", justify="right")
        table.add_column("Min Time", justify="right")
        table.add_column("Max Time", justify="right")
        table.add_column("Total Time", justify="right")
        
        # Find timer metrics
        for name, metric in metrics.items():
            if metric.type == MetricType.TIMER:
                stats = metric.metadata.get('stats', {})
                
                table.add_row(
                    name,
                    f"{stats.get('count', 0):,}",
                    f"{stats.get('avg', 0):.3f}s",
                    f"{stats.get('min', 0):.3f}s",
                    f"{stats.get('max', 0):.3f}s",
                    f"{stats.get('total', 0):.3f}s"
                )
                
        return table