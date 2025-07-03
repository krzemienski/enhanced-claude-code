"""Error handling for Claude Code SDK operations."""

import logging
import asyncio
from typing import Optional, Dict, Any, List, Type, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import traceback

from ..exceptions.base import (
    ClaudeCodeBuilderError,
    SDKError,
    TimeoutError,
    RateLimitError,
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"  # Can continue with warnings
    MEDIUM = "medium"  # May impact functionality
    HIGH = "high"  # Critical but recoverable
    CRITICAL = "critical"  # Fatal, must stop


class RecoveryStrategy(Enum):
    """Error recovery strategies."""
    RETRY = "retry"  # Retry the operation
    RETRY_WITH_BACKOFF = "retry_with_backoff"  # Retry with exponential backoff
    SKIP = "skip"  # Skip and continue
    FALLBACK = "fallback"  # Use fallback approach
    ABORT = "abort"  # Abort operation
    IGNORE = "ignore"  # Ignore and continue


@dataclass
class ErrorContext:
    """Context for an error."""
    error_type: Type[Exception]
    error_message: str
    severity: ErrorSeverity
    operation: str
    timestamp: datetime
    session_id: Optional[str] = None
    command: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize error context."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RecoveryAttempt:
    """Record of a recovery attempt."""
    strategy: RecoveryStrategy
    timestamp: datetime
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


class SDKErrorHandler:
    """Handles errors in Claude Code SDK operations."""
    
    # Error to recovery strategy mapping
    ERROR_STRATEGIES = {
        TimeoutError: RecoveryStrategy.RETRY_WITH_BACKOFF,
        RateLimitError: RecoveryStrategy.RETRY_WITH_BACKOFF,
        AuthenticationError: RecoveryStrategy.ABORT,
        ResourceNotFoundError: RecoveryStrategy.SKIP,
        ValidationError: RecoveryStrategy.ABORT,
        ConnectionError: RecoveryStrategy.RETRY_WITH_BACKOFF,
        SDKError: RecoveryStrategy.FALLBACK
    }
    
    # Error to severity mapping
    ERROR_SEVERITIES = {
        TimeoutError: ErrorSeverity.MEDIUM,
        RateLimitError: ErrorSeverity.MEDIUM,
        AuthenticationError: ErrorSeverity.CRITICAL,
        ResourceNotFoundError: ErrorSeverity.LOW,
        ValidationError: ErrorSeverity.HIGH,
        ConnectionError: ErrorSeverity.HIGH,
        SDKError: ErrorSeverity.MEDIUM
    }
    
    def __init__(
        self,
        max_retries: int = 3,
        base_backoff: float = 1.0,
        max_backoff: float = 60.0
    ):
        """
        Initialize error handler.
        
        Args:
            max_retries: Maximum retry attempts
            base_backoff: Base backoff time in seconds
            max_backoff: Maximum backoff time in seconds
        """
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self.error_history: List[ErrorContext] = []
        self.recovery_attempts: Dict[str, List[RecoveryAttempt]] = {}
        self.custom_handlers: Dict[Type[Exception], Callable] = {}
    
    async def handle_error(
        self,
        error: Exception,
        operation: str,
        session_id: Optional[str] = None,
        command: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[RecoveryStrategy]:
        """
        Handle an error and determine recovery strategy.
        
        Args:
            error: The exception that occurred
            operation: Operation that failed
            session_id: Session ID if applicable
            command: Command that failed if applicable
            context: Additional error context
            
        Returns:
            Recovery strategy to use
        """
        # Create error context
        error_context = ErrorContext(
            error_type=type(error),
            error_message=str(error),
            severity=self._get_error_severity(error),
            operation=operation,
            timestamp=datetime.now(),
            session_id=session_id,
            command=command,
            stack_trace=traceback.format_exc(),
            metadata=context or {}
        )
        
        # Log error
        self._log_error(error_context)
        
        # Store in history
        self.error_history.append(error_context)
        
        # Check for custom handler
        if type(error) in self.custom_handlers:
            try:
                return await self.custom_handlers[type(error)](error, error_context)
            except Exception as e:
                logger.error(f"Custom error handler failed: {e}")
        
        # Determine recovery strategy
        strategy = self._get_recovery_strategy(error)
        
        # Record strategy
        operation_key = f"{operation}:{session_id or 'global'}"
        if operation_key not in self.recovery_attempts:
            self.recovery_attempts[operation_key] = []
        
        return strategy
    
    async def execute_with_recovery(
        self,
        operation: Callable,
        operation_name: str,
        session_id: Optional[str] = None,
        fallback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """
        Execute an operation with error recovery.
        
        Args:
            operation: Operation to execute
            operation_name: Name of the operation
            session_id: Session ID if applicable
            fallback: Fallback operation if main fails
            **kwargs: Arguments for the operation
            
        Returns:
            Operation result
        """
        attempt = 0
        last_error = None
        backoff = self.base_backoff
        
        while attempt < self.max_retries:
            try:
                # Execute operation
                result = await operation(**kwargs)
                
                # Record successful recovery if this was a retry
                if attempt > 0:
                    self._record_recovery(
                        operation_name,
                        session_id,
                        RecoveryStrategy.RETRY,
                        success=True,
                        result=result
                    )
                
                return result
                
            except Exception as error:
                last_error = error
                
                # Handle error
                strategy = await self.handle_error(
                    error=error,
                    operation=operation_name,
                    session_id=session_id,
                    context={"attempt": attempt + 1, "kwargs": kwargs}
                )
                
                # Apply recovery strategy
                if strategy == RecoveryStrategy.ABORT:
                    raise
                
                elif strategy == RecoveryStrategy.SKIP:
                    logger.warning(f"Skipping operation {operation_name} due to error")
                    return None
                
                elif strategy == RecoveryStrategy.IGNORE:
                    logger.warning(f"Ignoring error in {operation_name}")
                    return None
                
                elif strategy == RecoveryStrategy.FALLBACK and fallback:
                    logger.info(f"Using fallback for {operation_name}")
                    try:
                        result = await fallback(**kwargs)
                        self._record_recovery(
                            operation_name,
                            session_id,
                            RecoveryStrategy.FALLBACK,
                            success=True,
                            result=result
                        )
                        return result
                    except Exception as fallback_error:
                        logger.error(f"Fallback failed: {fallback_error}")
                        raise last_error
                
                elif strategy in (RecoveryStrategy.RETRY, RecoveryStrategy.RETRY_WITH_BACKOFF):
                    attempt += 1
                    
                    if attempt >= self.max_retries:
                        break
                    
                    # Apply backoff if needed
                    if strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                        logger.info(f"Retrying {operation_name} in {backoff}s (attempt {attempt}/{self.max_retries})")
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, self.max_backoff)
                    else:
                        logger.info(f"Retrying {operation_name} (attempt {attempt}/{self.max_retries})")
                
                else:
                    # Unknown strategy, abort
                    raise
        
        # Max retries exceeded
        self._record_recovery(
            operation_name,
            session_id,
            RecoveryStrategy.RETRY,
            success=False,
            error=str(last_error)
        )
        
        raise SDKError(f"Operation {operation_name} failed after {attempt} attempts: {last_error}")
    
    def register_custom_handler(
        self,
        error_type: Type[Exception],
        handler: Callable[[Exception, ErrorContext], RecoveryStrategy]
    ) -> None:
        """
        Register a custom error handler.
        
        Args:
            error_type: Type of error to handle
            handler: Handler function
        """
        self.custom_handlers[error_type] = handler
        logger.info(f"Registered custom handler for {error_type.__name__}")
    
    def _get_error_severity(self, error: Exception) -> ErrorSeverity:
        """Get severity level for an error."""
        error_type = type(error)
        return self.ERROR_SEVERITIES.get(error_type, ErrorSeverity.MEDIUM)
    
    def _get_recovery_strategy(self, error: Exception) -> RecoveryStrategy:
        """Get recovery strategy for an error."""
        error_type = type(error)
        
        # Check exact type match
        if error_type in self.ERROR_STRATEGIES:
            return self.ERROR_STRATEGIES[error_type]
        
        # Check inheritance
        for error_class, strategy in self.ERROR_STRATEGIES.items():
            if isinstance(error, error_class):
                return strategy
        
        # Default strategy
        return RecoveryStrategy.RETRY
    
    def _log_error(self, context: ErrorContext) -> None:
        """Log an error with appropriate level."""
        message = (
            f"Error in {context.operation}: {context.error_message} "
            f"(severity: {context.severity.value})"
        )
        
        if context.session_id:
            message += f" [session: {context.session_id}]"
        
        if context.command:
            message += f" [command: {context.command}]"
        
        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical(message)
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(message)
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(message)
        else:
            logger.info(message)
        
        # Log stack trace for high severity errors
        if context.severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            logger.debug(f"Stack trace:\n{context.stack_trace}")
    
    def _record_recovery(
        self,
        operation: str,
        session_id: Optional[str],
        strategy: RecoveryStrategy,
        success: bool,
        result: Optional[Any] = None,
        error: Optional[str] = None
    ) -> None:
        """Record a recovery attempt."""
        operation_key = f"{operation}:{session_id or 'global'}"
        
        if operation_key not in self.recovery_attempts:
            self.recovery_attempts[operation_key] = []
        
        self.recovery_attempts[operation_key].append(
            RecoveryAttempt(
                strategy=strategy,
                timestamp=datetime.now(),
                success=success,
                result=result,
                error=error
            )
        )
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        stats = {
            "total_errors": len(self.error_history),
            "errors_by_type": {},
            "errors_by_severity": {},
            "errors_by_operation": {},
            "recovery_success_rate": 0.0
        }
        
        # Count errors by type
        for error in self.error_history:
            error_type = error.error_type.__name__
            stats["errors_by_type"][error_type] = stats["errors_by_type"].get(error_type, 0) + 1
            
            severity = error.severity.value
            stats["errors_by_severity"][severity] = stats["errors_by_severity"].get(severity, 0) + 1
            
            operation = error.operation
            stats["errors_by_operation"][operation] = stats["errors_by_operation"].get(operation, 0) + 1
        
        # Calculate recovery success rate
        total_recoveries = 0
        successful_recoveries = 0
        
        for attempts in self.recovery_attempts.values():
            for attempt in attempts:
                total_recoveries += 1
                if attempt.success:
                    successful_recoveries += 1
        
        if total_recoveries > 0:
            stats["recovery_success_rate"] = successful_recoveries / total_recoveries
        
        return stats
    
    def get_recent_errors(
        self,
        limit: int = 10,
        severity: Optional[ErrorSeverity] = None,
        session_id: Optional[str] = None
    ) -> List[ErrorContext]:
        """Get recent errors."""
        errors = self.error_history
        
        # Filter by session
        if session_id:
            errors = [e for e in errors if e.session_id == session_id]
        
        # Filter by severity
        if severity:
            errors = [e for e in errors if e.severity == severity]
        
        # Sort by timestamp and limit
        errors.sort(key=lambda e: e.timestamp, reverse=True)
        return errors[:limit]
    
    def clear_error_history(self) -> None:
        """Clear error history."""
        self.error_history.clear()
        self.recovery_attempts.clear()
        logger.info("Cleared error history")
    
    async def handle_rate_limit(
        self,
        error: RateLimitError,
        retry_after: Optional[int] = None
    ) -> None:
        """
        Handle rate limit errors specifically.
        
        Args:
            error: Rate limit error
            retry_after: Seconds to wait before retry
        """
        wait_time = retry_after or 60  # Default to 1 minute
        
        logger.warning(f"Rate limit hit, waiting {wait_time}s: {error}")
        await asyncio.sleep(wait_time)
    
    def create_error_report(self) -> str:
        """Create a detailed error report."""
        stats = self.get_error_stats()
        recent_errors = self.get_recent_errors(limit=5)
        
        report = "=== Claude Code SDK Error Report ===\n\n"
        report += f"Total Errors: {stats['total_errors']}\n"
        report += f"Recovery Success Rate: {stats['recovery_success_rate']:.2%}\n\n"
        
        report += "Errors by Type:\n"
        for error_type, count in stats["errors_by_type"].items():
            report += f"  {error_type}: {count}\n"
        
        report += "\nErrors by Severity:\n"
        for severity, count in stats["errors_by_severity"].items():
            report += f"  {severity}: {count}\n"
        
        report += "\nRecent Errors:\n"
        for error in recent_errors:
            report += f"  [{error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
            report += f"{error.operation}: {error.error_message}\n"
        
        return report