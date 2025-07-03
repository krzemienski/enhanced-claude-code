"""Phase Executor for managing individual phase execution."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json

from ..models.project import BuildPhase, BuildTask, BuildStatus
from ..models.context import ExecutionContext, PhaseResult, TaskResult
from ..sdk.client import ClaudeCodeClient
from ..mcp.registry import MCPRegistry
from ..research.coordinator import ResearchCoordinator
from ..instructions.executor import RuleExecutor

logger = logging.getLogger(__name__)


class TaskExecutionStrategy(Enum):
    """Strategy for task execution within a phase."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DEPENDENCY_BASED = "dependency_based"
    PRIORITY_BASED = "priority_based"


@dataclass
class PhaseExecutionConfig:
    """Configuration for phase execution."""
    strategy: TaskExecutionStrategy = TaskExecutionStrategy.DEPENDENCY_BASED
    max_concurrent_tasks: int = 5
    task_timeout: int = 600  # seconds
    enable_research: bool = True
    enable_mcp: bool = True
    enable_rules: bool = True
    checkpoint_after_tasks: int = 10
    retry_failed_tasks: bool = True
    continue_on_error: bool = False


@dataclass
class PhaseExecutionState:
    """State tracking for phase execution."""
    phase: BuildPhase
    context: ExecutionContext
    start_time: datetime
    completed_tasks: Set[str] = field(default_factory=set)
    failed_tasks: Set[str] = field(default_factory=set)
    task_results: Dict[str, TaskResult] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)


class PhaseExecutor:
    """Executes individual build phases with task management."""
    
    def __init__(self, config: Optional[PhaseExecutionConfig] = None):
        """Initialize the phase executor."""
        self.config = config or PhaseExecutionConfig()
        
        # Component instances
        self.claude_client = ClaudeCodeClient()
        self.mcp_registry = MCPRegistry()
        self.research_coordinator = ResearchCoordinator()
        self.rule_executor = RuleExecutor()
        
        # Execution state
        self.current_state: Optional[PhaseExecutionState] = None
        self.task_semaphore = asyncio.Semaphore(
            self.config.max_concurrent_tasks
        )
        
        # Task handlers
        self.task_handlers: Dict[str, Callable] = {}
        self.pre_task_hooks: List[Callable] = []
        self.post_task_hooks: List[Callable] = []
        
        logger.info("Phase Executor initialized")
    
    async def execute_phase(
        self,
        phase: BuildPhase,
        context: ExecutionContext
    ) -> PhaseResult:
        """Execute a complete build phase."""
        logger.info(f"Starting phase execution: {phase.name}")
        
        # Initialize state
        self.current_state = PhaseExecutionState(
            phase=phase,
            context=context,
            start_time=datetime.now()
        )
        
        try:
            # Pre-phase preparation
            await self._prepare_phase()
            
            # Execute based on strategy
            if self.config.strategy == TaskExecutionStrategy.SEQUENTIAL:
                task_results = await self._execute_sequential()
            elif self.config.strategy == TaskExecutionStrategy.PARALLEL:
                task_results = await self._execute_parallel()
            elif self.config.strategy == TaskExecutionStrategy.DEPENDENCY_BASED:
                task_results = await self._execute_dependency_based()
            else:  # PRIORITY_BASED
                task_results = await self._execute_priority_based()
            
            # Post-phase processing
            phase_result = await self._finalize_phase(task_results)
            
            logger.info(
                f"Phase execution completed: {phase.name} - "
                f"Status: {phase_result.status}"
            )
            
            return phase_result
            
        except Exception as e:
            logger.error(f"Phase execution failed: {phase.name} - {e}")
            
            # Create error result
            return PhaseResult(
                phase_id=phase.id,
                status=BuildStatus.FAILED,
                start_time=self.current_state.start_time,
                end_time=datetime.now(),
                error=str(e),
                outputs=self.current_state.task_results
            )
    
    async def execute_task(
        self,
        task: BuildTask,
        context: ExecutionContext
    ) -> TaskResult:
        """Execute a single task."""
        logger.info(f"Executing task: {task.name}")
        
        task_start = datetime.now()
        
        try:
            # Run pre-task hooks
            for hook in self.pre_task_hooks:
                await self._run_hook(hook, task=task, context=context)
            
            # Check for custom handler
            if task.type in self.task_handlers:
                result = await self._run_custom_handler(task, context)
            else:
                # Execute based on task type
                if task.type == "code":
                    result = await self._execute_code_task(task, context)
                elif task.type == "research":
                    result = await self._execute_research_task(task, context)
                elif task.type == "mcp":
                    result = await self._execute_mcp_task(task, context)
                elif task.type == "validation":
                    result = await self._execute_validation_task(task, context)
                else:
                    result = await self._execute_generic_task(task, context)
            
            # Run post-task hooks
            for hook in self.post_task_hooks:
                await self._run_hook(
                    hook, task=task, context=context, result=result
                )
            
            # Create task result
            task_result = TaskResult(
                task_id=task.id,
                status=BuildStatus.COMPLETED,
                start_time=task_start,
                end_time=datetime.now(),
                outputs=result.get("outputs", {}),
                artifacts=result.get("artifacts", {}),
                metrics=result.get("metrics", {})
            )
            
            # Update state
            self.current_state.completed_tasks.add(task.id)
            self.current_state.task_results[task.id] = task_result
            
            return task_result
            
        except Exception as e:
            logger.error(f"Task execution failed: {task.name} - {e}")
            
            # Create error result
            task_result = TaskResult(
                task_id=task.id,
                status=BuildStatus.FAILED,
                start_time=task_start,
                end_time=datetime.now(),
                error=str(e)
            )
            
            # Update state
            self.current_state.failed_tasks.add(task.id)
            self.current_state.task_results[task.id] = task_result
            
            # Retry if configured
            if self.config.retry_failed_tasks:
                return await self._retry_task(task, context)
            
            # Continue or raise based on config
            if not self.config.continue_on_error:
                raise
            
            return task_result
    
    def register_task_handler(
        self,
        task_type: str,
        handler: Callable
    ) -> None:
        """Register a custom task handler."""
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    def add_pre_task_hook(self, hook: Callable) -> None:
        """Add a pre-task execution hook."""
        self.pre_task_hooks.append(hook)
    
    def add_post_task_hook(self, hook: Callable) -> None:
        """Add a post-task execution hook."""
        self.post_task_hooks.append(hook)
    
    async def _prepare_phase(self) -> None:
        """Prepare for phase execution."""
        # Research if enabled
        if self.config.enable_research:
            logger.info("Conducting phase research...")
            research_results = await self.research_coordinator.research_phase(
                self.current_state.phase,
                self.current_state.context
            )
            self.current_state.context.add_research(research_results)
        
        # Setup MCP if enabled
        if self.config.enable_mcp:
            logger.info("Setting up MCP servers...")
            mcp_config = await self._setup_mcp_for_phase()
            self.current_state.context.mcp_config = mcp_config
        
        # Apply rules if enabled
        if self.config.enable_rules:
            logger.info("Applying phase rules...")
            rule_results = await self._apply_phase_rules()
            self.current_state.context.rule_results = rule_results
    
    async def _execute_sequential(self) -> Dict[str, TaskResult]:
        """Execute tasks sequentially."""
        results = {}
        
        for task in self.current_state.phase.tasks:
            result = await self.execute_task(task, self.current_state.context)
            results[task.id] = result
            
            # Check if we should continue
            if result.status == BuildStatus.FAILED and not self.config.continue_on_error:
                break
            
            # Checkpoint if needed
            if len(results) % self.config.checkpoint_after_tasks == 0:
                await self._create_checkpoint()
        
        return results
    
    async def _execute_parallel(self) -> Dict[str, TaskResult]:
        """Execute all tasks in parallel."""
        tasks = []
        
        for task in self.current_state.phase.tasks:
            task_coro = self.execute_task(task, self.current_state.context)
            tasks.append(asyncio.create_task(task_coro))
        
        # Wait for all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        task_results = {}
        for task, result in zip(self.current_state.phase.tasks, results):
            if isinstance(result, Exception):
                # Create error result
                task_results[task.id] = TaskResult(
                    task_id=task.id,
                    status=BuildStatus.FAILED,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error=str(result)
                )
            else:
                task_results[task.id] = result
        
        return task_results
    
    async def _execute_dependency_based(self) -> Dict[str, TaskResult]:
        """Execute tasks based on dependencies."""
        results = {}
        completed = set()
        
        while len(completed) < len(self.current_state.phase.tasks):
            # Find executable tasks
            executable = []
            
            for task in self.current_state.phase.tasks:
                if task.id in completed:
                    continue
                
                # Check dependencies
                deps_satisfied = all(
                    dep in completed for dep in task.dependencies
                )
                
                if deps_satisfied:
                    executable.append(task)
            
            if not executable:
                # No tasks can be executed
                remaining = [
                    t for t in self.current_state.phase.tasks
                    if t.id not in completed
                ]
                raise BuildError(
                    f"Cannot execute remaining tasks: {[t.name for t in remaining]}"
                )
            
            # Execute batch of tasks
            batch_tasks = []
            for task in executable[:self.config.max_concurrent_tasks]:
                task_coro = self.execute_task(task, self.current_state.context)
                batch_tasks.append((task.id, asyncio.create_task(task_coro)))
            
            # Wait for batch completion
            for task_id, task_future in batch_tasks:
                try:
                    result = await task_future
                    results[task_id] = result
                    completed.add(task_id)
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    if not self.config.continue_on_error:
                        raise
            
            # Checkpoint if needed
            if len(completed) % self.config.checkpoint_after_tasks == 0:
                await self._create_checkpoint()
        
        return results
    
    async def _execute_priority_based(self) -> Dict[str, TaskResult]:
        """Execute tasks based on priority."""
        # Sort tasks by priority
        sorted_tasks = sorted(
            self.current_state.phase.tasks,
            key=lambda t: t.metadata.get("priority", 0),
            reverse=True
        )
        
        results = {}
        
        # Execute in priority order with controlled parallelism
        for i in range(0, len(sorted_tasks), self.config.max_concurrent_tasks):
            batch = sorted_tasks[i:i + self.config.max_concurrent_tasks]
            
            batch_tasks = []
            for task in batch:
                task_coro = self.execute_task(task, self.current_state.context)
                batch_tasks.append((task.id, asyncio.create_task(task_coro)))
            
            # Wait for batch
            for task_id, task_future in batch_tasks:
                try:
                    result = await task_future
                    results[task_id] = result
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    if not self.config.continue_on_error:
                        raise
        
        return results
    
    async def _execute_code_task(
        self,
        task: BuildTask,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute a code generation task."""
        # Prepare prompt
        prompt = self._prepare_code_prompt(task, context)
        
        # Execute with Claude
        response = await self.claude_client.execute(
            prompt=prompt,
            context=context.to_claude_context()
        )
        
        # Extract artifacts
        artifacts = self._extract_code_artifacts(response)
        
        return {
            "outputs": {
                "response": response,
                "files_created": len(artifacts.get("files", [])),
                "code_blocks": len(artifacts.get("code_blocks", []))
            },
            "artifacts": artifacts,
            "metrics": {
                "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                "execution_time": response.get("execution_time", 0)
            }
        }
    
    async def _execute_research_task(
        self,
        task: BuildTask,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute a research task."""
        # Determine research type
        research_type = task.metadata.get("research_type", "general")
        
        # Conduct research
        research_results = await self.research_coordinator.research(
            query=task.description,
            research_type=research_type,
            context=context
        )
        
        return {
            "outputs": {
                "findings": research_results.get("findings", []),
                "recommendations": research_results.get("recommendations", []),
                "sources": research_results.get("sources", [])
            },
            "artifacts": {
                "research_report": research_results
            },
            "metrics": {
                "sources_analyzed": len(research_results.get("sources", [])),
                "confidence_score": research_results.get("confidence", 0)
            }
        }
    
    async def _execute_mcp_task(
        self,
        task: BuildTask,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute an MCP-related task."""
        mcp_action = task.metadata.get("mcp_action", "discover")
        
        if mcp_action == "discover":
            # Discover MCP servers
            servers = await self.mcp_registry.discover_servers(
                task.metadata.get("search_pattern", "*")
            )
            result = {"servers": servers}
            
        elif mcp_action == "install":
            # Install MCP server
            server_name = task.metadata.get("server_name")
            result = await self.mcp_registry.install_server(server_name)
            
        elif mcp_action == "configure":
            # Configure MCP
            config = task.metadata.get("config", {})
            result = await self.mcp_registry.configure(config)
            
        else:
            result = {"error": f"Unknown MCP action: {mcp_action}"}
        
        return {
            "outputs": result,
            "artifacts": {
                "mcp_state": await self.mcp_registry.get_state()
            }
        }
    
    async def _execute_validation_task(
        self,
        task: BuildTask,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute a validation task."""
        validation_type = task.metadata.get("validation_type", "general")
        target = task.metadata.get("target", "phase")
        
        # Perform validation
        if validation_type == "code":
            result = await self._validate_code()
        elif validation_type == "structure":
            result = await self._validate_structure()
        elif validation_type == "dependencies":
            result = await self._validate_dependencies()
        else:
            result = await self._validate_general()
        
        return {
            "outputs": {
                "valid": result.get("valid", False),
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", [])
            },
            "artifacts": {
                "validation_report": result
            },
            "metrics": {
                "error_count": len(result.get("errors", [])),
                "warning_count": len(result.get("warnings", []))
            }
        }
    
    async def _execute_generic_task(
        self,
        task: BuildTask,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute a generic task."""
        # Default implementation
        logger.info(f"Executing generic task: {task.name}")
        
        # Simulate work
        await asyncio.sleep(0.1)
        
        return {
            "outputs": {
                "status": "completed",
                "task_type": task.type
            },
            "artifacts": {},
            "metrics": {}
        }
    
    async def _run_custom_handler(
        self,
        task: BuildTask,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Run a custom task handler."""
        handler = self.task_handlers[task.type]
        
        if asyncio.iscoroutinefunction(handler):
            return await handler(task, context)
        else:
            return handler(task, context)
    
    async def _run_hook(self, hook: Callable, **kwargs) -> None:
        """Run a hook function."""
        try:
            if asyncio.iscoroutinefunction(hook):
                await hook(**kwargs)
            else:
                hook(**kwargs)
        except Exception as e:
            logger.error(f"Hook execution error: {e}")
    
    async def _retry_task(
        self,
        task: BuildTask,
        context: ExecutionContext,
        attempt: int = 1
    ) -> TaskResult:
        """Retry a failed task."""
        max_attempts = 3
        
        if attempt > max_attempts:
            logger.error(f"Task {task.name} failed after {max_attempts} attempts")
            return self.current_state.task_results[task.id]
        
        logger.info(f"Retrying task {task.name} (attempt {attempt})")
        
        # Wait before retry
        await asyncio.sleep(2 ** attempt)
        
        # Clear failed status
        self.current_state.failed_tasks.discard(task.id)
        
        # Retry execution
        return await self.execute_task(task, context)
    
    async def _setup_mcp_for_phase(self) -> Dict[str, Any]:
        """Setup MCP configuration for the phase."""
        phase_requirements = self.current_state.phase.metadata.get(
            "mcp_requirements", {}
        )
        
        # Discover required servers
        required_servers = phase_requirements.get("servers", [])
        available_servers = await self.mcp_registry.discover_servers()
        
        # Install missing servers
        for server in required_servers:
            if server not in available_servers:
                await self.mcp_registry.install_server(server)
        
        # Generate configuration
        config = await self.mcp_registry.generate_config(
            servers=required_servers,
            phase_context=self.current_state.context
        )
        
        return config
    
    async def _apply_phase_rules(self) -> Dict[str, Any]:
        """Apply custom rules for the phase."""
        # Get phase rules
        phase_rules = self.current_state.phase.metadata.get("rules", {})
        
        # Execute rules
        rule_results = await self.rule_executor.execute(
            input_data={
                "phase": self.current_state.phase.to_dict(),
                "context": self.current_state.context.to_dict()
            },
            instruction_set=phase_rules.get("instruction_set"),
            context=self.current_state.context
        )
        
        return rule_results
    
    async def _create_checkpoint(self) -> None:
        """Create a checkpoint of current execution state."""
        checkpoint = {
            "phase_id": self.current_state.phase.id,
            "timestamp": datetime.now().isoformat(),
            "completed_tasks": list(self.current_state.completed_tasks),
            "failed_tasks": list(self.current_state.failed_tasks),
            "artifacts": self.current_state.artifacts,
            "metrics": self.current_state.metrics
        }
        
        # Save checkpoint (implementation depends on storage backend)
        logger.info(f"Checkpoint created for phase {self.current_state.phase.name}")
        
        return checkpoint
    
    async def _finalize_phase(
        self,
        task_results: Dict[str, TaskResult]
    ) -> PhaseResult:
        """Finalize phase execution and create result."""
        end_time = datetime.now()
        duration = (end_time - self.current_state.start_time).total_seconds()
        
        # Determine phase status
        failed_count = len(self.current_state.failed_tasks)
        if failed_count == 0:
            status = BuildStatus.COMPLETED
        elif failed_count == len(self.current_state.phase.tasks):
            status = BuildStatus.FAILED
        else:
            status = BuildStatus.PARTIAL
        
        # Aggregate metrics
        total_metrics = {
            "duration": duration,
            "tasks_total": len(self.current_state.phase.tasks),
            "tasks_completed": len(self.current_state.completed_tasks),
            "tasks_failed": failed_count
        }
        
        # Create phase result
        return PhaseResult(
            phase_id=self.current_state.phase.id,
            status=status,
            start_time=self.current_state.start_time,
            end_time=end_time,
            outputs=task_results,
            artifacts=self.current_state.artifacts,
            metrics=total_metrics
        )
    
    def _prepare_code_prompt(
        self,
        task: BuildTask,
        context: ExecutionContext
    ) -> str:
        """Prepare prompt for code generation task."""
        # Build comprehensive prompt
        prompt_parts = [
            f"Task: {task.name}",
            f"Description: {task.description}",
            "",
            "Context:",
            f"- Phase: {self.current_state.phase.name}",
            f"- Project: {context.project_name}"
        ]
        
        # Add requirements
        if task.requirements:
            prompt_parts.extend([
                "",
                "Requirements:",
                *[f"- {req}" for req in task.requirements]
            ])
        
        # Add previous outputs if available
        if context.previous_outputs:
            prompt_parts.extend([
                "",
                "Previous Outputs Available:",
                *[f"- {k}: {v}" for k, v in context.previous_outputs.items()]
            ])
        
        return "\n".join(prompt_parts)
    
    def _extract_code_artifacts(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract code artifacts from response."""
        artifacts = {
            "files": [],
            "code_blocks": [],
            "commands": []
        }
        
        # Extract from response (implementation depends on response format)
        # This is a placeholder
        
        return artifacts
    
    async def _validate_code(self) -> Dict[str, Any]:
        """Validate generated code."""
        # Placeholder implementation
        return {
            "valid": True,
            "errors": [],
            "warnings": []
        }
    
    async def _validate_structure(self) -> Dict[str, Any]:
        """Validate project structure."""
        # Placeholder implementation
        return {
            "valid": True,
            "errors": [],
            "warnings": []
        }
    
    async def _validate_dependencies(self) -> Dict[str, Any]:
        """Validate dependencies."""
        # Placeholder implementation
        return {
            "valid": True,
            "errors": [],
            "warnings": []
        }
    
    async def _validate_general(self) -> Dict[str, Any]:
        """General validation."""
        # Placeholder implementation
        return {
            "valid": True,
            "errors": [],
            "warnings": []
        }