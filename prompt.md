# Claude Code Builder v2.3.0 - Complete Specification

## Project Overview

You are building **Claude Code Builder v2.3.0**, an enhanced production-ready autonomous multi-phase project builder. This is a sophisticated Python **package** (not a single file) that orchestrates Claude Code SDK to autonomously build complete projects through multiple execution phases, with enhanced memory management, improved research capabilities, accurate cost tracking, and robust error handling.

**IMPORTANT**: This should be implemented as a proper Python package with multiple modules following clean architecture principles, NOT as a single monolithic file.

### Key Improvements in v2.3.0
- Enhanced research implementation using Anthropic SDK knowledge base
- Accurate cost tracking from Claude Code execution results
- Improved error handling and recovery mechanisms
- Better memory management with context preservation
- Enhanced MCP server discovery and configuration
- Optimized phase execution with better context passing
- Improved streaming output parsing with real-time cost updates
- Advanced tool management with usage analytics
- Comprehensive validation and testing framework

## Core Architecture

### Package Structure

```
claude_code_builder/
├── __init__.py              # Package initialization, version
├── __main__.py              # Entry point for python -m
├── cli.py                   # Click CLI application
├── main.py                  # Main ClaudeCodeBuilder class
├── models/                  # Data models and types
│   ├── __init__.py
│   ├── build_status.py      # BuildStatus enum
│   ├── tool_call.py         # ToolCall dataclass
│   ├── build_stats.py       # BuildStats dataclass
│   ├── cost_tracker.py      # CostTracker class
│   ├── phase.py             # Phase dataclass
│   ├── project_memory.py    # ProjectMemory class
│   ├── research.py          # Research-related models
│   └── mcp.py              # MCP-related models
├── mcp/                     # MCP server management
│   ├── __init__.py
│   ├── server_registry.py   # MCP server definitions
│   ├── recommendation_engine.py
│   ├── config_generator.py
│   ├── discovery.py
│   └── installer.py
├── research/                # AI research system
│   ├── __init__.py
│   ├── base_agent.py
│   ├── agents.py           # All 7 research agents
│   ├── manager.py
│   └── prompts.py
├── execution/               # Claude Code execution
│   ├── __init__.py
│   ├── executor.py
│   ├── streaming.py
│   ├── phase_runner.py
│   └── prompt_builder.py
├── ui/                      # Rich UI components
│   ├── __init__.py
│   ├── console.py          # Singleton console
│   ├── progress.py
│   ├── display.py
│   └── reports.py
├── validation/              # Project validation
│   ├── __init__.py
│   ├── validator.py
│   ├── checks.py
│   └── test_runner.py
├── utils/                   # Utilities and helpers
│   ├── __init__.py
│   ├── constants.py        # TOKEN_COSTS, etc.
│   ├── exceptions.py
│   ├── git.py
│   └── helpers.py
└── instructions/            # Custom instructions
    ├── __init__.py
    ├── manager.py
    ├── defaults.py
    └── templates.py
```

### Main Components

1. **ClaudeCodeBuilder** - Main orchestration class
2. **MCPRecommendationEngine** - MCP server discovery and configuration
3. **ResearchManager** - Multi-agent AI research system
4. **CustomInstructionManager** - Dynamic instruction generation
5. **ClaudeCodeExecutor** - Claude Code CLI integration
6. **ProjectValidator** - Comprehensive validation system
7. **ReportGenerator** - Analytics and reporting
8. **RichUI** - Beautiful terminal interface

### Data Models

```python
@dataclass
class BuildStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    start_time: float
    end_time: Optional[float] = None
    result: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def duration(self) -> float
    
    @property
    def is_mcp_tool(self) -> bool

@dataclass
class BuildStats:
    files_created: int = 0
    files_modified: int = 0
    directories_created: int = 0
    lines_written: int = 0
    functions_created: int = 0
    classes_created: int = 0
    tool_calls: List[ToolCall] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    # ... 20+ more fields

@dataclass
class CostTracker:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    costs_by_model: Dict[str, float] = field(default_factory=dict)
    costs_by_phase: Dict[str, float] = field(default_factory=dict)
    
    def add_tokens(self, model: str, input_tokens: int, output_tokens: int)
    
    @property
    def total_cost(self) -> float

@dataclass
class Phase:
    id: str
    name: str
    description: str
    tasks: List[str]
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    status: BuildStatus = BuildStatus.PENDING
    # ... more fields
```

## Complete CLI Interface

```bash
claude-code-builder <spec_file> [options]

Positional Arguments:
  spec_file             Project specification file (markdown format)

Output Configuration:
  --output-dir, -o      Output directory for the project (default: ./output)
  --git-init            Initialize git repository in output directory

Model Configuration:
  --model-analyzer      Model for project analysis (default: claude-opus-4-20250514)
  --model-executor      Model for code execution (default: claude-opus-4-20250514)
  --api-key             Anthropic API key (or set ANTHROPIC_API_KEY env var)

Execution Configuration:
  --max-turns           Maximum conversation turns per phase (default: 30)
  --max-retries         Maximum retries for failed phases (default: 3)
  --continue-on-error   Continue execution even if a phase fails
  --auto-confirm        Skip confirmation prompts

Enhanced Features:
  --enable-research     Enable comprehensive AI-powered research phase
  --discover-mcp        Discover and recommend MCP servers
  --auto-install-mcp    Automatically install recommended MCP servers
  --additional-mcp-servers  Additional MCP servers (format: name:package:description)
  --additional-tools    Additional tools to allow

Phase Configuration:
  --min-phases          Minimum number of phases (default: 7)
  --min-tasks-per-phase Minimum tasks per phase (default: 8)
  --phase-timeout       Timeout per phase in seconds (default: 600)

Output Formatting:
  --stream-output       Stream output in real-time (default: True)
  --no-stream-output    Disable streaming output
  --parse-output        Parse and format streaming output
  --verbose, -v         Verbose output
  --debug               Debug mode

Validation and Testing:
  --validate            Validate project after build (default: True)
  --no-validate         Skip project validation
  --run-tests           Run tests after build
  --test-coverage-threshold  Minimum test coverage (default: 80.0)

Logging Configuration:
  --log-file            Log file path
  --log-level           Logging level (default: INFO)
  --save-prompts        Save all prompts for debugging

Reporting:
  --export-report       Export detailed build report
  --report-format       Report format (json, markdown, both)
```

## MCP Server Registry

```python
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
    "github": {
        "package": "@modelcontextprotocol/server-github",
        "description": "GitHub repository operations",
        "config_template": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
        },
        "technologies": ["git", "github"],
        "use_cases": ["version_control", "collaboration"],
        "confidence_boost": 0.8
    },
    # ... 15+ more servers
}
```

## Research Agents

1. **Technology Analyst** - Evaluates technology choices and alternatives
2. **Security Specialist** - Identifies security requirements and best practices
3. **Performance Engineer** - Optimizes for speed and efficiency
4. **Solutions Architect** - Designs system architecture
5. **Best Practices Advisor** - Ensures industry standards
6. **Quality Assurance Expert** - Defines testing strategies
7. **DevOps Specialist** - Plans deployment and operations

## Validation Checks

1. Entry point detection
2. Package structure validation
3. Directory organization
4. Dependencies and lock files
5. TODO/FIXME detection
6. Error handling patterns
7. Logging implementation
8. Test directory structure
9. Documentation presence
10. Security checks (hardcoded secrets)
11. Docker support
12. CI/CD configuration

## Build Reports

### PROJECT_SUMMARY.md
- Project overview
- Technology stack
- Features implemented
- Build statistics
- Next steps

### VALIDATION_REPORT.md
- All validation checks
- Pass/fail status
- Suggestions for improvements
- Security findings

### Build Analytics (JSON/Markdown)
- Detailed metrics
- Cost breakdown
- Performance analysis
- Tool usage statistics

## Example Usage

### Basic Build
```bash
claude-code-builder project-spec.md --output-dir ./my-project
```

### With Research and MCP
```bash
claude-code-builder project-spec.md \
    --output-dir ./my-project \
    --enable-research \
    --discover-mcp \
    --auto-confirm
```

### Full Configuration
```bash
claude-code-builder project-spec.md \
    --output-dir ./my-awesome-app \
    --api-key $ANTHROPIC_API_KEY \
    --model-analyzer claude-opus-4-20250514 \
    --model-executor claude-opus-4-20250514 \
    --max-turns 30 \
    --max-retries 3 \
    --continue-on-error \
    --auto-confirm \
    --enable-research \
    --discover-mcp \
    --auto-install-mcp \
    --git-init \
    --run-tests \
    --export-report \
    --report-format both
```

## Implementation Requirements

1. **Modular Package Structure** - Proper Python package with multiple modules
2. **Clean Architecture** - Clear separation of concerns between modules
3. **No Circular Imports** - Well-defined dependency graph
4. **Production Ready** - No placeholders, fully functional
5. **Type Hints** - Complete type annotations in all modules
6. **Error Handling** - Comprehensive exception handling
7. **Rich UI** - Beautiful terminal output using ui module
8. **Real Testing** - Functional tests only
9. **Documentation** - Complete and accurate

## Token Costs

```python
TOKEN_COSTS = {
    'claude-3-5-sonnet-20241022': {
        'input': 0.003,
        'output': 0.015
    },
    'claude-opus-4-20250514': {
        'input': 0.015,
        'output': 0.075
    },
    'claude-3-opus-20240229': {
        'input': 0.015,
        'output': 0.075
    },
    'claude-3-sonnet-20240229': {
        'input': 0.003,
        'output': 0.015
    },
    'claude-3-haiku-20240307': {
        'input': 0.00025,
        'output': 0.00125
    }
}
```

## Success Criteria

1. **Builds Real Projects** - Can build any project from a specification
2. **Accurate Cost Tracking** - Tracks actual API costs
3. **Resume Capability** - Can resume interrupted builds
4. **Beautiful Output** - Rich, colored terminal UI
5. **Comprehensive Validation** - Catches common issues
6. **Detailed Reports** - Provides actionable insights
7. **MCP Integration** - Discovers and configures servers
8. **Research Integration** - Provides AI-powered insights

This tool represents the state of the art in autonomous project building, combining the power of Claude with sophisticated orchestration and beautiful user experience.