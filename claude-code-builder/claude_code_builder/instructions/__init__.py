"""Custom Instructions Engine for Claude Code Builder.

This module provides a comprehensive system for defining, parsing, validating,
and executing custom instruction rules.
"""

from .engine import RulesEngine, RuleMatch
from .parser import InstructionParser
from .validator import PatternValidator, InstructionValidator
from .filter import ContextFilter
from .priority import PriorityExecutor, ExecutionPlan, ExecutionResult, ExecutionStrategy
from .loader import RuleLoader
from .executor import RuleExecutor, ExecutionConfig, ExecutionMetrics

__all__ = [
    # Engine
    "RulesEngine",
    "RuleMatch",
    
    # Parser
    "InstructionParser",
    
    # Validator
    "PatternValidator",
    "InstructionValidator",
    
    # Filter
    "ContextFilter",
    
    # Priority
    "PriorityExecutor",
    "ExecutionPlan",
    "ExecutionResult",
    "ExecutionStrategy",
    
    # Loader
    "RuleLoader",
    
    # Executor
    "RuleExecutor",
    "ExecutionConfig",
    "ExecutionMetrics",
]