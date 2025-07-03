"""Phase generator for AI planning."""

from typing import Dict, List, Any, Optional
from datetime import timedelta
import uuid

from ..models import (
    ProjectSpec,
    Phase,
    PhaseStatus,
    MemoryStore,
    MemoryType,
    Dependency
)
from ..config import AIConfig
from ..logging import logger
from ..exceptions import PlanningError


class PhaseTemplate:
    """Template for common phase patterns."""
    
    def __init__(self, name: str, objective: str, complexity: int = 3):
        self.name = name
        self.objective = objective
        self.complexity = complexity
        self.deliverables: List[str] = []
        self.required_tools: List[str] = []
        self.typical_tasks: List[str] = []


class PhaseGenerator:
    """Generates project phases based on analysis."""
    
    def __init__(self, ai_config: AIConfig, memory_store: MemoryStore):
        """Initialize phase generator."""
        self.ai_config = ai_config
        self.memory_store = memory_store
        
        # Initialize phase templates
        self._init_templates()
    
    def _init_templates(self):
        """Initialize common phase templates."""
        self.templates = {
            "foundation": PhaseTemplate(
                "Project Foundation",
                "Establish project structure, configuration, and core infrastructure",
                complexity=2
            ),
            "data_models": PhaseTemplate(
                "Data Models and Schema",
                "Define data structures, database schema, and domain models",
                complexity=3
            ),
            "core_logic": PhaseTemplate(
                "Core Business Logic",
                "Implement primary business logic and domain services",
                complexity=5
            ),
            "api_development": PhaseTemplate(
                "API Development",
                "Create REST/GraphQL APIs with authentication and validation",
                complexity=4
            ),
            "frontend": PhaseTemplate(
                "Frontend Development",
                "Build user interface components and pages",
                complexity=4
            ),
            "integration": PhaseTemplate(
                "External Integrations",
                "Integrate with third-party services and APIs",
                complexity=4
            ),
            "testing": PhaseTemplate(
                "Testing Implementation",
                "Create comprehensive test suites and fixtures",
                complexity=3
            ),
            "deployment": PhaseTemplate(
                "Deployment Setup",
                "Configure deployment pipeline and infrastructure",
                complexity=3
            ),
            "documentation": PhaseTemplate(
                "Documentation",
                "Create user guides, API docs, and developer documentation",
                complexity=2
            ),
            "optimization": PhaseTemplate(
                "Performance Optimization",
                "Optimize performance, security, and scalability",
                complexity=4
            )
        }
        
        # Set deliverables for templates
        self.templates["foundation"].deliverables = [
            "Project structure created",
            "Configuration files setup",
            "Development environment ready",
            "Version control initialized"
        ]
        
        self.templates["data_models"].deliverables = [
            "Database schema defined",
            "Domain models implemented",
            "Migrations created",
            "Validation rules defined"
        ]
        
        self.templates["core_logic"].deliverables = [
            "Business services implemented",
            "Core algorithms created",
            "Domain rules enforced",
            "Error handling implemented"
        ]
    
    async def generate(
        self,
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any],
        max_phases: int = 15
    ) -> List[Phase]:
        """Generate project phases."""
        logger.info("Generating project phases")
        
        try:
            # Check memory for similar projects
            similar_phases = self._check_similar_projects(project_spec)
            if similar_phases and not self.ai_config.adaptive_planning:
                logger.info("Using phases from similar project")
                return self._adapt_phases(similar_phases, project_spec)
            
            # Determine required phases
            required_phases = self._determine_required_phases(
                project_spec,
                analysis_results
            )
            
            # Generate phase list
            phases = self._create_phases(
                required_phases,
                project_spec,
                analysis_results
            )
            
            # Add dependencies
            self._add_dependencies(phases)
            
            # Optimize phase count
            if len(phases) > max_phases:
                phases = self._consolidate_phases(phases, max_phases)
            
            # Store in memory
            self._store_phases(project_spec, phases)
            
            logger.info(f"Generated {len(phases)} phases")
            return phases
            
        except Exception as e:
            logger.error("Phase generation failed", error=str(e))
            raise PlanningError(f"Failed to generate phases: {str(e)}", cause=e)
    
    def _check_similar_projects(self, project_spec: ProjectSpec) -> Optional[List[Phase]]:
        """Check memory for similar project phases."""
        # Search for similar project type
        query_result = self.memory_store.query(
            MemoryQuery(
                key_pattern=f"project_type_{project_spec.metadata.name}",
                max_results=1
            )
        )
        
        if not query_result:
            return None
        
        project_type = query_result[0].value
        
        # Search for phases from similar projects
        similar_phases_result = self.memory_store.query(
            MemoryQuery(
                tags={f"phases_{project_type}"},
                max_results=1
            )
        )
        
        if similar_phases_result:
            return similar_phases_result[0].value
        
        return None
    
    def _determine_required_phases(
        self,
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any]
    ) -> List[str]:
        """Determine which phases are required."""
        required = ["foundation"]  # Always need foundation
        
        # Based on project type
        project_type = analysis_results.get("project_type", "general")
        
        if project_type in ["web_app", "api"]:
            required.extend(["data_models", "core_logic"])
        
        if analysis_results.get("requirements", {}).get("has_api", False):
            required.append("api_development")
        
        if analysis_results.get("requirements", {}).get("has_frontend", False):
            required.append("frontend")
        
        # Based on technologies
        if analysis_results.get("technologies", {}).get("external_services", []):
            required.append("integration")
        
        # Always include testing and documentation
        required.extend(["testing", "documentation"])
        
        # Deployment for production-ready projects
        if project_spec.build_requirements.deployment_platforms:
            required.append("deployment")
        
        # Performance optimization for high-performance requirements
        if project_spec.performance_requirements.throughput_rps > 1000:
            required.append("optimization")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_required = []
        for phase in required:
            if phase not in seen:
                seen.add(phase)
                unique_required.append(phase)
        
        return unique_required
    
    def _create_phases(
        self,
        required_phase_types: List[str],
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any]
    ) -> List[Phase]:
        """Create phase instances."""
        phases = []
        
        for i, phase_type in enumerate(required_phase_types, 1):
            template = self.templates.get(phase_type)
            
            if not template:
                # Create custom phase
                phase = self._create_custom_phase(
                    phase_type,
                    project_spec,
                    analysis_results,
                    order=i
                )
            else:
                # Create from template
                phase = self._create_phase_from_template(
                    template,
                    project_spec,
                    analysis_results,
                    order=i
                )
            
            phases.append(phase)
        
        # Add project-specific phases
        custom_phases = self._generate_custom_phases(
            project_spec,
            analysis_results,
            existing_phases=phases
        )
        
        phases.extend(custom_phases)
        
        return phases
    
    def _create_phase_from_template(
        self,
        template: PhaseTemplate,
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any],
        order: int
    ) -> Phase:
        """Create phase from template."""
        # Customize template based on project
        name = self._customize_phase_name(template.name, project_spec)
        objective = self._customize_objective(template.objective, project_spec)
        
        # Adjust complexity based on project
        complexity = template.complexity
        if analysis_results.get("complexity", {}).get("overall", 5) > 7:
            complexity = min(complexity + 2, 10)
        
        # Create phase
        phase = Phase(
            id=str(uuid.uuid4()),
            name=name,
            description=f"Phase {order}: {name}",
            objective=objective,
            complexity=complexity,
            priority=10 - order,  # Higher priority for earlier phases
            deliverables=template.deliverables.copy(),
            required_tools=template.required_tools.copy()
        )
        
        # Add estimated duration
        phase.planned_duration = self._estimate_phase_duration(
            phase,
            analysis_results
        )
        
        return phase
    
    def _create_custom_phase(
        self,
        phase_type: str,
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any],
        order: int
    ) -> Phase:
        """Create custom phase not in templates."""
        # Generate phase details based on type
        if "security" in phase_type.lower():
            return Phase(
                id=str(uuid.uuid4()),
                name="Security Implementation",
                description=f"Phase {order}: Security hardening and compliance",
                objective="Implement security measures and ensure compliance",
                complexity=6,
                priority=10 - order,
                deliverables=[
                    "Security policies implemented",
                    "Encryption configured",
                    "Access controls established",
                    "Security testing completed"
                ],
                required_tools=["security-scanner", "penetration-testing"]
            )
        elif "migration" in phase_type.lower():
            return Phase(
                id=str(uuid.uuid4()),
                name="Data Migration",
                description=f"Phase {order}: Migrate existing data",
                objective="Safely migrate data from existing systems",
                complexity=7,
                priority=10 - order,
                deliverables=[
                    "Migration scripts created",
                    "Data validation completed",
                    "Rollback procedures defined",
                    "Migration executed"
                ]
            )
        else:
            # Generic custom phase
            return Phase(
                id=str(uuid.uuid4()),
                name=phase_type.replace("_", " ").title(),
                description=f"Phase {order}: {phase_type}",
                objective=f"Complete {phase_type} requirements",
                complexity=5,
                priority=10 - order
            )
    
    def _customize_phase_name(self, template_name: str, project_spec: ProjectSpec) -> str:
        """Customize phase name for project."""
        # Add project context to phase names
        if "API" in template_name and project_spec.api_endpoints:
            endpoint_types = set()
            for endpoint in project_spec.api_endpoints[:5]:  # Sample first 5
                if "user" in endpoint.path.lower():
                    endpoint_types.add("User")
                elif "auth" in endpoint.path.lower():
                    endpoint_types.add("Auth")
                elif "data" in endpoint.path.lower():
                    endpoint_types.add("Data")
            
            if endpoint_types:
                return f"{template_name} ({', '.join(list(endpoint_types)[:2])} APIs)"
        
        return template_name
    
    def _customize_objective(self, template_objective: str, project_spec: ProjectSpec) -> str:
        """Customize phase objective for project."""
        # Add specific project goals
        if project_spec.metadata.description:
            # Extract key goal from description (first sentence)
            first_sentence = project_spec.metadata.description.split('.')[0]
            if len(first_sentence) < 100:
                return f"{template_objective} for {first_sentence.lower()}"
        
        return template_objective
    
    def _generate_custom_phases(
        self,
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any],
        existing_phases: List[Phase]
    ) -> List[Phase]:
        """Generate project-specific custom phases."""
        custom_phases = []
        existing_types = {p.name.lower() for p in existing_phases}
        
        # Check for specific requirements
        
        # Real-time features need special phase
        if analysis_results.get("requirements", {}).get("has_realtime", False):
            if "real-time" not in existing_types and "realtime" not in existing_types:
                custom_phases.append(
                    Phase(
                        id=str(uuid.uuid4()),
                        name="Real-time Features",
                        description="Implement WebSocket and real-time functionality",
                        objective="Enable real-time communication and updates",
                        complexity=6,
                        priority=5,
                        deliverables=[
                            "WebSocket server configured",
                            "Real-time event handling",
                            "Client reconnection logic",
                            "Real-time state synchronization"
                        ]
                    )
                )
        
        # Machine learning features
        if any(keyword in project_spec.description.lower() 
               for keyword in ["machine learning", "ml", "ai", "model"]):
            if "machine learning" not in existing_types and "ml" not in existing_types:
                custom_phases.append(
                    Phase(
                        id=str(uuid.uuid4()),
                        name="Machine Learning Pipeline",
                        description="Implement ML model training and inference",
                        objective="Create ML pipeline for model deployment",
                        complexity=8,
                        priority=4,
                        deliverables=[
                            "Model training pipeline",
                            "Feature engineering",
                            "Model serving API",
                            "Performance monitoring"
                        ]
                    )
                )
        
        # Analytics and reporting
        if any(keyword in project_spec.description.lower() 
               for keyword in ["analytics", "reporting", "dashboard", "metrics"]):
            if "analytics" not in existing_types and "reporting" not in existing_types:
                custom_phases.append(
                    Phase(
                        id=str(uuid.uuid4()),
                        name="Analytics and Reporting",
                        description="Build analytics engine and reporting features",
                        objective="Enable data analytics and report generation",
                        complexity=5,
                        priority=4,
                        deliverables=[
                            "Analytics data pipeline",
                            "Report templates",
                            "Dashboard components",
                            "Export functionality"
                        ]
                    )
                )
        
        return custom_phases
    
    def _add_dependencies(self, phases: List[Phase]) -> None:
        """Add dependencies between phases."""
        # Create phase index by name
        phase_by_name = {p.name.lower(): p for p in phases}
        
        # Define dependency rules
        dependency_rules = {
            "data models": ["foundation"],
            "core business logic": ["foundation", "data models"],
            "api development": ["core business logic", "data models"],
            "frontend": ["api development", "foundation"],
            "integration": ["core business logic", "api development"],
            "testing": ["core business logic"],  # Can start after core logic
            "deployment": ["testing"],
            "documentation": [],  # Can run in parallel
            "optimization": ["testing", "deployment"],
            "real-time": ["api development", "frontend"],
            "machine learning": ["data models", "core business logic"],
            "analytics": ["data models", "api development"]
        }
        
        # Apply dependencies
        for phase in phases:
            phase_key = phase.name.lower()
            
            # Check for matching rules
            for rule_key, deps in dependency_rules.items():
                if rule_key in phase_key:
                    for dep_name in deps:
                        # Find matching phase
                        for dep_key, dep_phase in phase_by_name.items():
                            if dep_name in dep_key:
                                phase.dependencies.append(
                                    Dependency(
                                        source_id=dep_phase.id,
                                        target_id=phase.id,
                                        dependency_type="finish_to_start"
                                    )
                                )
                                break
        
        # Ensure no circular dependencies by ordering
        self._validate_dependencies(phases)
    
    def _validate_dependencies(self, phases: List[Phase]) -> None:
        """Validate and fix dependency issues."""
        # Build dependency graph
        graph = {}
        phase_index = {p.id: p for p in phases}
        
        for phase in phases:
            graph[phase.id] = [dep.source_id for dep in phase.dependencies]
        
        # Topological sort to detect cycles
        visited = set()
        rec_stack = set()
        order = []
        
        def visit(node_id: str) -> bool:
            if node_id in rec_stack:
                return False  # Cycle detected
            
            if node_id in visited:
                return True
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for dep_id in graph.get(node_id, []):
                if not visit(dep_id):
                    # Remove this dependency to break cycle
                    phase = phase_index[node_id]
                    phase.dependencies = [
                        d for d in phase.dependencies 
                        if d.source_id != dep_id
                    ]
                    logger.warning(
                        f"Removed circular dependency: {phase.name} -> {phase_index[dep_id].name}"
                    )
            
            rec_stack.remove(node_id)
            order.append(node_id)
            return True
        
        # Visit all nodes
        for phase_id in graph:
            visit(phase_id)
    
    def _consolidate_phases(self, phases: List[Phase], max_phases: int) -> List[Phase]:
        """Consolidate phases if exceeding maximum."""
        if len(phases) <= max_phases:
            return phases
        
        logger.info(f"Consolidating {len(phases)} phases to {max_phases}")
        
        # Group related phases
        consolidation_groups = [
            ["documentation", "testing"],  # Can be combined
            ["optimization", "deployment"],  # Can be combined
            ["analytics", "reporting"],  # Similar phases
        ]
        
        consolidated = []
        used_phases = set()
        
        # First, handle consolidation groups
        for group in consolidation_groups:
            group_phases = [p for p in phases if any(
                keyword in p.name.lower() for keyword in group
            ) and p.id not in used_phases]
            
            if len(group_phases) > 1:
                # Merge phases
                merged = self._merge_phases(group_phases)
                consolidated.append(merged)
                used_phases.update(p.id for p in group_phases)
        
        # Add remaining phases
        for phase in phases:
            if phase.id not in used_phases:
                consolidated.append(phase)
        
        # If still too many, merge lowest complexity phases
        while len(consolidated) > max_phases:
            # Find two adjacent phases with lowest combined complexity
            min_complexity = float('inf')
            merge_index = -1
            
            for i in range(len(consolidated) - 1):
                combined_complexity = (
                    consolidated[i].complexity + 
                    consolidated[i + 1].complexity
                )
                if combined_complexity < min_complexity:
                    # Check if they can be merged (no dependency conflicts)
                    if not self._has_dependency_conflict(
                        consolidated[i], 
                        consolidated[i + 1]
                    ):
                        min_complexity = combined_complexity
                        merge_index = i
            
            if merge_index >= 0:
                # Merge the phases
                merged = self._merge_phases([
                    consolidated[merge_index],
                    consolidated[merge_index + 1]
                ])
                consolidated[merge_index] = merged
                consolidated.pop(merge_index + 1)
            else:
                # Can't merge more, stop
                break
        
        return consolidated[:max_phases]
    
    def _merge_phases(self, phases: List[Phase]) -> Phase:
        """Merge multiple phases into one."""
        # Create merged phase
        merged = Phase(
            id=str(uuid.uuid4()),
            name=" + ".join(p.name for p in phases),
            description=f"Combined phase: {', '.join(p.name for p in phases)}",
            objective=" and ".join(p.objective for p in phases),
            complexity=max(p.complexity for p in phases),
            priority=max(p.priority for p in phases)
        )
        
        # Merge deliverables
        merged.deliverables = []
        for phase in phases:
            merged.deliverables.extend(phase.deliverables)
        
        # Merge dependencies (union of all dependencies)
        all_deps = []
        for phase in phases:
            all_deps.extend(phase.dependencies)
        
        # Remove internal dependencies
        phase_ids = {p.id for p in phases}
        merged.dependencies = [
            d for d in all_deps 
            if d.source_id not in phase_ids
        ]
        
        # Merge required tools
        tools = set()
        for phase in phases:
            tools.update(phase.required_tools)
        merged.required_tools = list(tools)
        
        return merged
    
    def _has_dependency_conflict(self, phase1: Phase, phase2: Phase) -> bool:
        """Check if two phases have dependency conflicts."""
        # Phase 2 depends on phase 1
        for dep in phase2.dependencies:
            if dep.source_id == phase1.id:
                return True
        
        # Phase 1 depends on phase 2
        for dep in phase1.dependencies:
            if dep.source_id == phase2.id:
                return True
        
        return False
    
    def _estimate_phase_duration(
        self,
        phase: Phase,
        analysis_results: Dict[str, Any]
    ) -> timedelta:
        """Estimate phase duration."""
        # Base duration on complexity
        base_hours = phase.complexity * 2  # 2 hours per complexity point
        
        # Adjust based on project complexity
        project_complexity = analysis_results.get("complexity", {}).get("overall", 5)
        complexity_factor = 1 + (project_complexity - 5) * 0.1
        
        # Adjust based on phase type
        if "optimization" in phase.name.lower():
            base_hours *= 1.5  # Optimization takes longer
        elif "documentation" in phase.name.lower():
            base_hours *= 0.7  # Documentation is faster
        elif "testing" in phase.name.lower():
            base_hours *= 1.2  # Testing needs thorough time
        
        adjusted_hours = base_hours * complexity_factor
        
        return timedelta(hours=adjusted_hours)
    
    def _adapt_phases(
        self,
        template_phases: List[Phase],
        project_spec: ProjectSpec
    ) -> List[Phase]:
        """Adapt template phases for specific project."""
        adapted = []
        
        for template_phase in template_phases:
            # Create new phase instance
            phase = Phase(
                id=str(uuid.uuid4()),
                name=self._customize_phase_name(template_phase.name, project_spec),
                description=template_phase.description,
                objective=self._customize_objective(template_phase.objective, project_spec),
                complexity=template_phase.complexity,
                priority=template_phase.priority,
                deliverables=template_phase.deliverables.copy()
            )
            
            adapted.append(phase)
        
        return adapted
    
    def _store_phases(self, project_spec: ProjectSpec, phases: List[Phase]) -> None:
        """Store generated phases in memory."""
        # Store complete phase list
        self.memory_store.add(
            key=f"generated_phases_{project_spec.metadata.name}",
            value=[p.to_dict() for p in phases],
            entry_type=MemoryType.RESULT,
            phase="planning",
            tags={"phases", project_spec.metadata.name},
            importance=9.0
        )
        
        # Store by project type for future reference
        project_type = self.memory_store.get_by_key(
            f"project_type_{project_spec.metadata.name}"
        )
        if project_type:
            self.memory_store.add(
                key=f"phases_template_{project_type.value}",
                value=[p.to_dict() for p in phases],
                entry_type=MemoryType.CONTEXT,
                phase="planning",
                tags={f"phases_{project_type.value}"},
                importance=7.0
            )