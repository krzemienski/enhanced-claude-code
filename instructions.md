# Claude Code Builder v2.3.0 - Custom Build Instructions

## CRITICAL IMPLEMENTATION REQUIREMENTS

### 1. **MODULAR ARCHITECTURE**
- Create a proper Python package structure, NOT a single file
- Each module should have a single responsibility
- Use proper imports between modules
- Follow clean architecture principles
- Maintain clear boundaries between layers

### 2. **NO MOCK IMPLEMENTATIONS**
- Every function, method, and class must be fully implemented
- No placeholder code, TODOs, or "pass" statements
- All features must be production-ready and functional
- Test with real data and actual use cases

### 3. **Package Structure**
```
claude_code_builder/
├── __init__.py          # Package initialization, version
├── __main__.py          # Entry point for python -m
├── cli.py              # Click CLI application
├── main.py             # Main ClaudeCodeBuilder class
├── models/             # Data models and types
├── mcp/                # MCP server management
├── research/           # AI research system
├── execution/          # Claude Code execution
├── ui/                 # Rich UI components
├── validation/         # Project validation
├── utils/              # Utilities and helpers
└── instructions/       # Custom instructions
```

### 4. **Python Best Practices**
- Use Python 3.8+ features appropriately
- Type hints for ALL function signatures and class attributes
- Comprehensive docstrings for all modules, classes, and public methods
- Follow PEP 8 style guidelines strictly
- Use async/await for I/O operations where beneficial
- Proper module-level __all__ exports

### 5. **Clean Code Principles**
- Single Responsibility Principle for each module
- Dependency Injection where appropriate
- Clear interfaces between modules
- Avoid circular imports
- Use abstract base classes for extensibility

### 6. **Rich Library Integration**
- Create a central console instance in ui/console.py
- Use Rich components consistently throughout
- Implement custom Rich renderables where needed
- Apply consistent styling and themes
- Create beautiful, colored terminal experiences

### 7. **Error Handling Standards**
- Define custom exceptions in utils/exceptions.py
- Use exception hierarchy for different error types
- Implement error context managers
- User-friendly error messages with actionable suggestions
- Proper error propagation between modules

### 8. **Import Organization**
```python
# Standard library imports
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
import click
from rich.console import Console
from anthropic import Anthropic

# Local imports
from claude_code_builder.models import BuildStatus, Phase
from claude_code_builder.ui import RichConsole
from claude_code_builder.utils import constants
```

### 9. **Module-Specific Requirements**

#### models/ Package
- Each model in its own file
- Use @dataclass with field validation
- Implement to_dict() and from_dict() methods
- Add __rich__ methods for Rich rendering
- Include proper type annotations

#### mcp/ Package
- server_registry.py contains MCP_SERVER_REGISTRY constant
- recommendation_engine.py implements analysis logic
- config_generator.py handles JSON generation
- Clear separation of concerns

#### research/ Package
- base_agent.py defines abstract ResearchAgent
- agents.py implements all 7 specialized agents
- manager.py coordinates multi-agent research
- Use actual Anthropic SDK

#### execution/ Package
- executor.py builds and runs Claude commands
- streaming.py parses JSON stream events
- phase_runner.py orchestrates phase execution
- Proper subprocess management

#### ui/ Package
- console.py provides singleton Console instance
- progress.py manages all progress tracking
- display.py creates panels, tables, layouts
- Consistent styling throughout

#### validation/ Package
- validator.py is the main validation orchestrator
- checks.py implements individual validation checks
- Reports validation results clearly
- Integrates with test runners

### 10. **Configuration Management**
- Use utils/constants.py for all constants
- Environment variables for sensitive data
- Configuration precedence (CLI > env > defaults)
- Validate all configuration inputs

### 11. **Testing Philosophy**
- Create functional tests in tests/functional/
- Test actual module integration
- Use pytest for test runner
- Include fixtures for common setups
- Test error scenarios

### 12. **Documentation Standards**
- Module-level docstrings explaining purpose
- Class docstrings with usage examples
- Method docstrings with parameter descriptions
- Type hints serve as documentation
- README with architecture overview

### 13. **Entry Points**
```python
# setup.py
entry_points={
    'console_scripts': [
        'claude-code-builder=claude_code_builder.cli:main',
    ],
}
```

### 14. **Dependency Management**
- Minimal dependencies in __init__.py
- Lazy imports where beneficial
- Clear dependency graph
- No circular dependencies
- Optional dependencies handled gracefully

### 15. **Logging Strategy**
- Use Python's logging module
- Configure in main.py
- Module-specific loggers
- Appropriate log levels
- Rich handler for formatted output

## SPECIFIC MODULE IMPLEMENTATIONS

### claude_code_builder/__init__.py
```python
"""Claude Code Builder - Autonomous project builder using Claude Code SDK."""
__version__ = "2.3.0"
__author__ = "Claude Code Builder Team"

from claude_code_builder.main import ClaudeCodeBuilder

__all__ = ["ClaudeCodeBuilder", "__version__"]
```

### claude_code_builder/cli.py
```python
import click
from claude_code_builder.main import ClaudeCodeBuilder
from claude_code_builder.ui import console

@click.command()
@click.argument('spec_file', type=click.Path(exists=True))
@click.option('--output-dir', '-o', default='./output')
# ... all other options
def main(spec_file, output_dir, **kwargs):
    """Build projects autonomously using Claude Code SDK."""
    builder = ClaudeCodeBuilder(spec_file, output_dir, **kwargs)
    builder.run()

if __name__ == '__main__':
    main()
```

### Module Interfaces

#### models/phase.py
```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from claude_code_builder.models.build_status import BuildStatus

@dataclass
class Phase:
    """Represents a build phase."""
    id: str
    name: str
    description: str
    tasks: List[str]
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    status: BuildStatus = BuildStatus.PENDING
    
    def validate(self) -> bool:
        """Validate phase configuration."""
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        
    def __rich__(self) -> Panel:
        """Rich representation for display."""
```

#### execution/executor.py
```python
class ClaudeCodeExecutor:
    """Executes Claude Code CLI commands."""
    
    def __init__(self, model: str, max_turns: int):
        self.model = model
        self.max_turns = max_turns
        
    async def execute_phase(self, phase: Phase, 
                          prompt: str,
                          mcp_config: Optional[Path] = None) -> ExecutionResult:
        """Execute a build phase."""
```

### Quality Checklist

Before completing each module:
- [ ] Module has clear single responsibility
- [ ] All functions are fully implemented
- [ ] Proper imports and exports
- [ ] Type hints complete
- [ ] Docstrings present
- [ ] Error handling comprehensive
- [ ] Unit tests written (where applicable)
- [ ] Integration with other modules tested
- [ ] No circular dependencies
- [ ] Follows PEP 8

## Phase-Specific Module Creation

### Phase 1: Foundation
- Set up package structure
- Create all directories
- Initialize all __init__.py files
- Create setup.py with proper configuration

### Phase 2: Models
- One file per model
- Consistent structure
- Rich formatting support
- Validation methods

### Phase 3-9: Feature Modules
- Clear module boundaries
- Well-defined interfaces
- Consistent patterns
- Proper error handling

### Phase 10: Integration
- Wire everything together in main.py
- Ensure all imports work
- Test module interactions
- Verify CLI functionality

### Phase 11: Testing
- Test each module independently
- Test integration points
- Test error scenarios
- Performance testing

### Phase 12: Polish
- Final documentation
- Code cleanup
- Consistency check
- Release preparation

Remember: This is a professional Python package that will be distributed and used by others. Quality, modularity, and maintainability are paramount!