"""Functional Testing Framework for comprehensive validation."""

from .framework import (
    TestingFramework,
    TestStage,
    TestSeverity,
    TestConfiguration,
    TestContext,
    TestStageResult
)

from .executor import (
    TestExecutor,
    ExecutionPlan
)

from .analyzer import (
    TestAnalyzer,
    TestAnalysis,
    AnalysisLevel
)

from .report_generator import (
    TestReportGenerator
)

# Stage implementations
from .stages.installation_test import InstallationTestStage
from .stages.cli_test import CLITestStage
from .stages.functional_test import FunctionalTestStage
from .stages.performance_test import PerformanceTestStage
from .stages.recovery_test import RecoveryTestStage

__all__ = [
    # Framework components
    "TestingFramework",
    "TestStage",
    "TestSeverity", 
    "TestConfiguration",
    "TestContext",
    "TestStageResult",
    
    # Execution components
    "TestExecutor",
    "ExecutionPlan",
    
    # Analysis components
    "TestAnalyzer",
    "TestAnalysis",
    "AnalysisLevel",
    
    # Reporting components
    "TestReportGenerator",
    
    # Stage implementations
    "InstallationTestStage",
    "CLITestStage",
    "FunctionalTestStage",
    "PerformanceTestStage",
    "RecoveryTestStage"
]

# Version information
__version__ = "3.0.0"