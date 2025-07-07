#!/usr/bin/env python3
"""
Claude Code CLI Builder - Production build script using subprocess wrapper.
Based on CloudDocs implementation patterns.
"""

import os
import sys
import json
import asyncio
import argparse
import logging
import time
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BuildStats:
    """Track build statistics."""
    files_created: int = 0
    files_modified: int = 0
    tool_calls: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    messages: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    
    @property
    def duration(self) -> float:
        return time.time() - self.start_time


@dataclass
class BuildConfig:
    """Build configuration."""
    model: str = "claude-opus-4-20250514"
    max_turns: int = 50
    output_format: str = "stream-json"
    allowed_tools: List[str] = field(default_factory=lambda: [
        "create", "write", "edit", "str_replace_editor", "str_replace",
        "bash", "run_command", "execute_command",
        "search", "find", "grep", "list_files",
        "web_search", "fetch_url",
        "mcp__*"  # All MCP tools
    ])
    mcp_servers: Dict[str, Dict] = field(default_factory=dict)
    system_prompt_suffix: str = ""


class ClaudeCliBuilder:
    """Builder that wraps Claude Code CLI."""
    
    def __init__(self, config: BuildConfig = None):
        self.config = config or BuildConfig()
        self.stats = BuildStats()
        
    def build_command(self, output_dir: Path, mcp_config_path: Path) -> List[str]:
        """Build Claude CLI command."""
        cmd = ["claude"]
        
        # Model
        cmd.extend(["--model", self.config.model])
        
        # MCP configuration
        if mcp_config_path.exists():
            cmd.extend(["--mcp-config", str(mcp_config_path)])
        
        # Allowed tools
        tools_str = ",".join(self.config.allowed_tools)
        cmd.extend(["--allowedTools", tools_str])
        
        # Permissions
        cmd.append("--dangerously-skip-permissions")
        
        # Output format
        cmd.extend(["--output-format", self.config.output_format])
        
        # Max turns
        cmd.extend(["--max-turns", str(self.config.max_turns)])
        
        # System prompt
        system_prompt = (
            "You are Claude Code Builder creating a production-ready project. "
            "CRITICAL: Implement everything fully - NO PLACEHOLDERS, NO MOCKS, NO STUBS. "
            "Create production-ready code with proper error handling. "
            "Follow best practices and include comprehensive documentation. "
        )
        if self.config.system_prompt_suffix:
            system_prompt += self.config.system_prompt_suffix
            
        cmd.extend(["--append-system-prompt", system_prompt])
        
        return cmd
    
    def setup_mcp_config(self, output_dir: Path) -> Path:
        """Setup MCP configuration."""
        mcp_config = {"mcpServers": {}}
        
        # Default filesystem server
        mcp_config["mcpServers"]["filesystem"] = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", str(output_dir.absolute())]
        }
        
        # Add additional servers
        for name, server_config in self.config.mcp_servers.items():
            mcp_config["mcpServers"][name] = server_config
        
        # Write config
        mcp_config_path = output_dir / ".mcp.json"
        with open(mcp_config_path, 'w') as f:
            json.dump(mcp_config, f, indent=2)
            
        logger.info(f"Created MCP config with {len(mcp_config['mcpServers'])} servers")
        return mcp_config_path
    
    def process_stream_line(self, line: str, files_created: Set[str], files_modified: Set[str]) -> Optional[str]:
        """Process a line from Claude's streaming output."""
        if not line.strip():
            return None
            
        try:
            data = json.loads(line)
            event_type = data.get("type", "")
            
            if event_type == "text":
                self.stats.messages += 1
                return data.get("text", "")
                
            elif event_type == "tool_use":
                tool_name = data.get("name", "unknown")
                self.stats.tool_calls[tool_name] += 1
                
                # Track file operations
                params = data.get("input", {})
                if tool_name in ["create", "write"] and "path" in params:
                    files_created.add(params["path"])
                    return f"📄 Creating: {params['path']}"
                elif tool_name in ["edit", "str_replace_editor"] and "path" in params:
                    files_modified.add(params["path"]) 
                    return f"✏️  Editing: {params['path']}"
                elif tool_name in ["bash", "run_command"] and "command" in params:
                    return f"🔧 Running: {params['command']}"
                    
            elif event_type == "error":
                self.stats.errors += 1
                return f"❌ Error: {data.get('message', 'Unknown error')}"
                
        except json.JSONDecodeError:
            pass
            
        return None
    
    async def build(self, spec: str, output_dir: Path, show_output: bool = True) -> bool:
        """Build a project from specification."""
        logger.info(f"Starting build in {output_dir}")
        
        # Setup output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup MCP configuration
        mcp_config_path = self.setup_mcp_config(output_dir)
        
        # Build command
        cmd = self.build_command(output_dir, mcp_config_path)
        
        # Create prompt with specification
        prompt = f"""Build the following project:

{spec}

Requirements:
1. Create a complete, production-ready implementation
2. Include proper project structure and organization
3. Implement all features with error handling
4. Add comprehensive logging and configuration
5. Create documentation (README.md, docstrings, comments)
6. Include dependency files (requirements.txt, package.json, etc.)
7. Add scripts for common operations (install, run, test)
8. Follow best practices for the technology stack

Start by analyzing the specification and creating the project structure."""

        # Write prompt to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name
        
        try:
            # Start process
            logger.info(f"Executing: {' '.join(cmd[:4])}...")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                prompt_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=output_dir
            )
            
            # Track files
            files_created = set()
            files_modified = set()
            
            # Process output
            if show_output:
                print("\n🤖 Claude is building your project...\n")
                
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                    
                decoded = line.decode('utf-8', errors='replace')
                output = self.process_stream_line(decoded, files_created, files_modified)
                
                if output and show_output:
                    print(f"   {output}")
            
            # Wait for completion
            return_code = await process.wait()
            
            # Update stats
            self.stats.files_created = len(files_created)
            self.stats.files_modified = len(files_modified)
            
            # Log summary
            logger.info(f"Build completed with return code: {return_code}")
            logger.info(f"Duration: {self.stats.duration:.1f}s")
            logger.info(f"Files created: {self.stats.files_created}")
            logger.info(f"Tool calls: {sum(self.stats.tool_calls.values())}")
            
            return return_code == 0
            
        except Exception as e:
            logger.error(f"Build failed: {e}")
            return False
        finally:
            os.unlink(prompt_file)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get build summary."""
        return {
            "duration": self.stats.duration,
            "files_created": self.stats.files_created,
            "files_modified": self.stats.files_modified,
            "messages": self.stats.messages,
            "errors": self.stats.errors,
            "tool_calls": dict(self.stats.tool_calls),
            "top_tools": sorted(
                self.stats.tool_calls.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build projects using Claude Code CLI"
    )
    parser.add_argument("spec_file", help="Project specification file")
    parser.add_argument("-o", "--output-dir", help="Output directory")
    parser.add_argument("--model", default="claude-opus-4-20250514", help="Claude model")
    parser.add_argument("--max-turns", type=int, default=50, help="Maximum turns")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    
    args = parser.parse_args()
    
    # Check API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("❌ ERROR: ANTHROPIC_API_KEY not set!")
        return 1
    
    # Check Claude CLI
    if not shutil.which("claude"):
        print("❌ ERROR: Claude Code CLI not found!")
        print("Install with: npm install -g @anthropic-ai/claude-code")
        return 1
    
    # Load specification
    spec_path = Path(args.spec_file)
    if not spec_path.exists():
        print(f"❌ ERROR: Specification file not found: {spec_path}")
        return 1
        
    spec_content = spec_path.read_text()
    
    # Setup output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        project_name = spec_path.stem
        output_dir = Path(f"{project_name}-{timestamp}")
    
    # Configure builder
    config = BuildConfig(
        model=args.model,
        max_turns=args.max_turns
    )
    
    # Build
    print("🚀 Claude Code CLI Builder")
    print("=" * 50)
    print(f"📋 Specification: {spec_path}")
    print(f"📁 Output: {output_dir}")
    print(f"🤖 Model: {config.model}")
    print(f"🔄 Max turns: {config.max_turns}")
    print("=" * 50)
    
    builder = ClaudeCliBuilder(config)
    success = await builder.build(
        spec_content,
        output_dir,
        show_output=not args.quiet
    )
    
    # Show summary
    summary = builder.get_summary()
    print("\n" + "=" * 50)
    print("📊 BUILD SUMMARY")
    print("=" * 50)
    print(f"⏱️  Duration: {summary['duration']:.1f}s")
    print(f"📄 Files created: {summary['files_created']}")
    print(f"✏️  Files modified: {summary['files_modified']}")
    print(f"💬 Messages: {summary['messages']}")
    print(f"🛠️  Tool calls: {sum(summary['tool_calls'].values())}")
    
    if summary['errors'] > 0:
        print(f"❌ Errors: {summary['errors']}")
    
    if summary['top_tools']:
        print("\n🔧 Top tools used:")
        for tool, count in summary['top_tools']:
            print(f"   - {tool}: {count} calls")
    
    print("\n" + "=" * 50)
    if success:
        print(f"✅ BUILD SUCCESSFUL! Project ready at: {output_dir}")
    else:
        print("❌ BUILD FAILED! Check the logs for details.")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)