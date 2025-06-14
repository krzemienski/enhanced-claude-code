#!/bin/bash

# Claude Code Builder v2.3.0 - Autonomous Build Script
# Orchestrates Claude Code to build the Claude Code Builder project
# 
# This script builds a sophisticated Python application that uses Claude Code SDK
# to autonomously build complete projects through multiple execution phases.

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
SPEC_FILE="prompt.md"
MODEL="claude-opus-4-20250514"
STATE_FILE=".claude-builder-state.json"

# Build configuration
MAX_TURNS=50
MAX_PHASE_RETRIES=3
RETRY_DELAY=30
JSON_OUTPUT_DIR=".claude_outputs"
VALIDATION_LOG="phase_validation.log"
METRICS_LOG="build_metrics.json"
HUMAN_LOG="build_progress.log"

# Progress tracking
CURRENT_PHASE=0
TOTAL_PHASES=12
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

# Load external instructions if available
# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Look for files in script directory first, then current directory
if [ -f "$SCRIPT_DIR/instructions.md" ]; then
    INSTRUCTIONS_FILE="$SCRIPT_DIR/instructions.md"
elif [ -f "instructions.md" ]; then
    INSTRUCTIONS_FILE="instructions.md"
else
    INSTRUCTIONS_FILE=""
fi

if [ -f "$SCRIPT_DIR/phases.md" ]; then
    PHASES_FILE="$SCRIPT_DIR/phases.md"
elif [ -f "phases.md" ]; then
    PHASES_FILE="phases.md"
else
    PHASES_FILE=""
fi

if [ -f "$SCRIPT_DIR/prompt.md" ]; then
    PROMPT_FILE="$SCRIPT_DIR/prompt.md"
elif [ -f "prompt.md" ]; then
    PROMPT_FILE="prompt.md"
else
    PROMPT_FILE=""
fi

if [ -f "$SCRIPT_DIR/tasks.md" ]; then
    TASKS_FILE="$SCRIPT_DIR/tasks.md"
elif [ -f "tasks.md" ]; then
    TASKS_FILE="tasks.md"
else
    TASKS_FILE=""
fi

# Check for required files
for file_var in PHASES_FILE PROMPT_FILE INSTRUCTIONS_FILE TASKS_FILE; do
    file="${!file_var}"
    if [ -z "$file" ] || [ ! -f "$file" ]; then
        echo -e "${RED}Error: Required file ${file_var//_FILE/}.md not found in script directory or current directory${NC}"
        echo -e "${YELLOW}Please run this script in a directory with all supporting files.${NC}"
        exit 1
    fi
done

# Load prompt content (full specification)
FULL_SPEC=$(cat "$PROMPT_FILE")

# Load custom instructions
CUSTOM_INSTRUCTIONS=$(cat "$INSTRUCTIONS_FILE")

# Initialize directories and logs
mkdir -p "$JSON_OUTPUT_DIR" "$METRICS_DIR"
echo "Claude Code Builder v2.3.0 Build Script Log - $(date)" > "$VALIDATION_LOG"
echo "Build Progress - $(date)" > "$HUMAN_LOG"

# ASCII Art Banner
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
    echo "║               ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗    ║"
    echo "║               ██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗   ║"
    echo "║               ██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝   ║"
    echo "║               ██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗   ║"
    echo "║               ██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║   ║"
    echo "║               ╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝   ║"
    echo "║                                                                       ║"
    echo "║                              v2.3.0                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
}

# Logging functions
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
    esac
}

# Enhanced logging functions
log_info() {
    echo -e "${CYAN}ℹ ${NC}$1"
}

log_error() {
    echo -e "${RED}✗ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✓ ${NC}$1"
}

log_warning() {
    echo -e "${YELLOW}⚠ ${NC}$1"
}

log_file_created() {
    local file=$1
    echo -e "${GREEN}📄${NC} Created: ${LIGHT_BLUE}$file${NC}"
}

log_tool_use() {
    local tool=$1
    local description=$2
    echo -e "${PURPLE}🔧${NC} Using ${BOLD}$tool${NC}: $description"
}

log_ai_message() {
    local message=$1
    echo -e "${LIGHT_BLUE}🤖${NC} Claude: $message"
}

# State management
save_state() {
    local phase=$1
    local status=$2
    local details="${3:-}"
    local retry_count="${4:-0}"
    local elapsed=$(($(date +%s) - START_TIME))
    
    cat > "$STATE_FILE" <<EOF
{
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
"total_cost": $TOTAL_COST
}
}
EOF
}

load_state() {
    if [ ! -f "$STATE_FILE" ]; then
        return 1
    fi
    
    CURRENT_PHASE=$(jq -r '.current_phase // 0' "$STATE_FILE")
    PHASE_RETRY_COUNT=$(jq -r '.retry_count // 0' "$STATE_FILE")
    LAST_SESSION_ID=$(jq -r '.last_session_id // empty' "$STATE_FILE")
    local saved_start_time=$(jq -r '.start_time // empty' "$STATE_FILE")
    
    if [ -n "$saved_start_time" ]; then
        START_TIME=$saved_start_time
        RESUMED=true
    fi
    
    return 0
}

# MCP Configuration for Claude Code Builder
setup_mcp_servers() {
    log_phase "START" "Setting up MCP servers for Claude Code Builder"
    
    log_info "Configuring Model Context Protocol servers..."
    
    cat > .mcp.json <<"MCP_CONFIG"
{
"mcpServers": {
"memory": {
"command": "npx",
"args": ["-y", "@modelcontextprotocol/server-memory"],
"description": "Store build progress, architectural decisions, and phase contexts"
},
"sequential-thinking": {
"command": "npx",
"args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
"description": "Plan complex implementations and dependencies"
},
"filesystem": {
"command": "npx",
"args": ["-y", "@modelcontextprotocol/server-filesystem", "--allowed-paths", "."],
"description": "Enhanced file operations for complex project structure"
}
}
}
MCP_CONFIG
    
    log_success "MCP configuration created with memory, sequential-thinking, and filesystem servers"
    log_phase "SUCCESS" "MCP configuration created"
}

# JSON stream parser for Claude output
parse_claude_stream() {
    local line
    local in_progress_bar=false
    
    while IFS= read -r line; do
        # Skip empty lines
        [ -z "$line" ] && continue
        
        # Try to parse as JSON
        if echo "$line" | jq -e . >/dev/null 2>&1; then
            local type=$(echo "$line" | jq -r '.type // empty')
            
            case $type in
                "system")
                    local session_id=$(echo "$line" | jq -r '.session_id // empty')
                    if [ -n "$session_id" ]; then
                        LAST_SESSION_ID=$session_id
                        log_info "Session ID: $session_id"
                    fi
                    ;;
                    
                "assistant")
                    local content=$(echo "$line" | jq -r '.message.content[]? | select(.type == "text") | .text // empty' 2>/dev/null)
                    if [ -n "$content" ]; then
                        # Only show first 100 chars of AI messages to reduce noise
                        if [ ${#content} -gt 100 ]; then
                            log_ai_message "${content:0:100}..."
                        else
                            log_ai_message "$content"
                        fi
                    fi
                    
                    # Check for tool use
                    local tool_name=$(echo "$line" | jq -r '.message.content[]? | select(.type == "tool_use") | .name // empty' 2>/dev/null)
                    if [ -n "$tool_name" ]; then
                        case $tool_name in
                            "Write")
                                local file_path=$(echo "$line" | jq -r '.message.content[]? | select(.type == "tool_use") | .input.file_path // empty' 2>/dev/null)
                                if [ -n "$file_path" ]; then
                                    log_tool_use "Write" "Creating $file_path"
                                    ((CURRENT_TASK_COUNT++))
                                    update_progress_bar
                                fi
                                ;;
                            "mcp__memory__"*)
                                log_tool_use "Memory" "Storing progress in memory server"
                                ;;
                            "mcp__sequential-thinking__"*)
                                log_tool_use "Sequential Thinking" "Planning implementation approach"
                                ;;
                            *)
                                log_tool_use "$tool_name" "Processing..."
                                ;;
                        esac
                    fi
                    ;;
                    
                "user")
                    local tool_result=$(echo "$line" | jq -r '.message.content[]? | select(.type == "tool_result") | .content // empty' 2>/dev/null)
                    if [ -n "$tool_result" ] && [[ "$tool_result" == *"successfully"* ]]; then
                        local file_created=$(echo "$tool_result" | grep -oE '/[^ ]+$' || echo "")
                        if [ -n "$file_created" ]; then
                            log_file_created "$file_created"
                        fi
                    fi
                    ;;
                    
                "result")
                    # Extract cost information from result
                    local cost=$(echo "$line" | jq -r '.cost // empty' 2>/dev/null)
                    if [ -n "$cost" ]; then
                        TOTAL_COST=$cost
                        log_info "Current session cost: \$$cost"
                    fi
                    ;;
            esac
        fi
    done
}

# Progress bar updater
update_progress_bar() {
    if [ $TOTAL_TASK_COUNT -gt 0 ]; then
        local progress=$((CURRENT_TASK_COUNT * 100 / TOTAL_TASK_COUNT))
        local bar_length=50
        local filled_length=$((progress * bar_length / 100))
        
        printf "\r${CLEAR_LINE}"
        printf "${DIM}Progress: [${NC}"
        
        for ((i=0; i<filled_length; i++)); do
            printf "${GREEN}█${NC}"
        done
        
        for ((i=filled_length; i<bar_length; i++)); do
            printf "${DIM}░${NC}"
        done
        
        printf "${DIM}] ${progress}%% (${CURRENT_TASK_COUNT}/${TOTAL_TASK_COUNT} tasks)${NC}"
    fi
}

# Claude execution with enhanced output
run_claude_auto() {
    local prompt="$1"
    local task_name="$2"
    local phase_num="${CURRENT_PHASE}"
    
    # Estimate task count based on phase (specific to Claude Code Builder)
    case $phase_num in
        1) TOTAL_TASK_COUNT=35 ;;  # Many files to create
        2) TOTAL_TASK_COUNT=25 ;;  # Data classes and enums
        3) TOTAL_TASK_COUNT=15 ;;  # MCP implementation
        4) TOTAL_TASK_COUNT=20 ;;  # Research system
        5) TOTAL_TASK_COUNT=12 ;;  # Custom instructions
        6) TOTAL_TASK_COUNT=15 ;;  # Claude Code integration
        7) TOTAL_TASK_COUNT=18 ;;  # Build execution engine
        8) TOTAL_TASK_COUNT=14 ;;  # Progress and UI
        9) TOTAL_TASK_COUNT=16 ;;  # Validation system
        10) TOTAL_TASK_COUNT=12 ;; # Reporting
        11) TOTAL_TASK_COUNT=10 ;; # Error handling
        12) TOTAL_TASK_COUNT=25 ;; # Documentation
        *) TOTAL_TASK_COUNT=15 ;;
    esac
    
    CURRENT_TASK_COUNT=0
    
    log_phase "START" "Phase $phase_num: $task_name"
    echo -e "\n${DIM}════════════════════════════════════════════════════════════════════════${NC}\n"
    
    # Create prompt file
    local prompt_file=$(mktemp)
    echo "$prompt" > "$prompt_file"
    
    # Build Claude command
    local claude_cmd="claude"
    claude_cmd+=" --print"
    claude_cmd+=" --model $MODEL"
    
    if [ -f ".mcp.json" ]; then
        claude_cmd+=" --mcp-config .mcp.json"
    fi
    
    claude_cmd+=" --dangerously-skip-permissions"
    claude_cmd+=" --output-format stream-json"
    claude_cmd+=" --verbose"
    claude_cmd+=" --max-turns $MAX_TURNS"
    
    # Execute with enhanced parsing
    log_info "Starting Claude with model $MODEL..."
    echo ""
    
    cat "$prompt_file" | eval $claude_cmd 2>&1 | parse_claude_stream
    local exit_code=${PIPESTATUS[1]}
    
    echo -e "\n"
    rm -f "$prompt_file"
    
    if [ $exit_code -ne 0 ]; then
        log_phase "ERROR" "Phase $phase_num failed (exit code: $exit_code)"
        return 1
    fi
    
    log_phase "SUCCESS" "Phase $phase_num completed"
    return 0
}

# Progress display
show_progress() {
    local phase=$1
    local description=$2
    local elapsed=$(($(date +%s) - START_TIME))
    local progress=$((phase * 100 / TOTAL_PHASES))
    
    # Progress bar
    local bar_length=40
    local filled_length=$((progress * bar_length / 100))
    local bar=""
    for ((i=0; i<filled_length; i++)); do bar+="█"; done
    for ((i=filled_length; i<bar_length; i++)); do bar+="░"; done
    
    echo -e "\n${BOLD}${MAGENTA}═══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${YELLOW}PHASE $phase/$TOTAL_PHASES${NC} ${DIM}|${NC} ${CYAN}$description${NC}"
    echo -e "${BLUE}Overall Progress:${NC} [$bar] ${BOLD}$progress%${NC}"
    echo -e "${DIM}Elapsed: $((elapsed/60))m $((elapsed%60))s${NC}"
    echo -e "${BOLD}${MAGENTA}═══════════════════════════════════════════════════════════════════════${NC}"
    
    save_state $phase "in_progress" "$description"
}

# Phase-specific validation functions
validate_phase_1() {
    log_phase "VALIDATE" "Validating Phase 1: Project Foundation"
    local validation_passed=true
    
    # Check main project files
    local required_files=(
        "setup.py" "requirements.txt" "pyproject.toml"
        "README.md" "LICENSE" ".gitignore"
        "claude_code_builder/__init__.py"
        "claude_code_builder/__main__.py"
        "claude_code_builder/cli.py"
        "claude_code_builder/main.py"
    )
    
    echo ""
    log_info "Checking project files..."
    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            log_success "Found file: $file"
        else
            log_error "Missing file: $file"
            validation_passed=false
        fi
    done
    
    # Check package directories
    local required_dirs=(
        "claude_code_builder/models"
        "claude_code_builder/mcp"
        "claude_code_builder/research"
        "claude_code_builder/execution"
        "claude_code_builder/ui"
        "claude_code_builder/validation"
        "claude_code_builder/utils"
        "claude_code_builder/instructions"
    )
    
    echo ""
    log_info "Checking package structure..."
    for dir in "${required_dirs[@]}"; do
        if [ -d "$dir" ]; then
            log_success "Found directory: $dir"
        else
            log_error "Missing directory: $dir"
            validation_passed=false
        fi
    done
    
    [ "$validation_passed" = true ]
}

validate_phase_2() {
    log_phase "VALIDATE" "Validating Phase 2: Data Models"
    local validation_passed=true
    
    # Check model files
    local required_models=(
        "claude_code_builder/models/build_status.py"
        "claude_code_builder/models/tool_call.py"
        "claude_code_builder/models/build_stats.py"
        "claude_code_builder/models/cost_tracker.py"
        "claude_code_builder/models/phase.py"
        "claude_code_builder/models/project_memory.py"
        "claude_code_builder/models/research.py"
        "claude_code_builder/models/mcp.py"
    )
    
    for file in "${required_models[@]}"; do
        if [ -f "$file" ]; then
            log_success "Found model: $file"
        else
            log_error "Missing model: $file"
            validation_passed=false
        fi
    done
    
    [ "$validation_passed" = true ]
}

# Phase validation dispatcher
validate_phase() {
    local phase=$1
    
    case $phase in
        1) validate_phase_1; return $? ;;
        2) validate_phase_2; return $? ;;
        *) 
            # Generic validation for other phases
            log_phase "VALIDATE" "Validating Phase $phase"
            return 0
            ;;
    esac
}

# Execute phase with retry logic
execute_phase_with_retry() {
    local phase_num=$1
    local phase_description=$2
    local next_phase=$((phase_num + 1))
    local validation_attempts=0
    local phase_complete=false
    
    while [ "$phase_complete" = false ] && [ $validation_attempts -lt $MAX_PHASE_RETRIES ]; do
        show_progress $phase_num "$phase_description"
        
        if run_claude_auto "$(get_phase_prompt $phase_num)" "$phase_description"; then
            if validate_phase $phase_num; then
                CURRENT_PHASE=$next_phase
                save_state $next_phase "ready" "$phase_description completed"
                phase_complete=true
            else
                ((validation_attempts++))
                log_error "Phase $phase_num validation failed (attempt $validation_attempts/$MAX_PHASE_RETRIES)"
                if [ $validation_attempts -lt $MAX_PHASE_RETRIES ]; then
                    log_warning "Validation failed. Retrying phase..."
                    echo -e "${YELLOW}Waiting ${RETRY_DELAY} seconds before retry...${NC}"
                    sleep $RETRY_DELAY
                else
                    log_error "Phase $phase_num failed after $MAX_PHASE_RETRIES attempts"
                    exit 1
                fi
            fi
        else
            log_error "Claude execution failed for Phase $phase_num"
            exit 1
        fi
    done
}

# Interrupt handler
handle_interrupt() {
    echo -e "\n\n${RED}⚠️  Build interrupted!${NC}"
    echo -e "${YELLOW}Progress saved at phase $CURRENT_PHASE/$TOTAL_PHASES${NC}"
    save_state $CURRENT_PHASE "interrupted" "User interrupted"
    exit 1
}

trap handle_interrupt SIGINT SIGTERM

# Load phase details
get_phase_prompt() {
    local phase_num=$1
    local phase_content=""
    local tasks_content=""
    
    # Check if files exist before reading
    if [ -f "$PHASES_FILE" ]; then
        phase_content=$(cat "$PHASES_FILE")
        # Extract the specific phase section from phases.md
        phase_section=$(echo "$phase_content" | awk "/^## Phase $phase_num:/{flag=1} /^## Phase $((phase_num+1)):/{flag=0} flag")
    else
        phase_section=""
    fi
    
    if [ -f "$TASKS_FILE" ]; then
        tasks_content=$(cat "$TASKS_FILE")
    fi
    
    # Combine with custom instructions and full spec
    echo "$phase_section

$CUSTOM_INSTRUCTIONS

📋 FULL SPECIFICATION:
$FULL_SPEC

📝 DETAILED TASKS:
$tasks_content"
}

# Main script
clear
show_banner

echo -e "${BLUE}${BOLD}=== Claude Code Builder v2.3.0 - Autonomous Build Script ===${NC}"
echo -e "${YELLOW}Building an enhanced production-ready project builder${NC}"
echo -e "${CYAN}Model: $MODEL | Phases: $TOTAL_PHASES${NC}\n"

# Check prerequisites
if ! command -v claude &> /dev/null; then
    echo -e "${RED}Error: Claude Code CLI not found. Please install it first:${NC}"
    echo -e "${YELLOW}npm install -g @anthropic-ai/claude-code${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq not found. Please install it first.${NC}"
    exit 1
fi

# Create project directory
if [ ! -d "$PROJECT_NAME" ]; then
    mkdir -p "$PROJECT_NAME"
fi
cd "$PROJECT_NAME"

# Load or create state
if load_state; then
    echo -e "${YELLOW}📂 Resuming from phase $CURRENT_PHASE/$TOTAL_PHASES${NC}"
    log_info "Previous session ID: ${LAST_SESSION_ID:-none}"
    log_info "Elapsed time: $(($(date +%s) - START_TIME))s"
    echo ""
else
    echo -e "${GREEN}🚀 Starting fresh build${NC}\n"
fi

# Phase 0: MCP Setup
if [ $CURRENT_PHASE -eq 0 ]; then
    setup_mcp_servers
    CURRENT_PHASE=1
    save_state 1 "ready" "MCP setup complete"
fi

# Phase 1: Project Foundation and Structure
if [ $CURRENT_PHASE -eq 1 ]; then
    execute_phase_with_retry 1 "Project Foundation and Package Structure"
fi

# Phase 2: Data Models and Types
if [ $CURRENT_PHASE -eq 2 ]; then
    execute_phase_with_retry 2 "Data Models and Types"
fi

# Phase 3: MCP System Implementation
if [ $CURRENT_PHASE -eq 3 ]; then
    execute_phase_with_retry 3 "MCP System Implementation"
fi

# Phase 4: Research System
if [ $CURRENT_PHASE -eq 4 ]; then
    execute_phase_with_retry 4 "Research System"
fi

# Phase 5: Custom Instructions System
if [ $CURRENT_PHASE -eq 5 ]; then
    execute_phase_with_retry 5 "Custom Instructions System"
fi

# Phase 6: Execution System
if [ $CURRENT_PHASE -eq 6 ]; then
    execute_phase_with_retry 6 "Execution System"
fi

# Phase 7: UI and Progress System
if [ $CURRENT_PHASE -eq 7 ]; then
    execute_phase_with_retry 7 "UI and Progress System"
fi

# Phase 8: Validation System
if [ $CURRENT_PHASE -eq 8 ]; then
    execute_phase_with_retry 8 "Validation System"
fi

# Phase 9: Utilities and Helpers
if [ $CURRENT_PHASE -eq 9 ]; then
    execute_phase_with_retry 9 "Utilities and Helpers"
fi

# Phase 10: Main Application Integration
if [ $CURRENT_PHASE -eq 10 ]; then
    execute_phase_with_retry 10 "Main Application Integration"
fi

# Phase 11: Testing and Examples
if [ $CURRENT_PHASE -eq 11 ]; then
    execute_phase_with_retry 11 "Testing and Examples"
fi

# Phase 12: Documentation and Polish
if [ $CURRENT_PHASE -eq 12 ]; then
    execute_phase_with_retry 12 "Documentation and Polish"
fi

# Final summary
if [ $CURRENT_PHASE -ge $TOTAL_PHASES ]; then
    echo -e "\n${MAGENTA}═══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}${BOLD}=== Build Complete ===${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════${NC}\n"
    
    elapsed=$(($(date +%s) - START_TIME))
    echo -e "${CYAN}Total Time: $((elapsed/60))m $((elapsed%60))s${NC}"
    echo -e "${CYAN}Total Cost: \$$TOTAL_COST${NC}"
    echo -e "${GREEN}All phases completed successfully!${NC}\n"
    
    log_info "Next steps:"
    echo -e "  1. ${GREEN}cd $PROJECT_NAME${NC}"
    echo -e "  2. ${GREEN}pip install -e .${NC}"
    echo -e "  3. ${GREEN}claude-code-builder --help${NC}"
    echo -e "  4. ${GREEN}claude-code-builder examples/simple-api-spec.md --output-dir ./test-project${NC}\n"
    
    echo -e "${YELLOW}📚 Check the README.md for detailed documentation${NC}"
    echo -e "${YELLOW}🧪 Run the test suite with: pytest tests/${NC}"
fi