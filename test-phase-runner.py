#!/usr/bin/env python3
"""Test the phase runner directly to debug the error."""

import asyncio
import sys
from pathlib import Path

# Add the claude-code-builder to Python path
sys.path.insert(0, '/Users/nick/Desktop/ccb-mem0/claude-code-builder')

from claude_code_builder.models import Phase, BuildStatus
from claude_code_builder.execution.executor import ClaudeCodeExecutor
from claude_code_builder.execution.phase_runner import PhaseRunner
from claude_code_builder.models import CostTracker

async def test_phase_runner():
    """Test the phase runner with a simple phase."""
    
    # Create a simple test phase
    phase = Phase(
        id="test",
        name="Test Phase",
        description="Testing phase runner",
        tasks=[
            {"id": "task1", "description": "Create a test file", "type": "create_file"}
        ]
    )
    
    # Create executor and runner
    executor = ClaudeCodeExecutor(model="claude-opus-4-20250514", max_turns=5)
    cost_tracker = CostTracker()
    
    working_dir = Path("/Users/nick/Desktop/enhanced-claude-code/test-build/output")
    working_dir.mkdir(exist_ok=True)
    
    runner = PhaseRunner(
        executor=executor,
        cost_tracker=cost_tracker,
        working_dir=working_dir,
        enable_retries=False
    )
    
    # Test context
    context = {
        "spec": {"title": "Test Project"},
        "output_dir": str(working_dir)
    }
    
    try:
        # Run the phase
        success, result = await runner.run_phase(
            phase=phase,
            context=context,
            custom_instructions=["This is a test"],
            on_progress=lambda line: print(f"Progress: {line}")
        )
        
        print(f"\nSuccess: {success}")
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_phase_runner())