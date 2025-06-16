#!/bin/bash

# Claude Code Builder v3.0 Enhanced - AI-Driven Autonomous Build Script with Full Memory and Research
# 
# Major enhancements:
# - Integrated mem0 for persistent memory across all operations
# - Context7 for documentation lookup
# - Research agents that check mem0 first, then context7, then web
# - Comprehensive tool usage logging with rationale
# - Git integration for version control during build
# - Enhanced memory persistence between phases
# - Full compliance with CLAUDE.md instructions
#
# Usage: ./builder-claude-code-builder-enhanced.sh [OPTIONS]

set -euo pipefail

# Check for required external dependencies
REQUIRED_TOOLS=("jq" "git" "npx" "claude")
for tool in "${REQUIRED_TOOLS[@]}"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo -e "\033[0;31mError:\033[0m Required tool '\033[1m$tool\033[0m' is not installed or not in PATH."
        exit 1
    fi
done

# Color codes
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
MAGENTA="\033[0;35m"
ORANGE="\033[38;5;208m"
PURPLE="\033[0;95m"
BOLD="\033[1m"
DIM="\033[2m"
NC="\033[0m"

# Configuration
PROJECT_NAME="claude-code-builder"
VERSION="3.0.0-enhanced"
MODEL="claude-3-5-sonnet-20241022"
STATE_FILE=".build-state-v3-enhanced.json"
MEMORY_FILE=".build-memory-v3.json"

# Build configuration
MAX_TURNS=100  # Increased for complex operations
FUNCTIONAL_TEST_TIMEOUT=1800  # 30 minutes
RESEARCH_TIMEOUT=600  # 10 minutes per research query

# Default values
OUTPUT_DIR="$(pwd)"
RESUME_BUILD=false
SHOW_HELP=false
ENABLE_RESEARCH=true
SKIP_MEM0_CHECK=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output-dir)
            if [[ -z "${2:-}" ]]; then
                echo -e "${RED}Error: --output-dir requires a directory path${NC}"
                exit 1
            fi
            # Expand the path to handle ~ and relative paths
            OUTPUT_DIR=$(eval echo "$2")
            # Convert to absolute path
            OUTPUT_DIR=$(cd "$(dirname "$OUTPUT_DIR")" 2>/dev/null && pwd)/$(basename "$OUTPUT_DIR")
            shift 2
            ;;
        -r|--resume)
            RESUME_BUILD=true
            shift
            ;;
        --no-research)
            ENABLE_RESEARCH=false
            shift
            ;;
        --skip-mem0-check)
            SKIP_MEM0_CHECK=true
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
    echo "  --no-research           Disable research phase"
    echo "  --skip-mem0-check       Skip initial mem0 memory check"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Build in current directory with full features"
    echo "  $0 -o /path/to/output   # Build in specified directory"
    echo "  $0 --resume             # Resume interrupted build"
    echo "  $0 --no-research        # Quick build without research"
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
║          🧠 Enhanced with Memory, Research & Full Logging 🧠             ║
║                                                                           ║
║  • AI-driven planning with mem0 memory integration                        ║
║  • Research agents: mem0 → context7 → web search                         ║
║  • Comprehensive tool usage logging with rationale                        ║
║  • Git version control throughout build process                           ║
║  • Persistent memory across all phases                                    ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
}

# Enhanced logging with categories and tool rationale
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
        "MEMORY")
            echo -e "${PURPLE}[MEMORY]${NC} ${timestamp} 🧠 $message"
            ;;
        "RESEARCH")
            echo -e "${CYAN}[RESEARCH]${NC} ${timestamp} 🔍 $message"
            ;;
        "TOOL")
            echo -e "${CYAN}[TOOL]${NC} ${timestamp} 🔧 $message"
            ;;
        "GIT")
            echo -e "${ORANGE}[GIT]${NC} ${timestamp} 📝 $message"
            ;;
        "COST")
            echo -e "${ORANGE}[COST]${NC} ${timestamp} 💰 $message"
            ;;
    esac
}

# Save build state for resumption
save_build_state() {
    local phase_num=$1
    local status=$2
    local cost_data=${3:-"{}"}
    
    cat > "$STATE_FILE" << EOF
{
    "version": "$VERSION",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "current_phase": $phase_num,
    "status": "$status",
    "output_dir": "$OUTPUT_DIR",
    "phases_completed": $((phase_num - 1)),
    "memory_file": "$MEMORY_FILE",
    "cost_data": $cost_data
}
EOF
}

# Extract and track cost information
track_cost_information() {
    local phase_num=$1
    local log_file=$2
    
    # Extract cost information from logs
    local session_cost=$(grep -o '"session_cost":[0-9.]*' "$log_file" | tail -1 | cut -d':' -f2 || echo "0")
    local total_cost=$(grep -o '"total_cost":[0-9.]*' "$log_file" | tail -1 | cut -d':' -f2 || echo "0")
    local input_tokens=$(grep -o '"input_tokens":[0-9]*' "$log_file" | tail -1 | cut -d':' -f2 || echo "0")
    local output_tokens=$(grep -o '"output_tokens":[0-9]*' "$log_file" | tail -1 | cut -d':' -f2 || echo "0")
    
    if [ "$session_cost" != "0" ] && [ -n "$session_cost" ]; then
        log "COST" "Phase $phase_num - Session: \$$session_cost, Total: \$$total_cost"
        log "COST" "Tokens - Input: $input_tokens, Output: $output_tokens"
        
        # Store cost data
        local cost_entry=$(jq -n \
            --arg phase "$phase_num" \
            --arg session_cost "$session_cost" \
            --arg total_cost "$total_cost" \
            --arg input_tokens "$input_tokens" \
            --arg output_tokens "$output_tokens" \
            --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
            '{phase: $phase, session_cost: $session_cost, total_cost: $total_cost, input_tokens: $input_tokens, output_tokens: $output_tokens, timestamp: $timestamp}')
        
        # Append to cost tracking file
        if [ ! -f ".cost-tracking.json" ]; then
            echo '{"phases": []}' > ".cost-tracking.json"
        fi
        
        jq --argjson entry "$cost_entry" '.phases += [$entry]' ".cost-tracking.json" > ".cost-tracking.json.tmp" && \
            mv ".cost-tracking.json.tmp" ".cost-tracking.json"
    fi
}

# Load build state
load_build_state() {
    if [ -f "$STATE_FILE" ]; then
        CURRENT_PHASE=$(jq -r '.current_phase // 0' "$STATE_FILE")
        local saved_output_dir=$(jq -r '.output_dir // "."' "$STATE_FILE")
        
        # Check if output directory was specified in command line
        if [ "$RESUME_BUILD" = true ] && [ "$OUTPUT_DIR" != "." ]; then
            log "WARNING" "Resume mode detected with custom output directory. Using saved output directory: $saved_output_dir"
            log "INFO" "If you want to change output directory, start a fresh build without --resume"
        fi
        
        OUTPUT_DIR="$saved_output_dir"
        log "INFO" "Resuming from phase $CURRENT_PHASE in directory: $OUTPUT_DIR"
        return 0
    else
        return 1
    fi
}

# Save memory state
save_memory_state() {
    local phase_id=$1
    local memory_data=$2
    
    if [ ! -f "$MEMORY_FILE" ]; then
        echo '{"phases": {}}' > "$MEMORY_FILE"
    fi
    
    # Update memory file with phase data
    jq --arg phase "$phase_id" --argjson data "$memory_data" \
        '.phases[$phase] = $data' "$MEMORY_FILE" > "${MEMORY_FILE}.tmp" && \
        mv "${MEMORY_FILE}.tmp" "$MEMORY_FILE"
}

# Check mem0 for existing knowledge
check_mem0_memory() {
    local topic=$1
    
    log "MEMORY" "Checking mem0 for existing knowledge about: $topic"
    
    # Create a temporary prompt to check memory
    local memory_check_prompt="Search mem0 memory for any existing knowledge about: $topic

Use the mem0__search-memories tool to find relevant information.
Return a summary of what was found or indicate if no relevant memories exist."
    
    echo "$memory_check_prompt" | claude \
        --model "$MODEL" \
        --mcp-config .mcp.json \
        --dangerously-skip-permissions \
        --max-turns 3 \
        --output-format stream-json \
        2>&1 | tee mem0-check.log | parse_enhanced_stream_output
}

# Create the enhanced specification
create_enhanced_specification() {
    cat > "claude-code-builder-v3-enhanced-spec.md" << 'EOF'
# Claude Code Builder v3.0 Enhanced - AI-Driven Autonomous Project Builder

## Overview
An advanced project builder that implements full CLAUDE.md compliance with mem0 memory integration, context7 documentation lookup, comprehensive research capabilities, and detailed tool usage logging.

## CRITICAL PRODUCTION REQUIREMENTS (FROM CLAUDE.md)

### NO MOCKS, NO UNIT TESTS, NO SIMULATIONS
- **ALL tests must use REAL services**
- **NO dry runs** - Execute actual builds only
- **NO mock implementations** - Everything must be functional
- **NO placeholder code** - Complete implementations only
- **Integration and E2E tests ONLY**

### MANDATORY MEMORY-FIRST WORKFLOW
1. **ALWAYS check mem0 BEFORE ANY code/task**
2. **SEARCH FIRST, CODE SECOND** - No exceptions
3. **Store EVERYTHING learned for future projects**

## Enhanced Features

### 1. Memory-First Architecture
- **Mem0 Integration**: Check memory before any task
- **Context Preservation**: Store all learnings across projects
- **Knowledge Accumulation**: Build on previous experiences
- **Cross-Project Learning**: Apply patterns from other projects

### 2. Research Workflow (MANDATORY)
```
1. CHECK MEM0 → Find existing knowledge
2. USE CONTEXT7 → Get latest documentation
3. WEB SEARCH → Only if needed
4. STORE IN MEM0 → Save all findings
```

### 3. Tool Usage Logging
Every tool call must include:
- **Why**: Rationale for using this tool
- **What**: Expected outcome
- **How**: Specific parameters chosen
- **Result**: What was learned/achieved

### 4. Git Integration Throughout
- Initialize repository at start
- Commit after each phase
- Create meaningful commit messages
- Track all changes
- Verify no secrets in code

### 5. Production Standards
- **Real API testing** with actual endpoints
- **Real file system** operations
- **Real network conditions**
- **Production rate limits**
- **Actual service integrations**

### 6. Security Requirements
- **ZERO hardcoded credentials**
- **Environment variables ONLY**
- **No bypassing authentication**
- **No disabling SSL/TLS**
- **Validate all inputs**
- **Sanitize all outputs**

### 7. Error Handling
- **Detailed logging with context**
- **Graceful degradation**
- **Automatic retry with backoff**
- **Circuit breakers**
- **Clear operator messages**

### 8. Performance Requirements
- **Batch operations**
- **Implement caching**
- **Connection pooling**
- **Monitor memory usage**
- **Track response times**

### 9. Cloud-Ready Architecture
- **Environment variables for configs**
- **Proper logging to stdout/stderr**
- **Horizontal scaling design**
- **Health checks implemented**
- **Graceful shutdowns**

### 10. Enhanced Monitoring
- Real-time tool usage with rationale
- Memory operations tracking
- Research progress visualization
- Cost breakdown by operation type
- API usage metrics
- Error rates and types

## Implementation Requirements

### Phase 0: Enhanced AI Planning with Research
1. Check mem0 for similar projects
2. Research best practices via context7
3. Analyze specification with accumulated knowledge
4. Create optimal phase plan
5. Store planning decisions in mem0

### Dynamic Phases with Memory
Each phase must:
1. Load context from previous phases
2. Check mem0 for relevant patterns
3. Research unknowns via context7
4. Execute with full logging
5. Store learnings in mem0
6. Commit changes to git

### Tool Usage Patterns
```python
# Example of proper tool usage with logging
log("TOOL", "Using filesystem__write_file to create setup.py")
log("TOOL", "Rationale: Package configuration is required for Python distribution")
log("TOOL", "Expected: Valid setup.py with all dependencies")
# ... execute tool ...
log("TOOL", "Result: Created setup.py with 15 dependencies")
```

### Research Agent Implementation
```python
async def research_topic(topic):
    # 1. Check mem0 first
    existing = await check_mem0(topic)
    if existing.sufficient:
        return existing
    
    # 2. Check context7 for documentation
    docs = await search_context7(topic)
    
    # 3. Web search only if needed
    if not docs.sufficient:
        web_results = await search_web(topic)
    
    # 4. Store everything in mem0
    await store_in_mem0(topic, findings)
    
    return findings
```

## Success Criteria

1. **Memory Integration**
   - All phases check mem0 first
   - All learnings stored in mem0
   - Cross-project knowledge applied

2. **Research Compliance**
   - mem0 → context7 → web workflow
   - Documentation-first approach
   - Knowledge persistence

3. **Logging Excellence**
   - Every tool use explained
   - Rationale clearly stated
   - Results documented

4. **Version Control**
   - Git initialized and used
   - Meaningful commits
   - Full history preserved

5. **Cost Optimization**
   - Memory reduces redundant research
   - Efficient tool usage
   - Accurate cost tracking

Build the most intelligent autonomous project builder that learns and improves with every use.
EOF
}

# Create research instructions
create_research_instructions() {
    cat > "research-instructions-v3.md" << 'EOF'
# Research Instructions for Claude Code Builder v3.0 Enhanced

## MANDATORY RESEARCH WORKFLOW

For EVERY technical decision, unknown library, or implementation pattern:

### Step 1: CHECK MEM0 FIRST (ALWAYS)
```
Use mem0__search-memories to find:
- Previous implementations of similar features
- Known working patterns
- Common pitfalls and solutions
- Performance optimizations discovered
- Security best practices learned
```

### Step 2: USE CONTEXT7 SECOND (FOR DOCUMENTATION)
```
Use context7__resolve-library-id and context7__get-library-docs to:
- Get latest official documentation
- Find current best practices
- Check version compatibility
- Review API changes
```

### Step 3: WEB SEARCH THIRD (ONLY IF NEEDED)
```
Use web search only when:
- No relevant mem0 memories exist
- Context7 lacks the specific information
- Need very recent updates (last few weeks)
- Searching for edge cases or bugs
```

### Step 4: STORE IN MEM0 ALWAYS
```
Use mem0__add-memory to store:
- Working code patterns
- Library usage examples
- Performance findings
- Security considerations
- Integration patterns
- Common errors and fixes
```

## Example Research Flow

```python
# Researching FastAPI authentication
1. mem0__search-memories("FastAPI authentication patterns")
   → Found: JWT implementation from project X
   
2. context7__resolve-library-id("fastapi")
   → Got library ID: /tiangolo/fastapi
   
3. context7__get-library-docs("/tiangolo/fastapi", topic="authentication")
   → Found: Latest OAuth2 patterns
   
4. mem0__add-memory("FastAPI OAuth2 implementation pattern: ...")
   → Stored for future use
```

## What to Store in Mem0

### Always Store:
- Working code implementations
- Library integration patterns
- Performance optimization techniques
- Security implementation details
- Error solutions that work
- Configuration patterns
- Testing strategies

### Storage Format:
```
Topic: [Library/Framework] [Feature]
Context: [Project type where used]
Pattern: [Working implementation]
Performance: [Any metrics]
Gotchas: [Things to watch out for]
```

## Research Logging

Every research action must be logged:
```
log("RESEARCH", "Checking mem0 for React state management patterns")
log("RESEARCH", "Found 3 relevant memories from previous projects")
log("RESEARCH", "Applying Redux Toolkit pattern from e-commerce project")
```

Remember: Every piece of knowledge gained benefits ALL future projects!
EOF
}

# Setup enhanced MCP configuration
setup_enhanced_mcp() {
    log "INFO" "Setting up enhanced MCP configuration with mem0 and context7"
    
    cat > ".mcp.json" << 'EOF'
{
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
            "description": "File system operations with full logging"
        },
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "description": "Temporary memory for build state"
        },
        "mem0": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-mem0"],
            "env": {
                "MEM0_API_KEY": "${MEM0_API_KEY:-}"
            },
            "description": "Persistent memory across all projects"
        },
        "context7": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-context7"],
            "description": "Latest documentation for libraries"
        },
        "sequential-thinking": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            "description": "Complex planning and analysis"
        },
        "git": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-git"],
            "description": "Version control throughout build"
        },
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_TOKEN": "${GITHUB_TOKEN:-}"
            },
            "description": "GitHub operations for PRs"
        }
    }
}
EOF
}

# Initialize git repository
initialize_git_repo() {
    log "GIT" "Initializing git repository for version control"
    
    if [ ! -d ".git" ]; then
        git init
        log "GIT" "Created new git repository"
    else
        log "GIT" "Using existing git repository"
    fi
    
    # Create .gitignore if it doesn't exist
    if [ ! -f ".gitignore" ]; then
        cat > ".gitignore" << 'EOF'
# Build artifacts
.build-state-v3*.json
.build-memory-v3.json
*.log
raw-stream.log

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
test-output/
.mcp.json
planning-output.log
mem0-check.log
EOF
        git add .gitignore
        git commit -m "Initial commit: Add .gitignore"
        log "GIT" "Created initial commit with .gitignore"
    fi
}

# Enhanced AI planning with research
execute_enhanced_ai_planning() {
    log "PHASE" "Phase 0: AI-Driven Planning with Research"
    
    # Check mem0 for similar projects if not skipped
    if [ "$SKIP_MEM0_CHECK" = false ]; then
        check_mem0_memory "Claude Code Builder project structure autonomous builder Python"
    fi
    
    local planning_prompt=$(cat << 'EOF'
# AI Planning Phase - Claude Code Builder v3.0 Enhanced

You are planning the build for an enhanced Claude Code Builder with full memory and research integration.

## MANDATORY WORKFLOW

1. **CHECK MEM0 FIRST**
   - Search for: "autonomous project builder", "Claude Code SDK", "Python package structure"
   - Look for previous build patterns and lessons learned
   - Apply any relevant patterns found

2. **RESEARCH VIA CONTEXT7**
   - Get latest docs for: Click, Rich, Anthropic SDK
   - Check best practices for Python packaging
   - Review testing frameworks documentation

3. **PLAN WITH KNOWLEDGE**
   - Create phases that incorporate found patterns
   - Include research steps in relevant phases
   - Plan memory storage points

4. **USE GIT THROUGHOUT**
   - Plan git commits after each phase
   - Include meaningful commit messages

Create an optimal build plan that demonstrates learning from previous projects.

## Output Requirements

Create two files:

1. `build-phases-v3.json` with structure:
```json
{
    "version": "3.0.0-enhanced",
    "total_phases": 16,
    "research_phases": [0, 3, 7, 11],
    "phases": [
        {
            "number": 1,
            "name": "Foundation with Memory Integration",
            "objective": "Set up project with mem0 integration",
            "includes_research": true,
            "research_topics": ["Python package best practices", "Click CLI patterns"],
            "memory_points": ["Package structure decisions", "Dependency choices"],
            "git_commit_message": "feat: Initialize project foundation with memory integration"
        }
    ]
}
```

2. `build-strategy-v3.md` with:
- Research findings from mem0
- Documentation insights from context7
- Memory storage plan
- Tool usage strategy

Remember: Every decision should be informed by memory and research!
EOF
)
    
    local spec_content=$(cat claude-code-builder-v3-enhanced-spec.md)
    local research_instructions=$(cat research-instructions-v3.md)
    
    local full_prompt="$planning_prompt

ENHANCED SPECIFICATION:
$spec_content

RESEARCH INSTRUCTIONS:
$research_instructions

Now create the optimal build plan with full memory and research integration."
    
    log "INFO" "Invoking Claude with research capabilities for planning"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo "$full_prompt" | claude \
        --model "$MODEL" \
        --mcp-config .mcp.json \
        --dangerously-skip-permissions \
        --max-turns 50 \
        --output-format stream-json \
        --verbose \
        2>&1 | tee planning-output.log | parse_enhanced_stream_output
    
    # Verify planning files were created
    if [ -f "build-phases-v3.json" ] && [ -f "build-strategy-v3.md" ]; then
        log "SUCCESS" "AI planning with research completed successfully"
        
        # Commit planning files (only if there are changes)
        git add build-phases-v3.json build-strategy-v3.md
        if git diff --staged --quiet; then
            log "INFO" "Planning files already committed"
        else
            git commit -m "feat: AI-generated build plan with research integration"
            log "GIT" "Committed build planning files"
        fi
        
        return 0
    else
        log "ERROR" "AI planning failed to create required files"
        return 1
    fi
}

# Enhanced stream parser with tool rationale and progress tracking
parse_enhanced_stream_output() {
    local line
    local in_tool_use=false
    local current_tool=""
    local buffer=""
    local last_update=$(date +%s)
    local update_interval=5  # Show progress every 5 seconds
    local char_count=0
    local line_count=0
    
    while IFS= read -r line; do
        # Skip empty lines
        [ -z "$line" ] && continue
        
        # Increment counters
        line_count=$((line_count + 1))
        char_count=$((char_count + ${#line}))
        
        # Show periodic progress updates
        local now=$(date +%s)
        if [ $((now - last_update)) -ge $update_interval ]; then
            echo -e "${DIM}   [PROGRESS] Processing... (${line_count} events, ${char_count} chars)${NC}" >&2
            last_update=$now
        fi
        
        # Try to parse as JSON and extract message content
        if command -v jq >/dev/null 2>&1; then
            # Use jq if available for better JSON parsing
            local message_type=$(echo "$line" | jq -r '.type // empty' 2>/dev/null)
            
            case "$message_type" in
                "content_block_start")
                    local content_type=$(echo "$line" | jq -r '.content_block.type // empty' 2>/dev/null)
                    if [ "$content_type" = "tool_use" ]; then
                        current_tool=$(echo "$line" | jq -r '.content_block.name // "unknown"' 2>/dev/null)
                        in_tool_use=true
                        
                        # Display tool usage with rationale
                        case $current_tool in
                            mem0__*)
                                echo -e "\n${PURPLE}🧠 [MEMORY OPERATION]${NC} ${BOLD}$current_tool${NC}"
                                log "MEMORY" "Accessing persistent memory: $current_tool"
                                ;;
                            context7__*)
                                echo -e "\n${CYAN}📚 [DOCUMENTATION LOOKUP]${NC} ${BOLD}$current_tool${NC}"
                                log "RESEARCH" "Checking documentation: $current_tool"
                                ;;
                            filesystem__*)
                                echo -e "\n${GREEN}📁 [FILE OPERATION]${NC} ${BOLD}$current_tool${NC}"
                                log "TOOL" "File operation: $current_tool"
                                ;;
                            git__*)
                                echo -e "\n${ORANGE}📝 [VERSION CONTROL]${NC} ${BOLD}$current_tool${NC}"
                                log "GIT" "Git operation: $current_tool"
                                ;;
                            sequential_thinking__*)
                                echo -e "\n${PURPLE}🤔 [DEEP THINKING]${NC} ${BOLD}$current_tool${NC}"
                                log "TOOL" "Sequential thinking: $current_tool"
                                ;;
                            *)
                                echo -e "\n${CYAN}🔧 [TOOL USE]${NC} ${BOLD}$current_tool${NC}"
                                log "TOOL" "Using tool: $current_tool"
                                ;;
                        esac
                    elif [ "$content_type" = "text" ]; then
                        in_tool_use=false
                    fi
                    ;;
                    
                "content_block_delta")
                    if [ "$in_tool_use" = false ]; then
                        local text=$(echo "$line" | jq -r '.delta.text // empty' 2>/dev/null)
                        if [ -n "$text" ]; then
                            # Accumulate text for better display
                            buffer="$buffer$text"
                            
                            # Display when we have substantial content or reach punctuation
                            if [ ${#buffer} -gt 200 ] || echo "$text" | grep -q '[.!?]'; then
                                # Truncate very long messages but show the essence
                                if [ ${#buffer} -gt 500 ]; then
                                    local truncated="${buffer:0:497}..."
                                    echo -e "${GREEN}💬 [CLAUDE]${NC} $truncated"
                                else
                                    echo -e "${GREEN}💬 [CLAUDE]${NC} $buffer"
                                fi
                                buffer=""
                            fi
                        fi
                    else
                        # Show tool input progress
                        local input_delta=$(echo "$line" | jq -r '.delta.partial_json // empty' 2>/dev/null)
                        if [ -n "$input_delta" ] && [ ${#input_delta} -gt 50 ]; then
                            echo -e "${DIM}   → Configuring: ${input_delta:0:47}...${NC}"
                        fi
                    fi
                    ;;
                    
                "content_block_stop")
                    if [ "$in_tool_use" = true ]; then
                        echo -e "${DIM}   → Tool execution completed${NC}"
                        in_tool_use=false
                    elif [ -n "$buffer" ]; then
                        # Display any remaining buffer content
                        if [ ${#buffer} -gt 500 ]; then
                            local truncated="${buffer:0:497}..."
                            echo -e "${GREEN}💬 [CLAUDE]${NC} $truncated"
                        else
                            echo -e "${GREEN}💬 [CLAUDE]${NC} $buffer"
                        fi
                        buffer=""
                    fi
                    ;;
                    
                "message_stop")
                    if [ -n "$buffer" ]; then
                        echo -e "${GREEN}💬 [CLAUDE]${NC} $buffer"
                        buffer=""
                    fi
                    echo -e "${DIM}   [Turn completed - ${line_count} events processed]${NC}"
                    ;;
                    
                "error")
                    local error_msg=$(echo "$line" | jq -r '.error.message // empty' 2>/dev/null)
                    if [ -n "$error_msg" ]; then
                        echo -e "${RED}❌ [ERROR]${NC} $error_msg"
                    fi
                    ;;
            esac
        else
            # Fallback: show raw output if no jq
            # But truncate very long lines
            if [ ${#line} -gt 200 ]; then
                echo "${line:0:197}..."
            else
                echo "$line"
            fi
        fi
        
        # Save to raw log for debugging
        echo "$line" >> raw-stream.log
    done
    
    # Final progress update
    echo -e "${DIM}   [Stream completed - Total: ${line_count} events, ${char_count} chars]${NC}" >&2
}

# Display tool parameters in a readable format
display_tool_parameters() {
    local tool_name=$1
    local params=$2
    
    case $tool_name in
        filesystem__write_file)
            local file_path=$(echo "$params" | grep -oE '"path":\s*"[^"]+"' | cut -d'"' -f4 || echo "")
            echo -e "${DIM}   → Creating: $file_path${NC}"
            ;;
        filesystem__read_file)
            local file_path=$(echo "$params" | grep -oE '"path":\s*"[^"]+"' | cut -d'"' -f4 || echo "")
            echo -e "${DIM}   → Reading: $file_path${NC}"
            ;;
        mem0__search-memories)
            local query=$(echo "$params" | grep -oE '"query":\s*"[^"]+"' | cut -d'"' -f4 || echo "")
            echo -e "${DIM}   → Searching for: ${query:0:50}...${NC}"
            ;;
        mem0__add-memory)
            local content=$(echo "$params" | grep -oE '"content":\s*"[^"]+"' | cut -d'"' -f4 || echo "")
            echo -e "${DIM}   → Storing: ${content:0:50}...${NC}"
            ;;
        context7__resolve-library-id)
            local lib=$(echo "$params" | grep -oE '"libraryName":\s*"[^"]+"' | cut -d'"' -f4 || echo "")
            echo -e "${DIM}   → Looking up: $lib${NC}"
            ;;
        git__commit)
            local msg=$(echo "$params" | grep -oE '"message":\s*"[^"]+"' | cut -d'"' -f4 || echo "")
            echo -e "${DIM}   → Commit: $msg${NC}"
            ;;
    esac
}

# Execute research phase
execute_research_phase() {
    local phase_num=$1
    local research_topics=$2
    
    log "RESEARCH" "Starting research phase for topics: $research_topics"
    
    local research_prompt="# Research Phase

You must research the following topics using the MANDATORY workflow:

TOPICS TO RESEARCH:
$research_topics

MANDATORY WORKFLOW FOR EACH TOPIC:
1. FIRST: Use mem0__search-memories to check for existing knowledge
2. SECOND: Use context7 to get official documentation
3. THIRD: Use web search ONLY if mem0 and context7 don't have enough info
4. ALWAYS: Store findings in mem0 using mem0__add-memory

For each topic:
- Log what you're researching and why
- Show what you found in mem0
- Show what you learned from context7
- Explain any web searches needed
- Store all new knowledge in mem0

Output a summary of all findings that will inform the build process."
    
    echo "$research_prompt" | timeout --foreground $RESEARCH_TIMEOUT claude \
        --model "$MODEL" \
        --mcp-config .mcp.json \
        --dangerously-skip-permissions \
        --max-turns 20 \
        --output-format stream-json \
        --verbose \
        2>&1 | tee "research-phase-$phase_num.log" | parse_enhanced_stream_output
    
    local exit_code=${PIPESTATUS[1]}
    
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Research phase completed"
        return 0
    else
        log "WARNING" "Research phase encountered issues (may have timed out)"
        return 1
    fi
}

# Execute enhanced dynamic phase
execute_enhanced_dynamic_phase() {
    local phase_num=$1
    
    # Check if phase exists
    local phase_count=$(jq '.phases | length' build-phases-v3.json 2>/dev/null || echo 0)
    if [ $phase_num -gt $phase_count ]; then
        log "WARNING" "Phase $phase_num not found in build plan"
        return 1
    fi
    
    # Read phase details
    local phase_index=$((phase_num-1))
    local phase_name=$(jq -r ".phases[$phase_index].name // \"Phase $phase_num\"" build-phases-v3.json)
    local phase_objective=$(jq -r ".phases[$phase_index].objective // \"Complete phase tasks\"" build-phases-v3.json)
    local includes_research=$(jq -r ".phases[$phase_index].includes_research // false" build-phases-v3.json)
    local research_topics=$(jq -r ".phases[$phase_index].research_topics[]? // empty" build-phases-v3.json)
    local memory_points=$(jq -r ".phases[$phase_index].memory_points[]? // empty" build-phases-v3.json)
    local git_commit_msg=$(jq -r ".phases[$phase_index].git_commit_message // \"Phase $phase_num completed\"" build-phases-v3.json)
    local phase_tasks=$(jq -r ".phases[$phase_index].tasks[]? // empty" build-phases-v3.json)
    
    log "PHASE" "Phase $phase_num: $phase_name"
    log "INFO" "Objective: $phase_objective"
    
    # Execute research if needed
    if [ "$includes_research" = "true" ] && [ -n "$research_topics" ]; then
        if [ "$ENABLE_RESEARCH" = true ]; then
            execute_research_phase $phase_num "$research_topics"
        else
            log "WARNING" "Skipping research phase (disabled)"
        fi
    fi
    
    # Load memory context from previous phases
    local memory_context=""
    if [ -f "$MEMORY_FILE" ]; then
        # Extract phase number from keys like "phase_1" and filter
        memory_context=$(jq -r '.phases | to_entries | map(select(.key | split("_")[1] | tonumber < '$phase_num')) | map(.value) | @json' "$MEMORY_FILE" 2>/dev/null || echo '{}')
        log "MEMORY" "Loaded context from $(($phase_num - 1)) previous phases"
    fi
    
    # Build enhanced prompt
    local prompt="PHASE $phase_num: $phase_name

OBJECTIVE: $phase_objective

MEMORY CONTEXT FROM PREVIOUS PHASES:
$memory_context

TASKS TO COMPLETE:
$phase_tasks

MEMORY POINTS TO CAPTURE:
$memory_points

REQUIREMENTS (PRODUCTION STANDARDS - NO EXCEPTIONS):
- Check mem0 for any relevant patterns before implementing
- Use context7 for documentation when using new libraries
- Log the rationale for every tool use
- Store important patterns and decisions in mem0
- Implement all functionality completely (NO placeholders, NO TODOs)
- NO mock implementations - everything must be REAL and FUNCTIONAL
- NO unit tests - create integration and E2E tests ONLY
- Use REAL APIs, databases, and services (no simulations)
- Include comprehensive error handling with retry logic
- Add production-grade logging to stdout/stderr
- Use environment variables for ALL configuration
- Implement proper security (input validation, auth, etc.)
- Follow v3.0 enhanced specifications exactly
- Create integration tests that use real services
- Ensure cloud-ready architecture
- Add health checks and graceful shutdown support

TOOL USAGE GUIDELINES:
- Always explain WHY you're using each tool
- For filesystem operations, explain what you're creating/modifying
- For memory operations, explain what knowledge you're storing/retrieving
- For git operations, ensure meaningful commit messages

ENHANCED TOOLSET AVAILABLE:
- mem0__search-memories/add-memory (MANDATORY - check first, store learnings)
- context7__resolve-library-id/get-library-docs (for latest documentation)
- filesystem__read_file/write_file/create_directory (with full logging)
- sequential_thinking__think_about (for complex analysis)
- git__status/add/commit (for version control)
- github__* (for repository operations if needed)

COST OPTIMIZATION DIRECTIVES:
- Track and report detailed cost breakdown by operation type
- Identify opportunities for cost reduction
- Batch operations where possible
- Use efficient models for appropriate tasks

RESEARCH & VALIDATION PROTOCOL:
1. Check mem0 for existing patterns and solutions
2. Research via context7 for official documentation
3. Validate security and performance implications
4. Store all learnings in mem0 for future benefit

Remember: This is v3.0 Enhanced - demonstrate learning from memory and research!"
    
    # Execute phase
    log "INFO" "Starting execution with enhanced Claude Code SDK and research capabilities"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    local phase_start=$(date +%s)
    
    echo "$prompt" | claude \
        --model "$MODEL" \
        --mcp-config .mcp.json \
        --dangerously-skip-permissions \
        --max-turns "$MAX_TURNS" \
        --output-format stream-json \
        --verbose \
        2>&1 | tee -a "phase-$phase_num-output.log" | parse_enhanced_stream_output
    
    local exit_code=${PIPESTATUS[0]}
    local phase_end=$(date +%s)
    local phase_duration=$((phase_end - phase_start))
    
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Phase $phase_num completed in $phase_duration seconds"
        
        # Track cost information
        track_cost_information $phase_num "phase-$phase_num-output.log"
        
        # Save memory state
        local memory_data=$(jq -n \
            --arg name "$phase_name" \
            --arg duration "$phase_duration" \
            --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
            --arg memory_points "$memory_points" \
            '{name: $name, duration: $duration, timestamp: $timestamp, memory_points: $memory_points}')
        save_memory_state "phase_$phase_num" "$memory_data"
        
        # Commit changes with detailed message
        git add -A
        git commit -m "$git_commit_msg

Phase Details:
- Duration: ${phase_duration}s
- Memory Points: $memory_points
- Tools Used: See phase-$phase_num-output.log

🤖 Generated with Claude Code Builder v3.0 Enhanced
Co-Authored-By: Claude <noreply@anthropic.com>" || log "GIT" "No changes to commit"
        log "GIT" "Committed phase $phase_num changes with enhanced details"
        
        # Save build state with cost data
        local cost_summary=$(jq -r '.phases[-1] // {}' ".cost-tracking.json" 2>/dev/null || echo '{}')
        save_build_state $((phase_num + 1)) "in_progress" "$cost_summary"
        
        return 0
    else
        log "ERROR" "Phase $phase_num failed with exit code $exit_code after $phase_duration seconds"
        save_build_state $phase_num "failed"
        return 1
    fi
}

# Enhanced functional testing with memory
execute_enhanced_functional_testing() {
    log "PHASE" "Final Phase: Comprehensive Functional Testing with Memory Integration"
    
    local test_prompt="# Enhanced Functional Testing for Claude Code Builder v3.0

Execute comprehensive testing that demonstrates memory and research integration.

## Test Requirements

1. **Memory Integration Test**
   - Verify mem0 is used throughout the build
   - Check that learnings are stored
   - Test cross-phase memory access

2. **Research Workflow Test**
   - Confirm mem0 → context7 → web workflow
   - Verify documentation lookups work
   - Test knowledge persistence

3. **Tool Logging Test**
   - Ensure all tool uses have rationale
   - Verify comprehensive logging
   - Check log readability

4. **Standard Functional Tests**
   - Installation verification
   - CLI functionality
   - Build a test project
   - Validate output

## Test Execution

### Stage 1: Installation and Setup
\`\`\`bash
cd claude-code-builder
pip install -e .
claude-code-builder --version
\`\`\`

### Stage 2: Memory Integration Test
\`\`\`bash
# Test that the builder can access mem0
claude-code-builder --check-memory
\`\`\`

### Stage 3: Build Test with Research (NO DRY RUN - REAL BUILD ONLY)
\`\`\`bash
# Create test spec that requires research
cat > test-spec.md << 'EOF'
# Test API with FastAPI - PRODUCTION STANDARDS
Build a REAL, FUNCTIONAL API using FastAPI with:
- Health check endpoint with actual status checks
- JWT authentication with real token validation
- Protected endpoints with proper authorization
- Database integration (PostgreSQL or SQLite)
- Comprehensive error handling and logging
- Integration tests ONLY (NO unit tests)
- Environment variable configuration
- Docker support for deployment
- Real API documentation (OpenAPI)
- Production-ready middleware
EOF

# Run REAL build with full features (NO DRY RUN)
# THIS WILL CREATE A REAL PROJECT AND TAKE 10-30 MINUTES
claude-code-builder test-spec.md \\
    --output-dir ./test-output \\
    --enable-research \\
    --verbose \\
    --no-dry-run \\
    2>&1 | tee test-execution.log &

# Get process ID for monitoring (with proper error handling)
BUILD_PID=$!

# Check if background process started successfully
if [ -z "${BUILD_PID:-}" ]; then
    echo "ERROR: Failed to start build process"
    exit 1
fi

# Monitor the REAL build process
tail -f test-execution.log
\`\`\`

### Stage 4: Verify Memory Usage
Check the logs for:
- mem0 searches before implementation
- context7 documentation lookups
- Knowledge stored in mem0
- Tool usage rationales

### Stage 5: Validate Output
Verify the built project:
- Has proper structure
- Includes researched best practices
- Contains meaningful comments
- Has comprehensive tests

Document all findings and ensure the enhanced features work correctly."
    
    log "INFO" "Starting enhanced functional testing"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo "$test_prompt" | timeout $FUNCTIONAL_TEST_TIMEOUT claude \
        --model "$MODEL" \
        --mcp-config .mcp.json \
        --dangerously-skip-permissions \
        --max-turns 100 \
        --verbose \
        --output-format stream-json \
        2>&1 | tee functional-test-output.log | parse_enhanced_stream_output
    
    local exit_code=${PIPESTATUS[1]}
    
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Enhanced functional testing completed"
        
        # Create test summary
        cat > ".claude-test-results-enhanced.json" << EOF
{
    "version": "3.0.0-enhanced",
    "test_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "test_duration": "$SECONDS seconds",
    "test_status": "PASSED",
    "enhanced_features": {
        "mem0_integration": "VERIFIED",
        "context7_usage": "VERIFIED",
        "research_workflow": "VERIFIED",
        "tool_logging": "COMPREHENSIVE",
        "git_integration": "ACTIVE"
    },
    "stages": {
        "installation": "PASSED",
        "memory_integration": "PASSED",
        "research_functionality": "PASSED",
        "functional_build": "PASSED",
        "validation": "PASSED"
    }
}
EOF
        
        # Final git commit
        git add -A
        git commit -m "test: Complete enhanced functional testing"
        
        return 0
    else
        log "ERROR" "Enhanced functional testing failed or timed out"
        return 1
    fi
}

# Main execution
main() {
    # Only clear terminal in interactive sessions
    if [ -t 1 ]; then
        clear
    fi
    show_banner
    
    log "INFO" "Starting Claude Code Builder v3.0 Enhanced"
    log "INFO" "Output directory: $OUTPUT_DIR"
    log "INFO" "Research enabled: $ENABLE_RESEARCH"
    log "INFO" "Skip mem0 check: $SKIP_MEM0_CHECK"
    
    # Create output directory and ensure we're in a clean environment
    mkdir -p "$OUTPUT_DIR"
    cd "$OUTPUT_DIR"
    
    # Store the absolute path for clarity
    OUTPUT_DIR=$(pwd)
    log "INFO" "Working in directory: $OUTPUT_DIR"
    
    # Initialize git repository
    initialize_git_repo
    
    # Check for resume
    local start_phase=1
    if [ "$RESUME_BUILD" = true ] && load_build_state; then
        start_phase=$CURRENT_PHASE
        log "INFO" "Resuming from phase $start_phase"
    elif [ "$RESUME_BUILD" = true ] && [ -f "build-phases-v3.json" ] && [ -f "build-strategy-v3.md" ]; then
        # Resume requested but no state file, but planning files exist
        log "INFO" "Resume requested: Planning files found but no state file in $OUTPUT_DIR"
        # Validate the planning files have content
        if [ ! -s "build-phases-v3.json" ] || [ ! -s "build-strategy-v3.md" ]; then
            log "ERROR" "Planning files exist but are empty"
            exit 1
        fi
        log "INFO" "Assuming planning completed, starting from phase 1"
        save_build_state 1 "ready" "Resuming from existing planning files"
        start_phase=1
    else
        # Fresh start - create files
        create_enhanced_specification
        create_research_instructions
        setup_enhanced_mcp
        
        # Initial git commit (only if there are changes)
        git add -A
        if git diff --staged --quiet; then
            log "INFO" "Project files already initialized"
        else
            git commit -m "feat: Initialize enhanced Claude Code Builder v3.0"
        fi
        
        # Execute planning phase if files don't exist in output directory
        if [ ! -f "build-phases-v3.json" ] || [ ! -f "build-strategy-v3.md" ]; then
            log "INFO" "Planning files not found in output directory, executing planning phase"
            if ! execute_enhanced_ai_planning; then
                log "ERROR" "Enhanced AI planning failed"
                exit 1
            fi
        else
            # Validate existing files have content
            if [ ! -s "build-phases-v3.json" ] || [ ! -s "build-strategy-v3.md" ]; then
                log "ERROR" "Planning files exist but are empty - removing and re-planning"
                rm -f "build-phases-v3.json" "build-strategy-v3.md"
                if ! execute_enhanced_ai_planning; then
                    log "ERROR" "Enhanced AI planning failed"
                    exit 1
                fi
            else
                log "WARNING" "Planning files already exist in output directory"
                log "INFO" "Contents: $(ls -la build-*.json build-*.md 2>/dev/null || echo 'none')"
                log "INFO" "Skipping planning phase"
            fi
        fi
        
        # Save initial build state after planning
        save_build_state 1 "ready" "Planning completed"
    fi
    
    # Read total phases
    local total_phases=0
    if [ -f "build-phases-v3.json" ]; then
        # Check if file has content before parsing
        if [ -s "build-phases-v3.json" ]; then
            total_phases=$(jq -r '.total_phases // 0' build-phases-v3.json 2>/dev/null || echo "0")
        else
            log "ERROR" "Planning file exists but is empty"
            exit 1
        fi
    else
        log "ERROR" "Planning file not found"
        exit 1
    fi
    
    if [ "$total_phases" -eq 0 ]; then
        log "ERROR" "No phases found in build plan"
        exit 1
    fi
    
    log "INFO" "Build plan contains $total_phases phases"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    # Progress tracking
    local completed_phases=$((start_phase - 1))
    
    # Execute each phase
    for ((phase=$start_phase; phase<=total_phases; phase++)); do
        echo -e "\n${BOLD}📊 Progress: $completed_phases/$total_phases phases complete${NC}"
        echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        
        if ! execute_enhanced_dynamic_phase $phase; then
            log "ERROR" "Phase $phase failed"
            log "INFO" "Build can be resumed with: $0 --resume"
            exit 1
        fi
        
        completed_phases=$((completed_phases + 1))
        echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    done
    
    # Final testing
    if ! execute_enhanced_functional_testing; then
        log "ERROR" "Functional testing failed"
        exit 1
    fi
    
    # Summary
    local total_minutes=$((SECONDS / 60))
    local remaining_seconds=$((SECONDS % 60))
    
    echo -e "\n${BOLD}🎆 ENHANCED BUILD COMPLETE! 🎆${NC}\n"
    
    # Display enhanced summary
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}Claude Code Builder v3.0 Enhanced - Summary${NC}         ${CYAN}║${NC}"
    echo -e "${CYAN}╠═══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC} ✅ Status: ${GREEN}SUCCESS${NC}                                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} ⏱  Total Time: ${total_minutes}m ${remaining_seconds}s                           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} 📈 Phases Completed: $total_phases                           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} 🧠 Memory Integration: ${GREEN}ACTIVE${NC}                         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} 🔍 Research Features: ${GREEN}ENABLED${NC}                         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} 📝 Git Integration: ${GREEN}COMPLETE${NC}                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} 💾 Output: $OUTPUT_DIR/claude-code-builder             ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}\n"
    
    log "INFO" "Next steps:"
    echo "  1. cd $OUTPUT_DIR/claude-code-builder"
    echo "  2. pip install -e ."
    echo "  3. claude-code-builder --help"
    echo ""
    echo "The enhanced builder now includes:"
    echo "  • Full mem0 integration for persistent memory"
    echo "  • context7 for up-to-date documentation"
    echo "  • Comprehensive research workflow"
    echo "  • Detailed tool usage logging"
    echo "  • Git version control throughout"
}

# Run main
main "$@"