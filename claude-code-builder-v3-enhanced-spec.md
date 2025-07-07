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
