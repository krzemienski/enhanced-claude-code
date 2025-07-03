"""MCP configuration generation for Claude Code."""

import json
import logging
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass
import os

from ..models.base import BaseModel
from ..models.project import ProjectSpec
from ..exceptions.base import ClaudeCodeBuilderError, ValidationError
from .discovery import MCPServer
from .recommender import ServerRecommendation
from .registry import MCPRegistry

logger = logging.getLogger(__name__)


@dataclass
class MCPConfiguration:
    """Complete MCP configuration."""
    servers: Dict[str, Dict[str, Any]]
    global_settings: Dict[str, Any]
    project_specific: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mcpServers": self.servers,
            "globalSettings": self.global_settings,
            "projectSpecific": self.project_specific,
            "metadata": self.metadata
        }
    
    def to_claude_format(self) -> Dict[str, Any]:
        """Convert to Claude Code format."""
        # Claude Code expects specific format
        return {
            "mcpServers": self.servers
        }


class MCPConfigGenerator:
    """Generates MCP configurations for projects."""
    
    # Environment variable patterns
    ENV_PATTERNS = {
        "api_key": "${{{}_API_KEY}}",
        "token": "${{{}_TOKEN}}",
        "password": "${{{}_PASSWORD}}",
        "secret": "${{{}_SECRET}}",
        "url": "${{{}_URL}}",
        "connection": "${{{}_CONNECTION}}"
    }
    
    def __init__(self, registry: Optional[MCPRegistry] = None):
        """
        Initialize config generator.
        
        Args:
            registry: MCP registry to use
        """
        self.registry = registry or MCPRegistry()
    
    async def generate_configuration(
        self,
        project_spec: ProjectSpec,
        recommendations: List[ServerRecommendation],
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> MCPConfiguration:
        """
        Generate MCP configuration for a project.
        
        Args:
            project_spec: Project specification
            recommendations: Server recommendations
            custom_settings: Custom settings to apply
            
        Returns:
            MCP configuration
        """
        logger.info(f"Generating MCP configuration for {project_spec.name}")
        
        servers = {}
        
        # Process each recommended server
        for rec in recommendations:
            server_config = await self._generate_server_config(
                rec.server,
                project_spec,
                rec.configuration_tips
            )
            
            if server_config:
                servers[rec.server.name] = server_config
        
        # Global settings
        global_settings = self._generate_global_settings(project_spec)
        
        # Project-specific settings
        project_settings = self._generate_project_settings(project_spec, recommendations)
        
        # Apply custom settings
        if custom_settings:
            global_settings.update(custom_settings.get("global", {}))
            project_settings.update(custom_settings.get("project", {}))
        
        # Metadata
        metadata = {
            "generated_for": project_spec.name,
            "project_type": project_spec.type,
            "server_count": len(servers),
            "version": "1.0"
        }
        
        return MCPConfiguration(
            servers=servers,
            global_settings=global_settings,
            project_specific=project_settings,
            metadata=metadata
        )
    
    async def _generate_server_config(
        self,
        server: MCPServer,
        project_spec: ProjectSpec,
        tips: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Generate configuration for a single server."""
        server_type = self._extract_server_type(server.name)
        if not server_type:
            return None
        
        # Base configuration
        config = {
            "command": server.command,
            "args": server.args.copy() if server.args else []
        }
        
        # Add environment variables
        env_vars = self._generate_env_vars(server, project_spec)
        if env_vars:
            config["env"] = env_vars
        
        # Server-specific configurations
        if server_type == "filesystem":
            config.update(self._configure_filesystem(project_spec))
        elif server_type == "github":
            config.update(self._configure_github(project_spec))
        elif server_type == "postgres":
            config.update(self._configure_postgres(project_spec))
        elif server_type == "puppeteer":
            config.update(self._configure_puppeteer(project_spec))
        elif server_type == "memory":
            config.update(self._configure_memory(project_spec))
        elif server_type == "search":
            config.update(self._configure_search(project_spec))
        
        # Apply schema defaults if available
        if server.schema:
            config.update(self._apply_schema_defaults(server.schema))
        
        # Apply registry custom config
        registry_entry = self.registry.get_entry(server.name)
        if registry_entry and registry_entry.custom_config:
            config.update(registry_entry.custom_config)
        
        return config
    
    def _generate_env_vars(
        self,
        server: MCPServer,
        project_spec: ProjectSpec
    ) -> Dict[str, str]:
        """Generate environment variables for server."""
        env_vars = {}
        server_type = self._extract_server_type(server.name)
        
        if server_type == "github":
            env_vars["GITHUB_TOKEN"] = self.ENV_PATTERNS["token"].format("GITHUB")
        elif server_type == "postgres":
            env_vars["DATABASE_URL"] = self.ENV_PATTERNS["connection"].format("DATABASE")
        elif server_type == "search":
            env_vars["SEARCH_API_KEY"] = self.ENV_PATTERNS["api_key"].format("SEARCH")
        
        # Add project-specific env vars
        if project_spec.metadata.get("env_prefix"):
            prefix = project_spec.metadata["env_prefix"]
            env_vars[f"{prefix}_ENV"] = "production"
        
        return env_vars
    
    def _configure_filesystem(self, project_spec: ProjectSpec) -> Dict[str, Any]:
        """Configure filesystem server."""
        config = {}
        
        # Set allowed paths based on project
        allowed_paths = [
            str(Path.cwd()),  # Project directory
            str(Path.cwd() / "src"),  # Source directory
            str(Path.cwd() / "tests"),  # Test directory
        ]
        
        # Add project-specific paths
        if project_spec.metadata.get("additional_paths"):
            allowed_paths.extend(project_spec.metadata["additional_paths"])
        
        config["args"] = config.get("args", [])
        config["args"].extend(["--allowed-paths", json.dumps(allowed_paths)])
        
        return config
    
    def _configure_github(self, project_spec: ProjectSpec) -> Dict[str, Any]:
        """Configure GitHub server."""
        config = {}
        
        # Set repository if available
        if project_spec.metadata.get("github_repo"):
            repo = project_spec.metadata["github_repo"]
            config["env"] = config.get("env", {})
            config["env"]["GITHUB_REPOSITORY"] = repo
        
        return config
    
    def _configure_postgres(self, project_spec: ProjectSpec) -> Dict[str, Any]:
        """Configure PostgreSQL server."""
        config = {}
        
        # Connection settings
        config["env"] = config.get("env", {})
        
        # Use project-specific database
        db_name = project_spec.name.lower().replace(" ", "_").replace("-", "_")
        config["env"]["PGDATABASE"] = db_name
        
        # Set connection pool size based on project type
        pool_sizes = {
            "web_application": 20,
            "api_service": 30,
            "cli_tool": 5,
            "data_pipeline": 10
        }
        
        pool_size = pool_sizes.get(project_spec.type, 10)
        config["env"]["PGPOOL_SIZE"] = str(pool_size)
        
        return config
    
    def _configure_puppeteer(self, project_spec: ProjectSpec) -> Dict[str, Any]:
        """Configure Puppeteer server."""
        config = {
            "args": ["--no-sandbox", "--disable-setuid-sandbox"]
        }
        
        # Headless mode for servers/CI
        if project_spec.metadata.get("ci_environment"):
            config["args"].append("--headless")
        
        # Set viewport based on project type
        if project_spec.type == "web_application":
            config["env"] = {
                "PUPPETEER_DEFAULT_VIEWPORT": json.dumps({
                    "width": 1920,
                    "height": 1080
                })
            }
        
        return config
    
    def _configure_memory(self, project_spec: ProjectSpec) -> Dict[str, Any]:
        """Configure memory server."""
        config = {}
        
        # Set memory limits based on project
        memory_limits = {
            "web_application": "512MB",
            "api_service": "256MB",
            "cli_tool": "128MB",
            "data_pipeline": "1GB"
        }
        
        limit = memory_limits.get(project_spec.type, "256MB")
        config["env"] = {"MEMORY_LIMIT": limit}
        
        # Enable persistence for certain project types
        if project_spec.type in ["web_application", "api_service"]:
            config["env"]["ENABLE_PERSISTENCE"] = "true"
            config["env"]["PERSISTENCE_PATH"] = str(Path.cwd() / ".mcp" / "memory")
        
        return config
    
    def _configure_search(self, project_spec: ProjectSpec) -> Dict[str, Any]:
        """Configure search server."""
        config = {}
        
        # Set search scope based on project
        if project_spec.type == "documentation":
            config["args"] = ["--scope", "documentation"]
        elif project_spec.type == "web_application":
            config["args"] = ["--scope", "web"]
        
        return config
    
    def _apply_schema_defaults(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Apply defaults from schema."""
        config = {}
        
        properties = schema.get("properties", {})
        for prop, prop_schema in properties.items():
            if "default" in prop_schema:
                config[prop] = prop_schema["default"]
        
        return config
    
    def _generate_global_settings(self, project_spec: ProjectSpec) -> Dict[str, Any]:
        """Generate global MCP settings."""
        return {
            "timeout": 30000,  # 30 seconds
            "retries": 3,
            "logLevel": "info",
            "enableTelemetry": False
        }
    
    def _generate_project_settings(
        self,
        project_spec: ProjectSpec,
        recommendations: List[ServerRecommendation]
    ) -> Dict[str, Any]:
        """Generate project-specific settings."""
        return {
            "projectName": project_spec.name,
            "projectType": project_spec.type,
            "serverCount": len(recommendations),
            "primaryServers": [
                r.server.name for r in recommendations
                if r.priority.value in ["critical", "high"]
            ]
        }
    
    def _extract_server_type(self, server_name: str) -> Optional[str]:
        """Extract server type from name."""
        known_types = ["filesystem", "github", "postgres", "puppeteer", "memory", "search"]
        
        for known_type in known_types:
            if known_type in server_name.lower():
                return known_type
        
        return None
    
    async def save_configuration(
        self,
        config: MCPConfiguration,
        output_path: Optional[Path] = None,
        format: str = "claude"
    ) -> Path:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            output_path: Output path
            format: Output format (claude, full)
            
        Returns:
            Path to saved file
        """
        if not output_path:
            output_path = Path.cwd() / ".claude" / "mcp-config.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "claude":
            data = config.to_claude_format()
        else:
            data = config.to_dict()
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved MCP configuration to {output_path}")
        return output_path
    
    async def generate_env_template(
        self,
        config: MCPConfiguration,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate environment variable template.
        
        Args:
            config: Configuration
            output_path: Output path
            
        Returns:
            Path to template file
        """
        if not output_path:
            output_path = Path.cwd() / ".env.mcp.template"
        
        env_vars = set()
        
        # Extract all environment variables
        for server_config in config.servers.values():
            if "env" in server_config:
                for key, value in server_config["env"].items():
                    if value.startswith("${") and value.endswith("}"):
                        # Extract variable name
                        var_name = value[2:-1]
                        env_vars.add(var_name)
        
        # Generate template
        template = "# MCP Server Environment Variables\n"
        template += f"# Generated for: {config.metadata.get('generated_for', 'Unknown')}\n\n"
        
        for var in sorted(env_vars):
            if "TOKEN" in var or "KEY" in var:
                template += f"{var}=your_{var.lower()}_here\n"
            elif "URL" in var or "CONNECTION" in var:
                template += f"{var}=connection_string_here\n"
            else:
                template += f"{var}=value_here\n"
        
        with open(output_path, "w") as f:
            f.write(template)
        
        logger.info(f"Generated environment template at {output_path}")
        return output_path
    
    def merge_configurations(
        self,
        configs: List[MCPConfiguration]
    ) -> MCPConfiguration:
        """
        Merge multiple configurations.
        
        Args:
            configs: Configurations to merge
            
        Returns:
            Merged configuration
        """
        merged_servers = {}
        merged_global = {}
        merged_project = {}
        
        for config in configs:
            # Merge servers (later configs override)
            merged_servers.update(config.servers)
            
            # Merge global settings
            merged_global.update(config.global_settings)
            
            # Merge project settings
            merged_project.update(config.project_specific)
        
        return MCPConfiguration(
            servers=merged_servers,
            global_settings=merged_global,
            project_specific=merged_project,
            metadata={
                "merged_from": len(configs),
                "merge_timestamp": str(datetime.now())
            }
        )