"""
Rich terminal interface for Claude Code Builder.
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
import json

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.live import Live
from rich.table import Table
from rich.progress import Progress
from rich.columns import Columns
from rich.syntax import Syntax
from rich.markdown import Markdown

from ..models.project import ProjectSpec
from ..models.phase import Phase, Task, TaskResult
from ..models.monitoring import Metric, MonitoringDashboard


@dataclass
class UIConfig:
    """Configuration for UI appearance and behavior."""
    theme: str = "default"
    refresh_rate: float = 0.1
    show_timestamps: bool = True
    show_phase_details: bool = True
    show_task_details: bool = True
    show_metrics: bool = True
    show_logs: bool = True
    log_level: str = "INFO"
    max_log_lines: int = 50
    enable_animations: bool = True
    enable_colors: bool = True
    compact_mode: bool = False


class RichTerminal:
    """Rich terminal UI for Claude Code Builder."""
    
    def __init__(self, config: Optional[UIConfig] = None):
        """Initialize terminal UI."""
        self.config = config or UIConfig()
        self.console = self._create_console()
        self.layout = Layout()
        self.logs: List[Dict[str, Any]] = []
        self.current_phase: Optional[Phase] = None
        self.current_task: Optional[Task] = None
        self.metrics: Optional[MonitoringDashboard] = None
        self.callbacks: Dict[str, List[Callable]] = {}
        self._setup_layout()
        
    def _create_console(self) -> Console:
        """Create Rich console with theme."""
        theme = Theme({
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "success": "bold green",
            "phase": "bold blue",
            "task": "magenta",
            "metric": "dim cyan",
            "timestamp": "dim white"
        })
        
        return Console(
            theme=theme,
            force_terminal=True,
            force_interactive=True,
            color_system="auto" if self.config.enable_colors else None
        )
        
    def _setup_layout(self):
        """Setup the terminal layout."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        self.layout["body"].split_row(
            Layout(name="main", ratio=2),
            Layout(name="sidebar", ratio=1)
        )
        
        self.layout["main"].split_column(
            Layout(name="progress", size=10),
            Layout(name="content")
        )
        
        self.layout["sidebar"].split_column(
            Layout(name="metrics", size=15),
            Layout(name="logs")
        )
        
    def update_header(self, project: ProjectSpec):
        """Update header with project info."""
        header_text = Text()
        header_text.append("Claude Code Builder v3.0", style="bold blue")
        header_text.append(" | ", style="dim")
        header_text.append(project.metadata.name, style="bold white")
        
        if self.config.show_timestamps:
            header_text.append(" | ", style="dim")
            header_text.append(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                style="timestamp"
            )
            
        self.layout["header"].update(
            Panel(header_text, border_style="blue")
        )
        
    def update_progress(self, phase: Phase, tasks: List[Task]):
        """Update progress display."""
        progress_layout = Layout()
        progress_layout.split_column(
            Layout(name="phase_progress", size=3),
            Layout(name="task_progress", size=3),
            Layout(name="overall_progress", size=3)
        )
        
        # Phase progress
        phase_text = Text()
        phase_text.append(f"Phase {phase.phase_number}: ", style="phase")
        phase_text.append(phase.name, style="bold")
        phase_text.append(f" ({phase.status.value})", style="dim")
        progress_layout["phase_progress"].update(phase_text)
        
        # Task progress
        completed_tasks = sum(1 for t in tasks if t.status.value == "completed")
        task_text = Text()
        task_text.append("Tasks: ", style="task")
        task_text.append(f"{completed_tasks}/{len(tasks)}", style="bold")
        progress_layout["task_progress"].update(task_text)
        
        # Overall progress
        overall_text = Text()
        overall_text.append("Overall: ", style="info")
        overall_percent = (completed_tasks / len(tasks) * 100) if tasks else 0
        overall_text.append(f"{overall_percent:.1f}%", style="bold")
        progress_layout["overall_progress"].update(overall_text)
        
        self.layout["progress"].update(
            Panel(progress_layout, title="Progress", border_style="green")
        )
        
    def update_content(self, content: Any):
        """Update main content area."""
        if isinstance(content, str):
            # Check if it's code
            if any(content.startswith(lang) for lang in ['python', 'javascript', 'typescript']):
                syntax = Syntax(content, "python", theme="monokai", line_numbers=True)
                self.layout["content"].update(Panel(syntax, border_style="cyan"))
            else:
                # Treat as markdown
                md = Markdown(content)
                self.layout["content"].update(Panel(md, border_style="white"))
        elif isinstance(content, Table):
            self.layout["content"].update(Panel(content, border_style="white"))
        else:
            self.layout["content"].update(Panel(str(content), border_style="white"))
            
    def update_metrics(self, metrics: MonitoringDashboard):
        """Update metrics display."""
        if not self.config.show_metrics:
            return
            
        metrics_table = Table(show_header=False, box=None)
        metrics_table.add_column("Metric", style="metric")
        metrics_table.add_column("Value", style="bold")
        
        # Get metrics from dashboard
        total_tokens = sum(m.value for m in metrics.metrics.values() if m.type.value == "counter" and "token" in m.name.lower())
        total_cost = sum(m.value for m in metrics.metrics.values() if m.type.value == "gauge" and "cost" in m.name.lower())
        api_calls = sum(m.value for m in metrics.metrics.values() if m.type.value == "counter" and "api" in m.name.lower())
        duration = max((m.value for m in metrics.metrics.values() if m.type.value == "timer"), default=0)
        memory = max((m.value for m in metrics.metrics.values() if m.type.value == "gauge" and "memory" in m.name.lower()), default=0)
        
        metrics_table.add_row("Total Tokens", f"{int(total_tokens):,}")
        metrics_table.add_row("Total Cost", f"${total_cost:.2f}")
        metrics_table.add_row("API Calls", str(int(api_calls)))
        metrics_table.add_row("Duration", f"{duration:.1f}s")
        metrics_table.add_row("Memory", f"{memory:.1f} MB")
        
        self.layout["metrics"].update(
            Panel(metrics_table, title="Metrics", border_style="cyan")
        )
        
    def update_logs(self, log_entry: Dict[str, Any]):
        """Update log display."""
        if not self.config.show_logs:
            return
            
        # Add to log buffer
        self.logs.append(log_entry)
        
        # Keep only recent logs
        if len(self.logs) > self.config.max_log_lines:
            self.logs = self.logs[-self.config.max_log_lines:]
            
        # Format logs
        log_text = Text()
        for entry in self.logs:
            level = entry.get('level', 'INFO')
            message = entry.get('message', '')
            timestamp = entry.get('timestamp', '')
            
            if self.config.show_timestamps:
                log_text.append(f"[{timestamp}] ", style="timestamp")
                
            style = {
                'ERROR': 'error',
                'WARNING': 'warning',
                'INFO': 'info',
                'DEBUG': 'dim',
                'SUCCESS': 'success'
            }.get(level, 'white')
            
            log_text.append(f"{level}: ", style=style)
            log_text.append(f"{message}\n", style="white")
            
        self.layout["logs"].update(
            Panel(log_text, title="Logs", border_style="yellow")
        )
        
    def update_footer(self, status: str = "Ready"):
        """Update footer with status."""
        footer_text = Text()
        footer_text.append("Status: ", style="dim")
        footer_text.append(status, style="bold green")
        
        shortcuts = [
            "[Q] Quit",
            "[P] Pause",
            "[R] Resume",
            "[S] Skip",
            "[H] Help"
        ]
        
        footer_text.append(" | ", style="dim")
        footer_text.append(" ".join(shortcuts), style="dim cyan")
        
        self.layout["footer"].update(
            Panel(footer_text, border_style="dim")
        )
        
    async def start_live_display(self):
        """Start live display with auto-refresh."""
        with Live(
            self.layout,
            console=self.console,
            refresh_per_second=1 / self.config.refresh_rate,
            transient=False
        ) as live:
            self.live = live
            
            # Keep display running
            while True:
                await asyncio.sleep(self.config.refresh_rate)
                
    def print_phase_start(self, phase: Phase):
        """Print phase start message."""
        self.console.print(
            Panel(
                f"[bold blue]Starting Phase {phase.phase_number}: {phase.name}[/bold blue]\n"
                f"[dim]{phase.description}[/dim]",
                title="Phase Start",
                border_style="blue"
            )
        )
        
    def print_phase_complete(self, phase: Phase, result: TaskResult):
        """Print phase completion message."""
        status_style = "green" if result.success else "red"
        status_text = "Completed" if result.success else "Failed"
        
        content = f"[bold {status_style}]Phase {phase.phase_number}: {phase.name} {status_text}[/bold {status_style}]\n"
        
        if result.metrics:
            content += f"\n[cyan]Metrics:[/cyan]\n"
            content += f"  Duration: {result.metrics.get('duration', 0):.1f}s\n"
            content += f"  Tokens: {result.metrics.get('tokens', 0):,}\n"
            content += f"  Cost: ${result.metrics.get('cost', 0):.2f}\n"
            
        if result.errors and not result.success:
            content += f"\n[red]Errors:[/red]\n"
            for error in result.errors[:3]:  # Show first 3 errors
                content += f"  • {error}\n"
                
        self.console.print(
            Panel(content, title="Phase Complete", border_style=status_style)
        )
        
    def print_task_start(self, task: Task):
        """Print task start message."""
        self.console.print(
            f"[magenta]▶ Starting task:[/magenta] {task.name}",
            highlight=True
        )
        
    def print_task_complete(self, task: Task, success: bool):
        """Print task completion message."""
        icon = "✓" if success else "✗"
        style = "green" if success else "red"
        self.console.print(
            f"[{style}]{icon} Task complete:[/{style}] {task.name}",
            highlight=True
        )
        
    def print_error(self, error: str):
        """Print error message."""
        self.console.print(
            Panel(
                f"[bold red]Error:[/bold red] {error}",
                border_style="red",
                expand=False
            )
        )
        
    def print_warning(self, warning: str):
        """Print warning message."""
        self.console.print(
            f"[yellow]⚠ Warning:[/yellow] {warning}",
            highlight=True
        )
        
    def print_info(self, info: str):
        """Print info message."""
        self.console.print(
            f"[cyan]ℹ Info:[/cyan] {info}",
            highlight=True
        )
        
    def print_success(self, message: str):
        """Print success message."""
        self.console.print(
            f"[green]✓ Success:[/green] {message}",
            highlight=True
        )
        
    def clear(self):
        """Clear the console."""
        self.console.clear()
        
    def get_confirmation(self, prompt: str) -> bool:
        """Get user confirmation."""
        return self.console.input(
            f"[yellow]{prompt}[/yellow] [dim](y/n)[/dim]: "
        ).lower() == 'y'
        
    def get_input(self, prompt: str) -> str:
        """Get user input."""
        return self.console.input(f"[cyan]{prompt}:[/cyan] ")
        
    def show_spinner(self, message: str):
        """Show spinner with message."""
        return self.console.status(message, spinner="dots")
        
    def create_progress(self) -> Progress:
        """Create a progress bar."""
        return Progress(console=self.console)
        
    def register_callback(self, event: str, callback: Callable):
        """Register event callback."""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
        
    def trigger_event(self, event: str, data: Any = None):
        """Trigger registered callbacks."""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                callback(data)
    
    def show_header(self, title: str) -> None:
        """Show header with title.
        
        Args:
            title: Header title
        """
        header_text = Text()
        header_text.append("Claude Code Builder v3.0", style="bold blue")
        header_text.append(" | ", style="dim")
        header_text.append(title, style="bold white")
        
        self.console.print(Panel(header_text, border_style="blue"))
    
    def show_phases_table(self, phases: List[Any]) -> None:
        """Show phases in a table.
        
        Args:
            phases: List of phases
        """
        table = Table(title="Project Phases")
        table.add_column("Phase", style="cyan")
        table.add_column("Description")
        table.add_column("Status")
        
        for i, phase in enumerate(phases, 1):
            status = getattr(phase, 'status', 'pending')
            description = getattr(phase, 'description', '')
            name = getattr(phase, 'name', f'Phase {i}')
            
            table.add_row(name, description[:50] + "..." if len(description) > 50 else description, status)
        
        self.console.print(table)