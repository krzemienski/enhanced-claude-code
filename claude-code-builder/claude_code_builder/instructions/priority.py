"""Priority execution system for custom instructions."""

import logging
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
from collections import defaultdict
import heapq
from dataclasses import dataclass, field
from enum import Enum

from ..models.custom_instructions import (
    InstructionRule, InstructionSet, Priority,
    InstructionContext
)

logger = logging.getLogger(__name__)


class ExecutionStrategy(Enum):
    """Execution strategy for rules."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PRIORITY_QUEUE = "priority_queue"
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"


@dataclass
class ExecutionPlan:
    """Represents an execution plan for rules."""
    strategy: ExecutionStrategy
    rule_groups: List[List[InstructionRule]]
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of rule execution."""
    rule_name: str
    priority: Priority
    start_time: datetime
    end_time: datetime
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PriorityExecutor:
    """Executes instruction rules based on priority and dependencies."""
    
    def __init__(self):
        """Initialize the priority executor."""
        self.execution_strategies = {
            ExecutionStrategy.SEQUENTIAL: self._execute_sequential,
            ExecutionStrategy.PARALLEL: self._execute_parallel,
            ExecutionStrategy.PRIORITY_QUEUE: self._execute_priority_queue,
            ExecutionStrategy.ROUND_ROBIN: self._execute_round_robin,
            ExecutionStrategy.WEIGHTED: self._execute_weighted
        }
        
        # Execution statistics
        self.stats = defaultdict(lambda: {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "avg_execution_time": 0,
            "priority_distribution": defaultdict(int)
        })
        
        # Execution history
        self.execution_history: List[ExecutionResult] = []
        
        # Priority modifiers
        self.priority_modifiers: Dict[str, Callable[[InstructionRule, InstructionContext], float]] = {}
    
    def create_execution_plan(
        self,
        rules: List[InstructionRule],
        context: Optional[InstructionContext] = None,
        strategy: ExecutionStrategy = ExecutionStrategy.PRIORITY_QUEUE
    ) -> ExecutionPlan:
        """Create an execution plan for the given rules."""
        logger.info(f"Creating execution plan with {strategy.value} strategy for {len(rules)} rules")
        
        # Apply priority modifiers if context provided
        if context:
            rules = self._apply_priority_modifiers(rules, context)
        
        # Sort rules by priority (highest first)
        sorted_rules = sorted(rules, key=lambda r: r.priority.value, reverse=True)
        
        # Build dependency graph
        dependencies = self._build_dependency_graph(sorted_rules)
        
        # Create rule groups based on strategy
        if strategy == ExecutionStrategy.SEQUENTIAL:
            rule_groups = self._group_sequential(sorted_rules, dependencies)
        elif strategy == ExecutionStrategy.PARALLEL:
            rule_groups = self._group_parallel(sorted_rules, dependencies)
        elif strategy == ExecutionStrategy.PRIORITY_QUEUE:
            rule_groups = self._group_priority_queue(sorted_rules, dependencies)
        elif strategy == ExecutionStrategy.ROUND_ROBIN:
            rule_groups = self._group_round_robin(sorted_rules)
        else:  # WEIGHTED
            weights = self._calculate_weights(sorted_rules, context)
            rule_groups = self._group_weighted(sorted_rules, weights)
        
        return ExecutionPlan(
            strategy=strategy,
            rule_groups=rule_groups,
            dependencies=dependencies,
            weights=weights if strategy == ExecutionStrategy.WEIGHTED else {},
            metadata={
                "total_rules": len(rules),
                "group_count": len(rule_groups),
                "has_dependencies": bool(dependencies)
            }
        )
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext] = None,
        executor_func: Optional[Callable] = None
    ) -> List[ExecutionResult]:
        """Execute an execution plan."""
        logger.info(f"Executing plan with {plan.strategy.value} strategy")
        
        # Get execution function
        execute_func = self.execution_strategies[plan.strategy]
        
        # Execute based on strategy
        results = await execute_func(
            plan, input_data, context, executor_func
        )
        
        # Update statistics
        self._update_statistics(results)
        
        # Store in history
        self.execution_history.extend(results)
        
        return results
    
    def add_priority_modifier(
        self,
        name: str,
        modifier_func: Callable[[InstructionRule, InstructionContext], float]
    ) -> None:
        """Add a priority modifier function."""
        self.priority_modifiers[name] = modifier_func
        logger.info(f"Added priority modifier: {name}")
    
    def remove_priority_modifier(self, name: str) -> None:
        """Remove a priority modifier."""
        if name in self.priority_modifiers:
            del self.priority_modifiers[name]
            logger.info(f"Removed priority modifier: {name}")
    
    def _apply_priority_modifiers(
        self,
        rules: List[InstructionRule],
        context: InstructionContext
    ) -> List[InstructionRule]:
        """Apply priority modifiers to rules."""
        if not self.priority_modifiers:
            return rules
        
        modified_rules = []
        
        for rule in rules:
            # Calculate priority adjustment
            adjustment = 0.0
            for modifier_name, modifier_func in self.priority_modifiers.items():
                try:
                    adjustment += modifier_func(rule, context)
                except Exception as e:
                    logger.error(f"Error in priority modifier '{modifier_name}': {e}")
            
            # Create modified rule if needed
            if adjustment != 0:
                # Create a copy with adjusted priority
                new_priority_value = rule.priority.value + adjustment
                new_priority_value = max(0, min(5, new_priority_value))  # Clamp to valid range
                
                # Map to nearest Priority enum
                priority_map = {
                    0: Priority.INFO,
                    1: Priority.LOW,
                    2: Priority.MEDIUM,
                    3: Priority.HIGH,
                    4: Priority.CRITICAL,
                    5: Priority.CRITICAL
                }
                
                new_priority = priority_map[int(new_priority_value)]
                
                # Note: In a real implementation, we'd properly copy the rule
                # For now, we'll just update the metadata
                rule.metadata["adjusted_priority"] = new_priority_value
                rule.metadata["original_priority"] = rule.priority
                
            modified_rules.append(rule)
        
        return modified_rules
    
    def _build_dependency_graph(
        self,
        rules: List[InstructionRule]
    ) -> Dict[str, List[str]]:
        """Build dependency graph from rules."""
        dependencies = {}
        rule_names = {rule.name for rule in rules}
        
        for rule in rules:
            if "depends_on" in rule.metadata:
                deps = rule.metadata["depends_on"]
                if isinstance(deps, str):
                    deps = [deps]
                
                # Filter valid dependencies
                valid_deps = [d for d in deps if d in rule_names]
                if valid_deps:
                    dependencies[rule.name] = valid_deps
        
        return dependencies
    
    def _group_sequential(
        self,
        rules: List[InstructionRule],
        dependencies: Dict[str, List[str]]
    ) -> List[List[InstructionRule]]:
        """Group rules for sequential execution."""
        # Topological sort considering dependencies
        sorted_rules = self._topological_sort(rules, dependencies)
        
        # Each rule in its own group for sequential execution
        return [[rule] for rule in sorted_rules]
    
    def _group_parallel(
        self,
        rules: List[InstructionRule],
        dependencies: Dict[str, List[str]]
    ) -> List[List[InstructionRule]]:
        """Group rules for parallel execution."""
        # Group rules that can be executed in parallel
        groups = []
        processed = set()
        rule_by_name = {rule.name: rule for rule in rules}
        
        while len(processed) < len(rules):
            # Find rules that can be executed now
            current_group = []
            
            for rule in rules:
                if rule.name in processed:
                    continue
                
                # Check if dependencies are satisfied
                if rule.name in dependencies:
                    deps_satisfied = all(
                        dep in processed for dep in dependencies[rule.name]
                    )
                    if not deps_satisfied:
                        continue
                
                current_group.append(rule)
            
            if not current_group:
                # Handle circular dependencies or missing rules
                remaining = [r for r in rules if r.name not in processed]
                if remaining:
                    current_group = [remaining[0]]
                else:
                    break
            
            groups.append(current_group)
            processed.update(rule.name for rule in current_group)
        
        return groups
    
    def _group_priority_queue(
        self,
        rules: List[InstructionRule],
        dependencies: Dict[str, List[str]]
    ) -> List[List[InstructionRule]]:
        """Group rules using priority queue approach."""
        # Group by priority level, respecting dependencies
        priority_groups = defaultdict(list)
        
        for rule in rules:
            priority_groups[rule.priority].append(rule)
        
        # Sort priority levels (highest first)
        sorted_priorities = sorted(priority_groups.keys(), key=lambda p: p.value, reverse=True)
        
        groups = []
        for priority in sorted_priorities:
            # Within same priority, group by parallelizability
            priority_rules = priority_groups[priority]
            parallel_groups = self._group_parallel(priority_rules, dependencies)
            groups.extend(parallel_groups)
        
        return groups
    
    def _group_round_robin(
        self,
        rules: List[InstructionRule]
    ) -> List[List[InstructionRule]]:
        """Group rules for round-robin execution."""
        # Distribute rules across groups evenly
        num_groups = min(4, len(rules))  # Max 4 groups for round-robin
        groups = [[] for _ in range(num_groups)]
        
        for i, rule in enumerate(rules):
            groups[i % num_groups].append(rule)
        
        return groups
    
    def _group_weighted(
        self,
        rules: List[InstructionRule],
        weights: Dict[str, float]
    ) -> List[List[InstructionRule]]:
        """Group rules based on weights."""
        # Sort by weight (highest first)
        sorted_rules = sorted(
            rules,
            key=lambda r: weights.get(r.name, 0.5),
            reverse=True
        )
        
        # Group by weight thresholds
        groups = []
        thresholds = [0.8, 0.6, 0.4, 0.2]
        
        for i, threshold in enumerate(thresholds):
            group = []
            min_weight = thresholds[i+1] if i+1 < len(thresholds) else 0
            
            for rule in sorted_rules:
                weight = weights.get(rule.name, 0.5)
                if min_weight <= weight < threshold:
                    group.append(rule)
            
            if group:
                groups.append(group)
        
        return groups
    
    def _calculate_weights(
        self,
        rules: List[InstructionRule],
        context: Optional[InstructionContext]
    ) -> Dict[str, float]:
        """Calculate execution weights for rules."""
        weights = {}
        
        for rule in rules:
            # Base weight from priority
            base_weight = rule.priority.value / 5.0
            
            # Adjust based on metadata
            if "weight" in rule.metadata:
                base_weight = rule.metadata["weight"]
            
            # Context-based adjustments
            if context:
                # Boost weight for matching environment
                if rule.metadata.get("preferred_env") == context.environment:
                    base_weight += 0.1
                
                # Boost weight for matching phase
                if rule.metadata.get("preferred_phase") == context.phase:
                    base_weight += 0.1
            
            # Normalize to [0, 1]
            weights[rule.name] = min(max(base_weight, 0), 1)
        
        return weights
    
    def _topological_sort(
        self,
        rules: List[InstructionRule],
        dependencies: Dict[str, List[str]]
    ) -> List[InstructionRule]:
        """Perform topological sort on rules based on dependencies."""
        # Build adjacency list
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        rule_by_name = {rule.name: rule for rule in rules}
        
        # Initialize
        for rule in rules:
            in_degree[rule.name] = 0
        
        # Build graph
        for rule_name, deps in dependencies.items():
            for dep in deps:
                if dep in rule_by_name:
                    graph[dep].append(rule_name)
                    in_degree[rule_name] += 1
        
        # Find rules with no dependencies
        queue = [rule.name for rule in rules if in_degree[rule.name] == 0]
        sorted_names = []
        
        while queue:
            # Sort queue by priority for deterministic order
            queue.sort(key=lambda n: rule_by_name[n].priority.value, reverse=True)
            
            current = queue.pop(0)
            sorted_names.append(current)
            
            # Update dependencies
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Convert back to rules
        sorted_rules = []
        for name in sorted_names:
            if name in rule_by_name:
                sorted_rules.append(rule_by_name[name])
        
        # Add any remaining rules (cycles or disconnected)
        for rule in rules:
            if rule not in sorted_rules:
                sorted_rules.append(rule)
        
        return sorted_rules
    
    async def _execute_sequential(
        self,
        plan: ExecutionPlan,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext],
        executor_func: Optional[Callable]
    ) -> List[ExecutionResult]:
        """Execute rules sequentially."""
        results = []
        
        for group in plan.rule_groups:
            for rule in group:
                result = await self._execute_single_rule(
                    rule, input_data, context, executor_func
                )
                results.append(result)
                
                # Update input data with output if successful
                if result.success and isinstance(result.output, dict):
                    input_data.update(result.output.get("data", {}))
        
        return results
    
    async def _execute_parallel(
        self,
        plan: ExecutionPlan,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext],
        executor_func: Optional[Callable]
    ) -> List[ExecutionResult]:
        """Execute rules in parallel groups."""
        import asyncio
        
        results = []
        
        for group in plan.rule_groups:
            # Execute group in parallel
            group_tasks = [
                self._execute_single_rule(rule, input_data, context, executor_func)
                for rule in group
            ]
            
            group_results = await asyncio.gather(*group_tasks)
            results.extend(group_results)
            
            # Update input data with outputs
            for result in group_results:
                if result.success and isinstance(result.output, dict):
                    input_data.update(result.output.get("data", {}))
        
        return results
    
    async def _execute_priority_queue(
        self,
        plan: ExecutionPlan,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext],
        executor_func: Optional[Callable]
    ) -> List[ExecutionResult]:
        """Execute rules using priority queue."""
        # Use heap for priority queue
        queue = []
        
        # Add all rules to queue
        for group_idx, group in enumerate(plan.rule_groups):
            for rule in group:
                # Use negative priority for max heap
                heapq.heappush(queue, (-rule.priority.value, group_idx, rule))
        
        results = []
        
        while queue:
            _, _, rule = heapq.heappop(queue)
            result = await self._execute_single_rule(
                rule, input_data, context, executor_func
            )
            results.append(result)
            
            if result.success and isinstance(result.output, dict):
                input_data.update(result.output.get("data", {}))
        
        return results
    
    async def _execute_round_robin(
        self,
        plan: ExecutionPlan,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext],
        executor_func: Optional[Callable]
    ) -> List[ExecutionResult]:
        """Execute rules in round-robin fashion."""
        results = []
        group_indices = [0] * len(plan.rule_groups)
        
        # Continue until all groups are exhausted
        while any(idx < len(group) for idx, group in zip(group_indices, plan.rule_groups)):
            for i, group in enumerate(plan.rule_groups):
                if group_indices[i] < len(group):
                    rule = group[group_indices[i]]
                    result = await self._execute_single_rule(
                        rule, input_data, context, executor_func
                    )
                    results.append(result)
                    group_indices[i] += 1
                    
                    if result.success and isinstance(result.output, dict):
                        input_data.update(result.output.get("data", {}))
        
        return results
    
    async def _execute_weighted(
        self,
        plan: ExecutionPlan,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext],
        executor_func: Optional[Callable]
    ) -> List[ExecutionResult]:
        """Execute rules based on weights."""
        results = []
        
        # Execute in weight order (groups already sorted by weight)
        for group in plan.rule_groups:
            for rule in group:
                result = await self._execute_single_rule(
                    rule, input_data, context, executor_func
                )
                results.append(result)
                
                if result.success and isinstance(result.output, dict):
                    input_data.update(result.output.get("data", {}))
        
        return results
    
    async def _execute_single_rule(
        self,
        rule: InstructionRule,
        input_data: Dict[str, Any],
        context: Optional[InstructionContext],
        executor_func: Optional[Callable]
    ) -> ExecutionResult:
        """Execute a single rule."""
        start_time = datetime.now()
        
        try:
            # Use provided executor or default
            if executor_func:
                output = await executor_func(rule, input_data, context)
            else:
                # Default execution (simplified)
                output = {
                    "status": "executed",
                    "rule": rule.name,
                    "action": rule.action,
                    "data": {}
                }
            
            end_time = datetime.now()
            
            return ExecutionResult(
                rule_name=rule.name,
                priority=rule.priority,
                start_time=start_time,
                end_time=end_time,
                success=True,
                output=output,
                metadata={
                    "execution_time": (end_time - start_time).total_seconds()
                }
            )
            
        except Exception as e:
            end_time = datetime.now()
            logger.error(f"Error executing rule '{rule.name}': {e}")
            
            return ExecutionResult(
                rule_name=rule.name,
                priority=rule.priority,
                start_time=start_time,
                end_time=end_time,
                success=False,
                output=None,
                error=str(e),
                metadata={
                    "execution_time": (end_time - start_time).total_seconds()
                }
            )
    
    def _update_statistics(self, results: List[ExecutionResult]) -> None:
        """Update execution statistics."""
        for result in results:
            env = "default"  # Could be extracted from context
            stats = self.stats[env]
            
            stats["total_executions"] += 1
            if result.success:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
            
            # Update priority distribution
            stats["priority_distribution"][result.priority.value] += 1
            
            # Update average execution time
            exec_time = result.metadata.get("execution_time", 0)
            total = stats["total_executions"]
            stats["avg_execution_time"] = (
                (stats["avg_execution_time"] * (total - 1) + exec_time) / total
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            "environments": dict(self.stats),
            "total_executions": sum(s["total_executions"] for s in self.stats.values()),
            "success_rate": self._calculate_success_rate(),
            "priority_distribution": self._aggregate_priority_distribution()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate."""
        total = sum(s["total_executions"] for s in self.stats.values())
        successful = sum(s["successful"] for s in self.stats.values())
        
        return successful / total if total > 0 else 0.0
    
    def _aggregate_priority_distribution(self) -> Dict[str, int]:
        """Aggregate priority distribution across all environments."""
        aggregated = defaultdict(int)
        
        for stats in self.stats.values():
            for priority, count in stats["priority_distribution"].items():
                aggregated[f"Priority_{priority}"] = aggregated.get(f"Priority_{priority}", 0) + count
        
        return dict(aggregated)