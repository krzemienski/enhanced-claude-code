"""Claude Code Builder - AI-Driven Autonomous Project Builder

A next-generation tool that uses AI to plan optimal build strategies,
execute through intelligent phases, and perform comprehensive functional testing.
"""

__version__ = "3.0.0"
__author__ = "Claude Code Builder Team"
__license__ = "MIT"

from .config.settings import (
    AIConfig,
    ExecutionConfig,
    TestingConfig,
    BuilderConfig
)
from .exceptions.base import (
    ClaudeCodeBuilderError,
    PlanningError,
    ExecutionError,
    ValidationError,
    TestingError
)

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "AIConfig",
    "ExecutionConfig", 
    "TestingConfig",
    "BuilderConfig",
    "ClaudeCodeBuilderError",
    "PlanningError",
    "ExecutionError",
    "ValidationError",
    "TestingError"
]