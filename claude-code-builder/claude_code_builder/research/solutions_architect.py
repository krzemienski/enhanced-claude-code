"""Solutions Architect research agent."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .base_agent import BaseResearchAgent, AgentCapability, AgentContext, AgentResponse
from ..models.research import ResearchSource

logger = logging.getLogger(__name__)


class SolutionsArchitect(BaseResearchAgent):
    """Specializes in system architecture and design patterns."""
    
    def __init__(self):
        """Initialize Solutions Architect agent."""
        super().__init__(
            name="Solutions Architect",
            capabilities=[
                AgentCapability.ARCHITECTURE,
                AgentCapability.ANALYSIS,
                AgentCapability.RECOMMENDATION,
                AgentCapability.IMPLEMENTATION
            ]
        )
        
        # Architecture patterns knowledge base
        self.architecture_patterns = {
            "layered": {
                "description": "Separates concerns into layers (presentation, business, data)",
                "use_cases": ["Traditional web apps", "Enterprise applications"],
                "pros": ["Separation of concerns", "Easy to understand", "Testable"],
                "cons": ["Can be rigid", "Performance overhead", "Tight coupling between layers"]
            },
            "microservices": {
                "description": "Decomposed into small, independent services",
                "use_cases": ["Large-scale applications", "Multi-team projects"],
                "pros": ["Independent deployment", "Technology diversity", "Scalability"],
                "cons": ["Complexity", "Network latency", "Data consistency"]
            },
            "event_driven": {
                "description": "Components communicate through events",
                "use_cases": ["Real-time systems", "Reactive applications"],
                "pros": ["Loose coupling", "Scalability", "Flexibility"],
                "cons": ["Complexity", "Event ordering", "Debugging difficulty"]
            },
            "serverless": {
                "description": "Functions as a service, no server management",
                "use_cases": ["Event processing", "APIs", "Scheduled tasks"],
                "pros": ["No infrastructure management", "Auto-scaling", "Pay per use"],
                "cons": ["Vendor lock-in", "Cold starts", "Limited execution time"]
            },
            "hexagonal": {
                "description": "Ports and adapters pattern for flexibility",
                "use_cases": ["Domain-driven design", "Test-driven development"],
                "pros": ["Testability", "Flexibility", "Clear boundaries"],
                "cons": ["Initial complexity", "More code", "Learning curve"]
            }
        }
        
        self.design_patterns = {
            "creational": ["Singleton", "Factory", "Builder", "Prototype"],
            "structural": ["Adapter", "Decorator", "Facade", "Proxy"],
            "behavioral": ["Observer", "Strategy", "Command", "Iterator"],
            "architectural": ["MVC", "MVP", "MVVM", "Repository", "CQRS"]
        }
        
        self.integration_patterns = {
            "sync": {
                "rest": {"protocols": ["HTTP"], "formats": ["JSON", "XML"]},
                "graphql": {"protocols": ["HTTP"], "formats": ["JSON"]},
                "rpc": {"protocols": ["gRPC", "JSON-RPC"], "formats": ["Protocol Buffers", "JSON"]}
            },
            "async": {
                "message_queue": {"tools": ["RabbitMQ", "AWS SQS", "Redis"], "patterns": ["Pub/Sub", "Work Queue"]},
                "event_streaming": {"tools": ["Kafka", "AWS Kinesis", "Azure Event Hub"], "patterns": ["Event Sourcing", "CQRS"]},
                "webhooks": {"protocols": ["HTTP"], "patterns": ["Callback", "Notification"]}
            }
        }
    
    async def _initialize(self) -> None:
        """Initialize the Solutions Architect."""
        logger.info("Solutions Architect initialized with architecture patterns knowledge")
    
    async def _perform_research(self, context: AgentContext) -> AgentResponse:
        """Perform architecture analysis research."""
        findings = []
        recommendations = []
        
        # Analyze architecture requirements
        arch_requirements = await self._analyze_architecture_requirements(context)
        findings.extend(arch_requirements["findings"])
        recommendations.extend(arch_requirements["recommendations"])
        
        # Recommend architecture pattern
        pattern_recommendation = await self._recommend_architecture_pattern(context)
        findings.extend(pattern_recommendation["findings"])
        recommendations.extend(pattern_recommendation["recommendations"])
        
        # Design system components
        component_design = await self._design_system_components(context)
        findings.extend(component_design["findings"])
        recommendations.extend(component_design["recommendations"])
        
        # Integration strategy
        integration = await self._plan_integration_strategy(context)
        findings.extend(integration["findings"])
        recommendations.extend(integration["recommendations"])
        
        # Data architecture
        data_arch = await self._design_data_architecture(context)
        findings.extend(data_arch["findings"])
        recommendations.extend(data_arch["recommendations"])
        
        # Calculate confidence
        confidence = self._calculate_confidence(context, findings)
        
        return AgentResponse(
            agent_name=self.name,
            findings=findings,
            recommendations=self.prioritize_recommendations(recommendations, context),
            confidence=confidence,
            sources_used=[ResearchSource.DOCUMENTATION, ResearchSource.COMMUNITY],
            metadata={
                "patterns_analyzed": len(self.architecture_patterns),
                "components_designed": len(component_design.get("components", []))
            }
        )
    
    async def _analyze_architecture_requirements(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze architecture requirements from project context."""
        findings = []
        recommendations = []
        
        # Analyze scale requirements
        scale_analysis = self._analyze_scale_requirements(context)
        findings.append({
            "title": "Scale Requirements Analysis",
            "description": f"Project requires {scale_analysis['scale']} scale architecture",
            "relevance": 1.0,
            "area": "requirements",
            "details": scale_analysis
        })
        
        # Analyze complexity
        complexity = self._assess_complexity(context)
        findings.append({
            "title": "System Complexity Assessment",
            "description": f"Estimated system complexity: {complexity['level']}",
            "relevance": 0.9,
            "factors": complexity["factors"]
        })
        
        # Non-functional requirements
        nfr = self._identify_non_functional_requirements(context)
        if nfr:
            findings.append({
                "title": "Non-Functional Requirements",
                "description": "Identified key quality attributes",
                "relevance": 0.9,
                "requirements": nfr
            })
            
            for req in nfr:
                recommendations.append(f"Design for {req['name']}: {req['strategy']}")
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _recommend_architecture_pattern(self, context: AgentContext) -> Dict[str, Any]:
        """Recommend appropriate architecture pattern."""
        findings = []
        recommendations = []
        
        # Score each pattern
        pattern_scores = {}
        for pattern_name, pattern_info in self.architecture_patterns.items():
            score = self._score_pattern(pattern_name, pattern_info, context)
            pattern_scores[pattern_name] = score
        
        # Get best pattern
        best_pattern = max(pattern_scores, key=pattern_scores.get)
        best_info = self.architecture_patterns[best_pattern]
        
        findings.append({
            "title": f"Recommended Architecture: {best_pattern.replace('_', ' ').title()}",
            "description": best_info["description"],
            "relevance": 1.0,
            "score": pattern_scores[best_pattern],
            "pros": best_info["pros"],
            "cons": best_info["cons"]
        })
        
        # Pattern-specific recommendations
        if best_pattern == "microservices":
            recommendations.extend([
                "Implement service discovery mechanism",
                "Use API gateway for client communication",
                "Implement distributed tracing",
                "Design for eventual consistency",
                "Use container orchestration (Kubernetes)"
            ])
        elif best_pattern == "layered":
            recommendations.extend([
                "Implement clear layer boundaries",
                "Use dependency injection",
                "Keep business logic in domain layer",
                "Implement repository pattern for data access"
            ])
        elif best_pattern == "event_driven":
            recommendations.extend([
                "Choose appropriate message broker",
                "Implement event schema registry",
                "Design for idempotency",
                "Implement event sourcing if needed"
            ])
        
        # Also mention alternative patterns
        alternatives = sorted(
            pattern_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[1:3]
        
        for alt_pattern, score in alternatives:
            if score > 0.6:
                findings.append({
                    "title": f"Alternative: {alt_pattern.replace('_', ' ').title()}",
                    "description": f"Could also work for this project (score: {score:.2f})",
                    "relevance": 0.7
                })
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _design_system_components(self, context: AgentContext) -> Dict[str, Any]:
        """Design high-level system components."""
        findings = []
        recommendations = []
        components = []
        
        project_type = context.project_spec.type
        
        # Define components by project type
        if project_type == "web_application":
            components = [
                {"name": "Frontend", "type": "presentation", "technologies": ["React/Vue/Angular"]},
                {"name": "API Gateway", "type": "integration", "purpose": "Route and authenticate requests"},
                {"name": "Application Server", "type": "business", "purpose": "Business logic processing"},
                {"name": "Database", "type": "data", "technologies": ["PostgreSQL", "MongoDB"]},
                {"name": "Cache Layer", "type": "performance", "technologies": ["Redis"]},
                {"name": "File Storage", "type": "storage", "technologies": ["S3", "MinIO"]}
            ]
        elif project_type == "api_service":
            components = [
                {"name": "API Gateway", "type": "integration", "purpose": "Rate limiting, authentication"},
                {"name": "Service Layer", "type": "business", "purpose": "Core API logic"},
                {"name": "Data Access Layer", "type": "data", "purpose": "Database abstraction"},
                {"name": "Cache", "type": "performance", "technologies": ["Redis", "Memcached"]},
                {"name": "Message Queue", "type": "async", "technologies": ["RabbitMQ", "SQS"]}
            ]
        elif project_type == "data_pipeline":
            components = [
                {"name": "Data Ingestion", "type": "input", "purpose": "Collect data from sources"},
                {"name": "Processing Engine", "type": "compute", "technologies": ["Spark", "Flink"]},
                {"name": "Data Storage", "type": "storage", "technologies": ["Data Lake", "Data Warehouse"]},
                {"name": "Orchestrator", "type": "control", "technologies": ["Airflow", "Prefect"]},
                {"name": "Monitoring", "type": "observability", "purpose": "Track pipeline health"}
            ]
        
        findings.append({
            "title": "System Component Design",
            "description": f"Designed {len(components)} core components",
            "relevance": 1.0,
            "components": components
        })
        
        # Component-specific recommendations
        for component in components:
            if component["type"] == "data":
                recommendations.append(f"{component['name']}: Implement proper backup and recovery")
            elif component["type"] == "integration":
                recommendations.append(f"{component['name']}: Implement circuit breaker pattern")
            elif component["type"] == "performance":
                recommendations.append(f"{component['name']}: Monitor hit rates and performance")
        
        # Communication patterns
        comm_patterns = self._design_communication_patterns(components)
        findings.append({
            "title": "Component Communication",
            "description": "Defined communication patterns between components",
            "relevance": 0.8,
            "patterns": comm_patterns
        })
        
        return {
            "findings": findings,
            "recommendations": recommendations,
            "components": components
        }
    
    async def _plan_integration_strategy(self, context: AgentContext) -> Dict[str, Any]:
        """Plan integration strategy for external systems."""
        findings = []
        recommendations = []
        
        # Identify integration needs
        integration_needs = self._identify_integration_needs(context)
        
        if integration_needs:
            findings.append({
                "title": "Integration Requirements",
                "description": f"Identified {len(integration_needs)} integration points",
                "relevance": 0.9,
                "integrations": integration_needs
            })
            
            # Recommend integration patterns
            for need in integration_needs:
                if need["type"] == "sync":
                    recommendations.append(
                        f"{need['name']}: Use REST API with circuit breaker"
                    )
                else:
                    recommendations.append(
                        f"{need['name']}: Implement async messaging with retry logic"
                    )
        
        # API design principles
        if context.project_spec.type in ["api_service", "web_application"]:
            findings.append({
                "title": "API Design Principles",
                "description": "Recommended API design approach",
                "relevance": 0.8,
                "principles": [
                    "RESTful design with proper HTTP verbs",
                    "Versioning strategy (URL or header)",
                    "Consistent error response format",
                    "Pagination for list endpoints",
                    "Rate limiting per client"
                ]
            })
            
            recommendations.extend([
                "Document APIs using OpenAPI/Swagger",
                "Implement API versioning from the start",
                "Use consistent naming conventions",
                "Implement proper HTTP status codes"
            ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _design_data_architecture(self, context: AgentContext) -> Dict[str, Any]:
        """Design data architecture and storage strategy."""
        findings = []
        recommendations = []
        
        # Analyze data requirements
        data_types = self._analyze_data_types(context)
        
        findings.append({
            "title": "Data Architecture Analysis",
            "description": "Analyzed data storage requirements",
            "relevance": 0.9,
            "data_types": data_types
        })
        
        # Storage recommendations
        storage_strategy = self._determine_storage_strategy(data_types, context)
        
        for storage in storage_strategy:
            findings.append({
                "title": f"Storage: {storage['type']}",
                "description": storage["reason"],
                "relevance": 0.8,
                "technology": storage["technology"],
                "use_case": storage["use_case"]
            })
            
            recommendations.extend(storage["recommendations"])
        
        # Data consistency strategy
        if len(storage_strategy) > 1:
            findings.append({
                "title": "Data Consistency Strategy",
                "description": "Multiple data stores require consistency approach",
                "relevance": 0.8,
                "approach": "Eventual consistency with saga pattern"
            })
            
            recommendations.extend([
                "Implement saga pattern for distributed transactions",
                "Use event sourcing for audit trail",
                "Implement compensating transactions"
            ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    def _analyze_scale_requirements(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze scale requirements from context."""
        scale_indicators = {
            "small": ["prototype", "mvp", "internal", "pilot"],
            "medium": ["startup", "smb", "department"],
            "large": ["enterprise", "platform", "saas", "global"]
        }
        
        project_text = context.project_spec.description.lower()
        detected_scale = "medium"  # default
        
        for scale, indicators in scale_indicators.items():
            if any(indicator in project_text for indicator in indicators):
                detected_scale = scale
                break
        
        # Check feature count
        feature_count = len(context.project_spec.features)
        if feature_count > 20:
            detected_scale = "large"
        elif feature_count < 5:
            detected_scale = "small"
        
        return {
            "scale": detected_scale,
            "factors": {
                "features": feature_count,
                "complexity": self._assess_complexity(context)["level"]
            }
        }
    
    def _assess_complexity(self, context: AgentContext) -> Dict[str, Any]:
        """Assess system complexity."""
        factors = []
        score = 0
        
        # Feature complexity
        feature_count = len(context.project_spec.features)
        if feature_count > 15:
            factors.append("High feature count")
            score += 3
        elif feature_count > 8:
            factors.append("Moderate feature count")
            score += 2
        else:
            factors.append("Low feature count")
            score += 1
        
        # Technology diversity
        tech_count = len(context.project_spec.technologies)
        if tech_count > 5:
            factors.append("High technology diversity")
            score += 2
        
        # Integration complexity
        integration_keywords = ["api", "integration", "third-party", "external"]
        if any(kw in context.project_spec.description.lower() for kw in integration_keywords):
            factors.append("External integrations")
            score += 2
        
        # Determine level
        if score >= 7:
            level = "high"
        elif score >= 4:
            level = "medium"
        else:
            level = "low"
        
        return {
            "level": level,
            "score": score,
            "factors": factors
        }
    
    def _identify_non_functional_requirements(self, context: AgentContext) -> List[Dict[str, Any]]:
        """Identify non-functional requirements."""
        nfrs = []
        
        # Performance
        if any(kw in str(context.project_spec).lower() for kw in ["performance", "fast", "speed"]):
            nfrs.append({
                "name": "Performance",
                "requirement": "Sub-second response times",
                "strategy": "Caching, CDN, optimization"
            })
        
        # Availability
        if context.project_spec.type in ["api_service", "web_application"]:
            nfrs.append({
                "name": "Availability",
                "requirement": "99.9% uptime",
                "strategy": "Redundancy, health checks, auto-recovery"
            })
        
        # Scalability
        if "scale" in context.project_spec.description.lower():
            nfrs.append({
                "name": "Scalability",
                "requirement": "Handle 10x growth",
                "strategy": "Horizontal scaling, caching, async processing"
            })
        
        # Security
        nfrs.append({
            "name": "Security",
            "requirement": "Data protection and access control",
            "strategy": "Encryption, authentication, authorization"
        })
        
        return nfrs
    
    def _score_pattern(self, pattern_name: str, pattern_info: Dict[str, Any], context: AgentContext) -> float:
        """Score an architecture pattern for the context."""
        score = 0.5  # Base score
        
        # Project type matching
        type_patterns = {
            "web_application": ["layered", "microservices", "hexagonal"],
            "api_service": ["microservices", "serverless", "hexagonal"],
            "cli_tool": ["layered", "hexagonal"],
            "data_pipeline": ["event_driven", "microservices"],
            "automation": ["serverless", "event_driven"]
        }
        
        if context.project_spec.type in type_patterns:
            if pattern_name in type_patterns[context.project_spec.type]:
                score += 0.3
        
        # Scale matching
        scale = self._analyze_scale_requirements(context)["scale"]
        if scale == "large" and pattern_name in ["microservices", "event_driven"]:
            score += 0.2
        elif scale == "small" and pattern_name in ["layered", "serverless"]:
            score += 0.2
        
        # Complexity matching
        complexity = self._assess_complexity(context)["level"]
        if complexity == "high" and pattern_name in ["microservices", "hexagonal"]:
            score += 0.1
        elif complexity == "low" and pattern_name in ["layered", "serverless"]:
            score += 0.1
        
        return min(score, 1.0)
    
    def _design_communication_patterns(self, components: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Design communication patterns between components."""
        patterns = []
        
        # Frontend to Backend
        if any(c["name"] == "Frontend" for c in components):
            patterns.append({
                "from": "Frontend",
                "to": "API Gateway",
                "pattern": "REST/GraphQL",
                "protocol": "HTTPS"
            })
        
        # API Gateway to Services
        if any(c["name"] == "API Gateway" for c in components):
            patterns.append({
                "from": "API Gateway",
                "to": "Application Server",
                "pattern": "HTTP/gRPC",
                "protocol": "Internal network"
            })
        
        # Service to Database
        patterns.append({
            "from": "Application Layer",
            "to": "Database",
            "pattern": "Connection Pool",
            "protocol": "TCP"
        })
        
        # Async communication
        if any(c["type"] == "async" for c in components):
            patterns.append({
                "from": "Services",
                "to": "Message Queue",
                "pattern": "Pub/Sub",
                "protocol": "AMQP/MQTT"
            })
        
        return patterns
    
    def _identify_integration_needs(self, context: AgentContext) -> List[Dict[str, Any]]:
        """Identify external integration needs."""
        integrations = []
        
        # Check for common integrations
        integration_map = {
            "payment": {"name": "Payment Gateway", "type": "sync", "examples": ["Stripe", "PayPal"]},
            "email": {"name": "Email Service", "type": "async", "examples": ["SendGrid", "AWS SES"]},
            "storage": {"name": "Object Storage", "type": "sync", "examples": ["S3", "Azure Blob"]},
            "auth": {"name": "Identity Provider", "type": "sync", "examples": ["Auth0", "Okta"]},
            "search": {"name": "Search Service", "type": "sync", "examples": ["Elasticsearch", "Algolia"]},
            "analytics": {"name": "Analytics", "type": "async", "examples": ["Google Analytics", "Mixpanel"]}
        }
        
        project_text = (
            context.project_spec.description.lower() +
            " ".join(f.name.lower() for f in context.project_spec.features)
        )
        
        for keyword, integration in integration_map.items():
            if keyword in project_text:
                integrations.append(integration)
        
        return integrations
    
    def _analyze_data_types(self, context: AgentContext) -> List[Dict[str, str]]:
        """Analyze data types in the project."""
        data_types = []
        
        # Structured data
        if any(kw in str(context.project_spec).lower() for kw in ["user", "account", "profile"]):
            data_types.append({
                "type": "Structured",
                "examples": "User profiles, accounts",
                "characteristics": "Relational, ACID"
            })
        
        # Document data
        if any(kw in str(context.project_spec).lower() for kw in ["content", "article", "post"]):
            data_types.append({
                "type": "Document",
                "examples": "Articles, posts, content",
                "characteristics": "Flexible schema, nested"
            })
        
        # Time series
        if any(kw in str(context.project_spec).lower() for kw in ["metrics", "logs", "events"]):
            data_types.append({
                "type": "Time Series",
                "examples": "Metrics, logs, events",
                "characteristics": "Time-based, append-only"
            })
        
        # File storage
        if any(kw in str(context.project_spec).lower() for kw in ["upload", "file", "image"]):
            data_types.append({
                "type": "Binary",
                "examples": "Files, images, videos",
                "characteristics": "Large objects, CDN"
            })
        
        return data_types
    
    def _determine_storage_strategy(self, data_types: List[Dict[str, str]], context: AgentContext) -> List[Dict[str, Any]]:
        """Determine storage strategy based on data types."""
        strategy = []
        
        for data_type in data_types:
            if data_type["type"] == "Structured":
                strategy.append({
                    "type": "Relational Database",
                    "technology": "PostgreSQL",
                    "reason": "ACID compliance for transactional data",
                    "use_case": data_type["examples"],
                    "recommendations": [
                        "Design normalized schema",
                        "Implement proper indexing",
                        "Use connection pooling"
                    ]
                })
            elif data_type["type"] == "Document":
                strategy.append({
                    "type": "Document Database",
                    "technology": "MongoDB",
                    "reason": "Flexible schema for content",
                    "use_case": data_type["examples"],
                    "recommendations": [
                        "Design document schema carefully",
                        "Implement proper sharding",
                        "Use aggregation pipelines"
                    ]
                })
            elif data_type["type"] == "Time Series":
                strategy.append({
                    "type": "Time Series Database",
                    "technology": "InfluxDB or TimescaleDB",
                    "reason": "Optimized for time-based data",
                    "use_case": data_type["examples"],
                    "recommendations": [
                        "Define retention policies",
                        "Use continuous aggregations",
                        "Implement data downsampling"
                    ]
                })
            elif data_type["type"] == "Binary":
                strategy.append({
                    "type": "Object Storage",
                    "technology": "S3 or MinIO",
                    "reason": "Scalable file storage",
                    "use_case": data_type["examples"],
                    "recommendations": [
                        "Use CDN for distribution",
                        "Implement access control",
                        "Generate presigned URLs"
                    ]
                })
        
        # Add cache layer if needed
        if len(strategy) > 0 and context.project_spec.type in ["web_application", "api_service"]:
            strategy.append({
                "type": "Cache Layer",
                "technology": "Redis",
                "reason": "Performance optimization",
                "use_case": "Session storage, query caching",
                "recommendations": [
                    "Implement cache invalidation strategy",
                    "Use appropriate TTL values",
                    "Monitor cache hit rates"
                ]
            })
        
        return strategy
    
    def _calculate_confidence(self, context: AgentContext, findings: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for architecture analysis."""
        base_confidence = 0.8
        
        # Increase confidence based on project type familiarity
        familiar_types = ["web_application", "api_service", "data_pipeline"]
        if context.project_spec.type in familiar_types:
            base_confidence += 0.1
        
        # Adjust based on complexity
        complexity = self._assess_complexity(context)["level"]
        if complexity == "low":
            base_confidence += 0.05
        elif complexity == "high":
            base_confidence -= 0.05
        
        return min(max(base_confidence, 0.5), 0.95)
    
    def get_expertise_areas(self) -> List[str]:
        """Get Solutions Architect's areas of expertise."""
        return [
            "System Architecture",
            "Design Patterns",
            "Microservices",
            "Cloud Architecture",
            "Integration Patterns",
            "Data Architecture",
            "Scalability Design",
            "API Design",
            "Component Design",
            "Architecture Patterns"
        ]
    
    def get_research_methods(self) -> List[str]:
        """Get research methods used by Solutions Architect."""
        return [
            "Architecture Analysis",
            "Pattern Matching",
            "Component Design",
            "Integration Planning",
            "Data Modeling",
            "Scalability Assessment",
            "Complexity Analysis",
            "Best Practices Application"
        ]