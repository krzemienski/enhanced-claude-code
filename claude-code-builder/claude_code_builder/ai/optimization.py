"""Plan optimization for maximum efficiency and quality."""

from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

from ..models.phase import Phase, Task, PhaseStatus, TaskStatus
from ..models.cost import CostEntry, CostCategory
from ..models.base import BaseModel
from ..exceptions.base import ClaudeCodeBuilderError
from .dependency_resolver import DependencyResolver
from .complexity_estimator import ComplexityEstimator
from .risk_assessor import RiskAssessor

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Optimization strategies."""
    SPEED = "speed"  # Minimize time
    QUALITY = "quality"  # Maximize quality
    COST = "cost"  # Minimize cost
    BALANCED = "balanced"  # Balance all factors
    RISK_AVERSE = "risk_averse"  # Minimize risk


@dataclass
class OptimizationConstraints:
    """Constraints for optimization."""
    max_duration: Optional[timedelta] = None
    max_cost: Optional[float] = None
    max_parallel_tasks: int = 5
    required_quality_score: float = 0.8
    acceptable_risk_level: str = "medium"
    preserve_dependencies: bool = True
    allow_phase_merging: bool = False
    allow_task_splitting: bool = True


@dataclass
class OptimizationResult:
    """Result of plan optimization."""
    optimized_phases: List[Phase]
    improvements: Dict[str, Any]
    estimated_time_saved: timedelta
    estimated_cost_saved: float
    quality_impact: float
    risk_impact: float
    applied_techniques: List[str]


class PlanOptimizer:
    """Optimize execution plans for efficiency and quality."""
    
    def __init__(
        self,
        dependency_resolver: DependencyResolver,
        complexity_estimator: ComplexityEstimator,
        risk_assessor: RiskAssessor
    ):
        """Initialize optimizer with required components."""
        self.dependency_resolver = dependency_resolver
        self.complexity_estimator = complexity_estimator
        self.risk_assessor = risk_assessor
    
    async def optimize_plan(
        self,
        phases: List[Phase],
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
        constraints: Optional[OptimizationConstraints] = None
    ) -> OptimizationResult:
        """
        Optimize execution plan based on strategy and constraints.
        
        Args:
            phases: Phases to optimize
            strategy: Optimization strategy
            constraints: Optimization constraints
            
        Returns:
            Optimization result with improved plan
        """
        if not constraints:
            constraints = OptimizationConstraints()
        
        logger.info(f"Optimizing plan with {strategy.value} strategy")
        
        # Track improvements
        improvements = {
            "parallelization": [],
            "task_merging": [],
            "phase_reordering": [],
            "resource_optimization": [],
            "risk_mitigation": []
        }
        
        # Clone phases for optimization
        optimized_phases = [phase.model_copy(deep=True) for phase in phases]
        
        # Apply optimization techniques based on strategy
        if strategy == OptimizationStrategy.SPEED:
            optimized_phases = await self._optimize_for_speed(
                optimized_phases, constraints, improvements
            )
        elif strategy == OptimizationStrategy.QUALITY:
            optimized_phases = await self._optimize_for_quality(
                optimized_phases, constraints, improvements
            )
        elif strategy == OptimizationStrategy.COST:
            optimized_phases = await self._optimize_for_cost(
                optimized_phases, constraints, improvements
            )
        elif strategy == OptimizationStrategy.RISK_AVERSE:
            optimized_phases = await self._optimize_for_risk(
                optimized_phases, constraints, improvements
            )
        else:  # BALANCED
            optimized_phases = await self._optimize_balanced(
                optimized_phases, constraints, improvements
            )
        
        # Calculate improvements
        original_metrics = await self._calculate_plan_metrics(phases)
        optimized_metrics = await self._calculate_plan_metrics(optimized_phases)
        
        time_saved = original_metrics["total_duration"] - optimized_metrics["total_duration"]
        cost_saved = original_metrics["total_cost"] - optimized_metrics["total_cost"]
        
        return OptimizationResult(
            optimized_phases=optimized_phases,
            improvements=improvements,
            estimated_time_saved=time_saved,
            estimated_cost_saved=cost_saved,
            quality_impact=optimized_metrics["quality_score"] - original_metrics["quality_score"],
            risk_impact=optimized_metrics["risk_score"] - original_metrics["risk_score"],
            applied_techniques=list({
                tech for techniques in improvements.values() 
                for tech in techniques
            })
        )
    
    async def _optimize_for_speed(
        self,
        phases: List[Phase],
        constraints: OptimizationConstraints,
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Optimize for minimum execution time."""
        # Maximize parallelization
        phases = await self._maximize_parallelization(phases, constraints, improvements)
        
        # Merge compatible tasks
        if constraints.allow_task_splitting:
            phases = await self._merge_compatible_tasks(phases, improvements)
        
        # Optimize resource allocation
        phases = await self._optimize_resource_allocation(phases, improvements)
        
        # Reorder for critical path
        phases = await self._optimize_critical_path(phases, constraints, improvements)
        
        return phases
    
    async def _optimize_for_quality(
        self,
        phases: List[Phase],
        constraints: OptimizationConstraints,
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Optimize for maximum quality."""
        # Add quality checkpoints
        phases = await self._add_quality_checkpoints(phases, improvements)
        
        # Increase validation tasks
        phases = await self._enhance_validation_tasks(phases, improvements)
        
        # Add review cycles
        phases = await self._add_review_cycles(phases, improvements)
        
        # Optimize test coverage
        phases = await self._optimize_test_coverage(phases, improvements)
        
        return phases
    
    async def _optimize_for_cost(
        self,
        phases: List[Phase],
        constraints: OptimizationConstraints,
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Optimize for minimum cost."""
        # Minimize AI token usage
        phases = await self._minimize_token_usage(phases, improvements)
        
        # Batch similar operations
        phases = await self._batch_operations(phases, improvements)
        
        # Use cheaper models where appropriate
        phases = await self._optimize_model_selection(phases, improvements)
        
        # Reduce redundant operations
        phases = await self._eliminate_redundancy(phases, improvements)
        
        return phases
    
    async def _optimize_for_risk(
        self,
        phases: List[Phase],
        constraints: OptimizationConstraints,
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Optimize for minimum risk."""
        # Add safety checkpoints
        phases = await self._add_safety_checkpoints(phases, improvements)
        
        # Increase validation
        phases = await self._increase_validation(phases, improvements)
        
        # Add rollback points
        phases = await self._add_rollback_points(phases, improvements)
        
        # Sequential critical operations
        phases = await self._sequentialize_critical_ops(phases, improvements)
        
        return phases
    
    async def _optimize_balanced(
        self,
        phases: List[Phase],
        constraints: OptimizationConstraints,
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Balance all optimization factors."""
        # Apply moderate parallelization
        phases = await self._moderate_parallelization(phases, constraints, improvements)
        
        # Add essential quality checks
        phases = await self._add_essential_quality_checks(phases, improvements)
        
        # Optimize cost-effectively
        phases = await self._cost_effective_optimization(phases, improvements)
        
        # Mitigate major risks
        phases = await self._mitigate_major_risks(phases, improvements)
        
        return phases
    
    async def _maximize_parallelization(
        self,
        phases: List[Phase],
        constraints: OptimizationConstraints,
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Maximize parallel execution of tasks."""
        for phase in phases:
            # Analyze task dependencies
            dependency_graph = await self.dependency_resolver.build_dependency_graph([phase])
            
            # Find independent task groups
            independent_groups = self._find_independent_task_groups(
                phase.tasks, dependency_graph
            )
            
            # Mark tasks for parallel execution
            for group in independent_groups:
                if len(group) > 1:
                    for task in group:
                        task.metadata["parallel_group"] = independent_groups.index(group)
                    
                    improvements["parallelization"].append(
                        f"Parallelized {len(group)} tasks in {phase.name}"
                    )
        
        return phases
    
    async def _merge_compatible_tasks(
        self,
        phases: List[Phase],
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Merge compatible tasks to reduce overhead."""
        for phase in phases:
            merged_tasks = []
            skip_indices = set()
            
            for i, task1 in enumerate(phase.tasks):
                if i in skip_indices:
                    continue
                
                # Find compatible tasks to merge
                compatible_tasks = [task1]
                for j, task2 in enumerate(phase.tasks[i+1:], i+1):
                    if j in skip_indices:
                        continue
                    
                    if self._are_tasks_compatible(task1, task2):
                        compatible_tasks.append(task2)
                        skip_indices.add(j)
                
                if len(compatible_tasks) > 1:
                    # Create merged task
                    merged_task = self._merge_tasks(compatible_tasks)
                    merged_tasks.append(merged_task)
                    
                    improvements["task_merging"].append(
                        f"Merged {len(compatible_tasks)} tasks in {phase.name}"
                    )
                else:
                    merged_tasks.append(task1)
            
            phase.tasks = merged_tasks
        
        return phases
    
    async def _optimize_critical_path(
        self,
        phases: List[Phase],
        constraints: OptimizationConstraints,
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Optimize execution order for critical path."""
        # Calculate critical path
        critical_path = await self._calculate_critical_path(phases)
        
        # Reorder phases to prioritize critical path
        reordered_phases = []
        critical_phase_ids = {task.phase_id for task in critical_path}
        
        # Add critical phases first
        for phase in phases:
            if phase.id in critical_phase_ids:
                reordered_phases.append(phase)
        
        # Add non-critical phases
        for phase in phases:
            if phase.id not in critical_phase_ids:
                reordered_phases.append(phase)
        
        if reordered_phases != phases:
            improvements["phase_reordering"].append(
                "Reordered phases to optimize critical path"
            )
        
        return reordered_phases
    
    async def _calculate_plan_metrics(
        self,
        phases: List[Phase]
    ) -> Dict[str, Any]:
        """Calculate metrics for a plan."""
        total_duration = timedelta()
        total_cost = 0.0
        total_complexity = 0.0
        risk_scores = []
        
        for phase in phases:
            # Duration (considering parallelization)
            phase_duration = await self._calculate_phase_duration(phase)
            total_duration += phase_duration
            
            # Cost
            for task in phase.tasks:
                if task.cost_estimate:
                    total_cost += task.cost_estimate.total_cost
            
            # Complexity
            complexity = await self.complexity_estimator.estimate_phase_complexity(phase)
            total_complexity += complexity.overall_score
            
            # Risk
            risks = await self.risk_assessor.assess_phase_risks(phase)
            risk_scores.extend([r.severity.value for r in risks])
        
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        quality_score = 1.0 - (avg_risk / 10.0)  # Simple quality metric
        
        return {
            "total_duration": total_duration,
            "total_cost": total_cost,
            "average_complexity": total_complexity / len(phases),
            "quality_score": quality_score,
            "risk_score": avg_risk
        }
    
    async def _calculate_phase_duration(self, phase: Phase) -> timedelta:
        """Calculate phase duration considering parallelization."""
        if not phase.tasks:
            return timedelta()
        
        # Group tasks by parallel group
        parallel_groups = {}
        for task in phase.tasks:
            group = task.metadata.get("parallel_group", task.id)
            if group not in parallel_groups:
                parallel_groups[group] = []
            parallel_groups[group].append(task)
        
        # Calculate max duration for each group
        total_duration = timedelta()
        for group_tasks in parallel_groups.values():
            group_duration = timedelta()
            for task in group_tasks:
                if task.estimated_duration:
                    task_duration = timedelta(seconds=task.estimated_duration)
                    group_duration = max(group_duration, task_duration)
            total_duration += group_duration
        
        return total_duration
    
    def _find_independent_task_groups(
        self,
        tasks: List[Task],
        dependency_graph: Dict[str, Set[str]]
    ) -> List[List[Task]]:
        """Find groups of tasks that can run in parallel."""
        groups = []
        processed = set()
        
        for task in tasks:
            if task.id in processed:
                continue
            
            # Find all tasks that can run with this task
            group = [task]
            processed.add(task.id)
            
            for other_task in tasks:
                if other_task.id in processed:
                    continue
                
                # Check if tasks are independent
                if (task.id not in dependency_graph.get(other_task.id, set()) and
                    other_task.id not in dependency_graph.get(task.id, set())):
                    group.append(other_task)
                    processed.add(other_task.id)
            
            groups.append(group)
        
        return groups
    
    def _are_tasks_compatible(self, task1: Task, task2: Task) -> bool:
        """Check if two tasks can be merged."""
        # Same type and no dependencies between them
        return (
            task1.type == task2.type and
            task1.id not in task2.dependencies and
            task2.id not in task1.dependencies and
            task1.metadata.get("category") == task2.metadata.get("category")
        )
    
    def _merge_tasks(self, tasks: List[Task]) -> Task:
        """Merge multiple tasks into one."""
        base_task = tasks[0].model_copy(deep=True)
        
        # Combine descriptions and details
        descriptions = [t.description for t in tasks]
        details = [t.implementation_details for t in tasks if t.implementation_details]
        
        base_task.title = f"Combined: {', '.join(t.title for t in tasks[:2])}..."
        base_task.description = " AND ".join(descriptions)
        if details:
            base_task.implementation_details = "\n\n".join(details)
        
        # Combine dependencies
        all_deps = set()
        for task in tasks:
            all_deps.update(task.dependencies)
        base_task.dependencies = list(all_deps)
        
        # Sum estimates
        if all(t.estimated_duration for t in tasks):
            base_task.estimated_duration = sum(t.estimated_duration for t in tasks)
        
        if all(t.cost_estimate for t in tasks):
            total_cost = sum(t.cost_estimate.total_cost for t in tasks)
            base_task.cost_estimate = CostEntry(
                total_cost=total_cost,
                breakdown={
                    CostCategory.COMPUTE: total_cost * 0.7,
                    CostCategory.API: total_cost * 0.3
                }
            )
        
        base_task.metadata["merged_tasks"] = [t.id for t in tasks]
        
        return base_task
    
    async def _calculate_critical_path(self, phases: List[Phase]) -> List[Task]:
        """Calculate the critical path through all phases."""
        all_tasks = []
        for phase in phases:
            for task in phase.tasks:
                task.phase_id = phase.id  # Track phase
                all_tasks.append(task)
        
        # Build dependency graph
        dependency_graph = {}
        for task in all_tasks:
            dependency_graph[task.id] = set(task.dependencies)
        
        # Find tasks with no dependents (end tasks)
        end_tasks = []
        for task in all_tasks:
            has_dependents = False
            for deps in dependency_graph.values():
                if task.id in deps:
                    has_dependents = True
                    break
            if not has_dependents:
                end_tasks.append(task)
        
        # Work backwards to find critical path
        critical_path = []
        visited = set()
        
        def find_longest_path(task: Task, current_path: List[Task]) -> List[Task]:
            if task.id in visited:
                return current_path
            
            visited.add(task.id)
            current_path = [task] + current_path
            
            if not task.dependencies:
                return current_path
            
            longest = current_path
            for dep_id in task.dependencies:
                dep_task = next((t for t in all_tasks if t.id == dep_id), None)
                if dep_task:
                    path = find_longest_path(dep_task, current_path[:])
                    if len(path) > len(longest):
                        longest = path
            
            return longest
        
        # Find longest path from any end task
        for end_task in end_tasks:
            path = find_longest_path(end_task, [])
            if len(path) > len(critical_path):
                critical_path = path
        
        return critical_path
    
    # Additional optimization methods would be implemented here...
    async def _add_quality_checkpoints(
        self,
        phases: List[Phase],
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Add quality checkpoints to phases."""
        for phase in phases:
            if len(phase.tasks) > 3:
                # Add checkpoint after every 3 tasks
                checkpoint_task = Task(
                    id=f"{phase.id}_quality_checkpoint",
                    title="Quality Checkpoint",
                    description="Validate quality of completed tasks",
                    type="validation",
                    priority="high",
                    metadata={"checkpoint_type": "quality"}
                )
                phase.tasks.insert(len(phase.tasks) // 2, checkpoint_task)
                improvements["quality"].append(f"Added quality checkpoint to {phase.name}")
        return phases
    
    async def _minimize_token_usage(
        self,
        phases: List[Phase],
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Minimize AI token usage across tasks."""
        for phase in phases:
            for task in phase.tasks:
                if task.metadata.get("uses_ai", True):
                    # Optimize prompts
                    task.metadata["optimized_prompts"] = True
                    improvements["cost"].append(f"Optimized prompts for {task.title}")
        return phases
    
    async def _add_safety_checkpoints(
        self,
        phases: List[Phase],
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Add safety checkpoints for risk mitigation."""
        for phase in phases:
            # Add rollback checkpoint before risky operations
            risky_tasks = [t for t in phase.tasks if t.metadata.get("risk_level", 0) > 5]
            for task in risky_tasks:
                checkpoint = Task(
                    id=f"{task.id}_safety",
                    title=f"Safety checkpoint for {task.title}",
                    description="Create restore point before risky operation",
                    type="checkpoint",
                    priority="high",
                    dependencies=[],
                    metadata={"checkpoint_type": "safety"}
                )
                idx = phase.tasks.index(task)
                phase.tasks.insert(idx, checkpoint)
                task.dependencies.append(checkpoint.id)
                improvements["risk_mitigation"].append(f"Added safety checkpoint for {task.title}")
        return phases
    
    async def _moderate_parallelization(
        self,
        phases: List[Phase],
        constraints: OptimizationConstraints,
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Apply moderate parallelization for balanced approach."""
        # Limit parallel groups to 3 tasks max
        for phase in phases:
            parallel_groups = {}
            for task in phase.tasks:
                if "parallel_group" in task.metadata:
                    group = task.metadata["parallel_group"]
                    if group not in parallel_groups:
                        parallel_groups[group] = []
                    parallel_groups[group].append(task)
            
            # Split large groups
            for group_id, tasks in parallel_groups.items():
                if len(tasks) > 3:
                    for i, task in enumerate(tasks[3:]):
                        task.metadata["parallel_group"] = f"{group_id}_split_{i//3}"
                    improvements["parallelization"].append(
                        f"Split large parallel group in {phase.name} for balance"
                    )
        return phases
    
    async def _add_essential_quality_checks(
        self,
        phases: List[Phase],
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Add only essential quality checks."""
        critical_phases = [p for p in phases if p.metadata.get("critical", False)]
        for phase in critical_phases:
            quality_task = Task(
                id=f"{phase.id}_quality",
                title=f"Quality validation for {phase.name}",
                description="Validate critical phase outputs",
                type="validation",
                priority="high",
                metadata={"validation_type": "essential"}
            )
            phase.tasks.append(quality_task)
            improvements["quality"].append(f"Added essential quality check to {phase.name}")
        return phases
    
    async def _cost_effective_optimization(
        self,
        phases: List[Phase],
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Apply cost-effective optimizations."""
        for phase in phases:
            # Batch small AI operations
            ai_tasks = [t for t in phase.tasks if t.metadata.get("uses_ai", False)]
            if len(ai_tasks) > 5:
                # Create batched task
                batched = Task(
                    id=f"{phase.id}_batched",
                    title="Batched AI operations",
                    description=f"Process {len(ai_tasks)} AI tasks in batch",
                    type="batch",
                    metadata={"batched_tasks": [t.id for t in ai_tasks]}
                )
                # Replace individual tasks with batch
                phase.tasks = [t for t in phase.tasks if t not in ai_tasks]
                phase.tasks.append(batched)
                improvements["cost"].append(f"Batched {len(ai_tasks)} AI operations in {phase.name}")
        return phases
    
    async def _mitigate_major_risks(
        self,
        phases: List[Phase],
        improvements: Dict[str, List[str]]
    ) -> List[Phase]:
        """Mitigate only major risks."""
        for phase in phases:
            # Assess phase risks
            risks = await self.risk_assessor.assess_phase_risks(phase)
            major_risks = [r for r in risks if r.severity.value >= 7]
            
            if major_risks:
                mitigation_task = Task(
                    id=f"{phase.id}_risk_mitigation",
                    title="Risk mitigation",
                    description=f"Mitigate {len(major_risks)} major risks",
                    type="mitigation",
                    priority="high",
                    metadata={"risks": [r.type.value for r in major_risks]}
                )
                phase.tasks.insert(0, mitigation_task)
                improvements["risk_mitigation"].append(
                    f"Added mitigation for {len(major_risks)} major risks in {phase.name}"
                )
        return phases