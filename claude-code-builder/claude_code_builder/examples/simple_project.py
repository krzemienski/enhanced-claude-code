"""Simple project example for Claude Code Builder."""
from pathlib import Path
from typing import Dict, Any


def get_simple_calculator_spec() -> str:
    """Get calculator project specification.
    
    Returns:
        Markdown specification for a calculator project
    """
    return """# Calculator CLI

A simple command-line calculator application.

## Features

- Basic arithmetic operations (addition, subtraction, multiplication, division)
- Support for decimal numbers
- Error handling for invalid inputs and division by zero
- Interactive mode for continuous calculations
- History of recent calculations
- Clear and help commands

## Technical Requirements

- Language: Python 3.8+
- CLI Framework: Click
- No external dependencies for core functionality
- Comprehensive unit tests with pytest
- Type hints for all functions
- Proper error handling and user feedback

## Command Structure

```bash
# Single calculation
calculator add 5 3
calculator multiply 2.5 4
calculator divide 10 2

# Interactive mode
calculator interactive

# Show history
calculator history

# Clear history
calculator clear
```

## Project Structure

```
calculator/
├── calculator/
│   ├── __init__.py
│   ├── cli.py          # CLI entry point
│   ├── operations.py   # Mathematical operations
│   ├── history.py      # Calculation history
│   └── utils.py        # Helper functions
├── tests/
│   ├── test_operations.py
│   ├── test_history.py
│   └── test_cli.py
├── README.md
├── setup.py
└── requirements.txt
```

## Error Handling

- Graceful handling of invalid inputs
- Clear error messages for users
- Proper exit codes for scripting
- Validation of numerical inputs

## Testing Requirements

- Unit tests for all operations
- CLI command tests
- Edge case coverage
- Integration tests for interactive mode
"""


def get_todo_app_spec() -> str:
    """Get todo application specification.
    
    Returns:
        Markdown specification for a todo app
    """
    return """# Todo List CLI

A feature-rich command-line todo list manager.

## Features

- Add, update, and delete tasks
- Mark tasks as complete/incomplete
- Task priorities (high, medium, low)
- Due dates with reminders
- Categories for organization
- Search and filter tasks
- Export to various formats (JSON, CSV, Markdown)
- Data persistence with local storage

## Technical Requirements

- Language: Python 3.8+
- CLI Framework: Click
- Database: SQLite for local storage
- Rich library for terminal formatting
- Pydantic for data validation
- pytest for testing

## Commands

```bash
# Task management
todo add "Complete project documentation" --priority high --due tomorrow
todo list --filter priority:high
todo complete 1
todo update 2 --priority medium
todo delete 3

# Categories
todo add "Buy groceries" --category personal
todo list --category work

# Search
todo search "documentation"

# Export
todo export --format json > tasks.json
todo export --format markdown > tasks.md
```

## Data Model

### Task
- id: integer (auto-increment)
- title: string (required)
- description: string (optional)
- priority: enum (high, medium, low)
- category: string (optional)
- due_date: datetime (optional)
- completed: boolean
- created_at: datetime
- updated_at: datetime

## Configuration

Support for configuration file:
```yaml
# ~/.todo/config.yaml
default_priority: medium
date_format: "%Y-%m-%d"
colors:
  high: red
  medium: yellow
  low: green
```

## Testing

- Unit tests for all CRUD operations
- CLI command testing
- Database transaction tests
- Export format validation
"""


def get_file_organizer_spec() -> str:
    """Get file organizer specification.
    
    Returns:
        Markdown specification for file organizer
    """
    return """# File Organizer

Automatically organize files in directories based on rules.

## Features

- Organize files by type (documents, images, videos, etc.)
- Organize by date (creation/modification)
- Custom organization rules
- Dry run mode to preview changes
- Undo functionality
- Watch mode for automatic organization
- Exclude patterns support

## Technical Requirements

- Language: Python 3.8+
- Path handling: pathlib
- Configuration: YAML
- Logging: Python logging module
- Testing: pytest

## Usage

```bash
# Organize by file type
file-organizer organize ~/Downloads --by type

# Organize by date
file-organizer organize ~/Photos --by date --format "YYYY/MM"

# Dry run
file-organizer organize ~/Desktop --dry-run

# Use custom rules
file-organizer organize ~/Documents --rules my-rules.yaml

# Watch directory
file-organizer watch ~/Downloads --rules auto-rules.yaml
```

## Organization Rules

```yaml
# rules.yaml
rules:
  - name: "Documents"
    patterns: ["*.pdf", "*.doc", "*.docx", "*.txt"]
    destination: "Documents"
    
  - name: "Images"
    patterns: ["*.jpg", "*.png", "*.gif", "*.svg"]
    destination: "Images/{year}/{month}"
    
  - name: "Source Code"
    patterns: ["*.py", "*.js", "*.java", "*.cpp"]
    destination: "Code/{extension}"
    
  - name: "Archives"
    patterns: ["*.zip", "*.tar", "*.gz", "*.rar"]
    destination: "Archives"
    
exclude:
  - "*.tmp"
  - "~*"
  - ".DS_Store"
```

## Safety Features

- No files are deleted, only moved
- Automatic backup before organization
- Detailed logging of all operations
- Conflict resolution (duplicate names)
- Preserve file attributes and timestamps
"""


def create_simple_example(output_dir: Path) -> None:
    """Create simple example files.
    
    Args:
        output_dir: Output directory for examples
    """
    examples_dir = output_dir / "simple"
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculator example
    calc_spec = examples_dir / "calculator.md"
    calc_spec.write_text(get_simple_calculator_spec())
    
    # Build script for calculator
    calc_build = examples_dir / "build_calculator.sh"
    calc_build.write_text("""#!/bin/bash
# Build calculator example

set -e

echo "Building Calculator CLI example..."
claude-code-builder build calculator.md --output-dir ./calculator-output

echo "Build complete! To test:"
echo "  cd calculator-output"
echo "  pip install -e ."
echo "  calculator --help"
""")
    calc_build.chmod(0o755)
    
    # Todo app example
    todo_spec = examples_dir / "todo_app.md"
    todo_spec.write_text(get_todo_app_spec())
    
    # File organizer example
    organizer_spec = examples_dir / "file_organizer.md"
    organizer_spec.write_text(get_file_organizer_spec())
    
    # README for simple examples
    readme = examples_dir / "README.md"
    readme.write_text("""# Simple Project Examples

This directory contains simple, self-contained project examples to get started with Claude Code Builder.

## Examples

### Calculator CLI (`calculator.md`)
A basic command-line calculator demonstrating:
- CLI argument parsing
- Error handling
- Unit testing
- Clean code structure

**Build**: `./build_calculator.sh` or `claude-code-builder build calculator.md`

### Todo App (`todo_app.md`)
A feature-rich todo list manager showing:
- Database integration (SQLite)
- CRUD operations
- Rich terminal output
- Data export functionality

**Build**: `claude-code-builder build todo_app.md --output-dir ./todo-output`

### File Organizer (`file_organizer.md`)
An automatic file organization tool featuring:
- Rule-based file organization
- Configuration management
- Safety features (dry-run, undo)
- Watch mode for automation

**Build**: `claude-code-builder build file_organizer.md --output-dir ./organizer-output`

## Getting Started

1. Choose an example that interests you
2. Review the specification file (`.md`)
3. Build the project:
   ```bash
   claude-code-builder build <example>.md --output-dir ./<name>-output
   ```
4. Navigate to the output directory and follow the README

## Customization

Feel free to modify any specification to add features or change requirements. Some ideas:

- **Calculator**: Add scientific functions, GUI interface, or expression parsing
- **Todo App**: Add collaboration features, web API, or mobile sync
- **File Organizer**: Add cloud storage support, duplicate detection, or image recognition

## Tips

- Use `--dry-run` flag to see the build plan without executing
- Add `--debug` for detailed output during builds
- Create a `.claude-instructions.yaml` file for custom code style preferences
""")


class SimpleProjectExample:
    """Simple project example demonstrations."""
    
    @staticmethod
    def get_examples() -> Dict[str, Dict[str, Any]]:
        """Get all simple project examples.
        
        Returns:
            Dictionary of example configurations
        """
        return {
            'calculator': {
                'name': 'Calculator CLI',
                'description': 'Basic command-line calculator',
                'difficulty': 'beginner',
                'duration': '10 minutes',
                'spec': get_simple_calculator_spec()
            },
            'todo_app': {
                'name': 'Todo List Manager',
                'description': 'Feature-rich todo application',
                'difficulty': 'beginner',
                'duration': '15 minutes',
                'spec': get_todo_app_spec()
            },
            'file_organizer': {
                'name': 'File Organizer',
                'description': 'Automatic file organization tool',
                'difficulty': 'intermediate',
                'duration': '20 minutes',
                'spec': get_file_organizer_spec()
            }
        }
    
    @staticmethod
    def create_hello_world() -> str:
        """Create the simplest possible example.
        
        Returns:
            Hello world specification
        """
        return """# Hello World

The simplest possible project to test your setup.

## Features

- Print "Hello, World!" to the console
- Accept an optional name parameter
- Include a simple test

## Requirements

- Python 3.8+
- No external dependencies

## Usage

```bash
hello
hello --name Alice
```

## Expected Output

```
Hello, World!
Hello, Alice!
```
"""
    
    @staticmethod
    def create_with_instructions(spec: str) -> Dict[str, Any]:
        """Create example with custom instructions.
        
        Args:
            spec: Base specification
            
        Returns:
            Specification with instructions
        """
        return {
            'specification': spec,
            'instructions': {
                'code_style': [
                    'Use type hints for all functions',
                    'Follow PEP 8 strictly',
                    'Add docstrings to all public functions'
                ],
                'testing': [
                    'Include unit tests for all functions',
                    'Aim for 90% code coverage',
                    'Use pytest fixtures'
                ],
                'documentation': [
                    'Include comprehensive README',
                    'Add usage examples',
                    'Document all CLI commands'
                ]
            }
        }


# Example usage functions
def generate_all_simple_examples(output_dir: Path) -> None:
    """Generate all simple examples.
    
    Args:
        output_dir: Output directory
    """
    create_simple_example(output_dir)
    
    # Create hello world
    hello_dir = output_dir / "minimal"
    hello_dir.mkdir(parents=True, exist_ok=True)
    
    hello_spec = hello_dir / "hello_world.md"
    hello_spec.write_text(SimpleProjectExample.create_hello_world())


if __name__ == "__main__":
    # Example of generating examples
    examples_dir = Path("generated_examples")
    generate_all_simple_examples(examples_dir)
    print(f"Examples generated in: {examples_dir}")