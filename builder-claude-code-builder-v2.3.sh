#!/bin/bash

# Claude Code Builder v2.3.0 - Enhanced Autonomous Build Script
# Builds the complete Claude Code Builder with all v2.3.0 enhancements
# 
# This script orchestrates Claude Code to build a sophisticated Python application
# that includes all enhancements from the monolithic implementation:
# - Enhanced cost tracking with Claude Code separation
# - 7 research agents including PerformanceEngineer and DevOpsSpecialist
# - Advanced tool management with analytics
# - MCP server discovery and complexity assessment
# - Custom instruction validation with regex support
# - Phase context management and validation
# - Enhanced project memory with error logging
#
# Usage: ./builder-claude-code-builder-v2.3.sh [OPTIONS]
# Options:
#   -o, --output-dir DIR    Output directory for the build (default: current directory)
#   -r, --resume            Resume from last checkpoint
#   -h, --help              Show this help message

set -euo pipefail

# Color codes for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
MAGENTA="\033[0;35m"
ORANGE="\033[0;33m"
PURPLE="\033[0;35m"
LIGHT_BLUE="\033[1;34m"
LIGHT_GREEN="\033[1;32m"
DIM="\033[2m"
BOLD="\033[1m"
NC="\033[0m"
CLEAR_LINE="\033[2K\r"

# Configuration
PROJECT_NAME="claude-code-builder"
VERSION="2.3.0"
SPEC_FILE="prompt-v2.3.md"
MODEL="claude-3-5-sonnet-20241022"
STATE_FILE=".build-state-v2.3.json"

# Build configuration
MAX_TURNS=50
MAX_PHASE_RETRIES=3
RETRY_DELAY=30
JSON_OUTPUT_DIR=".claude_outputs"
VALIDATION_LOG="phase_validation.log"
METRICS_LOG="build_metrics.json"
HUMAN_LOG="build_progress.log"

# Enhanced Phase Configuration (includes all v2.3.0 enhancements)
TOTAL_PHASES=15  # Increased from 12 to include enhancement phases

# Progress tracking
CURRENT_PHASE=0
START_TIME=$(date +%s)
RESUMED=false
PHASE_RETRY_COUNT=0
LAST_SESSION_ID=""
CURRENT_TASK_COUNT=0
TOTAL_TASK_COUNT=0

# Metrics tracking
METRICS_DIR=".metrics"
TOTAL_API_CALLS=0
TOTAL_TOKENS_USED=0
TOTAL_COST="0.0"
CLAUDE_CODE_COST="0.0"
RESEARCH_COST="0.0"

# Memory management tracking
MEMORY_KEYS_FILE=".memory_keys.json"
MEMORY_KEYS_DIR=".memory_keys"

# Output directory (can be overridden by CLI argument)
OUTPUT_DIR=""
RESUME_BUILD=false

# Global arrays for MCP discovery
declare -a DISCOVERED_MCP_SERVERS
declare -a MCP_SERVER_COMMANDS

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -o, --output-dir DIR    Output directory for the build (default: current directory)"
    echo "  -r, --resume            Resume from last checkpoint"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Build in current directory"
    echo "  $0 -o /path/to/output   # Build in specified directory"
    echo "  $0 --resume             # Resume interrupted build"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output-dir)
            if [[ -z "${2:-}" ]]; then
                echo -e "${RED}Error: --output-dir requires a directory path${NC}"
                exit 1
            fi
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -r|--resume)
            RESUME_BUILD=true
            shift
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo -e "${RED}Error: Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set output directory to current directory if not specified
if [ -z "$OUTPUT_DIR" ]; then
    OUTPUT_DIR="$(pwd)"
else
    # Convert to absolute path if relative
    if [[ "$OUTPUT_DIR" != /* ]]; then
        OUTPUT_DIR="$(pwd)/$OUTPUT_DIR"
    fi
fi

# Set MCP configuration file path
MCP_CONFIG_FILE=".mcp.json"

# ASCII Art Banner - Enhanced for v2.3.0
show_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                       ║"
    echo "║     ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗                 ║"
    echo "║    ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝                 ║"
    echo "║    ██║     ██║     ███████║██║   ██║██║  ██║█████╗                   ║"
    echo "║    ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝                   ║"
    echo "║    ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗                 ║"
    echo "║     ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝                 ║"
    echo "║                                                                       ║"
    echo "║          ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗        ║"
    echo "║          ██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗       ║"
    echo "║          ██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝       ║"
    echo "║          ██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗       ║"
    echo "║          ██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║       ║"
    echo "║          ╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝       ║"
    echo "║                                                                       ║"
    echo "║                    🚀 Version 2.3.0 Enhanced 🚀                      ║"
    echo "║                                                                       ║"
    echo "║  ✨ Features:                                                        ║"
    echo "║     • Enhanced cost tracking with Claude Code separation             ║"
    echo "║     • 7 specialized research agents for comprehensive analysis       ║"
    echo "║     • Advanced tool management with performance analytics            ║"
    echo "║     • MCP server discovery and intelligent recommendations           ║"
    echo "║     • Custom instruction validation with regex support               ║"
    echo "║     • Phase context management and validation framework              ║"
    echo "║     • Enhanced memory with error logging and recovery                ║"
    echo "║                                                                       ║"
    echo "╚═══════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
}

# Enhanced logging functions
log_phase() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "START")
            echo -e "\n${MAGENTA}[PHASE START]${NC} ${timestamp} ${BOLD}$message${NC}" | tee -a "$HUMAN_LOG"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[PHASE COMPLETE]${NC} ${timestamp} ✅ ${BOLD}$message${NC}" | tee -a "$HUMAN_LOG"
            ;;
        "ERROR")
            echo -e "${RED}[PHASE ERROR]${NC} ${timestamp} ❌ ${BOLD}$message${NC}" | tee -a "$HUMAN_LOG"
            ;;
        "VALIDATE")
            echo -e "${BLUE}[VALIDATING]${NC} ${timestamp} 🔍 ${BOLD}$message${NC}" | tee -a "$HUMAN_LOG" "$VALIDATION_LOG"
            ;;
        "INIT")
            echo -e "${CYAN}[INITIALIZING]${NC} ${timestamp} 🔧 ${BOLD}$message${NC}" | tee -a "$HUMAN_LOG"
            ;;
        "ANALYSIS")
            echo -e "${YELLOW}[ANALYZING]${NC} ${timestamp} 📊 ${BOLD}$message${NC}" | tee -a "$HUMAN_LOG"
            ;;
        "RESEARCH")
            echo -e "${PURPLE}[RESEARCHING]${NC} ${timestamp} 🔬 ${BOLD}$message${NC}" | tee -a "$HUMAN_LOG"
            ;;
        "COST")
            echo -e "${ORANGE}[COST TRACKING]${NC} ${timestamp} 💰 ${BOLD}$message${NC}" | tee -a "$HUMAN_LOG"
            ;;
    esac
}

# Create enhanced prompt-v2.3.md specification
create_enhanced_specification() {
    cat > "$SPEC_FILE" << 'EOF'
# Claude Code Builder v2.3.0 - Enhanced Autonomous Multi-Phase Project Builder

## Overview
An intelligent project builder that orchestrates Claude Code SDK to autonomously build complete projects through multiple execution phases, with enhanced memory management, improved research capabilities, accurate cost tracking, and robust error handling.

## Key Enhancements in v2.3.0

### 1. Enhanced Cost Tracking
- **Separate Claude Code cost tracking**: Track costs from Claude Code CLI execution separately
- **Research cost categorization**: Identify and track research agent API costs
- **Session analytics**: Detailed tracking of Claude Code sessions with duration and turns
- **Model breakdown**: Comprehensive cost analytics by model and execution type

### 2. Expanded Research System (7 Agents)
1. **Technology Analyst**: Technology stack analysis and recommendations
2. **Security Specialist**: Cybersecurity and data protection
3. **Performance Engineer**: Performance optimization and scalability (NEW)
4. **Solutions Architect**: System architecture and integration
5. **Best Practices Advisor**: Industry standards and conventions
6. **Quality Assurance Expert**: Testing strategies and automation
7. **DevOps Specialist**: Deployment and infrastructure (NEW)

### 3. Advanced Tool Management
- **Performance metrics**: Track tool execution time and success rates
- **Tool dependencies**: Manage inter-tool dependencies
- **Disabled tools set**: Ability to disable problematic tools
- **New tools**: Added rename, chmod, rmdir, sed, awk

### 4. MCP Server Discovery
- **Installed server detection**: Check which MCP servers are already installed
- **Complexity assessment**: Analyze project complexity for recommendations
- **Enhanced pattern matching**: Better technology and requirement detection
- **Intelligent recommendations**: Context-aware server suggestions

### 5. Custom Instructions Enhancement
- **Validation rules**: Define and enforce instruction validation
- **Regex pattern support**: Use "regex:pattern" in context filters
- **Enhanced matching**: Support for nested conditions and list values
- **Validation method**: Built-in validate() for instruction verification

### 6. Phase Context Management
- **Context accumulation**: Store and retrieve context between phases
- **Validation framework**: Comprehensive phase completion validation
- **Context propagation**: Pass relevant context to subsequent phases
- **Validation results**: Track what passed/failed in each phase

### 7. Enhanced Project Memory
- **Phase contexts storage**: Preserve context from completed phases
- **Error logging system**: Comprehensive error tracking with context
- **Context accumulation**: Get accumulated context up to any phase
- **Recovery mechanisms**: Better checkpoint and recovery support

## Technical Architecture

### Core Components

1. **Main Orchestrator (main.py)**
   - Enhanced with cost separation logic
   - Improved checkpoint/resume with error recovery
   - Better phase context management
   - Enhanced validation framework

2. **Cost Tracking (models/cost_tracker.py)**
   ```python
   @dataclass
   class CostTracker:
       total_cost: float = 0.0
       claude_code_cost: float = 0.0  # NEW
       research_cost: float = 0.0  # NEW
       claude_code_sessions: List[Dict[str, Any]] = field(default_factory=list)  # NEW
   ```

3. **Research System (research/)**
   - 7 specialized agents (expanded from 5)
   - AI-powered synthesis
   - Confidence scoring
   - Research history tracking

4. **Tool Management (tools/manager.py)**
   - Performance metrics collection
   - Tool dependency tracking
   - Success rate analytics
   - Adaptive tool selection

5. **MCP System (mcp/)**
   - Server discovery mechanism
   - Complexity assessment
   - Installation detection
   - Enhanced recommendations

6. **Custom Instructions (instructions/)**
   - Validation rule engine
   - Regex pattern matching
   - Context filter enhancement
   - Instruction validation

7. **Phase Management (models/phase.py)**
   - Context storage per phase
   - Validation framework
   - Result tracking
   - Error recovery

8. **Memory System (models/memory.py)**
   - Phase context preservation
   - Error log with context
   - Context accumulation
   - Enhanced persistence

## Implementation Phases

### Phase 1: Project Foundation (Enhanced)
- Include v2.3.0 version markers
- Set up enhanced directory structure
- Create comprehensive pyproject.toml with all dependencies
- Initialize git with proper .gitignore

### Phase 2: Enhanced Data Models
- Implement CostTracker with new fields
- Add Phase context and validation
- Enhance ProjectMemory with error logging
- Add validation results tracking

### Phase 3: MCP System with Discovery
- Implement server discovery
- Add complexity assessment
- Create installation detection
- Build recommendation engine

### Phase 4: Complete Research System (7 Agents)
- Implement all 7 research agents
- Add AI-powered synthesis
- Create confidence scoring
- Build research history

### Phase 5: Enhanced Custom Instructions
- Add validation rules
- Implement regex patterns
- Create validation engine
- Build context filters

### Phase 6: Advanced Execution System
- Integrate Claude Code cost tracking
- Add session analytics
- Implement error recovery
- Create checkpoint system

### Phase 7: Enhanced UI System
- Show cost breakdown by category
- Display session analytics
- Add progress visualization
- Create rich error displays

### Phase 8: Comprehensive Validation
- Phase validation framework
- Context validation
- Output verification
- Integration testing

### Phase 9: Advanced Utilities
- Performance profiling
- Cost analytics
- Tool metrics
- Memory optimization

### Phase 10: Main Integration
- Wire all components
- Add CLI enhancements
- Create orchestration logic
- Implement resume capability

### Phase 11: Tool Management System
- Performance tracking
- Dependency management
- Success analytics
- Adaptive selection

### Phase 12: Memory Enhancements
- Phase context storage
- Error logging system
- Context accumulation
- Recovery mechanisms

### Phase 13: Testing Framework
- Unit tests for all components
- Integration test suite
- Performance benchmarks
- Cost tracking validation

### Phase 14: Examples and Templates
- Enhanced example projects
- Cost tracking demos
- Research system examples
- MCP configuration templates

### Phase 15: Documentation and Release
- Comprehensive API docs
- Migration guide from v2.2.0
- Feature showcase
- Performance guide

## Key Implementation Details

### Cost Tracking Integration
```python
# In ClaudeCodeExecutor
def parse_cost_from_stream(self, event):
    if event.type == "usage":
        session_data = {
            "session_id": self.current_session_id,
            "duration_ms": self.get_duration_ms(),
            "num_turns": self.turn_count,
            "phase": self.current_phase
        }
        self.cost_tracker.add_claude_code_cost(event.cost, session_data)
```

### Research Agent Integration
```python
# New agents to add
class PerformanceEngineer(ResearchAgent):
    """Performance optimization, scalability, caching"""
    
class DevOpsSpecialist(ResearchAgent):
    """Deployment strategies, containerization, monitoring"""
```

### MCP Discovery
```python
async def discover_installed_servers(self):
    """Check which MCP servers are installed"""
    # Check npm global packages
    # Parse package names
    # Update installed_servers set
```

### Custom Instruction Validation
```python
def validate(self) -> bool:
    """Validate instruction content"""
    for rule in self.validation_rules:
        if not self._check_rule(rule):
            return False
    return True
```

## Success Criteria

1. **Cost Tracking**
   - Claude Code costs tracked separately ✓
   - Research costs identified ✓
   - Session analytics working ✓
   - Backward compatible ✓

2. **Research System**
   - All 7 agents functional ✓
   - AI synthesis working ✓
   - Confidence scoring accurate ✓
   - History preserved ✓

3. **Tool Management**
   - Performance tracked ✓
   - Dependencies managed ✓
   - Analytics collected ✓
   - Selection optimized ✓

4. **All Other Enhancements**
   - MCP discovery working ✓
   - Instructions validated ✓
   - Context managed ✓
   - Memory enhanced ✓

## Output Structure
```
claude-code-builder/
├── claude_code_builder/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── cost_tracker.py      # Enhanced with separation
│   │   ├── phase.py             # Enhanced with context
│   │   ├── memory.py            # Enhanced with error logging
│   │   └── ...
│   ├── research/
│   │   ├── __init__.py
│   │   ├── agents.py            # 7 agents
│   │   ├── manager.py           # AI synthesis
│   │   └── ...
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── manager.py           # Performance tracking
│   │   └── ...
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── discovery.py         # NEW
│   │   ├── recommendation.py    # Enhanced
│   │   └── ...
│   └── ...
├── tests/                       # Comprehensive test suite
├── examples/                    # Enhanced examples
├── docs/                        # Full documentation
├── setup.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Dependencies
- Python 3.8+
- click>=8.1.0
- rich>=13.0.0
- anthropic>=0.18.0
- aiofiles>=23.0.0
- pyyaml>=6.0
- jsonschema>=4.0.0
- pytest>=7.0.0
- pytest-asyncio>=0.21.0
- pytest-cov>=4.0.0

Build an intelligent, production-ready tool that incorporates ALL enhancements from v2.3.0.
EOF
}

# Create enhanced instructions for v2.3.0
create_enhanced_instructions() {
    cat > "instructions-v2.3.md" << 'EOF'
# Critical Implementation Instructions for Claude Code Builder v2.3.0

## MANDATORY REQUIREMENTS

### 1. Code Structure
- Create a **modular Python package structure**, NOT a single file
- Every module must have proper `__init__.py` files with exports
- Use absolute imports: `from claude_code_builder.models import CostTracker`
- Follow PEP 8 strictly with type hints for all functions
- Maximum line length: 100 characters

### 2. No Placeholder Code
- **EVERY function must be fully implemented** - no `pass` statements
- **EVERY class must have complete functionality** - no TODOs
- **EVERY error must be handled** - no bare exceptions
- If you're unsure about implementation, make a reasonable decision and implement it fully

### 3. Enhanced Cost Tracking (v2.3.0)
```python
# MUST implement these exact methods in CostTracker
def add_claude_code_cost(self, cost: float, session_data: Dict[str, Any]) -> None:
    """Track Claude Code execution costs separately"""
    
def get_model_breakdown(self) -> List[Dict[str, Any]]:
    """Get detailed breakdown including Claude Code sessions"""
```

### 4. Research System Requirements
- **MUST implement all 7 research agents**:
  1. TechnologyAnalyst
  2. SecuritySpecialist 
  3. PerformanceEngineer (NEW in v2.3.0)
  4. SolutionsArchitect
  5. BestPracticesAdvisor
  6. QualityAssuranceExpert
  7. DevOpsSpecialist (NEW in v2.3.0)

### 5. Tool Management Enhancements
```python
# MUST add these fields to EnhancedToolManager
tool_dependencies: Dict[str, Set[str]] = defaultdict(set)
disabled_tools: Set[str] = set()
performance_metrics: Dict[str, float] = defaultdict(float)
```

### 6. MCP Discovery Requirements
- Implement `discover_installed_servers()` method
- Add `installed_servers: Set[str]` tracking
- Create `assess_complexity()` for project analysis
- Check npm global packages for MCP servers

### 7. Custom Instructions
- Add `validation_rules: List[str]` field
- Implement `validate()` method
- Support regex patterns with "regex:" prefix
- Handle nested context conditions

### 8. Phase Enhancements
- Add `context: Dict[str, Any]` to Phase class
- Add `validation_results: Dict[str, bool]`
- Implement `validate()` method
- Store context between phases

### 9. Memory Enhancements
- Add `phase_contexts: Dict[str, Dict[str, Any]]`
- Add `error_log: List[Dict[str, Any]]`
- Implement `store_phase_context()`
- Implement `log_error()`
- Implement `get_accumulated_context()`

### 10. Testing Requirements
- Create pytest tests for EVERY public method
- Test files must be in `tests/` directory with `test_` prefix
- Include fixtures for common test data
- Mock external dependencies properly
- Achieve minimum 80% code coverage

### 11. Documentation
- Every public class and method needs docstrings
- Use Google-style docstrings with full parameter descriptions
- Include usage examples in docstrings
- Create comprehensive README.md with all v2.3.0 features

### 12. Error Handling
- Use custom exception classes in `exceptions.py`
- Log all errors with proper context
- Provide helpful error messages to users
- Never let exceptions bubble up unhandled

### 13. Async/Await Patterns
- Use `async/await` for all I/O operations
- Implement proper async context managers
- Handle asyncio cancellation gracefully
- Use `asyncio.gather()` for parallel operations

### 14. Configuration
- All configuration in `config.py` with sensible defaults
- Support environment variables with `CLAUDE_BUILDER_` prefix
- Validate all configuration on startup
- Document all configuration options

### 15. Performance
- Implement streaming for large file operations
- Use connection pooling for API calls
- Cache frequently accessed data appropriately
- Profile and optimize hot paths

## FORBIDDEN PRACTICES

1. **NO placeholder implementations** - Every function must work
2. **NO print statements** - Use proper logging only
3. **NO hardcoded paths** - Everything must be configurable
4. **NO synchronous I/O** in async functions
5. **NO mutable default arguments** in functions
6. **NO broad exception catching** without re-raising
7. **NO code duplication** - Extract common functionality
8. **NO magic numbers** - Use named constants
9. **NO circular imports** - Design proper module hierarchy
10. **NO untested code** - If you write it, test it

## Validation Checklist

Before considering any module complete, verify:

- [ ] All functions have type hints
- [ ] All classes have docstrings
- [ ] All methods are implemented (no TODOs)
- [ ] Error handling is comprehensive
- [ ] Tests exist and pass
- [ ] No linting errors
- [ ] Imports are organized (stdlib, third-party, local)
- [ ] Constants are in UPPER_CASE
- [ ] Private methods start with underscore
- [ ] All v2.3.0 enhancements are included

Remember: This is v2.3.0 - it must include ALL enhancements!
EOF
}

# Create enhanced phases for v2.3.0
create_enhanced_phases() {
    cat > "phases-v2.3.md" << 'EOF'
# Claude Code Builder v2.3.0 - Implementation Phases

## Phase 1: Enhanced Project Foundation
Create the foundational structure with v2.3.0 enhancements:
- Set up package structure with all directories
- Create setup.py with v2.3.0 version
- Create pyproject.toml with all dependencies
- Create requirements.txt with versions
- Initialize git repository
- Create comprehensive .gitignore
- Create __init__.py files with proper exports
- Set up logging configuration
- Create config.py with v2.3.0 settings
- Create exceptions.py with custom exceptions

## Phase 2: Enhanced Data Models
Implement all data models with v2.3.0 enhancements:
- Create cost_tracker.py with Claude Code separation
- Create phase.py with context and validation
- Create memory.py with error logging
- Create build_status.py enum
- Create tool_call.py dataclass
- Create build_stats.py with analytics
- Create research.py models
- Create mcp.py models
- Create instructions.py with validation
- Add all type hints and docstrings

## Phase 3: MCP System with Discovery
Implement the enhanced MCP system:
- Create discovery.py for server detection
- Create recommendation_engine.py with complexity assessment
- Create config_manager.py for MCP configuration
- Create registry.py with known servers
- Implement installed server checking
- Add npm package detection
- Create confidence scoring
- Build configuration templates
- Add server management utilities
- Create MCP validation logic

## Phase 4: Complete Research System
Implement all 7 research agents with enhancements:
- Create base ResearchAgent class
- Implement TechnologyAnalyst
- Implement SecuritySpecialist
- Implement PerformanceEngineer (NEW)
- Implement SolutionsArchitect
- Implement BestPracticesAdvisor
- Implement QualityAssuranceExpert
- Implement DevOpsSpecialist (NEW)
- Create ResearchManager with AI synthesis
- Add confidence scoring and history

## Phase 5: Enhanced Custom Instructions
Build the instruction system with validation:
- Create instruction models with validation rules
- Implement regex pattern support
- Create context filter enhancement
- Build validation engine
- Add instruction loading/parsing
- Create priority handling
- Implement conflict resolution
- Add instruction templates
- Create validation framework
- Build error reporting

## Phase 6: Advanced Execution System
Create the execution engine with cost tracking:
- Create ClaudeCodeExecutor with session tracking
- Implement cost extraction from streams
- Add phase context passing
- Create retry mechanisms
- Build checkpoint system
- Add error recovery
- Implement parallel execution
- Create execution monitoring
- Add resource management
- Build cancellation support

## Phase 7: Enhanced UI System
Build the user interface with rich displays:
- Create progress tracking with categories
- Implement cost breakdown displays
- Add session analytics visualization
- Create error display system
- Build validation reporting
- Add memory usage display
- Create phase timeline
- Implement live updates
- Add export functionality
- Build interactive prompts

## Phase 8: Comprehensive Validation System
Implement validation at all levels:
- Create phase validators
- Build output validators
- Add integration validators
- Create test validators
- Implement metric validators
- Add performance validators
- Create security validators
- Build compatibility validators
- Add regression validators
- Create validation reports

## Phase 9: Advanced Tool Management
Build the enhanced tool system:
- Create tool manager with analytics
- Add performance tracking
- Implement dependency management
- Create success rate tracking
- Add new tools (rename, chmod, etc.)
- Build tool selection logic
- Create fallback mechanisms
- Add tool configuration
- Implement tool testing
- Create tool documentation

## Phase 10: Main Application Integration
Wire everything together:
- Create main.py orchestrator
- Implement CLI with all options
- Add configuration loading
- Create initialization logic
- Build phase execution flow
- Add checkpoint/resume
- Implement graceful shutdown
- Create report generation
- Add metrics collection
- Build final validation

## Phase 11: Enhanced Memory System
Implement advanced memory features:
- Add phase context storage
- Create error logging system
- Implement context accumulation
- Build recovery mechanisms
- Add memory optimization
- Create persistence layer
- Implement memory queries
- Add garbage collection
- Create memory analytics
- Build export functionality

## Phase 12: Testing Framework
Create comprehensive test suite:
- Set up pytest configuration
- Create test fixtures
- Write unit tests for models
- Test cost tracking accuracy
- Test research agents
- Test MCP discovery
- Test instruction validation
- Test phase execution
- Create integration tests
- Add performance benchmarks

## Phase 13: Performance Optimization
Optimize for production use:
- Profile critical paths
- Optimize memory usage
- Improve startup time
- Enhance streaming performance
- Optimize API calls
- Add caching layers
- Improve error handling
- Optimize file operations
- Enhance progress tracking
- Create performance reports

## Phase 14: Examples and Templates
Create comprehensive examples:
- Simple API project example
- Complex microservices example
- CLI tool example
- Web application example
- Cost tracking demonstrations
- Research system examples
- MCP configuration templates
- Custom instruction examples
- Error recovery examples
- Performance optimization guides

## Phase 15: Documentation and Polish
Complete documentation and final touches:
- Write comprehensive README.md
- Create API documentation
- Write migration guide from v2.2.0
- Document all v2.3.0 features
- Create troubleshooting guide
- Write performance guide
- Add architecture diagrams
- Create video tutorials
- Write blog post
- Prepare release notes

Each phase builds upon previous phases and includes all v2.3.0 enhancements.
EOF
}

# Create detailed tasks for each phase
create_enhanced_tasks() {
    cat > "tasks-v2.3.md" << 'EOF'
# Detailed Tasks for Claude Code Builder v2.3.0

## Phase 1 Tasks: Enhanced Project Foundation

### Package Structure
- Create claude_code_builder/ directory
- Create all subdirectories: models/, research/, execution/, ui/, validation/, utils/, instructions/, mcp/, tools/
- Create __init__.py in every directory with proper __all__ exports
- Create __version__ = "2.3.0" in main __init__.py

### Configuration Files
- Create setup.py with all v2.3.0 metadata
- Create pyproject.toml with [build-system] and [project] sections
- Add all dependencies with minimum versions
- Create requirements.txt from pyproject.toml
- Create requirements-dev.txt with test dependencies

### Project Files
- Create README.md with v2.3.0 feature list
- Create LICENSE file (MIT)
- Create .gitignore with Python patterns
- Create .github/workflows/test.yml for CI
- Create CHANGELOG.md with v2.3.0 changes

### Core Files
- Create config.py with DEFAULT_MODEL, TOKEN_COSTS, etc.
- Create exceptions.py with custom exception hierarchy
- Create logging_config.py with rich logging setup
- Create constants.py with all string constants

## Phase 2 Tasks: Enhanced Data Models

### Cost Tracker Enhancement
```python
# In cost_tracker.py, must include:
- total_cost: float = 0.0
- claude_code_cost: float = 0.0
- research_cost: float = 0.0
- claude_code_sessions: List[Dict[str, Any]] = field(default_factory=list)
- add_claude_code_cost(cost: float, session_data: Dict[str, Any])
- get_model_breakdown() -> List[Dict[str, Any]]
- analysis_cost property
```

### Phase Model Enhancement
```python
# In phase.py, must include:
- context: Dict[str, Any] = field(default_factory=dict)
- validation_results: Dict[str, bool] = field(default_factory=dict)
- validate() -> bool method
- add_context(key: str, value: Any)
```

### Memory Model Enhancement
```python
# In memory.py, must include:
- phase_contexts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
- error_log: List[Dict[str, Any]] = field(default_factory=list)
- store_phase_context(phase_id: str, context: Dict[str, Any])
- log_error(error: str, phase_id: Optional[str] = None)
- get_accumulated_context(up_to_phase: str) -> Dict[str, Any]
```

## Phase 3 Tasks: MCP System with Discovery

### Discovery Implementation
- Create discover_installed_servers() async method
- Implement npm list parsing for global packages
- Add installed_servers: Set[str] tracking
- Create package name extraction logic
- Handle different package naming patterns

### Complexity Assessment
- Create assess_complexity(specification: str) -> str
- Count complexity indicators (microservices, distributed, etc.)
- Calculate word count thresholds
- Return "low", "medium", or "high"

### Enhanced Recommendations
- Update confidence calculation with installation status
- Add complexity-based recommendations
- Improve pattern matching for technologies
- Create better recommendation reasons

## Phase 4 Tasks: Complete Research System

### New Research Agents
```python
# PerformanceEngineer must include:
- Focus: performance optimization, scalability, caching
- analyze() method returning performance recommendations
- Specific prompts for performance analysis

# DevOpsSpecialist must include:
- Focus: deployment, containerization, monitoring
- analyze() method returning deployment strategies
- Infrastructure recommendations
```

### Research Enhancement
- Implement AI-powered synthesis
- Add confidence scoring to all agents
- Create research history tracking
- Build agent assignment logic
- Add parallel research execution

## Phase 5-15 Tasks: [Detailed tasks for remaining phases...]

Each task must be fully implemented with no placeholders or TODOs.
EOF
}

# Initialize directories and logs
initialize_build_environment() {
    mkdir -p "$JSON_OUTPUT_DIR" "$METRICS_DIR"
    echo "Claude Code Builder v$VERSION Build Script Log - $(date)" > "$VALIDATION_LOG"
    echo "Build Progress - $(date)" > "$HUMAN_LOG"
    
    # Create all specification files
    create_enhanced_specification
    create_enhanced_instructions
    create_enhanced_phases
    create_enhanced_tasks
    
    log_phase "INIT" "Created enhanced v2.3.0 specifications"
}

# State management functions
save_state() {
    local phase=$1
    local status=$2
    local details="${3:-}"
    local retry_count="${4:-0}"
    local elapsed=$(($(date +%s) - START_TIME))
    
    cat > "$STATE_FILE" <<EOF
{
    "version": "$VERSION",
    "project_name": "$PROJECT_NAME",
    "current_phase": $phase,
    "total_phases": $TOTAL_PHASES,
    "status": "$status",
    "details": "$details",
    "retry_count": $retry_count,
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "elapsed_seconds": $elapsed,
    "start_time": $START_TIME,
    "working_directory": "$(pwd)",
    "last_session_id": "${LAST_SESSION_ID:-}",
    "metrics": {
        "total_api_calls": $TOTAL_API_CALLS,
        "total_tokens": $TOTAL_TOKENS_USED,
        "total_cost": $TOTAL_COST,
        "claude_code_cost": $CLAUDE_CODE_COST,
        "research_cost": $RESEARCH_COST
    }
}
EOF
}

load_state() {
    if [ ! -f "$STATE_FILE" ]; then
        return 1
    fi
    
    # Validate JSON before parsing
    if ! jq . "$STATE_FILE" >/dev/null 2>&1; then
        log_warning "State file is corrupted, starting fresh"
        rm -f "$STATE_FILE"
        return 1
    }
    
    # Check version compatibility
    local saved_version=$(jq -r '.version // "2.2.0"' "$STATE_FILE")
    if [ "$saved_version" != "$VERSION" ]; then
        log_warning "State file is from version $saved_version, current version is $VERSION"
        log_info "Starting fresh build for v$VERSION"
        rm -f "$STATE_FILE"
        return 1
    fi
    
    CURRENT_PHASE=$(jq -r '.current_phase // 0' "$STATE_FILE")
    PHASE_RETRY_COUNT=$(jq -r '.retry_count // 0' "$STATE_FILE")
    LAST_SESSION_ID=$(jq -r '.last_session_id // empty' "$STATE_FILE")
    CLAUDE_CODE_COST=$(jq -r '.metrics.claude_code_cost // "0.0"' "$STATE_FILE")
    RESEARCH_COST=$(jq -r '.metrics.research_cost // "0.0"' "$STATE_FILE")
    local saved_start_time=$(jq -r '.start_time // empty' "$STATE_FILE")
    
    if [ -n "$saved_start_time" ]; then
        START_TIME=$saved_start_time
        RESUMED=true
    fi
    
    return 0
}

# Enhanced MCP configuration for v2.3.0
setup_enhanced_mcp_servers() {
    log_phase "START" "Setting up enhanced MCP servers for v2.3.0"
    
    cat > "$MCP_CONFIG_FILE" << 'EOF'
{
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
            "description": "File system operations with enhanced capabilities"
        },
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "description": "Memory storage with context preservation"
        },
        "sequential-thinking": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            "description": "Complex problem solving and planning"
        },
        "git": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-git"],
            "description": "Version control for progress tracking"
        }
    }
}
EOF
    
    log_phase "SUCCESS" "Enhanced MCP configuration created"
}

# Phase-specific prompts for v2.3.0
get_enhanced_phase_prompt() {
    local phase_num=$1
    local phase_content=""
    local phase_instruction=""
    
    case $phase_num in
        1)
            phase_instruction="Create the enhanced project foundation with v2.3.0 structure and configuration."
            ;;
        2)
            phase_instruction="Implement all data models with v2.3.0 enhancements including separated cost tracking."
            ;;
        3)
            phase_instruction="Build the MCP system with server discovery and complexity assessment."
            ;;
        4)
            phase_instruction="Implement all 7 research agents including PerformanceEngineer and DevOpsSpecialist."
            ;;
        5)
            phase_instruction="Create the enhanced custom instructions system with validation rules and regex support."
            ;;
        6)
            phase_instruction="Build the advanced execution system with Claude Code cost tracking and session analytics."
            ;;
        7)
            phase_instruction="Create the enhanced UI system with cost breakdown displays and rich visualizations."
            ;;
        8)
            phase_instruction="Implement the comprehensive validation system with phase and output validators."
            ;;
        9)
            phase_instruction="Build the advanced tool management system with performance tracking and analytics."
            ;;
        10)
            phase_instruction="Create the main application integration with CLI and orchestration logic."
            ;;
        11)
            phase_instruction="Implement the enhanced memory system with phase contexts and error logging."
            ;;
        12)
            phase_instruction="Create the comprehensive testing framework with unit and integration tests."
            ;;
        13)
            phase_instruction="Perform performance optimization and profiling."
            ;;
        14)
            phase_instruction="Create examples and templates showcasing v2.3.0 features."
            ;;
        15)
            phase_instruction="Complete documentation and prepare for release."
            ;;
    esac
    
    # Load phase details from files
    local phase_details=$(grep -A 20 "^## Phase $phase_num:" phases-v2.3.md || echo "")
    local phase_tasks=$(grep -A 50 "^## Phase $phase_num Tasks:" tasks-v2.3.md || echo "")
    
    # Build the complete prompt
    echo "PHASE $phase_num of $TOTAL_PHASES: $phase_instruction

$phase_details

SPECIFIC TASKS:
$phase_tasks

CRITICAL REQUIREMENTS:
- Every function must be fully implemented (no placeholders)
- Include all v2.3.0 enhancements as specified
- Follow the instructions in instructions-v2.3.md exactly
- Create proper tests for new functionality
- Use type hints and docstrings everywhere

AVAILABLE MCP TOOLS:
- filesystem__read_file/write_file for file operations
- memory__create_memory/retrieve_memory for state management
- sequential_thinking__think_about for complex planning
- git__status/add/commit for version control

Remember: This is v2.3.0 - include ALL enhancements!"
}

# Execute phase with validation
execute_enhanced_phase() {
    local phase_num=$1
    local phase_name=""
    
    case $phase_num in
        1) phase_name="Enhanced Project Foundation" ;;
        2) phase_name="Enhanced Data Models" ;;
        3) phase_name="MCP System with Discovery" ;;
        4) phase_name="Complete Research System (7 Agents)" ;;
        5) phase_name="Enhanced Custom Instructions" ;;
        6) phase_name="Advanced Execution System" ;;
        7) phase_name="Enhanced UI System" ;;
        8) phase_name="Comprehensive Validation" ;;
        9) phase_name="Advanced Tool Management" ;;
        10) phase_name="Main Application Integration" ;;
        11) phase_name="Enhanced Memory System" ;;
        12) phase_name="Testing Framework" ;;
        13) phase_name="Performance Optimization" ;;
        14) phase_name="Examples and Templates" ;;
        15) phase_name="Documentation and Release" ;;
    esac
    
    log_phase "START" "Phase $phase_num: $phase_name"
    
    local prompt=$(get_enhanced_phase_prompt $phase_num)
    
    # Execute with Claude
    local temp_prompt=$(mktemp)
    echo "$prompt" > "$temp_prompt"
    
    # Build command with enhanced cost tracking
    local claude_cmd="claude --print --model $MODEL"
    claude_cmd+=" --mcp-config $MCP_CONFIG_FILE"
    claude_cmd+=" --dangerously-skip-permissions"
    claude_cmd+=" --output-format stream-json"
    claude_cmd+=" --verbose"
    claude_cmd+=" --max-turns $MAX_TURNS"
    
    # Execute and track costs
    local start_time=$(date +%s)
    cat "$temp_prompt" | eval $claude_cmd 2>&1 | parse_enhanced_stream $phase_num
    local exit_code=${PIPESTATUS[1]}
    local duration=$(($(date +%s) - start_time))
    
    rm -f "$temp_prompt"
    
    if [ $exit_code -eq 0 ]; then
        log_phase "SUCCESS" "Phase $phase_num completed in ${duration}s"
        CURRENT_PHASE=$((phase_num + 1))
        save_state $CURRENT_PHASE "ready" "Phase $phase_num completed"
        return 0
    else
        log_phase "ERROR" "Phase $phase_num failed"
        return 1
    fi
}

# Enhanced stream parser for v2.3.0
parse_enhanced_stream() {
    local phase_num=$1
    local line
    local turn_count=0
    local session_cost=0.0
    
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        
        # Try to parse as JSON
        if echo "$line" | jq -e . >/dev/null 2>&1; then
            local type=$(echo "$line" | jq -r '.type // empty')
            
            case $type in
                "system")
                    local session_id=$(echo "$line" | jq -r '.session_id // empty')
                    if [ -n "$session_id" ]; then
                        LAST_SESSION_ID=$session_id
                        log_info "Session: $session_id"
                    fi
                    ;;
                
                "assistant")
                    # Track turns for session analytics
                    ((turn_count++))
                    
                    # Check for tool use
                    local tool_name=$(echo "$line" | jq -r '.message.content[]? | select(.type == "tool_use") | .name // empty' 2>/dev/null)
                    if [ -n "$tool_name" ]; then
                        log_info "Tool: $tool_name"
                        ((TOTAL_API_CALLS++))
                    fi
                    ;;
                
                "result")
                    # Extract cost information
                    local cost=$(echo "$line" | jq -r '.cost // empty' 2>/dev/null)
                    if [ -n "$cost" ]; then
                        session_cost=$cost
                        TOTAL_COST=$(echo "$TOTAL_COST + $cost" | bc)
                        CLAUDE_CODE_COST=$(echo "$CLAUDE_CODE_COST + $cost" | bc)
                        
                        log_phase "COST" "Session cost: \$$cost (Total: \$$TOTAL_COST)"
                        log_info "Claude Code: \$$CLAUDE_CODE_COST | Research: \$$RESEARCH_COST"
                    fi
                    
                    # Extract token usage
                    local tokens=$(echo "$line" | jq -r '.usage.total_tokens // empty' 2>/dev/null)
                    if [ -n "$tokens" ]; then
                        TOTAL_TOKENS_USED=$((TOTAL_TOKENS_USED + tokens))
                    fi
                    ;;
            esac
        fi
    done
    
    # Log phase metrics
    if [ "$turn_count" -gt 0 ]; then
        log_info "Phase $phase_num: $turn_count turns, \$$session_cost"
    fi
}

# Main execution
main() {
    clear
    show_banner
    
    log_info "Claude Code Builder v$VERSION - Enhanced Build Script"
    log_info "Building with model: $MODEL"
    log_info "Output directory: $OUTPUT_DIR"
    
    # Check prerequisites
    for cmd in claude jq git npm; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd not found. Please install it first."
            exit 1
        fi
    done
    
    # Move to output directory
    cd "$OUTPUT_DIR"
    
    # Create project directory
    if [ ! -d "$PROJECT_NAME" ]; then
        mkdir -p "$PROJECT_NAME"
    fi
    cd "$PROJECT_NAME"
    
    log_info "Building in: $(pwd)"
    
    # Initialize or resume
    if [ "$RESUME_BUILD" = true ] && load_state; then
        log_phase "INIT" "Resuming build from phase $CURRENT_PHASE"
    else
        log_phase "INIT" "Starting fresh v$VERSION build"
        initialize_build_environment
        setup_enhanced_mcp_servers
        CURRENT_PHASE=1
        save_state 1 "ready" "Build initialized"
    fi
    
    # Execute phases
    while [ $CURRENT_PHASE -le $TOTAL_PHASES ]; do
        if execute_enhanced_phase $CURRENT_PHASE; then
            log_success "Phase $CURRENT_PHASE completed successfully"
        else
            ((PHASE_RETRY_COUNT++))
            if [ $PHASE_RETRY_COUNT -lt $MAX_PHASE_RETRIES ]; then
                log_warning "Retrying phase $CURRENT_PHASE (attempt $PHASE_RETRY_COUNT/$MAX_PHASE_RETRIES)"
                sleep $RETRY_DELAY
            else
                log_error "Phase $CURRENT_PHASE failed after $MAX_PHASE_RETRIES attempts"
                exit 1
            fi
        fi
    done
    
    # Final summary
    local elapsed=$(($(date +%s) - START_TIME))
    echo -e "\n${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Build Complete! Claude Code Builder v$VERSION${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "Total time: $((elapsed/60))m $((elapsed%60))s"
    echo -e "Total cost: \$$TOTAL_COST"
    echo -e "  - Claude Code: \$$CLAUDE_CODE_COST"
    echo -e "  - Research: \$$RESEARCH_COST"
    echo -e "API calls: $TOTAL_API_CALLS"
    echo -e "Tokens used: $TOTAL_TOKENS_USED"
    echo -e "\nNext steps:"
    echo -e "  1. cd $PROJECT_NAME"
    echo -e "  2. pip install -e ."
    echo -e "  3. claude-code-builder --help"
}

# Signal handlers
trap 'log_warning "Build interrupted"; save_state $CURRENT_PHASE "interrupted" "User interrupted"; exit 130' SIGINT SIGTERM

# Run main
main "$@"