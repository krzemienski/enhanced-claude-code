"""Claude Code SDK client wrapper for v3.0."""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List, AsyncIterator, Union
from datetime import datetime
from pathlib import Path
import subprocess
import os

from ..models.base import BaseModel
from ..models.cost import CostEntry, CostCategory
from ..exceptions.base import ClaudeCodeBuilderError, SDKError
from ..config.settings import AIConfig
from .session import SessionManager, Session
from .parser import ResponseParser
from .metrics import SDKMetrics

logger = logging.getLogger(__name__)


class ClaudeCodeClient:
    """Wrapper for Claude Code SDK operations."""
    
    def __init__(self, config: AIConfig = None):
        """
        Initialize Claude Code client.
        
        Args:
            config: SDK configuration
        """
        self.config = config
        self.session_manager = SessionManager(config)
        self.response_parser = ResponseParser()
        self.metrics = SDKMetrics()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the SDK client."""
        if self._initialized:
            return
        
        logger.info("Initializing Claude Code SDK client")
        
        # Verify Claude Code CLI is installed
        if not await self._verify_cli_installation():
            raise SDKError("Claude Code CLI not found. Please install with: npm install -g @anthropic-ai/claude-code")
        
        # Initialize session manager
        await self.session_manager.initialize()
        
        self._initialized = True
        logger.info("Claude Code SDK client initialized successfully")
    
    async def _verify_cli_installation(self) -> bool:
        """Verify Claude Code CLI is installed."""
        try:
            result = await self._run_command(["claude-code", "--version"])
            logger.info(f"Claude Code CLI version: {result.stdout.strip()}")
            return True
        except Exception as e:
            logger.error(f"Failed to verify Claude Code CLI: {e}")
            return False
    
    async def create_session(
        self,
        project_path: Path,
        instructions: Optional[str] = None,
        mcp_servers: Optional[List[Dict[str, Any]]] = None
    ) -> Session:
        """
        Create a new Claude Code session.
        
        Args:
            project_path: Path to project directory
            instructions: Custom instructions for the session
            mcp_servers: MCP server configurations
            
        Returns:
            Created session
        """
        if not self._initialized:
            await self.initialize()
        
        session = await self.session_manager.create_session(
            project_path=project_path,
            instructions=instructions,
            mcp_servers=mcp_servers
        )
        
        logger.info(f"Created session {session.id} for project {project_path}")
        return session
    
    async def execute_command(
        self,
        session: Session,
        command: str,
        stream: bool = True,
        timeout: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute a command in a Claude Code session.
        
        Args:
            session: Active session
            command: Command to execute
            stream: Whether to stream responses
            timeout: Command timeout in seconds
            
        Yields:
            Parsed response chunks
        """
        if not session.active:
            raise SDKError(f"Session {session.id} is not active")
        
        start_time = datetime.now()
        self.metrics.record_command_start(session.id, command)
        
        try:
            # Prepare command arguments
            cmd_args = [
                "claude-code",
                "--project", str(session.project_path),
                "--session-id", session.id
            ]
            
            if session.instructions:
                cmd_args.extend(["--instructions", session.instructions])
            
            if session.mcp_servers:
                cmd_args.extend(["--mcp-servers", json.dumps(session.mcp_servers)])
            
            if timeout:
                cmd_args.extend(["--timeout", str(timeout)])
            
            if stream:
                cmd_args.append("--stream")
            
            # Add the actual command
            cmd_args.extend(["--", command])
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(session.project_path)
            )
            
            if stream:
                # Stream output
                async for line in self._stream_output(process):
                    parsed = await self.response_parser.parse_streaming_response(line)
                    if parsed:
                        yield parsed
                        
                        # Track metrics
                        if parsed.get("type") == "token_usage":
                            self.metrics.record_token_usage(
                                session.id,
                                parsed.get("input_tokens", 0),
                                parsed.get("output_tokens", 0)
                            )
            else:
                # Wait for completion
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    raise SDKError(f"Command failed: {error_msg}")
                
                # Parse complete response
                response = await self.response_parser.parse_complete_response(
                    stdout.decode()
                )
                yield response
            
            # Record completion
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_command_completion(session.id, command, duration)
            
        except Exception as e:
            # Record error
            self.metrics.record_command_error(session.id, command, str(e))
            raise SDKError(f"Failed to execute command: {e}") from e
    
    async def _stream_output(self, process: asyncio.subprocess.Process) -> AsyncIterator[str]:
        """Stream output from a subprocess."""
        if not process.stdout:
            return
        
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            yield line.decode().strip()
    
    async def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=process.returncode,
            stdout=stdout.decode() if stdout else "",
            stderr=stderr.decode() if stderr else ""
        )
    
    async def estimate_cost(
        self,
        session: Session,
        command: str,
        model: str = "claude-3-opus-20240229"
    ) -> CostEntry:
        """
        Estimate cost for a command.
        
        Args:
            session: Active session
            command: Command to estimate
            model: Model to use for estimation
            
        Returns:
            Cost estimate
        """
        # Estimate based on command complexity
        base_tokens = len(command.split()) * 4  # Rough estimate
        
        # Add context from session
        if session.context:
            base_tokens += len(str(session.context).split()) * 2
        
        # Model-specific pricing (example rates)
        model_costs = {
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125}
        }
        
        costs = model_costs.get(model, model_costs["claude-3-opus-20240229"])
        
        # Estimate output tokens (usually 2-3x input)
        output_tokens = base_tokens * 2.5
        
        # Calculate costs
        input_cost = (base_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]
        total_cost = input_cost + output_cost
        
        return CostEntry(
            total_cost=total_cost,
            breakdown={
                CostCategory.API: total_cost,
                CostCategory.COMPUTE: 0.0
            },
            metadata={
                "model": model,
                "estimated_input_tokens": base_tokens,
                "estimated_output_tokens": int(output_tokens)
            }
        )
    
    async def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get metrics for a session."""
        return self.metrics.get_session_metrics(session_id)
    
    async def close_session(self, session: Session) -> None:
        """Close a Claude Code session."""
        await self.session_manager.close_session(session)
        logger.info(f"Closed session {session.id}")
    
    async def cleanup(self) -> None:
        """Cleanup client resources."""
        if self._initialized:
            await self.session_manager.cleanup()
            self._initialized = False
            logger.info("Claude Code SDK client cleaned up")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    def configure_tools(self, tools: List[Dict[str, Any]]) -> None:
        """
        Configure available tools for Claude Code.
        
        Args:
            tools: List of tool configurations
        """
        self.config.available_tools = tools
        logger.info(f"Configured {len(tools)} tools for Claude Code")
    
    def set_model(self, model: str) -> None:
        """
        Set the model to use.
        
        Args:
            model: Model identifier
        """
        self.config.model = model
        logger.info(f"Set Claude Code model to {model}")
    
    def set_max_turns(self, max_turns: int) -> None:
        """
        Set maximum conversation turns.
        
        Args:
            max_turns: Maximum number of turns
        """
        self.config.max_turns = max_turns
        logger.info(f"Set max turns to {max_turns}")
    
    async def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate a Claude Code response.
        
        Args:
            response: Response to validate
            
        Returns:
            True if valid
        """
        return await self.response_parser.validate_response(response)
    
    async def extract_artifacts(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract code artifacts from response.
        
        Args:
            response: Response containing artifacts
            
        Returns:
            List of extracted artifacts
        """
        return await self.response_parser.extract_artifacts(response)