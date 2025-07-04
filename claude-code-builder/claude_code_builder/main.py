#!/usr/bin/env python3
"""Main entry point for Claude Code Builder."""
import sys
import signal
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
import argparse
import json

from .cli.cli import CLI
from .config.settings import Settings
from .logging.logger import setup_logging as setup_logger, get_logger
from .exceptions.base import ClaudeCodeBuilderError
from .utils.path_utils import find_project_root
from .utils.config_loader import ConfigLoader, ConfigSchema
from .utils.error_handler import error_context, format_exception
from .__init__ import __version__

logger = get_logger(__name__)


class ClaudeCodeBuilder:
    """Main application class for Claude Code Builder."""
    
    def __init__(self, args: argparse.Namespace):
        """Initialize Claude Code Builder.
        
        Args:
            args: Command-line arguments
        """
        self.args = args
        self.settings = Settings()
        self.config_loader = ConfigLoader("claude_code_builder")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)
    
    async def initialize(self) -> None:
        """Initialize the application."""
        # Setup logging
        log_level = "DEBUG" if self.args.debug else self.args.log_level
        setup_logger(level=log_level)
        
        logger.info(f"Claude Code Builder v{__version__} starting...")
        
        # Load configuration
        await self._load_configuration()
        
        # Initialize CLI
        self.cli = CLI(self.settings, self.args)
        
    async def _load_configuration(self) -> None:
        """Load configuration from various sources."""
        # Define configuration schema
        schema = ConfigSchema(
            fields={
                'api_key': {'type': str},
                'model': {'type': str, 'default': 'claude-3-sonnet-20240229'},
                'max_tokens': {'type': int, 'min': 1000, 'max': 200000},
                'mcp_servers': {'type': dict},
                'research': {'type': dict},
                'ui': {'type': dict},
                'cache': {'type': dict}
            },
            required=['api_key'],
            defaults={
                'max_tokens': 100000,
                'mcp_servers': {},
                'research': {'enabled': True},
                'ui': {'rich': True},
                'cache': {'enabled': True, 'ttl': 3600}
            }
        )
        
        self.config_loader.schema = schema
        
        # Load from multiple sources
        sources = []
        
        # Project config
        if self.args.project_dir:
            project_config = Path(self.args.project_dir) / '.claude-code-builder.yaml'
            if project_config.exists():
                sources.append(project_config)
        
        # User config
        if self.args.config:
            sources.append(self.args.config)
        
        # Load and merge configs
        config = self.config_loader.load(sources)
        
        # Apply to settings
        self.settings.update(config)
        
        # Override with command-line args
        if self.args.api_key:
            self.settings.api_key = self.args.api_key
        if self.args.model:
            self.settings.model = self.args.model
        if self.args.max_tokens:
            self.settings.max_tokens = self.args.max_tokens
        
        logger.debug(f"Configuration loaded from {len(self.config_loader.sources)} sources")
    
    async def run(self) -> int:
        """Run the application.
        
        Returns:
            Exit code
        """
        try:
            # Initialize application
            await self.initialize()
            
            # Run CLI
            return await self.cli.run()
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 130
        except ClaudeCodeBuilderError as e:
            logger.error(f"Application error: {e}")
            if self.args.debug:
                logger.error(format_exception(e))
            return 1
        except Exception as e:
            logger.critical(f"Unexpected error: {e}")
            if self.args.debug:
                logger.critical(format_exception(e))
            return 2


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser.
    
    Returns:
        Argument parser
    """
    parser = argparse.ArgumentParser(
        prog='claude-code-builder',
        description='AI-powered autonomous project builder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build project from specification
  claude-code-builder build project.md
  
  # Plan project without building
  claude-code-builder plan project.md --output plan.json
  
  # Resume interrupted build
  claude-code-builder resume --checkpoint latest
  
  # Validate project specification
  claude-code-builder validate project.md
  
  # List available MCP servers
  claude-code-builder mcp list
  
  # Run with custom config
  claude-code-builder build project.md --config my-config.yaml
  
For more information: https://github.com/yourusername/claude-code-builder
"""
    )
    
    # Global options
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set log level'
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--api-key',
        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)'
    )
    
    parser.add_argument(
        '--model',
        help='Claude model to use'
    )
    
    parser.add_argument(
        '--max-tokens',
        type=int,
        help='Maximum tokens per phase'
    )
    
    parser.add_argument(
        '--project-dir',
        type=Path,
        help='Project directory'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(
        title='commands',
        description='Available commands',
        dest='command',
        required=True
    )
    
    # Build command
    build_parser = subparsers.add_parser(
        'build',
        help='Build project from specification'
    )
    build_parser.add_argument(
        'specification',
        type=Path,
        help='Project specification file (markdown)'
    )
    build_parser.add_argument(
        '--output-dir',
        type=Path,
        help='Output directory (default: project name)'
    )
    build_parser.add_argument(
        '--phases',
        type=int,
        help='Number of phases (auto-detected if not specified)'
    )
    build_parser.add_argument(
        '--no-research',
        action='store_true',
        help='Disable research phase'
    )
    build_parser.add_argument(
        '--no-testing',
        action='store_true',
        help='Skip testing phase'
    )
    build_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform dry run without building'
    )
    
    # Plan command
    plan_parser = subparsers.add_parser(
        'plan',
        help='Generate project plan without building'
    )
    plan_parser.add_argument(
        'specification',
        type=Path,
        help='Project specification file'
    )
    plan_parser.add_argument(
        '--output',
        type=Path,
        help='Output plan file'
    )
    plan_parser.add_argument(
        '--format',
        choices=['json', 'yaml', 'markdown'],
        default='json',
        help='Output format'
    )
    
    # Resume command
    resume_parser = subparsers.add_parser(
        'resume',
        help='Resume interrupted build'
    )
    resume_parser.add_argument(
        '--checkpoint',
        default='latest',
        help='Checkpoint to resume from'
    )
    resume_parser.add_argument(
        '--project-dir',
        type=Path,
        help='Project directory'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate project specification'
    )
    validate_parser.add_argument(
        'specification',
        type=Path,
        help='Project specification file'
    )
    validate_parser.add_argument(
        '--strict',
        action='store_true',
        help='Enable strict validation'
    )
    
    # MCP command
    mcp_parser = subparsers.add_parser(
        'mcp',
        help='Manage MCP servers'
    )
    mcp_subparsers = mcp_parser.add_subparsers(
        dest='mcp_command',
        required=True
    )
    
    # MCP list
    mcp_list_parser = mcp_subparsers.add_parser(
        'list',
        help='List available MCP servers'
    )
    mcp_list_parser.add_argument(
        '--installed',
        action='store_true',
        help='Show only installed servers'
    )
    
    # MCP install
    mcp_install_parser = mcp_subparsers.add_parser(
        'install',
        help='Install MCP server'
    )
    mcp_install_parser.add_argument(
        'server',
        help='Server name to install'
    )
    
    # MCP discover
    mcp_discover_parser = mcp_subparsers.add_parser(
        'discover',
        help='Discover MCP servers for project'
    )
    mcp_discover_parser.add_argument(
        'specification',
        type=Path,
        help='Project specification file'
    )
    
    # Plugin command
    plugin_parser = subparsers.add_parser(
        'plugin',
        help='Manage plugins'
    )
    plugin_subparsers = plugin_parser.add_subparsers(
        dest='plugin_command',
        required=True
    )
    
    # Plugin list
    plugin_list_parser = plugin_subparsers.add_parser(
        'list',
        help='List available plugins'
    )
    
    # Plugin install
    plugin_install_parser = plugin_subparsers.add_parser(
        'install',
        help='Install plugin'
    )
    plugin_install_parser.add_argument(
        'plugin',
        help='Plugin name or path'
    )
    
    # Config command
    config_parser = subparsers.add_parser(
        'config',
        help='Manage configuration'
    )
    config_subparsers = config_parser.add_subparsers(
        dest='config_command',
        required=True
    )
    
    # Config show
    config_show_parser = config_subparsers.add_parser(
        'show',
        help='Show current configuration'
    )
    
    # Config set
    config_set_parser = config_subparsers.add_parser(
        'set',
        help='Set configuration value'
    )
    config_set_parser.add_argument(
        'key',
        help='Configuration key'
    )
    config_set_parser.add_argument(
        'value',
        help='Configuration value'
    )
    
    # Config init
    config_init_parser = config_subparsers.add_parser(
        'init',
        help='Initialize configuration file'
    )
    config_init_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing config'
    )
    
    return parser


def main() -> int:
    """Main entry point.
    
    Returns:
        Exit code
    """
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Create and run application
    app = ClaudeCodeBuilder(args)
    
    # Run with asyncio
    try:
        return asyncio.run(app.run())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            # Already in event loop (e.g., Jupyter)
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(app.run())
        raise


if __name__ == '__main__':
    sys.exit(main())