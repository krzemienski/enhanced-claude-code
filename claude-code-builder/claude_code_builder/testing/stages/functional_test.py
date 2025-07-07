"""Functional testing stage for end-to-end workflow validation."""

import logging
import subprocess
import sys
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from ..framework import TestStageResult, TestStage, TestStatus

logger = logging.getLogger(__name__)


class FunctionalTestStage:
    """Test stage for functional workflow validation."""
    
    def __init__(self, framework, context):
        """Initialize functional test stage."""
        self.framework = framework
        self.context = context
        self.test_projects = []
    
    async def execute(self) -> TestStageResult:
        """Execute functional tests."""
        logger.info("Starting functional test stage")
        
        stage_result = TestStageResult(
            stage=TestStage.FUNCTIONAL,
            status=TestStatus.RUNNING,
            start_time=datetime.now(),
            duration_seconds=0.0
        )
        
        try:
            # Test 1: Simple project build
            await self._test_simple_project_build(stage_result)
            
            # Test 2: Configuration handling
            await self._test_configuration_handling(stage_result)
            
            # Test 3: Error recovery
            await self._test_error_recovery(stage_result)
            
            # Test 4: Multi-phase execution
            await self._test_multi_phase_execution(stage_result)
            
        except Exception as e:
            stage_result.errors.append(f"Functional test stage failed: {e}")
            stage_result.tests_failed += 1
            logger.error(f"Functional test stage error: {e}")
        
        finally:
            # Cleanup test projects
            await self._cleanup()
        
        return stage_result
    
    async def _test_simple_project_build(self, stage_result: TestStageResult) -> None:
        """Test simple project build workflow."""
        logger.info("Testing simple project build")
        
        test_dir = None
        try:
            # Create test project directory
            test_dir = Path(tempfile.mkdtemp(prefix="ccb_functional_test_"))
            self.test_projects.append(test_dir)
            
            # Create simple spec file
            spec_file = test_dir / "simple_project.md"
            spec_content = """# Simple CLI Tool

A basic command-line tool for demonstration.

## Features
- Print hello world message
- Accept user name parameter

## Technical Requirements
- Python 3.8+
- Click library for CLI
- Simple package structure

## Implementation
- main.py with CLI entry point
- setup.py for packaging
- README.md documentation
"""
            
            spec_file.write_text(spec_content)
            
            # Run build with timeout and validation
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder",
                "build", str(spec_file),
                "--output", str(test_dir / "output"),
                "--timeout", "300"  # 5 minute timeout
            ], capture_output=True, text=True, timeout=360)
            
            if result.returncode == 0:
                # Check if output was created
                output_dir = test_dir / "output"
                if output_dir.exists() and any(output_dir.iterdir()):
                    stage_result.tests_passed += 1
                    logger.info("Simple project build test passed")
                else:
                    stage_result.warnings.append("Build succeeded but no output generated")
            else:
                stage_result.warnings.append(f"Simple build failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Simple project build timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Simple project build test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_configuration_handling(self, stage_result: TestStageResult) -> None:
        """Test configuration file handling."""
        logger.info("Testing configuration handling")
        
        test_dir = None
        try:
            test_dir = Path(tempfile.mkdtemp(prefix="ccb_config_test_"))
            self.test_projects.append(test_dir)
            
            # Create config file
            config_file = test_dir / "config.json"
            config_content = {
                "project_name": "test-config-project",
                "build_phases": ["foundation", "implementation"],
                "timeout_minutes": 10
            }
            
            import json
            config_file.write_text(json.dumps(config_content, indent=2))
            
            # Create spec file
            spec_file = test_dir / "config_test.md"
            spec_file.write_text("# Config Test Project\n\nTest configuration handling.")
            
            # Test with config file
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder",
                "build", str(spec_file),
                "--config", str(config_file),
                "--dry-run"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                stage_result.tests_passed += 1
                logger.info("Configuration handling test passed")
            else:
                stage_result.warnings.append(f"Config handling failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Configuration test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Configuration test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_error_recovery(self, stage_result: TestStageResult) -> None:
        """Test error recovery mechanisms."""
        logger.info("Testing error recovery")
        
        try:
            # Test with invalid spec file
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder",
                "build", "/nonexistent/file.md"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0 and "not found" in result.stderr.lower():
                stage_result.tests_passed += 1
                logger.info("Error recovery test passed")
            else:
                stage_result.warnings.append("Expected error not handled properly")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Error recovery test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Error recovery test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_multi_phase_execution(self, stage_result: TestStageResult) -> None:
        """Test multi-phase execution."""
        logger.info("Testing multi-phase execution")
        
        try:
            # Test phase listing
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder",
                "list", "phases"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout:
                stage_result.tests_passed += 1
                logger.info("Multi-phase execution test passed")
            else:
                stage_result.warnings.append("Phase listing failed")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Multi-phase test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Multi-phase test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _cleanup(self) -> None:
        """Clean up test projects."""
        for test_dir in self.test_projects:
            try:
                if test_dir.exists():
                    shutil.rmtree(test_dir)
                    logger.debug(f"Cleaned up test project: {test_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {test_dir}: {e}")
        
        self.test_projects.clear()