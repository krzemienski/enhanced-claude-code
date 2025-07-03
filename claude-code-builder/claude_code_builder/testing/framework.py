"""Comprehensive functional testing framework for Claude Code Builder."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
import time

from ..models.testing import TestPlan, TestResult, TestMetrics, TestStatus, TestType
from ..models.project import Project, BuildPhase
from ..execution.orchestrator import ExecutionOrchestrator
from ..memory.store import PersistentMemoryStore, MemoryType, MemoryPriority

logger = logging.getLogger(__name__)


class TestStage(Enum):
    """Testing stages in order of execution."""
    INSTALLATION = "installation"
    CLI = "cli"
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    RECOVERY = "recovery"


class TestSeverity(Enum):
    """Test failure severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class TestConfiguration:
    """Configuration for test execution."""
    enabled_stages: List[TestStage] = field(default_factory=lambda: list(TestStage))
    timeout_minutes: int = 30
    parallel_execution: bool = True
    max_concurrent_tests: int = 4
    retry_failed_tests: bool = True
    max_retries: int = 3
    capture_logs: bool = True
    capture_screenshots: bool = False
    generate_reports: bool = True
    report_formats: List[str] = field(default_factory=lambda: ["json", "html"])
    test_data_path: Optional[Path] = None
    artifact_retention_days: int = 7


@dataclass
class TestContext:
    """Context information for test execution."""
    test_id: str
    execution_id: str
    project: Optional[Project] = None
    stage: Optional[TestStage] = None
    start_time: Optional[datetime] = None
    environment: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[Path] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestStageResult:
    """Result of a single test stage."""
    stage: TestStage
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: float
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    artifacts: List[Path] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class TestingFramework:
    """Comprehensive functional testing framework."""
    
    def __init__(
        self,
        config: Optional[TestConfiguration] = None,
        memory_store: Optional[PersistentMemoryStore] = None,
        orchestrator: Optional[ExecutionOrchestrator] = None
    ):
        """Initialize the testing framework."""
        self.config = config or TestConfiguration()
        self.memory_store = memory_store
        self.orchestrator = orchestrator
        
        # Test stage implementations
        self._stage_implementations: Dict[TestStage, Type] = {}
        
        # Test execution state
        self.active_tests: Dict[str, TestContext] = {}
        self.test_history: List[TestResult] = []
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Performance tracking
        self.stats = {
            "total_tests_run": 0,
            "total_tests_passed": 0,
            "total_tests_failed": 0,
            "avg_test_duration_seconds": 0.0,
            "last_test_run": None
        }
        
        # Initialize test stages
        self._initialize_test_stages()
        
        logger.info("Testing Framework initialized")
    
    def register_test_stage(self, stage: TestStage, implementation: Type) -> None:
        """Register a test stage implementation."""
        self._stage_implementations[stage] = implementation
        logger.debug(f"Registered test stage: {stage.value}")
    
    async def run_comprehensive_test(
        self,
        project: Optional[Project] = None,
        execution_id: Optional[str] = None,
        stages: Optional[List[TestStage]] = None
    ) -> TestResult:
        """Run comprehensive functional test suite."""
        test_id = self._generate_test_id()
        execution_id = execution_id or f"test_{test_id}"
        stages = stages or self.config.enabled_stages
        
        logger.info(f"Starting comprehensive test: {test_id}")
        
        # Create test context
        context = TestContext(
            test_id=test_id,
            execution_id=execution_id,
            project=project,
            start_time=datetime.now(),
            environment=self._get_test_environment()
        )
        
        # Register active test
        with self.lock:
            self.active_tests[test_id] = context
        
        try:
            # Initialize test result
            test_result = TestResult(
                test_id=test_id,
                test_type=TestType.FUNCTIONAL,
                status=TestStatus.RUNNING,
                start_time=context.start_time,
                project_id=project.config.id if project else None,
                execution_id=execution_id
            )
            
            # Execute test stages
            stage_results = []
            
            if self.config.parallel_execution and len(stages) > 1:
                stage_results = await self._run_stages_parallel(context, stages)
            else:
                stage_results = await self._run_stages_sequential(context, stages)
            
            # Aggregate results
            test_result = self._aggregate_stage_results(test_result, stage_results)
            
            # Generate metrics
            test_result.metrics = self._calculate_test_metrics(stage_results)
            
            # Store result
            await self._store_test_result(test_result)
            
            # Update statistics
            self._update_stats(test_result)
            
            logger.info(f"Comprehensive test completed: {test_id} - {test_result.status.value}")
            
            return test_result
        
        except Exception as e:
            logger.error(f"Test execution error: {e}")
            
            # Create failed result
            failed_result = TestResult(
                test_id=test_id,
                test_type=TestType.FUNCTIONAL,
                status=TestStatus.FAILED,
                start_time=context.start_time,
                end_time=datetime.now(),
                project_id=project.config.id if project else None,
                execution_id=execution_id,
                error_message=str(e)
            )
            
            await self._store_test_result(failed_result)
            return failed_result
        
        finally:
            # Clean up active test
            with self.lock:
                if test_id in self.active_tests:
                    del self.active_tests[test_id]
    
    async def run_single_stage(
        self,
        stage: TestStage,
        context: TestContext
    ) -> TestStageResult:
        """Run a single test stage."""
        logger.info(f"Running test stage: {stage.value}")
        
        start_time = datetime.now()
        stage_result = TestStageResult(
            stage=stage,
            status=TestStatus.RUNNING,
            start_time=start_time,
            duration_seconds=0.0
        )
        
        try:
            # Get stage implementation
            if stage not in self._stage_implementations:
                raise ValueError(f"No implementation found for stage: {stage.value}")
            
            stage_impl = self._stage_implementations[stage](self, context)
            
            # Execute stage with timeout
            timeout_seconds = self.config.timeout_minutes * 60
            stage_result = await asyncio.wait_for(
                stage_impl.execute(),
                timeout=timeout_seconds
            )
            
            # Update timing
            stage_result.end_time = datetime.now()
            stage_result.duration_seconds = (stage_result.end_time - start_time).total_seconds()
            
            # Determine overall status
            if stage_result.tests_failed > 0:
                stage_result.status = TestStatus.FAILED
            elif stage_result.tests_passed > 0:
                stage_result.status = TestStatus.PASSED
            else:
                stage_result.status = TestStatus.SKIPPED
            
            logger.info(f"Stage {stage.value} completed: {stage_result.status.value}")
            
            return stage_result
        
        except asyncio.TimeoutError:
            stage_result.status = TestStatus.FAILED
            stage_result.errors.append(f"Stage timeout after {self.config.timeout_minutes} minutes")
            stage_result.end_time = datetime.now()
            stage_result.duration_seconds = (stage_result.end_time - start_time).total_seconds()
            
            logger.error(f"Stage {stage.value} timed out")
            return stage_result
        
        except Exception as e:
            stage_result.status = TestStatus.FAILED
            stage_result.errors.append(str(e))
            stage_result.end_time = datetime.now()
            stage_result.duration_seconds = (stage_result.end_time - start_time).total_seconds()
            
            logger.error(f"Stage {stage.value} failed: {e}")
            return stage_result
    
    def get_test_status(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get current test status."""
        with self.lock:
            if test_id in self.active_tests:
                context = self.active_tests[test_id]
                return {
                    "test_id": test_id,
                    "status": "running",
                    "stage": context.stage.value if context.stage else None,
                    "start_time": context.start_time.isoformat() if context.start_time else None,
                    "duration_seconds": (datetime.now() - context.start_time).total_seconds() if context.start_time else 0
                }
        
        # Check historical results
        for result in reversed(self.test_history):
            if result.test_id == test_id:
                return {
                    "test_id": test_id,
                    "status": result.status.value,
                    "start_time": result.start_time.isoformat() if result.start_time else None,
                    "end_time": result.end_time.isoformat() if result.end_time else None,
                    "duration_seconds": result.duration_seconds,
                    "tests_passed": result.tests_passed,
                    "tests_failed": result.tests_failed
                }
        
        return None
    
    def cancel_test(self, test_id: str) -> bool:
        """Cancel a running test."""
        with self.lock:
            if test_id in self.active_tests:
                # Mark test as cancelled (implementation would need to handle this)
                context = self.active_tests[test_id]
                context.metadata["cancelled"] = True
                logger.info(f"Test cancellation requested: {test_id}")
                return True
        
        return False
    
    def get_test_history(
        self,
        limit: int = 100,
        status_filter: Optional[TestStatus] = None
    ) -> List[TestResult]:
        """Get test execution history."""
        results = self.test_history
        
        if status_filter:
            results = [r for r in results if r.status == status_filter]
        
        return results[-limit:]
    
    def get_framework_stats(self) -> Dict[str, Any]:
        """Get framework statistics."""
        with self.lock:
            stats = self.stats.copy()
            stats["active_tests"] = len(self.active_tests)
            stats["total_test_history"] = len(self.test_history)
            
            # Calculate success rate
            if stats["total_tests_run"] > 0:
                stats["success_rate"] = stats["total_tests_passed"] / stats["total_tests_run"]
            else:
                stats["success_rate"] = 0.0
            
            return stats
    
    async def cleanup_old_artifacts(self, max_age_days: int = None) -> int:
        """Clean up old test artifacts."""
        max_age_days = max_age_days or self.config.artifact_retention_days
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        cleaned_count = 0
        
        # Clean up test artifacts from memory store
        if self.memory_store:
            from ..memory.store import MemoryQuery
            
            old_test_query = MemoryQuery(
                memory_type=MemoryType.TEMPLATE,  # Using TEMPLATE for test artifacts
                tags=["test_artifact"],
                until=cutoff_date,
                limit=1000
            )
            
            old_entries = self.memory_store.query(old_test_query)
            
            for entry in old_entries:
                if self.memory_store.delete(entry.id):
                    cleaned_count += 1
        
        # Clean up local artifact files
        if self.config.test_data_path and self.config.test_data_path.exists():
            for artifact_file in self.config.test_data_path.glob("**/*"):
                if (artifact_file.is_file() and 
                    artifact_file.stat().st_mtime < cutoff_date.timestamp()):
                    try:
                        artifact_file.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove artifact {artifact_file}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} old test artifacts")
        return cleaned_count
    
    def _initialize_test_stages(self) -> None:
        """Initialize test stage implementations."""
        # Stage implementations will be imported and registered
        # This is a placeholder for the actual implementations
        pass
    
    async def _run_stages_sequential(
        self,
        context: TestContext,
        stages: List[TestStage]
    ) -> List[TestStageResult]:
        """Run test stages sequentially."""
        results = []
        
        for stage in stages:
            context.stage = stage
            
            # Skip stage if previous critical failures
            if self._should_skip_stage(stage, results):
                skipped_result = TestStageResult(
                    stage=stage,
                    status=TestStatus.SKIPPED,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_seconds=0.0,
                    tests_skipped=1
                )
                results.append(skipped_result)
                continue
            
            stage_result = await self.run_single_stage(stage, context)
            results.append(stage_result)
            
            # Stop on critical failures
            if (stage_result.status == TestStatus.FAILED and 
                self._is_critical_failure(stage_result)):
                logger.error(f"Critical failure in stage {stage.value}, stopping test execution")
                break
        
        return results
    
    async def _run_stages_parallel(
        self,
        context: TestContext,
        stages: List[TestStage]
    ) -> List[TestStageResult]:
        """Run test stages in parallel where possible."""
        # Group stages by dependencies
        sequential_stages = [TestStage.INSTALLATION, TestStage.CLI]  # Must run first
        parallel_stages = [TestStage.FUNCTIONAL, TestStage.PERFORMANCE, TestStage.RECOVERY]
        
        results = []
        
        # Run sequential stages first
        for stage in sequential_stages:
            if stage in stages:
                context.stage = stage
                stage_result = await self.run_single_stage(stage, context)
                results.append(stage_result)
                
                if (stage_result.status == TestStatus.FAILED and 
                    self._is_critical_failure(stage_result)):
                    return results  # Stop on critical failure
        
        # Run parallel stages
        parallel_tasks = []
        for stage in parallel_stages:
            if stage in stages:
                # Create context copy for each parallel stage
                stage_context = TestContext(
                    test_id=context.test_id,
                    execution_id=context.execution_id,
                    project=context.project,
                    stage=stage,
                    start_time=context.start_time,
                    environment=context.environment.copy(),
                    metadata=context.metadata.copy()
                )
                
                task = asyncio.create_task(
                    self.run_single_stage(stage, stage_context)
                )
                parallel_tasks.append(task)
        
        # Wait for parallel stages to complete
        if parallel_tasks:
            parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
            
            for result in parallel_results:
                if isinstance(result, Exception):
                    # Create failed stage result for exceptions
                    error_result = TestStageResult(
                        stage=TestStage.FUNCTIONAL,  # Default stage
                        status=TestStatus.FAILED,
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        duration_seconds=0.0,
                        errors=[str(result)]
                    )
                    results.append(error_result)
                else:
                    results.append(result)
        
        return results
    
    def _should_skip_stage(self, stage: TestStage, previous_results: List[TestStageResult]) -> bool:
        """Determine if a stage should be skipped based on previous results."""
        # Skip later stages if installation failed
        if stage != TestStage.INSTALLATION:
            installation_results = [r for r in previous_results if r.stage == TestStage.INSTALLATION]
            if installation_results and installation_results[0].status == TestStatus.FAILED:
                return True
        
        # Skip functional tests if CLI tests failed critically
        if stage == TestStage.FUNCTIONAL:
            cli_results = [r for r in previous_results if r.stage == TestStage.CLI]
            if cli_results and self._is_critical_failure(cli_results[0]):
                return True
        
        return False
    
    def _is_critical_failure(self, stage_result: TestStageResult) -> bool:
        """Determine if a stage failure is critical."""
        # Critical if no tests passed and multiple failures
        if stage_result.tests_passed == 0 and stage_result.tests_failed > 2:
            return True
        
        # Critical if specific error patterns
        critical_patterns = ["installation failed", "command not found", "permission denied"]
        for error in stage_result.errors:
            if any(pattern in error.lower() for pattern in critical_patterns):
                return True
        
        return False
    
    def _aggregate_stage_results(
        self,
        test_result: TestResult,
        stage_results: List[TestStageResult]
    ) -> TestResult:
        """Aggregate stage results into overall test result."""
        test_result.end_time = datetime.now()
        test_result.duration_seconds = (test_result.end_time - test_result.start_time).total_seconds()
        
        # Aggregate counts
        test_result.tests_passed = sum(r.tests_passed for r in stage_results)
        test_result.tests_failed = sum(r.tests_failed for r in stage_results)
        test_result.tests_skipped = sum(r.tests_skipped for r in stage_results)
        
        # Determine overall status
        if any(r.status == TestStatus.FAILED for r in stage_results):
            test_result.status = TestStatus.FAILED
        elif all(r.status == TestStatus.SKIPPED for r in stage_results):
            test_result.status = TestStatus.SKIPPED
        elif test_result.tests_passed > 0:
            test_result.status = TestStatus.PASSED
        else:
            test_result.status = TestStatus.FAILED
        
        # Collect errors and warnings
        all_errors = []
        all_warnings = []
        
        for stage_result in stage_results:
            all_errors.extend([f"{stage_result.stage.value}: {error}" for error in stage_result.errors])
            all_warnings.extend([f"{stage_result.stage.value}: {warning}" for warning in stage_result.warnings])
        
        if all_errors:
            test_result.error_message = "; ".join(all_errors[:5])  # Limit to first 5 errors
        
        # Store stage details in metadata
        test_result.metadata["stage_results"] = [
            {
                "stage": r.stage.value,
                "status": r.status.value,
                "duration_seconds": r.duration_seconds,
                "tests_passed": r.tests_passed,
                "tests_failed": r.tests_failed,
                "tests_skipped": r.tests_skipped
            }
            for r in stage_results
        ]
        
        return test_result
    
    def _calculate_test_metrics(self, stage_results: List[TestStageResult]) -> TestMetrics:
        """Calculate comprehensive test metrics."""
        total_duration = sum(r.duration_seconds for r in stage_results)
        total_tests = sum(r.tests_passed + r.tests_failed + r.tests_skipped for r in stage_results)
        
        metrics = TestMetrics(
            total_tests=total_tests,
            passed_tests=sum(r.tests_passed for r in stage_results),
            failed_tests=sum(r.tests_failed for r in stage_results),
            skipped_tests=sum(r.tests_skipped for r in stage_results),
            execution_time_seconds=total_duration,
            success_rate=0.0,
            coverage_percentage=0.0,
            performance_score=0.0
        )
        
        # Calculate success rate
        if total_tests > 0:
            metrics.success_rate = metrics.passed_tests / total_tests
        
        # Calculate performance score based on execution time and success
        if total_duration > 0:
            # Score based on speed (tests per second) and success rate
            tests_per_second = total_tests / total_duration
            metrics.performance_score = min(100.0, tests_per_second * 10 * metrics.success_rate)
        
        # Estimate coverage based on stages completed successfully
        successful_stages = sum(1 for r in stage_results if r.status == TestStatus.PASSED)
        total_stages = len(stage_results)
        if total_stages > 0:
            metrics.coverage_percentage = (successful_stages / total_stages) * 100
        
        return metrics
    
    async def _store_test_result(self, test_result: TestResult) -> None:
        """Store test result in memory store."""
        if self.memory_store:
            result_data = {
                "test_id": test_result.test_id,
                "test_type": test_result.test_type.value,
                "status": test_result.status.value,
                "start_time": test_result.start_time.isoformat() if test_result.start_time else None,
                "end_time": test_result.end_time.isoformat() if test_result.end_time else None,
                "duration_seconds": test_result.duration_seconds,
                "tests_passed": test_result.tests_passed,
                "tests_failed": test_result.tests_failed,
                "tests_skipped": test_result.tests_skipped,
                "project_id": test_result.project_id,
                "execution_id": test_result.execution_id,
                "error_message": test_result.error_message,
                "metrics": test_result.metrics.__dict__ if test_result.metrics else None,
                "metadata": test_result.metadata
            }
            
            self.memory_store.store(
                f"test_result_{test_result.test_id}",
                result_data,
                MemoryType.TEMPLATE,  # Using TEMPLATE for test results
                MemoryPriority.MEDIUM,
                tags=["test_result", test_result.test_type.value, test_result.status.value],
                ttl_hours=168  # Keep for 1 week
            )
        
        # Also store in local history
        with self.lock:
            self.test_history.append(test_result)
            
            # Keep only recent history
            if len(self.test_history) > 1000:
                self.test_history = self.test_history[-500:]
    
    def _update_stats(self, test_result: TestResult) -> None:
        """Update framework statistics."""
        with self.lock:
            self.stats["total_tests_run"] += 1
            self.stats["last_test_run"] = datetime.now().isoformat()
            
            if test_result.status == TestStatus.PASSED:
                self.stats["total_tests_passed"] += 1
            elif test_result.status == TestStatus.FAILED:
                self.stats["total_tests_failed"] += 1
            
            # Update average duration
            total_duration = (self.stats["avg_test_duration_seconds"] * 
                            (self.stats["total_tests_run"] - 1) + 
                            test_result.duration_seconds)
            self.stats["avg_test_duration_seconds"] = total_duration / self.stats["total_tests_run"]
    
    def _get_test_environment(self) -> Dict[str, Any]:
        """Get current test environment information."""
        import platform
        import sys
        import os
        
        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "working_directory": os.getcwd(),
            "environment_variables": {
                k: v for k, v in os.environ.items()
                if not k.startswith("SECRET") and not k.startswith("PASSWORD")
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_test_id(self) -> str:
        """Generate unique test ID."""
        import uuid
        return f"test_{uuid.uuid4().hex[:8]}"