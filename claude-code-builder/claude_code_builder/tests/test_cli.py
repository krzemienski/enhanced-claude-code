"""Tests for CLI interface."""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import tempfile
import shutil
import json
import sys
from io import StringIO
from click.testing import CliRunner

from claude_code_builder.cli.main import cli, build, init, validate, resume, status
from claude_code_builder.cli.config import ConfigManager
from claude_code_builder.cli.output import OutputFormatter, ProgressTracker
from claude_code_builder.config.settings import BuilderConfig
from claude_code_builder.models.project import ProjectSpec


class TestCLIMain:
    """Test suite for main CLI commands."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = Path(tempfile.mkdtemp())
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)
    
    @pytest.fixture
    def sample_spec_file(self, temp_workspace):
        """Create sample specification file."""
        spec_file = temp_workspace / "project_spec.md"
        spec_file.write_text("""# Test Project

A simple test project for CLI testing.

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
""")
        return spec_file
    
    def test_cli_help(self, cli_runner):
        """Test CLI help command."""
        result = cli_runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'Claude Code Builder' in result.output
        assert 'build' in result.output
        assert 'init' in result.output
        assert 'validate' in result.output
    
    def test_init_command(self, cli_runner, temp_workspace):
        """Test init command."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(init, ['--output', str(temp_workspace)])
            
            assert result.exit_code == 0
            assert 'Initialized' in result.output
            
            # Check that config file was created
            config_file = temp_workspace / '.claude-code-builder.json'
            assert config_file.exists()
    
    def test_build_command_success(self, cli_runner, temp_workspace, sample_spec_file):
        """Test successful build command."""
        # Mock the project executor
        with patch('claude_code_builder.cli.main.ProjectExecutor') as mock_executor:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.phase_results = []
            mock_result.total_execution_time = 30
            mock_result.total_tokens_used = 500
            
            mock_instance.execute_project = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            result = cli_runner.invoke(build, [
                '--spec', str(sample_spec_file),
                '--output', str(temp_workspace),
                '--api-key', 'test-key'
            ])
            
            assert result.exit_code == 0
            assert 'Build completed successfully' in result.output
    
    def test_build_command_failure(self, cli_runner, temp_workspace, sample_spec_file):
        """Test build command with failure."""
        # Mock the project executor to fail
        with patch('claude_code_builder.cli.main.ProjectExecutor') as mock_executor:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.success = False
            mock_result.error_message = "Build failed due to compilation error"
            mock_result.phase_results = []
            
            mock_instance.execute_project = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            result = cli_runner.invoke(build, [
                '--spec', str(sample_spec_file),
                '--output', str(temp_workspace),
                '--api-key', 'test-key'
            ])
            
            assert result.exit_code == 1
            assert 'Build failed' in result.output
            assert 'compilation error' in result.output
    
    def test_build_command_missing_spec(self, cli_runner, temp_workspace):
        """Test build command with missing spec file."""
        result = cli_runner.invoke(build, [
            '--spec', str(temp_workspace / 'nonexistent.md'),
            '--output', str(temp_workspace)
        ])
        
        assert result.exit_code != 0
        assert 'not found' in result.output or 'does not exist' in result.output
    
    def test_validate_command(self, cli_runner, sample_spec_file):
        """Test validate command."""
        with patch('claude_code_builder.cli.main.ProjectValidator') as mock_validator:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.is_valid = True
            mock_result.errors = []
            mock_result.warnings = []
            mock_result.score = 0.9
            
            mock_instance.validate_project_spec.return_value = mock_result
            mock_validator.return_value = mock_instance
            
            result = cli_runner.invoke(validate, ['--spec', str(sample_spec_file)])
            
            assert result.exit_code == 0
            assert 'Validation passed' in result.output or 'Valid' in result.output
    
    def test_resume_command(self, cli_runner, temp_workspace):
        """Test resume command."""
        # Create checkpoint file
        checkpoint_file = temp_workspace / '.checkpoint.json'
        checkpoint_data = {
            'project_name': 'test-project',
            'completed_phases': ['Foundation'],
            'current_phase_index': 1,
            'timestamp': '2024-01-01T12:00:00Z'
        }
        checkpoint_file.write_text(json.dumps(checkpoint_data))
        
        with patch('claude_code_builder.cli.main.ProjectExecutor') as mock_executor:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.phase_results = []
            
            mock_instance.execute_project = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            result = cli_runner.invoke(resume, [
                '--workspace', str(temp_workspace),
                '--api-key', 'test-key'
            ])
            
            assert result.exit_code == 0
            assert 'Resuming' in result.output or 'Resumed' in result.output
    
    def test_status_command(self, cli_runner, temp_workspace):
        """Test status command."""
        # Create some project structure
        (temp_workspace / 'src').mkdir()
        (temp_workspace / 'src' / 'main.py').write_text('print("Hello")')
        
        # Create checkpoint
        checkpoint_file = temp_workspace / '.checkpoint.json'
        checkpoint_data = {
            'project_name': 'test-project',
            'completed_phases': ['Foundation', 'Core'],
            'current_phase_index': 2,
            'total_phases': 5,
            'timestamp': '2024-01-01T12:00:00Z'
        }
        checkpoint_file.write_text(json.dumps(checkpoint_data))
        
        result = cli_runner.invoke(status, ['--workspace', str(temp_workspace)])
        
        assert result.exit_code == 0
        assert 'test-project' in result.output
        assert 'Foundation' in result.output
        assert 'Core' in result.output
    
    def test_build_with_custom_instructions(self, cli_runner, temp_workspace, sample_spec_file):
        """Test build command with custom instructions."""
        # Create custom instructions file
        instructions_file = temp_workspace / 'custom_instructions.yaml'
        instructions_data = {
            'code_style': ['Use type hints', 'Follow PEP 8'],
            'architecture': ['Use clean architecture', 'Separate concerns'],
            'testing': ['Write comprehensive tests', 'Use pytest fixtures']
        }
        instructions_file.write_text(json.dumps(instructions_data))
        
        with patch('claude_code_builder.cli.main.ProjectExecutor') as mock_executor:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.phase_results = []
            
            mock_instance.execute_project = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            result = cli_runner.invoke(build, [
                '--spec', str(sample_spec_file),
                '--output', str(temp_workspace),
                '--instructions', str(instructions_file),
                '--api-key', 'test-key'
            ])
            
            assert result.exit_code == 0
    
    def test_build_with_config_file(self, cli_runner, temp_workspace, sample_spec_file):
        """Test build command with configuration file."""
        # Create config file
        config_file = temp_workspace / 'config.json'
        config_data = {
            'api_key': 'test-key',
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 10000,
            'max_retries': 3
        }
        config_file.write_text(json.dumps(config_data))
        
        with patch('claude_code_builder.cli.main.ProjectExecutor') as mock_executor:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.phase_results = []
            
            mock_instance.execute_project = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            result = cli_runner.invoke(build, [
                '--spec', str(sample_spec_file),
                '--output', str(temp_workspace),
                '--config', str(config_file)
            ])
            
            assert result.exit_code == 0


class TestConfigManager:
    """Test suite for ConfigManager."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        config_dir = Path(tempfile.mkdtemp())
        yield config_dir
        shutil.rmtree(config_dir, ignore_errors=True)
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create config manager instance."""
        return ConfigManager(config_dir=temp_config_dir)
    
    def test_create_default_config(self, config_manager, temp_config_dir):
        """Test creating default configuration."""
        config_manager.create_default_config()
        
        config_file = temp_config_dir / 'config.json'
        assert config_file.exists()
        
        config_data = json.loads(config_file.read_text())
        assert 'model' in config_data
        assert 'max_tokens' in config_data
        assert 'max_retries' in config_data
    
    def test_load_config(self, config_manager, temp_config_dir):
        """Test loading configuration."""
        # Create config file
        config_file = temp_config_dir / 'config.json'
        config_data = {
            'api_key': 'test-key',
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 15000
        }
        config_file.write_text(json.dumps(config_data))
        
        config = config_manager.load_config()
        
        assert config.api_key == 'test-key'
        assert config.model == 'claude-3-sonnet-20240229'
        assert config.max_tokens == 15000
    
    def test_save_config(self, config_manager, temp_config_dir):
        """Test saving configuration."""
        config = BuilderConfig()
        config.api_key = 'new-test-key'
        config.model = 'claude-3-opus-20240229'
        config.max_tokens = 20000
        
        config_manager.save_config(config)
        
        config_file = temp_config_dir / 'config.json'
        assert config_file.exists()
        
        saved_data = json.loads(config_file.read_text())
        assert saved_data['api_key'] == 'new-test-key'
        assert saved_data['model'] == 'claude-3-opus-20240229'
        assert saved_data['max_tokens'] == 20000
    
    def test_merge_configs(self, config_manager):
        """Test merging configurations."""
        base_config = BuilderConfig()
        base_config.api_key = 'base-key'
        base_config.model = 'claude-3-sonnet-20240229'
        base_config.max_tokens = 10000
        
        override_config = {
            'model': 'claude-3-opus-20240229',
            'max_retries': 5
        }
        
        merged = config_manager.merge_configs(base_config, override_config)
        
        assert merged.api_key == 'base-key'  # From base
        assert merged.model == 'claude-3-opus-20240229'  # Overridden
        assert merged.max_tokens == 10000  # From base
        assert merged.max_retries == 5  # From override
    
    def test_validate_config(self, config_manager):
        """Test config validation."""
        # Valid config
        valid_config = BuilderConfig()
        valid_config.api_key = 'sk-test-key'
        valid_config.model = 'claude-3-sonnet-20240229'
        valid_config.max_tokens = 10000
        
        assert config_manager.validate_config(valid_config) is True
        
        # Invalid config
        invalid_config = BuilderConfig()
        invalid_config.api_key = ''  # Empty API key
        invalid_config.max_tokens = -1  # Invalid max tokens
        
        assert config_manager.validate_config(invalid_config) is False


class TestOutputFormatter:
    """Test suite for OutputFormatter."""
    
    @pytest.fixture
    def output_formatter(self):
        """Create output formatter instance."""
        return OutputFormatter()
    
    def test_format_success_message(self, output_formatter):
        """Test formatting success messages."""
        message = output_formatter.format_success("Build completed successfully")
        
        assert "✓" in message or "SUCCESS" in message
        assert "Build completed successfully" in message
    
    def test_format_error_message(self, output_formatter):
        """Test formatting error messages."""
        message = output_formatter.format_error("Build failed due to syntax error")
        
        assert "✗" in message or "ERROR" in message
        assert "Build failed due to syntax error" in message
    
    def test_format_warning_message(self, output_formatter):
        """Test formatting warning messages."""
        message = output_formatter.format_warning("Deprecated function usage detected")
        
        assert "⚠" in message or "WARNING" in message
        assert "Deprecated function usage detected" in message
    
    def test_format_info_message(self, output_formatter):
        """Test formatting info messages."""
        message = output_formatter.format_info("Starting Phase 1: Foundation")
        
        assert "Starting Phase 1: Foundation" in message
    
    def test_format_build_summary(self, output_formatter):
        """Test formatting build summary."""
        # Mock build result
        build_result = Mock()
        build_result.success = True
        build_result.total_execution_time = 180  # 3 minutes
        build_result.total_tokens_used = 5000
        build_result.phase_results = [
            Mock(phase_name="Foundation", status="completed"),
            Mock(phase_name="Core", status="completed"),
            Mock(phase_name="Testing", status="completed")
        ]
        
        summary = output_formatter.format_build_summary(build_result)
        
        assert "3 minutes" in summary or "180" in summary
        assert "5000" in summary
        assert "Foundation" in summary
        assert "Core" in summary
        assert "Testing" in summary
    
    def test_format_validation_results(self, output_formatter):
        """Test formatting validation results."""
        # Mock validation result
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.score = 0.85
        validation_result.errors = []
        validation_result.warnings = [
            Mock(message="Missing docstring in function 'hello'", severity="low"),
            Mock(message="Consider using type hints", severity="medium")
        ]
        
        formatted = output_formatter.format_validation_results(validation_result)
        
        assert "85%" in formatted or "0.85" in formatted
        assert "Missing docstring" in formatted
        assert "type hints" in formatted
    
    def test_format_table(self, output_formatter):
        """Test table formatting."""
        headers = ["Phase", "Status", "Time", "Files"]
        rows = [
            ["Foundation", "Completed", "2m 30s", "5"],
            ["Core", "Completed", "5m 15s", "8"],
            ["Testing", "In Progress", "1m 45s", "3"]
        ]
        
        table = output_formatter.format_table(headers, rows)
        
        assert "Phase" in table
        assert "Foundation" in table
        assert "Completed" in table
        assert "2m 30s" in table


class TestProgressTracker:
    """Test suite for ProgressTracker."""
    
    @pytest.fixture
    def progress_tracker(self):
        """Create progress tracker instance."""
        return ProgressTracker()
    
    def test_start_progress(self, progress_tracker):
        """Test starting progress tracking."""
        progress_tracker.start_progress("Building project", total_steps=5)
        
        assert progress_tracker.is_active is True
        assert progress_tracker.total_steps == 5
        assert progress_tracker.current_step == 0
    
    def test_update_progress(self, progress_tracker):
        """Test updating progress."""
        progress_tracker.start_progress("Building project", total_steps=3)
        
        progress_tracker.update_progress("Phase 1: Foundation", step=1)
        assert progress_tracker.current_step == 1
        
        progress_tracker.update_progress("Phase 2: Core", step=2)
        assert progress_tracker.current_step == 2
        
        progress_tracker.update_progress("Phase 3: Testing", step=3)
        assert progress_tracker.current_step == 3
    
    def test_finish_progress(self, progress_tracker):
        """Test finishing progress tracking."""
        progress_tracker.start_progress("Building project", total_steps=2)
        progress_tracker.update_progress("Phase 1", step=1)
        progress_tracker.finish_progress("Build completed")
        
        assert progress_tracker.is_active is False
    
    def test_progress_with_spinner(self, progress_tracker):
        """Test progress with spinner for indeterminate tasks."""
        progress_tracker.start_spinner("Analyzing project structure...")
        
        # Simulate some work
        import time
        time.sleep(0.1)
        
        progress_tracker.stop_spinner("Analysis complete")
        
        assert progress_tracker.is_active is False
    
    def test_nested_progress(self, progress_tracker):
        """Test nested progress tracking."""
        # Start main progress
        progress_tracker.start_progress("Building project", total_steps=2)
        
        # Start sub-progress for phase
        progress_tracker.start_sub_progress("Phase 1: Foundation", total_steps=3)
        
        # Update sub-progress
        progress_tracker.update_sub_progress("Creating files", step=1)
        progress_tracker.update_sub_progress("Writing code", step=2)
        progress_tracker.update_sub_progress("Running tests", step=3)
        
        # Finish sub-progress
        progress_tracker.finish_sub_progress("Phase 1 complete")
        
        # Update main progress
        progress_tracker.update_progress("Phase 1 completed", step=1)
        
        assert progress_tracker.current_step == 1


@pytest.mark.integration
class TestCLIIntegration:
    """Integration tests for CLI interface."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = Path(tempfile.mkdtemp())
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)
    
    def test_full_cli_workflow(self, temp_workspace):
        """Test complete CLI workflow."""
        runner = CliRunner()
        
        # 1. Initialize project
        with runner.isolated_filesystem():
            # Create a workspace directory
            workspace = Path.cwd() / "test_workspace"
            workspace.mkdir()
            
            # Initialize
            result = runner.invoke(init, ['--output', str(workspace)])
            assert result.exit_code == 0
            
            # Check that config was created
            config_file = workspace / '.claude-code-builder.json'
            assert config_file.exists()
    
    def test_cli_error_handling(self, temp_workspace):
        """Test CLI error handling."""
        runner = CliRunner()
        
        # Test with invalid arguments
        result = runner.invoke(build, ['--spec', 'nonexistent.md'])
        assert result.exit_code != 0
        
        # Test with invalid config
        invalid_config = temp_workspace / 'invalid_config.json'
        invalid_config.write_text('{"invalid": "json"')  # Malformed JSON
        
        result = runner.invoke(build, [
            '--config', str(invalid_config),
            '--spec', 'test.md'
        ])
        assert result.exit_code != 0
    
    def test_cli_verbose_output(self, temp_workspace):
        """Test CLI verbose output mode."""
        runner = CliRunner()
        
        # Create minimal spec
        spec_file = temp_workspace / 'spec.md'
        spec_file.write_text('# Test\nA test project.')
        
        with patch('claude_code_builder.cli.main.ProjectExecutor') as mock_executor:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.phase_results = []
            
            mock_instance.execute_project = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            # Test verbose mode
            result = runner.invoke(build, [
                '--spec', str(spec_file),
                '--output', str(temp_workspace),
                '--verbose',
                '--api-key', 'test-key'
            ])
            
            assert result.exit_code == 0
            # In verbose mode, should see more detailed output
            assert len(result.output) > 0
    
    def test_cli_quiet_mode(self, temp_workspace):
        """Test CLI quiet mode."""
        runner = CliRunner()
        
        # Create minimal spec
        spec_file = temp_workspace / 'spec.md'
        spec_file.write_text('# Test\nA test project.')
        
        with patch('claude_code_builder.cli.main.ProjectExecutor') as mock_executor:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.phase_results = []
            
            mock_instance.execute_project = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            # Test quiet mode
            result = runner.invoke(build, [
                '--spec', str(spec_file),
                '--output', str(temp_workspace),
                '--quiet',
                '--api-key', 'test-key'
            ])
            
            assert result.exit_code == 0
            # In quiet mode, should see minimal output
            output_lines = result.output.strip().split('\n')
            assert len(output_lines) <= 5  # Should be very minimal