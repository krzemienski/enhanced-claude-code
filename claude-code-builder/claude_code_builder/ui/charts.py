"""
Chart visualization for cost and performance metrics.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import math

from rich.console import Console, ConsoleOptions, RenderResult
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from rich.align import Align

from ..models.monitoring import Metric, MetricType
from ..models.cost import CostTracker, SessionInfo


class ChartType(Enum):
    """Types of charts available."""
    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    PIE = "pie"
    SPARKLINE = "sparkline"


@dataclass
class ChartConfig:
    """Configuration for chart rendering."""
    width: int = 60
    height: int = 20
    show_title: bool = True
    show_labels: bool = True
    show_values: bool = True
    show_grid: bool = True
    color_scheme: str = "default"
    unicode_bars: bool = True
    decimal_places: int = 2
    
    
@dataclass
class DataPoint:
    """Single data point for charts."""
    x: float
    y: float
    label: Optional[str] = None
    color: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSeries:
    """Series of data points."""
    name: str
    points: List[DataPoint] = field(default_factory=list)
    color: Optional[str] = None
    chart_type: ChartType = ChartType.LINE
    
    def add_point(self, x: float, y: float, **kwargs) -> None:
        """Add a data point to the series."""
        self.points.append(DataPoint(x=x, y=y, **kwargs))
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Get min/max bounds for x and y."""
        if not self.points:
            return 0, 0, 0, 0
        
        x_values = [p.x for p in self.points]
        y_values = [p.y for p in self.points]
        
        return min(x_values), max(x_values), min(y_values), max(y_values)


class AsciiChart:
    """ASCII chart renderer."""
    
    def __init__(self, config: Optional[ChartConfig] = None):
        """Initialize chart renderer."""
        self.config = config or ChartConfig()
        self.series: List[DataSeries] = []
        self.title: Optional[str] = None
        self.x_label: Optional[str] = None
        self.y_label: Optional[str] = None
    
    def add_series(self, series: DataSeries) -> None:
        """Add a data series to the chart."""
        self.series.append(series)
    
    def set_labels(self, title: Optional[str] = None,
                   x_label: Optional[str] = None,
                   y_label: Optional[str] = None) -> None:
        """Set chart labels."""
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
    
    def render(self) -> Panel:
        """Render the chart as a panel."""
        if not self.series:
            return Panel("[dim]No data to display[/dim]", title=self.title or "Chart")
        
        # Determine chart type from first series
        chart_type = self.series[0].chart_type
        
        if chart_type == ChartType.BAR:
            content = self._render_bar_chart()
        elif chart_type == ChartType.LINE:
            content = self._render_line_chart()
        elif chart_type == ChartType.SPARKLINE:
            content = self._render_sparkline()
        elif chart_type == ChartType.PIE:
            content = self._render_pie_chart()
        else:
            content = self._render_line_chart()  # Default
        
        return Panel(
            content,
            title=self.title or "Chart",
            border_style="blue"
        )
    
    def _render_bar_chart(self) -> str:
        """Render a bar chart."""
        if not self.series or not self.series[0].points:
            return "[dim]No data[/dim]"
        
        series = self.series[0]
        points = sorted(series.points, key=lambda p: p.x)
        
        # Calculate scale
        max_value = max(p.y for p in points)
        if max_value == 0:
            max_value = 1
        
        # Unicode bar characters
        if self.config.unicode_bars:
            bars = "▁▂▃▄▅▆▇█"
        else:
            bars = ".:-=+*#%@"
        
        lines = []
        
        # Render bars
        bar_width = max(1, self.config.width // len(points))
        bar_chars = []
        
        for point in points:
            # Calculate bar height
            height = int((point.y / max_value) * self.config.height)
            
            # Build bar
            bar_lines = []
            for h in range(self.config.height):
                if h < self.config.height - height:
                    bar_lines.append(" " * bar_width)
                else:
                    # Select bar character based on fractional part
                    frac = (point.y / max_value) * self.config.height - height + 1
                    char_idx = min(int(frac * len(bars)), len(bars) - 1)
                    bar_lines.append(bars[char_idx] * bar_width)
            
            bar_chars.append(bar_lines)
        
        # Combine bars horizontally
        for h in range(self.config.height):
            line = ""
            for bar in bar_chars:
                line += bar[h]
            
            # Add y-axis label
            if h == 0 and self.config.show_labels:
                label = f"{max_value:.{self.config.decimal_places}f}"
                line = f"{label:>8} │ {line}"
            elif h == self.config.height - 1 and self.config.show_labels:
                line = f"{'0':>8} │ {line}"
            else:
                line = f"{' ':>8} │ {line}"
            
            lines.append(line)
        
        # Add x-axis
        if self.config.show_labels:
            # Axis line
            lines.append(" " * 8 + " └" + "─" * (len(bar_chars) * bar_width))
            
            # Labels
            labels = []
            for point in points:
                label = point.label or f"{point.x:.0f}"
                labels.append(label[:bar_width].center(bar_width))
            lines.append(" " * 10 + "".join(labels))
        
        return "\n".join(lines)
    
    def _render_line_chart(self) -> str:
        """Render a line chart."""
        if not self.series:
            return "[dim]No data[/dim]"
        
        # Get bounds across all series
        min_x, max_x, min_y, max_y = float('inf'), float('-inf'), float('inf'), float('-inf')
        for series in self.series:
            if series.points:
                sx_min, sx_max, sy_min, sy_max = series.get_bounds()
                min_x = min(min_x, sx_min)
                max_x = max(max_x, sx_max)
                min_y = min(min_y, sy_min)
                max_y = max(max_y, sy_max)
        
        if min_x == float('inf'):
            return "[dim]No data[/dim]"
        
        # Ensure we have a range
        if max_x == min_x:
            max_x = min_x + 1
        if max_y == min_y:
            max_y = min_y + 1
        
        # Create grid
        width = self.config.width
        height = self.config.height
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        
        # Plot each series
        markers = ['●', '○', '■', '□', '▲', '△', '◆', '◇']
        for series_idx, series in enumerate(self.series):
            marker = markers[series_idx % len(markers)]
            
            for i, point in enumerate(series.points):
                # Map to grid coordinates
                x = int((point.x - min_x) / (max_x - min_x) * (width - 1))
                y = int((1 - (point.y - min_y) / (max_y - min_y)) * (height - 1))
                
                # Ensure within bounds
                x = max(0, min(width - 1, x))
                y = max(0, min(height - 1, y))
                
                # Plot point
                grid[y][x] = marker
                
                # Draw line to next point
                if i < len(series.points) - 1 and self.config.show_grid:
                    next_point = series.points[i + 1]
                    next_x = int((next_point.x - min_x) / (max_x - min_x) * (width - 1))
                    next_y = int((1 - (next_point.y - min_y) / (max_y - min_y)) * (height - 1))
                    
                    # Simple line drawing
                    steps = max(abs(next_x - x), abs(next_y - y))
                    if steps > 0:
                        for step in range(1, steps):
                            interp_x = int(x + (next_x - x) * step / steps)
                            interp_y = int(y + (next_y - y) * step / steps)
                            if 0 <= interp_x < width and 0 <= interp_y < height:
                                if grid[interp_y][interp_x] == ' ':
                                    grid[interp_y][interp_x] = '·'
        
        # Convert grid to string
        lines = []
        
        for h, row in enumerate(grid):
            line = "".join(row)
            
            # Add y-axis labels
            if self.config.show_labels:
                if h == 0:
                    label = f"{max_y:.{self.config.decimal_places}f}"
                elif h == height - 1:
                    label = f"{min_y:.{self.config.decimal_places}f}"
                else:
                    label = ""
                line = f"{label:>8} │ {line}"
            
            lines.append(line)
        
        # Add x-axis
        if self.config.show_labels:
            # Axis line
            lines.append(" " * 8 + " └" + "─" * width)
            
            # Labels
            x_labels = " " * 10
            label_positions = [0, width // 2, width - 1]
            for pos in label_positions:
                x_val = min_x + (max_x - min_x) * pos / (width - 1)
                label = f"{x_val:.{self.config.decimal_places}f}"
                x_labels += label.ljust(width // 3)
            lines.append(x_labels[:10 + width])
        
        # Add legend if multiple series
        if len(self.series) > 1:
            lines.append("")
            legend = "Legend: "
            for i, series in enumerate(self.series):
                marker = markers[i % len(markers)]
                legend += f"{marker} {series.name}  "
            lines.append(legend)
        
        return "\n".join(lines)
    
    def _render_sparkline(self) -> str:
        """Render a compact sparkline."""
        if not self.series or not self.series[0].points:
            return "[dim]No data[/dim]"
        
        series = self.series[0]
        points = sorted(series.points, key=lambda p: p.x)
        
        # Sparkline characters
        spark_chars = "▁▂▃▄▅▆▇█"
        
        # Get value range
        values = [p.y for p in points]
        min_val = min(values)
        max_val = max(values)
        
        if max_val == min_val:
            return spark_chars[4] * len(points)
        
        # Map values to sparkline characters
        sparkline = ""
        for value in values:
            # Normalize to 0-1
            normalized = (value - min_val) / (max_val - min_val)
            # Map to character index
            idx = int(normalized * (len(spark_chars) - 1))
            sparkline += spark_chars[idx]
        
        # Add min/max labels if configured
        if self.config.show_values:
            return f"{min_val:.{self.config.decimal_places}f} {sparkline} {max_val:.{self.config.decimal_places}f}"
        else:
            return sparkline
    
    def _render_pie_chart(self) -> str:
        """Render a simple pie chart."""
        if not self.series or not self.series[0].points:
            return "[dim]No data[/dim]"
        
        series = self.series[0]
        points = series.points
        
        # Calculate total
        total = sum(p.y for p in points)
        if total == 0:
            return "[dim]No data[/dim]"
        
        # Create percentage table
        table = Table(show_header=True, box=None)
        table.add_column("Category", style="cyan")
        table.add_column("Value", justify="right")
        table.add_column("Percentage", justify="right")
        table.add_column("Bar", width=20)
        
        # Sort by value
        sorted_points = sorted(points, key=lambda p: p.y, reverse=True)
        
        for point in sorted_points:
            percentage = (point.y / total) * 100
            bar_length = int((percentage / 100) * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            table.add_row(
                point.label or f"Item {point.x}",
                f"{point.y:.{self.config.decimal_places}f}",
                f"{percentage:.1f}%",
                f"[blue]{bar}[/blue]"
            )
        
        # Add total row
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]{total:.{self.config.decimal_places}f}[/bold]",
            "[bold]100.0%[/bold]",
            ""
        )
        
        return table


class CostChart:
    """Specialized chart for cost tracking visualization."""
    
    def __init__(self, tracker: CostTracker, config: Optional[ChartConfig] = None):
        """Initialize cost chart."""
        self.tracker = tracker
        self.config = config or ChartConfig()
    
    def render_cost_breakdown(self) -> Panel:
        """Render cost breakdown by category."""
        chart = AsciiChart(self.config)
        series = DataSeries("Costs", chart_type=ChartType.BAR)
        
        # Get cost breakdown
        breakdown = {
            "Claude Code": self.tracker.claude_code_cost,
            "Research": self.tracker.research_cost,
            "Analysis": self.tracker.get_total_cost() - self.tracker.claude_code_cost - self.tracker.research_cost
        }
        
        # Add data points
        for i, (category, cost) in enumerate(breakdown.items()):
            series.add_point(i, cost, label=category)
        
        chart.add_series(series)
        chart.set_labels(
            title="Cost Breakdown by Category",
            x_label="Category",
            y_label="Cost ($)"
        )
        
        return chart.render()
    
    def render_cost_timeline(self, sessions: List[SessionInfo]) -> Panel:
        """Render cost over time."""
        if not sessions:
            return Panel("[dim]No session data available[/dim]", title="Cost Timeline")
        
        chart = AsciiChart(self.config)
        series = DataSeries("Session Costs", chart_type=ChartType.LINE)
        
        # Sort sessions by timestamp
        sorted_sessions = sorted(sessions, key=lambda s: s.timestamp)
        
        # Add cumulative costs
        cumulative = 0.0
        for i, session in enumerate(sorted_sessions):
            cumulative += session.cost
            series.add_point(i, cumulative, label=session.phase)
        
        chart.add_series(series)
        chart.set_labels(
            title="Cumulative Cost Over Time",
            x_label="Session",
            y_label="Total Cost ($)"
        )
        
        return chart.render()
    
    def render_model_usage(self) -> Panel:
        """Render model usage breakdown."""
        chart = AsciiChart(self.config)
        series = DataSeries("Model Usage", chart_type=ChartType.PIE)
        
        # Get model breakdown
        breakdown = self.tracker.get_model_breakdown()
        
        # Add data points
        for i, (model, cost) in enumerate(breakdown.items()):
            series.add_point(i, cost, label=model)
        
        chart.add_series(series)
        chart.set_labels(title="Cost by Model")
        
        return chart.render()


class MetricsChart:
    """Specialized chart for metrics visualization."""
    
    def __init__(self, config: Optional[ChartConfig] = None):
        """Initialize metrics chart."""
        self.config = config or ChartConfig()
        self.metrics_history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def add_metric(self, metric: Metric) -> None:
        """Add a metric to the history."""
        if metric.name not in self.metrics_history:
            self.metrics_history[metric.name] = []
        
        self.metrics_history[metric.name].append((metric.timestamp, metric.value))
        
        # Keep only recent history (last 100 points)
        if len(self.metrics_history[metric.name]) > 100:
            self.metrics_history[metric.name] = self.metrics_history[metric.name][-100:]
    
    def render_metric_sparklines(self) -> Panel:
        """Render sparklines for all metrics."""
        if not self.metrics_history:
            return Panel("[dim]No metrics data[/dim]", title="Metrics")
        
        lines = []
        
        for metric_name, history in sorted(self.metrics_history.items()):
            if not history:
                continue
            
            # Create sparkline chart
            chart = AsciiChart(ChartConfig(
                width=30,
                height=1,
                show_values=True,
                show_labels=False
            ))
            
            series = DataSeries(metric_name, chart_type=ChartType.SPARKLINE)
            
            # Add recent values
            for i, (timestamp, value) in enumerate(history[-30:]):
                series.add_point(i, value)
            
            chart.add_series(series)
            
            # Format metric name
            display_name = metric_name.replace("_", " ").title()
            
            # Render sparkline
            sparkline = chart._render_sparkline()
            
            # Add to output
            lines.append(f"{display_name:.<30} {sparkline}")
        
        return Panel(
            "\n".join(lines),
            title="Metrics Overview",
            border_style="cyan"
        )
    
    def render_metric_detail(self, metric_name: str) -> Panel:
        """Render detailed chart for a specific metric."""
        if metric_name not in self.metrics_history:
            return Panel(
                f"[dim]No data for metric: {metric_name}[/dim]",
                title=metric_name
            )
        
        history = self.metrics_history[metric_name]
        
        chart = AsciiChart(self.config)
        series = DataSeries(metric_name, chart_type=ChartType.LINE)
        
        # Add data points
        for i, (timestamp, value) in enumerate(history):
            series.add_point(i, value)
        
        chart.add_series(series)
        chart.set_labels(
            title=metric_name.replace("_", " ").title(),
            x_label="Time",
            y_label="Value"
        )
        
        return chart.render()