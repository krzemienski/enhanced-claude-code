"""Error context preservation for learning and recovery."""

import logging
import traceback
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import re
import hashlib

from .store import PersistentMemoryStore, MemoryType, MemoryPriority
from .context_accumulator import ContextAccumulator, ContextType, ContextScope

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    LOGIC = "logic"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    PERMISSION = "permission"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for errors."""
    RETRY = "retry"
    SKIP = "skip"
    ROLLBACK = "rollback"
    ALTERNATIVE = "alternative"
    MANUAL = "manual"
    ABORT = "abort"


@dataclass
class ErrorContext:
    """Comprehensive error context information."""
    id: str
    timestamp: datetime
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    
    # Execution context
    execution_id: Optional[str] = None
    project_id: Optional[str] = None
    phase_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # Error details
    traceback_text: str = ""
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    
    # Environmental context
    system_state: Dict[str, Any] = field(default_factory=dict)
    execution_state: Dict[str, Any] = field(default_factory=dict)
    preceding_actions: List[str] = field(default_factory=list)
    
    # Recovery context
    attempted_recoveries: List[Dict[str, Any]] = field(default_factory=list)
    successful_recovery: Optional[Dict[str, Any]] = None
    recovery_suggestions: List[str] = field(default_factory=list)
    
    # Learning context
    similar_errors: List[str] = field(default_factory=list)  # IDs of similar errors
    patterns: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorPattern:
    """Pattern identified from multiple error occurrences."""
    id: str
    pattern_type: str
    description: str
    error_signature: str
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime
    
    # Pattern characteristics
    common_elements: Dict[str, Any] = field(default_factory=dict)
    variations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recovery information
    successful_recoveries: List[Dict[str, Any]] = field(default_factory=list)
    recovery_success_rate: float = 0.0
    recommended_strategy: Optional[RecoveryStrategy] = None
    
    # Context
    affected_components: Set[str] = field(default_factory=set)
    environmental_factors: Dict[str, Any] = field(default_factory=dict)
    
    # Learning
    prevention_strategies: List[str] = field(default_factory=list)
    monitoring_recommendations: List[str] = field(default_factory=list)


class ErrorContextManager:
    """Manages error context preservation and learning."""
    
    def __init__(
        self,
        memory_store: PersistentMemoryStore,
        context_accumulator: Optional[ContextAccumulator] = None
    ):
        """Initialize the error context manager."""
        self.memory_store = memory_store
        self.context_accumulator = context_accumulator
        
        # Error tracking
        self.error_contexts: Dict[str, ErrorContext] = {}
        self.error_patterns: Dict[str, ErrorPattern] = {}
        
        # Configuration
        self.max_similar_errors = 10
        self.pattern_min_occurrences = 3
        self.similarity_threshold = 0.7
        
        # Classification rules
        self.classification_rules = self._setup_classification_rules()
        
        # Load existing patterns
        self._load_existing_patterns()
        
        logger.info("Error Context Manager initialized")
    
    def capture_error_context(
        self,
        error: Exception,
        execution_id: Optional[str] = None,
        project_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        task_id: Optional[str] = None,
        system_state: Optional[Dict[str, Any]] = None,
        execution_state: Optional[Dict[str, Any]] = None,
        preceding_actions: Optional[List[str]] = None
    ) -> ErrorContext:
        """Capture comprehensive error context."""
        # Extract error information
        error_info = self._extract_error_info(error)
        
        # Classify error
        severity = self._classify_severity(error, error_info)
        category = self._classify_category(error, error_info)
        
        # Generate unique ID
        error_id = self._generate_error_id(error, error_info, execution_id)
        
        # Create error context
        error_context = ErrorContext(
            id=error_id,
            timestamp=datetime.now(),
            error_type=type(error).__name__,
            error_message=str(error),
            severity=severity,
            category=category,
            execution_id=execution_id,
            project_id=project_id,
            phase_id=phase_id,
            task_id=task_id,
            traceback_text=error_info["traceback"],
            source_file=error_info["source_file"],
            line_number=error_info["line_number"],
            function_name=error_info["function_name"],
            system_state=system_state or {},
            execution_state=execution_state or {},
            preceding_actions=preceding_actions or []
        )
        
        # Find similar errors
        error_context.similar_errors = self._find_similar_errors(error_context)
        
        # Generate recovery suggestions
        error_context.recovery_suggestions = self._generate_recovery_suggestions(error_context)
        
        # Add contextual tags
        error_context.tags = self._generate_tags(error_context)
        
        # Store error context
        self.error_contexts[error_id] = error_context
        self._persist_error_context(error_context)
        
        # Add to context accumulator if available
        if self.context_accumulator and execution_id:
            self.context_accumulator.add_error_context(
                execution_id,
                error,
                phase_id,
                task_id,
                {
                    "error_id": error_id,
                    "severity": severity.value,
                    "category": category.value,
                    "recovery_suggestions": error_context.recovery_suggestions
                }
            )
        
        # Update patterns
        self._update_error_patterns(error_context)
        
        logger.error(f"Captured error context: {error_id} - {error_context.error_message}")
        
        return error_context
    
    def record_recovery_attempt(
        self,
        error_id: str,
        strategy: RecoveryStrategy,
        actions: List[str],
        success: bool,
        notes: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record a recovery attempt."""
        if error_id not in self.error_contexts:
            logger.warning(f"Error context not found: {error_id}")
            return False
        
        error_context = self.error_contexts[error_id]
        
        recovery_record = {
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy.value,
            "actions": actions,
            "success": success,
            "notes": notes,
            "metadata": metadata or {}
        }
        
        error_context.attempted_recoveries.append(recovery_record)
        
        if success and not error_context.successful_recovery:
            error_context.successful_recovery = recovery_record
            
            # Learn from successful recovery
            self._learn_from_recovery(error_context, recovery_record)
        
        # Update stored context
        self._persist_error_context(error_context)
        
        logger.info(f"Recorded recovery attempt for {error_id}: {strategy.value} ({'success' if success else 'failure'})")
        
        return True
    
    def get_recovery_suggestions(self, error_id: str) -> List[str]:
        """Get recovery suggestions for an error."""
        if error_id not in self.error_contexts:
            return []
        
        error_context = self.error_contexts[error_id]
        suggestions = error_context.recovery_suggestions.copy()
        
        # Add pattern-based suggestions
        pattern_suggestions = self._get_pattern_suggestions(error_context)
        suggestions.extend(pattern_suggestions)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions
    
    def get_similar_errors(
        self,
        error_id: str,
        limit: int = 10
    ) -> List[ErrorContext]:
        """Get similar error contexts."""
        if error_id not in self.error_contexts:
            return []
        
        error_context = self.error_contexts[error_id]
        similar_contexts = []
        
        for similar_id in error_context.similar_errors[:limit]:
            if similar_id in self.error_contexts:
                similar_contexts.append(self.error_contexts[similar_id])
        
        return similar_contexts
    
    def get_error_patterns(
        self,
        category: Optional[ErrorCategory] = None,
        min_occurrences: int = 3
    ) -> List[ErrorPattern]:
        """Get identified error patterns."""
        patterns = list(self.error_patterns.values())
        
        if category:
            patterns = [
                p for p in patterns
                if category.value in p.common_elements.get("categories", [])
            ]
        
        patterns = [p for p in patterns if p.occurrence_count >= min_occurrences]
        
        # Sort by occurrence count and recency
        patterns.sort(
            key=lambda p: (p.occurrence_count, p.last_seen),
            reverse=True
        )
        
        return patterns
    
    def export_error_knowledge(self) -> Dict[str, Any]:
        """Export accumulated error knowledge."""
        return {
            "metadata": {
                "export_time": datetime.now().isoformat(),
                "total_errors": len(self.error_contexts),
                "total_patterns": len(self.error_patterns)
            },
            "patterns": [
                {
                    "id": pattern.id,
                    "pattern_type": pattern.pattern_type,
                    "description": pattern.description,
                    "error_signature": pattern.error_signature,
                    "occurrence_count": pattern.occurrence_count,
                    "first_seen": pattern.first_seen.isoformat(),
                    "last_seen": pattern.last_seen.isoformat(),
                    "common_elements": pattern.common_elements,
                    "successful_recoveries": pattern.successful_recoveries,
                    "recovery_success_rate": pattern.recovery_success_rate,
                    "recommended_strategy": pattern.recommended_strategy.value if pattern.recommended_strategy else None,
                    "prevention_strategies": pattern.prevention_strategies,
                    "monitoring_recommendations": pattern.monitoring_recommendations
                }
                for pattern in self.error_patterns.values()
            ],
            "classification_rules": self.classification_rules,
            "statistics": self._calculate_error_statistics()
        }
    
    def _extract_error_info(self, error: Exception) -> Dict[str, Any]:
        """Extract detailed information from an exception."""
        tb = traceback.format_exc()
        
        # Extract source location
        source_file = None
        line_number = None
        function_name = None
        
        try:
            tb_lines = tb.split('\n')
            for line in tb_lines:
                if 'File "' in line and 'line' in line:
                    # Parse line like: File "/path/to/file.py", line 123, in function_name
                    match = re.search(r'File "([^"]+)", line (\d+), in (.+)', line)
                    if match:
                        source_file = match.group(1).split('/')[-1]  # Just filename
                        line_number = int(match.group(2))
                        function_name = match.group(3)
                        break
        except Exception:
            pass  # Fallback to defaults
        
        return {
            "traceback": tb,
            "source_file": source_file,
            "line_number": line_number,
            "function_name": function_name
        }
    
    def _classify_severity(self, error: Exception, error_info: Dict[str, Any]) -> ErrorSeverity:
        """Classify error severity."""
        error_type = type(error).__name__
        message = str(error).lower()
        
        # Critical errors
        if error_type in ["SystemExit", "KeyboardInterrupt", "MemoryError"]:
            return ErrorSeverity.CRITICAL
        
        if any(word in message for word in ["critical", "fatal", "corruption"]):
            return ErrorSeverity.CRITICAL
        
        # High severity
        if error_type in ["PermissionError", "FileNotFoundError", "ConnectionError"]:
            return ErrorSeverity.HIGH
        
        if any(word in message for word in ["permission", "access", "connection", "network"]):
            return ErrorSeverity.HIGH
        
        # Medium severity
        if error_type in ["ValueError", "TypeError", "AttributeError"]:
            return ErrorSeverity.MEDIUM
        
        # Default to medium
        return ErrorSeverity.MEDIUM
    
    def _classify_category(self, error: Exception, error_info: Dict[str, Any]) -> ErrorCategory:
        """Classify error category."""
        error_type = type(error).__name__
        message = str(error).lower()
        
        # Use classification rules
        for category, rules in self.classification_rules.items():
            if error_type in rules["error_types"]:
                return ErrorCategory(category)
            
            if any(pattern in message for pattern in rules["message_patterns"]):
                return ErrorCategory(category)
        
        return ErrorCategory.UNKNOWN
    
    def _setup_classification_rules(self) -> Dict[str, Dict[str, List[str]]]:
        """Setup error classification rules."""
        return {
            "syntax": {
                "error_types": ["SyntaxError", "IndentationError", "TabError"],
                "message_patterns": ["syntax", "indent", "tab", "unexpected token"]
            },
            "runtime": {
                "error_types": ["RuntimeError", "RecursionError", "SystemError"],
                "message_patterns": ["runtime", "recursion", "system"]
            },
            "logic": {
                "error_types": ["ValueError", "TypeError", "AttributeError", "KeyError", "IndexError"],
                "message_patterns": ["value", "type", "attribute", "key", "index"]
            },
            "network": {
                "error_types": ["ConnectionError", "URLError", "HTTPError", "TimeoutError"],
                "message_patterns": ["connection", "network", "http", "url", "timeout"]
            },
            "file_system": {
                "error_types": ["FileNotFoundError", "FileExistsError", "IsADirectoryError"],
                "message_patterns": ["file", "directory", "path", "no such file"]
            },
            "permission": {
                "error_types": ["PermissionError"],
                "message_patterns": ["permission", "access", "denied", "forbidden"]
            },
            "dependency": {
                "error_types": ["ImportError", "ModuleNotFoundError"],
                "message_patterns": ["import", "module", "package", "dependency"]
            },
            "configuration": {
                "error_types": ["ConfigurationError"],
                "message_patterns": ["config", "setting", "parameter", "option"]
            },
            "resource": {
                "error_types": ["MemoryError", "ResourceWarning"],
                "message_patterns": ["memory", "resource", "quota", "limit"]
            },
            "validation": {
                "error_types": ["ValidationError", "AssertionError"],
                "message_patterns": ["validation", "assertion", "invalid", "constraint"]
            }
        }
    
    def _find_similar_errors(self, error_context: ErrorContext) -> List[str]:
        """Find similar error contexts."""
        similar_errors = []
        
        # Create error signature for comparison
        signature = self._create_error_signature(error_context)
        
        # Load recent errors from memory
        recent_errors = self.memory_store.query(
            query_obj_from_dict({
                "memory_type": MemoryType.ERROR,
                "tags": ["error_context"],
                "limit": 100
            })
        )
        
        for entry in recent_errors:
            if entry.id == f"error_context_{error_context.id}":
                continue  # Skip self
            
            stored_context = entry.data
            if isinstance(stored_context, dict):
                stored_signature = self._create_error_signature_from_dict(stored_context)
                similarity = self._calculate_similarity(signature, stored_signature)
                
                if similarity >= self.similarity_threshold:
                    similar_errors.append(stored_context.get("id", entry.id))
        
        return similar_errors[:self.max_similar_errors]
    
    def _create_error_signature(self, error_context: ErrorContext) -> Dict[str, Any]:
        """Create error signature for similarity comparison."""
        return {
            "error_type": error_context.error_type,
            "category": error_context.category.value,
            "severity": error_context.severity.value,
            "message_pattern": self._extract_message_pattern(error_context.error_message),
            "source_file": error_context.source_file,
            "function_name": error_context.function_name
        }
    
    def _create_error_signature_from_dict(self, error_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Create error signature from dictionary representation."""
        return {
            "error_type": error_dict.get("error_type"),
            "category": error_dict.get("category"),
            "severity": error_dict.get("severity"),
            "message_pattern": self._extract_message_pattern(error_dict.get("error_message", "")),
            "source_file": error_dict.get("source_file"),
            "function_name": error_dict.get("function_name")
        }
    
    def _extract_message_pattern(self, message: str) -> str:
        """Extract pattern from error message."""
        if not message:
            return ""
        
        # Remove variable parts
        patterns = [
            (r'\b\d+\b', '<NUMBER>'),
            (r'["\'][^"\']*["\']', '<STRING>'),
            (r'\b[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}\b', '<UUID>'),
            (r'/[^/\s]+', '<PATH>')
        ]
        
        pattern = message
        for regex, replacement in patterns:
            pattern = re.sub(regex, replacement, pattern)
        
        return pattern[:200]  # Limit length
    
    def _calculate_similarity(self, sig1: Dict[str, Any], sig2: Dict[str, Any]) -> float:
        """Calculate similarity between error signatures."""
        score = 0.0
        total_weight = 0.0
        
        weights = {
            "error_type": 0.3,
            "category": 0.2,
            "message_pattern": 0.3,
            "source_file": 0.1,
            "function_name": 0.1
        }
        
        for field, weight in weights.items():
            total_weight += weight
            
            val1 = sig1.get(field)
            val2 = sig2.get(field)
            
            if val1 == val2:
                score += weight
            elif val1 and val2 and isinstance(val1, str) and isinstance(val2, str):
                # Partial string similarity
                if val1.lower() in val2.lower() or val2.lower() in val1.lower():
                    score += weight * 0.5
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _generate_recovery_suggestions(self, error_context: ErrorContext) -> List[str]:
        """Generate recovery suggestions based on error context."""
        suggestions = []
        
        # Category-based suggestions
        category_suggestions = {
            ErrorCategory.SYNTAX: [
                "Check syntax in source file",
                "Verify indentation and brackets",
                "Use a code linter to identify issues"
            ],
            ErrorCategory.NETWORK: [
                "Check network connectivity",
                "Verify URL and endpoints",
                "Implement retry logic with backoff"
            ],
            ErrorCategory.FILE_SYSTEM: [
                "Verify file paths exist",
                "Check file permissions",
                "Ensure directory structure is correct"
            ],
            ErrorCategory.PERMISSION: [
                "Check file/directory permissions",
                "Run with appropriate user privileges",
                "Verify access rights for resources"
            ],
            ErrorCategory.DEPENDENCY: [
                "Install missing dependencies",
                "Check package versions",
                "Verify import paths"
            ]
        }
        
        suggestions.extend(category_suggestions.get(error_context.category, []))
        
        # Severity-based suggestions
        if error_context.severity == ErrorSeverity.CRITICAL:
            suggestions.extend([
                "Stop execution and investigate immediately",
                "Check system resources and stability",
                "Review recent changes that might have caused this"
            ])
        
        return suggestions
    
    def _generate_tags(self, error_context: ErrorContext) -> List[str]:
        """Generate contextual tags for error."""
        tags = [
            "error_context",
            error_context.error_type.lower(),
            error_context.category.value,
            error_context.severity.value
        ]
        
        if error_context.source_file:
            tags.append(f"file_{error_context.source_file}")
        
        if error_context.function_name:
            tags.append(f"function_{error_context.function_name}")
        
        if error_context.project_id:
            tags.append(f"project_{error_context.project_id}")
        
        return tags
    
    def _generate_error_id(
        self,
        error: Exception,
        error_info: Dict[str, Any],
        execution_id: Optional[str]
    ) -> str:
        """Generate unique error ID."""
        content = f"{type(error).__name__}:{str(error)}:{execution_id}:{datetime.now().timestamp()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _persist_error_context(self, error_context: ErrorContext) -> None:
        """Persist error context to memory store."""
        context_data = {
            "id": error_context.id,
            "timestamp": error_context.timestamp.isoformat(),
            "error_type": error_context.error_type,
            "error_message": error_context.error_message,
            "severity": error_context.severity.value,
            "category": error_context.category.value,
            "execution_id": error_context.execution_id,
            "project_id": error_context.project_id,
            "phase_id": error_context.phase_id,
            "task_id": error_context.task_id,
            "traceback_text": error_context.traceback_text,
            "source_file": error_context.source_file,
            "line_number": error_context.line_number,
            "function_name": error_context.function_name,
            "system_state": error_context.system_state,
            "execution_state": error_context.execution_state,
            "preceding_actions": error_context.preceding_actions,
            "attempted_recoveries": error_context.attempted_recoveries,
            "successful_recovery": error_context.successful_recovery,
            "recovery_suggestions": error_context.recovery_suggestions,
            "similar_errors": error_context.similar_errors,
            "patterns": error_context.patterns,
            "lessons_learned": error_context.lessons_learned,
            "tags": error_context.tags,
            "metadata": error_context.metadata
        }
        
        self.memory_store.store(
            f"error_context_{error_context.id}",
            context_data,
            MemoryType.ERROR,
            MemoryPriority.HIGH,
            tags=error_context.tags,
            ttl_hours=168  # Keep for 1 week
        )
    
    def _update_error_patterns(self, error_context: ErrorContext) -> None:
        """Update error patterns based on new error context."""
        signature = self._create_error_signature(error_context)
        pattern_key = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:16]
        
        if pattern_key in self.error_patterns:
            # Update existing pattern
            pattern = self.error_patterns[pattern_key]
            pattern.occurrence_count += 1
            pattern.last_seen = error_context.timestamp
            
            # Add variation if different
            variation = {
                "error_id": error_context.id,
                "message": error_context.error_message,
                "context": {
                    "project_id": error_context.project_id,
                    "phase_id": error_context.phase_id,
                    "task_id": error_context.task_id
                }
            }
            
            if variation not in pattern.variations:
                pattern.variations.append(variation)
                if len(pattern.variations) > 10:  # Keep only recent variations
                    pattern.variations = pattern.variations[-10:]
        
        else:
            # Create new pattern
            if len(self.error_patterns) >= self.pattern_min_occurrences:
                pattern = ErrorPattern(
                    id=pattern_key,
                    pattern_type="error_signature",
                    description=f"{signature['error_type']} in {signature.get('source_file', 'unknown')}",
                    error_signature=json.dumps(signature, sort_keys=True),
                    occurrence_count=1,
                    first_seen=error_context.timestamp,
                    last_seen=error_context.timestamp,
                    common_elements=signature,
                    variations=[{
                        "error_id": error_context.id,
                        "message": error_context.error_message,
                        "context": {
                            "project_id": error_context.project_id,
                            "phase_id": error_context.phase_id,
                            "task_id": error_context.task_id
                        }
                    }]
                )
                
                self.error_patterns[pattern_key] = pattern
    
    def _learn_from_recovery(
        self,
        error_context: ErrorContext,
        recovery_record: Dict[str, Any]
    ) -> None:
        """Learn from successful recovery."""
        # Update error context with lessons learned
        lesson = f"Successfully recovered using {recovery_record['strategy']} strategy"
        if lesson not in error_context.lessons_learned:
            error_context.lessons_learned.append(lesson)
        
        # Update patterns with successful recovery
        signature = self._create_error_signature(error_context)
        pattern_key = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:16]
        
        if pattern_key in self.error_patterns:
            pattern = self.error_patterns[pattern_key]
            pattern.successful_recoveries.append(recovery_record)
            
            # Update success rate
            total_attempts = len([r for r in pattern.successful_recoveries if r.get("success")])
            if total_attempts > 0:
                pattern.recovery_success_rate = len(pattern.successful_recoveries) / total_attempts
            
            # Update recommended strategy
            strategy_counts = {}
            for recovery in pattern.successful_recoveries:
                strategy = recovery.get("strategy")
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
            if strategy_counts:
                most_successful = max(strategy_counts.items(), key=lambda x: x[1])
                pattern.recommended_strategy = RecoveryStrategy(most_successful[0])
    
    def _get_pattern_suggestions(self, error_context: ErrorContext) -> List[str]:
        """Get recovery suggestions based on patterns."""
        suggestions = []
        
        signature = self._create_error_signature(error_context)
        pattern_key = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:16]
        
        if pattern_key in self.error_patterns:
            pattern = self.error_patterns[pattern_key]
            
            if pattern.recommended_strategy:
                suggestions.append(f"Recommended strategy: {pattern.recommended_strategy.value}")
            
            if pattern.successful_recoveries:
                recent_recovery = pattern.successful_recoveries[-1]
                if recent_recovery.get("notes"):
                    suggestions.append(f"Previous successful approach: {recent_recovery['notes']}")
            
            suggestions.extend(pattern.prevention_strategies)
        
        return suggestions
    
    def _load_existing_patterns(self) -> None:
        """Load existing error patterns from memory."""
        pattern_entries = self.memory_store.query(
            query_obj_from_dict({
                "memory_type": MemoryType.PATTERN,
                "tags": ["error_pattern"],
                "limit": 1000
            })
        )
        
        for entry in pattern_entries:
            if isinstance(entry.data, dict):
                try:
                    pattern = ErrorPattern(
                        id=entry.data["id"],
                        pattern_type=entry.data["pattern_type"],
                        description=entry.data["description"],
                        error_signature=entry.data["error_signature"],
                        occurrence_count=entry.data["occurrence_count"],
                        first_seen=datetime.fromisoformat(entry.data["first_seen"]),
                        last_seen=datetime.fromisoformat(entry.data["last_seen"]),
                        common_elements=entry.data.get("common_elements", {}),
                        variations=entry.data.get("variations", []),
                        successful_recoveries=entry.data.get("successful_recoveries", []),
                        recovery_success_rate=entry.data.get("recovery_success_rate", 0.0),
                        recommended_strategy=RecoveryStrategy(entry.data["recommended_strategy"]) if entry.data.get("recommended_strategy") else None,
                        affected_components=set(entry.data.get("affected_components", [])),
                        environmental_factors=entry.data.get("environmental_factors", {}),
                        prevention_strategies=entry.data.get("prevention_strategies", []),
                        monitoring_recommendations=entry.data.get("monitoring_recommendations", [])
                    )
                    
                    self.error_patterns[pattern.id] = pattern
                
                except Exception as e:
                    logger.error(f"Error loading pattern {entry.id}: {e}")
    
    def _calculate_error_statistics(self) -> Dict[str, Any]:
        """Calculate error statistics."""
        total_errors = len(self.error_contexts)
        
        # Count by category
        category_counts = {}
        for context in self.error_contexts.values():
            category = context.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for context in self.error_contexts.values():
            severity = context.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Recovery success rate
        total_recoveries = sum(
            len(context.attempted_recoveries)
            for context in self.error_contexts.values()
        )
        
        successful_recoveries = sum(
            1 for context in self.error_contexts.values()
            if context.successful_recovery
        )
        
        recovery_rate = (successful_recoveries / total_recoveries) if total_recoveries > 0 else 0.0
        
        return {
            "total_errors": total_errors,
            "category_distribution": category_counts,
            "severity_distribution": severity_counts,
            "total_patterns": len(self.error_patterns),
            "recovery_success_rate": recovery_rate,
            "total_recoveries_attempted": total_recoveries,
            "successful_recoveries": successful_recoveries
        }


def query_obj_from_dict(query_dict: Dict[str, Any]):
    """Helper to create query object from dictionary."""
    from .store import MemoryQuery
    return MemoryQuery(
        memory_type=query_dict.get("memory_type"),
        key_pattern=query_dict.get("key_pattern"),
        tags=query_dict.get("tags", []),
        priority_min=query_dict.get("priority_min"),
        since=query_dict.get("since"),
        until=query_dict.get("until"),
        limit=query_dict.get("limit", 100),
        include_expired=query_dict.get("include_expired", False)
    )