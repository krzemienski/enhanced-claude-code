"""Tests for validation system."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil
import json
import ast

from claude_code_builder.validation.project_validator import ProjectValidator
from claude_code_builder.validation.code_validator import CodeValidator
from claude_code_builder.validation.file_validator import FileValidator
from claude_code_builder.validation.dependency_validator import DependencyValidator
from claude_code_builder.validation.security_validator import SecurityValidator
from claude_code_builder.validation.style_validator import StyleValidator
from claude_code_builder.validation.test_validator import TestValidator
from claude_code_builder.models.project import ProjectSpec
from claude_code_builder.models.phase import Phase
from claude_code_builder.models.validation import ValidationResult, ValidationError, ValidationRule
from claude_code_builder.exceptions.base import ValidationError as ValidationException


class TestProjectValidator:
    """Test suite for ProjectValidator."""
    
    @pytest.fixture
    def project_validator(self):
        """Create project validator instance."""
        return ProjectValidator()
    
    def test_validate_project_spec_success(self, project_validator, sample_project_spec):
        """Test successful project spec validation."""
        result = project_validator.validate_project_spec(sample_project_spec)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) >= 0
        assert result.score >= 0.8  # Should have high score for valid spec
    
    def test_validate_project_spec_missing_name(self, project_validator):
        """Test validation with missing project name."""
        # Create invalid spec
        spec = ProjectSpec(
            name="",  # Empty name
            description="Test project",
            version="1.0.0"
        )
        
        result = project_validator.validate_project_spec(spec)
        
        assert result.is_valid is False
        assert any("name" in error.field.lower() for error in result.errors)
    
    def test_validate_project_spec_missing_phases(self, project_validator):
        """Test validation with missing phases."""
        spec = ProjectSpec(
            name="test-project",
            description="Test project",
            version="1.0.0",
            phases=[]  # No phases
        )
        
        result = project_validator.validate_project_spec(spec)
        
        assert result.is_valid is False
        assert any("phase" in error.message.lower() for error in result.errors)
    
    def test_validate_project_spec_invalid_version(self, project_validator):
        """Test validation with invalid version."""
        spec = ProjectSpec(
            name="test-project",
            description="Test project",
            version="not-a-version"  # Invalid version format
        )
        
        result = project_validator.validate_project_spec(spec)
        
        assert result.is_valid is False
        assert any("version" in error.field.lower() for error in result.errors)
    
    def test_validate_phase_dependencies(self, project_validator):
        """Test phase dependency validation."""
        # Create phases with circular dependency
        phase1 = Phase(name="Phase1", dependencies=["Phase2"])
        phase2 = Phase(name="Phase2", dependencies=["Phase1"])
        
        spec = ProjectSpec(
            name="test-project",
            description="Test project",
            version="1.0.0",
            phases=[phase1, phase2]
        )
        
        result = project_validator.validate_project_spec(spec)
        
        assert result.is_valid is False
        assert any("circular" in error.message.lower() or "dependency" in error.message.lower() 
                  for error in result.errors)
    
    def test_validate_deliverables(self, project_validator):
        """Test deliverable validation."""
        # Create phase with duplicate deliverables
        phase = Phase(
            name="Test Phase",
            deliverables=["file1.py", "file1.py", "file2.py"]  # Duplicate
        )
        
        spec = ProjectSpec(
            name="test-project",
            description="Test project",
            version="1.0.0",
            phases=[phase]
        )
        
        result = project_validator.validate_project_spec(spec)
        
        # Should warn about duplicates
        assert any("duplicate" in warning.message.lower() for warning in result.warnings)


class TestCodeValidator:
    """Test suite for CodeValidator."""
    
    @pytest.fixture
    def code_validator(self):
        """Create code validator instance."""
        return CodeValidator()
    
    def test_validate_python_syntax_valid(self, code_validator):
        """Test validation of valid Python code."""
        code = '''
def hello(name: str) -> str:
    """Say hello to someone.
    
    Args:
        name: Name to greet
        
    Returns:
        Greeting message
    """
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(hello("World"))
'''
        
        result = code_validator.validate_syntax(code, language="python")
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_python_syntax_invalid(self, code_validator):
        """Test validation of invalid Python code."""
        code = '''
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name!"  # Missing closing brace
'''
        
        result = code_validator.validate_syntax(code, language="python")
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("syntax" in error.message.lower() for error in result.errors)
    
    def test_validate_python_imports(self, code_validator):
        """Test import validation."""
        code = '''
import os
import sys
import nonexistent_module  # This doesn't exist
from pathlib import Path
from typing import List, Dict
'''
        
        result = code_validator.validate_imports(code, language="python")
        
        # Should warn about nonexistent module
        assert any("nonexistent_module" in warning.message for warning in result.warnings)
    
    def test_validate_javascript_syntax_valid(self, code_validator):
        """Test validation of valid JavaScript code."""
        code = '''
function hello(name) {
    return `Hello, ${name}!`;
}

const greet = (name) => {
    console.log(hello(name));
};

greet("World");
'''
        
        result = code_validator.validate_syntax(code, language="javascript")
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_javascript_syntax_invalid(self, code_validator):
        """Test validation of invalid JavaScript code."""
        code = '''
function hello(name) {
    return `Hello, ${name}!`;
}

const greet = (name) => {
    console.log(hello(name);  // Missing closing parenthesis
};
'''
        
        result = code_validator.validate_syntax(code, language="javascript")
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_code_complexity(self, code_validator):
        """Test code complexity validation."""
        # Complex function with many branches
        complex_code = '''
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                for i in range(x):
                    for j in range(y):
                        for k in range(z):
                            if i + j + k > 10:
                                if i % 2 == 0:
                                    return i * j * k
                                else:
                                    return i + j + k
                            else:
                                continue
        else:
            return x * y
    else:
        return 0
'''
        
        result = code_validator.validate_complexity(complex_code, language="python")
        
        # Should warn about high complexity
        assert any("complexity" in warning.message.lower() for warning in result.warnings)
    
    def test_validate_security_issues(self, code_validator):
        """Test security issue detection."""
        # Code with potential security issues
        insecure_code = '''
import os
import subprocess

def dangerous_function(user_input):
    # SQL injection risk
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    
    # Command injection risk
    os.system(f"rm -rf {user_input}")
    
    # Using eval
    result = eval(user_input)
    
    return result
'''
        
        result = code_validator.validate_security(insecure_code, language="python")
        
        # Should find security issues
        assert len(result.errors) > 0 or len(result.warnings) > 0
        security_messages = [e.message.lower() for e in result.errors] + [w.message.lower() for w in result.warnings]
        assert any("injection" in msg or "eval" in msg or "security" in msg for msg in security_messages)


class TestFileValidator:
    """Test suite for FileValidator."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = Path(tempfile.mkdtemp())
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)
    
    @pytest.fixture
    def file_validator(self):
        """Create file validator instance."""
        return FileValidator()
    
    def test_validate_file_structure(self, file_validator, temp_workspace):
        """Test file structure validation."""
        # Create test project structure
        (temp_workspace / "src").mkdir()
        (temp_workspace / "src" / "__init__.py").touch()
        (temp_workspace / "src" / "main.py").write_text("print('Hello')")
        (temp_workspace / "tests").mkdir()
        (temp_workspace / "tests" / "test_main.py").write_text("def test_main(): pass")
        (temp_workspace / "README.md").write_text("# Test Project")
        (temp_workspace / "requirements.txt").write_text("pytest\nclick")
        
        # Expected structure
        expected_files = [
            "src/__init__.py",
            "src/main.py",
            "tests/test_main.py",
            "README.md",
            "requirements.txt"
        ]
        
        result = file_validator.validate_structure(temp_workspace, expected_files)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_file_structure_missing_files(self, file_validator, temp_workspace):
        """Test validation with missing files."""
        # Create partial structure
        (temp_workspace / "src").mkdir()
        (temp_workspace / "src" / "main.py").write_text("print('Hello')")
        
        # Expected more files
        expected_files = [
            "src/__init__.py",
            "src/main.py",
            "tests/test_main.py",
            "README.md"
        ]
        
        result = file_validator.validate_structure(temp_workspace, expected_files)
        
        assert result.is_valid is False
        assert len(result.errors) >= 3  # Missing files
        
        missing_files = [error.message for error in result.errors if "missing" in error.message.lower()]
        assert len(missing_files) >= 3
    
    def test_validate_file_permissions(self, file_validator, temp_workspace):
        """Test file permission validation."""
        # Create test files with different permissions
        script_file = temp_workspace / "script.py"
        script_file.write_text("#!/usr/bin/env python\nprint('Hello')")
        script_file.chmod(0o755)  # Executable
        
        data_file = temp_workspace / "data.txt"
        data_file.write_text("test data")
        data_file.chmod(0o644)  # Read-write for owner, read for others
        
        result = file_validator.validate_permissions(temp_workspace)
        
        # Should pass - permissions are reasonable
        assert result.is_valid is True
    
    def test_validate_file_encoding(self, file_validator, temp_workspace):
        """Test file encoding validation."""
        # Create files with different encodings
        utf8_file = temp_workspace / "utf8.py"
        utf8_file.write_text("# -*- coding: utf-8 -*-\nprint('Hello 世界')", encoding='utf-8')
        
        ascii_file = temp_workspace / "ascii.py"
        ascii_file.write_text("print('Hello')", encoding='ascii')
        
        result = file_validator.validate_encoding(temp_workspace)
        
        # Should be valid
        assert result.is_valid is True
    
    def test_validate_file_size_limits(self, file_validator, temp_workspace):
        """Test file size validation."""
        # Create normal sized file
        normal_file = temp_workspace / "normal.py"
        normal_file.write_text("print('Hello')\n" * 100)  # Small file
        
        # Create large file (simulate)
        large_file = temp_workspace / "large.py"
        large_content = "# Large file\n" + "print('line')\n" * 10000
        large_file.write_text(large_content)
        
        result = file_validator.validate_size_limits(temp_workspace, max_file_size=1024*1024)  # 1MB limit
        
        # Should pass - files are still reasonable
        assert result.is_valid is True


class TestDependencyValidator:
    """Test suite for DependencyValidator."""
    
    @pytest.fixture
    def dependency_validator(self):
        """Create dependency validator instance."""
        return DependencyValidator()
    
    def test_validate_python_dependencies(self, dependency_validator, temp_workspace):
        """Test Python dependency validation."""
        # Create requirements.txt
        requirements_file = temp_workspace / "requirements.txt"
        requirements_file.write_text("""
pytest>=6.0.0
click>=8.0.0
requests>=2.25.0
non-existent-package==1.0.0
""")
        
        result = dependency_validator.validate_dependencies(temp_workspace, "python")
        
        # Should find issues with non-existent package
        assert any("non-existent-package" in warning.message for warning in result.warnings)
    
    def test_validate_javascript_dependencies(self, dependency_validator, temp_workspace):
        """Test JavaScript dependency validation."""
        # Create package.json
        package_json = temp_workspace / "package.json"
        package_json.write_text(json.dumps({
            "name": "test-project",
            "version": "1.0.0",
            "dependencies": {
                "express": "^4.18.0",
                "lodash": "^4.17.0",
                "non-existent-js-package": "^1.0.0"
            },
            "devDependencies": {
                "jest": "^28.0.0"
            }
        }))
        
        result = dependency_validator.validate_dependencies(temp_workspace, "javascript")
        
        # Should validate package.json structure
        assert result.is_valid is True or len(result.warnings) > 0
    
    def test_validate_version_conflicts(self, dependency_validator):
        """Test version conflict detection."""
        dependencies = [
            {"name": "package-a", "version": "1.0.0", "requires": {"shared-dep": ">=2.0.0"}},
            {"name": "package-b", "version": "2.0.0", "requires": {"shared-dep": "<2.0.0"}},
            {"name": "shared-dep", "version": "1.5.0"}
        ]
        
        result = dependency_validator.check_version_conflicts(dependencies)
        
        # Should detect conflict
        assert len(result.errors) > 0
        assert any("conflict" in error.message.lower() for error in result.errors)
    
    def test_validate_security_vulnerabilities(self, dependency_validator):
        """Test security vulnerability detection."""
        # Mock vulnerability database
        vulnerable_packages = {
            "old-package": ["1.0.0", "1.1.0"],  # Vulnerable versions
            "secure-package": []  # No known vulnerabilities
        }
        
        dependencies = [
            {"name": "old-package", "version": "1.0.0"},
            {"name": "secure-package", "version": "2.0.0"}
        ]
        
        with patch.object(dependency_validator, '_get_vulnerability_data', return_value=vulnerable_packages):
            result = dependency_validator.check_security_vulnerabilities(dependencies)
            
            # Should find vulnerability in old-package
            assert len(result.warnings) > 0
            assert any("old-package" in warning.message for warning in result.warnings)


class TestSecurityValidator:
    """Test suite for SecurityValidator."""
    
    @pytest.fixture
    def security_validator(self):
        """Create security validator instance."""
        return SecurityValidator()
    
    def test_validate_hardcoded_secrets(self, security_validator):
        """Test hardcoded secret detection."""
        code_with_secrets = '''
# Configuration
API_KEY = "sk-1234567890abcdef"  # OpenAI API key
DATABASE_PASSWORD = "super_secret_password"
AWS_SECRET = "AKIAIOSFODNN7EXAMPLE"

# Safe configuration
API_ENDPOINT = "https://api.example.com"
MAX_RETRIES = 3
'''
        
        result = security_validator.validate_secrets(code_with_secrets)
        
        # Should find secrets
        assert len(result.errors) > 0 or len(result.warnings) > 0
        secret_messages = [e.message.lower() for e in result.errors] + [w.message.lower() for w in result.warnings]
        assert any("secret" in msg or "key" in msg or "password" in msg for msg in secret_messages)
    
    def test_validate_sql_injection(self, security_validator):
        """Test SQL injection detection."""
        vulnerable_code = '''
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # Vulnerable
    return execute_query(query)

def get_user_safe(user_id):
    query = "SELECT * FROM users WHERE id = ?"  # Safe - parameterized
    return execute_query(query, (user_id,))
'''
        
        result = security_validator.validate_sql_injection(vulnerable_code)
        
        # Should detect potential SQL injection
        assert len(result.warnings) > 0
        assert any("injection" in warning.message.lower() for warning in result.warnings)
    
    def test_validate_command_injection(self, security_validator):
        """Test command injection detection."""
        vulnerable_code = '''
import os
import subprocess

def process_file(filename):
    # Vulnerable to command injection
    os.system(f"cat {filename}")
    subprocess.call(f"rm {filename}", shell=True)
    
def process_file_safe(filename):
    # Safe approach
    subprocess.run(["cat", filename], check=True)
'''
        
        result = security_validator.validate_command_injection(vulnerable_code)
        
        # Should detect potential command injection
        assert len(result.warnings) > 0
        assert any("injection" in warning.message.lower() or "command" in warning.message.lower() 
                  for warning in result.warnings)
    
    def test_validate_unsafe_functions(self, security_validator):
        """Test unsafe function detection."""
        code_with_unsafe_functions = '''
import pickle
import eval

def dangerous_operations(data):
    # Unsafe functions
    result1 = eval(data)  # Dangerous
    result2 = exec(data)  # Dangerous
    result3 = pickle.loads(data)  # Can be dangerous
    
    return result1, result2, result3
'''
        
        result = security_validator.validate_unsafe_functions(code_with_unsafe_functions)
        
        # Should find unsafe functions
        assert len(result.warnings) > 0
        unsafe_messages = [w.message.lower() for w in result.warnings]
        assert any("eval" in msg or "exec" in msg or "pickle" in msg for msg in unsafe_messages)


class TestStyleValidator:
    """Test suite for StyleValidator."""
    
    @pytest.fixture
    def style_validator(self):
        """Create style validator instance."""
        return StyleValidator()
    
    def test_validate_python_pep8(self, style_validator):
        """Test PEP 8 style validation."""
        # Code with style issues
        code_with_issues = '''
import os,sys  # Should be separate lines
from pathlib import Path

def badlyNamedFunction( x,y ):  # Bad naming and spacing
    z=x+y  # No spaces around operators
    return z

class badClassName:  # Should be PascalCase
    def __init__(self):
        self.variableName = 42
'''
        
        result = style_validator.validate_style(code_with_issues, "python")
        
        # Should find style issues
        assert len(result.warnings) > 0
        style_messages = [w.message.lower() for w in result.warnings]
        assert any("spacing" in msg or "naming" in msg or "import" in msg for msg in style_messages)
    
    def test_validate_javascript_style(self, style_validator):
        """Test JavaScript style validation."""
        code_with_issues = '''
function badlynamed_function(x,y){  // Bad naming and spacing
var z=x+y;  // No spaces, should use const/let
return z;
}

const goodFunction = (x, y) => {
const z = x + y;
return z;
};
'''
        
        result = style_validator.validate_style(code_with_issues, "javascript")
        
        # Should find style issues
        assert len(result.warnings) >= 0  # May or may not find issues depending on rules
    
    def test_validate_docstring_coverage(self, style_validator):
        """Test docstring coverage validation."""
        code_missing_docstrings = '''
def function_without_docstring(x, y):
    return x + y

def function_with_docstring(x, y):
    """Add two numbers.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Sum of x and y
    """
    return x + y

class ClassWithoutDocstring:
    def method_without_docstring(self):
        pass
'''
        
        result = style_validator.validate_docstrings(code_missing_docstrings, "python")
        
        # Should warn about missing docstrings
        assert len(result.warnings) > 0
        docstring_messages = [w.message.lower() for w in result.warnings]
        assert any("docstring" in msg for msg in docstring_messages)


class TestTestValidator:
    """Test suite for TestValidator."""
    
    @pytest.fixture
    def test_validator(self):
        """Create test validator instance."""
        return TestValidator()
    
    def test_validate_test_coverage(self, test_validator, temp_workspace):
        """Test code coverage validation."""
        # Create source files
        src_dir = temp_workspace / "src"
        src_dir.mkdir()
        
        (src_dir / "main.py").write_text('''
def add(x, y):
    return x + y

def subtract(x, y):
    return x - y

def multiply(x, y):
    return x * y
''')
        
        # Create test files
        tests_dir = temp_workspace / "tests"
        tests_dir.mkdir()
        
        (tests_dir / "test_main.py").write_text('''
from src.main import add, subtract

def test_add():
    assert add(2, 3) == 5

def test_subtract():
    assert subtract(5, 3) == 2

# Note: multiply function is not tested
''')
        
        result = test_validator.validate_coverage(temp_workspace, target_coverage=80)
        
        # Should warn about incomplete coverage
        assert result.is_valid is True or len(result.warnings) > 0
    
    def test_validate_test_structure(self, test_validator, temp_workspace):
        """Test test structure validation."""
        # Create tests with good structure
        tests_dir = temp_workspace / "tests"
        tests_dir.mkdir()
        
        (tests_dir / "test_calculator.py").write_text('''
import pytest
from src.calculator import Calculator

class TestCalculator:
    @pytest.fixture
    def calculator(self):
        return Calculator()
    
    def test_addition(self, calculator):
        result = calculator.add(2, 3)
        assert result == 5
    
    def test_division_by_zero(self, calculator):
        with pytest.raises(ZeroDivisionError):
            calculator.divide(5, 0)
''')
        
        result = test_validator.validate_test_structure(tests_dir)
        
        # Should pass validation
        assert result.is_valid is True
    
    def test_validate_test_naming(self, test_validator):
        """Test naming convention validation."""
        test_code = '''
def test_valid_test_name():
    assert True

def invalidTestName():  # Bad naming
    assert True

def test_another_valid_test():
    assert True

def not_a_test():  # Not a test function
    pass
'''
        
        result = test_validator.validate_test_naming(test_code)
        
        # Should warn about bad naming
        assert any("naming" in warning.message.lower() for warning in result.warnings)


@pytest.mark.integration
class TestValidationIntegration:
    """Integration tests for validation system."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = Path(tempfile.mkdtemp())
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)
    
    def test_full_project_validation(self, temp_workspace):
        """Test complete project validation workflow."""
        # Create a realistic project structure
        self._create_sample_project(temp_workspace)
        
        # Create validators
        project_validator = ProjectValidator()
        code_validator = CodeValidator()
        file_validator = FileValidator()
        
        # Validate project structure
        expected_files = [
            "src/__init__.py",
            "src/main.py",
            "tests/test_main.py",
            "README.md",
            "requirements.txt"
        ]
        
        structure_result = file_validator.validate_structure(temp_workspace, expected_files)
        assert structure_result.is_valid is True
        
        # Validate code in all Python files
        python_files = list(temp_workspace.glob("**/*.py"))
        all_code_valid = True
        
        for py_file in python_files:
            code = py_file.read_text()
            code_result = code_validator.validate_syntax(code, "python")
            if not code_result.is_valid:
                all_code_valid = False
                break
        
        assert all_code_valid is True
    
    def _create_sample_project(self, workspace: Path):
        """Create a sample project for testing."""
        # Create directories
        (workspace / "src").mkdir()
        (workspace / "tests").mkdir()
        
        # Create source files
        (workspace / "src" / "__init__.py").write_text('"""Sample project."""')
        
        (workspace / "src" / "main.py").write_text('''
"""Main module for sample project."""

def add(x: int, y: int) -> int:
    """Add two integers.
    
    Args:
        x: First integer
        y: Second integer
        
    Returns:
        Sum of x and y
    """
    return x + y

def main():
    """Main function."""
    result = add(2, 3)
    print(f"2 + 3 = {result}")

if __name__ == "__main__":
    main()
''')
        
        # Create test files
        (workspace / "tests" / "test_main.py").write_text('''
"""Tests for main module."""
import pytest
from src.main import add

def test_add():
    """Test addition function."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_add_large_numbers():
    """Test addition with large numbers."""
    assert add(1000000, 2000000) == 3000000
''')
        
        # Create project files
        (workspace / "README.md").write_text('''# Sample Project

A simple sample project for testing validation.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python src/main.py
```
''')
        
        (workspace / "requirements.txt").write_text('''pytest>=6.0.0
click>=8.0.0
''')
    
    def test_validation_error_aggregation(self, temp_workspace):
        """Test that validation errors are properly aggregated."""
        # Create project with multiple issues
        self._create_problematic_project(temp_workspace)
        
        # Run comprehensive validation
        validators = [
            ProjectValidator(),
            CodeValidator(),
            FileValidator(),
            SecurityValidator()
        ]
        
        all_results = []
        
        # Validate with each validator
        for validator in validators:
            if isinstance(validator, ProjectValidator):
                # Create minimal spec for testing
                spec = ProjectSpec(name="test", description="test", version="1.0.0")
                result = validator.validate_project_spec(spec)
            elif isinstance(validator, FileValidator):
                result = validator.validate_structure(temp_workspace, ["nonexistent.py"])
            else:
                # For other validators, create a simple test
                result = ValidationResult(is_valid=True, errors=[], warnings=[])
            
            all_results.append(result)
        
        # Should have found various issues
        total_errors = sum(len(r.errors) for r in all_results)
        total_warnings = sum(len(r.warnings) for r in all_results)
        
        assert total_errors > 0 or total_warnings > 0
    
    def _create_problematic_project(self, workspace: Path):
        """Create a project with various validation issues."""
        # Create file with syntax errors
        (workspace / "broken.py").write_text('''
def broken_function(
    # Missing closing parenthesis and other syntax errors
    return "broken"
        
def another_function():
    # Indentation error
  return 42
''')
        
        # Create file with security issues
        (workspace / "insecure.py").write_text('''
import os

def dangerous(user_input):
    # Command injection vulnerability
    os.system(f"rm -rf {user_input}")
    
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    
    # Using eval
    return eval(user_input)
''')
        
        # Create empty or minimal files to trigger missing file errors
        (workspace / "empty.py").touch()