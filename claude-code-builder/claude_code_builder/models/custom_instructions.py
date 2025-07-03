"""Models for custom instructions and rules."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Pattern, Tuple
from datetime import datetime
from enum import Enum, auto
import re

from .base import BaseModel, TimestampedModel, IdentifiedModel


class Priority(Enum):
    """Priority levels for instruction rules."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class InstructionContext(BaseModel):
    """Context for instruction execution."""
    project_name: str
    phase: str
    task_name: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a variable from context."""
        return self.variables.get(name, default)
    
    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable in context."""
        self.variables[name] = value


@dataclass
class ValidationResult(BaseModel):
    """Result of validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)
    
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return bool(self.errors or self.warnings)


@dataclass
class InstructionRule(BaseModel):
    """A single instruction rule."""
    name: str
    description: str
    pattern: str
    replacement: str
    priority: Priority = Priority.MEDIUM
    enabled: bool = True
    conditions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps and ID
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    
    # Compiled pattern for performance
    _compiled_pattern: Optional[Pattern] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Initialize the compiled pattern."""
        super().__post_init__()
        self.compile_pattern()
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
    
    def compile_pattern(self) -> None:
        """Compile the regex pattern."""
        try:
            self._compiled_pattern = re.compile(self.pattern, re.MULTILINE | re.DOTALL)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{self.pattern}': {e}")
    
    def match(self, text: str) -> bool:
        """Check if the rule matches the given text."""
        if not self.enabled or not self._compiled_pattern:
            return False
        return bool(self._compiled_pattern.search(text))
    
    def apply(self, text: str) -> str:
        """Apply the rule to the given text."""
        if not self.enabled or not self._compiled_pattern:
            return text
        return self._compiled_pattern.sub(self.replacement, text)
    
    def validate_conditions(self, context: InstructionContext) -> bool:
        """Validate conditions against context."""
        if not self.conditions:
            return True
        
        for condition in self.conditions:
            if not self._evaluate_condition(condition, context):
                return False
        return True
    
    def _evaluate_condition(self, condition: str, context: InstructionContext) -> bool:
        """Evaluate a single condition."""
        # Simple condition evaluation - can be extended
        if "=" in condition:
            key, value = condition.split("=", 1)
            return str(context.get_variable(key.strip())) == value.strip()
        return True


@dataclass
class InstructionSet(BaseModel):
    """A collection of instruction rules."""
    name: str
    description: str
    rules: List[InstructionRule] = field(default_factory=list)
    enabled: bool = True
    priority: Priority = Priority.MEDIUM
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps and ID
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
    
    def add_rule(self, rule: InstructionRule) -> None:
        """Add a rule to the set."""
        if rule not in self.rules:
            self.rules.append(rule)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                self.rules.pop(i)
                return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[InstructionRule]:
        """Get a rule by ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None
    
    def get_enabled_rules(self) -> List[InstructionRule]:
        """Get all enabled rules."""
        return [rule for rule in self.rules if rule.enabled]
    
    def apply_rules(self, text: str, context: InstructionContext) -> str:
        """Apply all enabled rules to the text."""
        if not self.enabled:
            return text
        
        result = text
        for rule in sorted(self.get_enabled_rules(), key=lambda r: r.priority.value):
            if rule.validate_conditions(context):
                result = rule.apply(result)
        
        return result
    
    def validate(self) -> ValidationResult:
        """Validate the instruction set."""
        result = ValidationResult(is_valid=True)
        
        if not self.name:
            result.add_error("InstructionSet name is required")
        
        if not self.rules:
            result.add_warning("InstructionSet has no rules")
        
        # Validate each rule
        for rule in self.rules:
            try:
                rule.compile_pattern()
            except ValueError as e:
                result.add_error(f"Rule '{rule.name}' has invalid pattern: {e}")
        
        return result