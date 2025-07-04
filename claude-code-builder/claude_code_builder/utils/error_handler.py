"""Error handling utilities for Claude Code Builder."""
import sys
import traceback
import logging
from typing import Optional, Dict, Any, List, Callable, Type, Union, Tuple
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
import json

from ..exceptions.base import ClaudeCodeBuilderError
from ..logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ErrorContext:
    """Context information for errors."""
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    traceback: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    handled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'error_type': self.error_type,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'traceback': self.traceback,
            'context': self.context,
            'handled': self.handled
        }


class ErrorHandler:
    """Central error handling utilities."""
    
    def __init__(self):
        """Initialize error handler."""
        self._error_history: List[ErrorContext] = []
        self._error_handlers: Dict[Type[Exception], List[Callable]] = {}
        self._fallback_handler: Optional[Callable] = None
        
    def register_handler(
        self,
        exception_type: Type[Exception],
        handler: Callable[[Exception, ErrorContext], None]
    ) -> None:
        """Register an error handler for specific exception type.
        
        Args:
            exception_type: Exception type to handle
            handler: Handler function
        """
        if exception_type not in self._error_handlers:
            self._error_handlers[exception_type] = []
        
        self._error_handlers[exception_type].append(handler)
        logger.debug(f"Registered handler for {exception_type.__name__}")
    
    def set_fallback_handler(
        self,
        handler: Callable[[Exception, ErrorContext], None]
    ) -> None:
        """Set fallback handler for unhandled exceptions.
        
        Args:
            handler: Fallback handler function
        """
        self._fallback_handler = handler
        logger.debug("Set fallback error handler")
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = True
    ) -> ErrorContext:
        """Handle an error with registered handlers.
        
        Args:
            error: Exception to handle
            context: Additional context
            reraise: Whether to reraise after handling
            
        Returns:
            Error context
        """
        # Create error context
        error_ctx = ErrorContext(
            error_type=type(error).__name__,
            message=str(error),
            traceback=traceback.format_exc(),
            context=context or {}
        )
        
        # Add to history
        self._error_history.append(error_ctx)
        
        # Find and execute handlers
        handled = False
        for exc_type, handlers in self._error_handlers.items():
            if isinstance(error, exc_type):
                for handler in handlers:
                    try:
                        handler(error, error_ctx)
                        handled = True
                    except Exception as e:
                        logger.error(f"Error in handler: {e}")
        
        # Use fallback if not handled
        if not handled and self._fallback_handler:
            try:
                self._fallback_handler(error, error_ctx)
                handled = True
            except Exception as e:
                logger.error(f"Error in fallback handler: {e}")
        
        error_ctx.handled = handled
        
        # Log if not handled
        if not handled:
            logger.error(f"Unhandled error: {error}", exc_info=True)
        
        # Reraise if requested
        if reraise:
            raise error
        
        return error_ctx
    
    @contextmanager
    def error_context(
        self,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        suppress: bool = False
    ):
        """Context manager for error handling.
        
        Args:
            operation: Operation description
            context: Additional context
            suppress: Suppress exceptions
            
        Yields:
            Error context if error occurs
        """
        error_context = None
        
        try:
            yield error_context
        except Exception as e:
            # Add operation to context
            ctx = context or {}
            ctx['operation'] = operation
            
            # Handle error
            error_context = self.handle_error(e, ctx, reraise=not suppress)
            
            if not suppress:
                raise
    
    def retry_on_error(
        self,
        max_attempts: int = 3,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        delay: float = 0.0,
        backoff: float = 1.0
    ):
        """Decorator for retrying on specific errors.
        
        Args:
            max_attempts: Maximum retry attempts
            exceptions: Exception types to retry on
            delay: Initial delay between retries
            backoff: Backoff multiplier
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                current_delay = delay
                last_error = None
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_error = e
                        
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"Retry {attempt + 1}/{max_attempts} for {func.__name__}: {e}"
                            )
                            
                            if current_delay > 0:
                                import time
                                time.sleep(current_delay)
                                current_delay *= backoff
                        else:
                            # Last attempt failed
                            self.handle_error(
                                e,
                                context={
                                    'function': func.__name__,
                                    'attempts': max_attempts,
                                    'args': str(args),
                                    'kwargs': str(kwargs)
                                },
                                reraise=True
                            )
                
                # Should not reach here
                if last_error:
                    raise last_error
            
            return wrapper
        return decorator
    
    def ignore_errors(
        self,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        default: Any = None,
        log: bool = True
    ):
        """Decorator to ignore specific errors.
        
        Args:
            exceptions: Exception types to ignore
            default: Default return value
            log: Whether to log ignored errors
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if log:
                        logger.debug(f"Ignored error in {func.__name__}: {e}")
                    
                    # Record but don't raise
                    self.handle_error(
                        e,
                        context={'function': func.__name__},
                        reraise=False
                    )
                    
                    return default
            
            return wrapper
        return decorator
    
    def get_error_history(
        self,
        limit: Optional[int] = None,
        error_type: Optional[str] = None
    ) -> List[ErrorContext]:
        """Get error history.
        
        Args:
            limit: Maximum number of errors to return
            error_type: Filter by error type
            
        Returns:
            List of error contexts
        """
        history = self._error_history
        
        # Filter by type if specified
        if error_type:
            history = [e for e in history if e.error_type == error_type]
        
        # Apply limit
        if limit:
            history = history[-limit:]
        
        return history
    
    def clear_history(self) -> None:
        """Clear error history."""
        self._error_history.clear()
        logger.debug("Cleared error history")
    
    def export_errors(
        self,
        path: Optional[str] = None,
        format: str = 'json'
    ) -> str:
        """Export error history.
        
        Args:
            path: Output file path
            format: Export format (json, text)
            
        Returns:
            Exported content
        """
        if format == 'json':
            content = json.dumps(
                [e.to_dict() for e in self._error_history],
                indent=2,
                default=str
            )
        else:  # text format
            lines = []
            for error in self._error_history:
                lines.append(f"{'=' * 60}")
                lines.append(f"Error: {error.error_type}")
                lines.append(f"Time: {error.timestamp}")
                lines.append(f"Message: {error.message}")
                lines.append(f"Handled: {error.handled}")
                
                if error.context:
                    lines.append(f"Context: {json.dumps(error.context, indent=2)}")
                
                if error.traceback:
                    lines.append("Traceback:")
                    lines.append(error.traceback)
            
            content = '\n'.join(lines)
        
        # Save to file if path provided
        if path:
            with open(path, 'w') as f:
                f.write(content)
            logger.info(f"Exported errors to {path}")
        
        return content


# Global error handler instance
_error_handler = ErrorHandler()


def handle_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    reraise: bool = True
) -> ErrorContext:
    """Handle an error using global handler.
    
    Args:
        error: Exception to handle
        context: Additional context
        reraise: Whether to reraise
        
    Returns:
        Error context
    """
    return _error_handler.handle_error(error, context, reraise)


def register_handler(
    exception_type: Type[Exception],
    handler: Callable[[Exception, ErrorContext], None]
) -> None:
    """Register error handler with global handler.
    
    Args:
        exception_type: Exception type
        handler: Handler function
    """
    _error_handler.register_handler(exception_type, handler)


def retry_on_error(
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    delay: float = 0.0,
    backoff: float = 1.0
):
    """Retry decorator using global handler.
    
    Args:
        max_attempts: Maximum attempts
        exceptions: Exceptions to retry on
        delay: Initial delay
        backoff: Backoff multiplier
        
    Returns:
        Decorator
    """
    return _error_handler.retry_on_error(max_attempts, exceptions, delay, backoff)


def ignore_errors(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    default: Any = None,
    log: bool = True
):
    """Ignore errors decorator using global handler.
    
    Args:
        exceptions: Exceptions to ignore
        default: Default return value
        log: Whether to log
        
    Returns:
        Decorator
    """
    return _error_handler.ignore_errors(exceptions, default, log)


@contextmanager
def error_context(
    operation: str,
    context: Optional[Dict[str, Any]] = None,
    suppress: bool = False
):
    """Error context manager using global handler.
    
    Args:
        operation: Operation description
        context: Additional context
        suppress: Suppress exceptions
        
    Yields:
        Error context if error occurs
    """
    with _error_handler.error_context(operation, context, suppress) as ctx:
        yield ctx


def format_exception(
    exc: Exception,
    include_traceback: bool = True,
    max_traceback_lines: Optional[int] = None
) -> str:
    """Format exception for display.
    
    Args:
        exc: Exception to format
        include_traceback: Include traceback
        max_traceback_lines: Limit traceback lines
        
    Returns:
        Formatted exception string
    """
    lines = [f"{type(exc).__name__}: {exc}"]
    
    if include_traceback:
        tb_lines = traceback.format_exc().splitlines()
        
        if max_traceback_lines and len(tb_lines) > max_traceback_lines:
            tb_lines = tb_lines[:max_traceback_lines] + ["..."]
        
        lines.extend(tb_lines)
    
    return '\n'.join(lines)