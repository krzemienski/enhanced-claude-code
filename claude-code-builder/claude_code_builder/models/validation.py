"""Validation models for Claude Code Builder."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Pattern, Callable
from datetime import datetime
from pathlib import Path
import re
from enum import Enum

from .base import SerializableModel, TimestampedModel
from ..exceptions import ValidationError


class ValidationLevel(Enum):
    """Validation severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    
    def is_blocking(self) -> bool:
        """Check if level blocks execution."""
        return self in [ValidationLevel.ERROR, ValidationLevel.CRITICAL]


class ValidationType(Enum):
    """Types of validation checks."""
    
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    COMPATIBILITY = "compatibility"
    COMPLETENESS = "completeness"


@dataclass
class ValidationIssue(SerializableModel, TimestampedModel):
    """Individual validation issue."""
    
    # All fields must have defaults due to TimestampedModel inheritance
    message: str = ""
    level: ValidationLevel = ValidationLevel.INFO
    validation_type: ValidationType = ValidationType.SYNTAX
    
    # Location information
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    
    # Issue details
    code: Optional[str] = None
    rule_id: Optional[str] = None
    suggestion: Optional[str] = None
    
    # Context
    context_lines: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate issue data."""
        if not self.message:
            raise ValidationError("Validation issue must have a message")
        
        if self.line_number is not None and self.line_number < 1:
            raise ValidationError("Line number must be positive")
        
        if self.column_number is not None and self.column_number < 1:
            raise ValidationError("Column number must be positive")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data["level"] = self.level.value
        data["validation_type"] = self.validation_type.value
        if self.file_path:
            data["file_path"] = str(self.file_path)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationIssue":
        """Create from dictionary."""
        if "level" in data and isinstance(data["level"], str):
            data["level"] = ValidationLevel(data["level"])
        if "validation_type" in data and isinstance(data["validation_type"], str):
            data["validation_type"] = ValidationType(data["validation_type"])
        if "file_path" in data and data["file_path"]:
            data["file_path"] = Path(data["file_path"])
        return super().from_dict(data)
    
    def format_message(self) -> str:
        """Format issue as readable message."""
        parts = []
        
        # Location
        if self.file_path:
            location = str(self.file_path)
            if self.line_number:
                location += f":{self.line_number}"
                if self.column_number:
                    location += f":{self.column_number}"
            parts.append(location)
        
        # Level and type
        parts.append(f"[{self.level.value.upper()}]")
        parts.append(f"({self.validation_type.value})")
        
        # Rule ID
        if self.rule_id:
            parts.append(f"[{self.rule_id}]")
        
        # Message
        parts.append(self.message)
        
        # Suggestion
        if self.suggestion:
            parts.append(f"\n  Suggestion: {self.suggestion}")
        
        return " ".join(parts)


@dataclass
class ValidationRule:
    """Validation rule definition."""
    
    rule_id: str
    name: str
    description: str
    validation_type: ValidationType
    level: ValidationLevel = ValidationLevel.ERROR
    
    # Rule implementation
    pattern: Optional[Pattern] = None
    validator: Optional[Callable] = None
    
    # Rule configuration
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Applicability
    file_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    
    def validate_text(self, text: str, file_path: Optional[Path] = None) -> List[ValidationIssue]:
        """Validate text against rule."""
        issues = []
        
        if not self.enabled:
            return issues
        
        # Check file patterns
        if file_path and self.file_patterns:
            matches_pattern = any(
                file_path.match(pattern) for pattern in self.file_patterns
            )
            if not matches_pattern:
                return issues
        
        if file_path and self.exclude_patterns:
            matches_exclude = any(
                file_path.match(pattern) for pattern in self.exclude_patterns
            )
            if matches_exclude:
                return issues
        
        # Apply pattern-based validation
        if self.pattern:
            for line_num, line in enumerate(text.splitlines(), 1):
                matches = list(self.pattern.finditer(line))
                for match in matches:
                    issue = ValidationIssue(
                        level=self.level,
                        validation_type=self.validation_type,
                        message=self.description,
                        file_path=file_path,
                        line_number=line_num,
                        column_number=match.start() + 1,
                        rule_id=self.rule_id,
                        context_lines=[line]
                    )
                    issues.append(issue)
        
        # Apply custom validator
        if self.validator:
            try:
                validator_issues = self.validator(text, file_path, self.config)
                if validator_issues:
                    for issue in validator_issues:
                        issue.rule_id = self.rule_id
                        issues.extend(validator_issues)
            except Exception as e:
                # Validator error
                issue = ValidationIssue(
                    level=ValidationLevel.ERROR,
                    validation_type=ValidationType.SYNTAX,
                    message=f"Validator error: {str(e)}",
                    file_path=file_path,
                    rule_id=self.rule_id
                )
                issues.append(issue)
        
        return issues


@dataclass
class ValidationResult(SerializableModel, TimestampedModel):
    """Complete validation result."""
    
    # All fields must have defaults due to TimestampedModel inheritance
    target: str = ""
    success: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    
    # Statistics
    total_files: int = 0
    files_validated: int = 0
    files_skipped: int = 0
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Configuration
    rules_applied: List[str] = field(default_factory=list)
    validation_config: Dict[str, Any] = field(default_factory=dict)
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add validation issue."""
        self.issues.append(issue)
        if issue.level.is_blocking():
            self.success = False
    
    def complete(self) -> None:
        """Mark validation as complete."""
        self.completed_at = datetime.utcnow()
    
    def get_issues_by_level(self, level: ValidationLevel) -> List[ValidationIssue]:
        """Get issues by severity level."""
        return [issue for issue in self.issues if issue.level == level]
    
    def get_issues_by_type(self, validation_type: ValidationType) -> List[ValidationIssue]:
        """Get issues by validation type."""
        return [issue for issue in self.issues if issue.validation_type == validation_type]
    
    def get_issues_by_file(self, file_path: Path) -> List[ValidationIssue]:
        """Get issues for specific file."""
        return [issue for issue in self.issues if issue.file_path == file_path]
    
    def get_blocking_issues(self) -> List[ValidationIssue]:
        """Get issues that block execution."""
        return [issue for issue in self.issues if issue.level.is_blocking()]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        issue_counts = {level: 0 for level in ValidationLevel}
        type_counts = {vtype: 0 for vtype in ValidationType}
        
        for issue in self.issues:
            issue_counts[issue.level] += 1
            type_counts[issue.validation_type] += 1
        
        duration = None
        if self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()
        
        return {
            "target": self.target,
            "success": self.success,
            "total_issues": len(self.issues),
            "blocking_issues": len(self.get_blocking_issues()),
            "issues_by_level": {
                level.value: count for level, count in issue_counts.items()
            },
            "issues_by_type": {
                vtype.value: count for vtype, count in type_counts.items()
            },
            "total_files": self.total_files,
            "files_validated": self.files_validated,
            "files_skipped": self.files_skipped,
            "duration": duration,
            "rules_applied": len(self.rules_applied)
        }
    
    def format_report(self, verbose: bool = False) -> str:
        """Format validation report."""
        lines = [
            f"Validation Report for {self.target}",
            "=" * 50,
            f"Status: {'PASSED' if self.success else 'FAILED'}",
            f"Total Issues: {len(self.issues)}",
            f"Blocking Issues: {len(self.get_blocking_issues())}",
            ""
        ]
        
        # Group issues by file
        issues_by_file: Dict[Optional[Path], List[ValidationIssue]] = {}
        for issue in self.issues:
            if issue.file_path not in issues_by_file:
                issues_by_file[issue.file_path] = []
            issues_by_file[issue.file_path].append(issue)
        
        # Format issues
        for file_path, file_issues in sorted(issues_by_file.items()):
            if file_path:
                lines.append(f"\n{file_path}:")
            else:
                lines.append("\nGeneral Issues:")
            
            for issue in sorted(file_issues, key=lambda i: (i.line_number or 0, i.column_number or 0)):
                lines.append(f"  {issue.format_message()}")
                
                if verbose and issue.context_lines:
                    for context_line in issue.context_lines:
                        lines.append(f"    > {context_line}")
        
        # Summary
        lines.extend([
            "",
            "Summary:",
            f"  Files Validated: {self.files_validated}",
            f"  Files Skipped: {self.files_skipped}",
            f"  Rules Applied: {len(self.rules_applied)}"
        ])
        
        if self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()
            lines.append(f"  Duration: {duration:.2f}s")
        
        return "\n".join(lines)
    
    def validate(self) -> None:
        """Validate result data."""
        if not self.target:
            raise ValidationError("Validation result must have a target")
        
        for issue in self.issues:
            issue.validate()


@dataclass
class ValidationConfig(SerializableModel):
    """Validation configuration."""
    
    rules: List[ValidationRule] = field(default_factory=list)
    enabled: bool = True
    fail_on_warning: bool = False
    max_issues: int = 1000
    
    # File filtering
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    
    # Rule sets
    enable_security: bool = True
    enable_performance: bool = True
    enable_style: bool = True
    enable_compatibility: bool = True
    
    # Custom validators
    custom_validators: Dict[str, Callable] = field(default_factory=dict)
    
    def get_enabled_rules(self) -> List[ValidationRule]:
        """Get all enabled rules."""
        if not self.enabled:
            return []
        
        enabled_rules = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # Check rule set filters
            if rule.validation_type == ValidationType.SECURITY and not self.enable_security:
                continue
            if rule.validation_type == ValidationType.PERFORMANCE and not self.enable_performance:
                continue
            if rule.validation_type == ValidationType.STYLE and not self.enable_style:
                continue
            if rule.validation_type == ValidationType.COMPATIBILITY and not self.enable_compatibility:
                continue
            
            enabled_rules.append(rule)
        
        return enabled_rules
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add validation rule."""
        self.rules.append(rule)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove validation rule by ID."""
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                del self.rules[i]
                return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[ValidationRule]:
        """Get rule by ID."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None
    
    def validate(self) -> None:
        """Validate configuration."""
        if self.max_issues < 1:
            raise ValidationError("Max issues must be at least 1")
        
        # Check for duplicate rule IDs
        rule_ids = set()
        for rule in self.rules:
            if rule.rule_id in rule_ids:
                raise ValidationError(f"Duplicate rule ID: {rule.rule_id}")
            rule_ids.add(rule.rule_id)


# Built-in validation rules
BUILTIN_RULES = [
    ValidationRule(
        rule_id="no-hardcoded-secrets",
        name="No Hardcoded Secrets",
        description="Detects hardcoded API keys, passwords, and secrets",
        validation_type=ValidationType.SECURITY,
        level=ValidationLevel.CRITICAL,
        pattern=re.compile(
            r'(?i)(api[_-]?key|password|secret|token|auth)["\']?\s*[:=]\s*["\'][^"\']+["\']'
        )
    ),
    ValidationRule(
        rule_id="no-debug-code",
        name="No Debug Code",
        description="Detects debug print statements and breakpoints",
        validation_type=ValidationType.STYLE,
        level=ValidationLevel.WARNING,
        pattern=re.compile(r'(?:print\(|console\.log|debugger|pdb\.set_trace)')
    ),
    ValidationRule(
        rule_id="no-todo-comments",
        name="No TODO Comments",
        description="Detects TODO, FIXME, and HACK comments",
        validation_type=ValidationType.COMPLETENESS,
        level=ValidationLevel.INFO,
        pattern=re.compile(r'(?i)#\s*(?:TODO|FIXME|HACK|XXX):')
    ),
    ValidationRule(
        rule_id="sql-injection-risk",
        name="SQL Injection Risk",
        description="Detects potential SQL injection vulnerabilities",
        validation_type=ValidationType.SECURITY,
        level=ValidationLevel.ERROR,
        pattern=re.compile(r'(?:execute|query)\s*\(\s*["\'].*%[s@]|f["\'].*SELECT|UPDATE|DELETE')
    )
]