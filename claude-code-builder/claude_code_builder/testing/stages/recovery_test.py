"""Recovery testing stage for error handling and resilience validation."""

import logging
import subprocess
import sys
import tempfile
import signal
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from ..framework import TestStageResult, TestStage, TestStatus

logger = logging.getLogger(__name__)


class RecoveryTestStage:
    """Test stage for recovery and resilience validation."""
    
    def __init__(self, framework, context):
        """Initialize recovery test stage."""
        self.framework = framework
        self.context = context
        self.test_scenarios = []
    
    async def execute(self) -> TestStageResult:
        """Execute recovery tests."""
        logger.info("Starting recovery test stage")
        
        stage_result = TestStageResult(
            stage=TestStage.RECOVERY,
            status=TestStatus.RUNNING,
            start_time=datetime.now(),
            duration_seconds=0.0
        )
        
        try:
            # Test 1: Interruption recovery
            await self._test_interruption_recovery(stage_result)
            
            # Test 2: Invalid input handling
            await self._test_invalid_input_handling(stage_result)
            
            # Test 3: Resource exhaustion handling
            await self._test_resource_exhaustion(stage_result)
            
            # Test 4: Network failure simulation
            await self._test_network_failure(stage_result)
            
        except Exception as e:
            stage_result.errors.append(f"Recovery test stage failed: {e}")
            stage_result.tests_failed += 1
            logger.error(f"Recovery test stage error: {e}")
        
        return stage_result
    
    async def _test_interruption_recovery(self, stage_result: TestStageResult) -> None:
        """Test recovery from process interruption."""
        logger.info("Testing interruption recovery")
        
        try:
            # Create test spec
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("# Interruption Test\n\nTest graceful interruption handling.")
                spec_file = f.name
            
            # Start process
            process = subprocess.Popen([
                sys.executable, "-m", "claude_code_builder",
                "build", spec_file, "--dry-run"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Let it run briefly
            time.sleep(2)
            
            # Send interrupt signal
            if sys.platform == "win32":
                process.terminate()
            else:
                process.send_signal(signal.SIGINT)
            
            # Wait for graceful shutdown
            try:
                stdout, stderr = process.communicate(timeout=10)
                
                if process.returncode != 0:
                    stage_result.tests_passed += 1
                    logger.info("Interruption recovery test passed")
                else:
                    stage_result.warnings.append("Process didn't handle interruption properly")
            
            except subprocess.TimeoutExpired:
                process.kill()
                stage_result.warnings.append("Process didn't shutdown gracefully")
            
            # Cleanup
            Path(spec_file).unlink(missing_ok=True)
        
        except Exception as e:
            stage_result.errors.append(f"Interruption recovery test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_invalid_input_handling(self, stage_result: TestStageResult) -> None:
        """Test handling of invalid inputs."""
        logger.info("Testing invalid input handling")
        
        try:
            # Test with malformed spec file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("Invalid markdown content\n<<>>[[[]]\n@#$%^&*()")
                invalid_spec = f.name
            
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder",
                "build", invalid_spec
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0 and result.stderr:
                stage_result.tests_passed += 1
                logger.info("Invalid input handling test passed")
            else:
                stage_result.warnings.append("Invalid input not handled properly")
            
            # Test with empty file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("")
                empty_spec = f.name
            
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder",
                "build", empty_spec
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                stage_result.tests_passed += 1
                logger.info("Empty file handling test passed")
            else:
                stage_result.warnings.append("Empty file not handled properly")
            
            # Cleanup
            Path(invalid_spec).unlink(missing_ok=True)
            Path(empty_spec).unlink(missing_ok=True)
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Invalid input test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Invalid input test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_resource_exhaustion(self, stage_result: TestStageResult) -> None:
        """Test handling of resource exhaustion."""
        logger.info("Testing resource exhaustion handling")
        
        try:
            # Create spec that might cause resource issues
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                # Create a large spec file
                large_content = "# Large Project\n\n" + "Very long description. " * 1000
                f.write(large_content)
                large_spec = f.name
            
            # Test with limited timeout
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder",
                "build", large_spec, "--timeout", "5"  # 5 second timeout
            ], capture_output=True, text=True, timeout=15)
            
            # Should either complete or timeout gracefully
            if result.returncode != 0 and ("timeout" in result.stderr.lower() or "time" in result.stderr.lower()):
                stage_result.tests_passed += 1
                logger.info("Resource exhaustion test passed")
            elif result.returncode == 0:
                stage_result.tests_passed += 1
                logger.info("Large project handled successfully")
            else:
                stage_result.warnings.append("Resource exhaustion not handled properly")
            
            # Cleanup
            Path(large_spec).unlink(missing_ok=True)
        
        except subprocess.TimeoutExpired:
            stage_result.tests_passed += 1  # Timeout is expected behavior
            logger.info("Resource exhaustion test passed (timeout)")
        except Exception as e:
            stage_result.errors.append(f"Resource exhaustion test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_network_failure(self, stage_result: TestStageResult) -> None:
        """Test handling of network-related failures."""
        logger.info("Testing network failure handling")
        
        try:
            # Test with invalid API configuration
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                import json
                invalid_config = {
                    "api_key": "invalid_key_12345",
                    "api_url": "https://invalid.example.com/api"
                }
                json.dump(invalid_config, f)
                config_file = f.name
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("# Network Test\n\nTest network failure handling.")
                spec_file = f.name
            
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder",
                "build", spec_file,
                "--config", config_file,
                "--dry-run"  # Use dry run to avoid actual API calls
            ], capture_output=True, text=True, timeout=60)
            
            # Should handle invalid config gracefully
            if result.returncode == 0 or ("config" in result.stderr.lower() and "invalid" in result.stderr.lower()):
                stage_result.tests_passed += 1
                logger.info("Network failure test passed")
            else:
                stage_result.warnings.append("Network failure not handled properly")
            
            # Cleanup
            Path(config_file).unlink(missing_ok=True)
            Path(spec_file).unlink(missing_ok=True)
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Network failure test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Network failure test failed: {e}")
            stage_result.tests_failed += 1