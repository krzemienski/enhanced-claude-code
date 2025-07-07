"""Log streaming and parsing for real-time monitoring."""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Iterator, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogEventType(Enum):
    """Types of log events."""
    EXECUTION_START = "execution_start"
    EXECUTION_END = "execution_end"
    PHASE_START = "phase_start"
    PHASE_END = "phase_end"
    TASK_START = "task_start"
    TASK_END = "task_end"
    PROGRESS_UPDATE = "progress_update"
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    CHECKPOINT_CREATED = "checkpoint_created"
    RECOVERY_INITIATED = "recovery_initiated"
    COST_UPDATE = "cost_update"
    CUSTOM = "custom"


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: datetime
    level: LogLevel
    event_type: LogEventType
    message: str
    source: str
    execution_id: Optional[str] = None
    phase_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_line: str = ""


@dataclass
class StreamStats:
    """Statistics for log stream processing."""
    total_lines: int = 0
    parsed_lines: int = 0
    error_lines: int = 0
    events_by_type: Dict[LogEventType, int] = field(default_factory=dict)
    events_by_level: Dict[LogLevel, int] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None


class StreamParser:
    """Parses log streams for real-time monitoring."""
    
    def __init__(self):
        """Initialize the stream parser."""
        # Log patterns for different formats
        self.patterns = {
            # Standard Python logging format
            "python": re.compile(
                r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - "
                r"(?P<logger>\S+) - (?P<level>\w+) - (?P<message>.*)"
            ),
            
            # Structured JSON logging
            "json": re.compile(r"^{.*}$"),
            
            # Claude Code specific format
            "claude_code": re.compile(
                r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}) "
                r"\[(?P<level>\w+)\] \[(?P<execution_id>\w+)\] "
                r"(?:\[(?P<phase_id>\w+)\])? (?:\[(?P<task_id>\w+)\])? "
                r"(?P<message>.*)"
            ),
            
            # Generic format
            "generic": re.compile(
                r"(?P<timestamp>\S+) (?P<level>\w+) (?P<message>.*)"
            )
        }
        
        # Event pattern mapping
        self.event_patterns = {
            LogEventType.EXECUTION_START: [
                r"starting execution",
                r"execution.*started",
                r"begin.*execution"
            ],
            LogEventType.EXECUTION_END: [
                r"execution.*complete",
                r"finished execution",
                r"execution.*ended"
            ],
            LogEventType.PHASE_START: [
                r"starting phase",
                r"phase.*started",
                r"begin.*phase"
            ],
            LogEventType.PHASE_END: [
                r"phase.*complete",
                r"finished phase",
                r"phase.*ended"
            ],
            LogEventType.TASK_START: [
                r"starting task",
                r"task.*started",
                r"executing task"
            ],
            LogEventType.TASK_END: [
                r"task.*complete",
                r"finished task",
                r"task.*ended"
            ],
            LogEventType.PROGRESS_UPDATE: [
                r"progress:",
                r"\d+%",
                r"completed \d+",
                r"eta:"
            ],
            LogEventType.ERROR_OCCURRED: [
                r"error:",
                r"exception:",
                r"failed:",
                r"traceback"
            ],
            LogEventType.WARNING_ISSUED: [
                r"warning:",
                r"warn:",
                r"deprecated"
            ],
            LogEventType.CHECKPOINT_CREATED: [
                r"checkpoint.*created",
                r"saved checkpoint",
                r"created checkpoint"
            ],
            LogEventType.RECOVERY_INITIATED: [
                r"recovery.*started",
                r"recovering from",
                r"recovery.*initiated"
            ],
            LogEventType.COST_UPDATE: [
                r"cost:",
                r"\$\d+",
                r"tokens:",
                r"api.*cost"
            ]
        }
        
        # Statistics tracking
        self.stats = StreamStats()
        
        # Event handlers
        self.event_handlers: Dict[LogEventType, List[Callable]] = {}
        
        logger.info("Stream Parser initialized")
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line."""
        if not line.strip():
            return None
        
        self.stats.total_lines += 1
        
        # Try different parsing patterns
        for pattern_name, pattern in self.patterns.items():
            match = pattern.match(line.strip())
            if match:
                try:
                    entry = self._create_log_entry(match, pattern_name, line)
                    if entry:
                        self.stats.parsed_lines += 1
                        self._update_stats(entry)
                        return entry
                except Exception as e:
                    logger.debug(f"Error parsing line with {pattern_name}: {e}")
                    continue
        
        # If no pattern matches, create a generic entry
        self.stats.error_lines += 1
        return LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            event_type=LogEventType.CUSTOM,
            message=line.strip(),
            source="unknown",
            raw_line=line
        )
    
    def parse_stream(self, stream: Iterator[str]) -> Iterator[LogEntry]:
        """Parse a stream of log lines."""
        self.stats.start_time = datetime.now()
        
        for line in stream:
            entry = self.parse_line(line)
            if entry:
                yield entry
    
    async def parse_stream_async(
        self,
        stream: asyncio.StreamReader
    ) -> Iterator[LogEntry]:
        """Parse an async stream of log lines."""
        self.stats.start_time = datetime.now()
        
        async for line in stream:
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            
            entry = self.parse_line(line)
            if entry:
                yield entry
    
    def parse_file(self, file_path: Path) -> Iterator[LogEntry]:
        """Parse a log file."""
        try:
            with open(file_path, 'r') as f:
                yield from self.parse_stream(f)
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
    
    def register_event_handler(
        self,
        event_type: LogEventType,
        handler: Callable[[LogEntry], None]
    ) -> None:
        """Register an event handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def _create_log_entry(
        self,
        match: re.Match,
        pattern_name: str,
        raw_line: str
    ) -> Optional[LogEntry]:
        """Create a log entry from a regex match."""
        try:
            groups = match.groupdict()
            
            # Parse timestamp
            timestamp_str = groups.get('timestamp', '')
            timestamp = self._parse_timestamp(timestamp_str)
            
            # Parse level
            level_str = groups.get('level', 'INFO').upper()
            level = LogLevel(level_str.lower()) if level_str.lower() in [l.value for l in LogLevel] else LogLevel.INFO
            
            # Extract message
            message = groups.get('message', '')
            
            # Determine event type
            event_type = self._determine_event_type(message)
            
            # Extract additional fields
            execution_id = groups.get('execution_id')
            phase_id = groups.get('phase_id')
            task_id = groups.get('task_id')
            source = groups.get('logger', 'unknown')
            
            # Handle JSON format
            if pattern_name == "json":
                return self._parse_json_log(raw_line)
            
            # Create metadata
            metadata = {
                "pattern": pattern_name,
                "source_logger": source
            }
            
            # Extract additional metadata from message
            metadata.update(self._extract_metadata(message, event_type))
            
            entry = LogEntry(
                timestamp=timestamp,
                level=level,
                event_type=event_type,
                message=message,
                source=source,
                execution_id=execution_id,
                phase_id=phase_id,
                task_id=task_id,
                metadata=metadata,
                raw_line=raw_line
            )
            
            # Trigger event handlers
            self._trigger_handlers(entry)
            
            return entry
            
        except Exception as e:
            logger.debug(f"Error creating log entry: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string."""
        if not timestamp_str:
            return datetime.now()
        
        # Try different timestamp formats
        formats = [
            "%Y-%m-%d %H:%M:%S,%f",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%H:%M:%S"
        ]
        
        for fmt in formats:
            try:
                if fmt == "%H:%M:%S":
                    # For time-only format, use today's date
                    time_obj = datetime.strptime(timestamp_str, fmt).time()
                    return datetime.combine(datetime.now().date(), time_obj)
                else:
                    return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        # If all formats fail, return current time
        return datetime.now()
    
    def _determine_event_type(self, message: str) -> LogEventType:
        """Determine event type from message content."""
        message_lower = message.lower()
        
        for event_type, patterns in self.event_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return event_type
        
        return LogEventType.CUSTOM
    
    def _extract_metadata(
        self,
        message: str,
        event_type: LogEventType
    ) -> Dict[str, Any]:
        """Extract metadata from log message."""
        metadata = {}
        
        # Extract progress percentage
        progress_match = re.search(r"(\d+)%", message)
        if progress_match:
            metadata["progress_percent"] = int(progress_match.group(1))
        
        # Extract ETA
        eta_match = re.search(r"eta:\s*(\d+(?:\.\d+)?)\s*(s|min|h)", message)
        if eta_match:
            value = float(eta_match.group(1))
            unit = eta_match.group(2)
            metadata["eta"] = {"value": value, "unit": unit}
        
        # Extract cost information
        cost_match = re.search(r"\$(\d+(?:\.\d+)?)", message)
        if cost_match:
            metadata["cost"] = float(cost_match.group(1))
        
        # Extract token information
        token_match = re.search(r"(\d+)\s*tokens", message)
        if token_match:
            metadata["tokens"] = int(token_match.group(1))
        
        # Extract duration
        duration_match = re.search(r"(\d+(?:\.\d+)?)\s*(s|ms|min)", message)
        if duration_match:
            value = float(duration_match.group(1))
            unit = duration_match.group(2)
            metadata["duration"] = {"value": value, "unit": unit}
        
        return metadata
    
    def _parse_json_log(self, json_line: str) -> Optional[LogEntry]:
        """Parse JSON-formatted log line."""
        try:
            data = json.loads(json_line)
            
            timestamp = datetime.fromisoformat(
                data.get('timestamp', datetime.now().isoformat())
            )
            
            level_str = data.get('level', 'INFO').lower()
            level = LogLevel(level_str) if level_str in [l.value for l in LogLevel] else LogLevel.INFO
            
            message = data.get('message', '')
            event_type = LogEventType(
                data.get('event_type', LogEventType.CUSTOM.value)
            )
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                event_type=event_type,
                message=message,
                source=data.get('source', 'json'),
                execution_id=data.get('execution_id'),
                phase_id=data.get('phase_id'),
                task_id=data.get('task_id'),
                metadata=data.get('metadata', {}),
                raw_line=json_line
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Error parsing JSON log: {e}")
            return None
    
    def _update_stats(self, entry: LogEntry) -> None:
        """Update parsing statistics."""
        self.stats.last_update = datetime.now()
        
        # Update event type counts
        if entry.event_type not in self.stats.events_by_type:
            self.stats.events_by_type[entry.event_type] = 0
        self.stats.events_by_type[entry.event_type] += 1
        
        # Update level counts
        if entry.level not in self.stats.events_by_level:
            self.stats.events_by_level[entry.level] = 0
        self.stats.events_by_level[entry.level] += 1
    
    def _trigger_handlers(self, entry: LogEntry) -> None:
        """Trigger registered event handlers."""
        handlers = self.event_handlers.get(entry.event_type, [])
        for handler in handlers:
            try:
                handler(entry)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def get_stats(self) -> StreamStats:
        """Get parsing statistics."""
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset parsing statistics."""
        self.stats = StreamStats()
    
    def filter_entries(
        self,
        entries: List[LogEntry],
        level: Optional[LogLevel] = None,
        event_type: Optional[LogEventType] = None,
        execution_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        time_range: Optional[tuple] = None
    ) -> List[LogEntry]:
        """Filter log entries based on criteria."""
        filtered = entries
        
        if level:
            filtered = [e for e in filtered if e.level == level]
        
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        
        if execution_id:
            filtered = [e for e in filtered if e.execution_id == execution_id]
        
        if phase_id:
            filtered = [e for e in filtered if e.phase_id == phase_id]
        
        if task_id:
            filtered = [e for e in filtered if e.task_id == task_id]
        
        if time_range:
            start_time, end_time = time_range
            filtered = [
                e for e in filtered
                if start_time <= e.timestamp <= end_time
            ]
        
        return filtered


class LogStreamer:
    """Streams logs in real-time."""
    
    def __init__(self, parser: StreamParser):
        """Initialize the log streamer."""
        self.parser = parser
        self.active_streams: Dict[str, asyncio.Task] = {}
        
    async def stream_file(
        self,
        file_path: Path,
        follow: bool = True,
        callback: Optional[Callable[[LogEntry], None]] = None
    ) -> None:
        """Stream a log file."""
        try:
            if follow:
                # Follow file like 'tail -f'
                await self._follow_file(file_path, callback)
            else:
                # Read entire file
                for entry in self.parser.parse_file(file_path):
                    if callback:
                        callback(entry)
        
        except Exception as e:
            logger.error(f"Error streaming file {file_path}: {e}")
    
    async def _follow_file(
        self,
        file_path: Path,
        callback: Optional[Callable[[LogEntry], None]]
    ) -> None:
        """Follow a file for new lines."""
        try:
            with open(file_path, 'r') as f:
                # Seek to end of file
                f.seek(0, 2)
                
                while True:
                    line = f.readline()
                    if line:
                        entry = self.parser.parse_line(line)
                        if entry and callback:
                            callback(entry)
                    else:
                        # No new data, wait a bit
                        await asyncio.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Error following file {file_path}: {e}")
    
    def start_stream(
        self,
        stream_id: str,
        file_path: Path,
        callback: Callable[[LogEntry], None]
    ) -> None:
        """Start a new log stream."""
        if stream_id in self.active_streams:
            self.stop_stream(stream_id)
        
        task = asyncio.create_task(
            self.stream_file(file_path, follow=True, callback=callback)
        )
        self.active_streams[stream_id] = task
    
    def stop_stream(self, stream_id: str) -> None:
        """Stop a log stream."""
        if stream_id in self.active_streams:
            task = self.active_streams[stream_id]
            task.cancel()
            del self.active_streams[stream_id]
    
    def stop_all_streams(self) -> None:
        """Stop all active streams."""
        for stream_id in list(self.active_streams.keys()):
            self.stop_stream(stream_id)