"""Pytest configuration and fixtures for Claude Code Builder tests."""
import pytest
from pathlib import Path
import tempfile
import shutil
from typing import Generator, Dict, Any
import yaml
import json

from claude_code_builder.models.project import ProjectSpec
from claude_code_builder.models.phase import Phase
from claude_code_builder.config.settings import BuilderConfig
from claude_code_builder.memory.store import PersistentMemoryStore


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing.
    
    Yields:
        Temporary directory path
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_project_spec() -> ProjectSpec:
    """Create a sample project specification.
    
    Returns:
        Sample project spec
    """
    spec = ProjectSpec(
        name="test-project",
        description="A test project for unit testing",
        version="1.0.0"
    )
    
    # Add phases
    phase1 = Phase(
        name="Foundation",
        description="Setup project foundation",
        deliverables=["src/__init__.py", "README.md", "requirements.txt"]
    )
    phase2 = Phase(
        name="Core Implementation",
        description="Implement core functionality",
        deliverables=["src/main.py", "src/utils.py", "tests/test_main.py"]
    )
    
    spec.phases = [phase1, phase2]
    spec.requirements = ["Python 3.8+", "pytest", "Click"]
    
    return spec


@pytest.fixture
def sample_project_markdown() -> str:
    """Create sample project specification in markdown.
    
    Returns:
        Markdown specification
    """
    return """# Test Project

A simple test project for unit testing.

## Features

- Command-line interface
- Basic functionality
- Unit tests

## Technical Requirements

- Python 3.8+
- Click for CLI
- pytest for testing

## Project Structure

```
test-project/
├── src/
│   ├── __init__.py
│   └── main.py
├── tests/
│   └── test_main.py
├── README.md
└── requirements.txt
```
"""


@pytest.fixture
def builder_config() -> BuilderConfig:
    """Create a test builder configuration.
    
    Returns:
        Test configuration
    """
    config = BuilderConfig()
    config.api_key = "test-key"
    config.model = "claude-3-sonnet-20240229"
    config.max_tokens = 10000
    config.max_retries = 1
    config.timeout = 30
    config.cache_enabled = False  # Disable cache for tests
    config.telemetry_enabled = False
    
    return config


@pytest.fixture
def mock_api_response() -> Dict[str, Any]:
    """Create a mock API response.
    
    Returns:
        Mock response data
    """
    return {
        "id": "msg_test123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "```python\n# Test code\nprint('Hello, World!')\n```"
            }
        ],
        "model": "claude-3-sonnet-20240229",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50
        }
    }


@pytest.fixture
def memory_manager(temp_dir: Path) -> PersistentMemoryStore:
    """Create a test memory manager.
    
    Args:
        temp_dir: Temporary directory
        
    Returns:
        Memory manager instance
    """
    db_path = temp_dir / "test_memory.db"
    manager = PersistentMemoryStore(db_path=str(db_path))
    return manager


@pytest.fixture
def sample_phase() -> Phase:
    """Create a sample phase.
    
    Returns:
        Sample phase
    """
    return Phase(
        name="Test Phase",
        description="A phase for testing",
        deliverables=["file1.py", "file2.py", "tests/test_file1.py"],
        validation_rules=["All files must have docstrings", "Tests must pass"],
        success_criteria=["Code compiles", "Tests pass", "Documentation complete"]
    )


@pytest.fixture
def custom_instructions() -> Dict[str, Any]:
    """Create sample custom instructions.
    
    Returns:
        Custom instructions dictionary
    """
    return {
        "code_style": [
            "Use type hints for all functions",
            "Follow PEP 8 strictly",
            "Add comprehensive docstrings"
        ],
        "architecture": [
            "Use clean architecture principles",
            "Separate business logic from infrastructure",
            "Implement proper error handling"
        ],
        "testing": [
            "Write unit tests for all public functions",
            "Aim for 90% code coverage",
            "Use pytest fixtures"
        ]
    }


@pytest.fixture
def mcp_server_config() -> Dict[str, Any]:
    """Create MCP server configuration.
    
    Returns:
        MCP server config
    """
    return {
        "filesystem": {
            "enabled": True,
            "path": "/usr/local/bin/mcp-filesystem",
            "args": ["--allow-write"]
        },
        "github": {
            "enabled": False,
            "token": "test-token"
        }
    }


@pytest.fixture
def plugin_config() -> Dict[str, Any]:
    """Create plugin configuration.
    
    Returns:
        Plugin config
    """
    return {
        "basic_plugin": {
            "enabled": True,
            "debug": True
        },
        "test_runner": {
            "enabled": True,
            "coverage_threshold": 80
        }
    }


@pytest.fixture
def test_files(temp_dir: Path) -> Dict[str, Path]:
    """Create test files in temporary directory.
    
    Args:
        temp_dir: Temporary directory
        
    Returns:
        Dictionary of test file paths
    """
    files = {}
    
    # Python file
    py_file = temp_dir / "test.py"
    py_file.write_text("""
def hello(name: str) -> str:
    \"\"\"Say hello to someone.
    
    Args:
        name: Name to greet
        
    Returns:
        Greeting message
    \"\"\"
    return f"Hello, {name}!"
""")
    files['python'] = py_file
    
    # JavaScript file
    js_file = temp_dir / "test.js"
    js_file.write_text("""
function hello(name) {
    return `Hello, ${name}!`;
}

module.exports = { hello };
""")
    files['javascript'] = js_file
    
    # Markdown file
    md_file = temp_dir / "README.md"
    md_file.write_text("""# Test Project

This is a test project.

## Features

- Testing
- More testing
""")
    files['markdown'] = md_file
    
    # Config file
    config_file = temp_dir / "config.yaml"
    config_file.write_text("""
api_key: test-key
model: claude-3-sonnet
max_tokens: 10000

features:
  - testing
  - validation
""")
    files['config'] = config_file
    
    return files


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests.
    
    This ensures tests don't interfere with each other.
    """
    # Reset any singleton instances here
    # For example, if you have a global config or logger
    yield
    # Cleanup after test


@pytest.fixture
def mock_claude_response():
    """Mock Claude API response for testing.
    
    Returns:
        Mock response callable
    """
    def _mock_response(content: str, tokens_used: int = 100):
        return {
            "content": content,
            "usage": {
                "input_tokens": tokens_used,
                "output_tokens": tokens_used // 2
            },
            "model": "claude-3-sonnet-20240229"
        }
    
    return _mock_response


# Markers for different test categories
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "requires_api: marks tests that require API access"
    )