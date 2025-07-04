"""
Automated test generation for code validation.
"""
import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import textwrap

from ..models.base import SerializableModel
from ..models.validation import ValidationResult, ValidationIssue, ValidationLevel, ValidationType


class TestType(Enum):
    """Types of tests to generate."""
    UNIT = "unit"
    INTEGRATION = "integration"
    FUNCTIONAL = "functional"
    EDGE_CASE = "edge_case"
    ERROR_HANDLING = "error_handling"
    PERFORMANCE = "performance"
    SECURITY = "security"
    REGRESSION = "regression"


@dataclass
class GeneratedTest:
    """Represents a generated test."""
    test_type: TestType
    test_name: str
    test_code: str
    target_function: str
    target_file: str
    description: str
    assertions: List[str] = field(default_factory=list)
    setup_code: Optional[str] = None
    teardown_code: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.test_name} ({self.test_type.value}) for {self.target_function}"


@dataclass
class TestSuite:
    """Represents a test suite."""
    suite_name: str
    target_module: str
    tests: List[GeneratedTest] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    fixtures: List[str] = field(default_factory=list)
    
    def to_code(self) -> str:
        """Generate complete test suite code."""
        lines = []
        
        # Header
        lines.append(f'"""')
        lines.append(f'Test suite for {self.target_module}')
        lines.append(f'Generated automatically by TestGenerator')
        lines.append(f'"""')
        lines.append('')
        
        # Imports
        for imp in self.imports:
            lines.append(imp)
        lines.append('')
        
        # Fixtures
        for fixture in self.fixtures:
            lines.append(fixture)
            lines.append('')
            
        # Test class
        lines.append(f'class {self.suite_name}:')
        lines.append(f'    """Test suite for {self.target_module}."""')
        lines.append('')
        
        # Tests
        for test in self.tests:
            if test.setup_code:
                lines.append(f'    def setup_{test.test_name}(self):')
                lines.append(f'        """Setup for {test.test_name}."""')
                for line in test.setup_code.splitlines():
                    lines.append(f'        {line}')
                lines.append('')
                
            lines.append(f'    def {test.test_name}(self):')
            lines.append(f'        """')
            lines.append(f'        {test.description}')
            lines.append(f'        """')
            for line in test.test_code.splitlines():
                lines.append(f'        {line}')
            lines.append('')
            
            if test.teardown_code:
                lines.append(f'    def teardown_{test.test_name}(self):')
                lines.append(f'        """Teardown for {test.test_name}."""')
                for line in test.teardown_code.splitlines():
                    lines.append(f'        {line}')
                lines.append('')
                
        return '\n'.join(lines)


@dataclass
class TestGenerationResult(ValidationResult):
    """Result of test generation."""
    target_path: str = ""
    test_suites: List[TestSuite] = field(default_factory=list)
    total_tests_generated: int = 0
    coverage_estimate: float = 0.0
    functions_covered: int = 0
    functions_total: int = 0
    classes_covered: int = 0
    classes_total: int = 0
    edge_cases_generated: int = 0
    
    @property
    def test_count_by_type(self) -> Dict[TestType, int]:
        """Count tests by type."""
        counts = {}
        for suite in self.test_suites:
            for test in suite.tests:
                counts[test.test_type] = counts.get(test.test_type, 0) + 1
        return counts


class TestGenerator:
    """Generates automated tests for code validation."""
    
    def __init__(self):
        """Initialize test generator."""
        self.test_frameworks = {
            'python': 'pytest',
            'javascript': 'jest',
            'typescript': 'jest',
            'java': 'junit',
            'csharp': 'nunit',
            'go': 'testing'
        }
        
        # Common test patterns
        self.assertion_patterns = {
            'equals': 'assert {actual} == {expected}',
            'not_equals': 'assert {actual} != {expected}',
            'true': 'assert {condition}',
            'false': 'assert not {condition}',
            'is_none': 'assert {value} is None',
            'is_not_none': 'assert {value} is not None',
            'raises': 'with pytest.raises({exception}): {code}',
            'contains': 'assert {item} in {container}',
            'not_contains': 'assert {item} not in {container}',
            'greater': 'assert {actual} > {expected}',
            'less': 'assert {actual} < {expected}',
            'instance': 'assert isinstance({value}, {type})'
        }
        
    def generate_tests(self, source_path: Path, 
                      output_dir: Optional[Path] = None,
                      test_types: Optional[List[TestType]] = None) -> TestGenerationResult:
        """Generate tests for source code."""
        result = TestGenerationResult(
            target_path=str(source_path),
            success=True
        )
        
        if test_types is None:
            test_types = [TestType.UNIT, TestType.EDGE_CASE, TestType.ERROR_HANDLING]
            
        try:
            if source_path.is_file():
                # Generate tests for single file
                suite = self._generate_tests_for_file(source_path, test_types)
                if suite and suite.tests:
                    result.test_suites.append(suite)
            else:
                # Generate tests for directory
                python_files = list(source_path.glob('**/*.py'))
                for py_file in python_files:
                    if 'test' not in py_file.name and '__pycache__' not in str(py_file):
                        suite = self._generate_tests_for_file(py_file, test_types)
                        if suite and suite.tests:
                            result.test_suites.append(suite)
                            
            # Calculate statistics
            for suite in result.test_suites:
                result.total_tests_generated += len(suite.tests)
                result.edge_cases_generated += sum(1 for t in suite.tests 
                                                 if t.test_type == TestType.EDGE_CASE)
                
            # Estimate coverage
            if result.functions_total > 0:
                result.coverage_estimate = result.functions_covered / result.functions_total
                
            # Write test files if output directory specified
            if output_dir and result.test_suites:
                self._write_test_files(result.test_suites, output_dir)
                
        except Exception as e:
            result.success = False
            result.add_issue(ValidationIssue(
                message=f"Test generation failed: {str(e)}",
                level=ValidationLevel.ERROR,
                validation_type=ValidationType.TEST
            ))
            
        return result
        
    def _generate_tests_for_file(self, file_path: Path, 
                                test_types: List[TestType]) -> Optional[TestSuite]:
        """Generate tests for a single Python file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            # Create test suite
            module_name = file_path.stem
            suite = TestSuite(
                suite_name=f"Test{self._to_camel_case(module_name)}",
                target_module=module_name,
                imports=[
                    'import pytest',
                    'import unittest',
                    f'from {module_name} import *'
                ]
            )
            
            # Analyze module
            analyzer = ModuleAnalyzer()
            analyzer.visit(tree)
            
            # Generate tests for functions
            for func in analyzer.functions:
                if TestType.UNIT in test_types:
                    unit_test = self._generate_unit_test(func, file_path)
                    if unit_test:
                        suite.tests.append(unit_test)
                        
                if TestType.EDGE_CASE in test_types:
                    edge_tests = self._generate_edge_case_tests(func, file_path)
                    suite.tests.extend(edge_tests)
                    
                if TestType.ERROR_HANDLING in test_types:
                    error_test = self._generate_error_handling_test(func, file_path)
                    if error_test:
                        suite.tests.append(error_test)
                        
            # Generate tests for classes
            for cls in analyzer.classes:
                for method in cls['methods']:
                    if not method['name'].startswith('_'):  # Skip private methods
                        if TestType.UNIT in test_types:
                            unit_test = self._generate_unit_test(method, file_path, cls['name'])
                            if unit_test:
                                suite.tests.append(unit_test)
                                
            return suite if suite.tests else None
            
        except Exception:
            return None
            
    def _generate_unit_test(self, func_info: Dict, file_path: Path, 
                           class_name: Optional[str] = None) -> Optional[GeneratedTest]:
        """Generate a unit test for a function."""
        func_name = func_info['name']
        params = func_info['params']
        returns = func_info['returns']
        
        # Skip certain functions
        if func_name.startswith('__') or func_name == '__init__':
            return None
            
        # Generate test name
        test_name = f"test_{func_name}_basic"
        
        # Generate test code
        test_lines = []
        
        if class_name:
            # Test for class method
            test_lines.append(f"# Arrange")
            test_lines.append(f"instance = {class_name}()")
            test_lines.append(f"")
        
        # Generate parameter values
        param_values = self._generate_param_values(params)
        
        # Generate function call
        if class_name:
            if params:
                call = f"result = instance.{func_name}({', '.join(param_values)})"
            else:
                call = f"result = instance.{func_name}()"
        else:
            if params:
                call = f"result = {func_name}({', '.join(param_values)})"
            else:
                call = f"result = {func_name}()"
                
        test_lines.append(f"# Act")
        test_lines.append(call)
        test_lines.append(f"")
        test_lines.append(f"# Assert")
        
        # Generate assertions based on return type
        if returns:
            if returns == 'str':
                test_lines.append(f"assert isinstance(result, str)")
            elif returns == 'int':
                test_lines.append(f"assert isinstance(result, int)")
            elif returns == 'bool':
                test_lines.append(f"assert isinstance(result, bool)")
            elif returns == 'list':
                test_lines.append(f"assert isinstance(result, list)")
            elif returns == 'dict':
                test_lines.append(f"assert isinstance(result, dict)")
            else:
                test_lines.append(f"assert result is not None")
        else:
            test_lines.append(f"# Add appropriate assertions")
            
        return GeneratedTest(
            test_type=TestType.UNIT,
            test_name=test_name,
            test_code='\n'.join(test_lines),
            target_function=func_name,
            target_file=str(file_path),
            description=f"Basic unit test for {func_name}",
            assertions=['isinstance', 'not None']
        )
        
    def _generate_edge_case_tests(self, func_info: Dict, file_path: Path) -> List[GeneratedTest]:
        """Generate edge case tests for a function."""
        tests = []
        func_name = func_info['name']
        params = func_info['params']
        
        # Empty/None parameters
        if params:
            test_lines = []
            none_params = ['None'] * len(params)
            test_lines.append(f"# Test with None parameters")
            test_lines.append(f"with pytest.raises(Exception):")
            test_lines.append(f"    {func_name}({', '.join(none_params)})")
            
            tests.append(GeneratedTest(
                test_type=TestType.EDGE_CASE,
                test_name=f"test_{func_name}_none_params",
                test_code='\n'.join(test_lines),
                target_function=func_name,
                target_file=str(file_path),
                description=f"Test {func_name} with None parameters",
                assertions=['raises']
            ))
            
        # Empty collections
        for i, param in enumerate(params):
            if param.get('type') in ['list', 'dict', 'set', 'tuple']:
                test_lines = []
                edge_params = self._generate_param_values(params)
                edge_params[i] = '[]' if param['type'] == 'list' else '{}'
                
                test_lines.append(f"# Test with empty {param['type']}")
                test_lines.append(f"result = {func_name}({', '.join(edge_params)})")
                test_lines.append(f"assert result is not None")
                
                tests.append(GeneratedTest(
                    test_type=TestType.EDGE_CASE,
                    test_name=f"test_{func_name}_empty_{param['name']}",
                    test_code='\n'.join(test_lines),
                    target_function=func_name,
                    target_file=str(file_path),
                    description=f"Test {func_name} with empty {param['type']}",
                    assertions=['not None']
                ))
                
        return tests
        
    def _generate_error_handling_test(self, func_info: Dict, file_path: Path) -> Optional[GeneratedTest]:
        """Generate error handling test for a function."""
        func_name = func_info['name']
        
        # Check if function has try/except blocks
        if not func_info.get('has_error_handling'):
            return None
            
        test_lines = []
        test_lines.append(f"# Test error handling")
        test_lines.append(f"with pytest.raises(Exception):")
        test_lines.append(f"    # Call with invalid parameters that should raise an exception")
        test_lines.append(f"    {func_name}(None)")
        
        return GeneratedTest(
            test_type=TestType.ERROR_HANDLING,
            test_name=f"test_{func_name}_error_handling",
            test_code='\n'.join(test_lines),
            target_function=func_name,
            target_file=str(file_path),
            description=f"Test error handling in {func_name}",
            assertions=['raises']
        )
        
    def _generate_param_values(self, params: List[Dict]) -> List[str]:
        """Generate parameter values based on type hints."""
        values = []
        
        for param in params:
            param_type = param.get('type', 'Any')
            param_name = param['name']
            
            if param_type == 'str':
                values.append(f'"test_{param_name}"')
            elif param_type == 'int':
                values.append('42')
            elif param_type == 'float':
                values.append('3.14')
            elif param_type == 'bool':
                values.append('True')
            elif param_type == 'list':
                values.append('[1, 2, 3]')
            elif param_type == 'dict':
                values.append('{"key": "value"}')
            elif param_type == 'set':
                values.append('{1, 2, 3}')
            elif param_type == 'tuple':
                values.append('(1, 2, 3)')
            elif 'Optional' in param_type:
                # Extract inner type
                inner_type = param_type.replace('Optional[', '').replace(']', '')
                if inner_type == 'str':
                    values.append('"optional_value"')
                else:
                    values.append('None')
            else:
                # Default value
                values.append(f'None  # TODO: provide {param_type}')
                
        return values
        
    def _write_test_files(self, test_suites: List[TestSuite], output_dir: Path):
        """Write test suites to files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for suite in test_suites:
            test_file = output_dir / f"test_{suite.target_module}.py"
            test_file.write_text(suite.to_code())
            
    def _to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case to CamelCase."""
        components = snake_str.split('_')
        return ''.join(x.title() for x in components)


class ModuleAnalyzer(ast.NodeVisitor):
    """Analyzes Python modules for test generation."""
    
    def __init__(self):
        """Initialize analyzer."""
        self.functions = []
        self.classes = []
        self.current_class = None
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        func_info = {
            'name': node.name,
            'params': self._extract_params(node),
            'returns': self._extract_return_type(node),
            'has_docstring': ast.get_docstring(node) is not None,
            'has_error_handling': self._has_error_handling(node),
            'complexity': self._calculate_complexity(node),
            'line_number': node.lineno
        }
        
        if self.current_class:
            self.current_class['methods'].append(func_info)
        else:
            self.functions.append(func_info)
            
        self.generic_visit(node)
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition."""
        # Treat same as regular function but mark as async
        func_info = {
            'name': node.name,
            'params': self._extract_params(node),
            'returns': self._extract_return_type(node),
            'has_docstring': ast.get_docstring(node) is not None,
            'has_error_handling': self._has_error_handling(node),
            'is_async': True,
            'complexity': self._calculate_complexity(node),
            'line_number': node.lineno
        }
        
        if self.current_class:
            self.current_class['methods'].append(func_info)
        else:
            self.functions.append(func_info)
            
        self.generic_visit(node)
        
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        class_info = {
            'name': node.name,
            'methods': [],
            'has_docstring': ast.get_docstring(node) is not None,
            'base_classes': [self._get_name(base) for base in node.bases],
            'line_number': node.lineno
        }
        
        self.classes.append(class_info)
        
        # Visit class body
        old_class = self.current_class
        self.current_class = class_info
        self.generic_visit(node)
        self.current_class = old_class
        
    def _extract_params(self, node: ast.FunctionDef) -> List[Dict]:
        """Extract parameter information."""
        params = []
        
        for arg in node.args.args:
            param_info = {
                'name': arg.arg,
                'type': 'Any'  # Default type
            }
            
            # Extract type annotation if available
            if arg.annotation:
                param_info['type'] = self._get_type_string(arg.annotation)
                
            params.append(param_info)
            
        return params
        
    def _extract_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract return type annotation."""
        if node.returns:
            return self._get_type_string(node.returns)
        return None
        
    def _get_type_string(self, node: ast.AST) -> str:
        """Convert AST type annotation to string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Subscript):
            # Handle Optional, List, Dict, etc.
            value = self._get_type_string(node.value)
            slice_value = self._get_type_string(node.slice)
            return f"{value}[{slice_value}]"
        elif isinstance(node, ast.Tuple):
            elements = [self._get_type_string(elt) for elt in node.elts]
            return f"Tuple[{', '.join(elements)}]"
        else:
            return 'Any'
            
    def _has_error_handling(self, node: ast.FunctionDef) -> bool:
        """Check if function has error handling."""
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                return True
        return False
        
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
                
        return complexity
        
    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        else:
            return str(node)