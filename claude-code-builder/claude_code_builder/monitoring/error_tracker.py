"""Error tracking and analysis for monitoring."""

import logging
import traceback
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
import re
import json

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    SYSTEM = "system"
    NETWORK = "network"
    API = "api"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    DATA = "data"
    LOGIC = "logic"
    CONFIGURATION = "configuration"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


@dataclass
class ErrorSignature:
    """Error signature for grouping similar errors."""
    error_type: str
    message_pattern: str
    location: str
    signature_hash: str


@dataclass
class ErrorOccurrence:
    """Individual error occurrence."""
    timestamp: datetime
    error_id: str
    signature: ErrorSignature
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    exception_type: str
    traceback_text: str
    source_file: str
    line_number: Optional[int]
    execution_id: Optional[str] = None
    phase_id: Optional[str] = None
    task_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorPattern:
    """Grouped error pattern."""
    signature: ErrorSignature
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
    occurrences: List[ErrorOccurrence] = field(default_factory=list)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.UNKNOWN
    is_resolved: bool = False
    resolution_notes: str = ""


@dataclass
class ErrorStats:
    """Error statistics."""
    total_errors: int
    errors_by_severity: Dict[ErrorSeverity, int] = field(default_factory=dict)
    errors_by_category: Dict[ErrorCategory, int] = field(default_factory=dict)
    error_rate: float = 0.0  # errors per minute
    top_errors: List[ErrorPattern] = field(default_factory=list)
    period_start: datetime = field(default_factory=datetime.now)
    period_end: datetime = field(default_factory=datetime.now)


class ErrorTracker:
    """Tracks and analyzes errors for monitoring."""
    
    def __init__(self):
        """Initialize the error tracker."""
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.error_occurrences: List[ErrorOccurrence] = []
        self.lock = threading.RLock()
        
        # Error classification rules
        self.classification_rules = self._setup_classification_rules()
        
        # Error grouping configuration
        self.max_pattern_length = 1000
        self.max_occurrences_per_pattern = 100
        self.retention_hours = 168  # 7 days
        
        # Rate tracking
        self.error_timestamps: List[datetime] = []
        self.rate_window_minutes = 5
        
        logger.info("Error Tracker initialized")
    
    def track_error(
        self,
        exception: Exception,
        execution_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ErrorOccurrence:
        """Track an error occurrence."""
        with self.lock:
            # Extract error information
            error_info = self._extract_error_info(exception)
            
            # Create error signature
            signature = self._create_error_signature(error_info)
            
            # Classify error
            severity = self._classify_severity(exception, error_info)
            category = self._classify_category(exception, error_info)
            
            # Create error occurrence
            occurrence = ErrorOccurrence(
                timestamp=datetime.now(),
                error_id=self._generate_error_id(signature),
                signature=signature,
                severity=severity,
                category=category,
                message=str(exception),
                exception_type=type(exception).__name__,
                traceback_text=error_info["traceback"],
                source_file=error_info["file"],
                line_number=error_info["line"],
                execution_id=execution_id,
                phase_id=phase_id,
                task_id=task_id,
                context=context or {},
                metadata=metadata or {}
            )
            
            # Add to occurrences
            self.error_occurrences.append(occurrence)
            self.error_timestamps.append(occurrence.timestamp)
            
            # Update or create error pattern
            self._update_error_pattern(occurrence)
            
            # Cleanup old data
            self._cleanup_old_data()
            
            logger.error(
                f"Tracked error: {occurrence.exception_type} - {occurrence.message}"
            )
            
            return occurrence
    
    def track_custom_error(
        self,
        error_type: str,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        execution_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ErrorOccurrence:
        """Track a custom error without an exception."""
        with self.lock:
            # Create synthetic error info
            error_info = {
                "traceback": f"Custom error: {error_type}",
                "file": metadata.get("source_file", "unknown") if metadata else "unknown",
                "line": metadata.get("line_number") if metadata else None
            }
            
            # Create signature
            signature = ErrorSignature(
                error_type=error_type,
                message_pattern=self._extract_message_pattern(message),
                location=error_info["file"],
                signature_hash=self._hash_signature(error_type, message, error_info["file"])
            )
            
            # Create occurrence
            occurrence = ErrorOccurrence(
                timestamp=datetime.now(),
                error_id=self._generate_error_id(signature),
                signature=signature,
                severity=severity,
                category=category,
                message=message,
                exception_type=error_type,
                traceback_text=error_info["traceback"],
                source_file=error_info["file"],
                line_number=error_info["line"],
                execution_id=execution_id,
                phase_id=phase_id,
                task_id=task_id,
                context=context or {},
                metadata=metadata or {}
            )
            
            # Add to tracking
            self.error_occurrences.append(occurrence)
            self.error_timestamps.append(occurrence.timestamp)
            self._update_error_pattern(occurrence)
            self._cleanup_old_data()
            
            logger.error(f"Tracked custom error: {error_type} - {message}")
            
            return occurrence
    
    def get_error_stats(
        self,
        hours: int = 24,
        execution_id: Optional[str] = None
    ) -> ErrorStats:
        """Get error statistics for a period."""
        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            # Filter occurrences
            filtered_occurrences = [
                occ for occ in self.error_occurrences
                if (occ.timestamp >= cutoff and
                    (execution_id is None or occ.execution_id == execution_id))
            ]
            
            # Calculate statistics
            total_errors = len(filtered_occurrences)
            
            # Group by severity
            errors_by_severity = {}
            for severity in ErrorSeverity:
                errors_by_severity[severity] = sum(
                    1 for occ in filtered_occurrences
                    if occ.severity == severity
                )
            
            # Group by category
            errors_by_category = {}
            for category in ErrorCategory:
                errors_by_category[category] = sum(
                    1 for occ in filtered_occurrences
                    if occ.category == category
                )
            
            # Calculate error rate (errors per minute)
            if hours > 0:
                error_rate = total_errors / (hours * 60)
            else:
                error_rate = 0.0
            
            # Get top error patterns
            pattern_counts = {}
            for occ in filtered_occurrences:
                sig_hash = occ.signature.signature_hash
                pattern_counts[sig_hash] = pattern_counts.get(sig_hash, 0) + 1
            
            top_patterns = sorted(
                [(self.error_patterns[sig_hash], count) 
                 for sig_hash, count in pattern_counts.items()
                 if sig_hash in self.error_patterns],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            top_errors = [pattern for pattern, count in top_patterns]
            
            return ErrorStats(
                total_errors=total_errors,
                errors_by_severity=errors_by_severity,
                errors_by_category=errors_by_category,
                error_rate=error_rate,
                top_errors=top_errors,
                period_start=cutoff,
                period_end=datetime.now()
            )
    
    def get_error_patterns(
        self,
        limit: int = 50,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        unresolved_only: bool = False
    ) -> List[ErrorPattern]:
        """Get error patterns with filtering."""
        with self.lock:
            patterns = list(self.error_patterns.values())
            
            # Apply filters
            if severity:
                patterns = [p for p in patterns if p.severity == severity]
            
            if category:
                patterns = [p for p in patterns if p.category == category]
            
            if unresolved_only:
                patterns = [p for p in patterns if not p.is_resolved]
            
            # Sort by occurrence count (descending)
            patterns.sort(key=lambda p: p.occurrence_count, reverse=True)
            
            return patterns[:limit]
    
    def get_error_trend(
        self,
        hours: int = 24,
        bucket_minutes: int = 60
    ) -> List[Tuple[datetime, int]]:
        """Get error count trend over time."""
        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            # Filter recent errors
            recent_errors = [
                ts for ts in self.error_timestamps
                if ts >= cutoff
            ]
            
            # Create time buckets
            buckets = {}
            bucket_size = timedelta(minutes=bucket_minutes)
            
            for error_time in recent_errors:
                # Round down to bucket boundary
                bucket_start = error_time.replace(
                    minute=(error_time.minute // bucket_minutes) * bucket_minutes,
                    second=0,
                    microsecond=0
                )
                
                buckets[bucket_start] = buckets.get(bucket_start, 0) + 1
            
            # Convert to sorted list
            trend = sorted(buckets.items())
            return trend
    
    def get_current_error_rate(self, window_minutes: int = 5) -> float:
        """Get current error rate (errors per minute)."""
        with self.lock:
            cutoff = datetime.now() - timedelta(minutes=window_minutes)
            recent_errors = [
                ts for ts in self.error_timestamps
                if ts >= cutoff
            ]
            
            if window_minutes > 0:
                return len(recent_errors) / window_minutes
            else:
                return 0.0
    
    def mark_pattern_resolved(
        self,
        signature_hash: str,
        resolution_notes: str = ""
    ) -> bool:
        """Mark an error pattern as resolved."""
        with self.lock:
            if signature_hash in self.error_patterns:
                pattern = self.error_patterns[signature_hash]
                pattern.is_resolved = True
                pattern.resolution_notes = resolution_notes
                
                logger.info(f"Marked error pattern as resolved: {signature_hash}")
                return True
            
            return False
    
    def export_error_data(
        self,
        hours: int = 24,
        include_occurrences: bool = False
    ) -> Dict[str, Any]:
        """Export error data for analysis."""
        with self.lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            # Filter recent patterns
            recent_patterns = [
                pattern for pattern in self.error_patterns.values()
                if pattern.last_seen >= cutoff
            ]
            
            export_data = {
                "metadata": {
                    "export_time": datetime.now().isoformat(),
                    "period_hours": hours,
                    "total_patterns": len(recent_patterns),
                    "include_occurrences": include_occurrences
                },
                "patterns": []
            }
            
            for pattern in recent_patterns:
                pattern_data = {
                    "signature": {
                        "error_type": pattern.signature.error_type,
                        "message_pattern": pattern.signature.message_pattern,
                        "location": pattern.signature.location,
                        "signature_hash": pattern.signature.signature_hash
                    },
                    "first_seen": pattern.first_seen.isoformat(),
                    "last_seen": pattern.last_seen.isoformat(),
                    "occurrence_count": pattern.occurrence_count,
                    "severity": pattern.severity.value,
                    "category": pattern.category.value,
                    "is_resolved": pattern.is_resolved,
                    "resolution_notes": pattern.resolution_notes
                }
                
                if include_occurrences:
                    pattern_data["occurrences"] = [
                        {
                            "timestamp": occ.timestamp.isoformat(),
                            "message": occ.message,
                            "execution_id": occ.execution_id,
                            "phase_id": occ.phase_id,
                            "task_id": occ.task_id,
                            "context": occ.context,
                            "metadata": occ.metadata
                        }
                        for occ in pattern.occurrences
                        if occ.timestamp >= cutoff
                    ]
                
                export_data["patterns"].append(pattern_data)
            
            return export_data
    
    def _extract_error_info(self, exception: Exception) -> Dict[str, Any]:
        """Extract information from an exception."""
        tb = traceback.format_exc()
        
        # Extract file and line number from traceback
        file_name = "unknown"
        line_number = None
        
        try:
            tb_lines = tb.split('\n')
            for line in tb_lines:
                if 'File "' in line and 'line' in line:
                    # Parse line like: File "/path/to/file.py", line 123, in function_name
                    match = re.search(r'File "([^"]+)", line (\d+)', line)
                    if match:
                        file_name = match.group(1).split('/')[-1]  # Just filename
                        line_number = int(match.group(2))
                        break
        except Exception:
            pass  # Fallback to defaults
        
        return {
            "traceback": tb,
            "file": file_name,
            "line": line_number
        }
    
    def _create_error_signature(self, error_info: Dict[str, Any]) -> ErrorSignature:
        """Create an error signature for grouping."""
        error_type = error_info.get("exception_type", "Unknown")
        message = error_info.get("message", "")
        location = error_info.get("file", "unknown")
        
        # Extract pattern from message (remove variable parts)
        message_pattern = self._extract_message_pattern(message)
        
        # Create hash for the signature
        signature_hash = self._hash_signature(error_type, message_pattern, location)
        
        return ErrorSignature(
            error_type=error_type,
            message_pattern=message_pattern,
            location=location,
            signature_hash=signature_hash
        )
    
    def _extract_message_pattern(self, message: str) -> str:
        """Extract a pattern from an error message by removing variable parts."""
        if not message:
            return ""
        
        # Remove common variable patterns
        patterns_to_replace = [
            (r'\b\d+\b', '<NUMBER>'),  # Numbers
            (r'\b0x[0-9a-fA-F]+\b', '<HEX>'),  # Hex addresses
            (r'["\'][^"\']*["\']', '<STRING>'),  # Quoted strings
            (r'\b[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}\b', '<UUID>'),  # UUIDs
            (r'\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\b', '<TIMESTAMP>'),  # ISO timestamps
            (r'/[^/\s]+/[^/\s]*', '<PATH>'),  # File paths
        ]
        
        pattern = message
        for regex, replacement in patterns_to_replace:
            pattern = re.sub(regex, replacement, pattern)
        
        # Limit length
        if len(pattern) > self.max_pattern_length:
            pattern = pattern[:self.max_pattern_length] + "..."
        
        return pattern
    
    def _hash_signature(self, error_type: str, message_pattern: str, location: str) -> str:
        """Create a hash for error signature."""
        content = f"{error_type}:{message_pattern}:{location}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _generate_error_id(self, signature: ErrorSignature) -> str:
        """Generate a unique error ID."""
        timestamp = datetime.now().isoformat()
        content = f"{signature.signature_hash}:{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _classify_severity(
        self,
        exception: Exception,
        error_info: Dict[str, Any]
    ) -> ErrorSeverity:
        """Classify error severity."""
        exception_type = type(exception).__name__
        message = str(exception).lower()
        
        # Critical errors
        critical_patterns = [
            "systemerror", "memoryerror", "keyboardinterrupt",
            "out of memory", "segmentation fault", "fatal"
        ]
        
        if (exception_type in ["SystemError", "MemoryError", "KeyboardInterrupt"] or
            any(pattern in message for pattern in critical_patterns)):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        high_patterns = [
            "permissionerror", "authenticationerror", "securityerror",
            "permission denied", "access denied", "unauthorized"
        ]
        
        if (exception_type in ["PermissionError", "AuthenticationError"] or
            any(pattern in message for pattern in high_patterns)):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        medium_patterns = [
            "connectionerror", "timeouterror", "httperror",
            "connection", "timeout", "network"
        ]
        
        if (exception_type in ["ConnectionError", "TimeoutError", "HTTPError"] or
            any(pattern in message for pattern in medium_patterns)):
            return ErrorSeverity.MEDIUM
        
        # Default to medium
        return ErrorSeverity.MEDIUM
    
    def _classify_category(
        self,
        exception: Exception,
        error_info: Dict[str, Any]
    ) -> ErrorCategory:
        """Classify error category."""
        exception_type = type(exception).__name__
        message = str(exception).lower()
        
        # Use classification rules
        for category, rules in self.classification_rules.items():
            if (exception_type in rules["exception_types"] or
                any(pattern in message for pattern in rules["message_patterns"])):
                return category
        
        return ErrorCategory.UNKNOWN
    
    def _setup_classification_rules(self) -> Dict[ErrorCategory, Dict[str, List[str]]]:
        """Setup error classification rules."""
        return {
            ErrorCategory.SYSTEM: {
                "exception_types": ["SystemError", "OSError", "MemoryError"],
                "message_patterns": ["system", "os", "memory", "disk"]
            },
            ErrorCategory.NETWORK: {
                "exception_types": ["ConnectionError", "URLError", "HTTPError"],
                "message_patterns": ["connection", "network", "http", "url", "socket"]
            },
            ErrorCategory.API: {
                "exception_types": ["APIError", "HTTPError"],
                "message_patterns": ["api", "endpoint", "response", "request"]
            },
            ErrorCategory.VALIDATION: {
                "exception_types": ["ValueError", "ValidationError"],
                "message_patterns": ["validation", "invalid", "format", "schema"]
            },
            ErrorCategory.AUTHENTICATION: {
                "exception_types": ["AuthenticationError", "PermissionError"],
                "message_patterns": ["auth", "permission", "access", "token", "credential"]
            },
            ErrorCategory.TIMEOUT: {
                "exception_types": ["TimeoutError"],
                "message_patterns": ["timeout", "timed out", "deadline"]
            },
            ErrorCategory.RESOURCE: {
                "exception_types": ["ResourceError", "MemoryError"],
                "message_patterns": ["resource", "memory", "quota", "limit"]
            },
            ErrorCategory.DATA: {
                "exception_types": ["DataError", "KeyError", "IndexError"],
                "message_patterns": ["data", "key", "index", "missing"]
            },
            ErrorCategory.CONFIGURATION: {
                "exception_types": ["ValidationError"],
                "message_patterns": ["config", "setting", "parameter", "option"]
            }
        }
    
    def _update_error_pattern(self, occurrence: ErrorOccurrence) -> None:
        """Update or create error pattern."""
        signature_hash = occurrence.signature.signature_hash
        
        if signature_hash in self.error_patterns:
            # Update existing pattern
            pattern = self.error_patterns[signature_hash]
            pattern.last_seen = occurrence.timestamp
            pattern.occurrence_count += 1
            
            # Add occurrence to pattern (with limit)
            pattern.occurrences.append(occurrence)
            if len(pattern.occurrences) > self.max_occurrences_per_pattern:
                pattern.occurrences = pattern.occurrences[-self.max_occurrences_per_pattern:]
            
            # Update severity if higher
            if occurrence.severity.value > pattern.severity.value:
                pattern.severity = occurrence.severity
        
        else:
            # Create new pattern
            pattern = ErrorPattern(
                signature=occurrence.signature,
                first_seen=occurrence.timestamp,
                last_seen=occurrence.timestamp,
                occurrence_count=1,
                occurrences=[occurrence],
                severity=occurrence.severity,
                category=occurrence.category
            )
            
            self.error_patterns[signature_hash] = pattern
    
    def _cleanup_old_data(self) -> None:
        """Clean up old error data."""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        
        # Clean up old occurrences
        self.error_occurrences = [
            occ for occ in self.error_occurrences
            if occ.timestamp >= cutoff
        ]
        
        # Clean up old timestamps
        self.error_timestamps = [
            ts for ts in self.error_timestamps
            if ts >= cutoff
        ]
        
        # Clean up old patterns
        patterns_to_remove = []
        for signature_hash, pattern in self.error_patterns.items():
            if pattern.last_seen < cutoff:
                patterns_to_remove.append(signature_hash)
            else:
                # Clean up old occurrences from pattern
                pattern.occurrences = [
                    occ for occ in pattern.occurrences
                    if occ.timestamp >= cutoff
                ]
        
        for signature_hash in patterns_to_remove:
            del self.error_patterns[signature_hash]