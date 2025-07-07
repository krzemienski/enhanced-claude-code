"""Best Practices Advisor research agent."""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from .base_agent import BaseResearchAgent, AgentCapability, AgentContext, AgentResponse
from ..models.research import ResearchSource

logger = logging.getLogger(__name__)


class BestPracticesAdvisor(BaseResearchAgent):
    """Specializes in development best practices and code quality."""
    
    def __init__(self):
        """Initialize Best Practices Advisor agent."""
        super().__init__(
            name="Best Practices Advisor",
            capabilities=[
                AgentCapability.RECOMMENDATION,
                AgentCapability.ANALYSIS,
                AgentCapability.DOCUMENTATION,
                AgentCapability.VALIDATION
            ]
        )
        
        # Best practices knowledge base
        self.coding_standards = {
            "naming": {
                "variables": ["Use descriptive names", "camelCase for JS/TS", "snake_case for Python"],
                "functions": ["Verb-based names", "Single responsibility", "Clear intent"],
                "classes": ["PascalCase", "Noun-based", "Single responsibility"],
                "constants": ["UPPER_SNAKE_CASE", "Meaningful names"]
            },
            "structure": {
                "files": ["One class/component per file", "Logical grouping", "Clear naming"],
                "folders": ["Feature-based structure", "Clear hierarchy", "Consistent naming"],
                "modules": ["High cohesion", "Low coupling", "Clear interfaces"]
            },
            "documentation": {
                "code": ["Self-documenting code", "Inline comments for complex logic", "JSDoc/docstrings"],
                "api": ["OpenAPI/Swagger", "Clear examples", "Version documentation"],
                "project": ["README.md", "CONTRIBUTING.md", "Architecture docs"]
            }
        }
        
        self.solid_principles = {
            "S": {
                "name": "Single Responsibility",
                "description": "A class should have one reason to change",
                "violations": ["God classes", "Mixed concerns", "Bloated methods"]
            },
            "O": {
                "name": "Open/Closed",
                "description": "Open for extension, closed for modification",
                "practices": ["Use interfaces", "Strategy pattern", "Plugin architecture"]
            },
            "L": {
                "name": "Liskov Substitution",
                "description": "Subtypes must be substitutable for base types",
                "checks": ["Consistent behavior", "No strengthened preconditions"]
            },
            "I": {
                "name": "Interface Segregation",
                "description": "No client should depend on unused methods",
                "practices": ["Small interfaces", "Role-based interfaces"]
            },
            "D": {
                "name": "Dependency Inversion",
                "description": "Depend on abstractions, not concretions",
                "implementation": ["Dependency injection", "IoC containers"]
            }
        }
        
        self.clean_code_principles = {
            "readability": [
                "Code should read like well-written prose",
                "Meaningful variable and function names",
                "Consistent formatting and style",
                "Avoid deep nesting"
            ],
            "simplicity": [
                "KISS - Keep It Simple, Stupid",
                "YAGNI - You Aren't Gonna Need It",
                "Avoid premature optimization",
                "Favor composition over inheritance"
            ],
            "maintainability": [
                "Write tests first (TDD)",
                "Refactor regularly",
                "Keep functions small",
                "Minimize dependencies"
            ]
        }
        
        self.project_practices = {
            "version_control": {
                "commits": ["Atomic commits", "Meaningful messages", "Conventional commits"],
                "branching": ["GitFlow or GitHub Flow", "Feature branches", "Protected main"],
                "review": ["Pull request reviews", "Code review checklist", "Automated checks"]
            },
            "testing": {
                "unit": ["High coverage", "Fast execution", "Isolated tests"],
                "integration": ["Test interactions", "Real dependencies", "Error scenarios"],
                "e2e": ["User workflows", "Critical paths", "Cross-browser"],
                "performance": ["Load testing", "Stress testing", "Benchmarks"]
            },
            "ci_cd": {
                "ci": ["Automated builds", "Test execution", "Code quality checks"],
                "cd": ["Automated deployment", "Environment promotion", "Rollback capability"],
                "monitoring": ["Health checks", "Error tracking", "Performance monitoring"]
            }
        }
    
    async def _initialize(self) -> None:
        """Initialize the Best Practices Advisor."""
        logger.info("Best Practices Advisor initialized with comprehensive best practices")
    
    async def _perform_research(self, context: AgentContext) -> AgentResponse:
        """Perform best practices analysis."""
        findings = []
        recommendations = []
        
        # Analyze coding standards
        coding_analysis = await self._analyze_coding_standards(context)
        findings.extend(coding_analysis["findings"])
        recommendations.extend(coding_analysis["recommendations"])
        
        # Check SOLID principles
        solid_analysis = await self._analyze_solid_principles(context)
        findings.extend(solid_analysis["findings"])
        recommendations.extend(solid_analysis["recommendations"])
        
        # Project structure best practices
        structure_analysis = await self._analyze_project_structure(context)
        findings.extend(structure_analysis["findings"])
        recommendations.extend(structure_analysis["recommendations"])
        
        # Development workflow practices
        workflow_analysis = await self._analyze_development_workflow(context)
        findings.extend(workflow_analysis["findings"])
        recommendations.extend(workflow_analysis["recommendations"])
        
        # Testing best practices
        testing_analysis = await self._analyze_testing_practices(context)
        findings.extend(testing_analysis["findings"])
        recommendations.extend(testing_analysis["recommendations"])
        
        # Documentation standards
        doc_analysis = await self._analyze_documentation_needs(context)
        findings.extend(doc_analysis["findings"])
        recommendations.extend(doc_analysis["recommendations"])
        
        # Calculate confidence
        confidence = self._calculate_confidence(context, findings)
        
        return AgentResponse(
            agent_name=self.name,
            findings=findings,
            recommendations=self.prioritize_recommendations(recommendations, context),
            confidence=confidence,
            sources_used=[ResearchSource.DOCUMENTATION, ResearchSource.COMMUNITY],
            metadata={
                "principles_checked": ["SOLID", "Clean Code", "DRY", "KISS"],
                "practice_areas": len(self.project_practices)
            }
        )
    
    async def _analyze_coding_standards(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze and recommend coding standards."""
        findings = []
        recommendations = []
        
        # Language-specific standards
        languages = self._detect_languages(context)
        
        for language in languages:
            standards = self._get_language_standards(language)
            
            findings.append({
                "title": f"{language} Coding Standards",
                "description": f"Recommended coding standards for {language}",
                "relevance": 0.9,
                "standards": standards
            })
            
            # Style guide recommendations
            style_guide = self._get_style_guide(language)
            if style_guide:
                recommendations.append(f"Follow {style_guide} style guide for {language}")
            
            # Linting recommendations
            linters = self._get_linters(language)
            if linters:
                recommendations.append(f"Use {', '.join(linters)} for {language} code quality")
        
        # General coding standards
        findings.append({
            "title": "Universal Coding Principles",
            "description": "Language-agnostic best practices",
            "relevance": 1.0,
            "principles": [
                "DRY - Don't Repeat Yourself",
                "KISS - Keep It Simple, Stupid",
                "YAGNI - You Aren't Gonna Need It",
                "Boy Scout Rule - Leave code better than you found it"
            ]
        })
        
        recommendations.extend([
            "Establish team coding standards document",
            "Use automated formatting (Prettier, Black, etc.)",
            "Implement pre-commit hooks for consistency",
            "Regular code reviews for standard compliance"
        ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_solid_principles(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze SOLID principles application."""
        findings = []
        recommendations = []
        
        # Check project complexity
        complexity = len(context.project_spec.features)
        
        if complexity > 5:  # Non-trivial project
            findings.append({
                "title": "SOLID Principles Application",
                "description": "Project complexity warrants SOLID principles",
                "relevance": 0.9,
                "applicable_principles": list(self.solid_principles.keys())
            })
            
            # Principle-specific recommendations
            for principle, info in self.solid_principles.items():
                recommendations.append(
                    f"{principle} - {info['name']}: {info['description']}"
                )
            
            # Design pattern recommendations
            patterns = self._recommend_design_patterns(context)
            if patterns:
                findings.append({
                    "title": "Recommended Design Patterns",
                    "description": "Patterns that support SOLID principles",
                    "relevance": 0.8,
                    "patterns": patterns
                })
                
                for pattern in patterns:
                    recommendations.append(f"Consider {pattern['name']} pattern for {pattern['use_case']}")
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_project_structure(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze project structure best practices."""
        findings = []
        recommendations = []
        
        project_type = context.project_spec.type
        
        # Recommend structure based on project type
        structure_templates = {
            "web_application": {
                "frontend": ["components/", "pages/", "services/", "utils/", "assets/"],
                "backend": ["controllers/", "models/", "services/", "middleware/", "routes/"]
            },
            "api_service": {
                "structure": ["api/", "models/", "services/", "middleware/", "utils/", "tests/"]
            },
            "cli_tool": {
                "structure": ["commands/", "core/", "utils/", "config/", "tests/"]
            }
        }
        
        if project_type in structure_templates:
            structure = structure_templates[project_type]
            
            findings.append({
                "title": "Recommended Project Structure",
                "description": f"Best practice folder structure for {project_type}",
                "relevance": 0.9,
                "structure": structure
            })
            
            recommendations.extend([
                "Use feature-based folder structure for scalability",
                "Keep related files close together",
                "Separate concerns clearly (business logic, data access, presentation)",
                "Use index files for clean imports"
            ])
        
        # Configuration management
        findings.append({
            "title": "Configuration Management",
            "description": "Best practices for configuration",
            "relevance": 0.8,
            "practices": [
                "Environment-based configuration",
                "Secret management",
                "Configuration validation",
                "Default values"
            ]
        })
        
        recommendations.extend([
            "Use environment variables for configuration",
            "Never commit secrets to version control",
            "Validate configuration at startup",
            "Document all configuration options"
        ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_development_workflow(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze development workflow best practices."""
        findings = []
        recommendations = []
        
        # Version control practices
        findings.append({
            "title": "Version Control Best Practices",
            "description": "Git workflow recommendations",
            "relevance": 1.0,
            "practices": self.project_practices["version_control"]
        })
        
        recommendations.extend([
            "Use conventional commits for clear history",
            "Implement branch protection rules",
            "Require pull request reviews",
            "Use semantic versioning for releases"
        ])
        
        # CI/CD practices
        findings.append({
            "title": "CI/CD Pipeline",
            "description": "Continuous integration and deployment practices",
            "relevance": 0.9,
            "stages": [
                "Build verification",
                "Test execution",
                "Code quality checks",
                "Security scanning",
                "Deployment"
            ]
        })
        
        recommendations.extend([
            "Automate builds on every commit",
            "Run tests in CI pipeline",
            "Implement automated deployments",
            "Use feature flags for safe releases",
            "Monitor deployment health"
        ])
        
        # Code review practices
        findings.append({
            "title": "Code Review Process",
            "description": "Peer review best practices",
            "relevance": 0.9,
            "checklist": [
                "Functionality correctness",
                "Code style compliance",
                "Test coverage",
                "Performance implications",
                "Security considerations"
            ]
        })
        
        recommendations.extend([
            "Establish code review checklist",
            "Keep pull requests small and focused",
            "Respond to reviews promptly",
            "Use automated checks before human review"
        ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_testing_practices(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze testing best practices."""
        findings = []
        recommendations = []
        
        # Testing pyramid
        findings.append({
            "title": "Testing Strategy",
            "description": "Recommended testing pyramid",
            "relevance": 1.0,
            "levels": {
                "unit": "70% - Fast, isolated component tests",
                "integration": "20% - Component interaction tests",
                "e2e": "10% - Critical user path tests"
            }
        })
        
        # Test practices by project type
        if context.project_spec.type == "web_application":
            recommendations.extend([
                "Implement unit tests for all business logic",
                "Use React Testing Library or similar for component tests",
                "Add E2E tests for critical user journeys",
                "Test accessibility with automated tools"
            ])
        elif context.project_spec.type == "api_service":
            recommendations.extend([
                "Test all API endpoints",
                "Include negative test cases",
                "Test rate limiting and authentication",
                "Add contract testing for API consumers"
            ])
        
        # General testing best practices
        recommendations.extend([
            "Aim for 80%+ code coverage",
            "Write tests before fixing bugs (regression tests)",
            "Keep tests fast and independent",
            "Use test data builders for maintainability",
            "Mock external dependencies in unit tests"
        ])
        
        # Test-Driven Development
        findings.append({
            "title": "Test-Driven Development (TDD)",
            "description": "Benefits of TDD approach",
            "relevance": 0.8,
            "benefits": [
                "Better design through testability",
                "Confidence in refactoring",
                "Living documentation",
                "Fewer bugs in production"
            ]
        })
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_documentation_needs(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze documentation best practices."""
        findings = []
        recommendations = []
        
        # Essential documentation
        findings.append({
            "title": "Essential Documentation",
            "description": "Must-have documentation for the project",
            "relevance": 1.0,
            "documents": [
                "README.md - Project overview and setup",
                "API documentation (if applicable)",
                "Architecture documentation",
                "Contributing guidelines",
                "Deployment guide"
            ]
        })
        
        recommendations.extend([
            "Create comprehensive README with setup instructions",
            "Document API endpoints with examples",
            "Maintain architecture decision records (ADRs)",
            "Keep documentation close to code",
            "Use diagrams for complex concepts"
        ])
        
        # Code documentation
        language_docs = {
            "javascript": "Use JSDoc for function documentation",
            "typescript": "Use TSDoc for type documentation",
            "python": "Use docstrings (Google or NumPy style)",
            "java": "Use Javadoc for public APIs"
        }
        
        languages = self._detect_languages(context)
        for lang in languages:
            if lang.lower() in language_docs:
                recommendations.append(language_docs[lang.lower()])
        
        # API documentation
        if context.project_spec.type in ["api_service", "web_application"]:
            findings.append({
                "title": "API Documentation",
                "description": "API documentation best practices",
                "relevance": 0.9,
                "tools": ["OpenAPI/Swagger", "Postman collections", "API Blueprint"]
            })
            
            recommendations.extend([
                "Generate API docs from code annotations",
                "Include request/response examples",
                "Document error responses",
                "Version API documentation"
            ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    def _detect_languages(self, context: AgentContext) -> List[str]:
        """Detect programming languages from context."""
        languages = set()
        
        # From technologies
        for tech in context.project_spec.technologies:
            tech_lower = tech.name.lower()
            if "javascript" in tech_lower or "node" in tech_lower:
                languages.add("JavaScript")
            elif "typescript" in tech_lower:
                languages.add("TypeScript")
            elif "python" in tech_lower:
                languages.add("Python")
            elif "java" in tech_lower and "javascript" not in tech_lower:
                languages.add("Java")
            elif "rust" in tech_lower:
                languages.add("Rust")
            elif "go" in tech_lower:
                languages.add("Go")
        
        return list(languages)
    
    def _get_language_standards(self, language: str) -> Dict[str, List[str]]:
        """Get language-specific coding standards."""
        standards = {
            "JavaScript": {
                "naming": ["camelCase for variables/functions", "PascalCase for classes"],
                "style": ["Use const/let, avoid var", "Prefer arrow functions", "Use template literals"],
                "async": ["Use async/await over callbacks", "Handle promise rejections"]
            },
            "Python": {
                "naming": ["snake_case for variables/functions", "PascalCase for classes"],
                "style": ["Follow PEP 8", "Use type hints", "Prefer list comprehensions"],
                "structure": ["One class per file", "Clear module organization"]
            },
            "TypeScript": {
                "naming": ["Same as JavaScript", "Interface names without 'I' prefix"],
                "types": ["Avoid 'any' type", "Use strict mode", "Define return types"],
                "style": ["Use interfaces over type aliases for objects"]
            }
        }
        
        return standards.get(language, {})
    
    def _get_style_guide(self, language: str) -> Optional[str]:
        """Get recommended style guide for language."""
        guides = {
            "JavaScript": "Airbnb JavaScript Style Guide",
            "TypeScript": "TypeScript Style Guide",
            "Python": "PEP 8",
            "Java": "Google Java Style Guide",
            "Go": "Effective Go",
            "Rust": "Rust Style Guide"
        }
        
        return guides.get(language)
    
    def _get_linters(self, language: str) -> List[str]:
        """Get recommended linters for language."""
        linters = {
            "JavaScript": ["ESLint", "Prettier"],
            "TypeScript": ["ESLint", "Prettier", "tsc"],
            "Python": ["pylint", "flake8", "black", "mypy"],
            "Java": ["Checkstyle", "SpotBugs", "PMD"],
            "Go": ["golint", "go vet"],
            "Rust": ["clippy", "rustfmt"]
        }
        
        return linters.get(language, [])
    
    def _recommend_design_patterns(self, context: AgentContext) -> List[Dict[str, str]]:
        """Recommend design patterns based on context."""
        patterns = []
        
        # Check for common scenarios
        project_features = " ".join(f.name.lower() for f in context.project_spec.features)
        
        if "api" in project_features:
            patterns.append({
                "name": "Repository Pattern",
                "use_case": "Data access abstraction"
            })
        
        if "notification" in project_features or "event" in project_features:
            patterns.append({
                "name": "Observer Pattern",
                "use_case": "Event handling and notifications"
            })
        
        if "payment" in project_features or "strategy" in context.project_spec.description.lower():
            patterns.append({
                "name": "Strategy Pattern",
                "use_case": "Multiple algorithm implementations"
            })
        
        if context.project_spec.type == "api_service":
            patterns.append({
                "name": "Factory Pattern",
                "use_case": "Object creation abstraction"
            })
        
        return patterns
    
    def _calculate_confidence(self, context: AgentContext, findings: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for best practices analysis."""
        # High confidence in best practices as they're well-established
        base_confidence = 0.85
        
        # Adjust based on project type familiarity
        if context.project_spec.type in ["web_application", "api_service"]:
            base_confidence += 0.05
        
        # Adjust based on language detection
        languages = self._detect_languages(context)
        if languages:
            base_confidence += 0.05
        
        return min(base_confidence, 0.95)
    
    def get_expertise_areas(self) -> List[str]:
        """Get Best Practices Advisor's areas of expertise."""
        return [
            "Coding Standards",
            "SOLID Principles",
            "Clean Code",
            "Design Patterns",
            "Testing Practices",
            "Documentation Standards",
            "Code Review",
            "CI/CD Practices",
            "Version Control",
            "Project Structure"
        ]
    
    def get_research_methods(self) -> List[str]:
        """Get research methods used by Best Practices Advisor."""
        return [
            "Standards Analysis",
            "Pattern Recognition",
            "Best Practices Review",
            "Code Quality Assessment",
            "Workflow Analysis",
            "Documentation Review",
            "Testing Strategy",
            "Industry Standards"
        ]