"""Specification analyzer for AI planning."""

import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import json

from ..models import ProjectSpec, Feature, Technology, APIEndpoint, MemoryStore, MemoryType
from ..config import AIConfig
from ..logging import logger
from ..exceptions import PlanningError


@dataclass
class AnalysisResult:
    """Result of specification analysis."""
    
    # Project characteristics
    project_type: str
    architecture_style: str
    deployment_model: str
    
    # Complexity factors
    feature_complexity: float
    technical_complexity: float
    integration_complexity: float
    overall_complexity: float
    
    # Technology analysis
    primary_language: str
    frameworks: List[str]
    databases: List[str]
    external_services: List[str]
    
    # Requirements analysis
    has_authentication: bool
    has_api: bool
    has_frontend: bool
    has_realtime: bool
    has_data_processing: bool
    
    # Patterns identified
    design_patterns: List[str]
    architectural_patterns: List[str]
    
    # Insights
    key_challenges: List[str]
    recommended_approaches: List[str]
    potential_bottlenecks: List[str]
    
    # Metadata
    tokens_used: int = 0
    analysis_confidence: float = 0.9


class SpecificationAnalyzer:
    """Analyzes project specifications for planning."""
    
    def __init__(self, ai_config: AIConfig, memory_store: MemoryStore):
        """Initialize analyzer."""
        self.ai_config = ai_config
        self.memory_store = memory_store
        
        # Analysis patterns
        self.project_type_patterns = {
            "web_app": ["frontend", "ui", "dashboard", "portal", "website"],
            "api": ["rest", "graphql", "microservice", "endpoint", "webhook"],
            "cli": ["command", "terminal", "console", "script"],
            "library": ["package", "module", "sdk", "framework"],
            "data_pipeline": ["etl", "pipeline", "processing", "analytics"],
            "ml_model": ["machine learning", "ai", "model", "training"]
        }
        
        self.architecture_patterns = {
            "monolithic": ["monolith", "single", "unified"],
            "microservices": ["microservice", "distributed", "service-oriented"],
            "serverless": ["serverless", "lambda", "function", "faas"],
            "event_driven": ["event", "message", "queue", "pubsub"],
            "layered": ["layer", "tier", "mvc", "mvp"]
        }
    
    async def analyze(self, project_spec: ProjectSpec) -> Dict[str, Any]:
        """Analyze project specification."""
        logger.info("Analyzing project specification", project=project_spec.metadata.name)
        
        try:
            # Check memory for similar analysis
            cached_analysis = self._check_memory_cache(project_spec)
            if cached_analysis:
                logger.info("Using cached analysis from memory")
                return cached_analysis
            
            # Perform analysis
            result = self._perform_analysis(project_spec)
            
            # If AI-enhanced analysis is enabled
            if self.ai_config.adaptive_planning:
                result = await self._enhance_with_ai(project_spec, result)
            
            # Store in memory
            self._store_analysis(project_spec, result)
            
            return result.to_dict()
            
        except Exception as e:
            logger.error("Specification analysis failed", error=str(e))
            raise PlanningError(f"Failed to analyze specification: {str(e)}", cause=e)
    
    def _check_memory_cache(self, project_spec: ProjectSpec) -> Optional[Dict[str, Any]]:
        """Check memory for cached analysis."""
        # Create cache key from project characteristics
        cache_key = f"spec_analysis_{project_spec.metadata.name}_{project_spec.version}"
        
        entry = self.memory_store.get_by_key(cache_key)
        if entry:
            logger.info("Found cached analysis", cache_key=cache_key)
            return entry.value
        
        return None
    
    def _perform_analysis(self, project_spec: ProjectSpec) -> AnalysisResult:
        """Perform detailed specification analysis."""
        # Determine project type
        project_type = self._identify_project_type(project_spec)
        
        # Determine architecture style
        architecture_style = self._identify_architecture(project_spec)
        
        # Analyze technologies
        tech_analysis = self._analyze_technologies(project_spec)
        
        # Analyze features
        feature_analysis = self._analyze_features(project_spec)
        
        # Calculate complexity
        complexity = self._calculate_complexity(project_spec, tech_analysis, feature_analysis)
        
        # Identify patterns
        patterns = self._identify_patterns(project_spec)
        
        # Generate insights
        insights = self._generate_insights(project_spec, tech_analysis, feature_analysis)
        
        return AnalysisResult(
            project_type=project_type,
            architecture_style=architecture_style,
            deployment_model=self._identify_deployment_model(project_spec),
            feature_complexity=complexity["feature"],
            technical_complexity=complexity["technical"],
            integration_complexity=complexity["integration"],
            overall_complexity=complexity["overall"],
            primary_language=tech_analysis["primary_language"],
            frameworks=tech_analysis["frameworks"],
            databases=tech_analysis["databases"],
            external_services=tech_analysis["external_services"],
            has_authentication=feature_analysis["has_authentication"],
            has_api=feature_analysis["has_api"],
            has_frontend=feature_analysis["has_frontend"],
            has_realtime=feature_analysis["has_realtime"],
            has_data_processing=feature_analysis["has_data_processing"],
            design_patterns=patterns["design"],
            architectural_patterns=patterns["architectural"],
            key_challenges=insights["challenges"],
            recommended_approaches=insights["approaches"],
            potential_bottlenecks=insights["bottlenecks"]
        )
    
    def _identify_project_type(self, project_spec: ProjectSpec) -> str:
        """Identify the type of project."""
        description_lower = project_spec.description.lower()
        name_lower = project_spec.metadata.name.lower()
        
        # Check against patterns
        scores = {}
        for ptype, keywords in self.project_type_patterns.items():
            score = sum(
                1 for keyword in keywords
                if keyword in description_lower or keyword in name_lower
            )
            scores[ptype] = score
        
        # Check features
        if project_spec.api_endpoints:
            scores["api"] = scores.get("api", 0) + 2
        
        if any(tech.category == "frontend" for tech in project_spec.technologies):
            scores["web_app"] = scores.get("web_app", 0) + 2
        
        # Return highest scoring type
        if scores:
            return max(scores, key=scores.get)
        
        return "general"
    
    def _identify_architecture(self, project_spec: ProjectSpec) -> str:
        """Identify architecture style."""
        description_lower = project_spec.description.lower()
        
        # Check against patterns
        for arch, keywords in self.architecture_patterns.items():
            if any(keyword in description_lower for keyword in keywords):
                return arch
        
        # Infer from project structure
        if len(project_spec.api_endpoints) > 20:
            return "microservices"
        elif any(tech.name.lower() in ["aws lambda", "google cloud functions"] 
                for tech in project_spec.technologies):
            return "serverless"
        elif any(keyword in description_lower 
                for keyword in ["event", "message", "queue"]):
            return "event_driven"
        
        return "layered"
    
    def _identify_deployment_model(self, project_spec: ProjectSpec) -> str:
        """Identify deployment model."""
        # Check deployment platforms
        if project_spec.build_requirements.deployment_platforms:
            platforms = [p.lower() for p in project_spec.build_requirements.deployment_platforms]
            
            if any("kubernetes" in p or "k8s" in p for p in platforms):
                return "kubernetes"
            elif any("docker" in p for p in platforms):
                return "containerized"
            elif any("serverless" in p or "lambda" in p for p in platforms):
                return "serverless"
            elif any("cloud" in p for p in platforms):
                return "cloud"
        
        # Check for Docker
        if project_spec.build_requirements.docker:
            return "containerized"
        
        return "traditional"
    
    def _analyze_technologies(self, project_spec: ProjectSpec) -> Dict[str, Any]:
        """Analyze technology stack."""
        languages = []
        frameworks = []
        databases = []
        services = []
        
        for tech in project_spec.technologies:
            if tech.category == "language":
                languages.append(tech.name)
            elif tech.category == "framework":
                frameworks.append(tech.name)
            elif tech.category == "database":
                databases.append(tech.name)
            elif tech.category == "service":
                services.append(tech.name)
        
        # Determine primary language
        primary_language = "Python"  # Default
        if languages:
            # Prioritize based on common patterns
            if "Python" in languages:
                primary_language = "Python"
            elif "JavaScript" in languages or "TypeScript" in languages:
                primary_language = "JavaScript"
            elif "Java" in languages:
                primary_language = "Java"
            elif "Go" in languages:
                primary_language = "Go"
            else:
                primary_language = languages[0]
        
        return {
            "primary_language": primary_language,
            "frameworks": frameworks,
            "databases": databases,
            "external_services": services
        }
    
    def _analyze_features(self, project_spec: ProjectSpec) -> Dict[str, bool]:
        """Analyze feature requirements."""
        feature_names = [f.name.lower() for f in project_spec.features]
        feature_descriptions = " ".join(f.description.lower() for f in project_spec.features)
        all_text = feature_descriptions + " " + project_spec.description.lower()
        
        return {
            "has_authentication": (
                project_spec.security_requirements.authentication_required or
                any(keyword in all_text for keyword in ["auth", "login", "user", "account"])
            ),
            "has_api": bool(project_spec.api_endpoints),
            "has_frontend": any(
                keyword in all_text 
                for keyword in ["ui", "frontend", "interface", "dashboard", "page"]
            ),
            "has_realtime": any(
                keyword in all_text 
                for keyword in ["realtime", "real-time", "websocket", "streaming", "live"]
            ),
            "has_data_processing": any(
                keyword in all_text 
                for keyword in ["process", "transform", "etl", "pipeline", "analytics"]
            )
        }
    
    def _calculate_complexity(
        self,
        project_spec: ProjectSpec,
        tech_analysis: Dict[str, Any],
        feature_analysis: Dict[str, bool]
    ) -> Dict[str, float]:
        """Calculate project complexity scores."""
        # Feature complexity (based on number and interdependencies)
        feature_count = len(project_spec.features)
        avg_feature_complexity = sum(f.complexity for f in project_spec.features) / max(feature_count, 1)
        feature_dependencies = sum(len(f.dependencies) for f in project_spec.features)
        
        feature_complexity = (
            (feature_count / 10) * 0.3 +  # Number of features
            (avg_feature_complexity / 10) * 0.5 +  # Average complexity
            (feature_dependencies / max(feature_count, 1)) * 0.2  # Dependencies
        )
        
        # Technical complexity (based on tech stack)
        tech_count = len(project_spec.technologies)
        framework_count = len(tech_analysis["frameworks"])
        db_count = len(tech_analysis["databases"])
        service_count = len(tech_analysis["external_services"])
        
        technical_complexity = (
            (tech_count / 15) * 0.2 +
            (framework_count / 5) * 0.3 +
            (db_count / 3) * 0.2 +
            (service_count / 5) * 0.3
        )
        
        # Integration complexity
        api_count = len(project_spec.api_endpoints)
        has_integrations = service_count > 0
        realtime_factor = 1.5 if feature_analysis["has_realtime"] else 1.0
        
        integration_complexity = (
            (api_count / 20) * 0.4 +
            (service_count / 5) * 0.4 +
            (0.2 if has_integrations else 0)
        ) * realtime_factor
        
        # Overall complexity
        overall_complexity = (
            feature_complexity * 0.4 +
            technical_complexity * 0.3 +
            integration_complexity * 0.3
        )
        
        return {
            "feature": min(feature_complexity * 10, 10),
            "technical": min(technical_complexity * 10, 10),
            "integration": min(integration_complexity * 10, 10),
            "overall": min(overall_complexity * 10, 10)
        }
    
    def _identify_patterns(self, project_spec: ProjectSpec) -> Dict[str, List[str]]:
        """Identify design and architectural patterns."""
        design_patterns = []
        architectural_patterns = []
        
        # Check for common design patterns
        all_text = (project_spec.description + " " + 
                   " ".join(f.description for f in project_spec.features)).lower()
        
        # Design patterns
        if "singleton" in all_text or "single instance" in all_text:
            design_patterns.append("Singleton")
        if "factory" in all_text or "create" in all_text:
            design_patterns.append("Factory")
        if "observer" in all_text or "event" in all_text or "listener" in all_text:
            design_patterns.append("Observer")
        if "strategy" in all_text or "algorithm" in all_text:
            design_patterns.append("Strategy")
        if "repository" in all_text or "data access" in all_text:
            design_patterns.append("Repository")
        
        # Architectural patterns
        if project_spec.api_endpoints:
            architectural_patterns.append("REST API")
        if "graphql" in all_text:
            architectural_patterns.append("GraphQL")
        if "microservice" in all_text:
            architectural_patterns.append("Microservices")
        if "event" in all_text and "driven" in all_text:
            architectural_patterns.append("Event-Driven")
        if "layer" in all_text or "tier" in all_text:
            architectural_patterns.append("Layered Architecture")
        
        # Default patterns if none identified
        if not design_patterns:
            design_patterns = ["MVC", "Repository"]
        if not architectural_patterns:
            architectural_patterns = ["Layered Architecture"]
        
        return {
            "design": design_patterns,
            "architectural": architectural_patterns
        }
    
    def _generate_insights(
        self,
        project_spec: ProjectSpec,
        tech_analysis: Dict[str, Any],
        feature_analysis: Dict[str, bool]
    ) -> Dict[str, List[str]]:
        """Generate analytical insights."""
        challenges = []
        approaches = []
        bottlenecks = []
        
        # Technology challenges
        if len(tech_analysis["frameworks"]) > 3:
            challenges.append("Multiple framework integration complexity")
            approaches.append("Create clear framework boundaries and adapters")
        
        if len(tech_analysis["databases"]) > 1:
            challenges.append("Multi-database consistency management")
            approaches.append("Implement distributed transaction patterns")
        
        # Feature challenges
        if feature_analysis["has_realtime"]:
            challenges.append("Real-time data synchronization")
            approaches.append("Use WebSocket with fallback to polling")
            bottlenecks.append("WebSocket connection limits")
        
        if feature_analysis["has_authentication"]:
            challenges.append("Secure authentication implementation")
            approaches.append("Use JWT with refresh token rotation")
        
        # Performance considerations
        if len(project_spec.api_endpoints) > 50:
            bottlenecks.append("API endpoint management complexity")
            approaches.append("Implement API versioning and documentation")
        
        if project_spec.performance_requirements.throughput_rps > 5000:
            bottlenecks.append("High throughput requirements")
            approaches.append("Implement caching and load balancing")
        
        # Security considerations
        if project_spec.security_requirements.compliance_standards:
            challenges.append(f"Compliance with {', '.join(project_spec.security_requirements.compliance_standards)}")
            approaches.append("Implement audit logging and encryption")
        
        # Default insights
        if not challenges:
            challenges = ["Standard implementation complexity"]
        if not approaches:
            approaches = ["Follow best practices and patterns"]
        if not bottlenecks:
            bottlenecks = ["Database query performance"]
        
        return {
            "challenges": challenges,
            "approaches": approaches,
            "bottlenecks": bottlenecks
        }
    
    async def _enhance_with_ai(
        self,
        project_spec: ProjectSpec,
        initial_result: AnalysisResult
    ) -> AnalysisResult:
        """Enhance analysis with AI insights."""
        import os
        from anthropic import AsyncAnthropic
        
        logger.info("Enhancing analysis with AI")
        
        # Get API key from environment or config
        api_key = os.environ.get('ANTHROPIC_API_KEY') or self.ai_config.api_key
        if not api_key:
            logger.warning("No API key available, skipping AI enhancement")
            return initial_result
        
        client = AsyncAnthropic(api_key=api_key)
        
        # Prepare prompt for AI analysis
        prompt = f"""Analyze this project specification and provide insights:

Project: {project_spec.name}
Description: {project_spec.description}

Key Requirements:
- Features: {len(project_spec.features)} features
- Technologies: {', '.join(t.name for t in project_spec.technologies)}
- Performance: {project_spec.performance_requirements.response_time_ms}ms response time

Initial Analysis:
- Risks: {initial_result.key_risks}
- Challenges: {initial_result.key_challenges}
- Bottlenecks: {initial_result.potential_bottlenecks}

Provide additional insights about:
1. Hidden technical challenges
2. Architecture recommendations
3. Performance optimization strategies
4. Technology stack improvements
5. Risk mitigation approaches

Format as JSON with keys: challenges, recommendations, bottlenecks, optimizations"""

        try:
            response = await client.messages.create(
                model=self.ai_config.model or "claude-3-opus-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            # Parse AI response
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                ai_insights = json.loads(json_match.group())
                
                # Add AI insights to result
                if 'challenges' in ai_insights:
                    initial_result.key_challenges.extend(ai_insights['challenges'])
                if 'recommendations' in ai_insights:
                    initial_result.recommended_approaches.extend(ai_insights['recommendations'])
                if 'bottlenecks' in ai_insights:
                    initial_result.potential_bottlenecks.extend(ai_insights['bottlenecks'])
                if 'optimizations' in ai_insights:
                    initial_result.optimization_opportunities.extend(ai_insights['optimizations'])
            
            # Calculate actual tokens used
            initial_result.tokens_used = response.usage.total_tokens
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            # Continue with initial result if AI fails
        
        return initial_result
    
    def _store_analysis(self, project_spec: ProjectSpec, result: AnalysisResult) -> None:
        """Store analysis in memory."""
        cache_key = f"spec_analysis_{project_spec.metadata.name}_{project_spec.version}"
        
        self.memory_store.add(
            key=cache_key,
            value=result.to_dict(),
            entry_type=MemoryType.RESULT,
            phase="planning",
            tags={"analysis", project_spec.metadata.name},
            importance=8.0
        )
        
        # Store key insights separately for quick access
        self.memory_store.add(
            key=f"project_type_{project_spec.metadata.name}",
            value=result.project_type,
            entry_type=MemoryType.CONTEXT,
            phase="planning",
            importance=7.0
        )
        
        self.memory_store.add(
            key=f"complexity_{project_spec.metadata.name}",
            value={
                "overall": result.overall_complexity,
                "feature": result.feature_complexity,
                "technical": result.technical_complexity
            },
            entry_type=MemoryType.CONTEXT,
            phase="planning",
            importance=7.0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis result to dictionary."""
        return {
            "project_type": self.project_type,
            "architecture_style": self.architecture_style,
            "deployment_model": self.deployment_model,
            "complexity": {
                "feature": self.feature_complexity,
                "technical": self.technical_complexity,
                "integration": self.integration_complexity,
                "overall": self.overall_complexity
            },
            "technologies": {
                "primary_language": self.primary_language,
                "frameworks": self.frameworks,
                "databases": self.databases,
                "external_services": self.external_services
            },
            "requirements": {
                "has_authentication": self.has_authentication,
                "has_api": self.has_api,
                "has_frontend": self.has_frontend,
                "has_realtime": self.has_realtime,
                "has_data_processing": self.has_data_processing
            },
            "patterns": {
                "design": self.design_patterns,
                "architectural": self.architectural_patterns
            },
            "insights": {
                "challenges": self.key_challenges,
                "approaches": self.recommended_approaches,
                "bottlenecks": self.potential_bottlenecks
            },
            "metadata": {
                "tokens_used": self.tokens_used,
                "confidence": self.analysis_confidence
            }
        }


# The to_dict method is already defined within the AnalysisResult class