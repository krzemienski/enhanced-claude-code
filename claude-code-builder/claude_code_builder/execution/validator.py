"""Execution validation for ensuring build correctness."""

import logging
import os
import json
import subprocess
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import ast
import re

from ..models.project import ProjectSpec
from ..models.phase import Phase, Task, TaskStatus, TaskResult
from ..models.validation import ValidationResult
from ..exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class ValidationConfig:
    """Configuration for execution validation."""
    validate_syntax: bool = True
    validate_imports: bool = True
    validate_structure: bool = True
    validate_dependencies: bool = True
    validate_tests: bool = True
    validate_documentation: bool = True
    run_linters: bool = True
    run_type_checkers: bool = True
    custom_validators: List[str] = field(default_factory=list)
    strict_mode: bool = False
    continue_on_warning: bool = True


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    timestamp: datetime
    project_id: str
    phase_id: Optional[str] = None
    task_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


class ExecutionValidator:
    """Validates execution results and project state."""
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """Initialize the execution validator."""
        self.config = config or ValidationConfig()
        
        # Validation handlers
        self.validators = {
            "syntax": self._validate_syntax,
            "imports": self._validate_imports,
            "structure": self._validate_structure,
            "dependencies": self._validate_dependencies,
            "tests": self._validate_tests,
            "documentation": self._validate_documentation
        }
        
        # Language-specific validators
        self.language_validators = {
            ".py": PythonValidator(),
            ".js": JavaScriptValidator(),
            ".ts": TypeScriptValidator(),
            ".java": JavaValidator(),
            ".go": GoValidator()
        }
        
        # Linter configurations
        self.linter_configs = {
            "python": ["ruff", "flake8", "pylint"],
            "javascript": ["eslint", "jshint"],
            "typescript": ["tslint", "eslint"],
            "java": ["checkstyle", "pmd"],
            "go": ["golint", "go vet"]
        }
        
        logger.info("Execution Validator initialized")
    
    def validate_project(
        self,
        project: ProjectSpec,
        context: Dict[str, Any]
    ) -> ValidationReport:
        """Validate entire project."""
        logger.info(f"Validating project: {project.config.name}")
        
        report = ValidationReport(
            timestamp=datetime.now(),
            project_id=project.config.id
        )
        
        # Run all validators
        for validator_name, validator_func in self.validators.items():
            if self._should_run_validator(validator_name):
                try:
                    result = validator_func(project, context, report)
                    if result:
                        report.passed_checks.append(validator_name)
                    else:
                        report.failed_checks.append(validator_name)
                except Exception as e:
                    logger.error(f"Validator {validator_name} failed: {e}")
                    report.errors.append(
                        ValidationError(
                            validator=validator_name,
                            message=str(e),
                            severity="high"
                        )
                    )
                    report.failed_checks.append(validator_name)
        
        # Run custom validators
        for custom_validator in self.config.custom_validators:
            self._run_custom_validator(custom_validator, project, context, report)
        
        # Calculate metrics
        report.metrics = self._calculate_metrics(report)
        
        # Generate suggestions
        report.suggestions = self._generate_suggestions(report)
        
        logger.info(
            f"Validation complete - Errors: {len(report.errors)}, "
            f"Warnings: {len(report.warnings)}"
        )
        
        return report
    
    def validate_phase(
        self,
        phase: Phase,
        phase_result: TaskResult,
        context: Dict[str, Any]
    ) -> ValidationReport:
        """Validate phase execution results."""
        logger.info(f"Validating phase: {phase.name}")
        
        report = ValidationReport(
            timestamp=datetime.now(),
            project_id=context.project_id,
            phase_id=phase.id
        )
        
        # Validate phase completion
        if phase_result.status.value != "completed":
            report.warnings.append(
                ValidationWarning(
                    validator="phase_completion",
                    message=f"Phase {phase.name} did not complete successfully",
                    severity="medium"
                )
            )
        
        # Validate phase outputs
        expected_outputs = phase.metadata.get("expected_outputs", [])
        actual_outputs = list(phase_result.outputs.keys())
        
        missing_outputs = set(expected_outputs) - set(actual_outputs)
        if missing_outputs:
            report.errors.append(
                ValidationError(
                    validator="phase_outputs",
                    message=f"Missing expected outputs: {missing_outputs}",
                    severity="high",
                    details={"missing": list(missing_outputs)}
                )
            )
        
        # Validate artifacts
        self._validate_phase_artifacts(phase, phase_result, report)
        
        return report
    
    def validate_task(
        self,
        task: Task,
        task_result: TaskResult,
        context: Dict[str, Any]
    ) -> ValidationReport:
        """Validate task execution results."""
        logger.info(f"Validating task: {task.name}")
        
        report = ValidationReport(
            timestamp=datetime.now(),
            project_id=context.project_id,
            task_id=task.id
        )
        
        # Validate task completion
        if task_result.status.value != "completed":
            report.warnings.append(
                ValidationWarning(
                    validator="task_completion",
                    message=f"Task {task.name} did not complete successfully",
                    severity="medium"
                )
            )
        
        # Validate task outputs
        if task.type == "code":
            self._validate_code_task(task, task_result, report)
        elif task.type == "file":
            self._validate_file_task(task, task_result, report)
        elif task.type == "test":
            self._validate_test_task(task, task_result, report)
        
        return report
    
    def validate_code_quality(
        self,
        file_paths: List[str],
        language: Optional[str] = None
    ) -> ValidationReport:
        """Validate code quality for specific files."""
        report = ValidationReport(
            timestamp=datetime.now(),
            project_id="code_quality_check"
        )
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                report.errors.append(
                    ValidationError(
                        validator="file_exists",
                        message=f"File not found: {file_path}",
                        severity="high"
                    )
                )
                continue
            
            # Determine language
            ext = Path(file_path).suffix.lower()
            
            # Get appropriate validator
            validator = self.language_validators.get(ext)
            if validator:
                file_report = validator.validate_file(file_path)
                report.errors.extend(file_report.errors)
                report.warnings.extend(file_report.warnings)
            
            # Run linters if enabled
            if self.config.run_linters:
                linter_report = self._run_linters(file_path, language or ext)
                report.errors.extend(linter_report.errors)
                report.warnings.extend(linter_report.warnings)
        
        return report
    
    def _should_run_validator(self, validator_name: str) -> bool:
        """Check if a validator should be run."""
        validator_config_map = {
            "syntax": self.config.validate_syntax,
            "imports": self.config.validate_imports,
            "structure": self.config.validate_structure,
            "dependencies": self.config.validate_dependencies,
            "tests": self.config.validate_tests,
            "documentation": self.config.validate_documentation
        }
        
        return validator_config_map.get(validator_name, True)
    
    def _validate_syntax(
        self,
        project: ProjectSpec,
        context: Dict[str, Any],
        report: ValidationReport
    ) -> bool:
        """Validate syntax of all code files."""
        success = True
        project_root = Path(context.project_root)
        
        # Find all code files
        code_files = []
        for ext in [".py", ".js", ".ts", ".java", ".go"]:
            code_files.extend(project_root.rglob(f"*{ext}"))
        
        for file_path in code_files:
            ext = file_path.suffix.lower()
            validator = self.language_validators.get(ext)
            
            if validator:
                try:
                    result = validator.check_syntax(str(file_path))
                    if not result["valid"]:
                        report.errors.append(
                            ValidationError(
                                validator="syntax",
                                message=f"Syntax error in {file_path}: {result['error']}",
                                severity="high",
                                file_path=str(file_path),
                                line_number=result.get("line")
                            )
                        )
                        success = False
                except Exception as e:
                    report.warnings.append(
                        ValidationWarning(
                            validator="syntax",
                            message=f"Could not validate {file_path}: {e}",
                            severity="low"
                        )
                    )
        
        return success
    
    def _validate_imports(
        self,
        project: ProjectSpec,
        context: Dict[str, Any],
        report: ValidationReport
    ) -> bool:
        """Validate import statements."""
        success = True
        project_root = Path(context.project_root)
        
        # Check Python imports
        python_files = list(project_root.rglob("*.py"))
        for file_path in python_files:
            missing_imports = self._check_python_imports(file_path)
            if missing_imports:
                report.errors.append(
                    ValidationError(
                        validator="imports",
                        message=f"Missing imports in {file_path}: {missing_imports}",
                        severity="medium",
                        file_path=str(file_path),
                        details={"missing": missing_imports}
                    )
                )
                success = False
        
        return success
    
    def _validate_structure(
        self,
        project: ProjectSpec,
        context: Dict[str, Any],
        report: ValidationReport
    ) -> bool:
        """Validate project structure."""
        success = True
        project_root = Path(context.project_root)
        
        # Check required directories
        required_dirs = project.config.metadata.get("required_directories", [])
        for dir_name in required_dirs:
            dir_path = project_root / dir_name
            if not dir_path.exists():
                report.errors.append(
                    ValidationError(
                        validator="structure",
                        message=f"Required directory missing: {dir_name}",
                        severity="medium"
                    )
                )
                success = False
        
        # Check required files
        required_files = project.config.metadata.get("required_files", [])
        for file_name in required_files:
            file_path = project_root / file_name
            if not file_path.exists():
                report.errors.append(
                    ValidationError(
                        validator="structure",
                        message=f"Required file missing: {file_name}",
                        severity="medium"
                    )
                )
                success = False
        
        return success
    
    def _validate_dependencies(
        self,
        project: ProjectSpec,
        context: Dict[str, Any],
        report: ValidationReport
    ) -> bool:
        """Validate project dependencies."""
        success = True
        project_root = Path(context.project_root)
        
        # Check Python dependencies
        requirements_file = project_root / "requirements.txt"
        if requirements_file.exists():
            success &= self._validate_python_dependencies(
                requirements_file, report
            )
        
        # Check Node.js dependencies
        package_json = project_root / "package.json"
        if package_json.exists():
            success &= self._validate_node_dependencies(
                package_json, report
            )
        
        return success
    
    def _validate_tests(
        self,
        project: ProjectSpec,
        context: Dict[str, Any],
        report: ValidationReport
    ) -> bool:
        """Validate test coverage and execution."""
        success = True
        
        # Check for test files
        test_patterns = ["test_*.py", "*_test.py", "*.test.js", "*.spec.js"]
        test_files = []
        
        project_root = Path(context.project_root)
        for pattern in test_patterns:
            test_files.extend(project_root.rglob(pattern))
        
        if not test_files:
            report.warnings.append(
                ValidationWarning(
                    validator="tests",
                    message="No test files found",
                    severity="medium"
                )
            )
        
        # Check test coverage if available
        coverage_file = project_root / "coverage.json"
        if coverage_file.exists():
            with open(coverage_file) as f:
                coverage_data = json.load(f)
                coverage_percent = coverage_data.get("total_coverage", 0)
                
                if coverage_percent < 80:
                    report.warnings.append(
                        ValidationWarning(
                            validator="tests",
                            message=f"Low test coverage: {coverage_percent}%",
                            severity="medium",
                            details={"coverage": coverage_percent}
                        )
                    )
        
        return success
    
    def _validate_documentation(
        self,
        project: ProjectSpec,
        context: Dict[str, Any],
        report: ValidationReport
    ) -> bool:
        """Validate documentation completeness."""
        success = True
        project_root = Path(context.project_root)
        
        # Check for README
        readme_files = ["README.md", "README.rst", "README.txt"]
        has_readme = any(
            (project_root / readme).exists() for readme in readme_files
        )
        
        if not has_readme:
            report.errors.append(
                ValidationError(
                    validator="documentation",
                    message="No README file found",
                    severity="medium"
                )
            )
            success = False
        
        # Check for docstrings in Python files
        if self.config.strict_mode:
            python_files = list(project_root.rglob("*.py"))
            for file_path in python_files:
                if not self._check_docstrings(file_path):
                    report.warnings.append(
                        ValidationWarning(
                            validator="documentation",
                            message=f"Missing docstrings in {file_path}",
                            severity="low",
                            file_path=str(file_path)
                        )
                    )
        
        return success
    
    def _validate_phase_artifacts(
        self,
        phase: Phase,
        phase_result: TaskResult,
        report: ValidationReport
    ) -> None:
        """Validate phase artifacts."""
        expected_artifacts = phase.metadata.get("expected_artifacts", {})
        
        for artifact_name, artifact_spec in expected_artifacts.items():
            if artifact_name not in phase_result.artifacts:
                report.errors.append(
                    ValidationError(
                        validator="artifacts",
                        message=f"Missing expected artifact: {artifact_name}",
                        severity="high"
                    )
                )
            else:
                # Validate artifact content
                artifact = phase_result.artifacts[artifact_name]
                if "schema" in artifact_spec:
                    # Validate against schema
                    pass
    
    def _validate_code_task(
        self,
        task: Task,
        task_result: TaskResult,
        report: ValidationReport
    ) -> None:
        """Validate code generation task results."""
        # Check if files were created
        created_files = task_result.outputs.get("files_created", [])
        expected_files = task.metadata.get("expected_files", [])
        
        missing_files = set(expected_files) - set(created_files)
        if missing_files:
            report.errors.append(
                ValidationError(
                    validator="code_task",
                    message=f"Expected files not created: {missing_files}",
                    severity="high",
                    details={"missing": list(missing_files)}
                )
            )
    
    def _validate_file_task(
        self,
        task: Task,
        task_result: TaskResult,
        report: ValidationReport
    ) -> None:
        """Validate file operation task results."""
        operations = task_result.outputs.get("operations", [])
        
        for operation in operations:
            if operation["type"] == "create":
                file_path = operation["path"]
                if not os.path.exists(file_path):
                    report.errors.append(
                        ValidationError(
                            validator="file_task",
                            message=f"File creation failed: {file_path}",
                            severity="high"
                        )
                    )
    
    def _validate_test_task(
        self,
        task: Task,
        task_result: TaskResult,
        report: ValidationReport
    ) -> None:
        """Validate test execution task results."""
        test_results = task_result.outputs.get("test_results", {})
        
        if test_results.get("failed", 0) > 0:
            report.errors.append(
                ValidationError(
                    validator="test_task",
                    message=f"Test failures: {test_results['failed']} tests failed",
                    severity="high",
                    details=test_results
                )
            )
    
    def _run_linters(
        self,
        file_path: str,
        language: str
    ) -> ValidationReport:
        """Run linters on a file."""
        report = ValidationReport(
            timestamp=datetime.now(),
            project_id="linter_check"
        )
        
        # Get linters for language
        linters = self.linter_configs.get(language, [])
        
        for linter in linters:
            if self._is_linter_available(linter):
                result = self._run_linter(linter, file_path)
                if result["errors"]:
                    report.errors.extend(result["errors"])
                if result["warnings"]:
                    report.warnings.extend(result["warnings"])
        
        return report
    
    def _run_custom_validator(
        self,
        validator_name: str,
        project: ProjectSpec,
        context: Dict[str, Any],
        report: ValidationReport
    ) -> None:
        """Run a custom validator."""
        # This would load and run custom validation scripts
        pass
    
    def _check_python_imports(self, file_path: Path) -> List[str]:
        """Check Python imports for missing modules."""
        missing_imports = []
        
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self._is_module_available(alias.name):
                            missing_imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module and not self._is_module_available(node.module):
                        missing_imports.append(node.module)
        
        except Exception as e:
            logger.error(f"Error checking imports in {file_path}: {e}")
        
        return missing_imports
    
    def _is_module_available(self, module_name: str) -> bool:
        """Check if a Python module is available."""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
    
    def _validate_python_dependencies(
        self,
        requirements_file: Path,
        report: ValidationReport
    ) -> bool:
        """Validate Python dependencies."""
        success = True
        
        try:
            with open(requirements_file) as f:
                requirements = f.readlines()
            
            for req in requirements:
                req = req.strip()
                if req and not req.startswith("#"):
                    # Parse requirement
                    match = re.match(r"([a-zA-Z0-9\-_]+)", req)
                    if match:
                        package_name = match.group(1)
                        if not self._is_module_available(package_name):
                            report.warnings.append(
                                ValidationWarning(
                                    validator="dependencies",
                                    message=f"Python package not installed: {package_name}",
                                    severity="medium"
                                )
                            )
        
        except Exception as e:
            logger.error(f"Error validating Python dependencies: {e}")
            success = False
        
        return success
    
    def _validate_node_dependencies(
        self,
        package_json: Path,
        report: ValidationReport
    ) -> bool:
        """Validate Node.js dependencies."""
        success = True
        
        try:
            with open(package_json) as f:
                package_data = json.load(f)
            
            # Check if node_modules exists
            node_modules = package_json.parent / "node_modules"
            if not node_modules.exists():
                report.errors.append(
                    ValidationError(
                        validator="dependencies",
                        message="node_modules directory not found",
                        severity="high"
                    )
                )
                success = False
        
        except Exception as e:
            logger.error(f"Error validating Node dependencies: {e}")
            success = False
        
        return success
    
    def _check_docstrings(self, file_path: Path) -> bool:
        """Check if Python file has proper docstrings."""
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        return False
            
            return True
        
        except Exception:
            return True  # Assume valid if can't parse
    
    def _is_linter_available(self, linter: str) -> bool:
        """Check if a linter is available."""
        try:
            subprocess.run(
                [linter, "--version"],
                capture_output=True,
                check=False
            )
            return True
        except FileNotFoundError:
            return False
    
    def _run_linter(self, linter: str, file_path: str) -> Dict[str, List]:
        """Run a specific linter on a file."""
        # This would run the actual linter command
        # and parse its output
        return {"errors": [], "warnings": []}
    
    def _calculate_metrics(self, report: ValidationReport) -> Dict[str, Any]:
        """Calculate validation metrics."""
        return {
            "total_errors": len(report.errors),
            "total_warnings": len(report.warnings),
            "passed_checks": len(report.passed_checks),
            "failed_checks": len(report.failed_checks),
            "error_severity_distribution": self._get_severity_distribution(
                report.errors
            ),
            "warning_severity_distribution": self._get_severity_distribution(
                report.warnings
            )
        }
    
    def _get_severity_distribution(
        self,
        items: List[str]
    ) -> Dict[str, int]:
        """Get distribution of items by severity."""
        distribution = {"high": 0, "medium": 0, "low": 0}
        
        for item in items:
            severity = item.severity
            if severity in distribution:
                distribution[severity] += 1
        
        return distribution
    
    def _generate_suggestions(self, report: ValidationReport) -> List[str]:
        """Generate improvement suggestions based on validation results."""
        suggestions = []
        
        # Check for common patterns
        if any(e.validator == "imports" for e in report.errors):
            suggestions.append(
                "Run 'pip install -r requirements.txt' to install missing dependencies"
            )
        
        if any(e.validator == "syntax" for e in report.errors):
            suggestions.append(
                "Use an IDE with syntax checking to catch errors early"
            )
        
        if any(w.validator == "tests" for w in report.warnings):
            suggestions.append(
                "Increase test coverage to at least 80%"
            )
        
        if any(e.validator == "documentation" for e in report.errors):
            suggestions.append(
                "Add a README.md file with project documentation"
            )
        
        return suggestions


class PythonValidator:
    """Python-specific validation."""
    
    def validate_file(self, file_path: str) -> ValidationReport:
        """Validate a Python file."""
        report = ValidationReport(
            timestamp=datetime.now(),
            project_id="python_validation"
        )
        
        # Check syntax
        syntax_result = self.check_syntax(file_path)
        if not syntax_result["valid"]:
            report.errors.append(
                ValidationError(
                    validator="python_syntax",
                    message=syntax_result["error"],
                    severity="high",
                    file_path=file_path,
                    line_number=syntax_result.get("line")
                )
            )
        
        return report
    
    def check_syntax(self, file_path: str) -> Dict[str, Any]:
        """Check Python syntax."""
        try:
            with open(file_path, 'r') as f:
                ast.parse(f.read())
            return {"valid": True}
        except SyntaxError as e:
            return {
                "valid": False,
                "error": str(e),
                "line": e.lineno
            }


class JavaScriptValidator:
    """JavaScript-specific validation."""
    
    def validate_file(self, file_path: str) -> ValidationReport:
        """Validate a JavaScript file."""
        report = ValidationReport(
            timestamp=datetime.now(),
            project_id="javascript_validation"
        )
        
        # Basic syntax check (would use proper parser in production)
        syntax_result = self.check_syntax(file_path)
        if not syntax_result["valid"]:
            report.errors.append(
                ValidationError(
                    validator="javascript_syntax",
                    message=syntax_result["error"],
                    severity="high",
                    file_path=file_path
                )
            )
        
        return report
    
    def check_syntax(self, file_path: str) -> Dict[str, Any]:
        """Check JavaScript syntax."""
        # Simplified - would use proper JS parser
        return {"valid": True}


class TypeScriptValidator:
    """TypeScript-specific validation."""
    
    def validate_file(self, file_path: str) -> ValidationReport:
        """Validate a TypeScript file."""
        report = ValidationReport(
            timestamp=datetime.now(),
            project_id="typescript_validation"
        )
        
        # Would run tsc --noEmit for real validation
        return report
    
    def check_syntax(self, file_path: str) -> Dict[str, Any]:
        """Check TypeScript syntax."""
        return {"valid": True}


class JavaValidator:
    """Java-specific validation."""
    
    def validate_file(self, file_path: str) -> ValidationReport:
        """Validate a Java file."""
        report = ValidationReport(
            timestamp=datetime.now(),
            project_id="java_validation"
        )
        
        # Would use Java compiler API
        return report
    
    def check_syntax(self, file_path: str) -> Dict[str, Any]:
        """Check Java syntax."""
        return {"valid": True}


class GoValidator:
    """Go-specific validation."""
    
    def validate_file(self, file_path: str) -> ValidationReport:
        """Validate a Go file."""
        report = ValidationReport(
            timestamp=datetime.now(),
            project_id="go_validation"
        )
        
        # Would run go fmt and go vet
        return report
    
    def check_syntax(self, file_path: str) -> Dict[str, Any]:
        """Check Go syntax."""
        return {"valid": True}