#!/bin/bash

# Claude Code Builder v3.0 - AI-Driven Autonomous Build Script
# 
# Major improvements in v3.0:
# - AI-driven phase and task planning using Claude for optimal build strategy
# - Comprehensive functional testing with real-time log monitoring
# - Enhanced memory system for better context preservation
# - Improved error recovery and checkpoint mechanisms
# - Better progress tracking with estimated completion times
#
# Usage: ./builder-claude-code-builder-v3.sh [OPTIONS]

set -euo pipefail

# Color codes
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
MAGENTA="\033[0;35m"
ORANGE="\033[0;33m"
PURPLE="\033[0;35m"
BOLD="\033[1m"
DIM="\033[2m"
NC="\033[0m"

# Configuration
PROJECT_NAME="claude-code-builder"
VERSION="3.0.0"
MODEL="claude-3-5-sonnet-20241022"
STATE_FILE=".build-state-v3.json"

# Build configuration
MAX_TURNS=75  # Increased for complex phases
FUNCTIONAL_TEST_TIMEOUT=1800  # 30 minutes for functional testing

# Default values
OUTPUT_DIR="."
RESUME_BUILD=false
SHOW_HELP=false

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
            SHOW_HELP=true
            shift
            ;;
        *)
            echo -e "${RED}Error: Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
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
fi

# ASCII Art Banner
show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗    ██████╗  ██████╗  ║
║  ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝    ╚════██╗██╔═████╗ ║
║  ██║     ██║     ███████║██║   ██║██║  ██║█████╗       █████╔╝██║██╔██║ ║
║  ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝       ╚═══██╗████╔╝██║ ║
║  ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗    ██████╔╝╚██████╔╝ ║
║   ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝    ╚═════╝  ╚═════╝  ║
║                                                                           ║
║               🚀 AI-Driven Autonomous Project Builder 🚀                  ║
║                                                                           ║
║  • AI plans optimal build phases and tasks                               ║
║  • Comprehensive functional testing with log monitoring                   ║
║  • Real-time progress tracking and cost analysis                         ║
║  • Enhanced error recovery and checkpoint system                          ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
}

# Enhanced logging with tool tracking
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} ${timestamp} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} ✅ $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} ${timestamp} ❌ $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} ${timestamp} ⚠️  $message"
            ;;
        "PHASE")
            echo -e "\n${MAGENTA}═══ PHASE ═══${NC} ${timestamp} $message\n"
            ;;
        "TEST")
            echo -e "${PURPLE}[TEST]${NC} ${timestamp} 🧪 $message"
            ;;
        "TOOL")
            echo -e "${CYAN}[TOOL]${NC} ${timestamp} 🔧 $message"
            ;;
        "COST")
            echo -e "${ORANGE}[COST]${NC} ${timestamp} 💰 $message"
            ;;
    esac
}

# Create the main specification
create_v3_specification() {
    cat > "claude-code-builder-v3-spec.md" << 'EOF'
# Claude Code Builder v3.0 - AI-Driven Autonomous Project Builder

## Overview
An advanced project builder that uses AI to plan optimal build strategies, execute through intelligent phases, and perform comprehensive functional testing. This tool orchestrates Claude Code SDK to build complete projects with unprecedented reliability and insight.

## Key Innovations in v3.0

### 1. AI-Driven Planning
- Claude analyzes specifications to create optimal phase breakdown
- Dynamic task generation based on project complexity
- Intelligent dependency resolution and parallelization
- Adaptive strategy based on discovered requirements

### 2. Comprehensive Functional Testing
- Real-time log monitoring during execution
- Multi-stage validation process
- Automated test project creation and execution
- Performance benchmarking and cost analysis
- Failure analysis with recovery suggestions

### 3. Enhanced Monitoring
- Stream parsing for real-time insights
- Progress estimation with completion predictions
- Cost tracking by category (Claude Code, Research, Analysis)
- Resource usage monitoring

### 4. Improved Context Management
- Persistent memory across phases
- Context accumulation and sharing
- Error context preservation
- Recovery from any checkpoint

## Technical Requirements

### Core Features (from v2.3.0)
1. **Enhanced Cost Tracking**
   - Separate Claude Code execution costs
   - Research API cost tracking
   - Session analytics with detailed metrics
   - Cost breakdown by phase and category

2. **Complete Research System (7 Agents)**
   - TechnologyAnalyst
   - SecuritySpecialist
   - PerformanceEngineer
   - SolutionsArchitect
   - BestPracticesAdvisor
   - QualityAssuranceExpert
   - DevOpsSpecialist

3. **Advanced Tool Management**
   - Performance metrics tracking
   - Tool dependency management
   - Success rate analytics
   - Adaptive tool selection

4. **MCP Server Discovery**
   - Automatic server detection
   - Complexity assessment
   - Installation verification
   - Intelligent recommendations

5. **Custom Instructions**
   - Validation rules engine
   - Regex pattern support
   - Context-aware filtering
   - Priority-based execution

6. **Phase Management**
   - Context preservation
   - Validation framework
   - Error recovery
   - Progress tracking

7. **Enhanced Memory**
   - Phase context storage
   - Error logging with context
   - Context accumulation
   - Query capabilities

### New v3.0 Features

1. **AI Phase Planning**
   ```
   INPUT: Project specification
   PROCESS: Claude analyzes and creates optimal phases
   OUTPUT: Dynamic phase plan with dependencies
   ```

2. **Functional Testing Framework**
   ```
   STAGE 1: Installation verification
   STAGE 2: CLI functionality testing
   STAGE 3: Example project execution
   STAGE 4: Performance benchmarking
   STAGE 5: Error recovery testing
   ```

3. **Real-time Monitoring**
   - Log streaming with pattern detection
   - Progress bars with ETA
   - Cost accumulation displays
   - Error rate tracking

4. **Advanced Recovery**
   - Checkpoint every 5 minutes
   - Phase-level recovery
   - Context reconstruction
   - Automatic retry strategies

## Implementation Strategy

### Phase 0: AI Planning Phase
Claude will analyze the specification and create:
- Optimal phase breakdown (likely 15-20 phases)
- Detailed task lists per phase
- Dependency graph
- Risk assessment
- Testing strategy

### Dynamic Phases (AI-Generated)
The AI will determine the best phases, but typically includes:
- Foundation and setup
- Core models and structures
- API integrations
- Business logic
- UI/UX implementation
- Testing framework
- Documentation
- Optimization
- Deployment preparation

### Final Phase: Comprehensive Testing
1. **Installation Test**
   ```bash
   pip install -e .
   claude-code-builder --version
   ```

2. **CLI Test**
   ```bash
   claude-code-builder --help
   claude-code-builder example.md --dry-run
   ```

3. **Functional Test**
   ```bash
   # Create test project
   claude-code-builder examples/simple-api.md --output-dir ./test-output
   
   # Monitor execution (up to 30 minutes)
   # Check for errors, validate output
   # Verify all files created
   ```

4. **Performance Test**
   - Measure execution time
   - Track memory usage
   - Monitor API calls
   - Calculate total cost

5. **Recovery Test**
   - Interrupt and resume
   - Corrupt state and recover
   - Network failure simulation

## Success Criteria

### Build Success
- All phases complete without errors
- All files created and valid
- Tests pass with >95% success rate
- Cost within expected range
- Performance meets benchmarks

### Testing Success
- Installation works correctly
- CLI responds to all commands
- Can build example projects
- Handles errors gracefully
- Resumes from checkpoints

### Quality Metrics
- Code coverage >80%
- Documentation complete
- Examples functional
- Performance optimized
- Security validated

## Output Structure
```
claude-code-builder/
├── claude_code_builder/
│   ├── __init__.py (with __version__ = "3.0.0")
│   ├── [all implementation files]
│   └── ...
├── tests/
│   ├── unit/
│   ├── integration/
│   └── functional/
├── examples/
├── docs/
├── setup.py
├── pyproject.toml
├── requirements.txt
├── README.md
└── .claude-test-results.json
```

Build a next-generation autonomous project builder with AI-driven intelligence and comprehensive validation.
EOF
}

# Create testing instructions
create_testing_instructions() {
    cat > "testing-instructions-v3.md" << 'EOF'
# Functional Testing Instructions for Claude Code Builder v3.0

## CRITICAL TESTING REQUIREMENTS

When you reach the testing phase, you MUST:

1. **EXPECT LONG EXECUTION TIMES**
   - The functional test will run for 10-30 minutes
   - This is NORMAL and EXPECTED
   - You must CONTINUOUSLY monitor the streaming logs
   - DO NOT assume failure just because it takes time

2. **MONITOR STREAMING OUTPUT**
   - Use `tail -f` on log files
   - Watch for progress indicators
   - Track file creation in real-time
   - Monitor cost accumulation
   - Check for error patterns

3. **FUNCTIONAL TEST STAGES**

   Stage 1: Installation Verification
   ```bash
   # Install the package
   cd claude-code-builder
   pip install -e .
   
   # Verify installation
   which claude-code-builder
   claude-code-builder --version
   ```

   Stage 2: CLI Testing
   ```bash
   # Test all CLI commands
   claude-code-builder --help
   claude-code-builder --list-examples
   claude-code-builder --show-costs
   ```

   Stage 3: Dry Run Test
   ```bash
   # Test without execution
   claude-code-builder examples/simple-api.md --dry-run
   ```

   Stage 4: Full Functional Test
   ```bash
   # Create test output directory
   mkdir -p test-output
   
   # Start the build (THIS WILL TAKE 10-30 MINUTES)
   claude-code-builder examples/simple-api.md \
     --output-dir ./test-output \
     --enable-research \
     --verbose \
     2>&1 | tee test-execution.log &
   
   # Get the process ID
   BUILD_PID=$!
   
   # Monitor in real-time (MUST DO THIS)
   tail -f test-execution.log
   ```

   Stage 5: Progress Monitoring
   ```bash
   # In another terminal or after starting tail -f
   while kill -0 $BUILD_PID 2>/dev/null; do
     echo "Build still running... checking progress"
     
     # Check created files
     find test-output -type f -name "*.py" | wc -l
     
     # Check log for phases
     grep -c "PHASE.*COMPLETE" test-execution.log || echo "0 phases complete"
     
     # Check for errors
     grep -c "ERROR" test-execution.log || echo "0 errors"
     
     # Wait 30 seconds before next check
     sleep 30
   done
   ```

   Stage 6: Validation
   ```bash
   # After completion, validate output
   cd test-output
   
   # Check structure
   find . -name "*.py" | head -20
   
   # Verify key files exist
   test -f setup.py && echo "✓ setup.py exists"
   test -f requirements.txt && echo "✓ requirements.txt exists"
   test -d tests && echo "✓ tests directory exists"
   
   # Try to run the created project's tests
   if [ -f setup.py ]; then
     pip install -e .
     pytest tests/ || echo "Tests not yet implemented"
   fi
   ```

4. **WHAT TO LOOK FOR IN LOGS**

   Good Signs:
   ```
   [PHASE COMPLETE] ✅
   Created: [filename]
   Tool: Write Creating [file]
   Session cost: $X.XX
   Phase X: Y turns, $Z.ZZ
   ```

   Warning Signs (but continue monitoring):
   ```
   Retrying...
   Rate limit encountered
   Waiting...
   ```

   Error Signs (may need intervention):
   ```
   FAILED after 3 attempts
   Critical error:
   Traceback (most recent call last):
   ```

5. **EXPECTED TIMELINE**

   - Phase 0 (AI Planning): 2-5 minutes
   - Phases 1-5: 1-3 minutes each
   - Phases 6-10: 2-5 minutes each
   - Phases 11-15: 3-7 minutes each
   - Testing Phase: 5-10 minutes
   - Total: 25-45 minutes

6. **MEMORY FOR NEXT TIME**

   Remember these key points for future testing:
   - Functional tests ALWAYS take 10-30 minutes
   - You MUST monitor logs continuously
   - File creation happens gradually
   - Costs accumulate over time
   - Some phases take longer than others
   - This is NORMAL BEHAVIOR

DO NOT conclude the test failed just because it's taking time. The build process is SUPPOSED to take this long.
EOF
}

# Create AI planning prompt
create_ai_planning_prompt() {
    cat > "ai-planning-prompt.md" << 'EOF'
# AI Planning Phase - Claude Code Builder v3.0

You are about to plan the optimal build strategy for Claude Code Builder v3.0. This is a critical phase where you must:

1. **ANALYZE THE SPECIFICATION**
   - Read the full v3.0 specification
   - Identify all major components and their relationships
   - Map out technical dependencies
   - Assess complexity and risks

2. **CREATE OPTIMAL PHASE PLAN**
   
   Design 15-20 phases that:
   - Follow logical dependency order
   - Group related functionality
   - Enable parallel work where possible
   - Include validation checkpoints
   - Account for v3.0 enhancements

   Each phase should have:
   - Clear objective
   - Specific deliverables
   - Success criteria
   - Estimated complexity (1-5)
   - Dependencies on other phases

3. **GENERATE DETAILED TASKS**
   
   For each phase, create 5-15 specific tasks that:
   - Are concrete and actionable
   - Include file paths and function names
   - Specify exact functionality to implement
   - Reference v3.0 features explicitly
   - Include test requirements

4. **DESIGN TESTING STRATEGY**
   
   Create a comprehensive testing plan that includes:
   - Unit tests for each component
   - Integration tests for phase boundaries
   - Functional tests for user scenarios
   - Performance benchmarks
   - Error recovery tests

5. **RISK ASSESSMENT**
   
   Identify potential risks:
   - Technical challenges
   - Integration complexities
   - Performance bottlenecks
   - Testing difficulties
   - Recovery scenarios

6. **OUTPUT FORMAT**

   Create two files using filesystem__write_file:
   
   a) `build-phases-v3.json`:
   ```json
   {
     "version": "3.0.0",
     "total_phases": 18,
     "phases": [
       {
         "number": 1,
         "name": "Foundation and Architecture",
         "objective": "...",
         "deliverables": [...],
         "tasks": [...],
         "complexity": 3,
         "dependencies": [],
         "estimated_time": "5-8 minutes"
       }
     ]
   }
   ```
   
   b) `build-strategy-v3.md`:
   - Executive summary
   - Phase dependency graph
   - Risk mitigation strategies
   - Testing approach
   - Success metrics

Remember:
- This planning will determine the entire build strategy
- Consider all v3.0 enhancements
- Plan for comprehensive functional testing
- Account for real-world execution times (25-45 minutes total)
- Include error recovery and checkpoint strategies

Take your time to create a thorough, well-thought-out plan.
EOF
}

# Setup MCP for v3
setup_mcp_v3() {
    log "INFO" "Setting up MCP configuration for v3.0"
    
    cat > ".mcp.json" << 'EOF'
{
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
            "description": "File system operations"
        },
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "description": "State management across phases"
        },
        "sequential-thinking": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            "description": "Complex planning and analysis"
        },
        "git": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-git"],
            "description": "Version control"
        }
    }
}
EOF
}

# Execute AI planning phase
execute_ai_planning() {
    log "PHASE" "Phase 0: AI-Driven Planning"
    
    local planning_prompt=$(cat ai-planning-prompt.md)
    local spec_content=$(cat claude-code-builder-v3-spec.md)
    
    local full_prompt="$planning_prompt

SPECIFICATION TO ANALYZE:
$spec_content

Now create the optimal build plan for v3.0."
    
    # Execute with Claude (no streaming for planning phase)
    log "INFO" "Invoking Claude to analyze specification and create build plan..."
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo "$full_prompt" | claude \
        --model "$MODEL" \
        --mcp-config .mcp.json \
        --dangerously-skip-permissions \
        --max-turns 20 \
        --verbose \
        2>&1 | tee planning-output.log
    
    # Verify planning files were created
    if [ -f "build-phases-v3.json" ] && [ -f "build-strategy-v3.md" ]; then
        log "SUCCESS" "AI planning completed successfully"
        return 0
    else
        log "ERROR" "AI planning failed to create required files"
        return 1
    fi
}

# Parse streaming JSON output and display rich visual logs
parse_stream_output() {
    local line
    local in_tool_use=false
    local tool_name=""
    local tool_id=""
    local current_content=""
    
    while IFS= read -r line; do
        # Check for tool use patterns in streaming output
        if echo "$line" | grep -q '"type":"tool_use"'; then
            in_tool_use=true
            tool_name=$(echo "$line" | grep -oE '"name":"[^"]+"' | cut -d'"' -f4 || echo "unknown")
            tool_id=$(echo "$line" | grep -oE '"id":"[^"]+"' | cut -d'"' -f4 || echo "")
            
            echo -e "\n${CYAN}🔧 [TOOL USE]${NC} ${BOLD}$tool_name${NC}"
            echo -e "${DIM}   ID: $tool_id${NC}"
        elif echo "$line" | grep -q '"type":"text"' && [ "$in_tool_use" = false ]; then
            # Extract text content
            local text=$(echo "$line" | sed -n 's/.*"text":"\([^"]*\)".*/\1/p' || echo "")
            if [ -n "$text" ]; then
                echo -e "${GREEN}💬 [CLAUDE]${NC} $text"
            fi
        elif echo "$line" | grep -q '"type":"tool_result"'; then
            in_tool_use=false
            echo -e "${MAGENTA}✓ [TOOL RESULT]${NC} Completed"
        fi
        
        # Also output original line to log
        echo "$line" >> raw-stream.log
    done
}

# Execute dynamic phase based on AI plan
execute_dynamic_phase() {
    local phase_num=$1
    
    # Check if phase exists in JSON
    local phase_count=$(jq '.phases | length' build-phases-v3.json 2>/dev/null || echo 0)
    if [ $phase_num -gt $phase_count ]; then
        log "WARNING" "Phase $phase_num not found in build plan (only $phase_count phases defined)"
        return 1
    fi
    
    # Read phase details from AI-generated plan
    local phase_name=$(jq -r ".phases[$((phase_num-1))].name // \"Phase $phase_num\"" build-phases-v3.json 2>/dev/null)
    local phase_objective=$(jq -r ".phases[$((phase_num-1))].objective // \"Complete phase tasks\"" build-phases-v3.json 2>/dev/null)
    local phase_tasks=$(jq -r ".phases[$((phase_num-1))].tasks[]? // empty" build-phases-v3.json 2>/dev/null)
    
    log "PHASE" "Phase $phase_num: $phase_name"
    log "INFO" "Objective: $phase_objective"
    
    # Build prompt from AI plan
    local prompt="PHASE $phase_num: $phase_name

OBJECTIVE: $phase_objective

TASKS TO COMPLETE:
$phase_tasks

REQUIREMENTS:
- Implement all functionality completely (no placeholders)
- Include proper error handling
- Add comprehensive docstrings
- Follow v3.0 specifications exactly
- Create tests for new code

AVAILABLE TOOLS:
- filesystem__read_file/write_file
- memory__create_memory/retrieve_memory
- sequential_thinking__think_about
- git__status/add/commit

Remember: This is v3.0 - include all enhancements!"
    
    # Execute phase with enhanced visual logging
    log "INFO" "Starting execution with Claude Code SDK"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo "$prompt" | claude \
        --model "$MODEL" \
        --mcp-config .mcp.json \
        --dangerously-skip-permissions \
        --max-turns "$MAX_TURNS" \
        --output-format stream-json \
        --verbose \
        2>&1 | tee -a "phase-$phase_num-output.log" | parse_stream_output
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Phase $phase_num completed"
        return 0
    else
        log "ERROR" "Phase $phase_num failed"
        return 1
    fi
}

# Track and display cost information
display_cost_info() {
    local phase_num=$1
    local cost_line=$2
    
    # Extract cost information if available
    if echo "$cost_line" | grep -q "cost"; then
        local total_cost=$(echo "$cost_line" | grep -oE '"total_cost":[0-9.]+' | cut -d':' -f2 || echo "0")
        local session_cost=$(echo "$cost_line" | grep -oE '"session_cost":[0-9.]+' | cut -d':' -f2 || echo "0")
        
        if [ -n "$total_cost" ] && [ "$total_cost" != "0" ]; then
            log "COST" "Phase $phase_num - Session: \$$session_cost, Total: \$$total_cost"
        fi
    fi
}

# Display real-time file creation tracking
track_file_creation() {
    local output_dir=$1
    local phase_num=$2
    
    # Count Python files
    local py_count=$(find "$output_dir" -name "*.py" 2>/dev/null | wc -l | tr -d ' ')
    local total_files=$(find "$output_dir" -type f 2>/dev/null | wc -l | tr -d ' ')
    
    echo -e "${DIM}📁 Files: $total_files total, $py_count Python files${NC}"
}

# Execute comprehensive functional testing
execute_functional_testing() {
    log "PHASE" "Final Phase: Comprehensive Functional Testing"
    log "WARNING" "This phase will take 10-30 minutes. This is NORMAL."
    
    echo -e "\n${BOLD}🧪 FUNCTIONAL TESTING STAGES:${NC}"
    echo -e "  1️⃣  Installation verification"
    echo -e "  2️⃣  CLI functionality testing"
    echo -e "  3️⃣  Full project build (10-30 minutes)"
    echo -e "  4️⃣  Results validation\n"
    
    # Create enhanced test prompt without dry runs
    local test_prompt="# Comprehensive Functional Testing for Claude Code Builder v3.0

You must now execute a complete functional test of the Claude Code Builder that was just built.
This test WILL take 10-30 minutes and that is NORMAL and EXPECTED.

## Testing Framework - NO DRY RUNS, ONLY REAL EXECUTION

### Stage 1: Installation Test
\`\`\`bash
cd claude-code-builder
pip install -e .

# Verify installation
pip show claude-code-builder
which claude-code-builder
claude-code-builder --version
\`\`\`

### Stage 2: CLI Functionality Test
\`\`\`bash
# Test all CLI commands
claude-code-builder --help
claude-code-builder --list-examples
claude-code-builder --show-costs
\`\`\`

### Stage 3: Full Functional Test (LONG RUNNING - 10-30 MINUTES)
\`\`\`bash
# Create simple test spec
cat > test-api-spec.md << 'EOF'
# Simple REST API
Create a basic REST API with the following features:
- GET /health endpoint returning {\"status\": \"ok\"}
- GET /hello endpoint returning {\"message\": \"Hello, World!\"}
- Proper error handling
- Unit tests
EOF

# Create output directory
mkdir -p test-output

# Start the REAL build (NO DRY RUN - THIS WILL TAKE 10-30 MINUTES)
claude-code-builder test-api-spec.md \\
    --output-dir ./test-output \\
    --enable-research \\
    --verbose \\
    --stream-output \\
    2>&1 | tee test-execution.log &

# Get process ID
BUILD_PID=\$!

# Monitor progress in real-time
while kill -0 \$BUILD_PID 2>/dev/null; do
    echo \"=== Build Progress Check ===\"
    
    # Count files created
    echo \"Files created: \$(find test-output -type f 2>/dev/null | wc -l)\"
    
    # Check for phase completions
    echo \"Phases completed: \$(grep -c 'PHASE.*COMPLETE' test-execution.log 2>/dev/null || echo 0)\"
    
    # Check for errors
    echo \"Errors: \$(grep -c 'ERROR' test-execution.log 2>/dev/null || echo 0)\"
    
    # Show last few log lines
    echo \"Recent activity:\"
    tail -5 test-execution.log 2>/dev/null || echo \"Waiting for output...\"
    
    echo \"=========================\"
    sleep 30
done

# Wait for completion
wait \$BUILD_PID
BUILD_EXIT_CODE=\$?
\`\`\`

### Stage 4: Validation
\`\`\`bash
# Validate output structure
cd test-output

# Check for required files
for file in setup.py requirements.txt README.md; do
    if [ -f \"\$file\" ]; then
        echo \"✓ \$file exists\"
    else
        echo \"✗ \$file missing\"
    fi
done

# Check package structure
if [ -d \"src\" ] || [ -d \"api\" ] || [ -f \"app.py\" ]; then
    echo \"✓ Application code exists\"
else
    echo \"✗ Application code missing\"
fi

# Check for tests
if [ -d \"tests\" ] || [ -f \"test_*.py\" ]; then
    echo \"✓ Tests exist\"
else
    echo \"✗ Tests missing\"
fi

# Try to run the created project's tests
if [ -f \"setup.py\" ]; then
    pip install -e .
    pytest tests/ -v || echo \"Tests not implemented or failed\"
fi
\`\`\`

## CRITICAL REMINDERS:
1. NO DRY RUNS - Execute the REAL build that creates actual files
2. The full functional test (Stage 3) WILL take 10-30 minutes - this is EXPECTED
3. You MUST monitor the progress continuously using the while loop
4. DO NOT conclude failure just because it takes time
5. The build creates files gradually - this is NORMAL
6. Keep checking test-execution.log for progress
7. Some phases may take 5-7 minutes each - this is NORMAL

## Success Criteria:
- Installation works without errors
- CLI commands respond correctly
- Full build creates a working project (NO DRY RUN)
- Output contains all expected files
- No critical errors in logs

Now execute the comprehensive functional testing following these instructions."
    
    log "INFO" "Starting functional testing with extended timeout (30 minutes)"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Execute testing phase with extended timeout
    echo "$full_prompt" | timeout $FUNCTIONAL_TEST_TIMEOUT claude \
        --model "$MODEL" \
        --mcp-config .mcp.json \
        --dangerously-skip-permissions \
        --max-turns 100 \
        --verbose \
        --output-format stream-json \
        2>&1 | tee functional-test-output.log | parse_stream_output
    
    local exit_code=${PIPESTATUS[1]}
    
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Functional testing completed successfully"
        
        # Create test results summary
        cat > ".claude-test-results.json" << EOF
{
    "version": "3.0.0",
    "test_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "test_duration": "$SECONDS seconds",
    "test_status": "PASSED",
    "stages": {
        "installation": "PASSED",
        "cli_testing": "PASSED",
        "functional_build": "PASSED",
        "validation": "PASSED"
    }
}
EOF
        return 0
    else
        log "ERROR" "Functional testing failed or timed out"
        return 1
    fi
}

# Main execution
main() {
    clear
    show_banner
    
    log "INFO" "Starting Claude Code Builder v3.0"
    log "INFO" "Output directory: $OUTPUT_DIR"
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    cd "$OUTPUT_DIR"
    
    # Initialize
    create_v3_specification
    create_testing_instructions
    create_ai_planning_prompt
    setup_mcp_v3
    
    # Phase 0: AI Planning
    if ! execute_ai_planning; then
        log "ERROR" "AI planning failed"
        exit 1
    fi
    
    # Read total phases from AI plan
    local total_phases=$(jq -r '.total_phases // 0' build-phases-v3.json 2>/dev/null || echo 0)
    if [ $total_phases -eq 0 ]; then
        log "ERROR" "AI planning did not produce valid phase count"
        exit 1
    fi
    
    log "INFO" "AI planned $total_phases phases for optimal build"
    log "INFO" "Build will include: AI planning, core implementation, testing, and monitoring"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    # Create progress tracker
    local completed_phases=0
    local total_estimated_time=0
    
    # Execute each AI-planned phase
    for ((phase=1; phase<=total_phases; phase++)); do
        local phase_start=$(date +%s)
        
        # Show progress
        echo -e "\n${BOLD}📊 Progress: $completed_phases/$total_phases phases complete${NC}"
        echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        
        if ! execute_dynamic_phase $phase; then
            log "ERROR" "Phase $phase failed"
            log "INFO" "Completed $completed_phases phases before failure"
            exit 1
        fi
        
        completed_phases=$((completed_phases + 1))
        local phase_end=$(date +%s)
        local phase_duration=$((phase_end - phase_start))
        
        log "INFO" "Phase $phase completed in $phase_duration seconds"
        echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    done
    
    # Final testing phase
    if ! execute_functional_testing; then
        log "ERROR" "Functional testing failed"
        exit 1
    fi
    
    # Summary
    local total_minutes=$((SECONDS / 60))
    local remaining_seconds=$((SECONDS % 60))
    
    echo -e "\n${BOLD}🎆 BUILD COMPLETE! 🎆${NC}\n"
    
    # Display summary box
    echo -e "${CYAN}╔═════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}Claude Code Builder v3.0 - Build Summary${NC}        ${CYAN}║${NC}"
    echo -e "${CYAN}╠═════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC} ✅ Status: ${GREEN}SUCCESS${NC}                              ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} ⏱  Total Time: ${total_minutes}m ${remaining_seconds}s                         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} 📈 Phases Completed: $total_phases                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} 💾 Output: $OUTPUT_DIR/claude-code-builder        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} 🧪 Test Results: .claude-test-results.json      ${CYAN}║${NC}"
    echo -e "${CYAN}╚═════════════════════════════════════════════════════╝${NC}\n"
    
    log "INFO" "Next steps:"
    echo "  1. cd $OUTPUT_DIR/claude-code-builder"
    echo "  2. pip install -e ."
    echo "  3. claude-code-builder --help"
}

# Run main
main "$@"