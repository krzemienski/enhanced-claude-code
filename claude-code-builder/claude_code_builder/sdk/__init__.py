"""Claude Code SDK Integration for v3.0."""

from .client import ClaudeCodeClient
from .session import Session, SessionManager
from .tools import Tool, ToolCategory, ToolManager
from .parser import ResponseParser, ParsedResponse
from .error_handler import SDKErrorHandler, ErrorSeverity, RecoveryStrategy
from .metrics import SDKMetrics, CommandMetrics, SessionMetrics
from .context_manager import ContextManager, ContextEntry

__all__ = [
    # Client
    "ClaudeCodeClient",
    
    # Session management
    "Session",
    "SessionManager",
    
    # Tools
    "Tool",
    "ToolCategory",
    "ToolManager",
    
    # Response parsing
    "ResponseParser",
    "ParsedResponse",
    
    # Error handling
    "SDKErrorHandler",
    "ErrorSeverity",
    "RecoveryStrategy",
    
    # Metrics
    "SDKMetrics",
    "CommandMetrics",
    "SessionMetrics",
    
    # Context management
    "ContextManager",
    "ContextEntry",
]