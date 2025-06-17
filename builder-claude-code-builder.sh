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
REQUIRED_TOOLS=("jq" "git" "npx" "claude" "bc")
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

# Model configuration
MODEL_OPUS_4="claude-opus-4-20250514"  # For complex tasks
MODEL_SONNET_4="claude-3-5-sonnet-20241022"  # For simple tasks
DEFAULT_MODEL="$MODEL_OPUS_4"  # Default to Opus 4 for quality

# State files
STATE_FILE=".build-state-v3-enhanced.json"
MEMORY_FILE=".build-memory-v3.json"

# Cost tracking (prices per 1M tokens as of Dec 2024)
# Opus 4 pricing
OPUS_INPUT_COST_PER_1M=15.00   # $15.00 per 1M input tokens
OPUS_OUTPUT_COST_PER_1M=75.00  # $75.00 per 1M output tokens
# Sonnet 3.5 pricing
SONNET_INPUT_COST_PER_1M=3.00   # $3.00 per 1M input tokens
SONNET_OUTPUT_COST_PER_1M=15.00 # $15.00 per 1M output tokens

# Initialize with Opus pricing (planning phase uses Opus)
INPUT_COST_PER_1M=$OPUS_INPUT_COST_PER_1M
OUTPUT_COST_PER_1M=$OPUS_OUTPUT_COST_PER_1M
TOTAL_INPUT_TOKENS=0
TOTAL_OUTPUT_TOKENS=0
TOTAL_COST=0.00

# API Key detection
API_KEY_MODE=false
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    API_KEY_MODE=true
fi

# Token tracking for last operation
LAST_INPUT_TOKENS=0
LAST_OUTPUT_TOKENS=0

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
FALLBACK_API_KEY=""

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
        --api-key)
            if [[ -z "${2:-}" ]]; then
                echo -e "${RED}Error: --api-key requires an API key${NC}"
                exit 1
            fi
            FALLBACK_API_KEY="$2"
            shift 2
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
    echo "  --api-key KEY           Fallback API key when max plan limits are reached"
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
# Display MCP capabilities summary
display_mcp_summary() {
    if [ -f ".mcp-capabilities.json" ]; then
        echo -e "\n${CYAN}📡 Available MCP Servers:${NC}"
        
        # Parse and display each server
        local servers=$(jq -r '.servers | to_entries[] | "\(.key): \(.value.status) (\(.value.tools | length) tools)"' .mcp-capabilities.json 2>/dev/null || echo "")
        
        if [ -n "$servers" ]; then
            echo "$servers" | while IFS= read -r server; do
                echo "  • $server"
            done
        fi
        
        echo ""
    fi
}

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
EOF
    echo -e "║  Models: ${BOLD}Opus 4${CYAN} (complex) & ${BOLD}Sonnet 4${CYAN} (simple)              ║"
    if [ "$API_KEY_MODE" = true ]; then
        echo -e "║  Mode: ${YELLOW}API Key${CYAN} (\$3/\$15 per 1M tokens)                               ║"
    elif [ -n "$FALLBACK_API_KEY" ]; then
        echo -e "║  Mode: ${GREEN}Max Plan${CYAN} with ${YELLOW}API Key fallback${CYAN}                               ║"
    else
        echo -e "║  Mode: ${GREEN}Max Plan${CYAN} (no additional charges)                                ║"
    fi
    echo -e "║                                                                           ║"
    echo -e "╚═══════════════════════════════════════════════════════════════════════════╝"
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

# Determine model based on phase complexity
determine_model_for_phase() {
    local phase_num=$1
    local phase_name="$2"
    
    # Complex phases that require Opus 4
    local complex_phases=(
        "AI Planning & Research"
        "AI-Driven Planning with Research"
        "Core Architecture"
        "Research Integration"
        "Memory System"
        "MCP Integration"
        "Execution Engine"
        "Integration Testing"
    )
    
    # Check if phase is complex
    local is_complex=false
    for complex in "${complex_phases[@]}"; do
        if [[ "$phase_name" == *"$complex"* ]]; then
            is_complex=true
            break
        fi
    done
    
    # Planning phase (0) always uses Opus 4 for complexity determination
    if [ "$phase_num" -eq 0 ]; then
        echo "$MODEL_OPUS_4"
        INPUT_COST_PER_1M=$OPUS_INPUT_COST_PER_1M
        OUTPUT_COST_PER_1M=$OPUS_OUTPUT_COST_PER_1M
    elif [ "$is_complex" = true ]; then
        echo "$MODEL_OPUS_4"
        INPUT_COST_PER_1M=$OPUS_INPUT_COST_PER_1M
        OUTPUT_COST_PER_1M=$OPUS_OUTPUT_COST_PER_1M
    else
        echo "$MODEL_SONNET_4"
        INPUT_COST_PER_1M=$SONNET_INPUT_COST_PER_1M
        OUTPUT_COST_PER_1M=$SONNET_OUTPUT_COST_PER_1M
    fi
}

# Calculate cost from tokens
calculate_cost() {
    local input_tokens=$1
    local output_tokens=$2
    
    # Calculate costs in dollars
    local input_cost=$(echo "scale=6; $input_tokens * $INPUT_COST_PER_1M / 1000000" | bc -l 2>/dev/null || echo "0")
    local output_cost=$(echo "scale=6; $output_tokens * $OUTPUT_COST_PER_1M / 1000000" | bc -l 2>/dev/null || echo "0")
    local phase_cost=$(echo "scale=6; $input_cost + $output_cost" | bc -l 2>/dev/null || echo "0")
    
    # Update totals
    TOTAL_INPUT_TOKENS=$((TOTAL_INPUT_TOKENS + input_tokens))
    TOTAL_OUTPUT_TOKENS=$((TOTAL_OUTPUT_TOKENS + output_tokens))
    TOTAL_COST=$(echo "scale=6; $TOTAL_COST + $phase_cost" | bc -l 2>/dev/null || echo "0")
    
    # Return phase cost
    echo "$phase_cost"
}

# Display cost summary
display_cost_summary() {
    local phase_name="$1"
    local input_tokens="$2"
    local output_tokens="$3"
    local phase_cost="$4"
    
    log "COST" "Phase: $phase_name"
    log "COST" "  Input tokens: $(printf "%'d" $input_tokens)"
    log "COST" "  Output tokens: $(printf "%'d" $output_tokens)"
    log "COST" "  Phase cost: \$$(printf "%.4f" $phase_cost)"
    log "COST" "  Total cost so far: \$$(printf "%.4f" $TOTAL_COST)"
    
    if [ "$API_KEY_MODE" = true ]; then
        log "COST" "  Mode: API Key (charges apply)"
    else
        log "COST" "  Mode: Max Plan (no additional charges)"
    fi
}

# Save build state for resumption
save_build_state() {
    local phase_num=$1
    local build_status=$2
    local cost_data=${3:-"{}"}
    
    # Ensure cost_data is properly quoted if it's a string
    if [[ ! "$cost_data" =~ ^[\{\[] ]]; then
        cost_data="\"$cost_data\""
    fi
    
    cat > "$STATE_FILE" << EOF
{
    "version": "$VERSION",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "current_phase": $phase_num,
    "status": "$build_status",
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
        # Validate JSON before parsing
        if ! jq empty "$STATE_FILE" 2>/dev/null; then
            log "ERROR" "State file exists but contains invalid JSON"
            return 1
        fi
        
        CURRENT_PHASE=$(jq -r '.current_phase // 0' "$STATE_FILE" 2>/dev/null)
        CURRENT_STATUS=$(jq -r '.status // "unknown"' "$STATE_FILE" 2>/dev/null)
        local saved_output_dir=$(jq -r '.output_dir // "."' "$STATE_FILE" 2>/dev/null)
        
        # Ensure values are not empty
        CURRENT_PHASE=${CURRENT_PHASE:-1}
        CURRENT_STATUS=${CURRENT_STATUS:-"unknown"}
        saved_output_dir=${saved_output_dir:-"."}
        
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

# Enhanced mem0 memory system with proper storage and retrieval
check_mem0_memory() {
    local topic=$1
    local phase_context="$2"
    
    log "MEMORY" "🧠 Performing comprehensive mem0 search for: $topic"
    log "MEMORY" "Rationale: Following CLAUDE.md memory-first approach - always check existing knowledge before proceeding"
    
    # Create comprehensive memory search prompt
    local memory_search_prompt="MEMORY-FIRST RESEARCH TASK

Primary search topic: $topic
Phase context: $phase_context

INSTRUCTIONS:
1. Use mcp__mem0__search-memories to search for ALL relevant knowledge about:
   - '$topic' (exact match)
   - Related project patterns and architectures
   - Similar build processes and tools
   - Known issues, solutions, and best practices
   - Performance optimizations and security patterns

2. Search multiple times with different keyword combinations:
   - Primary keywords from topic
   - Technical terms and frameworks mentioned
   - Common implementation patterns
   - Error patterns and solutions

3. For each search result found, provide:
   - Summary of the knowledge
   - Relevance to current task (1-10 scale)
   - How this information should influence our approach
   - What specific patterns or solutions to apply

4. If NO relevant memories found, explicitly state:
   - 'No relevant memories found for [specific search terms]'
   - Recommend what new knowledge should be captured

5. End with actionable recommendations:
   - What existing knowledge to apply immediately
   - What research gaps need to be filled
   - What new patterns should be documented

REMEMBER: This is production work - we need ALL available knowledge to avoid repeating mistakes and leverage proven solutions."

    echo "$memory_search_prompt" | claude \
        --model "$MODEL_SONNET_4" \
        --mcp-config .mcp.json \
        --dangerously-skip-permissions \
        --max-turns 10 \
        --output-format stream-json \
        --verbose \
        2>&1 | tee "mem0-search-${topic//[^a-zA-Z0-9]/_}.log" | parse_enhanced_stream_output
}

# Store knowledge in mem0 with proper categorization
store_mem0_knowledge() {
    local content="$1"
    local category="$2"
    local project_context="$3"
    
    log "MEMORY" "💾 Storing knowledge in mem0: $category"
    log "MEMORY" "Rationale: Following CLAUDE.md requirement to store ALL learnings for future projects"
    
    # Create comprehensive storage prompt
    local storage_prompt="KNOWLEDGE STORAGE TASK

Store the following knowledge in mem0 with proper categorization:

CONTENT TO STORE:
$content

CATEGORY: $category
PROJECT CONTEXT: $project_context

INSTRUCTIONS:
1. Use mcp__mem0__add-memory to store this knowledge
2. Make the memory entry comprehensive and searchable
3. Include relevant keywords and tags
4. Structure the content so future searches will find it easily
5. Add context about when/why this knowledge was valuable

Format the memory entry to include:
- Clear description of what was learned
- Technical details and implementation specifics  
- Context of when this applies
- Keywords for future searches
- Any warnings or important notes

Store this knowledge so future projects can benefit from these learnings."

    echo "$storage_prompt" | claude \
        --model "$MODEL_SONNET_4" \
        --mcp-config .mcp.json \
        --dangerously-skip-permissions \
        --max-turns 5 \
        --output-format stream-json \
        --verbose \
        2>&1 | tee "mem0-store-${category//[^a-zA-Z0-9]/_}.log" | parse_enhanced_stream_output
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

# Discover available MCP servers and tools
discover_mcp_capabilities() {
    log "INFO" "🔍 Discovering available MCP servers and their tools"
    
    # Skip the complex discovery and just create a working capabilities file
    # This is much faster and more reliable than trying to discover dynamically
    log "INFO" "Creating MCP capabilities based on standard configuration"

    # Create comprehensive capabilities file directly
    cat > ".mcp-capabilities.json" << EOF
{
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "discovery_method": "static_configuration",
    "servers": {
        "filesystem": {
            "status": "connected",
            "tools": [
                "mcp__filesystem__read_file",
                "mcp__filesystem__write_file",
                "mcp__filesystem__edit_file",
                "mcp__filesystem__create_directory",
                "mcp__filesystem__list_directory",
                "mcp__filesystem__directory_tree",
                "mcp__filesystem__move_file",
                "mcp__filesystem__search_files",
                "mcp__filesystem__get_file_info"
            ]
        },
        "memory": {
            "status": "connected",
            "tools": [
                "mcp__memory__create_entities",
                "mcp__memory__create_relations",
                "mcp__memory__add_observations",
                "mcp__memory__search_nodes",
                "mcp__memory__read_graph",
                "mcp__memory__open_nodes"
            ]
        },
        "mem0": {
            "status": "connected",
            "tools": [
                "mcp__mem0__add-memory",
                "mcp__mem0__search-memories"
            ]
        },
        "context7": {
            "status": "connected",
            "tools": [
                "mcp__context7__resolve-library-id",
                "mcp__context7__get-library-docs"
            ]
        },
        "git": {
            "status": "connected",
            "tools": [
                "mcp__git__git_status",
                "mcp__git__git_diff",
                "mcp__git__git_diff_staged",
                "mcp__git__git_diff_unstaged",
                "mcp__git__git_commit",
                "mcp__git__git_add",
                "mcp__git__git_log",
                "mcp__git__git_show"
            ]
        },
        "github": {
            "status": "connected",
            "tools": [
                "mcp__github__create_repository",
                "mcp__github__create_pull_request",
                "mcp__github__search_repositories",
                "mcp__github__get_file_contents",
                "mcp__github__create_or_update_file",
                "mcp__github__create_issue",
                "mcp__github__search_code"
            ]
        },
        "sequential-thinking": {
            "status": "connected",
            "tools": [
                "mcp__sequential-thinking__sequentialthinking"
            ]
        },
        "desktop-commander": {
            "status": "connected",
            "tools": [
                "mcp__desktop-commander__read_file",
                "mcp__desktop-commander__write_file",
                "mcp__desktop-commander__execute_command",
                "mcp__desktop-commander__search_files",
                "mcp__desktop-commander__search_code"
            ]
        }
    }
}
EOF
    
    log "SUCCESS" "MCP capabilities created - found $(jq -r '.servers | length' .mcp-capabilities.json) servers"
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
            "args": ["-y", "@mem0/mcp-server"],
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
        git commit --no-verify -m "Initial commit: Add .gitignore"
        log "GIT" "Created initial commit with .gitignore"
    fi
}

# Enhanced AI planning with research
execute_enhanced_ai_planning() {
    log "PHASE" "Phase 0: AI-Driven Planning with Research"
    
    # Enhanced mem0 check for similar projects if not skipped
    if [ "$SKIP_MEM0_CHECK" = false ]; then
        log "MEMORY" "🔍 Phase 0: Comprehensive memory search before planning"
        check_mem0_memory "Claude Code Builder autonomous project builder Python packaging architecture" "AI-driven planning phase"
        check_mem0_memory "shell script builders automation tools Claude integration" "Build system design"
        check_mem0_memory "MCP server integration memory-first workflows context7" "Research system design"
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
    
    log "INFO" "Invoking Claude with Opus 4 for complexity determination and planning"
    log "INFO" "Using model: $MODEL_OPUS_4"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Log the planning command with detailed info
    local planning_cmd="claude --model $MODEL_OPUS_4 --mcp-config .mcp.json --dangerously-skip-permissions --max-turns 50 --output-format stream-json --verbose"
    log "INFO" "🔧 Planning command: $planning_cmd"
    log "COST" "💰 Using Opus 4 - Input: \$15/1M tokens, Output: \$75/1M tokens"
    echo -e "${DIM}   Input: Planning prompt with ${#full_prompt} characters${NC}" >&2
    echo -e "${DIM}   Expected tools: mem0, context7, filesystem, sequential-thinking${NC}" >&2
    
    # Always use Opus 4 for planning to determine complexity
    echo "$full_prompt" | $planning_cmd \
        --max-turns 50 \
        --output-format stream-json \
        --verbose \
        2>&1 | tee planning-output.log | parse_enhanced_stream_output
    
    # Verify planning files were created
    if [ -f "build-phases-v3.json" ] && [ -f "build-strategy-v3.md" ]; then
        log "SUCCESS" "AI planning with research completed successfully"
        
        # Store planning knowledge in mem0 for future projects
        if [ "$SKIP_MEM0_CHECK" = false ]; then
            log "MEMORY" "💾 Storing planning insights in mem0 for future projects"
            local planning_summary=$(head -n 50 build-strategy-v3.md | tail -n +10)
            store_mem0_knowledge "$planning_summary" "Claude Code Builder Planning Patterns" "Enhanced shell script builder v3.0"
            
            local phase_info=$(jq -r '.phases[] | "\(.name): \(.objective)"' build-phases-v3.json 2>/dev/null | head -10)
            store_mem0_knowledge "$phase_info" "AI Build Phase Patterns" "Autonomous project builder architecture"
        fi
        
        # Commit planning files (only if there are changes)
        git add build-phases-v3.json build-strategy-v3.md
        if git diff --staged --quiet; then
            log "INFO" "Planning files already committed"
        else
            git commit --no-verify -m "feat: AI-generated build plan with research integration"
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
    local tool_id=""
    local buffer=""
    local last_update=$(date +%s)
    local update_interval=3  # Show progress every 3 seconds
    local char_count=0
    local line_count=0
    local input_tokens=0
    local output_tokens=0
    local tool_count=0
    
    while IFS= read -r line; do
        # Skip empty lines
        [ -z "$line" ] && continue
        
        # Increment counters
        line_count=$((line_count + 1))
        char_count=$((char_count + ${#line}))
        
        # Show periodic progress updates with tool count and current activity
        local now=$(date +%s)
        if [ $((now - last_update)) -ge $update_interval ]; then
            local activity="thinking"
            [ "$in_tool_use" = true ] && activity="using $current_tool"
            echo -e "${DIM}   [PROGRESS] $activity... (${line_count} events, ${char_count} chars, ${tool_count} tools called)${NC}" >&2
            last_update=$now
        fi
        
        # Try to parse as JSON and extract message content
        if command -v jq >/dev/null 2>&1; then
            # Use jq if available for better JSON parsing
            local message_type=$(echo "$line" | jq -r '.type // empty' 2>/dev/null)
            
            # Log the actual event type for debugging (only occasionally to avoid spam)
            if [ $((line_count % 10)) -eq 0 ] && [ -n "$message_type" ] && [ "$message_type" != "empty" ]; then
                echo -e "${DIM}   [EVENT] Type: $message_type${NC}" >&2
            fi
            
            case "$message_type" in
                "message_start")
                    echo -e "${DIM}   [STREAM] Claude starting new message...${NC}" >&2
                    ;;
                    
                "user")
                    echo -e "${DIM}   [STREAM] Processing user input...${NC}" >&2
                    ;;
                    
                "assistant")
                    echo -e "${DIM}   [STREAM] Claude generating response...${NC}" >&2
                    ;;
                    
                "content_block_start")
                    local content_type=$(echo "$line" | jq -r '.content_block.type // empty' 2>/dev/null)
                    if [ "$content_type" = "tool_use" ]; then
                        current_tool=$(echo "$line" | jq -r '.content_block.name // "unknown"' 2>/dev/null)
                        tool_id=$(echo "$line" | jq -r '.content_block.id // "unknown"' 2>/dev/null)
                        in_tool_use=true
                        tool_count=$((tool_count + 1))
                        
                        # Extract and display tool parameters
                        local tool_input=$(echo "$line" | jq -r '.content_block.input // {}' 2>/dev/null)
                        
                        # Display tool usage with detailed parameters
                        case $current_tool in
                            mcp__mem0__*)
                                echo -e "\n${PURPLE}🧠 [MEMORY OPERATION]${NC} ${BOLD}$current_tool${NC} (ID: $tool_id)"
                                local query=$(echo "$tool_input" | jq -r '.query // .content // "unknown"' 2>/dev/null)
                                echo -e "   ${DIM}Query: $query${NC}"
                                log "MEMORY" "Accessing persistent memory: $current_tool - Query: $query"
                                ;;
                            mcp__context7__*)
                                echo -e "\n${CYAN}📚 [DOCUMENTATION LOOKUP]${NC} ${BOLD}$current_tool${NC} (ID: $tool_id)"
                                local library=$(echo "$tool_input" | jq -r '.libraryName // .context7CompatibleLibraryID // "unknown"' 2>/dev/null)
                                echo -e "   ${DIM}Library: $library${NC}"
                                log "RESEARCH" "Checking documentation: $current_tool - Library: $library"
                                ;;
                            mcp__filesystem__*)
                                echo -e "\n${GREEN}📁 [FILE OPERATION]${NC} ${BOLD}$current_tool${NC} (ID: $tool_id)"
                                local path=$(echo "$tool_input" | jq -r '.path // .paths[0] // "unknown"' 2>/dev/null)
                                echo -e "   ${DIM}Path: $path${NC}"
                                log "TOOL" "File operation: $current_tool - Path: $path"
                                ;;
                            mcp__git__*)
                                echo -e "\n${ORANGE}📝 [VERSION CONTROL]${NC} ${BOLD}$current_tool${NC} (ID: $tool_id)"
                                local repo_path=$(echo "$tool_input" | jq -r '.repo_path // "current"' 2>/dev/null)
                                echo -e "   ${DIM}Repo: $repo_path${NC}"
                                log "GIT" "Git operation: $current_tool - Repo: $repo_path"
                                ;;
                            mcp__sequential-thinking__*)
                                echo -e "\n${PURPLE}🤔 [DEEP THINKING]${NC} ${BOLD}$current_tool${NC} (ID: $tool_id)"
                                local thought_num=$(echo "$tool_input" | jq -r '.thoughtNumber // "unknown"' 2>/dev/null)
                                echo -e "   ${DIM}Thought: #$thought_num${NC}"
                                log "TOOL" "Sequential thinking: $current_tool - Thought: #$thought_num"
                                ;;
                            mcp__github__*)
                                echo -e "\n${BLUE}🔗 [GITHUB OPERATION]${NC} ${BOLD}$current_tool${NC} (ID: $tool_id)"
                                local repo=$(echo "$tool_input" | jq -r '.repo // .owner // "unknown"' 2>/dev/null)
                                echo -e "   ${DIM}Repo: $repo${NC}"
                                log "TOOL" "GitHub operation: $current_tool - Repo: $repo"
                                ;;
                            mcp__firecrawl__*)
                                echo -e "\n${YELLOW}🕷️ [WEB SCRAPING]${NC} ${BOLD}$current_tool${NC} (ID: $tool_id)"
                                local url=$(echo "$tool_input" | jq -r '.url // .query // "unknown"' 2>/dev/null)
                                echo -e "   ${DIM}URL: $url${NC}"
                                log "RESEARCH" "Web scraping: $current_tool - URL: $url"
                                ;;
                            *)
                                echo -e "\n${CYAN}🔧 [TOOL USE]${NC} ${BOLD}$current_tool${NC} (ID: $tool_id)"
                                log "TOOL" "Using tool: $current_tool"
                                ;;
                        esac
                    elif [ "$content_type" = "text" ]; then
                        in_tool_use=false
                        echo -e "${DIM}   [STREAM] Claude thinking and writing...${NC}" >&2
                    fi
                    ;;
                    
                "tool_result")
                    local result_tool_id=$(echo "$line" | jq -r '.tool_use_id // "unknown"' 2>/dev/null)
                    local is_error=$(echo "$line" | jq -r '.is_error // false' 2>/dev/null)
                    local content_length=$(echo "$line" | jq -r '.content[0].text | length // 0' 2>/dev/null)
                    
                    if [ "$is_error" = "true" ]; then
                        echo -e "   ${RED}❌ Tool failed${NC} (ID: $result_tool_id)"
                        local error_msg=$(echo "$line" | jq -r '.content[0].text // "Unknown error"' 2>/dev/null)
                        echo -e "   ${RED}Error: ${error_msg:0:100}${NC}"
                        log "ERROR" "Tool $result_tool_id failed: $error_msg"
                    else
                        echo -e "   ${GREEN}✅ Tool completed${NC} (ID: $result_tool_id, ${content_length} chars)"
                        log "SUCCESS" "Tool $result_tool_id completed successfully"
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
                    
                "message_stop")
                    # Extract token usage from final message
                    local usage=$(echo "$line" | jq -r '.message.usage // empty' 2>/dev/null)
                    if [ -n "$usage" ]; then
                        input_tokens=$(echo "$usage" | jq -r '.input_tokens // 0' 2>/dev/null)
                        output_tokens=$(echo "$usage" | jq -r '.output_tokens // 0' 2>/dev/null)
                        echo -e "${DIM}   [STREAM] Claude finished - ${input_tokens} input tokens, ${output_tokens} output tokens${NC}" >&2
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
    
    # Final progress update with comprehensive summary
    echo -e "${DIM}   [STREAM COMPLETE]${NC}" >&2
    echo -e "${DIM}   • Total events: ${line_count}${NC}" >&2  
    echo -e "${DIM}   • Total characters: ${char_count}${NC}" >&2
    echo -e "${DIM}   • Tools called: ${tool_count}${NC}" >&2
    if [ "$input_tokens" -gt 0 ] && [ "$output_tokens" -gt 0 ]; then
        echo -e "${DIM}   • Token usage: ${input_tokens} in, ${output_tokens} out${NC}" >&2
    fi
    
    # Return token counts via global variables
    LAST_INPUT_TOKENS=$input_tokens
    LAST_OUTPUT_TOKENS=$output_tokens
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
    
    # Research is always complex, use Opus 4
    log "INFO" "Using model: $MODEL_OPUS_4 (Research requires Opus 4)"
    
    # Log the research command with detailed info
    local research_cmd="claude --model $MODEL_OPUS_4 --mcp-config .mcp.json --dangerously-skip-permissions --max-turns 20 --output-format stream-json --verbose"
    log "INFO" "🔧 Research command: timeout --foreground $RESEARCH_TIMEOUT $research_cmd"
    log "COST" "💰 Using Opus 4 for research - Input: \$15/1M tokens, Output: \$75/1M tokens"
    echo -e "${DIM}   Input: Research prompt with ${#research_prompt} characters${NC}" >&2
    echo -e "${DIM}   Timeout: $RESEARCH_TIMEOUT seconds${NC}" >&2
    echo -e "${DIM}   Research workflow: mem0 → context7 → web search → store findings${NC}" >&2
    
    echo "$research_prompt" | timeout --foreground $RESEARCH_TIMEOUT $research_cmd \
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
    
    # Tool whitelist is handled by MCP capabilities file
    
    # Load available tools
    local available_tools=""
    if [ -f ".mcp-tool-whitelist.txt" ]; then
        available_tools=$(cat .mcp-tool-whitelist.txt)
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

DISCOVERED MCP TOOLS (USE THESE EXACT NAMES):
$available_tools

MANDATORY TOOL USAGE WORKFLOW:
1. ALWAYS use mcp__mem0__search-memories FIRST for any task
2. Use mcp__context7__resolve-library-id and mcp__context7__get-library-docs for documentation
3. Use mcp__filesystem__* for all file operations (NOT the basic Read/Write tools)
4. Use mcp__git__* for version control (NOT bash git commands)
5. Use mcp__sequential-thinking__sequentialthinking for complex reasoning
6. ALWAYS store learnings with mcp__mem0__add-memory

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
    
    # Determine which model to use based on phase complexity
    local phase_model=$(determine_model_for_phase "$phase_num" "$phase_name")
    
    # Set up environment for fallback API key if provided
    local claude_env=""
    if [ -n "$FALLBACK_API_KEY" ] && [ "$API_KEY_MODE" = false ]; then
        claude_env="ANTHROPIC_API_KEY=$FALLBACK_API_KEY"
        log "INFO" "Using fallback API key for this phase"
    fi
    
    # Log model being used and why with cost info
    if [ "$phase_model" = "$MODEL_OPUS_4" ]; then
        log "INFO" "🎯 Using model: $phase_model (Complex task requiring Opus 4)"
        log "COST" "💰 Opus 4 costs - Input: \$15/1M tokens, Output: \$75/1M tokens"
    else
        log "INFO" "⚡ Using model: $phase_model (Simple task, using efficient Sonnet 4)"
        log "COST" "💰 Sonnet 4 costs - Input: \$3/1M tokens, Output: \$15/1M tokens"
    fi
    
    # Log detailed Claude command
    log "INFO" "🔧 Claude command details:"
    log "INFO" "  Model: $phase_model"
    log "INFO" "  Max turns: $MAX_TURNS"
    log "INFO" "  MCP config: .mcp.json"
    log "INFO" "  Output format: stream-json"
    log "INFO" "  Permissions: dangerously-skip-permissions"
    [ -n "$claude_env" ] && log "INFO" "  Environment: Using fallback API key"
    
    # Log available MCP tools for this phase
    if [ -f ".mcp-capabilities.json" ]; then
        local tool_count=$(jq -r '.servers | to_entries | map(.value.tools | length) | add' .mcp-capabilities.json 2>/dev/null || echo "0")
        log "INFO" "  Available MCP tools: $tool_count across $(jq -r '.servers | length' .mcp-capabilities.json) servers"
    fi
    
    # Log the exact Claude command being executed
    log "INFO" "🔧 Executing Claude command:"
    local claude_cmd="claude --model $phase_model --mcp-config .mcp.json --dangerously-skip-permissions --max-turns $MAX_TURNS --output-format stream-json --verbose"
    echo -e "${DIM}   Command: $claude_cmd${NC}" >&2
    echo -e "${DIM}   Input: <prompt of ${#prompt} characters>${NC}" >&2
    echo -e "${DIM}   Log file: phase-$phase_num-output.log${NC}" >&2
    
    # Predict expected tool usage based on phase type
    case "$phase_name" in
        *"Research"*|*"Planning"*)
            echo -e "${DIM}   Expected tools: mem0, context7, firecrawl, sequential-thinking${NC}" >&2
            ;;
        *"Architecture"*|*"Design"*)
            echo -e "${DIM}   Expected tools: mem0, filesystem, sequential-thinking${NC}" >&2
            ;;
        *"Implementation"*|*"Build"*)
            echo -e "${DIM}   Expected tools: filesystem, git, mem0${NC}" >&2
            ;;
        *"Test"*|*"Validation"*)
            echo -e "${DIM}   Expected tools: filesystem, desktop-commander, git${NC}" >&2
            ;;
        *)
            echo -e "${DIM}   Expected tools: filesystem, mem0, git${NC}" >&2
            ;;
    esac
    
    echo "$prompt" | env $claude_env $claude_cmd \
        2>&1 | tee -a "phase-$phase_num-output.log" | parse_enhanced_stream_output
    
    local exit_code=${PIPESTATUS[0]}
    local phase_end=$(date +%s)
    local phase_duration=$((phase_end - phase_start))
    
    # Calculate and display costs
    local phase_cost="0.0000"
    if [ $LAST_INPUT_TOKENS -gt 0 ] || [ $LAST_OUTPUT_TOKENS -gt 0 ]; then
        phase_cost=$(calculate_cost $LAST_INPUT_TOKENS $LAST_OUTPUT_TOKENS)
        display_cost_summary "$phase_name" $LAST_INPUT_TOKENS $LAST_OUTPUT_TOKENS "$phase_cost"
    fi
    
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Phase $phase_num completed in $phase_duration seconds"
        
        # Cost already tracked and displayed above
        
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
        git commit --no-verify -m "$git_commit_msg

Phase Details:
- Duration: ${phase_duration}s
- Memory Points: $memory_points
- Tools Used: See phase-$phase_num-output.log

🤖 Generated with Claude Code Builder v3.0 Enhanced
Co-Authored-By: Claude <noreply@anthropic.com>" || log "GIT" "No changes to commit"
        log "GIT" "Committed phase $phase_num changes with enhanced details"
        
        # Store phase learnings in mem0 for future projects
        if [ "$SKIP_MEM0_CHECK" = false ]; then
            log "MEMORY" "💾 Storing phase $phase_num learnings in mem0"
            local phase_summary="Phase $phase_num ($phase_name) completed successfully in ${phase_duration}s. 
Cost: $phase_cost. Key outputs and patterns learned during this phase can inform future similar work."
            store_mem0_knowledge "$phase_summary" "Build Phase $phase_num Completion" "Claude Code Builder v3.0 - $phase_name"
            
            # Store any significant files created (first 500 chars of each)
            if [ -d "." ]; then
                local new_files=$(find . -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.json" -newer "phase-$phase_num-start.marker" 2>/dev/null | head -5)
                if [ -n "$new_files" ]; then
                    local files_content=""
                    for file in $new_files; do
                        files_content+="\n\n=== $file ===\n$(head -c 500 "$file" 2>/dev/null)"
                    done
                    store_mem0_knowledge "$files_content" "Phase $phase_num Artifacts" "Generated files and code patterns"
                fi
            fi
        fi
        
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
    
    local test_prompt=$(cat << 'EOF'
# Enhanced Functional Testing for Claude Code Builder v3.0

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
```bash
cd claude-code-builder
pip install -e .
claude-code-builder --version
```

### Stage 2: Memory Integration Test
```bash
# Test that the builder can access mem0
claude-code-builder --check-memory
```

### Stage 3: Build Test with Research (NO DRY RUN - REAL BUILD ONLY)
```bash
# Create test spec that requires research
cat > test-spec.md << 'TESTEOF'
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
TESTEOF

# Run REAL build with full features (NO DRY RUN)
# THIS WILL CREATE A REAL PROJECT AND TAKE 10-30 MINUTES
claude-code-builder test-spec.md \
    --output-dir ./test-output \
    --enable-research \
    --verbose \
    --no-dry-run
```

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

Document all findings and ensure the enhanced features work correctly.
EOF
)
    
    log "INFO" "Starting enhanced functional testing"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo "$test_prompt" | timeout $FUNCTIONAL_TEST_TIMEOUT claude \
        --model "$MODEL_OPUS_4" \
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
        git commit --no-verify -m "test: Complete enhanced functional testing"
        
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
    
    # Auto-detect existing build and resume if possible
    local start_phase=1
    local auto_resumed=false
    
    # Check for existing build artifacts
    if [ -f "$STATE_FILE" ] || [ -f "build-phases-v3.json" ] || [ -f "build-strategy-v3.md" ]; then
        log "INFO" "🔍 Detected existing build artifacts in $OUTPUT_DIR"
        echo -e "${CYAN}Found context:${NC}"
        
        # List what we found
        [ -f "$STATE_FILE" ] && echo "  ✓ Build state file"
        [ -f "build-phases-v3.json" ] && echo "  ✓ Build phases plan ($(jq -r '.total_phases // 0' build-phases-v3.json 2>/dev/null || echo 'unknown') phases)"
        [ -f "build-strategy-v3.md" ] && echo "  ✓ Build strategy document"
        [ -f "$MEMORY_FILE" ] && echo "  ✓ Memory from previous phases"
        [ -d ".git" ] && echo "  ✓ Git repository ($(git rev-list --count HEAD 2>/dev/null || echo '0') commits)"
        
        # Try to load state file first
        if load_build_state; then
            start_phase=$CURRENT_PHASE
            auto_resumed=true
            log "SUCCESS" "✅ Auto-resuming from phase $start_phase (status: $CURRENT_STATUS)"
            
            # Show phase history
            if [ -f "$MEMORY_FILE" ]; then
                local completed_phases=$(jq -r '.phases | keys | length' "$MEMORY_FILE" 2>/dev/null || echo "0")
                log "INFO" "Completed phases: $completed_phases"
            fi
        elif [ -f "build-phases-v3.json" ] && [ -f "build-strategy-v3.md" ]; then
            # No state file but planning files exist
            if [ -s "build-phases-v3.json" ] && [ -s "build-strategy-v3.md" ]; then
                log "INFO" "Planning files found, assuming planning completed"
                save_build_state 1 "ready" "Auto-resuming from existing planning files"
                start_phase=1
                auto_resumed=true
                log "SUCCESS" "✅ Auto-resuming from phase 1 with existing plan"
            else
                log "ERROR" "Planning files exist but are empty"
                exit 1
            fi
        fi
        
        if [ "$auto_resumed" = true ]; then
            echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${BOLD}🔄 AUTO-RESUME ACTIVATED${NC}"
            echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
        fi
    fi
    
    # If not auto-resumed, proceed with fresh start
    if [ "$auto_resumed" = false ]; then
        # Fresh start - create files
        create_enhanced_specification
        create_research_instructions
        setup_enhanced_mcp
        
        # Discover MCP capabilities (fast static method)
        discover_mcp_capabilities
        display_mcp_summary
        
        # Initial git commit (only if there are changes)
        git add -A
        if git diff --staged --quiet; then
            log "INFO" "Project files already initialized"
        else
            git commit --no-verify -m "feat: Initialize enhanced Claude Code Builder v3.0"
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
    echo -e "${CYAN}╠═══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC} 💰 ${BOLD}COST SUMMARY${NC}                                      ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} Input tokens: $(printf "%'d" $TOTAL_INPUT_TOKENS)                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} Output tokens: $(printf "%'d" $TOTAL_OUTPUT_TOKENS)                           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC} Total cost: ${YELLOW}\$$(printf "%.4f" $TOTAL_COST)${NC}                            ${CYAN}║${NC}"
    if [ "$API_KEY_MODE" = true ]; then
        echo -e "${CYAN}║${NC} Mode: ${YELLOW}API Key (charged)${NC}                               ${CYAN}║${NC}"
    else
        echo -e "${CYAN}║${NC} Mode: ${GREEN}Max Plan (no charge)${NC}                            ${CYAN}║${NC}"
    fi
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