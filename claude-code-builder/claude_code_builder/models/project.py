"""Project specification and configuration models."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from datetime import datetime

from .base import SerializableModel, TimestampedModel, IdentifiedModel, VersionedModel
from ..exceptions import ValidationError


@dataclass
class Technology:
    """Technology or tool specification."""
    
    name: str
    version: Optional[str] = None
    package: Optional[str] = None
    category: str = "general"
    required: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate technology specification."""
        if not self.name:
            raise ValidationError("Technology name is required")
        
        valid_categories = ["language", "framework", "database", "tool", "service", "general"]
        if self.category not in valid_categories:
            raise ValidationError(f"Invalid category: {self.category}")


@dataclass
class Feature:
    """Project feature specification."""
    
    name: str
    description: str
    priority: str = "medium"
    complexity: int = 3
    dependencies: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    technical_requirements: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Validate feature specification."""
        if not self.name:
            raise ValidationError("Feature name is required")
        
        valid_priorities = ["low", "medium", "high", "critical"]
        if self.priority not in valid_priorities:
            raise ValidationError(f"Invalid priority: {self.priority}")
        
        if not 1 <= self.complexity <= 10:
            raise ValidationError(f"Complexity must be between 1 and 10")


@dataclass
class APIEndpoint:
    """API endpoint specification."""
    
    path: str
    method: str
    description: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    authentication: bool = True
    rate_limit: Optional[int] = None
    
    def validate(self) -> None:
        """Validate API endpoint."""
        if not self.path:
            raise ValidationError("API path is required")
        
        valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
        if self.method.upper() not in valid_methods:
            raise ValidationError(f"Invalid HTTP method: {self.method}")


@dataclass
class ProjectMetadata:
    """Project metadata information."""
    
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    license: str = "MIT"
    repository: Optional[str] = None
    homepage: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Validate project metadata."""
        if not self.name:
            raise ValidationError("Project name is required")
        
        # Validate version format
        import re
        if not re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$', self.version):
            raise ValidationError(f"Invalid version format: {self.version}")


@dataclass
class BuildRequirements:
    """Build requirements and constraints."""
    
    min_python_version: str = "3.8"
    max_python_version: Optional[str] = None
    system_dependencies: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    docker: bool = False
    docker_compose: bool = False
    ci_cd: List[str] = field(default_factory=list)
    deployment_platforms: List[str] = field(default_factory=list)


@dataclass
class SecurityRequirements:
    """Security requirements and considerations."""
    
    authentication_required: bool = True
    authentication_methods: List[str] = field(default_factory=list)
    authorization_model: str = "rbac"
    encryption_at_rest: bool = True
    encryption_in_transit: bool = True
    compliance_standards: List[str] = field(default_factory=list)
    security_headers: Dict[str, str] = field(default_factory=dict)
    rate_limiting: bool = True
    input_validation: bool = True


@dataclass
class PerformanceRequirements:
    """Performance requirements and targets."""
    
    response_time_ms: int = 200
    throughput_rps: int = 1000
    concurrent_users: int = 100
    cache_strategy: str = "redis"
    database_optimization: bool = True
    cdn_enabled: bool = False
    load_balancing: bool = False
    auto_scaling: bool = False
    monitoring: List[str] = field(default_factory=list)


@dataclass
class ProjectSpec(SerializableModel, TimestampedModel, IdentifiedModel, VersionedModel):
    """Complete project specification."""
    
    metadata: ProjectMetadata
    description: str
    features: List[Feature] = field(default_factory=list)
    technologies: List[Technology] = field(default_factory=list)
    api_endpoints: List[APIEndpoint] = field(default_factory=list)
    build_requirements: BuildRequirements = field(default_factory=BuildRequirements)
    security_requirements: SecurityRequirements = field(default_factory=SecurityRequirements)
    performance_requirements: PerformanceRequirements = field(default_factory=PerformanceRequirements)
    
    # Additional specifications
    database_schema: Optional[Dict[str, Any]] = None
    ui_mockups: List[str] = field(default_factory=list)
    user_stories: List[str] = field(default_factory=list)
    test_scenarios: List[str] = field(default_factory=list)
    documentation_requirements: List[str] = field(default_factory=list)
    custom_instructions: List[str] = field(default_factory=list)
    
    # Computed properties
    _technology_index: Optional[Dict[str, Technology]] = field(default=None, init=False)
    _feature_index: Optional[Dict[str, Feature]] = field(default=None, init=False)
    
    def __post_init__(self):
        """Initialize computed properties."""
        super().__init__()
        self._build_indices()
    
    def _build_indices(self):
        """Build internal indices for fast lookup."""
        self._technology_index = {tech.name: tech for tech in self.technologies}
        self._feature_index = {feat.name: feat for feat in self.features}
    
    def validate(self) -> None:
        """Validate the complete project specification."""
        # Validate metadata
        self.metadata.validate()
        
        # Validate features
        for feature in self.features:
            feature.validate()
        
        # Validate technologies
        for tech in self.technologies:
            tech.validate()
        
        # Validate API endpoints
        for endpoint in self.api_endpoints:
            endpoint.validate()
        
        # Check feature dependencies
        feature_names = {f.name for f in self.features}
        for feature in self.features:
            for dep in feature.dependencies:
                if dep not in feature_names:
                    raise ValidationError(
                        f"Feature '{feature.name}' depends on unknown feature '{dep}'"
                    )
    
    def get_technology(self, name: str) -> Optional[Technology]:
        """Get technology by name."""
        if self._technology_index is None:
            self._build_indices()
        return self._technology_index.get(name)
    
    def get_feature(self, name: str) -> Optional[Feature]:
        """Get feature by name."""
        if self._feature_index is None:
            self._build_indices()
        return self._feature_index.get(name)
    
    def get_required_technologies(self) -> List[Technology]:
        """Get all required technologies."""
        return [tech for tech in self.technologies if tech.required]
    
    def get_features_by_priority(self, priority: str) -> List[Feature]:
        """Get features by priority level."""
        return [f for f in self.features if f.priority == priority]
    
    def get_total_complexity(self) -> int:
        """Calculate total project complexity."""
        return sum(f.complexity for f in self.features)
    
    def estimate_effort_days(self) -> float:
        """Estimate total effort in days based on complexity."""
        total_complexity = self.get_total_complexity()
        # Rough estimation: 1 complexity point = 0.5 days
        base_days = total_complexity * 0.5
        
        # Adjust for number of technologies
        tech_factor = 1 + (len(self.technologies) * 0.1)
        
        # Adjust for API endpoints
        api_factor = 1 + (len(self.api_endpoints) * 0.05)
        
        return base_days * tech_factor * api_factor
    
    def to_markdown(self) -> str:
        """Convert specification to markdown format."""
        lines = [
            f"# {self.metadata.name}",
            f"\n{self.metadata.description}",
            f"\nVersion: {self.metadata.version}",
            f"Author: {self.metadata.author}",
            f"License: {self.metadata.license}",
            "\n## Features\n"
        ]
        
        for feature in self.features:
            lines.append(f"### {feature.name}")
            lines.append(f"{feature.description}")
            lines.append(f"- Priority: {feature.priority}")
            lines.append(f"- Complexity: {feature.complexity}/10")
            
            if feature.acceptance_criteria:
                lines.append("\n**Acceptance Criteria:**")
                for criteria in feature.acceptance_criteria:
                    lines.append(f"- {criteria}")
            
            lines.append("")
        
        if self.technologies:
            lines.append("## Technologies\n")
            for tech in self.technologies:
                version = f" {tech.version}" if tech.version else ""
                required = " (required)" if tech.required else " (optional)"
                lines.append(f"- {tech.name}{version}{required}")
        
        if self.api_endpoints:
            lines.append("\n## API Endpoints\n")
            for endpoint in self.api_endpoints:
                lines.append(f"### {endpoint.method} {endpoint.path}")
                lines.append(f"{endpoint.description}")
        
        return "\n".join(lines)


@dataclass
class BuildConfig(SerializableModel):
    """Build configuration for project generation."""
    
    output_dir: Path
    project_spec: ProjectSpec
    
    # Build options
    generate_tests: bool = True
    generate_docs: bool = True
    generate_examples: bool = True
    generate_ci_cd: bool = True
    
    # Code style
    code_formatter: str = "black"
    linter: str = "ruff"
    type_checker: str = "mypy"
    
    # Testing
    test_framework: str = "pytest"
    coverage_threshold: float = 0.8
    
    # Documentation
    doc_format: str = "sphinx"
    doc_theme: str = "sphinx_rtd_theme"
    
    # Git
    initialize_git: bool = True
    create_gitignore: bool = True
    initial_commit: bool = True
    
    # Virtual environment
    create_venv: bool = True
    venv_name: str = "venv"
    install_dependencies: bool = True
    
    def validate(self) -> None:
        """Validate build configuration."""
        if not self.output_dir:
            raise ValidationError("Output directory is required")
        
        if not self.project_spec:
            raise ValidationError("Project specification is required")
        
        # Validate project spec
        self.project_spec.validate()
        
        # Validate code style options
        valid_formatters = ["black", "autopep8", "yapf"]
        if self.code_formatter not in valid_formatters:
            raise ValidationError(f"Invalid code formatter: {self.code_formatter}")
        
        valid_linters = ["ruff", "flake8", "pylint"]
        if self.linter not in valid_linters:
            raise ValidationError(f"Invalid linter: {self.linter}")
        
        valid_type_checkers = ["mypy", "pytype", "pyre"]
        if self.type_checker not in valid_type_checkers:
            raise ValidationError(f"Invalid type checker: {self.type_checker}")
        
        # Validate test framework
        valid_test_frameworks = ["pytest", "unittest", "nose2"]
        if self.test_framework not in valid_test_frameworks:
            raise ValidationError(f"Invalid test framework: {self.test_framework}")
        
        # Validate coverage threshold
        if not 0 <= self.coverage_threshold <= 1:
            raise ValidationError("Coverage threshold must be between 0 and 1")