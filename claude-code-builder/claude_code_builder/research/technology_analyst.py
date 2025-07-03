"""Technology Analyst research agent."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseResearchAgent, AgentCapability, AgentContext, AgentResponse
from ..models.research import ResearchSource
from ..models.project import Technology

logger = logging.getLogger(__name__)


class TechnologyAnalyst(BaseResearchAgent):
    """Analyzes technology stacks and makes recommendations."""
    
    def __init__(self):
        """Initialize Technology Analyst agent."""
        super().__init__(
            name="Technology Analyst",
            capabilities=[
                AgentCapability.ANALYSIS,
                AgentCapability.RECOMMENDATION,
                AgentCapability.ARCHITECTURE,
                AgentCapability.IMPLEMENTATION
            ]
        )
        
        # Technology knowledge base
        self.tech_ecosystems = {
            "javascript": {
                "frameworks": ["React", "Vue", "Angular", "Next.js", "Nuxt", "Svelte"],
                "runtime": ["Node.js", "Deno", "Bun"],
                "build_tools": ["Webpack", "Vite", "Parcel", "Rollup", "esbuild"],
                "testing": ["Jest", "Vitest", "Cypress", "Playwright"],
                "state_management": ["Redux", "MobX", "Zustand", "Pinia"],
                "styling": ["CSS Modules", "Styled Components", "Emotion", "Tailwind CSS"]
            },
            "python": {
                "frameworks": ["Django", "FastAPI", "Flask", "Pyramid"],
                "async": ["asyncio", "aiohttp", "Tornado"],
                "testing": ["pytest", "unittest", "nose2"],
                "data": ["pandas", "NumPy", "Polars"],
                "ml": ["scikit-learn", "TensorFlow", "PyTorch"],
                "orm": ["SQLAlchemy", "Django ORM", "Tortoise ORM"]
            },
            "rust": {
                "frameworks": ["Actix", "Rocket", "Axum", "Warp"],
                "async": ["Tokio", "async-std"],
                "testing": ["built-in", "mockall", "proptest"],
                "serialization": ["serde", "bincode"],
                "cli": ["clap", "structopt"]
            },
            "go": {
                "frameworks": ["Gin", "Echo", "Fiber", "Chi"],
                "testing": ["testing", "testify", "ginkgo"],
                "orm": ["GORM", "sqlx"],
                "logging": ["logrus", "zap", "zerolog"]
            }
        }
        
        self.compatibility_matrix = {
            ("React", "Next.js"): 1.0,
            ("Vue", "Nuxt"): 1.0,
            ("FastAPI", "SQLAlchemy"): 0.9,
            ("Django", "PostgreSQL"): 0.95,
            ("Node.js", "Express"): 0.9,
            ("TypeScript", "React"): 0.95,
            ("GraphQL", "Apollo"): 0.9,
            ("Docker", "Kubernetes"): 0.85,
            ("Redis", "Node.js"): 0.9,
            ("Elasticsearch", "Python"): 0.85
        }
    
    async def _initialize(self) -> None:
        """Initialize the Technology Analyst."""
        logger.info("Technology Analyst initialized with comprehensive tech knowledge base")
    
    async def _perform_research(self, context: AgentContext) -> AgentResponse:
        """Perform technology analysis research."""
        findings = []
        recommendations = []
        
        # Analyze current technology stack
        tech_analysis = await self._analyze_technology_stack(context)
        findings.extend(tech_analysis["findings"])
        recommendations.extend(tech_analysis["recommendations"])
        
        # Check for compatibility issues
        compatibility = await self._check_compatibility(context)
        findings.extend(compatibility["findings"])
        recommendations.extend(compatibility["recommendations"])
        
        # Suggest technology improvements
        improvements = await self._suggest_improvements(context)
        findings.extend(improvements["findings"])
        recommendations.extend(improvements["recommendations"])
        
        # Analyze technology trends
        trends = await self._analyze_trends(context)
        findings.extend(trends["findings"])
        
        # Calculate confidence based on technology match
        confidence = self._calculate_confidence(context, findings)
        
        return AgentResponse(
            agent_name=self.name,
            findings=findings,
            recommendations=self.prioritize_recommendations(recommendations, context),
            confidence=confidence,
            sources_used=[ResearchSource.DOCUMENTATION, ResearchSource.COMMUNITY],
            metadata={
                "technologies_analyzed": len(context.project_spec.technologies),
                "compatibility_score": compatibility.get("overall_score", 0.0)
            }
        )
    
    async def _analyze_technology_stack(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze the project's technology stack."""
        findings = []
        recommendations = []
        
        # Analyze each technology
        for tech in context.project_spec.technologies:
            # Check if technology is in our knowledge base
            ecosystem = self._get_ecosystem(tech.name)
            
            if ecosystem:
                finding = {
                    "title": f"{tech.name} Technology Analysis",
                    "description": f"{tech.name} is part of the {ecosystem} ecosystem",
                    "relevance": 0.9,
                    "details": {
                        "version": tech.version,
                        "ecosystem": ecosystem,
                        "maturity": self._assess_maturity(tech)
                    }
                }
                findings.append(finding)
                
                # Check for missing complementary technologies
                missing = self._find_missing_complements(tech, context)
                if missing:
                    recommendations.append(
                        f"Consider adding {', '.join(missing)} to complement {tech.name}"
                    )
            
            # Version-specific recommendations
            if tech.version:
                version_rec = self._check_version(tech)
                if version_rec:
                    recommendations.append(version_rec)
        
        # Check for technology gaps
        gaps = self._identify_technology_gaps(context)
        for gap in gaps:
            findings.append({
                "title": f"Technology Gap: {gap['area']}",
                "description": gap["description"],
                "relevance": gap["importance"],
                "source": "Technology Analysis"
            })
            recommendations.append(gap["recommendation"])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _check_compatibility(self, context: AgentContext) -> Dict[str, Any]:
        """Check compatibility between technologies."""
        findings = []
        recommendations = []
        overall_score = 1.0
        
        tech_names = [t.name for t in context.project_spec.technologies]
        
        # Check pairwise compatibility
        for i, tech1 in enumerate(tech_names):
            for tech2 in tech_names[i+1:]:
                score = self._get_compatibility_score(tech1, tech2)
                
                if score < 0.7:  # Poor compatibility
                    findings.append({
                        "title": f"Compatibility Issue: {tech1} and {tech2}",
                        "description": f"Low compatibility score ({score:.2f}) between {tech1} and {tech2}",
                        "relevance": 0.8,
                        "severity": "high" if score < 0.5 else "medium"
                    })
                    recommendations.append(
                        f"Consider alternatives or additional integration layers between {tech1} and {tech2}"
                    )
                
                overall_score *= score
        
        # Overall compatibility assessment
        findings.append({
            "title": "Overall Technology Compatibility",
            "description": f"Technology stack compatibility score: {overall_score:.2f}",
            "relevance": 0.9,
            "score": overall_score
        })
        
        if overall_score < 0.7:
            recommendations.append(
                "Consider reviewing technology choices for better integration"
            )
        
        return {
            "findings": findings,
            "recommendations": recommendations,
            "overall_score": overall_score
        }
    
    async def _suggest_improvements(self, context: AgentContext) -> Dict[str, Any]:
        """Suggest technology improvements."""
        findings = []
        recommendations = []
        
        project_type = context.project_spec.type
        current_tech = {t.name.lower() for t in context.project_spec.technologies}
        
        # Type-specific technology recommendations
        type_recommendations = {
            "web_application": {
                "frontend": ["React", "Vue", "Angular"],
                "backend": ["Node.js", "Python", "Go"],
                "database": ["PostgreSQL", "MongoDB", "Redis"],
                "deployment": ["Docker", "Kubernetes"],
                "monitoring": ["Prometheus", "Grafana"],
                "testing": ["Jest", "Cypress", "Playwright"]
            },
            "api_service": {
                "framework": ["FastAPI", "Express", "Gin"],
                "database": ["PostgreSQL", "MongoDB"],
                "caching": ["Redis", "Memcached"],
                "documentation": ["OpenAPI", "Swagger"],
                "monitoring": ["Prometheus", "DataDog"],
                "testing": ["pytest", "Jest", "Postman"]
            },
            "cli_tool": {
                "language": ["Go", "Rust", "Python"],
                "framework": ["Cobra", "Click", "clap"],
                "testing": ["pytest", "cargo test"],
                "distribution": ["Homebrew", "snap", "pip"]
            }
        }
        
        if project_type in type_recommendations:
            for category, options in type_recommendations[project_type].items():
                # Check if category is covered
                covered = any(opt.lower() in current_tech for opt in options)
                
                if not covered:
                    findings.append({
                        "title": f"Missing {category.title()} Technology",
                        "description": f"No {category} technology detected in stack",
                        "relevance": 0.7,
                        "category": category
                    })
                    
                    recommendations.append(
                        f"Add {category} technology: consider {', '.join(options[:3])}"
                    )
        
        # Performance optimizations
        if "performance" in context.query.query.lower():
            perf_recommendations = self._get_performance_recommendations(context)
            recommendations.extend(perf_recommendations)
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_trends(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze technology trends relevant to the project."""
        findings = []
        
        # Simulated trend data (in real implementation, would fetch from external sources)
        trends = {
            "javascript": {
                "rising": ["Vite", "Bun", "Astro", "SolidJS"],
                "stable": ["React", "Vue", "Node.js"],
                "declining": ["Webpack", "jQuery"]
            },
            "python": {
                "rising": ["FastAPI", "Pydantic", "Poetry"],
                "stable": ["Django", "Flask", "pytest"],
                "declining": ["Python 2.x"]
            }
        }
        
        for tech in context.project_spec.technologies:
            ecosystem = self._get_ecosystem(tech.name)
            if ecosystem in trends:
                trend_data = trends[ecosystem]
                
                tech_lower = tech.name.lower()
                if any(t.lower() == tech_lower for t in trend_data["rising"]):
                    status = "rising"
                elif any(t.lower() == tech_lower for t in trend_data["declining"]):
                    status = "declining"
                else:
                    status = "stable"
                
                findings.append({
                    "title": f"{tech.name} Trend Analysis",
                    "description": f"{tech.name} is currently {status} in popularity",
                    "relevance": 0.6,
                    "trend": status,
                    "source": "Technology Trends"
                })
        
        return {"findings": findings}
    
    def _get_ecosystem(self, tech_name: str) -> Optional[str]:
        """Get the ecosystem a technology belongs to."""
        tech_lower = tech_name.lower()
        
        for ecosystem, data in self.tech_ecosystems.items():
            for category in data.values():
                if any(t.lower() == tech_lower for t in category):
                    return ecosystem
        
        # Check by common patterns
        if "js" in tech_lower or "javascript" in tech_lower:
            return "javascript"
        elif "py" in tech_lower or "python" in tech_lower:
            return "python"
        elif "rust" in tech_lower:
            return "rust"
        elif "go" in tech_lower:
            return "go"
        
        return None
    
    def _assess_maturity(self, tech: Technology) -> str:
        """Assess technology maturity."""
        # Simple maturity assessment based on version
        if not tech.version:
            return "unknown"
        
        try:
            major_version = int(tech.version.split(".")[0])
            if major_version == 0:
                return "experimental"
            elif major_version < 2:
                return "emerging"
            elif major_version < 5:
                return "stable"
            else:
                return "mature"
        except:
            return "unknown"
    
    def _find_missing_complements(self, tech: Technology, context: AgentContext) -> List[str]:
        """Find missing complementary technologies."""
        missing = []
        current_tech = {t.name.lower() for t in context.project_spec.technologies}
        
        complements = {
            "react": ["Redux", "React Router", "styled-components"],
            "vue": ["Vuex", "Vue Router", "Pinia"],
            "django": ["Django REST Framework", "Celery"],
            "fastapi": ["SQLAlchemy", "Alembic", "Pydantic"],
            "express": ["Passport.js", "Mongoose", "Socket.io"]
        }
        
        tech_lower = tech.name.lower()
        if tech_lower in complements:
            for comp in complements[tech_lower]:
                if comp.lower() not in current_tech:
                    missing.append(comp)
        
        return missing[:2]  # Return top 2 missing
    
    def _check_version(self, tech: Technology) -> Optional[str]:
        """Check technology version and recommend updates."""
        if not tech.version:
            return f"Specify version for {tech.name} to ensure consistency"
        
        # Simulated version checks
        latest_versions = {
            "react": "18.2.0",
            "vue": "3.3.0",
            "angular": "17.0.0",
            "node.js": "20.10.0",
            "python": "3.12.0",
            "django": "5.0.0",
            "fastapi": "0.104.0"
        }
        
        tech_lower = tech.name.lower()
        if tech_lower in latest_versions:
            latest = latest_versions[tech_lower]
            if tech.version < latest:
                return f"Update {tech.name} from {tech.version} to {latest} for latest features and security fixes"
        
        return None
    
    def _identify_technology_gaps(self, context: AgentContext) -> List[Dict[str, Any]]:
        """Identify gaps in technology stack."""
        gaps = []
        current_tech = {t.name.lower() for t in context.project_spec.technologies}
        
        # Essential categories by project type
        essential = {
            "web_application": {
                "testing": 0.9,
                "monitoring": 0.8,
                "caching": 0.7,
                "security": 0.9
            },
            "api_service": {
                "documentation": 0.9,
                "testing": 0.9,
                "monitoring": 0.8,
                "rate_limiting": 0.7
            }
        }
        
        if context.project_spec.type in essential:
            for area, importance in essential[context.project_spec.type].items():
                # Check if area is covered
                if not self._is_area_covered(area, current_tech):
                    gaps.append({
                        "area": area,
                        "description": f"No {area} solution detected in technology stack",
                        "importance": importance,
                        "recommendation": f"Implement {area} using appropriate tools"
                    })
        
        return gaps
    
    def _is_area_covered(self, area: str, current_tech: Set[str]) -> bool:
        """Check if a technology area is covered."""
        area_keywords = {
            "testing": ["test", "jest", "pytest", "cypress", "playwright"],
            "monitoring": ["prometheus", "grafana", "datadog", "newrelic"],
            "caching": ["redis", "memcached", "cache"],
            "security": ["auth", "jwt", "oauth", "security"],
            "documentation": ["swagger", "openapi", "redoc"]
        }
        
        keywords = area_keywords.get(area, [])
        return any(any(kw in tech for kw in keywords) for tech in current_tech)
    
    def _get_compatibility_score(self, tech1: str, tech2: str) -> float:
        """Get compatibility score between two technologies."""
        # Check direct compatibility
        pair = (tech1, tech2)
        reverse_pair = (tech2, tech1)
        
        if pair in self.compatibility_matrix:
            return self.compatibility_matrix[pair]
        elif reverse_pair in self.compatibility_matrix:
            return self.compatibility_matrix[reverse_pair]
        
        # Check ecosystem compatibility
        eco1 = self._get_ecosystem(tech1)
        eco2 = self._get_ecosystem(tech2)
        
        if eco1 and eco2:
            if eco1 == eco2:
                return 0.9  # Same ecosystem, likely compatible
            else:
                # Different ecosystems, check common pairings
                if {eco1, eco2} in [{"javascript", "python"}, {"python", "go"}]:
                    return 0.7
                else:
                    return 0.5
        
        return 0.6  # Default neutral score
    
    def _get_performance_recommendations(self, context: AgentContext) -> List[str]:
        """Get performance-related recommendations."""
        recs = []
        current_tech = {t.name.lower() for t in context.project_spec.technologies}
        
        # Check for performance tools
        if not any("cache" in t or "redis" in t for t in current_tech):
            recs.append("Implement caching with Redis or Memcached for better performance")
        
        if not any("cdn" in t for t in current_tech) and context.project_spec.type == "web_application":
            recs.append("Use a CDN for static assets to improve load times")
        
        # Language-specific performance tips
        for tech in context.project_spec.technologies:
            if "python" in tech.name.lower():
                recs.append("Consider using asyncio or multiprocessing for CPU-intensive tasks")
            elif "node" in tech.name.lower():
                recs.append("Use worker threads or clustering for better CPU utilization")
        
        return recs
    
    def _calculate_confidence(self, context: AgentContext, findings: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for the analysis."""
        base_confidence = 0.7
        
        # Increase confidence based on technology coverage
        tech_count = len(context.project_spec.technologies)
        if tech_count > 0:
            known_tech = sum(1 for t in context.project_spec.technologies if self._get_ecosystem(t.name))
            coverage = known_tech / tech_count
            base_confidence += 0.2 * coverage
        
        # Adjust based on findings quality
        if findings:
            avg_relevance = sum(f.get("relevance", 0.5) for f in findings) / len(findings)
            base_confidence += 0.1 * avg_relevance
        
        return min(base_confidence, 0.95)
    
    def get_expertise_areas(self) -> List[str]:
        """Get Technology Analyst's areas of expertise."""
        return [
            "Technology Stack Analysis",
            "Framework Selection",
            "Technology Compatibility",
            "Performance Optimization",
            "Architecture Design",
            "Technology Trends",
            "Tool Recommendations",
            "Version Management",
            "Ecosystem Analysis",
            "Integration Strategies"
        ]
    
    def get_research_methods(self) -> List[str]:
        """Get research methods used by Technology Analyst."""
        return [
            "Technology Stack Analysis",
            "Compatibility Matrix Evaluation",
            "Trend Analysis",
            "Performance Benchmarking",
            "Ecosystem Mapping",
            "Version Comparison",
            "Gap Analysis",
            "Best Practices Review"
        ]