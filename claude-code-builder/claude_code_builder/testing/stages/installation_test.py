"""Installation testing stage for Claude Code Builder package validation."""

import logging
import subprocess
import sys
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import venv
import importlib.util

from ..framework import TestStageResult, TestStage, TestStatus
from ...models.testing import TestResult

logger = logging.getLogger(__name__)


class InstallationTestStage:
    """Test stage for package installation validation."""
    
    def __init__(self, framework, context):
        """Initialize installation test stage."""
        self.framework = framework
        self.context = context
        self.test_results = []
        self.temp_dirs = []
    
    async def execute(self) -> TestStageResult:
        """Execute installation tests."""
        logger.info("Starting installation test stage")
        
        stage_result = TestStageResult(
            stage=TestStage.INSTALLATION,
            status=TestStatus.RUNNING,
            start_time=datetime.now(),
            duration_seconds=0.0
        )
        
        try:
            # Test 1: Package structure validation
            await self._test_package_structure(stage_result)
            
            # Test 2: Dependencies validation
            await self._test_dependencies(stage_result)
            
            # Test 3: Virtual environment installation
            await self._test_venv_installation(stage_result)
            
            # Test 4: Import validation
            await self._test_import_validation(stage_result)
            
            # Test 5: CLI installation
            await self._test_cli_installation(stage_result)
            
            # Test 6: Entry points validation
            await self._test_entry_points(stage_result)
            
            # Test 7: Uninstallation
            await self._test_uninstallation(stage_result)
            
        except Exception as e:
            stage_result.errors.append(f"Installation test stage failed: {e}")
            stage_result.tests_failed += 1
            logger.error(f"Installation test stage error: {e}")
        
        finally:
            # Cleanup temporary directories
            await self._cleanup()
        
        return stage_result
    
    async def _test_package_structure(self, stage_result: TestStageResult) -> None:
        """Test package structure and required files."""
        logger.info("Testing package structure")
        
        try:
            # Check for required package files
            package_root = Path(__file__).parent.parent.parent
            required_files = [
                "__init__.py",
                "main.py",
                "config/settings.py",
                "models/__init__.py",
                "execution/__init__.py",
                "testing/__init__.py"
            ]
            
            missing_files = []
            for file_path in required_files:
                full_path = package_root / file_path
                if not full_path.exists():
                    missing_files.append(file_path)
            
            if missing_files:
                stage_result.errors.append(f"Missing required files: {', '.join(missing_files)}")
                stage_result.tests_failed += 1
            else:
                stage_result.tests_passed += 1
                logger.info("Package structure validation passed")
            
            # Check pyproject.toml or setup.py
            pyproject_path = package_root.parent / "pyproject.toml"
            setup_path = package_root.parent / "setup.py"
            
            if not pyproject_path.exists() and not setup_path.exists():
                stage_result.errors.append("Missing pyproject.toml or setup.py")
                stage_result.tests_failed += 1
            else:
                stage_result.tests_passed += 1
                logger.info("Package configuration file found")
        
        except Exception as e:
            stage_result.errors.append(f"Package structure test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_dependencies(self, stage_result: TestStageResult) -> None:
        """Test package dependencies."""
        logger.info("Testing dependencies")
        
        try:
            # Check core dependencies
            core_dependencies = [
                "rich",
                "typer", 
                "pydantic",
                "requests",
                "asyncio"
            ]
            
            missing_deps = []
            for dep in core_dependencies:
                try:
                    if dep == "asyncio":
                        import asyncio
                    else:
                        __import__(dep)
                    logger.debug(f"Dependency {dep} is available")
                except ImportError:
                    missing_deps.append(dep)
            
            if missing_deps:
                stage_result.warnings.append(f"Missing dependencies: {', '.join(missing_deps)}")
                stage_result.tests_failed += 1
            else:
                stage_result.tests_passed += 1
                logger.info("Core dependencies validation passed")
        
        except Exception as e:
            stage_result.errors.append(f"Dependencies test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_venv_installation(self, stage_result: TestStageResult) -> None:
        """Test installation in a virtual environment."""
        logger.info("Testing virtual environment installation")
        
        venv_dir = None
        try:
            # Create temporary virtual environment
            venv_dir = Path(tempfile.mkdtemp(prefix="ccb_test_venv_"))
            self.temp_dirs.append(venv_dir)
            
            # Create virtual environment
            venv.create(venv_dir, with_pip=True)
            
            # Get venv python path
            if sys.platform == "win32":
                venv_python = venv_dir / "Scripts" / "python.exe"
                venv_pip = venv_dir / "Scripts" / "pip.exe"
            else:
                venv_python = venv_dir / "bin" / "python"
                venv_pip = venv_dir / "bin" / "pip"
            
            # Upgrade pip
            result = subprocess.run([
                str(venv_pip), "install", "--upgrade", "pip"
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                stage_result.warnings.append(f"Pip upgrade failed: {result.stderr}")
            
            # Install package in editable mode
            package_root = Path(__file__).parent.parent.parent.parent
            result = subprocess.run([
                str(venv_pip), "install", "-e", str(package_root)
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                stage_result.errors.append(f"Package installation failed: {result.stderr}")
                stage_result.tests_failed += 1
            else:
                stage_result.tests_passed += 1
                logger.info("Virtual environment installation passed")
                
                # Test import in venv
                import_result = subprocess.run([
                    str(venv_python), "-c", "import claude_code_builder; print('Import successful')"
                ], capture_output=True, text=True, timeout=30)
                
                if import_result.returncode != 0:
                    stage_result.errors.append(f"Import test in venv failed: {import_result.stderr}")
                    stage_result.tests_failed += 1
                else:
                    stage_result.tests_passed += 1
                    logger.info("Import test in venv passed")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Virtual environment installation timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Virtual environment test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_import_validation(self, stage_result: TestStageResult) -> None:
        """Test package imports."""
        logger.info("Testing package imports")
        
        try:
            # Test core module imports
            import_tests = [
                "claude_code_builder",
                "claude_code_builder.models",
                "claude_code_builder.execution",
                "claude_code_builder.testing",
                "claude_code_builder.config"
            ]
            
            failed_imports = []
            for module_name in import_tests:
                try:
                    importlib.import_module(module_name)
                    logger.debug(f"Successfully imported {module_name}")
                except ImportError as e:
                    failed_imports.append(f"{module_name}: {e}")
            
            if failed_imports:
                stage_result.errors.extend(failed_imports)
                stage_result.tests_failed += len(failed_imports)
            else:
                stage_result.tests_passed += len(import_tests)
                logger.info("All import tests passed")
        
        except Exception as e:
            stage_result.errors.append(f"Import validation failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_cli_installation(self, stage_result: TestStageResult) -> None:
        """Test CLI installation and basic functionality."""
        logger.info("Testing CLI installation")
        
        try:
            # Test help command
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder", "--help"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                stage_result.errors.append(f"CLI help command failed: {result.stderr}")
                stage_result.tests_failed += 1
            else:
                stage_result.tests_passed += 1
                logger.info("CLI help command passed")
            
            # Test version command
            result = subprocess.run([
                sys.executable, "-m", "claude_code_builder", "--version"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                stage_result.warnings.append(f"CLI version command failed: {result.stderr}")
            else:
                stage_result.tests_passed += 1
                logger.info("CLI version command passed")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("CLI test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"CLI test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_entry_points(self, stage_result: TestStageResult) -> None:
        """Test package entry points."""
        logger.info("Testing entry points")
        
        try:
            # Check if entry points are properly configured
            try:
                import pkg_resources
                
                # Look for our package entry points
                for entry_point in pkg_resources.iter_entry_points('console_scripts'):
                    if 'claude-code-builder' in entry_point.name:
                        stage_result.tests_passed += 1
                        logger.info(f"Found entry point: {entry_point.name}")
                        break
                else:
                    stage_result.warnings.append("No console script entry points found")
            
            except ImportError:
                # Try alternative method using importlib.metadata
                try:
                    import importlib.metadata as metadata
                    
                    dist = metadata.distribution("claude-code-builder")
                    entry_points = dist.entry_points
                    
                    if entry_points:
                        stage_result.tests_passed += 1
                        logger.info("Entry points found using importlib.metadata")
                    else:
                        stage_result.warnings.append("No entry points found")
                
                except Exception:
                    stage_result.warnings.append("Could not verify entry points")
        
        except Exception as e:
            stage_result.errors.append(f"Entry points test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _test_uninstallation(self, stage_result: TestStageResult) -> None:
        """Test package uninstallation."""
        logger.info("Testing uninstallation")
        
        venv_dir = None
        try:
            # Create fresh virtual environment for uninstall test
            venv_dir = Path(tempfile.mkdtemp(prefix="ccb_test_uninstall_"))
            self.temp_dirs.append(venv_dir)
            
            venv.create(venv_dir, with_pip=True)
            
            if sys.platform == "win32":
                venv_pip = venv_dir / "Scripts" / "pip.exe"
                venv_python = venv_dir / "Scripts" / "python.exe"
            else:
                venv_pip = venv_dir / "bin" / "pip"
                venv_python = venv_dir / "bin" / "python"
            
            # Install package
            package_root = Path(__file__).parent.parent.parent.parent
            install_result = subprocess.run([
                str(venv_pip), "install", "-e", str(package_root)
            ], capture_output=True, text=True, timeout=180)
            
            if install_result.returncode != 0:
                stage_result.warnings.append("Could not install for uninstall test")
                return
            
            # Uninstall package
            uninstall_result = subprocess.run([
                str(venv_pip), "uninstall", "claude-code-builder", "-y"
            ], capture_output=True, text=True, timeout=60)
            
            if uninstall_result.returncode != 0:
                stage_result.errors.append(f"Uninstallation failed: {uninstall_result.stderr}")
                stage_result.tests_failed += 1
            else:
                # Verify package is no longer importable
                import_result = subprocess.run([
                    str(venv_python), "-c", "import claude_code_builder"
                ], capture_output=True, text=True, timeout=30)
                
                if import_result.returncode == 0:
                    stage_result.errors.append("Package still importable after uninstallation")
                    stage_result.tests_failed += 1
                else:
                    stage_result.tests_passed += 1
                    logger.info("Uninstallation test passed")
        
        except subprocess.TimeoutExpired:
            stage_result.errors.append("Uninstallation test timed out")
            stage_result.tests_failed += 1
        except Exception as e:
            stage_result.errors.append(f"Uninstallation test failed: {e}")
            stage_result.tests_failed += 1
    
    async def _cleanup(self) -> None:
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {temp_dir}: {e}")
        
        self.temp_dirs.clear()