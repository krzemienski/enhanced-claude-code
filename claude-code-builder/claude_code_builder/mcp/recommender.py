"""Intelligent MCP server recommendations based on project context."""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models.base import BaseModel
from ..models.project import ProjectSpec, Technology
from .discovery import MCPServer
from .analyzer import ComplexityAssessment, ServerComplexity

logger = logging.getLogger(__name__)


class RecommendationPriority(Enum):
    """Priority levels for recommendations."""
    CRITICAL = "critical"  # Essential for project
    HIGH = "high"  # Strongly recommended
    MEDIUM = "medium"  # Would be beneficial
    LOW = "low"  # Nice to have
    OPTIONAL = "optional"  # Consider if needed


@dataclass
class ServerRecommendation:
    """MCP server recommendation."""
    server: MCPServer
    priority: RecommendationPriority
    reasoning: List[str]
    benefits: List[str]
    alternatives: List[str]
    configuration_tips: List[str]
    score: float  # 0-1 relevance score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "server": self.server.to_dict(),
            "priority": self.priority.value,
            "reasoning": self.reasoning,
            "benefits": self.benefits,
            "alternatives": self.alternatives,
            "configuration_tips": self.configuration_tips,
            "score": self.score
        }


class MCPRecommender:
    """Provides intelligent MCP server recommendations."""
    
    # Project type to server mappings
    PROJECT_SERVER_MAP = {
        "web_application": {
            "critical": ["filesystem"],
            "high": ["github", "puppeteer"],
            "medium": ["postgres", "memory"],
            "low": ["search"]
        },
        "api_service": {
            "critical": ["filesystem"],
            "high": ["postgres", "github"],
            "medium": ["memory"],
            "low": ["search"]
        },
        "cli_tool": {
            "critical": ["filesystem"],
            "high": ["github"],
            "medium": [],
            "low": ["memory"]
        },
        "data_pipeline": {
            "critical": ["filesystem", "postgres"],
            "high": ["memory"],
            "medium": ["github"],
            "low": ["search"]
        },
        "automation": {
            "critical": ["filesystem", "puppeteer"],
            "high": ["github"],
            "medium": ["memory"],
            "low": ["postgres"]
        },
        "documentation": {
            "critical": ["filesystem"],
            "high": ["github", "search"],
            "medium": [],
            "low": ["memory"]
        }
    }
    
    # Technology to server mappings
    TECH_SERVER_MAP = {
        "react": ["puppeteer", "filesystem"],
        "vue": ["puppeteer", "filesystem"],
        "angular": ["puppeteer", "filesystem"],
        "node": ["filesystem", "postgres"],
        "python": ["filesystem", "postgres"],
        "postgresql": ["postgres"],
        "mongodb": ["memory"],
        "docker": ["filesystem", "github"],
        "kubernetes": ["filesystem", "github"],
        "git": ["github"],
        "typescript": ["filesystem"],
        "javascript": ["filesystem", "puppeteer"]
    }
    
    # Feature to server mappings
    FEATURE_SERVER_MAP = {
        "authentication": ["postgres", "memory"],
        "database": ["postgres"],
        "file_upload": ["filesystem"],
        "web_scraping": ["puppeteer"],
        "search": ["search", "postgres"],
        "caching": ["memory"],
        "testing": ["puppeteer", "filesystem"],
        "deployment": ["github", "filesystem"],
        "monitoring": ["memory", "postgres"],
        "api": ["postgres", "memory"]
    }
    
    def __init__(self):
        """Initialize recommender."""
        self.recommendations_cache: Dict[str, List[ServerRecommendation]] = {}
    
    async def recommend_servers(
        self,
        project_spec: ProjectSpec,
        available_servers: List[MCPServer],
        assessments: Optional[Dict[str, ComplexityAssessment]] = None
    ) -> List[ServerRecommendation]:
        """
        Recommend MCP servers for a project.
        
        Args:
            project_spec: Project specification
            available_servers: Available MCP servers
            assessments: Complexity assessments if available
            
        Returns:
            List of server recommendations
        """
        logger.info(f"Generating MCP recommendations for {project_spec.name}")
        
        # Calculate scores for each server
        server_scores: Dict[str, Tuple[float, List[str], List[str]]] = {}
        
        for server in available_servers:
            score, reasoning, benefits = await self._calculate_server_score(
                server, project_spec
            )
            server_scores[server.name] = (score, reasoning, benefits)
        
        # Generate recommendations
        recommendations = []
        
        for server in available_servers:
            score, reasoning, benefits = server_scores[server.name]
            
            if score > 0.2:  # Minimum threshold
                priority = self._determine_priority(server, project_spec, score)
                alternatives = self._find_alternatives(server, available_servers)
                config_tips = self._generate_config_tips(server, project_spec)
                
                recommendation = ServerRecommendation(
                    server=server,
                    priority=priority,
                    reasoning=reasoning,
                    benefits=benefits,
                    alternatives=alternatives,
                    configuration_tips=config_tips,
                    score=score
                )
                
                recommendations.append(recommendation)
        
        # Sort by score and priority
        recommendations.sort(
            key=lambda r: (
                -list(RecommendationPriority).index(r.priority),
                -r.score
            )
        )
        
        # Cache recommendations
        cache_key = f"{project_spec.name}:{project_spec.type}"
        self.recommendations_cache[cache_key] = recommendations
        
        return recommendations
    
    async def _calculate_server_score(
        self,
        server: MCPServer,
        project_spec: ProjectSpec
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate relevance score for a server.
        
        Returns:
            Tuple of (score, reasoning, benefits)
        """
        score = 0.0
        reasoning = []
        benefits = []
        
        server_type = self._extract_server_type(server.name)
        if not server_type:
            return score, reasoning, benefits
        
        # Check project type match
        if project_spec.type in self.PROJECT_SERVER_MAP:
            type_servers = self.PROJECT_SERVER_MAP[project_spec.type]
            
            if server_type in type_servers.get("critical", []):
                score += 0.5
                reasoning.append(f"Critical for {project_spec.type} projects")
                benefits.append("Essential functionality for project type")
            elif server_type in type_servers.get("high", []):
                score += 0.3
                reasoning.append(f"Highly recommended for {project_spec.type}")
                benefits.append("Significant value for project goals")
            elif server_type in type_servers.get("medium", []):
                score += 0.2
                reasoning.append(f"Useful for {project_spec.type} projects")
                benefits.append("Enhances project capabilities")
            elif server_type in type_servers.get("low", []):
                score += 0.1
                reasoning.append(f"Optional for {project_spec.type}")
                benefits.append("Additional functionality if needed")
        
        # Check technology match
        tech_matches = 0
        for tech in project_spec.technologies:
            tech_name = tech.name.lower()
            if tech_name in self.TECH_SERVER_MAP:
                if server_type in self.TECH_SERVER_MAP[tech_name]:
                    tech_matches += 1
                    reasoning.append(f"Complements {tech.name} technology")
        
        if tech_matches > 0:
            score += 0.2 * min(tech_matches / 3, 1.0)  # Cap at 0.2
            benefits.append(f"Integrates well with {tech_matches} project technologies")
        
        # Check feature match
        feature_matches = 0
        for feature in project_spec.features:
            feature_key = feature.name.lower().replace(" ", "_")
            if feature_key in self.FEATURE_SERVER_MAP:
                if server_type in self.FEATURE_SERVER_MAP[feature_key]:
                    feature_matches += 1
                    reasoning.append(f"Supports {feature.name} feature")
                    benefits.append(f"Enables {feature.name} implementation")
        
        if feature_matches > 0:
            score += 0.3 * min(feature_matches / 2, 1.0)  # Cap at 0.3
        
        # Specific server benefits
        server_benefits = {
            "filesystem": [
                "File and directory management",
                "Code generation support",
                "Template processing"
            ],
            "github": [
                "Version control integration",
                "Issue and PR management",
                "CI/CD workflow support"
            ],
            "postgres": [
                "Relational database operations",
                "Complex query support",
                "Data persistence"
            ],
            "puppeteer": [
                "Browser automation",
                "E2E testing capabilities",
                "Web scraping support"
            ],
            "memory": [
                "Fast data caching",
                "Session management",
                "Temporary storage"
            ],
            "search": [
                "Full-text search",
                "Content indexing",
                "Advanced querying"
            ]
        }
        
        if server_type in server_benefits:
            benefits.extend(server_benefits[server_type])
        
        # Bonus for installed servers
        if server.installed:
            score += 0.05
            reasoning.append("Already installed")
        
        return min(score, 1.0), reasoning, benefits
    
    def _determine_priority(
        self,
        server: MCPServer,
        project_spec: ProjectSpec,
        score: float
    ) -> RecommendationPriority:
        """Determine recommendation priority."""
        server_type = self._extract_server_type(server.name)
        
        # Check if critical for project type
        if project_spec.type in self.PROJECT_SERVER_MAP:
            type_servers = self.PROJECT_SERVER_MAP[project_spec.type]
            if server_type in type_servers.get("critical", []):
                return RecommendationPriority.CRITICAL
        
        # Score-based priority
        if score >= 0.7:
            return RecommendationPriority.HIGH
        elif score >= 0.5:
            return RecommendationPriority.MEDIUM
        elif score >= 0.3:
            return RecommendationPriority.LOW
        else:
            return RecommendationPriority.OPTIONAL
    
    def _find_alternatives(
        self,
        server: MCPServer,
        available_servers: List[MCPServer]
    ) -> List[str]:
        """Find alternative servers."""
        alternatives = []
        server_type = self._extract_server_type(server.name)
        
        # Define alternatives
        alternative_map = {
            "postgres": ["mysql", "sqlite", "mongodb"],
            "puppeteer": ["playwright", "selenium"],
            "github": ["gitlab", "bitbucket"],
            "memory": ["redis", "memcached"]
        }
        
        if server_type in alternative_map:
            for alt in alternative_map[server_type]:
                # Check if alternative is available
                alt_servers = [
                    s for s in available_servers
                    if alt in s.name.lower() and s.name != server.name
                ]
                if alt_servers:
                    alternatives.extend([s.name for s in alt_servers])
        
        return alternatives[:3]  # Limit to 3 alternatives
    
    def _generate_config_tips(
        self,
        server: MCPServer,
        project_spec: ProjectSpec
    ) -> List[str]:
        """Generate configuration tips."""
        tips = []
        server_type = self._extract_server_type(server.name)
        
        # General tips
        tips.append("Review server documentation for latest configuration options")
        
        # Server-specific tips
        if server_type == "filesystem":
            tips.append("Configure allowed paths to restrict file access")
            tips.append("Set appropriate read/write permissions")
            if project_spec.type == "web_application":
                tips.append("Consider limiting access to public directories only")
        
        elif server_type == "github":
            tips.append("Use fine-grained personal access tokens")
            tips.append("Limit token scope to required permissions only")
            if "deployment" in [f.name.lower() for f in project_spec.features]:
                tips.append("Include workflow and actions permissions for CI/CD")
        
        elif server_type == "postgres":
            tips.append("Use connection pooling for better performance")
            tips.append("Configure SSL for production environments")
            tips.append("Create read-only user for query operations")
            if project_spec.metadata.get("multi_tenant"):
                tips.append("Implement row-level security for multi-tenancy")
        
        elif server_type == "puppeteer":
            tips.append("Use headless mode for better performance")
            tips.append("Configure appropriate viewport sizes")
            tips.append("Set memory limits to prevent resource exhaustion")
            if "testing" in [f.name.lower() for f in project_spec.features]:
                tips.append("Enable video recording for test debugging")
        
        elif server_type == "memory":
            tips.append("Set appropriate memory limits")
            tips.append("Configure persistence options if needed")
            tips.append("Implement cache expiration policies")
        
        elif server_type == "search":
            tips.append("Configure search indexing strategies")
            tips.append("Set up search result ranking rules")
            tips.append("Implement search query validation")
        
        return tips
    
    def _extract_server_type(self, server_name: str) -> Optional[str]:
        """Extract server type from name."""
        known_types = ["filesystem", "github", "postgres", "puppeteer", "memory", "search"]
        
        for known_type in known_types:
            if known_type in server_name.lower():
                return known_type
        
        return None
    
    def get_minimal_setup(
        self,
        recommendations: List[ServerRecommendation]
    ) -> List[ServerRecommendation]:
        """
        Get minimal server setup.
        
        Args:
            recommendations: All recommendations
            
        Returns:
            Minimal set of servers
        """
        minimal = []
        
        # Include all critical servers
        critical = [r for r in recommendations if r.priority == RecommendationPriority.CRITICAL]
        minimal.extend(critical)
        
        # Add highest scored high-priority server if no critical servers
        if not minimal:
            high_priority = [r for r in recommendations if r.priority == RecommendationPriority.HIGH]
            if high_priority:
                minimal.append(high_priority[0])
        
        # Always include filesystem if available and not already included
        if not any("filesystem" in r.server.name.lower() for r in minimal):
            filesystem_recs = [r for r in recommendations if "filesystem" in r.server.name.lower()]
            if filesystem_recs:
                minimal.append(filesystem_recs[0])
        
        return minimal
    
    def generate_setup_plan(
        self,
        recommendations: List[ServerRecommendation],
        assessments: Optional[Dict[str, ComplexityAssessment]] = None
    ) -> Dict[str, Any]:
        """
        Generate a setup plan for recommended servers.
        
        Args:
            recommendations: Server recommendations
            assessments: Complexity assessments
            
        Returns:
            Setup plan with phases and time estimates
        """
        phases = {
            "immediate": [],
            "short_term": [],
            "long_term": []
        }
        
        total_setup_time = 0
        
        for rec in recommendations:
            assessment = assessments.get(rec.server.name) if assessments else None
            setup_time = assessment.estimated_setup_time if assessment else 10
            
            server_info = {
                "server": rec.server.name,
                "priority": rec.priority.value,
                "setup_time": setup_time,
                "installed": rec.server.installed
            }
            
            # Assign to phase based on priority and complexity
            if rec.priority == RecommendationPriority.CRITICAL:
                phases["immediate"].append(server_info)
            elif rec.priority in (RecommendationPriority.HIGH, RecommendationPriority.MEDIUM):
                if assessment and assessment.complexity in (ServerComplexity.SIMPLE, ServerComplexity.MODERATE):
                    phases["short_term"].append(server_info)
                else:
                    phases["long_term"].append(server_info)
            else:
                phases["long_term"].append(server_info)
            
            if not rec.server.installed:
                total_setup_time += setup_time
        
        return {
            "phases": phases,
            "total_setup_time": total_setup_time,
            "immediate_count": len(phases["immediate"]),
            "total_servers": len(recommendations),
            "already_installed": sum(1 for r in recommendations if r.server.installed)
        }