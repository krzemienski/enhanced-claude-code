# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Enhanced Claude Code Builder - a meta-builder that creates an autonomous multi-phase project builder tool. The repository contains the build scripts and specifications to create the Claude Code Builder v2.3.0 Python package.

## Key Commands

### Building the Claude Code Builder
```bash
# Main build command (requires Claude Code CLI and jq)
./builder-claude-code-builder.sh

# Install after successful build
cd claude-code-builder
pip install -e .
claude-code-builder --help
```

### Prerequisites
```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Install jq (JSON processor)
brew install jq  # macOS
sudo apt-get install jq  # Ubuntu/Debian

# Optional: Set API key for research features
export ANTHROPIC_API_KEY="your-key"

# Optional: Set Mem0 API key for intelligent memory
export MEM0_API_KEY="your-mem0-key"
```

## Architecture

The repository structure:
- `builder-claude-code-builder.sh` - Main orchestration script that drives the build
- `prompt.md` - Complete specification for Claude Code Builder v2.3.0
- `phases.md` - 12 build phases definition
- `tasks.md` - Detailed tasks for each phase
- `instructions.md` - Critical implementation requirements

## Important Implementation Notes

From instructions.md:
- Create a **modular Python package**, NOT a single file
- No mock implementations - all code must be functional
- Follow clean architecture principles
- Include comprehensive error handling
- Production-ready code only

## Build Process

The build script executes 12 phases:
1. Project Foundation - Setup and structure
2. Data Models - Core data structures
3. MCP System - Model Context Protocol integration
4. Research System - Multi-agent research capabilities
5. Custom Instructions - Instruction processing
6. Execution System - Project building logic
7. UI System - Rich terminal interface
8. Validation System - Comprehensive validation
9. Utilities - Helper functions
10. Main Integration - CLI and orchestration
11. Testing - Test implementation
12. Documentation - README and examples

Each phase uses Claude Code with specific prompts and up to 50 turns. The build includes:
- Progress tracking with visual indicators
- State persistence for resumable builds
- MCP servers for enhanced capabilities
- Automatic validation after each phase
- Intelligent memory with Mem0 MCP (when API key is set)

## Development Tips

- The build creates a `claude-code-builder` directory with the complete Python package
- Use `--resume` flag to continue interrupted builds
- Build state is saved in `.build-state.json`
- Each phase produces specific modules as defined in tasks.md
- The final tool can build any project from markdown specifications

## Mem0 Integration

When `MEM0_API_KEY` is set, the builder uses Mem0's intelligent memory system instead of the standard MCP memory server. This provides:

### Key Benefits
- **Semantic Search**: Find memories using natural language queries instead of exact keys
- **Intelligent Extraction**: Mem0 uses LLMs to automatically extract important information
- **Contradiction Resolution**: Automatically updates and resolves conflicting memories
- **Persistent Storage**: Memories persist across sessions for better continuity
- **Context Understanding**: Mem0 understands relationships between memories

### Memory Usage
- Init phase stores comprehensive project analysis
- Start phase saves dependency research and patterns
- Each build phase tracks progress and decisions
- All memories are searchable across sessions

### Configuration
```bash
# Enable Mem0 integration
export MEM0_API_KEY="your-mem0-api-key"

# Run the builder - it will automatically use Mem0
./builder-claude-code-builder.sh
```

Without `MEM0_API_KEY`, the builder falls back to the standard memory MCP server.