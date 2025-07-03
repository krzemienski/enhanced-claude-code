"""MCP server installation verification and management."""

import json
import logging
import subprocess
import asyncio
import shutil
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import os

from ..models.base import BaseModel
from ..exceptions.base import ClaudeCodeBuilderError, ConfigurationError
from .discovery import MCPServer

logger = logging.getLogger(__name__)


@dataclass
class InstallationResult:
    """Result of an installation attempt."""
    server_name: str
    success: bool
    installation_path: Optional[Path] = None
    version: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        """Initialize result attributes."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "server_name": self.server_name,
            "success": self.success,
            "installation_path": str(self.installation_path) if self.installation_path else None,
            "version": self.version,
            "error": self.error,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class VerificationResult:
    """Result of installation verification."""
    server_name: str
    installed: bool
    executable_found: bool
    version_verified: bool
    permissions_ok: bool
    dependencies_met: bool
    issues: List[str]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize verification attributes."""
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_valid(self) -> bool:
        """Check if installation is valid."""
        return (
            self.installed and
            self.executable_found and
            self.permissions_ok and
            self.dependencies_met
        )


class MCPInstaller:
    """Manages MCP server installation and verification."""
    
    def __init__(self, install_dir: Optional[Path] = None):
        """
        Initialize MCP installer.
        
        Args:
            install_dir: Directory for local installations
        """
        self.install_dir = install_dir or Path.home() / ".claude" / "mcp-servers"
        self.install_dir.mkdir(parents=True, exist_ok=True)
        self.installation_cache: Dict[str, InstallationResult] = {}
    
    async def verify_installation(self, server: MCPServer) -> VerificationResult:
        """
        Verify MCP server installation.
        
        Args:
            server: Server to verify
            
        Returns:
            Verification result
        """
        logger.info(f"Verifying installation of {server.name}")
        
        issues = []
        
        # Check if marked as installed
        installed = server.installed
        
        # Check executable
        executable_found = await self._check_executable(server)
        if not executable_found:
            issues.append("Executable not found")
        
        # Check version
        version_verified = await self._verify_version(server)
        if not version_verified:
            issues.append("Could not verify version")
        
        # Check permissions
        permissions_ok = await self._check_permissions(server)
        if not permissions_ok:
            issues.append("Insufficient permissions")
        
        # Check dependencies
        dependencies_met, missing_deps = await self._check_dependencies(server)
        if not dependencies_met:
            issues.extend([f"Missing dependency: {dep}" for dep in missing_deps])
        
        return VerificationResult(
            server_name=server.name,
            installed=installed,
            executable_found=executable_found,
            version_verified=version_verified,
            permissions_ok=permissions_ok,
            dependencies_met=dependencies_met,
            issues=issues,
            metadata={
                "checked_at": datetime.now().isoformat(),
                "server_command": server.command,
                "server_args": server.args
            }
        )
    
    async def install_server(
        self,
        server: MCPServer,
        force: bool = False
    ) -> InstallationResult:
        """
        Install an MCP server.
        
        Args:
            server: Server to install
            force: Force reinstallation
            
        Returns:
            Installation result
        """
        logger.info(f"Installing MCP server: {server.name}")
        
        start_time = datetime.now()
        
        # Check if already installed
        if server.installed and not force:
            verification = await self.verify_installation(server)
            if verification.is_valid:
                return InstallationResult(
                    server_name=server.name,
                    success=True,
                    installation_path=server.installation_path,
                    version=server.version,
                    error="Already installed and verified"
                )
        
        try:
            # Install based on server type
            if server.command == "npx" and server.metadata.get("npm_package"):
                result = await self._install_npm_server(server)
            else:
                result = await self._install_generic_server(server)
            
            # Calculate duration
            result.duration = (datetime.now() - start_time).total_seconds()
            
            # Cache result
            self.installation_cache[server.name] = result
            
            # Update server status
            if result.success:
                server.installed = True
                server.installation_path = result.installation_path
                server.version = result.version
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to install {server.name}: {e}")
            return InstallationResult(
                server_name=server.name,
                success=False,
                error=str(e),
                duration=(datetime.now() - start_time).total_seconds()
            )
    
    async def _install_npm_server(self, server: MCPServer) -> InstallationResult:
        """Install an npm-based MCP server."""
        package_name = server.metadata.get("npm_package", server.name)
        
        # Try global installation first
        cmd = ["npm", "install", "-g", package_name]
        result = await self._run_command(cmd, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            # Get installation path
            path_cmd = ["npm", "list", "-g", package_name, "--json"]
            path_result = await self._run_command(path_cmd)
            
            installation_path = None
            if path_result.returncode == 0:
                try:
                    data = json.loads(path_result.stdout)
                    # Extract path from npm output
                    deps = data.get("dependencies", {})
                    if package_name in deps:
                        installation_path = Path(deps[package_name].get("resolved", ""))
                except Exception:
                    pass
            
            # Get version
            version = await self._get_npm_version(package_name)
            
            return InstallationResult(
                server_name=server.name,
                success=True,
                installation_path=installation_path,
                version=version
            )
        
        # Try local installation as fallback
        local_path = self.install_dir / server.name
        local_path.mkdir(exist_ok=True)
        
        cmd = ["npm", "install", package_name]
        result = await self._run_command(cmd, cwd=str(local_path), timeout=300)
        
        if result.returncode == 0:
            return InstallationResult(
                server_name=server.name,
                success=True,
                installation_path=local_path,
                version=await self._get_npm_version(package_name)
            )
        
        return InstallationResult(
            server_name=server.name,
            success=False,
            error=result.stderr or "Installation failed"
        )
    
    async def _install_generic_server(self, server: MCPServer) -> InstallationResult:
        """Install a generic MCP server."""
        # For generic servers, we assume they need to be downloaded/built
        # This is a placeholder for custom installation logic
        
        return InstallationResult(
            server_name=server.name,
            success=False,
            error="Generic server installation not implemented"
        )
    
    async def _check_executable(self, server: MCPServer) -> bool:
        """Check if server executable exists."""
        if server.command == "npx":
            # For npx, check if the package is available
            package = server.metadata.get("npm_package")
            if package:
                result = await self._run_command(["npm", "list", "-g", package])
                return result.returncode == 0
        
        # Check if command exists in PATH
        result = await self._run_command(["which", server.command])
        if result.returncode == 0:
            return True
        
        # Check installation path
        if server.installation_path and server.installation_path.exists():
            executable = server.installation_path / server.command
            return executable.exists() and os.access(executable, os.X_OK)
        
        return False
    
    async def _verify_version(self, server: MCPServer) -> bool:
        """Verify server version."""
        try:
            # Build version command
            cmd = [server.command] + server.args + ["--version"]
            
            result = await self._run_command(cmd, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                # Update server version if found
                version_line = result.stdout.strip().split('\n')[0]
                # Extract version number (common patterns)
                import re
                version_match = re.search(r'(\d+\.\d+\.\d+)', version_line)
                if version_match:
                    server.version = version_match.group(1)
                return True
                
        except Exception as e:
            logger.debug(f"Version check failed for {server.name}: {e}")
        
        return False
    
    async def _check_permissions(self, server: MCPServer) -> bool:
        """Check if server has required permissions."""
        # For npx servers, permissions are usually OK
        if server.command == "npx":
            return True
        
        # Check executable permissions
        if server.installation_path:
            executable = server.installation_path / server.command
            if executable.exists():
                return os.access(executable, os.X_OK)
        
        # Check if we can run the command
        result = await self._run_command([server.command, "--help"], timeout=5)
        return result.returncode == 0
    
    async def _check_dependencies(self, server: MCPServer) -> Tuple[bool, List[str]]:
        """Check server dependencies."""
        missing_deps = []
        
        # Common dependencies by server type
        dependencies = {
            "puppeteer": ["chromium", "chrome"],
            "postgres": ["psql"],
            "github": ["git"]
        }
        
        # Check based on server name
        for dep_type, deps in dependencies.items():
            if dep_type in server.name.lower():
                for dep in deps:
                    result = await self._run_command(["which", dep])
                    if result.returncode != 0:
                        missing_deps.append(dep)
        
        # Node.js dependency for npm packages
        if server.command == "npx" or server.metadata.get("npm_package"):
            result = await self._run_command(["node", "--version"])
            if result.returncode != 0:
                missing_deps.append("node.js")
        
        return len(missing_deps) == 0, missing_deps
    
    async def _get_npm_version(self, package_name: str) -> Optional[str]:
        """Get version of an npm package."""
        cmd = ["npm", "list", "-g", package_name, "--json"]
        result = await self._run_command(cmd)
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                deps = data.get("dependencies", {})
                if package_name in deps:
                    return deps[package_name].get("version")
            except Exception:
                pass
        
        return None
    
    async def uninstall_server(self, server: MCPServer) -> bool:
        """
        Uninstall an MCP server.
        
        Args:
            server: Server to uninstall
            
        Returns:
            True if successful
        """
        logger.info(f"Uninstalling MCP server: {server.name}")
        
        try:
            if server.command == "npx" and server.metadata.get("npm_package"):
                # Uninstall npm package
                package = server.metadata["npm_package"]
                cmd = ["npm", "uninstall", "-g", package]
                result = await self._run_command(cmd)
                
                if result.returncode == 0:
                    server.installed = False
                    server.installation_path = None
                    return True
            
            # Remove local installation
            if server.installation_path and server.installation_path.exists():
                if server.installation_path.is_dir():
                    shutil.rmtree(server.installation_path)
                else:
                    server.installation_path.unlink()
                
                server.installed = False
                server.installation_path = None
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to uninstall {server.name}: {e}")
            return False
    
    async def batch_install(
        self,
        servers: List[MCPServer],
        parallel: bool = True,
        force: bool = False
    ) -> Dict[str, InstallationResult]:
        """
        Install multiple servers.
        
        Args:
            servers: Servers to install
            parallel: Install in parallel
            force: Force reinstallation
            
        Returns:
            Dictionary of installation results
        """
        if parallel:
            tasks = [
                self.install_server(server, force)
                for server in servers
            ]
            results = await asyncio.gather(*tasks)
        else:
            results = []
            for server in servers:
                result = await self.install_server(server, force)
                results.append(result)
        
        return {
            result.server_name: result
            for result in results
        }
    
    async def _run_command(
        self,
        cmd: List[str],
        timeout: int = 30,
        cwd: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """Run a command with timeout."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
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
    
    def get_installation_summary(self) -> Dict[str, Any]:
        """Get summary of installations."""
        successful = [r for r in self.installation_cache.values() if r.success]
        failed = [r for r in self.installation_cache.values() if not r.success]
        
        return {
            "total_attempts": len(self.installation_cache),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.installation_cache) if self.installation_cache else 0,
            "total_duration": sum(r.duration for r in self.installation_cache.values()),
            "failed_servers": [r.server_name for r in failed],
            "errors": {r.server_name: r.error for r in failed if r.error}
        }