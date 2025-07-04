"""
Interactive menu components for Claude Code Builder UI.
"""
from typing import Optional, List, Dict, Any, Callable, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
import asyncio

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.tree import Tree
from rich.columns import Columns
from rich.align import Align
from rich import box

from ..models.phase import Phase, PhaseStatus
from ..models.project import Technology
from ..mcp.discovery import MCPServer
from ..models.custom_instructions import InstructionSet


T = TypeVar('T')


@dataclass
class MenuItem(Generic[T]):
    """A single menu item."""
    label: str
    value: T
    description: Optional[str] = None
    icon: Optional[str] = None
    enabled: bool = True
    shortcut: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
            
    def render(self) -> Text:
        """Render the menu item."""
        text = Text()
        
        # Add icon
        if self.icon:
            text.append(f"{self.icon} ", style="blue")
            
        # Add label
        style = "white" if self.enabled else "dim"
        text.append(self.label, style=style)
        
        # Add shortcut
        if self.shortcut:
            text.append(f" [{self.shortcut}]", style="dim cyan")
            
        return text


@dataclass
class MenuConfig:
    """Configuration for menu appearance and behavior."""
    title: Optional[str] = None
    show_numbers: bool = True
    show_descriptions: bool = True
    show_icons: bool = True
    allow_cancel: bool = True
    cancel_text: str = "Cancel"
    clear_screen: bool = False
    box_style: Any = box.ROUNDED
    highlight_style: str = "bold cyan"
    disabled_style: str = "dim"
    prompt_style: str = "bold yellow"


class BaseMenu(Generic[T]):
    """Base class for interactive menus."""
    
    def __init__(self, 
                 items: List[MenuItem[T]], 
                 console: Optional[Console] = None,
                 config: Optional[MenuConfig] = None):
        """Initialize menu."""
        self.items = items
        self.console = console or Console()
        self.config = config or MenuConfig()
        self._validate_items()
        
    def _validate_items(self):
        """Validate menu items."""
        if not self.items:
            raise ValueError("Menu must have at least one item")
            
        # Check for duplicate shortcuts
        shortcuts = [item.shortcut for item in self.items if item.shortcut]
        if len(shortcuts) != len(set(shortcuts)):
            raise ValueError("Duplicate shortcuts found in menu items")
            
    def _render_menu(self) -> Panel:
        """Render the menu as a panel."""
        # Create table for menu items
        table = Table(show_header=False, box=None, padding=(0, 2))
        
        if self.config.show_numbers:
            table.add_column("Number", style="dim cyan", width=3)
        if self.config.show_icons and any(item.icon for item in self.items):
            table.add_column("Icon", width=2)
        table.add_column("Label")
        if self.config.show_descriptions and any(item.description for item in self.items):
            table.add_column("Description", style="dim")
            
        # Add items
        for i, item in enumerate(self.items, 1):
            row = []
            
            if self.config.show_numbers:
                row.append(str(i) if item.enabled else "")
                
            if self.config.show_icons and any(it.icon for it in self.items):
                row.append(item.icon or "")
                
            row.append(item.render())
            
            if self.config.show_descriptions and any(it.description for it in self.items):
                row.append(item.description or "")
                
            table.add_row(*row)
            
        # Add cancel option
        if self.config.allow_cancel:
            row = []
            if self.config.show_numbers:
                row.append("0")
            if self.config.show_icons and any(item.icon for item in self.items):
                row.append("✗")
            row.append(Text(self.config.cancel_text, style="red"))
            if self.config.show_descriptions and any(item.description for item in self.items):
                row.append("")
            table.add_row(*row)
            
        # Create panel
        return Panel(
            table,
            title=self.config.title,
            box=self.config.box_style,
            expand=False
        )
        
    def _get_choice(self) -> Optional[T]:
        """Get user's choice."""
        # Display menu
        if self.config.clear_screen:
            self.console.clear()
            
        self.console.print(self._render_menu())
        
        # Get input
        while True:
            try:
                # Check for shortcuts first
                choice_str = Prompt.ask(
                    "[bold yellow]Enter your choice[/bold yellow]",
                    console=self.console
                )
                
                # Check shortcuts
                for item in self.items:
                    if item.shortcut and choice_str.lower() == item.shortcut.lower():
                        if item.enabled:
                            return item.value
                        else:
                            self.console.print(
                                "[red]This option is currently disabled[/red]"
                            )
                            continue
                            
                # Check number
                choice = int(choice_str)
                
                if choice == 0 and self.config.allow_cancel:
                    return None
                    
                if 1 <= choice <= len(self.items):
                    item = self.items[choice - 1]
                    if item.enabled:
                        return item.value
                    else:
                        self.console.print(
                            "[red]This option is currently disabled[/red]"
                        )
                else:
                    self.console.print(
                        f"[red]Please enter a number between 1 and {len(self.items)}[/red]"
                    )
                    
            except ValueError:
                self.console.print(
                    "[red]Invalid input. Please enter a number or shortcut[/red]"
                )
                
    def show(self) -> Optional[T]:
        """Show the menu and return the selected value."""
        return self._get_choice()
        
    async def show_async(self) -> Optional[T]:
        """Show the menu asynchronously."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._get_choice
        )


class PhaseMenu(BaseMenu[Phase]):
    """Menu for selecting phases."""
    
    def __init__(self, 
                 phases: List[Phase],
                 console: Optional[Console] = None,
                 show_status: bool = True,
                 show_dependencies: bool = True):
        """Initialize phase menu."""
        # Create menu items from phases
        items = []
        for phase in phases:
            # Determine icon based on status
            icon = {
                PhaseStatus.PENDING: "⏸",
                PhaseStatus.PLANNING: "📋",
                PhaseStatus.EXECUTING: "▶",
                PhaseStatus.COMPLETED: "✓",
                PhaseStatus.FAILED: "✗",
                PhaseStatus.SKIPPED: "⏭"
            }.get(phase.status, "?")
            
            # Build description
            description_parts = []
            if show_status:
                description_parts.append(phase.status.value)
            if show_dependencies and phase.dependencies:
                deps = f"deps: {', '.join(map(str, phase.dependencies))}"
                description_parts.append(deps)
                
            description = " | ".join(description_parts) if description_parts else None
            
            # Create menu item
            item = MenuItem(
                label=f"Phase {phase.phase_number}: {phase.name}",
                value=phase,
                description=description,
                icon=icon,
                enabled=phase.status == PhaseStatus.PENDING,
                shortcut=str(phase.phase_number) if phase.phase_number < 10 else None
            )
            items.append(item)
            
        # Initialize base menu
        config = MenuConfig(
            title="Select Phase to Execute",
            show_descriptions=True,
            show_icons=True
        )
        super().__init__(items, console, config)


class MCPServerMenu(BaseMenu[MCPServer]):
    """Menu for selecting MCP servers."""
    
    def __init__(self,
                 servers: List[MCPServer],
                 console: Optional[Console] = None,
                 show_status: bool = True,
                 allow_multiple: bool = False):
        """Initialize MCP server menu."""
        self.allow_multiple = allow_multiple
        
        # Create menu items
        items = []
        for server in servers:
            # Status icon
            icon = "🟢" if server.enabled else "🔴"
            
            # Description
            description_parts = []
            if server.description:
                description_parts.append(server.description)
            if show_status:
                status = "enabled" if server.enabled else "disabled"
                description_parts.append(f"[{status}]")
                
            description = " - ".join(description_parts) if description_parts else None
            
            item = MenuItem(
                label=server.name,
                value=server,
                description=description,
                icon=icon,
                enabled=True
            )
            items.append(item)
            
        # Configure menu
        title = "Select MCP Servers" if allow_multiple else "Select MCP Server"
        config = MenuConfig(
            title=title,
            show_descriptions=True,
            show_icons=True
        )
        super().__init__(items, console, config)
        
    def show_multiple(self) -> List[MCPServer]:
        """Show menu for selecting multiple servers."""
        if not self.allow_multiple:
            raise ValueError("Multiple selection not enabled")
            
        selected = []
        remaining_items = self.items.copy()
        
        while remaining_items:
            # Update menu with remaining items
            self.items = remaining_items
            
            # Show menu
            if self.config.clear_screen:
                self.console.clear()
                
            # Show selected so far
            if selected:
                self.console.print("\n[green]Selected servers:[/green]")
                for server in selected:
                    self.console.print(f"  • {server.name}")
                    
            # Get choice
            choice = self._get_choice()
            
            if choice is None:  # Cancel or done
                break
                
            # Add to selected and remove from remaining
            selected.append(choice)
            remaining_items = [
                item for item in remaining_items 
                if item.value != choice
            ]
            
            # Ask if they want to select more
            if remaining_items:
                if not Confirm.ask(
                    "\n[yellow]Select another server?[/yellow]",
                    console=self.console
                ):
                    break
                    
        return selected


class InstructionMenu(BaseMenu[InstructionSet]):
    """Menu for selecting instruction templates."""
    
    def __init__(self,
                 templates: List[InstructionSet],
                 console: Optional[Console] = None,
                 group_by_category: bool = True):
        """Initialize instruction menu."""
        self.group_by_category = group_by_category
        
        # Create menu items
        items = []
        for template in templates:
            icon = "📝"
            description = template.description or str(template.priority.name)
            
            item = MenuItem(
                label=template.name,
                value=template,
                description=description,
                icon=icon,
                metadata={'category': template.priority.name if template.priority else 'MEDIUM'}
            )
            items.append(item)
            
        # Sort by category if requested
        if group_by_category:
            items.sort(key=lambda x: (x.metadata.get('category', ''), x.label))
            
        config = MenuConfig(
            title="Select Instruction Template",
            show_descriptions=True,
            show_icons=True
        )
        super().__init__(items, console, config)
        
    def _render_menu(self) -> Panel:
        """Render menu grouped by category."""
        if not self.group_by_category:
            return super()._render_menu()
            
        # Group items by category
        categories = {}
        for item in self.items:
            category = item.metadata.get('category', 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
            
        # Create tree structure
        tree = Tree("📚 Instruction Templates")
        
        for category, items in sorted(categories.items()):
            branch = tree.add(f"[bold cyan]{category}[/bold cyan]")
            
            for i, item in enumerate(items, 1):
                # Create item text
                item_text = Text()
                if self.config.show_numbers:
                    item_text.append(f"{i}. ", style="dim cyan")
                item_text.append(item.label)
                if item.description and item.description != category:
                    item_text.append(f" - {item.description}", style="dim")
                    
                branch.add(item_text)
                
        return Panel(tree, box=self.config.box_style, expand=False)


class InteractiveMenu:
    """Factory for creating interactive menus."""
    
    @staticmethod
    def select_option(
        options: List[str],
        prompt: str = "Select an option",
        console: Optional[Console] = None
    ) -> Optional[str]:
        """Simple menu for selecting from string options."""
        items = [
            MenuItem(label=option, value=option)
            for option in options
        ]
        
        config = MenuConfig(title=prompt)
        menu = BaseMenu(items, console, config)
        return menu.show()
        
    @staticmethod
    def select_multiple(
        options: List[str],
        prompt: str = "Select options (space to toggle, enter to confirm)",
        console: Optional[Console] = None
    ) -> List[str]:
        """Menu for selecting multiple options."""
        console = console or Console()
        selected = set()
        
        while True:
            # Clear and show current selection
            console.clear()
            console.print(Panel(prompt, style="bold yellow"))
            
            # Show options with checkboxes
            for i, option in enumerate(options, 1):
                checkbox = "☑" if option in selected else "☐"
                style = "green" if option in selected else "white"
                console.print(f"{i}. {checkbox} {option}", style=style)
                
            console.print("\n0. Done selecting")
            
            # Get choice
            try:
                choice = IntPrompt.ask(
                    "Toggle option",
                    console=console
                )
                
                if choice == 0:
                    break
                elif 1 <= choice <= len(options):
                    option = options[choice - 1]
                    if option in selected:
                        selected.remove(option)
                    else:
                        selected.add(option)
            except Exception:
                continue
                
        return list(selected)
        
    @staticmethod
    def confirm_action(
        message: str,
        default: bool = False,
        console: Optional[Console] = None
    ) -> bool:
        """Simple confirmation prompt."""
        return Confirm.ask(
            message,
            default=default,
            console=console or Console()
        )