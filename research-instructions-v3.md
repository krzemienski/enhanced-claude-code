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
