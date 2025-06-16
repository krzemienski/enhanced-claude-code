# Claude Code Builder Enhancement Plan

## Overview
This document outlines the enhancements found in `claude-code-builder-researcher.py` (monolithic v2.3.0) that need to be ported to the modular implementation at `/Users/nick/Desktop/ccb-mem0/claude-code-builder`.

## Priority 1: Critical Enhancements

### 1.1 CostTracker Enhancements
**File:** `claude_code_builder/models/cost_tracker.py`

**New Fields:**
```python
claude_code_cost: float = 0.0  # Separate Claude Code cost tracking
research_cost: float = 0.0  # Separate research cost tracking
claude_code_sessions: List[Dict[str, Any]] = field(default_factory=list)
```

**New Methods:**
```python
def add_claude_code_cost(self, cost: float, session_data: Dict[str, Any]):
    """Track Claude Code execution costs separately with session analytics"""
    
def get_model_breakdown(self) -> List[Dict[str, Any]]:
    """Get detailed cost breakdown by model including Claude Code sessions"""
```

**Enhanced get_summary():**
- Add claude_code_cost breakdown
- Add research_cost breakdown
- Add analysis_cost (total - claude_code - research)
- Add claude_code_sessions count
- Add avg_claude_code_cost

### 1.2 Research Agent Additions
**Files:** 
- `claude_code_builder/research/agents.py`
- `claude_code_builder/models/research.py`

**Missing Agents:**
1. **PerformanceEngineer**
   - Focus: performance optimization, scalability, caching
   - Metadata: performance_metrics, optimization_areas

2. **DevOpsSpecialist**
   - Focus: deployment, containerization, monitoring
   - Metadata: deployment_checklist, recommended_tools

## Priority 2: Important Enhancements

### 2.1 Tool Management Enhancements
**File:** `claude_code_builder/tools/manager.py`

**New Features:**
```python
tool_dependencies: Dict[str, Set[str]] = defaultdict(set)
disabled_tools: Set[str] = set()
performance_metrics: Dict[str, float] = defaultdict(float)
```

**New Tools:**
- File operations: `rename`, `chmod`, `rmdir`
- Text processing: `sed`, `awk`

### 2.2 MCP Server Discovery
**File:** `claude_code_builder/mcp/recommendation_engine.py`

**New Features:**
```python
installed_servers: Set[str] = set()

async def _check_installed_servers(self):
    """Check which MCP servers are already installed"""
    
async def _assess_complexity(self, specification: str) -> str:
    """Assess project complexity from specification"""
```

## Priority 3: Enhancement Features

### 3.1 Custom Instructions
**File:** `claude_code_builder/instructions/manager.py`

**Enhanced Matching:**
- Regex pattern support: `"regex:pattern"`
- Validation rules
- validate() method

### 3.2 Phase Context Management
**File:** `claude_code_builder/models/phase.py`

**New Fields:**
```python
context: Dict[str, Any] = field(default_factory=dict)
validation_results: Dict[str, bool] = field(default_factory=dict)
```

**New Methods:**
```python
def validate(self) -> bool:
    """Validate phase completion"""
```

### 3.3 Project Memory
**File:** `claude_code_builder/models/memory.py`

**New Fields:**
```python
phase_contexts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
error_log: List[Dict[str, Any]] = field(default_factory=list)
```

**New Methods:**
```python
def store_phase_context(self, phase_id: str, context: Dict[str, Any])
def log_error(self, error: str, phase_id: Optional[str] = None)
def get_accumulated_context(self, up_to_phase: str) -> Dict[str, Any]
```

## Implementation Order

1. **Week 1: Cost Tracking**
   - Update CostTracker with new fields and methods
   - Integrate Claude Code cost tracking in executor
   - Update UI displays

2. **Week 2: Research System**
   - Add missing research agents
   - Enhance research synthesis
   - Add confidence scoring

3. **Week 3: Tool & MCP**
   - Add new tools
   - Implement server discovery
   - Add performance metrics

4. **Week 4: Context & Validation**
   - Enhance phase validation
   - Add memory context methods
   - Update custom instructions

## Testing Requirements

Each enhancement needs:
1. Unit tests for new functionality
2. Integration tests with existing systems
3. Backward compatibility checks
4. Performance impact assessment

## Migration Guide

For existing users:
1. New cost tracking fields will default to 0.0
2. Missing research agents will be auto-initialized
3. Existing builds can continue without new features
4. New features opt-in via configuration