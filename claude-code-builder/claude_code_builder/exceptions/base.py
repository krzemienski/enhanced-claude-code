"""Base exception classes for Claude Code Builder."""

from typing import Optional, Dict, Any
import traceback


class ClaudeCodeBuilderError(Exception):
    """Base exception for all Claude Code Builder errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            cause: The underlying exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
        
        if cause:
            self.details["cause"] = str(cause)
            self.details["cause_type"] = type(cause).__name__
            self.details["traceback"] = traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class PlanningError(ClaudeCodeBuilderError):
    """Raised when AI planning fails."""
    
    def __init__(self, message: str, phase: Optional[str] = None, **kwargs):
        """Initialize planning error.
        
        Args:
            message: Error message
            phase: The planning phase that failed
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if phase:
            details["phase"] = phase
        kwargs["details"] = details
        super().__init__(message, error_code="PLANNING_ERROR", **kwargs)


class ExecutionError(ClaudeCodeBuilderError):
    """Raised when project execution fails."""
    
    def __init__(
        self,
        message: str,
        phase: Optional[str] = None,
        task: Optional[str] = None,
        **kwargs
    ):
        """Initialize execution error.
        
        Args:
            message: Error message
            phase: The execution phase that failed
            task: The specific task that failed
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if phase:
            details["phase"] = phase
        if task:
            details["task"] = task
        kwargs["details"] = details
        super().__init__(message, error_code="EXECUTION_ERROR", **kwargs)


class ValidationError(ClaudeCodeBuilderError):
    """Raised when validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        """Initialize validation error.
        
        Args:
            message: Error message
            field: The field that failed validation
            value: The invalid value
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        kwargs["details"] = details
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)


class TestingError(ClaudeCodeBuilderError):
    """Raised when testing fails."""
    
    def __init__(
        self,
        message: str,
        test_stage: Optional[str] = None,
        test_name: Optional[str] = None,
        **kwargs
    ):
        """Initialize testing error.
        
        Args:
            message: Error message
            test_stage: The testing stage that failed
            test_name: The specific test that failed
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if test_stage:
            details["test_stage"] = test_stage
        if test_name:
            details["test_name"] = test_name
        kwargs["details"] = details
        super().__init__(message, error_code="TESTING_ERROR", **kwargs)


class SDKError(ClaudeCodeBuilderError):
    """Raised when Claude Code SDK operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        """Initialize SDK error.
        
        Args:
            message: Error message
            operation: The SDK operation that failed
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
        kwargs["details"] = details
        super().__init__(message, error_code="SDK_ERROR", **kwargs)


class MCPError(ClaudeCodeBuilderError):
    """Raised when MCP operations fail."""
    
    def __init__(self, message: str, server: Optional[str] = None, **kwargs):
        """Initialize MCP error.
        
        Args:
            message: Error message
            server: The MCP server that caused the error
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if server:
            details["server"] = server
        kwargs["details"] = details
        super().__init__(message, error_code="MCP_ERROR", **kwargs)


class ResearchError(ClaudeCodeBuilderError):
    """Raised when research operations fail."""
    
    def __init__(self, message: str, agent: Optional[str] = None, **kwargs):
        """Initialize research error.
        
        Args:
            message: Error message
            agent: The research agent that failed
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if agent:
            details["agent"] = agent
        kwargs["details"] = details
        super().__init__(message, error_code="RESEARCH_ERROR", **kwargs)


class MemoryError(ClaudeCodeBuilderError):
    """Raised when memory operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        """Initialize memory error.
        
        Args:
            message: Error message
            operation: The memory operation that failed
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
        kwargs["details"] = details
        super().__init__(message, error_code="MEMORY_ERROR", **kwargs)


class MonitoringError(ClaudeCodeBuilderError):
    """Raised when monitoring operations fail."""
    
    def __init__(self, message: str, component: Optional[str] = None, **kwargs):
        """Initialize monitoring error.
        
        Args:
            message: Error message
            component: The monitoring component that failed
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if component:
            details["component"] = component
        kwargs["details"] = details
        super().__init__(message, error_code="MONITORING_ERROR", **kwargs)


class TimeoutError(ClaudeCodeBuilderError):
    """Raised when an operation times out."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        """Initialize timeout error.
        
        Args:
            message: Error message
            operation: The operation that timed out
            timeout_seconds: The timeout duration in seconds
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        kwargs["details"] = details
        super().__init__(message, error_code="TIMEOUT_ERROR", **kwargs)


class RecoveryError(ClaudeCodeBuilderError):
    """Raised when recovery operations fail."""
    
    def __init__(
        self,
        message: str,
        checkpoint: Optional[str] = None,
        recovery_attempt: Optional[int] = None,
        **kwargs
    ):
        """Initialize recovery error.
        
        Args:
            message: Error message
            checkpoint: The checkpoint that failed to recover
            recovery_attempt: The recovery attempt number
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if checkpoint:
            details["checkpoint"] = checkpoint
        if recovery_attempt:
            details["recovery_attempt"] = recovery_attempt
        kwargs["details"] = details
        super().__init__(message, error_code="RECOVERY_ERROR", **kwargs)


class FileOperationError(ClaudeCodeBuilderError):
    """Raised when file operations fail."""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        """Initialize file operation error.
        
        Args:
            message: Error message
            file_path: The file path that caused the error
            operation: The file operation that failed
            **kwargs: Additional error details
        """
        details = kwargs.get("details", {})
        if file_path:
            details["file_path"] = file_path
        if operation:
            details["operation"] = operation
        kwargs["details"] = details
        super().__init__(message, error_code="FILE_OPERATION_ERROR", **kwargs)