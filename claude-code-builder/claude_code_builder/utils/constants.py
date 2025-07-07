"""Constants used throughout Claude Code Builder."""

from pathlib import Path
from typing import Dict, List, Set

# Version info
VERSION = "3.0.0"
MIN_PYTHON_VERSION = (3, 8)

# File patterns
PYTHON_FILE_EXTENSIONS = {".py", ".pyi", ".pyx"}
CONFIG_FILE_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".ini"}
MARKDOWN_FILE_EXTENSIONS = {".md", ".markdown", ".rst"}
CODE_FILE_EXTENSIONS = PYTHON_FILE_EXTENSIONS | {
    ".js", ".ts", ".jsx", ".tsx",  # JavaScript/TypeScript
    ".java", ".kt",                 # Java/Kotlin
    ".cpp", ".c", ".h", ".hpp",     # C/C++
    ".go",                          # Go
    ".rs",                          # Rust
    ".rb",                          # Ruby
    ".php",                         # PHP
    ".swift",                       # Swift
    ".cs",                          # C#
}

# Default paths
DEFAULT_OUTPUT_DIR = Path("./output")
DEFAULT_TEMP_DIR = Path("/tmp/claude-code-builder")
DEFAULT_LOG_FILE = "claude-code-builder.log"
DEFAULT_STATE_FILE = ".claude-state.json"
DEFAULT_TEST_RESULTS_FILE = ".claude-test-results.json"

# Phase constants
PHASE_PLANNING = "planning"
PHASE_EXECUTION = "execution"
PHASE_TESTING = "testing"
PHASE_VALIDATION = "validation"
PHASE_COMPLETION = "completion"

# Task states
TASK_PENDING = "pending"
TASK_IN_PROGRESS = "in_progress"
TASK_COMPLETED = "completed"
TASK_FAILED = "failed"
TASK_SKIPPED = "skipped"
TASK_BLOCKED = "blocked"

# Test stages
TEST_STAGE_INSTALLATION = "installation"
TEST_STAGE_CLI = "cli"
TEST_STAGE_FUNCTIONAL = "functional"
TEST_STAGE_PERFORMANCE = "performance"
TEST_STAGE_RECOVERY = "recovery"

# Cost categories
COST_CLAUDE_CODE = "claude_code"
COST_RESEARCH = "research"
COST_PLANNING = "planning"
COST_EXECUTION = "execution"
COST_TESTING = "testing"
COST_VALIDATION = "validation"

# Research agents
RESEARCH_AGENTS = [
    "TechnologyAnalyst",
    "SecuritySpecialist",
    "PerformanceEngineer",
    "SolutionsArchitect",
    "BestPracticesAdvisor",
    "QualityAssuranceExpert",
    "DevOpsSpecialist"
]

# MCP complexity levels
MCP_COMPLEXITY_LOW = 1
MCP_COMPLEXITY_MEDIUM = 3
MCP_COMPLEXITY_HIGH = 5
MCP_COMPLEXITY_VERY_HIGH = 7
MCP_COMPLEXITY_EXTREME = 10

# Timeouts (in seconds)
DEFAULT_TIMEOUT = 300  # 5 minutes
PHASE_TIMEOUT = 600   # 10 minutes
TEST_TIMEOUT = 1800   # 30 minutes
SDK_TIMEOUT = 120     # 2 minutes
RESEARCH_TIMEOUT = 300 # 5 minutes

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5
RETRY_BACKOFF = 2

# Progress milestones
PROGRESS_STARTED = 0.0
PROGRESS_PLANNING = 0.1
PROGRESS_EXECUTING = 0.3
PROGRESS_TESTING = 0.8
PROGRESS_COMPLETE = 1.0

# Error codes
ERROR_PLANNING = "PLANNING_ERROR"
ERROR_EXECUTION = "EXECUTION_ERROR"
ERROR_VALIDATION = "VALIDATION_ERROR"
ERROR_TESTING = "TESTING_ERROR"
ERROR_SDK = "SDK_ERROR"
ERROR_MCP = "MCP_ERROR"
ERROR_RESEARCH = "RESEARCH_ERROR"
ERROR_MEMORY = "MEMORY_ERROR"
ERROR_MONITORING = "MONITORING_ERROR"
ERROR_TIMEOUT = "TIMEOUT_ERROR"
ERROR_RECOVERY = "RECOVERY_ERROR"

# Log levels
LOG_DEBUG = "DEBUG"
LOG_INFO = "INFO"
LOG_WARNING = "WARNING"
LOG_ERROR = "ERROR"
LOG_CRITICAL = "CRITICAL"

# Environment variables
ENV_ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
ENV_CLAUDE_CODE_CONFIG = "CLAUDE_CODE_CONFIG"
ENV_CLAUDE_CODE_LOG_LEVEL = "CLAUDE_CODE_LOG_LEVEL"
ENV_CLAUDE_CODE_OUTPUT_DIR = "CLAUDE_CODE_OUTPUT_DIR"
ENV_CLAUDE_CODE_TEMP_DIR = "CLAUDE_CODE_TEMP_DIR"

# CLI commands
CMD_BUILD = "build"
CMD_PLAN = "plan"
CMD_ANALYZE = "analyze"
CMD_VALIDATE = "validate"
CMD_TEST = "test"
CMD_RESUME = "resume"

# Validation rules
VALIDATION_RULES = {
    "project_name": r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$",
    "version": r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$",
    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "url": r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$",
}

# Templates
GITIGNORE_TEMPLATE = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Project
.claude-state.json
.claude-test-results.json
*.log
.DS_Store
"""

README_TEMPLATE = """# {project_name}

{description}

## Installation

```bash
pip install -e .
```

## Usage

{usage}

## Development

{development}

## License

{license}
"""

# Magic strings
PHASE_SEPARATOR = "=" * 80
TASK_SEPARATOR = "-" * 60
CHECKPOINT_MAGIC = "CLAUDE_CODE_CHECKPOINT_V1"

# Limits
MAX_PHASES = 50
MAX_TASKS_PER_PHASE = 100
MAX_PARALLEL_WORKERS = 10
MAX_LOG_SIZE = 100 * 1024 * 1024  # 100MB
MAX_MEMORY_ENTRIES = 10000

# Default messages
MSG_WELCOME = "Welcome to Claude Code Builder v3.0 🚀"
MSG_PLANNING = "Analyzing specification and planning optimal build strategy..."
MSG_EXECUTING = "Executing build phases..."
MSG_TESTING = "Running comprehensive functional tests..."
MSG_COMPLETE = "Build completed successfully! ✨"
MSG_FAILED = "Build failed. Check logs for details."
MSG_RECOVERING = "Recovering from checkpoint..."

# Performance thresholds
PERF_WARNING_MEMORY = 1024 * 1024 * 1024  # 1GB
PERF_WARNING_TIME = 300  # 5 minutes per phase
PERF_WARNING_COST = 10.0  # $10

# Feature flags
FEATURE_AI_PLANNING = True
FEATURE_PARALLEL_EXECUTION = True
FEATURE_REAL_TIME_MONITORING = True
FEATURE_AUTO_RECOVERY = True
FEATURE_COST_TRACKING = True
FEATURE_PERFORMANCE_BENCHMARKS = True