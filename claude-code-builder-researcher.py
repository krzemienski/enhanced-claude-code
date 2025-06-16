#!/usr/bin/env python3
"""
Claude Code Builder v2.3.0 - Enhanced Production-Ready Autonomous Multi-Phase Project Builder

An intelligent project builder that orchestrates Claude Code SDK to autonomously build
complete projects through multiple execution phases, with enhanced memory management,
improved research capabilities, accurate cost tracking, and robust error handling.

Key Improvements in v2.3.0:
- Enhanced research implementation using Anthropic SDK knowledge base
- Accurate cost tracking from Claude Code execution results
- Improved error handling and recovery mechanisms
- Better memory management with context preservation
- Enhanced MCP server discovery and configuration
- Optimized phase execution with better context passing
- Improved streaming output parsing with real-time cost updates
- Advanced tool management with usage analytics
- Comprehensive validation and testing framework

This version implements:
- Claude Code SDK CLI integration (TypeScript/Python SDKs coming soon)
- MCP (Model Context Protocol) with enhanced server management
- Anthropic SDK for intelligent research and analysis
- Accurate cost tracking and usage analytics
- Robust error recovery and checkpoint system

Usage:
    python claude_code_builder_v2.3.py <spec_file> [options]

Example:
    python claude_code_builder_v2.3.py project-spec.md \
        --output-dir ./my-project \
        --api-key $ANTHROPIC_API_KEY \
        --enable-research \
        --discover-mcp \
        --auto-confirm

Requirements:
    - Python 3.8+
    - Claude Code installed and accessible (npm install -g @anthropic-ai/claude-code)
    - Anthropic SDK: pip install anthropic>=0.18.0
    - Rich: pip install rich>=13.0.0
    - Aiofiles: pip install aiofiles>=23.0.0
    - MCP servers (optional): Various npm packages

Author: Claude (Version 2.3.0)
License: MIT
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
import re
import signal
import hashlib
import traceback
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set, Union, AsyncIterator
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from contextlib import contextmanager, asynccontextmanager
from enum import Enum, auto

# Anthropic SDK imports for AI interactions
try:
    from anthropic import AsyncAnthropic, Anthropic
    from anthropic.types import (
        Message, MessageStreamEvent, ContentBlockDeltaEvent,
        ContentBlockStartEvent, ContentBlockStopEvent,
        MessageStartEvent, MessageStopEvent, MessageDeltaEvent,
        ContentBlock, TextBlock, ToolUseBlock, ToolResultBlock,
        Usage
    )
    ANTHROPIC_SDK_AVAILABLE = True
except ImportError:
    ANTHROPIC_SDK_AVAILABLE = False
    print("Warning: Anthropic SDK not installed. Install with: pip install anthropic")
    print("This is required for research features and cost tracking.")
    # Define placeholder types
    Usage = Any

# Rich imports for beautiful console output
try:
    from rich.console import Console, Group
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, TaskID
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.prompt import Confirm, Prompt
    from rich.live import Live
    from rich.layout import Layout
    from rich.syntax import Syntax
    from rich import box
    from rich.logging import RichHandler
    from rich.tree import Tree
    from rich.status import Status
    from rich.text import Text
    from rich.columns import Columns
except ImportError:
    print("Error: Rich library not installed. Install with: pip install rich")
    sys.exit(1)

# Async file operations
try:
    import aiofiles
except ImportError:
    print("Warning: aiofiles not installed. Install with: pip install aiofiles")
    aiofiles = None

# Initialize Rich console for beautiful output
console = Console()

# Token costs per million tokens (as of 2025)
# Based on Anthropic's current pricing model
TOKEN_COSTS = {
    # Claude 4 models (current generation)
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    
    # Claude 3.5 models (previous generation, still supported)
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 1.00, "output": 5.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
}

# Default models for different tasks
DEFAULT_ANALYZER_MODEL = "claude-opus-4-20250514"  # Best for complex analysis
DEFAULT_EXECUTOR_MODEL = "claude-opus-4-20250514"  # Best for code generation
DEFAULT_RESEARCH_MODEL = "claude-sonnet-4-20250514"  # Good balance for research

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds

# Enhanced MCP Server Registry with v2.3 improvements
MCP_SERVER_REGISTRY = {
    # Core MCP Servers - Essential for most projects
    "memory": {
        "package": "@modelcontextprotocol/server-memory",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "description": "Persistent memory storage across conversations",
        "category": "core",
        "priority": 10,
        "tools": ["store", "recall", "search", "delete", "list", "update", "clear"],
        "use_cases": ["context_preservation", "cross_session_memory", "decision_tracking", "state_management"],
        "config_template": {
            "storage_path": "${workspace}/.memory",
            "max_entries": 10000,
            "compression": True,
            "auto_save": True
        }
    },
    "sequential-thinking": {
        "package": "@modelcontextprotocol/server-sequential-thinking",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "description": "Structured problem decomposition and reasoning",
        "category": "core",
        "priority": 9,
        "tools": ["plan", "decompose", "analyze", "synthesize", "reason", "evaluate"],
        "use_cases": ["problem_solving", "task_planning", "decision_analysis", "architecture_design"]
    },
    "filesystem": {
        "package": "@modelcontextprotocol/server-filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "${workspace}"],
        "description": "Advanced file system operations",
        "category": "core",
        "priority": 8,
        "tools": ["read_file", "write_file", "list_directory", "create_directory", "delete_file", "move_file", "copy_file"],
        "use_cases": ["file_management", "code_operations", "project_structure", "asset_handling"]
    },
    
    # Development Tools
    "git": {
        "package": "@modelcontextprotocol/server-git",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-git"],
        "description": "Git repository operations and version control",
        "category": "development",
        "priority": 7,
        "tools": ["commit", "branch", "merge", "diff", "log", "status", "checkout", "push", "pull", "stash"],
        "use_cases": ["version_control", "change_tracking", "collaboration", "release_management"]
    },
    "github": {
        "package": "@modelcontextprotocol/server-github",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "description": "GitHub API integration for repository management",
        "category": "development",
        "priority": 6,
        "tools": ["create_issue", "create_pr", "list_repos", "get_file", "create_repo", "update_issue"],
        "use_cases": ["repository_management", "issue_tracking", "collaboration", "ci_cd"],
        "env": {
            "GITHUB_TOKEN": "${GITHUB_TOKEN}"
        }
    },
    
    # Database Servers
    "postgres": {
        "package": "@modelcontextprotocol/server-postgres",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
        "description": "PostgreSQL database operations",
        "category": "database",
        "priority": 7,
        "tools": ["query", "execute", "list_tables", "describe_table", "create_table", "alter_table"],
        "use_cases": ["database_operations", "data_analysis", "schema_management", "data_migration"],
        "env": {
            "POSTGRES_URL": "${DATABASE_URL}"
        }
    },
    "sqlite": {
        "package": "@modelcontextprotocol/server-sqlite",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sqlite", "${workspace}/database.db"],
        "description": "SQLite database operations",
        "category": "database",
        "priority": 5,
        "tools": ["query", "execute", "list_tables", "create_database", "backup"],
        "use_cases": ["local_database", "prototyping", "testing", "embedded_apps"]
    },
    
    # External Services
    "web": {
        "package": "@modelcontextprotocol/server-web",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-web"],
        "description": "Web browsing and scraping capabilities",
        "category": "external",
        "priority": 6,
        "tools": ["fetch", "search", "scrape", "screenshot", "crawl"],
        "use_cases": ["web_scraping", "api_testing", "documentation_lookup", "research"]
    },
    "slack": {
        "package": "@modelcontextprotocol/server-slack",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-slack"],
        "description": "Slack integration for messaging",
        "category": "communication",
        "priority": 4,
        "tools": ["send_message", "list_channels", "search_messages", "create_channel"],
        "use_cases": ["notifications", "team_communication", "alerts", "reporting"],
        "env": {
            "SLACK_TOKEN": "${SLACK_TOKEN}"
        }
    },
    
    # New in v2.3: Additional useful servers
    "context7": {
        "package": "@modelcontextprotocol/server-context7",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-context7"],
        "description": "Access latest documentation for libraries and frameworks",
        "category": "documentation",
        "priority": 8,
        "tools": ["search_docs", "get_examples", "get_api_reference"],
        "use_cases": ["documentation_lookup", "api_reference", "best_practices"]
    }
}

class BuildStatus(Enum):
    """Enumeration for build phase status"""
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    SKIPPED = auto()
    CANCELLED = auto()
    RETRYING = auto()  # New in v2.3

@dataclass
class ToolCall:
    """
    Represents a single tool call made during execution.
    Enhanced in v2.3 with better metrics and categorization.
    """
    id: str
    name: str
    parameters: Dict[str, Any]
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    category: Optional[str] = None  # New in v2.3
    phase_id: Optional[str] = None  # New in v2.3
    
    @property
    def duration(self) -> float:
        """Calculate duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def is_mcp_tool(self) -> bool:
        """Check if this is an MCP tool call"""
        return self.name.startswith("mcp__")
    
    @property
    def mcp_server(self) -> Optional[str]:
        """Extract MCP server name if this is an MCP tool"""
        if self.is_mcp_tool:
            parts = self.name.split("__")
            if len(parts) >= 2:
                return parts[1]
        return None
    
    @property
    def tool_type(self) -> str:
        """Categorize tool type"""
        if self.is_mcp_tool:
            return f"mcp_{self.mcp_server}"
        elif any(cmd in self.name.lower() for cmd in ['bash', 'run', 'execute', 'command']):
            return "command"
        elif any(op in self.name.lower() for op in ['write', 'create', 'edit', 'read', 'delete']):
            return "file_operation"
        else:
            return "other"
    
    def to_rich(self) -> Panel:
        """Convert to rich panel for display"""
        content = []
        
        # Tool name and status
        if self.error:
            status = "[red]✗ Failed[/red]"
        elif self.end_time:
            status = f"[green]✓ Complete[/green] ({self.duration:.1f}s)"
        else:
            status = "[yellow]⚡ Running[/yellow]"
        
        content.append(f"{status}")
        
        # Tool type and category
        content.append(f"[dim]Type:[/dim] {self.tool_type}")
        if self.category:
            content.append(f"[dim]Category:[/dim] {self.category}")
        
        # MCP server info if applicable
        if self.is_mcp_tool and self.mcp_server:
            content.append(f"[dim]MCP Server:[/dim] {self.mcp_server}")
        
        # Parameters (formatted better)
        if self.parameters:
            params_str = self._format_parameters()
            content.append(f"\n[dim]Parameters:[/dim]\n{params_str}")
        
        # Result preview
        if self.result:
            result_str = self._format_result()
            content.append(f"\n[dim]Result:[/dim] {result_str}")
        
        # Error
        if self.error:
            content.append(f"\n[red]Error:[/red] {self.error}")
        
        return Panel(
            "\n".join(content),
            title=f"[bold cyan]{self.name}[/bold cyan]",
            border_style="cyan" if not self.error else "red"
        )
    
    def _format_parameters(self) -> str:
        """Format parameters for display"""
        if isinstance(self.parameters, dict):
            # Special formatting for common parameters
            if 'path' in self.parameters or 'file' in self.parameters:
                path = self.parameters.get('path') or self.parameters.get('file', '')
                return f"  Path: {path}"
            elif 'command' in self.parameters:
                return f"  Command: {self.parameters['command']}"
            else:
                params_str = json.dumps(self.parameters, indent=2)
                if len(params_str) > 200:
                    params_str = params_str[:197] + "..."
                return params_str
        return str(self.parameters)[:200]
    
    def _format_result(self) -> str:
        """Format result for display"""
        result_str = str(self.result)
        if len(result_str) > 100:
            # Try to extract meaningful part
            if isinstance(self.result, dict):
                if 'status' in self.result:
                    return f"Status: {self.result['status']}"
                elif 'success' in self.result:
                    return f"Success: {self.result['success']}"
            return result_str[:97] + "..."
        return result_str

@dataclass
class BuildStats:
    """
    Comprehensive build statistics tracking.
    Enhanced in v2.3 with better categorization and analytics.
    """
    # File operations
    files_created: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    directories_created: int = 0
    
    # Testing metrics
    tests_written: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    test_coverage: float = 0.0  # New in v2.3
    
    # Code metrics
    lines_of_code: int = 0
    functions_created: int = 0  # New in v2.3
    classes_created: int = 0  # New in v2.3
    
    # Execution metrics
    commands_executed: int = 0
    errors_encountered: int = 0
    warnings_encountered: int = 0
    retries_performed: int = 0  # New in v2.3
    
    # Tool usage
    mcp_calls: int = 0
    web_searches: int = 0
    tool_calls: Counter = field(default_factory=Counter)
    tool_success_rate: Dict[str, float] = field(default_factory=dict)  # New in v2.3
    
    # File type tracking
    file_types: Counter = field(default_factory=Counter)
    
    # Performance metrics (new in v2.3)
    phase_durations: Dict[str, float] = field(default_factory=dict)
    tool_durations: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    
    # Active tool tracking
    active_tool_calls: Dict[str, ToolCall] = field(default_factory=dict)
    completed_tool_calls: List[ToolCall] = field(default_factory=list)  # New in v2.3
    
    def increment(self, stat: str, amount: int = 1):
        """Increment a statistic by amount"""
        if hasattr(self, stat):
            setattr(self, stat, getattr(self, stat) + amount)
    
    def add_file(self, filepath: str, created: bool = True):
        """Track file creation/modification with enhanced metrics"""
        if created:
            self.files_created += 1
        else:
            self.files_modified += 1
        
        # Track file type
        ext = Path(filepath).suffix.lower() or 'no_extension'
        self.file_types[ext] += 1
        
        # Count lines and analyze code structure for code files
        code_extensions = {'.py', '.js', '.ts', '.java', '.c', '.cpp', '.go', '.rs', '.rb', '.php', '.jsx', '.tsx'}
        if ext in code_extensions and Path(filepath).exists():
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    self.lines_of_code += len(lines)
                    
                    # Basic code analysis
                    for line in lines:
                        stripped = line.strip()
                        if ext in {'.py'}:
                            if stripped.startswith('def '):
                                self.functions_created += 1
                            elif stripped.startswith('class '):
                                self.classes_created += 1
                        elif ext in {'.js', '.ts', '.jsx', '.tsx'}:
                            if 'function ' in stripped or '=>' in stripped:
                                self.functions_created += 1
                            elif stripped.startswith('class '):
                                self.classes_created += 1
            except Exception:
                pass  # Ignore errors in analysis
    
    def start_tool_call(self, tool_id: str, name: str, parameters: Dict[str, Any], 
                       phase_id: Optional[str] = None) -> ToolCall:
        """Start tracking a tool call with enhanced metadata"""
        tool_call = ToolCall(
            id=tool_id, 
            name=name, 
            parameters=parameters,
            phase_id=phase_id
        )
        
        # Categorize tool
        if tool_call.is_mcp_tool:
            tool_call.category = "mcp"
        elif "test" in name.lower():
            tool_call.category = "testing"
        elif any(cmd in name.lower() for cmd in ['bash', 'run', 'execute']):
            tool_call.category = "command"
        else:
            tool_call.category = "file_operation"
        
        self.active_tool_calls[tool_id] = tool_call
        self.tool_calls[name] += 1
        
        # Special tracking for tool types
        if tool_call.is_mcp_tool:
            self.mcp_calls += 1
        elif "web" in name.lower() or "search" in name.lower():
            self.web_searches += 1
        
        return tool_call
    
    def end_tool_call(self, tool_id: str, result: Any = None, error: str = None):
        """End tracking a tool call with enhanced analytics"""
        if tool_id in self.active_tool_calls:
            tool_call = self.active_tool_calls.pop(tool_id)
            tool_call.end_time = datetime.now()
            tool_call.result = result
            tool_call.error = error
            
            # Move to completed
            self.completed_tool_calls.append(tool_call)
            
            # Track duration
            self.tool_durations[tool_call.name].append(tool_call.duration)
            
            # Update success rate
            if tool_call.name not in self.tool_success_rate:
                self.tool_success_rate[tool_call.name] = 0.0
            
            total_calls = self.tool_calls[tool_call.name]
            if error:
                self.errors_encountered += 1
                # Update success rate
                successful_calls = total_calls - sum(1 for tc in self.completed_tool_calls 
                                                   if tc.name == tool_call.name and tc.error)
                self.tool_success_rate[tool_call.name] = successful_calls / total_calls
            else:
                # Update success rate
                successful_calls = sum(1 for tc in self.completed_tool_calls 
                                     if tc.name == tool_call.name and not tc.error)
                self.tool_success_rate[tool_call.name] = successful_calls / total_calls
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of all statistics"""
        # Calculate average tool durations
        avg_tool_durations = {}
        for tool, durations in self.tool_durations.items():
            if durations:
                avg_tool_durations[tool] = sum(durations) / len(durations)
        
        return {
            "files": {
                "created": self.files_created,
                "modified": self.files_modified,
                "deleted": self.files_deleted,
                "types": dict(self.file_types.most_common())
            },
            "code": {
                "lines": self.lines_of_code,
                "functions": self.functions_created,
                "classes": self.classes_created,
                "directories": self.directories_created
            },
            "testing": {
                "written": self.tests_written,
                "passed": self.tests_passed,
                "failed": self.tests_failed,
                "coverage": f"{self.test_coverage:.1f}%"
            },
            "execution": {
                "commands": self.commands_executed,
                "errors": self.errors_encountered,
                "warnings": self.warnings_encountered,
                "retries": self.retries_performed
            },
            "tools": {
                "total_calls": sum(self.tool_calls.values()),
                "mcp_calls": self.mcp_calls,
                "web_searches": self.web_searches,
                "by_tool": dict(self.tool_calls.most_common()),
                "success_rates": {k: f"{v:.1%}" for k, v in self.tool_success_rate.items()},
                "avg_durations": {k: f"{v:.1f}s" for k, v in avg_tool_durations.items()}
            },
            "performance": {
                "phase_durations": {k: f"{v:.1f}s" for k, v in self.phase_durations.items()},
                "total_tool_time": sum(sum(d) for d in self.tool_durations.values())
            }
        }

@dataclass
class CostTracker:
    """
    Tracks API usage costs across all phases of execution.
    Enhanced in v2.3 with accurate Claude Code cost tracking.
    """
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    claude_code_cost: float = 0.0  # New in v2.3
    research_cost: float = 0.0  # New in v2.3
    phase_costs: Dict[str, float] = field(default_factory=dict)
    phase_tokens: Dict[str, Dict[str, int]] = field(default_factory=dict)
    model_usage: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"input": 0, "output": 0}))
    claude_code_sessions: List[Dict[str, Any]] = field(default_factory=list)  # New in v2.3
    
    def add_tokens(self, input_tokens: int, output_tokens: int, model: str, phase: str = "general"):
        """Add tokens and calculate cost for a specific model and phase"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        # Track per-phase tokens
        if phase not in self.phase_tokens:
            self.phase_tokens[phase] = {"input": 0, "output": 0}
        self.phase_tokens[phase]["input"] += input_tokens
        self.phase_tokens[phase]["output"] += output_tokens
        
        # Track per-model usage
        self.model_usage[model]["input"] += input_tokens
        self.model_usage[model]["output"] += output_tokens
        
        # Calculate cost
        if model in TOKEN_COSTS:
            input_cost = (input_tokens / 1_000_000) * TOKEN_COSTS[model]["input"]
            output_cost = (output_tokens / 1_000_000) * TOKEN_COSTS[model]["output"]
            phase_cost = input_cost + output_cost
            
            self.total_cost += phase_cost
            if phase not in self.phase_costs:
                self.phase_costs[phase] = 0.0
            self.phase_costs[phase] += phase_cost
            
            # Track research costs separately
            if "research" in phase.lower():
                self.research_cost += phase_cost
    
    def add_usage(self, usage: 'Usage', model: str, phase: str = "general"):
        """Add tokens from Anthropic Usage object"""
        if usage:
            self.add_tokens(usage.input_tokens, usage.output_tokens, model, phase)
    
    def add_claude_code_cost(self, cost: float, session_data: Dict[str, Any]):
        """Add Claude Code execution cost with session tracking"""
        self.claude_code_cost += cost
        self.total_cost += cost
        
        # Store session data for analysis
        session_info = {
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
            "session_id": session_data.get("session_id"),
            "duration_ms": session_data.get("duration_ms"),
            "num_turns": session_data.get("num_turns"),
            "phase": session_data.get("phase", "unknown")
        }
        self.claude_code_sessions.append(session_info)
        
        # Add to phase costs
        phase = session_data.get("phase", "claude_code_execution")
        if phase not in self.phase_costs:
            self.phase_costs[phase] = 0.0
        self.phase_costs[phase] += cost
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive cost summary with Claude Code breakdown"""
        # Calculate average cost per Claude Code session
        avg_claude_code_cost = 0.0
        if self.claude_code_sessions:
            avg_claude_code_cost = self.claude_code_cost / len(self.claude_code_sessions)
        
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost": round(self.total_cost, 2),
            "claude_code_cost": round(self.claude_code_cost, 2),
            "research_cost": round(self.research_cost, 2),
            "analysis_cost": round(self.total_cost - self.claude_code_cost - self.research_cost, 2),
            "phase_costs": {k: round(v, 2) for k, v in self.phase_costs.items()},
            "phase_tokens": self.phase_tokens,
            "model_usage": dict(self.model_usage),
            "claude_code_sessions": len(self.claude_code_sessions),
            "avg_claude_code_cost": round(avg_claude_code_cost, 4),
            "average_cost_per_phase": round(self.total_cost / max(len(self.phase_costs), 1), 2)
        }
    
    def get_model_breakdown(self) -> List[Dict[str, Any]]:
        """Get cost breakdown by model"""
        breakdown = []
        for model, usage in self.model_usage.items():
            if model in TOKEN_COSTS:
                input_cost = (usage["input"] / 1_000_000) * TOKEN_COSTS[model]["input"]
                output_cost = (usage["output"] / 1_000_000) * TOKEN_COSTS[model]["output"]
                total_cost = input_cost + output_cost
                
                breakdown.append({
                    "model": model,
                    "input_tokens": usage["input"],
                    "output_tokens": usage["output"],
                    "total_tokens": usage["input"] + usage["output"],
                    "cost": round(total_cost, 2)
                })
        
        # Add Claude Code as a separate entry
        if self.claude_code_cost > 0:
            breakdown.append({
                "model": "claude-code-execution",
                "sessions": len(self.claude_code_sessions),
                "avg_turns": sum(s.get("num_turns", 0) for s in self.claude_code_sessions) / max(len(self.claude_code_sessions), 1),
                "cost": round(self.claude_code_cost, 2)
            })
        
        return sorted(breakdown, key=lambda x: x["cost"], reverse=True)

@dataclass
class Phase:
    """
    Represents a single build phase with enhanced metadata.
    Enhanced in v2.3 with better context management and validation.
    """
    id: str
    name: str
    description: str
    tasks: List[str]
    dependencies: List[str] = field(default_factory=list)
    status: BuildStatus = BuildStatus.PENDING
    completed: bool = False
    success: bool = False
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output_summary: Optional[str] = None
    files_created: List[str] = field(default_factory=list)
    retry_count: int = 0
    messages: List[str] = field(default_factory=list)
    tool_calls: List[str] = field(default_factory=list)  # Tool call IDs
    context: Dict[str, Any] = field(default_factory=dict)  # New in v2.3
    validation_results: Dict[str, bool] = field(default_factory=dict)  # New in v2.3
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate phase duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds"""
        if self.duration:
            return self.duration.total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0
    
    def add_message(self, message: str, level: str = "info"):
        """Add a timestamped message to phase history with level"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.messages.append(f"[{timestamp}] [{level.upper()}] {message}")
    
    def add_context(self, key: str, value: Any):
        """Add context information for future phases"""
        self.context[key] = value
    
    def validate(self) -> bool:
        """Validate phase completion"""
        validations = {
            "has_files": len(self.files_created) > 0,
            "no_errors": self.error is None,
            "completed": self.completed,
            "has_output": self.output_summary is not None
        }
        
        self.validation_results = validations
        return all(validations.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tasks": self.tasks,
            "dependencies": self.dependencies,
            "status": self.status.name,
            "completed": self.completed,
            "success": self.success,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "output_summary": self.output_summary,
            "files_created": self.files_created,
            "retry_count": self.retry_count,
            "duration_seconds": self.duration_seconds,
            "messages": self.messages,
            "tool_calls": self.tool_calls,
            "context": self.context,
            "validation_results": self.validation_results
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Phase':
        """Create Phase from dictionary"""
        phase_data = data.copy()
        
        # Convert status
        if 'status' in phase_data:
            phase_data['status'] = BuildStatus[phase_data['status']]
        
        # Convert timestamps
        if phase_data.get('start_time'):
            phase_data['start_time'] = datetime.fromisoformat(phase_data['start_time'])
        if phase_data.get('end_time'):
            phase_data['end_time'] = datetime.fromisoformat(phase_data['end_time'])
        
        # Remove computed fields
        phase_data.pop('duration_seconds', None)
        
        return cls(**phase_data)

@dataclass
class ProjectMemory:
    """
    Persistent project memory with enhanced context management.
    Enhanced in v2.3 with better state tracking and recovery.
    """
    project_name: str
    project_path: str
    specification: str
    specification_hash: str
    phases: List[Phase]
    completed_phases: List[str] = field(default_factory=list)
    current_phase: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    created_files: List[str] = field(default_factory=list)
    important_decisions: List[str] = field(default_factory=list)
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    mcp_servers: Dict[str, Any] = field(default_factory=dict)
    build_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    phase_contexts: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # New in v2.3
    error_log: List[Dict[str, Any]] = field(default_factory=list)  # New in v2.3
    
    def to_json(self) -> str:
        """Convert to JSON for storage"""
        return json.dumps({
            "project_name": self.project_name,
            "project_path": self.project_path,
            "specification": self.specification,
            "specification_hash": self.specification_hash,
            "phases": [p.to_dict() for p in self.phases],
            "completed_phases": self.completed_phases,
            "current_phase": self.current_phase,
            "context": self.context,
            "created_files": self.created_files,
            "important_decisions": self.important_decisions,
            "checkpoints": self.checkpoints,
            "mcp_servers": self.mcp_servers,
            "build_id": self.build_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "phase_contexts": self.phase_contexts,
            "error_log": self.error_log
        }, default=str, indent=2)
    
    @classmethod
    def from_json(cls, data: str) -> 'ProjectMemory':
        """Create from JSON data"""
        obj = json.loads(data)
        
        # Reconstruct phases
        phases = [Phase.from_dict(p) for p in obj['phases']]
        obj['phases'] = phases
        
        # Convert timestamps
        obj['created_at'] = datetime.fromisoformat(obj['created_at'])
        obj['updated_at'] = datetime.fromisoformat(obj['updated_at'])
        
        return cls(**obj)
    
    def add_checkpoint(self, name: str, data: Any = None):
        """Add a checkpoint to the memory"""
        checkpoint = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "phase": self.current_phase,
            "completed_phases": self.completed_phases.copy(),
            "data": data,
            "build_stats_snapshot": data.get("build_stats") if data else None
        }
        self.checkpoints.append(checkpoint)
        self.updated_at = datetime.now()
    
    def store_phase_context(self, phase_id: str, context: Dict[str, Any]):
        """Store context from a completed phase"""
        self.phase_contexts[phase_id] = {
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "files_created": self.get_phase_by_id(phase_id).files_created if self.get_phase_by_id(phase_id) else []
        }
        self.updated_at = datetime.now()
    
    def log_error(self, error: str, phase_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        """Log an error with context"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "phase_id": phase_id,
            "context": context or {}
        }
        self.error_log.append(error_entry)
        self.updated_at = datetime.now()
    
    def get_phase_by_id(self, phase_id: str) -> Optional[Phase]:
        """Get phase by ID"""
        return next((p for p in self.phases if p.id == phase_id), None)
    
    def get_accumulated_context(self, up_to_phase: str) -> Dict[str, Any]:
        """Get accumulated context up to a specific phase"""
        accumulated = self.context.copy()
        
        # Add contexts from completed phases
        for phase in self.phases:
            if phase.id == up_to_phase:
                break
            if phase.id in self.phase_contexts:
                accumulated.update(self.phase_contexts[phase.id].get("context", {}))
        
        return accumulated

@dataclass
class MCPRecommendation:
    """
    Enhanced MCP server recommendation with installation status.
    """
    server_name: str
    confidence: float  # 0.0 to 1.0
    reasons: List[str]
    use_cases: List[str]
    priority: int
    install_command: str
    config_suggestion: Dict[str, Any]
    is_installed: bool = False  # New in v2.3
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ResearchQuery:
    """
    Enhanced research query with better context integration.
    """
    id: str
    query: str
    context: Dict[str, Any]
    focus_areas: List[str]  # New in v2.3: specific areas to focus on
    priority: int
    estimated_time: int  # seconds
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    results: Optional[Dict[str, Any]] = None
    confidence: float = 0.0  # New in v2.3
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CustomInstruction:
    """
    Enhanced custom instruction with better filtering and validation.
    """
    id: str
    name: str
    content: str
    scope: str  # global, project, phase, tool
    context_filters: Dict[str, Any]
    priority: int
    active: bool = True
    validation_rules: List[str] = field(default_factory=list)  # New in v2.3
    
    def matches_context(self, context: Dict[str, Any]) -> bool:
        """Check if instruction applies to given context with enhanced matching"""
        for key, value in self.context_filters.items():
            if key not in context:
                return False
            
            context_value = context[key]
            
            # Handle list values (check if context value is in filter list)
            if isinstance(value, list):
                if isinstance(context_value, list):
                    # Check if any value matches
                    if not any(cv in value for cv in context_value):
                        return False
                elif context_value not in value:
                    return False
            # Handle dict values (check nested conditions)
            elif isinstance(value, dict):
                if not isinstance(context_value, dict):
                    return False
                for sub_key, sub_value in value.items():
                    if sub_key not in context_value or context_value[sub_key] != sub_value:
                        return False
            # Handle regex patterns (new in v2.3)
            elif isinstance(value, str) and value.startswith("regex:"):
                pattern = value[6:]  # Remove "regex:" prefix
                if not re.search(pattern, str(context_value), re.IGNORECASE):
                    return False
            # Handle direct comparison
            elif context_value != value:
                return False
        
        return True
    
    def validate(self) -> bool:
        """Validate instruction content"""
        # Check for required elements in content
        for rule in self.validation_rules:
            if rule == "has_requirements" and "REQUIREMENT" not in self.content:
                return False
            elif rule == "has_examples" and "Example" not in self.content:
                return False
        return True

class MCPRecommendationEngine:
    """
    Enhanced MCP server recommendation engine with better analysis.
    """
    
    def __init__(self):
        self.registry = MCP_SERVER_REGISTRY
        self.usage_patterns = defaultdict(int)
        self.success_rates = defaultdict(float)
        self.installed_servers: Set[str] = set()  # New in v2.3
    
    async def analyze_project_needs(self, specification: str, project_context: Dict[str, Any]) -> List[MCPRecommendation]:
        """
        Enhanced project analysis with deeper pattern matching.
        """
        recommendations = []
        
        # Extract key information from specification
        tech_stack = await self._extract_technology_stack(specification)
        requirements = await self._extract_requirements(specification)
        project_type = await self._determine_project_type(specification)
        complexity = await self._assess_complexity(specification)  # New in v2.3
        
        # Update context with extracted information
        project_context.update({
            "technology_stack": tech_stack,
            "requirements": requirements,
            "project_type": project_type,
            "complexity": complexity
        })
        
        # Check installed servers
        await self._check_installed_servers()
        
        # Generate recommendations for each server
        for server_name, server_info in self.registry.items():
            confidence = self._calculate_confidence(
                server_info, tech_stack, requirements, project_type, complexity
            )
            
            if confidence > 0.3:  # Threshold for recommendations
                recommendations.append(MCPRecommendation(
                    server_name=server_name,
                    confidence=confidence,
                    reasons=self._generate_reasons(server_info, tech_stack, requirements, complexity),
                    use_cases=server_info["use_cases"],
                    priority=server_info["priority"],
                    install_command=f"npm install -g {server_info['package']}",
                    config_suggestion=self._generate_config(server_info, project_context),
                    is_installed=server_name in self.installed_servers
                ))
        
        # Sort by confidence and priority
        recommendations.sort(key=lambda x: (x.confidence, x.priority), reverse=True)
        return recommendations
    
    async def _check_installed_servers(self):
        """Check which MCP servers are already installed"""
        self.installed_servers.clear()
        
        for server_name, server_info in self.registry.items():
            try:
                # Check if package is installed
                check_cmd = ["npm", "list", "-g", server_info['package'], "--depth=0"]
                result = await asyncio.create_subprocess_exec(
                    *check_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if result.returncode == 0:
                    self.installed_servers.add(server_name)
            except:
                pass
    
    async def _assess_complexity(self, specification: str) -> str:
        """Assess project complexity from specification"""
        spec_lower = specification.lower()
        word_count = len(specification.split())
        
        # Complexity indicators
        complex_patterns = [
            r'\bmicroservice\b', r'\bdistributed\b', r'\bscalable\b',
            r'\bhigh.?performance\b', r'\breal.?time\b', r'\bconcurrent\b',
            r'\bload.?balanc\b', r'\bcache\b', r'\bqueue\b'
        ]
        
        complex_count = sum(1 for pattern in complex_patterns 
                          if re.search(pattern, spec_lower))
        
        if word_count > 2000 or complex_count > 3:
            return "high"
        elif word_count > 500 or complex_count > 1:
            return "medium"
        else:
            return "low"
    
    async def _extract_technology_stack(self, specification: str) -> List[str]:
        """Enhanced technology extraction with better patterns"""
        tech_patterns = {
            "python": r"\b(python|fastapi|django|flask|pydantic|pytest|numpy|pandas)\b",
            "javascript": r"\b(javascript|js|node|nodejs|react|vue|angular|express|next\.?js)\b",
            "typescript": r"\b(typescript|ts|tsx|type.?script)\b",
            "database": r"\b(postgresql|postgres|mysql|mongodb|redis|sqlite|database|db|sql)\b",
            "docker": r"\b(docker|container|dockerfile|compose|kubernetes|k8s)\b",
            "cloud": r"\b(aws|azure|gcp|google cloud|amazon|cloud|serverless|lambda)\b",
            "git": r"\b(git|github|gitlab|version control|repository)\b",
            "api": r"\b(api|rest|restful|graphql|endpoint|backend|webhook)\b",
            "frontend": r"\b(frontend|ui|user interface|webapp|website|react|vue|angular)\b",
            "monitoring": r"\b(monitor|metrics|prometheus|grafana|logs|logging|observability)\b",
            "ci/cd": r"\b(ci/cd|continuous integration|deployment|pipeline|github actions|jenkins)\b",
            "security": r"\b(security|auth|oauth|jwt|encryption|ssl|https|firewall)\b",
            "ai/ml": r"\b(machine learning|ml|ai|tensorflow|pytorch|model|training)\b"
        }
        
        detected_tech = []
        spec_lower = specification.lower()
        
        for tech, pattern in tech_patterns.items():
            if re.search(pattern, spec_lower, re.IGNORECASE):
                detected_tech.append(tech)
        
        return detected_tech
    
    async def _extract_requirements(self, specification: str) -> List[str]:
        """Enhanced requirement extraction with more patterns"""
        requirement_patterns = {
            "authentication": r"\b(login|auth|authentication|user|account|signin|oauth|jwt|sso|ldap)\b",
            "database": r"\b(store|data|persist|database|save|crud|query|transaction)\b",
            "api": r"\b(api|endpoint|service|backend|server|webhook|integration)\b",
            "frontend": r"\b(ui|interface|frontend|web|dashboard|app|mobile|responsive)\b",
            "realtime": r"\b(realtime|real-time|websocket|live|push|streaming|event)\b",
            "security": r"\b(secure|security|encrypt|ssl|https|protection|firewall|vpn)\b",
            "scalability": r"\b(scale|scalable|performance|load|concurrent|optimize|cache)\b",
            "deployment": r"\b(deploy|deployment|production|hosting|cloud|release|ci/cd)\b",
            "monitoring": r"\b(monitor|log|metric|alert|observability|tracking|analytics)\b",
            "documentation": r"\b(document|documentation|docs|readme|guide|tutorial|api docs)\b",
            "collaboration": r"\b(team|collaborate|share|multi-user|workflow|permission)\b",
            "backup": r"\b(backup|restore|disaster recovery|redundancy|failover)\b",
            "integration": r"\b(integrate|integration|connect|sync|import|export|webhook)\b"
        }
        
        detected_requirements = []
        spec_lower = specification.lower()
        
        for req, pattern in requirement_patterns.items():
            if re.search(pattern, spec_lower, re.IGNORECASE):
                detected_requirements.append(req)
        
        return detected_requirements
    
    async def _determine_project_type(self, specification: str) -> str:
        """Enhanced project type detection with more categories"""
        type_patterns = {
            "web_application": r"\b(web app|website|webapp|web application|full-stack|spa|pwa)\b",
            "api_service": r"\b(api|service|microservice|backend|rest api|graphql|grpc)\b",
            "cli_tool": r"\b(cli|command line|terminal|console|script|automation tool)\b",
            "data_pipeline": r"\b(pipeline|etl|data processing|analytics|stream|batch processing)\b",
            "ml_system": r"\b(machine learning|ml|ai|model|neural|prediction|training)\b",
            "mobile_app": r"\b(mobile|ios|android|app|react native|flutter|swift)\b",
            "desktop_app": r"\b(desktop|gui|tkinter|qt|electron|native|windows app|mac app)\b",
            "library": r"\b(library|package|sdk|framework|module|npm package|pip package)\b",
            "automation": r"\b(automation|bot|scraper|workflow|task automation|rpa)\b",
            "game": r"\b(game|gaming|unity|unreal|gamedev|3d|2d game)\b",
            "iot": r"\b(iot|embedded|arduino|raspberry pi|sensor|device)\b",
            "blockchain": r"\b(blockchain|smart contract|dapp|web3|crypto|defi)\b"
        }
        
        spec_lower = specification.lower()
        
        # Check each pattern and return the first match
        for project_type, pattern in type_patterns.items():
            if re.search(pattern, spec_lower, re.IGNORECASE):
                return project_type
        
        return "general"
    
    def _calculate_confidence(self, server_info: Dict, tech_stack: List[str], 
                             requirements: List[str], project_type: str, 
                             complexity: str) -> float:
        """
        Enhanced confidence calculation with complexity factor.
        """
        confidence = 0.0
        
        # Base confidence from server priority (normalized to 0-0.2)
        confidence += server_info["priority"] / 50.0
        
        # Technology stack matching (0-0.3)
        tech_matches = self._count_tech_matches(server_info, tech_stack)
        if tech_stack:
            confidence += (tech_matches / len(tech_stack)) * 0.3
        
        # Requirement matching (0-0.3)
        req_matches = self._count_requirement_matches(server_info, requirements)
        if requirements:
            confidence += (req_matches / len(requirements)) * 0.3
        
        # Project type matching (0-0.2)
        if self._matches_project_type(server_info, project_type):
            confidence += 0.2
        
        # Complexity bonus for core servers
        if server_info["category"] == "core":
            if complexity == "high":
                confidence += 0.15
            elif complexity == "medium":
                confidence += 0.1
            else:
                confidence += 0.05
        
        # Boost for already installed servers
        if server_info.get("package", "").split("/")[-1].replace("server-", "") in self.installed_servers:
            confidence += 0.05
        
        # Apply historical success rate if available
        success_rate = self.success_rates.get(server_info.get("package", ""), 0.8)
        confidence *= success_rate
        
        return min(confidence, 1.0)
    
    def _count_tech_matches(self, server_info: Dict, tech_stack: List[str]) -> int:
        """Enhanced technology matching with better mappings"""
        matches = 0
        server_name = server_info.get("package", "").lower()
        
        # Enhanced technology mappings
        tech_mappings = {
            "postgres": ["database", "postgresql", "sql"],
            "sqlite": ["database", "sqlite", "sql"],
            "mongodb": ["database", "mongodb", "nosql"],
            "redis": ["database", "redis", "cache"],
            "git": ["git", "version control"],
            "github": ["git", "github", "ci/cd"],
            "web": ["api", "frontend", "web", "testing"],
            "filesystem": ["*"],  # Matches all projects
            "memory": ["*"],  # Matches all projects
            "sequential-thinking": ["*"],  # Matches all projects
            "context7": ["*"]  # Matches all projects for documentation
        }
        
        # Check server name against mappings
        for server_key, tech_list in tech_mappings.items():
            if server_key in server_name:
                for tech in tech_list:
                    if tech == "*" or tech in tech_stack:
                        matches += 1
                        break
        
        return matches
    
    def _count_requirement_matches(self, server_info: Dict, requirements: List[str]) -> int:
        """Enhanced requirement matching with better patterns"""
        matches = 0
        use_cases = server_info.get("use_cases", [])
        tools = server_info.get("tools", [])
        
        # Enhanced requirement to use case/tool mappings
        requirement_mappings = {
            "database": ["database", "data", "storage", "query", "schema"],
            "api": ["api", "service", "endpoint", "integration"],
            "authentication": ["auth", "security", "user", "permission"],
            "testing": ["test", "validation", "quality", "automation"],
            "deployment": ["deploy", "release", "production", "ci_cd"],
            "monitoring": ["monitor", "log", "metric", "observability", "tracking"],
            "collaboration": ["team", "share", "collaborate", "workflow"],
            "documentation": ["doc", "guide", "help", "reference"],
            "realtime": ["realtime", "live", "push", "websocket", "streaming"],
            "scalability": ["scale", "performance", "optimize", "concurrent"],
            "security": ["security", "encrypt", "protect", "firewall"],
            "backup": ["backup", "restore", "recovery"],
            "integration": ["integrate", "connect", "sync", "webhook"]
        }
        
        for req in requirements:
            if req in requirement_mappings:
                keywords = requirement_mappings[req]
                # Check if any keyword matches use cases or tools
                for keyword in keywords:
                    if any(keyword in use_case.lower() for use_case in use_cases):
                        matches += 1
                        break
                    if any(keyword in tool.lower() for tool in tools):
                        matches += 1
                        break
        
        return matches
    
    def _matches_project_type(self, server_info: Dict, project_type: str) -> bool:
        """Enhanced project type matching with better categories"""
        category = server_info.get("category", "")
        
        # Enhanced project type to category mappings
        type_mappings = {
            "web_application": ["core", "development", "database", "external", "documentation"],
            "api_service": ["core", "development", "database", "external", "documentation"],
            "cli_tool": ["core", "development", "documentation"],
            "data_pipeline": ["database", "core", "external"],
            "ml_system": ["database", "core", "external", "documentation"],
            "mobile_app": ["development", "external", "database"],
            "desktop_app": ["development", "core", "database"],
            "library": ["core", "development", "documentation"],
            "automation": ["external", "communication", "core"],
            "game": ["core", "development"],
            "iot": ["core", "external", "database"],
            "blockchain": ["core", "database", "external"],
            "general": ["core", "documentation"]  # Core servers match all project types
        }
        
        if project_type in type_mappings:
            return category in type_mappings[project_type]
        
        return category == "core"
    
    def _generate_reasons(self, server_info: Dict, tech_stack: List[str], 
                         requirements: List[str], complexity: str) -> List[str]:
        """Enhanced reason generation with complexity consideration"""
        reasons = []
        server_name = server_info.get("package", "").split("/")[-1].replace("server-", "")
        
        # Technology-based reasons
        if server_name == "postgres" and "database" in tech_stack:
            reasons.append("Project uses PostgreSQL database")
        elif server_name == "sqlite" and "database" in tech_stack:
            reasons.append("Lightweight database needs for local development")
        elif server_name == "git" and any(t in tech_stack for t in ["git", "version control"]):
            reasons.append("Version control integration required")
        elif server_name == "filesystem":
            reasons.append("Essential for file and directory operations")
        elif server_name == "memory":
            reasons.append("Persistent context across build phases")
        elif server_name == "sequential-thinking":
            reasons.append("Structured problem solving and planning")
        elif server_name == "context7":
            reasons.append("Access to latest framework documentation")
        
        # Requirement-based reasons
        if "deployment" in requirements and server_name in ["git", "github"]:
            reasons.append("Deployment automation requires version control")
        if "testing" in requirements and server_name == "filesystem":
            reasons.append("Test file creation and management")
        if "api" in requirements and server_name == "web":
            reasons.append("API testing and documentation lookup")
        if "documentation" in requirements and server_name == "context7":
            reasons.append("Framework-specific documentation access")
        
        # Complexity-based reasons
        if complexity == "high":
            if server_name in ["memory", "sequential-thinking"]:
                reasons.append("Complex project requires advanced planning and state management")
            if server_name == "postgres":
                reasons.append("High-complexity projects benefit from robust database")
        
        # Category-based reasons
        if server_info["category"] == "core":
            reasons.append("Core functionality essential for all projects")
        
        # Priority-based reasons
        if server_info["priority"] >= 8:
            reasons.append("High-priority tool with proven reliability")
        
        # Installation status
        if server_name in self.installed_servers:
            reasons.append("Already installed and ready to use")
        
        return reasons[:4]  # Limit to top 4 reasons
    
    def _generate_config(self, server_info: Dict, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced configuration generation with better defaults"""
        config = {
            "command": server_info["command"],
            "args": []
        }
        
        # Process args with template substitution
        for arg in server_info.get("args", []):
            if "${workspace}" in arg:
                arg = arg.replace("${workspace}", project_context.get("output_dir", "."))
            elif "${project_name}" in arg:
                arg = arg.replace("${project_name}", project_context.get("project_name", "project"))
            elif "${" in arg:
                # Keep other templates for user to fill
                pass
            config["args"].append(arg)
        
        # Add environment variables if needed
        if "env" in server_info:
            config["env"] = {}
            for key, value in server_info["env"].items():
                if "${" in value:
                    # Keep template for user to fill
                    config["env"][key] = value
                else:
                    config["env"][key] = value
        
        # Add project-specific configurations
        if server_info.get("config_template"):
            config["settings"] = {}
            for key, value in server_info["config_template"].items():
                if isinstance(value, str) and "${" in value:
                    value = value.replace("${workspace}", project_context.get("output_dir", "."))
                config["settings"][key] = value
        
        return config

class CustomInstructionManager:
    """
    Enhanced custom instruction manager with validation and categorization.
    """
    
    def __init__(self):
        self.instructions: List[CustomInstruction] = []
        self._load_default_instructions()
        self.instruction_cache: Dict[str, List[CustomInstruction]] = {}  # New in v2.3
    
    def _load_default_instructions(self):
        """Load enhanced default instruction templates"""
        default_instructions = [
            CustomInstruction(
                id="global_system",
                name="Global System Instructions",
                content="""You are Claude Code Builder v2.3, an enhanced autonomous project builder. Core principles:

1. PRODUCTION QUALITY: Always create production-ready code with comprehensive error handling
2. NO PLACEHOLDERS: Never use TODO, placeholder, or incomplete implementations
3. COMPLETE IMPLEMENTATIONS: Every function, class, and module must be fully functional
4. BEST PRACTICES: Follow language-specific conventions and industry standards
5. TESTING: Include comprehensive tests with high coverage (aim for >90%)
6. SECURITY: Implement proper security measures and validate all inputs
7. PERFORMANCE: Optimize for performance and scalability
8. DOCUMENTATION: Provide clear documentation with examples
9. MCP INTEGRATION: Use MCP servers intelligently for enhanced functionality
10. MEMORY USAGE: Store important context in memory MCP for future reference
11. ERROR RECOVERY: Implement robust error handling and recovery mechanisms
12. CONTEXT PRESERVATION: Use mcp__memory__store to save decisions and state

Remember: You have full access to the project directory and all configured tools.
Always verify your work with tests and validation.""",
                scope="global",
                context_filters={},
                priority=100,
                validation_rules=["has_requirements"]
            ),
            CustomInstruction(
                id="mcp_best_practices",
                name="MCP Server Best Practices",
                content="""When using MCP servers, follow these enhanced guidelines:

1. TOOL NAMING: MCP tools follow the pattern mcp__<serverName>__<toolName>
2. MEMORY MANAGEMENT:
   - Use mcp__memory__store to save important context after each major decision
   - Use mcp__memory__recall at the start of each phase to get previous context
   - Store structured data with clear keys: phase_<id>_<type>
   - Update existing memories with mcp__memory__update when refining decisions

3. SEQUENTIAL THINKING:
   - Always use mcp__sequential-thinking__plan for complex tasks
   - Break down problems with mcp__sequential-thinking__decompose
   - Validate solutions with mcp__sequential-thinking__evaluate

4. FILESYSTEM OPERATIONS:
   - Prefer mcp__filesystem__* over basic file operations when available
   - Always check file existence before operations
   - Use atomic operations for critical files

5. VERSION CONTROL:
   - Commit after each successful phase with mcp__git__commit
   - Use descriptive commit messages with phase information
   - Create feature branches for experimental changes

6. ERROR HANDLING:
   - Always wrap MCP calls in try-catch blocks
   - Implement fallback strategies for MCP failures
   - Log MCP errors to memory for debugging

7. PERFORMANCE:
   - Batch operations when possible
   - Cache frequently accessed data in memory
   - Monitor MCP call frequency and optimize

Example patterns:
```python
# Store context
await mcp__memory__store(key="phase_1_config", value=config_data)

# Recall context
previous_config = await mcp__memory__recall(key="phase_1_config")

# Plan complex task
plan = await mcp__sequential-thinking__plan(task="implement authentication system")
```""",
                scope="global",
                context_filters={},
                priority=95,
                validation_rules=["has_examples"]
            ),
            CustomInstruction(
                id="phase_context_preservation",
                name="Phase Context Preservation",
                content="""CRITICAL: Preserve and build upon context between phases:

1. AT PHASE START:
   - Use mcp__memory__recall to retrieve all previous phase contexts
   - Review files created in previous phases
   - Understand architectural decisions made
   - Check for any pending tasks or notes

2. DURING PHASE EXECUTION:
   - Reference existing code and patterns
   - Maintain consistency with previous implementations
   - Build upon existing abstractions and interfaces
   - Extend rather than duplicate functionality

3. AT PHASE END:
   - Store all important decisions with mcp__memory__store
   - Document any deviations from the plan
   - Note any technical debt or future improvements
   - Save configuration and state for next phases

4. CONTEXT KEYS:
   - Use structured keys: phase_<id>_<category>
   - Categories: config, decisions, api, schema, state
   - Example: phase_2_api_endpoints, phase_3_database_schema

This ensures continuity and prevents redundant work across phases.""",
                scope="global",
                context_filters={},
                priority=94
            ),
            CustomInstruction(
                id="python_enhanced",
                name="Enhanced Python Development Guidelines",
                content="""For Python projects, follow these comprehensive guidelines:

CODE STRUCTURE:
- Use type hints for ALL function parameters and return values
- Implement Protocol classes for interfaces
- Use dataclasses or Pydantic for data models
- Apply SOLID principles consistently

ERROR HANDLING:
- Create custom exception hierarchy
- Use context managers for resource management
- Implement retry logic with exponential backoff
- Add comprehensive logging with structured formats

PRODUCTION FOCUS:
- Work with real data only (no mocking)
- Implement comprehensive error handling
- Add detailed logging for debugging
- Focus on real-world scenarios
- Manual testing with actual services

PERFORMANCE:
- Use async/await for I/O operations
- Implement caching with functools.lru_cache
- Profile code and optimize bottlenecks
- Use generators for large data processing

DOCUMENTATION:
- Add comprehensive docstrings (Google style)
- Include usage examples in docstrings
- Create API documentation with Sphinx
- Add type stubs for better IDE support

PROJECT STRUCTURE:
```
project/
├── src/
│   └── project_name/
│       ├── __init__.py
│       ├── api/
│       ├── core/
│       ├── models/
│       └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
├── scripts/
├── pyproject.toml
├── Makefile
└── .pre-commit-config.yaml
```""",
                scope="project",
                context_filters={"primary_language": "python"},
                priority=90,
                validation_rules=["has_examples"]
            ),
            CustomInstruction(
                id="typescript_enhanced",
                name="Enhanced TypeScript Development Guidelines",
                content="""For TypeScript projects, implement these patterns:

TYPE SAFETY:
- Enable strict mode in tsconfig.json
- Use discriminated unions for state
- Implement branded types for validation
- Leverage conditional types and generics

CODE PATTERNS:
- Apply functional programming principles
- Use composition over inheritance
- Implement dependency injection
- Create reusable custom hooks (React)

ERROR HANDLING:
- Use Result<T, E> pattern for operations
- Implement proper error boundaries
- Add request/response interceptors
- Use Zod for runtime validation

REAL-WORLD VALIDATION:
- Test with actual API endpoints
- Use real databases and services
- Validate with production-like data
- Focus on error recovery scenarios

PERFORMANCE:
- Implement code splitting
- Use React.memo and useMemo wisely
- Add service workers for caching
- Optimize bundle size with tree shaking

BUILD CONFIGURATION:
```json
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true
  }
}
```""",
                scope="project",
                context_filters={"primary_language": ["javascript", "typescript"]},
                priority=90
            ),
            CustomInstruction(
                id="api_security_enhanced",
                name="Enhanced API Security Implementation",
                content="""Implement comprehensive API security measures:

AUTHENTICATION & AUTHORIZATION:
- Use JWT with refresh tokens
- Implement OAuth2/OIDC when appropriate
- Add API key management for services
- Use RBAC with fine-grained permissions
- Implement session management properly

INPUT VALIDATION:
- Validate ALL inputs at the edge
- Use schema validation (Joi, Zod, Pydantic)
- Sanitize data to prevent XSS
- Implement rate limiting per endpoint
- Add request size limits

SECURITY HEADERS:
```javascript
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  }
}));
```

DATA PROTECTION:
- Encrypt sensitive data at rest
- Use TLS 1.3 for transport
- Implement field-level encryption
- Add audit logging for sensitive operations
- Use secure session storage

API SECURITY CHECKLIST:
- [ ] Rate limiting implemented
- [ ] Authentication required
- [ ] Authorization checks in place
- [ ] Input validation on all endpoints
- [ ] CORS properly configured
- [ ] Security headers set
- [ ] API versioning implemented
- [ ] Error messages don't leak info
- [ ] Monitoring and alerting active""",
                scope="project",
                context_filters={"requirements": ["api", "security"]},
                priority=92
            ),
            CustomInstruction(
                id="database_optimization",
                name="Database Design & Optimization",
                content="""Implement optimized database design:

SCHEMA DESIGN:
- Normalize to 3NF minimum
- Add appropriate indexes:
  - Primary keys (clustered)
  - Foreign keys
  - Composite indexes for common queries
  - Covering indexes for read-heavy tables
- Use proper data types and constraints
- Implement soft deletes with deleted_at

PERFORMANCE OPTIMIZATION:
```sql
-- Example optimized query
CREATE INDEX idx_users_email_active 
ON users(email, is_active) 
WHERE is_active = true;

-- Partitioning for large tables
CREATE TABLE events (
    id BIGSERIAL,
    created_at TIMESTAMP NOT NULL,
    data JSONB
) PARTITION BY RANGE (created_at);
```

CONNECTION MANAGEMENT:
- Use connection pooling
- Set appropriate pool sizes
- Implement connection retry logic
- Monitor connection health

MIGRATIONS:
- Use versioned migrations
- Make migrations reversible
- Test migrations on copy of production
- Include data migrations when needed

MONITORING:
- Track slow queries
- Monitor index usage
- Watch for lock contention
- Set up query performance alerts""",
                scope="project",
                context_filters={"requirements": "database"},
                priority=85
            ),
            CustomInstruction(
                id="testing_strategy_comprehensive",
                name="Comprehensive Testing Strategy",
                content="""Implement multi-layer testing approach:

UNIT TESTS (70% of tests):
- Test individual functions/methods
- Use mocks for dependencies
- Test edge cases and error conditions
- Aim for 90%+ code coverage

INTEGRATION TESTS (20% of tests):
- Test component interactions
- Use test databases
- Verify API contracts
- Test third-party integrations

E2E TESTS (10% of tests):
- Test critical user journeys
- Run in production-like environment
- Include performance benchmarks
- Test across different browsers/devices

TEST PATTERNS:
```python
# Example comprehensive test
@pytest.mark.parametrize("input,expected", [
    (valid_input, valid_output),
    (edge_case, edge_output),
    (None, raises(ValueError)),
])
async def test_process_data(input, expected, mock_deps):
    # Arrange
    service = DataService(mock_deps)
    
    # Act & Assert
    if isinstance(expected, raises):
        with expected:
            await service.process(input)
    else:
        result = await service.process(input)
        assert result == expected
```

CONTINUOUS TESTING:
- Run tests on every commit
- Parallel test execution
- Test result caching
- Automatic retry of flaky tests
- Coverage tracking and reporting""",
                scope="phase",
                context_filters={"phase_name": ["test", "testing", "validation", "quality"]},
                priority=91
            ),
            CustomInstruction(
                id="deployment_automation",
                name="Deployment & DevOps Automation",
                content="""Implement comprehensive deployment automation:

CONTAINERIZATION:
```dockerfile
# Multi-stage build
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
USER node
EXPOSE 3000
CMD ["node", "server.js"]
```

CI/CD PIPELINE:
- Build on every commit
- Run all tests in parallel
- Security scanning (SAST/DAST)
- Dependency vulnerability checks
- Automated deployment to staging
- Manual approval for production

INFRASTRUCTURE AS CODE:
- Use Terraform or Pulumi
- Version control all configs
- Implement blue-green deployments
- Add automatic rollback capability

MONITORING SETUP:
- Application metrics (Prometheus)
- Distributed tracing (Jaeger)
- Log aggregation (ELK stack)
- Error tracking (Sentry)
- Uptime monitoring
- Performance benchmarks

DEPLOYMENT CHECKLIST:
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Health checks implemented
- [ ] Rollback plan documented
- [ ] Monitoring alerts configured
- [ ] Load testing completed
- [ ] Security scan passed
- [ ] Documentation updated""",
                scope="phase",
                context_filters={"phase_name": ["deploy", "deployment", "devops", "infrastructure"]},
                priority=88
            )
        ]
        
        self.instructions.extend(default_instructions)
    
    def add_instruction(self, instruction: CustomInstruction):
        """Add a custom instruction with validation"""
        if instruction.validate():
            self.instructions.append(instruction)
            # Clear cache when new instruction added
            self.instruction_cache.clear()
        else:
            raise ValueError(f"Invalid instruction: {instruction.name}")
    
    def get_applicable_instructions(self, context: Dict[str, Any]) -> List[CustomInstruction]:
        """Get instructions applicable to the given context with caching"""
        # Create cache key from context
        cache_key = json.dumps(context, sort_keys=True)
        
        if cache_key in self.instruction_cache:
            return self.instruction_cache[cache_key]
        
        applicable = []
        
        for instruction in self.instructions:
            if instruction.active and instruction.matches_context(context):
                applicable.append(instruction)
        
        # Sort by priority (higher first) and scope specificity
        scope_priority = {"global": 0, "project": 1, "phase": 2, "tool": 3}
        applicable.sort(
            key=lambda x: (x.priority, scope_priority.get(x.scope, 0)), 
            reverse=True
        )
        
        # Cache results
        self.instruction_cache[cache_key] = applicable
        
        return applicable
    
    def generate_context_prompt(self, context: Dict[str, Any]) -> str:
        """Generate a comprehensive prompt with applicable instructions"""
        applicable_instructions = self.get_applicable_instructions(context)
        
        if not applicable_instructions:
            return ""
        
        prompt_parts = ["CUSTOM INSTRUCTIONS:\n"]
        
        # Group instructions by scope
        by_scope = defaultdict(list)
        for instruction in applicable_instructions:
            by_scope[instruction.scope].append(instruction)
        
        # Add instructions in order of scope specificity
        for scope in ["global", "project", "phase", "tool"]:
            if scope in by_scope:
                if len(by_scope[scope]) > 0:
                    prompt_parts.append(f"\n[{scope.upper()} SCOPE]")
                    for instruction in by_scope[scope]:
                        prompt_parts.append(f"\n{instruction.name}:")
                        prompt_parts.append(f"{instruction.content}")
        
        prompt_parts.append("\n\nApply these instructions throughout your work.")
        prompt_parts.append("Pay special attention to phase-specific and tool-specific instructions.")
        
        return "\n".join(prompt_parts)
    
    def add_project_specific_instructions(self, project_context: Dict[str, Any], 
                                        research_findings: Optional[Dict[str, Any]] = None):
        """Add enhanced project-specific instructions"""
        project_name = project_context.get("project_name", "project")
        tech_stack = project_context.get("technology_stack", [])
        requirements = project_context.get("requirements", [])
        complexity = project_context.get("complexity", "medium")
        
        # Add complexity-based instructions
        if complexity == "high":
            self.add_instruction(CustomInstruction(
                id=f"{project_name}_high_complexity",
                name="High Complexity Project Guidelines",
                content="""For this high-complexity project:

- Implement comprehensive logging at all levels
- Add distributed tracing for debugging
- Use event sourcing for critical state changes
- Implement circuit breakers for external services
- Add comprehensive monitoring and alerting
- Design for horizontal scalability
- Implement caching at multiple levels
- Use message queues for async processing
- Add feature flags for gradual rollouts
- Implement comprehensive error recovery""",
                scope="project",
                context_filters={"project_name": project_name},
                priority=85
            ))
        
        # Add technology-specific instructions
        if "fastapi" in tech_stack:
            self.add_instruction(CustomInstruction(
                id=f"{project_name}_fastapi",
                name="FastAPI Specific Guidelines",
                content="""For FastAPI development:

STRUCTURE:
```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

app = FastAPI(
    title="API Title",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Dependency injection
async def get_db() -> Session:
    async with SessionLocal() as session:
        yield session

# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )
```

PATTERNS:
- Use dependency injection for all services
- Implement Pydantic models for validation
- Add OpenAPI documentation
- Use background tasks for long operations
- Implement middleware for logging/auth
- Add health check endpoints
- Use async database drivers
- Implement proper CORS handling""",
                scope="project",
                context_filters={"project_name": project_name},
                priority=75
            ))
        
        if "react" in tech_stack or "next.js" in tech_stack:
            self.add_instruction(CustomInstruction(
                id=f"{project_name}_react_next",
                name="React/Next.js Development Guidelines",
                content="""For React/Next.js development:

COMPONENT PATTERNS:
```typescript
// Use functional components with TypeScript
interface Props {
  data: DataType;
  onUpdate: (data: DataType) => Promise<void>;
}

export const DataComponent: FC<Props> = memo(({ data, onUpdate }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const handleUpdate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await onUpdate(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [data, onUpdate]);
  
  return (
    <ErrorBoundary>
      {/* Component JSX */}
    </ErrorBoundary>
  );
});
```

NEXT.JS SPECIFIC:
- Use App Router for new projects
- Implement ISR for static content
- Use Server Components by default
- Add loading.tsx and error.tsx
- Implement proper metadata
- Use next/image for optimization
- Add proper caching strategies""",
                scope="project",
                context_filters={"project_name": project_name},
                priority=75
            ))
        
        # Add requirement-specific instructions
        if "realtime" in requirements:
            self.add_instruction(CustomInstruction(
                id=f"{project_name}_realtime",
                name="Real-time System Guidelines",
                content="""For real-time functionality:

- Implement WebSocket connections with reconnection logic
- Use Socket.io or native WebSockets
- Add heartbeat/ping-pong for connection health
- Implement message queuing for offline support
- Add event deduplication
- Use optimistic UI updates
- Implement proper error recovery
- Add connection state indicators
- Use binary protocols for performance
- Implement backpressure handling""",
                scope="project",
                context_filters={"project_name": project_name},
                priority=80
            ))
        
        # Add research-based instructions if available
        if research_findings:
            self._add_research_based_instructions(project_name, research_findings)
    
    def _add_research_based_instructions(self, project_name: str, research_findings: Dict[str, Any]):
        """Add instructions based on research findings"""
        # Extract key insights from research
        for category, findings in research_findings.items():
            if isinstance(findings, dict) and "recommendations" in findings:
                recommendations = findings.get("recommendations", [])[:5]
                best_practices = findings.get("best_practices", [])[:5]
                
                if recommendations or best_practices:
                    content_parts = [f"Based on research for {category}:\n"]
                    
                    if recommendations:
                        content_parts.append("RECOMMENDATIONS:")
                        for rec in recommendations:
                            content_parts.append(f"- {rec}")
                    
                    if best_practices:
                        content_parts.append("\nBEST PRACTICES:")
                        for practice in best_practices:
                            content_parts.append(f"- {practice}")
                    
                    content_parts.append("\nImplement these insights throughout the project.")
                    
                    self.add_instruction(CustomInstruction(
                        id=f"{project_name}_research_{category}",
                        name=f"Research-Based {category.title()} Guidelines",
                        content="\n".join(content_parts),
                        scope="project",
                        context_filters={"project_name": project_name},
                        priority=85
                    ))

class ResearchAgent:
    """
    Enhanced research agent using Anthropic SDK for knowledge-based analysis.
    """
    
    def __init__(self, name: str, specialty: str, anthropic_client: Optional[AsyncAnthropic] = None):
        self.name = name
        self.specialty = specialty
        self.anthropic = anthropic_client
        self.research_model = DEFAULT_RESEARCH_MODEL
    
    async def research(self, query: ResearchQuery, context: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct knowledge-based research using Anthropic SDK"""
        if not self.anthropic:
            return {"error": "Anthropic client not available", "agent": self.name}
        
        research_prompt = self._create_research_prompt(query, context)
        
        try:
            # Use Anthropic SDK for knowledge-based research
            response = await self.anthropic.messages.create(
                model=self.research_model,
                max_tokens=4096,
                temperature=0.1,  # Lower temperature for factual research
                messages=[{
                    "role": "user",
                    "content": research_prompt
                }]
            )
            
            # Extract content from response
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        content += block.text
            
            # Parse and enhance results
            results = self._parse_research_results(content)
            
            # Add confidence score based on response quality
            results["confidence"] = self._calculate_confidence(results)
            results["agent"] = self.name
            results["specialty"] = self.specialty
            
            return results
            
        except Exception as e:
            return {
                "error": str(e), 
                "agent": self.name,
                "specialty": self.specialty
            }
    
    def _create_research_prompt(self, query: ResearchQuery, context: Dict[str, Any]) -> str:
        """Create enhanced research prompt focusing on specific areas"""
        focus_areas_str = ""
        if query.focus_areas:
            focus_areas_str = f"\nFOCUS AREAS:\n" + "\n".join(f"- {area}" for area in query.focus_areas)
        
        return f"""You are a {self.specialty} research specialist providing expert analysis for a software project.

RESEARCH QUERY: {query.query}

PROJECT CONTEXT:
- Project Type: {context.get('project_type', 'Unknown')}
- Technology Stack: {', '.join(context.get('technology_stack', []))}
- Requirements: {', '.join(context.get('requirements', []))}
- Complexity: {context.get('complexity', 'medium')}
{focus_areas_str}

RESEARCH INSTRUCTIONS:
1. Provide current best practices and patterns (as of 2024-2025)
2. Include specific implementation details and code examples
3. Focus on production-ready, enterprise-grade solutions
4. Consider security, performance, and maintainability
5. Provide concrete, actionable recommendations
6. Include version numbers and tool recommendations
7. Address the specific focus areas if provided

Structure your response as JSON with the following format:
{{
    "summary": "Brief overview of findings",
    "key_insights": ["List of key insights"],
    "recommendations": ["Specific actionable recommendations"],
    "best_practices": ["Current industry best practices"],
    "implementation_patterns": ["Code patterns and examples"],
    "tools_and_versions": {{"tool": "recommended_version"}},
    "security_considerations": ["Security-specific recommendations"],
    "performance_tips": ["Performance optimization strategies"],
    "common_pitfalls": ["Common mistakes to avoid"],
    "resources": ["Key documentation or learning resources"],
    "confidence_level": "High/Medium/Low"
}}

Provide comprehensive, expert-level analysis based on current industry standards."""
    
    def _parse_research_results(self, content: str) -> Dict[str, Any]:
        """Parse research results with enhanced error handling"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                results = json.loads(json_match.group())
                
                # Validate and enhance results
                required_keys = ["summary", "recommendations", "best_practices"]
                for key in required_keys:
                    if key not in results:
                        results[key] = []
                
                # Ensure all lists are actually lists
                list_keys = ["key_insights", "recommendations", "best_practices", 
                           "implementation_patterns", "security_considerations",
                           "performance_tips", "common_pitfalls", "resources"]
                for key in list_keys:
                    if key in results and not isinstance(results[key], list):
                        results[key] = [results[key]] if results[key] else []
                
                return results
            else:
                # Fallback parsing for non-JSON responses
                return self._fallback_parse(content)
        except json.JSONDecodeError:
            return self._fallback_parse(content)
    
    def _fallback_parse(self, content: str) -> Dict[str, Any]:
        """Fallback parsing when JSON extraction fails"""
        # Extract key sections using patterns
        sections = {
            "summary": self._extract_section(content, ["summary", "overview"]),
            "recommendations": self._extract_list_section(content, ["recommend", "suggestion"]),
            "best_practices": self._extract_list_section(content, ["best practice", "pattern"]),
            "implementation_patterns": self._extract_code_blocks(content),
            "security_considerations": self._extract_list_section(content, ["security"]),
            "performance_tips": self._extract_list_section(content, ["performance", "optimization"]),
            "tools_and_versions": {},
            "common_pitfalls": self._extract_list_section(content, ["pitfall", "mistake", "avoid"]),
            "resources": self._extract_list_section(content, ["resource", "documentation", "link"]),
            "raw_content": content,
            "parsing_method": "fallback"
        }
        
        return sections
    
    def _extract_section(self, content: str, keywords: List[str]) -> str:
        """Extract a section based on keywords"""
        for keyword in keywords:
            pattern = rf"{keyword}[:\s]*([^.]+\.)"
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""
    
    def _extract_list_section(self, content: str, keywords: List[str]) -> List[str]:
        """Extract list items based on keywords"""
        items = []
        for keyword in keywords:
            # Look for bullet points or numbered lists after keyword
            pattern = rf"{keyword}[:\s]*\n((?:[-*•]\s*[^\n]+\n?)+)"
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                list_text = match.group(1)
                # Extract individual items
                item_pattern = r'[-*•]\s*([^\n]+)'
                items.extend(re.findall(item_pattern, list_text))
        return items[:10]  # Limit to 10 items
    
    def _extract_code_blocks(self, content: str) -> List[str]:
        """Extract code blocks from content"""
        code_pattern = r'```[\w]*\n([\s\S]*?)\n```'
        code_blocks = re.findall(code_pattern, content)
        return code_blocks[:5]  # Limit to 5 code blocks
    
    def _calculate_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate confidence score based on result quality"""
        confidence = 0.5  # Base confidence
        
        # Check for key sections
        if results.get("summary"):
            confidence += 0.1
        if len(results.get("recommendations", [])) > 3:
            confidence += 0.1
        if len(results.get("best_practices", [])) > 3:
            confidence += 0.1
        if results.get("implementation_patterns"):
            confidence += 0.1
        if results.get("tools_and_versions"):
            confidence += 0.1
        
        # Check for parsing method
        if results.get("parsing_method") == "fallback":
            confidence *= 0.8
        
        # Cap at 1.0
        return min(confidence, 1.0)

class ResearchManager:
    """
    Enhanced research manager with better coordination and synthesis.
    """
    
    def __init__(self, anthropic_client: Optional[AsyncAnthropic] = None):
        self.anthropic = anthropic_client
        self.agents = self._create_research_agents()
        self.active_queries: Dict[str, ResearchQuery] = {}
        self.research_history: List[Dict[str, Any]] = []
        self.synthesis_model = DEFAULT_ANALYZER_MODEL  # Use best model for synthesis
    
    def _create_research_agents(self) -> Dict[str, ResearchAgent]:
        """Create specialized research agents with enhanced capabilities"""
        return {
            "technology": ResearchAgent(
                "Technology Analyst", 
                "technology stack analysis, framework selection, and tooling recommendations", 
                self.anthropic
            ),
            "security": ResearchAgent(
                "Security Specialist", 
                "cybersecurity, authentication, authorization, and data protection", 
                self.anthropic
            ),
            "performance": ResearchAgent(
                "Performance Engineer", 
                "performance optimization, scalability, caching, and resource management", 
                self.anthropic
            ),
            "architecture": ResearchAgent(
                "Solutions Architect", 
                "system architecture, design patterns, microservices, and integration", 
                self.anthropic
            ),
            "best_practices": ResearchAgent(
                "Best Practices Advisor", 
                "industry standards, coding conventions, and development workflows", 
                self.anthropic
            ),
            "testing": ResearchAgent(
                "Quality Assurance Expert",
                "testing strategies, automation, CI/CD, and quality metrics",
                self.anthropic
            ),
            "deployment": ResearchAgent(
                "DevOps Specialist",
                "deployment strategies, containerization, monitoring, and infrastructure",
                self.anthropic
            )
        }
    
    async def conduct_comprehensive_research(self, specification: str, 
                                           project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct enhanced multi-agent research with synthesis"""
        if not self.anthropic:
            return {"error": "Research requires Anthropic API key"}
        
        research_queries = self._generate_research_queries(specification, project_context)
        
        # Execute research queries in parallel with progress tracking
        research_tasks = []
        for query in research_queries:
            self.active_queries[query.id] = query
            
            # Assign agents based on query focus areas
            assigned_agents = self._assign_agents_to_query(query)
            
            for agent_name in assigned_agents:
                if agent_name in self.agents:
                    task = self.agents[agent_name].research(query, project_context)
                    research_tasks.append((agent_name, query.id, task))
        
        # Wait for all research to complete with timeout
        results = {}
        completed = 0
        total = len(research_tasks)
        
        for agent_name, query_id, task in research_tasks:
            try:
                # Add timeout to prevent hanging
                result = await asyncio.wait_for(task, timeout=120.0)  # 2 minute timeout
                
                if query_id not in results:
                    results[query_id] = {}
                results[query_id][agent_name] = result
                
                completed += 1
                # Update progress in active queries
                if query_id in self.active_queries:
                    self.active_queries[query_id].status = f"completed_{completed}/{total}"
                    
            except asyncio.TimeoutError:
                console.print(f"[yellow]Research timeout for {agent_name}[/yellow]")
            except Exception as e:
                console.print(f"[red]Research failed for {agent_name}: {e}[/red]")
        
        # Synthesize results with enhanced analysis
        synthesized_results = await self._enhanced_synthesis(results, project_context)
        
        # Store in history
        self.research_history.append({
            "timestamp": datetime.now().isoformat(),
            "project_context": project_context,
            "queries": [q.to_dict() for q in research_queries],
            "results": synthesized_results,
            "agent_participation": {
                query_id: list(agent_results.keys()) 
                for query_id, agent_results in results.items()
            }
        })
        
        # Clear active queries
        self.active_queries.clear()
        
        return synthesized_results
    
    def _assign_agents_to_query(self, query: ResearchQuery) -> List[str]:
        """Assign appropriate agents based on query focus areas"""
        # Default assignments based on query ID
        default_assignments = {
            "technology_analysis": ["technology", "best_practices"],
            "security_analysis": ["security"],
            "architecture_patterns": ["architecture", "best_practices"],
            "performance_optimization": ["performance"],
            "testing_strategy": ["testing", "best_practices"],
            "deployment_strategy": ["deployment", "security"]
        }
        
        assigned = default_assignments.get(query.id, ["best_practices"])
        
        # Add agents based on focus areas
        for focus_area in query.focus_areas:
            if "security" in focus_area.lower():
                assigned.append("security")
            elif "performance" in focus_area.lower():
                assigned.append("performance")
            elif "test" in focus_area.lower():
                assigned.append("testing")
            elif "deploy" in focus_area.lower() or "devops" in focus_area.lower():
                assigned.append("deployment")
        
        # Remove duplicates while preserving order
        seen = set()
        return [x for x in assigned if not (x in seen or seen.add(x))]
    
    def _generate_research_queries(self, specification: str, 
                                 project_context: Dict[str, Any]) -> List[ResearchQuery]:
        """Generate enhanced research queries with focus areas"""
        queries = []
        tech_stack = project_context.get("technology_stack", [])
        project_type = project_context.get("project_type", "application")
        requirements = project_context.get("requirements", [])
        complexity = project_context.get("complexity", "medium")
        
        # Technology stack research with specific focus
        if tech_stack:
            focus_areas = [
                f"Latest stable versions for {', '.join(tech_stack[:3])}",
                "Integration patterns between technologies",
                "Common compatibility issues and solutions",
                "Performance optimization techniques"
            ]
            
            queries.append(ResearchQuery(
                id="technology_analysis",
                query=f"Analyze best practices and patterns for {', '.join(tech_stack)} in {project_type} development",
                context=project_context,
                focus_areas=focus_areas,
                priority=10,
                estimated_time=60
            ))
        
        # Security research with comprehensive focus
        security_focus = [
            f"Authentication and authorization for {project_type}",
            "Data protection and encryption strategies",
            "Common vulnerabilities and mitigation",
            "Compliance requirements (GDPR, SOC2, etc.)",
            "Security testing and monitoring"
        ]
        
        queries.append(ResearchQuery(
            id="security_analysis",
            query=f"Comprehensive security strategy for {project_type} including authentication, data protection, and vulnerability prevention",
            context=project_context,
            focus_areas=security_focus,
            priority=9,
            estimated_time=60
        ))
        
        # Architecture patterns with scalability focus
        architecture_focus = [
            f"Scalable architecture patterns for {complexity} complexity projects",
            "Microservices vs monolith decision criteria",
            "Event-driven architecture considerations",
            "API design and versioning strategies",
            "Database architecture and sharding"
        ]
        
        queries.append(ResearchQuery(
            id="architecture_patterns",
            query=f"Recommended architecture patterns for scalable {project_type} with {', '.join(tech_stack) if tech_stack else 'modern tech stack'}",
            context=project_context,
            focus_areas=architecture_focus,
            priority=8,
            estimated_time=60
        ))
        
        # Performance optimization (conditional)
        if "scalability" in requirements or complexity == "high":
            performance_focus = [
                "Caching strategies at different layers",
                "Database query optimization",
                "Load balancing and horizontal scaling",
                "CDN and asset optimization",
                "Monitoring and profiling tools"
            ]
            
            queries.append(ResearchQuery(
                id="performance_optimization",
                query=f"Performance optimization strategies for high-traffic {project_type}",
                context=project_context,
                focus_areas=performance_focus,
                priority=7,
                estimated_time=60
            ))
        
        # Testing strategy
        testing_focus = [
            "Test pyramid implementation",
            "Automated testing frameworks",
            "CI/CD integration",
            "Performance and load testing",
            "Security testing automation"
        ]
        
        queries.append(ResearchQuery(
            id="testing_strategy",
            query=f"Comprehensive testing strategy for {project_type} including unit, integration, E2E, and performance testing",
            context=project_context,
            focus_areas=testing_focus,
            priority=6,
            estimated_time=60
        ))
        
        # Deployment strategy
        deployment_focus = [
            "Container orchestration options",
            "CI/CD pipeline design",
            "Infrastructure as Code",
            "Monitoring and observability",
            "Disaster recovery planning"
        ]
        
        queries.append(ResearchQuery(
            id="deployment_strategy",
            query=f"Modern deployment and DevOps practices for {project_type} with focus on automation and reliability",
            context=project_context,
            focus_areas=deployment_focus,
            priority=5,
            estimated_time=60
        ))
        
        return queries
    
    async def _enhanced_synthesis(self, results: Dict[str, Dict[str, Any]], 
                                project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced synthesis with AI-powered integration"""
        # First, do basic synthesis
        basic_synthesis = self._basic_synthesis(results)
        
        # Then use AI to create a coherent, prioritized synthesis
        if self.anthropic:
            synthesis_prompt = self._create_synthesis_prompt(basic_synthesis, project_context)
            
            try:
                response = await self.anthropic.messages.create(
                    model=self.synthesis_model,
                    max_tokens=8192,
                    temperature=0.2,
                    messages=[{
                        "role": "user",
                        "content": synthesis_prompt
                    }]
                )
                
                # Extract content
                content = ""
                if response.content:
                    for block in response.content:
                        if hasattr(block, 'text'):
                            content += block.text
                
                # Parse synthesized results
                final_synthesis = self._parse_synthesis(content)
                
                # Merge with basic synthesis
                final_synthesis.update(basic_synthesis)
                
                return final_synthesis
                
            except Exception as e:
                console.print(f"[yellow]AI synthesis failed, using basic synthesis: {e}[/yellow]")
                return basic_synthesis
        
        return basic_synthesis
    
    def _basic_synthesis(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Basic synthesis of research results"""
        synthesized = {
            "summary": {},
            "recommendations": {},
            "best_practices": {},
            "security_guidelines": {},
            "implementation_roadmap": [],
            "tool_recommendations": {},
            "key_decisions": []
        }
        
        # Process each query's results
        for query_id, query_results in results.items():
            query_synthesis = {
                "recommendations": [],
                "best_practices": [],
                "security": [],
                "tools": {},
                "patterns": [],
                "confidence": 0.0
            }
            
            agent_count = 0
            total_confidence = 0.0
            
            # Combine findings from all agents
            for agent_name, agent_result in query_results.items():
                if "error" not in agent_result:
                    agent_count += 1
                    
                    # Extract and deduplicate recommendations
                    if "recommendations" in agent_result:
                        query_synthesis["recommendations"].extend(agent_result["recommendations"])
                    if "best_practices" in agent_result:
                        query_synthesis["best_practices"].extend(agent_result["best_practices"])
                    if "security_considerations" in agent_result:
                        query_synthesis["security"].extend(agent_result["security_considerations"])
                    if "tools_and_versions" in agent_result:
                        query_synthesis["tools"].update(agent_result["tools_and_versions"])
                    if "implementation_patterns" in agent_result:
                        query_synthesis["patterns"].extend(agent_result["implementation_patterns"])
                    
                    # Track confidence
                    if "confidence" in agent_result:
                        total_confidence += agent_result["confidence"]
            
            # Calculate average confidence
            if agent_count > 0:
                query_synthesis["confidence"] = total_confidence / agent_count
            
            # Remove duplicates and limit items
            for key in ["recommendations", "best_practices", "security", "patterns"]:
                if key in query_synthesis:
                    # Remove duplicates while preserving order
                    seen = set()
                    unique_items = []
                    for item in query_synthesis[key]:
                        if item not in seen:
                            seen.add(item)
                            unique_items.append(item)
                    query_synthesis[key] = unique_items[:10]  # Limit to top 10
            
            synthesized[query_id] = query_synthesis
        
        # Create implementation roadmap
        synthesized["implementation_roadmap"] = self._create_implementation_roadmap(synthesized)
        
        # Extract key decisions
        synthesized["key_decisions"] = self._extract_key_decisions(synthesized)
        
        return synthesized
    
    def _create_synthesis_prompt(self, basic_synthesis: Dict[str, Any], 
                               project_context: Dict[str, Any]) -> str:
        """Create prompt for AI-powered synthesis"""
        return f"""You are synthesizing research findings for a software project. Create a coherent, prioritized action plan.

PROJECT CONTEXT:
- Type: {project_context.get('project_type')}
- Stack: {', '.join(project_context.get('technology_stack', []))}
- Requirements: {', '.join(project_context.get('requirements', []))}
- Complexity: {project_context.get('complexity')}

RESEARCH FINDINGS:
{json.dumps(basic_synthesis, indent=2)}

Create a synthesized response with:
1. Top 10 prioritized recommendations
2. Critical architectural decisions
3. Security must-haves
4. Technology selection rationale
5. Risk mitigation strategies
6. Quick wins vs long-term goals

Format as JSON:
{{
    "executive_summary": "2-3 sentence overview",
    "prioritized_recommendations": [
        {{"priority": 1, "recommendation": "...", "rationale": "...", "effort": "low/medium/high"}}
    ],
    "architectural_decisions": [
        {{"decision": "...", "rationale": "...", "alternatives_considered": []}}
    ],
    "security_requirements": [
        {{"requirement": "...", "implementation": "...", "priority": "critical/high/medium"}}
    ],
    "technology_stack": {{"category": {{"selected": "...", "version": "...", "rationale": "..."}} }},
    "risk_mitigation": [{{"risk": "...", "mitigation": "...", "probability": "low/medium/high"}}],
    "implementation_phases": [
        {{"phase": "...", "duration": "...", "deliverables": [], "dependencies": []}}
    ]
}}"""
    
    def _parse_synthesis(self, content: str) -> Dict[str, Any]:
        """Parse AI synthesis response"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "synthesis_error": "Failed to parse AI synthesis",
            "raw_synthesis": content[:1000]
        }
    
    def _create_implementation_roadmap(self, research_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create enhanced implementation roadmap"""
        roadmap = [
            {
                "phase": "Foundation & Security",
                "priority": 1,
                "tasks": [
                    "Set up project structure with proper separation of concerns",
                    "Implement authentication and authorization framework",
                    "Configure secure communication protocols (HTTPS, TLS)",
                    "Set up comprehensive logging and monitoring",
                    "Implement input validation and sanitization",
                    "Configure development and testing environments"
                ],
                "duration_estimate": "2-3 days",
                "success_criteria": [
                    "All security measures implemented",
                    "Authentication working end-to-end",
                    "Monitoring dashboard accessible"
                ]
            },
            {
                "phase": "Core Implementation",
                "priority": 2,
                "tasks": [
                    "Design and implement data models with validation",
                    "Create core business logic with error handling",
                    "Build API endpoints with proper versioning",
                    "Implement caching strategy",
                    "Add comprehensive error handling",
                    "Create integration points for external services"
                ],
                "duration_estimate": "5-7 days",
                "success_criteria": [
                    "All core features functional",
                    "API documentation complete",
                    "Error handling tested"
                ]
            },
            {
                "phase": "Production Validation",
                "priority": 3,
                "tasks": [
                    "Validate all functionality with real data",
                    "Test error handling with actual services",
                    "Verify performance with production loads",
                    "Check security with real authentication",
                    "Monitor resource usage under real conditions",
                    "Document manual testing procedures"
                ],
                "duration_estimate": "3-4 days",
                "success_criteria": [
                    "All features work with real data",
                    "Error handling proven effective",
                    "Performance meets requirements"
                ]
            },
            {
                "phase": "Deployment & Operations",
                "priority": 4,
                "tasks": [
                    "Create containerized deployment",
                    "Set up infrastructure as code",
                    "Configure monitoring and alerting",
                    "Implement backup and recovery procedures",
                    "Create operational runbooks",
                    "Conduct load testing in staging"
                ],
                "duration_estimate": "2-3 days",
                "success_criteria": [
                    "Successful deployment to staging",
                    "Monitoring active",
                    "Disaster recovery tested"
                ]
            },
            {
                "phase": "Optimization & Polish",
                "priority": 5,
                "tasks": [
                    "Performance optimization based on metrics",
                    "UI/UX improvements based on feedback",
                    "Documentation completion",
                    "Security hardening",
                    "Feature flags implementation",
                    "A/B testing setup"
                ],
                "duration_estimate": "2-3 days",
                "success_criteria": [
                    "Performance targets met",
                    "Documentation complete",
                    "Ready for production"
                ]
            }
        ]
        
        return roadmap
    
    def _extract_key_decisions(self, research_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract key architectural and technology decisions"""
        decisions = []
        
        # Technology stack decisions
        for query_id, results in research_results.items():
            if isinstance(results, dict) and "tools" in results and results["tools"]:
                for tool, version in results["tools"].items():
                    decisions.append({
                        "category": "technology",
                        "decision": f"Use {tool} version {version}",
                        "based_on": query_id,
                        "confidence": results.get("confidence", 0.5)
                    })
        
        # Architecture decisions based on patterns
        if "architecture_patterns" in research_results:
            patterns = research_results["architecture_patterns"].get("patterns", [])
            if patterns:
                decisions.append({
                    "category": "architecture",
                    "decision": "Implement recommended architecture patterns",
                    "details": patterns[:3],  # Top 3 patterns
                    "confidence": research_results["architecture_patterns"].get("confidence", 0.5)
                })
        
        # Security decisions
        if "security_analysis" in research_results:
            security_items = research_results["security_analysis"].get("security", [])
            for item in security_items[:3]:  # Top 3 security decisions
                decisions.append({
                    "category": "security",
                    "decision": item,
                    "priority": "high",
                    "confidence": research_results["security_analysis"].get("confidence", 0.5)
                })
        
        return decisions

class EnhancedToolManager:
    """
    Enhanced tool management with better analytics and optimization.
    """
    
    def __init__(self, available_mcp_servers: Set[str]):
        self.available_mcp_servers = available_mcp_servers
        self.tool_configs: Dict[str, Dict] = {}
        self.usage_stats: Dict[str, int] = defaultdict(int)
        self.performance_metrics: Dict[str, float] = defaultdict(float)
        self.tool_dependencies: Dict[str, Set[str]] = defaultdict(set)  # New in v2.3
        self.disabled_tools: Set[str] = set()  # New in v2.3
    
    def generate_allowed_tools_list(self, context: Dict[str, Any], 
                                   custom_instructions: Optional[CustomInstructionManager] = None) -> List[str]:
        """Generate enhanced context-aware allowed tools list"""
        tools = []
        
        # Core file operations (always included)
        core_tools = [
            # Enhanced file editing tools
            "str_replace_editor",
            "str_replace_based_edit_tool", 
            "str_replace",
            "edit",
            "create",
            "view",
            "write",
            "delete",
            "move",
            "copy",
            "rename",  # New in v2.3
            "chmod",   # New in v2.3
            "mkdir",
            "rmdir",   # New in v2.3
            "ls",
            "find",
            "grep",
            "sed",     # New in v2.3
            "awk"      # New in v2.3
        ]
        tools.extend(core_tools)
        
        # Command execution tools (context-dependent)
        phase_name = context.get("current_phase", "").lower()
        if any(keyword in phase_name for keyword in ["deploy", "test", "build", "setup", "install", "run"]):
            execution_tools = [
                "bash",
                "run_command",
                "execute_command",
                "shell",
                "exec",
                "python",
                "node",
                "npm",
                "yarn",
                "pip",
                "make",
                "docker",
                "kubectl"
            ]
            tools.extend(execution_tools)
        
        # Development tools based on technology stack
        tech_stack = context.get("technology_stack", [])
        
        # Python tools
        if "python" in tech_stack:
            python_tools = [
                "python", "python3", "pip", "pip3", "pytest", "black", 
                "flake8", "mypy", "isort", "poetry", "pipenv", "venv"
            ]
            tools.extend(python_tools)
        
        # JavaScript/TypeScript tools
        if any(tech in tech_stack for tech in ["javascript", "typescript"]):
            js_tools = [
                "node", "npm", "yarn", "pnpm", "jest", "vitest", 
                "eslint", "prettier", "tsc", "webpack", "vite", "rollup"
            ]
            tools.extend(js_tools)
        
        # Docker/Container tools
        if "docker" in tech_stack or "kubernetes" in tech_stack:
            container_tools = [
                "docker", "docker-compose", "kubectl", "helm", 
                "podman", "buildah", "skaffold"
            ]
            tools.extend(container_tools)
        
        # Database tools
        if "database" in tech_stack:
            db_tools = [
                "psql", "mysql", "mongosh", "redis-cli", 
                "sqlite3", "pg_dump", "mongodump"
            ]
            tools.extend(db_tools)
        
        # Web tools for API and web projects
        project_type = context.get("project_type", "")
        if any(keyword in project_type for keyword in ["web", "api"]):
            web_tools = [
                "curl", "wget", "http", "httpie", 
                "ab", "siege", "wrk", "jq"
            ]
            tools.extend(web_tools)
        
        # Add MCP tools with enhanced patterns
        for server in self.available_mcp_servers:
            # Add wildcard pattern for all tools from this server
            tools.append(f"mcp__{server}__*")
            
            # Add specific tools based on server capabilities
            if server in MCP_SERVER_REGISTRY:
                server_info = MCP_SERVER_REGISTRY[server]
                for tool in server_info.get("tools", []):
                    tools.append(f"mcp__{server}__{tool}")
        
        # Git tools (enhanced)
        if "git" in tech_stack or "git" in self.available_mcp_servers:
            git_tools = [
                "git", "git-*",  # Wildcard for all git commands
                "gh",  # GitHub CLI
                "glab"  # GitLab CLI
            ]
            tools.extend(git_tools)
        
        # Testing tools (enhanced)
        if "test" in phase_name or "testing" in context.get("requirements", []):
            test_tools = [
                "test", "pytest", "jest", "mocha", "vitest",
                "coverage", "nyc", "playwright", "cypress",
                "locust", "k6", "junit", "rspec"
            ]
            tools.extend(test_tools)
        
        # CI/CD tools
        if "ci/cd" in context.get("requirements", []) or "deploy" in phase_name:
            cicd_tools = [
                "github-actions", "jenkins", "circleci",
                "travis", "gitlab-ci", "drone", "buildkite"
            ]
            tools.extend(cicd_tools)
        
        # Monitoring tools
        if "monitoring" in context.get("requirements", []):
            monitoring_tools = [
                "prometheus", "grafana", "datadog",
                "newrelic", "sentry", "elastic"
            ]
            tools.extend(monitoring_tools)
        
        # Security tools
        if "security" in context.get("requirements", []):
            security_tools = [
                "trivy", "snyk", "bandit", "safety",
                "semgrep", "sonarqube", "owasp-zap"
            ]
            tools.extend(security_tools)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tools = []
        for tool in tools:
            if tool not in seen and tool not in self.disabled_tools:
                seen.add(tool)
                unique_tools.append(tool)
        
        # Apply custom instruction filters if available
        if custom_instructions:
            applicable_instructions = custom_instructions.get_applicable_instructions(context)
            for instruction in applicable_instructions:
                if "restricted_tools" in instruction.context_filters:
                    restricted = instruction.context_filters["restricted_tools"]
                    unique_tools = [tool for tool in unique_tools if tool not in restricted]
                if "required_tools" in instruction.context_filters:
                    required = instruction.context_filters["required_tools"]
                    for req_tool in required:
                        if req_tool not in unique_tools:
                            unique_tools.append(req_tool)
        
        # Sort tools by priority based on usage stats
        unique_tools.sort(key=lambda x: self.usage_stats.get(x, 0), reverse=True)
        
        return unique_tools
    
    def track_tool_usage(self, tool_name: str, success: bool = True, duration: float = 0.0):
        """Enhanced tool usage tracking with performance metrics"""
        self.usage_stats[tool_name] += 1
        
        # Update performance metrics with weighted average
        if tool_name in self.performance_metrics:
            # Weighted moving average (newer = higher weight)
            alpha = 0.3  # Weight for new observation
            current = self.performance_metrics[tool_name]
            success_score = 1.0 if success else 0.0
            self.performance_metrics[tool_name] = (alpha * success_score) + ((1 - alpha) * current)
        else:
            self.performance_metrics[tool_name] = 1.0 if success else 0.0
        
        # Track tool dependencies
        if duration > 10.0:  # Tools taking >10 seconds might have dependencies
            self.tool_dependencies[tool_name].add("high_latency")
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get enhanced tool usage statistics"""
        total_calls = sum(self.usage_stats.values())
        
        # Calculate tool efficiency scores
        efficiency_scores = {}
        for tool, perf in self.performance_metrics.items():
            usage = self.usage_stats.get(tool, 0)
            if usage > 0:
                # Efficiency = success rate * usage frequency
                efficiency_scores[tool] = perf * (usage / max(total_calls, 1))
        
        # Get top performers
        top_performers = sorted(
            [(tool, score) for tool, score in self.performance_metrics.items() if score > 0.8],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Get problematic tools
        problematic_tools = sorted(
            [(tool, score) for tool, score in self.performance_metrics.items() if score < 0.5],
            key=lambda x: x[1]
        )[:10]
        
        return {
            "usage_counts": dict(self.usage_stats),
            "performance_metrics": dict(self.performance_metrics),
            "most_used": list(Counter(self.usage_stats).most_common(10)),
            "total_calls": total_calls,
            "efficiency_scores": efficiency_scores,
            "top_performers": top_performers,
            "problematic_tools": problematic_tools,
            "disabled_tools": list(self.disabled_tools),
            "tool_dependencies": {k: list(v) for k, v in self.tool_dependencies.items()}
        }
    
    def optimize_tool_list(self, base_tools: List[str]) -> List[str]:
        """Optimize tool list based on performance metrics"""
        optimized = []
        
        for tool in base_tools:
            # Skip tools with poor performance unless essential
            if tool in self.performance_metrics:
                if self.performance_metrics[tool] < 0.3:
                    # Only include if it's a core tool
                    if not any(core in tool for core in ["create", "write", "edit", "mcp__memory"]):
                        continue
            
            optimized.append(tool)
        
        return optimized
    
    def disable_tool(self, tool_name: str, reason: str = ""):
        """Disable a tool due to errors or other issues"""
        self.disabled_tools.add(tool_name)
        if reason:
            self.tool_dependencies[tool_name].add(f"disabled:{reason}")
    
    def enable_tool(self, tool_name: str):
        """Re-enable a previously disabled tool"""
        self.disabled_tools.discard(tool_name)


class StreamingMessageHandler:
    """
    Enhanced streaming message handler with better parsing and cost tracking.
    """
    
    def __init__(self, phase: Phase, console: Console, logger: logging.Logger,
                 build_stats: BuildStats, cost_tracker: CostTracker, args: argparse.Namespace):
        self.phase = phase
        self.console = console
        self.logger = logger
        self.build_stats = build_stats
        self.cost_tracker = cost_tracker  # New in v2.3
        self.args = args
        
        # Message state
        self.current_message = ""
        self.current_tool_use: Optional[Dict[str, Any]] = None
        self.message_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.usage: Optional[Dict[str, Any]] = None
        self.message_count = 0
        self.tool_results: List[Dict[str, Any]] = []  # New in v2.3
        
        # Visual elements
        self.live_display = None
        self.layout = None
        self._setup_display()
    
    def _setup_display(self):
        """Setup enhanced rich display layout"""
        if self.args.parse_output:
            self.layout = Layout()
            self.layout.split_column(
                Layout(name="header", size=3),
                Layout(name="main"),
                Layout(name="tools", size=6),
                Layout(name="footer", size=4)
            )
            
            # Header
            self._update_header()
            
            # Tools area for active tool tracking
            self.layout["tools"].update(
                Panel("No active tools", title="[bold]Tool Activity[/bold]", box=box.ROUNDED)
            )
            
            # Footer with enhanced stats
            self._update_footer()
    
    def _update_header(self):
        """Update header with phase info"""
        if self.layout:
            header_content = f"[bold cyan]Phase: {self.phase.name}[/bold cyan]\n"
            header_content += f"[dim]Tasks: {len(self.phase.tasks)} | Status: {self.phase.status.name}[/dim]"
            self.layout["header"].update(
                Panel(header_content, box=box.ROUNDED)
            )
    
    def _update_footer(self):
        """Update footer with enhanced statistics"""
        if self.layout:
            stats = [
                f"[green]Files: {self.build_stats.files_created}[/green]",
                f"[yellow]Tools: {sum(self.build_stats.tool_calls.values())}[/yellow]",
                f"[blue]Commands: {self.build_stats.commands_executed}[/blue]",
                f"[cyan]MCP: {self.build_stats.mcp_calls}[/cyan]",
                f"[magenta]Messages: {self.message_count}[/magenta]"
            ]
            
            # Add cost if available
            if hasattr(self, 'session_cost'):
                stats.append(f"[red]Cost: ${self.session_cost:.4f}[/red]")
            
            self.layout["footer"].update(
                Panel(" | ".join(stats), box=box.ROUNDED)
            )
    
    def _update_tools_display(self):
        """Update tools activity display"""
        if self.layout and self.build_stats.active_tool_calls:
            tool_widgets = []
            for tool_id, tool_call in list(self.build_stats.active_tool_calls.items())[:3]:
                # Create mini display for each active tool
                status = "[yellow]Running[/yellow]" if not tool_call.end_time else "[green]Done[/green]"
                tool_info = f"{tool_call.name} {status} ({tool_call.duration:.1f}s)"
                tool_widgets.append(tool_info)
            
            if tool_widgets:
                self.layout["tools"].update(
                    Panel("\n".join(tool_widgets), 
                          title=f"[bold]Active Tools ({len(self.build_stats.active_tool_calls)})[/bold]", 
                          box=box.ROUNDED)
                )
    
    async def handle_stream(self, process: asyncio.subprocess.Process):
        """Handle streaming output with enhanced parsing and error recovery"""
        output_buffer = []
        json_buffer = ""
        self.session_cost = 0.0
        
        # Check if there's already a live display active or if streaming is disabled
        if (hasattr(self.console, '_live') and self.console._live is not None) or not self.args.stream_output:
            # If there's already a live display, we'll handle output differently
            self.live_display = None
            use_live = False
        else:
            use_live = True
        
        try:
            # Process the stream based on whether we're using Live display
            if use_live:
                # Use Live display for interactive output
                with Live(self.layout if self.layout else "", console=self.console, 
                          refresh_per_second=4, transient=not self.args.verbose) as live:
                    self.live_display = live
                    return await self._process_stream(process, output_buffer, json_buffer)
            else:
                # Process without Live display
                return await self._process_stream(process, output_buffer, json_buffer)
        except Exception as e:
            self.logger.error(f"Stream handling error: {e}")
            raise
        finally:
            self.live_display = None
    
    async def _process_stream(self, process: asyncio.subprocess.Process, output_buffer: list, json_buffer: str):
        """Process the actual stream output"""
        while True:
            # Read line from stdout
            line = await process.stdout.readline()
            if not line:
                break
            
            decoded = line.decode('utf-8', errors='replace')
            output_buffer.append(decoded)
            
            # Handle JSON parsing with buffering for multi-line JSON
            if decoded.strip().startswith('{'):
                json_buffer = decoded.strip()
            elif json_buffer and decoded.strip():
                json_buffer += decoded.strip()
            
            # Try to parse when we have a complete JSON object
            if json_buffer and (decoded.strip().endswith('}') or decoded.strip() == ''):
                try:
                    event_data = json.loads(json_buffer)
                    await self._handle_event(event_data)
                    json_buffer = ""  # Reset buffer after successful parse
                except json.JSONDecodeError:
                    # Not complete yet or invalid JSON
                    if decoded.strip() == '':
                        # End of a potential JSON block that failed to parse
                        if not self.args.parse_output:
                            self.console.print(json_buffer, end='')
                        json_buffer = ""
            elif not json_buffer and decoded.strip() and not self.args.parse_output:
                # Non-JSON output
                self.console.print(decoded, end='')
        
        # Wait for process to complete
        return_code = await process.wait()
        
        # Process any stderr output
        stderr_output = await process.stderr.read()
        if stderr_output:
            stderr_decoded = stderr_output.decode('utf-8', errors='replace')
            if stderr_decoded.strip():
                self.logger.warning(f"Claude Code stderr: {stderr_decoded}")
        
        # Get final result from output
        for line in reversed(output_buffer):
            try:
                data = json.loads(line.strip())
                if data.get("type") == "result":
                    self.usage = data
                    self.phase.output_summary = self._create_output_summary(data)
                    
                    # Track cost
                    if "cost_usd" in data:
                        self.cost_tracker.add_claude_code_cost(
                            data["cost_usd"],
                            {
                                "session_id": self.session_id,
                                "duration_ms": data.get("duration_ms"),
                                "num_turns": data.get("num_turns"),
                                "phase": self.phase.name
                            }
                        )
                    break
            except:
                continue
        
        return return_code, ''.join(output_buffer)
    
    async def _handle_event(self, event_data: Dict[str, Any]):
        """Handle a single streaming event with enhanced processing"""
        event_type = event_data.get("type", "")
        
        # System initialization
        if event_type == "system" and event_data.get("subtype") == "init":
            self.session_id = event_data.get("session_id")
            tools = event_data.get("tools", [])
            mcp_servers = event_data.get("mcp_servers", [])
            
            self.phase.add_message(f"Session initialized: {self.session_id}")
            if mcp_servers:
                active_servers = [s['name'] for s in mcp_servers if s.get('status') == 'active']
                self.phase.add_message(f"MCP servers active: {', '.join(active_servers)}")
            
            # Update header with session info
            self._update_header()
        
        # User message
        elif event_type == "user":
            self.message_count += 1
            self.phase.add_message("User prompt sent", "info")
        
        # Assistant message
        elif event_type == "assistant":
            self.message_count += 1
            message = event_data.get("message", {})
            
            # Handle different content types
            for content in message.get("content", []):
                await self._handle_content_block(content)
        
        # Tool result (new in v2.3)
        elif event_type == "tool_result":
            tool_id = event_data.get("tool_use_id")
            result = event_data.get("content")
            
            if tool_id and tool_id in self.build_stats.active_tool_calls:
                self.build_stats.end_tool_call(tool_id, result=result)
                self.tool_results.append({
                    "tool_id": tool_id,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
        
        # Result message
        elif event_type == "result":
            await self._handle_result(event_data)
        
        # Error message (new in v2.3)
        elif event_type == "error":
            error_message = event_data.get("message", "Unknown error")
            self.phase.add_message(f"Error: {error_message}", "error")
            self.phase.error = error_message
        
        # Update displays
        if self.layout:
            self._update_footer()
            self._update_tools_display()
    
    async def _handle_content_block(self, content: Dict[str, Any]):
        """Handle a content block from assistant message"""
        content_type = content.get("type", "")
        
        if content_type == "text":
            text = content.get("text", "")
            self.current_message += text
            
            if self.args.parse_output and self.layout:
                # Show last 1500 chars with markdown rendering
                display_text = self.current_message[-1500:]
                self._update_main_display(
                    Panel(Markdown(display_text), 
                          title="Assistant Response", 
                          border_style="green")
                )
        
        elif content_type == "tool_use":
            tool_id = content.get("id", "")
            tool_name = content.get("name", "")
            tool_input = content.get("input", {})
            
            # Track tool call
            tool_call = self.build_stats.start_tool_call(
                tool_id, tool_name, tool_input, self.phase.id
            )
            self.phase.tool_calls.append(tool_id)
            
            if self.args.parse_output:
                self._update_main_display(tool_call.to_rich())
            else:
                self.console.print(f"\n[cyan]→ Tool: {tool_name}[/cyan]")
            
            # Track specific tool usage
            await self._track_tool_use(tool_name, tool_input)
    
    async def _handle_result(self, event_data: Dict[str, Any]):
        """Handle result message with enhanced tracking"""
        subtype = event_data.get("subtype", "")
        
        if subtype == "success":
            self.phase.add_message("Execution completed successfully", "success")
            self.usage = event_data
            
            # Track cost
            if "cost_usd" in event_data:
                self.session_cost = event_data["cost_usd"]
                
        elif subtype == "error_max_turns":
            self.phase.add_message("Maximum turns reached", "warning")
            self.phase.error = "Maximum conversation turns exceeded"
            
        elif subtype == "error":
            error_msg = event_data.get("error", "Unknown error")
            self.phase.add_message(f"Execution error: {error_msg}", "error")
            self.phase.error = error_msg
    
    def _update_main_display(self, content):
        """Update main display area"""
        if self.layout and self.live_display:
            self.layout["main"].update(content)
            self.live_display.update(self.layout)
    
    async def _track_tool_use(self, tool_name: str, tool_input: Dict[str, Any]):
        """Enhanced tool usage tracking"""
        name_lower = tool_name.lower()
        
        # File operations
        if any(op in name_lower for op in ['write', 'create', 'edit']):
            if 'path' in tool_input or 'file' in tool_input:
                file_path = tool_input.get('path') or tool_input.get('file', '')
                if file_path:
                    self.phase.files_created.append(file_path)
                    self.build_stats.add_file(file_path, created='create' in name_lower)
                    
                    # Track file content for analysis
                    if 'content' in tool_input:
                        content = tool_input['content']
                        # Analyze for test files
                        if 'test' in file_path.lower() or 'spec' in file_path.lower():
                            self.build_stats.tests_written += 1
        
        # Command execution
        elif any(cmd in name_lower for cmd in ['bash', 'run', 'execute', 'command']):
            self.build_stats.commands_executed += 1
            command = tool_input.get('command', '')
            
            # Track specific command types
            if any(test_cmd in command for test_cmd in ['pytest', 'jest', 'test', 'mocha']):
                self.build_stats.tests_written += 1
                # Look for coverage in output
                if 'coverage' in command:
                    self.phase.add_context("has_coverage", True)
            
            elif any(install_cmd in command for install_cmd in ['npm install', 'pip install', 'yarn add']):
                self.phase.add_context("dependencies_installed", True)
            
            elif 'git' in command:
                self.phase.add_context("git_operations", True)
        
        # MCP tool tracking
        elif tool_name.startswith("mcp__"):
            parts = tool_name.split("__")
            if len(parts) >= 3:
                server = parts[1]
                operation = parts[2]
                
                # Track memory operations
                if server == "memory" and operation == "store":
                    key = tool_input.get("key", "")
                    self.phase.add_message(f"Stored memory: {key}", "debug")
                
                # Track git operations
                elif server == "git" and operation == "commit":
                    self.phase.add_context("git_commits", True)
    
    def _create_output_summary(self, result_data: Dict[str, Any]) -> str:
        """Create enhanced output summary from result data"""
        summary_parts = []
        
        # Basic metrics
        if "num_turns" in result_data:
            summary_parts.append(f"Turns: {result_data['num_turns']}")
        
        if "duration_ms" in result_data:
            duration_s = result_data['duration_ms'] / 1000.0
            summary_parts.append(f"Duration: {duration_s:.1f}s")
        
        if "cost_usd" in result_data:
            summary_parts.append(f"Cost: ${result_data['cost_usd']:.4f}")
        
        # Add file metrics
        if self.phase.files_created:
            summary_parts.append(f"Files: {len(self.phase.files_created)}")
        
        # Add tool metrics
        if self.phase.tool_calls:
            summary_parts.append(f"Tools: {len(self.phase.tool_calls)}")
        
        # Create summary
        if summary_parts:
            return " | ".join(summary_parts)
        else:
            return "Phase completed"
    
    def get_summary(self) -> Dict[str, Any]:
        """Get enhanced execution summary"""
        return {
            "session_id": self.session_id,
            "usage": self.usage,
            "files_created": len(self.phase.files_created),
            "tools_used": len(self.phase.tool_calls),
            "message_count": self.message_count,
            "tool_results": len(self.tool_results),
            "session_cost": getattr(self, 'session_cost', 0.0),
            "message_preview": self.current_message[:500] if self.current_message else None,
            "has_errors": self.phase.error is not None
        }


# Main Claude Code Builder Class
class ClaudeCodeBuilder:
    """
    Enhanced main builder class with improved error handling and recovery.
    """
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.console = Console()
        self.logger = self._setup_logging()
        self.cost_tracker = CostTracker()
        self.build_stats = BuildStats()
        self.memory: Optional[ProjectMemory] = None
        self.available_mcp_servers: Set[str] = set()
        self.mcp_server_configs: Dict[str, Dict] = {}
        self.custom_instructions = CustomInstructionManager()
        self.research_manager: Optional[ResearchManager] = None
        self.mcp_recommender = MCPRecommendationEngine()
        self.tool_manager: Optional[EnhancedToolManager] = None
        self.start_time = datetime.now()
        self._shutdown_requested = False
        self._setup_signal_handlers()
        
        # Initialize Anthropic client for analysis and research
        if ANTHROPIC_SDK_AVAILABLE and self.args.api_key:
            self.anthropic = AsyncAnthropic(api_key=self.args.api_key)
            self.research_manager = ResearchManager(self.anthropic)
        else:
            self.anthropic = None
            if self.args.enable_research:
                self.logger.warning("Research features require Anthropic API key")
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            self.logger.warning(f"Received signal {signum}, initiating graceful shutdown...")
            self._shutdown_requested = True
            
            # Save current state
            if self.memory:
                asyncio.create_task(self._emergency_checkpoint())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _emergency_checkpoint(self):
        """Save emergency checkpoint on interrupt"""
        try:
            await self._store_memory("emergency_shutdown")
            self.console.print("\n[yellow]Emergency checkpoint saved[/yellow]")
        except Exception as e:
            self.logger.error(f"Failed to save emergency checkpoint: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging configuration"""
        logger = logging.getLogger("claude_builder")
        logger.setLevel(logging.DEBUG if self.args.debug else logging.INFO)
        
        # Remove existing handlers
        logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # File handler for detailed logs
        if self.args.log_file:
            log_dir = os.path.dirname(self.args.log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(self.args.log_file, mode='a')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
        
        # Rich console handler
        console_handler = RichHandler(
            console=self.console,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=self.args.debug
        )
        console_handler.setLevel(getattr(logging, self.args.log_level.upper()))
        logger.addHandler(console_handler)
        
        # Log startup info
        logger.info("="*80)
        logger.info("Claude Code Builder v2.3.0 Starting")
        logger.info("="*80)
        logger.debug(f"Arguments: {vars(self.args)}")
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"Working directory: {os.getcwd()}")
        logger.debug(f"Anthropic SDK available: {ANTHROPIC_SDK_AVAILABLE}")
        
        return logger
    
    async def run(self):
        """Main execution method with enhanced error handling"""
        try:
            # Show banner
            self._show_banner()
            
            # Check prerequisites
            await self._check_prerequisites()
            
            # Load specification
            spec_content = await self._load_specification()
            self._spec_content = spec_content  # Store for later use
            
            # Create output directory
            self._create_output_directory()
            
            # ALWAYS start fresh - no checkpoint resumption
            if await self._check_existing_build():
                self.console.print("[yellow]Found existing build. Starting fresh (checkpoint resumption disabled)...[/yellow]")
                # Clean up old memory and checkpoints
                memory_dir = self.args.output_dir / ".memory"
                if memory_dir.exists():
                    self.logger.info("Cleaning up previous build memory...")
                    shutil.rmtree(memory_dir)
                # Remove checkpoint files
                for checkpoint in self.args.output_dir.glob("checkpoint_*.json"):
                    checkpoint.unlink()
            
            # Initialize git if requested
            if self.args.git_init:
                self._initialize_git()
            
            # Create initial project structure
            await self._create_initial_structure()
            
            # MCP discovery and setup
            if self.args.discover_mcp:
                await self._enhanced_mcp_setup()
            else:
                await self._setup_mcp_configuration()
            
            # Conduct research phase if enabled
            research_results = None
            if self.args.enable_research and self.research_manager:
                research_results = await self._conduct_research_phase(spec_content)
            
            # Analyze project and create phases
            if research_results:
                phases = await self._enhanced_project_analysis(spec_content, research_results)
            else:
                phases = await self._analyze_project(spec_content)
            
            # Initialize project memory
            await self._initialize_memory(spec_content, phases, research_results)
            
            # Setup custom instructions
            await self._setup_custom_instructions(research_results)
            
            # Initialize tool manager
            self.tool_manager = EnhancedToolManager(self.available_mcp_servers)
            
            # Confirm execution plan
            if not self.args.auto_confirm:
                if not await self._confirm_execution_plan(phases):
                    self.console.print("[yellow]Build cancelled by user[/yellow]")
                    return
            
            # Execute phases
            await self._execute_phases(phases)
            
            # Post-build operations
            await self._post_build_operations()
            
            # Validate project
            if self.args.validate:
                validation_passed = await self._validate_project()
                if not validation_passed:
                    self.console.print("[yellow]⚠ Some validations failed. Review the project.[/yellow]")
            
            # Run tests if requested
            if self.args.run_tests:
                await self._run_project_tests()
            
            # Show final report
            self._show_final_report()
            
            # Export report if requested
            if self.args.export_report:
                await self._export_report()
            
        except KeyboardInterrupt:
            self.console.print("\n[red]Build interrupted by user[/red]")
            await self._handle_interruption()
        except Exception as e:
            self.logger.error(f"Build failed: {str(e)}", exc_info=True)
            self.console.print(f"[red]✗ Build failed: {str(e)}[/red]")
            if self.args.debug:
                self.console.print("[dim]" + traceback.format_exc() + "[/dim]")
            await self._handle_failure(e)
        finally:
            await self._cleanup()
    
    def _show_banner(self):
        """Display enhanced startup banner"""
        banner_text = Text.from_markup(
            "[bold cyan]Claude Code Builder v2.3.0[/bold cyan]\n"
            "[dim]Enhanced Production-Ready Autonomous Multi-Phase Project Builder[/dim]\n"
            "[green]🧠 AI Research • 🔧 Smart MCP Management • 📋 Custom Instructions[/green]\n"
            "[blue]🚀 Powered by Claude Code SDK & Anthropic AI[/blue]\n"
            "[yellow]✨ Now with accurate cost tracking & enhanced error recovery[/yellow]"
        )
        
        banner = Panel(
            banner_text,
            box=box.DOUBLE,
            expand=False,
            padding=(1, 2),
            border_style="bright_cyan"
        )
        
        self.console.print(banner)
        self.console.print()
    
    async def _check_prerequisites(self):
        """Enhanced prerequisite checking"""
        self.logger.info("Checking prerequisites...")
        
        with Status("[bold blue]Checking prerequisites...", console=self.console) as status:
            # Check Claude Code CLI
            claude_path = shutil.which("claude")
            if not claude_path:
                # Try npm global bin path
                npm_prefix = subprocess.run(
                    ["npm", "config", "get", "prefix"],
                    capture_output=True,
                    text=True
                ).stdout.strip()
                
                if npm_prefix:
                    claude_path = shutil.which("claude", path=f"{npm_prefix}/bin")
                
                if not claude_path:
                    # Try to find in common locations
                    common_paths = [
                        os.path.expanduser("~/.npm-global/bin"),
                        "/usr/local/bin",
                        "/opt/homebrew/bin"
                    ]
                    for path in common_paths:
                        if os.path.exists(path):
                            claude_path = shutil.which("claude", path=path)
                            if claude_path:
                                break
                
                if not claude_path:
                    raise RuntimeError(
                        "Claude Code CLI not found. "
                        "Install with: npm install -g @anthropic-ai/claude-code\n"
                        "Or add npm global bin to PATH"
                    )
            
            status.update("[green]✓[/green] Claude Code CLI found")
            self.logger.info(f"✓ Claude Code CLI found: {claude_path}")
            
            # Check Claude Code version
            try:
                result = subprocess.run(
                    ["claude", "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                version = result.stdout.strip()
                self.logger.info(f"✓ Claude Code version: {version}")
                
                # Check for minimum version (if needed)
                version_match = re.search(r'(\d+)\.(\d+)\.(\d+)', version)
                if version_match:
                    major, minor, patch = map(int, version_match.groups())
                    # Add version checking logic here if needed
                    
            except Exception as e:
                self.logger.warning(f"Could not check Claude Code version: {e}")
            
            # Check API key if needed
            if not self.args.api_key and not os.environ.get("ANTHROPIC_API_KEY"):
                if self.args.enable_research:
                    raise RuntimeError(
                        "Research features require Anthropic API key. "
                        "Set ANTHROPIC_API_KEY or use --api-key"
                    )
                else:
                    self.logger.warning(
                        "No API key provided. Cost tracking and research unavailable."
                    )
            else:
                status.update("[green]✓[/green] API key configured")
            
            # Check Python version
            if sys.version_info < (3, 8):
                raise RuntimeError(f"Python 3.8+ required, found {sys.version}")
            
            # Check Node.js for MCP servers
            node_path = shutil.which("node")
            if not node_path:
                self.logger.warning("Node.js not found. MCP servers may not work.")
            else:
                # Check Node version
                try:
                    node_version = subprocess.run(
                        ["node", "--version"],
                        capture_output=True,
                        text=True
                    ).stdout.strip()
                    self.logger.info(f"✓ Node.js version: {node_version}")
                    status.update("[green]✓[/green] Node.js available")
                except:
                    pass
            
            # Check npm
            npm_path = shutil.which("npm")
            if not npm_path:
                self.logger.warning("npm not found. Cannot install MCP servers.")
            else:
                status.update("[green]✓[/green] npm available")
            
            # Check disk space
            import shutil as disk_shutil
            stat = disk_shutil.disk_usage(self.args.output_dir.parent)
            free_gb = stat.free / (1024**3)
            if free_gb < 1.0:
                self.logger.warning(f"Low disk space: {free_gb:.1f}GB free")
        
        self.console.print("[green]✓ All prerequisites met[/green]")
    
    async def _check_existing_build(self) -> bool:
        """Enhanced check for existing build with validation"""
        memory_dir = self.args.output_dir / ".memory"
        if memory_dir.exists():
            memory_files = list(memory_dir.glob("*.json"))
            if memory_files:
                # Check if the latest memory is valid
                latest_memory = max(memory_files, key=lambda f: f.stat().st_mtime)
                try:
                    with open(latest_memory, 'r') as f:
                        memory_data = json.load(f)
                        if 'memory' in memory_data:
                            self.logger.info(f"Found valid memory checkpoint: {latest_memory.name}")
                            return True
                except Exception as e:
                    self.logger.warning(f"Invalid memory file {latest_memory}: {e}")
        return False
    
    async def _resume_build(self):
        """Enhanced build resumption with better state recovery"""
        self.logger.info("Resuming build from last checkpoint...")
        
        # Load latest memory
        memory_dir = self.args.output_dir / ".memory"
        memory_files = sorted(memory_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)
        
        if not memory_files:
            self.logger.warning("No memory files found, starting fresh")
            return
        
        # Try to load from most recent valid memory
        loaded = False
        for memory_file in reversed(memory_files):
            try:
                self.logger.info(f"Attempting to load memory from: {memory_file.name}")
                
                with open(memory_file, 'r') as f:
                    memory_data = json.load(f)
                    self.memory = ProjectMemory.from_json(memory_data['memory'])
                    
                    # Restore stats if available
                    if 'stats' in memory_data:
                        self._restore_stats(memory_data['stats'])
                    
                    # Restore costs if available
                    if 'costs' in memory_data:
                        self._restore_costs(memory_data['costs'])
                    
                    loaded = True
                    break
                    
            except Exception as e:
                self.logger.warning(f"Failed to load {memory_file.name}: {e}")
                continue
        
        if not loaded:
            raise RuntimeError("Failed to load any valid memory checkpoint")
        
        # Restore MCP configuration
        if self.memory.mcp_servers:
            self.mcp_server_configs = self.memory.mcp_servers
            self.available_mcp_servers = set(self.memory.mcp_servers.keys())
        
        # Restore custom instructions
        await self._setup_custom_instructions(self.memory.context.get("research_results"))
        
        # Initialize tool manager
        self.tool_manager = EnhancedToolManager(self.available_mcp_servers)
        
        # Display resume information
        self._display_resume_info()
        
        # Resume execution from incomplete phases
        incomplete_phases = [p for p in self.memory.phases if not p.completed]
        if incomplete_phases:
            self.console.print(f"\n[yellow]Resuming {len(incomplete_phases)} incomplete phases[/yellow]")
            
            # Confirm resume if not auto-confirm
            if not self.args.auto_confirm:
                if not Confirm.ask("Continue with incomplete phases?"):
                    self.console.print("[yellow]Resume cancelled[/yellow]")
                    return
            
            await self._execute_phases(self.memory.phases, resume=True)
        else:
            self.console.print("[green]All phases already completed![/green]")
        
        # Show final report
        self._show_final_report()
    
    def _restore_stats(self, stats_dict: Dict[str, Any]):
        """Restore build statistics from checkpoint"""
        for key, value in stats_dict.items():
            if hasattr(self.build_stats, key):
                if isinstance(value, dict):
                    # Handle Counter objects
                    if key in ['tool_calls', 'file_types']:
                        setattr(self.build_stats, key, Counter(value))
                    # Handle defaultdict objects
                    elif key == 'tool_durations':
                        dd = defaultdict(list)
                        dd.update(value)
                        setattr(self.build_stats, key, dd)
                    else:
                        setattr(self.build_stats, key, value)
                elif not isinstance(value, (list, set)):
                    setattr(self.build_stats, key, value)
    
    def _restore_costs(self, costs: Dict[str, Any]):
        """Restore cost tracking from checkpoint"""
        self.cost_tracker.total_input_tokens = costs.get('total_input_tokens', 0)
        self.cost_tracker.total_output_tokens = costs.get('total_output_tokens', 0)
        self.cost_tracker.total_cost = costs.get('total_cost', 0.0)
        self.cost_tracker.claude_code_cost = costs.get('claude_code_cost', 0.0)
        self.cost_tracker.research_cost = costs.get('research_cost', 0.0)
        self.cost_tracker.phase_costs = costs.get('phase_costs', {})
        self.cost_tracker.phase_tokens = costs.get('phase_tokens', {})
        
        # Restore model usage
        if 'model_usage' in costs:
            for model, usage in costs['model_usage'].items():
                self.cost_tracker.model_usage[model] = usage
    
    def _display_resume_info(self):
        """Display information about resumed build"""
        info_table = Table(
            title="[bold]Resumed Build Information[/bold]",
            box=box.ROUNDED,
            show_lines=True
        )
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="white")
        
        info_table.add_row("Project", self.memory.project_name)
        info_table.add_row("Build ID", self.memory.build_id[:8] + "...")
        info_table.add_row("Started", self.memory.created_at.strftime("%Y-%m-%d %H:%M"))
        info_table.add_row("Last Update", self.memory.updated_at.strftime("%Y-%m-%d %H:%M"))
        info_table.add_row("Progress", f"{len(self.memory.completed_phases)}/{len(self.memory.phases)} phases")
        info_table.add_row("Files Created", str(len(self.memory.created_files)))
        info_table.add_row("Current Cost", f"${self.cost_tracker.total_cost:.2f}")
        
        self.console.print(info_table)
    
    async def _load_specification(self) -> str:
        """Load and validate project specification with better error handling"""
        self.logger.info(f"Loading specification from {self.args.spec_file}")
        
        if not self.args.spec_file.exists():
            raise FileNotFoundError(f"Specification file not found: {self.args.spec_file}")
        
        # Check file size
        file_size = self.args.spec_file.stat().st_size
        if file_size > 10 * 1024 * 1024:  # 10MB
            self.logger.warning(f"Large specification file: {file_size / 1024 / 1024:.1f}MB")
        elif file_size == 0:
            raise ValueError("Specification file is empty")
        
        # Load file content
        try:
            if aiofiles:
                async with aiofiles.open(self.args.spec_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
            else:
                with open(self.args.spec_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Store specification content for use in prompts
            self.specification_content = content
        except UnicodeDecodeError:
            # Try different encodings
            for encoding in ['latin-1', 'cp1252']:
                try:
                    with open(self.args.spec_file, 'r', encoding=encoding) as f:
                        content = f.read()
                    self.logger.warning(f"Loaded specification with {encoding} encoding")
                    break
                except:
                    continue
            else:
                raise ValueError("Could not decode specification file")
        
        # Validate specification
        if not content.strip():
            raise ValueError("Specification file is empty")
        
        # Basic specification validation
        if len(content) < 50:
            self.logger.warning("Specification seems very short. Consider adding more detail.")
        
        self.logger.info(f"Loaded specification ({len(content)} characters)")
        
        # Show preview if verbose
        if self.args.verbose:
            lines = content.splitlines()
            preview = '\n'.join(lines[:30])
            if len(lines) > 30:
                preview += f"\n... ({len(lines)-30} more lines)"
            
            self.console.print(Panel(
                Markdown(preview),
                title="[bold]Specification Preview[/bold]",
                border_style="dim"
            ))
        
        return content
    
    def _create_output_directory(self):
        """Create output directory with enhanced structure"""
        self.args.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        subdirs = [
            '.memory',      # Memory checkpoints
            '.prompts',     # Saved prompts
            '.logs',        # Detailed logs
            '.backup',      # Backups
            '.research',    # Research findings
            '.analytics'    # Build analytics
        ]
        for subdir in subdirs:
            (self.args.output_dir / subdir).mkdir(exist_ok=True)
        
        # Create .claude directory for Claude Code
        claude_dir = self.args.output_dir / ".claude"
        claude_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Output directory: {self.args.output_dir.absolute()}")
    
    async def _create_initial_structure(self):
        """Create initial project structure files"""
        # Create CLAUDE.md file with project context
        claude_md_content = f"""# {self.args.output_dir.name}

This project was generated by Claude Code Builder v2.3.0.

## Project Overview
Generated from: {self.args.spec_file.name}
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Builder Configuration
- Research Enabled: {self.args.enable_research}
- MCP Discovery: {self.args.discover_mcp}
- Auto Confirm: {self.args.auto_confirm}

## Development Guidelines
- Always create production-ready code
- No placeholders or TODOs
- Include comprehensive error handling
- Work with real data only (no mocking or unit tests)
- Follow language-specific best practices

## MCP Server Usage
When MCP servers are available, use them for enhanced functionality:
- mcp__memory__* for context preservation
- mcp__sequential-thinking__* for complex problem solving
- mcp__filesystem__* for file operations when available

## Notes
This file is automatically included in Claude Code's context.
Update it with project-specific information as needed.
"""
        
        claude_md_path = self.args.output_dir / "CLAUDE.md"
        with open(claude_md_path, 'w') as f:
            f.write(claude_md_content)
        
        self.logger.debug("Created CLAUDE.md file")
    
    def _initialize_git(self):
        """Initialize git repository with enhanced configuration"""
        try:
            git_dir = self.args.output_dir / ".git"
            if git_dir.exists():
                self.logger.info("Git repository already exists")
                return
            
            # Initialize git
            subprocess.run(
                ["git", "init"],
                cwd=self.args.output_dir,
                check=True,
                capture_output=True
            )
            
            # Configure git
            git_config = [
                ["git", "config", "user.name", "Claude Code Builder"],
                ["git", "config", "user.email", "builder@claude-code.local"]
            ]
            
            for cmd in git_config:
                try:
                    subprocess.run(cmd, cwd=self.args.output_dir, check=True, capture_output=True)
                except:
                    pass  # Ignore config errors
            
            # Create comprehensive .gitignore
            gitignore_content = """# Claude Code Builder Generated .gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
venv/
ENV/
env/
.env
.venv

# JavaScript/Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
lerna-debug.log*
.pnpm-debug.log*
.npm
.yarn/
.pnp.*

# TypeScript
*.tsbuildinfo
.tsc-cache/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.project
.classpath
.c9/
*.launch
.settings/
*.sublime-workspace

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
.AppleDouble
.LSOverride

# Project specific
.memory/
.prompts/
.logs/
.backup/
.research/
.analytics/
*.log
.env.*
!.env.example

# Testing
.coverage
.pytest_cache/
coverage/
htmlcov/
.tox/
.nox/
.hypothesis/
*.cover
*.py,cover
.coverage.*
nosetests.xml
coverage.xml
*.coveragerc
.dmypy.json
dmypy.json

# Build artifacts
*.dll
*.exe
*.o
*.a
*.lib
*.so
*.dylib
*.pdb

# Temporary files
*.tmp
*.temp
*.bak
*.swp
*.orig
*~

# Secrets
*.pem
*.key
*.cert
*.crt
secrets/
credentials/
"""
            
            gitignore_path = self.args.output_dir / ".gitignore"
            with open(gitignore_path, 'w') as f:
                f.write(gitignore_content)
            
            # Create .gitattributes for better diffs
            gitattributes_content = """# Auto detect text files and perform LF normalization
* text=auto

# Explicitly declare text files
*.py text
*.js text
*.ts text
*.jsx text
*.tsx text
*.json text
*.md text
*.yml text
*.yaml text
*.txt text
*.sh text
*.css text
*.html text

# Declare files that will always have CRLF line endings on checkout
*.bat text eol=crlf
*.cmd text eol=crlf

# Denote all files that are truly binary
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.pdf binary
*.zip binary
*.gz binary
*.tar binary
*.tgz binary
*.jar binary
*.war binary
*.ear binary
*.dll binary
*.exe binary
*.so binary
"""
            
            gitattributes_path = self.args.output_dir / ".gitattributes"
            with open(gitattributes_path, 'w') as f:
                f.write(gitattributes_content)
            
            # Create initial commit
            subprocess.run(
                ["git", "add", ".gitignore", ".gitattributes", "CLAUDE.md"],
                cwd=self.args.output_dir,
                check=True,
                capture_output=True
            )
            
            subprocess.run(
                ["git", "commit", "-m", "Initial commit - Claude Code Builder v2.3.0"],
                cwd=self.args.output_dir,
                check=True,
                capture_output=True
            )
            
            self.logger.info("✓ Git repository initialized")
            self.console.print("[green]✓ Git repository initialized[/green]")
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Git initialization error: {e}")
            if e.stderr:
                self.logger.debug(f"Git stderr: {e.stderr.decode()}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize git: {e}")
            self.console.print(f"[yellow]⚠ Git initialization failed: {e}[/yellow]")
    
    async def _enhanced_mcp_setup(self):
        """Enhanced MCP setup with better discovery and configuration"""
        self.console.print("[bold blue]🔍 Discovering and analyzing MCP servers...[/bold blue]")
        
        with Status("Comprehensive MCP analysis...", spinner="dots2", console=self.console):
            # Discover installed MCP servers
            discovered_servers = await self._discover_mcp_servers()
            self.available_mcp_servers = set(discovered_servers.keys())
            
            # Get project context for recommendations
            project_context = {
                "project_name": self.args.output_dir.name,
                "output_dir": str(self.args.output_dir.absolute()),
                "specification": getattr(self, '_spec_content', ''),
                "project_type": "general",
                "complexity": "medium"
            }
            
            # Get MCP recommendations
            if hasattr(self, '_spec_content'):
                recommendations = await self.mcp_recommender.analyze_project_needs(
                    self._spec_content, project_context
                )
                await self._display_mcp_recommendations(recommendations, discovered_servers)
                
                # Auto-install high-confidence missing servers
                if self.args.auto_install_mcp:
                    await self._auto_install_mcp_servers(recommendations)
            
            # Create MCP configuration
            mcp_config = self._create_mcp_config(discovered_servers)
            
            # Write configuration
            mcp_config_path = self.args.output_dir / ".mcp.json"
            with open(mcp_config_path, 'w') as f:
                json.dump(mcp_config, f, indent=2)
            
            self.mcp_server_configs = discovered_servers
            
            # Create MCP usage guide
            self._create_mcp_usage_guide()
    
    async def _setup_mcp_configuration(self):
        """Basic MCP configuration setup"""
        self.logger.info("Setting up MCP configuration...")
        
        with Status("Discovering MCP servers...", spinner="dots", console=self.console):
            mcp_servers = await self._discover_mcp_servers()
        
        self.available_mcp_servers = set(mcp_servers.keys())
        
        # Create MCP configuration
        mcp_config = self._create_mcp_config(mcp_servers)
        
        # Write MCP configuration
        mcp_config_path = self.args.output_dir / ".mcp.json"
        with open(mcp_config_path, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        
        self.logger.info(f"Created MCP configuration with {len(mcp_servers)} servers")
        
        # Display discovered servers
        if mcp_servers:
            self._display_mcp_servers(mcp_servers)
        else:
            self.console.print("[yellow]No MCP servers discovered[/yellow]")
    
    async def _discover_mcp_servers(self) -> Dict[str, Dict]:
        """Discover all available MCP servers with enhanced detection"""
        servers = {}
        
        # Check each server from registry
        for server_name, server_info in MCP_SERVER_REGISTRY.items():
            # Multiple methods to check if server is installed
            installed = False
            
            # Method 1: Check with npm list
            check_cmd = ["npm", "list", "-g", server_info['package'], "--depth=0"]
            try:
                result = await asyncio.create_subprocess_exec(
                    *check_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if result.returncode == 0:
                    installed = True
            except:
                pass
            
            # Method 2: Try to resolve with node
            if not installed:
                check_cmd = ["node", "-e", f"require.resolve('{server_info['package']}')"]
                try:
                    result = await asyncio.create_subprocess_exec(
                        *check_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await result.communicate()
                    
                    if result.returncode == 0:
                        installed = True
                except:
                    pass
            
            if installed:
                servers[server_name] = {
                    "command": server_info["command"],
                    "args": server_info["args"].copy(),
                    "description": server_info["description"],
                    "tools": server_info.get("tools", [])
                }
                
                # Add environment variables if needed
                if "env" in server_info:
                    servers[server_name]["env"] = server_info["env"].copy()
                
                self.logger.debug(f"Discovered MCP server: {server_name}")
        
        # Check for custom servers from args
        if self.args.additional_mcp_servers:
            for server in self.args.additional_mcp_servers:
                if ':' in server:
                    parts = server.split(':', 2)
                    name = parts[0]
                    package = parts[1]
                    desc = parts[2] if len(parts) > 2 else "Custom MCP server"
                    
                    servers[name] = {
                        "command": "npx",
                        "args": ["-y", package],
                        "description": desc
                    }
        
        return servers
    
    def _create_mcp_config(self, servers: Dict[str, Dict]) -> Dict[str, Any]:
        """Create enhanced MCP configuration for Claude Code"""
        # Process server configurations
        mcp_servers = {}
        
        for name, config in servers.items():
            server_config = {
                "command": config["command"],
                "args": []
            }
            
            # Process args with template substitution
            for arg in config.get("args", []):
                if "${workspace}" in arg:
                    arg = arg.replace("${workspace}", str(self.args.output_dir.absolute()))
                elif "${project_name}" in arg:
                    arg = arg.replace("${project_name}", self.args.output_dir.name)
                server_config["args"].append(arg)
            
            # Add environment variables if present
            if "env" in config:
                server_config["env"] = {}
                for key, value in config["env"].items():
                    # Check for environment variable availability
                    if "${" in value:
                        env_var = value.strip("${}")
                        if env_var in os.environ:
                            server_config["env"][key] = os.environ[env_var]
                        else:
                            # Keep template for user to fill
                            server_config["env"][key] = value
                    else:
                        server_config["env"][key] = value
            
            mcp_servers[name] = server_config
        
        return {
            "mcpServers": mcp_servers,
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "builder": "claude-code-builder-v2.3.0",
            "metadata": {
                "total_servers": len(mcp_servers),
                "server_names": list(mcp_servers.keys())
            }
        }
    
    def _display_mcp_servers(self, servers: Dict[str, Dict]):
        """Display discovered MCP servers with enhanced information"""
        table = Table(
            title="[bold]Discovered MCP Servers[/bold]",
            box=box.ROUNDED,
            show_lines=True,
            header_style="bold cyan"
        )
        table.add_column("Server", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Tools", style="yellow")
        table.add_column("Status", justify="center")
        
        for name, info in sorted(servers.items()):
            desc = info.get("description", "No description")
            tools = info.get("tools", [])
            tools_str = ", ".join(tools[:3])
            if len(tools) > 3:
                tools_str += f" +{len(tools)-3}"
            
            table.add_row(
                name, 
                desc, 
                tools_str or "Unknown",
                "[green]✓ Active[/green]"
            )
        
        self.console.print(table)
    
    async def _display_mcp_recommendations(self, recommendations: List[MCPRecommendation], 
                                         discovered_servers: Dict[str, Dict]):
        """Display enhanced MCP server recommendations"""
        if not recommendations:
            return
        
        self.console.print("\n[bold]🤖 MCP Server Recommendations[/bold]\n")
        
        # Separate installed and not installed
        installed = [r for r in recommendations if r.is_installed]
        not_installed = [r for r in recommendations if not r.is_installed]
        
        # Create recommendations table
        table = Table(
            title="[bold]Intelligent MCP Server Analysis[/bold]",
            box=box.ROUNDED,
            show_lines=True,
            header_style="bold cyan"
        )
        table.add_column("Server", style="cyan", no_wrap=True)
        table.add_column("Confidence", justify="center", style="yellow")
        table.add_column("Priority", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Primary Reason", style="white")
        
        # Show installed first
        for rec in installed[:5]:
            confidence_bar = "█" * int(rec.confidence * 10) + "▒" * (10 - int(rec.confidence * 10))
            confidence_str = f"{confidence_bar} {rec.confidence:.1%}"
            priority_str = f"P{rec.priority}"
            status = "[green]✓ Installed[/green]"
            primary_reason = rec.reasons[0] if rec.reasons else "Enhanced functionality"
            
            table.add_row(
                rec.server_name,
                confidence_str,
                priority_str,
                status,
                primary_reason
            )
        
        # Show not installed
        for rec in not_installed[:5]:
            confidence_bar = "█" * int(rec.confidence * 10) + "▒" * (10 - int(rec.confidence * 10))
            confidence_str = f"{confidence_bar} {rec.confidence:.1%}"
            priority_str = f"P{rec.priority}"
            status = "[yellow]⚡ Recommended[/yellow]"
            primary_reason = rec.reasons[0] if rec.reasons else "Enhanced functionality"
            
            table.add_row(
                rec.server_name,
                confidence_str,
                priority_str,
                status,
                primary_reason
            )
        
        self.console.print(table)
        
        # Show installation suggestions for high-confidence missing servers
        missing_high_conf = [r for r in not_installed if r.confidence > 0.7]
        
        if missing_high_conf and not self.args.auto_confirm:
            self.console.print(f"\n[yellow]💡 {len(missing_high_conf)} high-confidence servers not installed[/yellow]")
            
            install_panel_content = []
            for rec in missing_high_conf[:3]:
                install_panel_content.append(f"[bold]{rec.server_name}[/bold]")
                install_panel_content.append(f"  {rec.install_command}")
                install_panel_content.append(f"  [dim]{rec.reasons[0]}[/dim]\n")
            
            self.console.print(Panel(
                "\n".join(install_panel_content),
                title="[bold]Recommended Installations[/bold]",
                border_style="yellow"
            ))
    
    async def _auto_install_mcp_servers(self, recommendations: List[MCPRecommendation]):
        """Auto-install high-confidence MCP servers"""
        to_install = [r for r in recommendations if r.confidence > 0.8 and not r.is_installed]
        
        if not to_install:
            return
        
        self.console.print(f"\n[yellow]Auto-installing {len(to_install)} recommended MCP servers...[/yellow]")
        
        for rec in to_install:
            try:
                # Install the server
                install_cmd = rec.install_command.split()
                result = await asyncio.create_subprocess_exec(
                    *install_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    self.console.print(f"[green]✓ Installed {rec.server_name}[/green]")
                    # Update available servers
                    self.available_mcp_servers.add(rec.server_name)
                else:
                    self.console.print(f"[red]✗ Failed to install {rec.server_name}[/red]")
                    if stderr:
                        self.logger.debug(f"Installation error: {stderr.decode()}")
            except Exception as e:
                self.console.print(f"[red]✗ Error installing {rec.server_name}: {e}[/red]")
    
    def _create_mcp_usage_guide(self):
        """Create MCP usage guide in the project"""
        guide_content = f"""# MCP Server Usage Guide

This project has the following MCP servers configured:

## Available Servers

"""
        
        for server_name in sorted(self.available_mcp_servers):
            if server_name in MCP_SERVER_REGISTRY:
                info = MCP_SERVER_REGISTRY[server_name]
                guide_content += f"### {server_name}\n"
                guide_content += f"{info['description']}\n\n"
                guide_content += f"**Tools:**\n"
                for tool in info.get('tools', []):
                    guide_content += f"- `mcp__{server_name}__{tool}`\n"
                guide_content += "\n"
        
        guide_content += """## Usage Examples

### Memory Server
```python
# Store context
await mcp__memory__store(key="project_config", value=config_data)

# Recall context
config = await mcp__memory__recall(key="project_config")

# Search memory
results = await mcp__memory__search(query="database schema")
```

### Sequential Thinking Server
```python
# Plan a complex task
plan = await mcp__sequential-thinking__plan(task="implement authentication")

# Decompose problem
components = await mcp__sequential-thinking__decompose(problem="scale to 1M users")
```

### Git Server
```python
# Commit changes
await mcp__git__commit(message="feat: add user authentication")

# Check status
status = await mcp__git__status()
```

## Best Practices

1. Always use MCP servers when available for enhanced functionality
2. Store important context in memory server for cross-phase access
3. Use sequential thinking for complex problem solving
4. Commit changes regularly with descriptive messages
5. Handle MCP failures gracefully with fallback strategies
"""
        
        guide_path = self.args.output_dir / "MCP_USAGE_GUIDE.md"
        with open(guide_path, 'w') as f:
            f.write(guide_content)
        
        self.logger.debug("Created MCP usage guide")
    
    async def _conduct_research_phase(self, spec_content: str) -> Dict[str, Any]:
        """Enhanced research phase with better progress tracking"""
        self.console.print("[bold blue]🔬 Starting comprehensive research phase...[/bold blue]")
        
        # Extract project context
        project_context = await self._extract_project_context(spec_content)
        
        # Log research plan
        self.logger.info("="*80)
        self.logger.info("RESEARCH PHASE STARTING")
        self.logger.info("="*80)
        self.logger.info(f"Project Type: {project_context.get('project_type', 'Unknown')}")
        self.logger.info(f"Technology Stack: {', '.join(project_context.get('technology_stack', []))}")
        self.logger.info(f"Requirements: {', '.join(project_context.get('requirements', []))}")
        self.logger.info(f"Complexity: {project_context.get('complexity', 'Unknown')}")
        
        # Display research plan
        self._display_research_plan(project_context)
        
        # Track research cost
        research_start_tokens = self.cost_tracker.total_input_tokens
        
        # Conduct research with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        ) as progress:
            
            research_task = progress.add_task("Conducting research...", total=100)
            
            # Update progress callback
            async def update_progress(completed: int, total: int):
                progress.update(research_task, completed=int((completed/total) * 100))
            
            # Set callback (if research manager supports it)
            # For now, just run the research
            research_results = await self.research_manager.conduct_comprehensive_research(
                spec_content, project_context
            )
            
            progress.update(research_task, completed=100)
        
        # Calculate research cost
        research_tokens_used = self.cost_tracker.total_input_tokens - research_start_tokens
        if research_tokens_used > 0:
            self.logger.info(f"Research phase used {research_tokens_used} tokens")
        
        # Display research summary
        self._display_research_summary(research_results)
        
        # Save research results
        await self._save_research_results(research_results)
        
        return research_results
    
    async def _extract_project_context(self, spec_content: str) -> Dict[str, Any]:
        """Enhanced project context extraction"""
        context = {
            "project_name": self.args.output_dir.name,
            "specification": spec_content
        }
        
        # Use MCP recommender's analysis functions
        tech_stack = await self.mcp_recommender._extract_technology_stack(spec_content)
        requirements = await self.mcp_recommender._extract_requirements(spec_content)
        project_type = await self.mcp_recommender._determine_project_type(spec_content)
        complexity = await self.mcp_recommender._assess_complexity(spec_content)
        
        context.update({
            "technology_stack": tech_stack,
            "requirements": requirements,
            "project_type": project_type,
            "complexity": complexity,
            "output_dir": str(self.args.output_dir.absolute()),
            "enable_web_search": False  # Claude Code SDK doesn't support web search tools
        })
        
        # Store for later use
        self._tech_stack = tech_stack
        self._requirements = requirements
        self._project_type = project_type
        self._complexity = complexity
        
        return context
    
    def _display_research_plan(self, project_context: Dict[str, Any]):
        """Display enhanced research plan"""
        research_panel = Panel(
            f"""[bold]Research Plan[/bold]

[cyan]Project Type:[/cyan] {project_context.get('project_type', 'Unknown')}
[cyan]Technologies:[/cyan] {', '.join(project_context.get('technology_stack', [])) or 'To be determined'}
[cyan]Requirements:[/cyan] {', '.join(project_context.get('requirements', [])) or 'To be analyzed'}
[cyan]Complexity:[/cyan] {project_context.get('complexity', 'Unknown')}

[green]Research Areas:[/green]
• Technology stack best practices and patterns
• Security recommendations and vulnerabilities
• Architecture patterns and scalability
• Performance optimization strategies
• Testing and quality assurance
• Deployment and DevOps practices
• Implementation guidelines and pitfalls

[yellow]Estimated Time:[/yellow] 2-5 minutes
[blue]Research Agents:[/blue] 7 specialized AI agents

[dim]Note: Research uses Claude's knowledge base (up to early 2025)[/dim]""",
            title="[bold]🔬 Research Phase[/bold]",
            border_style="blue"
        )
        
        self.console.print(research_panel)
    
    def _display_research_summary(self, research_results: Dict[str, Any]):
        """Display enhanced research summary"""
        self.console.print("\n[bold green]✅ Research Phase Complete[/bold green]\n")
        
        # Count findings
        total_recommendations = 0
        total_best_practices = 0
        total_patterns = 0
        key_decisions = 0
        
        for category, findings in research_results.items():
            if isinstance(findings, dict):
                if "recommendations" in findings:
                    total_recommendations += len(findings["recommendations"])
                if "best_practices" in findings:
                    total_best_practices += len(findings["best_practices"])
                if "patterns" in findings:
                    total_patterns += len(findings["patterns"])
            elif category == "key_decisions":
                key_decisions = len(findings) if isinstance(findings, list) else 0
        
        # Create summary table
        summary_table = Table(
            title="[bold]Research Findings Summary[/bold]",
            box=box.ROUNDED,
            show_lines=True
        )
        summary_table.add_column("Category", style="cyan")
        summary_table.add_column("Count", justify="right", style="green")
        
        summary_table.add_row("Recommendations", str(total_recommendations))
        summary_table.add_row("Best Practices", str(total_best_practices))
        summary_table.add_row("Implementation Patterns", str(total_patterns))
        summary_table.add_row("Key Decisions", str(key_decisions))
        summary_table.add_row("Research Queries", str(len(research_results)))
        
        self.console.print(summary_table)
        
        # Show key insights
        if "executive_summary" in research_results:
            self.console.print(Panel(
                research_results["executive_summary"],
                title="[bold]Executive Summary[/bold]",
                border_style="green"
            ))
        
        self.console.print("""
[dim]The research findings will be automatically incorporated into:
- Custom instructions for each phase
- Technology-specific implementations
- Security measures throughout the project
- Testing and deployment strategies[/dim]""")
    
    async def _save_research_results(self, research_results: Dict[str, Any]):
        """Save research results for reference"""
        research_dir = self.args.output_dir / ".research"
        research_dir.mkdir(exist_ok=True)
        
        # Save full results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = research_dir / f"research_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(research_results, f, indent=2, default=str)
        
        # Create human-readable summary
        summary_file = research_dir / f"research_summary_{timestamp}.md"
        summary_content = self._create_research_summary_markdown(research_results)
        
        with open(summary_file, 'w') as f:
            f.write(summary_content)
        
        self.logger.debug(f"Saved research results to {results_file}")
    
    def _create_research_summary_markdown(self, research_results: Dict[str, Any]) -> str:
        """Create markdown summary of research results"""
        md_parts = [f"# Research Summary\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"]
        
        # Executive summary
        if "executive_summary" in research_results:
            md_parts.append(f"## Executive Summary\n\n{research_results['executive_summary']}\n")
        
        # Key recommendations
        if "prioritized_recommendations" in research_results:
            md_parts.append("## Top Recommendations\n")
            for i, rec in enumerate(research_results["prioritized_recommendations"][:10], 1):
                if isinstance(rec, dict):
                    md_parts.append(f"{i}. **{rec.get('recommendation', 'Unknown')}**")
                    if 'rationale' in rec:
                        md_parts.append(f"   - Rationale: {rec['rationale']}")
                    if 'effort' in rec:
                        md_parts.append(f"   - Effort: {rec['effort']}")
                    md_parts.append("")
        
        # Technology decisions
        if "technology_stack" in research_results:
            md_parts.append("## Technology Stack\n")
            for category, tech in research_results["technology_stack"].items():
                if isinstance(tech, dict):
                    md_parts.append(f"- **{category}**: {tech.get('selected', 'TBD')} v{tech.get('version', 'latest')}")
                    if 'rationale' in tech:
                        md_parts.append(f"  - {tech['rationale']}")
            md_parts.append("")
        
        # Implementation roadmap
        if "implementation_roadmap" in research_results:
            md_parts.append("## Implementation Roadmap\n")
            for phase in research_results["implementation_roadmap"]:
                if isinstance(phase, dict):
                    md_parts.append(f"### {phase.get('phase', 'Unknown Phase')}")
                    md_parts.append(f"Duration: {phase.get('duration_estimate', 'TBD')}\n")
                    if 'tasks' in phase:
                        for task in phase['tasks']:
                            md_parts.append(f"- {task}")
                    md_parts.append("")
        
        return "\n".join(md_parts)
    
    async def _enhanced_project_analysis(self, spec_content: str, 
                                       research_results: Optional[Dict[str, Any]]) -> List[Phase]:
        """Enhanced project analysis with research integration"""
        self.console.print("[bold blue]🧠 Enhanced project analysis with research integration...[/bold blue]")
        
        # Create enhanced analysis prompt
        analysis_prompt = self._create_analysis_prompt(spec_content)
        
        # Add research findings to prompt if available
        if research_results:
            analysis_prompt += self._format_research_for_analysis(research_results)
        
        # Execute analysis
        phases = await self._execute_analysis(analysis_prompt)
        
        # Enhance phases with research insights
        if research_results:
            phases = self._integrate_research_into_phases(phases, research_results)
        
        # Validate and optimize phases
        phases = self._optimize_phases(phases)
        
        return phases
    
    async def _analyze_project(self, spec_content: str) -> List[Phase]:
        """Standard project analysis without research"""
        self.logger.info("Analyzing project specification...")
        
        # Create analysis prompt
        analysis_prompt = self._create_analysis_prompt(spec_content)
        
        # Execute analysis
        with Status("Analyzing project structure...", spinner="dots2", console=self.console):
            phases = await self._execute_analysis(analysis_prompt)
        
        # Optimize phases
        phases = self._optimize_phases(phases)
        
        # Log generated phases
        self.logger.info("="*80)
        self.logger.info("PHASES GENERATED FROM SPECIFICATION")
        self.logger.info("="*80)
        self.logger.info(f"Total Phases: {len(phases)}")
        for phase in phases:
            self.logger.info(f"\n{phase.name} ({phase.id}):")
            self.logger.info(f"  Description: {phase.description}")
            self.logger.info(f"  Tasks: {len(phase.tasks)}")
            for i, task in enumerate(phase.tasks[:3], 1):
                self.logger.info(f"    {i}. {task}")
            if len(phase.tasks) > 3:
                self.logger.info(f"    ... and {len(phase.tasks) - 3} more tasks")
            self.logger.info(f"  Dependencies: {', '.join(phase.dependencies) if phase.dependencies else 'None'}")
        
        return phases
    
    def _create_analysis_prompt(self, spec_content: str) -> str:
        """Create comprehensive analysis prompt"""
        return f"""You are an expert software architect analyzing a project specification.

PROJECT SPECIFICATION:
{spec_content}

Create a comprehensive build plan with multiple phases following these requirements:

PHASE DESIGN PRINCIPLES:
1. Each phase should have a single, clear responsibility
2. Phases should build incrementally with proper dependencies
3. Early phases establish foundation, later phases add features
4. Include dedicated phases for testing, documentation, and deployment
5. Ensure proper separation of concerns
6. Consider the complexity level: {getattr(self, '_complexity', 'medium')}

REQUIRED PHASES (minimum, add more as needed):
1. Project Foundation - Core structure, configuration, error handling, logging
2. Data Layer - Models, database schema, data access, migrations
3. Business Logic - Core algorithms, domain logic, services
4. API/Interface Layer - External interfaces, APIs, controllers
5. Integration Layer - Third-party services, external APIs
6. User Interface - CLI, GUI, or web interface (if applicable)
7. Security Implementation - Authentication, authorization, data protection
8. Testing Suite - Unit, integration, E2E tests
9. Documentation - API docs, user guide, deployment guide
10. Performance Optimization - Caching, query optimization, monitoring
11. Deployment Setup - Containerization, CI/CD, infrastructure
12. Production Readiness - Final validation, hardening, monitoring

OUTPUT FORMAT:
```json
{{
  "phases": [
    {{
      "id": "phase_1",
      "name": "Project Foundation",
      "description": "Establish core architecture and infrastructure",
      "tasks": [
        "Create comprehensive directory structure",
        "Initialize package configuration with dependencies",
        "Set up structured logging system with rotation",
        "Create custom exception hierarchy",
        "Implement configuration management (env vars, config files)",
        "Set up development environment with hot reload",
        "Create base classes and interfaces",
        "Implement dependency injection framework",
        "Set up code quality tools (linting, formatting)",
        "Create development scripts and Makefile"
      ],
      "dependencies": []
    }},
    ... more phases ...
  ]
}}
```

IMPORTANT:
- Create at least {self.args.min_phases} phases
- Each phase must have {self.args.min_tasks_per_phase}-20 specific, actionable tasks
- Tasks should be detailed and implementation-ready
- Include specific technical details relevant to the project
- Consider production requirements and best practices
- Ensure proper error handling and recovery in all phases
- Include performance and security considerations
- Plan for scalability and maintainability"""
    
    def _format_research_for_analysis(self, research_results: Dict[str, Any]) -> str:
        """Format research results for inclusion in analysis"""
        research_section = "\n\nRESEARCH FINDINGS TO INCORPORATE:\n"
        
        # Add prioritized recommendations
        if "prioritized_recommendations" in research_results:
            research_section += "\nTOP RECOMMENDATIONS:\n"
            for i, rec in enumerate(research_results["prioritized_recommendations"][:5], 1):
                if isinstance(rec, dict):
                    research_section += f"{i}. {rec.get('recommendation', '')}\n"
        
        # Add technology decisions
        if "technology_stack" in research_results:
            research_section += "\nTECHNOLOGY DECISIONS:\n"
            for category, tech in research_results["technology_stack"].items():
                if isinstance(tech, dict):
                    research_section += f"- {category}: {tech.get('selected', '')} {tech.get('version', '')}\n"
        
        # Add security requirements
        if "security_requirements" in research_results:
            research_section += "\nSECURITY REQUIREMENTS:\n"
            for req in research_results["security_requirements"][:5]:
                if isinstance(req, dict):
                    research_section += f"- {req.get('requirement', '')}\n"
        
        # Add architectural decisions
        if "architectural_decisions" in research_results:
            research_section += "\nARCHITECTURAL DECISIONS:\n"
            for decision in research_results["architectural_decisions"][:3]:
                if isinstance(decision, dict):
                    research_section += f"- {decision.get('decision', '')}\n"
        
        research_section += "\nEnsure these findings are incorporated into appropriate phases."
        
        return research_section
    
    async def _execute_analysis(self, prompt: str) -> List[Phase]:
        """Execute project analysis using AI"""
        if self.anthropic:
            try:
                # Use Anthropic SDK for analysis
                message = await self.anthropic.messages.create(
                    model=self.args.model_analyzer,
                    max_tokens=8192,
                    temperature=0.3,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                
                # Extract content
                content = ""
                if message.content:
                    for block in message.content:
                        if hasattr(block, 'text'):
                            content += block.text
                
                # Track usage
                if message.usage:
                    self.cost_tracker.add_usage(message.usage, self.args.model_analyzer, "analysis")
                
                # Parse phases
                return self._parse_phases_from_output(content)
                
            except Exception as e:
                self.logger.error(f"Analysis failed: {e}")
                # Fallback to enhanced default phases
                return self._create_enhanced_default_phases()
        else:
            # No API key, use enhanced default phases
            self.logger.warning("Using enhanced default phases (no API key provided)")
            return self._create_enhanced_default_phases()
    
    def _parse_phases_from_output(self, output: str) -> List[Phase]:
        """Parse phases from analysis output with validation"""
        try:
            # Extract JSON from output
            json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', output)
            if not json_match:
                json_match = re.search(r'(\{[\s\S]*"phases"[\s\S]*\})', output)
            
            if not json_match:
                raise ValueError("No valid JSON found in output")
            
            data = json.loads(json_match.group(1))
            
            if "phases" not in data:
                raise ValueError("JSON does not contain 'phases' key")
            
            phases = []
            phase_ids = set()
            
            for phase_data in data["phases"]:
                # Validate required fields
                if not all(key in phase_data for key in ["id", "name", "description", "tasks"]):
                    self.logger.warning(f"Skipping invalid phase: {phase_data}")
                    continue
                
                # Ensure unique IDs
                phase_id = phase_data["id"]
                if phase_id in phase_ids:
                    phase_id = f"{phase_id}_{len(phases)}"
                phase_ids.add(phase_id)
                
                phase = Phase(
                    id=phase_id,
                    name=phase_data["name"],
                    description=phase_data["description"],
                    tasks=phase_data["tasks"],
                    dependencies=phase_data.get("dependencies", [])
                )
                phases.append(phase)
            
            # Validate dependencies
            for phase in phases:
                phase.dependencies = [d for d in phase.dependencies if d in phase_ids]
            
            # Ensure minimum phases
            if len(phases) < self.args.min_phases:
                self.logger.warning(f"Only {len(phases)} phases found, adding default phases")
                phases.extend(self._create_enhanced_default_phases()[len(phases):])
            
            return phases
            
        except Exception as e:
            self.logger.error(f"Failed to parse phases: {e}")
            return self._create_enhanced_default_phases()
    
    def _create_enhanced_default_phases(self) -> List[Phase]:
        """Create enhanced default phases with better coverage"""
        return [
            Phase(
                id="phase_1",
                name="Project Foundation",
                description="Establish core architecture and infrastructure",
                tasks=[
                    "Create comprehensive directory structure for the project",
                    "Initialize package configuration files (package.json, pyproject.toml, etc.)",
                    "Set up structured logging system with rotation and levels",
                    "Create custom exception hierarchy for error handling",
                    "Implement configuration management for environment variables",
                    "Set up development environment with hot reload capabilities",
                    "Create base classes and interfaces for core abstractions",
                    "Implement dependency injection framework if applicable",
                    "Set up code quality tools (linting, formatting, type checking)",
                    "Create Makefile or task runner configuration",
                    "Initialize documentation structure",
                    "Set up development database if needed"
                ],
                dependencies=[]
            ),
            Phase(
                id="phase_2",
                name="Data Layer",
                description="Implement data models and storage layer",
                tasks=[
                    "Design comprehensive database schema with relationships",
                    "Create data model classes with validation",
                    "Implement database connection management with pooling",
                    "Create repository pattern for data access",
                    "Add data validation and sanitization layers",
                    "Implement database migrations system",
                    "Create seed data scripts for development",
                    "Add caching layer for frequently accessed data",
                    "Implement transaction management",
                    "Create data access interfaces",
                    "Add database query optimization",
                    "Implement backup and recovery procedures"
                ],
                dependencies=["phase_1"]
            ),
            Phase(
                id="phase_3",
                name="Business Logic",
                description="Implement core business logic and services",
                tasks=[
                    "Create service classes for business operations",
                    "Implement core business rules and validations",
                    "Add algorithm implementations for key features",
                    "Create workflow orchestration logic",
                    "Implement state management patterns",
                    "Add transaction handling for business operations",
                    "Create event system for decoupled communication",
                    "Implement background task processing",
                    "Add business metrics collection",
                    "Create domain-specific language if needed",
                    "Implement feature flags system",
                    "Add business rule engine if applicable"
                ],
                dependencies=["phase_1", "phase_2"]
            ),
            Phase(
                id="phase_4",
                name="API Layer",
                description="Build API endpoints and external interfaces",
                tasks=[
                    "Design RESTful API endpoints with proper HTTP methods",
                    "Implement request routing and middleware",
                    "Add authentication and authorization mechanisms",
                    "Create comprehensive request validation",
                    "Implement response formatting and serialization",
                    "Add rate limiting and throttling",
                    "Create OpenAPI/Swagger documentation",
                    "Implement API versioning strategy",
                    "Add CORS configuration for web clients",
                    "Create API client SDKs if needed",
                    "Implement webhook support if applicable",
                    "Add GraphQL layer if required"
                ],
                dependencies=["phase_3"]
            ),
            Phase(
                id="phase_5",
                name="Security Implementation",
                description="Implement comprehensive security measures",
                tasks=[
                    "Implement secure authentication system (JWT, OAuth, etc.)",
                    "Add role-based access control (RBAC)",
                    "Implement data encryption at rest and in transit",
                    "Add input validation and sanitization everywhere",
                    "Implement CSRF protection for web applications",
                    "Add security headers and CSP policies",
                    "Implement audit logging for sensitive operations",
                    "Add rate limiting per user/IP",
                    "Implement secure session management",
                    "Add vulnerability scanning integration",
                    "Create security incident response procedures",
                    "Implement principle of least privilege"
                ],
                dependencies=["phase_4"]
            ),
            Phase(
                id="phase_6",
                name="User Interface",
                description="Build user interface components",
                tasks=[
                    "Create UI components based on specification",
                    "Implement responsive design patterns",
                    "Build interactive features and state management",
                    "Implement real-time updates if required",
                    "Create accessibility features (WCAG compliance)",
                    "Implement internationalization if needed",
                    "Build form validation and user feedback",
                    "Create data visualization components",
                    "Implement progressive enhancement",
                    "Add offline capabilities if applicable",
                    "Create UI performance optimizations",
                    "Build interactive documentation"
                ],
                dependencies=["phase_5"]
            ),
            Phase(
                id="phase_7",
                name="Documentation",
                description="Create comprehensive documentation",
                tasks=[
                    "Write detailed API documentation with examples",
                    "Create user guide with screenshots/diagrams",
                    "Document system architecture and design decisions",
                    "Add inline code documentation and docstrings",
                    "Create deployment and operations guide",
                    "Write troubleshooting guide with common issues",
                    "Add configuration reference documentation",
                    "Create developer onboarding guide",
                    "Document API client usage examples",
                    "Add performance tuning guide",
                    "Create disaster recovery documentation",
                    "Generate automated API documentation"
                ],
                dependencies=["phase_6"]
            ),
            Phase(
                id="phase_8",
                name="Performance Optimization",
                description="Optimize performance and scalability",
                tasks=[
                    "Profile application to identify bottlenecks",
                    "Implement caching strategies at multiple levels",
                    "Optimize database queries and add indexes",
                    "Implement connection pooling and reuse",
                    "Add lazy loading and pagination",
                    "Optimize asset delivery and bundling",
                    "Implement CDN integration if applicable",
                    "Add response compression",
                    "Optimize memory usage and garbage collection",
                    "Implement horizontal scaling capabilities",
                    "Add performance monitoring and alerting",
                    "Create performance benchmarks"
                ],
                dependencies=["phase_7"]
            ),
            Phase(
                id="phase_9",
                name="Deployment Setup",
                description="Deployment and DevOps configuration",
                tasks=[
                    "Create Docker configuration with multi-stage builds",
                    "Set up CI/CD pipeline with automated testing",
                    "Configure production environment variables",
                    "Create infrastructure as code (Terraform/Pulumi)",
                    "Set up monitoring and observability stack",
                    "Configure log aggregation and analysis",
                    "Implement health checks and readiness probes",
                    "Create automated backup procedures",
                    "Set up auto-scaling policies",
                    "Configure SSL/TLS certificates",
                    "Create deployment rollback procedures",
                    "Set up staging environment"
                ],
                dependencies=["phase_8"]
            ),
            Phase(
                id="phase_10",
                name="Production Readiness",
                description="Final production preparation and validation",
                tasks=[
                    "Conduct security audit and penetration testing",
                    "Perform load testing and capacity planning",
                    "Create operational runbooks",
                    "Set up 24/7 monitoring and alerting",
                    "Implement feature flags for gradual rollouts",
                    "Create incident response procedures",
                    "Set up error tracking and reporting",
                    "Configure automated backups and disaster recovery",
                    "Create SLA monitoring and reporting",
                    "Implement compliance checks if required",
                    "Set up A/B testing framework",
                    "Create production checklist and sign-off"
                ],
                dependencies=["phase_9"]
            )
        ]
    
    def _integrate_research_into_phases(self, phases: List[Phase], 
                                      research_results: Dict[str, Any]) -> List[Phase]:
        """Integrate research findings into phases with intelligent mapping"""
        # Map research categories to phase types
        research_mappings = {
            "security_analysis": ["security", "auth", "foundation"],
            "performance_optimization": ["optimization", "performance", "scaling"],
            "architecture_patterns": ["foundation", "architecture", "structure"],
            "technology_analysis": ["foundation", "setup", "configuration"],
            "testing_strategy": ["test", "testing", "quality"],
            "deployment_strategy": ["deploy", "devops", "infrastructure"]
        }
        
        # Apply research findings to relevant phases
        for research_category, findings in research_results.items():
            if not isinstance(findings, dict):
                continue
                
            # Find relevant phases for this research category
            relevant_keywords = research_mappings.get(research_category, [])
            
            for phase in phases:
                phase_name_lower = phase.name.lower()
                
                # Check if phase matches any relevant keywords
                if any(keyword in phase_name_lower for keyword in relevant_keywords):
                    # Add recommendations as tasks
                    if "recommendations" in findings:
                        for rec in findings["recommendations"][:3]:
                            task = f"[Research] {rec}"
                            if task not in phase.tasks:
                                phase.tasks.append(task)
                    
                    # Add best practices
                    if "best_practices" in findings:
                        for practice in findings["best_practices"][:2]:
                            task = f"[Best Practice] {practice}"
                            if task not in phase.tasks:
                                phase.tasks.append(task)
                    
                    # Add implementation patterns to context
                    if "implementation_patterns" in findings:
                        phase.add_context("research_patterns", findings["implementation_patterns"])
        
        # Add research-driven phases if missing
        self._add_research_driven_phases(phases, research_results)
        
        return phases
    
    def _add_research_driven_phases(self, phases: List[Phase], research_results: Dict[str, Any]):
        """Add additional phases based on research findings"""
        existing_phase_names = {p.name.lower() for p in phases}
        
        # Check if we need a dedicated security phase
        if "security" not in existing_phase_names and "security_analysis" in research_results:
            security_findings = research_results.get("security_analysis", {})
            if isinstance(security_findings, dict) and security_findings.get("recommendations"):
                security_phase = Phase(
                    id=f"phase_{len(phases)+1}",
                    name="Security Hardening",
                    description="Implement comprehensive security measures based on research",
                    tasks=[f"[Research] {rec}" for rec in security_findings["recommendations"][:10]],
                    dependencies=[p.id for p in phases if "api" in p.name.lower() or "core" in p.name.lower()]
                )
                phases.append(security_phase)
        
        # Check if we need a performance optimization phase
        if "optimization" not in existing_phase_names and "performance_optimization" in research_results:
            perf_findings = research_results.get("performance_optimization", {})
            if isinstance(perf_findings, dict) and perf_findings.get("recommendations"):
                perf_phase = Phase(
                    id=f"phase_{len(phases)+1}",
                    name="Performance Optimization",
                    description="Optimize performance based on research findings",
                    tasks=[f"[Research] {rec}" for rec in perf_findings["recommendations"][:10]],
                    dependencies=[p.id for p in phases if "test" in p.name.lower()]
                )
                phases.append(perf_phase)
    
    def _optimize_phases(self, phases: List[Phase]) -> List[Phase]:
        """Optimize phase ordering and dependencies"""
        # Ensure phases are properly ordered by dependencies
        optimized = []
        phase_dict = {p.id: p for p in phases}
        processed = set()
        
        def can_process(phase: Phase) -> bool:
            """Check if all dependencies are processed"""
            return all(dep in processed for dep in phase.dependencies)
        
        # Process phases in dependency order
        while len(optimized) < len(phases):
            made_progress = False
            
            for phase in phases:
                if phase.id not in processed and can_process(phase):
                    optimized.append(phase)
                    processed.add(phase.id)
                    made_progress = True
            
            if not made_progress:
                # Add remaining phases (might have circular dependencies)
                for phase in phases:
                    if phase.id not in processed:
                        # Clear invalid dependencies
                        phase.dependencies = [d for d in phase.dependencies if d in processed]
                        optimized.append(phase)
                        processed.add(phase.id)
                break
        
        return optimized
    
    async def _initialize_memory(self, spec_content: str, phases: List[Phase],
                               research_results: Optional[Dict[str, Any]]):
        """Initialize project memory with enhanced context"""
        spec_hash = hashlib.sha256(spec_content.encode()).hexdigest()
        
        self.memory = ProjectMemory(
            project_name=self.args.output_dir.name,
            project_path=str(self.args.output_dir.absolute()),
            specification=spec_content,
            specification_hash=spec_hash,
            phases=phases,
            mcp_servers=self.mcp_server_configs
        )
        
        # Add research results to context
        if research_results:
            self.memory.context["research_results"] = research_results
            self.memory.context["research_timestamp"] = datetime.now().isoformat()
            
            # Extract key decisions
            if "key_decisions" in research_results:
                for decision in research_results["key_decisions"]:
                    if isinstance(decision, dict):
                        self.memory.important_decisions.append(
                            f"{decision.get('category', 'general')}: {decision.get('decision', '')}"
                        )
        
        # Add project metadata
        self.memory.context.update({
            "technology_stack": getattr(self, '_tech_stack', []),
            "requirements": getattr(self, '_requirements', []),
            "project_type": getattr(self, '_project_type', 'general'),
            "complexity": getattr(self, '_complexity', 'medium'),
            "builder_version": "2.3.0",
            "features": {
                "mcp_enabled": bool(self.available_mcp_servers),
                "research_enabled": bool(research_results),
                "custom_instructions": True,
                "git_enabled": self.args.git_init,
                "auto_resume": True
            }
        })
        
        # Store initial memory
        await self._store_memory("project_initialized")
    
    async def _setup_custom_instructions(self, research_results: Optional[Dict[str, Any]]):
        """Setup enhanced custom instructions from specification and research"""
        self.logger.info("="*80)
        self.logger.info("GENERATING CUSTOM INSTRUCTIONS")
        self.logger.info("="*80)
        
        project_context = {
            "project_name": self.memory.project_name if self.memory else self.args.output_dir.name,
            "project_type": getattr(self, '_project_type', 'general'),
            "technology_stack": getattr(self, '_tech_stack', []),
            "requirements": getattr(self, '_requirements', []),
            "complexity": getattr(self, '_complexity', 'medium')
        }
        
        # Generate instructions from specification
        if hasattr(self, 'specification_content') and self.specification_content:
            spec_instructions = self._generate_instructions_from_spec(self.specification_content, research_results)
            for instruction in spec_instructions:
                self.custom_instructions.add_instruction(instruction)
                self.logger.info(f"Added instruction: {instruction.name} (priority: {instruction.priority})")
        
        # Add project-specific instructions
        self.custom_instructions.add_project_specific_instructions(
            project_context, research_results
        )
        
        # Add complexity-specific instructions
        if project_context["complexity"] == "high":
            self._add_high_complexity_instructions()
        
        self.logger.info(f"Loaded {len(self.custom_instructions.instructions)} custom instructions")
    
    def _generate_instructions_from_spec(self, spec_content: str, research_results: Optional[Dict[str, Any]] = None) -> List[CustomInstruction]:
        """Generate project-specific custom instructions from specification"""
        instructions = []
        spec_lower = spec_content.lower()
        
        # Technology-specific instructions
        if "react" in spec_lower or "vue" in spec_lower or "angular" in spec_lower:
            instructions.append(CustomInstruction(
                id="frontend_framework_guidelines",
                name="Frontend Framework Guidelines",
                content="""When building frontend components:
- Use functional components with hooks (React) or composition API (Vue)
- Implement proper state management (Redux/Vuex/Context)
- Ensure all components are fully typed with TypeScript
- Implement error boundaries for graceful error handling
- Use lazy loading for route-based code splitting
- Implement proper loading states and error states
- Never use any/unknown types - be explicit""",
                scope="project",
                context_filters={},
                priority=100
            ))
        
        if "api" in spec_lower or "rest" in spec_lower or "graphql" in spec_lower:
            instructions.append(CustomInstruction(
                id="api_development_standards",
                name="API Development Standards",
                content="""For all API endpoints:
- Implement proper authentication and authorization
- Use consistent error response format
- Implement request validation and sanitization
- Add rate limiting to prevent abuse
- Use proper HTTP status codes
- Implement CORS properly for web clients
- Add comprehensive API documentation
- Version APIs from the start""",
                scope="project",
                context_filters={},
                priority=95
            ))
        
        if "database" in spec_lower or "postgres" in spec_lower or "mysql" in spec_lower:
            instructions.append(CustomInstruction(
                id="database_best_practices",
                name="Database Best Practices",
                content="""Database implementation requirements:
- Use migrations for all schema changes
- Implement proper indexing strategies
- Use transactions for data consistency
- Implement connection pooling
- Add audit columns (created_at, updated_at)
- Use prepared statements to prevent SQL injection
- Implement soft deletes where appropriate
- Regular backup strategies""",
                scope="project",
                context_filters={},
                priority=90
            ))
        
        # Universal no-testing instruction
        instructions.append(CustomInstruction(
            id="no_mocking_or_testing",
            name="No Mocking or Testing",
            content="""CRITICAL: This project works with real data only:
- Never create unit tests or test files
- Never use mocking libraries or mock data
- Always work with real services and APIs
- Test manually with actual data
- Focus on error handling for real scenarios""",
            scope="global",
            context_filters={},
            priority=1000
        ))
        
        # Production quality instruction
        instructions.append(CustomInstruction(
            id="production_quality",
            name="Production Quality",
            content="""Every implementation must be production-ready:
- No TODO comments or placeholders
- Complete error handling with recovery
- Comprehensive logging at appropriate levels
- Performance considerations from the start
- Security built-in, not added later
- Documentation inline with code""",
            scope="global",
            context_filters={},
            priority=999
        ))
        
        # From research results
        if research_results and "security_recommendations" in research_results:
            instructions.append(CustomInstruction(
                id="security_requirements_from_research",
                name="Security Requirements from Research",
                content=f"""Security measures identified during research:
{chr(10).join('- ' + rec for rec in research_results['security_recommendations'][:10])}
- Always validate and sanitize inputs
- Use parameterized queries
- Implement proper session management""",
                scope="project",
                context_filters={},
                priority=100
            ))
        
        return instructions
    
    def _add_high_complexity_instructions(self):
        """Add instructions for high-complexity projects"""
        self.custom_instructions.add_instruction(CustomInstruction(
            id="high_complexity_patterns",
            name="High Complexity Design Patterns",
            content="""For this high-complexity project, implement these patterns:

ARCHITECTURE:
- Use Domain-Driven Design (DDD) principles
- Implement CQRS pattern for read/write separation
- Use event sourcing for audit trails
- Apply hexagonal architecture (ports and adapters)

SCALABILITY:
- Design for horizontal scaling from the start
- Implement database sharding strategy
- Use message queues for async processing
- Add circuit breakers for external services

RELIABILITY:
- Implement saga pattern for distributed transactions
- Add comprehensive health checks
- Use feature flags for gradual rollouts
- Implement chaos engineering practices

OBSERVABILITY:
- Add distributed tracing (OpenTelemetry)
- Implement structured logging
- Create custom metrics and dashboards
- Add synthetic monitoring""",
            scope="project",
            context_filters={"complexity": "high"},
            priority=90
        ))
    
    async def _confirm_execution_plan(self, phases: List[Phase]) -> bool:
        """Show enhanced execution plan and get confirmation"""
        self.console.print("\n[bold]EXECUTION PLAN[/bold]\n")
        
        # Phase overview table
        overview_table = Table(
            title="[bold]Phase Overview[/bold]",
            box=box.ROUNDED,
            show_lines=True,
            header_style="bold cyan"
        )
        overview_table.add_column("#", style="dim", width=3)
        overview_table.add_column("Phase", style="cyan", width=30)
        overview_table.add_column("Tasks", style="green", justify="center", width=6)
        overview_table.add_column("Dependencies", style="yellow", width=20)
        overview_table.add_column("Type", style="blue", width=15)
        
        total_tasks = 0
        for i, phase in enumerate(phases, 1):
            deps = ", ".join(phase.dependencies) if phase.dependencies else "None"
            
            # Determine phase type
            phase_type = "Core"
            # Testing phases removed - no unit tests or mocking
            if "doc" in phase.name.lower():
                phase_type = "Documentation"
            elif "deploy" in phase.name.lower():
                phase_type = "Deployment"
            elif "security" in phase.name.lower():
                phase_type = "Security"
            elif "optim" in phase.name.lower():
                phase_type = "Optimization"
            
            overview_table.add_row(
                str(i),
                phase.name[:30],
                str(len(phase.tasks)),
                deps[:20] + "..." if len(deps) > 20 else deps,
                phase_type
            )
            total_tasks += len(phase.tasks)
        
        self.console.print(overview_table)
        
        # Enhanced statistics
        stats_content = []
        
        # Time estimation with complexity factor
        complexity_multiplier = {"low": 0.8, "medium": 1.0, "high": 1.5}.get(
            getattr(self, '_complexity', 'medium'), 1.0
        )
        avg_seconds_per_task = 25 * complexity_multiplier
        estimated_time = (total_tasks * avg_seconds_per_task) / 60
        
        stats_content.append(f"[bold]Total Phases:[/bold] {len(phases)}")
        stats_content.append(f"[bold]Total Tasks:[/bold] {total_tasks}")
        stats_content.append(f"[bold]Complexity:[/bold] {getattr(self, '_complexity', 'medium').title()}")
        stats_content.append(f"[bold]Estimated Time:[/bold] {estimated_time:.0f}-{estimated_time*1.5:.0f} minutes")
        
        # Cost estimation
        estimated_cost = self._estimate_cost(phases)
        stats_content.append(f"[bold]Estimated Cost:[/bold] ${estimated_cost:.2f}-${estimated_cost*1.3:.2f}")
        
        # Technology stack
        if hasattr(self, '_tech_stack') and self._tech_stack:
            stats_content.append(f"[bold]Technologies:[/bold] {', '.join(self._tech_stack[:5])}")
        
        # MCP servers
        if self.available_mcp_servers:
            stats_content.append(f"[bold]MCP Servers:[/bold] {len(self.available_mcp_servers)} available")
        
        # Research status
        if self.memory and "research_results" in self.memory.context:
            stats_content.append(f"[bold]Research:[/bold] ✓ Completed")
        
        stats_panel = Panel(
            "\n".join(stats_content),
            title="[bold]Build Statistics[/bold]",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        
        self.console.print(stats_panel)
        
        # Show first phase details
        if phases and self.args.verbose:
            first_phase = phases[0]
            phase_details = []
            phase_details.append(f"[bold cyan]{first_phase.name}[/bold cyan]")
            phase_details.append(f"[dim]{first_phase.description}[/dim]")
            phase_details.append("\n[green]Tasks:[/green]")
            
            for j, task in enumerate(first_phase.tasks[:8], 1):
                phase_details.append(f"  {j}. {task}")
            
            if len(first_phase.tasks) > 8:
                phase_details.append(f"  ... and {len(first_phase.tasks) - 8} more tasks")
            
            self.console.print(Panel(
                "\n".join(phase_details),
                title="First Phase Preview",
                box=box.ROUNDED,
                padding=(1, 2)
            ))
        
        # Show key features
        features = []
        if self.args.enable_research:
            features.append("[green]✓[/green] AI-Powered Research")
        if self.available_mcp_servers:
            features.append("[green]✓[/green] MCP Server Integration")
        if self.args.git_init:
            features.append("[green]✓[/green] Git Version Control")
        if self.args.run_tests:
            features.append("[green]✓[/green] Automated Testing")
        
        if features:
            self.console.print(Panel(
                " • ".join(features),
                title="[bold]Enabled Features[/bold]",
                box=box.ROUNDED
            ))
        
        # Confirmation
        if self.args.auto_confirm:
            self.console.print("\n[green]Auto-confirm enabled, proceeding...[/green]")
            return True
        
        return Confirm.ask("\n[bold]Proceed with build?[/bold]", default=True)
    
    def _estimate_cost(self, phases: List[Phase]) -> float:
        """Enhanced cost estimation based on complexity"""
        total_tasks = sum(len(p.tasks) for p in phases)
        
        # Base token estimates
        avg_input_tokens = 2500  # Per task average
        avg_output_tokens = 3500  # Per task average
        
        # Adjust for complexity
        complexity_multiplier = {
            "low": 0.8,
            "medium": 1.0,
            "high": 1.3
        }.get(getattr(self, '_complexity', 'medium'), 1.0)
        
        # Adjust for Claude Code execution overhead
        claude_code_multiplier = 1.2  # Claude Code adds ~20% overhead
        
        total_input = total_tasks * avg_input_tokens * complexity_multiplier
        total_output = total_tasks * avg_output_tokens * complexity_multiplier
        
        # Calculate API cost
        model = self.args.model_executor
        if model in TOKEN_COSTS:
            input_cost = (total_input / 1_000_000) * TOKEN_COSTS[model]["input"]
            output_cost = (total_output / 1_000_000) * TOKEN_COSTS[model]["output"]
            api_cost = input_cost + output_cost
        else:
            # Fallback estimation
            api_cost = total_tasks * 0.08
        
        # Add Claude Code execution cost (rough estimate)
        claude_code_cost = len(phases) * 0.05  # Estimated $0.05 per phase
        
        return (api_cost + claude_code_cost) * claude_code_multiplier
    
    async def _execute_phases(self, phases: List[Phase], resume: bool = False):
        """Execute all phases with enhanced error handling and recovery"""
        self.console.print("\n[bold cyan]🚀 Starting build process...[/bold cyan]\n")
        
        # Filter phases to execute
        if resume:
            phases_to_execute = [p for p in phases if not p.completed]
        else:
            phases_to_execute = phases
        
        if not phases_to_execute:
            self.console.print("[green]All phases already completed![/green]")
            return
        
        # Create progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console,
            transient=False
        ) as progress:
            
            overall_task = progress.add_task(
                "[bold]Overall Progress",
                total=len(phases_to_execute)
            )
            
            for i, phase in enumerate(phases):
                # Check for shutdown
                if self._shutdown_requested:
                    self.logger.warning("Shutdown requested, stopping execution")
                    self.console.print("\n[yellow]Build interrupted, saving state...[/yellow]")
                    await self._store_memory("interrupted")
                    break
                
                # Skip completed phases
                if phase.completed and resume:
                    continue
                
                # Check dependencies
                if not self._check_dependencies(phase, phases):
                    if self.args.continue_on_error:
                        self.console.print(f"[yellow]⚠ Skipping {phase.name} - dependencies not met[/yellow]")
                        phase.status = BuildStatus.SKIPPED
                        phase.add_message("Skipped due to unmet dependencies", "warning")
                        progress.advance(overall_task)
                        continue
                    else:
                        raise RuntimeError(f"Dependencies not met for {phase.name}")
                
                # Execute phase
                phase_num = phases.index(phase) + 1
                total_phases = len(phases)
                
                # Show phase header
                self.console.rule(
                    f"[bold cyan]Phase {phase_num}/{total_phases}: {phase.name}[/bold cyan]",
                    style="cyan"
                )
                
                phase_task = progress.add_task(
                    f"[cyan]Executing {phase.name}",
                    total=100
                )
                
                try:
                    # Update build stats
                    phase_start = datetime.now()
                    
                    # Execute the phase
                    await self._execute_phase(phase, progress, phase_task)
                    
                    # Track phase duration
                    phase_duration = (datetime.now() - phase_start).total_seconds()
                    self.build_stats.phase_durations[phase.id] = phase_duration
                    
                    # Store memory checkpoint
                    await self._store_memory(f"completed_{phase.id}")
                    
                    # Store phase context
                    if phase.context:
                        self.memory.store_phase_context(phase.id, phase.context)
                    
                    # Commit changes if git enabled
                    if self.args.git_init:
                        self._commit_phase_changes(phase)
                    
                    # Show phase summary
                    self._show_phase_summary(phase)
                    
                except Exception as e:
                    self.logger.error(f"Phase failed: {phase.name}", exc_info=True)
                    phase.error = str(e)
                    phase.status = BuildStatus.FAILED
                    self.memory.log_error(str(e), phase.id, {"phase": phase.name})
                    
                    # Retry logic
                    if phase.retry_count < self.args.max_retries:
                        self.console.print(f"[yellow]⚠ Phase failed, retrying ({phase.retry_count + 1}/{self.args.max_retries})...[/yellow]")
                        phase.retry_count += 1
                        phase.status = BuildStatus.RETRYING
                        self.build_stats.retries_performed += 1
                        
                        # Wait before retry
                        await asyncio.sleep(RETRY_DELAY * phase.retry_count)
                        
                        # Clear error and retry
                        phase.error = None
                        try:
                            await self._execute_phase(phase, progress, phase_task)
                        except Exception as retry_error:
                            phase.error = str(retry_error)
                            phase.status = BuildStatus.FAILED
                    
                    if phase.status == BuildStatus.FAILED:
                        if not self.args.continue_on_error:
                            progress.stop()
                            raise
                        
                        self.console.print(f"[red]✗ Failed: {phase.name}[/red]")
                        self.console.print(f"[dim]Error: {str(e)}[/dim]")
                
                finally:
                    progress.update(phase_task, completed=100)
                    progress.advance(overall_task)
            
            progress.update(overall_task, completed=len(phases_to_execute))
    
    def _check_dependencies(self, phase: Phase, all_phases: List[Phase]) -> bool:
        """Enhanced dependency checking with validation"""
        if not phase.dependencies:
            return True
        
        for dep_id in phase.dependencies:
            dep_phase = next((p for p in all_phases if p.id == dep_id), None)
            if not dep_phase:
                self.logger.error(f"Dependency {dep_id} not found for phase {phase.id}")
                return False
            if not dep_phase.completed:
                self.logger.debug(f"Dependency {dep_id} not completed for phase {phase.id}")
                return False
            if not dep_phase.success:
                self.logger.warning(f"Dependency {dep_id} failed for phase {phase.id}")
                # Allow execution if continue_on_error is set
                if not self.args.continue_on_error:
                    return False
        
        return True
    
    async def _execute_phase(self, phase: Phase, progress: Progress, task_id: TaskID):
        """Execute a single phase with enhanced context management"""
        phase.start_time = datetime.now()
        phase.status = BuildStatus.RUNNING
        self.memory.current_phase = phase.id
        
        # Enhanced logging for phase execution
        self.logger.info("="*80)
        self.logger.info(f"EXECUTING PHASE: {phase.name}")
        self.logger.info("="*80)
        self.logger.info(f"Phase ID: {phase.id}")
        self.logger.info(f"Description: {phase.description}")
        self.logger.info(f"Tasks ({len(phase.tasks)}):")
        for i, task in enumerate(phase.tasks, 1):
            self.logger.info(f"  {i}. {task}")
        self.logger.info(f"Dependencies: {', '.join(phase.dependencies) if phase.dependencies else 'None'}")
        self.logger.info(f"Retry attempt: {phase.retry_count + 1}/{self.args.max_retries}")
        
        phase.add_message(f"Phase execution started", "info")
        
        # Display phase info
        phase_info = Panel(
            f"[dim]{phase.description}[/dim]\n\n"
            f"[green]📋 Tasks:[/green] {len(phase.tasks)}\n"
            f"[yellow]🔗 Dependencies:[/yellow] {', '.join(phase.dependencies) if phase.dependencies else 'None'}\n"
            f"[blue]🔄 Retry:[/blue] {phase.retry_count}/{self.args.max_retries}",
            title=f"[bold]{phase.name}[/bold]",
            box=box.ROUNDED
        )
        self.console.print(phase_info)
        
        # Create phase prompt with enhanced context
        prompt = await self._create_phase_prompt(phase)
        
        # Save prompt if requested
        if self.args.save_prompts:
            await self._save_prompt(phase, prompt)
        
        # Update progress
        progress.update(task_id, description=f"[cyan]Executing {phase.name}...")
        
        try:
            # Execute Claude Code
            await self._execute_claude_code(prompt, phase, progress, task_id)
            
            # Validate phase completion
            if phase.validate():
                phase.completed = True
                phase.success = True
                phase.status = BuildStatus.SUCCESS
                self.memory.completed_phases.append(phase.id)
                
                # Add success message
                phase.add_message(f"Phase completed successfully", "success")
                
                # Record important decision
                self.memory.important_decisions.append(
                    f"Completed {phase.name} successfully after {phase.retry_count + 1} attempt(s)"
                )
                
                self.logger.info(f"✓ Phase completed: {phase.name}")
            else:
                # Phase completed but validation failed
                phase.completed = True
                phase.success = False
                phase.status = BuildStatus.FAILED
                phase.error = "Phase validation failed"
                phase.add_message("Phase validation failed", "error")
                
                self.logger.warning(f"Phase completed but validation failed: {phase.name}")
                
                if not self.args.continue_on_error:
                    raise RuntimeError(f"Phase validation failed: {phase.name}")
                
        except Exception as e:
            phase.add_message(f"Execution error: {str(e)}", "error")
            raise
        
        finally:
            phase.end_time = datetime.now()
            if phase.duration:
                self.logger.info(f"Phase duration: {phase.duration.total_seconds():.1f}s")
    
    async def _create_phase_prompt(self, phase: Phase) -> str:
        """Create enhanced phase prompt with better context integration"""
        # Get accumulated context from all previous phases
        accumulated_context = self.memory.get_accumulated_context(phase.id)
        
        # Get phase-specific context
        context = self._get_enhanced_phase_context(phase, accumulated_context)
        
        # Get memory summary
        memory_summary = self._get_enhanced_memory_summary()
        
        # Get MCP servers summary
        mcp_summary = self._get_enhanced_mcp_summary()
        
        # Get custom instructions
        project_context = {
            "current_phase": phase.id,
            "phase_name": phase.name,
            "project_name": self.memory.project_name if self.memory else "",
            "project_type": getattr(self, '_project_type', 'general'),
            "technology_stack": getattr(self, '_tech_stack', []),
            "requirements": getattr(self, '_requirements', []),
            "complexity": getattr(self, '_complexity', 'medium'),
            "phase_number": self.memory.phases.index(phase) + 1 if self.memory else 1,
            "total_phases": len(self.memory.phases) if self.memory else 1
        }
        custom_instructions = self.custom_instructions.generate_context_prompt(project_context)
        
        # Get allowed tools
        allowed_tools = []
        if self.tool_manager:
            allowed_tools = self.tool_manager.generate_allowed_tools_list(
                project_context, self.custom_instructions
            )
        
        # Include specification content
        spec_section = ""
        if hasattr(self, 'specification_content') and self.specification_content:
            if phase.id == "phase_1":
                # Full spec for first phase
                spec_section = f"""
PROJECT SPECIFICATION:
================================================================================
{self.specification_content}
================================================================================

This specification must be implemented exactly as described above.
"""
            else:
                # Summary for subsequent phases
                spec_section = f"""
PROJECT SPECIFICATION SUMMARY:
{self.specification_content[:2000]}
... [See phase 1 for full specification]
================================================================================
"""
        
        # Enhanced logging
        self.logger.info(f"Creating prompt for phase: {phase.name}")
        self.logger.debug(f"Phase tasks ({len(phase.tasks)}): {phase.tasks}")
        self.logger.debug(f"Phase dependencies: {phase.dependencies}")
        self.logger.debug(f"Custom instructions included: {len(custom_instructions)} chars")
        
        prompt = f"""You are Claude Code Builder v2.3 executing phase {phase.id} of a multi-phase project.

{memory_summary}

{mcp_summary}

{custom_instructions}

{spec_section}

CURRENT PHASE:
- Name: {phase.name}
- Description: {phase.description}
- Phase {project_context['phase_number']} of {project_context['total_phases']}
- Retry Attempt: {phase.retry_count + 1}

DETAILED TASKS TO COMPLETE:
{chr(10).join(f"{i+1}. {task}" for i, task in enumerate(phase.tasks))}

{context}

CRITICAL REQUIREMENTS:
1. Complete ALL tasks listed above - implement actual functionality
2. Create production-ready code with comprehensive error handling
3. Use MCP servers when available (tools follow pattern mcp__<server>__<tool>)
4. Store important decisions and context in memory MCP
5. NO UNIT TESTS OR MOCKING - we work with real data only
6. Add proper logging throughout the implementation
7. Include documentation and comments
8. Follow best practices for the technology stack
9. Never use placeholder implementations or TODOs
10. Validate all inputs and outputs

APPROACH:
1. Start by understanding the specification and tasks
2. Use mcp__memory__recall to get previous context
3. Use mcp__sequential-thinking__plan to plan the implementation
4. Create all necessary files and directories
5. Implement each task completely and thoroughly
6. Store decisions with mcp__memory__store
7. Commit changes with mcp__git__commit after major milestones
8. Verify all tasks are completed before finishing

Remember: This is a production build. Every file must be complete and functional."""
        
        return prompt
    
    def _get_enhanced_phase_context(self, phase: Phase, accumulated_context: Dict[str, Any]) -> str:
        """Get enhanced context from previous phases with accumulated knowledge"""
        if not phase.dependencies:
            return "\nCONTEXT: This is the first phase. Establish the project foundation with production-quality code."
        
        context_parts = ["\nCONTEXT FROM PREVIOUS PHASES:"]
        
        # Add accumulated context summary
        if accumulated_context:
            context_parts.append("\nACCUMULATED PROJECT KNOWLEDGE:")
            for key, value in accumulated_context.items():
                if key not in ["specification", "research_results"]:  # Skip large items
                    if isinstance(value, list) and value:
                        context_parts.append(f"- {key}: {', '.join(str(v) for v in value[:5])}")
                    elif isinstance(value, dict):
                        context_parts.append(f"- {key}: {len(value)} items")
                    else:
                        context_parts.append(f"- {key}: {value}")
        
        # Add specific phase contexts
        for dep_id in phase.dependencies:
            dep_phase = self.memory.get_phase_by_id(dep_id)
            if dep_phase and dep_phase.completed:
                context_parts.append(f"\n{'='*60}")
                context_parts.append(f"Phase: {dep_phase.name}")
                context_parts.append(f"Status: {'✓ Success' if dep_phase.success else '✗ Failed'}")
                context_parts.append(f"Duration: {dep_phase.duration_seconds:.1f}s")
                
                if dep_phase.output_summary:
                    context_parts.append(f"Summary: {dep_phase.output_summary}")
                
                if dep_phase.files_created:
                    context_parts.append(f"\nFiles created ({len(dep_phase.files_created)}):")
                    # Group files by type
                    files_by_type = defaultdict(list)
                    for file in dep_phase.files_created:
                        ext = Path(file).suffix or 'no_ext'
                        files_by_type[ext].append(file)
                    
                    for ext, files in sorted(files_by_type.items()):
                        context_parts.append(f"  {ext}: {len(files)} files")
                        for file in files[:3]:
                            context_parts.append(f"    - {file}")
                        if len(files) > 3:
                            context_parts.append(f"    ... and {len(files) - 3} more")
                
                # Add phase-specific context
                if dep_id in self.memory.phase_contexts:
                    phase_ctx = self.memory.phase_contexts[dep_id]
                    if "context" in phase_ctx and phase_ctx["context"]:
                        context_parts.append("\nPhase-specific context:")
                        for k, v in phase_ctx["context"].items():
                            context_parts.append(f"  - {k}: {v}")
        
        # Add error context if retrying
        if phase.retry_count > 0 and phase.messages:
            context_parts.append(f"\n{'='*60}")
            context_parts.append("PREVIOUS ATTEMPT INFORMATION:")
            # Show last few messages
            for msg in phase.messages[-5:]:
                if "error" in msg.lower():
                    context_parts.append(f"  {msg}")
        
        return "\n".join(context_parts)
    
    def _get_enhanced_memory_summary(self) -> str:
        """Get enhanced memory summary with key insights"""
        if not self.memory:
            return "PROJECT MEMORY: No previous context available."
        
        summary = ["PROJECT MEMORY AND CONTEXT:"]
        summary.append(f"Project: {self.memory.project_name}")
        summary.append(f"Location: {self.memory.project_path}")
        summary.append(f"Build ID: {self.memory.build_id[:8]}...")
        summary.append(f"Progress: {len(self.memory.completed_phases)}/{len(self.memory.phases)} phases completed")
        
        # Technology summary
        if self.memory.context.get("technology_stack"):
            summary.append(f"Stack: {', '.join(self.memory.context['technology_stack'])}")
        
        # Key decisions
        if self.memory.important_decisions:
            summary.append("\nKEY DECISIONS MADE:")
            for decision in self.memory.important_decisions[-5:]:
                summary.append(f"- {decision}")
        
        # Files summary
        if self.memory.created_files:
            file_stats = defaultdict(int)
            for file in self.memory.created_files:
                ext = Path(file).suffix or 'other'
                file_stats[ext] += 1
            
            summary.append(f"\nFILES CREATED: {len(self.memory.created_files)} total")
            for ext, count in sorted(file_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                summary.append(f"  {ext}: {count} files")
        
        # Research insights
        if "research_results" in self.memory.context:
            summary.append("\nRESEARCH INSIGHTS AVAILABLE: Yes")
            summary.append("Key areas: technology, security, architecture, performance")
        
        return "\n".join(summary)
    
    def _get_enhanced_mcp_summary(self) -> str:
        """Get enhanced MCP servers summary with usage tips"""
        if not self.available_mcp_servers:
            return "MCP SERVERS: None available. Using standard tools only."
        
        summary = ["MCP SERVERS AVAILABLE:"]
        
        # Group servers by category
        servers_by_category = defaultdict(list)
        for server in sorted(self.available_mcp_servers):
            if server in MCP_SERVER_REGISTRY:
                info = MCP_SERVER_REGISTRY[server]
                servers_by_category[info["category"]].append((server, info))
        
        # Display by category
        for category in ["core", "development", "database", "external", "communication", "documentation"]:
            if category in servers_by_category:
                summary.append(f"\n[{category.upper()}]")
                for server, info in servers_by_category[category]:
                    tools = info.get("tools", [])
                    tools_str = ", ".join([f"mcp__{server}__{tool}" for tool in tools[:4]])
                    if len(tools) > 4:
                        tools_str += f" +{len(tools)-4} more"
                    summary.append(f"- {server}: {tools_str}")
        
        # Add usage reminders
        summary.extend([
            "\nMCP USAGE REMINDERS:",
            "- Always use mcp__memory__store for important context",
            "- Use mcp__sequential-thinking__plan for complex tasks",
            "- Prefer mcp__filesystem__* over basic file operations when available",
            "- Commit with mcp__git__commit after significant changes"
        ])
        
        return "\n".join(summary)
    
    async def _save_prompt(self, phase: Phase, prompt: str):
        """Save prompt for debugging and analysis"""
        prompt_dir = self.args.output_dir / ".prompts"
        prompt_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_file = prompt_dir / f"{phase.id}_{timestamp}.md"
        
        content = f"""# Prompt for {phase.name}
Generated at: {datetime.now().isoformat()}
Phase: {phase.id}
Tasks: {len(phase.tasks)}
Retry: {phase.retry_count}
{"="*80}

{prompt}
"""
        
        if aiofiles:
            async with aiofiles.open(prompt_file, 'w', encoding='utf-8') as f:
                await f.write(content)
        else:
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(content)
        
        self.logger.debug(f"Saved prompt to: {prompt_file}")
    
    async def _execute_claude_code(self, prompt: str, phase: Phase, progress: Progress, task_id: TaskID):
        """Execute Claude Code with enhanced error handling and cost tracking"""
        # Build command
        cmd = self._build_claude_command(phase)
        
        # Write prompt to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(prompt)
            prompt_file = f.name
        
        self.logger.info(f"Executing Claude Code for phase: {phase.name}")
        self.logger.debug(f"Command: {' '.join(cmd)}")
        phase.add_message("Starting Claude Code execution", "info")
        
        try:
            # Create subprocess with enhanced environment
            env = os.environ.copy()
            env['CLAUDE_CODE_BUILDER'] = 'v2.3.0'
            
            # Read prompt content for stdin
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_content = f.read()
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.args.output_dir,
                env=env
            )
            
            self.logger.info(f"Process started (PID: {process.pid})")
            phase.add_message(f"Claude Code process started (PID: {process.pid})", "info")
            
            # Handle streaming output
            if self.args.stream_output:
                handler = StreamingMessageHandler(
                    phase=phase,
                    console=self.console,
                    logger=self.logger,
                    build_stats=self.build_stats,
                    cost_tracker=self.cost_tracker,
                    args=self.args
                )
                
                # Update progress during streaming
                async def update_progress_callback():
                    while process.returncode is None:
                        # Update based on message count or other metrics
                        if hasattr(handler, 'message_count'):
                            completion = min(95, handler.message_count * 5)  # Cap at 95%
                            progress.update(task_id, completed=completion)
                        await asyncio.sleep(1)
                
                # Start progress updater
                progress_task = asyncio.create_task(update_progress_callback())
                
                try:
                    # Send prompt via stdin
                    process.stdin.write(prompt_content.encode('utf-8'))
                    await process.stdin.drain()
                    process.stdin.close()
                    
                    return_code, output = await handler.handle_stream(process)
                finally:
                    progress_task.cancel()
                
                # Get summary
                summary = handler.get_summary()
                
                # Update phase with summary
                if summary.get('session_cost'):
                    phase.add_message(f"Session cost: ${summary['session_cost']:.4f}", "info")
                
            else:
                # Non-streaming execution - send prompt via stdin
                stdout, stderr = await process.communicate(input=prompt_content.encode('utf-8'))
                output = stdout.decode('utf-8', errors='replace')
                return_code = process.returncode
                
                # Parse output for cost
                for line in output.splitlines():
                    try:
                        data = json.loads(line.strip())
                        if data.get("type") == "result" and "cost_usd" in data:
                            self.cost_tracker.add_claude_code_cost(
                                data["cost_usd"],
                                {"phase": phase.name}
                            )
                            break
                    except:
                        continue
            
            if return_code != 0:
                stderr_output = stderr.decode('utf-8', errors='replace') if 'stderr' in locals() else ""
                error_msg = f"Claude Code failed (exit code {return_code})"
                if stderr_output:
                    error_msg += f": {stderr_output[:500]}"
                phase.add_message(error_msg, "error")
                raise RuntimeError(error_msg)
            
            # Update memory with created files
            self.memory.created_files.extend(phase.files_created)
            
            # Deduplicate files
            self.memory.created_files = list(set(self.memory.created_files))
            
            self.logger.info(f"Phase execution completed successfully")
            phase.add_message("Claude Code execution completed", "success")
            
        except asyncio.TimeoutError:
            error_msg = f"Claude Code execution timed out for phase {phase.name}"
            phase.add_message(error_msg, "error")
            raise RuntimeError(error_msg)
        except Exception as e:
            phase.add_message(f"Execution failed: {str(e)}", "error")
            raise
        finally:
            if os.path.exists(prompt_file):
                os.unlink(prompt_file)
            
            # Ensure progress is updated
            progress.update(task_id, completed=100)
    
    def _build_claude_command(self, phase: Phase) -> List[str]:
        """Build enhanced Claude Code command"""
        cmd = ["claude"]
        
        # Log command building
        self.logger.info(f"Building command for phase: {phase.name}")
        
        # Use -p flag with streaming JSON for programmatic execution
        cmd.extend(["-p"])
        
        # Skip permissions for programmatic execution
        cmd.extend(["--dangerously-skip-permissions"])
        
        # Add output format based on streaming preference
        if self.args.stream_output:
            cmd.extend(["--output-format", "stream-json", "--verbose"])
        else:
            cmd.extend(["--output-format", "json"])
        
        # Model
        cmd.extend(["--model", self.args.model_executor])
        
        # MCP configuration - use absolute path
        mcp_config_path = (self.args.output_dir / ".mcp.json").resolve()
        if mcp_config_path.exists():
            cmd.extend(["--mcp-config", str(mcp_config_path)])
        
        # Allowed tools with optimization
        if self.tool_manager:
            project_context = {
                "current_phase": phase.id,
                "phase_name": phase.name,
                "project_name": self.memory.project_name if self.memory else "",
                "project_type": getattr(self, '_project_type', 'general'),
                "technology_stack": getattr(self, '_tech_stack', []),
                "requirements": getattr(self, '_requirements', []),
                "complexity": getattr(self, '_complexity', 'medium'),
                "phase_number": self.memory.phases.index(phase) + 1 if self.memory else 1
            }
            allowed_tools = self.tool_manager.generate_allowed_tools_list(
                project_context, self.custom_instructions
            )
            
            # Optimize tool list based on performance
            allowed_tools = self.tool_manager.optimize_tool_list(allowed_tools)
            
            if allowed_tools:
                # Join tools with commas for the CLI
                tools_str = ",".join(allowed_tools)
                cmd.extend(["--allowedTools", tools_str])
        
        # Output format for better parsing
        if self.args.stream_output:
            cmd.extend(["--output-format", "stream-json"])
            # Need verbose with stream-json when using --print
            cmd.extend(["--verbose"])
        else:
            cmd.extend(["--output-format", "json"])
        
        # Max turns with phase-specific adjustment
        max_turns = self.args.max_turns
        # Increase turns for complex phases
        if any(keyword in phase.name.lower() for keyword in ["test", "deploy", "optimization"]):
            max_turns = int(max_turns * 1.5)
        cmd.extend(["--max-turns", str(max_turns)])
        
        # Add timeout if supported
        # cmd.extend(["--timeout", str(self.args.phase_timeout)])
        
        # Log the final command
        self.logger.info(f"Claude Code command: {' '.join(cmd)}")
        
        return cmd
    
    def _show_phase_summary(self, phase: Phase):
        """Show enhanced phase execution summary"""
        if not phase.completed:
            return
        
        # Create summary content
        summary_parts = []
        
        # Status
        if phase.success:
            summary_parts.append(f"[green]✓ Status: Success[/green]")
        else:
            summary_parts.append(f"[red]✗ Status: Failed[/red]")
        
        # Duration
        if phase.duration:
            summary_parts.append(f"⏱ Duration: {phase.duration_seconds:.1f}s")
        
        # Files
        if phase.files_created:
            file_count = len(phase.files_created)
            summary_parts.append(f"📁 Files created: {file_count}")
            
            # Show file types
            file_types = defaultdict(int)
            for file in phase.files_created:
                ext = Path(file).suffix or 'other'
                file_types[ext] += 1
            
            if file_types:
                types_str = ", ".join(f"{ext}:{count}" for ext, count in sorted(file_types.items()))
                summary_parts.append(f"   Types: {types_str}")
        
        # Tool usage
        if phase.tool_calls:
            summary_parts.append(f"🔧 Tools used: {len(phase.tool_calls)}")
        
        # Retries
        if phase.retry_count > 0:
            summary_parts.append(f"🔄 Retries: {phase.retry_count}")
        
        # Cost (if available)
        phase_cost = self.cost_tracker.phase_costs.get(phase.name, 0.0)
        if phase_cost > 0:
            summary_parts.append(f"💰 Cost: ${phase_cost:.4f}")
        
        # Show summary
        summary_panel = Panel(
            "\n".join(summary_parts),
            title=f"[bold]Phase Summary: {phase.name}[/bold]",
            box=box.ROUNDED,
            border_style="green" if phase.success else "red"
        )
        
        self.console.print(summary_panel)
    
    def _commit_phase_changes(self, phase: Phase):
        """Commit changes with enhanced information"""
        try:
            # Check if there are changes to commit
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.args.output_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            if not status_result.stdout.strip():
                self.logger.debug(f"No changes to commit for phase {phase.id}")
                return
            
            # Add all changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.args.output_dir,
                check=True,
                capture_output=True
            )
            
            # Create detailed commit message
            commit_msg = f"Phase {phase.id}: {phase.name}\n\n"
            commit_msg += f"Status: {'Success' if phase.success else 'Failed'}\n"
            commit_msg += f"Duration: {phase.duration_seconds:.1f}s\n"
            commit_msg += f"Tasks completed: {len(phase.tasks)}\n"
            
            if phase.files_created:
                commit_msg += f"\nFiles created ({len(phase.files_created)}):\n"
                
                # Group by directory
                files_by_dir = defaultdict(list)
                for file in phase.files_created:
                    dir_name = os.path.dirname(file) or "."
                    files_by_dir[dir_name].append(os.path.basename(file))
                
                for dir_name, files in sorted(files_by_dir.items())[:5]:
                    commit_msg += f"\n{dir_name}/\n"
                    for file in sorted(files)[:5]:
                        commit_msg += f"  - {file}\n"
                    if len(files) > 5:
                        commit_msg += f"  ... and {len(files) - 5} more\n"
                
                if len(files_by_dir) > 5:
                    commit_msg += f"\n... and {len(files_by_dir) - 5} more directories\n"
            
            # Add cost if available
            phase_cost = self.cost_tracker.phase_costs.get(phase.name, 0.0)
            if phase_cost > 0:
                commit_msg += f"\nCost: ${phase_cost:.4f}\n"
            
            # Add builder info
            commit_msg += f"\nBuilder: Claude Code Builder v2.3.0\n"
            commit_msg += f"Build ID: {self.memory.build_id[:8] if self.memory else 'unknown'}\n"
            
            # Commit
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.args.output_dir,
                check=True,
                capture_output=True
            )
            
            self.logger.debug(f"Committed changes for phase {phase.id}")
            
        except subprocess.CalledProcessError as e:
            # Check if there were no changes
            if "nothing to commit" in e.stdout.decode('utf-8', errors='ignore'):
                self.logger.debug(f"No changes to commit for phase {phase.id}")
            else:
                self.logger.warning(f"Failed to commit changes: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to commit changes: {e}")
    
    async def _store_memory(self, checkpoint_name: str):
        """Store enhanced project memory checkpoint"""
        self.memory.updated_at = datetime.now()
        self.memory.add_checkpoint(checkpoint_name, {
            "build_stats": self.build_stats.get_summary(),
            "cost_summary": self.cost_tracker.get_summary(),
            "tool_stats": self.tool_manager.get_tool_statistics() if self.tool_manager else None
        })
        
        # Store to file system
        memory_dir = self.args.output_dir / ".memory"
        memory_dir.mkdir(exist_ok=True)
        
        timestamp = int(time.time())
        memory_file = memory_dir / f"{checkpoint_name}_{timestamp}.json"
        
        memory_data = {
            "timestamp": datetime.now().isoformat(),
            "checkpoint": checkpoint_name,
            "memory": self.memory.to_json(),
            "stats": self.build_stats.get_summary(),
            "costs": self.cost_tracker.get_summary(),
            "tool_performance": self.tool_manager.get_tool_statistics() if self.tool_manager else None
        }
        
        # Write atomically
        temp_file = memory_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        # Atomic rename
        temp_file.replace(memory_file)
        
        self.logger.debug(f"Stored memory checkpoint: {checkpoint_name}")
        
        # Store to MCP memory if available
        if "memory" in self.available_mcp_servers:
            # This would be done within Claude Code execution
            pass
        
        # Cleanup old checkpoints
        self._cleanup_old_checkpoints(memory_dir)
    
    def _cleanup_old_checkpoints(self, memory_dir: Path, keep: int = 20):
        """Keep only the most recent checkpoints"""
        try:
            checkpoints = sorted(
                memory_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            # Always keep certain checkpoints
            important_patterns = ["emergency", "final", "interrupted", "failed"]
            
            to_delete = []
            kept_count = 0
            
            for checkpoint in checkpoints:
                # Keep important checkpoints
                if any(pattern in checkpoint.name for pattern in important_patterns):
                    continue
                
                kept_count += 1
                if kept_count > keep:
                    to_delete.append(checkpoint)
            
            # Delete old checkpoints
            for old_checkpoint in to_delete:
                old_checkpoint.unlink()
                self.logger.debug(f"Removed old checkpoint: {old_checkpoint.name}")
                
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old checkpoints: {e}")
    
    async def _post_build_operations(self):
        """Perform post-build operations"""
        self.logger.info("Performing post-build operations...")
        
        # Create project summary
        await self._create_project_summary()
        
        # Generate analytics
        await self._generate_build_analytics()
        
        # Create deployment guide if applicable
        if any("deploy" in phase.name.lower() for phase in self.memory.phases if phase.completed):
            await self._create_deployment_guide()
        
        # Final git commit
        if self.args.git_init:
            self._final_git_commit()
    
    async def _create_project_summary(self):
        """Create comprehensive project summary"""
        summary_content = f"""# {self.memory.project_name if self.memory else 'Project'} Summary

Generated by Claude Code Builder v2.3.0
Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Build ID: {self.memory.build_id if self.memory else 'unknown'}

## Project Overview

- **Type**: {getattr(self, '_project_type', 'Unknown')}
- **Complexity**: {getattr(self, '_complexity', 'Unknown')}
- **Technology Stack**: {', '.join(getattr(self, '_tech_stack', []))}
- **Requirements**: {', '.join(getattr(self, '_requirements', []))}

## Build Statistics

- **Total Phases**: {len(self.memory.phases) if self.memory else 0}
- **Completed Phases**: {len([p for p in self.memory.phases if p.completed]) if self.memory else 0}
- **Total Files Created**: {self.build_stats.files_created}
- **Lines of Code**: {self.build_stats.lines_of_code:,}
- **Total Cost**: ${self.cost_tracker.total_cost:.2f}
- **Build Duration**: {str(datetime.now() - self.start_time).split('.')[0]}

## Phase Summary

"""
        
        if self.memory:
            for i, phase in enumerate(self.memory.phases, 1):
                status = "✓" if phase.success else "✗" if phase.completed else "○"
                summary_content += f"{i}. **{phase.name}** [{status}]\n"
                if phase.completed:
                    summary_content += f"   - Duration: {phase.duration_seconds:.1f}s\n"
                    summary_content += f"   - Files: {len(phase.files_created)}\n"
                    if phase.error:
                        summary_content += f"   - Error: {phase.error}\n"
                summary_content += "\n"
        
        summary_content += """## Key Files

### Configuration Files
"""
        
        # List key configuration files
        config_patterns = ["config", "settings", ".env", "package.json", "pyproject.toml", "requirements.txt"]
        config_files = []
        
        if self.memory:
            for file in self.memory.created_files:
                if any(pattern in file.lower() for pattern in config_patterns):
                    config_files.append(file)
        
        for file in sorted(config_files)[:10]:
            summary_content += f"- `{file}`\n"
        
        summary_content += "\n### Entry Points\n"
        
        # List entry points
        entry_patterns = ["main", "app", "index", "server", "__main__", "cli"]
        entry_files = []
        
        if self.memory:
            for file in self.memory.created_files:
                if any(pattern in os.path.basename(file).lower() for pattern in entry_patterns):
                    entry_files.append(file)
        
        for file in sorted(entry_files)[:10]:
            summary_content += f"- `{file}`\n"
        
        summary_content += """
## Next Steps

1. Review the generated code and documentation
2. Install dependencies (check package.json or requirements.txt)
3. Configure environment variables (see .env.example)
4. Run tests to verify functionality
5. Deploy according to the deployment guide

## MCP Servers Used

"""
        
        for server in sorted(self.available_mcp_servers):
            summary_content += f"- **{server}**: {MCP_SERVER_REGISTRY.get(server, {}).get('description', 'Custom server')}\n"
        
        # Save summary
        summary_path = self.args.output_dir / "PROJECT_SUMMARY.md"
        with open(summary_path, 'w') as f:
            f.write(summary_content)
        
        self.logger.info("Created project summary")
    
    async def _generate_build_analytics(self):
        """Generate detailed build analytics"""
        analytics_dir = self.args.output_dir / ".analytics"
        analytics_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Build statistics
        stats_file = analytics_dir / f"build_stats_{timestamp}.json"
        with open(stats_file, 'w') as f:
            json.dump({
                "build_info": {
                    "builder_version": "2.3.0",
                    "build_id": self.memory.build_id if self.memory else "unknown",
                    "start_time": self.start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration_seconds": (datetime.now() - self.start_time).total_seconds()
                },
                "statistics": self.build_stats.get_summary(),
                "costs": self.cost_tracker.get_summary(),
                "cost_breakdown": self.cost_tracker.get_model_breakdown(),
                "tool_performance": self.tool_manager.get_tool_statistics() if self.tool_manager else None,
                "phase_performance": {
                    phase.id: {
                        "name": phase.name,
                        "duration": phase.duration_seconds,
                        "success": phase.success,
                        "files_created": len(phase.files_created),
                        "tool_calls": len(phase.tool_calls),
                        "retries": phase.retry_count
                    }
                    for phase in (self.memory.phases if self.memory else [])
                }
            }, f, indent=2)
        
        # Create human-readable analytics report
        report_file = analytics_dir / f"analytics_report_{timestamp}.md"
        report_content = self._create_analytics_report()
        
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        self.logger.info("Generated build analytics")
    
    def _create_analytics_report(self) -> str:
        """Create human-readable analytics report"""
        report = f"""# Build Analytics Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Performance Metrics

### Build Performance
- **Total Duration**: {str(datetime.now() - self.start_time).split('.')[0]}
- **Average Phase Duration**: {sum(self.build_stats.phase_durations.values()) / max(len(self.build_stats.phase_durations), 1):.1f}s
- **Longest Phase**: {max(self.build_stats.phase_durations.items(), key=lambda x: x[1])[0] if self.build_stats.phase_durations else 'N/A'}

### Resource Usage
- **Total Tool Calls**: {sum(self.build_stats.tool_calls.values())}
- **MCP Calls**: {self.build_stats.mcp_calls}
- **Commands Executed**: {self.build_stats.commands_executed}
- **Errors Encountered**: {self.build_stats.errors_encountered}
- **Retries Performed**: {self.build_stats.retries_performed}

## Cost Analysis

### Total Costs
- **Total Cost**: ${self.cost_tracker.total_cost:.2f}
- **Claude Code Execution**: ${self.cost_tracker.claude_code_cost:.2f}
- **Research Phase**: ${self.cost_tracker.research_cost:.2f}
- **Analysis & Other**: ${self.cost_tracker.total_cost - self.cost_tracker.claude_code_cost - self.cost_tracker.research_cost:.2f}

### Cost by Model
"""
        
        for breakdown in self.cost_tracker.get_model_breakdown():
            if "model" in breakdown:
                report += f"- **{breakdown['model']}**: ${breakdown.get('cost', 0):.2f}\n"
        
        report += """
## Code Metrics

"""
        
        stats = self.build_stats.get_summary()
        
        report += f"- **Total Files**: {stats['files']['created']}\n"
        report += f"- **Lines of Code**: {stats['code']['lines']:,}\n"
        report += f"- **Functions Created**: {stats['code']['functions']}\n"
        report += f"- **Classes Created**: {stats['code']['classes']}\n"
        
        report += "\n### File Types\n"
        for ext, count in sorted(stats['files']['types'].items(), key=lambda x: x[1], reverse=True)[:10]:
            report += f"- `{ext}`: {count} files\n"
        
        report += "\n## Tool Usage\n\n"
        
        # Top tools by usage
        report += "### Most Used Tools\n"
        for tool, count in self.build_stats.tool_calls.most_common(10):
            success_rate = self.build_stats.tool_success_rate.get(tool, 1.0)
            report += f"- **{tool}**: {count} calls ({success_rate:.1%} success rate)\n"
        
        # MCP server usage
        if self.build_stats.mcp_calls > 0:
            report += "\n### MCP Server Usage\n"
            mcp_usage = defaultdict(int)
            for tool in self.build_stats.tool_calls:
                if tool.startswith("mcp__"):
                    parts = tool.split("__")
                    if len(parts) >= 2:
                        mcp_usage[parts[1]] += self.build_stats.tool_calls[tool]
            
            for server, count in sorted(mcp_usage.items(), key=lambda x: x[1], reverse=True):
                report += f"- **{server}**: {count} calls\n"
        
        return report
    
    async def _create_deployment_guide(self):
        """Create deployment guide based on project analysis"""
        guide_content = f"""# Deployment Guide

This guide provides instructions for deploying the {self.memory.project_name if self.memory else 'application'}.

## Prerequisites

"""
        
        # Add technology-specific prerequisites
        if hasattr(self, '_tech_stack'):
            for tech in self._tech_stack:
                if tech == "python":
                    guide_content += "- Python 3.8 or higher\n"
                elif tech == "javascript":
                    guide_content += "- Node.js 16.x or higher\n"
                elif tech == "docker":
                    guide_content += "- Docker 20.x or higher\n"
                elif tech == "kubernetes":
                    guide_content += "- Kubernetes cluster (1.20+)\n"
        
        guide_content += """
## Environment Setup

1. **Clone the repository** (if using git):
   ```bash
   git clone <repository-url>
   cd """ + self.args.output_dir.name + """
   ```

2. **Install dependencies**:
"""
        
        # Add dependency installation based on files created
        if self.memory:
            if any("requirements.txt" in f for f in self.memory.created_files):
                guide_content += """   ```bash
   pip install -r requirements.txt
   ```
"""
            if any("package.json" in f for f in self.memory.created_files):
                guide_content += """   ```bash
   npm install
   # or
   yarn install
   ```
"""
        
        guide_content += """
3. **Configure environment variables**:
   - Copy `.env.example` to `.env`
   - Update values according to your environment

## Deployment Options

### Option 1: Local Development
```bash
# Start the development server
"""
        
        # Add start commands based on project type
        if hasattr(self, '_project_type'):
            if "api" in self._project_type:
                guide_content += "python main.py  # or: npm start\n"
            elif "web" in self._project_type:
                guide_content += "npm run dev  # or: python manage.py runserver\n"
        
        guide_content += """```

### Option 2: Docker Deployment
```bash
# Build the Docker image
docker build -t """ + self.args.output_dir.name + """ .

# Run the container
docker run -p 8080:8080 --env-file .env """ + self.args.output_dir.name + """
```

### Option 3: Production Deployment

#### Cloud Platforms
- **AWS**: Use Elastic Beanstalk, ECS, or Lambda
- **Google Cloud**: Use App Engine, Cloud Run, or GKE
- **Azure**: Use App Service or AKS
- **Heroku**: Use Heroku CLI or GitHub integration

#### Container Orchestration
If using Kubernetes:
```bash
kubectl apply -f k8s/
```

## Post-Deployment

1. **Verify deployment**:
   - Check health endpoints
   - Review logs for errors
   - Test core functionality

2. **Monitor**:
   - Set up monitoring dashboards
   - Configure alerts
   - Review performance metrics

3. **Backup**:
   - Set up automated backups
   - Test restore procedures

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change the port in configuration
2. **Database connection**: Verify connection strings
3. **Missing dependencies**: Re-run dependency installation
4. **Permission errors**: Check file and directory permissions

### Logs

Check logs in:
- Application logs: `./logs/`
- Docker logs: `docker logs <container-id>`
- System logs: `/var/log/`

## Security Checklist

- [ ] Change default passwords
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up intrusion detection
- [ ] Enable audit logging
- [ ] Regular security updates

## Support

For issues or questions:
- Review the documentation in `/docs`
- Check the project README
- Review error messages in logs

---
Generated by Claude Code Builder v2.3.0
"""
        
        # Save deployment guide
        guide_path = self.args.output_dir / "DEPLOYMENT_GUIDE.md"
        with open(guide_path, 'w') as f:
            f.write(guide_content)
        
        self.logger.info("Created deployment guide")
    
    def _final_git_commit(self):
        """Create final git commit with summary"""
        try:
            # Add any uncommitted changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.args.output_dir,
                check=True,
                capture_output=True
            )
            
            # Check if there are changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.args.output_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            if not status_result.stdout.strip():
                return
            
            # Create comprehensive final commit
            commit_msg = "Final: Project build completed\n\n"
            commit_msg += f"Builder: Claude Code Builder v2.3.0\n"
            commit_msg += f"Build ID: {self.memory.build_id if self.memory else 'unknown'}\n"
            commit_msg += f"Duration: {str(datetime.now() - self.start_time).split('.')[0]}\n"
            commit_msg += f"\nStatistics:\n"
            commit_msg += f"- Phases completed: {len([p for p in self.memory.phases if p.completed]) if self.memory else 0}\n"
            commit_msg += f"- Files created: {self.build_stats.files_created}\n"
            commit_msg += f"- Lines of code: {self.build_stats.lines_of_code:,}\n"
            commit_msg += f"- Total cost: ${self.cost_tracker.total_cost:.2f}\n"
            
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.args.output_dir,
                check=True,
                capture_output=True
            )
            
            self.logger.info("Created final git commit")
            
        except Exception as e:
            self.logger.debug(f"Final commit failed: {e}")
    
    async def _validate_project(self) -> bool:
        """Enhanced project validation with detailed checks"""
        self.logger.info("Running comprehensive project validation...")
        
        validations = []
        
        # Define validation checks with categories
        validation_categories = {
            "Structure": [
                ("Entry Point", self._check_entry_point, True),
                ("Package Structure", self._check_package_structure, False),
                ("Directory Organization", self._check_directory_structure, False)
            ],
            "Dependencies": [
                ("Dependency File", self._check_dependencies_file, True),
                ("Lock File", self._check_lock_file, False),
                ("Version Constraints", self._check_version_constraints, False)
            ],
            "Code Quality": [
                ("No TODOs", self._check_no_todos, False),
                ("Error Handling", self._check_error_handling, True),
                ("Logging", self._check_logging, False)
            ],
            "Testing": [
                ("Test Directory", self._check_tests, False),
                ("Test Coverage", self._check_test_coverage, False),
                ("Test Configuration", self._check_test_config, False)
            ],
            "Documentation": [
                ("README", self._check_documentation, False),
                ("API Documentation", self._check_api_docs, False),
                ("Code Comments", self._check_code_comments, False)
            ],
            "Configuration": [
                ("Environment Config", self._check_configuration, False),
                ("Example Config", self._check_example_config, True),
                ("Config Validation", self._check_config_validation, False)
            ],
            "Security": [
                ("No Hardcoded Secrets", self._check_security, True),
                ("Auth Implementation", self._check_authentication, False),
                ("Input Validation", self._check_input_validation, False)
            ],
            "Deployment": [
                ("Docker Support", self._check_docker, False),
                ("CI/CD Config", self._check_cicd, False),
                ("Health Checks", self._check_health_checks, False)
            ]
        }
        
        # Run validation checks
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            total_checks = sum(len(checks) for checks in validation_categories.values())
            task = progress.add_task("Validating project...", total=total_checks)
            
            for category, checks in validation_categories.items():
                for name, check_func, critical in checks:
                    progress.update(task, description=f"Checking {name}...")
                    
                    try:
                        passed, details = check_func()
                        validations.append({
                            "category": category,
                            "name": name,
                            "passed": passed,
                            "details": details,
                            "critical": critical
                        })
                    except Exception as e:
                        validations.append({
                            "category": category,
                            "name": name,
                            "passed": False,
                            "details": f"Check failed: {str(e)}",
                            "critical": critical
                        })
                    
                    progress.advance(task)
        
        # Display results
        self._display_validation_results(validations)
        
        # Save validation report
        await self._save_validation_report(validations)
        
        # Return overall result
        critical_failed = any(v["critical"] and not v["passed"] for v in validations)
        return not critical_failed
    
    def _check_entry_point(self) -> Tuple[bool, str]:
        """Check for main entry point with better detection"""
        entry_points = [
            "main.py", "app.py", "__main__.py", "cli.py", "run.py", "server.py",
            "index.js", "index.ts", "app.js", "server.js", "main.js",
            "main.go", "main.rs", "Main.java", "main.cpp", "main.c"
        ]
        
        for entry in entry_points:
            entry_path = self.args.output_dir / entry
            if entry_path.exists():
                # Check if it's a valid entry point
                try:
                    content = entry_path.read_text()
                    if ("if __name__" in content or 
                        "def main" in content or 
                        "function main" in content or
                        "export" in content or
                        "listen" in content):
                        return True, f"Found entry point: {entry}"
                except:
                    pass
        
        # Check for package.json scripts
        package_json = self.args.output_dir / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text())
                if "scripts" in data and ("start" in data["scripts"] or "main" in data):
                    return True, "Entry point defined in package.json"
            except:
                pass
        
        return False, "No entry point found"
    
    def _check_package_structure(self) -> Tuple[bool, str]:
        """Check package structure"""
        indicators = {
            "Python": ["__init__.py", "setup.py", "pyproject.toml"],
            "Node.js": ["package.json"],
            "Go": ["go.mod"],
            "Rust": ["Cargo.toml"],
            "Java": ["pom.xml", "build.gradle"]
        }
        
        for lang, files in indicators.items():
            for file in files:
                if (self.args.output_dir / file).exists():
                    return True, f"Valid {lang} package structure"
        
        # Check for src directory
        if (self.args.output_dir / "src").exists():
            return True, "Source directory structure found"
        
        return False, "No standard package structure found"
    
    def _check_directory_structure(self) -> Tuple[bool, str]:
        """Check directory organization"""
        expected_dirs = ["src", "tests", "docs", "config", "scripts", "lib", "app"]
        found_dirs = []
        
        for dir_name in expected_dirs:
            if (self.args.output_dir / dir_name).exists():
                found_dirs.append(dir_name)
        
        if len(found_dirs) >= 2:
            return True, f"Good directory structure: {', '.join(found_dirs)}"
        elif found_dirs:
            return True, f"Basic directory structure: {', '.join(found_dirs)}"
        else:
            return False, "No organized directory structure"
    
    def _check_dependencies_file(self) -> Tuple[bool, str]:
        """Check for dependency files"""
        dep_files = {
            "requirements.txt": "Python (pip)",
            "pyproject.toml": "Python (modern)",
            "package.json": "Node.js",
            "Gemfile": "Ruby",
            "go.mod": "Go",
            "Cargo.toml": "Rust",
            "pom.xml": "Java (Maven)",
            "build.gradle": "Java (Gradle)"
        }
        
        for file, lang in dep_files.items():
            file_path = self.args.output_dir / file
            if file_path.exists():
                try:
                    # Validate it's not empty
                    content = file_path.read_text()
                    if len(content.strip()) > 10:
                        return True, f"{lang} dependencies: {file}"
                except:
                    pass
        
        return False, "No dependency file found"
    
    def _check_lock_file(self) -> Tuple[bool, str]:
        """Check for dependency lock files"""
        lock_files = [
            "requirements.lock", "poetry.lock", "Pipfile.lock",
            "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            "Gemfile.lock", "go.sum", "Cargo.lock"
        ]
        
        for lock_file in lock_files:
            if (self.args.output_dir / lock_file).exists():
                return True, f"Lock file present: {lock_file}"
        
        return False, "No dependency lock file"
    
    def _check_version_constraints(self) -> Tuple[bool, str]:
        """Check version constraints in dependencies"""
        # Check package.json
        package_json = self.args.output_dir / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text())
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                # Check if versions are properly constrained
                unconstrained = [k for k, v in deps.items() if v == "*" or v == "latest"]
                if unconstrained:
                    return False, f"Unconstrained versions: {', '.join(unconstrained[:3])}"
                elif deps:
                    return True, "All dependencies have version constraints"
            except:
                pass
        
        # Check requirements.txt
        req_file = self.args.output_dir / "requirements.txt"
        if req_file.exists():
            try:
                lines = req_file.read_text().splitlines()
                versioned = sum(1 for line in lines if "==" in line or ">=" in line)
                if versioned > len(lines) * 0.8:
                    return True, "Most dependencies have version constraints"
            except:
                pass
        
        return False, "Version constraints not properly specified"
    
    def _check_no_todos(self) -> Tuple[bool, str]:
        """Check for TODO comments"""
        todo_count = 0
        files_with_todos = []
        
        code_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c'}
        
        for file_path in self.args.output_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in code_extensions:
                try:
                    content = file_path.read_text(errors='ignore')
                    todos = len(re.findall(r'\b(TODO|FIXME|XXX|HACK)\b', content, re.IGNORECASE))
                    if todos > 0:
                        todo_count += todos
                        files_with_todos.append(file_path.name)
                except:
                    pass
        
        if todo_count == 0:
            return True, "No TODOs found"
        else:
            return False, f"Found {todo_count} TODOs in {len(files_with_todos)} files"
    
    def _check_error_handling(self) -> Tuple[bool, str]:
        """Check for error handling patterns"""
        error_patterns = [
            r'try\s*:',  # Python
            r'except\s+',  # Python
            r'try\s*\{',  # JavaScript/Java
            r'catch\s*\(',  # JavaScript/Java
            r'\.catch\(',  # Promise
            r'if\s+err\s*!=\s*nil',  # Go
            r'Result<',  # Rust
            r'panic!',  # Rust
        ]
        
        error_handling_found = False
        files_checked = 0
        
        for file_path in self.args.output_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in {'.py', '.js', '.ts', '.java', '.go', '.rs'}:
                files_checked += 1
                try:
                    content = file_path.read_text(errors='ignore')
                    for pattern in error_patterns:
                        if re.search(pattern, content):
                            error_handling_found = True
                            break
                except:
                    pass
                
                if files_checked > 20:  # Sample check
                    break
        
        if error_handling_found:
            return True, "Error handling patterns found"
        else:
            return False, "No error handling patterns detected"
    
    def _check_logging(self) -> Tuple[bool, str]:
        """Check for logging implementation"""
        logging_patterns = [
            r'import\s+logging',  # Python
            r'console\.(log|error|warn)',  # JavaScript
            r'logger\.',  # General
            r'log\.',  # General
            r'winston',  # Node.js
            r'pino',  # Node.js
            r'logrus',  # Go
            r'slog',  # Go
        ]
        
        logging_found = False
        
        for file_path in self.args.output_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in {'.py', '.js', '.ts', '.go', '.java'}:
                try:
                    content = file_path.read_text(errors='ignore')
                    for pattern in logging_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            logging_found = True
                            return True, "Logging implementation found"
                except:
                    pass
        
        return False, "No logging implementation found"
    
    def _check_tests(self) -> Tuple[bool, str]:
        """Enhanced test checking"""
        test_dirs = ["tests", "test", "__tests__", "spec", "test_suite"]
        test_files_patterns = ["test_*.py", "*_test.py", "*.test.js", "*.spec.js", "*_test.go"]
        
        for test_dir in test_dirs:
            test_path = self.args.output_dir / test_dir
            if test_path.exists() and test_path.is_dir():
                # Count test files
                test_count = 0
                for pattern in test_files_patterns:
                    test_count += len(list(test_path.rglob(pattern)))
                
                if test_count > 0:
                    return True, f"{test_count} test files in {test_dir}/"
                else:
                    return False, f"{test_dir}/ exists but contains no test files"
        
        return False, "No test directory found"
    
    def _check_test_coverage(self) -> Tuple[bool, str]:
        """Check for test coverage configuration"""
        coverage_files = [
            ".coveragerc", "coverage.xml", "coverage.json",
            "jest.config.js", "vitest.config.js",
            ".nycrc", "karma.conf.js"
        ]
        
        for cov_file in coverage_files:
            if (self.args.output_dir / cov_file).exists():
                return True, f"Coverage configuration: {cov_file}"
        
        # Check package.json for coverage scripts
        package_json = self.args.output_dir / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text())
                scripts = data.get("scripts", {})
                if any("coverage" in script for script in scripts.values()):
                    return True, "Coverage script in package.json"
            except:
                pass
        
        return False, "No test coverage configuration"
    
    def _check_test_config(self) -> Tuple[bool, str]:
        """Check for test configuration files"""
        test_configs = [
            "pytest.ini", "tox.ini", ".pytest.ini",
            "jest.config.js", "vitest.config.js",
            "mocha.opts", ".mocharc.json",
            "phpunit.xml", "rspec.yml"
        ]
        
        for config in test_configs:
            if (self.args.output_dir / config).exists():
                return True, f"Test configuration: {config}"
        
        return False, "No test configuration file"
    
    def _check_documentation(self) -> Tuple[bool, str]:
        """Check for documentation"""
        doc_files = ["README.md", "README.rst", "README.txt"]
        
        for doc_file in doc_files:
            doc_path = self.args.output_dir / doc_file
            if doc_path.exists():
                try:
                    content = doc_path.read_text()
                    # Check if it's substantial
                    if len(content) > 500:
                        sections = len(re.findall(r'^#+\s+', content, re.MULTILINE))
                        return True, f"{doc_file} with {sections} sections ({len(content)} chars)"
                    else:
                        return False, f"{doc_file} exists but minimal content"
                except:
                    pass
        
        # Check for docs directory
        docs_dir = self.args.output_dir / "docs"
        if docs_dir.exists() and any(docs_dir.iterdir()):
            return True, "Documentation directory with content"
        
        return False, "No documentation found"
    
    def _check_api_docs(self) -> Tuple[bool, str]:
        """Check for API documentation"""
        api_doc_files = [
            "openapi.yaml", "openapi.json", "swagger.yaml", "swagger.json",
            "api.md", "API.md", "api-docs.md"
        ]
        
        for doc_file in api_doc_files:
            if (self.args.output_dir / doc_file).exists():
                return True, f"API documentation: {doc_file}"
        
        # Check for inline API docs (docstrings)
        if (self.args.output_dir / "docs" / "api").exists():
            return True, "API documentation directory"
        
        return False, "No API documentation"
    
    def _check_code_comments(self) -> Tuple[bool, str]:
        """Check code comment density"""
        total_lines = 0
        comment_lines = 0
        files_analyzed = 0
        
        comment_patterns = [
            r'^\s*#',  # Python, Shell
            r'^\s*//',  # C-style
            r'^\s*/\*',  # C-style block
            r'^\s*\*',  # C-style block cont
        ]
        
        for file_path in self.args.output_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in {'.py', '.js', '.ts', '.java', '.go'}:
                files_analyzed += 1
                try:
                    lines = file_path.read_text(errors='ignore').splitlines()
                    total_lines += len(lines)
                    
                    for line in lines:
                        if any(re.match(pattern, line) for pattern in comment_patterns):
                            comment_lines += 1
                except:
                    pass
                
                if files_analyzed > 50:  # Sample size
                    break
        
        if total_lines > 0:
            comment_ratio = comment_lines / total_lines
            if comment_ratio > 0.1:
                return True, f"Good comment coverage ({comment_ratio:.1%})"
            else:
                return False, f"Low comment coverage ({comment_ratio:.1%})"
        
        return False, "Could not analyze comments"
    
    def _check_configuration(self) -> Tuple[bool, str]:
        """Check for configuration files"""
        config_files = [
            "config.py", "config.js", "config.yaml", "config.json",
            "settings.py", "settings.json", ".env", "app.config.js",
            "config/", "configs/"
        ]
        
        for config in config_files:
            config_path = self.args.output_dir / config
            if config_path.exists():
                if config_path.is_file():
                    return True, f"Configuration file: {config}"
                else:
                    return True, f"Configuration directory: {config}"
        
        return False, "No configuration files"
    
    def _check_example_config(self) -> Tuple[bool, str]:
        """Check for example configuration"""
        example_configs = [
            ".env.example", ".env.sample", ".env.template",
            "config.example.js", "config.sample.yaml"
        ]
        
        for example in example_configs:
            if (self.args.output_dir / example).exists():
                return True, f"Example configuration: {example}"
        
        return False, "No example configuration file"
    
    def _check_config_validation(self) -> Tuple[bool, str]:
        """Check for configuration validation"""
        validation_patterns = [
            r'config\.validate',
            r'validateConfig',
            r'checkConfig',
            r'assert.*config',
            r'ConfigSchema',
            r'env\.required'
        ]
        
        for file_path in self.args.output_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in {'.py', '.js', '.ts'}:
                try:
                    content = file_path.read_text(errors='ignore')
                    for pattern in validation_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            return True, "Configuration validation found"
                except:
                    pass
        
        return False, "No configuration validation"
    
    def _check_security(self) -> Tuple[bool, str]:
        """Enhanced security checking"""
        # Patterns that indicate potential security issues
        suspicious_patterns = [
            (r'(?i)(api[-_]?key|apikey)\s*[:=]\s*["\'][^"\']+["\']', "API key"),
            (r'(?i)(secret[-_]?key|secret)\s*[:=]\s*["\'][^"\']+["\']', "Secret key"),
            (r'(?i)password\s*[:=]\s*["\'][^"\']+["\']', "Password"),
            (r'(?i)(aws[-_]?access[-_]?key|aws[-_]?secret)\s*[:=]\s*["\'][^"\']+["\']', "AWS credentials"),
            (r'(?i)bearer\s+[a-zA-Z0-9\-._~+/]+', "Bearer token"),
            (r'-----BEGIN (RSA )?PRIVATE KEY-----', "Private key")
        ]
        
        issues_found = []
        
        # Files to check
        code_files = list(self.args.output_dir.rglob("*.py")) + \
                    list(self.args.output_dir.rglob("*.js")) + \
                    list(self.args.output_dir.rglob("*.ts")) + \
                    list(self.args.output_dir.rglob("*.env"))
        
        for code_file in code_files[:20]:  # Check first 20 files
            if code_file.name in [".env.example", ".env.sample", ".env.template"]:
                continue  # Skip example files
                
            try:
                content = code_file.read_text(errors='ignore')
                for pattern, issue_type in suspicious_patterns:
                    if re.search(pattern, content):
                        issues_found.append((code_file.name, issue_type))
                        break
            except:
                pass
        
        if issues_found:
            issue_summary = ", ".join(f"{file}: {issue}" for file, issue in issues_found[:3])
            return False, f"Potential secrets found: {issue_summary}"
        
        return True, "No hardcoded secrets detected"
    
    def _check_authentication(self) -> Tuple[bool, str]:
        """Check for authentication implementation"""
        auth_patterns = [
            r'(?i)authenticate',
            r'(?i)authorization',
            r'(?i)jwt|oauth|session',
            r'(?i)login|signin',
            r'(?i)@auth|@authenticated',
            r'(?i)requireAuth|require_auth'
        ]
        
        auth_found = False
        
        for file_path in self.args.output_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in {'.py', '.js', '.ts', '.java'}:
                try:
                    content = file_path.read_text(errors='ignore')
                    for pattern in auth_patterns:
                        if re.search(pattern, content):
                            auth_found = True
                            return True, "Authentication implementation found"
                except:
                    pass
        
        return False, "No authentication implementation found"
    
    def _check_input_validation(self) -> Tuple[bool, str]:
        """Check for input validation"""
        validation_patterns = [
            r'(?i)validate|validator',
            r'(?i)sanitize|escape',
            r'(?i)schema\.(parse|validate)',
            r'(?i)joi\.|yup\.|zod\.',  # JS validation libraries
            r'(?i)pydantic|marshmallow',  # Python validation
            r'(?i)@Valid|@NotNull|@Size',  # Java annotations
        ]
        
        for file_path in self.args.output_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in {'.py', '.js', '.ts', '.java'}:
                try:
                    content = file_path.read_text(errors='ignore')
                    for pattern in validation_patterns:
                        if re.search(pattern, content):
                            return True, "Input validation found"
                except:
                    pass
        
        return False, "No input validation found"
    
    def _check_docker(self) -> Tuple[bool, str]:
        """Check for Docker support"""
        dockerfile = self.args.output_dir / "Dockerfile"
        docker_compose = self.args.output_dir / "docker-compose.yml"
        
        if dockerfile.exists():
            try:
                content = dockerfile.read_text()
                # Check if it's a multi-stage build
                if content.count("FROM") > 1:
                    return True, "Multi-stage Dockerfile present"
                else:
                    return True, "Dockerfile present"
            except:
                pass
        
        if docker_compose.exists():
            return True, "Docker Compose configuration present"
        
        return False, "No Docker configuration"
    
    def _check_cicd(self) -> Tuple[bool, str]:
        """Check for CI/CD configuration"""
        cicd_files = [
            ".github/workflows",
            ".gitlab-ci.yml",
            "Jenkinsfile",
            ".circleci/config.yml",
            ".travis.yml",
            "azure-pipelines.yml",
            "bitbucket-pipelines.yml"
        ]
        
        for cicd in cicd_files:
            cicd_path = self.args.output_dir / cicd
            if cicd_path.exists():
                return True, f"CI/CD configuration: {cicd}"
        
        return False, "No CI/CD configuration"
    
    def _check_health_checks(self) -> Tuple[bool, str]:
        """Check for health check endpoints"""
        health_patterns = [
            r'["\']/(health|healthz|alive|ready)["\']',
            r'health_check|healthcheck',
            r'@app\.route.*health',
            r'router\.(get|post).*health'
        ]
        
        for file_path in self.args.output_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in {'.py', '.js', '.ts', '.go'}:
                try:
                    content = file_path.read_text(errors='ignore')
                    for pattern in health_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            return True, "Health check endpoints found"
                except:
                    pass
        
        return False, "No health check endpoints"
    
    def _display_validation_results(self, validations: List[Dict[str, Any]]):
        """Display enhanced validation results"""
        # Group by category
        by_category = defaultdict(list)
        for validation in validations:
            by_category[validation["category"]].append(validation)
        
        # Create summary
        total_passed = sum(1 for v in validations if v["passed"])
        total_critical_passed = sum(1 for v in validations if v["critical"] and v["passed"])
        total_critical = sum(1 for v in validations if v["critical"])
        
        # Summary panel
        summary_text = f"""[bold]Validation Summary[/bold]

Total Checks: {len(validations)}
Passed: {total_passed}/{len(validations)} ({total_passed/len(validations)*100:.1f}%)
Critical: {total_critical_passed}/{total_critical} passed

"""
        
        # Category summaries
        for category, items in by_category.items():
            passed = sum(1 for item in items if item["passed"])
            summary_text += f"{category}: {passed}/{len(items)} passed\n"
        
        self.console.print(Panel(summary_text, title="[bold]Validation Overview[/bold]", box=box.ROUNDED))
        
        # Detailed results by category
        for category, items in by_category.items():
            table = Table(
                title=f"[bold]{category} Validation[/bold]",
                box=box.ROUNDED,
                show_lines=True,
                header_style="bold cyan"
            )
            table.add_column("Check", style="bold")
            table.add_column("Status", justify="center")
            table.add_column("Details", style="dim")
            table.add_column("Type", justify="center")
            
            for validation in items:
                status = "[green]✓[/green]" if validation["passed"] else "[red]✗[/red]"
                type_str = "[red]Critical[/red]" if validation["critical"] else "[yellow]Optional[/yellow]"
                
                table.add_row(
                    validation["name"],
                    status,
                    validation["details"],
                    type_str
                )
            
            self.console.print(table)
            self.console.print()
        
        # Overall result
        all_passed = total_passed == len(validations)
        critical_failed = total_critical_passed < total_critical
        
        if all_passed:
            self.console.print("[bold green]✓ All validation checks passed![/bold green]")
        elif critical_failed:
            self.console.print("[bold red]✗ Critical validation checks failed[/bold red]")
        else:
            failed_count = len(validations) - total_passed
            self.console.print(f"[yellow]⚠ {failed_count} optional validation(s) failed[/yellow]")
    
    async def _save_validation_report(self, validations: List[Dict[str, Any]]):
        """Save validation report"""
        report_path = self.args.output_dir / "VALIDATION_REPORT.md"
        
        report_content = f"""# Validation Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Project: {self.memory.project_name if self.memory else self.args.output_dir.name}

## Summary

- Total Checks: {len(validations)}
- Passed: {sum(1 for v in validations if v["passed"])}
- Failed: {sum(1 for v in validations if not v["passed"])}
- Critical Failed: {sum(1 for v in validations if v["critical"] and not v["passed"])}

## Detailed Results

"""
        
        # Group by category
        by_category = defaultdict(list)
        for validation in validations:
            by_category[validation["category"]].append(validation)
        
        for category, items in sorted(by_category.items()):
            report_content += f"### {category}\n\n"
            
            for validation in items:
                status = "✓" if validation["passed"] else "✗"
                critical = " [CRITICAL]" if validation["critical"] else ""
                report_content += f"- **{validation['name']}**: {status}{critical}\n"
                report_content += f"  - {validation['details']}\n"
            
            report_content += "\n"
        
        # Recommendations
        report_content += "## Recommendations\n\n"
        
        failed_critical = [v for v in validations if v["critical"] and not v["passed"]]
        if failed_critical:
            report_content += "### Critical Issues (Must Fix)\n\n"
            for validation in failed_critical:
                report_content += f"- **{validation['name']}**: {validation['details']}\n"
            report_content += "\n"
        
        failed_optional = [v for v in validations if not v["critical"] and not v["passed"]]
        if failed_optional:
            report_content += "### Optional Improvements\n\n"
            for validation in failed_optional[:10]:  # Top 10
                report_content += f"- **{validation['name']}**: {validation['details']}\n"
        
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        self.logger.info("Saved validation report")
    
    async def _run_project_tests(self):
        """Run project tests with enhanced detection and reporting"""
        self.logger.info("Running project tests...")
        
        # Test runners in order of preference
        test_runners = [
            # Python
            (["pytest", "-v", "--tb=short"], "pytest"),
            (["python", "-m", "pytest", "-v"], "pytest"),
            (["python", "-m", "unittest", "discover"], "unittest"),
            (["tox"], "tox"),
            
            # JavaScript/Node
            (["npm", "test"], "npm"),
            (["yarn", "test"], "yarn"),
            (["pnpm", "test"], "pnpm"),
            (["jest"], "jest"),
            (["vitest"], "vitest"),
            (["mocha"], "mocha"),
            
            # Other languages
            (["go", "test", "./..."], "go"),
            (["cargo", "test"], "rust"),
            (["mvn", "test"], "maven"),
            (["gradle", "test"], "gradle"),
            (["make", "test"], "make"),
        ]
        
        test_executed = False
        
        for cmd, runner_name in test_runners:
            # Check if command is available
            if not shutil.which(cmd[0]):
                continue
            
            # Special handling for npm/yarn/pnpm
            if runner_name in ["npm", "yarn", "pnpm"]:
                # Check if test script exists
                package_json = self.args.output_dir / "package.json"
                if package_json.exists():
                    try:
                        data = json.loads(package_json.read_text())
                        if "test" not in data.get("scripts", {}):
                            continue
                    except:
                        continue
                else:
                    continue
            
            try:
                self.console.print(f"\n[cyan]Running tests with {runner_name}...[/cyan]")
                
                with Status(f"Executing {' '.join(cmd)}...", console=self.console):
                    result = await asyncio.create_subprocess_exec(
                        *cmd,
                        cwd=self.args.output_dir,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await asyncio.wait_for(
                        result.communicate(),
                        timeout=300  # 5 minute timeout
                    )
                
                stdout_text = stdout.decode('utf-8', errors='replace')
                stderr_text = stderr.decode('utf-8', errors='replace')
                
                if result.returncode == 0:
                    self.console.print(f"[green]✓ Tests passed with {runner_name}[/green]")
                    
                    # Try to extract test statistics
                    self._extract_test_stats(stdout_text, runner_name)
                    
                    # Show test output if verbose
                    if self.args.verbose and stdout_text:
                        output_lines = stdout_text.splitlines()
                        preview = '\n'.join(output_lines[-50:])  # Last 50 lines
                        
                        self.console.print(Panel(
                            preview,
                            title="Test Output (last 50 lines)",
                            border_style="green"
                        ))
                else:
                    self.console.print(f"[red]✗ Tests failed with {runner_name} (exit code: {result.returncode})[/red]")
                    self.build_stats.tests_failed += 1
                    
                    # Show error output
                    error_output = stderr_text or stdout_text
                    if error_output:
                        error_lines = error_output.splitlines()
                        # Find relevant error lines
                        relevant_lines = []
                        for i, line in enumerate(error_lines):
                            if any(keyword in line.lower() for keyword in ["error", "failed", "failure", "assert"]):
                                # Include context
                                start = max(0, i - 2)
                                end = min(len(error_lines), i + 3)
                                relevant_lines.extend(error_lines[start:end])
                        
                        if relevant_lines:
                            preview = '\n'.join(relevant_lines[:50])
                        else:
                            preview = '\n'.join(error_lines[-50:])
                        
                        self.console.print(Panel(
                            preview,
                            title="Test Errors",
                            border_style="red"
                        ))
                
                test_executed = True
                break
                
            except asyncio.TimeoutError:
                self.console.print(f"[yellow]⚠ Test timeout with {runner_name}[/yellow]")
            except Exception as e:
                self.logger.warning(f"Failed to run tests with {runner_name}: {e}")
        
        if not test_executed:
            self.console.print("[yellow]⚠ No test runner found or no tests to run[/yellow]")
            self.console.print("[dim]Consider adding tests to your project[/dim]")
    
    def _extract_test_stats(self, output: str, runner_name: str):
        """Extract test statistics from output"""
        # Patterns for different test runners
        patterns = {
            "pytest": [
                r'(\d+) passed',
                r'(\d+) failed',
                r'(\d+) skipped',
                r'(\d+)% coverage'
            ],
            "jest": [
                r'Tests:\s+(\d+) passed',
                r'Tests:.*?(\d+) failed',
                r'Coverage:\s+(\d+(?:\.\d+)?)%'
            ],
            "go": [
                r'PASS.*?(\d+\.\d+)s',
                r'FAIL.*?(\d+\.\d+)s',
                r'coverage:\s+(\d+\.\d+)%'
            ]
        }
        
        # Try to extract stats
        if runner_name in patterns:
            for pattern in patterns[runner_name]:
                match = re.search(pattern, output)
                if match:
                    if "passed" in pattern:
                        self.build_stats.tests_passed += int(match.group(1))
                    elif "failed" in pattern:
                        self.build_stats.tests_failed += int(match.group(1))
                    elif "coverage" in pattern:
                        try:
                            self.build_stats.test_coverage = float(match.group(1))
                        except:
                            pass
    
    def _show_final_report(self):
        """Show comprehensive final build report"""
        self.console.print("\n" + "="*80)
        self.console.print("[bold cyan]BUILD COMPLETE - FINAL REPORT[/bold cyan]")
        self.console.print("="*80 + "\n")
        
        # Build duration
        build_duration = datetime.now() - self.start_time
        
        # Overall status
        if self.memory:
            completed_phases = [p for p in self.memory.phases if p.completed]
            successful_phases = [p for p in completed_phases if p.success]
            
            if len(successful_phases) == len(self.memory.phases):
                overall_status = "[bold green]✓ BUILD SUCCESSFUL[/bold green]"
            elif len(successful_phases) > 0:
                overall_status = "[bold yellow]⚠ BUILD PARTIALLY SUCCESSFUL[/bold yellow]"
            else:
                overall_status = "[bold red]✗ BUILD FAILED[/bold red]"
        else:
            overall_status = "[bold yellow]⚠ BUILD STATUS UNKNOWN[/bold yellow]"
        
        self.console.print(overall_status)
        self.console.print()
        
        # Phase summary
        if self.memory:
            phase_table = Table(
                title="[bold]Phase Execution Summary[/bold]",
                box=box.ROUNDED,
                show_lines=True,
                header_style="bold cyan"
            )
            phase_table.add_column("Phase", style="cyan", width=30)
            phase_table.add_column("Status", justify="center")
            phase_table.add_column("Duration", justify="right")
            phase_table.add_column("Files", justify="center")
            phase_table.add_column("Cost", justify="right")
            
            for phase in self.memory.phases:
                if phase.status == BuildStatus.SUCCESS:
                    status = "[green]✓ Success[/green]"
                elif phase.status == BuildStatus.FAILED:
                    status = "[red]✗ Failed[/red]"
                elif phase.status == BuildStatus.SKIPPED:
                    status = "[yellow]⊘ Skipped[/yellow]"
                else:
                    status = "[dim]- Pending[/dim]"
                
                duration = f"{phase.duration_seconds:.1f}s" if phase.completed else "-"
                files = str(len(phase.files_created)) if phase.files_created else "0"
                
                # Get phase cost
                phase_cost = self.cost_tracker.phase_costs.get(phase.name, 0.0)
                cost = f"${phase_cost:.3f}" if phase_cost > 0 else "-"
                
                phase_table.add_row(phase.name[:30], status, duration, files, cost)
            
            self.console.print(phase_table)
        
        # Build statistics
        stats = self.build_stats.get_summary()
        
        # Create statistics panels
        file_stats = Panel(
            f"""[bold]Files[/bold]
Created: {stats['files']['created']}
Modified: {stats['files']['modified']}
Lines of Code: {stats['code']['lines']:,}
Functions: {stats['code']['functions']}
Classes: {stats['code']['classes']}""",
            title="Code Statistics",
            box=box.ROUNDED
        )
        
        exec_stats = Panel(
            f"""[bold]Execution[/bold]
Commands: {stats['execution']['commands']}
Tool Calls: {stats['tools']['total_calls']}
MCP Calls: {stats['tools']['mcp_calls']}
Errors: {stats['execution']['errors']}
Retries: {stats['execution']['retries']}""",
            title="Execution Statistics",
            box=box.ROUNDED
        )
        
        test_stats = Panel(
            f"""[bold]Testing[/bold]
Tests Written: {stats['testing']['written']}
Tests Passed: {stats['testing']['passed']}
Tests Failed: {stats['testing']['failed']}
Coverage: {stats['testing']['coverage']}""",
            title="Test Statistics",
            box=box.ROUNDED
        )
        
        # Display stats side by side
        self.console.print(Columns([file_stats, exec_stats, test_stats]))
        
        # Cost summary
        cost_summary = self.cost_tracker.get_summary()
        cost_breakdown = self.cost_tracker.get_model_breakdown()
        
        cost_content = []
        cost_content.append(f"[bold]Total Cost:[/bold] ${cost_summary['total_cost']:.2f}")
        cost_content.append(f"[bold]Claude Code:[/bold] ${cost_summary['claude_code_cost']:.2f}")
        if cost_summary['research_cost'] > 0:
            cost_content.append(f"[bold]Research:[/bold] ${cost_summary['research_cost']:.2f}")
        cost_content.append(f"[bold]Analysis:[/bold] ${cost_summary['analysis_cost']:.2f}")
        cost_content.append(f"[bold]Total Tokens:[/bold] {cost_summary['total_tokens']:,}")
        
        # Add top model by cost
        if cost_breakdown:
            top_model = cost_breakdown[0]
            cost_content.append(f"\n[dim]Primary Model: {top_model['model']}[/dim]")
        
        cost_panel = Panel(
            "\n".join(cost_content),
            title="[bold]Cost Analysis[/bold]",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        self.console.print(cost_panel)
        
        # Project location and summary
        summary_panel = Panel(
            f"""[bold]Project:[/bold] {self.memory.project_name if self.memory else self.args.output_dir.name}
[bold]Location:[/bold] {self.args.output_dir.absolute()}
[bold]Build Duration:[/bold] {str(build_duration).split('.')[0]}
[bold]Builder Version:[/bold] Claude Code Builder v2.3.0
[bold]Build ID:[/bold] {self.memory.build_id[:12] if self.memory else 'N/A'}

[bold]Features Used:[/bold]
{"• AI Research" if self.args.enable_research else ""}
{"• MCP Servers (" + str(len(self.available_mcp_servers)) + " active)" if self.available_mcp_servers else ""}
{"• Git Integration" if self.args.git_init else ""}
{"• Automated Testing" if self.args.run_tests else ""}
{"• Project Validation" if self.args.validate else ""}""",
            title="[bold]Build Summary[/bold]",
            box=box.ROUNDED,
            border_style="cyan"
        )
        self.console.print(summary_panel)
        
        # Next steps
        next_steps = []
        
        # Determine next steps based on validation
        if hasattr(self, '_validation_failed') and self._validation_failed:
            next_steps.append("1. Review and fix validation issues (see VALIDATION_REPORT.md)")
        else:
            next_steps.append("1. Review the generated code and documentation")
        
        next_steps.extend([
            "2. Install dependencies (check package.json or requirements.txt)",
            "3. Configure environment variables (see .env.example)",
            "4. Run tests to verify functionality",
            "5. Read PROJECT_SUMMARY.md for detailed information",
            "6. Deploy using DEPLOYMENT_GUIDE.md"
        ])
        
        next_panel = Panel(
            "\n".join(next_steps),
            title="[bold]Next Steps[/bold]",
            box=box.ROUNDED,
            border_style="green"
        )
        self.console.print(next_panel)
        
        # Show any warnings or important notes
        if self.memory and self.memory.error_log:
            self.console.print(f"\n[yellow]⚠ {len(self.memory.error_log)} errors logged during build[/yellow]")
            self.console.print("[dim]Check .analytics/build_stats_*.json for details[/dim]")
    
    async def _export_report(self):
        """Export comprehensive build report"""
        report_dir = self.args.output_dir / ".reports"
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_path = report_dir / f"build-report-{timestamp}.json"
        
        # Gather comprehensive report data
        report_data = {
            "build_id": self.memory.build_id if self.memory else "unknown",
            "timestamp": datetime.now().isoformat(),
            "duration": str(datetime.now() - self.start_time),
            "builder_version": "2.3.0",
            "status": self._determine_build_status(),
            "project": {
                "name": self.memory.project_name if self.memory else self.args.output_dir.name,
                "path": str(self.args.output_dir.absolute()),
                "specification": self.args.spec_file.name,
                "type": getattr(self, '_project_type', 'unknown'),
                "complexity": getattr(self, '_complexity', 'unknown'),
                "technology_stack": getattr(self, '_tech_stack', []),
                "requirements": getattr(self, '_requirements', [])
            },
            "phases": [p.to_dict() for p in self.memory.phases] if self.memory else [],
            "statistics": self.build_stats.get_summary(),
            "costs": self.cost_tracker.get_summary(),
            "cost_breakdown": self.cost_tracker.get_model_breakdown(),
            "mcp_servers": {
                "available": list(self.available_mcp_servers),
                "configurations": self.mcp_server_configs
            },
            "tool_performance": self.tool_manager.get_tool_statistics() if self.tool_manager else None,
            "configuration": {
                "models": {
                    "analyzer": self.args.model_analyzer,
                    "executor": self.args.model_executor,
                    "research": DEFAULT_RESEARCH_MODEL
                },
                "options": {
                    "max_turns": self.args.max_turns,
                    "stream_output": self.args.stream_output,
                    "enable_research": self.args.enable_research,
                    "discover_mcp": self.args.discover_mcp,
                    "auto_confirm": self.args.auto_confirm,
                    "continue_on_error": self.args.continue_on_error,
                    "run_tests": self.args.run_tests,
                    "validate": self.args.validate
                }
            },
            "errors": self.memory.error_log if self.memory else []
        }
        
        # Add research summary if available
        if self.memory and "research_results" in self.memory.context:
            report_data["research"] = {
                "enabled": True,
                "timestamp": self.memory.context.get("research_timestamp"),
                "key_findings": self._summarize_research_findings()
            }
        
        # Add validation results if available
        if hasattr(self, '_validation_results'):
            report_data["validation"] = self._validation_results
        
        # Write report
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Create human-readable summary
        summary_path = report_dir / f"build-summary-{timestamp}.md"
        summary_content = self._create_report_summary(report_data)
        
        with open(summary_path, 'w') as f:
            f.write(summary_content)
        
        self.console.print(f"\n[green]✓ Reports exported to:[/green]")
        self.console.print(f"  - JSON: {report_path}")
        self.console.print(f"  - Summary: {summary_path}")
    
    def _determine_build_status(self) -> str:
        """Determine overall build status"""
        if not self.memory:
            return "unknown"
        
        completed = [p for p in self.memory.phases if p.completed]
        successful = [p for p in completed if p.success]
        
        if len(successful) == len(self.memory.phases):
            return "success"
        elif len(successful) > len(self.memory.phases) * 0.7:
            return "partial_success"
        elif len(successful) > 0:
            return "partial_failure"
        else:
            return "failure"
    
    def _summarize_research_findings(self) -> Dict[str, Any]:
        """Summarize key research findings"""
        if not self.memory or "research_results" not in self.memory.context:
            return {}
        
        research = self.memory.context["research_results"]
        summary = {
            "categories_researched": [],
            "key_recommendations": [],
            "technology_decisions": [],
            "implementation_guidance": []
        }
        
        # Extract key findings
        for category, findings in research.items():
            if isinstance(findings, dict):
                summary["categories_researched"].append(category)
                
                if "recommendations" in findings:
                    summary["key_recommendations"].extend(findings["recommendations"][:3])
                
                if "tools_and_versions" in findings:
                    for tool, version in findings["tools_and_versions"].items():
                        summary["technology_decisions"].append(f"{tool} {version}")
        
        return summary
    
    def _create_report_summary(self, report_data: Dict[str, Any]) -> str:
        """Create human-readable report summary"""
        summary = f"""# Build Report Summary

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Build ID:** {report_data['build_id'][:12]}...
**Status:** {report_data['status'].replace('_', ' ').title()}
**Duration:** {report_data['duration']}

## Project Information

- **Name:** {report_data['project']['name']}
- **Type:** {report_data['project']['type']}
- **Complexity:** {report_data['project']['complexity']}
- **Technology Stack:** {', '.join(report_data['project']['technology_stack'])}

## Build Results

### Phase Summary

| Phase | Status | Duration | Files | Cost |
|-------|--------|----------|-------|------|
"""
        
        for phase in report_data['phases']:
            status = "✓" if phase['success'] else "✗" if phase['completed'] else "○"
            duration = f"{phase['duration_seconds']:.1f}s" if phase['duration_seconds'] else "-"
            files = len(phase['files_created'])
            cost = report_data['costs']['phase_costs'].get(phase['name'], 0)
            
            summary += f"| {phase['name'][:30]} | {status} | {duration} | {files} | ${cost:.3f} |\n"
        
        summary += f"""
### Statistics

- **Files Created:** {report_data['statistics']['files']['created']}
- **Lines of Code:** {report_data['statistics']['code']['lines']:,}
- **Total Tool Calls:** {report_data['statistics']['tools']['total_calls']}
- **Tests Written:** {report_data['statistics']['testing']['written']}

### Cost Analysis

- **Total Cost:** ${report_data['costs']['total_cost']:.2f}
- **Claude Code Execution:** ${report_data['costs']['claude_code_cost']:.2f}
- **Research Phase:** ${report_data['costs']['research_cost']:.2f}
- **Total Tokens:** {report_data['costs']['total_tokens']:,}

## Configuration

- **Analyzer Model:** {report_data['configuration']['models']['analyzer']}
- **Executor Model:** {report_data['configuration']['models']['executor']}
- **MCP Servers:** {len(report_data['mcp_servers']['available'])} active

## Notes

"""
        
        if report_data.get('errors'):
            summary += f"- {len(report_data['errors'])} errors encountered during build\n"
        
        if report_data.get('research', {}).get('enabled'):
            summary += "- AI-powered research was conducted\n"
        
        if report_data['configuration']['options']['run_tests']:
            summary += "- Automated tests were executed\n"
        
        summary += f"\nFor complete details, see the full JSON report."
        
        return summary
    
    async def _handle_interruption(self):
        """Handle graceful interruption with state preservation"""
        self.logger.info("Handling build interruption...")
        
        # Store current state
        if self.memory:
            await self._store_memory("interrupted")
            
            # Show partial report
            self.console.print("\n[yellow]Build interrupted - Partial Report[/yellow]\n")
            
            completed = len([p for p in self.memory.phases if p.completed])
            total = len(self.memory.phases)
            self.console.print(f"Progress: {completed}/{total} phases completed")
            
            if self.memory.created_files:
                self.console.print(f"Files created: {len(self.memory.created_files)}")
            
            self.console.print(f"Partial cost: ${self.cost_tracker.total_cost:.2f}")
        
        self.console.print(f"\nProject location: {self.args.output_dir.absolute()}")
        self.console.print("[yellow]You can resume this build by running the same command[/yellow]")
        self.console.print("[dim]The build will continue from the last completed phase[/dim]")
    
    async def _handle_failure(self, error: Exception):
        """Handle build failure with comprehensive error reporting"""
        self.logger.error(f"Build failed: {str(error)}")
        
        # Store error state
        if self.memory:
            self.memory.context["last_error"] = str(error)
            self.memory.context["error_timestamp"] = datetime.now().isoformat()
            self.memory.context["error_traceback"] = traceback.format_exc()
            self.memory.log_error(str(error), self.memory.current_phase, {
                "type": type(error).__name__,
                "phase": self.memory.current_phase,
                "completed_phases": len(self.memory.completed_phases)
            })
            await self._store_memory("failed")
        
        # Error report
        error_content = [
            f"[red]Error Type:[/red] {type(error).__name__}",
            f"[red]Error Message:[/red] {str(error)}",
            f"[red]Phase:[/red] {self.memory.current_phase if self.memory else 'Unknown'}",
            f"[red]Time:[/red] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        if self.args.debug and self.memory:
            error_content.append(f"\n[dim]Traceback saved to memory[/dim]")
        
        error_panel = Panel(
            "\n".join(error_content),
            title="[bold red]Build Failed[/bold red]",
            box=box.ROUNDED,
            border_style="red",
            padding=(1, 2)
        )
        self.console.print(error_panel)
        
        # Recovery suggestions
        suggestions = [
            "1. Check the error message and logs for details",
            "2. Review the last phase's output and files",
            "3. Fix any issues in your specification or environment",
            "4. Run with --debug for more detailed information",
            "5. Use --continue-on-error to skip failing phases",
            "6. Resume the build after fixing issues"
        ]
        
        recovery_panel = Panel(
            "\n".join(suggestions),
            title="[bold]Recovery Suggestions[/bold]",
            box=box.ROUNDED,
            border_style="yellow"
        )
        self.console.print(recovery_panel)
    
    async def _cleanup(self):
        """Enhanced cleanup with final operations"""
        self.logger.info("Performing cleanup...")
        
        try:
            # Final memory checkpoint
            if self.memory:
                await self._store_memory("final")
            
            # Generate final analytics if not already done
            if not (self.args.output_dir / ".analytics").exists():
                await self._generate_build_analytics()
            
            # Log final statistics
            self.logger.info(f"Build completed in {datetime.now() - self.start_time}")
            self.logger.info(f"Total cost: ${self.cost_tracker.total_cost:.2f}")
            self.logger.info(f"Files created: {self.build_stats.files_created}")
            self.logger.info(f"Lines of code: {self.build_stats.lines_of_code:,}")
            
            # Close any open resources
            # (Anthropic client is managed by context managers)
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        
        self.logger.info("Cleanup complete")


# Main entry point and argument parsing
def create_argument_parser():
    """Create comprehensive argument parser"""
    parser = argparse.ArgumentParser(
        description="Claude Code Builder v2.3.0 - Enhanced Production-Ready Autonomous Project Builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  %(prog)s project-spec.md --output-dir ./my-project

  # With research and MCP discovery
  %(prog)s project-spec.md --output-dir ./my-project --enable-research --discover-mcp

  # Full configuration
  %(prog)s project-spec.md \\
    --output-dir ./my-awesome-app \\
    --api-key $ANTHROPIC_API_KEY \\
    --model-analyzer claude-opus-4-20250514 \\
    --model-executor claude-opus-4-20250514 \\
    --max-turns 30 \\
    --discover-mcp \\
    --enable-research \\
    --auto-confirm \\
    --stream-output \\
    --git-init \\
    --run-tests \\
    --export-report

  # Resume interrupted build
  %(prog)s project-spec.md --output-dir ./my-project --auto-confirm

Environment Variables:
  ANTHROPIC_API_KEY - Your Anthropic API key for research and analysis

Version 2.3.0 Features:
  ✨ Accurate cost tracking from Claude Code execution
  🔬 Enhanced research using Anthropic knowledge base
  🛡️ Improved error handling and automatic recovery
  📊 Detailed analytics and performance tracking
  🔄 Seamless build resumption from any point
  🎯 Context-aware tool optimization
  📝 Comprehensive validation and testing
"""
    )
    
    # Positional arguments
    parser.add_argument(
        'spec_file',
        type=Path,
        help='Project specification file (markdown format)'
    )
    
    # Output configuration
    output_group = parser.add_argument_group('Output Configuration')
    output_group.add_argument(
        '--output-dir', '-o',
        type=Path,
        default=Path('./output'),
        help='Output directory for the project (default: ./output)'
    )
    output_group.add_argument(
        '--git-init',
        action='store_true',
        help='Initialize git repository in output directory'
    )
    
    # Model configuration
    model_group = parser.add_argument_group('Model Configuration')
    model_group.add_argument(
        '--model-analyzer',
        default=DEFAULT_ANALYZER_MODEL,
        help=f'Model for project analysis (default: {DEFAULT_ANALYZER_MODEL})'
    )
    model_group.add_argument(
        '--model-executor',
        default=DEFAULT_EXECUTOR_MODEL,
        help=f'Model for code execution (default: {DEFAULT_EXECUTOR_MODEL})'
    )
    model_group.add_argument(
        '--api-key',
        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)'
    )
    
    # Execution configuration
    exec_group = parser.add_argument_group('Execution Configuration')
    exec_group.add_argument(
        '--max-turns',
        type=int,
        default=30,
        help='Maximum conversation turns per phase (default: 30)'
    )
    exec_group.add_argument(
        '--max-retries',
        type=int,
        default=MAX_RETRIES,
        help=f'Maximum retries for failed phases (default: {MAX_RETRIES})'
    )
    exec_group.add_argument(
        '--continue-on-error',
        action='store_true',
        help='Continue execution even if a phase fails'
    )
    exec_group.add_argument(
        '--auto-confirm',
        action='store_true',
        help='Skip confirmation prompts and auto-resume interrupted builds'
    )
    
    # Enhanced features
    enhanced_group = parser.add_argument_group('Enhanced Features (v2.3)')
    enhanced_group.add_argument(
        '--enable-research',
        action='store_true',
        help='Enable comprehensive AI-powered research phase'
    )
    enhanced_group.add_argument(
        '--discover-mcp',
        action='store_true',
        help='Discover and recommend MCP servers intelligently'
    )
    enhanced_group.add_argument(
        '--auto-install-mcp',
        action='store_true',
        help='Automatically install recommended MCP servers'
    )
    enhanced_group.add_argument(
        '--additional-mcp-servers',
        nargs='+',
        help='Additional MCP servers (format: name:package:description)'
    )
    enhanced_group.add_argument(
        '--additional-tools',
        nargs='+',
        help='Additional tools to allow during execution'
    )
    
    # Phase configuration
    phase_group = parser.add_argument_group('Phase Configuration')
    phase_group.add_argument(
        '--min-phases',
        type=int,
        default=7,
        help='Minimum number of phases to create (default: 7)'
    )
    phase_group.add_argument(
        '--min-tasks-per-phase',
        type=int,
        default=8,
        help='Minimum tasks per phase (default: 8)'
    )
    phase_group.add_argument(
        '--phase-timeout',
        type=int,
        default=600,
        help='Timeout per phase in seconds (default: 600)'
    )
    
    # Output formatting
    format_group = parser.add_argument_group('Output Formatting')
    format_group.add_argument(
        '--stream-output',
        action='store_true',
        default=True,
        help='Stream output in real-time (default: True)'
    )
    format_group.add_argument(
        '--no-stream-output',
        dest='stream_output',
        action='store_false',
        help='Disable streaming output'
    )
    format_group.add_argument(
        '--parse-output',
        action='store_true',
        help='Parse and format streaming output with rich display'
    )
    format_group.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output with additional details'
    )
    format_group.add_argument(
        '--debug',
        action='store_true',
        help='Debug mode with detailed logging and tracebacks'
    )
    
    # Validation and testing
    validation_group = parser.add_argument_group('Validation and Testing')
    validation_group.add_argument(
        '--validate',
        action='store_true',
        default=True,
        help='Validate project after build (default: True)'
    )
    validation_group.add_argument(
        '--no-validate',
        dest='validate',
        action='store_false',
        help='Skip project validation'
    )
    validation_group.add_argument(
        '--run-tests',
        action='store_true',
        help='Run tests after build completion'
    )
    validation_group.add_argument(
        '--test-coverage-threshold',
        type=float,
        default=80.0,
        help='Minimum test coverage percentage (default: 80.0)'
    )
    
    # Logging configuration
    log_group = parser.add_argument_group('Logging Configuration')
    log_group.add_argument(
        '--log-file',
        type=Path,
        help='Log file path (creates parent directories if needed)'
    )
    log_group.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    log_group.add_argument(
        '--save-prompts',
        action='store_true',
        help='Save all prompts for debugging and analysis'
    )
    
    # Reporting
    report_group = parser.add_argument_group('Reporting')
    report_group.add_argument(
        '--export-report',
        action='store_true',
        help='Export detailed build report with analytics'
    )
    report_group.add_argument(
        '--report-format',
        choices=['json', 'markdown', 'both'],
        default='both',
        help='Report format (default: both)'
    )
    
    return parser


async def main():
    """Enhanced main entry point"""
    # Parse arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Set API key from environment if not provided
    if not args.api_key:
        args.api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    # Validate arguments
    if not args.spec_file.exists():
        console = Console()
        console.print(f"[red]Error: Specification file not found: {args.spec_file}[/red]")
        sys.exit(1)
    
    # Create and run builder
    try:
        builder = ClaudeCodeBuilder(args)
        await builder.run()
    except KeyboardInterrupt:
        # Handled within builder
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        console = Console()
        console.print(f"[red]Fatal error: {e}[/red]")
        if args.debug:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print(f"Error: Python 3.8+ required, found {sys.version}")
        sys.exit(1)
    
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBuild interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)