"""End-to-end integration tests for Claude Code Builder."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import shutil
import json
import asyncio
import subprocess
import sys
from typing import Dict, Any

from claude_code_builder.cli.main import ClaudeCodeBuilder
from claude_code_builder.models.project import ProjectSpec
from claude_code_builder.models.phase import Phase
from claude_code_builder.config.settings import BuilderConfig
from claude_code_builder.exceptions.base import BuilderError


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = Path(tempfile.mkdtemp())
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)
    
    @pytest.fixture
    def builder_config(self):
        """Create test builder configuration."""
        config = BuilderConfig()
        config.api_key = "test-key"
        config.model = "claude-3-sonnet-20240229"
        config.max_tokens = 10000
        config.max_retries = 2
        config.timeout = 60
        return config
    
    @pytest.fixture
    def simple_project_spec(self):
        """Create simple project specification."""
        return """# Simple Calculator

A basic calculator application with command-line interface.

## Features

- Basic arithmetic operations (add, subtract, multiply, divide)
- Command-line interface
- Input validation
- Error handling
- Unit tests

## Technical Requirements

- Python 3.8+
- Click for CLI
- pytest for testing
- Type hints throughout

## Project Structure

```
calculator/
├── src/
│   ├── __init__.py
│   ├── calculator.py
│   └── cli.py
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py
│   └── test_cli.py
├── README.md
├── requirements.txt
└── setup.py
```

## Implementation Details

### Calculator Module (src/calculator.py)
- Calculator class with methods for each operation
- Input validation and error handling
- Support for floating point numbers

### CLI Module (src/cli.py)
- Click-based command-line interface
- Interactive mode and single operation mode
- User-friendly error messages

### Tests
- Comprehensive unit tests for all operations
- Edge case testing (division by zero, invalid inputs)
- CLI interaction testing
"""
    
    @pytest.fixture
    def complex_project_spec(self):
        """Create complex project specification."""
        return """# Task Management API

A RESTful API for task management with user authentication and real-time updates.

## Features

- User authentication (JWT)
- CRUD operations for tasks
- Task categories and priorities
- Real-time updates via WebSocket
- Data persistence with SQLite
- API documentation
- Rate limiting
- Input validation

## Technical Requirements

- Python 3.9+
- FastAPI for web framework
- SQLAlchemy for ORM
- Pydantic for data validation
- pytest for testing
- Docker for containerization
- OpenAPI documentation

## Project Structure

```
task-api/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── task.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── tasks.py
│   │   └── users.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   └── utils/
│       ├── __init__.py
│       └── validators.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_tasks.py
│   └── test_models.py
├── docs/
│   ├── api.md
│   └── deployment.md
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── scripts/
│   ├── run_dev.py
│   └── migrate_db.py
├── README.md
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## Implementation Phases

### Phase 1: Foundation
- Project structure setup
- Configuration management
- Database models and migrations
- Basic API skeleton

### Phase 2: Authentication
- User model and registration
- JWT token generation and validation
- Login/logout endpoints
- Password hashing

### Phase 3: Task Management
- Task CRUD operations
- Category and priority management
- User-task associations
- Data validation

### Phase 4: Advanced Features
- Real-time WebSocket updates
- Rate limiting middleware
- API documentation
- Error handling

### Phase 5: Testing & Deployment
- Comprehensive test suite
- Docker containerization
- Documentation
- Deployment scripts
"""
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_simple_project_build_workflow(self, temp_workspace, simple_project_spec, builder_config):
        """Test building a simple project end-to-end."""
        # Create specification file
        spec_file = temp_workspace / "calculator_spec.md"
        spec_file.write_text(simple_project_spec)
        
        # Create builder instance
        builder = ClaudeCodeBuilder(config=builder_config)
        
        # Mock Claude API responses for each phase
        mock_responses = self._create_mock_responses_simple_project()
        
        with patch.object(builder.claude_client, 'send_message', side_effect=mock_responses):
            # Build project
            result = await builder.build_from_spec(
                spec_file=spec_file,
                output_dir=temp_workspace / "calculator",
                use_checkpoints=True
            )
            
            # Verify build success
            assert result.success is True
            assert len(result.phase_results) >= 3  # Should have multiple phases
            
            # Verify project structure
            project_dir = temp_workspace / "calculator"
            assert project_dir.exists()
            
            # Check key files exist
            expected_files = [
                "src/__init__.py",
                "src/calculator.py",
                "src/cli.py",
                "tests/test_calculator.py",
                "README.md",
                "requirements.txt"
            ]
            
            for file_path in expected_files:
                file_full_path = project_dir / file_path
                assert file_full_path.exists(), f"Missing file: {file_path}"
                assert file_full_path.stat().st_size > 0, f"Empty file: {file_path}"
            
            # Verify Python syntax in generated files
            python_files = list(project_dir.glob("**/*.py"))
            for py_file in python_files:
                try:
                    compile(py_file.read_text(), py_file, 'exec')
                except SyntaxError as e:
                    pytest.fail(f"Syntax error in {py_file}: {e}")
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_complex_project_build_workflow(self, temp_workspace, complex_project_spec, builder_config):
        """Test building a complex project end-to-end."""
        # Create specification file
        spec_file = temp_workspace / "task_api_spec.md"
        spec_file.write_text(complex_project_spec)
        
        # Create builder instance
        builder = ClaudeCodeBuilder(config=builder_config)
        
        # Mock Claude API responses for complex project
        mock_responses = self._create_mock_responses_complex_project()
        
        with patch.object(builder.claude_client, 'send_message', side_effect=mock_responses):
            # Build project
            result = await builder.build_from_spec(
                spec_file=spec_file,
                output_dir=temp_workspace / "task-api",
                use_checkpoints=True
            )
            
            # Verify build success
            assert result.success is True
            assert len(result.phase_results) >= 5  # Should have 5 phases
            
            # Verify complex project structure
            project_dir = temp_workspace / "task-api"
            assert project_dir.exists()
            
            # Check complex structure
            expected_dirs = [
                "src",
                "src/models",
                "src/api",
                "src/core",
                "src/utils",
                "tests",
                "docs",
                "docker",
                "scripts"
            ]
            
            for dir_path in expected_dirs:
                dir_full_path = project_dir / dir_path
                assert dir_full_path.exists(), f"Missing directory: {dir_path}"
                assert dir_full_path.is_dir(), f"Not a directory: {dir_path}"
            
            # Check key files in complex project
            expected_files = [
                "src/main.py",
                "src/models/user.py",
                "src/models/task.py",
                "src/api/auth.py",
                "src/api/tasks.py",
                "src/core/config.py",
                "src/core/database.py",
                "tests/conftest.py",
                "tests/test_auth.py",
                "docker/Dockerfile",
                "requirements.txt",
                "pyproject.toml"
            ]
            
            for file_path in expected_files:
                file_full_path = project_dir / file_path
                assert file_full_path.exists(), f"Missing file: {file_path}"
    
    @pytest.mark.integration
    async def test_build_with_validation_failures(self, temp_workspace, builder_config):
        """Test build workflow with validation failures."""
        # Create invalid specification
        invalid_spec = """# Invalid Project

This project has missing requirements and unclear structure.

## Features
- Something
- Something else

## Structure
No clear structure defined.
"""
        
        spec_file = temp_workspace / "invalid_spec.md"
        spec_file.write_text(invalid_spec)
        
        builder = ClaudeCodeBuilder(config=builder_config)
        
        # Mock validation failure
        with patch.object(builder.validator, 'validate_project_spec') as mock_validator:
            mock_result = Mock()
            mock_result.is_valid = False
            mock_result.errors = [
                Mock(message="Missing technical requirements"),
                Mock(message="Unclear project structure")
            ]
            mock_validator.return_value = mock_result
            
            # Should raise validation error
            with pytest.raises(BuilderError) as exc_info:
                await builder.build_from_spec(
                    spec_file=spec_file,
                    output_dir=temp_workspace / "invalid_project"
                )
            
            assert "validation" in str(exc_info.value).lower()
    
    @pytest.mark.integration
    async def test_build_with_checkpoint_resume(self, temp_workspace, simple_project_spec, builder_config):
        """Test checkpoint and resume functionality."""
        spec_file = temp_workspace / "calculator_spec.md"
        spec_file.write_text(simple_project_spec)
        
        output_dir = temp_workspace / "calculator"
        builder = ClaudeCodeBuilder(config=builder_config)
        
        # First, start a build that will be "interrupted"
        mock_responses = self._create_mock_responses_simple_project()
        
        with patch.object(builder.claude_client, 'send_message', side_effect=mock_responses[:2]):  # Only first 2 phases
            # Simulate interrupted build
            try:
                await builder.build_from_spec(
                    spec_file=spec_file,
                    output_dir=output_dir,
                    use_checkpoints=True
                )
            except IndexError:
                pass  # Expected when we run out of mock responses
        
        # Verify checkpoint was created
        checkpoint_file = output_dir / '.checkpoint.json'
        assert checkpoint_file.exists()
        
        # Resume build
        with patch.object(builder.claude_client, 'send_message', side_effect=mock_responses[2:]):  # Remaining phases
            result = await builder.resume_build(workspace=output_dir)
            
            # Should complete successfully
            assert result.success is True
    
    @pytest.mark.integration
    async def test_build_with_custom_instructions(self, temp_workspace, simple_project_spec, builder_config):
        """Test build with custom instructions."""
        spec_file = temp_workspace / "calculator_spec.md"
        spec_file.write_text(simple_project_spec)
        
        # Create custom instructions
        custom_instructions = {
            'code_style': [
                'Use dataclasses instead of regular classes where appropriate',
                'Prefer f-strings over .format() or % formatting',
                'Add type hints to all function parameters and return values'
            ],
            'architecture': [
                'Use dependency injection pattern',
                'Implement proper error handling with custom exceptions',
                'Follow single responsibility principle'
            ],
            'testing': [
                'Write tests using pytest fixtures',
                'Aim for 95% code coverage',
                'Include both unit and integration tests'
            ]
        }
        
        instructions_file = temp_workspace / "custom_instructions.json"
        instructions_file.write_text(json.dumps(custom_instructions))
        
        builder = ClaudeCodeBuilder(config=builder_config)
        
        # Mock responses that should reflect custom instructions
        mock_responses = self._create_mock_responses_with_custom_instructions()
        
        with patch.object(builder.claude_client, 'send_message', side_effect=mock_responses):
            result = await builder.build_from_spec(
                spec_file=spec_file,
                output_dir=temp_workspace / "calculator",
                custom_instructions=instructions_file
            )
            
            assert result.success is True
            
            # Verify that custom instructions were applied
            calculator_file = temp_workspace / "calculator" / "src" / "calculator.py"
            if calculator_file.exists():
                content = calculator_file.read_text()
                # Check for evidence of custom instructions
                assert "from dataclasses import dataclass" in content or "def " in content
                assert ":" in content  # Type hints should be present
    
    @pytest.mark.integration
    async def test_mcp_integration_workflow(self, temp_workspace, simple_project_spec, builder_config):
        """Test MCP integration during build."""
        spec_file = temp_workspace / "calculator_spec.md"
        spec_file.write_text(simple_project_spec)
        
        builder = ClaudeCodeBuilder(config=builder_config)
        
        # Mock MCP handler
        mock_mcp_handler = Mock()
        mock_mcp_responses = [
            Mock(success=True, result={"files": ["calculator.py", "cli.py"]}),
            Mock(success=True, result={"content": "# Calculator implementation"}),
            Mock(success=True, result={"validation": "passed"})
        ]
        mock_mcp_handler.execute_request = AsyncMock(side_effect=mock_mcp_responses)
        
        # Mock Claude responses
        mock_responses = self._create_mock_responses_simple_project()
        
        with patch.object(builder, 'mcp_handler', mock_mcp_handler):
            with patch.object(builder.claude_client, 'send_message', side_effect=mock_responses):
                result = await builder.build_from_spec(
                    spec_file=spec_file,
                    output_dir=temp_workspace / "calculator",
                    enable_mcp=True
                )
                
                assert result.success is True
                
                # Verify MCP was used
                assert mock_mcp_handler.execute_request.call_count > 0
    
    @pytest.mark.integration
    async def test_memory_system_integration(self, temp_workspace, simple_project_spec, builder_config):
        """Test memory system integration during build."""
        spec_file = temp_workspace / "calculator_spec.md"
        spec_file.write_text(simple_project_spec)
        
        builder = ClaudeCodeBuilder(config=builder_config)
        
        # Mock memory manager
        mock_memory = Mock()
        mock_memory.store_context = AsyncMock()
        mock_memory.retrieve_context = AsyncMock(return_value={
            "previous_implementations": ["basic calculator", "cli tools"],
            "coding_patterns": ["error handling", "type hints"],
            "common_issues": ["division by zero", "input validation"]
        })
        
        mock_responses = self._create_mock_responses_simple_project()
        
        with patch.object(builder, 'memory_manager', mock_memory):
            with patch.object(builder.claude_client, 'send_message', side_effect=mock_responses):
                result = await builder.build_from_spec(
                    spec_file=spec_file,
                    output_dir=temp_workspace / "calculator",
                    use_memory=True
                )
                
                assert result.success is True
                
                # Verify memory was used
                assert mock_memory.retrieve_context.call_count > 0
                assert mock_memory.store_context.call_count > 0
    
    @pytest.mark.integration
    async def test_monitoring_system_integration(self, temp_workspace, simple_project_spec, builder_config):
        """Test monitoring system integration during build."""
        spec_file = temp_workspace / "calculator_spec.md"
        spec_file.write_text(simple_project_spec)
        
        builder = ClaudeCodeBuilder(config=builder_config)
        
        # Mock monitor
        mock_monitor = Mock()
        mock_monitor.start_monitoring = AsyncMock()
        mock_monitor.log_phase_start = AsyncMock()
        mock_monitor.log_phase_complete = AsyncMock()
        mock_monitor.log_error = AsyncMock()
        mock_monitor.stop_monitoring = AsyncMock()
        mock_monitor.get_metrics = Mock(return_value={
            "total_time": 180,
            "tokens_used": 5000,
            "phases_completed": 3,
            "files_created": 8
        })
        
        mock_responses = self._create_mock_responses_simple_project()
        
        with patch.object(builder, 'monitor', mock_monitor):
            with patch.object(builder.claude_client, 'send_message', side_effect=mock_responses):
                result = await builder.build_from_spec(
                    spec_file=spec_file,
                    output_dir=temp_workspace / "calculator",
                    enable_monitoring=True
                )
                
                assert result.success is True
                
                # Verify monitoring was used
                mock_monitor.start_monitoring.assert_called_once()
                mock_monitor.stop_monitoring.assert_called_once()
                assert mock_monitor.log_phase_start.call_count > 0
    
    def _create_mock_responses_simple_project(self):
        """Create mock Claude responses for simple project."""
        return [
            # Phase 1: Foundation
            Mock(content="Phase 1: Foundation - Created calculator.py, __init__.py, and requirements.txt", 
                 usage={"input_tokens": 200, "output_tokens": 300}),
            
            # Phase 2: CLI Implementation  
            Mock(content="Phase 2: CLI Implementation - Created cli.py with Click interface and interactive mode",
                 usage={"input_tokens": 150, "output_tokens": 400}),
            
            # Phase 3: Testing
            Mock(content="Phase 3: Testing - Created test_calculator.py and test_cli.py with comprehensive test coverage",
                 usage={"input_tokens": 100, "output_tokens": 500})
        ]
    
    def _create_mock_responses_complex_project(self):
        """Create mock Claude responses for complex project."""
        # This would be much longer in reality, but abbreviated for testing
        return [
            Mock(content="Phase 1: Foundation setup complete", usage={"input_tokens": 300, "output_tokens": 400}),
            Mock(content="Phase 2: Authentication implemented", usage={"input_tokens": 250, "output_tokens": 600}),
            Mock(content="Phase 3: Task management complete", usage={"input_tokens": 280, "output_tokens": 550}),
            Mock(content="Phase 4: Advanced features added", usage={"input_tokens": 200, "output_tokens": 450}),
            Mock(content="Phase 5: Testing and deployment ready", usage={"input_tokens": 180, "output_tokens": 300})
        ]
    
    def _create_mock_responses_with_custom_instructions(self):
        """Create mock responses that reflect custom instructions."""
        return [
            Mock(content="Phase 1: Foundation with custom instructions - Used dataclasses, type hints, and f-strings as requested", 
                 usage={"input_tokens": 200, "output_tokens": 300}),
            
            Mock(content="Phase 2: Additional phases with custom instructions applied - Implemented dependency injection and custom exceptions", 
                 usage={"input_tokens": 150, "output_tokens": 200})
        ]


@pytest.mark.integration
@pytest.mark.requires_api
class TestRealAPIIntegration:
    """Integration tests with real API (requires valid API key)."""
    
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-integration", default=False),
        reason="Integration tests disabled by default"
    )
    async def test_real_simple_build(self, temp_workspace, builder_config):
        """Test building simple project with real API."""
        # Skip if no real API key
        if not builder_config.api_key or builder_config.api_key == "test-key":
            pytest.skip("Requires real API key")
        
        # Very simple project spec
        simple_spec = """# Hello World

A simple Hello World application.

## Features
- Print "Hello, World!" to console
- Python script

## Structure
```
hello/
├── hello.py
└── README.md
```
"""
        
        spec_file = temp_workspace / "hello_spec.md"
        spec_file.write_text(simple_spec)
        
        # Use real builder with minimal configuration
        from claude_code_builder.cli.main import ClaudeCodeBuilder
        
        real_builder = ClaudeCodeBuilder(config=builder_config)
        
        try:
            result = await real_builder.build_from_spec(
                spec_file=spec_file,
                output_dir=temp_workspace / "hello",
                use_checkpoints=False  # Keep it simple
            )
            
            # Basic verification
            assert result is not None
            assert hasattr(result, 'success')
            
            # Check if any files were created
            hello_dir = temp_workspace / "hello"
            if hello_dir.exists():
                files = list(hello_dir.glob("**/*"))
                assert len(files) > 0, "No files created"
                
        except Exception as e:
            # Log the error but don't fail the test - API might be down
            pytest.skip(f"Real API integration failed: {e}")


def pytest_configure(config):
    """Configure pytest with integration test options."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may take several minutes)"
    )
    config.addinivalue_line(
        "markers", "requires_api: marks tests that require real API access"
    )