"""Testing models for functional test framework."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from .base import SerializableModel, TimestampedModel, IdentifiedModel
from ..exceptions import TestingError
from ..utils.constants import (
    TEST_STAGE_INSTALLATION,
    TEST_STAGE_CLI,
    TEST_STAGE_FUNCTIONAL,
    TEST_STAGE_PERFORMANCE,
    TEST_STAGE_RECOVERY
)


class TestStage(Enum):
    """Testing stages."""
    
    INSTALLATION = TEST_STAGE_INSTALLATION
    CLI = TEST_STAGE_CLI
    FUNCTIONAL = TEST_STAGE_FUNCTIONAL
    PERFORMANCE = TEST_STAGE_PERFORMANCE
    RECOVERY = TEST_STAGE_RECOVERY
    
    def get_order(self) -> int:
        """Get execution order for stage."""
        order_map = {
            TestStage.INSTALLATION: 1,
            TestStage.CLI: 2,
            TestStage.FUNCTIONAL: 3,
            TestStage.PERFORMANCE: 4,
            TestStage.RECOVERY: 5
        }
        return order_map.get(self, 99)


class TestStatus(Enum):
    """Test execution status."""
    
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"
    
    def is_terminal(self) -> bool:
        """Check if status is terminal."""
        return self in [
            TestStatus.PASSED,
            TestStatus.FAILED,
            TestStatus.SKIPPED,
            TestStatus.ERROR,
            TestStatus.TIMEOUT
        ]
    
    def is_success(self) -> bool:
        """Check if status indicates success."""
        return self in [TestStatus.PASSED, TestStatus.SKIPPED]


@dataclass
class TestAssertion:
    """Test assertion definition."""
    
    description: str
    condition: str
    expected: Any
    actual: Optional[Any] = None
    passed: Optional[bool] = None
    error_message: Optional[str] = None
    
    def evaluate(self, actual: Any) -> bool:
        """Evaluate assertion."""
        self.actual = actual
        
        try:
            if self.condition == "equals":
                self.passed = self.actual == self.expected
            elif self.condition == "contains":
                self.passed = self.expected in str(self.actual)
            elif self.condition == "greater_than":
                self.passed = self.actual > self.expected
            elif self.condition == "less_than":
                self.passed = self.actual < self.expected
            elif self.condition == "exists":
                self.passed = self.actual is not None
            elif self.condition == "matches_regex":
                import re
                self.passed = bool(re.match(self.expected, str(self.actual)))
            else:
                self.passed = False
                self.error_message = f"Unknown condition: {self.condition}"
        except Exception as e:
            self.passed = False
            self.error_message = str(e)
        
        if not self.passed and not self.error_message:
            self.error_message = f"Expected {self.expected}, got {self.actual}"
        
        return self.passed


@dataclass
class TestMetrics:
    """Performance and quality metrics."""
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    setup_duration: Optional[timedelta] = None
    execution_duration: Optional[timedelta] = None
    teardown_duration: Optional[timedelta] = None
    
    # Performance
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    disk_io_mb: Optional[float] = None
    network_io_mb: Optional[float] = None
    
    # Quality
    assertions_total: int = 0
    assertions_passed: int = 0
    assertions_failed: int = 0
    code_coverage: Optional[float] = None
    
    # Cost
    api_calls: int = 0
    tokens_used: int = 0
    estimated_cost: float = 0.0
    
    def get_duration(self) -> Optional[timedelta]:
        """Get total test duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    def get_success_rate(self) -> float:
        """Get assertion success rate."""
        if self.assertions_total == 0:
            return 1.0
        return self.assertions_passed / self.assertions_total
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration": self.get_duration().total_seconds() if self.get_duration() else None,
            "setup_duration": self.setup_duration.total_seconds() if self.setup_duration else None,
            "execution_duration": self.execution_duration.total_seconds() if self.execution_duration else None,
            "teardown_duration": self.teardown_duration.total_seconds() if self.teardown_duration else None,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "disk_io_mb": self.disk_io_mb,
            "network_io_mb": self.network_io_mb,
            "assertions_total": self.assertions_total,
            "assertions_passed": self.assertions_passed,
            "assertions_failed": self.assertions_failed,
            "success_rate": self.get_success_rate(),
            "code_coverage": self.code_coverage,
            "api_calls": self.api_calls,
            "tokens_used": self.tokens_used,
            "estimated_cost": self.estimated_cost
        }


@dataclass
class TestCase(SerializableModel, TimestampedModel, IdentifiedModel):
    """Individual test case."""
    
    name: str
    description: str
    stage: TestStage
    
    # Test definition
    setup_steps: List[str] = field(default_factory=list)
    execution_steps: List[str] = field(default_factory=list)
    teardown_steps: List[str] = field(default_factory=list)
    assertions: List[TestAssertion] = field(default_factory=list)
    
    # Test configuration
    timeout: timedelta = timedelta(minutes=5)
    retries: int = 0
    required: bool = True
    enabled: bool = True
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    
    # Execution state
    status: TestStatus = TestStatus.PENDING
    metrics: TestMetrics = field(default_factory=TestMetrics)
    
    # Results
    output: Optional[str] = None
    error: Optional[str] = None
    artifacts: List[Path] = field(default_factory=list)
    screenshots: List[Path] = field(default_factory=list)
    logs: List[Path] = field(default_factory=list)
    
    def validate(self) -> None:
        """Validate test case."""
        if not self.name:
            raise TestingError("Test case must have a name")
        
        if not self.execution_steps:
            raise TestingError("Test case must have execution steps")
    
    def can_run(self, completed_tests: Set[str]) -> bool:
        """Check if test can run based on dependencies."""
        return all(dep in completed_tests for dep in self.depends_on)
    
    def start(self) -> None:
        """Start test execution."""
        self.status = TestStatus.RUNNING
        self.metrics.start_time = datetime.utcnow()
        self.update_timestamp()
    
    def complete(self, success: bool, output: Optional[str] = None, error: Optional[str] = None) -> None:
        """Complete test execution."""
        self.status = TestStatus.PASSED if success else TestStatus.FAILED
        self.output = output
        self.error = error
        self.metrics.end_time = datetime.utcnow()
        self.update_timestamp()
    
    def skip(self, reason: str) -> None:
        """Skip test execution."""
        self.status = TestStatus.SKIPPED
        self.output = f"Skipped: {reason}"
        self.update_timestamp()
    
    def timeout_error(self) -> None:
        """Mark test as timed out."""
        self.status = TestStatus.TIMEOUT
        self.error = f"Test timed out after {self.timeout.total_seconds()}s"
        self.metrics.end_time = datetime.utcnow()
        self.update_timestamp()
    
    def add_artifact(self, path: Path, artifact_type: str = "general") -> None:
        """Add test artifact."""
        if artifact_type == "screenshot":
            self.screenshots.append(path)
        elif artifact_type == "log":
            self.logs.append(path)
        else:
            self.artifacts.append(path)
    
    def evaluate_assertions(self) -> bool:
        """Evaluate all test assertions."""
        all_passed = True
        
        for assertion in self.assertions:
            # Note: Actual evaluation would happen during test execution
            # This is a placeholder for the structure
            if assertion.passed is False:
                all_passed = False
            
            # Update metrics
            self.metrics.assertions_total += 1
            if assertion.passed:
                self.metrics.assertions_passed += 1
            else:
                self.metrics.assertions_failed += 1
        
        return all_passed


@dataclass
class TestPlan(SerializableModel, TimestampedModel, IdentifiedModel):
    """Complete test plan for a project."""
    
    name: str
    description: str
    test_cases: List[TestCase] = field(default_factory=list)
    
    # Plan configuration
    parallel_execution: bool = True
    max_parallel_tests: int = 4
    fail_fast: bool = False
    continue_on_error: bool = True
    
    # Environment setup
    environment_variables: Dict[str, str] = field(default_factory=dict)
    required_services: List[str] = field(default_factory=list)
    setup_commands: List[str] = field(default_factory=list)
    teardown_commands: List[str] = field(default_factory=list)
    
    # Test data
    test_data_dir: Optional[Path] = None
    fixtures: Dict[str, Any] = field(default_factory=dict)
    
    # Coverage settings
    coverage_enabled: bool = True
    coverage_threshold: float = 0.8
    coverage_exclude: List[str] = field(default_factory=list)
    
    # Reporting
    generate_html_report: bool = True
    generate_junit_xml: bool = True
    report_dir: Path = Path("./test-reports")
    
    # Internal state
    _test_index: Dict[str, TestCase] = field(default_factory=dict, init=False)
    
    def __post_init__(self):
        """Initialize test plan."""
        super().__init__()
        self._rebuild_index()
    
    def _rebuild_index(self):
        """Rebuild test case index."""
        self._test_index = {test.id: test for test in self.test_cases}
    
    def validate(self) -> None:
        """Validate test plan."""
        if not self.name:
            raise TestingError("Test plan must have a name")
        
        if not 0 <= self.coverage_threshold <= 1:
            raise TestingError("Coverage threshold must be between 0 and 1")
        
        # Validate all test cases
        test_ids = set()
        for test in self.test_cases:
            test.validate()
            if test.id in test_ids:
                raise TestingError(f"Duplicate test ID: {test.id}")
            test_ids.add(test.id)
        
        # Validate dependencies
        for test in self.test_cases:
            for dep in test.depends_on:
                if dep not in test_ids:
                    raise TestingError(f"Test '{test.name}' depends on unknown test '{dep}'")
    
    def add_test_case(self, test_case: TestCase) -> None:
        """Add test case to plan."""
        test_case.validate()
        self.test_cases.append(test_case)
        self._test_index[test_case.id] = test_case
    
    def get_test_case(self, test_id: str) -> Optional[TestCase]:
        """Get test case by ID."""
        return self._test_index.get(test_id)
    
    def get_tests_by_stage(self, stage: TestStage) -> List[TestCase]:
        """Get all tests for a specific stage."""
        return [test for test in self.test_cases if test.stage == stage]
    
    def get_executable_tests(self, completed_tests: Set[str]) -> List[TestCase]:
        """Get tests that can be executed now."""
        return [
            test for test in self.test_cases
            if test.status == TestStatus.PENDING and
            test.enabled and
            test.can_run(completed_tests)
        ]
    
    def get_execution_order(self) -> List[List[TestCase]]:
        """Get test execution order respecting dependencies."""
        # Group by stages first
        stages_order = sorted(TestStage, key=lambda s: s.get_order())
        execution_order = []
        
        for stage in stages_order:
            stage_tests = self.get_tests_by_stage(stage)
            if not stage_tests:
                continue
            
            # Within stage, respect dependencies
            completed = set()
            stage_batches = []
            
            while len(completed) < len(stage_tests):
                batch = []
                for test in stage_tests:
                    if test.id not in completed and test.can_run(completed):
                        batch.append(test)
                
                if not batch:
                    # Circular dependency or all remaining tests are disabled
                    break
                
                stage_batches.append(batch)
                completed.update(test.id for test in batch)
            
            execution_order.extend(stage_batches)
        
        return execution_order


@dataclass
class TestResult(SerializableModel, TimestampedModel):
    """Complete test execution result."""
    
    test_plan: TestPlan
    success: bool = True
    
    # Execution summary
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_duration: Optional[timedelta] = None
    
    # Stage results
    stage_results: Dict[TestStage, Dict[str, Any]] = field(default_factory=dict)
    
    # Metrics
    total_assertions: int = 0
    passed_assertions: int = 0
    failed_assertions: int = 0
    code_coverage: Optional[float] = None
    
    # Performance
    peak_memory_mb: float = 0.0
    avg_cpu_percent: float = 0.0
    total_api_calls: int = 0
    total_cost: float = 0.0
    
    # Artifacts
    report_files: List[Path] = field(default_factory=list)
    coverage_report: Optional[Path] = None
    
    def update_from_test_case(self, test_case: TestCase) -> None:
        """Update results from completed test case."""
        self.total_tests += 1
        
        if test_case.status == TestStatus.PASSED:
            self.passed_tests += 1
        elif test_case.status == TestStatus.FAILED:
            self.failed_tests += 1
            self.success = False
        elif test_case.status == TestStatus.SKIPPED:
            self.skipped_tests += 1
        elif test_case.status in [TestStatus.ERROR, TestStatus.TIMEOUT]:
            self.error_tests += 1
            self.success = False
        
        # Update assertions
        self.total_assertions += test_case.metrics.assertions_total
        self.passed_assertions += test_case.metrics.assertions_passed
        self.failed_assertions += test_case.metrics.assertions_failed
        
        # Update performance metrics
        if test_case.metrics.memory_usage_mb:
            self.peak_memory_mb = max(self.peak_memory_mb, test_case.metrics.memory_usage_mb)
        
        self.total_api_calls += test_case.metrics.api_calls
        self.total_cost += test_case.metrics.estimated_cost
        
        # Update stage results
        if test_case.stage not in self.stage_results:
            self.stage_results[test_case.stage] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "duration": timedelta()
            }
        
        stage_result = self.stage_results[test_case.stage]
        stage_result["total"] += 1
        if test_case.status == TestStatus.PASSED:
            stage_result["passed"] += 1
        elif test_case.status in [TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT]:
            stage_result["failed"] += 1
        
        if test_case.metrics.get_duration():
            stage_result["duration"] += test_case.metrics.get_duration()
    
    def complete(self) -> None:
        """Mark test execution as complete."""
        self.completed_at = datetime.utcnow()
        self.total_duration = self.completed_at - self.started_at
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test execution summary."""
        return {
            "success": self.success,
            "total_tests": self.total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "skipped": self.skipped_tests,
            "errors": self.error_tests,
            "pass_rate": self.passed_tests / self.total_tests if self.total_tests > 0 else 0,
            "total_duration": self.total_duration.total_seconds() if self.total_duration else None,
            "assertions": {
                "total": self.total_assertions,
                "passed": self.passed_assertions,
                "failed": self.failed_assertions,
                "pass_rate": self.passed_assertions / self.total_assertions if self.total_assertions > 0 else 0
            },
            "coverage": self.code_coverage,
            "performance": {
                "peak_memory_mb": self.peak_memory_mb,
                "avg_cpu_percent": self.avg_cpu_percent,
                "total_api_calls": self.total_api_calls,
                "total_cost": self.total_cost
            },
            "stages": {
                stage.value: {
                    "total": result["total"],
                    "passed": result["passed"],
                    "failed": result["failed"],
                    "pass_rate": result["passed"] / result["total"] if result["total"] > 0 else 0,
                    "duration": result["duration"].total_seconds()
                }
                for stage, result in self.stage_results.items()
            }
        }
    
    def generate_report(self) -> str:
        """Generate human-readable test report."""
        lines = [
            f"Test Report: {self.test_plan.name}",
            "=" * 60,
            f"Status: {'PASSED' if self.success else 'FAILED'}",
            f"Duration: {self.total_duration if self.total_duration else 'N/A'}",
            "",
            "Test Summary:",
            f"  Total: {self.total_tests}",
            f"  Passed: {self.passed_tests} ({self.passed_tests/self.total_tests*100:.1f}%)" if self.total_tests > 0 else "  Passed: 0",
            f"  Failed: {self.failed_tests}",
            f"  Skipped: {self.skipped_tests}",
            f"  Errors: {self.error_tests}",
            "",
            "Assertions:",
            f"  Total: {self.total_assertions}",
            f"  Passed: {self.passed_assertions}",
            f"  Failed: {self.failed_assertions}",
            ""
        ]
        
        if self.code_coverage is not None:
            lines.extend([
                f"Code Coverage: {self.code_coverage:.1%}",
                ""
            ])
        
        # Stage breakdown
        lines.append("Stage Results:")
        for stage in sorted(self.stage_results.keys(), key=lambda s: s.get_order()):
            result = self.stage_results[stage]
            lines.append(
                f"  {stage.value}: {result['passed']}/{result['total']} passed "
                f"({result['duration'].total_seconds():.1f}s)"
            )
        
        # Failed tests
        if self.failed_tests > 0 or self.error_tests > 0:
            lines.extend(["", "Failed Tests:"])
            for test in self.test_plan.test_cases:
                if test.status in [TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT]:
                    lines.append(f"  - {test.name}: {test.error or 'Unknown error'}")
        
        return "\n".join(lines)
    
    def validate(self) -> None:
        """Validate test result."""
        self.test_plan.validate()