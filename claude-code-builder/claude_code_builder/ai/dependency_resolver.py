"""Dependency resolver for AI planning."""

from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict, deque

from ..models import Phase, Task, Dependency, MemoryStore
from ..config import AIConfig
from ..logging import logger
from ..exceptions import PlanningError


@dataclass
class DependencyNode:
    """Node in dependency graph."""
    
    id: str
    name: str
    node_type: str  # "phase" or "task"
    dependencies: Set[str]
    dependents: Set[str]
    level: int = 0
    critical_path: bool = False


class DependencyResolver:
    """Resolves and optimizes dependencies between phases and tasks."""
    
    def __init__(self, ai_config: AIConfig, memory_store: MemoryStore):
        """Initialize dependency resolver."""
        self.ai_config = ai_config
        self.memory_store = memory_store
    
    async def resolve(self, phases: List[Phase]) -> None:
        """Resolve dependencies for all phases."""
        logger.info("Resolving phase and task dependencies")
        
        try:
            # Build dependency graph
            graph = self._build_dependency_graph(phases)
            
            # Detect and resolve circular dependencies
            self._resolve_circular_dependencies(graph)
            
            # Calculate dependency levels
            self._calculate_levels(graph)
            
            # Identify critical path
            critical_path = self._find_critical_path(graph, phases)
            
            # Optimize dependencies if enabled
            if self.ai_config.dependency_resolution:
                self._optimize_dependencies(graph, phases)
            
            # Update phases with resolved dependencies
            self._update_phases(graph, phases)
            
            # Validate final dependencies
            self._validate_dependencies(phases)
            
            logger.info(
                f"Resolved dependencies for {len(phases)} phases, "
                f"critical path length: {len(critical_path)}"
            )
            
        except Exception as e:
            logger.error("Dependency resolution failed", error=str(e))
            raise PlanningError(f"Failed to resolve dependencies: {str(e)}", cause=e)
    
    def _build_dependency_graph(self, phases: List[Phase]) -> Dict[str, DependencyNode]:
        """Build complete dependency graph."""
        graph = {}
        
        # Add phase nodes
        for phase in phases:
            node = DependencyNode(
                id=phase.id,
                name=phase.name,
                node_type="phase",
                dependencies=set(),
                dependents=set()
            )
            
            # Add phase dependencies
            for dep in phase.dependencies:
                node.dependencies.add(dep.source_id)
            
            graph[phase.id] = node
            
            # Add task nodes
            for task in phase.tasks:
                task_node = DependencyNode(
                    id=task.id,
                    name=task.name,
                    node_type="task",
                    dependencies=set(task.dependencies),
                    dependents=set()
                )
                
                # Task implicitly depends on its phase start
                task_node.dependencies.add(f"{phase.id}_start")
                
                graph[task.id] = task_node
            
            # Add phase start/end nodes for better modeling
            graph[f"{phase.id}_start"] = DependencyNode(
                id=f"{phase.id}_start",
                name=f"{phase.name} Start",
                node_type="phase_marker",
                dependencies={phase.id},
                dependents=set()
            )
            
            graph[f"{phase.id}_end"] = DependencyNode(
                id=f"{phase.id}_end",
                name=f"{phase.name} End",
                node_type="phase_marker",
                dependencies=set(),
                dependents=set()
            )
        
        # Build dependent relationships
        for node_id, node in graph.items():
            for dep_id in node.dependencies:
                if dep_id in graph:
                    graph[dep_id].dependents.add(node_id)
        
        return graph
    
    def _resolve_circular_dependencies(self, graph: Dict[str, DependencyNode]) -> None:
        """Detect and resolve circular dependencies."""
        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node_id: str, path: List[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            node = graph.get(node_id)
            if node:
                for dep_id in node.dependencies:
                    if dep_id not in visited:
                        dfs(dep_id, path[:])
                    elif dep_id in rec_stack:
                        # Found cycle
                        cycle_start = path.index(dep_id)
                        cycle = path[cycle_start:] + [dep_id]
                        cycles.append(cycle)
            
            rec_stack.remove(node_id)
        
        # Check all nodes
        for node_id in graph:
            if node_id not in visited:
                dfs(node_id, [])
        
        # Resolve cycles
        for cycle in cycles:
            logger.warning(f"Circular dependency detected: {' -> '.join(cycle)}")
            
            # Find weakest link to break
            weakest_link = self._find_weakest_link(cycle, graph)
            if weakest_link:
                source_id, target_id = weakest_link
                graph[target_id].dependencies.discard(source_id)
                graph[source_id].dependents.discard(target_id)
                logger.info(f"Broke circular dependency: {source_id} -> {target_id}")
    
    def _find_weakest_link(
        self,
        cycle: List[str],
        graph: Dict[str, DependencyNode]
    ) -> Optional[Tuple[str, str]]:
        """Find the weakest link in a dependency cycle."""
        # Prefer to break links between tasks over phases
        # Prefer to break links with fewer dependent nodes
        
        min_impact = float('inf')
        weakest_link = None
        
        for i in range(len(cycle) - 1):
            source_id = cycle[i]
            target_id = cycle[i + 1]
            
            source_node = graph.get(source_id)
            target_node = graph.get(target_id)
            
            if source_node and target_node:
                # Calculate impact of breaking this link
                impact = len(source_node.dependents) + len(target_node.dependencies)
                
                # Prefer breaking task->task over phase->phase
                if source_node.node_type == "task" and target_node.node_type == "task":
                    impact *= 0.5
                
                if impact < min_impact:
                    min_impact = impact
                    weakest_link = (source_id, target_id)
        
        return weakest_link
    
    def _calculate_levels(self, graph: Dict[str, DependencyNode]) -> None:
        """Calculate dependency levels (topological sort)."""
        # Find nodes with no dependencies
        queue = deque()
        in_degree = {}
        
        for node_id, node in graph.items():
            in_degree[node_id] = len(node.dependencies)
            if in_degree[node_id] == 0:
                queue.append(node_id)
                node.level = 0
        
        # Process nodes level by level
        while queue:
            current_id = queue.popleft()
            current_node = graph.get(current_id)
            
            if current_node:
                # Update dependents
                for dep_id in current_node.dependents:
                    dep_node = graph.get(dep_id)
                    if dep_node:
                        in_degree[dep_id] -= 1
                        dep_node.level = max(dep_node.level, current_node.level + 1)
                        
                        if in_degree[dep_id] == 0:
                            queue.append(dep_id)
        
        # Check for unprocessed nodes (would indicate cycles)
        unprocessed = [
            node_id for node_id, degree in in_degree.items()
            if degree > 0
        ]
        
        if unprocessed:
            logger.warning(f"Unresolved dependencies for nodes: {unprocessed}")
    
    def _find_critical_path(
        self,
        graph: Dict[str, DependencyNode],
        phases: List[Phase]
    ) -> List[str]:
        """Find the critical path through the project."""
        # Use dynamic programming to find longest path
        distances = {node_id: 0 for node_id in graph}
        predecessors = {node_id: None for node_id in graph}
        
        # Topological order
        topo_order = sorted(
            graph.keys(),
            key=lambda x: (graph[x].level, x)
        )
        
        # Calculate longest distances
        for node_id in topo_order:
            node = graph[node_id]
            
            # Get node weight (duration)
            weight = self._get_node_weight(node_id, phases)
            
            for dep_id in node.dependents:
                if dep_id in distances:
                    new_distance = distances[node_id] + weight
                    if new_distance > distances[dep_id]:
                        distances[dep_id] = new_distance
                        predecessors[dep_id] = node_id
        
        # Find end node with maximum distance
        end_nodes = [
            node_id for node_id, node in graph.items()
            if len(node.dependents) == 0
        ]
        
        if not end_nodes:
            return []
        
        end_node = max(end_nodes, key=lambda x: distances[x])
        
        # Trace back critical path
        critical_path = []
        current = end_node
        
        while current is not None:
            graph[current].critical_path = True
            critical_path.append(current)
            current = predecessors[current]
        
        critical_path.reverse()
        
        return critical_path
    
    def _get_node_weight(self, node_id: str, phases: List[Phase]) -> float:
        """Get weight (duration) for a node."""
        # Find corresponding phase or task
        for phase in phases:
            if phase.id == node_id:
                # Phase weight is sum of its tasks
                return sum(
                    task.estimated_duration.total_seconds() / 3600
                    if task.estimated_duration else 1.0
                    for task in phase.tasks
                )
            
            for task in phase.tasks:
                if task.id == node_id:
                    return (
                        task.estimated_duration.total_seconds() / 3600
                        if task.estimated_duration else 1.0
                    )
        
        return 1.0  # Default weight
    
    def _optimize_dependencies(
        self,
        graph: Dict[str, DependencyNode],
        phases: List[Phase]
    ) -> None:
        """Optimize dependencies for better parallelization."""
        logger.info("Optimizing dependencies for parallelization")
        
        # Identify opportunities for parallelization
        parallel_opportunities = self._find_parallel_opportunities(graph)
        
        # Remove redundant dependencies
        self._remove_redundant_dependencies(graph)
        
        # Balance workload across levels
        self._balance_workload(graph, phases)
        
        # Update graph with optimizations
        optimizations_applied = len(parallel_opportunities)
        
        if optimizations_applied > 0:
            logger.info(f"Applied {optimizations_applied} dependency optimizations")
            
            # Store optimization insights
            self.memory_store.add(
                key="dependency_optimizations",
                value={
                    "parallel_opportunities": parallel_opportunities,
                    "optimization_count": optimizations_applied
                },
                entry_type="CONTEXT",
                phase="planning",
                importance=6.0
            )
    
    def _find_parallel_opportunities(
        self,
        graph: Dict[str, DependencyNode]
    ) -> List[Dict[str, Any]]:
        """Find opportunities for parallel execution."""
        opportunities = []
        
        # Group nodes by level
        levels = defaultdict(list)
        for node_id, node in graph.items():
            levels[node.level].append(node_id)
        
        # Analyze each level
        for level, nodes in levels.items():
            if len(nodes) > 1:
                # Check if nodes can run in parallel
                parallel_groups = self._group_parallel_nodes(nodes, graph)
                
                if len(parallel_groups) > 1:
                    opportunities.append({
                        "level": level,
                        "parallel_groups": parallel_groups,
                        "potential_speedup": len(parallel_groups)
                    })
        
        return opportunities
    
    def _group_parallel_nodes(
        self,
        nodes: List[str],
        graph: Dict[str, DependencyNode]
    ) -> List[List[str]]:
        """Group nodes that can execute in parallel."""
        groups = []
        
        for node_id in nodes:
            # Check if node can be added to any existing group
            added = False
            
            for group in groups:
                # Check if node has dependencies on any node in group
                can_add = True
                node = graph[node_id]
                
                for group_node_id in group:
                    if group_node_id in node.dependencies or node_id in graph[group_node_id].dependencies:
                        can_add = False
                        break
                
                if can_add:
                    group.append(node_id)
                    added = True
                    break
            
            if not added:
                groups.append([node_id])
        
        return groups
    
    def _remove_redundant_dependencies(self, graph: Dict[str, DependencyNode]) -> None:
        """Remove redundant transitive dependencies."""
        for node_id, node in graph.items():
            if len(node.dependencies) > 1:
                # Check for transitive dependencies
                redundant = set()
                
                for dep1 in node.dependencies:
                    for dep2 in node.dependencies:
                        if dep1 != dep2 and self._has_path(graph, dep1, dep2):
                            # dep1 -> dep2 exists, so direct dep2 is redundant
                            redundant.add(dep2)
                
                # Remove redundant dependencies
                for red_dep in redundant:
                    node.dependencies.discard(red_dep)
                    if red_dep in graph:
                        graph[red_dep].dependents.discard(node_id)
    
    def _has_path(self, graph: Dict[str, DependencyNode], start: str, end: str) -> bool:
        """Check if there's a path from start to end."""
        if start == end:
            return True
        
        visited = set()
        queue = deque([start])
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            
            visited.add(current)
            
            if current == end:
                return True
            
            node = graph.get(current)
            if node:
                queue.extend(node.dependents)
        
        return False
    
    def _balance_workload(
        self,
        graph: Dict[str, DependencyNode],
        phases: List[Phase]
    ) -> None:
        """Balance workload across parallel execution levels."""
        # Group by level
        levels = defaultdict(list)
        for node_id, node in graph.items():
            if node.node_type in ["phase", "task"]:
                levels[node.level].append(node_id)
        
        # Calculate workload per level
        level_workloads = {}
        for level, nodes in levels.items():
            workload = sum(
                self._get_node_weight(node_id, phases)
                for node_id in nodes
            )
            level_workloads[level] = workload
        
        # Find imbalanced levels
        avg_workload = sum(level_workloads.values()) / len(level_workloads) if level_workloads else 0
        
        for level, workload in level_workloads.items():
            if workload > avg_workload * 1.5:  # 50% above average
                logger.info(f"Level {level} has high workload: {workload:.1f} hours")
                # Could implement load balancing here
    
    def _update_phases(
        self,
        graph: Dict[str, DependencyNode],
        phases: List[Phase]
    ) -> None:
        """Update phases with resolved dependencies."""
        # Update phase dependencies
        for phase in phases:
            node = graph.get(phase.id)
            if node:
                # Clear and rebuild dependencies
                phase.dependencies.clear()
                
                for dep_id in node.dependencies:
                    # Only add dependencies to other phases
                    dep_node = graph.get(dep_id)
                    if dep_node and dep_node.node_type == "phase":
                        phase.dependencies.append(
                            Dependency(
                                source_id=dep_id,
                                target_id=phase.id,
                                dependency_type="finish_to_start"
                            )
                        )
                
                # Update phase metadata
                phase.complexity = max(phase.complexity, node.level)
        
        # Update task dependencies
        for phase in phases:
            for task in phase.tasks:
                node = graph.get(task.id)
                if node:
                    # Update task dependencies
                    task.dependencies = list(node.dependencies)
                    
                    # Mark critical path tasks
                    if node.critical_path:
                        task.critical = True
                        task.tags.add("critical_path")
    
    def _validate_dependencies(self, phases: List[Phase]) -> None:
        """Validate final dependency configuration."""
        all_phase_ids = {p.id for p in phases}
        all_task_ids = set()
        
        for phase in phases:
            all_task_ids.update(t.id for t in phase.tasks)
        
        # Validate phase dependencies
        for phase in phases:
            for dep in phase.dependencies:
                if dep.source_id not in all_phase_ids:
                    raise PlanningError(
                        f"Phase '{phase.name}' depends on unknown phase '{dep.source_id}'"
                    )
        
        # Validate task dependencies
        for phase in phases:
            for task in phase.tasks:
                for dep_id in task.dependencies:
                    if dep_id not in all_task_ids and not dep_id.endswith("_start"):
                        raise PlanningError(
                            f"Task '{task.name}' depends on unknown task '{dep_id}'"
                        )
        
        logger.info("Dependency validation passed")