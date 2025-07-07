# Claude Code Builder v3.0 Enhanced - Build Instructions

## CRITICAL IMPLEMENTATION REQUIREMENTS

This document defines the implementation standards for the Claude Code Builder v3.0 Enhanced shell script that builds autonomous project builders with full memory integration, research capabilities, and production-first standards.

### 1. **MEMORY-FIRST ARCHITECTURE (MANDATORY)**
- **ALWAYS check mem0 BEFORE any code/task** - No exceptions
- **SEARCH FIRST, CODE SECOND** - Memory drives all decisions
- **Store EVERYTHING learned** for future projects
- **Cross-project knowledge benefits** - Project A learnings help Project B

### 2. **PRODUCTION STANDARDS ENFORCEMENT**
- **NO mock implementations** - Everything must be REAL and FUNCTIONAL
- **NO unit tests** - Integration and end-to-end tests ONLY
- **NO dry runs** - Execute actual builds that create real projects
- **NO placeholders** - Complete implementations only
- **Real APIs, databases, services** - No simulations ever

### 3. **RESEARCH WORKFLOW (MANDATORY)**
```bash
MANDATORY RESEARCH SEQUENCE:
1. CHECK MEM0 FIRST → Search for existing knowledge
2. USE CONTEXT7 SECOND → Get latest documentation  
3. WEB SEARCH THIRD → Only if mem0 and context7 insufficient
4. STORE IN MEM0 ALWAYS → Save all findings for future use
```

### 4. **ENHANCED SHELL SCRIPT ARCHITECTURE**

The builder creates a sophisticated shell script with these components:

```bash
builder-claude-code-builder.sh
├── Memory Integration Functions
│   ├── check_mem0_memory()           # Search existing knowledge
│   ├── save_memory_state()           # Store phase learnings
│   └── load_build_state()            # Resume capability
├── Research System Functions  
│   ├── execute_research_phase()      # Comprehensive research
│   ├── create_research_instructions() # Research guidelines
│   └── Research workflow enforcement
├── Enhanced Logging Functions
│   ├── parse_enhanced_stream_output() # Tool usage tracking
│   ├── display_tool_parameters()     # Parameter explanation
│   └── Tool rationale logging
├── Git Integration Functions
│   ├── initialize_git_repo()         # Version control setup
│   ├── Enhanced commit messages      # Detailed commits
│   └── Per-phase commit automation
├── MCP Configuration
│   ├── setup_enhanced_mcp()          # Server configuration
│   ├── mem0 server integration       # Persistent memory
│   ├── context7 server integration   # Documentation
│   └── Enhanced .mcp.json generation
└── Production Standards Enforcement
    ├── Dependency validation         # Required tools check
    ├── Production requirements       # NO mocks enforcement
    ├── Cost tracking integration     # API usage monitoring
    └── Error handling standards
```

### 5. **MCP SERVER INTEGRATION**

#### Required MCP Servers
```json
{
    "mcpServers": {
        "mem0": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-mem0"],
            "env": {"MEM0_API_KEY": "${MEM0_API_KEY:-}"},
            "description": "Persistent memory across all projects"
        },
        "context7": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-context7"],
            "description": "Latest documentation for libraries"
        },
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
            "description": "File system operations with full logging"
        },
        "git": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-git"],
            "description": "Version control throughout build"
        }
    }
}
```

### 6. **TOOL USAGE LOGGING STANDARDS**

#### Every Tool Use Must Include:
```bash
# Before tool execution
log("TOOL", "Using ${TOOL_NAME}")
log("TOOL", "Rationale: ${WHY_USING_THIS_TOOL}")
log("TOOL", "Expected outcome: ${WHAT_WE_EXPECT}")

# During execution
display_tool_parameters "${TOOL_NAME}" "${PARAMETERS}"

# After execution
log("TOOL", "Result: ${WHAT_WAS_ACHIEVED}")
log("TOOL", "Learning: ${WHAT_WAS_LEARNED}")

# Memory storage
log("MEMORY", "Storing: ${PATTERN_FOR_FUTURE_USE}")
```

#### Tool Categories and Logging:
- **Memory Operations** (mem0__*): Purple logging with 🧠 icon
- **Documentation Lookup** (context7__*): Cyan logging with 📚 icon  
- **File Operations** (filesystem__*): Green logging with 📁 icon
- **Version Control** (git__*): Orange logging with 📝 icon
- **General Tools**: Cyan logging with 🔧 icon

### 7. **PHASE EXECUTION STANDARDS**

#### Every Phase Must:
1. **Load Context**: Previous phase memory and learnings
2. **Check mem0**: Search for relevant patterns and solutions
3. **Research**: Use context7 for documentation when needed
4. **Execute with Logging**: Implement with full rationale
5. **Store Learnings**: Save discoveries and patterns to mem0
6. **Git Commit**: Version control with detailed messages
7. **Track Costs**: Record and analyze API usage

#### Phase Prompt Template:
```bash
PHASE ${PHASE_NUM}: ${PHASE_NAME}

OBJECTIVE: ${PHASE_OBJECTIVE}

MEMORY CONTEXT FROM PREVIOUS PHASES:
${MEMORY_CONTEXT}

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
- Ensure cloud-ready architecture
- Create integration tests that use real services

ENHANCED TOOLSET AVAILABLE:
- mem0__search-memories/add-memory (MANDATORY - check first, store learnings)
- context7__resolve-library-id/get-library-docs (for latest documentation)
- filesystem__read_file/write_file/create_directory (with full logging)
- sequential_thinking__think_about (for complex analysis)
- git__status/add/commit (for version control)
```

### 8. **GIT INTEGRATION STANDARDS**

#### Repository Initialization:
```bash
initialize_git_repo() {
    log "GIT" "📝 Initializing git repository for version control"
    
    if [ ! -d ".git" ]; then
        git init
        log "GIT" "📝 Created new git repository"
    fi
    
    # Create comprehensive .gitignore
    # Add build artifacts, logs, state files
    # Commit initial setup
}
```

#### Enhanced Commit Messages:
```bash
git commit -m "${GIT_COMMIT_MSG}

Phase Details:
- Duration: ${PHASE_DURATION}s
- Memory Points: ${MEMORY_POINTS}
- Tools Used: See phase-${PHASE_NUM}-output.log

🤖 Generated with Claude Code Builder v3.0 Enhanced
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 9. **COST TRACKING IMPLEMENTATION**

#### Cost Information Extraction:
```bash
track_cost_information() {
    local phase_num=$1
    local log_file=$2
    
    # Extract cost data from Claude Code logs
    local session_cost=$(grep -o '"session_cost":[0-9.]*' "$log_file" | tail -1)
    local total_cost=$(grep -o '"total_cost":[0-9.]*' "$log_file" | tail -1)
    
    # Store in .cost-tracking.json
    # Log cost breakdown
    # Identify optimization opportunities
}
```

### 10. **ERROR HANDLING STANDARDS**

#### Production-Grade Error Handling:
```bash
# Dependency checking at script start
REQUIRED_TOOLS=("jq" "git" "npx" "claude")
for tool in "${REQUIRED_TOOLS[@]}"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo -e "\033[0;31mError:\033[0m Required tool '\033[1m$tool\033[0m' not found."
        exit 1
    fi
done

# Interactive session detection
if [ -t 1 ]; then
    clear  # Only clear in interactive sessions
fi

# Resume logic with directory handling
if [ "$RESUME_BUILD" = true ] && [ "$OUTPUT_DIR" != "." ]; then
    log "WARNING" "Using saved output directory during resume"
fi
```

### 11. **FUNCTIONAL TESTING REQUIREMENTS**

#### Testing Must Be Real:
```bash
# NO DRY RUNS - Create actual test specification
cat > test-spec.md << 'EOF'
# Test API with FastAPI - PRODUCTION STANDARDS
Build a REAL, FUNCTIONAL API using FastAPI with:
- Health check endpoint with actual status checks
- JWT authentication with real token validation
- Protected endpoints with proper authorization
- Database integration (PostgreSQL or SQLite)
- Integration tests ONLY (NO unit tests)
- Environment variable configuration
- Production-ready middleware
EOF

# Execute REAL build (NO dry run)
claude-code-builder test-spec.md \
    --output-dir ./test-output \
    --enable-research \
    --verbose \
    --no-dry-run \
    2>&1 | tee test-execution.log
```

### 12. **SECURITY IMPLEMENTATION**

#### Security Standards:
- **ZERO hardcoded credentials** - Environment variables only
- **Input validation** for all user inputs
- **Output sanitization** for all displays
- **No bypassing authentication** ever
- **SSL/TLS enforcement** for all connections
- **Security event logging** for audit trails

#### Environment Variable Configuration:
```bash
# MCP server environment variables
"env": {
    "MEM0_API_KEY": "${MEM0_API_KEY:-}",
    "GITHUB_TOKEN": "${GITHUB_TOKEN:-}"
}
```

### 13. **MEMORY PERSISTENCE STANDARDS**

#### Build State Management:
```bash
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
    "memory_file": "$MEMORY_FILE",
    "cost_data": $cost_data
}
EOF
}
```

#### Memory State Preservation:
```bash
save_memory_state() {
    local phase_id=$1
    local memory_data=$2
    
    # Update .build-memory-v3.json with phase learnings
    # Include decisions made, patterns discovered
    # Store for cross-phase context and future projects
}
```

### 14. **SPECIFICATION COMPLIANCE**

The builder must create projects that are:
- **Complete and functional** - No placeholder code
- **Production-ready** - Real error handling, logging, security
- **Cloud-compatible** - Environment variables, health checks
- **Well-tested** - Integration and E2E tests only
- **Properly documented** - README, API docs, deployment guides
- **Version controlled** - Full git history
- **Cost-optimized** - Efficient API usage patterns

### 15. **QUALITY VALIDATION**

Before completion, verify:
- ✅ All phases completed successfully
- ✅ Memory integration active throughout
- ✅ Research workflow demonstrated
- ✅ Tool logging comprehensive with rationale
- ✅ Git commits include detailed context
- ✅ Cost tracking functional and accurate
- ✅ NO mock implementations anywhere
- ✅ Production standards enforced
- ✅ Security requirements met
- ✅ Error handling comprehensive

### 16. **OUTPUT STRUCTURE**

Final directory structure:
```
output-directory/
├── claude-code-builder/                    # Generated project
│   ├── [Complete, functional codebase]
│   └── [Production-ready implementation]
├── .build-state-v3-enhanced.json         # Build state
├── .build-memory-v3.json                 # Memory persistence  
├── .cost-tracking.json                   # Cost analytics
├── .mcp.json                             # MCP configuration
├── build-phases-v3.json                  # AI-generated phases
├── build-strategy-v3.md                  # Strategy document
├── .git/                                 # Version control
└── [Various log files]                   # Execution logs
```

## SUCCESS CRITERIA

The enhanced builder succeeds when it:
1. **Learns from memory** and applies knowledge across projects
2. **Researches thoroughly** using the mandatory workflow
3. **Builds real projects** with no mocks or simulations
4. **Logs comprehensively** with rationale for every action
5. **Tracks costs accurately** and identifies optimizations
6. **Enforces production standards** throughout the process
7. **Integrates version control** with detailed history
8. **Stores knowledge** for future project benefits

This creates the most intelligent autonomous project builder that learns, researches, and improves with every use while maintaining the highest production standards.