"""Main entry point for Claude Code Builder package."""

import sys
import asyncio
import argparse
from pathlib import Path
from typing import Optional

from claude_code_builder.config.settings import Settings
from claude_code_builder.cli.cli import CLI
from claude_code_builder.exceptions.base import ClaudeCodeBuilderError
from claude_code_builder.logging.logger import get_logger

logger = get_logger(__name__)

def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="claude-code-builder",
        description="Autonomous project builder powered by Claude AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build a project from specification
  claude-code-builder build project_spec.md

  # Build with custom output directory
  claude-code-builder build project_spec.md -o my-project

  # Dry run to see planned phases
  claude-code-builder build project_spec.md --dry-run

  # Validate a specification without building
  claude-code-builder validate project_spec.md

  # Initialize configuration
  claude-code-builder init
        """
    )
    
    # Global options
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--config", type=Path, help="Path to config file")
    parser.add_argument("--api-key", help="Claude API key")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build project from specification")
    build_parser.add_argument("spec_file", type=Path, help="Path to project specification file")
    build_parser.add_argument("-o", "--output", dest="output_dir", type=Path, help="Output directory")
    build_parser.add_argument("--dry-run", action="store_true", help="Show phases without building")
    build_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompts")
    build_parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    build_parser.add_argument("--model", help="Claude model to use")
    build_parser.add_argument("--max-tokens", type=int, help="Maximum tokens per request")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate project specification")
    validate_parser.add_argument("spec_file", type=Path, help="Path to project specification file")
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize configuration")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing config")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show build status")
    status_parser.add_argument("project_dir", type=Path, nargs="?", default=".", help="Project directory")
    
    return parser

def load_settings(args: argparse.Namespace) -> Settings:
    """Load application settings."""
    settings = Settings()
    
    # Override with config file
    if args.config and args.config.exists():
        settings.load_from_file(args.config)
    
    # Override with command-line args
    if args.api_key:
        settings.api_key = args.api_key
    if hasattr(args, 'model') and args.model:
        settings.model = args.model
    if hasattr(args, 'max_tokens') and args.max_tokens:
        settings.max_tokens = args.max_tokens
    
    return settings

async def async_main() -> int:
    """Async main function."""
    try:
        # Parse arguments
        parser = create_parser()
        args = parser.parse_args()
        
        # Handle no command
        if not args.command:
            parser.print_help()
            return 1
        
        # Load settings
        settings = load_settings(args)
        
        # Validate settings
        if args.command == 'build' and not settings.api_key:
            print("Error: Claude API key required. Set via --api-key or config file.")
            return 1
        
        # Create and run CLI
        cli = CLI(settings, args)
        return await cli.run()
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except ClaudeCodeBuilderError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        if getattr(args, 'debug', False):
            import traceback
            traceback.print_exc()
        return 2

def main():
    """Main entry point for the package."""
    return asyncio.run(async_main())

if __name__ == "__main__":
    sys.exit(main())