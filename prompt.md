# Claude Code Builder v3.0 Enhanced - Complete Specification

## Project Overview

You are building **Claude Code Builder v3.0 Enhanced**, an autonomous multi-phase project builder shell script that orchestrates Claude Code SDK with full memory integration, research capabilities, and production-first standards.

**CRITICAL**: This is a sophisticated shell script that implements CLAUDE.md compliance with:
- Full mem0 integration for persistent memory across all projects
- Context7 integration for latest documentation lookup
- Comprehensive research workflow (mem0 → context7 → web → store)
- Enhanced tool usage logging with rationale
- Git integration throughout build process
- Production standards enforcement (NO mocks, NO dry runs)

## Enhanced Architecture

### Memory-First Workflow
```bash
1. CHECK MEM0 FIRST → Search for existing knowledge
2. USE CONTEXT7 SECOND → Get latest documentation  
3. WEB SEARCH THIRD → Only if needed
4. STORE IN MEM0 ALWAYS → Save all findings
```

### Script Components

```
builder-claude-code-builder.sh          # Main enhanced script
├── Memory Integration
│   ├── mem0 MCP server configuration
│   ├── check_mem0_memory() function
│   ├── save_memory_state() function
│   └── Memory persistence across phases
├── Research System
│   ├── context7 MCP server configuration
│   ├── execute_research_phase() function
│   ├── Research workflow enforcement
│   └── Knowledge storage automation
├── Enhanced Logging
│   ├── Tool usage rationale logging
│   ├── parse_enhanced_stream_output()
│   ├── display_tool_parameters()
│   └── Comprehensive operation tracking
├── Git Integration
│   ├── initialize_git_repo() function
│   ├── Per-phase commit automation
│   ├── Enhanced commit messages
│   └── Version control throughout
├── Production Standards
│   ├── NO mock implementations
│   ├── NO unit tests (integration only)
│   ├── NO dry runs (real builds only)
│   ├── Real API testing requirements
│   └── Complete functionality mandate
└── MCP Configuration
    ├── .mcp.json generation
    ├── Enhanced server registry
    ├── Environment variable configuration
    └── Security compliance
```

## Key Features in v3.0 Enhanced

### 1. Memory-First Architecture
- **Persistent Knowledge**: mem0 integration stores learnings across ALL projects
- **Cross-Project Learning**: Knowledge from Project A benefits Project B
- **Context Preservation**: Maintains state across build phases
- **Knowledge Accumulation**: Builds intelligence over time

### 2. Comprehensive Research System
- **Mandatory Workflow**: mem0 → context7 → web search → store findings
- **Documentation-First**: Always check official docs via context7
- **Learning Storage**: All research findings stored in mem0
- **Research Agents**: Specialized research for different topics

### 3. Enhanced Tool Logging
- **Rationale Tracking**: Every tool use includes WHY it was chosen
- **Expected Outcomes**: Documents what each tool should achieve
- **Result Tracking**: Captures what was actually learned/achieved
- **Performance Analytics**: Tracks tool effectiveness over time

### 4. Git Integration Throughout
- **Version Control**: Every phase commits changes
- **Detailed Messages**: Commits include phase details and duration
- **Change Tracking**: Full history of build process
- **Rollback Capability**: Can revert to any previous state

### 5. Production Standards Enforcement
```bash
REQUIREMENTS (PRODUCTION STANDARDS - NO EXCEPTIONS):
- NO mock implementations - everything must be REAL and FUNCTIONAL
- NO unit tests - create integration and E2E tests ONLY  
- NO dry runs - execute actual builds that create real projects
- Use REAL APIs, databases, and services (no simulations)
- Implement all functionality completely (NO placeholders)
```

### 6. Cost Tracking and Analytics
- **Per-Phase Costs**: Detailed breakdown by phase
- **Operation Categorization**: Research vs implementation vs testing
- **Optimization Suggestions**: Identifies cost reduction opportunities
- **Usage Analytics**: Tracks patterns for efficiency improvements

## MCP Server Configuration

### Enhanced Server Registry
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

## Enhanced CLI Interface

### Command Line Options
```bash
./builder-claude-code-builder.sh [OPTIONS]

Options:
  -o, --output-dir DIR    Output directory for the build (default: current directory)
  -r, --resume            Resume from last checkpoint  
  --no-research           Disable research phase
  --skip-mem0-check       Skip initial mem0 memory check
  -h, --help              Show this help message

Examples:
  # Full-featured build with memory and research
  ./builder-claude-code-builder.sh
  
  # Build in specific directory
  ./builder-claude-code-builder.sh -o /path/to/output
  
  # Resume interrupted build
  ./builder-claude-code-builder.sh --resume
  
  # Quick build without research (not recommended)
  ./builder-claude-code-builder.sh --no-research
```

## Build Process Flow

### Phase 0: Enhanced AI Planning with Research
1. **Memory Check**: Search mem0 for similar projects
2. **Research Phase**: Use context7 for best practices
3. **AI Planning**: Create optimal phase breakdown with research insights
4. **Git Initialization**: Set up version control
5. **Knowledge Storage**: Store planning decisions in mem0

### Dynamic Phases (AI-Generated)
Each phase follows enhanced workflow:
1. **Load Context**: Previous phase memory and learnings
2. **Check mem0**: Search for relevant patterns and solutions
3. **Research**: Use context7 for documentation when needed
4. **Execute**: Implement with full logging and rationale
5. **Store Learnings**: Save discoveries and patterns to mem0
6. **Git Commit**: Version control with detailed messages
7. **Cost Tracking**: Record and analyze API usage

### Final Phase: Enhanced Functional Testing
1. **Memory Integration Test**: Verify mem0 usage throughout
2. **Research Workflow Test**: Confirm mem0 → context7 → web workflow
3. **Tool Logging Test**: Ensure comprehensive rationale logging
4. **Standard Functional Tests**: Installation, CLI, build validation
5. **Production Standards Verification**: Confirm NO mocks, real builds only

## CLAUDE.md Compliance

### ✅ Memory Context Management (MANDATORY FIRST STEP)
- Always check mem0 before ANY code/task
- Search first, code second - No exceptions
- Store everything learned for future projects
- Cross-project knowledge benefits

### ✅ Production Testing Requirements
- NO mock testing - All tests use real services
- NO unit tests - Integration and end-to-end only
- Test in production-like environments
- Real APIs, file systems, network conditions

### ✅ Research and Documentation (MEMORY-FIRST APPROACH)
- Research workflow: mem0 → context7 → web → store
- Mandatory documentation of all findings
- Cross-project learning stored in mem0
- Generic, reusable knowledge captured

### ✅ Git and Version Control
- Every change properly versioned
- Descriptive commit messages with context
- Feature branches for development
- Full build history preserved

### ✅ Security Standards
- Zero tolerance for security violations
- Environment variables for all credentials
- Input validation and output sanitization
- Production-grade error handling

## Success Criteria

### Build Success
- All phases complete with memory integration
- Research workflow demonstrated throughout
- Comprehensive tool logging with rationale
- Git integration active and functional
- Production standards enforced (no mocks)

### Memory Integration Success
- mem0 checked before every major decision
- Knowledge stored and retrieved effectively
- Cross-phase memory context preserved
- Research findings accumulated in mem0

### Research Workflow Success
- mem0 → context7 → web pattern followed
- Documentation lookups via context7
- Web searches only when necessary
- All findings stored in mem0 for future use

### Tool Logging Success
- Every tool use includes rationale
- Expected outcomes documented
- Results tracked and analyzed
- Performance patterns identified

### Production Standards Success
- NO mock implementations anywhere
- NO unit tests (integration/E2E only)
- Real APIs and services used throughout
- Complete, functional implementations

## Output Structure

```
output-directory/
├── claude-code-builder/               # Generated project
│   ├── [AI-generated project files]
│   └── [Complete, functional codebase]
├── .build-state-v3-enhanced.json    # Build state for resumption
├── .build-memory-v3.json            # Memory persistence
├── .cost-tracking.json              # Cost analytics
├── .mcp.json                        # MCP configuration
├── build-phases-v3.json             # AI-generated phases
├── build-strategy-v3.md             # Build strategy
├── .git/                           # Version control
├── planning-output.log             # Planning phase logs
├── phase-*-output.log             # Per-phase execution logs
├── functional-test-output.log     # Testing logs
└── .claude-test-results-enhanced.json # Test results
```

Build the most intelligent autonomous project builder that learns, researches, and improves with every use while maintaining the highest production standards.