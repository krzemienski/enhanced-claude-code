# 🚀 Advanced Claude Code Tutorial: Building Complex Projects with AI

> **Learn how to leverage Claude Code's advanced features through a real-world example of building an autonomous project builder**

This repository demonstrates **production-level techniques** for using Claude Code to build complex software projects. Through our example of building the Claude Code Builder v2.3.0, you'll learn how to orchestrate Claude Code for maximum effectiveness.

## 📖 Essential Claude Code Documentation

- 🏠 **[Claude Code Overview](https://docs.anthropic.com/en/docs/claude-code/overview)** - Getting started
- 🛠️ **[CLI Usage & Commands](https://docs.anthropic.com/en/docs/claude-code/cli-usage)** - All CLI features
- 🧠 **[Memory Management](https://docs.anthropic.com/en/docs/claude-code/memory)** - CLAUDE.md files
- 🔒 **[Security & Permissions](https://docs.anthropic.com/en/docs/claude-code/security)** - Tool permissions
- 💰 **[Cost Management](https://docs.anthropic.com/en/docs/claude-code/costs)** - API usage costs
- 🎓 **[Tutorials](https://docs.anthropic.com/en/docs/claude-code/tutorials)** - Common workflows
- 🔧 **[Troubleshooting](https://docs.anthropic.com/en/docs/claude-code/troubleshooting)** - Common issues

## 🎯 What This Tutorial Teaches

### Claude Code Basics vs. Advanced Usage

```mermaid
graph LR
    A[Basic Claude Code] -->|This Tutorial| B[Advanced Claude Code]
    
    subgraph "Basic Usage"
        A1[Simple prompts]
        A2[Manual oversight]
        A3[Single context]
        A4[Limited scope]
    end
    
    subgraph "Advanced Features"
        B1[Multi-phase orchestration]
        B2[MCP servers]
        B3[State persistence]
        B4[Context management]
        B5[Automated validation]
        B6[Custom instructions]
    end
```

## 🔑 Critical Insight: Custom Instructions & Tool Awareness

**THE MOST IMPORTANT LESSON:** Every prompt sent to Claude must explicitly remind it of available tools and MCP servers. Claude doesn't automatically remember what tools it has access to!

```bash
# ❌ BAD - Claude won't use tools effectively
PROMPT="Build the research system"

# ✅ GOOD - Explicit tool awareness
PROMPT="Build the research system.

IMPORTANT: You have access to these MCP tools:
- memory__create_memory: Save important state
- memory__retrieve_memory: Access saved state
- sequential_thinking__think_about: Break down complex problems
- filesystem__read_file: Enhanced file operations

Use these tools to:
1. Save progress frequently with memory__create_memory
2. Break complex logic with sequential_thinking__think_about
3. Validate outputs before proceeding"
```

### Why This Matters

```mermaid
sequenceDiagram
    participant S as Shell Script
    participant C as Claude Code
    participant M as MCP Servers
    participant F as Filesystem
    
    Note over S,F: Phase 4: Research System
    
    S->>C: Prompt with tool instructions
    Note right of C: "You have memory__create_memory<br/>Use it to save agent states"
    
    C->>M: memory__create_memory("agent_config")
    M-->>C: Memory saved
    
    C->>M: sequential_thinking__think_about("How to implement 7 agents")
    M-->>C: Step-by-step plan
    
    C->>F: Write agent implementations
    F-->>C: Files created
    
    C->>M: memory__create_memory("phase_4_complete")
    Note over C: Preserves state for next phase
```

## 🏗️ Architecture Overview

The shell script demonstrates sophisticated orchestration:

```mermaid
graph TD
    A[Shell Script Orchestrator] --> B[Claude Code CLI]
    B --> C[MCP Servers]
    B --> D[Phase Management]
    B --> E[State Persistence]
    
    C --> C1[memory__*<br/>Persistent Storage]
    C --> C2[sequential_thinking__*<br/>Complex Reasoning]
    C --> C3[filesystem__*<br/>Enhanced I/O]
    
    D --> D1[12 Build Phases]
    D --> D2[Context Isolation]
    D --> D3[Tool Reminders]
    
    E --> E1[Resume Capability]
    E --> E2[Progress Tracking]
    E --> E3[Error Recovery]
    
    style C1 fill:#f9f,stroke:#333,stroke-width:4px
    style C2 fill:#f9f,stroke:#333,stroke-width:4px
    style C3 fill:#f9f,stroke:#333,stroke-width:4px
```

## 📚 Key Concepts & Techniques

### 1. **Multi-Phase Architecture with Tool Awareness** 🔄

Each phase includes explicit tool instructions:

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant P1 as Phase 1
    participant P2 as Phase 2
    participant P3 as Phase 3
    participant MCP as MCP Memory
    
    O->>P1: Foundation + Tool List
    P1->>MCP: memory__create_memory("foundation_complete")
    MCP-->>P1: State saved
    P1-->>O: Phase complete
    
    O->>P2: Models + Tool List + Previous State
    P2->>MCP: memory__retrieve_memory("foundation_complete")
    MCP-->>P2: Previous state
    P2->>MCP: memory__create_memory("models_complete")
    MCP-->>P2: State saved
    P2-->>O: Phase complete
    
    O->>P3: MCP System + Tool List + All States
    P3->>MCP: memory__retrieve_memory("*")
    MCP-->>P3: All previous states
    Note over P3: Builds on previous work
```

### 2. **MCP (Model Context Protocol) Servers** 🧠

```bash
# Critical: These servers provide tools Claude must be reminded to use!
MCP_SERVERS='[
  {
    "id": "memory",
    "command": "npx",
    "arguments": ["-y", "@modelcontextprotocol/server-memory"],
    "name": "Memory Operations"
  },
  {
    "id": "sequential-thinking", 
    "command": "npx",
    "arguments": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
    "name": "Sequential Thinking"
  },
  {
    "id": "filesystem",
    "command": "npx",
    "arguments": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp", "/Users"],
    "name": "Filesystem Operations"
  }
]'
```

**Available MCP Tools:**
- **Memory Server** 📝
  - `memory__create_memory(key, value)` - Save state
  - `memory__retrieve_memory(key)` - Get saved state
  - `memory__search_memories(query)` - Find memories
- **Sequential Thinking** 🤔
  - `sequential_thinking__think_about(problem)` - Step-by-step reasoning
- **Filesystem Server** 📁
  - `filesystem__read_file(path)` - Enhanced reading
  - `filesystem__write_file(path, content)` - Enhanced writing

### 3. **Custom Instructions in Every Prompt** 📝

Look at how each phase prompt includes tool reminders:

```bash
# From phases.md - EVERY phase includes this pattern:
PHASE_PROMPT="
Task: [Specific task description]

AVAILABLE TOOLS AND THEIR USAGE:
- memory__create_memory: Use this to save important state/decisions
- memory__retrieve_memory: Use this to access previous phase outputs
- sequential_thinking__think_about: Use for complex architectural decisions
- filesystem__read_file/write_file: Use for all file operations

CRITICAL REMINDERS:
1. Save your progress frequently using memory__create_memory
2. Check previous work with memory__retrieve_memory before starting
3. Use sequential_thinking for any complex logic
4. Validate all outputs before marking complete

Remember: These tools are available through MCP. Use them actively!"
```

### 4. **State Management Across Phases** 💾

```mermaid
sequenceDiagram
    participant P as Phase
    participant C as Claude
    participant M as Memory MCP
    participant S as State File
    
    P->>C: Start Phase with tools list
    C->>M: memory__retrieve_memory("previous_phases")
    M-->>C: Previous context
    
    Note over C: Works on task
    
    C->>M: memory__create_memory("current_progress", data)
    M-->>C: Saved
    
    C->>M: memory__create_memory("decisions_made", rationale)
    M-->>C: Saved
    
    P->>S: Save phase state to .json
    Note over S: Enables resume capability
```

### 5. **Context Window Optimization** 📊

```mermaid
graph TD
    A[Phase Input] --> B{Context Builder}
    B --> C[Current Instructions]
    B --> D[Tool Reminders]
    B --> E[Previous Memories]
    B --> F[Validation Rules]
    
    C --> G[Claude Code]
    D --> G
    E --> G
    F --> G
    
    G --> H[Uses Tools]
    H --> I[memory__*]
    H --> J[sequential_thinking__*]
    H --> K[filesystem__*]
    
    I --> L[Phase Output]
    J --> L
    K --> L
    
    L --> M[Validation]
    M -->|Pass| N[Save to Memory]
    M -->|Fail| O[Retry with Feedback]
```

### 6. **Tool Usage Patterns** 🛠️

```bash
# Pattern 1: Start of each phase
"First, use memory__retrieve_memory to check previous work"

# Pattern 2: Complex decisions
"Use sequential_thinking__think_about to plan the architecture"

# Pattern 3: Progress tracking
"Use memory__create_memory to save completed components"

# Pattern 4: Cross-phase communication
"Save interface definitions with memory__create_memory for later phases"
```

## 🎓 Advanced Techniques Demonstrated

### 1. **Memory-Driven Development**

```mermaid
sequenceDiagram
    participant Phase1 as Phase 1: Foundation
    participant Phase2 as Phase 2: Models
    participant Phase3 as Phase 3: MCP
    participant Memory as Memory Server
    
    Phase1->>Memory: create_memory("project_structure", {...})
    Phase1->>Memory: create_memory("core_decisions", {...})
    
    Phase2->>Memory: retrieve_memory("project_structure")
    Note over Phase2: Builds on foundation
    Phase2->>Memory: create_memory("data_models", {...})
    
    Phase3->>Memory: retrieve_memory("data_models")
    Note over Phase3: Integrates with models
    Phase3->>Memory: create_memory("mcp_config", {...})
```

### 2. **Progressive Context Building**

Each phase explicitly tells Claude:
1. What tools are available
2. What was built in previous phases (via memory)
3. What specific tools to use for this phase
4. How to validate the output

### 3. **Tool-First Architecture**

```bash
# Every major decision goes through tools:
DECISION_PATTERN="
1. Use sequential_thinking__think_about to analyze options
2. Use memory__create_memory to save the decision
3. Use filesystem__ tools for implementation
4. Use memory__create_memory to mark completion"
```

## 🚀 Best Practices for Tool Usage

### 1. **Always List Available Tools**

```bash
# In EVERY prompt:
echo "Available MCP tools:
- memory__create_memory(key, value)
- memory__retrieve_memory(key)
- sequential_thinking__think_about(problem)
- filesystem__read_file(path)
- filesystem__write_file(path, content)"
```

### 2. **Provide Usage Examples**

```bash
# Show Claude HOW to use tools:
echo "Example usage:
await memory__create_memory('agent_1_complete', {
    'status': 'implemented',
    'files': ['agent1.py'],
    'interfaces': ['ResearchAgent']
})"
```

### 3. **Enforce Tool Usage**

```bash
# Make it mandatory:
echo "REQUIREMENT: You MUST use memory__create_memory 
after completing each component"
```

## 📊 Performance Impact of Tool Awareness

| Approach | Success Rate | Context Efficiency | State Preservation |
|----------|--------------|-------------------|-------------------|
| Without tool reminders | ~40% | Poor | None |
| With explicit tool instructions | ~95% | Excellent | Complete |

## 🔍 Deep Dive: Critical Script Sections

### Custom Instruction Injection

```bash
# The script ensures EVERY phase includes:
inject_tool_instructions() {
    local phase_prompt=$1
    local tool_instructions="
CRITICAL: Use these MCP tools actively:
- memory__create_memory: Save ALL decisions and progress
- memory__retrieve_memory: Check previous work FIRST
- sequential_thinking__think_about: For ANY complex logic
- filesystem__*: For ALL file operations

DO NOT rely on standard file operations when MCP tools are available!"
    
    echo "${phase_prompt}${tool_instructions}"
}
```

### Memory-First Validation

```bash
# Validation checks memory usage:
validate_phase() {
    # Check if Claude used memory tools
    if ! grep -q "memory__create_memory" "$OUTPUT"; then
        echo "ERROR: Phase didn't save state to memory!"
        return 1
    fi
}
```

## 🎯 Key Takeaways

1. **Every prompt must include tool instructions** - Claude doesn't remember
2. **Use MCP memory for everything** - Don't rely on filesystem state alone
3. **Break complex tasks with sequential_thinking** - Better than one-shot attempts
4. **Save progress frequently** - Use memory__create_memory liberally
5. **Check previous work first** - Always memory__retrieve_memory at start
6. **Validate tool usage** - Ensure Claude actually uses the tools

## 🤝 Contributing

Found better prompt patterns? Submit a PR! Help others master Claude Code orchestration.

## 📝 License

MIT - Use these techniques in your own projects!

---

**Remember:** The difference between basic and advanced Claude Code usage is **explicit tool awareness in every prompt**. This tutorial shows you how to build that awareness into your orchestration layer for maximum effectiveness.