"""
Code quality metrics analyzer.
"""
import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics

from ..models.base import SerializableModel
from ..models.validation import ValidationResult, ValidationIssue, ValidationLevel, ValidationType


class QualityMetricType(Enum):
    """Types of quality metrics."""
    COMPLEXITY = "cyclomatic_complexity"
    MAINTAINABILITY = "maintainability_index"
    DUPLICATION = "code_duplication"
    COUPLING = "coupling"
    COHESION = "cohesion"
    DOCUMENTATION = "documentation_coverage"
    TEST_COVERAGE = "test_coverage"
    CODE_SMELLS = "code_smells"
    TECHNICAL_DEBT = "technical_debt"


@dataclass
class QualityMetric:
    """Represents a quality metric."""
    metric_type: QualityMetricType
    value: float
    threshold: float
    rating: str  # A, B, C, D, F
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_below_threshold(self) -> bool:
        """Check if metric is below acceptable threshold."""
        return self.value < self.threshold
        
    def __str__(self) -> str:
        """String representation."""
        return f"{self.metric_type.value}: {self.value:.2f} (Rating: {self.rating})"


@dataclass
class CodeSmell:
    """Represents a code smell."""
    smell_type: str  # long_method, large_class, duplicate_code, etc.
    severity: str  # high, medium, low
    file_path: str
    line_number: int
    description: str
    suggestion: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.file_path}:{self.line_number} - {self.smell_type}: {self.description}"


@dataclass
class QualityAnalysisResult(ValidationResult):
    """Result of quality analysis."""
    project_path: str = ""
    metrics: List[QualityMetric] = field(default_factory=list)
    code_smells: List[CodeSmell] = field(default_factory=list)
    overall_rating: str = "A"  # A-F rating
    maintainability_score: float = 100.0
    complexity_score: float = 100.0
    documentation_score: float = 100.0
    files_analyzed: int = 0
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    
    @property
    def quality_score(self) -> float:
        """Calculate overall quality score."""
        scores = [
            self.maintainability_score,
            self.complexity_score,
            self.documentation_score
        ]
        return statistics.mean(scores)
    
    @property
    def smell_count_by_severity(self) -> Dict[str, int]:
        """Count code smells by severity."""
        counts = {"high": 0, "medium": 0, "low": 0}
        for smell in self.code_smells:
            counts[smell.severity] = counts.get(smell.severity, 0) + 1
        return counts


class QualityAnalyzer:
    """Analyzes code quality metrics."""
    
    def __init__(self):
        """Initialize quality analyzer."""
        # Thresholds for various metrics
        self.complexity_thresholds = {
            'function': 10,  # McCabe complexity per function
            'class': 50,     # Total complexity per class
            'file': 100      # Total complexity per file
        }
        
        self.size_thresholds = {
            'function_lines': 50,
            'class_lines': 300,
            'file_lines': 500,
            'function_params': 5,
            'class_methods': 20,
            'class_attributes': 15
        }
        
        self.duplication_threshold = 0.05  # 5% duplication acceptable
        self.documentation_threshold = 0.80  # 80% documentation coverage
        
    def analyze_project(self, project_path: Path) -> QualityAnalysisResult:
        """Analyze quality metrics for entire project."""
        result = QualityAnalysisResult(
            project_path=str(project_path),
            success=True
        )
        
        try:
            # Find all Python files
            python_files = list(project_path.glob('**/*.py'))
            result.files_analyzed = len(python_files)
            
            # Analyze each file
            file_metrics = []
            all_functions = []
            all_classes = []
            
            for py_file in python_files:
                if '__pycache__' in str(py_file):
                    continue
                    
                file_result = self._analyze_file(py_file)
                if file_result:
                    file_metrics.append(file_result)
                    all_functions.extend(file_result.get('functions', []))
                    all_classes.extend(file_result.get('classes', []))
                    
                    # Update line counts
                    result.total_lines += file_result.get('total_lines', 0)
                    result.code_lines += file_result.get('code_lines', 0)
                    result.comment_lines += file_result.get('comment_lines', 0)
                    result.blank_lines += file_result.get('blank_lines', 0)
                    
            # Calculate overall metrics
            self._calculate_complexity_metrics(result, file_metrics, all_functions, all_classes)
            self._calculate_maintainability_metrics(result, file_metrics)
            self._calculate_documentation_metrics(result, file_metrics)
            self._detect_code_smells(result, file_metrics, project_path)
            self._calculate_duplication(result, python_files)
            
            # Calculate overall rating
            result.overall_rating = self._calculate_overall_rating(result)
            
            # Add validation issues for problems
            for smell in result.code_smells:
                if smell.severity == "high":
                    result.add_issue(ValidationIssue(
                        message=str(smell),
                        level=ValidationLevel.WARNING,
                        validation_type=ValidationType.QUALITY,
                        file_path=Path(smell.file_path),
                        line_number=smell.line_number
                    ))
                    
            for metric in result.metrics:
                if metric.rating in ["D", "F"]:
                    result.add_issue(ValidationIssue(
                        message=f"Poor {metric.metric_type.value}: {metric.description}",
                        level=ValidationLevel.WARNING,
                        validation_type=ValidationType.QUALITY
                    ))
                    
        except Exception as e:
            result.success = False
            result.add_issue(ValidationIssue(
                message=f"Quality analysis failed: {str(e)}",
                level=ValidationLevel.ERROR,
                validation_type=ValidationType.QUALITY
            ))
            
        return result
        
    def _analyze_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze a single Python file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Count lines
            total_lines = len(lines)
            code_lines = 0
            comment_lines = 0
            blank_lines = 0
            
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    blank_lines += 1
                elif stripped.startswith('#'):
                    comment_lines += 1
                else:
                    code_lines += 1
                    
            # Analyze AST
            analyzer = ASTAnalyzer(file_path, lines)
            analyzer.visit(tree)
            
            return {
                'file_path': str(file_path),
                'total_lines': total_lines,
                'code_lines': code_lines,
                'comment_lines': comment_lines,
                'blank_lines': blank_lines,
                'functions': analyzer.functions,
                'classes': analyzer.classes,
                'complexity': analyzer.total_complexity,
                'imports': analyzer.imports,
                'docstring_coverage': analyzer.docstring_coverage,
                'max_nesting_depth': analyzer.max_nesting_depth
            }
            
        except Exception:
            return None
            
    def _calculate_complexity_metrics(self, result: QualityAnalysisResult,
                                    file_metrics: List[Dict],
                                    all_functions: List[Dict],
                                    all_classes: List[Dict]):
        """Calculate complexity metrics."""
        if not all_functions:
            return
            
        # Average function complexity
        func_complexities = [f['complexity'] for f in all_functions]
        avg_func_complexity = statistics.mean(func_complexities) if func_complexities else 0
        max_func_complexity = max(func_complexities) if func_complexities else 0
        
        # Complexity score (inverse relationship)
        if avg_func_complexity <= 5:
            complexity_score = 100
        elif avg_func_complexity <= 10:
            complexity_score = 80
        elif avg_func_complexity <= 15:
            complexity_score = 60
        elif avg_func_complexity <= 20:
            complexity_score = 40
        else:
            complexity_score = 20
            
        result.complexity_score = complexity_score
        
        # Add metric
        rating = self._score_to_rating(complexity_score)
        result.metrics.append(QualityMetric(
            metric_type=QualityMetricType.COMPLEXITY,
            value=avg_func_complexity,
            threshold=self.complexity_thresholds['function'],
            rating=rating,
            description=f"Average function complexity: {avg_func_complexity:.2f}",
            details={
                'avg_function_complexity': avg_func_complexity,
                'max_function_complexity': max_func_complexity,
                'total_functions': len(all_functions),
                'complex_functions': sum(1 for f in all_functions if f['complexity'] > 10)
            }
        ))
        
    def _calculate_maintainability_metrics(self, result: QualityAnalysisResult,
                                         file_metrics: List[Dict]):
        """Calculate maintainability metrics."""
        if not file_metrics:
            return
            
        # Simplified maintainability index calculation
        # MI = 171 - 5.2 * ln(V) - 0.23 * C - 16.2 * ln(L)
        # Where V = Halstead Volume, C = Cyclomatic Complexity, L = Lines of Code
        
        total_complexity = sum(f.get('complexity', 0) for f in file_metrics)
        total_lines = sum(f.get('code_lines', 1) for f in file_metrics)
        
        # Simplified calculation
        import math
        complexity_factor = 5.2 * math.log(max(total_complexity, 1))
        lines_factor = 16.2 * math.log(max(total_lines, 1))
        
        maintainability_index = max(0, min(100, 171 - complexity_factor - lines_factor))
        result.maintainability_score = maintainability_index
        
        rating = self._score_to_rating(maintainability_index)
        result.metrics.append(QualityMetric(
            metric_type=QualityMetricType.MAINTAINABILITY,
            value=maintainability_index,
            threshold=65,  # Generally accepted threshold
            rating=rating,
            description=f"Maintainability index: {maintainability_index:.2f}",
            details={
                'total_complexity': total_complexity,
                'total_lines': total_lines,
                'avg_file_size': total_lines / len(file_metrics) if file_metrics else 0
            }
        ))
        
    def _calculate_documentation_metrics(self, result: QualityAnalysisResult,
                                       file_metrics: List[Dict]):
        """Calculate documentation metrics."""
        if not file_metrics:
            return
            
        total_items = 0
        documented_items = 0
        
        for file_metric in file_metrics:
            for func in file_metric.get('functions', []):
                total_items += 1
                if func.get('has_docstring'):
                    documented_items += 1
                    
            for cls in file_metric.get('classes', []):
                total_items += 1
                if cls.get('has_docstring'):
                    documented_items += 1
                    
        doc_coverage = documented_items / total_items if total_items > 0 else 0
        result.documentation_score = doc_coverage * 100
        
        rating = self._score_to_rating(result.documentation_score)
        result.metrics.append(QualityMetric(
            metric_type=QualityMetricType.DOCUMENTATION,
            value=doc_coverage,
            threshold=self.documentation_threshold,
            rating=rating,
            description=f"Documentation coverage: {doc_coverage:.2%}",
            details={
                'total_items': total_items,
                'documented_items': documented_items,
                'undocumented_items': total_items - documented_items
            }
        ))
        
    def _detect_code_smells(self, result: QualityAnalysisResult,
                           file_metrics: List[Dict],
                           project_path: Path):
        """Detect various code smells."""
        for file_metric in file_metrics:
            file_path = file_metric['file_path']
            
            # Long file
            if file_metric['code_lines'] > self.size_thresholds['file_lines']:
                result.code_smells.append(CodeSmell(
                    smell_type="long_file",
                    severity="medium",
                    file_path=file_path,
                    line_number=1,
                    description=f"File has {file_metric['code_lines']} lines of code",
                    suggestion="Consider splitting into smaller modules",
                    metrics={'lines': file_metric['code_lines']}
                ))
                
            # Check functions
            for func in file_metric.get('functions', []):
                # Long method
                if func['lines'] > self.size_thresholds['function_lines']:
                    result.code_smells.append(CodeSmell(
                        smell_type="long_method",
                        severity="medium",
                        file_path=file_path,
                        line_number=func['line_number'],
                        description=f"Function '{func['name']}' has {func['lines']} lines",
                        suggestion="Break down into smaller functions",
                        metrics={'lines': func['lines']}
                    ))
                    
                # High complexity
                if func['complexity'] > self.complexity_thresholds['function']:
                    result.code_smells.append(CodeSmell(
                        smell_type="complex_method",
                        severity="high",
                        file_path=file_path,
                        line_number=func['line_number'],
                        description=f"Function '{func['name']}' has complexity {func['complexity']}",
                        suggestion="Reduce complexity by extracting methods or simplifying logic",
                        metrics={'complexity': func['complexity']}
                    ))
                    
                # Too many parameters
                if func['param_count'] > self.size_thresholds['function_params']:
                    result.code_smells.append(CodeSmell(
                        smell_type="too_many_parameters",
                        severity="low",
                        file_path=file_path,
                        line_number=func['line_number'],
                        description=f"Function '{func['name']}' has {func['param_count']} parameters",
                        suggestion="Consider using parameter objects or builder pattern",
                        metrics={'params': func['param_count']}
                    ))
                    
            # Check classes
            for cls in file_metric.get('classes', []):
                # Large class
                if cls['lines'] > self.size_thresholds['class_lines']:
                    result.code_smells.append(CodeSmell(
                        smell_type="large_class",
                        severity="medium",
                        file_path=file_path,
                        line_number=cls['line_number'],
                        description=f"Class '{cls['name']}' has {cls['lines']} lines",
                        suggestion="Consider splitting responsibilities into smaller classes",
                        metrics={'lines': cls['lines']}
                    ))
                    
                # Too many methods
                if cls['method_count'] > self.size_thresholds['class_methods']:
                    result.code_smells.append(CodeSmell(
                        smell_type="too_many_methods",
                        severity="medium",
                        file_path=file_path,
                        line_number=cls['line_number'],
                        description=f"Class '{cls['name']}' has {cls['method_count']} methods",
                        suggestion="Consider extracting related methods to separate classes",
                        metrics={'methods': cls['method_count']}
                    ))
                    
    def _calculate_duplication(self, result: QualityAnalysisResult, python_files: List[Path]):
        """Calculate code duplication metrics."""
        # Simple duplication detection using hashing
        chunk_size = 5  # Number of lines to consider as a chunk
        chunks_seen = {}
        total_chunks = 0
        duplicate_chunks = 0
        
        for py_file in python_files[:50]:  # Limit for performance
            try:
                lines = py_file.read_text().splitlines()
                
                for i in range(len(lines) - chunk_size + 1):
                    chunk = '\n'.join(lines[i:i + chunk_size]).strip()
                    if len(chunk) > 50:  # Ignore small chunks
                        total_chunks += 1
                        
                        chunk_hash = hash(chunk)
                        if chunk_hash in chunks_seen:
                            duplicate_chunks += 1
                            # Record duplication
                            original = chunks_seen[chunk_hash]
                            result.code_smells.append(CodeSmell(
                                smell_type="duplicate_code",
                                severity="low",
                                file_path=str(py_file),
                                line_number=i + 1,
                                description=f"Duplicate code found (also in {original['file']}:{original['line']})",
                                suggestion="Extract duplicate code to a shared function",
                                metrics={'lines': chunk_size}
                            ))
                        else:
                            chunks_seen[chunk_hash] = {
                                'file': str(py_file),
                                'line': i + 1
                            }
            except Exception:
                pass
                
        duplication_ratio = duplicate_chunks / total_chunks if total_chunks > 0 else 0
        
        rating = "A" if duplication_ratio < 0.02 else \
                "B" if duplication_ratio < 0.05 else \
                "C" if duplication_ratio < 0.10 else \
                "D" if duplication_ratio < 0.15 else "F"
                
        result.metrics.append(QualityMetric(
            metric_type=QualityMetricType.DUPLICATION,
            value=duplication_ratio,
            threshold=self.duplication_threshold,
            rating=rating,
            description=f"Code duplication: {duplication_ratio:.2%}",
            details={
                'total_chunks': total_chunks,
                'duplicate_chunks': duplicate_chunks
            }
        ))
        
    def _calculate_overall_rating(self, result: QualityAnalysisResult) -> str:
        """Calculate overall quality rating."""
        score = result.quality_score
        return self._score_to_rating(score)
        
    def _score_to_rating(self, score: float) -> str:
        """Convert numeric score to letter rating."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


class ASTAnalyzer(ast.NodeVisitor):
    """AST visitor for quality analysis."""
    
    def __init__(self, file_path: Path, lines: List[str]):
        """Initialize analyzer."""
        self.file_path = file_path
        self.lines = lines
        self.functions = []
        self.classes = []
        self.imports = []
        self.total_complexity = 0
        self.current_class = None
        self.nesting_depth = 0
        self.max_nesting_depth = 0
        self.docstring_items = 0
        self.documented_items = 0
        
    @property
    def docstring_coverage(self) -> float:
        """Calculate docstring coverage."""
        if self.docstring_items == 0:
            return 1.0
        return self.documented_items / self.docstring_items
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        self.docstring_items += 1
        has_docstring = ast.get_docstring(node) is not None
        if has_docstring:
            self.documented_items += 1
            
        # Calculate complexity
        complexity = self._calculate_complexity(node)
        self.total_complexity += complexity
        
        # Count lines
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        lines = end_line - start_line + 1
        
        func_info = {
            'name': node.name,
            'line_number': start_line,
            'lines': lines,
            'complexity': complexity,
            'param_count': len(node.args.args),
            'has_docstring': has_docstring,
            'is_method': self.current_class is not None
        }
        
        if self.current_class:
            self.current_class['methods'].append(func_info)
        else:
            self.functions.append(func_info)
            
        # Track nesting
        self.nesting_depth += 1
        self.max_nesting_depth = max(self.max_nesting_depth, self.nesting_depth)
        self.generic_visit(node)
        self.nesting_depth -= 1
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition."""
        # Treat same as regular function
        self.visit_FunctionDef(node)
        
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        self.docstring_items += 1
        has_docstring = ast.get_docstring(node) is not None
        if has_docstring:
            self.documented_items += 1
            
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        lines = end_line - start_line + 1
        
        class_info = {
            'name': node.name,
            'line_number': start_line,
            'lines': lines,
            'methods': [],
            'has_docstring': has_docstring,
            'base_classes': [self._get_name(base) for base in node.bases],
            'decorators': [self._get_name(dec) for dec in node.decorator_list]
        }
        
        self.classes.append(class_info)
        
        # Visit class body
        old_class = self.current_class
        self.current_class = class_info
        self.generic_visit(node)
        self.current_class = old_class
        
        # Update method count
        class_info['method_count'] = len(class_info['methods'])
        
    def visit_Import(self, node: ast.Import):
        """Visit import statement."""
        for alias in node.names:
            self.imports.append({
                'module': alias.name,
                'alias': alias.asname,
                'line_number': node.lineno
            })
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from-import statement."""
        module = node.module or ''
        for alias in node.names:
            self.imports.append({
                'module': f"{module}.{alias.name}",
                'alias': alias.asname,
                'line_number': node.lineno
            })
        self.generic_visit(node)
        
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a node."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each and/or adds a branch
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += sum(1 for _ in child.ifs) + 1
                
        return complexity
        
    def _get_name(self, node: ast.AST) -> str:
        """Get name from various AST nodes."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        else:
            return str(node)