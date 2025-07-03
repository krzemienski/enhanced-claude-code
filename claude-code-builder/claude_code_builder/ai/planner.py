"""AI-driven project planning system."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path

from ..models import (
    ProjectSpec,
    Phase,
    Task,
    TaskStatus,
    PhaseStatus,
    Dependency,
    MemoryStore,
    MemoryType,
    CostTracker,
    CostCategory
)
from ..exceptions import PlanningError
from ..logging import logger
from ..config import AIConfig
from .analyzer import SpecificationAnalyzer
from .phase_generator import PhaseGenerator
from .task_generator import TaskGenerator
from .dependency_resolver import DependencyResolver
from .complexity_estimator import ComplexityEstimator
from .risk_assessor import RiskAssessor
from .optimization import PlanOptimizer


@dataclass
class PlanningContext:
    """Context for AI planning operations."""
    
    project_spec: ProjectSpec
    ai_config: AIConfig
    memory_store: MemoryStore
    cost_tracker: CostTracker
    
    # Planning state
    analysis_results: Optional[Dict[str, Any]] = None
    identified_risks: List[Dict[str, Any]] = field(default_factory=list)
    phase_plan: List[Phase] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
    
    # Constraints
    max_phases: int = 20
    max_tasks_per_phase: int = 15
    target_duration_hours: float = 1.0
    budget_limit: Optional[float] = None


@dataclass
class PlanningResult:
    """Result of AI planning process."""
    
    phases: List[Phase]
    total_tasks: int
    estimated_duration: timedelta
    estimated_cost: float
    complexity_score: float
    risk_assessment: Dict[str, Any]
    optimization_applied: List[str]
    
    # Metadata
    planning_duration: timedelta
    ai_calls_made: int
    tokens_used: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "phases": [phase.to_dict() for phase in self.phases],
            "total_tasks": self.total_tasks,
            "estimated_duration": self.estimated_duration.total_seconds(),
            "estimated_cost": self.estimated_cost,
            "complexity_score": self.complexity_score,
            "risk_assessment": self.risk_assessment,
            "optimization_applied": self.optimization_applied,
            "planning_duration": self.planning_duration.total_seconds(),
            "ai_calls_made": self.ai_calls_made,
            "tokens_used": self.tokens_used
        }


class AIPlanner:
    """Main AI planning orchestrator."""
    
    def __init__(
        self,
        ai_config: AIConfig,
        memory_store: MemoryStore,
        cost_tracker: CostTracker
    ):
        """Initialize AI planner."""
        self.ai_config = ai_config
        self.memory_store = memory_store
        self.cost_tracker = cost_tracker
        
        # Initialize sub-components
        self.analyzer = SpecificationAnalyzer(ai_config, memory_store)
        self.phase_generator = PhaseGenerator(ai_config, memory_store)
        self.task_generator = TaskGenerator(ai_config, memory_store)
        self.dependency_resolver = DependencyResolver(ai_config, memory_store)
        self.complexity_estimator = ComplexityEstimator(ai_config, memory_store)
        self.risk_assessor = RiskAssessor(ai_config, memory_store)
        self.optimizer = PlanOptimizer(ai_config, memory_store)
        
        # Planning metrics
        self.start_time: Optional[datetime] = None
        self.ai_calls = 0
        self.total_tokens = 0
    
    async def create_plan(
        self,
        project_spec: ProjectSpec,
        constraints: Optional[Dict[str, Any]] = None
    ) -> PlanningResult:
        """Create optimal plan for project specification."""
        logger.info("Starting AI-driven planning", project=project_spec.metadata.name)
        self.start_time = datetime.utcnow()
        
        try:
            # Create planning context
            context = PlanningContext(
                project_spec=project_spec,
                ai_config=self.ai_config,
                memory_store=self.memory_store,
                cost_tracker=self.cost_tracker
            )
            
            # Apply constraints
            if constraints:
                self._apply_constraints(context, constraints)
            
            # Step 1: Analyze specification
            with logger.context(phase="analysis"):
                context.analysis_results = await self._analyze_specification(context)
            
            # Step 2: Assess risks
            with logger.context(phase="risk_assessment"):
                context.identified_risks = await self._assess_risks(context)
            
            # Step 3: Generate phases
            with logger.context(phase="phase_generation"):
                context.phase_plan = await self._generate_phases(context)
            
            # Step 4: Generate tasks for each phase
            with logger.context(phase="task_generation"):
                await self._generate_tasks(context)
            
            # Step 5: Resolve dependencies
            with logger.context(phase="dependency_resolution"):
                await self._resolve_dependencies(context)
            
            # Step 6: Estimate complexity and duration
            with logger.context(phase="estimation"):
                complexity_data = await self._estimate_complexity(context)
            
            # Step 7: Optimize plan
            with logger.context(phase="optimization"):
                context.optimization_suggestions = await self._optimize_plan(context)
            
            # Step 8: Validate plan
            with logger.context(phase="validation"):
                self._validate_plan(context)
            
            # Create result
            result = self._create_result(context, complexity_data)
            
            # Store planning result in memory
            self._store_planning_result(context, result)
            
            logger.info(
                "Planning completed successfully",
                phases=len(result.phases),
                tasks=result.total_tasks,
                duration=result.estimated_duration,
                cost=result.estimated_cost
            )
            
            return result
            
        except Exception as e:
            logger.error("Planning failed", error=str(e), exc_info=True)
            raise PlanningError(f"AI planning failed: {str(e)}", cause=e)
    
    def _apply_constraints(self, context: PlanningContext, constraints: Dict[str, Any]) -> None:
        """Apply planning constraints."""
        if "max_phases" in constraints:
            context.max_phases = constraints["max_phases"]
        
        if "max_tasks_per_phase" in constraints:
            context.max_tasks_per_phase = constraints["max_tasks_per_phase"]
        
        if "target_duration_hours" in constraints:
            context.target_duration_hours = constraints["target_duration_hours"]
        
        if "budget_limit" in constraints:
            context.budget_limit = constraints["budget_limit"]
    
    async def _analyze_specification(self, context: PlanningContext) -> Dict[str, Any]:
        """Analyze project specification."""
        logger.info("Analyzing project specification")
        
        # Track API call
        self.ai_calls += 1
        
        # Analyze specification
        analysis = await self.analyzer.analyze(context.project_spec)
        
        # Track cost
        self.cost_tracker.add_cost(
            CostCategory.PLANNING,
            amount=0.05,  # Estimated cost
            description="Specification analysis",
            phase="planning",
            api_calls=1,
            tokens_used=analysis.get("tokens_used", 1000)
        )
        
        self.total_tokens += analysis.get("tokens_used", 1000)
        
        # Store in memory
        self.memory_store.add(
            key="specification_analysis",
            value=analysis,
            entry_type=MemoryType.CONTEXT,
            phase="planning",
            importance=9.0
        )
        
        return analysis
    
    async def _assess_risks(self, context: PlanningContext) -> List[Dict[str, Any]]:
        """Assess project risks."""
        logger.info("Assessing project risks")
        
        # Track API call
        self.ai_calls += 1
        
        # Assess risks
        risks = await self.risk_assessor.assess(
            context.project_spec,
            context.analysis_results
        )
        
        # Track cost
        self.cost_tracker.add_cost(
            CostCategory.PLANNING,
            amount=0.03,
            description="Risk assessment",
            phase="planning",
            api_calls=1,
            tokens_used=500
        )
        
        self.total_tokens += 500
        
        # Store high-priority risks in memory
        for risk in risks:
            if risk.get("severity", "low") in ["high", "critical"]:
                self.memory_store.add(
                    key=f"risk_{risk['id']}",
                    value=risk,
                    entry_type=MemoryType.CONTEXT,
                    phase="planning",
                    tags={"risk", risk["category"]},
                    importance=8.0
                )
        
        return risks
    
    async def _generate_phases(self, context: PlanningContext) -> List[Phase]:
        """Generate project phases."""
        logger.info("Generating project phases")
        
        # Track API call
        self.ai_calls += 1
        
        # Generate phases
        phases = await self.phase_generator.generate(
            context.project_spec,
            context.analysis_results,
            max_phases=context.max_phases
        )
        
        # Track cost
        self.cost_tracker.add_cost(
            CostCategory.PLANNING,
            amount=0.08,
            description="Phase generation",
            phase="planning",
            api_calls=1,
            tokens_used=2000
        )
        
        self.total_tokens += 2000
        
        logger.info(f"Generated {len(phases)} phases")
        
        return phases
    
    async def _generate_tasks(self, context: PlanningContext) -> None:
        """Generate tasks for each phase."""
        logger.info("Generating tasks for all phases")
        
        for phase in context.phase_plan:
            logger.info(f"Generating tasks for phase: {phase.name}")
            
            # Track API call
            self.ai_calls += 1
            
            # Generate tasks
            tasks = await self.task_generator.generate_for_phase(
                phase,
                context.project_spec,
                context.analysis_results,
                max_tasks=context.max_tasks_per_phase
            )
            
            # Add tasks to phase
            phase.tasks = tasks
            
            # Track cost
            self.cost_tracker.add_cost(
                CostCategory.PLANNING,
                amount=0.05,
                description=f"Task generation for {phase.name}",
                phase="planning",
                api_calls=1,
                tokens_used=1000
            )
            
            self.total_tokens += 1000
        
        total_tasks = sum(len(phase.tasks) for phase in context.phase_plan)
        logger.info(f"Generated {total_tasks} total tasks")
    
    async def _resolve_dependencies(self, context: PlanningContext) -> None:
        """Resolve dependencies between phases and tasks."""
        logger.info("Resolving dependencies")
        
        # Track API call
        self.ai_calls += 1
        
        # Resolve dependencies
        await self.dependency_resolver.resolve(context.phase_plan)
        
        # Track cost
        self.cost_tracker.add_cost(
            CostCategory.PLANNING,
            amount=0.04,
            description="Dependency resolution",
            phase="planning",
            api_calls=1,
            tokens_used=800
        )
        
        self.total_tokens += 800
        
        # Store dependency graph in memory
        dep_graph = self._create_dependency_graph(context.phase_plan)
        self.memory_store.add(
            key="dependency_graph",
            value=dep_graph,
            entry_type=MemoryType.CONTEXT,
            phase="planning",
            importance=7.0
        )
    
    async def _estimate_complexity(
        self,
        context: PlanningContext
    ) -> Dict[str, Any]:
        """Estimate project complexity and duration."""
        logger.info("Estimating complexity and duration")
        
        # Track API call
        self.ai_calls += 1
        
        # Estimate complexity
        complexity_data = await self.complexity_estimator.estimate(
            context.phase_plan,
            context.project_spec,
            context.identified_risks
        )
        
        # Track cost
        self.cost_tracker.add_cost(
            CostCategory.PLANNING,
            amount=0.03,
            description="Complexity estimation",
            phase="planning",
            api_calls=1,
            tokens_used=600
        )
        
        self.total_tokens += 600
        
        return complexity_data
    
    async def _optimize_plan(self, context: PlanningContext) -> List[str]:
        """Optimize the generated plan."""
        logger.info("Optimizing plan")
        
        if not context.ai_config.phase_optimization:
            return []
        
        # Track API call
        self.ai_calls += 1
        
        # Optimize plan
        optimizations = await self.optimizer.optimize(
            context.phase_plan,
            context.target_duration_hours,
            context.budget_limit
        )
        
        # Track cost
        self.cost_tracker.add_cost(
            CostCategory.PLANNING,
            amount=0.05,
            description="Plan optimization",
            phase="planning",
            api_calls=1,
            tokens_used=1000
        )
        
        self.total_tokens += 1000
        
        # Apply optimizations
        for optimization in optimizations:
            logger.info(f"Applied optimization: {optimization}")
        
        return optimizations
    
    def _validate_plan(self, context: PlanningContext) -> None:
        """Validate the generated plan."""
        # Check phase count
        if len(context.phase_plan) == 0:
            raise PlanningError("No phases generated")
        
        if len(context.phase_plan) > context.max_phases:
            raise PlanningError(f"Too many phases: {len(context.phase_plan)} > {context.max_phases}")
        
        # Check tasks
        for phase in context.phase_plan:
            if len(phase.tasks) == 0:
                raise PlanningError(f"Phase '{phase.name}' has no tasks")
            
            if len(phase.tasks) > context.max_tasks_per_phase:
                raise PlanningError(
                    f"Phase '{phase.name}' has too many tasks: "
                    f"{len(phase.tasks)} > {context.max_tasks_per_phase}"
                )
            
            # Validate phase
            phase.validate()
        
        # Check for circular dependencies
        if self._has_circular_dependencies(context.phase_plan):
            raise PlanningError("Circular dependencies detected in plan")
    
    def _has_circular_dependencies(self, phases: List[Phase]) -> bool:
        """Check for circular dependencies."""
        # Build dependency graph
        graph = {}
        for phase in phases:
            graph[phase.id] = [dep.source_id for dep in phase.dependencies]
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for phase_id in graph:
            if phase_id not in visited:
                if has_cycle(phase_id):
                    return True
        
        return False
    
    def _create_dependency_graph(self, phases: List[Phase]) -> Dict[str, Any]:
        """Create dependency graph representation."""
        nodes = []
        edges = []
        
        for phase in phases:
            nodes.append({
                "id": phase.id,
                "name": phase.name,
                "complexity": phase.complexity,
                "task_count": len(phase.tasks)
            })
            
            for dep in phase.dependencies:
                edges.append({
                    "source": dep.source_id,
                    "target": phase.id,
                    "type": dep.dependency_type
                })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "phase_count": len(phases),
            "total_dependencies": len(edges)
        }
    
    def _create_result(
        self,
        context: PlanningContext,
        complexity_data: Dict[str, Any]
    ) -> PlanningResult:
        """Create planning result."""
        total_tasks = sum(len(phase.tasks) for phase in context.phase_plan)
        planning_duration = datetime.utcnow() - self.start_time
        
        return PlanningResult(
            phases=context.phase_plan,
            total_tasks=total_tasks,
            estimated_duration=timedelta(
                hours=complexity_data.get("estimated_hours", 1.0)
            ),
            estimated_cost=complexity_data.get("estimated_cost", 5.0),
            complexity_score=complexity_data.get("complexity_score", 5.0),
            risk_assessment={
                "identified_risks": len(context.identified_risks),
                "high_priority_risks": sum(
                    1 for risk in context.identified_risks
                    if risk.get("severity") in ["high", "critical"]
                ),
                "mitigation_strategies": [
                    risk.get("mitigation", "")
                    for risk in context.identified_risks
                    if risk.get("mitigation")
                ]
            },
            optimization_applied=context.optimization_suggestions,
            planning_duration=planning_duration,
            ai_calls_made=self.ai_calls,
            tokens_used=self.total_tokens
        )
    
    def _store_planning_result(
        self,
        context: PlanningContext,
        result: PlanningResult
    ) -> None:
        """Store planning result in memory."""
        # Store complete plan
        self.memory_store.add(
            key="project_plan",
            value=result.to_dict(),
            entry_type=MemoryType.RESULT,
            phase="planning",
            importance=10.0
        )
        
        # Store phase summaries
        for phase in result.phases:
            self.memory_store.add(
                key=f"phase_plan_{phase.id}",
                value={
                    "name": phase.name,
                    "objective": phase.objective,
                    "task_count": len(phase.tasks),
                    "complexity": phase.complexity,
                    "deliverables": phase.deliverables
                },
                entry_type=MemoryType.CONTEXT,
                phase="planning",
                tags={phase.name.lower().replace(" ", "_")},
                importance=7.0
            )
        
        logger.info("Planning result stored in memory")