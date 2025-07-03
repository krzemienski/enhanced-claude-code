"""Structured logging for Claude Code Builder."""

import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union
from contextlib import contextmanager
import threading
from queue import Queue
import atexit


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, "phase"):
            log_data["phase"] = record.phase
        if hasattr(record, "task"):
            log_data["task"] = record.task
        if hasattr(record, "error_code"):
            log_data["error_code"] = record.error_code
        if hasattr(record, "details"):
            log_data["details"] = record.details
        if hasattr(record, "cost"):
            log_data["cost"] = record.cost
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        if hasattr(record, "progress"):
            log_data["progress"] = record.progress
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Formatter for human-readable console output."""
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"
    
    def __init__(self, use_colors: bool = True):
        """Initialize formatter."""
        super().__init__()
        self.use_colors = use_colors and sys.stderr.isatty()
        
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human reading."""
        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format level with color
        if self.use_colors:
            level = f"{self.COLORS.get(record.levelname, '')}{record.levelname:8}{self.RESET}"
        else:
            level = f"{record.levelname:8}"
            
        # Format message
        message = record.getMessage()
        
        # Add context if available
        context_parts = []
        if hasattr(record, "phase"):
            context_parts.append(f"[{record.phase}]")
        if hasattr(record, "task"):
            context_parts.append(f"<{record.task}>")
            
        context = " ".join(context_parts)
        if context:
            message = f"{context} {message}"
            
        # Format the complete line
        line = f"{timestamp} {level} {message}"
        
        # Add exception info if present
        if record.exc_info:
            line += f"\n{self.formatException(record.exc_info)}"
            
        return line


class AsyncFileHandler(logging.Handler):
    """Asynchronous file handler to prevent I/O blocking."""
    
    def __init__(self, filename: Union[str, Path], mode: str = "a"):
        """Initialize async file handler."""
        super().__init__()
        self.filename = Path(filename)
        self.mode = mode
        self.queue: Queue = Queue()
        self.thread = threading.Thread(target=self._writer_thread, daemon=True)
        self.thread.start()
        self._shutdown = False
        atexit.register(self.close)
        
    def _writer_thread(self):
        """Background thread for writing logs."""
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.filename, self.mode) as f:
            while not self._shutdown:
                try:
                    record = self.queue.get(timeout=0.1)
                    if record is None:  # Shutdown signal
                        break
                    f.write(self.format(record) + "\n")
                    f.flush()
                except:
                    continue
                    
    def emit(self, record: logging.LogRecord):
        """Queue record for writing."""
        if not self._shutdown:
            self.queue.put(record)
            
    def close(self):
        """Close the handler."""
        if not self._shutdown:
            self._shutdown = True
            self.queue.put(None)  # Signal shutdown
            self.thread.join(timeout=1)
        super().close()


class ClaudeCodeLogger:
    """Enhanced logger for Claude Code Builder."""
    
    def __init__(self, name: str = "claude_code_builder"):
        """Initialize logger."""
        self.logger = logging.getLogger(name)
        self._context = threading.local()
        
    def setup(
        self,
        level: str = "INFO",
        log_file: Optional[Path] = None,
        console: bool = True,
        structured: bool = False
    ):
        """Setup logger configuration.
        
        Args:
            level: Logging level
            log_file: Path to log file
            console: Enable console output
            structured: Use structured JSON logging
        """
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Add console handler
        if console:
            console_handler = logging.StreamHandler(sys.stderr)
            if structured:
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(HumanReadableFormatter())
            self.logger.addHandler(console_handler)
            
        # Add file handler
        if log_file:
            file_handler = AsyncFileHandler(log_file)
            file_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(file_handler)
            
    @contextmanager
    def context(self, **kwargs):
        """Context manager for adding context to logs.
        
        Usage:
            with logger.context(phase="planning", task="analyze_spec"):
                logger.info("Processing specification")
        """
        # Save current context
        old_context = getattr(self._context, "data", {})
        
        # Set new context
        self._context.data = {**old_context, **kwargs}
        
        try:
            yield
        finally:
            # Restore old context
            self._context.data = old_context
            
    def _add_context(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Add context data to log kwargs."""
        context = getattr(self._context, "data", {})
        return {**context, **kwargs}
        
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=self._add_context(kwargs))
        
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=self._add_context(kwargs))
        
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=self._add_context(kwargs))
        
    def error(self, message: str, exc_info: bool = False, **kwargs):
        """Log error message."""
        self.logger.error(message, exc_info=exc_info, extra=self._add_context(kwargs))
        
    def critical(self, message: str, exc_info: bool = False, **kwargs):
        """Log critical message."""
        self.logger.critical(message, exc_info=exc_info, extra=self._add_context(kwargs))
        
    def phase_start(self, phase: str, **kwargs):
        """Log phase start."""
        self.info(f"Starting phase: {phase}", phase=phase, event="phase_start", **kwargs)
        
    def phase_complete(self, phase: str, duration: float, **kwargs):
        """Log phase completion."""
        self.info(
            f"Completed phase: {phase}",
            phase=phase,
            event="phase_complete",
            duration=duration,
            **kwargs
        )
        
    def task_start(self, task: str, **kwargs):
        """Log task start."""
        self.info(f"Starting task: {task}", task=task, event="task_start", **kwargs)
        
    def task_complete(self, task: str, duration: float, **kwargs):
        """Log task completion."""
        self.info(
            f"Completed task: {task}",
            task=task,
            event="task_complete",
            duration=duration,
            **kwargs
        )
        
    def cost_update(self, category: str, amount: float, total: float, **kwargs):
        """Log cost update."""
        self.info(
            f"Cost update: {category} +${amount:.2f} (total: ${total:.2f})",
            event="cost_update",
            cost_category=category,
            cost_amount=amount,
            cost_total=total,
            **kwargs
        )
        
    def progress_update(self, progress: float, message: str = "", **kwargs):
        """Log progress update."""
        self.info(
            f"Progress: {progress:.1%} {message}".strip(),
            event="progress_update",
            progress=progress,
            **kwargs
        )
        
    def validation_error(self, field: str, value: Any, reason: str, **kwargs):
        """Log validation error."""
        self.error(
            f"Validation failed for {field}: {reason}",
            event="validation_error",
            field=field,
            value=str(value),
            reason=reason,
            **kwargs
        )
        
    def recovery_attempt(self, checkpoint: str, attempt: int, **kwargs):
        """Log recovery attempt."""
        self.warning(
            f"Attempting recovery from {checkpoint} (attempt {attempt})",
            event="recovery_attempt",
            checkpoint=checkpoint,
            attempt=attempt,
            **kwargs
        )


# Create global logger instance
logger = ClaudeCodeLogger()

# Convenience functions
def get_logger(name: str) -> ClaudeCodeLogger:
    """Get a logger instance."""
    return ClaudeCodeLogger(name)

def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console: bool = True,
    structured: bool = False
):
    """Setup global logging configuration."""
    logger.setup(level, log_file, console, structured)