"""
Progress bar components for Claude Code Builder UI.
"""
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import time

from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
    SpinnerColumn,
    MofNCompleteColumn,
    ProgressColumn,
    Task as RichTask
)
from rich.text import Text
from rich.console import Console
from rich.table import Column

from ..models.phase import Phase, Task, TaskStatus
from ..models.monitoring import Metric, MetricType


class TokenColumn(ProgressColumn):
    """Custom column to display token usage."""
    
    def render(self, task: RichTask) -> Text:
        """Render the token count."""
        tokens = task.fields.get('tokens', 0)
        max_tokens = task.fields.get('max_tokens', 0)
        
        if max_tokens > 0:
            percentage = (tokens / max_tokens) * 100
            style = "green" if percentage < 80 else "yellow" if percentage < 95 else "red"
            return Text(f"{tokens:,}/{max_tokens:,} ({percentage:.0f}%)", style=style)
        else:
            return Text(f"{tokens:,} tokens", style="cyan")


class CostColumn(ProgressColumn):
    """Custom column to display cost."""
    
    def render(self, task: RichTask) -> Text:
        """Render the cost."""
        cost = task.fields.get('cost', 0.0)
        budget = task.fields.get('budget', 0.0)
        
        if budget > 0:
            percentage = (cost / budget) * 100
            style = "green" if percentage < 80 else "yellow" if percentage < 95 else "red"
            return Text(f"${cost:.2f}/${budget:.2f} ({percentage:.0f}%)", style=style)
        else:
            return Text(f"${cost:.2f}", style="cyan")


class StatusColumn(ProgressColumn):
    """Custom column to display status with icon."""
    
    def render(self, task: RichTask) -> Text:
        """Render the status."""
        status = task.fields.get('status', 'pending')
        
        icons = {
            'pending': '⏸',
            'running': '▶',
            'completed': '✓',
            'failed': '✗',
            'skipped': '⏭'
        }
        
        styles = {
            'pending': 'dim',
            'running': 'blue',
            'completed': 'green',
            'failed': 'red',
            'skipped': 'yellow'
        }
        
        icon = icons.get(status, '?')
        style = styles.get(status, 'white')
        
        return Text(f"{icon} {status}", style=style)


@dataclass
class ProgressBarConfig:
    """Configuration for progress bars."""
    show_spinner: bool = True
    show_percentage: bool = True
    show_time_elapsed: bool = True
    show_time_remaining: bool = True
    show_tokens: bool = True
    show_cost: bool = True
    show_status: bool = True
    show_speed: bool = False
    expand: bool = True
    transient: bool = False


class PhaseProgressBar:
    """Progress bar for tracking phase execution."""
    
    def __init__(self, console: Optional[Console] = None, config: Optional[ProgressBarConfig] = None):
        """Initialize phase progress bar."""
        self.console = console or Console()
        self.config = config or ProgressBarConfig()
        self.progress = self._create_progress()
        self.phase_tasks: Dict[str, Any] = {}
        
    def _create_progress(self) -> Progress:
        """Create Rich progress bar with custom columns."""
        columns = []
        
        if self.config.show_spinner:
            columns.append(SpinnerColumn())
            
        columns.extend([
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
        ])
        
        if self.config.show_percentage:
            columns.append(TextColumn("[progress.percentage]{task.percentage:>3.0f}%"))
            
        columns.append(MofNCompleteColumn())
        
        if self.config.show_time_elapsed:
            columns.append(TimeElapsedColumn())
            
        if self.config.show_time_remaining:
            columns.append(TimeRemainingColumn())
            
        if self.config.show_status:
            columns.append(StatusColumn())
            
        if self.config.show_tokens:
            columns.append(TokenColumn())
            
        if self.config.show_cost:
            columns.append(CostColumn())
            
        return Progress(
            *columns,
            console=self.console,
            expand=self.config.expand,
            transient=self.config.transient
        )
        
    def add_phase(self, phase: Phase, total_tasks: int) -> str:
        """Add a phase to track."""
        task_id = self.progress.add_task(
            f"Phase {phase.phase_number}: {phase.name}",
            total=total_tasks,
            status='pending',
            tokens=0,
            max_tokens=phase.metadata.get('max_tokens', 0),
            cost=0.0,
            budget=phase.metadata.get('budget', 0.0)
        )
        
        self.phase_tasks[phase.id] = task_id
        return task_id
        
    def update_phase(self, phase: Phase, completed_tasks: int, 
                    tokens: Optional[int] = None, cost: Optional[float] = None):
        """Update phase progress."""
        if phase.id not in self.phase_tasks:
            return
            
        task_id = self.phase_tasks[phase.id]
        update_fields = {
            'completed': completed_tasks,
            'status': phase.status.value
        }
        
        if tokens is not None:
            update_fields['tokens'] = tokens
            
        if cost is not None:
            update_fields['cost'] = cost
            
        self.progress.update(task_id, **update_fields)
        
    def complete_phase(self, phase: Phase, success: bool = True):
        """Mark phase as complete."""
        if phase.id not in self.phase_tasks:
            return
            
        task_id = self.phase_tasks[phase.id]
        status = 'completed' if success else 'failed'
        
        self.progress.update(
            task_id,
            completed=self.progress.tasks[task_id].total,
            status=status
        )
        
    def start(self):
        """Start the progress display."""
        return self.progress.start()
        
    def stop(self):
        """Stop the progress display."""
        self.progress.stop()
        
    def __enter__(self):
        """Enter context manager."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.stop()


class TaskProgressBar:
    """Progress bar for tracking individual task execution."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize task progress bar."""
        self.console = console or Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold magenta]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True
        )
        self.task_ids: Dict[str, Any] = {}
        
    def add_task(self, task: Task, total_steps: int = 100) -> str:
        """Add a task to track."""
        task_id = self.progress.add_task(
            task.name,
            total=total_steps
        )
        self.task_ids[task.id] = task_id
        return task_id
        
    def update_task(self, task: Task, completed_steps: int):
        """Update task progress."""
        if task.id in self.task_ids:
            self.progress.update(
                self.task_ids[task.id],
                completed=completed_steps
            )
            
    def complete_task(self, task: Task):
        """Mark task as complete."""
        if task.id in self.task_ids:
            task_id = self.task_ids[task.id]
            self.progress.update(
                task_id,
                completed=self.progress.tasks[task_id].total
            )
            
    def start(self):
        """Start the progress display."""
        return self.progress.start()
        
    def stop(self):
        """Stop the progress display."""
        self.progress.stop()


class OverallProgressBar:
    """Progress bar for tracking overall project progress."""
    
    def __init__(self, total_phases: int, console: Optional[Console] = None):
        """Initialize overall progress bar."""
        self.console = console or Console()
        self.total_phases = total_phases
        self.progress = Progress(
            TextColumn("[bold green]Overall Progress"),
            BarColumn(bar_width=50, complete_style="green", finished_style="bold green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            MofNCompleteColumn(),
            TextColumn("phases"),
            TimeElapsedColumn(),
            console=self.console,
            expand=True
        )
        
        self.main_task = self.progress.add_task(
            "Building project",
            total=total_phases
        )
        
    def update(self, completed_phases: int):
        """Update overall progress."""
        self.progress.update(self.main_task, completed=completed_phases)
        
    def complete(self):
        """Mark overall progress as complete."""
        self.progress.update(self.main_task, completed=self.total_phases)
        
    def start(self):
        """Start the progress display."""
        return self.progress.start()
        
    def stop(self):
        """Stop the progress display."""
        self.progress.stop()


class TokenProgressBar:
    """Specialized progress bar for tracking token usage."""
    
    def __init__(self, max_tokens: int, console: Optional[Console] = None):
        """Initialize token progress bar."""
        self.console = console or Console()
        self.max_tokens = max_tokens
        self.progress = Progress(
            TextColumn("[bold yellow]Token Usage"),
            BarColumn(
                bar_width=40,
                complete_style="yellow",
                finished_style="bold red"
            ),
            TextColumn("{task.completed:,}/{task.total:,}"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("{task.fields[rate]:.0f} tokens/sec", style="dim"),
            console=self.console
        )
        
        self.task = self.progress.add_task(
            "Tokens",
            total=max_tokens,
            rate=0
        )
        self.last_update = time.time()
        self.last_tokens = 0
        
    def update(self, tokens_used: int):
        """Update token usage."""
        current_time = time.time()
        time_diff = current_time - self.last_update
        
        if time_diff > 0:
            tokens_diff = tokens_used - self.last_tokens
            rate = tokens_diff / time_diff
        else:
            rate = 0
            
        self.progress.update(
            self.task,
            completed=tokens_used,
            rate=rate
        )
        
        self.last_update = current_time
        self.last_tokens = tokens_used
        
        # Warn if approaching limit
        percentage = (tokens_used / self.max_tokens) * 100
        if percentage >= 90 and percentage < 95:
            self.console.print("[yellow]⚠ Warning: Approaching token limit[/yellow]")
        elif percentage >= 95:
            self.console.print("[red]⚠ Critical: Token limit nearly reached![/red]")
            
    def start(self):
        """Start the progress display."""
        return self.progress.start()
        
    def stop(self):
        """Stop the progress display."""
        self.progress.stop()


class MultiProgressBar:
    """Manage multiple progress bars simultaneously."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize multi-progress bar manager."""
        self.console = console or Console()
        self.progress_bars: List[Progress] = []
        
    def add_progress_bar(self, progress_bar: Progress):
        """Add a progress bar to manage."""
        self.progress_bars.append(progress_bar)
        
    def start_all(self):
        """Start all progress bars."""
        for pb in self.progress_bars:
            pb.start()
            
    def stop_all(self):
        """Stop all progress bars."""
        for pb in self.progress_bars:
            pb.stop()
            
    def __enter__(self):
        """Enter context manager."""
        self.start_all()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.stop_all()