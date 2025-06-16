# Phase 1: CostTracker Enhancement - Technical Implementation Guide

## Overview
This guide provides the exact code changes and integration steps for implementing CostTracker enhancements in the Claude Code Builder modular codebase.

## Step 1: Update cost_tracker.py

### 1.1 Add New Imports
```python
from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime
from collections import defaultdict
```

### 1.2 Add New Fields to CostTracker
```python
@dataclass
class CostTracker:
    """Track API usage costs across models and phases.
    
    Enhanced in v2.3.0 with:
    - Separate Claude Code cost tracking
    - Research cost categorization  
    - Session analytics for Claude Code executions
    """
    
    # Existing fields...
    
    # NEW FIELDS (v2.3.0)
    total_cost: float = 0.0
    claude_code_cost: float = 0.0
    research_cost: float = 0.0
    claude_code_sessions: List[Dict[str, Any]] = field(default_factory=list)
```

### 1.3 Add New Method: add_claude_code_cost
```python
def add_claude_code_cost(self, cost: float, session_data: Dict[str, Any]) -> None:
    """Add Claude Code execution cost with session tracking.
    
    Args:
        cost: The cost of the Claude Code session
        session_data: Metadata about the session including:
            - session_id: Unique session identifier
            - duration_ms: Session duration in milliseconds
            - num_turns: Number of conversation turns
            - phase: Phase name for tracking
    """
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
    
    # Add to phase costs
    phase = session_data.get("phase", "claude_code_execution")
    if phase not in self.costs_by_phase:
        self.costs_by_phase[phase] = 0.0
    self.costs_by_phase[phase] += cost
```

### 1.4 Update add_tokens Method
```python
def add_tokens(self, model: str, input_tokens: int, output_tokens: int, phase_id: Optional[str] = None) -> float:
    """Add token usage and calculate cost."""
    # Existing token update code...
    
    # Calculate cost
    cost = self._calculate_cost(model, input_tokens, output_tokens)
    
    # Update cost tracking
    self.costs_by_model[model] += cost
    self.total_cost += cost  # NEW: Update total cost
    
    # Track by phase if provided
    phase_id = phase_id or self.current_phase
    if phase_id:
        self.costs_by_phase[phase_id] += cost
        
        # NEW: Track research costs separately
        if "research" in phase_id.lower():
            self.research_cost += cost
    
    # Rest of existing method...
```

### 1.5 Add New Property: analysis_cost
```python
@property
def analysis_cost(self) -> float:
    """Calculate cost for non-Claude-Code, non-research API calls."""
    return self.total_cost - self.claude_code_cost - self.research_cost
```

### 1.6 Add New Method: get_model_breakdown
```python
def get_model_breakdown(self) -> List[Dict[str, Any]]:
    """Get cost breakdown by model including Claude Code.
    
    Returns:
        List of model cost breakdowns sorted by cost
    """
    breakdown = []
    
    # Add traditional model costs
    for model, usage in self.tokens_by_model.items():
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
        avg_turns = 0
        if self.claude_code_sessions:
            total_turns = sum(s.get("num_turns", 0) for s in self.claude_code_sessions)
            avg_turns = total_turns / len(self.claude_code_sessions)
        
        breakdown.append({
            "model": "claude-code-execution",
            "sessions": len(self.claude_code_sessions),
            "avg_turns": round(avg_turns, 1),
            "cost": round(self.claude_code_cost, 2)
        })
    
    return sorted(breakdown, key=lambda x: x["cost"], reverse=True)
```

### 1.7 Update to_dict Method
```python
def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary for serialization."""
    # Calculate average Claude Code cost
    avg_claude_code_cost = 0.0
    if self.claude_code_sessions:
        avg_claude_code_cost = self.claude_code_cost / len(self.claude_code_sessions)
    
    return {
        # Existing fields...
        "total_cost": self.total_cost,
        "claude_code_cost": round(self.claude_code_cost, 2),
        "research_cost": round(self.research_cost, 2),
        "analysis_cost": round(self.analysis_cost, 2),
        # ... rest of existing fields ...
        "model_breakdown": self.get_model_breakdown(),
        "claude_code_sessions": len(self.claude_code_sessions),
        "avg_claude_code_cost": round(avg_claude_code_cost, 4)
    }
```

### 1.8 Update from_dict Method
```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'CostTracker':
    """Create CostTracker from dictionary."""
    tracker = cls()
    
    # Restore token counts
    tracker.total_input_tokens = data.get("total_input_tokens", 0)
    tracker.total_output_tokens = data.get("total_output_tokens", 0)
    
    # Restore costs (with v2.3.0 fields)
    tracker.total_cost = data.get("total_cost", 0.0)
    tracker.claude_code_cost = data.get("claude_code_cost", 0.0)
    tracker.research_cost = data.get("research_cost", 0.0)
    
    # Restore dictionaries
    tracker.costs_by_model = defaultdict(float, data.get("costs_by_model", {}))
    tracker.costs_by_phase = defaultdict(float, data.get("costs_by_phase", {}))
    tracker.costs_by_hour = defaultdict(float, data.get("costs_by_hour", {}))
    
    # Restore token usage by model
    tokens_data = data.get("tokens_by_model", {})
    for model, tokens in tokens_data.items():
        tracker.tokens_by_model[model] = defaultdict(int, tokens)
    
    # Restore Claude Code sessions if present
    if "claude_code_sessions" in data and isinstance(data["claude_code_sessions"], list):
        tracker.claude_code_sessions = data["claude_code_sessions"]
    
    # Calculate total_cost if not present (backward compatibility)
    if tracker.total_cost == 0.0 and tracker.costs_by_model:
        tracker.total_cost = sum(tracker.costs_by_model.values())
    
    return tracker
```

### 1.9 Update __rich__ Display Method
```python
def __rich__(self) -> Panel:
    """Rich representation for terminal display."""
    # Create cost summary table
    summary_table = Table(title="Cost Summary", show_header=True, header_style="bold cyan")
    summary_table.add_column("Metric", style="yellow")
    summary_table.add_column("Value", style="white")
    
    summary_table.add_row("Total Cost", f"${self.total_cost:.4f}")
    summary_table.add_row("├─ Claude Code", f"${self.claude_code_cost:.4f}")
    summary_table.add_row("├─ Research", f"${self.research_cost:.4f}")
    summary_table.add_row("└─ Analysis", f"${self.analysis_cost:.4f}")
    # ... rest of existing display code ...
    
    if self.claude_code_sessions:
        avg_cost = self.claude_code_cost / len(self.claude_code_sessions)
        summary_table.add_row("Claude Code Sessions", str(len(self.claude_code_sessions)))
        summary_table.add_row("Avg Cost/Session", f"${avg_cost:.4f}")
```

## Step 2: Update ClaudeCodeExecutor

### 2.1 Locate execution/executor.py
Find the section where Claude Code output is parsed for cost information.

### 2.2 Add Session Tracking
```python
# In the execute_phase method, after parsing the cost from stream:

# Look for where cost is extracted, likely something like:
if event_type == "usage" or "cost" in data:
    # Extract cost information
    cost_value = data.get("cost", 0.0)
    
    # NEW: Create session data
    session_data = {
        "session_id": str(uuid.uuid4()),  # Or use existing session ID
        "duration_ms": int((time.time() - start_time) * 1000),
        "num_turns": turn_count,  # Track this during execution
        "phase": phase.id
    }
    
    # NEW: Add Claude Code cost
    if self.cost_tracker:
        self.cost_tracker.add_claude_code_cost(cost_value, session_data)
```

### 2.3 Update Stream Parsing
```python
# In the stream parsing loop:
turn_count = 0

async for event in stream:
    if event.type == "message_start":
        turn_count += 1
    
    # Existing parsing logic...
    
    # NEW: Track session metrics
    if event.type == "usage":
        # This might be the final usage summary
        if hasattr(event, 'total_cost'):
            session_data = {
                "session_id": execution_id,
                "duration_ms": int((time.time() - start_time) * 1000),
                "num_turns": turn_count,
                "phase": self.current_phase
            }
            self.cost_tracker.add_claude_code_cost(event.total_cost, session_data)
```

## Step 3: Update Research Manager

### 3.1 Locate research/manager.py
Find where research agent costs are tracked.

### 3.2 Update Cost Tracking
```python
# In the method where research is performed:
async def _perform_research(self, agent, query):
    # Existing research logic...
    
    # When adding cost:
    if response and hasattr(response, 'usage'):
        self.cost_tracker.add_tokens(
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            phase_id=f"research_{agent.name}"  # Ensures research tracking
        )
```

## Step 4: Update UI Display

### 4.1 Locate ui/display.py
Find the cost display section.

### 4.2 Enhanced Cost Display
```python
def display_cost_summary(self):
    """Display enhanced cost summary with breakdown."""
    cost_data = self.cost_tracker.to_dict()
    
    # Create breakdown panel
    breakdown_items = []
    
    # Total cost with breakdown
    breakdown_items.append(
        f"[bold]Total Cost:[/bold] ${cost_data['total_cost']:.2f}"
    )
    
    # Category breakdown
    if cost_data['claude_code_cost'] > 0:
        breakdown_items.append(
            f"├─ Claude Code: ${cost_data['claude_code_cost']:.2f} "
            f"({cost_data['claude_code_sessions']} sessions)"
        )
    
    if cost_data['research_cost'] > 0:
        breakdown_items.append(
            f"├─ Research: ${cost_data['research_cost']:.2f}"
        )
    
    if cost_data['analysis_cost'] > 0:
        breakdown_items.append(
            f"└─ Analysis: ${cost_data['analysis_cost']:.2f}"
        )
    
    # Model breakdown
    if cost_data.get('model_breakdown'):
        breakdown_items.append("\n[bold]By Model:[/bold]")
        for model_info in cost_data['model_breakdown']:
            if model_info['model'] == 'claude-code-execution':
                breakdown_items.append(
                    f"• {model_info['model']}: ${model_info['cost']:.2f} "
                    f"({model_info['sessions']} sessions, "
                    f"avg {model_info['avg_turns']:.1f} turns)"
                )
            else:
                breakdown_items.append(
                    f"• {model_info['model']}: ${model_info['cost']:.2f} "
                    f"({model_info['total_tokens']:,} tokens)"
                )
    
    self.console.print(Panel(
        "\n".join(breakdown_items),
        title="💰 Cost Breakdown",
        border_style="green" if cost_data['total_cost'] < 10 else "yellow"
    ))
```

## Step 5: Create Unit Tests

### 5.1 Create tests/test_cost_tracker_v2_3.py
```python
import pytest
from datetime import datetime
from claude_code_builder.models.cost_tracker import CostTracker

class TestCostTrackerV23:
    """Test v2.3.0 enhancements to CostTracker."""
    
    def test_claude_code_cost_tracking(self):
        """Test Claude Code cost tracking separately."""
        tracker = CostTracker()
        
        # Add Claude Code cost
        session_data = {
            "session_id": "test-123",
            "duration_ms": 5000,
            "num_turns": 3,
            "phase": "test_phase"
        }
        tracker.add_claude_code_cost(1.50, session_data)
        
        assert tracker.claude_code_cost == 1.50
        assert tracker.total_cost == 1.50
        assert len(tracker.claude_code_sessions) == 1
        assert tracker.claude_code_sessions[0]['cost'] == 1.50
        assert tracker.claude_code_sessions[0]['num_turns'] == 3
    
    def test_research_cost_separation(self):
        """Test research costs are tracked separately."""
        tracker = CostTracker()
        
        # Add research cost
        tracker.add_tokens("claude-3-opus-20240229", 1000, 500, "research_technology")
        
        assert tracker.research_cost > 0
        assert tracker.total_cost > 0
        assert "research_technology" in tracker.costs_by_phase
    
    def test_analysis_cost_calculation(self):
        """Test analysis cost is calculated correctly."""
        tracker = CostTracker()
        
        # Add different types of costs
        tracker.add_tokens("claude-3-opus-20240229", 1000, 500, "planning")  # Analysis
        tracker.add_tokens("claude-3-opus-20240229", 1000, 500, "research_security")  # Research
        tracker.add_claude_code_cost(2.00, {"phase": "execution"})  # Claude Code
        
        analysis_cost = tracker.analysis_cost
        assert analysis_cost == tracker.total_cost - tracker.claude_code_cost - tracker.research_cost
        assert analysis_cost > 0
    
    def test_model_breakdown(self):
        """Test model breakdown includes Claude Code."""
        tracker = CostTracker()
        
        # Add various costs
        tracker.add_tokens("claude-3-opus-20240229", 1000, 500, "test")
        tracker.add_claude_code_cost(3.00, {
            "session_id": "test-1",
            "num_turns": 5,
            "phase": "execution"
        })
        
        breakdown = tracker.get_model_breakdown()
        
        # Check Claude Code entry exists
        claude_code_entry = next(
            (item for item in breakdown if item['model'] == 'claude-code-execution'),
            None
        )
        assert claude_code_entry is not None
        assert claude_code_entry['sessions'] == 1
        assert claude_code_entry['avg_turns'] == 5.0
        assert claude_code_entry['cost'] == 3.00
    
    def test_backward_compatibility(self):
        """Test loading old format data."""
        old_data = {
            "total_input_tokens": 1000,
            "total_output_tokens": 500,
            "costs_by_model": {"claude-3-opus-20240229": 0.03},
            "costs_by_phase": {"test": 0.03}
        }
        
        tracker = CostTracker.from_dict(old_data)
        
        # Check new fields have defaults
        assert tracker.claude_code_cost == 0.0
        assert tracker.research_cost == 0.0
        assert tracker.claude_code_sessions == []
        
        # Check total_cost is calculated
        assert tracker.total_cost == 0.03
    
    def test_session_analytics(self):
        """Test Claude Code session analytics."""
        tracker = CostTracker()
        
        # Add multiple sessions
        for i in range(3):
            session_data = {
                "session_id": f"test-{i}",
                "duration_ms": (i + 1) * 1000,
                "num_turns": (i + 1) * 2,
                "phase": f"phase_{i}"
            }
            tracker.add_claude_code_cost(1.00 + i, session_data)
        
        summary = tracker.to_dict()
        
        assert summary['claude_code_sessions'] == 3
        assert summary['claude_code_cost'] == 6.00  # 1 + 2 + 3
        assert summary['avg_claude_code_cost'] == 2.00  # 6 / 3
        
        # Check model breakdown
        breakdown = tracker.get_model_breakdown()
        claude_entry = next(
            item for item in breakdown 
            if item['model'] == 'claude-code-execution'
        )
        assert claude_entry['avg_turns'] == 4.0  # (2 + 4 + 6) / 3
```

## Step 6: Integration Testing

### 6.1 Create tests/test_cost_integration.py
```python
import pytest
import asyncio
from claude_code_builder.models.cost_tracker import CostTracker
from claude_code_builder.execution.executor import ClaudeCodeExecutor
from claude_code_builder.research.manager import ResearchManager

class TestCostIntegration:
    """Integration tests for cost tracking."""
    
    @pytest.mark.asyncio
    async def test_full_cost_tracking(self):
        """Test cost tracking across all components."""
        cost_tracker = CostTracker()
        
        # Simulate research phase
        research_mgr = ResearchManager(cost_tracker=cost_tracker)
        # ... perform research ...
        
        # Simulate Claude Code execution
        executor = ClaudeCodeExecutor(cost_tracker=cost_tracker)
        # ... execute phase ...
        
        # Verify all costs are tracked
        summary = cost_tracker.to_dict()
        assert summary['total_cost'] > 0
        assert summary['claude_code_cost'] >= 0
        assert summary['research_cost'] >= 0
        assert summary['analysis_cost'] >= 0
        
        # Verify breakdown
        assert len(summary['model_breakdown']) > 0
```

## Step 7: Performance Validation

### 7.1 Create Benchmark Script
```python
# scripts/benchmark_cost_tracker.py
import time
import random
from claude_code_builder.models.cost_tracker import CostTracker

def benchmark_cost_tracker():
    """Benchmark CostTracker performance."""
    tracker = CostTracker()
    
    # Benchmark token additions
    start = time.time()
    for i in range(1000):
        tracker.add_tokens(
            "claude-3-opus-20240229",
            random.randint(100, 1000),
            random.randint(50, 500),
            f"phase_{i % 10}"
        )
    token_time = time.time() - start
    
    # Benchmark Claude Code sessions
    start = time.time()
    for i in range(100):
        session_data = {
            "session_id": f"session-{i}",
            "duration_ms": random.randint(1000, 10000),
            "num_turns": random.randint(1, 10),
            "phase": f"phase_{i % 10}"
        }
        tracker.add_claude_code_cost(random.uniform(0.1, 5.0), session_data)
    session_time = time.time() - start
    
    # Benchmark serialization
    start = time.time()
    for i in range(100):
        data = tracker.to_dict()
    serialize_time = time.time() - start
    
    print(f"Token additions (1000): {token_time:.3f}s")
    print(f"Session additions (100): {session_time:.3f}s")
    print(f"Serializations (100): {serialize_time:.3f}s")
    print(f"Memory usage: {len(str(tracker.to_dict())) / 1024:.1f} KB")

if __name__ == "__main__":
    benchmark_cost_tracker()
```

## Validation Checklist

### Pre-Implementation
- [ ] Backup existing cost_tracker.py
- [ ] Create feature branch
- [ ] Set up test environment

### Implementation
- [ ] Add new fields to CostTracker
- [ ] Implement add_claude_code_cost method
- [ ] Update add_tokens for research tracking
- [ ] Add analysis_cost property
- [ ] Implement get_model_breakdown
- [ ] Update to_dict/from_dict
- [ ] Enhance __rich__ display

### Integration
- [ ] Update ClaudeCodeExecutor
- [ ] Update ResearchManager
- [ ] Update UI displays
- [ ] Test data persistence

### Testing
- [ ] Run unit tests
- [ ] Run integration tests
- [ ] Benchmark performance
- [ ] Test backward compatibility
- [ ] Test with real builds

### Documentation
- [ ] Update API documentation
- [ ] Add usage examples
- [ ] Update changelog
- [ ] Create migration guide

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure all imports are added
   - Check for circular dependencies
   - Verify module paths

2. **Serialization Failures**
   - Check all fields are serializable
   - Test with empty/None values
   - Verify datetime handling

3. **Backward Compatibility**
   - Test with old saved states
   - Ensure defaults for new fields
   - Calculate missing values

4. **Performance Issues**
   - Profile with large datasets
   - Optimize data structures
   - Consider caching

## Success Criteria

1. **Functional**
   - Claude Code costs tracked separately ✓
   - Research costs identified correctly ✓
   - Session analytics working ✓
   - Model breakdown accurate ✓

2. **Performance**
   - No noticeable slowdown ✓
   - Memory usage < 10% increase ✓
   - Serialization fast ✓

3. **Compatibility**
   - Old data loads correctly ✓
   - Existing builds continue ✓
   - No API breaks ✓

## Next Steps

After completing Phase 1:
1. Monitor for 24 hours
2. Gather feedback
3. Fix any issues
4. Proceed to Phase 2 (Research Agents)