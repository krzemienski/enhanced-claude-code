"""
Live status panel for real-time updates.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import asyncio
from enum import Enum

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..models.phase import Phase, PhaseStatus, Task, TaskStatus
from ..models.monitoring import Metric, MetricType, LogEntry, LogLevel
from ..execution import OrchestrationState


class StatusType(Enum):
    """Types of status indicators."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PAUSED = "paused"


@dataclass
class StatusItem:
    """Individual status item."""
    key: str
    label: str
    value: Any
    status: StatusType = StatusType.IDLE
    timestamp: datetime = field(default_factory=datetime.now)
    details: Optional[str] = None
    
    def get_icon(self) -> str:
        """Get icon for status type."""
        icons = {
            StatusType.IDLE: "⚪",
            StatusType.RUNNING: "🔵",
            StatusType.SUCCESS: "🟢",
            StatusType.WARNING: "🟡",
            StatusType.ERROR: "🔴",
            StatusType.PAUSED: "⏸️"
        }
        return icons.get(self.status, "⚪")
    
    def get_color(self) -> str:
        """Get color for status type."""
        colors = {
            StatusType.IDLE: "dim",
            StatusType.RUNNING: "blue",
            StatusType.SUCCESS: "green",
            StatusType.WARNING: "yellow",
            StatusType.ERROR: "red",
            StatusType.PAUSED: "cyan"
        }
        return colors.get(self.status, "white")


@dataclass
class StatusSection:
    """Section of related status items."""
    name: str
    items: List[StatusItem] = field(default_factory=list)
    expanded: bool = True
    
    def add_item(self, item: StatusItem) -> None:
        """Add status item to section."""
        # Update existing item or add new
        for i, existing in enumerate(self.items):
            if existing.key == item.key:
                self.items[i] = item
                return
        self.items.append(item)
    
    def get_item(self, key: str) -> Optional[StatusItem]:
        """Get item by key."""
        for item in self.items:
            if item.key == key:
                return item
        return None
    
    def remove_item(self, key: str) -> None:
        """Remove item by key."""
        self.items = [item for item in self.items if item.key != key]


@dataclass
class StatusPanelConfig:
    """Configuration for status panel."""
    title: str = "Status"
    refresh_rate: float = 0.5
    show_timestamps: bool = True
    show_icons: bool = True
    compact_mode: bool = False
    max_items_per_section: int = 10
    auto_collapse_sections: bool = True
    highlight_changes: bool = True
    change_highlight_duration: float = 2.0


class StatusPanel:
    """Live status panel with real-time updates."""
    
    def __init__(self, console: Optional[Console] = None, 
                 config: Optional[StatusPanelConfig] = None):
        """Initialize status panel."""
        self.console = console or Console()
        self.config = config or StatusPanelConfig()
        self.sections: Dict[str, StatusSection] = {}
        self._running = False
        self._live: Optional[Live] = None
        self._update_callbacks: List[Callable] = []
        self._last_update = datetime.now()
        self._change_highlights: Dict[str, datetime] = {}
    
    def add_section(self, name: str, expanded: bool = True) -> StatusSection:
        """Add a new status section."""
        section = StatusSection(name=name, expanded=expanded)
        self.sections[name] = section
        return section
    
    def update_status(self, section: str, key: str, label: str, 
                     value: Any, status: StatusType = StatusType.IDLE,
                     details: Optional[str] = None) -> None:
        """Update a status item."""
        if section not in self.sections:
            self.add_section(section)
        
        item = StatusItem(
            key=key,
            label=label,
            value=value,
            status=status,
            details=details
        )
        
        self.sections[section].add_item(item)
        
        # Track change for highlighting
        if self.config.highlight_changes:
            self._change_highlights[f"{section}.{key}"] = datetime.now()
        
        # Trigger update callbacks
        for callback in self._update_callbacks:
            callback(section, item)
    
    def update_from_phase(self, phase: Phase) -> None:
        """Update status from phase information."""
        # Update phase status
        self.update_status(
            "Phase",
            "current",
            "Current Phase",
            phase.name,
            self._phase_status_to_status_type(phase.status)
        )
        
        # Update task counts
        total_tasks = len(phase.tasks)
        completed_tasks = sum(1 for t in phase.tasks if t.status == TaskStatus.COMPLETED)
        
        self.update_status(
            "Phase",
            "progress",
            "Task Progress",
            f"{completed_tasks}/{total_tasks}",
            StatusType.RUNNING if completed_tasks < total_tasks else StatusType.SUCCESS
        )
        
        # Update current task
        current_task = next((t for t in phase.tasks if t.status == TaskStatus.IN_PROGRESS), None)
        if current_task:
            self.update_status(
                "Current Task",
                "name",
                "Task",
                current_task.name,
                StatusType.RUNNING
            )
    
    def update_from_metrics(self, metrics: List[Metric]) -> None:
        """Update status from metrics."""
        for metric in metrics:
            section = "Metrics"
            status_type = StatusType.IDLE
            
            # Determine status based on metric value
            if metric.metric_type == MetricType.PERCENTAGE:
                if metric.value > 90:
                    status_type = StatusType.WARNING
                elif metric.value > 95:
                    status_type = StatusType.ERROR
            elif metric.metric_type == MetricType.RATE:
                if metric.value > metric.metadata.get("threshold", float('inf')):
                    status_type = StatusType.WARNING
            
            self.update_status(
                section,
                metric.name,
                metric.name.replace("_", " ").title(),
                f"{metric.value:.2f}{metric.unit}",
                status_type
            )
    
    def add_update_callback(self, callback: Callable) -> None:
        """Add callback for status updates."""
        self._update_callbacks.append(callback)
    
    def _phase_status_to_status_type(self, phase_status: PhaseStatus) -> StatusType:
        """Convert phase status to status type."""
        mapping = {
            PhaseStatus.PENDING: StatusType.IDLE,
            PhaseStatus.RUNNING: StatusType.RUNNING,
            PhaseStatus.COMPLETED: StatusType.SUCCESS,
            PhaseStatus.FAILED: StatusType.ERROR,
            PhaseStatus.SKIPPED: StatusType.WARNING
        }
        return mapping.get(phase_status, StatusType.IDLE)
    
    def _should_highlight(self, key: str) -> bool:
        """Check if item should be highlighted."""
        if not self.config.highlight_changes:
            return False
        
        if key not in self._change_highlights:
            return False
        
        elapsed = (datetime.now() - self._change_highlights[key]).total_seconds()
        return elapsed < self.config.change_highlight_duration
    
    def _render_section(self, section: StatusSection) -> Panel:
        """Render a status section."""
        if not section.expanded and not self.config.compact_mode:
            # Collapsed section
            return Panel(
                f"[dim]({len(section.items)} items)[/dim]",
                title=f"▶ {section.name}",
                border_style="dim"
            )
        
        # Create table for items
        table = Table(show_header=False, box=None, padding=(0, 1))
        
        if self.config.show_icons:
            table.add_column("Icon", width=2)
        table.add_column("Label", style="cyan")
        table.add_column("Value", style="white")
        if self.config.show_timestamps and not self.config.compact_mode:
            table.add_column("Time", style="dim")
        
        # Add items (limited by max_items_per_section)
        items_to_show = section.items[:self.config.max_items_per_section]
        for item in items_to_show:
            row = []
            
            if self.config.show_icons:
                row.append(item.get_icon())
            
            # Label with highlighting
            label = item.label
            if self._should_highlight(f"{section.name}.{item.key}"):
                label = f"[bold yellow]{label}[/bold yellow]"
            row.append(label)
            
            # Value with color
            value_text = Text(str(item.value), style=item.get_color())
            row.append(value_text)
            
            # Timestamp
            if self.config.show_timestamps and not self.config.compact_mode:
                time_str = item.timestamp.strftime("%H:%M:%S")
                row.append(time_str)
            
            table.add_row(*row)
        
        # Add overflow indicator
        if len(section.items) > self.config.max_items_per_section:
            overflow_count = len(section.items) - self.config.max_items_per_section
            table.add_row(
                "" if self.config.show_icons else None,
                f"[dim]... and {overflow_count} more[/dim]",
                "",
                "" if self.config.show_timestamps and not self.config.compact_mode else None
            )
        
        # Create panel
        title = f"{'▼' if section.expanded else '▶'} {section.name}"
        return Panel(
            table,
            title=title,
            border_style="blue" if any(
                item.status == StatusType.RUNNING for item in section.items
            ) else "white"
        )
    
    def render(self) -> Layout:
        """Render the complete status panel."""
        # Create sections layout
        sections = []
        for section in self.sections.values():
            sections.append(self._render_section(section))
        
        # Create main panel
        if sections:
            content = Group(*sections)
        else:
            content = Align.center(
                "[dim]No status information available[/dim]",
                vertical="middle"
            )
        
        # Update timestamp
        timestamp = ""
        if self.config.show_timestamps:
            timestamp = f" [dim]({datetime.now().strftime('%H:%M:%S')})[/dim]"
        
        return Panel(
            content,
            title=f"{self.config.title}{timestamp}",
            border_style="green"
        )
    
    async def start(self) -> None:
        """Start live status updates."""
        self._running = True
        
        with Live(
            self.render(),
            console=self.console,
            refresh_per_second=1 / self.config.refresh_rate
        ) as live:
            self._live = live
            
            while self._running:
                # Update display
                live.update(self.render())
                
                # Clean old highlights
                now = datetime.now()
                self._change_highlights = {
                    k: v for k, v in self._change_highlights.items()
                    if (now - v).total_seconds() < self.config.change_highlight_duration * 2
                }
                
                # Sleep for refresh interval
                await asyncio.sleep(self.config.refresh_rate)
    
    def stop(self) -> None:
        """Stop live updates."""
        self._running = False
    
    def clear(self) -> None:
        """Clear all status information."""
        self.sections.clear()
        self._change_highlights.clear()


class MultiStatusPanel:
    """Multiple status panels in a layout."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize multi-panel display."""
        self.console = console or Console()
        self.panels: Dict[str, StatusPanel] = {}
        self.layout = Layout()
        self._running = False
    
    def add_panel(self, name: str, panel: StatusPanel, 
                  size: Optional[int] = None) -> None:
        """Add a status panel to the layout."""
        self.panels[name] = panel
        self._update_layout()
    
    def _update_layout(self) -> None:
        """Update the layout with current panels."""
        if len(self.panels) == 1:
            # Single panel
            panel_name, panel = next(iter(self.panels.items()))
            self.layout = Layout(panel.render())
        elif len(self.panels) == 2:
            # Side by side
            panels = list(self.panels.values())
            self.layout.split_row(
                Layout(panels[0].render()),
                Layout(panels[1].render())
            )
        else:
            # Grid layout
            rows = []
            panels = list(self.panels.values())
            for i in range(0, len(panels), 2):
                if i + 1 < len(panels):
                    row = Layout()
                    row.split_row(
                        Layout(panels[i].render()),
                        Layout(panels[i + 1].render())
                    )
                    rows.append(row)
                else:
                    rows.append(Layout(panels[i].render()))
            
            self.layout.split_column(*rows)
    
    async def start(self) -> None:
        """Start all panels."""
        self._running = True
        
        with Live(
            self.layout,
            console=self.console,
            refresh_per_second=2
        ) as live:
            while self._running:
                # Update layout
                self._update_layout()
                live.update(self.layout)
                
                # Sleep briefly
                await asyncio.sleep(0.5)
    
    def stop(self) -> None:
        """Stop all panels."""
        self._running = False
        for panel in self.panels.values():
            panel.stop()