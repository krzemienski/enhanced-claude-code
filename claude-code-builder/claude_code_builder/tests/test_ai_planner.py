"""Tests for AI planning system."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import json

from claude_code_builder.ai.ai_planner import AIPlanner
from claude_code_builder.ai.phase_planner import PhasePlanner
from claude_code_builder.ai.task_decomposer import TaskDecomposer
from claude_code_builder.models.project import ProjectSpec
from claude_code_builder.models.phase import Phase
from claude_code_builder.models.planning import PlanningResult, PhaseTask
from claude_code_builder.sdk.claude_client import ClaudeResponse
from claude_code_builder.exceptions.base import PlanningError


class TestAIPlanner:
    """Test suite for AIPlanner."""
    
    @pytest.fixture
    def mock_claude_client(self):
        """Create mock Claude client."""
        client = Mock()
        client.send_message = AsyncMock()
        return client
    
    @pytest.fixture
    def ai_planner(self, mock_claude_client, builder_config, custom_instructions):
        """Create AI planner instance."""
        return AIPlanner(
            claude_client=mock_claude_client,
            config=builder_config,
            custom_instructions=custom_instructions
        )
    
    @pytest.mark.asyncio
    async def test_plan_project_success(self, ai_planner, sample_project_spec, mock_claude_client):
        """Test successful project planning."""
        # Mock Claude response
        mock_response = ClaudeResponse(
            content="""Based on the project specification, here's my planning:

## Phase 1: Foundation (2 hours)
- Set up project structure
- Create configuration files
- Initialize git repository

## Phase 2: Core Implementation (4 hours)
- Implement main functionality
- Create utility functions
- Add error handling

## Phase 3: Testing (2 hours)
- Write unit tests
- Add integration tests
- Setup CI/CD

Total estimated time: 8 hours
""",
            usage={"input_tokens": 100, "output_tokens": 200},
            model="claude-3-sonnet-20240229"
        )
        mock_claude_client.send_message.return_value = mock_response
        
        # Plan project
        result = await ai_planner.plan_project(sample_project_spec)
        
        # Assertions
        assert isinstance(result, PlanningResult)
        assert len(result.phases) == 3
        assert result.total_estimated_hours == 8
        assert result.phases[0].name == "Foundation"
        assert result.phases[1].name == "Core Implementation"
        assert result.phases[2].name == "Testing"
        
        # Verify Claude was called
        mock_claude_client.send_message.assert_called_once()
        call_args = mock_claude_client.send_message.call_args[0][0]
        assert "test-project" in call_args
        assert "planning" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_plan_project_with_constraints(self, ai_planner, sample_project_spec, mock_claude_client):
        """Test project planning with constraints."""
        # Add constraints
        constraints = {
            "max_phases": 5,
            "max_hours_per_phase": 4,
            "required_phases": ["Testing", "Documentation"]
        }
        
        # Mock response
        mock_response = ClaudeResponse(
            content="""Following the constraints:

## Phase 1: Setup (2 hours)
- Initial setup

## Phase 2: Implementation (4 hours)
- Core features

## Phase 3: Testing (3 hours)
- Required testing phase

## Phase 4: Documentation (2 hours)
- Required documentation

Total: 11 hours
""",
            usage={"input_tokens": 150, "output_tokens": 150},
            model="claude-3-sonnet-20240229"
        )
        mock_claude_client.send_message.return_value = mock_response
        
        # Plan with constraints
        result = await ai_planner.plan_project(sample_project_spec, constraints=constraints)
        
        # Assertions
        assert len(result.phases) <= 5
        assert any(p.name == "Testing" for p in result.phases)
        assert any(p.name == "Documentation" for p in result.phases)
        assert all(p.estimated_hours <= 4 for p in result.phases)
    
    @pytest.mark.asyncio
    async def test_plan_project_error_handling(self, ai_planner, sample_project_spec, mock_claude_client):
        """Test error handling in project planning."""
        # Mock Claude error
        mock_claude_client.send_message.side_effect = Exception("API error")
        
        # Should raise PlanningError
        with pytest.raises(PlanningError) as exc_info:
            await ai_planner.plan_project(sample_project_spec)
        
        assert "Failed to generate project plan" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_refine_plan(self, ai_planner, mock_claude_client):
        """Test plan refinement."""
        # Initial plan
        initial_plan = PlanningResult(
            phases=[
                Phase(name="Setup", description="Setup phase"),
                Phase(name="Implementation", description="Build features")
            ],
            total_estimated_hours=6,
            complexity_score=5
        )
        
        # Feedback
        feedback = "Add more testing and split implementation into smaller phases"
        
        # Mock refined response
        mock_response = ClaudeResponse(
            content="""Refined plan based on feedback:

## Phase 1: Setup (2 hours)
- Initial setup

## Phase 2: Core Features (3 hours)
- Basic functionality

## Phase 3: Advanced Features (3 hours)
- Complex features

## Phase 4: Testing (4 hours)
- Comprehensive testing

Total: 12 hours
""",
            usage={"input_tokens": 200, "output_tokens": 150},
            model="claude-3-sonnet-20240229"
        )
        mock_claude_client.send_message.return_value = mock_response
        
        # Refine plan
        refined = await ai_planner.refine_plan(initial_plan, feedback)
        
        # Assertions
        assert len(refined.phases) == 4
        assert any(p.name == "Testing" for p in refined.phases)
        assert refined.total_estimated_hours > initial_plan.total_estimated_hours


class TestPhasePlanner:
    """Test suite for PhasePlanner."""
    
    @pytest.fixture
    def phase_planner(self):
        """Create phase planner instance."""
        return PhasePlanner()
    
    def test_analyze_phases(self, phase_planner):
        """Test phase analysis."""
        phases = [
            Phase(name="Setup", description="Project setup", deliverables=["README.md", "setup.py"]),
            Phase(name="Core", description="Core implementation", deliverables=["src/main.py", "src/utils.py"]),
            Phase(name="Tests", description="Testing", deliverables=["tests/test_main.py"])
        ]
        
        analysis = phase_planner.analyze_phases(phases)
        
        assert analysis['total_phases'] == 3
        assert analysis['total_deliverables'] == 5
        assert analysis['average_deliverables_per_phase'] == 5/3
        assert 'Setup' in analysis['phase_names']
        assert 'Core' in analysis['phase_names']
        assert 'Tests' in analysis['phase_names']
    
    def test_optimize_phase_order(self, phase_planner):
        """Test phase order optimization."""
        phases = [
            Phase(name="Testing", dependencies=["Implementation"]),
            Phase(name="Documentation", dependencies=["Testing"]),
            Phase(name="Setup", dependencies=[]),
            Phase(name="Implementation", dependencies=["Setup"])
        ]
        
        optimized = phase_planner.optimize_phase_order(phases)
        
        # Check order
        phase_names = [p.name for p in optimized]
        assert phase_names.index("Setup") < phase_names.index("Implementation")
        assert phase_names.index("Implementation") < phase_names.index("Testing")
        assert phase_names.index("Testing") < phase_names.index("Documentation")
    
    def test_validate_phase_dependencies(self, phase_planner):
        """Test phase dependency validation."""
        # Valid dependencies
        valid_phases = [
            Phase(name="A", dependencies=[]),
            Phase(name="B", dependencies=["A"]),
            Phase(name="C", dependencies=["B"])
        ]
        
        assert phase_planner.validate_phase_dependencies(valid_phases) == True
        
        # Circular dependency
        circular_phases = [
            Phase(name="A", dependencies=["B"]),
            Phase(name="B", dependencies=["A"])
        ]
        
        assert phase_planner.validate_phase_dependencies(circular_phases) == False
        
        # Missing dependency
        missing_phases = [
            Phase(name="A", dependencies=["NonExistent"]),
            Phase(name="B", dependencies=[])
        ]
        
        assert phase_planner.validate_phase_dependencies(missing_phases) == False
    
    def test_estimate_phase_complexity(self, phase_planner, sample_phase):
        """Test phase complexity estimation."""
        complexity = phase_planner.estimate_phase_complexity(sample_phase)
        
        assert isinstance(complexity, int)
        assert 1 <= complexity <= 10
        
        # Complex phase
        complex_phase = Phase(
            name="Complex",
            description="Very complex phase with many deliverables",
            deliverables=["file" + str(i) + ".py" for i in range(20)],
            validation_rules=["rule" + str(i) for i in range(10)]
        )
        
        complex_score = phase_planner.estimate_phase_complexity(complex_phase)
        assert complex_score > complexity  # Should be higher


class TestTaskDecomposer:
    """Test suite for TaskDecomposer."""
    
    @pytest.fixture
    def task_decomposer(self):
        """Create task decomposer instance."""
        return TaskDecomposer()
    
    def test_decompose_phase(self, task_decomposer, sample_phase):
        """Test phase decomposition into tasks."""
        tasks = task_decomposer.decompose_phase(sample_phase)
        
        assert len(tasks) > 0
        assert all(isinstance(t, PhaseTask) for t in tasks)
        
        # Check task properties
        for task in tasks:
            assert task.name
            assert task.description
            assert task.estimated_minutes > 0
            assert task.priority in ['high', 'medium', 'low']
    
    def test_decompose_phase_with_complex_deliverables(self, task_decomposer):
        """Test decomposition with complex deliverables."""
        phase = Phase(
            name="API Development",
            description="Build REST API",
            deliverables=[
                "api/auth.py",
                "api/users.py",
                "api/products.py",
                "tests/test_auth.py",
                "tests/test_users.py",
                "docs/api.md"
            ]
        )
        
        tasks = task_decomposer.decompose_phase(phase)
        
        # Should create tasks for different aspects
        task_names = [t.name for t in tasks]
        assert any("auth" in name.lower() for name in task_names)
        assert any("test" in name.lower() for name in task_names)
        assert any("doc" in name.lower() for name in task_names)
    
    def test_prioritize_tasks(self, task_decomposer):
        """Test task prioritization."""
        tasks = [
            PhaseTask(name="Setup", priority="low", estimated_minutes=30),
            PhaseTask(name="Core Feature", priority="high", estimated_minutes=120),
            PhaseTask(name="Testing", priority="medium", estimated_minutes=60),
            PhaseTask(name="Critical Fix", priority="high", estimated_minutes=45)
        ]
        
        prioritized = task_decomposer.prioritize_tasks(tasks)
        
        # High priority tasks should come first
        high_priority_indices = [i for i, t in enumerate(prioritized) if t.priority == "high"]
        medium_priority_indices = [i for i, t in enumerate(prioritized) if t.priority == "medium"]
        low_priority_indices = [i for i, t in enumerate(prioritized) if t.priority == "low"]
        
        if high_priority_indices and medium_priority_indices:
            assert max(high_priority_indices) < min(medium_priority_indices)
        if medium_priority_indices and low_priority_indices:
            assert max(medium_priority_indices) < min(low_priority_indices)
    
    def test_estimate_task_duration(self, task_decomposer):
        """Test task duration estimation."""
        # Simple task
        simple_task = PhaseTask(
            name="Create README",
            description="Write project documentation",
            deliverables=["README.md"]
        )
        
        simple_duration = task_decomposer.estimate_task_duration(simple_task)
        assert 15 <= simple_duration <= 60  # README should be quick
        
        # Complex task
        complex_task = PhaseTask(
            name="Implement Authentication",
            description="Build complete auth system with JWT, OAuth, and 2FA",
            deliverables=["auth/jwt.py", "auth/oauth.py", "auth/twofa.py", "tests/test_auth.py"]
        )
        
        complex_duration = task_decomposer.estimate_task_duration(complex_task)
        assert complex_duration > simple_duration  # Should take longer
    
    def test_group_related_tasks(self, task_decomposer):
        """Test grouping of related tasks."""
        tasks = [
            PhaseTask(name="Create User Model", category="models"),
            PhaseTask(name="Create Product Model", category="models"),
            PhaseTask(name="Write User Tests", category="tests"),
            PhaseTask(name="Write Product Tests", category="tests"),
            PhaseTask(name="Setup Database", category="infrastructure")
        ]
        
        groups = task_decomposer.group_related_tasks(tasks)
        
        assert "models" in groups
        assert "tests" in groups
        assert "infrastructure" in groups
        assert len(groups["models"]) == 2
        assert len(groups["tests"]) == 2
        assert len(groups["infrastructure"]) == 1


@pytest.mark.integration
class TestAIPlannerIntegration:
    """Integration tests for AI planning system."""
    
    @pytest.mark.asyncio
    @pytest.mark.requires_api
    async def test_full_planning_workflow(self, builder_config, sample_project_spec):
        """Test complete planning workflow with real API."""
        # Skip if no API key
        if not builder_config.api_key or builder_config.api_key == "test-key":
            pytest.skip("Requires real API key")
        
        # Create real planner
        from claude_code_builder.sdk.claude_client import ClaudeClient
        
        client = ClaudeClient(config=builder_config)
        planner = AIPlanner(claude_client=client, config=builder_config)
        
        # Plan project
        result = await planner.plan_project(sample_project_spec)
        
        # Basic validations
        assert isinstance(result, PlanningResult)
        assert len(result.phases) > 0
        assert result.total_estimated_hours > 0
        assert all(phase.name for phase in result.phases)
        assert all(phase.deliverables for phase in result.phases)