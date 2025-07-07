"""
Output formatting utilities for Claude Code Builder.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import json
import re

from rich.console import Console
from rich.text import Text
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.columns import Columns
from rich.align import Align
from rich.rule import Rule
from rich.highlighter import RegexHighlighter

from ..models.phase import Phase, PhaseStatus, Task, TaskStatus, TaskResult
from ..models.project import ProjectSpec
from ..models.custom_instructions import InstructionSet
from ..models.cost import CostTracker, SessionInfo


class PathHighlighter(RegexHighlighter):
    """Highlight file paths in text."""
    highlights = [
        r"(?P<path>(?:[a-zA-Z]:)?[/\\](?:[^/\\]+[/\\])*[^/\\]+\.[a-zA-Z]+)",
        r"(?P<dir>(?:[a-zA-Z]:)?[/\\](?:[^/\\]+[/\\])*[^/\\]+[/\\]?)",
    ]


@dataclass
class FormatConfig:
    """Configuration for output formatting."""
    max_width: int = 120
    indent_size: int = 2
    show_timestamps: bool = True
    show_line_numbers: bool = True
    syntax_theme: str = "monokai"
    truncate_long_strings: bool = True
    max_string_length: int = 1000
    highlight_paths: bool = True
    highlight_errors: bool = True
    compact_mode: bool = False


class OutputFormatter:
    """Format various outputs for display."""
    
    def __init__(self, console: Optional[Console] = None,
                 config: Optional[FormatConfig] = None):
        """Initialize formatter."""
        self.console = console or Console()
        self.config = config or FormatConfig()
        self.path_highlighter = PathHighlighter()
    
    def format_phase(self, phase: Phase) -> Panel:
        """Format phase information."""
        # Create phase tree
        tree = Tree(f"[bold cyan]{phase.name}[/bold cyan]")
        
        # Add phase metadata
        metadata = tree.add("[dim]Metadata[/dim]")
        metadata.add(f"ID: {phase.id}")
        metadata.add(f"Status: {self._format_phase_status(phase.status)}")
        metadata.add(f"Tasks: {len(phase.tasks)}")
        
        if phase.started_at:
            metadata.add(f"Started: {self._format_timestamp(phase.started_at)}")
        if phase.completed_at:
            duration = phase.completed_at - phase.started_at
            metadata.add(f"Duration: {self._format_duration(duration)}")
        
        # Add tasks
        if phase.tasks:
            tasks_branch = tree.add("[dim]Tasks[/dim]")
            for task in phase.tasks:
                task_text = f"{self._format_task_status(task.status)} {task.name}"
                task_node = tasks_branch.add(task_text)
                
                if task.result and not self.config.compact_mode:
                    # Add result summary
                    if task.result.files_created:
                        task_node.add(f"[green]Created {len(task.result.files_created)} files[/green]")
                    if task.result.files_modified:
                        task_node.add(f"[yellow]Modified {len(task.result.files_modified)} files[/yellow]")
                    if task.result.errors:
                        task_node.add(f"[red]Errors: {len(task.result.errors)}[/red]")
        
        return Panel(
            tree,
            title=f"Phase: {phase.name}",
            border_style="cyan"
        )
    
    def format_task_result(self, task: Task, result: TaskResult) -> Panel:
        """Format detailed task result."""
        content = []
        
        # Summary
        summary = Table(show_header=False, box=None)
        summary.add_column("Property", style="cyan")
        summary.add_column("Value")
        
        summary.add_row("Task", task.name)
        summary.add_row("Status", self._format_task_status(task.status))
        summary.add_row("Success", "[green]✓[/green]" if result.success else "[red]✗[/red]")
        
        if result.duration_ms:
            summary.add_row("Duration", f"{result.duration_ms}ms")
        
        content.append(summary)
        content.append(Rule())
        
        # Files created
        if result.files_created:
            files_tree = Tree("[green]Files Created[/green]")
            for file_path in sorted(result.files_created):
                files_tree.add(self._format_path(file_path))
            content.append(files_tree)
        
        # Files modified
        if result.files_modified:
            files_tree = Tree("[yellow]Files Modified[/yellow]")
            for file_path in sorted(result.files_modified):
                files_tree.add(self._format_path(file_path))
            content.append(files_tree)
        
        # Output
        if result.output and not self.config.compact_mode:
            content.append(Rule("Output"))
            output_text = self._format_output(result.output)
            content.append(output_text)
        
        # Errors
        if result.errors:
            content.append(Rule("Errors", style="red"))
            for error in result.errors:
                error_panel = Panel(
                    Text(error, style="red"),
                    border_style="red",
                    title="Error"
                )
                content.append(error_panel)
        
        # Metrics
        if result.metrics:
            content.append(Rule("Metrics"))
            metrics_table = Table(show_header=True)
            metrics_table.add_column("Metric", style="cyan")
            metrics_table.add_column("Value", justify="right")
            
            for key, value in result.metrics.items():
                metrics_table.add_row(key, str(value))
            
            content.append(metrics_table)
        
        return Panel(
            Columns(content) if len(content) > 1 else content[0],
            title=f"Task Result: {task.name}",
            border_style="green" if result.success else "red"
        )
    
    def format_project_spec(self, spec: ProjectSpec) -> Panel:
        """Format project specification."""
        tree = Tree(f"[bold cyan]{spec.name}[/bold cyan]")
        
        # Basic info
        info = tree.add("[dim]Project Info[/dim]")
        info.add(f"Version: {spec.version}")
        info.add(f"Type: {spec.project_type}")
        info.add(f"Language: {spec.language}")
        
        # Description
        if spec.description:
            desc = tree.add("[dim]Description[/dim]")
            desc_text = self._truncate_text(spec.description)
            desc.add(Markdown(desc_text))
        
        # Requirements
        if spec.requirements:
            req = tree.add("[dim]Requirements[/dim]")
            for requirement in spec.requirements[:5]:  # Show first 5
                req.add(f"• {requirement}")
            if len(spec.requirements) > 5:
                req.add(f"[dim]... and {len(spec.requirements) - 5} more[/dim]")
        
        # Phases
        phases = tree.add(f"[dim]Phases ({len(spec.phases)})[/dim]")
        for phase in spec.phases[:3]:  # Show first 3
            phase_text = f"{phase.name} ({len(phase.tasks)} tasks)"
            phases.add(phase_text)
        if len(spec.phases) > 3:
            phases.add(f"[dim]... and {len(spec.phases) - 3} more[/dim]")
        
        return Panel(
            tree,
            title="Project Specification",
            border_style="blue"
        )
    
    def format_instructions(self, instructions: InstructionSet) -> Panel:
        """Format custom instructions."""
        content = []
        
        # Global instructions
        if instructions.global_instructions:
            global_panel = Panel(
                Markdown(self._truncate_text(instructions.global_instructions)),
                title="Global Instructions",
                border_style="cyan"
            )
            content.append(global_panel)
        
        # Phase instructions
        if instructions.phase_instructions:
            phase_tree = Tree("[cyan]Phase Instructions[/cyan]")
            for phase_name, instruction in list(instructions.phase_instructions.items())[:5]:
                phase_node = phase_tree.add(f"[bold]{phase_name}[/bold]")
                phase_node.add(self._truncate_text(instruction, 100))
            
            if len(instructions.phase_instructions) > 5:
                phase_tree.add(f"[dim]... and {len(instructions.phase_instructions) - 5} more[/dim]")
            
            content.append(phase_tree)
        
        # Task instructions
        if instructions.task_instructions:
            task_tree = Tree("[cyan]Task Instructions[/cyan]")
            for task_name, instruction in list(instructions.task_instructions.items())[:5]:
                task_node = task_tree.add(f"[bold]{task_name}[/bold]")
                task_node.add(self._truncate_text(instruction, 100))
            
            if len(instructions.task_instructions) > 5:
                task_tree.add(f"[dim]... and {len(instructions.task_instructions) - 5} more[/dim]")
            
            content.append(task_tree)
        
        return Panel(
            Columns(content) if len(content) > 1 else content[0],
            title="Custom Instructions",
            border_style="yellow"
        )
    
    def format_cost_summary(self, tracker: CostTracker) -> Panel:
        """Format cost tracking summary."""
        # Create summary table
        table = Table(show_header=True, title="Cost Summary")
        table.add_column("Category", style="cyan")
        table.add_column("Amount", justify="right", style="green")
        table.add_column("Percentage", justify="right")
        
        total = tracker.get_total_cost()
        
        # Add categories
        categories = [
            ("Claude Code", tracker.claude_code_cost),
            ("Research", tracker.research_cost),
            ("Other", total - tracker.claude_code_cost - tracker.research_cost)
        ]
        
        for category, amount in categories:
            percentage = (amount / total * 100) if total > 0 else 0
            table.add_row(
                category,
                f"${amount:.2f}",
                f"{percentage:.1f}%"
            )
        
        # Add total
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]${total:.2f}[/bold]",
            "[bold]100.0%[/bold]",
            style="bold"
        )
        
        # Add token counts
        table.add_row()  # Empty row
        table.add_row(
            "[dim]Total Tokens[/dim]",
            f"[dim]{tracker.total_tokens:,}[/dim]",
            ""
        )
        
        # Add model breakdown if available
        breakdown = tracker.get_model_breakdown()
        if breakdown:
            table.add_row()  # Empty row
            table.add_row("[dim]By Model:[/dim]", "", "")
            for model, cost in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                table.add_row(
                    f"  {model}",
                    f"${cost:.2f}",
                    f"{(cost/total*100):.1f}%" if total > 0 else "0.0%"
                )
        
        return Panel(table, border_style="green")
    
    def format_error(self, error: Union[str, Exception],
                    context: Optional[Dict[str, Any]] = None) -> Panel:
        """Format error message with context."""
        content = []
        
        # Error message
        if isinstance(error, Exception):
            error_type = type(error).__name__
            error_msg = str(error)
            content.append(Text(f"{error_type}: {error_msg}", style="bold red"))
        else:
            content.append(Text(error, style="bold red"))
        
        # Context information
        if context:
            content.append(Rule())
            context_table = Table(show_header=False, box=None)
            context_table.add_column("Key", style="cyan")
            context_table.add_column("Value")
            
            for key, value in context.items():
                context_table.add_row(key, str(value))
            
            content.append(context_table)
        
        return Panel(
            Columns(content) if len(content) > 1 else content[0],
            title="Error",
            border_style="red"
        )
    
    def format_code(self, code: str, language: str = "python",
                   title: Optional[str] = None) -> Panel:
        """Format code with syntax highlighting."""
        syntax = Syntax(
            code,
            language,
            theme=self.config.syntax_theme,
            line_numbers=self.config.show_line_numbers
        )
        
        return Panel(
            syntax,
            title=title or f"{language.title()} Code",
            border_style="blue"
        )
    
    def format_json(self, data: Any, title: Optional[str] = None) -> Panel:
        """Format JSON data with syntax highlighting."""
        json_str = json.dumps(data, indent=2, default=str)
        return self.format_code(json_str, "json", title or "JSON Data")
    
    def format_markdown(self, content: str, title: Optional[str] = None) -> Panel:
        """Format markdown content."""
        # Truncate if needed
        if self.config.truncate_long_strings and len(content) > self.config.max_string_length:
            content = content[:self.config.max_string_length] + "\n\n[dim]... (truncated)[/dim]"
        
        markdown = Markdown(content)
        
        return Panel(
            markdown,
            title=title or "Markdown",
            border_style="cyan"
        )
    
    def format_tree_structure(self, root_path: Path,
                            include_patterns: Optional[List[str]] = None,
                            exclude_patterns: Optional[List[str]] = None) -> Tree:
        """Format directory tree structure."""
        tree = Tree(f"[bold cyan]{root_path.name}[/bold cyan]")
        
        def should_include(path: Path) -> bool:
            """Check if path should be included."""
            if exclude_patterns:
                for pattern in exclude_patterns:
                    if re.match(pattern, str(path)):
                        return False
            
            if include_patterns:
                for pattern in include_patterns:
                    if re.match(pattern, str(path)):
                        return True
                return False
            
            return True
        
        def add_directory(tree_node: Tree, dir_path: Path, level: int = 0) -> None:
            """Recursively add directory contents."""
            if level > 5:  # Max depth
                tree_node.add("[dim]...[/dim]")
                return
            
            try:
                items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                
                for item in items:
                    if not should_include(item):
                        continue
                    
                    if item.is_dir():
                        dir_node = tree_node.add(f"[blue]{item.name}/[/blue]")
                        add_directory(dir_node, item, level + 1)
                    else:
                        # Add file with size
                        size = item.stat().st_size
                        size_str = self._format_file_size(size)
                        tree_node.add(f"{item.name} [dim]({size_str})[/dim]")
            
            except PermissionError:
                tree_node.add("[red]Permission Denied[/red]")
        
        if root_path.exists() and root_path.is_dir():
            add_directory(tree, root_path)
        else:
            tree.add("[red]Directory not found[/red]")
        
        return tree
    
    # Helper methods
    
    def _format_phase_status(self, status: PhaseStatus) -> str:
        """Format phase status with color."""
        status_map = {
            PhaseStatus.PENDING: "[dim]⏳ Pending[/dim]",
            PhaseStatus.RUNNING: "[blue]🔄 Running[/blue]",
            PhaseStatus.COMPLETED: "[green]✅ Completed[/green]",
            PhaseStatus.FAILED: "[red]❌ Failed[/red]",
            PhaseStatus.SKIPPED: "[yellow]⏭️ Skipped[/yellow]"
        }
        return status_map.get(status, str(status))
    
    def _format_task_status(self, status: TaskStatus) -> str:
        """Format task status with icon."""
        status_map = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.SKIPPED: "⏭️"
        }
        return status_map.get(status, "❓")
    
    def _format_timestamp(self, timestamp: datetime) -> str:
        """Format timestamp."""
        if self.config.show_timestamps:
            return timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return timestamp.strftime("%H:%M:%S")
    
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration in human-readable form."""
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def _format_file_size(self, size: int) -> str:
        """Format file size in human-readable form."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"
    
    def _format_path(self, path: str) -> str:
        """Format file path with highlighting."""
        if self.config.highlight_paths:
            return self.path_highlighter(path)
        return path
    
    def _format_output(self, output: str) -> Union[Text, Syntax]:
        """Format command output."""
        # Try to detect if it's code
        if any(indicator in output for indicator in ['def ', 'class ', 'import ', 'function', '{']):
            # Likely code - use syntax highlighting
            return Syntax(
                output,
                "python",  # Default to Python
                theme=self.config.syntax_theme
            )
        else:
            # Regular text
            return Text(self._truncate_text(output))
    
    def _truncate_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Truncate long text if configured."""
        max_len = max_length or self.config.max_string_length
        
        if self.config.truncate_long_strings and len(text) > max_len:
            return text[:max_len] + "... (truncated)"
        return text


class CompactFormatter(OutputFormatter):
    """Compact formatter for minimal output."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize compact formatter."""
        config = FormatConfig(
            compact_mode=True,
            show_timestamps=False,
            show_line_numbers=False,
            truncate_long_strings=True,
            max_string_length=200
        )
        super().__init__(console, config)
    
    def format_phase(self, phase: Phase) -> str:
        """Format phase as compact string."""
        status_icon = self._format_task_status(phase.status)
        task_summary = f"{sum(1 for t in phase.tasks if t.status == TaskStatus.COMPLETED)}/{len(phase.tasks)}"
        return f"{status_icon} {phase.name} [{task_summary}]"
    
    def format_task_result(self, task: Task, result: TaskResult) -> str:
        """Format task result as compact string."""
        status_icon = self._format_task_status(task.status)
        files_info = []
        
        if result.files_created:
            files_info.append(f"+{len(result.files_created)}")
        if result.files_modified:
            files_info.append(f"~{len(result.files_modified)}")
        if result.errors:
            files_info.append(f"!{len(result.errors)}")
        
        files_str = f" ({', '.join(files_info)})" if files_info else ""
        return f"{status_icon} {task.name}{files_str}"