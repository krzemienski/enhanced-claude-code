"""Quality Assurance Expert research agent."""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from .base_agent import BaseResearchAgent, AgentCapability, AgentContext, AgentResponse
from ..models.research import ResearchSource

logger = logging.getLogger(__name__)


class QualityAssuranceExpert(BaseResearchAgent):
    """Specializes in testing strategies and quality assurance."""
    
    def __init__(self):
        """Initialize Quality Assurance Expert agent."""
        super().__init__(
            name="Quality Assurance Expert",
            capabilities=[
                AgentCapability.TESTING,
                AgentCapability.VALIDATION,
                AgentCapability.ANALYSIS,
                AgentCapability.RECOMMENDATION
            ]
        )
        
        # Testing knowledge base
        self.testing_types = {
            "unit": {
                "description": "Test individual components in isolation",
                "coverage_target": 80,
                "tools": {
                    "javascript": ["Jest", "Vitest", "Mocha"],
                    "python": ["pytest", "unittest", "nose2"],
                    "java": ["JUnit", "TestNG"],
                    "go": ["testing", "testify"],
                    "rust": ["built-in test", "mockall"]
                }
            },
            "integration": {
                "description": "Test component interactions",
                "coverage_target": 60,
                "focus": ["API endpoints", "Database operations", "Service communication"]
            },
            "e2e": {
                "description": "Test complete user workflows",
                "coverage_target": 40,
                "tools": ["Cypress", "Playwright", "Selenium", "Puppeteer"]
            },
            "performance": {
                "description": "Test system performance under load",
                "tools": ["JMeter", "K6", "Locust", "Artillery"],
                "metrics": ["Response time", "Throughput", "Error rate", "Concurrency"]
            },
            "security": {
                "description": "Test for vulnerabilities",
                "tools": ["OWASP ZAP", "Burp Suite", "SQLMap"],
                "focus": ["Injection", "Authentication", "Authorization", "XSS"]
            }
        }
        
        self.quality_metrics = {
            "code_coverage": {
                "excellent": 90,
                "good": 80,
                "acceptable": 70,
                "poor": 60
            },
            "defect_density": {
                "excellent": 0.1,  # defects per KLOC
                "good": 0.5,
                "acceptable": 1.0,
                "poor": 2.0
            },
            "test_execution_time": {
                "unit": 5,  # minutes
                "integration": 15,
                "e2e": 30
            }
        }
        
        self.testing_patterns = {
            "arrange_act_assert": {
                "description": "Structure tests with setup, execution, and verification",
                "applicable_to": ["unit", "integration"]
            },
            "page_object": {
                "description": "Encapsulate page interactions in objects",
                "applicable_to": ["e2e", "ui"]
            },
            "test_data_builder": {
                "description": "Create flexible test data factories",
                "applicable_to": ["all"]
            },
            "mock_stub_spy": {
                "description": "Isolate components with test doubles",
                "applicable_to": ["unit", "integration"]
            }
        }
    
    async def _initialize(self) -> None:
        """Initialize the Quality Assurance Expert."""
        logger.info("Quality Assurance Expert initialized with comprehensive testing knowledge")
    
    async def _perform_research(self, context: AgentContext) -> AgentResponse:
        """Perform quality assurance analysis."""
        findings = []
        recommendations = []
        
        # Analyze testing requirements
        test_requirements = await self._analyze_testing_requirements(context)
        findings.extend(test_requirements["findings"])
        recommendations.extend(test_requirements["recommendations"])
        
        # Design test strategy
        test_strategy = await self._design_test_strategy(context)
        findings.extend(test_strategy["findings"])
        recommendations.extend(test_strategy["recommendations"])
        
        # Recommend testing tools
        tool_recommendations = await self._recommend_testing_tools(context)
        findings.extend(tool_recommendations["findings"])
        recommendations.extend(tool_recommendations["recommendations"])
        
        # Quality metrics and KPIs
        quality_metrics = await self._define_quality_metrics(context)
        findings.extend(quality_metrics["findings"])
        recommendations.extend(quality_metrics["recommendations"])
        
        # CI/CD integration
        cicd_integration = await self._plan_cicd_integration(context)
        findings.extend(cicd_integration["findings"])
        recommendations.extend(cicd_integration["recommendations"])
        
        # Calculate confidence
        confidence = self._calculate_confidence(context, findings)
        
        return AgentResponse(
            agent_name=self.name,
            findings=findings,
            recommendations=self.prioritize_recommendations(recommendations, context),
            confidence=confidence,
            sources_used=[ResearchSource.DOCUMENTATION, ResearchSource.COMMUNITY],
            metadata={
                "test_types_recommended": len(test_strategy.get("test_types", [])),
                "tools_recommended": len(tool_recommendations.get("tools", []))
            }
        )
    
    async def _analyze_testing_requirements(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze testing requirements based on project characteristics."""
        findings = []
        recommendations = []
        
        # Determine testing complexity
        complexity = self._assess_testing_complexity(context)
        
        findings.append({
            "title": "Testing Complexity Assessment",
            "description": f"Project testing complexity: {complexity['level']}",
            "relevance": 1.0,
            "factors": complexity["factors"]
        })
        
        # Critical features requiring thorough testing
        critical_features = self._identify_critical_features(context)
        if critical_features:
            findings.append({
                "title": "Critical Testing Areas",
                "description": "Features requiring comprehensive test coverage",
                "relevance": 0.9,
                "features": critical_features
            })
            
            for feature in critical_features:
                recommendations.append(
                    f"Implement comprehensive testing for {feature['name']} ({feature['reason']})"
                )
        
        # Compliance requirements
        compliance = self._check_compliance_requirements(context)
        if compliance:
            findings.append({
                "title": "Compliance Testing Requirements",
                "description": "Regulatory compliance needs",
                "relevance": 0.9,
                "requirements": compliance
            })
            
            recommendations.extend([
                f"Implement {req} compliance testing" for req in compliance
            ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _design_test_strategy(self, context: AgentContext) -> Dict[str, Any]:
        """Design comprehensive test strategy."""
        findings = []
        recommendations = []
        test_types = []
        
        project_type = context.project_spec.type
        
        # Base testing pyramid
        findings.append({
            "title": "Testing Strategy Design",
            "description": "Recommended testing pyramid approach",
            "relevance": 1.0,
            "pyramid": {
                "unit": "70% - Fast, isolated tests",
                "integration": "20% - Component interaction tests",
                "e2e": "10% - Critical path tests"
            }
        })
        
        # Unit testing strategy
        test_types.append("unit")
        recommendations.extend([
            "Write unit tests for all business logic",
            "Aim for 80%+ code coverage",
            "Use test-driven development (TDD) for critical components",
            "Mock external dependencies"
        ])
        
        # Integration testing
        if self._needs_integration_testing(context):
            test_types.append("integration")
            findings.append({
                "title": "Integration Testing Required",
                "description": "Multiple components require integration testing",
                "relevance": 0.9,
                "focus_areas": self._get_integration_focus_areas(context)
            })
            
            recommendations.extend([
                "Test API endpoint integrations",
                "Verify database transactions",
                "Test service-to-service communication",
                "Use test containers for dependencies"
            ])
        
        # E2E testing
        if project_type in ["web_application", "mobile_app"]:
            test_types.append("e2e")
            findings.append({
                "title": "End-to-End Testing Strategy",
                "description": "UI and workflow testing required",
                "relevance": 0.8,
                "scenarios": self._get_e2e_scenarios(context)
            })
            
            recommendations.extend([
                "Test critical user journeys",
                "Implement visual regression testing",
                "Test cross-browser compatibility",
                "Use Page Object Model pattern"
            ])
        
        # Performance testing
        if self._needs_performance_testing(context):
            test_types.append("performance")
            findings.append({
                "title": "Performance Testing Required",
                "description": "System requires load and stress testing",
                "relevance": 0.8,
                "targets": self._get_performance_targets(context)
            })
            
            recommendations.extend([
                "Define performance SLAs",
                "Implement load testing scenarios",
                "Test scalability limits",
                "Monitor resource utilization"
            ])
        
        # Security testing
        if self._needs_security_testing(context):
            test_types.append("security")
            recommendations.extend([
                "Perform vulnerability scanning",
                "Test authentication and authorization",
                "Implement penetration testing",
                "Test for OWASP Top 10 vulnerabilities"
            ])
        
        return {
            "findings": findings,
            "recommendations": recommendations,
            "test_types": test_types
        }
    
    async def _recommend_testing_tools(self, context: AgentContext) -> Dict[str, Any]:
        """Recommend appropriate testing tools."""
        findings = []
        recommendations = []
        tools = []
        
        # Detect primary language
        primary_language = self._detect_primary_language(context)
        
        # Unit testing tools
        if primary_language:
            unit_tools = self.testing_types["unit"]["tools"].get(primary_language, [])
            if unit_tools:
                findings.append({
                    "title": f"Unit Testing Tools for {primary_language.title()}",
                    "description": "Recommended unit testing frameworks",
                    "relevance": 0.9,
                    "tools": unit_tools
                })
                
                recommendations.append(f"Use {unit_tools[0]} for unit testing")
                tools.extend(unit_tools[:1])
        
        # E2E testing tools
        if context.project_spec.type == "web_application":
            e2e_tools = self.testing_types["e2e"]["tools"]
            findings.append({
                "title": "E2E Testing Tools",
                "description": "Modern E2E testing frameworks",
                "relevance": 0.8,
                "tools": e2e_tools,
                "recommendation": "Playwright or Cypress recommended for modern web apps"
            })
            
            recommendations.append("Use Playwright or Cypress for E2E testing")
            tools.append("Playwright")
        
        # API testing tools
        if context.project_spec.type == "api_service":
            api_tools = ["Postman", "Newman", "REST Assured", "Supertest"]
            findings.append({
                "title": "API Testing Tools",
                "description": "Tools for API testing and documentation",
                "relevance": 0.9,
                "tools": api_tools
            })
            
            recommendations.append("Use Postman/Newman for API testing")
            tools.append("Postman")
        
        # Performance testing tools
        if self._needs_performance_testing(context):
            perf_tools = self.testing_types["performance"]["tools"]
            recommendations.append(f"Use {perf_tools[0]} or {perf_tools[1]} for load testing")
            tools.append(perf_tools[0])
        
        # Test management
        findings.append({
            "title": "Test Management",
            "description": "Test case management and reporting",
            "relevance": 0.7,
            "options": ["TestRail", "Zephyr", "qTest", "GitHub Issues"]
        })
        
        return {
            "findings": findings,
            "recommendations": recommendations,
            "tools": tools
        }
    
    async def _define_quality_metrics(self, context: AgentContext) -> Dict[str, Any]:
        """Define quality metrics and KPIs."""
        findings = []
        recommendations = []
        
        # Code coverage targets
        coverage_targets = self._determine_coverage_targets(context)
        findings.append({
            "title": "Code Coverage Targets",
            "description": "Recommended coverage goals by test type",
            "relevance": 0.9,
            "targets": coverage_targets
        })
        
        recommendations.extend([
            f"Achieve {coverage_targets['unit']}% unit test coverage",
            f"Maintain {coverage_targets['integration']}% integration test coverage",
            "Set up coverage reporting in CI/CD"
        ])
        
        # Quality gates
        findings.append({
            "title": "Quality Gates",
            "description": "Automated quality checkpoints",
            "relevance": 0.8,
            "gates": [
                "All tests passing",
                "Code coverage meets targets",
                "No critical security vulnerabilities",
                "Performance benchmarks met",
                "Code quality score > 8/10"
            ]
        })
        
        recommendations.extend([
            "Implement quality gates in CI/CD pipeline",
            "Block deployments if quality gates fail",
            "Monitor quality metrics over time",
            "Set up automated quality reports"
        ])
        
        # Defect metrics
        findings.append({
            "title": "Defect Management Metrics",
            "description": "Track and reduce defect rates",
            "relevance": 0.7,
            "metrics": [
                "Defect density per release",
                "Mean time to detection (MTTD)",
                "Mean time to resolution (MTTR)",
                "Defect escape rate",
                "Test effectiveness"
            ]
        })
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _plan_cicd_integration(self, context: AgentContext) -> Dict[str, Any]:
        """Plan CI/CD integration for testing."""
        findings = []
        recommendations = []
        
        # CI/CD pipeline stages
        findings.append({
            "title": "CI/CD Testing Pipeline",
            "description": "Automated testing in deployment pipeline",
            "relevance": 0.9,
            "stages": [
                "1. Pre-commit: Linting and formatting",
                "2. Commit: Unit tests (< 5 min)",
                "3. PR/MR: Integration tests (< 15 min)",
                "4. Pre-deploy: E2E tests (< 30 min)",
                "5. Post-deploy: Smoke tests (< 5 min)"
            ]
        })
        
        recommendations.extend([
            "Run fast tests on every commit",
            "Run full test suite on pull requests",
            "Parallelize test execution for speed",
            "Use test result caching",
            "Implement flaky test detection"
        ])
        
        # Test environments
        findings.append({
            "title": "Test Environment Strategy",
            "description": "Isolated environments for testing",
            "relevance": 0.8,
            "environments": [
                "Local: Developer testing",
                "CI: Automated testing",
                "Staging: Pre-production testing",
                "Production: Smoke and monitoring"
            ]
        })
        
        recommendations.extend([
            "Use containerization for consistent test environments",
            "Implement test data management strategy",
            "Automate environment provisioning",
            "Use feature flags for safe testing"
        ])
        
        # Continuous testing
        findings.append({
            "title": "Continuous Testing Practices",
            "description": "Shift-left testing approach",
            "relevance": 0.8,
            "practices": [
                "Test-driven development",
                "Automated regression testing",
                "Continuous performance testing",
                "Security testing in pipeline",
                "Automated accessibility testing"
            ]
        })
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    def _assess_testing_complexity(self, context: AgentContext) -> Dict[str, Any]:
        """Assess overall testing complexity."""
        factors = []
        score = 0
        
        # Feature complexity
        feature_count = len(context.project_spec.features)
        if feature_count > 20:
            factors.append("High feature count")
            score += 3
        elif feature_count > 10:
            factors.append("Moderate feature count")
            score += 2
        else:
            factors.append("Low feature count")
            score += 1
        
        # Integration complexity
        tech_count = len(context.project_spec.technologies)
        if tech_count > 5:
            factors.append("Multiple technology integrations")
            score += 2
        
        # User interface
        if context.project_spec.type in ["web_application", "mobile_app"]:
            factors.append("UI testing required")
            score += 2
        
        # External dependencies
        if any(kw in str(context.project_spec).lower() for kw in ["api", "integration", "third-party"]):
            factors.append("External dependencies")
            score += 2
        
        # Determine level
        if score >= 8:
            level = "high"
        elif score >= 5:
            level = "medium"
        else:
            level = "low"
        
        return {
            "level": level,
            "score": score,
            "factors": factors
        }
    
    def _identify_critical_features(self, context: AgentContext) -> List[Dict[str, str]]:
        """Identify features requiring extensive testing."""
        critical = []
        
        critical_keywords = {
            "payment": "Financial transactions",
            "auth": "Security critical",
            "user": "User data handling",
            "api": "External integration",
            "real-time": "Performance critical",
            "upload": "Security and validation",
            "export": "Data integrity"
        }
        
        for feature in context.project_spec.features:
            feature_lower = feature.name.lower()
            for keyword, reason in critical_keywords.items():
                if keyword in feature_lower:
                    critical.append({
                        "name": feature.name,
                        "reason": reason
                    })
                    break
        
        return critical
    
    def _check_compliance_requirements(self, context: AgentContext) -> List[str]:
        """Check for compliance testing requirements."""
        compliance = []
        
        compliance_indicators = {
            "healthcare": ["HIPAA"],
            "medical": ["HIPAA", "FDA"],
            "financial": ["PCI-DSS", "SOX"],
            "payment": ["PCI-DSS"],
            "european": ["GDPR"],
            "privacy": ["GDPR", "CCPA"]
        }
        
        project_text = (
            context.project_spec.description.lower() +
            " ".join(f.name.lower() for f in context.project_spec.features)
        )
        
        for indicator, requirements in compliance_indicators.items():
            if indicator in project_text:
                compliance.extend(requirements)
        
        return list(set(compliance))
    
    def _needs_integration_testing(self, context: AgentContext) -> bool:
        """Determine if integration testing is needed."""
        indicators = [
            len(context.project_spec.technologies) > 2,
            any("database" in t.name.lower() for t in context.project_spec.technologies),
            any("api" in f.name.lower() for f in context.project_spec.features),
            context.project_spec.type in ["api_service", "web_application"]
        ]
        
        return any(indicators)
    
    def _get_integration_focus_areas(self, context: AgentContext) -> List[str]:
        """Get areas requiring integration testing."""
        areas = []
        
        if any("database" in t.name.lower() for t in context.project_spec.technologies):
            areas.append("Database operations")
        
        if any("api" in f.name.lower() for f in context.project_spec.features):
            areas.append("API endpoints")
        
        if any("auth" in f.name.lower() for f in context.project_spec.features):
            areas.append("Authentication flow")
        
        if len(context.project_spec.technologies) > 3:
            areas.append("Service communication")
        
        return areas
    
    def _get_e2e_scenarios(self, context: AgentContext) -> List[str]:
        """Get critical E2E test scenarios."""
        scenarios = []
        
        # Common user journeys
        if any("auth" in f.name.lower() for f in context.project_spec.features):
            scenarios.append("User registration and login")
        
        if any("payment" in f.name.lower() for f in context.project_spec.features):
            scenarios.append("Complete purchase flow")
        
        if any("search" in f.name.lower() for f in context.project_spec.features):
            scenarios.append("Search and filter functionality")
        
        if context.project_spec.type == "web_application":
            scenarios.append("Navigation and routing")
        
        return scenarios
    
    def _needs_performance_testing(self, context: AgentContext) -> bool:
        """Determine if performance testing is needed."""
        perf_indicators = [
            "real-time", "streaming", "high-volume",
            "concurrent", "scalable", "performance"
        ]
        
        project_text = (
            context.project_spec.description.lower() +
            " ".join(f.name.lower() for f in context.project_spec.features)
        )
        
        return any(indicator in project_text for indicator in perf_indicators)
    
    def _get_performance_targets(self, context: AgentContext) -> Dict[str, str]:
        """Get performance testing targets."""
        targets = {
            "response_time": "< 200ms for API calls",
            "throughput": "1000 requests/second",
            "concurrent_users": "100 simultaneous users",
            "error_rate": "< 0.1%"
        }
        
        # Adjust based on project type
        if context.project_spec.type == "web_application":
            targets["page_load"] = "< 3 seconds"
            targets["time_to_interactive"] = "< 5 seconds"
        
        return targets
    
    def _needs_security_testing(self, context: AgentContext) -> bool:
        """Determine if security testing is needed."""
        security_indicators = [
            "auth", "user", "payment", "upload",
            "api", "token", "password", "secure"
        ]
        
        project_text = (
            context.project_spec.description.lower() +
            " ".join(f.name.lower() for f in context.project_spec.features)
        )
        
        return any(indicator in project_text for indicator in security_indicators)
    
    def _detect_primary_language(self, context: AgentContext) -> Optional[str]:
        """Detect primary programming language."""
        language_map = {
            "javascript": ["node", "react", "vue", "angular", "express"],
            "python": ["django", "flask", "fastapi", "python"],
            "java": ["spring", "java", "kotlin"],
            "go": ["go", "golang", "gin", "echo"],
            "rust": ["rust", "actix", "rocket"]
        }
        
        tech_names = [t.name.lower() for t in context.project_spec.technologies]
        
        for language, indicators in language_map.items():
            if any(ind in tech for tech in tech_names for ind in indicators):
                return language
        
        return None
    
    def _determine_coverage_targets(self, context: AgentContext) -> Dict[str, int]:
        """Determine appropriate coverage targets."""
        base_targets = {
            "unit": 80,
            "integration": 60,
            "e2e": 40
        }
        
        # Adjust for critical applications
        if any(kw in str(context.project_spec).lower() for kw in ["payment", "healthcare", "financial"]):
            base_targets["unit"] = 90
            base_targets["integration"] = 70
        
        # Adjust for project complexity
        if len(context.project_spec.features) > 20:
            base_targets["unit"] = max(base_targets["unit"] - 5, 70)
        
        return base_targets
    
    def _calculate_confidence(self, context: AgentContext, findings: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for QA analysis."""
        base_confidence = 0.85
        
        # High confidence in QA best practices
        if context.project_spec.type in ["web_application", "api_service"]:
            base_confidence += 0.05
        
        # Adjust based on language detection
        if self._detect_primary_language(context):
            base_confidence += 0.05
        
        # Adjust based on findings
        if len(findings) > 5:
            base_confidence += 0.05
        
        return min(base_confidence, 0.95)
    
    def get_expertise_areas(self) -> List[str]:
        """Get Quality Assurance Expert's areas of expertise."""
        return [
            "Test Strategy Design",
            "Test Automation",
            "Quality Metrics",
            "Testing Tools",
            "CI/CD Integration",
            "Performance Testing",
            "Security Testing",
            "Test Management",
            "Quality Gates",
            "Defect Management"
        ]
    
    def get_research_methods(self) -> List[str]:
        """Get research methods used by QA Expert."""
        return [
            "Test Requirements Analysis",
            "Risk-Based Testing",
            "Test Strategy Planning",
            "Tool Evaluation",
            "Coverage Analysis",
            "Quality Metrics Definition",
            "CI/CD Planning",
            "Compliance Assessment"
        ]