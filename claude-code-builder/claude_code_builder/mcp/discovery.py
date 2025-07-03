"""MCP server discovery and management."""

import json
import logging
import subprocess
import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass
import re
import os

from ..models.base import BaseModel
from ..exceptions.base import ClaudeCodeBuilderError, ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class MCPServer:
    """Represents an MCP server."""
    name: str
    command: str
    args: List[str]
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    capabilities: List[str] = None
    schema: Optional[Dict[str, Any]] = None
    installed: bool = False
    installation_path: Optional[Path] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize server attributes."""
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "capabilities": self.capabilities,
            "schema": self.schema,
            "installed": self.installed,
            "installation_path": str(self.installation_path) if self.installation_path else None,
            "metadata": self.metadata
        }
    
    def to_mcp_config(self) -> Dict[str, Any]:
        """Convert to MCP configuration format."""
        config = {
            "command": self.command,
            "args": self.args
        }
        
        if self.schema:
            config["schema"] = self.schema
        
        if self.metadata.get("env"):
            config["env"] = self.metadata["env"]
        
        return config


class MCPDiscovery:
    """Discovers and manages MCP servers."""
    
    # Known MCP server patterns
    KNOWN_SERVERS = {
        "filesystem": {
            "pattern": r"@modelcontextprotocol/server-filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "description": "MCP server for filesystem operations",
            "capabilities": ["read", "write", "list", "search"]
        },
        "github": {
            "pattern": r"@modelcontextprotocol/server-github",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "description": "MCP server for GitHub operations",
            "capabilities": ["repos", "issues", "pull_requests", "actions"]
        },
        "postgres": {
            "pattern": r"@modelcontextprotocol/server-postgres",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres"],
            "description": "MCP server for PostgreSQL databases",
            "capabilities": ["query", "schema", "data_manipulation"]
        },
        "puppeteer": {
            "pattern": r"@modelcontextprotocol/server-puppeteer",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
            "description": "MCP server for web browser automation",
            "capabilities": ["browse", "screenshot", "scrape", "interact"]
        },
        "memory": {
            "pattern": r"modelcontextprotocol.*memory",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "description": "MCP server for memory and context management",
            "capabilities": ["store", "retrieve", "search", "persist"]
        },
        "search": {
            "pattern": r"@modelcontextprotocol/server-.*search",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-search"],
            "description": "MCP server for web search",
            "capabilities": ["search", "crawl", "index"]
        }
    }
    
    def __init__(self):
        """Initialize MCP discovery."""
        self.discovered_servers: Dict[str, MCPServer] = {}
        self.npm_cache: Optional[Dict[str, Any]] = None
        self.system_paths: List[Path] = self._get_system_paths()
    
    async def discover_all(self) -> Dict[str, MCPServer]:
        """
        Discover all available MCP servers.
        
        Returns:
            Dictionary of discovered servers
        """
        logger.info("Starting MCP server discovery")
        
        # Discovery methods
        discovery_tasks = [
            self._discover_npm_servers(),
            self._discover_system_servers(),
            self._discover_config_servers(),
            self._discover_known_servers()
        ]
        
        # Run all discovery methods
        results = await asyncio.gather(*discovery_tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Discovery error: {result}")
            elif isinstance(result, dict):
                self.discovered_servers.update(result)
        
        logger.info(f"Discovered {len(self.discovered_servers)} MCP servers")
        return self.discovered_servers
    
    async def _discover_npm_servers(self) -> Dict[str, MCPServer]:
        """Discover MCP servers from npm."""
        servers = {}
        
        try:
            # Search npm for MCP servers
            cmd = ["npm", "search", "@modelcontextprotocol", "--json"]
            result = await self._run_command(cmd)
            
            if result.returncode == 0 and result.stdout:
                packages = json.loads(result.stdout)
                
                for package in packages:
                    if "server" in package.get("name", ""):
                        server = self._create_server_from_npm(package)
                        if server:
                            servers[server.name] = server
                            
        except Exception as e:
            logger.warning(f"Failed to discover npm servers: {e}")
        
        return servers
    
    async def _discover_system_servers(self) -> Dict[str, MCPServer]:
        """Discover MCP servers installed on the system."""
        servers = {}
        
        for path in self.system_paths:
            if not path.exists():
                continue
            
            try:
                # Look for MCP server executables
                for file in path.glob("mcp-*"):
                    if file.is_file() and os.access(file, os.X_OK):
                        server = await self._analyze_executable(file)
                        if server:
                            servers[server.name] = server
                
                # Look for npm global packages
                node_modules = path / "node_modules"
                if node_modules.exists():
                    for package_dir in node_modules.glob("@modelcontextprotocol/server-*"):
                        server = await self._analyze_npm_package(package_dir)
                        if server:
                            servers[server.name] = server
                            
            except Exception as e:
                logger.warning(f"Error scanning {path}: {e}")
        
        return servers
    
    async def _discover_config_servers(self) -> Dict[str, MCPServer]:
        """Discover servers from configuration files."""
        servers = {}
        
        # Common config locations
        config_paths = [
            Path.home() / ".claude" / "mcp.json",
            Path.home() / ".config" / "claude" / "mcp.json",
            Path.cwd() / ".claude" / "mcp.json",
            Path.cwd() / "mcp.json"
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = json.load(f)
                    
                    for name, server_config in config.get("servers", {}).items():
                        server = self._create_server_from_config(name, server_config)
                        if server:
                            servers[server.name] = server
                            
                except Exception as e:
                    logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return servers
    
    async def _discover_known_servers(self) -> Dict[str, MCPServer]:
        """Discover known MCP servers."""
        servers = {}
        
        for name, info in self.KNOWN_SERVERS.items():
            server = MCPServer(
                name=f"mcp-{name}",
                command=info["command"],
                args=info["args"],
                description=info["description"],
                capabilities=info["capabilities"],
                metadata={"source": "known"}
            )
            
            # Check if installed
            server.installed = await self._check_installation(server)
            
            servers[server.name] = server
        
        return servers
    
    def _create_server_from_npm(self, package: Dict[str, Any]) -> Optional[MCPServer]:
        """Create server from npm package info."""
        name = package.get("name", "")
        if not name:
            return None
        
        # Extract server name
        server_name = name.replace("@modelcontextprotocol/server-", "mcp-")
        
        return MCPServer(
            name=server_name,
            command="npx",
            args=["-y", name],
            description=package.get("description"),
            version=package.get("version"),
            author=package.get("author", {}).get("name"),
            metadata={
                "npm_package": name,
                "keywords": package.get("keywords", []),
                "source": "npm"
            }
        )
    
    async def _analyze_executable(self, path: Path) -> Optional[MCPServer]:
        """Analyze an executable to determine if it's an MCP server."""
        try:
            # Try to get version/help info
            for flag in ["--version", "--help", "-h"]:
                result = await self._run_command([str(path), flag])
                if result.returncode == 0 and result.stdout:
                    # Look for MCP indicators
                    if "mcp" in result.stdout.lower() or "model context protocol" in result.stdout.lower():
                        return MCPServer(
                            name=path.stem,
                            command=str(path),
                            args=[],
                            installed=True,
                            installation_path=path,
                            metadata={"source": "system"}
                        )
            
        except Exception as e:
            logger.debug(f"Failed to analyze {path}: {e}")
        
        return None
    
    async def _analyze_npm_package(self, package_dir: Path) -> Optional[MCPServer]:
        """Analyze an npm package directory."""
        try:
            package_json = package_dir / "package.json"
            if package_json.exists():
                with open(package_json) as f:
                    data = json.load(f)
                
                return MCPServer(
                    name=data["name"].replace("@modelcontextprotocol/server-", "mcp-"),
                    command="node",
                    args=[str(package_dir / data.get("main", "index.js"))],
                    description=data.get("description"),
                    version=data.get("version"),
                    author=data.get("author", {}).get("name") if isinstance(data.get("author"), dict) else data.get("author"),
                    installed=True,
                    installation_path=package_dir,
                    metadata={
                        "npm_package": data["name"],
                        "source": "npm_global"
                    }
                )
                
        except Exception as e:
            logger.debug(f"Failed to analyze npm package {package_dir}: {e}")
        
        return None
    
    def _create_server_from_config(self, name: str, config: Dict[str, Any]) -> Optional[MCPServer]:
        """Create server from configuration."""
        command = config.get("command")
        if not command:
            return None
        
        return MCPServer(
            name=name,
            command=command,
            args=config.get("args", []),
            description=config.get("description"),
            schema=config.get("schema"),
            metadata={
                "env": config.get("env", {}),
                "source": "config"
            }
        )
    
    async def _check_installation(self, server: MCPServer) -> bool:
        """Check if a server is installed."""
        try:
            # For npx servers, check if the package exists
            if server.command == "npx" and server.args:
                package_name = None
                for i, arg in enumerate(server.args):
                    if arg == "-y" and i + 1 < len(server.args):
                        package_name = server.args[i + 1]
                        break
                    elif not arg.startswith("-"):
                        package_name = arg
                        break
                
                if package_name:
                    # Check npm global packages
                    result = await self._run_command(["npm", "list", "-g", package_name])
                    if result.returncode == 0:
                        return True
                    
                    # Check if it can be run with npx
                    result = await self._run_command(["npx", "-y", "--version", package_name])
                    return result.returncode == 0
            
            # For other commands, check if executable exists
            result = await self._run_command(["which", server.command])
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _get_system_paths(self) -> List[Path]:
        """Get system paths to search for MCP servers."""
        paths = []
        
        # Standard paths
        standard_paths = [
            "/usr/local/bin",
            "/usr/bin",
            "/opt/homebrew/bin",
            Path.home() / ".local" / "bin",
            Path.home() / "bin"
        ]
        
        for path in standard_paths:
            if Path(path).exists():
                paths.append(Path(path))
        
        # npm global paths
        try:
            result = subprocess.run(
                ["npm", "config", "get", "prefix"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                npm_prefix = Path(result.stdout.strip())
                paths.extend([
                    npm_prefix / "bin",
                    npm_prefix / "lib" / "node_modules"
                ])
        except Exception:
            pass
        
        # PATH environment variable
        if "PATH" in os.environ:
            for path in os.environ["PATH"].split(os.pathsep):
                if path and Path(path).exists():
                    paths.append(Path(path))
        
        return list(set(paths))  # Remove duplicates
    
    async def _run_command(
        self,
        cmd: List[str],
        timeout: int = 10
    ) -> subprocess.CompletedProcess:
        """Run a command with timeout."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else ""
            )
            
        except asyncio.TimeoutError:
            if process:
                process.terminate()
                await process.wait()
            raise
        except Exception as e:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr=str(e)
            )
    
    def get_server(self, name: str) -> Optional[MCPServer]:
        """Get a discovered server by name."""
        return self.discovered_servers.get(name)
    
    def get_installed_servers(self) -> List[MCPServer]:
        """Get list of installed servers."""
        return [
            server for server in self.discovered_servers.values()
            if server.installed
        ]
    
    def get_available_servers(self) -> List[MCPServer]:
        """Get list of available but not installed servers."""
        return [
            server for server in self.discovered_servers.values()
            if not server.installed
        ]
    
    def search_servers(
        self,
        query: str,
        capabilities: Optional[List[str]] = None
    ) -> List[MCPServer]:
        """
        Search for servers matching criteria.
        
        Args:
            query: Search query
            capabilities: Required capabilities
            
        Returns:
            List of matching servers
        """
        matches = []
        query_lower = query.lower()
        
        for server in self.discovered_servers.values():
            # Match name or description
            if (query_lower in server.name.lower() or
                (server.description and query_lower in server.description.lower())):
                
                # Check capabilities if specified
                if capabilities:
                    if all(cap in server.capabilities for cap in capabilities):
                        matches.append(server)
                else:
                    matches.append(server)
        
        return matches
    
    async def refresh_discovery(self) -> None:
        """Refresh server discovery."""
        self.discovered_servers.clear()
        self.npm_cache = None
        await self.discover_all()