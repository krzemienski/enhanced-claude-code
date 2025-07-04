"""CLI command handlers for Claude Code Builder."""
import asyncio
import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
import argparse

from rich.table import Table
from rich.tree import Tree
from rich.syntax import Syntax

from ..models.project import ProjectSpec
from ..ai.planner import AIPlanner as ProjectPlanner
from ..ai.analyzer import SpecificationAnalyzer as ProjectAnalyzer
from ..mcp.discovery import MCPDiscovery
from ..mcp.installer import MCPInstaller
from ..mcp.registry import MCPRegistry
from ..validation.syntax_validator import SyntaxValidator
from ..execution.checkpoint import CheckpointManager
from ..execution.state_manager import StateManager
from ..utils.file_handler import FileHandler
from ..utils.json_utils import dumps_json
from ..utils.config_loader import ConfigLoader
from ..logging.logger import get_logger
from .plugins import PluginManager
from .config_manager import ConfigManager

logger = get_logger(__name__)


class CommandHandler:
    """Handles CLI commands for Claude Code Builder."""
    
    def __init__(self, cli):
        """Initialize command handler.
        
        Args:
            cli: CLI instance
        """
        self.cli = cli
        self.file_handler = FileHandler()
        self.plugin_manager = PluginManager()
        self.config_manager = ConfigManager(cli.settings)
        
    async def handle_build(self, args: argparse.Namespace) -> int:
        """Handle build command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        return await self.cli.build_project(args.specification)
    
    async def handle_plan(self, args: argparse.Namespace) -> int:
        """Handle plan command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        self.cli.terminal.show_header(f"Planning project from {args.specification.name}")
        
        # Load specification
        self.cli.console.print("\n[cyan]Loading project specification...[/cyan]")
        spec_content = self.file_handler.read_file(args.specification)
        
        # Parse specification
        project_spec = ProjectSpec.from_markdown(spec_content)
        
        # Create planner
        planner = ProjectPlanner(self.cli.settings)
        
        # Generate plan
        with self.cli.console.status("[cyan]Generating project plan...[/cyan]"):
            plan = await planner.create_plan(project_spec)
        
        # Show plan summary
        self._show_plan_summary(plan)
        
        # Save plan if output specified
        if args.output:
            self._save_plan(plan, args.output, args.format)
            self.cli.console.print(f"\n[green]Plan saved to {args.output}[/green]")
        
        return 0
    
    async def handle_resume(self, args: argparse.Namespace) -> int:
        """Handle resume command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        # Find project directory
        project_dir = args.project_dir or Path.cwd()
        
        # Initialize checkpoint manager
        checkpoint_manager = CheckpointManager(project_dir)
        
        # Load checkpoint
        if args.checkpoint == 'latest':
            checkpoint = checkpoint_manager.get_latest_checkpoint()
            if not checkpoint:
                self.cli.console.print("[red]No checkpoints found[/red]")
                return 1
        else:
            checkpoint = checkpoint_manager.load_checkpoint(args.checkpoint)
            if not checkpoint:
                self.cli.console.print(f"[red]Checkpoint not found: {args.checkpoint}[/red]")
                return 1
        
        self.cli.console.print(f"\n[cyan]Resuming from checkpoint: {checkpoint.id}[/cyan]")
        self.cli.console.print(f"Phase: {checkpoint.phase}")
        self.cli.console.print(f"Progress: {checkpoint.progress * 100:.1f}%")
        
        # Confirm resume
        if not self.cli.confirm("\nResume build?"):
            return 0
        
        # Load project spec from checkpoint
        project_spec = checkpoint.project_spec
        
        # Initialize orchestrator with checkpoint
        from ..execution.orchestrator import ProjectOrchestrator
        orchestrator = ProjectOrchestrator(
            project_spec=project_spec,
            settings=self.cli.settings,
            output_dir=project_dir,
            terminal=self.cli.terminal,
            checkpoint=checkpoint
        )
        
        # Resume execution
        result = await orchestrator.execute()
        
        # Show results
        self.cli._show_build_results(result)
        
        return 0 if result.success else 1
    
    async def handle_validate(self, args: argparse.Namespace) -> int:
        """Handle validate command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        self.cli.terminal.show_header(f"Validating {args.specification.name}")
        
        # Load specification
        spec_content = self.file_handler.read_file(args.specification)
        
        # Parse specification
        try:
            project_spec = ProjectSpec.from_markdown(spec_content)
        except Exception as e:
            self.cli.console.print(f"[red]Failed to parse specification: {e}[/red]")
            return 1
        
        # Create analyzer
        analyzer = ProjectAnalyzer()
        
        # Analyze project
        with self.cli.console.status("[cyan]Analyzing project...[/cyan]"):
            analysis = await analyzer.analyze(project_spec)
        
        # Show validation results
        self._show_validation_results(project_spec, analysis, args.strict)
        
        # Return based on validation status
        return 0 if analysis.is_valid else 1
    
    async def handle_mcp(self, args: argparse.Namespace) -> int:
        """Handle MCP commands.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        if args.mcp_command == 'list':
            return await self._handle_mcp_list(args)
        elif args.mcp_command == 'install':
            return await self._handle_mcp_install(args)
        elif args.mcp_command == 'discover':
            return await self._handle_mcp_discover(args)
        
        return 1
    
    async def _handle_mcp_list(self, args: argparse.Namespace) -> int:
        """Handle MCP list command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        registry = MCPRegistry()
        
        if args.installed:
            servers = registry.get_installed_servers()
            title = "Installed MCP Servers"
        else:
            servers = registry.get_available_servers()
            title = "Available MCP Servers"
        
        if not servers:
            self.cli.console.print(f"[yellow]No {title.lower()} found[/yellow]")
            return 0
        
        # Create table
        table = Table(title=title)
        table.add_column("Name", style="cyan")
        table.add_column("Version")
        table.add_column("Description")
        table.add_column("Status", style="green")
        
        for server in servers:
            status = "Installed" if server.installed else "Available"
            table.add_row(
                server.name,
                server.version,
                server.description[:50] + "..." if len(server.description) > 50 else server.description,
                status
            )
        
        self.cli.console.print(table)
        return 0
    
    async def _handle_mcp_install(self, args: argparse.Namespace) -> int:
        """Handle MCP install command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        installer = MCPInstaller()
        
        self.cli.console.print(f"\n[cyan]Installing MCP server: {args.server}[/cyan]")
        
        try:
            with self.cli.console.status(f"Installing {args.server}..."):
                result = await installer.install_server(args.server)
            
            if result.success:
                self.cli.console.print(f"[green]✓ Successfully installed {args.server}[/green]")
                return 0
            else:
                self.cli.console.print(f"[red]✗ Failed to install {args.server}[/red]")
                if result.error:
                    self.cli.console.print(f"[red]Error:[/red] {result.error}")
                return 1
                
        except Exception as e:
            self.cli.console.print(f"[red]Installation failed: {e}[/red]")
            return 1
    
    async def _handle_mcp_discover(self, args: argparse.Namespace) -> int:
        """Handle MCP discover command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        # Load specification
        spec_content = self.file_handler.read_file(args.specification)
        project_spec = ProjectSpec.from_markdown(spec_content)
        
        # Discover servers
        discovery = MCPDiscovery()
        
        with self.cli.console.status("[cyan]Discovering MCP servers...[/cyan]"):
            recommendations = await discovery.discover_servers(project_spec)
        
        if not recommendations:
            self.cli.console.print("[yellow]No MCP servers recommended[/yellow]")
            return 0
        
        # Show recommendations
        table = Table(title="Recommended MCP Servers")
        table.add_column("Server", style="cyan")
        table.add_column("Reason")
        table.add_column("Priority", style="yellow")
        
        for rec in recommendations:
            table.add_row(
                rec.server_name,
                rec.reason,
                rec.priority.value
            )
        
        self.cli.console.print(table)
        return 0
    
    async def handle_plugin(self, args: argparse.Namespace) -> int:
        """Handle plugin commands.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        if args.plugin_command == 'list':
            return await self._handle_plugin_list()
        elif args.plugin_command == 'install':
            return await self._handle_plugin_install(args)
        
        return 1
    
    async def _handle_plugin_list(self) -> int:
        """Handle plugin list command.
        
        Returns:
            Exit code
        """
        plugins = self.plugin_manager.list_plugins()
        
        if not plugins:
            self.cli.console.print("[yellow]No plugins found[/yellow]")
            return 0
        
        table = Table(title="Installed Plugins")
        table.add_column("Name", style="cyan")
        table.add_column("Version")
        table.add_column("Description")
        table.add_column("Status")
        
        for plugin in plugins:
            status = "Active" if plugin.enabled else "Disabled"
            table.add_row(
                plugin.name,
                plugin.version,
                plugin.description,
                status
            )
        
        self.cli.console.print(table)
        return 0
    
    async def _handle_plugin_install(self, args: argparse.Namespace) -> int:
        """Handle plugin install command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        self.cli.console.print(f"\n[cyan]Installing plugin: {args.plugin}[/cyan]")
        
        try:
            with self.cli.console.status(f"Installing {args.plugin}..."):
                result = await self.plugin_manager.install_plugin(args.plugin)
            
            if result:
                self.cli.console.print(f"[green]✓ Successfully installed {args.plugin}[/green]")
                return 0
            else:
                self.cli.console.print(f"[red]✗ Failed to install {args.plugin}[/red]")
                return 1
                
        except Exception as e:
            self.cli.console.print(f"[red]Installation failed: {e}[/red]")
            return 1
    
    async def handle_config(self, args: argparse.Namespace) -> int:
        """Handle config commands.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        if args.config_command == 'show':
            return await self._handle_config_show()
        elif args.config_command == 'set':
            return await self._handle_config_set(args)
        elif args.config_command == 'init':
            return await self._handle_config_init(args)
        
        return 1
    
    async def _handle_config_show(self) -> int:
        """Handle config show command.
        
        Returns:
            Exit code
        """
        config = self.config_manager.get_all()
        
        # Create tree view
        tree = Tree("Configuration")
        
        def add_items(parent, items, prefix=""):
            for key, value in items.items():
                if isinstance(value, dict):
                    branch = parent.add(f"[cyan]{key}[/cyan]")
                    add_items(branch, value, f"{prefix}{key}.")
                else:
                    parent.add(f"[cyan]{key}[/cyan] = {value}")
        
        add_items(tree, config)
        self.cli.console.print(tree)
        
        return 0
    
    async def _handle_config_set(self, args: argparse.Namespace) -> int:
        """Handle config set command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        # Parse value
        try:
            # Try to parse as JSON first
            value = json.loads(args.value)
        except:
            # Use as string
            value = args.value
        
        # Set config value
        self.config_manager.set(args.key, value)
        
        # Save config
        self.config_manager.save()
        
        self.cli.console.print(f"[green]✓ Set {args.key} = {value}[/green]")
        return 0
    
    async def _handle_config_init(self, args: argparse.Namespace) -> int:
        """Handle config init command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code
        """
        config_path = Path.cwd() / ".claude-code-builder.yaml"
        
        if config_path.exists() and not args.force:
            self.cli.console.print("[yellow]Configuration file already exists[/yellow]")
            if not self.cli.confirm("Overwrite existing config?"):
                return 0
        
        # Create default config
        default_config = {
            'api_key': 'your-api-key-here',
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 100000,
            'mcp_servers': {},
            'research': {
                'enabled': True,
                'api_key': 'optional-perplexity-key'
            },
            'ui': {
                'rich': True,
                'color': True
            },
            'cache': {
                'enabled': True,
                'ttl': 3600
            }
        }
        
        # Save config
        self.file_handler.write_yaml(config_path, default_config)
        
        self.cli.console.print(f"[green]✓ Created configuration file: {config_path}[/green]")
        self.cli.console.print("\n[yellow]Please edit the file and add your API key[/yellow]")
        
        return 0
    
    def _show_plan_summary(self, plan: Any) -> None:
        """Show plan summary.
        
        Args:
            plan: Project plan
        """
        # Show phases
        table = Table(title="Project Phases")
        table.add_column("Phase", style="cyan")
        table.add_column("Tasks")
        table.add_column("Estimated Tokens")
        table.add_column("Dependencies")
        
        for phase in plan.phases:
            deps = ", ".join(phase.dependencies) if phase.dependencies else "None"
            table.add_row(
                phase.name,
                str(len(phase.tasks)),
                f"{phase.estimated_tokens:,}",
                deps
            )
        
        self.cli.console.print(table)
        
        # Show totals
        total_tasks = sum(len(p.tasks) for p in plan.phases)
        total_tokens = sum(p.estimated_tokens for p in plan.phases)
        
        self.cli.console.print(f"\n[cyan]Total phases:[/cyan] {len(plan.phases)}")
        self.cli.console.print(f"[cyan]Total tasks:[/cyan] {total_tasks}")
        self.cli.console.print(f"[cyan]Estimated tokens:[/cyan] {total_tokens:,}")
        self.cli.console.print(f"[cyan]Estimated cost:[/cyan] ${plan.estimated_cost:.2f}")
    
    def _save_plan(self, plan: Any, output_path: Path, format: str) -> None:
        """Save plan to file.
        
        Args:
            plan: Project plan
            output_path: Output file path
            format: Output format
        """
        plan_data = plan.to_dict()
        
        if format == 'json':
            self.file_handler.write_json(output_path, plan_data)
        elif format == 'yaml':
            self.file_handler.write_yaml(output_path, plan_data)
        elif format == 'markdown':
            # Convert to markdown
            md_content = self._plan_to_markdown(plan)
            self.file_handler.write_file(output_path, md_content)
    
    def _plan_to_markdown(self, plan: Any) -> str:
        """Convert plan to markdown format.
        
        Args:
            plan: Project plan
            
        Returns:
            Markdown content
        """
        lines = [
            f"# Project Plan: {plan.project_name}",
            "",
            f"**Total Phases:** {len(plan.phases)}",
            f"**Estimated Tokens:** {sum(p.estimated_tokens for p in plan.phases):,}",
            f"**Estimated Cost:** ${plan.estimated_cost:.2f}",
            "",
            "## Phases",
            ""
        ]
        
        for i, phase in enumerate(plan.phases, 1):
            lines.extend([
                f"### Phase {i}: {phase.name}",
                "",
                f"**Tasks:** {len(phase.tasks)}",
                f"**Tokens:** {phase.estimated_tokens:,}",
                f"**Dependencies:** {', '.join(phase.dependencies) if phase.dependencies else 'None'}",
                "",
                "#### Tasks:",
                ""
            ])
            
            for task in phase.tasks:
                lines.append(f"- {task.name}")
                if task.description:
                    lines.append(f"  - {task.description}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _show_validation_results(
        self,
        project_spec: ProjectSpec,
        analysis: Any,
        strict: bool
    ) -> None:
        """Show validation results.
        
        Args:
            project_spec: Project specification
            analysis: Analysis results
            strict: Strict validation mode
        """
        # Show validation status
        if analysis.is_valid:
            self.cli.console.print("\n[green]✓ Specification is valid[/green]")
        else:
            self.cli.console.print("\n[red]✗ Specification has issues[/red]")
        
        # Show issues if any
        if analysis.issues:
            table = Table(title="Validation Issues")
            table.add_column("Severity", style="yellow")
            table.add_column("Category")
            table.add_column("Message")
            
            for issue in analysis.issues:
                severity_color = "red" if issue.severity == "error" else "yellow"
                table.add_row(
                    f"[{severity_color}]{issue.severity}[/{severity_color}]",
                    issue.category,
                    issue.message
                )
            
            self.cli.console.print(table)
        
        # Show recommendations
        if analysis.recommendations and not strict:
            self.cli.console.print("\n[cyan]Recommendations:[/cyan]")
            for rec in analysis.recommendations:
                self.cli.console.print(f"• {rec}")
        
        # Show metrics
        if hasattr(analysis, 'metrics'):
            table = Table(title="Project Metrics")
            table.add_column("Metric")
            table.add_column("Value", style="cyan")
            
            table.add_row("Complexity", analysis.metrics.get('complexity', 'N/A'))
            table.add_row("Estimated LOC", str(analysis.metrics.get('estimated_loc', 'N/A')))
            table.add_row("Risk Level", analysis.metrics.get('risk_level', 'N/A'))
            
            self.cli.console.print(table)