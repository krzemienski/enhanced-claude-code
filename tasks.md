# Claude Code Builder v2.3.0 - Detailed Task Breakdown

## Phase 1: Project Foundation and Package Structure

### Package Structure Creation
1. **Create main package directory**
   ```bash
   claude_code_builder/
   ├── __init__.py
   ├── __main__.py
   ├── cli.py
   ├── main.py
   └── [subdirectories]
   ```

2. **Create claude_code_builder/__init__.py**
   ```python
   """Claude Code Builder - Autonomous project builder using Claude Code SDK."""
   __version__ = "2.3.0"
   __author__ = "Claude Code Builder Team"
   __all__ = ["ClaudeCodeBuilder", "__version__"]
   ```

3. **Create claude_code_builder/__main__.py**
   ```python
   """Entry point for python -m claude_code_builder."""
   from claude_code_builder.cli import main
   
   if __name__ == "__main__":
       main()
   ```

4. **Create setup.py**
   ```python
   from setuptools import setup, find_packages
   
   setup(
       name="claude-code-builder",
       version="2.3.0",
       packages=find_packages(),
       entry_points={
           "console_scripts": [
               "claude-code-builder=claude_code_builder.cli:main",
           ],
       },
       install_requires=[
           "anthropic>=0.18.0",
           "rich>=13.0.0",
           "click>=8.0.0",
           # ... all dependencies
       ],
   )
   ```

5. **Create requirements.txt**
   ```
   anthropic>=0.18.0
   rich>=13.0.0
   aiofiles>=23.0.0
   click>=8.0.0
   httpx>=0.24.0
   tenacity>=8.2.0
   prompt-toolkit>=3.0.0
   GitPython>=3.1.0
   psutil>=5.9.0
   pydantic>=2.0.0
   ```

### Subdirectory Structure
6. **Create all package subdirectories**
   - claude_code_builder/models/
   - claude_code_builder/mcp/
   - claude_code_builder/research/
   - claude_code_builder/execution/
   - claude_code_builder/ui/
   - claude_code_builder/validation/
   - claude_code_builder/utils/
   - claude_code_builder/instructions/

7. **Create __init__.py for each subdirectory**
   ```python
   # claude_code_builder/models/__init__.py
   """Data models for Claude Code Builder."""
   
   # claude_code_builder/mcp/__init__.py
   """Model Context Protocol server management."""
   
   # ... etc for each package
   ```

### Basic CLI Structure
8. **Create claude_code_builder/cli.py**
   ```python
   import click
   from pathlib import Path
   from typing import Optional
   
   @click.command()
   @click.argument('spec_file', type=click.Path(exists=True))
   @click.option('--output-dir', '-o', default='./output', help='Output directory')
   @click.option('--model-analyzer', default='claude-opus-4-20250514')
   @click.option('--model-executor', default='claude-opus-4-20250514')
   # ... all 30+ options
   def main(spec_file: str, output_dir: str, **kwargs):
       """Build projects autonomously using Claude Code SDK."""
       click.echo("Claude Code Builder v2.3.0")
       # Placeholder for now
   ```

9. **Create claude_code_builder/main.py skeleton**
   ```python
   from pathlib import Path
   from typing import Dict, Any
   
   class ClaudeCodeBuilder:
       """Main orchestrator for autonomous project building."""
       
       def __init__(self, spec_file: Path, output_dir: Path, **options):
           self.spec_file = spec_file
           self.output_dir = output_dir
           self.options = options
           
       def run(self):
           """Run the build process."""
           pass  # To be implemented
   ```

### Project Files
10. **Create README.md**
    ```markdown
    # Claude Code Builder v2.3.0
    
    An enhanced production-ready autonomous multi-phase project builder that orchestrates Claude Code SDK.
    
    ## Installation
    ```

11. **Create .gitignore**
    ```
    __pycache__/
    *.py[cod]
    *$py.class
    *.so
    .Python
    build/
    dist/
    *.egg-info/
    .env
    .venv/
    .claude_outputs/
    .metrics/
    *.log
    .mypy_cache/
    .pytest_cache/
    ```

12. **Create examples directory structure**
    - examples/simple-api-spec.md
    - examples/web-app-spec.md
    - examples/cli-tool-spec.md
    - examples/microservice-spec.md

## Phase 2: Data Models and Types

### Core Enumerations
1. **Create claude_code_builder/models/build_status.py**
   ```python
   from enum import Enum
   
   class BuildStatus(Enum):
       """Status of a build or phase."""
       PENDING = "pending"
       RUNNING = "running"
       SUCCESS = "success"
       FAILED = "failed"
       SKIPPED = "skipped"
       CANCELLED = "cancelled"
       RETRYING = "retrying"
       
       def __str__(self) -> str:
           return self.value
   ```

2. **Create claude_code_builder/models/tool_call.py**
   ```python
   from dataclasses import dataclass, field
   from typing import Dict, Any, Optional
   from datetime import datetime
   from rich.panel import Panel
   from rich.text import Text
   
   @dataclass
   class ToolCall:
       """Represents a tool call during execution."""
       name: str
       arguments: Dict[str, Any]
       start_time: float
       end_time: Optional[float] = None
       result: Optional[str] = None
       error: Optional[str] = None
       
       @property
       def duration(self) -> float:
           """Calculate duration in seconds."""
           if self.end_time:
               return self.end_time - self.start_time
           return 0.0
       
       @property
       def is_mcp_tool(self) -> bool:
           """Check if this is an MCP tool."""
           return self.name.startswith('mcp__')
       
       def __rich__(self) -> Panel:
           """Rich representation for display."""
           # Implementation here
   ```

3. **Create claude_code_builder/models/build_stats.py**
   ```python
   from dataclasses import dataclass, field
   from typing import List, Dict, Any
   from collections import defaultdict
   
   @dataclass
   class BuildStats:
       """Comprehensive build statistics tracking."""
       files_created: int = 0
       files_modified: int = 0
       directories_created: int = 0
       lines_written: int = 0
       functions_created: int = 0
       classes_created: int = 0
       tool_calls: List[ToolCall] = field(default_factory=list)
       errors: List[Dict[str, Any]] = field(default_factory=list)
       warnings: List[str] = field(default_factory=list)
       
       # Add 10+ more fields
       
       def increment_file_created(self, path: str):
           """Increment file creation counter."""
           
       def add_tool_call(self, tool_call: ToolCall):
           """Add a tool call to statistics."""
   ```

4. **Create claude_code_builder/models/cost_tracker.py**
   ```python
   from dataclasses import dataclass, field
   from typing import Dict
   from claude_code_builder.utils.constants import TOKEN_COSTS
   
   @dataclass
   class CostTracker:
       """Track API usage costs."""
       total_input_tokens: int = 0
       total_output_tokens: int = 0
       costs_by_model: Dict[str, float] = field(default_factory=dict)
       costs_by_phase: Dict[str, float] = field(default_factory=dict)
       
       def add_tokens(self, model: str, input_tokens: int, output_tokens: int):
           """Add token usage and calculate cost."""
           
       @property
       def total_cost(self) -> float:
           """Calculate total cost across all models."""
   ```

5. **Create claude_code_builder/models/phase.py**
   ```python
   from dataclasses import dataclass, field
   from typing import List, Dict, Any, Optional
   from claude_code_builder.models.build_status import BuildStatus
   
   @dataclass
   class Phase:
       """Represents a build phase."""
       id: str
       name: str
       description: str
       tasks: List[str]
       dependencies: List[str] = field(default_factory=list)
       context: Dict[str, Any] = field(default_factory=dict)
       max_retries: int = 3
       status: BuildStatus = BuildStatus.PENDING
       retry_count: int = 0
       error: Optional[str] = None
       
       def validate(self) -> bool:
           """Validate phase configuration."""
       
       def can_run(self, completed_phases: List[str]) -> bool:
           """Check if dependencies are met."""
   ```

6. **Create claude_code_builder/models/project_memory.py**
   ```python
   import json
   from pathlib import Path
   from typing import Dict, Any, Optional
   from datetime import datetime
   
   class ProjectMemory:
       """Manages project state and memory persistence."""
       
       def __init__(self, project_dir: Path):
           self.project_dir = project_dir
           self.memory_dir = project_dir / ".memory"
           self.memory_dir.mkdir(exist_ok=True)
           
       def save_checkpoint(self, phase_id: str, data: Dict[str, Any]):
           """Save a checkpoint for a phase."""
           
       def load_checkpoint(self, phase_id: str) -> Optional[Dict[str, Any]]:
           """Load a checkpoint for a phase."""
   ```

### Supporting Models
7. **Create claude_code_builder/models/research.py**
   ```python
   from dataclasses import dataclass
   from typing import List, Dict, Any, Optional
   
   @dataclass
   class ResearchQuery:
       """Query for research agents."""
       query: str
       context: Dict[str, Any]
       agent_type: Optional[str] = None
       
   @dataclass
   class ResearchResult:
       """Result from research agent."""
       agent: str
       findings: List[str]
       recommendations: List[str]
       confidence: float
       metadata: Dict[str, Any] = field(default_factory=dict)
   ```

8. **Create claude_code_builder/models/mcp.py**
   ```python
   from dataclasses import dataclass, field
   from typing import Dict, Any, List, Optional
   
   @dataclass
   class MCPServerInfo:
       """Information about an MCP server."""
       name: str
       package: str
       description: str
       installed: bool = False
       version: Optional[str] = None
       config_template: Dict[str, Any] = field(default_factory=dict)
       
   @dataclass
   class MCPRecommendation:
       """Recommendation for MCP server usage."""
       server: MCPServerInfo
       confidence: float
       reasons: List[str]
       config: Dict[str, Any]
   ```

9. **Update claude_code_builder/models/__init__.py**
   ```python
   """Data models for Claude Code Builder."""
   
   from claude_code_builder.models.build_status import BuildStatus
   from claude_code_builder.models.tool_call import ToolCall
   from claude_code_builder.models.build_stats import BuildStats
   from claude_code_builder.models.cost_tracker import CostTracker
   from claude_code_builder.models.phase import Phase
   from claude_code_builder.models.project_memory import ProjectMemory
   from claude_code_builder.models.research import ResearchQuery, ResearchResult
   from claude_code_builder.models.mcp import MCPServerInfo, MCPRecommendation
   
   __all__ = [
       "BuildStatus",
       "ToolCall",
       "BuildStats",
       "CostTracker",
       "Phase",
       "ProjectMemory",
       "ResearchQuery",
       "ResearchResult",
       "MCPServerInfo",
       "MCPRecommendation",
   ]
   ```

## Phase 3: MCP System Implementation

1. **Create claude_code_builder/mcp/server_registry.py**
   ```python
   """Registry of available MCP servers."""
   
   MCP_SERVER_REGISTRY = {
       "filesystem": {
           "package": "@modelcontextprotocol/server-filesystem",
           "description": "File system operations with security",
           "config_template": {
               "command": "npx",
               "args": ["-y", "@modelcontextprotocol/server-filesystem", "--allowed-paths", "${WORKSPACE}"]
           },
           "technologies": ["general"],
           "use_cases": ["file_management", "code_generation"],
           "confidence_boost": 0.9
       },
       # Add 15+ more servers
   }
   ```

2. **Create claude_code_builder/mcp/recommendation_engine.py**
   ```python
   from typing import List, Dict, Any
   from claude_code_builder.models.mcp import MCPRecommendation, MCPServerInfo
   from claude_code_builder.mcp.server_registry import MCP_SERVER_REGISTRY
   
   class MCPRecommendationEngine:
       """Recommends MCP servers based on project needs."""
       
       def __init__(self):
           self.registry = MCP_SERVER_REGISTRY
           
       async def analyze_project_needs(self, 
                                     specification: str, 
                                     context: Dict[str, Any]) -> List[MCPRecommendation]:
           """Analyze project and recommend MCP servers."""
           
       def _extract_technology_stack(self, specification: str) -> List[str]:
           """Extract technologies from specification."""
           
       def _calculate_confidence(self, server_info: Dict, 
                               tech_stack: List[str],
                               requirements: List[str]) -> float:
           """Calculate confidence score for a server."""
   ```

3. **Create claude_code_builder/mcp/discovery.py**
   ```python
   import subprocess
   import json
   from typing import Dict, List, Optional
   from pathlib import Path
   
   class MCPServerDiscovery:
       """Discover installed MCP servers."""
       
       def discover_installed_servers(self) -> Dict[str, MCPServerInfo]:
           """Find all installed MCP servers."""
           
       def _check_npm_global(self) -> List[str]:
           """Check globally installed npm packages."""
           
       def _check_node_modules(self, path: Path) -> List[str]:
           """Check local node_modules."""
   ```

4. **Create claude_code_builder/mcp/config_generator.py**
   ```python
   import json
   from pathlib import Path
   from typing import Dict, Any, List
   from claude_code_builder.models.mcp import MCPRecommendation
   
   class MCPConfigGenerator:
       """Generate MCP configuration files."""
       
       def generate_config(self, 
                         recommendations: List[MCPRecommendation],
                         workspace: Path) -> Dict[str, Any]:
           """Generate MCP configuration."""
           
       def _substitute_variables(self, config: Dict[str, Any], 
                               workspace: Path) -> Dict[str, Any]:
           """Substitute template variables."""
   ```

5. **Create claude_code_builder/mcp/installer.py**
   ```python
   import asyncio
   import subprocess
   from typing import List
   from claude_code_builder.models.mcp import MCPServerInfo
   from claude_code_builder.ui import console
   
   class MCPInstaller:
       """Install MCP servers via npm."""
       
       async def install_servers(self, servers: List[MCPServerInfo]):
           """Install multiple MCP servers."""
           
       async def _install_server(self, server: MCPServerInfo) -> bool:
           """Install a single MCP server."""
   ```

## Phase 4: Research System

1. **Create claude_code_builder/research/base_agent.py**
   ```python
   from abc import ABC, abstractmethod
   from typing import Dict, Any, Optional
   from anthropic import Anthropic
   from claude_code_builder.models.research import ResearchQuery, ResearchResult
   
   class ResearchAgent(ABC):
       """Base class for research agents."""
       
       def __init__(self, name: str, expertise: str, client: Optional[Anthropic] = None):
           self.name = name
           self.expertise = expertise
           self.client = client or Anthropic()
           
       @abstractmethod
       async def research(self, query: ResearchQuery) -> ResearchResult:
           """Conduct research on the query."""
           
       def _generate_prompt(self, query: ResearchQuery) -> str:
           """Generate research prompt."""
   ```

2. **Create claude_code_builder/research/agents.py**
   ```python
   from claude_code_builder.research.base_agent import ResearchAgent
   from claude_code_builder.models.research import ResearchQuery, ResearchResult
   
   class TechnologyAnalyst(ResearchAgent):
       """Analyzes technology choices and alternatives."""
       
       def __init__(self, client=None):
           super().__init__(
               name="Technology Analyst",
               expertise="technology stack evaluation and recommendations",
               client=client
           )
           
       async def research(self, query: ResearchQuery) -> ResearchResult:
           """Research technology options."""
   
   class SecuritySpecialist(ResearchAgent):
       """Identifies security requirements and best practices."""
       # Implementation
   
   # Add remaining 5 agents
   ```

3. **Create claude_code_builder/research/manager.py**
   ```python
   import asyncio
   from typing import List, Dict, Any, Optional
   from anthropic import Anthropic
   from claude_code_builder.models.research import ResearchQuery, ResearchResult
   from claude_code_builder.research.agents import *
   
   class ResearchManager:
       """Coordinates multiple research agents."""
       
       def __init__(self, api_key: Optional[str] = None):
           self.client = Anthropic(api_key=api_key) if api_key else None
           self.agents = self._initialize_agents()
           
       def _initialize_agents(self) -> List[ResearchAgent]:
           """Initialize all research agents."""
           
       async def conduct_research(self, 
                                specification: str,
                                context: Dict[str, Any]) -> Dict[str, ResearchResult]:
           """Conduct comprehensive research."""
   ```

## Phase 5: Custom Instructions System

1. **Create claude_code_builder/instructions/templates.py**
   ```python
   """Default instruction templates."""
   
   GLOBAL_INSTRUCTIONS = """
   You are building a production-ready application. Follow these principles:
   1. No mock implementations - everything must be functional
   2. Use proper error handling throughout
   3. Follow language-specific best practices
   4. Implement comprehensive logging
   5. Include security considerations
   """
   
   PYTHON_INSTRUCTIONS = """
   For Python projects:
   1. Use type hints for all functions
   2. Follow PEP 8 style guide
   3. Use async/await for I/O operations
   4. Include docstrings for all public methods
   """
   
   # Add more instruction templates
   ```

2. **Create claude_code_builder/instructions/manager.py**
   ```python
   import re
   from typing import List, Dict, Any, Optional
   from dataclasses import dataclass
   
   @dataclass
   class CustomInstruction:
       """Custom instruction with metadata."""
       name: str
       content: str
       context_pattern: Optional[str] = None
       priority: int = 50
       phase_specific: bool = False
       
   class CustomInstructionManager:
       """Manages custom instructions for builds."""
       
       def __init__(self):
           self.instructions: List[CustomInstruction] = []
           self._load_defaults()
           
       def get_instructions_for_context(self, 
                                      context: Dict[str, Any],
                                      phase: Optional[str] = None) -> List[str]:
           """Get applicable instructions for context."""
   ```

## Phase 6: Execution System

1. **Create claude_code_builder/execution/executor.py**
   ```python
   import subprocess
   import asyncio
   from pathlib import Path
   from typing import Dict, Any, Optional, List
   from claude_code_builder.models import Phase
   from claude_code_builder.execution.streaming import StreamingMessageHandler
   
   class ClaudeCodeExecutor:
       """Executes Claude Code CLI commands."""
       
       def __init__(self, model: str, max_turns: int = 30):
           self.model = model
           self.max_turns = max_turns
           
       async def execute_phase(self, 
                             phase: Phase,
                             prompt: str,
                             mcp_config: Optional[Path] = None,
                             additional_tools: Optional[List[str]] = None) -> Dict[str, Any]:
           """Execute a build phase with Claude Code."""
           
       def _build_command(self, 
                        prompt_file: Path,
                        mcp_config: Optional[Path] = None,
                        additional_tools: Optional[List[str]] = None) -> List[str]:
           """Build Claude Code command."""
   ```

2. **Create claude_code_builder/execution/streaming.py**
   ```python
   import json
   from typing import Dict, Any, Optional, Callable
   from claude_code_builder.models import ToolCall
   
   class StreamingMessageHandler:
       """Handles streaming JSON output from Claude Code."""
       
       def __init__(self, 
                  on_tool_call: Optional[Callable] = None,
                  on_message: Optional[Callable] = None,
                  on_cost: Optional[Callable] = None):
           self.on_tool_call = on_tool_call
           self.on_message = on_message
           self.on_cost = on_cost
           
       def process_line(self, line: str):
           """Process a single line of streaming output."""
           
       def _handle_event(self, event: Dict[str, Any]):
           """Handle different event types."""
   ```

3. **Create claude_code_builder/execution/phase_runner.py**
   ```python
   from typing import Dict, Any, List
   from claude_code_builder.models import Phase, BuildStatus
   from claude_code_builder.execution.executor import ClaudeCodeExecutor
   from claude_code_builder.execution.prompt_builder import PromptBuilder
   
   class PhaseRunner:
       """Orchestrates phase execution with retry logic."""
       
       def __init__(self, executor: ClaudeCodeExecutor):
           self.executor = executor
           self.prompt_builder = PromptBuilder()
           
       async def run_phase(self, 
                         phase: Phase,
                         context: Dict[str, Any],
                         custom_instructions: List[str]) -> Dict[str, Any]:
           """Run a phase with retry logic."""
   ```

## Phase 7: UI and Progress System

1. **Create claude_code_builder/ui/console.py**
   ```python
   from rich.console import Console
   from rich.theme import Theme
   
   # Custom theme
   custom_theme = Theme({
       "info": "cyan",
       "warning": "yellow",
       "error": "bold red",
       "success": "bold green",
       "phase": "bold magenta",
   })
   
   # Singleton console instance
   console = Console(theme=custom_theme)
   
   __all__ = ["console"]
   ```

2. **Create claude_code_builder/ui/progress.py**
   ```python
   from rich.progress import Progress, TaskID, BarColumn, TextColumn
   from typing import Dict, Optional
   
   class BuildProgress:
       """Manages build progress display."""
       
       def __init__(self):
           self.progress = Progress(
               TextColumn("[bold blue]{task.fields[phase_name]}", justify="right"),
               BarColumn(bar_width=None),
               "[progress.percentage]{task.percentage:>3.1f}%",
               console=console,
           )
           self.tasks: Dict[str, TaskID] = {}
           
       def add_phase(self, phase_id: str, name: str, total_tasks: int) -> TaskID:
           """Add a phase to track."""
   ```

3. **Create claude_code_builder/ui/display.py**
   ```python
   from rich.panel import Panel
   from rich.table import Table
   from rich.layout import Layout
   from typing import List, Dict, Any
   from claude_code_builder.models import Phase, BuildStats
   
   class DisplayComponents:
       """Rich display components."""
       
       @staticmethod
       def phase_panel(phase: Phase) -> Panel:
           """Create a panel for phase information."""
           
       @staticmethod
       def stats_table(stats: BuildStats) -> Table:
           """Create statistics table."""
           
       @staticmethod
       def build_layout() -> Layout:
           """Create main build layout."""
   ```

## Phase 8: Validation System

1. **Create claude_code_builder/validation/validator.py**
   ```python
   from pathlib import Path
   from typing import List, Dict, Any
   from claude_code_builder.validation.checks import ValidationCheck
   from claude_code_builder.models import BuildStats
   
   class ProjectValidator:
       """Validates built projects."""
       
       def __init__(self, project_path: Path):
           self.project_path = project_path
           self.checks = self._initialize_checks()
           
       def validate_all(self) -> Dict[str, Any]:
           """Run all validation checks."""
           
       def validate_category(self, category: str) -> Dict[str, Any]:
           """Run checks for a specific category."""
   ```

2. **Create claude_code_builder/validation/checks.py**
   ```python
   from abc import ABC, abstractmethod
   from pathlib import Path
   from typing import Dict, Any, List
   
   class ValidationCheck(ABC):
       """Base class for validation checks."""
       
       def __init__(self, name: str, category: str):
           self.name = name
           self.category = category
           
       @abstractmethod
       def check(self, project_path: Path) -> Dict[str, Any]:
           """Run the validation check."""
   
   class EntryPointCheck(ValidationCheck):
       """Check for valid entry point."""
       
       def check(self, project_path: Path) -> Dict[str, Any]:
           """Check if entry point exists."""
   
   # Add more check classes
   ```

## Phase 9: Utilities and Helpers

1. **Create claude_code_builder/utils/constants.py**
   ```python
   """Constants and configuration values."""
   
   TOKEN_COSTS = {
       'claude-3-5-sonnet-20241022': {
           'input': 0.003,
           'output': 0.015
       },
       'claude-opus-4-20250514': {
           'input': 0.015,
           'output': 0.075
       },
       # Add all models
   }
   
   DEFAULT_CONFIG = {
       'max_turns': 30,
       'max_retries': 3,
       'phase_timeout': 600,
       'min_phases': 7,
       'min_tasks_per_phase': 8,
   }
   ```

2. **Create claude_code_builder/utils/exceptions.py**
   ```python
   """Custom exceptions for Claude Code Builder."""
   
   class BuilderError(Exception):
       """Base exception for all builder errors."""
       pass
   
   class ValidationError(BuilderError):
       """Validation failed."""
       pass
   
   class ExecutionError(BuilderError):
       """Execution failed."""
       pass
   
   class ConfigurationError(BuilderError):
       """Invalid configuration."""
       pass
   ```

3. **Create claude_code_builder/utils/git.py**
   ```python
   import subprocess
   from pathlib import Path
   from typing import Optional
   
   class GitManager:
       """Manages git operations."""
       
       def __init__(self, repo_path: Path):
           self.repo_path = repo_path
           
       def init_repo(self) -> bool:
           """Initialize git repository."""
           
       def commit(self, message: str) -> bool:
           """Create a commit."""
           
       def tag(self, tag_name: str, message: Optional[str] = None) -> bool:
           """Create a tag."""
   ```

## Phase 10: Main Application Integration

1. **Complete claude_code_builder/main.py**
   ```python
   import asyncio
   import signal
   from pathlib import Path
   from typing import Dict, Any, Optional
   
   from claude_code_builder.models import (
       Phase, BuildStats, CostTracker, ProjectMemory
   )
   from claude_code_builder.mcp import MCPRecommendationEngine
   from claude_code_builder.research import ResearchManager
   from claude_code_builder.execution import PhaseRunner, ClaudeCodeExecutor
   from claude_code_builder.ui import console, BuildProgress
   from claude_code_builder.validation import ProjectValidator
   
   class ClaudeCodeBuilder:
       """Main orchestrator for autonomous project building."""
       
       def __init__(self, spec_file: Path, output_dir: Path, **options):
           self.spec_file = spec_file
           self.output_dir = output_dir
           self.options = options
           
           # Initialize components
           self.build_stats = BuildStats()
           self.cost_tracker = CostTracker()
           self.memory = ProjectMemory(output_dir)
           
           # Set up signal handlers
           signal.signal(signal.SIGINT, self._handle_interrupt)
           
       async def run(self):
           """Run the complete build process."""
           
       async def _run_research_phase(self):
           """Run AI-powered research."""
           
       async def _discover_mcp_servers(self):
           """Discover and configure MCP servers."""
           
       async def _execute_phases(self, phases: List[Phase]):
           """Execute all build phases."""
   ```

2. **Update claude_code_builder/cli.py**
   ```python
   import click
   import asyncio
   from pathlib import Path
   from claude_code_builder.main import ClaudeCodeBuilder
   from claude_code_builder.ui import console
   
   @click.command()
   @click.argument('spec_file', type=click.Path(exists=True, path_type=Path))
   @click.option('--output-dir', '-o', type=click.Path(path_type=Path), default='./output')
   # Add all 30+ options with proper types and help text
   def main(**kwargs):
       """Build projects autonomously using Claude Code SDK."""
       console.print("[bold cyan]Claude Code Builder v2.3.0[/bold cyan]")
       
       # Create and run builder
       builder = ClaudeCodeBuilder(**kwargs)
       asyncio.run(builder.run())
   ```

## Phase 11: Testing and Examples

1. **Create tests/conftest.py**
   ```python
   import pytest
   from pathlib import Path
   import tempfile
   
   @pytest.fixture
   def temp_dir():
       """Create temporary directory for tests."""
       with tempfile.TemporaryDirectory() as tmpdir:
           yield Path(tmpdir)
   
   @pytest.fixture
   def sample_spec():
       """Sample specification for testing."""
       return """
       # Test Project
       
       A simple test project.
       
       ## Technology Stack
       - Python
       - FastAPI
       """
   ```

2. **Create tests/functional/test_build.py**
   ```python
   import pytest
   from pathlib import Path
   from claude_code_builder.main import ClaudeCodeBuilder
   
   @pytest.mark.asyncio
   async def test_basic_build(temp_dir, sample_spec):
       """Test basic build functionality."""
       spec_file = temp_dir / "spec.md"
       spec_file.write_text(sample_spec)
       
       builder = ClaudeCodeBuilder(
           spec_file=spec_file,
           output_dir=temp_dir / "output",
           auto_confirm=True
       )
       
       await builder.run()
       
       # Verify output
       assert (temp_dir / "output").exists()
   ```

3. **Create examples/simple-api-spec.md**
   ```markdown
   # Simple REST API
   
   Build a basic REST API with user management.
   
   ## Technology Stack
   - Python 3.10+
   - FastAPI
   - SQLite with SQLAlchemy
   - Pydantic for validation
   - JWT for authentication
   
   ## Features
   1. User registration with email validation
   2. User login with JWT tokens
   3. CRUD operations for user profiles
   4. Password hashing with bcrypt
   5. Rate limiting
   6. OpenAPI documentation
   
   ## Project Structure
   Standard Python package with:
   - src/ directory for source code
   - tests/ for pytest tests
   - Docker support
   - Environment variable configuration
   
   ## Requirements
   - RESTful design
   - Async/await throughout
   - Comprehensive error handling
   - Logging with structured output
   - 90% test coverage
   ```

## Phase 12: Documentation and Polish

1. **Complete README.md**
   ```markdown
   # Claude Code Builder v2.3.0
   
   An enhanced production-ready autonomous multi-phase project builder that orchestrates Claude Code SDK to autonomously build complete projects.
   
   ## 🚀 Features
   
   ### Core Capabilities
   - **Autonomous Project Building**: Generates complete, production-ready projects
   - **Multi-Phase Execution**: Breaks down complex projects into manageable phases
   - **AI-Powered Research**: Conducts comprehensive research using specialized AI agents
   - **MCP Integration**: Discovers and configures Model Context Protocol servers
   - **Cost Tracking**: Accurate API usage tracking with detailed breakdowns
   - **Build Resumption**: Checkpoint system allows resuming interrupted builds
   - **Rich UI**: Beautiful terminal output with progress bars, tables, and animations
   
   ## 📋 Prerequisites
   
   - Python 3.8 or higher
   - Node.js 16.x or higher
   - npm (for Claude Code and MCP servers)
   - Git (optional, for version control)
   - Anthropic API key (for research features)
   
   ## 🛠️ Installation
   
   1. **Install Claude Code CLI**:
      ```bash
      npm install -g @anthropic-ai/claude-code
      ```
   
   2. **Install Claude Code Builder**:
      ```bash
      pip install claude-code-builder
      ```
   
      Or from source:
      ```bash
      git clone https://github.com/yourusername/claude-code-builder.git
      cd claude-code-builder
      pip install -e .
      ```
   
   ## 🎯 Quick Start
   
   ### Basic Usage
   ```bash
   claude-code-builder project-spec.md --output-dir ./my-project
   ```
   
   ### With Research and MCP Discovery
   ```bash
   claude-code-builder project-spec.md \
       --output-dir ./my-project \
       --enable-research \
       --discover-mcp \
       --auto-confirm
   ```
   
   ## 📚 Documentation
   
   - [Architecture Overview](docs/architecture.md)
   - [API Reference](docs/api-reference.md)
   - [Writing Specifications](docs/specifications.md)
   - [MCP Server Guide](docs/mcp-servers.md)
   
   ## 🤝 Contributing
   
   See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.
   
   ## 📜 License
   
   MIT License - see [LICENSE](LICENSE) for details.
   ```

2. **Create docs/architecture.md**
   ```markdown
   # Architecture Overview
   
   Claude Code Builder follows a modular architecture with clear separation of concerns.
   
   ## Package Structure
   
   ```
   claude_code_builder/
   ├── models/          # Data models and types
   ├── mcp/            # MCP server management
   ├── research/       # AI research system
   ├── execution/      # Claude Code execution
   ├── ui/             # Terminal UI components
   ├── validation/     # Project validation
   ├── utils/          # Utilities and helpers
   └── instructions/   # Custom instructions
   ```
   
   ## Component Interactions
   
   [Add architecture diagrams and flow charts]
   ```

3. **Create final test script**
   ```bash
   #!/bin/bash
   # scripts/run-tests.sh
   
   echo "Running Claude Code Builder Tests"
   echo "================================="
   
   # Run pytest
   pytest tests/ -v --cov=claude_code_builder --cov-report=html
   
   # Run mypy
   mypy claude_code_builder --strict
   
   # Run black
   black --check claude_code_builder tests
   
   # Run isort
   isort --check-only claude_code_builder tests
   
   echo "Tests complete!"
   ```

## Memory Checkpoints

Each phase should store its completion state:
```python
# After each phase
memory.save_checkpoint(f"phase_{phase_number}", {
    "completed": True,
    "files_created": [...],
    "key_decisions": [...],
    "context": {...}
})
```

## Git Commits

Structure commits for each phase:
```bash
git add -A
git commit -m "feat: Phase N - <description>

- <key achievement 1>
- <key achievement 2>
- <key achievement 3>

Implements: <what was implemented>
Files: <number of files created/modified>"
```

## Final Steps

1. Run all tests
2. Generate documentation
3. Create distribution package
4. Tag release v2.3.0