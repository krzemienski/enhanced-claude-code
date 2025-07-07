"""Performance Engineer research agent."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .base_agent import BaseResearchAgent, AgentCapability, AgentContext, AgentResponse
from ..models.research import ResearchSource

logger = logging.getLogger(__name__)


class PerformanceEngineer(BaseResearchAgent):
    """Specializes in performance optimization and scalability."""
    
    def __init__(self):
        """Initialize Performance Engineer agent."""
        super().__init__(
            name="Performance Engineer",
            capabilities=[
                AgentCapability.PERFORMANCE,
                AgentCapability.OPTIMIZATION,
                AgentCapability.ANALYSIS,
                AgentCapability.RECOMMENDATION
            ]
        )
        
        # Performance knowledge base
        self.performance_metrics = {
            "web": {
                "ttfb": {"target": 200, "unit": "ms", "name": "Time to First Byte"},
                "fcp": {"target": 1800, "unit": "ms", "name": "First Contentful Paint"},
                "lcp": {"target": 2500, "unit": "ms", "name": "Largest Contentful Paint"},
                "fid": {"target": 100, "unit": "ms", "name": "First Input Delay"},
                "cls": {"target": 0.1, "unit": "score", "name": "Cumulative Layout Shift"}
            },
            "api": {
                "response_time": {"target": 100, "unit": "ms", "name": "Response Time"},
                "throughput": {"target": 1000, "unit": "rps", "name": "Requests per Second"},
                "error_rate": {"target": 0.1, "unit": "%", "name": "Error Rate"},
                "latency_p99": {"target": 200, "unit": "ms", "name": "99th Percentile Latency"}
            },
            "database": {
                "query_time": {"target": 50, "unit": "ms", "name": "Query Execution Time"},
                "connections": {"target": 100, "unit": "count", "name": "Connection Pool Size"},
                "cache_hit": {"target": 90, "unit": "%", "name": "Cache Hit Rate"},
                "deadlocks": {"target": 0, "unit": "count", "name": "Deadlocks per Hour"}
            }
        }
        
        self.optimization_techniques = {
            "caching": {
                "browser": ["Cache-Control headers", "ETags", "Service Workers"],
                "cdn": ["Static asset caching", "Edge computing", "Geographic distribution"],
                "application": ["Redis", "Memcached", "In-memory caching"],
                "database": ["Query result caching", "Materialized views"]
            },
            "compression": {
                "text": ["Gzip", "Brotli", "Minification"],
                "images": ["WebP", "AVIF", "Lazy loading", "Responsive images"],
                "video": ["Adaptive bitrate", "H.265", "VP9"]
            },
            "async": {
                "frontend": ["Async/defer scripts", "Code splitting", "Lazy loading"],
                "backend": ["Async I/O", "Message queues", "Worker threads"],
                "database": ["Connection pooling", "Async queries", "Read replicas"]
            }
        }
        
        self.scalability_patterns = {
            "horizontal": {
                "techniques": ["Load balancing", "Auto-scaling", "Sharding"],
                "tools": ["Kubernetes", "Docker Swarm", "AWS ECS"]
            },
            "vertical": {
                "techniques": ["Resource optimization", "Memory management", "CPU optimization"],
                "considerations": ["Cost", "Hardware limits", "Downtime"]
            },
            "microservices": {
                "benefits": ["Independent scaling", "Technology diversity", "Fault isolation"],
                "challenges": ["Network latency", "Data consistency", "Complexity"]
            }
        }
    
    async def _initialize(self) -> None:
        """Initialize the Performance Engineer."""
        logger.info("Performance Engineer initialized with optimization knowledge base")
    
    async def _perform_research(self, context: AgentContext) -> AgentResponse:
        """Perform performance analysis research."""
        findings = []
        recommendations = []
        
        # Analyze performance requirements
        perf_requirements = await self._analyze_performance_requirements(context)
        findings.extend(perf_requirements["findings"])
        recommendations.extend(perf_requirements["recommendations"])
        
        # Identify performance bottlenecks
        bottlenecks = await self._identify_bottlenecks(context)
        findings.extend(bottlenecks["findings"])
        recommendations.extend(bottlenecks["recommendations"])
        
        # Suggest optimization strategies
        optimizations = await self._suggest_optimizations(context)
        findings.extend(optimizations["findings"])
        recommendations.extend(optimizations["recommendations"])
        
        # Scalability analysis
        scalability = await self._analyze_scalability(context)
        findings.extend(scalability["findings"])
        recommendations.extend(scalability["recommendations"])
        
        # Monitoring recommendations
        monitoring = await self._recommend_monitoring(context)
        findings.extend(monitoring["findings"])
        recommendations.extend(monitoring["recommendations"])
        
        # Calculate confidence
        confidence = self._calculate_confidence(context, findings)
        
        return AgentResponse(
            agent_name=self.name,
            findings=findings,
            recommendations=self.prioritize_recommendations(recommendations, context),
            confidence=confidence,
            sources_used=[ResearchSource.DOCUMENTATION, ResearchSource.COMMUNITY],
            metadata={
                "performance_areas": len(set(f.get("area", "") for f in findings)),
                "optimization_count": len([r for r in recommendations if "optimize" in r.lower()])
            }
        )
    
    async def _analyze_performance_requirements(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze performance requirements based on project type."""
        findings = []
        recommendations = []
        
        project_type = context.project_spec.type
        
        # Define performance targets by project type
        performance_targets = {
            "web_application": {
                "page_load": "< 3 seconds",
                "api_response": "< 200ms",
                "concurrent_users": "1000+",
                "availability": "99.9%"
            },
            "api_service": {
                "response_time": "< 100ms",
                "throughput": "1000 req/s",
                "availability": "99.95%",
                "error_rate": "< 0.1%"
            },
            "data_pipeline": {
                "processing_speed": "10K records/second",
                "latency": "< 5 minutes",
                "reliability": "99.99%",
                "scalability": "Horizontal"
            },
            "cli_tool": {
                "startup_time": "< 100ms",
                "response_time": "< 50ms",
                "memory_usage": "< 100MB",
                "cpu_usage": "< 10%"
            }
        }
        
        if project_type in performance_targets:
            targets = performance_targets[project_type]
            
            findings.append({
                "title": "Performance Requirements Analysis",
                "description": f"Identified performance targets for {project_type}",
                "relevance": 1.0,
                "area": "requirements",
                "targets": targets
            })
            
            # Generate recommendations based on targets
            recommendations.append(
                f"Design for {targets.get('concurrent_users', 'expected')} concurrent users"
            )
            recommendations.append(
                f"Optimize for {targets.get('response_time', 'fast')} response times"
            )
        
        # Check for specific performance features
        perf_features = self._identify_performance_features(context)
        if perf_features:
            findings.append({
                "title": "Performance-Critical Features",
                "description": "Identified features requiring optimization",
                "relevance": 0.9,
                "features": perf_features
            })
            
            for feature in perf_features:
                recommendations.append(f"Optimize {feature} for performance")
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _identify_bottlenecks(self, context: AgentContext) -> Dict[str, Any]:
        """Identify potential performance bottlenecks."""
        findings = []
        recommendations = []
        
        # Common bottlenecks by technology
        tech_bottlenecks = {
            "python": {
                "gil": "Global Interpreter Lock limits true parallelism",
                "sync_io": "Synchronous I/O can block execution"
            },
            "node.js": {
                "single_thread": "Single-threaded nature can limit CPU-intensive tasks",
                "callback_hell": "Deep callback nesting can impact performance"
            },
            "database": {
                "n_plus_one": "N+1 query problem in ORMs",
                "missing_indexes": "Lack of proper indexing",
                "connection_pool": "Inadequate connection pooling"
            }
        }
        
        # Check for technology-specific bottlenecks
        for tech in context.project_spec.technologies:
            tech_lower = tech.name.lower()
            
            for bottleneck_type, bottlenecks in tech_bottlenecks.items():
                if bottleneck_type in tech_lower:
                    for name, description in bottlenecks.items():
                        findings.append({
                            "title": f"Potential Bottleneck: {name.replace('_', ' ').title()}",
                            "description": description,
                            "relevance": 0.7,
                            "area": "bottleneck",
                            "technology": tech.name
                        })
                        
                        # Add mitigation recommendation
                        recommendations.append(
                            self._get_bottleneck_mitigation(bottleneck_type, name)
                        )
        
        # Architecture-based bottlenecks
        arch_bottlenecks = await self._check_architecture_bottlenecks(context)
        findings.extend(arch_bottlenecks["findings"])
        recommendations.extend(arch_bottlenecks["recommendations"])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _suggest_optimizations(self, context: AgentContext) -> Dict[str, Any]:
        """Suggest specific optimization strategies."""
        findings = []
        recommendations = []
        
        # Caching strategy
        caching_strategy = self._determine_caching_strategy(context)
        findings.append({
            "title": "Caching Strategy",
            "description": "Recommended caching approach for the project",
            "relevance": 0.9,
            "area": "optimization",
            "strategy": caching_strategy
        })
        
        for cache_type, techniques in caching_strategy.items():
            for technique in techniques:
                recommendations.append(f"Implement {technique}")
        
        # Database optimizations
        if self._uses_database(context):
            db_opts = await self._suggest_database_optimizations(context)
            findings.extend(db_opts["findings"])
            recommendations.extend(db_opts["recommendations"])
        
        # Frontend optimizations
        if context.project_spec.type == "web_application":
            frontend_opts = await self._suggest_frontend_optimizations(context)
            findings.extend(frontend_opts["findings"])
            recommendations.extend(frontend_opts["recommendations"])
        
        # API optimizations
        if context.project_spec.type == "api_service":
            api_opts = await self._suggest_api_optimizations(context)
            findings.extend(api_opts["findings"])
            recommendations.extend(api_opts["recommendations"])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_scalability(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze scalability requirements and strategies."""
        findings = []
        recommendations = []
        
        # Determine scalability needs
        scale_needs = self._assess_scalability_needs(context)
        
        findings.append({
            "title": "Scalability Assessment",
            "description": f"Project requires {scale_needs['level']} scalability",
            "relevance": 0.9,
            "area": "scalability",
            "approach": scale_needs["approach"]
        })
        
        # Recommend scalability patterns
        if scale_needs["level"] in ["high", "very high"]:
            pattern = self.scalability_patterns[scale_needs["approach"]]
            
            for technique in pattern["techniques"]:
                recommendations.append(f"Implement {technique} for scalability")
            
            if "tools" in pattern:
                recommendations.append(
                    f"Consider using {', '.join(pattern['tools'][:2])} for orchestration"
                )
        
        # State management for scalability
        if scale_needs["approach"] == "horizontal":
            findings.append({
                "title": "Stateless Design Required",
                "description": "Horizontal scaling requires stateless application design",
                "relevance": 0.8,
                "area": "architecture"
            })
            
            recommendations.extend([
                "Design application to be stateless",
                "Use external session storage (Redis/Database)",
                "Implement sticky sessions if needed"
            ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _recommend_monitoring(self, context: AgentContext) -> Dict[str, Any]:
        """Recommend performance monitoring solutions."""
        findings = []
        recommendations = []
        
        # Determine monitoring needs
        monitoring_tools = {
            "web_application": {
                "apm": ["New Relic", "DataDog", "AppDynamics"],
                "rum": ["Google Analytics", "Sentry", "LogRocket"],
                "synthetic": ["Pingdom", "UptimeRobot"]
            },
            "api_service": {
                "apm": ["New Relic", "DataDog", "Jaeger"],
                "metrics": ["Prometheus", "Grafana", "CloudWatch"],
                "logging": ["ELK Stack", "Splunk", "Fluentd"]
            },
            "data_pipeline": {
                "metrics": ["Prometheus", "CloudWatch", "DataDog"],
                "logging": ["ELK Stack", "CloudWatch Logs"],
                "tracing": ["AWS X-Ray", "Jaeger"]
            }
        }
        
        project_type = context.project_spec.type
        if project_type in monitoring_tools:
            tools = monitoring_tools[project_type]
            
            findings.append({
                "title": "Performance Monitoring Strategy",
                "description": "Recommended monitoring tools and approaches",
                "relevance": 0.8,
                "area": "monitoring",
                "categories": list(tools.keys())
            })
            
            for category, options in tools.items():
                recommendations.append(
                    f"Implement {category.upper()}: consider {', '.join(options[:2])}"
                )
        
        # Key metrics to monitor
        key_metrics = self._get_key_metrics(context)
        findings.append({
            "title": "Key Performance Metrics",
            "description": "Critical metrics to monitor",
            "relevance": 0.9,
            "metrics": key_metrics
        })
        
        recommendations.append(
            f"Set up monitoring for: {', '.join(key_metrics[:3])}"
        )
        recommendations.append("Establish performance baselines and alerts")
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    def _identify_performance_features(self, context: AgentContext) -> List[str]:
        """Identify features that require performance optimization."""
        perf_keywords = [
            "real-time", "streaming", "upload", "download",
            "search", "analytics", "dashboard", "report",
            "bulk", "batch", "concurrent", "parallel"
        ]
        
        perf_features = []
        for feature in context.project_spec.features:
            feature_lower = feature.name.lower()
            if any(keyword in feature_lower for keyword in perf_keywords):
                perf_features.append(feature.name)
        
        return perf_features
    
    def _get_bottleneck_mitigation(self, bottleneck_type: str, name: str) -> str:
        """Get mitigation strategy for a bottleneck."""
        mitigations = {
            ("python", "gil"): "Use multiprocessing or async I/O for parallelism",
            ("python", "sync_io"): "Implement async/await patterns with asyncio",
            ("node.js", "single_thread"): "Use worker threads or clustering for CPU tasks",
            ("node.js", "callback_hell"): "Refactor to use Promises or async/await",
            ("database", "n_plus_one"): "Use eager loading or query optimization",
            ("database", "missing_indexes"): "Analyze query patterns and add indexes",
            ("database", "connection_pool"): "Configure appropriate connection pool size"
        }
        
        return mitigations.get((bottleneck_type, name), f"Optimize {name}")
    
    def _determine_caching_strategy(self, context: AgentContext) -> Dict[str, List[str]]:
        """Determine appropriate caching strategy."""
        strategy = {}
        
        if context.project_spec.type == "web_application":
            strategy["browser"] = ["Cache-Control headers", "Service Workers"]
            strategy["cdn"] = ["Static asset caching via CDN"]
            strategy["application"] = ["Redis for session storage"]
        
        elif context.project_spec.type == "api_service":
            strategy["application"] = ["Redis for response caching"]
            strategy["database"] = ["Query result caching"]
        
        # Add technology-specific caching
        for tech in context.project_spec.technologies:
            if "react" in tech.name.lower():
                strategy.setdefault("frontend", []).append("React.memo for component caching")
            elif "django" in tech.name.lower():
                strategy.setdefault("application", []).append("Django cache framework")
        
        return strategy
    
    def _uses_database(self, context: AgentContext) -> bool:
        """Check if project uses a database."""
        db_indicators = ["database", "postgres", "mysql", "mongodb", "sqlite", "redis"]
        
        # Check technologies
        for tech in context.project_spec.technologies:
            if any(db in tech.name.lower() for db in db_indicators):
                return True
        
        # Check features
        for feature in context.project_spec.features:
            if "data" in feature.name.lower() or "database" in feature.name.lower():
                return True
        
        return False
    
    async def _suggest_database_optimizations(self, context: AgentContext) -> Dict[str, Any]:
        """Suggest database-specific optimizations."""
        findings = []
        recommendations = [
            "Implement database connection pooling",
            "Add indexes for frequently queried columns",
            "Use database query profiling",
            "Implement query result caching",
            "Consider read replicas for scaling",
            "Optimize database schema design"
        ]
        
        findings.append({
            "title": "Database Performance Optimization",
            "description": "Database usage detected, optimization needed",
            "relevance": 0.8,
            "area": "database"
        })
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _suggest_frontend_optimizations(self, context: AgentContext) -> Dict[str, Any]:
        """Suggest frontend-specific optimizations."""
        findings = []
        recommendations = [
            "Implement code splitting for faster initial load",
            "Use lazy loading for images and components",
            "Minify and compress JavaScript/CSS",
            "Implement browser caching strategies",
            "Optimize images (WebP, lazy loading)",
            "Use a CDN for static assets",
            "Implement Progressive Web App features"
        ]
        
        findings.append({
            "title": "Frontend Performance Optimization",
            "description": "Web application requires frontend optimization",
            "relevance": 0.9,
            "area": "frontend"
        })
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _suggest_api_optimizations(self, context: AgentContext) -> Dict[str, Any]:
        """Suggest API-specific optimizations."""
        findings = []
        recommendations = [
            "Implement response caching with appropriate TTL",
            "Use pagination for large data sets",
            "Implement rate limiting to prevent abuse",
            "Use compression for API responses",
            "Implement request/response validation",
            "Use async processing for long-running operations",
            "Implement API versioning for compatibility"
        ]
        
        findings.append({
            "title": "API Performance Optimization",
            "description": "API service requires performance optimization",
            "relevance": 0.9,
            "area": "api"
        })
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _check_architecture_bottlenecks(self, context: AgentContext) -> Dict[str, Any]:
        """Check for architecture-related bottlenecks."""
        findings = []
        recommendations = []
        
        # Check for monolithic architecture issues
        if len(context.project_spec.features) > 10:
            findings.append({
                "title": "Monolithic Architecture Concerns",
                "description": "Large feature set may benefit from modular architecture",
                "relevance": 0.7,
                "area": "architecture"
            })
            
            recommendations.append("Consider microservices for independent scaling")
            recommendations.append("Implement modular architecture patterns")
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    def _assess_scalability_needs(self, context: AgentContext) -> Dict[str, Any]:
        """Assess scalability requirements."""
        # Simple heuristic based on project type and features
        high_scale_indicators = [
            "real-time", "streaming", "analytics",
            "multi-tenant", "saas", "platform"
        ]
        
        project_text = (
            context.project_spec.description.lower() +
            " ".join(f.name.lower() for f in context.project_spec.features)
        )
        
        indicator_count = sum(
            1 for indicator in high_scale_indicators
            if indicator in project_text
        )
        
        if indicator_count >= 3:
            return {"level": "very high", "approach": "horizontal"}
        elif indicator_count >= 1:
            return {"level": "high", "approach": "horizontal"}
        elif context.project_spec.type in ["api_service", "web_application"]:
            return {"level": "medium", "approach": "horizontal"}
        else:
            return {"level": "low", "approach": "vertical"}
    
    def _get_key_metrics(self, context: AgentContext) -> List[str]:
        """Get key metrics to monitor for the project."""
        base_metrics = ["Response Time", "Error Rate", "Throughput"]
        
        if context.project_spec.type == "web_application":
            base_metrics.extend(["Page Load Time", "User Sessions", "Bounce Rate"])
        elif context.project_spec.type == "api_service":
            base_metrics.extend(["API Latency", "Request Rate", "Success Rate"])
        elif context.project_spec.type == "data_pipeline":
            base_metrics.extend(["Processing Time", "Queue Length", "Data Throughput"])
        
        return base_metrics
    
    def _calculate_confidence(self, context: AgentContext, findings: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for performance analysis."""
        base_confidence = 0.75
        
        # Increase confidence based on project type familiarity
        if context.project_spec.type in ["web_application", "api_service"]:
            base_confidence += 0.1
        
        # Adjust based on technology familiarity
        known_tech_count = sum(
            1 for tech in context.project_spec.technologies
            if tech.name.lower() in ["python", "node.js", "react", "django", "fastapi"]
        )
        
        if known_tech_count > 0:
            base_confidence += 0.05 * min(known_tech_count, 3)
        
        return min(base_confidence, 0.95)
    
    def get_expertise_areas(self) -> List[str]:
        """Get Performance Engineer's areas of expertise."""
        return [
            "Performance Optimization",
            "Scalability Architecture",
            "Caching Strategies",
            "Database Optimization",
            "Frontend Performance",
            "API Performance",
            "Load Testing",
            "Performance Monitoring",
            "Bottleneck Analysis",
            "Resource Optimization"
        ]
    
    def get_research_methods(self) -> List[str]:
        """Get research methods used by Performance Engineer."""
        return [
            "Performance Profiling",
            "Bottleneck Analysis",
            "Load Testing Simulation",
            "Scalability Assessment",
            "Architecture Review",
            "Metric Analysis",
            "Optimization Planning",
            "Monitoring Strategy"
        ]