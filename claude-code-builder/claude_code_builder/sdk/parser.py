"""Response parser for Claude Code SDK outputs."""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..models.base import BaseModel
from ..exceptions.base import SDKError

logger = logging.getLogger(__name__)


@dataclass
class ParsedResponse:
    """Parsed Claude Code response."""
    type: str
    content: Any
    metadata: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class ResponseParser:
    """Parses Claude Code SDK responses."""
    
    # Response type patterns
    PATTERNS = {
        "thinking": re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL),
        "answer": re.compile(r"<answer>(.*?)</answer>", re.DOTALL),
        "file_created": re.compile(r"Created file:\s*(.+)"),
        "file_modified": re.compile(r"Modified file:\s*(.+)"),
        "command_executed": re.compile(r"Executed:\s*(.+)"),
        "test_result": re.compile(r"Tests:\s*(\d+)\s*passed,\s*(\d+)\s*failed"),
        "error": re.compile(r"Error:\s*(.+)"),
        "warning": re.compile(r"Warning:\s*(.+)"),
        "token_usage": re.compile(r"Tokens:\s*input=(\d+),\s*output=(\d+)"),
        "cost": re.compile(r"Cost:\s*\$([0-9.]+)"),
        "artifact": re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    }
    
    def __init__(self):
        """Initialize response parser."""
        self.buffer = ""
        self.in_streaming_mode = False
    
    async def parse_streaming_response(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a streaming response line.
        
        Args:
            line: Response line
            
        Returns:
            Parsed response if complete
        """
        if not line.strip():
            return None
        
        self.in_streaming_mode = True
        
        # Handle JSON responses
        if line.startswith("{"):
            try:
                data = json.loads(line)
                return await self._process_json_response(data)
            except json.JSONDecodeError:
                # Might be partial JSON, add to buffer
                self.buffer += line
                return None
        
        # Handle structured responses
        if line.startswith("data: "):
            content = line[6:]  # Remove "data: " prefix
            try:
                data = json.loads(content)
                return await self._process_json_response(data)
            except json.JSONDecodeError:
                pass
        
        # Handle text responses
        return await self._process_text_response(line)
    
    async def parse_complete_response(self, response: str) -> Dict[str, Any]:
        """
        Parse a complete response.
        
        Args:
            response: Complete response text
            
        Returns:
            Parsed response
        """
        self.in_streaming_mode = False
        
        # Try JSON first
        try:
            data = json.loads(response)
            return await self._process_json_response(data)
        except json.JSONDecodeError:
            # Process as text
            return await self._process_text_response(response)
    
    async def _process_json_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process JSON response data."""
        response_type = data.get("type", "unknown")
        
        if response_type == "message":
            return {
                "type": "message",
                "content": data.get("content", ""),
                "role": data.get("role", "assistant"),
                "metadata": data.get("metadata", {})
            }
        
        elif response_type == "tool_use":
            return {
                "type": "tool_use",
                "tool": data.get("tool", ""),
                "arguments": data.get("arguments", {}),
                "result": data.get("result"),
                "metadata": data.get("metadata", {})
            }
        
        elif response_type == "error":
            return {
                "type": "error",
                "error": data.get("error", "Unknown error"),
                "code": data.get("code"),
                "metadata": data.get("metadata", {})
            }
        
        elif response_type == "status":
            return {
                "type": "status",
                "status": data.get("status", ""),
                "message": data.get("message", ""),
                "progress": data.get("progress"),
                "metadata": data.get("metadata", {})
            }
        
        elif response_type == "token_usage":
            return {
                "type": "token_usage",
                "input_tokens": data.get("input_tokens", 0),
                "output_tokens": data.get("output_tokens", 0),
                "total_tokens": data.get("total_tokens", 0),
                "metadata": data.get("metadata", {})
            }
        
        else:
            # Generic response
            return {
                "type": response_type,
                "data": data,
                "metadata": data.get("metadata", {})
            }
    
    async def _process_text_response(self, text: str) -> Dict[str, Any]:
        """Process text response."""
        # Extract structured content
        thinking = self._extract_pattern("thinking", text)
        answer = self._extract_pattern("answer", text)
        
        # Extract file operations
        files_created = self._extract_files("file_created", text)
        files_modified = self._extract_files("file_modified", text)
        
        # Extract commands
        commands = self._extract_commands(text)
        
        # Extract test results
        test_results = self._extract_test_results(text)
        
        # Extract errors and warnings
        errors = self._extract_pattern_list("error", text)
        warnings = self._extract_pattern_list("warning", text)
        
        # Extract token usage
        token_usage = self._extract_token_usage(text)
        
        # Extract artifacts
        artifacts = self._extract_artifacts(text)
        
        # Build response
        response = {
            "type": "composite",
            "content": text,
            "structured": {}
        }
        
        if thinking:
            response["structured"]["thinking"] = thinking
        if answer:
            response["structured"]["answer"] = answer
        if files_created:
            response["structured"]["files_created"] = files_created
        if files_modified:
            response["structured"]["files_modified"] = files_modified
        if commands:
            response["structured"]["commands_executed"] = commands
        if test_results:
            response["structured"]["test_results"] = test_results
        if errors:
            response["structured"]["errors"] = errors
        if warnings:
            response["structured"]["warnings"] = warnings
        if token_usage:
            response["structured"]["token_usage"] = token_usage
        if artifacts:
            response["structured"]["artifacts"] = artifacts
        
        # Determine primary type
        if errors:
            response["type"] = "error"
            response["success"] = False
        elif test_results:
            response["type"] = "test_result"
            response["success"] = test_results.get("failed", 0) == 0
        elif files_created or files_modified:
            response["type"] = "file_operation"
            response["success"] = True
        elif commands:
            response["type"] = "command_execution"
            response["success"] = True
        else:
            response["type"] = "message"
            response["success"] = True
        
        return response
    
    def _extract_pattern(self, pattern_name: str, text: str) -> Optional[str]:
        """Extract content matching a pattern."""
        pattern = self.PATTERNS.get(pattern_name)
        if not pattern:
            return None
        
        match = pattern.search(text)
        return match.group(1).strip() if match else None
    
    def _extract_pattern_list(self, pattern_name: str, text: str) -> List[str]:
        """Extract all matches for a pattern."""
        pattern = self.PATTERNS.get(pattern_name)
        if not pattern:
            return []
        
        return [match.group(1).strip() for match in pattern.finditer(text)]
    
    def _extract_files(self, pattern_name: str, text: str) -> List[str]:
        """Extract file paths."""
        return self._extract_pattern_list(pattern_name, text)
    
    def _extract_commands(self, text: str) -> List[Dict[str, Any]]:
        """Extract executed commands."""
        commands = []
        pattern = self.PATTERNS["command_executed"]
        
        for match in pattern.finditer(text):
            command = match.group(1).strip()
            commands.append({
                "command": command,
                "timestamp": datetime.now().isoformat()
            })
        
        return commands
    
    def _extract_test_results(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract test results."""
        pattern = self.PATTERNS["test_result"]
        match = pattern.search(text)
        
        if match:
            return {
                "passed": int(match.group(1)),
                "failed": int(match.group(2)),
                "total": int(match.group(1)) + int(match.group(2))
            }
        
        return None
    
    def _extract_token_usage(self, text: str) -> Optional[Dict[str, int]]:
        """Extract token usage."""
        pattern = self.PATTERNS["token_usage"]
        match = pattern.search(text)
        
        if match:
            input_tokens = int(match.group(1))
            output_tokens = int(match.group(2))
            return {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }
        
        return None
    
    def _extract_artifacts(self, text: str) -> List[Dict[str, Any]]:
        """Extract code artifacts."""
        artifacts = []
        pattern = self.PATTERNS["artifact"]
        
        for match in pattern.finditer(text):
            language = match.group(1) or "text"
            content = match.group(2).strip()
            
            artifacts.append({
                "language": language,
                "content": content,
                "lines": content.count("\n") + 1
            })
        
        return artifacts
    
    async def extract_artifacts(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract code artifacts from a response.
        
        Args:
            response: Response to extract from
            
        Returns:
            List of artifacts
        """
        artifacts = []
        
        # Check structured artifacts
        if "structured" in response and "artifacts" in response["structured"]:
            artifacts.extend(response["structured"]["artifacts"])
        
        # Check tool results
        if response.get("type") == "tool_use" and "result" in response:
            result = response["result"]
            if isinstance(result, str):
                # Extract from result text
                extracted = self._extract_artifacts(result)
                artifacts.extend(extracted)
        
        # Check message content
        if response.get("type") == "message" and "content" in response:
            extracted = self._extract_artifacts(response["content"])
            artifacts.extend(extracted)
        
        return artifacts
    
    async def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate a response structure.
        
        Args:
            response: Response to validate
            
        Returns:
            True if valid
        """
        # Check required fields
        if "type" not in response:
            logger.error("Response missing 'type' field")
            return False
        
        # Validate by type
        response_type = response["type"]
        
        if response_type == "error":
            if "error" not in response:
                logger.error("Error response missing 'error' field")
                return False
        
        elif response_type == "tool_use":
            if "tool" not in response:
                logger.error("Tool use response missing 'tool' field")
                return False
        
        elif response_type == "message":
            if "content" not in response:
                logger.error("Message response missing 'content' field")
                return False
        
        return True
    
    def reset_buffer(self) -> None:
        """Reset parser buffer."""
        self.buffer = ""
        self.in_streaming_mode = False
    
    def extract_cost(self, text: str) -> Optional[float]:
        """Extract cost from text."""
        pattern = self.PATTERNS["cost"]
        match = pattern.search(text)
        
        if match:
            return float(match.group(1))
        
        return None
    
    def parse_error_response(self, error: str) -> Dict[str, Any]:
        """
        Parse an error response.
        
        Args:
            error: Error text
            
        Returns:
            Parsed error response
        """
        # Common error patterns
        error_patterns = {
            "timeout": re.compile(r"timeout|timed out", re.IGNORECASE),
            "rate_limit": re.compile(r"rate limit|too many requests", re.IGNORECASE),
            "authentication": re.compile(r"auth|unauthorized|forbidden", re.IGNORECASE),
            "not_found": re.compile(r"not found|404", re.IGNORECASE),
            "validation": re.compile(r"invalid|validation|bad request", re.IGNORECASE),
            "connection": re.compile(r"connection|network|offline", re.IGNORECASE)
        }
        
        error_type = "unknown"
        for type_name, pattern in error_patterns.items():
            if pattern.search(error):
                error_type = type_name
                break
        
        return {
            "type": "error",
            "error": error,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat(),
            "success": False
        }