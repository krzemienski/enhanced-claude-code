"""Performance testing stage for efficiency and resource usage validation."""

import logging
import subprocess
import sys
import time
import psutil
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from ..framework import TestStageResult, TestStage, TestStatus

logger = logging.getLogger(__name__)


class PerformanceTestStage:
    """Test stage for performance validation."""
    
    def __init__(self, framework, context):
        """Initialize performance test stage."""
        self.framework = framework
        self.context = context
        self.metrics = {}
    
    async def execute(self) -> TestStageResult:
        """Execute performance tests."""
        logger.info("Starting performance test stage")
        
        stage_result = TestStageResult(
            stage=TestStage.PERFORMANCE,
            status=TestStatus.RUNNING,
            start_time=datetime.now(),
            duration_seconds=0.0
        )
        
        try:
            # Test 1: Memory usage
            await self._test_memory_usage(stage_result)
            
            # Test 2: CPU usage
            await self._test_cpu_usage(stage_result)
            
            # Test 3: Execution speed
            await self._test_execution_speed(stage_result)
            
            # Test 4: Concurrent execution
            await self._test_concurrent_execution(stage_result)
            
            # Store metrics
            stage_result.metrics = self.metrics
            
        except Exception as e:
            stage_result.errors.append(f"Performance test stage failed: {e}")
            stage_result.tests_failed += 1
            logger.error(f"Performance test stage error: {e}")
        
        return stage_result
    
    async def _test_memory_usage(self, stage_result: TestStageResult) -> None:
        """Test memory usage during execution."""
        logger.info("Testing memory usage")
        
        try:
            # Monitor memory before execution
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Create simple test spec
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("# Memory Test\n\nSimple project for memory testing.")
                spec_file = f.name
            
            # Execute and monitor memory
            start_time = time.time()
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder",
                "build", spec_file, "--dry-run"
            ], capture_output=True, text=True, timeout=60)
            
            end_time = time.time()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Calculate metrics
            memory_used = final_memory - initial_memory
            execution_time = end_time - start_time
            
            self.metrics["memory_usage_mb"] = memory_used
            self.metrics["initial_memory_mb"] = initial_memory
            self.metrics["final_memory_mb"] = final_memory
            
            # Check thresholds
            if memory_used < 100:  # Less than 100MB
                stage_result.tests_passed += 1
                logger.info(f"Memory usage test passed: {memory_used:.2f}MB")
            else:
                stage_result.warnings.append(f"High memory usage: {memory_used:.2f}MB")
            
            # Cleanup
            Path(spec_file).unlink(missing_ok=True)
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Memory test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Memory test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_cpu_usage(self, stage_result: TestStageResult) -> None:
        """Test CPU usage during execution."""
        logger.info("Testing CPU usage")
        
        try:
            # Create test spec
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("# CPU Test\n\nSimple project for CPU testing.")
                spec_file = f.name
            
            # Monitor CPU usage
            cpu_percentages = []
            
            def monitor_cpu():
                for _ in range(10):  # Monitor for ~10 seconds
                    cpu_percentages.append(psutil.cpu_percent(interval=1))
            
            import threading
            monitor_thread = threading.Thread(target=monitor_cpu)
            monitor_thread.start()
            
            # Execute command
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder",
                "build", spec_file, "--dry-run"
            ], capture_output=True, text=True, timeout=30)
            
            monitor_thread.join(timeout=5)
            
            if cpu_percentages:
                avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
                max_cpu = max(cpu_percentages)
                
                self.metrics["avg_cpu_percent"] = avg_cpu
                self.metrics["max_cpu_percent"] = max_cpu
                
                if avg_cpu < 50:  # Less than 50% average
                    stage_result.tests_passed += 1
                    logger.info(f"CPU usage test passed: {avg_cpu:.2f}% avg")
                else:
                    stage_result.warnings.append(f"High CPU usage: {avg_cpu:.2f}% avg")
            
            # Cleanup
            Path(spec_file).unlink(missing_ok=True)
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("CPU test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"CPU test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_execution_speed(self, stage_result: TestStageResult) -> None:
        """Test execution speed."""
        logger.info("Testing execution speed")
        
        try:
            # Create test spec
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("# Speed Test\n\nSimple project for speed testing.")
                spec_file = f.name
            
            # Measure execution time
            start_time = time.time()
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder",
                "build", spec_file, "--dry-run"
            ], capture_output=True, text=True, timeout=120)
            end_time = time.time()
            
            execution_time = end_time - start_time
            self.metrics["execution_time_seconds"] = execution_time
            
            # Check speed threshold
            if execution_time < 30:  # Less than 30 seconds
                stage_result.tests_passed += 1
                logger.info(f"Speed test passed: {execution_time:.2f}s")
            else:
                stage_result.warnings.append(f"Slow execution: {execution_time:.2f}s")
            
            # Cleanup
            Path(spec_file).unlink(missing_ok=True)
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Speed test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Speed test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_concurrent_execution(self, stage_result: TestStageResult) -> None:
        """Test concurrent execution capabilities."""
        logger.info("Testing concurrent execution")
        
        try:
            # Create multiple test specs
            test_files = []
            for i in range(3):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                    f.write(f"# Concurrent Test {i}\n\nTest project {i}.")
                    test_files.append(f.name)
            
            # Start concurrent processes
            import concurrent.futures
            
            def run_build(spec_file):
                return subprocess.run([
                    sys.executable, "-m", "claude_code_builder",
                    "build", spec_file, "--dry-run"
                ], capture_output=True, text=True, timeout=60)
            
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(run_build, spec) for spec in test_files]
                results = [future.result() for future in concurrent.futures.as_completed(futures, timeout=90)]
            
            end_time = time.time()
            
            # Check results
            successful_runs = sum(1 for r in results if r.returncode == 0)
            total_time = end_time - start_time
            
            self.metrics["concurrent_execution_time"] = total_time
            self.metrics["concurrent_successful_runs"] = successful_runs
            
            if successful_runs >= 2:  # At least 2 out of 3 successful
                stage_result.tests_passed += 1
                logger.info(f"Concurrent test passed: {successful_runs}/3 successful")
            else:
                stage_result.warnings.append(f"Concurrent execution issues: {successful_runs}/3 successful")
            
            # Cleanup
            for test_file in test_files:
                Path(test_file).unlink(missing_ok=True)
        
        except concurrent.futures.TimeoutError:
            stage_result.errors.append("Concurrent execution timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Concurrent execution test failed: {e}")
            stage_result.tests_failed += 1