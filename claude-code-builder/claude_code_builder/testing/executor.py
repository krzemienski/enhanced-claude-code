"""Test execution coordination and management."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

from .framework import TestingFramework, TestStage, TestConfiguration, TestResult
from .stages.installation_test import InstallationTestStage
from .stages.cli_test import CLITestStage
from .stages.functional_test import FunctionalTestStage
from .stages.performance_test import PerformanceTestStage
from .stages.recovery_test import RecoveryTestStage

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPlan:
    """Plan for test execution."""
    stages: List[TestStage]
    parallel: bool = False
    timeout_minutes: int = 30
    retry_failed: bool = True


class TestExecutor:
    """Coordinates and manages test execution."""
    
    def __init__(self, framework: TestingFramework):
        """Initialize test executor."""
        self.framework = framework
        
        # Register stage implementations
        self._register_stages()
        
        logger.info("Test Executor initialized")
    
    def _register_stages(self) -> None:
        """Register test stage implementations."""
        self.framework.register_test_stage(TestStage.INSTALLATION, InstallationTestStage)
        self.framework.register_test_stage(TestStage.CLI, CLITestStage)
        self.framework.register_test_stage(TestStage.FUNCTIONAL, FunctionalTestStage)
        self.framework.register_test_stage(TestStage.PERFORMANCE, PerformanceTestStage)
        self.framework.register_test_stage(TestStage.RECOVERY, RecoveryTestStage)
    
    async def execute_full_suite(
        self,
        project=None,
        execution_id: Optional[str] = None
    ) -> TestResult:
        """Execute complete test suite."""
        return await self.framework.run_comprehensive_test(
            project=project,
            execution_id=execution_id
        )
    
    async def execute_custom_plan(
        self,
        plan: ExecutionPlan,
        project=None,
        execution_id: Optional[str] = None
    ) -> TestResult:
        """Execute custom test plan."""
        # Update framework configuration
        original_config = self.framework.config
        
        try:
            self.framework.config.enabled_stages = plan.stages
            self.framework.config.parallel_execution = plan.parallel
            self.framework.config.timeout_minutes = plan.timeout_minutes
            self.framework.config.retry_failed_tests = plan.retry_failed
            
            return await self.framework.run_comprehensive_test(
                project=project,
                execution_id=execution_id,
                stages=plan.stages
            )
        
        finally:
            # Restore original configuration
            self.framework.config = original_config