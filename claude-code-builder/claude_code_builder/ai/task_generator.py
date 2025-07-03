"""Task generator for AI planning."""

from typing import Dict, List, Any, Optional
from datetime import timedelta
import uuid

from ..models import (
    ProjectSpec,
    Phase,
    Task,
    TaskStatus,
    MemoryStore,
    MemoryType
)
from ..config import AIConfig
from ..logging import logger
from ..exceptions import PlanningError


class TaskTemplate:
    """Template for common task patterns."""
    
    def __init__(
        self,
        name: str,
        description: str,
        command: Optional[str] = None,
        function: Optional[str] = None,
        weight: float = 1.0
    ):
        self.name = name
        self.description = description
        self.command = command
        self.function = function
        self.weight = weight
        self.parameters: Dict[str, Any] = {}
        self.tags: List[str] = []


class TaskGenerator:
    """Generates tasks for project phases."""
    
    def __init__(self, ai_config: AIConfig, memory_store: MemoryStore):
        """Initialize task generator."""
        self.ai_config = ai_config
        self.memory_store = memory_store
        
        # Initialize task templates
        self._init_templates()
    
    def _init_templates(self):
        """Initialize common task templates."""
        self.templates = {
            # Foundation tasks
            "create_structure": TaskTemplate(
                "Create project structure",
                "Set up directory structure and initial files",
                command="mkdir -p {directories}",
                weight=1.0
            ),
            "init_git": TaskTemplate(
                "Initialize Git repository",
                "Set up version control with .gitignore",
                command="git init && git add .",
                weight=0.5
            ),
            "setup_config": TaskTemplate(
                "Set up configuration",
                "Create configuration files and environment settings",
                function="create_config_files",
                weight=1.5
            ),
            
            # Development tasks
            "create_models": TaskTemplate(
                "Create data models",
                "Implement domain models and schemas",
                function="generate_models",
                weight=2.0
            ),
            "implement_service": TaskTemplate(
                "Implement service",
                "Create service layer with business logic",
                function="generate_service",
                weight=3.0
            ),
            "create_api": TaskTemplate(
                "Create API endpoint",
                "Implement REST/GraphQL endpoint",
                function="generate_api_endpoint",
                weight=2.0
            ),
            
            # Testing tasks
            "write_tests": TaskTemplate(
                "Write tests",
                "Create unit and integration tests",
                function="generate_tests",
                weight=2.0
            ),
            "run_tests": TaskTemplate(
                "Run test suite",
                "Execute all tests and verify coverage",
                command="pytest -v --cov",
                weight=1.0
            ),
            
            # Deployment tasks
            "create_dockerfile": TaskTemplate(
                "Create Dockerfile",
                "Set up container configuration",
                function="generate_dockerfile",
                weight=1.0
            ),
            "setup_ci": TaskTemplate(
                "Set up CI/CD",
                "Configure continuous integration pipeline",
                function="generate_ci_config",
                weight=2.0
            )
        }
    
    async def generate_for_phase(
        self,
        phase: Phase,
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any],
        max_tasks: int = 15
    ) -> List[Task]:
        """Generate tasks for a specific phase."""
        logger.info(f"Generating tasks for phase: {phase.name}")
        
        try:
            # Check memory for similar phase tasks
            similar_tasks = self._check_similar_phase_tasks(phase.name)
            if similar_tasks and not self.ai_config.adaptive_planning:
                logger.info("Using tasks from similar phase")
                return self._adapt_tasks(similar_tasks, phase, project_spec)
            
            # Generate tasks based on phase type
            tasks = []
            
            # Identify phase category
            phase_category = self._categorize_phase(phase.name)
            
            # Generate tasks by category
            if phase_category == "foundation":
                tasks = self._generate_foundation_tasks(phase, project_spec)
            elif phase_category == "data":
                tasks = self._generate_data_tasks(phase, project_spec)
            elif phase_category == "logic":
                tasks = self._generate_logic_tasks(phase, project_spec)
            elif phase_category == "api":
                tasks = self._generate_api_tasks(phase, project_spec)
            elif phase_category == "frontend":
                tasks = self._generate_frontend_tasks(phase, project_spec)
            elif phase_category == "testing":
                tasks = self._generate_testing_tasks(phase, project_spec)
            elif phase_category == "deployment":
                tasks = self._generate_deployment_tasks(phase, project_spec)
            else:
                tasks = self._generate_generic_tasks(phase, project_spec, analysis_results)
            
            # Add dependencies between tasks
            self._add_task_dependencies(tasks, phase)
            
            # Optimize task count
            if len(tasks) > max_tasks:
                tasks = self._consolidate_tasks(tasks, max_tasks)
            
            # Store in memory
            self._store_tasks(phase.name, tasks)
            
            logger.info(f"Generated {len(tasks)} tasks for phase {phase.name}")
            return tasks
            
        except Exception as e:
            logger.error(f"Task generation failed for phase {phase.name}", error=str(e))
            raise PlanningError(f"Failed to generate tasks: {str(e)}", cause=e)
    
    def _categorize_phase(self, phase_name: str) -> str:
        """Categorize phase by type."""
        name_lower = phase_name.lower()
        
        if any(keyword in name_lower for keyword in ["foundation", "setup", "structure"]):
            return "foundation"
        elif any(keyword in name_lower for keyword in ["data", "model", "schema", "database"]):
            return "data"
        elif any(keyword in name_lower for keyword in ["logic", "business", "core", "service"]):
            return "logic"
        elif any(keyword in name_lower for keyword in ["api", "endpoint", "rest", "graphql"]):
            return "api"
        elif any(keyword in name_lower for keyword in ["frontend", "ui", "interface", "client"]):
            return "frontend"
        elif any(keyword in name_lower for keyword in ["test", "testing", "qa"]):
            return "testing"
        elif any(keyword in name_lower for keyword in ["deploy", "deployment", "release"]):
            return "deployment"
        else:
            return "generic"
    
    def _generate_foundation_tasks(self, phase: Phase, project_spec: ProjectSpec) -> List[Task]:
        """Generate foundation phase tasks."""
        tasks = []
        
        # Project structure
        tasks.append(self._create_task(
            "Create project structure",
            "Set up directory layout and initial files",
            command="mkdir -p src tests docs config",
            weight=1.0,
            tags=["setup", "structure"]
        ))
        
        # Package initialization
        if project_spec.metadata.name:
            tasks.append(self._create_task(
                "Initialize package",
                f"Create {project_spec.metadata.name} package structure",
                function="create_package_structure",
                parameters={"package_name": project_spec.metadata.name},
                weight=1.5,
                tags=["package", "init"]
            ))
        
        # Configuration
        tasks.append(self._create_task(
            "Set up configuration",
            "Create configuration files and settings",
            function="generate_config_files",
            parameters={
                "config_format": "yaml",
                "include_env": True
            },
            weight=1.5,
            tags=["config"]
        ))
        
        # Dependencies
        if project_spec.technologies:
            tasks.append(self._create_task(
                "Set up dependencies",
                "Configure package dependencies and requirements",
                function="generate_requirements",
                parameters={
                    "technologies": [t.to_dict() for t in project_spec.technologies]
                },
                weight=2.0,
                tags=["dependencies"]
            ))
        
        # Development environment
        tasks.append(self._create_task(
            "Configure development environment",
            "Set up linting, formatting, and pre-commit hooks",
            function="setup_dev_environment",
            weight=1.5,
            tags=["development", "tooling"]
        ))
        
        # Version control
        if project_spec.build_requirements.deployment_platforms:
            tasks.append(self._create_task(
                "Initialize version control",
                "Set up Git with appropriate .gitignore",
                command="git init",
                weight=0.5,
                tags=["git", "vcs"]
            ))
        
        return tasks
    
    def _generate_data_tasks(self, phase: Phase, project_spec: ProjectSpec) -> List[Task]:
        """Generate data/model phase tasks."""
        tasks = []
        
        # Database setup
        databases = [t for t in project_spec.technologies if t.category == "database"]
        if databases:
            for db in databases:
                tasks.append(self._create_task(
                    f"Set up {db.name} database",
                    f"Configure {db.name} connection and settings",
                    function="setup_database",
                    parameters={"database": db.to_dict()},
                    weight=2.0,
                    tags=["database", db.name.lower()]
                ))
        
        # Data models
        if project_spec.features:
            # Group features by domain
            domains = self._group_features_by_domain(project_spec.features)
            
            for domain, features in domains.items():
                tasks.append(self._create_task(
                    f"Create {domain} models",
                    f"Implement data models for {domain} domain",
                    function="generate_domain_models",
                    parameters={
                        "domain": domain,
                        "features": [f.to_dict() for f in features]
                    },
                    weight=2.5,
                    tags=["models", domain.lower()]
                ))
        
        # Migrations
        if databases:
            tasks.append(self._create_task(
                "Create database migrations",
                "Generate migration files for schema",
                function="generate_migrations",
                weight=1.5,
                tags=["migrations", "database"]
            ))
        
        # Validation
        tasks.append(self._create_task(
            "Implement data validation",
            "Create validation rules and schemas",
            function="generate_validators",
            weight=2.0,
            tags=["validation", "data"]
        ))
        
        # Seed data
        tasks.append(self._create_task(
            "Create seed data",
            "Generate sample data for development",
            function="generate_seed_data",
            weight=1.0,
            tags=["seed", "fixtures"]
        ))
        
        return tasks
    
    def _generate_logic_tasks(self, phase: Phase, project_spec: ProjectSpec) -> List[Task]:
        """Generate business logic phase tasks."""
        tasks = []
        
        # Service layer
        for feature in project_spec.features:
            if feature.complexity >= 3:  # Complex features get dedicated services
                tasks.append(self._create_task(
                    f"Implement {feature.name} service",
                    f"Create service layer for {feature.name}",
                    function="generate_service",
                    parameters={
                        "feature": feature.to_dict(),
                        "include_tests": True
                    },
                    weight=3.0,
                    tags=["service", feature.name.lower().replace(" ", "_")]
                ))
        
        # Business rules
        if project_spec.features:
            tasks.append(self._create_task(
                "Implement business rules",
                "Create rule engine and validators",
                function="generate_business_rules",
                parameters={
                    "features": [f.to_dict() for f in project_spec.features]
                },
                weight=2.5,
                tags=["rules", "logic"]
            ))
        
        # Error handling
        tasks.append(self._create_task(
            "Implement error handling",
            "Create error handlers and recovery logic",
            function="generate_error_handlers",
            weight=2.0,
            tags=["errors", "exceptions"]
        ))
        
        # Logging
        tasks.append(self._create_task(
            "Set up logging",
            "Configure structured logging system",
            function="setup_logging",
            weight=1.5,
            tags=["logging", "monitoring"]
        ))
        
        return tasks
    
    def _generate_api_tasks(self, phase: Phase, project_spec: ProjectSpec) -> List[Task]:
        """Generate API phase tasks."""
        tasks = []
        
        # API framework setup
        tasks.append(self._create_task(
            "Set up API framework",
            "Configure REST/GraphQL framework",
            function="setup_api_framework",
            parameters={
                "framework": self._detect_api_framework(project_spec),
                "enable_cors": True,
                "enable_validation": True
            },
            weight=2.0,
            tags=["api", "framework"]
        ))
        
        # Authentication
        if project_spec.security_requirements.authentication_required:
            tasks.append(self._create_task(
                "Implement authentication",
                "Set up authentication system",
                function="generate_auth_system",
                parameters={
                    "methods": project_spec.security_requirements.authentication_methods,
                    "include_jwt": True
                },
                weight=3.0,
                tags=["auth", "security"]
            ))
        
        # API endpoints
        for endpoint in project_spec.api_endpoints[:10]:  # First 10 endpoints
            tasks.append(self._create_task(
                f"Implement {endpoint.method} {endpoint.path}",
                endpoint.description,
                function="generate_api_endpoint",
                parameters={
                    "endpoint": endpoint.to_dict(),
                    "include_tests": True
                },
                weight=2.0,
                tags=["endpoint", endpoint.method.lower()]
            ))
        
        # If more than 10 endpoints, group remaining
        if len(project_spec.api_endpoints) > 10:
            tasks.append(self._create_task(
                "Implement remaining API endpoints",
                f"Create {len(project_spec.api_endpoints) - 10} additional endpoints",
                function="generate_bulk_endpoints",
                parameters={
                    "endpoints": [e.to_dict() for e in project_spec.api_endpoints[10:]]
                },
                weight=3.0,
                tags=["endpoints", "bulk"]
            ))
        
        # API documentation
        tasks.append(self._create_task(
            "Generate API documentation",
            "Create OpenAPI/Swagger documentation",
            function="generate_api_docs",
            weight=1.5,
            tags=["docs", "openapi"]
        ))
        
        # Rate limiting
        if project_spec.security_requirements.rate_limiting:
            tasks.append(self._create_task(
                "Implement rate limiting",
                "Set up API rate limiting",
                function="setup_rate_limiting",
                weight=1.5,
                tags=["security", "rate-limit"]
            ))
        
        return tasks
    
    def _generate_frontend_tasks(self, phase: Phase, project_spec: ProjectSpec) -> List[Task]:
        """Generate frontend phase tasks."""
        tasks = []
        
        # Frontend setup
        framework = self._detect_frontend_framework(project_spec)
        tasks.append(self._create_task(
            f"Set up {framework} project",
            f"Initialize {framework} with configuration",
            function="setup_frontend_framework",
            parameters={"framework": framework},
            weight=2.0,
            tags=["frontend", "setup"]
        ))
        
        # Components
        ui_components = self._identify_ui_components(project_spec)
        for component in ui_components[:5]:  # First 5 components
            tasks.append(self._create_task(
                f"Create {component} component",
                f"Implement {component} with styling",
                function="generate_component",
                parameters={
                    "component": component,
                    "include_tests": True
                },
                weight=2.0,
                tags=["component", component.lower()]
            ))
        
        # Pages/Routes
        tasks.append(self._create_task(
            "Set up routing",
            "Configure application routes",
            function="setup_routing",
            weight=1.5,
            tags=["routing", "navigation"]
        ))
        
        # State management
        tasks.append(self._create_task(
            "Implement state management",
            "Set up global state management",
            function="setup_state_management",
            weight=2.5,
            tags=["state", "redux"]
        ))
        
        # API integration
        tasks.append(self._create_task(
            "Integrate with API",
            "Connect frontend to backend API",
            function="setup_api_client",
            weight=2.0,
            tags=["api", "integration"]
        ))
        
        # Styling
        tasks.append(self._create_task(
            "Implement styling system",
            "Set up CSS/styling framework",
            function="setup_styling",
            weight=1.5,
            tags=["styling", "css"]
        ))
        
        return tasks
    
    def _generate_testing_tasks(self, phase: Phase, project_spec: ProjectSpec) -> List[Task]:
        """Generate testing phase tasks."""
        tasks = []
        
        # Test setup
        tasks.append(self._create_task(
            "Set up test framework",
            "Configure testing tools and structure",
            function="setup_test_framework",
            parameters={
                "framework": project_spec.build_requirements.test_framework or "pytest",
                "coverage": True
            },
            weight=1.5,
            tags=["testing", "setup"]
        ))
        
        # Unit tests
        tasks.append(self._create_task(
            "Write unit tests",
            "Create unit tests for core functionality",
            function="generate_unit_tests",
            parameters={"coverage_target": 0.8},
            weight=3.0,
            tags=["unit-tests", "testing"]
        ))
        
        # Integration tests
        tasks.append(self._create_task(
            "Write integration tests",
            "Create tests for component interactions",
            function="generate_integration_tests",
            weight=2.5,
            tags=["integration-tests", "testing"]
        ))
        
        # E2E tests
        if project_spec.features:
            tasks.append(self._create_task(
                "Write end-to-end tests",
                "Create E2E tests for user workflows",
                function="generate_e2e_tests",
                parameters={
                    "features": [f.name for f in project_spec.features]
                },
                weight=3.0,
                tags=["e2e-tests", "testing"]
            ))
        
        # Performance tests
        if project_spec.performance_requirements.throughput_rps > 100:
            tasks.append(self._create_task(
                "Create performance tests",
                "Implement load and stress tests",
                function="generate_performance_tests",
                parameters={
                    "target_rps": project_spec.performance_requirements.throughput_rps
                },
                weight=2.0,
                tags=["performance", "testing"]
            ))
        
        # Test data
        tasks.append(self._create_task(
            "Create test fixtures",
            "Generate test data and mocks",
            function="generate_test_fixtures",
            weight=1.5,
            tags=["fixtures", "test-data"]
        ))
        
        return tasks
    
    def _generate_deployment_tasks(self, phase: Phase, project_spec: ProjectSpec) -> List[Task]:
        """Generate deployment phase tasks."""
        tasks = []
        
        # Containerization
        if project_spec.build_requirements.docker:
            tasks.append(self._create_task(
                "Create Dockerfile",
                "Set up container configuration",
                function="generate_dockerfile",
                parameters={"multi_stage": True},
                weight=1.5,
                tags=["docker", "container"]
            ))
            
            if project_spec.build_requirements.docker_compose:
                tasks.append(self._create_task(
                    "Create docker-compose",
                    "Set up multi-container orchestration",
                    function="generate_docker_compose",
                    weight=2.0,
                    tags=["docker-compose", "orchestration"]
                ))
        
        # CI/CD
        for ci_platform in project_spec.build_requirements.ci_cd:
            tasks.append(self._create_task(
                f"Configure {ci_platform} CI/CD",
                f"Set up continuous integration on {ci_platform}",
                function="generate_ci_config",
                parameters={"platform": ci_platform},
                weight=2.5,
                tags=["ci-cd", ci_platform.lower()]
            ))
        
        # Infrastructure
        for platform in project_spec.build_requirements.deployment_platforms:
            tasks.append(self._create_task(
                f"Configure {platform} deployment",
                f"Set up infrastructure for {platform}",
                function="generate_infrastructure_config",
                parameters={"platform": platform},
                weight=3.0,
                tags=["infrastructure", platform.lower()]
            ))
        
        # Monitoring
        tasks.append(self._create_task(
            "Set up monitoring",
            "Configure application monitoring",
            function="setup_monitoring",
            weight=2.0,
            tags=["monitoring", "observability"]
        ))
        
        # Secrets management
        tasks.append(self._create_task(
            "Configure secrets",
            "Set up secure secret management",
            function="setup_secrets_management",
            weight=2.0,
            tags=["secrets", "security"]
        ))
        
        return tasks
    
    def _generate_generic_tasks(
        self,
        phase: Phase,
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any]
    ) -> List[Task]:
        """Generate generic tasks for uncategorized phases."""
        tasks = []
        
        # Analyze phase deliverables
        for deliverable in phase.deliverables:
            task_name = f"Complete: {deliverable}"
            tasks.append(self._create_task(
                task_name,
                f"Implement deliverable: {deliverable}",
                function="generic_implementation",
                parameters={
                    "deliverable": deliverable,
                    "phase": phase.name
                },
                weight=2.0,
                tags=["deliverable", phase.name.lower().replace(" ", "_")]
            ))
        
        # Add setup task
        tasks.insert(0, self._create_task(
            f"Set up {phase.name}",
            f"Initialize phase: {phase.name}",
            function="phase_setup",
            parameters={"phase": phase.to_dict()},
            weight=1.0,
            tags=["setup", phase.name.lower().replace(" ", "_")]
        ))
        
        # Add validation task
        tasks.append(self._create_task(
            f"Validate {phase.name}",
            f"Verify phase completion: {phase.name}",
            function="phase_validation",
            parameters={"phase": phase.to_dict()},
            weight=1.5,
            tags=["validation", phase.name.lower().replace(" ", "_")]
        ))
        
        return tasks
    
    def _create_task(
        self,
        name: str,
        description: str,
        command: Optional[str] = None,
        function: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        weight: float = 1.0,
        tags: Optional[List[str]] = None
    ) -> Task:
        """Create a task instance."""
        task = Task(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            command=command,
            function=function,
            parameters=parameters or {},
            weight=weight,
            tags=set(tags or [])
        )
        
        # Estimate duration based on weight
        task.estimated_duration = timedelta(minutes=weight * 30)
        
        return task
    
    def _add_task_dependencies(self, tasks: List[Task], phase: Phase) -> None:
        """Add dependencies between tasks."""
        if not tasks:
            return
        
        # Simple linear dependencies for now
        # More complex logic can be added based on task types
        
        # Setup tasks should run first
        setup_tasks = [t for t in tasks if "setup" in t.tags or "init" in t.tags]
        implementation_tasks = [t for t in tasks if t not in setup_tasks and "test" not in t.tags]
        test_tasks = [t for t in tasks if "test" in t.tags]
        
        # Setup -> Implementation -> Tests
        if setup_tasks and implementation_tasks:
            for impl_task in implementation_tasks:
                for setup_task in setup_tasks:
                    impl_task.dependencies.append(setup_task.id)
        
        if implementation_tasks and test_tasks:
            for test_task in test_tasks:
                # Tests depend on at least one implementation task
                if implementation_tasks:
                    test_task.dependencies.append(implementation_tasks[0].id)
    
    def _consolidate_tasks(self, tasks: List[Task], max_tasks: int) -> List[Task]:
        """Consolidate tasks if exceeding maximum."""
        if len(tasks) <= max_tasks:
            return tasks
        
        logger.info(f"Consolidating {len(tasks)} tasks to {max_tasks}")
        
        # Group similar tasks
        grouped = {}
        for task in tasks:
            # Group by primary tag
            primary_tag = list(task.tags)[0] if task.tags else "other"
            if primary_tag not in grouped:
                grouped[primary_tag] = []
            grouped[primary_tag].append(task)
        
        # Consolidate groups
        consolidated = []
        
        for tag, group_tasks in grouped.items():
            if len(group_tasks) == 1:
                consolidated.append(group_tasks[0])
            else:
                # Merge similar tasks
                merged = self._merge_tasks(group_tasks, tag)
                consolidated.append(merged)
        
        # If still too many, merge lowest weight tasks
        while len(consolidated) > max_tasks:
            # Find task with lowest weight
            min_weight_idx = min(
                range(len(consolidated)),
                key=lambda i: consolidated[i].weight
            )
            
            # Merge with adjacent task
            if min_weight_idx > 0:
                merged = self._merge_tasks(
                    [consolidated[min_weight_idx - 1], consolidated[min_weight_idx]],
                    "combined"
                )
                consolidated[min_weight_idx - 1] = merged
                consolidated.pop(min_weight_idx)
            else:
                consolidated.pop(min_weight_idx)
        
        return consolidated[:max_tasks]
    
    def _merge_tasks(self, tasks: List[Task], group_name: str) -> Task:
        """Merge multiple tasks into one."""
        merged = Task(
            id=str(uuid.uuid4()),
            name=f"{group_name.title()} tasks ({len(tasks)} items)",
            description=f"Combined tasks: {', '.join(t.name for t in tasks[:3])}...",
            function="batch_implementation",
            parameters={
                "tasks": [
                    {
                        "name": t.name,
                        "function": t.function,
                        "parameters": t.parameters
                    }
                    for t in tasks
                ]
            },
            weight=sum(t.weight for t in tasks),
            tags=set().union(*[t.tags for t in tasks])
        )
        
        # Merge dependencies
        all_deps = set()
        for task in tasks:
            all_deps.update(task.dependencies)
        merged.dependencies = list(all_deps)
        
        return merged
    
    def _group_features_by_domain(self, features: List['Feature']) -> Dict[str, List['Feature']]:
        """Group features by domain."""
        domains = {}
        
        for feature in features:
            # Simple domain extraction from feature name
            words = feature.name.lower().split()
            
            # Common domain keywords
            if any(word in words for word in ["user", "account", "profile", "auth"]):
                domain = "user"
            elif any(word in words for word in ["product", "item", "catalog"]):
                domain = "product"
            elif any(word in words for word in ["order", "cart", "payment"]):
                domain = "commerce"
            elif any(word in words for word in ["content", "post", "article"]):
                domain = "content"
            elif any(word in words for word in ["admin", "management", "dashboard"]):
                domain = "admin"
            else:
                domain = "core"
            
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(feature)
        
        return domains
    
    def _detect_api_framework(self, project_spec: ProjectSpec) -> str:
        """Detect API framework from technologies."""
        frameworks = {
            "fastapi": ["fastapi", "fast-api"],
            "django": ["django", "django-rest"],
            "flask": ["flask"],
            "express": ["express", "node"],
            "graphql": ["graphql", "apollo"]
        }
        
        tech_names = [t.name.lower() for t in project_spec.technologies]
        
        for framework, keywords in frameworks.items():
            if any(keyword in tech_name for tech_name in tech_names for keyword in keywords):
                return framework
        
        # Default based on language
        primary_language = next(
            (t.name for t in project_spec.technologies if t.category == "language"),
            "Python"
        )
        
        if primary_language == "Python":
            return "fastapi"
        elif primary_language in ["JavaScript", "TypeScript"]:
            return "express"
        else:
            return "generic"
    
    def _detect_frontend_framework(self, project_spec: ProjectSpec) -> str:
        """Detect frontend framework from technologies."""
        frameworks = {
            "react": ["react", "next"],
            "vue": ["vue", "nuxt"],
            "angular": ["angular"],
            "svelte": ["svelte", "sveltekit"]
        }
        
        tech_names = [t.name.lower() for t in project_spec.technologies]
        
        for framework, keywords in frameworks.items():
            if any(keyword in tech_name for tech_name in tech_names for keyword in keywords):
                return framework
        
        return "react"  # Default
    
    def _identify_ui_components(self, project_spec: ProjectSpec) -> List[str]:
        """Identify UI components from features."""
        components = set()
        
        # Common component patterns
        component_keywords = {
            "Navigation": ["nav", "menu", "header"],
            "Dashboard": ["dashboard", "overview", "home"],
            "Form": ["form", "input", "submit"],
            "Table": ["table", "list", "grid"],
            "Card": ["card", "item", "preview"],
            "Modal": ["modal", "dialog", "popup"],
            "Chart": ["chart", "graph", "analytics"],
            "Profile": ["profile", "user", "account"]
        }
        
        # Check features for component keywords
        for feature in project_spec.features:
            feature_text = (feature.name + " " + feature.description).lower()
            
            for component, keywords in component_keywords.items():
                if any(keyword in feature_text for keyword in keywords):
                    components.add(component)
        
        # Ensure minimum components
        if not components:
            components = {"Navigation", "Dashboard", "Form", "Table"}
        
        return list(components)
    
    def _check_similar_phase_tasks(self, phase_name: str) -> Optional[List[Task]]:
        """Check memory for similar phase tasks."""
        # Search for tasks from similar phases
        query_result = self.memory_store.query(
            MemoryQuery(
                key_pattern=f"phase_tasks_{phase_name.lower().replace(' ', '_')}",
                max_results=1
            )
        )
        
        if query_result:
            return query_result[0].value
        
        return None
    
    def _adapt_tasks(
        self,
        template_tasks: List[Dict[str, Any]],
        phase: Phase,
        project_spec: ProjectSpec
    ) -> List[Task]:
        """Adapt template tasks for specific project."""
        adapted = []
        
        for task_data in template_tasks:
            task = Task(
                id=str(uuid.uuid4()),
                name=task_data["name"],
                description=task_data["description"],
                command=task_data.get("command"),
                function=task_data.get("function"),
                parameters=task_data.get("parameters", {}),
                weight=task_data.get("weight", 1.0),
                tags=set(task_data.get("tags", []))
            )
            
            # Customize parameters for project
            if task.function and "generate" in task.function:
                task.parameters["project_name"] = project_spec.metadata.name
                task.parameters["project_version"] = project_spec.metadata.version
            
            adapted.append(task)
        
        return adapted
    
    def _store_tasks(self, phase_name: str, tasks: List[Task]) -> None:
        """Store generated tasks in memory."""
        # Store tasks for the phase
        self.memory_store.add(
            key=f"phase_tasks_{phase_name.lower().replace(' ', '_')}",
            value=[t.to_dict() for t in tasks],
            entry_type=MemoryType.RESULT,
            phase="planning",
            tags={"tasks", phase_name.lower().replace(" ", "_")},
            importance=7.0
        )
        
        # Store task patterns for learning
        task_patterns = {}
        for task in tasks:
            if task.function:
                pattern_key = f"{task.function}_{list(task.tags)[0] if task.tags else 'generic'}"
                if pattern_key not in task_patterns:
                    task_patterns[pattern_key] = []
                task_patterns[pattern_key].append({
                    "name": task.name,
                    "parameters": task.parameters,
                    "weight": task.weight
                })
        
        if task_patterns:
            self.memory_store.add(
                key="task_generation_patterns",
                value=task_patterns,
                entry_type=MemoryType.LEARNING,
                phase="planning",
                tags={"patterns", "tasks"},
                importance=6.0
            )