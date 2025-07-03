"""MCP server validation and testing."""

import json
import logging
import asyncio
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..models.base import BaseModel
from ..exceptions.base import ClaudeCodeBuilderError, ValidationError
from .discovery import MCPServer

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation status levels."""
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ValidationCheck:
    """Individual validation check."""
    name: str
    status: ValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration": self.duration
        }


@dataclass
class ValidationResult:
    """Complete validation result for a server."""
    server_name: str
    overall_status: ValidationStatus
    checks: List[ValidationCheck]
    timestamp: datetime
    total_duration: float
    can_use: bool
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "server_name": self.server_name,
            "overall_status": self.overall_status.value,
            "checks": [check.to_dict() for check in self.checks],
            "timestamp": self.timestamp.isoformat(),
            "total_duration": self.total_duration,
            "can_use": self.can_use,
            "recommendations": self.recommendations
        }
    
    @property
    def passed_checks(self) -> int:
        """Count of passed checks."""
        return sum(1 for c in self.checks if c.status == ValidationStatus.PASSED)
    
    @property
    def failed_checks(self) -> int:
        """Count of failed checks."""
        return sum(1 for c in self.checks if c.status == ValidationStatus.FAILED)
    
    @property
    def warning_checks(self) -> int:
        """Count of warning checks."""
        return sum(1 for c in self.checks if c.status == ValidationStatus.WARNING)


class MCPValidator:
    """Validates MCP server functionality and configuration."""
    
    def __init__(self):
        """Initialize MCP validator."""
        self.validation_cache: Dict[str, ValidationResult] = {}
    
    async def validate_server(
        self,
        server: MCPServer,
        config: Optional[Dict[str, Any]] = None,
        deep_check: bool = True
    ) -> ValidationResult:
        """
        Validate an MCP server.
        
        Args:
            server: Server to validate
            config: Server configuration
            deep_check: Perform deep validation
            
        Returns:
            Validation result
        """
        logger.info(f"Validating MCP server: {server.name}")
        
        start_time = datetime.now()
        checks = []
        recommendations = []
        
        # Basic checks
        checks.append(await self._check_executable(server))
        checks.append(await self._check_version(server))
        checks.append(await self._check_dependencies(server))
        
        # Configuration checks
        if config:
            checks.append(await self._check_configuration(server, config))
        
        # Deep checks if requested
        if deep_check and server.installed:
            checks.append(await self._check_startup(server, config))
            checks.append(await self._check_basic_operation(server, config))
            checks.append(await self._check_shutdown(server, config))
        
        # Schema validation
        if server.schema:
            checks.append(await self._check_schema(server))
        
        # Determine overall status
        failed = any(c.status == ValidationStatus.FAILED for c in checks)
        warnings = any(c.status == ValidationStatus.WARNING for c in checks)
        
        if failed:
            overall_status = ValidationStatus.FAILED
            can_use = False
        elif warnings:
            overall_status = ValidationStatus.WARNING
            can_use = True
        else:
            overall_status = ValidationStatus.PASSED
            can_use = True
        
        # Generate recommendations
        recommendations = self._generate_recommendations(server, checks)
        
        # Create result
        result = ValidationResult(
            server_name=server.name,
            overall_status=overall_status,
            checks=checks,
            timestamp=datetime.now(),
            total_duration=(datetime.now() - start_time).total_seconds(),
            can_use=can_use,
            recommendations=recommendations
        )
        
        # Cache result
        self.validation_cache[server.name] = result
        
        return result
    
    async def _check_executable(self, server: MCPServer) -> ValidationCheck:
        """Check if server executable exists and is runnable."""
        start = datetime.now()
        
        try:
            if server.command == "npx":
                # Check npm package
                package = server.metadata.get("npm_package", server.name)
                cmd = ["npm", "list", "-g", package]
            else:
                # Check executable
                cmd = ["which", server.command]
            
            result = await self._run_command(cmd, timeout=10)
            
            if result.returncode == 0:
                return ValidationCheck(
                    name="executable_check",
                    status=ValidationStatus.PASSED,
                    message="Server executable found",
                    duration=(datetime.now() - start).total_seconds()
                )
            else:
                return ValidationCheck(
                    name="executable_check",
                    status=ValidationStatus.FAILED,
                    message="Server executable not found",
                    details={"command": " ".join(cmd), "error": result.stderr},
                    duration=(datetime.now() - start).total_seconds()
                )
                
        except Exception as e:
            return ValidationCheck(
                name="executable_check",
                status=ValidationStatus.FAILED,
                message=f"Failed to check executable: {e}",
                duration=(datetime.now() - start).total_seconds()
            )
    
    async def _check_version(self, server: MCPServer) -> ValidationCheck:
        """Check server version."""
        start = datetime.now()
        
        try:
            cmd = [server.command] + server.args + ["--version"]
            result = await self._run_command(cmd, timeout=10)
            
            if result.returncode == 0:
                version_info = result.stdout.strip()
                return ValidationCheck(
                    name="version_check",
                    status=ValidationStatus.PASSED,
                    message=f"Version: {version_info}",
                    details={"version": version_info},
                    duration=(datetime.now() - start).total_seconds()
                )
            else:
                return ValidationCheck(
                    name="version_check",
                    status=ValidationStatus.WARNING,
                    message="Could not determine version",
                    duration=(datetime.now() - start).total_seconds()
                )
                
        except Exception as e:
            return ValidationCheck(
                name="version_check",
                status=ValidationStatus.WARNING,
                message=f"Version check failed: {e}",
                duration=(datetime.now() - start).total_seconds()
            )
    
    async def _check_dependencies(self, server: MCPServer) -> ValidationCheck:
        """Check server dependencies."""
        start = datetime.now()
        missing = []
        
        # Check known dependencies
        dependency_map = {
            "puppeteer": ["node"],
            "postgres": ["psql"],
            "github": ["git"]
        }
        
        server_type = self._extract_server_type(server.name)
        if server_type in dependency_map:
            for dep in dependency_map[server_type]:
                result = await self._run_command(["which", dep], timeout=5)
                if result.returncode != 0:
                    missing.append(dep)
        
        if missing:
            return ValidationCheck(
                name="dependency_check",
                status=ValidationStatus.FAILED,
                message=f"Missing dependencies: {', '.join(missing)}",
                details={"missing": missing},
                duration=(datetime.now() - start).total_seconds()
            )
        else:
            return ValidationCheck(
                name="dependency_check",
                status=ValidationStatus.PASSED,
                message="All dependencies satisfied",
                duration=(datetime.now() - start).total_seconds()
            )
    
    async def _check_configuration(
        self,
        server: MCPServer,
        config: Dict[str, Any]
    ) -> ValidationCheck:
        """Validate server configuration."""
        start = datetime.now()
        issues = []
        
        # Check required fields from schema
        if server.schema:
            required = server.schema.get("required", [])
            properties = server.schema.get("properties", {})
            
            for field in required:
                if field not in config:
                    issues.append(f"Missing required field: {field}")
                else:
                    # Type validation
                    field_schema = properties.get(field, {})
                    expected_type = field_schema.get("type")
                    value = config[field]
                    
                    if expected_type and not self._validate_type(value, expected_type):
                        issues.append(f"Invalid type for {field}: expected {expected_type}")
        
        # Check for sensitive data
        sensitive_patterns = ["password", "key", "token", "secret"]
        for key, value in config.items():
            if any(pattern in key.lower() for pattern in sensitive_patterns):
                if isinstance(value, str) and len(value) < 10:
                    issues.append(f"Weak {key} detected")
        
        if issues:
            return ValidationCheck(
                name="configuration_check",
                status=ValidationStatus.FAILED,
                message=f"Configuration issues: {len(issues)}",
                details={"issues": issues},
                duration=(datetime.now() - start).total_seconds()
            )
        else:
            return ValidationCheck(
                name="configuration_check",
                status=ValidationStatus.PASSED,
                message="Configuration valid",
                duration=(datetime.now() - start).total_seconds()
            )
    
    async def _check_startup(
        self,
        server: MCPServer,
        config: Optional[Dict[str, Any]]
    ) -> ValidationCheck:
        """Check if server can start successfully."""
        start = datetime.now()
        
        try:
            # Build startup command
            cmd = [server.command] + server.args
            
            # Add test/dry-run flag if available
            test_flags = ["--test", "--dry-run", "--check"]
            for flag in test_flags:
                test_cmd = cmd + [flag]
                result = await self._run_command(test_cmd, timeout=30)
                
                if result.returncode == 0:
                    return ValidationCheck(
                        name="startup_check",
                        status=ValidationStatus.PASSED,
                        message="Server startup test passed",
                        duration=(datetime.now() - start).total_seconds()
                    )
            
            # If no test mode, try brief startup
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait briefly then terminate
            await asyncio.sleep(2)
            process.terminate()
            await process.wait()
            
            return ValidationCheck(
                name="startup_check",
                status=ValidationStatus.WARNING,
                message="Server starts but no test mode available",
                duration=(datetime.now() - start).total_seconds()
            )
            
        except Exception as e:
            return ValidationCheck(
                name="startup_check",
                status=ValidationStatus.FAILED,
                message=f"Startup test failed: {e}",
                duration=(datetime.now() - start).total_seconds()
            )
    
    async def _check_basic_operation(
        self,
        server: MCPServer,
        config: Optional[Dict[str, Any]]
    ) -> ValidationCheck:
        """Check basic server operations."""
        # This would be server-specific
        # For now, we'll skip if not testable
        return ValidationCheck(
            name="operation_check",
            status=ValidationStatus.SKIPPED,
            message="Operation testing not implemented for this server type"
        )
    
    async def _check_shutdown(
        self,
        server: MCPServer,
        config: Optional[Dict[str, Any]]
    ) -> ValidationCheck:
        """Check if server shuts down cleanly."""
        # This would test graceful shutdown
        # For now, we'll skip
        return ValidationCheck(
            name="shutdown_check",
            status=ValidationStatus.SKIPPED,
            message="Shutdown testing not implemented"
        )
    
    async def _check_schema(self, server: MCPServer) -> ValidationCheck:
        """Validate server schema."""
        start = datetime.now()
        
        try:
            # Basic schema validation
            if not isinstance(server.schema, dict):
                return ValidationCheck(
                    name="schema_check",
                    status=ValidationStatus.FAILED,
                    message="Invalid schema format",
                    duration=(datetime.now() - start).total_seconds()
                )
            
            # Check for required schema fields
            if "properties" not in server.schema:
                return ValidationCheck(
                    name="schema_check",
                    status=ValidationStatus.WARNING,
                    message="Schema missing properties definition",
                    duration=(datetime.now() - start).total_seconds()
                )
            
            return ValidationCheck(
                name="schema_check",
                status=ValidationStatus.PASSED,
                message="Schema validation passed",
                duration=(datetime.now() - start).total_seconds()
            )
            
        except Exception as e:
            return ValidationCheck(
                name="schema_check",
                status=ValidationStatus.FAILED,
                message=f"Schema validation error: {e}",
                duration=(datetime.now() - start).total_seconds()
            )
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected = type_map.get(expected_type)
        if not expected:
            return True  # Unknown type, assume valid
        
        return isinstance(value, expected)
    
    def _generate_recommendations(
        self,
        server: MCPServer,
        checks: List[ValidationCheck]
    ) -> List[str]:
        """Generate recommendations based on validation."""
        recommendations = []
        
        # Check for failed checks
        for check in checks:
            if check.status == ValidationStatus.FAILED:
                if check.name == "executable_check":
                    recommendations.append(f"Install {server.name} before use")
                elif check.name == "dependency_check":
                    missing = check.details.get("missing", [])
                    recommendations.append(f"Install missing dependencies: {', '.join(missing)}")
                elif check.name == "configuration_check":
                    recommendations.append("Review and fix configuration issues")
        
        # Check for warnings
        for check in checks:
            if check.status == ValidationStatus.WARNING:
                if check.name == "version_check":
                    recommendations.append("Consider updating to latest version")
        
        # General recommendations
        if not any(c.name == "operation_check" for c in checks):
            recommendations.append("Perform manual testing before production use")
        
        return recommendations
    
    def _extract_server_type(self, server_name: str) -> Optional[str]:
        """Extract server type from name."""
        known_types = ["filesystem", "github", "postgres", "puppeteer", "memory", "search"]
        
        for known_type in known_types:
            if known_type in server_name.lower():
                return known_type
        
        return None
    
    async def _run_command(
        self,
        cmd: List[str],
        timeout: int = 30
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
    
    async def batch_validate(
        self,
        servers: List[MCPServer],
        configs: Optional[Dict[str, Dict[str, Any]]] = None,
        deep_check: bool = True
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple servers.
        
        Args:
            servers: Servers to validate
            configs: Server configurations
            deep_check: Perform deep validation
            
        Returns:
            Dictionary of validation results
        """
        tasks = []
        
        for server in servers:
            config = configs.get(server.name) if configs else None
            tasks.append(self.validate_server(server, config, deep_check))
        
        results = await asyncio.gather(*tasks)
        
        return {
            result.server_name: result
            for result in results
        }
    
    def get_validation_summary(
        self,
        results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """
        Generate validation summary.
        
        Args:
            results: Validation results
            
        Returns:
            Summary statistics
        """
        total = len(results)
        passed = sum(1 for r in results if r.overall_status == ValidationStatus.PASSED)
        warnings = sum(1 for r in results if r.overall_status == ValidationStatus.WARNING)
        failed = sum(1 for r in results if r.overall_status == ValidationStatus.FAILED)
        
        usable = sum(1 for r in results if r.can_use)
        
        return {
            "total_validated": total,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "usable_servers": usable,
            "failed_servers": [r.server_name for r in results if r.overall_status == ValidationStatus.FAILED],
            "total_checks": sum(len(r.checks) for r in results),
            "average_duration": sum(r.total_duration for r in results) / total if total > 0 else 0
        }