# CostTracker Implementation Comparison

## Current Implementation (Modular)

```python
@dataclass
class CostTracker:
    """Track API usage costs across models and phases."""
    
    # Token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    
    # Token usage by model
    tokens_by_model: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: {"input": 0, "output": 0})
    )
    
    # Cost tracking
    costs_by_model: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    costs_by_phase: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    costs_by_hour: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    
    # Current phase tracking
    current_phase: Optional[str] = None
    phase_start_tokens: Dict[str, int] = field(default_factory=dict)
    
    # History
    cost_history: List[Dict[str, Any]] = field(default_factory=list)
```

## Enhanced Implementation (Monolithic v2.3.0)

```python
@dataclass
class CostTracker:
    """
    Tracks API usage costs across all phases of execution.
    Enhanced in v2.3 with accurate Claude Code cost tracking.
    """
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    claude_code_cost: float = 0.0  # NEW: Separate Claude Code tracking
    research_cost: float = 0.0  # NEW: Separate research cost tracking
    phase_costs: Dict[str, float] = field(default_factory=dict)
    phase_tokens: Dict[str, Dict[str, int]] = field(default_factory=dict)
    model_usage: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"input": 0, "output": 0}))
    claude_code_sessions: List[Dict[str, Any]] = field(default_factory=list)  # NEW: Session analytics
```

## Key Differences

### 1. New Cost Categories
The enhanced version separates costs into three categories:
- **claude_code_cost**: Costs from Claude Code CLI execution
- **research_cost**: Costs from research agent API calls
- **analysis_cost**: Other API costs (total - claude_code - research)

### 2. Claude Code Session Tracking
```python
def add_claude_code_cost(self, cost: float, session_data: Dict[str, Any]):
    """Add Claude Code execution cost with session tracking"""
    self.claude_code_cost += cost
    self.total_cost += cost
    
    # Store session data for analysis
    session_info = {
        "cost": cost,
        "timestamp": datetime.now().isoformat(),
        "session_id": session_data.get("session_id"),
        "duration_ms": session_data.get("duration_ms"),
        "num_turns": session_data.get("num_turns"),
        "phase": session_data.get("phase", "unknown")
    }
    self.claude_code_sessions.append(session_info)
```

### 3. Enhanced Summary Method
```python
def get_summary(self) -> Dict[str, Any]:
    """Get comprehensive cost summary with Claude Code breakdown"""
    avg_claude_code_cost = 0.0
    if self.claude_code_sessions:
        avg_claude_code_cost = self.claude_code_cost / len(self.claude_code_sessions)
    
    return {
        "total_input_tokens": self.total_input_tokens,
        "total_output_tokens": self.total_output_tokens,
        "total_tokens": self.total_input_tokens + self.total_output_tokens,
        "total_cost": round(self.total_cost, 2),
        "claude_code_cost": round(self.claude_code_cost, 2),  # NEW
        "research_cost": round(self.research_cost, 2),  # NEW
        "analysis_cost": round(self.total_cost - self.claude_code_cost - self.research_cost, 2),  # NEW
        "phase_costs": {k: round(v, 2) for k, v in self.phase_costs.items()},
        "phase_tokens": self.phase_tokens,
        "model_usage": dict(self.model_usage),
        "claude_code_sessions": len(self.claude_code_sessions),  # NEW
        "avg_claude_code_cost": round(avg_claude_code_cost, 4),  # NEW
        "average_cost_per_phase": round(self.total_cost / max(len(self.phase_costs), 1), 2)
    }
```

### 4. New Model Breakdown Method
```python
def get_model_breakdown(self) -> List[Dict[str, Any]]:
    """Get cost breakdown by model"""
    breakdown = []
    for model, usage in self.model_usage.items():
        if model in TOKEN_COSTS:
            input_cost = (usage["input"] / 1_000_000) * TOKEN_COSTS[model]["input"]
            output_cost = (usage["output"] / 1_000_000) * TOKEN_COSTS[model]["output"]
            total_cost = input_cost + output_cost
            
            breakdown.append({
                "model": model,
                "input_tokens": usage["input"],
                "output_tokens": usage["output"],
                "total_tokens": usage["input"] + usage["output"],
                "cost": round(total_cost, 2)
            })
    
    # Add Claude Code as a separate entry
    if self.claude_code_cost > 0:
        breakdown.append({
            "model": "claude-code-execution",
            "sessions": len(self.claude_code_sessions),
            "avg_turns": sum(s.get("num_turns", 0) for s in self.claude_code_sessions) / max(len(self.claude_code_sessions), 1),
            "cost": round(self.claude_code_cost, 2)
        })
    
    return sorted(breakdown, key=lambda x: x["cost"], reverse=True)
```

## Implementation Requirements

### 1. Update Existing Methods
- `add_tokens()`: Add phase tracking for research costs
- `total_cost` property: Remove in favor of tracked field
- Rich display: Add Claude Code cost display

### 2. Integration Points
- **ClaudeCodeExecutor**: Must call `add_claude_code_cost()` after execution
- **ResearchManager**: Must track costs separately
- **UI displays**: Show breakdown of costs by category

### 3. Backward Compatibility
- Existing `add_tokens()` calls continue to work
- New fields default to 0.0
- `from_dict()` method handles missing fields gracefully