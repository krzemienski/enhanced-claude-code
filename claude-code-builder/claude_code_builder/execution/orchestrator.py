"""Execution Orchestrator for Claude Code Builder."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..models.project import Project, BuildPhase, BuildStatus
from ..models.context import ExecutionContext, PhaseResult
from ..models.errors import BuildError
from ..ai.planner import BuildPlanner
from ..sdk.client import ClaudeCodeClient
from ..mcp.discovery import MCPDiscovery
from ..research.coordinator import ResearchCoordinator
from ..instructions.executor import RuleExecutor

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution modes for the orchestrator."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"
    CHECKPOINT = "checkpoint"


@dataclass
class OrchestrationConfig:
    """Configuration for execution orchestration."""
    mode: ExecutionMode = ExecutionMode.ADAPTIVE
    max_concurrent_phases: int = 3
    max_concurrent_tasks: int = 10
    checkpoint_interval: int = 300  # seconds
    retry_attempts: int = 3
    timeout_per_phase: int = 3600  # seconds
    enable_recovery: bool = True
    enable_monitoring: bool = True
    debug_mode: bool = False


@dataclass
class OrchestrationState:
    """Current state of orchestration."""
    execution_id: str
    project: Project
    start_time: datetime
    current_phase: Optional[BuildPhase] = None
    completed_phases: List[str] = field(default_factory=list)
    failed_phases: List[str] = field(default_factory=list)
    phase_results: Dict[str, PhaseResult] = field(default_factory=dict)
    context: Optional[ExecutionContext] = None
    errors: List[BuildError] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionOrchestrator:
    """Orchestrates the execution of project builds."""
    
    def __init__(self, config: Optional[OrchestrationConfig] = None):
        """Initialize the execution orchestrator."""
        self.config = config or OrchestrationConfig()
        self.state: Optional[OrchestrationState] = None
        
        # Component instances
        self.planner = BuildPlanner()
        self.claude_client = ClaudeCodeClient()
        self.mcp_discovery = MCPDiscovery()
        self.research_coordinator = ResearchCoordinator()
        self.rule_executor = RuleExecutor()
        
        # Execution tracking
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.phase_semaphore = asyncio.Semaphore(
            self.config.max_concurrent_phases
        )
        self.task_semaphore = asyncio.Semaphore(
            self.config.max_concurrent_tasks
        )
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            "phase_start": [],
            "phase_complete": [],
            "phase_error": [],
            "task_start": [],
            "task_complete": [],
            "checkpoint": [],
            "recovery": []
        }
        
        logger.info("Execution Orchestrator initialized")
    
    async def execute_project(
        self,
        project: Project,
        context: Optional[ExecutionContext] = None,
        resume_from: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a complete project build."""
        execution_id = str(uuid.uuid4())
        
        # Initialize state
        self.state = OrchestrationState(
            execution_id=execution_id,
            project=project,
            start_time=datetime.now(),
            context=context or ExecutionContext()
        )
        
        logger.info(f"Starting project execution: {project.config.name}")
        
        try:
            # Generate or validate build plan
            if not project.phases:
                logger.info("Generating build plan...")
                build_plan = await self.planner.generate_plan(
                    project.config.specification
                )
                project.phases = build_plan.phases
            
            # Resume from checkpoint if specified
            if resume_from:
                await self._resume_from_checkpoint(resume_from)
            
            # Execute based on mode
            if self.config.mode == ExecutionMode.SEQUENTIAL:
                result = await self._execute_sequential()
            elif self.config.mode == ExecutionMode.PARALLEL:
                result = await self._execute_parallel()
            elif self.config.mode == ExecutionMode.ADAPTIVE:
                result = await self._execute_adaptive()
            else:  # CHECKPOINT
                result = await self._execute_with_checkpoints()
            
            # Finalize execution
            execution_result = self._finalize_execution(result)
            
            logger.info(
                f"Project execution completed: {execution_result['status']}"
            )
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Project execution failed: {e}")
            
            # Attempt recovery if enabled
            if self.config.enable_recovery:
                return await self._handle_execution_error(e)
            else:
                raise
    
    async def execute_phase(
        self,
        phase: BuildPhase,
        context: ExecutionContext
    ) -> PhaseResult:
        """Execute a single build phase."""
        logger.info(f"Executing phase: {phase.name}")
        
        # Emit phase start event
        await self._emit_event("phase_start", phase=phase)
        
        phase_start = datetime.now()
        
        try:
            # Acquire semaphore for phase execution
            async with self.phase_semaphore:
                # Update state
                self.state.current_phase = phase
                
                # Check dependencies
                if not await self._check_dependencies(phase):
                    raise BuildError(
                        f"Dependencies not met for phase: {phase.name}"
                    )
                
                # Execute phase tasks
                task_results = await self._execute_phase_tasks(phase, context)
                
                # Validate phase results
                validation_result = await self._validate_phase_results(
                    phase, task_results
                )
                
                # Create phase result
                phase_result = PhaseResult(
                    phase_id=phase.id,
                    status=BuildStatus.COMPLETED,
                    start_time=phase_start,
                    end_time=datetime.now(),
                    outputs=task_results,
                    metrics={
                        "task_count": len(phase.tasks),
                        "duration": (datetime.now() - phase_start).total_seconds()
                    }
                )
                
                # Update state
                self.state.completed_phases.append(phase.id)
                self.state.phase_results[phase.id] = phase_result
                
                # Emit phase complete event
                await self._emit_event("phase_complete", phase=phase, result=phase_result)
                
                return phase_result
                
        except Exception as e:
            logger.error(f"Phase execution failed: {phase.name} - {e}")
            
            # Create error result
            phase_result = PhaseResult(
                phase_id=phase.id,
                status=BuildStatus.FAILED,
                start_time=phase_start,
                end_time=datetime.now(),
                error=str(e)
            )
            
            # Update state
            self.state.failed_phases.append(phase.id)
            self.state.phase_results[phase.id] = phase_result
            
            # Emit phase error event
            await self._emit_event("phase_error", phase=phase, error=e)
            
            # Retry if configured
            if self.config.retry_attempts > 0:
                return await self._retry_phase(phase, context)
            
            raise
    
    def register_event_handler(
        self,
        event: str,
        handler: Callable
    ) -> None:
        """Register an event handler."""
        if event in self.event_handlers:
            self.event_handlers[event].append(handler)
            logger.info(f"Registered handler for event: {event}")
    
    async def _execute_sequential(self) -> Dict[str, Any]:
        """Execute phases sequentially."""
        results = {}
        
        for phase in self.state.project.phases:
            try:
                result = await self.execute_phase(phase, self.state.context)
                results[phase.id] = result
                
                # Check if we should continue
                if result.status == BuildStatus.FAILED and not self.config.debug_mode:
                    break
                    
            except Exception as e:
                logger.error(f"Sequential execution error: {e}")
                if not self.config.debug_mode:
                    raise
        
        return results
    
    async def _execute_parallel(self) -> Dict[str, Any]:
        """Execute phases in parallel where possible."""
        results = {}
        executed = set()
        
        while len(executed) < len(self.state.project.phases):
            # Find executable phases
            executable = []
            
            for phase in self.state.project.phases:
                if phase.id in executed:
                    continue
                
                # Check if dependencies are satisfied
                deps_satisfied = all(
                    dep in self.state.completed_phases
                    for dep in phase.dependencies
                )
                
                if deps_satisfied:
                    executable.append(phase)
            
            if not executable:
                # No phases can be executed - check for circular dependencies
                remaining = [
                    p for p in self.state.project.phases
                    if p.id not in executed
                ]
                raise BuildError(
                    f"Cannot execute remaining phases: {[p.name for p in remaining]}"
                )
            
            # Execute phases in parallel
            tasks = []
            for phase in executable[:self.config.max_concurrent_phases]:
                task = asyncio.create_task(
                    self.execute_phase(phase, self.state.context)
                )
                tasks.append((phase.id, task))
                executed.add(phase.id)
            
            # Wait for completion
            for phase_id, task in tasks:
                try:
                    result = await task
                    results[phase_id] = result
                except Exception as e:
                    logger.error(f"Parallel execution error for {phase_id}: {e}")
                    if not self.config.debug_mode:
                        raise
        
        return results
    
    async def _execute_adaptive(self) -> Dict[str, Any]:
        """Execute with adaptive parallelism based on dependencies."""
        results = {}
        
        # Analyze phase dependencies
        dependency_graph = self._build_dependency_graph()
        
        # Calculate execution levels
        levels = self._calculate_execution_levels(dependency_graph)
        
        # Execute by level
        for level, phases in levels.items():
            logger.info(f"Executing level {level} with {len(phases)} phases")
            
            # Execute phases in level concurrently
            tasks = []
            for phase in phases:
                task = asyncio.create_task(
                    self.execute_phase(phase, self.state.context)
                )
                tasks.append((phase.id, task))
            
            # Wait for level completion
            for phase_id, task in tasks:
                try:
                    result = await task
                    results[phase_id] = result
                except Exception as e:
                    logger.error(f"Adaptive execution error for {phase_id}: {e}")
                    if not self.config.debug_mode:
                        raise
        
        return results
    
    async def _execute_with_checkpoints(self) -> Dict[str, Any]:
        """Execute with periodic checkpoints."""
        results = {}
        checkpoint_task = None
        
        try:
            # Start checkpoint task
            checkpoint_task = asyncio.create_task(
                self._checkpoint_loop()
            )
            
            # Execute adaptively
            results = await self._execute_adaptive()
            
            # Final checkpoint
            await self._create_checkpoint()
            
        finally:
            # Cancel checkpoint task
            if checkpoint_task:
                checkpoint_task.cancel()
                try:
                    await checkpoint_task
                except asyncio.CancelledError:
                    pass
        
        return results
    
    async def _execute_phase_tasks(
        self,
        phase: BuildPhase,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute tasks within a phase."""
        task_results = {}
        
        # Group tasks by parallelizability
        task_groups = self._group_tasks(phase.tasks)
        
        for group in task_groups:
            # Execute task group
            group_tasks = []
            
            for task in group:
                # Emit task start event
                await self._emit_event("task_start", task=task)
                
                # Create task
                exec_task = asyncio.create_task(
                    self._execute_single_task(task, context)
                )
                group_tasks.append((task.id, exec_task))
            
            # Wait for group completion
            for task_id, exec_task in group_tasks:
                try:
                    result = await exec_task
                    task_results[task_id] = result
                    
                    # Emit task complete event
                    await self._emit_event("task_complete", task_id=task_id, result=result)
                    
                except Exception as e:
                    logger.error(f"Task execution error for {task_id}: {e}")
                    task_results[task_id] = {"error": str(e)}
                    
                    if not self.config.debug_mode:
                        raise
        
        return task_results
    
    async def _execute_single_task(
        self,
        task: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute a single task."""
        async with self.task_semaphore:
            # Task implementation would go here
            # This is a placeholder
            await asyncio.sleep(0.1)  # Simulate work
            
            return {
                "status": "completed",
                "task_id": task.get("id"),
                "outputs": {}
            }
    
    async def _check_dependencies(self, phase: BuildPhase) -> bool:
        """Check if phase dependencies are satisfied."""
        for dep in phase.dependencies:
            if dep not in self.state.completed_phases:
                return False
        return True
    
    async def _validate_phase_results(
        self,
        phase: BuildPhase,
        results: Dict[str, Any]
    ) -> bool:
        """Validate phase execution results."""
        # Placeholder validation
        return all(
            r.get("status") == "completed"
            for r in results.values()
        )
    
    async def _retry_phase(
        self,
        phase: BuildPhase,
        context: ExecutionContext,
        attempt: int = 1
    ) -> PhaseResult:
        """Retry phase execution."""
        if attempt > self.config.retry_attempts:
            raise BuildError(
                f"Phase {phase.name} failed after {self.config.retry_attempts} attempts"
            )
        
        logger.info(f"Retrying phase {phase.name} (attempt {attempt})")
        
        # Wait before retry
        await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        try:
            return await self.execute_phase(phase, context)
        except Exception:
            return await self._retry_phase(phase, context, attempt + 1)
    
    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph for phases."""
        graph = {}
        
        for phase in self.state.project.phases:
            graph[phase.id] = phase.dependencies
        
        return graph
    
    def _calculate_execution_levels(
        self,
        dependency_graph: Dict[str, List[str]]
    ) -> Dict[int, List[BuildPhase]]:
        """Calculate execution levels based on dependencies."""
        levels = {}
        assigned = set()
        
        # Create phase lookup
        phase_lookup = {p.id: p for p in self.state.project.phases}
        
        level = 0
        while len(assigned) < len(self.state.project.phases):
            current_level = []
            
            for phase in self.state.project.phases:
                if phase.id in assigned:
                    continue
                
                # Check if all dependencies are assigned
                deps_assigned = all(
                    dep in assigned
                    for dep in phase.dependencies
                )
                
                if deps_assigned:
                    current_level.append(phase)
                    assigned.add(phase.id)
            
            if current_level:
                levels[level] = current_level
                level += 1
            else:
                # No progress - likely circular dependency
                break
        
        return levels
    
    def _group_tasks(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Group tasks for parallel execution."""
        # Simple grouping - can be enhanced
        groups = []
        current_group = []
        
        for task in tasks:
            if task.get("parallel", True):
                current_group.append(task)
            else:
                if current_group:
                    groups.append(current_group)
                    current_group = []
                groups.append([task])
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    async def _checkpoint_loop(self) -> None:
        """Periodic checkpoint creation."""
        while True:
            await asyncio.sleep(self.config.checkpoint_interval)
            await self._create_checkpoint()
    
    async def _create_checkpoint(self) -> None:
        """Create execution checkpoint."""
        checkpoint = {
            "execution_id": self.state.execution_id,
            "timestamp": datetime.now().isoformat(),
            "completed_phases": self.state.completed_phases,
            "failed_phases": self.state.failed_phases,
            "phase_results": {
                k: v.to_dict() if hasattr(v, 'to_dict') else v
                for k, v in self.state.phase_results.items()
            },
            "context": self.state.context.to_dict() if self.state.context else None
        }
        
        # Emit checkpoint event
        await self._emit_event("checkpoint", checkpoint=checkpoint)
        
        logger.info(f"Checkpoint created: {checkpoint['timestamp']}")
    
    async def _resume_from_checkpoint(self, checkpoint_id: str) -> None:
        """Resume execution from checkpoint."""
        # Placeholder - would load checkpoint data
        logger.info(f"Resuming from checkpoint: {checkpoint_id}")
        
        # Emit recovery event
        await self._emit_event("recovery", checkpoint_id=checkpoint_id)
    
    async def _handle_execution_error(
        self,
        error: Exception
    ) -> Dict[str, Any]:
        """Handle execution error with recovery."""
        logger.error(f"Handling execution error: {error}")
        
        # Create error result
        return {
            "status": "failed",
            "error": str(error),
            "execution_id": self.state.execution_id,
            "completed_phases": self.state.completed_phases,
            "failed_phases": self.state.failed_phases,
            "recovery_available": True
        }
    
    def _finalize_execution(
        self,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Finalize execution and prepare results."""
        end_time = datetime.now()
        duration = (end_time - self.state.start_time).total_seconds()
        
        # Determine overall status
        if self.state.failed_phases:
            status = "partial"
        elif len(self.state.completed_phases) == len(self.state.project.phases):
            status = "completed"
        else:
            status = "incomplete"
        
        return {
            "status": status,
            "execution_id": self.state.execution_id,
            "project": self.state.project.config.name,
            "duration": duration,
            "phases": {
                "total": len(self.state.project.phases),
                "completed": len(self.state.completed_phases),
                "failed": len(self.state.failed_phases)
            },
            "results": results,
            "errors": [e.to_dict() if hasattr(e, 'to_dict') else str(e) 
                      for e in self.state.errors],
            "metadata": self.state.metadata
        }
    
    async def _emit_event(self, event_name: str, **kwargs) -> None:
        """Emit an event to registered handlers."""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(**kwargs)
                    else:
                        handler(**kwargs)
                except Exception as e:
                    logger.error(f"Event handler error for {event_name}: {e}")
    
    def get_state(self) -> Optional[OrchestrationState]:
        """Get current orchestration state."""
        return self.state
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """Get information about active tasks."""
        return {
            task_id: {
                "done": task.done(),
                "cancelled": task.cancelled()
            }
            for task_id, task in self.active_tasks.items()
        }