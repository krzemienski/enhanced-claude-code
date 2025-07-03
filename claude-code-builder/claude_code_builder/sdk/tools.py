"""Tool configuration and management for Claude Code SDK."""

import json
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..models.base import BaseModel
from ..exceptions.base import SDKError, ConfigurationError

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of Claude Code tools."""
    FILE_SYSTEM = "file_system"
    EXECUTION = "execution"
    SEARCH = "search"
    WEB = "web"
    GIT = "git"
    TESTING = "testing"
    ANALYSIS = "analysis"
    MCP = "mcp"
    CUSTOM = "custom"


@dataclass
class Tool:
    """Represents a Claude Code tool."""
    name: str
    category: ToolCategory
    description: str
    enabled: bool = True
    configuration: Dict[str, Any] = None
    required_permissions: Set[str] = None
    
    def __post_init__(self):
        """Initialize tool attributes."""
        if self.configuration is None:
            self.configuration = {}
        if self.required_permissions is None:
            self.required_permissions = set()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary."""
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "enabled": self.enabled,
            "configuration": self.configuration,
            "required_permissions": list(self.required_permissions)
        }


class ToolManager:
    """Manages Claude Code tools configuration."""
    
    # Default Claude Code tools
    DEFAULT_TOOLS = [
        Tool(
            name="read_file",
            category=ToolCategory.FILE_SYSTEM,
            description="Read contents of a file",
            required_permissions={"file_read"}
        ),
        Tool(
            name="write_file",
            category=ToolCategory.FILE_SYSTEM,
            description="Write or create a file",
            required_permissions={"file_write"}
        ),
        Tool(
            name="list_directory",
            category=ToolCategory.FILE_SYSTEM,
            description="List directory contents",
            required_permissions={"file_read"}
        ),
        Tool(
            name="execute_command",
            category=ToolCategory.EXECUTION,
            description="Execute shell commands",
            required_permissions={"execute"}
        ),
        Tool(
            name="search_files",
            category=ToolCategory.SEARCH,
            description="Search for files by pattern",
            required_permissions={"file_read"}
        ),
        Tool(
            name="grep_search",
            category=ToolCategory.SEARCH,
            description="Search file contents",
            required_permissions={"file_read"}
        ),
        Tool(
            name="web_search",
            category=ToolCategory.WEB,
            description="Search the web",
            required_permissions={"web_access"}
        ),
        Tool(
            name="git_status",
            category=ToolCategory.GIT,
            description="Get git repository status",
            required_permissions={"git"}
        ),
        Tool(
            name="git_commit",
            category=ToolCategory.GIT,
            description="Create git commits",
            required_permissions={"git", "file_write"}
        ),
        Tool(
            name="run_tests",
            category=ToolCategory.TESTING,
            description="Execute project tests",
            required_permissions={"execute", "file_read"}
        )
    ]
    
    def __init__(self):
        """Initialize tool manager."""
        self.tools: Dict[str, Tool] = {}
        self.custom_tools: Dict[str, Tool] = {}
        self.disabled_tools: Set[str] = set()
        self.tool_configs: Dict[str, Dict[str, Any]] = {}
        
        # Load default tools
        self._load_default_tools()
    
    def _load_default_tools(self) -> None:
        """Load default Claude Code tools."""
        for tool in self.DEFAULT_TOOLS:
            self.tools[tool.name] = tool
        
        logger.info(f"Loaded {len(self.tools)} default tools")
    
    def register_tool(
        self,
        name: str,
        category: ToolCategory,
        description: str,
        configuration: Optional[Dict[str, Any]] = None,
        required_permissions: Optional[Set[str]] = None
    ) -> Tool:
        """
        Register a custom tool.
        
        Args:
            name: Tool name
            category: Tool category
            description: Tool description
            configuration: Tool configuration
            required_permissions: Required permissions
            
        Returns:
            Registered tool
        """
        if name in self.tools:
            raise ConfigurationError(f"Tool {name} already exists")
        
        tool = Tool(
            name=name,
            category=category,
            description=description,
            configuration=configuration or {},
            required_permissions=required_permissions or set()
        )
        
        self.custom_tools[name] = tool
        self.tools[name] = tool
        
        logger.info(f"Registered custom tool: {name}")
        return tool
    
    def configure_tool(self, name: str, configuration: Dict[str, Any]) -> None:
        """
        Configure a tool.
        
        Args:
            name: Tool name
            configuration: Tool configuration
        """
        if name not in self.tools:
            raise ConfigurationError(f"Tool {name} not found")
        
        self.tool_configs[name] = configuration
        self.tools[name].configuration.update(configuration)
        
        logger.info(f"Configured tool {name}")
    
    def enable_tool(self, name: str) -> None:
        """Enable a tool."""
        if name not in self.tools:
            raise ConfigurationError(f"Tool {name} not found")
        
        self.tools[name].enabled = True
        self.disabled_tools.discard(name)
        
        logger.info(f"Enabled tool: {name}")
    
    def disable_tool(self, name: str) -> None:
        """Disable a tool."""
        if name not in self.tools:
            raise ConfigurationError(f"Tool {name} not found")
        
        self.tools[name].enabled = False
        self.disabled_tools.add(name)
        
        logger.info(f"Disabled tool: {name}")
    
    def get_enabled_tools(self) -> List[Tool]:
        """Get all enabled tools."""
        return [
            tool for tool in self.tools.values()
            if tool.enabled
        ]
    
    def get_tools_by_category(self, category: ToolCategory) -> List[Tool]:
        """Get tools by category."""
        return [
            tool for tool in self.tools.values()
            if tool.category == category and tool.enabled
        ]
    
    def get_tool_configuration(self, name: str) -> Dict[str, Any]:
        """Get tool configuration."""
        if name not in self.tools:
            raise ConfigurationError(f"Tool {name} not found")
        
        return self.tools[name].configuration
    
    def validate_permissions(self, available_permissions: Set[str]) -> List[str]:
        """
        Validate tool permissions.
        
        Args:
            available_permissions: Available permissions
            
        Returns:
            List of tools with missing permissions
        """
        tools_with_missing_permissions = []
        
        for tool in self.get_enabled_tools():
            missing = tool.required_permissions - available_permissions
            if missing:
                tools_with_missing_permissions.append(
                    f"{tool.name}: missing {', '.join(missing)}"
                )
        
        return tools_with_missing_permissions
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export tool configuration."""
        return {
            "enabled_tools": [
                tool.to_dict() for tool in self.get_enabled_tools()
            ],
            "disabled_tools": list(self.disabled_tools),
            "custom_tools": [
                tool.to_dict() for tool in self.custom_tools.values()
            ],
            "tool_configs": self.tool_configs
        }
    
    def import_configuration(self, config: Dict[str, Any]) -> None:
        """Import tool configuration."""
        # Import custom tools
        for tool_data in config.get("custom_tools", []):
            self.register_tool(
                name=tool_data["name"],
                category=ToolCategory(tool_data["category"]),
                description=tool_data["description"],
                configuration=tool_data.get("configuration", {}),
                required_permissions=set(tool_data.get("required_permissions", []))
            )
        
        # Apply tool configs
        for name, cfg in config.get("tool_configs", {}).items():
            if name in self.tools:
                self.configure_tool(name, cfg)
        
        # Disable tools
        for name in config.get("disabled_tools", []):
            if name in self.tools:
                self.disable_tool(name)
        
        logger.info("Imported tool configuration")
    
    def create_mcp_tool_config(self, tool: Tool) -> Dict[str, Any]:
        """
        Create MCP server configuration for a tool.
        
        Args:
            tool: Tool to configure
            
        Returns:
            MCP configuration
        """
        if tool.category != ToolCategory.MCP:
            raise ConfigurationError(f"Tool {tool.name} is not an MCP tool")
        
        config = {
            "command": tool.configuration.get("command", tool.name),
            "args": tool.configuration.get("args", []),
            "env": tool.configuration.get("env", {})
        }
        
        # Add schema if available
        if "schema" in tool.configuration:
            config["schema"] = tool.configuration["schema"]
        
        return config
    
    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get all MCP tool configurations."""
        mcp_configs = []
        
        for tool in self.get_tools_by_category(ToolCategory.MCP):
            try:
                config = self.create_mcp_tool_config(tool)
                mcp_configs.append(config)
            except Exception as e:
                logger.error(f"Failed to create MCP config for {tool.name}: {e}")
        
        return mcp_configs
    
    def validate_tool_config(self, name: str) -> bool:
        """
        Validate tool configuration.
        
        Args:
            name: Tool name
            
        Returns:
            True if valid
        """
        if name not in self.tools:
            return False
        
        tool = self.tools[name]
        
        # Check required configuration fields
        required_fields = {
            ToolCategory.MCP: ["command"],
            ToolCategory.CUSTOM: ["handler"],
            ToolCategory.WEB: ["api_key"]
        }
        
        if tool.category in required_fields:
            for field in required_fields[tool.category]:
                if field not in tool.configuration:
                    logger.error(f"Tool {name} missing required field: {field}")
                    return False
        
        return True
    
    def reset_to_defaults(self) -> None:
        """Reset tools to default configuration."""
        self.tools.clear()
        self.custom_tools.clear()
        self.disabled_tools.clear()
        self.tool_configs.clear()
        
        self._load_default_tools()
        
        logger.info("Reset tools to defaults")