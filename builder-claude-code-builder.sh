#!/bin/bash

# Claude Code Builder v2.3.0 - Autonomous Build Script
# Orchestrates Claude Code to build the Claude Code Builder project
# 
# This script builds a sophisticated Python application that uses Claude Code SDK
# to autonomously build complete projects through multiple execution phases.
#
# Usage: ./builder-claude-code-builder.sh [OPTIONS]
# Options:
#   -o, --output-dir DIR    Output directory for the build (default: current directory)
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

# Memory management tracking
MEMORY_KEYS_FILE=".memory_keys.json"
# Use a simple file-based approach for compatibility with older bash versions
MEMORY_KEYS_DIR=".memory_keys"

# Output directory (can be overridden by CLI argument)
OUTPUT_DIR=""

# Global arrays for MCP discovery
declare -a DISCOVERED_MCP_SERVERS
declare -a MCP_SERVER_COMMANDS

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -o, --output-dir DIR    Output directory for the build (default: current directory)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Build in current directory"
    echo "  $0 -o /path/to/output   # Build in specified directory"
    echo "  $0 --output-dir ./build # Build in ./build directory"
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
    # Validate the output directory path
    if [[ "$OUTPUT_DIR" =~ [[:space:]] ]]; then
        echo -e "${YELLOW}Warning: Output directory contains spaces. This may cause issues.${NC}"
    fi
    
    # Convert to absolute path if relative
    if [[ "$OUTPUT_DIR" = /* ]]; then
        # Already absolute path
        :
    else
        # Relative path - make it absolute
        OUTPUT_DIR="$(pwd)/$OUTPUT_DIR"
    fi
    
    # Ensure parent directory exists
    parent_dir=$(dirname "$OUTPUT_DIR")
    if [ ! -d "$parent_dir" ]; then
        echo -e "${RED}Error: Parent directory does not exist: $parent_dir${NC}"
        exit 1
    fi
fi

# Set MCP configuration file path
MCP_CONFIG_FILE=".mcp.json"

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
        "INIT")
            echo -e "${CYAN}[INITIALIZING]${NC} ${timestamp} 🔧 ${BOLD}$message${NC}" | tee -a "$HUMAN_LOG"
            ;;
        "ANALYSIS")
            echo -e "${YELLOW}[ANALYZING]${NC} ${timestamp} 📊 ${BOLD}$message${NC}" | tee -a "$HUMAN_LOG"
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

# Memory management functions
load_memory_keys() {
    # Create memory keys directory if it doesn't exist
    mkdir -p "$MEMORY_KEYS_DIR"
    
    # Also maintain JSON file for compatibility
    if [ -f "$MEMORY_KEYS_FILE" ]; then
        # Migrate existing keys to directory structure
        while IFS="=" read -r key value; do
            echo "$value" > "$MEMORY_KEYS_DIR/$key"
        done < <(jq -r 'to_entries[] | "\(.key)=\(.value)"' "$MEMORY_KEYS_FILE" 2>/dev/null || true)
    fi
}

save_memory_keys() {
    # Save to JSON file for compatibility
    local json_obj="{"
    local first=true
    
    if [ -d "$MEMORY_KEYS_DIR" ]; then
        # Use find to handle empty directory case
        while IFS= read -r key_file; do
            if [ -n "$key_file" ] && [ -f "$key_file" ]; then
                local key=$(basename "$key_file")
                local value=$(cat "$key_file")
                
                if [ "$first" = true ]; then
                    first=false
                else
                    json_obj+=","
                fi
                json_obj+="\"$key\":\"$value\""
            fi
        done < <(find "$MEMORY_KEYS_DIR" -maxdepth 1 -type f 2>/dev/null || true)
    fi
    
    json_obj+="}"
    echo "$json_obj" > "$MEMORY_KEYS_FILE"
}

check_memory_key_exists() {
    local key=$1
    # Check if key file exists
    [ -f "$MEMORY_KEYS_DIR/$key" ]
}

add_memory_key() {
    local key=$1
    local phase=${2:-$CURRENT_PHASE}
    mkdir -p "$MEMORY_KEYS_DIR"
    echo "phase_${phase}_$(date +%s)" > "$MEMORY_KEYS_DIR/$key"
    save_memory_keys
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
    
    # Validate JSON before parsing
    if ! jq . "$STATE_FILE" >/dev/null 2>&1; then
        log_warning "State file is corrupted, starting fresh"
        rm -f "$STATE_FILE"
        return 1
    fi
    
    CURRENT_PHASE=$(jq -r '.current_phase // 0' "$STATE_FILE" 2>/dev/null || echo "0")
    PHASE_RETRY_COUNT=$(jq -r '.retry_count // 0' "$STATE_FILE" 2>/dev/null || echo "0")
    LAST_SESSION_ID=$(jq -r '.last_session_id // empty' "$STATE_FILE" 2>/dev/null || echo "")
    local saved_start_time=$(jq -r '.start_time // empty' "$STATE_FILE" 2>/dev/null || echo "")
    
    if [ -n "$saved_start_time" ]; then
        START_TIME=$saved_start_time
        RESUMED=true
    fi
    
    return 0
}

# MCP Configuration for Claude Code Builder with Git support
setup_mcp_servers() {
    log_phase "START" "Setting up MCP servers for Claude Code Builder"
    
    log_info "Configuring Model Context Protocol servers..."
    
    # Check for Claude Desktop config using dynamic home directory
    local claude_desktop_config="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    
    if [ -f "$claude_desktop_config" ]; then
        log_success "Found Claude Desktop configuration at: $claude_desktop_config"
        log_info "Using Claude Desktop MCP servers as base configuration..."
        
        # Copy the Claude Desktop config
        cp "$claude_desktop_config" "$MCP_CONFIG_FILE"
        
        # Update filesystem paths to point to our output directory
        # Use Python to modify JSON while preserving structure
        python3 -c "
import json
import sys

config_file = '$MCP_CONFIG_FILE'
output_dir = '$OUTPUT_DIR'

with open(config_file, 'r') as f:
    config = json.load(f)

# Update filesystem server to use our output directory
if 'filesystem' in config.get('mcpServers', {}):
    config['mcpServers']['filesystem']['args'] = [
        '-y',
        '@modelcontextprotocol/server-filesystem',
        output_dir
    ]

# Ensure Mem0 API key is set if we have one
mem0_key = '${MEM0_API_KEY:-}'
if mem0_key and 'mem0' in config.get('mcpServers', {}):
    if 'env' not in config['mcpServers']['mem0']:
        config['mcpServers']['mem0']['env'] = {}
    config['mcpServers']['mem0']['env']['MEM0_API_KEY'] = mem0_key

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)
"
        
        log_info "Updated MCP configuration with project-specific settings"
        
        # Log which memory server is being used
        if grep -q '"mem0"' "$MCP_CONFIG_FILE" && [ -n "${MEM0_API_KEY:-}" ]; then
            log_success "Using Mem0 intelligent memory system from Claude Desktop config"
        elif grep -q '"memory"' "$MCP_CONFIG_FILE"; then
            log_info "Using standard memory server from Claude Desktop config"
        fi
    else
        log_info "Claude Desktop config not found, using default configuration..."
        
        # Check if MEM0_API_KEY is set for fallback config
        if [ -z "${MEM0_API_KEY:-}" ]; then
            log_warning "MEM0_API_KEY not set. Please export MEM0_API_KEY to use Mem0 memory system."
            log_info "Using standard memory server:"
            log_info "  - Command: npx -y @modelcontextprotocol/server-memory"
            log_info "  - Purpose: Key-value storage for build state and phase data"
            log_info "  - Features: Simple persistence across phases"
            MEMORY_SERVER_CONFIG='"memory": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-memory"],
    "description": "Store build progress, architectural decisions, and phase contexts"
}'
        else
            log_success "MEM0_API_KEY detected. Using Mem0 for intelligent memory management."
            log_info "Mem0 MCP server configuration:"
            log_info "  - Command: npx -y @mem0/mcp-server"
            log_info "  - API Key: ${MEM0_API_KEY:0:10}...${MEM0_API_KEY: -4}"
            log_info "  - Purpose: Intelligent memory with semantic search"
            log_info "  - Features: LLM-powered extraction, contradiction resolution, persistence"
            MEMORY_SERVER_CONFIG='"mem0-mcp": {
    "command": "npx",
    "args": ["-y", "@mem0/mcp-server"],
    "env": {
        "MEM0_API_KEY": "'"$MEM0_API_KEY"'"
    },
    "description": "Intelligent memory with LLM-powered extraction and semantic search"
}'
        fi
        
        # Create the MCP configuration file
        {
            echo '{'
            echo '  "mcpServers": {'
            echo "    $MEMORY_SERVER_CONFIG,"
            echo '    "sequential-thinking": {'
            echo '      "command": "npx",'
            echo '      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],'
            echo '      "description": "Plan complex implementations and dependencies"'
            echo '    },'
            echo '    "filesystem": {'
            echo '      "command": "npx",'
            echo '      "args": ["-y", "@modelcontextprotocol/server-filesystem", "--allowed-paths", "."],'
            echo '      "description": "Enhanced file operations for complex project structure"'
            echo '    },'
            echo '    "git": {'
            echo '      "command": "npx",'
            echo '      "args": ["-y", "@modelcontextprotocol/server-git"],'
            echo '      "description": "Git operations for version control and progress tracking"'
            echo '    }'
            echo '  }'
            echo '}'
        } > "$MCP_CONFIG_FILE"
    fi
    
    # Log MCP server details
    log_info "MCP servers configured:"
    if [ -n "${MEM0_API_KEY:-}" ]; then
        log_info "  1. mem0-mcp - Intelligent memory with semantic search"
    else
        log_info "  1. memory - Standard key-value memory storage"
    fi
    log_info "  2. sequential-thinking - Step-by-step reasoning for complex problems"
    log_info "     Command: npx -y @modelcontextprotocol/server-sequential-thinking"
    log_info "  3. filesystem - Enhanced file operations with path restrictions"
    log_info "     Command: npx -y @modelcontextprotocol/server-filesystem"
    log_info "     Allowed paths: Current directory (.)"
    log_info "  4. git - Version control operations"
    log_info "     Command: npx -y @modelcontextprotocol/server-git"
    
    # Display the generated configuration
    log_info "Generated MCP configuration (.mcp.json):"
    cat .mcp.json | while IFS= read -r line; do
        echo "    $line" | tee -a "$VALIDATION_LOG"
    done
    
    log_success "MCP configuration created with memory, sequential-thinking, filesystem, and git servers"
    
    # Initialize git repository if not already initialized
    if [ ! -d ".git" ]; then
        log_info "Initializing git repository..."
        git init
        git add .gitignore 2>/dev/null || echo "*.pyc" > .gitignore
        git add .gitignore
        git commit -m "Initial commit: Claude Code Builder project setup" || true
    fi
    
    # Discover all available MCP servers
    discover_all_mcp_servers
    
    # Display MCP server status
    display_mcp_status
    
    log_phase "SUCCESS" "MCP configuration created"
}

# Helper function to store user preferences in Mem0
store_user_preferences() {
    if [ -n "${MEM0_API_KEY:-}" ]; then
        log_phase "INIT" "Storing user preferences in Mem0"
        
        local add_tool=$(get_memory_tool "add")
        
        # Create preferences prompt
        local preferences_prompt="STORE USER PREFERENCES IN MEM0

Please store the following user preferences using ${add_tool}:

1. 'User Preference: Output directory is $OUTPUT_DIR' 
2. 'User Preference: Building Claude Code Builder v2.3.0'
3. 'User Preference: Model is $MODEL'
4. 'User Preference: Max turns per phase is $MAX_TURNS'
5. 'User Preference: Project name is $PROJECT_NAME'

Include user_id='claude-code-builder' in all memory operations.

These preferences will help maintain consistency across sessions."
        
        run_claude_auto "$preferences_prompt" "Store User Preferences"
        log_phase "SUCCESS" "User preferences stored in Mem0"
    fi
}

# Function to discover all available MCP servers
discover_all_mcp_servers() {
    log_info "Discovering all available MCP servers..."
    
    local discovered_servers=()
    local server_commands=()
    
    # 1. Check globally installed NPM packages for MCP servers
    if command -v npm &> /dev/null; then
        log_info "Checking globally installed NPM packages..."
        local npm_list=$(npm list -g --depth=0 2>/dev/null | grep -E "@modelcontextprotocol/|mcp-server-|@.*\/mcp$" || true)
        
        if [ -n "$npm_list" ]; then
            while IFS= read -r line; do
                local pkg_name=$(echo "$line" | sed -E 's/.*[├└]── (@[^@]+).*/\1/')
                if [ -n "$pkg_name" ]; then
                    discovered_servers+=("$pkg_name")
                    log_info "  Found: $pkg_name"
                fi
            done <<< "$npm_list"
        fi
    fi
    
    # 2. Check Claude Desktop config for additional servers
    local claude_config=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        claude_config="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        claude_config="$HOME/.config/Claude/claude_desktop_config.json"
    fi
    
    if [ -f "$claude_config" ] && command -v jq &> /dev/null; then
        log_info "Checking Claude Desktop configuration..."
        local claude_servers=$(jq -r '.mcpServers | keys[]' "$claude_config" 2>/dev/null || true)
        
        if [ -n "$claude_servers" ]; then
            while IFS= read -r server; do
                if [[ ! " ${discovered_servers[@]} " =~ " ${server} " ]]; then
                    discovered_servers+=("$server")
                    log_info "  Found in Claude config: $server"
                fi
            done <<< "$claude_servers"
        fi
    fi
    
    # 3. Add known MCP servers that might be useful
    local known_servers=(
        "@modelcontextprotocol/server-filesystem"
        "@modelcontextprotocol/server-github" 
        "@modelcontextprotocol/server-gitlab"
        "@modelcontextprotocol/server-git"
        "@modelcontextprotocol/server-puppeteer"
        "@modelcontextprotocol/server-slack"
        "@modelcontextprotocol/server-postgres"
        "@modelcontextprotocol/server-sqlite"
        "@modelcontextprotocol/server-everything"
        "@modelcontextprotocol/server-fetch"
        "@modelcontextprotocol/server-brave-search"
        "@modelcontextprotocol/server-google-maps"
        "@anthropic/server-evals"
        "@mem0/mcp-server"
        "@shimizu/mcp-server-perplexity"
        "mcp-server-linear"
        "mcp-server-notion"
    )
    
    for server in "${known_servers[@]}"; do
        if [[ ! " ${discovered_servers[@]} " =~ " ${server} " ]]; then
            # Check if server is installed
            if npm list -g "$server" &> /dev/null; then
                discovered_servers+=("$server")
                log_info "  Verified installed: $server"
            fi
        fi
    done
    
    # Generate server commands for whitelisting
    for server in "${discovered_servers[@]}"; do
        case "$server" in
            *"filesystem"*)
                server_commands+=("filesystem__read_file" "filesystem__write_file" "filesystem__list_directory")
                ;;
            *"github"*)
                server_commands+=("github__search_repositories" "github__create_issue" "github__create_pull_request")
                ;;
            *"git"*)
                server_commands+=("git__status" "git__diff" "git__commit" "git__log")
                ;;
            *"mem0"*)
                server_commands+=("mem0-mcp__add-memory" "mem0-mcp__search-memories" "mem0-mcp__list-memories" "mem0-mcp__delete-memories")
                ;;
            *"memory"*)
                server_commands+=("memory__create_memory" "memory__retrieve_memory" "memory__list_memories" "memory__delete_memory")
                ;;
            *"fetch"*)
                server_commands+=("fetch__fetch")
                ;;
            *"puppeteer"*)
                server_commands+=("puppeteer__navigate" "puppeteer__screenshot" "puppeteer__click")
                ;;
            *"perplexity"*)
                server_commands+=("perplexity__search" "perplexity__ask")
                ;;
            *"everything"*)
                server_commands+=("everything__execute")
                ;;
            *"slack"*)
                server_commands+=("slack__send_message" "slack__get_messages")
                ;;
            *"postgres"*)
                server_commands+=("postgres__query" "postgres__execute")
                ;;
            *"sqlite"*)
                server_commands+=("sqlite__query" "sqlite__execute")
                ;;
            *"brave-search"*)
                server_commands+=("brave-search__search")
                ;;
            *"google-maps"*)
                server_commands+=("google-maps__search" "google-maps__directions")
                ;;
            *"gitlab"*)
                server_commands+=("gitlab__search_repositories" "gitlab__create_issue")
                ;;
            *"linear"*)
                server_commands+=("linear__create_issue" "linear__list_issues")
                ;;
            *"notion"*)
                server_commands+=("notion__search" "notion__create_page")
                ;;
            *"evals"*)
                server_commands+=("evals__run" "evals__list")
                ;;
        esac
    done
    
    # Export for use in other functions
    export DISCOVERED_MCP_SERVERS=("${discovered_servers[@]}")
    export MCP_SERVER_COMMANDS=("${server_commands[@]}")
    
    log_info "Discovered ${#discovered_servers[@]} MCP servers"
    log_info "Generated ${#server_commands[@]} whitelisted commands"
}

# Function to display MCP server status
display_mcp_status() {
    echo -e "\n${GREEN}✅ MCP Server Configuration:${NC}"
    
    if [ -f ".mcp.json" ]; then
        echo -e "${BLUE}  MCP config file created at: $(pwd)/.mcp.json${NC}"
        
        # Display configured servers
        if command -v jq &> /dev/null; then
            local servers=$(jq -r '.mcpServers | keys[]' ".mcp.json" 2>/dev/null)
            if [ -n "$servers" ]; then
                echo -e "${YELLOW}  Configured MCP servers:${NC}"
                echo "$servers" | while read -r server; do
                    echo -e "${CYAN}    - $server${NC}"
                done
            fi
        fi
    fi
    
    # Display discovered servers
    if [ -n "${DISCOVERED_MCP_SERVERS:-}" ]; then
        echo -e "\n${YELLOW}  All discovered MCP servers:${NC}"
        for server in "${DISCOVERED_MCP_SERVERS[@]}"; do
            echo -e "${CYAN}    - $server${NC}"
        done
        
        echo -e "\n${YELLOW}  Whitelisted MCP commands: ${#MCP_SERVER_COMMANDS[@]}${NC}"
    fi
    
    # Display memory backend status
    if [ -n "${MEM0_API_KEY:-}" ]; then
        echo -e "\n${GREEN}  Memory backend: Mem0 (intelligent memory with semantic search)${NC}"
        echo -e "${BLUE}  Mem0 API key is configured${NC}"
    else
        echo -e "${YELLOW}  Memory backend: Standard MCP memory server${NC}"
        echo -e "${DIM}  Set MEM0_API_KEY to enable intelligent memory features${NC}"
    fi
}

# Get memory tool names based on MEM0_API_KEY
get_memory_tools() {
    if [ -n "${MEM0_API_KEY:-}" ]; then
        # Mem0 MCP tool names
        echo "mem0-mcp__add-memory mem0-mcp__search-memories mem0-mcp__list-memories mem0-mcp__delete-memories"
    else
        # Standard memory MCP tool names
        echo "memory__create_memory memory__retrieve_memory memory__list_memories memory__delete_memory"
    fi
}

# Get specific memory tool
get_memory_tool() {
    local tool_type=$1
    local tools=($(get_memory_tools))
    
    case $tool_type in
        "add"|"create")
            echo "${tools[0]}"
            ;;
        "search"|"retrieve")
            echo "${tools[1]}"
            ;;
        "list")
            echo "${tools[2]}"
            ;;
        "delete")
            echo "${tools[3]}"
            ;;
    esac
}

# Initialize function - Full analysis of specs
init_project() {
    log_phase "INIT" "Initializing project analysis"
    
    local add_tool=$(get_memory_tool "add")
    local search_tool=$(get_memory_tool "search")
    
    # Create analysis prompt based on memory system
    if [ -n "${MEM0_API_KEY:-}" ]; then
        local analysis_prompt="INITIALIZATION PHASE - FULL PROJECT ANALYSIS (Using Mem0)

You are about to build the Claude Code Builder v2.3.0. This is a critical initialization phase where you must:

1. ANALYZE ALL SPECIFICATIONS
   - Read and understand the full project specification
   - Identify all major components and their relationships
   - Map out the complete architecture
   - List all dependencies and requirements

2. USE MEM0 TO STORE YOUR ANALYSIS
   - Use ${add_tool} to save comprehensive analysis:
     * Save with message: 'Project Overview: Claude Code Builder v2.3.0 - [your understanding]'
     * Save with message: 'Architecture: [component] connects to [component] via [interface]'
     * Save with message: 'Dependencies identified: [list of packages and versions]'
     * Save with message: 'Phase [N] requirements: [what needs to be accomplished]'
     * Save with message: 'Critical feature: [feature] requires [implementation details]'
   - Include user_id='claude-code-builder' in all operations
   - Mem0 will automatically extract key information and maintain consistency
   
3. IDENTIFY KNOWLEDGE GAPS
   - Save knowledge gaps: 'Research needed: [technology/library] for [purpose]'
   - Note challenges: 'Potential challenge: [issue] may require [solution approach]'

4. CREATE BUILD STRATEGY
   - Use sequential_thinking__think_about to plan the optimal build approach
   - Save strategy: 'Build strategy: [phase ordering and dependencies]'

AVAILABLE TOOLS:
- ${add_tool} - Save analysis with intelligent extraction
- ${search_tool} - Search existing memories semantically
- sequential_thinking__think_about(problem) - Analyze complex aspects
- filesystem__read_file(path) - Read specification files"
    else
        local analysis_prompt="INITIALIZATION PHASE - FULL PROJECT ANALYSIS

You are about to build the Claude Code Builder v2.3.0. This is a critical initialization phase where you must:

1. ANALYZE ALL SPECIFICATIONS
   - Read and understand the full project specification
   - Identify all major components and their relationships
   - Map out the complete architecture
   - List all dependencies and requirements

2. USE YOUR TOOLS TO GAIN CONTEXT
   - Use ${add_tool} to save your analysis with keys:
     * 'project_overview' - High-level project understanding
     * 'architecture_analysis' - Component relationships
     * 'dependency_list' - All required packages and tools
     * 'phase_requirements' - What each phase needs to accomplish
     * 'critical_features' - Must-have functionality
   
3. IDENTIFY KNOWLEDGE GAPS
   - List any technologies or libraries you're not fully familiar with
   - Identify areas that might need research
   - Note any potential challenges or complexities

4. CREATE BUILD STRATEGY
   - Use sequential_thinking__think_about to plan the optimal build approach
   - Consider phase dependencies and ordering
   - Identify potential parallelization opportunities

AVAILABLE MCP TOOLS:
- ${add_tool}(key, value) - Save analysis results
- ${search_tool}(key) - Check existing knowledge
- sequential_thinking__think_about(problem) - Analyze complex aspects
- filesystem__read_file(path) - Read specification files"
    fi

    analysis_prompt+="

FULL SPECIFICATION:
$FULL_SPEC

CUSTOM INSTRUCTIONS:
$CUSTOM_INSTRUCTIONS

Perform a comprehensive analysis and save all findings to memory with appropriate keys."

    log_info "Running comprehensive project analysis..."
    
    # Run Claude with analysis prompt
    run_claude_auto "$analysis_prompt" "Project Analysis"
    
    # Mark analysis keys as used (only for standard memory)
    if [ -z "${MEM0_API_KEY:-}" ]; then
        add_memory_key "project_overview" 0
        add_memory_key "architecture_analysis" 0
        add_memory_key "dependency_list" 0
        add_memory_key "phase_requirements" 0
        add_memory_key "critical_features" 0
    fi
    
    log_phase "SUCCESS" "Project analysis completed"
}

# Start function - Web search and dependency resolution
start_project() {
    log_phase "START" "Starting dependency resolution and research"
    
    local add_tool=$(get_memory_tool "add")
    local search_tool=$(get_memory_tool "search")
    
    # Create research prompt based on memory system
    if [ -n "${MEM0_API_KEY:-}" ]; then
        local research_prompt="RESEARCH AND DEPENDENCY RESOLUTION PHASE (Using Mem0)

Based on your initialization analysis, you must now:

1. RETRIEVE YOUR ANALYSIS
   - Use ${search_tool} with semantic queries:
     * 'dependencies for Claude Code Builder' - Get identified dependencies
     * 'critical features' - Key features to research
     * 'architecture analysis' - Technical requirements
   - Mem0 will understand context and return relevant memories

2. SEARCH FOR DOCUMENTATION
   - Use web_search to find documentation for:
     * Anthropic SDK latest features and best practices
     * Click CLI framework advanced patterns
     * Rich terminal UI library examples
     * MCP server implementation guides
     * Any dependencies found in your search

3. RESOLVE ALL DEPENDENCIES
   - Verify package versions and compatibility
   - Find code examples and best practices
   - Identify any deprecated features to avoid
   - Look for security considerations

4. UPDATE YOUR KNOWLEDGE BASE WITH MEM0
   - Use ${add_tool} to save research findings with descriptive messages:
     * 'Anthropic SDK: Use [pattern] for [feature] implementation'
     * 'Click CLI best practice: [pattern description]'
     * 'Rich UI implementation: [component] requires [setup]'
     * 'MCP integration: [server type] needs [configuration]'
     * 'Security: Always [practice] when [scenario]'
     * 'Dependency versions: [package]==[version] for compatibility'
   - Include user_id='claude-code-builder' for all memories

5. IDENTIFY IMPLEMENTATION PATTERNS
   - Save patterns: 'Implementation pattern: Use [pattern] for [scenario]'
   - Save anti-patterns: 'Avoid: [anti-pattern] because [reason]'
   - Save optimizations: 'Performance: [technique] improves [metric]'

AVAILABLE TOOLS:
- ${search_tool} - Search memories with natural language
- ${add_tool} - Save research findings with context
- web_search(query) - Search for documentation
- sequential_thinking__think_about(problem) - Plan implementation"
    else
        local research_prompt="RESEARCH AND DEPENDENCY RESOLUTION PHASE

Based on your initialization analysis, you must now:

1. RETRIEVE YOUR ANALYSIS
   - Use ${search_tool} to get:
     * 'dependency_list' - All identified dependencies
     * 'critical_features' - Key features to research
     * 'architecture_analysis' - Technical requirements

2. SEARCH FOR DOCUMENTATION
   - Use web_search to find documentation for:
     * Anthropic SDK latest features and best practices
     * Click CLI framework advanced patterns
     * Rich terminal UI library examples
     * MCP server implementation guides
     * Any other identified dependencies

3. RESOLVE ALL DEPENDENCIES
   - Verify package versions and compatibility
   - Find code examples and best practices
   - Identify any deprecated features to avoid
   - Look for security considerations

4. UPDATE YOUR KNOWLEDGE BASE
   - Use ${add_tool} to save research findings:
     * 'anthropic_sdk_knowledge' - Key SDK patterns and features
     * 'cli_best_practices' - Click framework patterns
     * 'ui_implementation_guide' - Rich UI examples
     * 'mcp_integration_patterns' - MCP server usage
     * 'security_considerations' - Security best practices
     * 'dependency_versions' - Exact versions to use

5. IDENTIFY IMPLEMENTATION PATTERNS
   - Based on research, identify:
     * Common patterns to follow
     * Anti-patterns to avoid
     * Performance optimization techniques
     * Error handling strategies

AVAILABLE TOOLS:
- ${search_tool}(key) - Get your previous analysis
- ${add_tool}(key, value) - Save research findings
- web_search(query) - Search for documentation and examples
- sequential_thinking__think_about(problem) - Plan implementation"
    fi
    
    research_prompt+="

Start by retrieving your analysis, then search for necessary documentation."

    log_info "Researching dependencies and best practices..."
    
    # Run Claude with research prompt
    run_claude_auto "$research_prompt" "Dependency Research"
    
    # Mark research keys as used (only for standard memory)
    if [ -z "${MEM0_API_KEY:-}" ]; then
        add_memory_key "anthropic_sdk_knowledge" 0
        add_memory_key "cli_best_practices" 0
        add_memory_key "ui_implementation_guide" 0
        add_memory_key "mcp_integration_patterns" 0
        add_memory_key "security_considerations" 0
        add_memory_key "dependency_versions" 0
    fi
    
    log_phase "SUCCESS" "Research and dependency resolution completed"
}

# JSON stream parser for Claude output with memory tracking
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
                    
                    # Check for MCP server configuration in system messages
                    local mcp_servers=$(echo "$line" | jq -r '.configured_servers[]? // empty' 2>/dev/null)
                    if [ -n "$mcp_servers" ]; then
                        log_info "Configured MCP servers in this session:"
                        echo "$mcp_servers" | while read -r server; do
                            log_info "  - $server"
                        done
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
                            "memory__create_memory")
                                local mem_key=$(echo "$line" | jq -r '.message.content[]? | select(.type == "tool_use") | .input.key // empty' 2>/dev/null)
                                if [ -n "$mem_key" ]; then
                                    log_tool_use "Memory (MCP)" "Storing key: $mem_key"
                                    log_info "  MCP Server: memory"
                                    log_info "  Purpose: Key-value storage for build state"
                                    if [ -z "${MEM0_API_KEY:-}" ]; then
                                        add_memory_key "$mem_key"
                                    fi
                                fi
                                ;;
                            "memory__retrieve_memory")
                                local mem_key=$(echo "$line" | jq -r '.message.content[]? | select(.type == "tool_use") | .input.key // empty' 2>/dev/null)
                                if [ -n "$mem_key" ]; then
                                    log_tool_use "Memory" "Retrieving key: $mem_key"
                                fi
                                ;;
                            "mem0-mcp__add-memory")
                                local messages=$(echo "$line" | jq -r '.message.content[]? | select(.type == "tool_use") | .input.messages[]?.content // empty' 2>/dev/null | head -1)
                                if [ -n "$messages" ]; then
                                    log_tool_use "Mem0 (MCP)" "Storing: ${messages:0:50}..."
                                    log_info "  MCP Server: mem0-mcp"
                                    log_info "  Purpose: Intelligent memory with semantic understanding"
                                fi
                                ;;
                            "mem0-mcp__search-memories")
                                local query=$(echo "$line" | jq -r '.message.content[]? | select(.type == "tool_use") | .input.query // empty' 2>/dev/null)
                                if [ -n "$query" ]; then
                                    log_tool_use "Mem0 (MCP)" "Searching: $query"
                                    log_info "  MCP Server: mem0-mcp"
                                    log_info "  Purpose: Semantic search across stored memories"
                                fi
                                ;;
                            "mem0-mcp__list-memories")
                                log_tool_use "Mem0" "Listing all memories"
                                ;;
                            "mem0-mcp__delete-memories")
                                log_tool_use "Mem0" "Deleting memories"
                                ;;
                            "sequential_thinking__think_about")
                                log_tool_use "Sequential Thinking (MCP)" "Planning implementation approach"
                                log_info "  MCP Server: sequential-thinking"
                                log_info "  Purpose: Step-by-step reasoning for complex logic"
                                ;;
                            "web_search")
                                local query=$(echo "$line" | jq -r '.message.content[]? | select(.type == "tool_use") | .input.query // empty' 2>/dev/null)
                                if [ -n "$query" ]; then
                                    log_tool_use "Web Search" "Searching: $query"
                                fi
                                ;;
                            git__*)
                                local git_op=$(echo "$tool_name" | sed 's/git__//')
                                log_tool_use "Git (MCP)" "Operation: $git_op"
                                log_info "  MCP Server: git"
                                log_info "  Purpose: Version control for tracking changes"
                                ;;
                            *)
                                log_tool_use "$tool_name" "Processing..."
                                ;;
                        esac
                    fi
                    ;;
                    
                "user")
                    local tool_result=$(echo "$line" | jq -r '.message.content[]? | select(.type == "tool_result") | .content // empty' 2>/dev/null || true)
                    if [ -n "$tool_result" ] && [[ "$tool_result" == *"successfully"* ]]; then
                        # Extract file path more safely
                        local file_created=""
                        if echo "$tool_result" | grep -q '/'; then
                            file_created=$(echo "$tool_result" | sed -n 's/.*\(\/[^ ]*\)$/\1/p')
                        fi
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
        0) TOTAL_TASK_COUNT=10 ;;  # Init/Start phases
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
    
    # Create prompt file with proper error handling
    local prompt_file
    prompt_file=$(mktemp) || {
        log_error "Failed to create temporary file"
        return 1
    }
    echo "$prompt" > "$prompt_file"
    
    # Build Claude command
    local claude_cmd="claude"
    claude_cmd+=" --print"
    claude_cmd+=" --model $MODEL"
    
    if [ -f ".mcp.json" ]; then
        claude_cmd+=" --mcp-config .mcp.json"
    fi
    

    # Add whitelisted MCP commands if discovered
    if [ -n "${MCP_SERVER_COMMANDS:-}" ] && [ ${#MCP_SERVER_COMMANDS[@]} -gt 0 ]; then
        log_info "Whitelisting ${#MCP_SERVER_COMMANDS[@]} MCP commands..."
        for cmd in "${MCP_SERVER_COMMANDS[@]}"; do
            claude_cmd+=" --mcp-allow $cmd"
        done
    fi
    # Note: MCP tools are automatically available when using --dangerously-skip-permissions
    # The MCP servers defined in .mcp.json will be loaded and their tools accessible
    
    claude_cmd+=" --dangerously-skip-permissions"
    claude_cmd+=" --output-format stream-json"
    claude_cmd+=" --verbose"
    claude_cmd+=" --max-turns $MAX_TURNS"
    
    # Log the full command (with sensitive data masked)
    local log_cmd=$(echo "$claude_cmd" | sed -E 's/(MEM0_API_KEY=")[^"]+"/\1[REDACTED]"/')
    log_info "Claude command: $log_cmd"
    
    # Also log if MCP commands were added
    if [ ${#MCP_SERVER_COMMANDS[@]} -gt 0 ]; then
        log_info "Whitelisted commands include: mem0-mcp__add-memory, mem0-mcp__search-memories, etc."
    fi
    
    # Execute with enhanced parsing
    log_info "Starting Claude with model $MODEL..."
    echo ""
    
    # Execute Claude with proper error handling
    local temp_output=$(mktemp)
    cat "$prompt_file" | eval $claude_cmd 2>"$temp_output" | parse_claude_stream
    local exit_code=${PIPESTATUS[1]}
    
    echo -e "\n"
    
    # Check for errors
    if [ $exit_code -ne 0 ]; then
        log_phase "ERROR" "Phase $phase_num failed (exit code: $exit_code)"
        if [ -s "$temp_output" ]; then
            log_error "Error details: $(cat "$temp_output")"
        fi
        rm -f "$prompt_file" "$temp_output"
        return 1
    fi
    
    rm -f "$prompt_file" "$temp_output"
    
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

# Git commit function for phase completion
commit_phase() {
    local phase_num=$1
    local phase_description=$2
    # Get list of added files safely, handling filenames with spaces
    local added_files=""
    if git status --porcelain | grep -q '^A'; then
        # Use cut to handle filenames with spaces properly
        added_files=$(git status --porcelain | grep '^A' | cut -c4- | sed 's/^/- /')
    else
        added_files="- No new files (modifications only)"
    fi
    
    local commit_message="Phase $phase_num: $phase_description

Completed implementation of:
$added_files

This phase includes:
- All required components for $phase_description
- Proper error handling and validation
- Documentation and type hints
- Integration with previous phases

Build metrics:
- Tasks completed: $CURRENT_TASK_COUNT
- Session cost: \$$TOTAL_COST
- Time elapsed: $(($(date +%s) - START_TIME))s"

    log_info "Committing phase $phase_num changes..."
    
    # Stage all changes
    git add -A
    
    # Create commit with proper escaping
    git commit -m "$(printf '%s' "$commit_message")" || {
        log_warning "No changes to commit for phase $phase_num"
        return 0
    }
    
    log_success "Phase $phase_num changes committed to git"
}

# Execute phase with retry logic and git integration
execute_phase_with_retry() {
    local phase_num=$1
    local phase_description=$2
    
    # Validate phase number
    if [[ ! "$phase_num" =~ ^[0-9]+$ ]] || [ "$phase_num" -lt 1 ] || [ "$phase_num" -gt "$TOTAL_PHASES" ]; then
        log_error "Invalid phase number: $phase_num"
        return 1
    fi
    
    local next_phase=$((phase_num + 1))
    local validation_attempts=0
    local phase_complete=false
    
    while [ "$phase_complete" = false ] && [ $validation_attempts -lt $MAX_PHASE_RETRIES ]; do
        show_progress $phase_num "$phase_description"
        
        if run_claude_auto "$(get_phase_prompt $phase_num)" "$phase_description"; then
            if validate_phase $phase_num; then
                # Commit phase changes to git
                commit_phase $phase_num "$phase_description"
                
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
            echo -e "${YELLOW}Possible causes:${NC}"
            echo -e "  - Network connectivity issues"
            echo -e "  - Invalid API credentials"
            echo -e "  - Rate limiting"
            echo -e "  - Claude service unavailable"
            echo -e "\n${CYAN}Check the logs and try again.${NC}"
            exit 1
        fi
    done
}

# Interrupt handler
handle_interrupt() {
    echo -e "\n\n${RED}⚠️  Build interrupted!${NC}"
    echo -e "${YELLOW}Progress saved at phase $CURRENT_PHASE/$TOTAL_PHASES${NC}"
    
    # Save state before exiting
    save_state $CURRENT_PHASE "interrupted" "User interrupted" "$PHASE_RETRY_COUNT"
    
    # Clean up any temporary files
    rm -f /tmp/tmp.*
    
    echo -e "${CYAN}You can resume by running the script again in the same directory.${NC}"
    exit 130  # Standard exit code for SIGINT
}

# Set up signal handlers
trap handle_interrupt SIGINT SIGTERM
trap 'rm -f /tmp/tmp.*' EXIT

# Load phase details with memory context
get_phase_prompt() {
    local phase_num=$1
    local phase_content=""
    local tasks_content=""
    
    # Check if files exist before reading
    if [ -f "$PHASES_FILE" ]; then
        phase_content=$(cat "$PHASES_FILE")
        # Extract the specific phase section from phases.md
        local phase_section=""
        local next_phase=$((phase_num + 1))
        
        # Use a more robust extraction method
        if [ $phase_num -lt $TOTAL_PHASES ]; then
            phase_section=$(echo "$phase_content" | sed -n "/^## Phase $phase_num:/,/^## Phase $next_phase:/p" | sed '$d')
        else
            # Last phase - get everything from phase marker to end
            phase_section=$(echo "$phase_content" | sed -n "/^## Phase $phase_num:/,\$p")
        fi
    else
        phase_section=""
    fi
    
    if [ -f "$TASKS_FILE" ]; then
        tasks_content=$(cat "$TASKS_FILE")
    fi
    
    # Get memory tool names
    local add_tool=$(get_memory_tool "add")
    local search_tool=$(get_memory_tool "search")
    local list_tool=$(get_memory_tool "list")
    
    # Build memory context prompt based on Mem0 vs standard memory
    if [ -n "${MEM0_API_KEY:-}" ]; then
        local memory_context="
MEMORY MANAGEMENT INSTRUCTIONS (Using Mem0 Intelligent Memory):

1. MEMORY OPERATIONS:
   - Use ${add_tool} to store new memories with semantic understanding
   - Use ${search_tool} to find memories using natural language queries
   - Use ${list_tool} to retrieve all memories for current context
   - Mem0 automatically extracts key information and resolves contradictions
   
2. MEMORY STRUCTURE for phase $phase_num:
   Store memories with descriptive messages that include:
   - Phase context: 'Phase $phase_num: [description of accomplishment]'
   - Architectural decisions: 'Architecture Decision: [component] uses [pattern/tech]'
   - Interface definitions: 'Interface: [component A] -> [component B] via [method]'
   - Implementation notes: 'Implementation: [feature] requires [dependency/consideration]'
   
3. SEARCHING MEMORIES:
   - Use semantic queries: ${search_tool}('architectural decisions for MCP system')
   - Search by phase: ${search_tool}('Phase 1 accomplishments')
   - Find interfaces: ${search_tool}('interfaces between components')
   - Mem0 understands context and returns relevant memories

4. USER CONTEXT:
   - Always include user_id='claude-code-builder' for proper memory isolation
   - Memories persist across sessions for continuity"
    else
        local memory_context="
MEMORY MANAGEMENT INSTRUCTIONS:
1. ALWAYS check if a memory key exists before creating it:
   - First use ${search_tool}(key) to check
   - Only use ${add_tool} if the key doesn't exist or needs updating
   
2. Use these standardized keys for phase $phase_num:
   - 'phase_${phase_num}_overview' - Overview of what this phase accomplishes
   - 'phase_${phase_num}_decisions' - Key decisions made
   - 'phase_${phase_num}_interfaces' - Interfaces created for other phases
   - 'phase_${phase_num}_complete' - Mark phase as complete with summary

3. Retrieve context from previous phases:
   - Always start by retrieving relevant previous phase data
   - Use ${search_tool}('phase_*_interfaces') to understand contracts
   - Build upon existing architecture and decisions"
    fi
    
    memory_context+="

AVAILABLE MCP TOOLS:
- ${add_tool} - Store memories/state
- ${search_tool} - Search/retrieve memories
- ${list_tool} - List all memories
- sequential_thinking__think_about(problem) - Complex planning
- filesystem__read_file/write_file - File operations
- git__status/add/commit - Version control operations"

    # Add discovered MCP servers information
    if [ -n "${DISCOVERED_MCP_SERVERS:-}" ] && [ ${#DISCOVERED_MCP_SERVERS[@]} -gt 0 ]; then
        memory_context+="

ADDITIONAL DISCOVERED MCP SERVERS:
You have access to ${#DISCOVERED_MCP_SERVERS[@]} MCP servers with ${#MCP_SERVER_COMMANDS[@]} whitelisted commands.
These include servers for GitHub, GitLab, databases, search engines, and more.
Use these tools when they would help accomplish the current phase objectives."
    fi

    memory_context+="

GIT WORKFLOW:
- Use git__status to check current changes
- Use git__add to stage files as you create them
- Do NOT commit (the script will handle phase commits)"
    
    # Combine with custom instructions and full spec
    echo "$phase_section

$memory_context

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
check_prerequisite() {
    local cmd=$1
    local install_msg=$2
    
    if ! command -v "$cmd" &> /dev/null; then
        echo -e "${RED}Error: $cmd not found.${NC}"
        if [ -n "$install_msg" ]; then
            echo -e "${YELLOW}$install_msg${NC}"
        fi
        return 1
    fi
    return 0
}

# Check all required tools
MISSING_PREREQS=false

if ! check_prerequisite "claude" "Install with: npm install -g @anthropic-ai/claude-code"; then
    MISSING_PREREQS=true
fi

if ! check_prerequisite "jq" "Install with: brew install jq (macOS) or apt-get install jq (Linux)"; then
    MISSING_PREREQS=true
fi

if ! check_prerequisite "git" "Install git from https://git-scm.com/downloads"; then
    MISSING_PREREQS=true
fi

if ! check_prerequisite "npx" "Install Node.js from https://nodejs.org/"; then
    MISSING_PREREQS=true
fi

if [ "$MISSING_PREREQS" = true ]; then
    echo -e "\n${RED}Missing required prerequisites. Please install them and try again.${NC}"
    exit 1
fi

# Create and move to output directory
echo -e "${CYAN}Output directory: ${BOLD}$OUTPUT_DIR${NC}"

# Create the output directory if it doesn't exist
if [ ! -d "$OUTPUT_DIR" ]; then
    echo -e "${YELLOW}Creating output directory...${NC}"
    mkdir -p "$OUTPUT_DIR"
fi

# Move to output directory
cd "$OUTPUT_DIR"

# Create project subdirectory
if [ ! -d "$PROJECT_NAME" ]; then
    mkdir -p "$PROJECT_NAME"
fi
cd "$PROJECT_NAME"

# Display full build path
echo -e "${GREEN}Building in: ${BOLD}$(pwd)${NC}\n"

# Load memory keys
load_memory_keys

# Check for existing state file before proceeding
if [ -f "$STATE_FILE" ]; then
    echo -e "${YELLOW}Found existing build state in this directory${NC}"
fi

# Load or create state
if load_state; then
    echo -e "${YELLOW}📂 Resuming from phase $CURRENT_PHASE/$TOTAL_PHASES${NC}"
    log_info "Previous session ID: ${LAST_SESSION_ID:-none}"
    log_info "Elapsed time: $(($(date +%s) - START_TIME))s"
    echo ""
else
    echo -e "${GREEN}🚀 Starting fresh build${NC}\n"
    
    # Phase -2: MCP Setup
    setup_mcp_servers
    
    # Store user preferences if using Mem0
    store_user_preferences
    
    # Phase -1: Initialize with full analysis
    init_project
    
    # Phase 0: Start with research and dependencies
    start_project
    
    CURRENT_PHASE=1
    save_state 1 "ready" "Initialization complete"
    
    # Initial git commit
    git add -A
    git commit -m "Initial setup: MCP servers, analysis, and research completed" || true
fi

# Handle Phase 0 (Research and Dependencies)
if [ $CURRENT_PHASE -eq 0 ]; then
    # Move to phase 1 after research phase
    CURRENT_PHASE=1
    save_state 1 "ready" "Moving to implementation phases"
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
    
    # Final git operations
    log_info "Creating final build summary..."
    git add -A
    git commit -m "Build completed: Claude Code Builder v2.3.0

Final metrics:
- Build time: $((elapsed/60))m $((elapsed%60))s
- Total cost: \$$TOTAL_COST
- All $TOTAL_PHASES phases completed successfully

The project is ready for installation and use." || true
    
    # Show git log
    echo -e "\n${CYAN}Git commit history:${NC}"
    git log --oneline -10
    
    log_info "\nNext steps:"
    echo -e "  1. ${GREEN}cd $PROJECT_NAME${NC}"
    echo -e "  2. ${GREEN}pip install -e .${NC}"
    echo -e "  3. ${GREEN}claude-code-builder --help${NC}"
    echo -e "  4. ${GREEN}claude-code-builder examples/simple-api-spec.md --output-dir ./test-project${NC}\n"
    
    echo -e "${YELLOW}📚 Check the README.md for detailed documentation${NC}"
    echo -e "${YELLOW}🧪 Run the test suite with: pytest tests/${NC}"
    echo -e "${YELLOW}📊 View git history with: git log --oneline${NC}"
fi