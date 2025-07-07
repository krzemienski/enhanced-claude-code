"""Complexity estimator for AI planning."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import timedelta
import math

from ..models import (
    ProjectSpec,
    Phase,
    Task,
    MemoryStore,
    MemoryType
)
from ..config import AIConfig
from ..logging import logger
from ..exceptions import PlanningError


@dataclass
class ComplexityMetrics:
    """Metrics for complexity estimation."""
    
    # Component counts
    total_phases: int = 0
    total_tasks: int = 0
    total_dependencies: int = 0
    
    # Complexity scores (0-10)
    structural_complexity: float = 0.0
    technical_complexity: float = 0.0
    integration_complexity: float = 0.0
    overall_complexity: float = 0.0
    
    # Time estimates
    estimated_hours: float = 0.0
    critical_path_hours: float = 0.0
    parallel_efficiency: float = 1.0
    
    # Cost estimates
    estimated_cost: float = 0.0
    cost_breakdown: Dict[str, float] = None
    
    # Risk factors
    risk_multiplier: float = 1.0
    confidence_level: float = 0.8
    
    def __post_init__(self):
        if self.cost_breakdown is None:
            self.cost_breakdown = {}


class ComplexityEstimator:
    """Estimates project complexity and resource requirements."""
    
    def __init__(self, ai_config: AIConfig, memory_store: MemoryStore):
        """Initialize complexity estimator."""
        self.ai_config = ai_config
        self.memory_store = memory_store
        
        # Complexity factors
        self.base_task_hours = 0.5  # Base hours per task
        self.complexity_multipliers = {
            1: 0.5,   # Very simple
            2: 0.7,   # Simple
            3: 1.0,   # Medium
            4: 1.5,   # Complex
            5: 2.0,   # Very complex
            6: 3.0,   # Highly complex
            7: 4.0,   # Extremely complex
            8: 5.0,   # Expert level
            9: 7.0,   # Research required
            10: 10.0  # Cutting edge
        }
        
        # Cost factors (per hour)
        self.cost_rates = {
            "development": 2.0,
            "testing": 1.5,
            "documentation": 1.0,
            "deployment": 2.5,
            "optimization": 3.0
        }
    
    async def estimate(
        self,
        phases: List[Phase],
        project_spec: ProjectSpec,
        risks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Estimate project complexity and requirements."""
        logger.info("Estimating project complexity")
        
        try:
            # Check memory for similar estimates
            cached_estimate = self._check_memory_cache(project_spec)
            if cached_estimate and not self.ai_config.adaptive_planning:
                logger.info("Using cached complexity estimate")
                return cached_estimate
            
            # Calculate metrics
            metrics = ComplexityMetrics()
            
            # Basic counts
            metrics.total_phases = len(phases)
            metrics.total_tasks = sum(len(phase.tasks) for phase in phases)
            metrics.total_dependencies = sum(
                len(phase.dependencies) + sum(len(task.dependencies) for task in phase.tasks)
                for phase in phases
            )
            
            # Calculate complexity scores
            self._calculate_structural_complexity(metrics, phases)
            self._calculate_technical_complexity(metrics, project_spec)
            self._calculate_integration_complexity(metrics, project_spec, phases)
            
            # Overall complexity
            metrics.overall_complexity = (
                metrics.structural_complexity * 0.3 +
                metrics.technical_complexity * 0.4 +
                metrics.integration_complexity * 0.3
            )
            
            # Apply risk factors
            metrics.risk_multiplier = self._calculate_risk_multiplier(risks)
            
            # Estimate time
            self._estimate_time(metrics, phases)
            
            # Apply risk to estimates
            metrics.estimated_hours *= metrics.risk_multiplier
            metrics.critical_path_hours *= metrics.risk_multiplier
            
            # Estimate cost
            self._estimate_cost(metrics, phases)
            
            # Calculate confidence
            metrics.confidence_level = self._calculate_confidence(metrics, project_spec)
            
            # Store in memory
            self._store_estimate(project_spec, metrics)
            
            result = self._create_result(metrics)
            
            logger.info(
                f"Complexity estimate: {metrics.overall_complexity:.1f}/10, "
                f"Duration: {metrics.estimated_hours:.1f} hours, "
                f"Cost: ${metrics.estimated_cost:.2f}"
            )
            
            return result
            
        except Exception as e:
            logger.error("Complexity estimation failed", error=str(e))
            raise PlanningError(f"Failed to estimate complexity: {str(e)}", cause=e)
    
    def _check_memory_cache(self, project_spec: ProjectSpec) -> Optional[Dict[str, Any]]:
        """Check memory for cached estimates."""
        cache_key = f"complexity_estimate_{project_spec.metadata.name}_{project_spec.version}"
        
        entry = self.memory_store.get_by_key(cache_key)
        if entry:
            logger.info("Found cached complexity estimate")
            return entry.value
        
        return None
    
    def _calculate_structural_complexity(
        self,
        metrics: ComplexityMetrics,
        phases: List[Phase]
    ) -> None:
        """Calculate structural complexity based on project structure."""
        # Phase complexity
        phase_score = min(metrics.total_phases / 10, 1.0) * 3  # Max 3 points
        
        # Task density
        avg_tasks_per_phase = metrics.total_tasks / max(metrics.total_phases, 1)
        task_density_score = min(avg_tasks_per_phase / 10, 1.0) * 3  # Max 3 points
        
        # Dependency complexity
        avg_dependencies = metrics.total_dependencies / max(metrics.total_tasks, 1)
        dependency_score = min(avg_dependencies / 3, 1.0) * 4  # Max 4 points
        
        # Check for complex dependency patterns
        circular_risk = 0
        parallel_phases = 0
        
        for phase in phases:
            # Count phases that can run in parallel
            if not phase.dependencies:
                parallel_phases += 1
            
            # Check for potential circular dependencies
            phase_deps = {d.source_id for d in phase.dependencies}
            for other_phase in phases:
                if other_phase.id != phase.id:
                    other_deps = {d.source_id for d in other_phase.dependencies}
                    if phase.id in other_deps and other_phase.id in phase_deps:
                        circular_risk += 1
        
        parallel_score = max(0, 1 - (parallel_phases / max(metrics.total_phases, 1)))
        
        metrics.structural_complexity = min(
            phase_score + task_density_score + dependency_score + parallel_score + circular_risk,
            10.0
        )
    
    def _calculate_technical_complexity(
        self,
        metrics: ComplexityMetrics,
        project_spec: ProjectSpec
    ) -> None:
        """Calculate technical complexity based on technologies."""
        # Technology diversity
        tech_count = len(project_spec.technologies)
        tech_categories = len(set(t.category for t in project_spec.technologies))
        
        tech_diversity_score = min((tech_count / 10) + (tech_categories / 5), 1.0) * 3
        
        # Framework complexity
        frameworks = [t for t in project_spec.technologies if t.category == "framework"]
        framework_score = min(len(frameworks) / 3, 1.0) * 2
        
        # Database complexity
        databases = [t for t in project_spec.technologies if t.category == "database"]
        db_score = min(len(databases) / 2, 1.0) * 2
        
        # External service complexity
        services = [t for t in project_spec.technologies if t.category == "service"]
        service_score = min(len(services) / 5, 1.0) * 2
        
        # Special complexity factors
        special_factors = 0
        
        # Real-time features
        if any("realtime" in f.name.lower() or "websocket" in f.description.lower() 
               for f in project_spec.features):
            special_factors += 1
        
        # Machine learning
        if any("ml" in t.name.lower() or "tensorflow" in t.name.lower() or "pytorch" in t.name.lower()
               for t in project_spec.technologies):
            special_factors += 1
        
        # Microservices
        if any("microservice" in project_spec.description.lower() or 
               "distributed" in project_spec.description.lower()):
            special_factors += 1
        
        metrics.technical_complexity = min(
            tech_diversity_score + framework_score + db_score + service_score + special_factors,
            10.0
        )
    
    def _calculate_integration_complexity(
        self,
        metrics: ComplexityMetrics,
        project_spec: ProjectSpec,
        phases: List[Phase]
    ) -> None:
        """Calculate integration complexity."""
        # API complexity
        api_count = len(project_spec.api_endpoints)
        api_score = min(api_count / 50, 1.0) * 3
        
        # External integration count
        external_integrations = sum(
            1 for t in project_spec.technologies 
            if t.category == "service" or "api" in t.name.lower()
        )
        integration_score = min(external_integrations / 5, 1.0) * 3
        
        # Authentication complexity
        auth_score = 0
        if project_spec.security_requirements.authentication_required:
            auth_methods = len(project_spec.security_requirements.authentication_methods)
            auth_score = min(auth_methods / 3, 1.0) * 2
        
        # Data flow complexity
        data_flow_score = 0
        if any(phase.name.lower() in ["data migration", "etl", "data pipeline"]
               for phase in phases):
            data_flow_score = 2
        
        metrics.integration_complexity = min(
            api_score + integration_score + auth_score + data_flow_score,
            10.0
        )
    
    def _calculate_risk_multiplier(self, risks: List[Dict[str, Any]]) -> float:
        """Calculate risk multiplier based on identified risks."""
        if not risks:
            return 1.0
        
        # Count risks by severity
        risk_counts = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0
        }
        
        for risk in risks:
            severity = risk.get("severity", "low")
            risk_counts[severity] = risk_counts.get(severity, 0) + 1
        
        # Calculate multiplier
        multiplier = 1.0
        multiplier += risk_counts["low"] * 0.02
        multiplier += risk_counts["medium"] * 0.05
        multiplier += risk_counts["high"] * 0.10
        multiplier += risk_counts["critical"] * 0.20
        
        # Cap at 2.0 (100% increase)
        return min(multiplier, 2.0)
    
    def _estimate_time(self, metrics: ComplexityMetrics, phases: List[Phase]) -> None:
        """Estimate time requirements."""
        total_hours = 0
        critical_path_hours = 0
        
        # Calculate time for each phase
        phase_times = {}
        
        for phase in phases:
            phase_hours = 0
            
            # Sum task times
            for task in phase.tasks:
                # Base time from task weight and complexity
                task_complexity = min(phase.complexity, 10)
                multiplier = self.complexity_multipliers.get(task_complexity, 1.0)
                
                task_hours = self.base_task_hours * task.weight * multiplier
                
                # Adjust for task type
                if "test" in task.tags:
                    task_hours *= 0.8  # Testing is somewhat faster
                elif "optimization" in task.tags:
                    task_hours *= 1.5  # Optimization takes longer
                elif "documentation" in task.tags:
                    task_hours *= 0.6  # Documentation is faster
                
                phase_hours += task_hours
            
            phase_times[phase.id] = phase_hours
            total_hours += phase_hours
            
            # Track critical path
            if any(task.tags for task in phase.tasks if "critical_path" in task.tags):
                critical_path_hours += phase_hours
        
        metrics.estimated_hours = total_hours
        metrics.critical_path_hours = critical_path_hours if critical_path_hours > 0 else total_hours * 0.7
        
        # Calculate parallel efficiency
        if metrics.total_phases > 1:
            # Estimate based on dependency density
            dependency_density = metrics.total_dependencies / (metrics.total_phases * metrics.total_tasks)
            metrics.parallel_efficiency = max(0.5, 1 - dependency_density * 0.5)
        
        # Adjust total time for parallelization
        metrics.estimated_hours = (
            metrics.critical_path_hours + 
            (metrics.estimated_hours - metrics.critical_path_hours) * (1 - metrics.parallel_efficiency)
        )
    
    def _estimate_cost(self, metrics: ComplexityMetrics, phases: List[Phase]) -> None:
        """Estimate project cost."""
        total_cost = 0
        breakdown = {
            "development": 0,
            "testing": 0,
            "documentation": 0,
            "deployment": 0,
            "optimization": 0
        }
        
        for phase in phases:
            phase_category = self._categorize_phase(phase.name)
            phase_hours = metrics.estimated_hours * (len(phase.tasks) / max(metrics.total_tasks, 1))
            
            rate = self.cost_rates.get(phase_category, 2.0)
            phase_cost = phase_hours * rate
            
            breakdown[phase_category] = breakdown.get(phase_category, 0) + phase_cost
            total_cost += phase_cost
        
        # Add complexity premium
        complexity_premium = 1 + (metrics.overall_complexity - 5) * 0.1  # ±10% per point from 5
        total_cost *= complexity_premium
        
        # Add risk premium
        total_cost *= metrics.risk_multiplier
        
        metrics.estimated_cost = total_cost
        metrics.cost_breakdown = breakdown
    
    def _categorize_phase(self, phase_name: str) -> str:
        """Categorize phase for cost estimation."""
        name_lower = phase_name.lower()
        
        if any(keyword in name_lower for keyword in ["test", "qa", "quality"]):
            return "testing"
        elif any(keyword in name_lower for keyword in ["doc", "guide", "manual"]):
            return "documentation"
        elif any(keyword in name_lower for keyword in ["deploy", "release", "production"]):
            return "deployment"
        elif any(keyword in name_lower for keyword in ["optim", "performance", "scale"]):
            return "optimization"
        else:
            return "development"
    
    def _calculate_confidence(
        self,
        metrics: ComplexityMetrics,
        project_spec: ProjectSpec
    ) -> float:
        """Calculate confidence level in estimates."""
        confidence = 0.9  # Base confidence
        
        # Reduce confidence for high complexity
        if metrics.overall_complexity > 7:
            confidence -= (metrics.overall_complexity - 7) * 0.05
        
        # Reduce confidence for many unknown technologies
        unknown_tech = sum(
            1 for t in project_spec.technologies
            if t.version is None or "beta" in str(t.version).lower()
        )
        confidence -= unknown_tech * 0.02
        
        # Reduce confidence for high dependency count
        if metrics.total_dependencies > metrics.total_tasks * 2:
            confidence -= 0.1
        
        # Reduce confidence for high risk
        if metrics.risk_multiplier > 1.5:
            confidence -= (metrics.risk_multiplier - 1.5) * 0.2
        
        return max(0.5, min(confidence, 0.95))
    
    def _create_result(self, metrics: ComplexityMetrics) -> Dict[str, Any]:
        """Create result dictionary."""
        return {
            "complexity_score": metrics.overall_complexity,
            "complexity_breakdown": {
                "structural": metrics.structural_complexity,
                "technical": metrics.technical_complexity,
                "integration": metrics.integration_complexity
            },
            "estimated_hours": metrics.estimated_hours,
            "critical_path_hours": metrics.critical_path_hours,
            "parallel_efficiency": metrics.parallel_efficiency,
            "estimated_cost": metrics.estimated_cost,
            "cost_breakdown": metrics.cost_breakdown,
            "risk_multiplier": metrics.risk_multiplier,
            "confidence_level": metrics.confidence_level,
            "metrics": {
                "total_phases": metrics.total_phases,
                "total_tasks": metrics.total_tasks,
                "total_dependencies": metrics.total_dependencies
            }
        }
    
    def _store_estimate(
        self,
        project_spec: ProjectSpec,
        metrics: ComplexityMetrics
    ) -> None:
        """Store estimate in memory."""
        cache_key = f"complexity_estimate_{project_spec.metadata.name}_{project_spec.version}"
        
        self.memory_store.add(
            key=cache_key,
            value=self._create_result(metrics),
            entry_type=MemoryType.RESULT,
            phase="planning",
            tags={"complexity", "estimate", project_spec.metadata.name},
            importance=7.0
        )
        
        # Store key metrics for quick access
        self.memory_store.add(
            key=f"project_hours_{project_spec.metadata.name}",
            value=metrics.estimated_hours,
            entry_type=MemoryType.CONTEXT,
            phase="planning",
            importance=6.0
        )
        
        self.memory_store.add(
            key=f"project_cost_{project_spec.metadata.name}",
            value=metrics.estimated_cost,
            entry_type=MemoryType.CONTEXT,
            phase="planning",
            importance=6.0
        )