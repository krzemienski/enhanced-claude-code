"""MCP server complexity assessment and analysis."""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..models.base import BaseModel
from ..exceptions.base import ClaudeCodeBuilderError
from .discovery import MCPServer

logger = logging.getLogger(__name__)


class ServerComplexity(Enum):
    """MCP server complexity levels."""
    SIMPLE = "simple"  # Basic operations, no configuration
    MODERATE = "moderate"  # Some configuration needed
    COMPLEX = "complex"  # Significant configuration required
    ADVANCED = "advanced"  # Expert-level configuration


class ConfigurationRequirement(Enum):
    """Types of configuration requirements."""
    NONE = "none"
    API_KEY = "api_key"
    CONNECTION_STRING = "connection_string"
    CREDENTIALS = "credentials"
    ENVIRONMENT = "environment"
    CUSTOM_CONFIG = "custom_config"


@dataclass
class ComplexityAssessment:
    """Assessment of MCP server complexity."""
    server_name: str
    complexity: ServerComplexity
    configuration_requirements: List[ConfigurationRequirement]
    estimated_setup_time: int  # minutes
    required_expertise: List[str]
    potential_issues: List[str]
    recommendations: List[str]
    compatibility_score: float  # 0-1
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize assessment attributes."""
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "server_name": self.server_name,
            "complexity": self.complexity.value,
            "configuration_requirements": [r.value for r in self.configuration_requirements],
            "estimated_setup_time": self.estimated_setup_time,
            "required_expertise": self.required_expertise,
            "potential_issues": self.potential_issues,
            "recommendations": self.recommendations,
            "compatibility_score": self.compatibility_score,
            "metadata": self.metadata
        }


class MCPAnalyzer:
    """Analyzes MCP server complexity and requirements."""
    
    # Server complexity mappings
    COMPLEXITY_MAP = {
        "filesystem": {
            "complexity": ServerComplexity.SIMPLE,
            "config_requirements": [ConfigurationRequirement.ENVIRONMENT],
            "setup_time": 2,
            "expertise": ["file_systems"],
            "issues": ["Path permissions", "Cross-platform compatibility"]
        },
        "github": {
            "complexity": ServerComplexity.MODERATE,
            "config_requirements": [ConfigurationRequirement.API_KEY],
            "setup_time": 5,
            "expertise": ["git", "github_api"],
            "issues": ["Rate limiting", "Authentication scope"]
        },
        "postgres": {
            "complexity": ServerComplexity.COMPLEX,
            "config_requirements": [ConfigurationRequirement.CONNECTION_STRING, ConfigurationRequirement.CREDENTIALS],
            "setup_time": 15,
            "expertise": ["sql", "database_administration"],
            "issues": ["Connection security", "Query permissions", "Database compatibility"]
        },
        "puppeteer": {
            "complexity": ServerComplexity.ADVANCED,
            "config_requirements": [ConfigurationRequirement.CUSTOM_CONFIG],
            "setup_time": 20,
            "expertise": ["web_automation", "javascript", "browser_apis"],
            "issues": ["Browser dependencies", "Memory usage", "Headless configuration"]
        },
        "memory": {
            "complexity": ServerComplexity.MODERATE,
            "config_requirements": [ConfigurationRequirement.ENVIRONMENT],
            "setup_time": 5,
            "expertise": ["data_structures"],
            "issues": ["Persistence configuration", "Memory limits"]
        },
        "search": {
            "complexity": ServerComplexity.MODERATE,
            "config_requirements": [ConfigurationRequirement.API_KEY],
            "setup_time": 10,
            "expertise": ["web_apis", "search_engines"],
            "issues": ["API quotas", "Result quality"]
        }
    }
    
    def __init__(self):
        """Initialize MCP analyzer."""
        self.assessments: Dict[str, ComplexityAssessment] = {}
    
    async def analyze_server(
        self,
        server: MCPServer,
        project_context: Optional[Dict[str, Any]] = None
    ) -> ComplexityAssessment:
        """
        Analyze a single MCP server.
        
        Args:
            server: MCP server to analyze
            project_context: Project context for compatibility assessment
            
        Returns:
            Complexity assessment
        """
        logger.info(f"Analyzing MCP server: {server.name}")
        
        # Get base complexity from known servers
        base_info = self._get_base_complexity(server)
        
        # Analyze specific aspects
        config_requirements = await self._analyze_configuration(server)
        compatibility = await self._assess_compatibility(server, project_context)
        potential_issues = await self._identify_issues(server, project_context)
        recommendations = self._generate_recommendations(server, potential_issues)
        
        # Create assessment
        assessment = ComplexityAssessment(
            server_name=server.name,
            complexity=base_info["complexity"],
            configuration_requirements=config_requirements,
            estimated_setup_time=base_info["setup_time"],
            required_expertise=base_info["expertise"],
            potential_issues=potential_issues,
            recommendations=recommendations,
            compatibility_score=compatibility,
            metadata={
                "server_version": server.version,
                "capabilities": server.capabilities,
                "installed": server.installed
            }
        )
        
        # Cache assessment
        self.assessments[server.name] = assessment
        
        return assessment
    
    async def analyze_multiple(
        self,
        servers: List[MCPServer],
        project_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ComplexityAssessment]:
        """
        Analyze multiple MCP servers.
        
        Args:
            servers: List of servers to analyze
            project_context: Project context
            
        Returns:
            Dictionary of assessments
        """
        tasks = [
            self.analyze_server(server, project_context)
            for server in servers
        ]
        
        assessments = await asyncio.gather(*tasks)
        
        return {
            assessment.server_name: assessment
            for assessment in assessments
        }
    
    def _get_base_complexity(self, server: MCPServer) -> Dict[str, Any]:
        """Get base complexity information for a server."""
        # Extract server type from name
        server_type = None
        for known_type in self.COMPLEXITY_MAP.keys():
            if known_type in server.name.lower():
                server_type = known_type
                break
        
        if server_type and server_type in self.COMPLEXITY_MAP:
            return self.COMPLEXITY_MAP[server_type]
        
        # Default complexity for unknown servers
        return {
            "complexity": ServerComplexity.MODERATE,
            "config_requirements": [ConfigurationRequirement.CUSTOM_CONFIG],
            "setup_time": 10,
            "expertise": ["general"],
            "issues": ["Unknown server configuration"]
        }
    
    async def _analyze_configuration(self, server: MCPServer) -> List[ConfigurationRequirement]:
        """Analyze configuration requirements."""
        requirements = []
        
        # Check schema for required fields
        if server.schema:
            schema_props = server.schema.get("properties", {})
            required_fields = server.schema.get("required", [])
            
            for field in required_fields:
                field_schema = schema_props.get(field, {})
                field_type = field_schema.get("type")
                
                # Determine requirement type based on field name and type
                if "key" in field.lower() or "token" in field.lower():
                    requirements.append(ConfigurationRequirement.API_KEY)
                elif "connection" in field.lower() or "url" in field.lower():
                    requirements.append(ConfigurationRequirement.CONNECTION_STRING)
                elif "password" in field.lower() or "credential" in field.lower():
                    requirements.append(ConfigurationRequirement.CREDENTIALS)
                elif field_type == "object":
                    requirements.append(ConfigurationRequirement.CUSTOM_CONFIG)
        
        # Check metadata for environment variables
        if server.metadata.get("env"):
            requirements.append(ConfigurationRequirement.ENVIRONMENT)
        
        # Get from known server info
        server_type = self._extract_server_type(server.name)
        if server_type in self.COMPLEXITY_MAP:
            base_reqs = self.COMPLEXITY_MAP[server_type]["config_requirements"]
            requirements.extend(base_reqs)
        
        # Remove duplicates
        return list(set(requirements))
    
    async def _assess_compatibility(
        self,
        server: MCPServer,
        project_context: Optional[Dict[str, Any]]
    ) -> float:
        """
        Assess compatibility with project.
        
        Returns:
            Compatibility score (0-1)
        """
        score = 1.0
        
        if not project_context:
            return score
        
        # Check project type compatibility
        project_type = project_context.get("type", "general")
        server_type = self._extract_server_type(server.name)
        
        compatibility_matrix = {
            "web": ["filesystem", "github", "puppeteer", "search"],
            "api": ["postgres", "memory", "github"],
            "cli": ["filesystem", "github"],
            "data": ["postgres", "filesystem", "memory"],
            "automation": ["puppeteer", "filesystem"]
        }
        
        if project_type in compatibility_matrix:
            if server_type not in compatibility_matrix[project_type]:
                score *= 0.7
        
        # Check technology stack compatibility
        tech_stack = project_context.get("technologies", [])
        if "node" not in tech_stack and server.command == "npx":
            score *= 0.8
        
        # Check for conflicting servers
        existing_servers = project_context.get("mcp_servers", [])
        if server_type == "postgres" and any("postgres" in s for s in existing_servers):
            score *= 0.5  # Multiple database servers might conflict
        
        return max(0.0, min(1.0, score))
    
    async def _identify_issues(
        self,
        server: MCPServer,
        project_context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Identify potential issues with server."""
        issues = []
        
        # Get base issues
        server_type = self._extract_server_type(server.name)
        if server_type in self.COMPLEXITY_MAP:
            issues.extend(self.COMPLEXITY_MAP[server_type]["issues"])
        
        # Installation issues
        if not server.installed:
            issues.append("Server not installed")
        
        # Version compatibility
        if server.version:
            # Check for known version issues
            if "0." in server.version:  # Beta version
                issues.append("Beta version may have stability issues")
        
        # Project-specific issues
        if project_context:
            # Check resource constraints
            if project_context.get("resource_constrained", False):
                if server_type == "puppeteer":
                    issues.append("High memory usage in resource-constrained environment")
            
            # Check security requirements
            if project_context.get("high_security", False):
                if ConfigurationRequirement.API_KEY in await self._analyze_configuration(server):
                    issues.append("API key management in high-security environment")
        
        return issues
    
    def _generate_recommendations(
        self,
        server: MCPServer,
        issues: List[str]
    ) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Installation recommendations
        if "Server not installed" in issues:
            if server.command == "npx":
                recommendations.append(f"Install with: npm install -g {server.metadata.get('npm_package', server.name)}")
            else:
                recommendations.append(f"Ensure {server.command} is installed and in PATH")
        
        # Configuration recommendations
        server_type = self._extract_server_type(server.name)
        
        if server_type == "github":
            recommendations.append("Create a GitHub personal access token with appropriate scopes")
            recommendations.append("Store token securely using environment variables")
        
        elif server_type == "postgres":
            recommendations.append("Use connection pooling for better performance")
            recommendations.append("Configure read-only user for safety")
            recommendations.append("Enable SSL for production databases")
        
        elif server_type == "puppeteer":
            recommendations.append("Use headless mode for better performance")
            recommendations.append("Configure viewport size based on target use case")
            recommendations.append("Implement proper cleanup to avoid memory leaks")
        
        elif server_type == "filesystem":
            recommendations.append("Restrict access paths for security")
            recommendations.append("Use absolute paths for reliability")
        
        # General recommendations
        if any("permission" in issue.lower() for issue in issues):
            recommendations.append("Review and configure appropriate permissions")
        
        if any("memory" in issue.lower() for issue in issues):
            recommendations.append("Monitor memory usage and set appropriate limits")
        
        return recommendations
    
    def _extract_server_type(self, server_name: str) -> Optional[str]:
        """Extract server type from name."""
        for known_type in self.COMPLEXITY_MAP.keys():
            if known_type in server_name.lower():
                return known_type
        return None
    
    def get_complexity_summary(
        self,
        assessments: List[ComplexityAssessment]
    ) -> Dict[str, Any]:
        """
        Generate summary of complexity assessments.
        
        Args:
            assessments: List of assessments
            
        Returns:
            Summary statistics
        """
        if not assessments:
            return {}
        
        total_setup_time = sum(a.estimated_setup_time for a in assessments)
        avg_compatibility = sum(a.compatibility_score for a in assessments) / len(assessments)
        
        complexity_counts = {
            level: sum(1 for a in assessments if a.complexity == level)
            for level in ServerComplexity
        }
        
        all_expertise = set()
        all_issues = []
        
        for assessment in assessments:
            all_expertise.update(assessment.required_expertise)
            all_issues.extend(assessment.potential_issues)
        
        return {
            "total_servers": len(assessments),
            "total_setup_time": total_setup_time,
            "average_compatibility": avg_compatibility,
            "complexity_distribution": {
                level.value: count
                for level, count in complexity_counts.items()
            },
            "required_expertise": list(all_expertise),
            "common_issues": list(set(all_issues)),
            "high_complexity_servers": [
                a.server_name for a in assessments
                if a.complexity in (ServerComplexity.COMPLEX, ServerComplexity.ADVANCED)
            ]
        }
    
    def recommend_server_order(
        self,
        assessments: List[ComplexityAssessment]
    ) -> List[str]:
        """
        Recommend installation order for servers.
        
        Args:
            assessments: List of assessments
            
        Returns:
            Ordered list of server names
        """
        # Sort by complexity (simple first) and setup time
        sorted_assessments = sorted(
            assessments,
            key=lambda a: (
                list(ServerComplexity).index(a.complexity),
                a.estimated_setup_time
            )
        )
        
        return [a.server_name for a in sorted_assessments]