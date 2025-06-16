# Claude Code Builder v3.0 Enhanced - Dynamic Phase Definitions

## Overview

The enhanced Claude Code Builder uses AI-driven dynamic phase planning. This document provides guidance for the AI planning phase, but the actual phases are generated dynamically based on the project requirements and accumulated knowledge from mem0.

## Phase 0: Enhanced AI Planning with Research

**Objective**: Create optimal build strategy using memory and research integration.

**Mandatory Workflow**:
1. **CHECK MEM0 FIRST**: Search for similar projects and patterns
2. **RESEARCH VIA CONTEXT7**: Get latest documentation and best practices  
3. **PLAN WITH KNOWLEDGE**: Create phases that incorporate found patterns
4. **STORE LEARNINGS**: Save planning decisions in mem0

**Key Tasks**:
1. Execute `check_mem0_memory()` for relevant project patterns
2. Use context7 to research best practices for detected technologies
3. Analyze project specification with accumulated knowledge
4. Generate optimal phase breakdown (typically 12-20 phases)
5. Create detailed task lists incorporating research findings
6. Store planning insights in mem0 for future projects
7. Initialize git repository with enhanced .gitignore
8. Create build-phases-v3.json with research-informed phases
9. Generate build-strategy-v3.md with memory and research insights

**Output Files**:
- `build-phases-v3.json` - AI-generated phase definitions
- `build-strategy-v3.md` - Strategy document with research findings
- `.mcp.json` - Enhanced MCP server configuration
- `.gitignore` - Comprehensive ignore patterns

## Dynamic Phase Template

Each AI-generated phase follows this enhanced structure:

```json
{
    "number": 1,
    "name": "Foundation with Memory Integration",
    "objective": "Set up project foundation with mem0 integration",
    "includes_research": true,
    "research_topics": [
        "Python package best practices",
        "Click CLI patterns",
        "Async/await in Python"
    ],
    "memory_points": [
        "Package structure decisions",
        "Dependency choices", 
        "Architecture patterns used"
    ],
    "tasks": [
        "Create package directory structure",
        "Set up requirements.txt with researched dependencies",
        "Initialize __init__.py with version",
        "Create setup.py with entry points",
        "Add comprehensive .gitignore"
    ],
    "dependencies": [],
    "git_commit_message": "feat: Initialize project foundation with memory integration",
    "estimated_duration": "5-8 minutes",
    "complexity": 3
}
```

## Enhanced Phase Requirements

### Every Phase Must:

1. **Memory Integration**:
   - Check mem0 for relevant patterns before implementation
   - Store key decisions and learnings in mem0
   - Apply knowledge from previous similar projects

2. **Research Integration**:
   - Use context7 for documentation lookup when needed
   - Follow mem0 → context7 → web → store workflow
   - Document all research findings

3. **Tool Logging**:
   - Provide rationale for every tool use
   - Explain expected outcomes
   - Track actual results achieved

4. **Production Standards**:
   - NO mock implementations - everything REAL and FUNCTIONAL
   - NO unit tests - integration and E2E tests ONLY
   - NO placeholders or TODO comments
   - Complete, production-ready implementations

5. **Git Integration**:
   - Commit all changes with detailed messages
   - Include phase duration and memory points
   - Reference specific files created/modified

6. **Cost Tracking**:
   - Monitor API usage and costs
   - Identify optimization opportunities
   - Track tool efficiency metrics

## Typical Phase Categories

### Foundation Phases (1-3)
- Project structure setup
- Build system configuration
- Dependency management
- Basic file creation

### Core Implementation (4-10)
- Main application logic
- Data models and types
- Business logic implementation
- API development

### Integration Phases (11-15)
- External service integration
- Database setup
- Authentication systems
- API endpoints

### Quality Assurance (16-18)
- Testing implementation (integration/E2E only)
- Error handling enhancement
- Performance optimization
- Security implementation

### Finalization (19-20)
- Documentation completion
- Build verification
- Deployment preparation
- Final validation

## Research-Informed Phase Planning

### Technology Analysis
AI planning phase will research:
- Best practices for detected technology stack
- Common architectural patterns
- Performance optimization techniques
- Security implementation standards
- Testing strategies (integration-focused)

### Memory-Informed Decisions
AI will check mem0 for:
- Previous implementations of similar features
- Known working patterns and configurations
- Performance optimizations discovered
- Common pitfalls and their solutions
- Successful architectural decisions

### Context7 Documentation
AI will lookup current documentation for:
- Framework-specific best practices
- Latest API patterns and conventions
- Security recommendations
- Performance optimization guides
- Testing framework documentation

## Production Standards Enforcement

### Every Phase Implementation Must:

```bash
REQUIREMENTS (PRODUCTION STANDARDS - NO EXCEPTIONS):
- Check mem0 for any relevant patterns before implementing
- NO mock implementations - everything must be REAL and FUNCTIONAL
- NO unit tests - create integration and E2E tests ONLY
- Use REAL APIs, databases, and services (no simulations)
- Implement all functionality completely (NO placeholders, NO TODOs)
- Include comprehensive error handling with retry logic
- Add production-grade logging to stdout/stderr
- Use environment variables for ALL configuration
- Implement proper security (input validation, auth, etc.)
- Ensure cloud-ready architecture with health checks
- Store important patterns and decisions in mem0
```

### Tool Usage Guidelines

Every tool operation must include:
- **WHY**: Rationale for using this specific tool
- **WHAT**: Expected outcome from the operation
- **HOW**: Specific parameters and their reasoning
- **RESULT**: What was actually learned or achieved

### Memory Storage Points

Each phase must store in mem0:
- Working code patterns discovered
- Architecture decisions made
- Performance optimizations applied
- Security implementations used
- Integration patterns that worked
- Common errors encountered and fixes

## Example Enhanced Phase Execution

### Phase Workflow:
1. **Load Context**: Previous phase memory and accumulated learnings
2. **Check mem0**: Search for relevant patterns (e.g., "FastAPI authentication", "Docker setup")
3. **Research Context7**: Get latest documentation for libraries being used
4. **Execute with Logging**: Implement with detailed rationale for each step
5. **Store Learnings**: Save new patterns and decisions to mem0
6. **Git Commit**: Version control with comprehensive commit message
7. **Track Costs**: Record API usage and identify optimization opportunities

### Example Tool Logging:
```bash
log("TOOL", "Using filesystem__write_file to create app.py")
log("TOOL", "Rationale: FastAPI application needs main entry point based on mem0 pattern #342")
log("TOOL", "Expected: Production-ready FastAPI app with proper error handling")
# ... execute tool ...
log("TOOL", "Result: Created app.py with async endpoints and middleware")
log("MEMORY", "Storing FastAPI app pattern for future projects")
```

The AI planning phase creates a customized, research-informed build strategy that learns from every project and applies best practices discovered through memory and documentation research.