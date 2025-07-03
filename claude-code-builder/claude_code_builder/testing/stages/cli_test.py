"""CLI testing stage for command-line interface validation."""

import logging
import subprocess
import sys
import tempfile
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from ..framework import TestStageResult, TestStage, TestStatus

logger = logging.getLogger(__name__)


class CLITestStage:
    """Test stage for CLI functionality validation."""
    
    def __init__(self, framework, context):
        """Initialize CLI test stage."""
        self.framework = framework
        self.context = context
        self.test_outputs = []
    
    async def execute(self) -> TestStageResult:
        """Execute CLI tests."""
        logger.info("Starting CLI test stage")
        
        stage_result = TestStageResult(
            stage=TestStage.CLI,
            status=TestStatus.RUNNING,
            start_time=datetime.now(),
            duration_seconds=0.0
        )
        
        try:
            # Test 1: Basic CLI help
            await self._test_help_command(stage_result)
            
            # Test 2: Version command
            await self._test_version_command(stage_result)
            
            # Test 3: Configuration commands
            await self._test_config_commands(stage_result)
            
            # Test 4: List commands
            await self._test_list_commands(stage_result)
            
            # Test 5: Build command (dry run)
            await self._test_build_command_dry_run(stage_result)
            
            # Test 6: Error handling
            await self._test_error_handling(stage_result)
            
            # Test 7: Output formats
            await self._test_output_formats(stage_result)
            
        except Exception as e:
            stage_result.errors.append(f"CLI test stage failed: {e}")
            stage_result.tests_failed += 1
            logger.error(f"CLI test stage error: {e}")
        
        return stage_result
    
    async def _test_help_command(self, stage_result: TestStageResult) -> None:
        """Test CLI help command."""
        logger.info("Testing help command")
        
        try:
            # Test main help
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder", "--help"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                stage_result.errors.append(f"Help command failed: {result.stderr}")
                stage_result.tests_failed += 1
            elif "claude-code-builder" not in result.stdout.lower():
                stage_result.errors.append("Help output missing expected content")
                stage_result.tests_failed += 1
            else:
                stage_result.tests_passed += 1
                logger.info("Help command test passed")
            
            # Test subcommand help
            help_commands = ["build --help", "config --help", "list --help"]
            for cmd in help_commands:
                cmd_parts = [sys.executable, "-m", "claude_code_builder"] + cmd.split()
                help_result = subprocess.run(
                    cmd_parts, capture_output=True, text=True, timeout=30
                )
                
                if help_result.returncode == 0:
                    stage_result.tests_passed += 1
                else:
                    stage_result.warnings.append(f"Help for '{cmd}' failed")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Help command timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Help command test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_version_command(self, stage_result: TestStageResult) -> None:
        """Test version command."""
        logger.info("Testing version command")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder", "--version"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                stage_result.warnings.append(f"Version command failed: {result.stderr}")
            elif not result.stdout.strip():
                stage_result.warnings.append("Version command returned empty output")
            else:
                stage_result.tests_passed += 1
                logger.info(f"Version test passed: {result.stdout.strip()}")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Version command timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Version command test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_config_commands(self, stage_result: TestStageResult) -> None:
        """Test configuration commands."""
        logger.info("Testing config commands")
        
        try:
            # Test config show
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder", "config", "show"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                stage_result.tests_passed += 1
                logger.info("Config show test passed")
            else:
                stage_result.warnings.append(f"Config show failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Config command timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Config command test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_list_commands(self, stage_result: TestStageResult) -> None:
        """Test list commands."""
        logger.info("Testing list commands")
        
        try:
            # Test list examples
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder", "list", "examples"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                stage_result.tests_passed += 1
                logger.info("List examples test passed")
            else:
                stage_result.warnings.append(f"List examples failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("List command timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"List command test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_build_command_dry_run(self, stage_result: TestStageResult) -> None:
        """Test build command in dry run mode."""
        logger.info("Testing build command (dry run)")
        
        try:
            # Create temporary spec file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("""# Test Project
                
Simple test project for CLI validation.

## Requirements
- Basic CLI tool
- Simple functionality
""")
                spec_file = f.name
            
            # Test dry run
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder", 
                "build", spec_file, "--dry-run"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                stage_result.tests_passed += 1
                logger.info("Build dry run test passed")
            else:
                stage_result.warnings.append(f"Build dry run failed: {result.stderr}")
            
            # Cleanup
            Path(spec_file).unlink(missing_ok=True)
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Build command timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Build command test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_error_handling(self, stage_result: TestStageResult) -> None:
        """Test CLI error handling."""
        logger.info("Testing error handling")
        
        try:
            # Test invalid command
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder", "invalid-command"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0 and "invalid" in result.stderr.lower():
                stage_result.tests_passed += 1
                logger.info("Invalid command error handling test passed")
            else:
                stage_result.warnings.append("Invalid command should return error")
            
            # Test missing required argument
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder", "build"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                stage_result.tests_passed += 1
                logger.info("Missing argument error handling test passed")
            else:
                stage_result.warnings.append("Missing argument should return error")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Error handling test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Error handling test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_output_formats(self, stage_result: TestStageResult) -> None:
        """Test different output formats."""
        logger.info("Testing output formats")
        
        try:
            # Test JSON output
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder", 
                "list", "examples", "--format", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                try:
                    json.loads(result.stdout)
                    stage_result.tests_passed += 1
                    logger.info("JSON output format test passed")
                except json.JSONDecodeError:
                    stage_result.warnings.append("JSON output format invalid")
            else:
                stage_result.warnings.append(f"JSON format failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Output format test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Output format test failed: {e}")
            stage_result.tests_failed += 1