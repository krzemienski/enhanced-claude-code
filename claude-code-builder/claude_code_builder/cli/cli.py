"""Command-line interface for Claude Code Builder."""
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
import argparse

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from ..config.settings import Settings
from ..logging.logger import get_logger
from ..exceptions.base import ClaudeCodeBuilderError
from ..ui.terminal import RichTerminal
from ..execution.orchestrator import ExecutionOrchestrator as ProjectOrchestrator
from ..models.project import ProjectSpec
from ..utils.file_handler import FileHandler
from .commands import CommandHandler

logger = get_logger(__name__)


class CLI:
    """Main CLI interface for Claude Code Builder."""
    
    def __init__(self, settings: Settings, args: argparse.Namespace):
        """Initialize CLI.
        
        Args:
            settings: Application settings
            args: Command-line arguments
        """
        self.settings = settings
        self.args = args
        self.console = Console(
            force_terminal=True,
            force_interactive=True,
            no_color=args.no_color
        )
        self.terminal = RichTerminal(self.console)
        self.file_handler = FileHandler()
        self.command_handler = CommandHandler(self)
        
    async def run(self) -> int:
        """Run the CLI command.
        
        Returns:
            Exit code
        """
        try:
            # Route to appropriate command handler
            command = self.args.command
            
            if hasattr(self.command_handler, f"handle_{command}"):
                handler = getattr(self.command_handler, f"handle_{command}")
                return await handler(self.args)
            else:
                self.console.print(f"[red]Unknown command: {command}[/red]")
                return 1
                
        except ClaudeCodeBuilderError as e:
            self._handle_error(e)
            return 1
        except Exception as e:
            self._handle_unexpected_error(e)
            return 2
    
    async def build_project(self, spec_path: Path) -> int:
        """Build a project from specification.
        
        Args:
            spec_path: Path to specification file
            
        Returns:
            Exit code
        """
        # Show build header
        self.terminal.show_header(f"Building project from {spec_path.name}")
        
        # Load specification
        self.console.print("\n[cyan]Loading project specification...[/cyan]")
        spec_content = self.file_handler.read_file(spec_path)
        
        # Parse specification
        project_spec = ProjectSpec.from_markdown(spec_content)
        
        # Show project summary
        self._show_project_summary(project_spec)
        
        # Confirm build
        if not self.args.dry_run and not self.args.yes:
            if not Confirm.ask("\nProceed with build?"):
                self.console.print("[yellow]Build cancelled[/yellow]")
                return 0
        
        # Setup output directory
        output_dir = self.args.output_dir or Path(project_spec.name.lower().replace(' ', '-'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize orchestrator
        orchestrator = ProjectOrchestrator(
            project_spec=project_spec,
            settings=self.settings,
            output_dir=output_dir,
            terminal=self.terminal
        )
        
        # Show phases
        self.terminal.show_phases_table(orchestrator.phases)
        
        if self.args.dry_run:
            self.console.print("\n[yellow]Dry run completed[/yellow]")
            return 0
        
        # Execute build
        self.console.print("\n[green]Starting build...[/green]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Building project...", total=None)
            
            try:
                result = await orchestrator.execute()
                progress.update(task, completed=True)
                
                # Show results
                self._show_build_results(result)
                
                return 0 if result.success else 1
                
            except Exception as e:
                progress.update(task, description=f"[red]Build failed: {e}[/red]")
                raise
    
    def _show_project_summary(self, project_spec: ProjectSpec) -> None:
        """Show project summary.
        
        Args:
            project_spec: Project specification
        """
        table = Table(title="Project Summary", show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        
        table.add_row("Name", project_spec.name)
        table.add_row("Description", project_spec.description[:100] + "..." if len(project_spec.description) > 100 else project_spec.description)
        table.add_row("Type", project_spec.project_type)
        table.add_row("Language", project_spec.language)
        table.add_row("Framework", project_spec.framework or "None")
        
        if project_spec.requirements:
            table.add_row("Requirements", f"{len(project_spec.requirements)} items")
        
        if project_spec.constraints:
            table.add_row("Constraints", f"{len(project_spec.constraints)} items")
        
        self.console.print(table)
    
    def _show_build_results(self, result: Any) -> None:
        """Show build results.
        
        Args:
            result: Build result
        """
        if result.success:
            self.console.print("\n[green]✓ Build completed successfully![/green]")
            
            # Show metrics
            if hasattr(result, 'metrics'):
                table = Table(title="Build Metrics")
                table.add_column("Metric")
                table.add_column("Value", style="cyan")
                
                table.add_row("Duration", f"{result.duration:.2f}s")
                table.add_row("Phases Completed", str(result.phases_completed))
                table.add_row("Files Created", str(result.files_created))
                table.add_row("Total Tokens", f"{result.total_tokens:,}")
                table.add_row("Estimated Cost", f"${result.estimated_cost:.2f}")
                
                self.console.print(table)
        else:
            self.console.print("\n[red]✗ Build failed![/red]")
            
            if hasattr(result, 'error'):
                self.console.print(f"\n[red]Error:[/red] {result.error}")
            
            if hasattr(result, 'failed_phase'):
                self.console.print(f"[red]Failed at phase:[/red] {result.failed_phase}")
    
    def _handle_error(self, error: ClaudeCodeBuilderError) -> None:
        """Handle application error.
        
        Args:
            error: Application error
        """
        self.console.print(f"\n[red]Error:[/red] {error}")
        
        if error.details:
            self.console.print("\n[yellow]Details:[/yellow]")
            for key, value in error.details.items():
                self.console.print(f"  {key}: {value}")
        
        if self.args.debug and error.cause:
            self.console.print(f"\n[yellow]Caused by:[/yellow] {error.cause}")
    
    def _handle_unexpected_error(self, error: Exception) -> None:
        """Handle unexpected error.
        
        Args:
            error: Unexpected error
        """
        self.console.print(f"\n[red]Unexpected error:[/red] {error}")
        
        if self.args.debug:
            import traceback
            self.console.print("\n[yellow]Traceback:[/yellow]")
            self.console.print(traceback.format_exc())
        else:
            self.console.print("\n[dim]Run with --debug for full traceback[/dim]")
    
    def prompt(
        self,
        message: str,
        default: Optional[str] = None,
        choices: Optional[List[str]] = None
    ) -> str:
        """Prompt user for input.
        
        Args:
            message: Prompt message
            default: Default value
            choices: Valid choices
            
        Returns:
            User input
        """
        return Prompt.ask(
            message,
            default=default,
            choices=choices,
            console=self.console
        )
    
    def confirm(self, message: str, default: bool = False) -> bool:
        """Prompt user for confirmation.
        
        Args:
            message: Confirmation message
            default: Default value
            
        Returns:
            User confirmation
        """
        return Confirm.ask(message, default=default, console=self.console)
    
    def show_panel(
        self,
        content: str,
        title: Optional[str] = None,
        style: str = "cyan"
    ) -> None:
        """Show content in a panel.
        
        Args:
            content: Panel content
            title: Panel title
            style: Panel style
        """
        panel = Panel(content, title=title, style=style)
        self.console.print(panel)