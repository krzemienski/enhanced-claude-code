"""Tests for execution system."""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import tempfile
import shutil
import json
import asyncio

from claude_code_builder.execution.project_executor import ProjectExecutor
from claude_code_builder.execution.phase_executor import PhaseExecutor
from claude_code_builder.execution.task_executor import TaskExecutor
from claude_code_builder.execution.checkpoint_manager import CheckpointManager
from claude_code_builder.models.project import ProjectSpec
from claude_code_builder.models.phase import Phase
from claude_code_builder.models.planning import PhaseTask
from claude_code_builder.models.execution import ExecutionResult, TaskResult, PhaseStatus
from claude_code_builder.exceptions.base import ExecutionError, ValidationError


class TestProjectExecutor:
    """Test suite for ProjectExecutor."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = Path(tempfile.mkdtemp())
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies."""
        return {
            'claude_client': Mock(),
            'mcp_handler': Mock(),
            'memory_manager': Mock(),
            'validator': Mock(),
            'monitor': Mock()
        }
    
    @pytest.fixture
    def project_executor(self, temp_workspace, mock_dependencies, builder_config):
        """Create project executor instance."""
        return ProjectExecutor(
            workspace=temp_workspace,
            config=builder_config,
            **mock_dependencies
        )
    
    @pytest.mark.asyncio
    async def test_execute_project_success(self, project_executor, sample_project_spec):
        """Test successful project execution."""
        # Mock successful execution
        project_executor.validator.validate_project_spec.return_value = True
        project_executor.monitor.start_monitoring = AsyncMock()
        project_executor.monitor.stop_monitoring = AsyncMock()
        
        # Mock phase execution
        phase_results = []
        for i, phase in enumerate(sample_project_spec.phases):
            result = ExecutionResult(
                phase_name=phase.name,
                status=PhaseStatus.COMPLETED,
                deliverables_created=[f"file{i}.py"],
                execution_time=30,
                tokens_used=100
            )
            phase_results.append(result)
        
        with patch.object(project_executor, '_execute_phase', side_effect=phase_results):
            result = await project_executor.execute_project(sample_project_spec)
        
        # Assertions
        assert result.success is True
        assert len(result.phase_results) == len(sample_project_spec.phases)
        assert all(r.status == PhaseStatus.COMPLETED for r in result.phase_results)
        assert result.total_execution_time > 0
        
        # Verify monitoring was started/stopped
        project_executor.monitor.start_monitoring.assert_called_once()
        project_executor.monitor.stop_monitoring.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_project_with_failure(self, project_executor, sample_project_spec):
        """Test project execution with phase failure."""
        # Mock validation
        project_executor.validator.validate_project_spec.return_value = True
        project_executor.monitor.start_monitoring = AsyncMock()
        project_executor.monitor.stop_monitoring = AsyncMock()
        
        # Mock first phase success, second phase failure
        phase_results = [
            ExecutionResult(
                phase_name="Foundation",
                status=PhaseStatus.COMPLETED,
                deliverables_created=["setup.py"],
                execution_time=30,
                tokens_used=100
            ),
            ExecutionResult(
                phase_name="Core Implementation",
                status=PhaseStatus.FAILED,
                error_message="Compilation failed",
                execution_time=15,
                tokens_used=50
            )
        ]
        
        with patch.object(project_executor, '_execute_phase', side_effect=phase_results):
            result = await project_executor.execute_project(sample_project_spec)
        
        # Assertions
        assert result.success is False
        assert len(result.phase_results) == 2  # Should stop after failure
        assert result.phase_results[0].status == PhaseStatus.COMPLETED
        assert result.phase_results[1].status == PhaseStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_execute_project_with_checkpoints(self, project_executor, sample_project_spec):
        """Test project execution with checkpoint management."""
        # Mock checkpoint manager
        checkpoint_manager = Mock()
        checkpoint_manager.load_checkpoint.return_value = None
        checkpoint_manager.save_checkpoint = AsyncMock()
        project_executor.checkpoint_manager = checkpoint_manager
        
        # Mock successful execution
        project_executor.validator.validate_project_spec.return_value = True
        project_executor.monitor.start_monitoring = AsyncMock()
        project_executor.monitor.stop_monitoring = AsyncMock()
        
        # Mock phase execution
        phase_result = ExecutionResult(
            phase_name="Foundation",
            status=PhaseStatus.COMPLETED,
            deliverables_created=["setup.py"],
            execution_time=30,
            tokens_used=100
        )
        
        with patch.object(project_executor, '_execute_phase', return_value=phase_result):
            await project_executor.execute_project(sample_project_spec, use_checkpoints=True)
        
        # Verify checkpoint operations
        checkpoint_manager.load_checkpoint.assert_called_once()
        assert checkpoint_manager.save_checkpoint.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self, project_executor, sample_project_spec):
        """Test resuming execution from checkpoint."""
        # Mock checkpoint data
        checkpoint_data = {
            'completed_phases': ['Foundation'],
            'current_phase_index': 1,
            'phase_results': [
                {
                    'phase_name': 'Foundation',
                    'status': 'completed',
                    'deliverables_created': ['setup.py'],
                    'execution_time': 30,
                    'tokens_used': 100
                }
            ]
        }
        
        # Mock checkpoint manager
        checkpoint_manager = Mock()
        checkpoint_manager.load_checkpoint.return_value = checkpoint_data
        checkpoint_manager.save_checkpoint = AsyncMock()
        project_executor.checkpoint_manager = checkpoint_manager
        
        # Mock remaining phase execution
        project_executor.validator.validate_project_spec.return_value = True
        project_executor.monitor.start_monitoring = AsyncMock()
        project_executor.monitor.stop_monitoring = AsyncMock()
        
        phase_result = ExecutionResult(
            phase_name="Core Implementation",
            status=PhaseStatus.COMPLETED,
            deliverables_created=["main.py"],
            execution_time=45,
            tokens_used=150
        )
        
        with patch.object(project_executor, '_execute_phase', return_value=phase_result):
            result = await project_executor.execute_project(sample_project_spec, use_checkpoints=True)
        
        # Should have both phases in results (loaded + executed)
        assert len(result.phase_results) == 2
        assert result.phase_results[0].phase_name == "Foundation"
        assert result.phase_results[1].phase_name == "Core Implementation"


class TestPhaseExecutor:
    """Test suite for PhaseExecutor."""
    
    @pytest.fixture
    def phase_executor(self, temp_workspace, mock_dependencies, builder_config):
        """Create phase executor instance."""
        return PhaseExecutor(
            workspace=temp_workspace,
            config=builder_config,
            **mock_dependencies
        )
    
    @pytest.mark.asyncio
    async def test_execute_phase_success(self, phase_executor, sample_phase):
        """Test successful phase execution."""
        # Mock task executor
        task_executor = Mock()
        task_results = [
            TaskResult(
                task_name="Create files",
                status="completed",
                files_created=["file1.py", "file2.py"],
                execution_time=20,
                tokens_used=80
            ),
            TaskResult(
                task_name="Write tests",
                status="completed",
                files_created=["test_file1.py"],
                execution_time=15,
                tokens_used=60
            )
        ]
        task_executor.execute_tasks = AsyncMock(return_value=task_results)
        
        # Mock dependencies
        phase_executor.task_decomposer.decompose_phase.return_value = [
            PhaseTask(name="Create files", priority="high"),
            PhaseTask(name="Write tests", priority="medium")
        ]
        phase_executor.validator.validate_phase_deliverables.return_value = True
        
        with patch.object(phase_executor, '_create_task_executor', return_value=task_executor):
            result = await phase_executor.execute_phase(sample_phase)
        
        # Assertions
        assert result.status == PhaseStatus.COMPLETED
        assert len(result.deliverables_created) == 3  # All files created
        assert result.execution_time > 0
        assert result.tokens_used > 0
        
        # Verify validation was called
        phase_executor.validator.validate_phase_deliverables.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_phase_with_task_failure(self, phase_executor, sample_phase):
        """Test phase execution with task failure."""
        # Mock task executor with failure
        task_executor = Mock()
        task_results = [
            TaskResult(
                task_name="Create files",
                status="completed",
                files_created=["file1.py"],
                execution_time=20,
                tokens_used=80
            ),
            TaskResult(
                task_name="Write tests",
                status="failed",
                error_message="Test creation failed",
                execution_time=10,
                tokens_used=30
            )
        ]
        task_executor.execute_tasks = AsyncMock(return_value=task_results)
        
        # Mock dependencies
        phase_executor.task_decomposer.decompose_phase.return_value = [
            PhaseTask(name="Create files", priority="high"),
            PhaseTask(name="Write tests", priority="medium")
        ]
        
        with patch.object(phase_executor, '_create_task_executor', return_value=task_executor):
            result = await phase_executor.execute_phase(sample_phase)
        
        # Should fail due to task failure
        assert result.status == PhaseStatus.FAILED
        assert "Test creation failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_execute_phase_validation_failure(self, phase_executor, sample_phase):
        """Test phase execution with validation failure."""
        # Mock successful task execution
        task_executor = Mock()
        task_results = [
            TaskResult(
                task_name="Create files",
                status="completed",
                files_created=["file1.py", "file2.py"],
                execution_time=20,
                tokens_used=80
            )
        ]
        task_executor.execute_tasks = AsyncMock(return_value=task_results)
        
        # Mock dependencies
        phase_executor.task_decomposer.decompose_phase.return_value = [
            PhaseTask(name="Create files", priority="high")
        ]
        
        # Mock validation failure
        phase_executor.validator.validate_phase_deliverables.side_effect = ValidationError("Files missing docstrings")
        
        with patch.object(phase_executor, '_create_task_executor', return_value=task_executor):
            result = await phase_executor.execute_phase(sample_phase)
        
        # Should fail due to validation
        assert result.status == PhaseStatus.FAILED
        assert "Files missing docstrings" in result.error_message


class TestTaskExecutor:
    """Test suite for TaskExecutor."""
    
    @pytest.fixture
    def task_executor(self, temp_workspace, mock_dependencies, builder_config):
        """Create task executor instance."""
        return TaskExecutor(
            workspace=temp_workspace,
            config=builder_config,
            **mock_dependencies
        )
    
    @pytest.mark.asyncio
    async def test_execute_task_success(self, task_executor):
        """Test successful task execution."""
        # Create test task
        task = PhaseTask(
            name="Create Python module",
            description="Create a simple Python module",
            deliverables=["src/module.py"],
            estimated_minutes=30
        )
        
        # Mock Claude response
        claude_response = Mock()
        claude_response.content = '''```python
# src/module.py
"""A simple Python module."""

def hello(name: str) -> str:
    """Say hello to someone.
    
    Args:
        name: Name to greet
        
    Returns:
        Greeting message
    """
    return f"Hello, {name}!"
```'''
        claude_response.usage = {"input_tokens": 50, "output_tokens": 100}
        
        task_executor.claude_client.send_message = AsyncMock(return_value=claude_response)
        
        # Execute task
        result = await task_executor.execute_task(task)
        
        # Assertions
        assert result.status == "completed"
        assert result.task_name == "Create Python module"
        assert "src/module.py" in result.files_created
        assert result.execution_time > 0
        assert result.tokens_used == 150  # input + output
        
        # Verify file was created
        module_file = task_executor.workspace / "src" / "module.py"
        assert module_file.exists()
        content = module_file.read_text()
        assert "def hello" in content
    
    @pytest.mark.asyncio
    async def test_execute_task_with_retry(self, task_executor):
        """Test task execution with retry on failure."""
        task = PhaseTask(
            name="Create config file",
            description="Create configuration file",
            deliverables=["config.json"],
            estimated_minutes=15
        )
        
        # Mock Claude responses - first fails, second succeeds
        failure_response = Mock()
        failure_response.content = "Invalid response"
        failure_response.usage = {"input_tokens": 20, "output_tokens": 10}
        
        success_response = Mock()
        success_response.content = '''```json
{
    "api_key": "your-key",
    "model": "claude-3-sonnet",
    "max_tokens": 10000
}
```'''
        success_response.usage = {"input_tokens": 30, "output_tokens": 40}
        
        task_executor.claude_client.send_message = AsyncMock(
            side_effect=[failure_response, success_response]
        )
        
        # Execute task
        result = await task_executor.execute_task(task, max_retries=2)
        
        # Should succeed on retry
        assert result.status == "completed"
        assert "config.json" in result.files_created
        
        # Verify file was created with correct content
        config_file = task_executor.workspace / "config.json"
        assert config_file.exists()
        config_data = json.loads(config_file.read_text())
        assert "api_key" in config_data
    
    @pytest.mark.asyncio
    async def test_execute_multiple_tasks(self, task_executor):
        """Test executing multiple tasks."""
        tasks = [
            PhaseTask(name="Task 1", deliverables=["file1.py"]),
            PhaseTask(name="Task 2", deliverables=["file2.py"]),
            PhaseTask(name="Task 3", deliverables=["file3.py"])
        ]
        
        # Mock Claude responses
        responses = []
        for i in range(3):
            response = Mock()
            response.content = f'''```python
# file{i+1}.py
"""Module {i+1}."""

def function_{i+1}():
    """Function {i+1}."""
    return {i+1}
```'''
            response.usage = {"input_tokens": 20, "output_tokens": 30}
            responses.append(response)
        
        task_executor.claude_client.send_message = AsyncMock(side_effect=responses)
        
        # Execute tasks
        results = await task_executor.execute_tasks(tasks)
        
        # Assertions
        assert len(results) == 3
        assert all(r.status == "completed" for r in results)
        
        # Verify all files were created
        for i in range(3):
            file_path = task_executor.workspace / f"file{i+1}.py"
            assert file_path.exists()
    
    @pytest.mark.asyncio
    async def test_execute_task_error_handling(self, task_executor):
        """Test task execution error handling."""
        task = PhaseTask(
            name="Failing task",
            description="This task will fail",
            deliverables=["output.py"],
            estimated_minutes=10
        )
        
        # Mock Claude client error
        task_executor.claude_client.send_message = AsyncMock(
            side_effect=Exception("API error")
        )
        
        # Execute task
        result = await task_executor.execute_task(task, max_retries=1)
        
        # Should fail gracefully
        assert result.status == "failed"
        assert "API error" in result.error_message
        assert result.task_name == "Failing task"


class TestCheckpointManager:
    """Test suite for CheckpointManager."""
    
    @pytest.fixture
    def checkpoint_manager(self, temp_workspace):
        """Create checkpoint manager instance."""
        return CheckpointManager(workspace=temp_workspace)
    
    def test_save_and_load_checkpoint(self, checkpoint_manager):
        """Test saving and loading checkpoints."""
        # Test data
        checkpoint_data = {
            'project_name': 'test-project',
            'completed_phases': ['Phase 1', 'Phase 2'],
            'current_phase_index': 2,
            'phase_results': [
                {'phase_name': 'Phase 1', 'status': 'completed'},
                {'phase_name': 'Phase 2', 'status': 'completed'}
            ],
            'timestamp': '2024-01-01T12:00:00Z'
        }
        
        # Save checkpoint
        checkpoint_manager.save_checkpoint(checkpoint_data)
        
        # Load checkpoint
        loaded_data = checkpoint_manager.load_checkpoint()
        
        # Verify data matches
        assert loaded_data['project_name'] == 'test-project'
        assert len(loaded_data['completed_phases']) == 2
        assert loaded_data['current_phase_index'] == 2
    
    def test_checkpoint_file_creation(self, checkpoint_manager):
        """Test checkpoint file is created correctly."""
        data = {'test': 'data'}
        
        checkpoint_manager.save_checkpoint(data)
        
        # Verify file exists
        checkpoint_file = checkpoint_manager.workspace / '.checkpoint.json'
        assert checkpoint_file.exists()
        
        # Verify content
        saved_data = json.loads(checkpoint_file.read_text())
        assert saved_data['test'] == 'data'
    
    def test_load_nonexistent_checkpoint(self, checkpoint_manager):
        """Test loading checkpoint when file doesn't exist."""
        result = checkpoint_manager.load_checkpoint()
        assert result is None
    
    def test_clear_checkpoint(self, checkpoint_manager):
        """Test clearing checkpoint data."""
        # Create checkpoint
        checkpoint_manager.save_checkpoint({'test': 'data'})
        
        # Verify it exists
        assert checkpoint_manager.load_checkpoint() is not None
        
        # Clear checkpoint
        checkpoint_manager.clear_checkpoint()
        
        # Verify it's gone
        assert checkpoint_manager.load_checkpoint() is None
        
        # Verify file is deleted
        checkpoint_file = checkpoint_manager.workspace / '.checkpoint.json'
        assert not checkpoint_file.exists()


@pytest.mark.integration
class TestExecutionIntegration:
    """Integration tests for execution system."""
    
    @pytest.mark.asyncio
    @pytest.mark.requires_api
    async def test_full_execution_workflow(self, builder_config, sample_project_spec, temp_workspace):
        """Test complete execution workflow with real components."""
        # Skip if no API key
        if not builder_config.api_key or builder_config.api_key == "test-key":
            pytest.skip("Requires real API key")
        
        # Create real executor with minimal mocking
        from claude_code_builder.sdk.claude_client import ClaudeClient
        from claude_code_builder.validation.project_validator import ProjectValidator
        from claude_code_builder.monitoring.build_monitor import BuildMonitor
        
        claude_client = ClaudeClient(config=builder_config)
        validator = ProjectValidator()
        monitor = BuildMonitor()
        
        executor = ProjectExecutor(
            workspace=temp_workspace,
            config=builder_config,
            claude_client=claude_client,
            validator=validator,
            monitor=monitor,
            mcp_handler=Mock(),  # Still mock MCP for now
            memory_manager=Mock()
        )
        
        # Execute simple project
        result = await executor.execute_project(sample_project_spec)
        
        # Basic validations
        assert isinstance(result, ExecutionResult)
        assert result.success is not None
        
        # Verify some output was created
        assert len(list(temp_workspace.glob("**/*"))) > 0