"""
Documentation completeness checking for projects.
"""
import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..models.base import SerializableModel
from ..models.validation import ValidationResult, ValidationIssue, ValidationLevel, ValidationType


class DocumentationType(Enum):
    """Types of documentation."""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    PARAMETER = "parameter"
    RETURN = "return"
    RAISES = "raises"
    EXAMPLE = "example"
    README = "readme"
    API = "api"
    TUTORIAL = "tutorial"
    CHANGELOG = "changelog"
    LICENSE = "license"


@dataclass
class DocumentationIssue:
    """Represents a documentation issue."""
    issue_type: str  # missing, incomplete, outdated, incorrect
    doc_type: DocumentationType
    file_path: str
    line_number: int
    element_name: str
    description: str
    suggestion: str
    severity: str = "medium"  # high, medium, low
    
    def __str__(self) -> str:
        """String representation."""
        location = f"{self.file_path}:{self.line_number}"
        return f"{location} - {self.element_name}: {self.description}"


@dataclass
class DocstringInfo:
    """Information extracted from a docstring."""
    summary: str = ""
    description: str = ""
    parameters: Dict[str, str] = field(default_factory=dict)
    returns: Optional[str] = None
    raises: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        """Check if docstring has all essential components."""
        return bool(self.summary)


@dataclass
class DocumentationCheckResult(ValidationResult):
    """Result of documentation checking."""
    project_path: str = ""
    issues: List[DocumentationIssue] = field(default_factory=list)
    coverage_by_type: Dict[DocumentationType, float] = field(default_factory=dict)
    total_elements: int = 0
    documented_elements: int = 0
    overall_coverage: float = 0.0
    readme_exists: bool = False
    license_exists: bool = False
    changelog_exists: bool = False
    api_docs_exist: bool = False
    docstring_stats: Dict[str, int] = field(default_factory=dict)
    
    @property
    def missing_count(self) -> int:
        """Count of missing documentation."""
        return sum(1 for issue in self.issues if issue.issue_type == "missing")
    
    @property
    def incomplete_count(self) -> int:
        """Count of incomplete documentation."""
        return sum(1 for issue in self.issues if issue.issue_type == "incomplete")


class DocumentationChecker:
    """Checks documentation completeness."""
    
    def __init__(self):
        """Initialize documentation checker."""
        self.docstring_styles = {
            'google': self._parse_google_docstring,
            'numpy': self._parse_numpy_docstring,
            'sphinx': self._parse_sphinx_docstring,
            'epytext': self._parse_epytext_docstring
        }
        
        self.required_files = {
            'README.md': 'Project overview and getting started guide',
            'LICENSE': 'License information',
            'CHANGELOG.md': 'Version history and changes',
            'CONTRIBUTING.md': 'Contribution guidelines',
            'CODE_OF_CONDUCT.md': 'Code of conduct for contributors'
        }
        
        self.docstring_sections = [
            'Parameters', 'Returns', 'Raises', 'Examples',
            'Args', 'Yields', 'Note', 'Notes', 'Warning',
            'See Also', 'References', 'Attributes'
        ]
        
    def check_project(self, project_path: Path) -> DocumentationCheckResult:
        """Check documentation completeness for entire project."""
        result = DocumentationCheckResult(
            project_path=str(project_path),
            success=True
        )
        
        try:
            # Check for required documentation files
            self._check_required_files(project_path, result)
            
            # Check Python docstrings
            python_files = list(project_path.glob('**/*.py'))
            for py_file in python_files:
                if '__pycache__' not in str(py_file):
                    self._check_python_file(py_file, result)
                    
            # Check README content
            if result.readme_exists:
                self._check_readme_content(project_path / 'README.md', result)
                
            # Calculate overall statistics
            if result.total_elements > 0:
                result.overall_coverage = result.documented_elements / result.total_elements
                
            # Add validation issues
            for issue in result.issues:
                level = ValidationLevel.ERROR if issue.severity == "high" else ValidationLevel.WARNING
                result.add_issue(ValidationIssue(
                    message=str(issue),
                    level=level,
                    validation_type=ValidationType.DOCUMENTATION,
                    file_path=Path(issue.file_path),
                    line_number=issue.line_number
                ))
                
            result.success = result.overall_coverage >= 0.7  # 70% threshold
            
        except Exception as e:
            result.success = False
            result.add_issue(ValidationIssue(
                message=f"Documentation check failed: {str(e)}",
                level=ValidationLevel.ERROR,
                validation_type=ValidationType.DOCUMENTATION
            ))
            
        return result
        
    def _check_required_files(self, project_path: Path, result: DocumentationCheckResult):
        """Check for required documentation files."""
        for filename, description in self.required_files.items():
            file_path = project_path / filename
            
            # Also check alternative names
            alt_names = []
            if filename == 'README.md':
                alt_names = ['README.rst', 'README.txt', 'readme.md']
                result.readme_exists = any((project_path / name).exists() for name in [filename] + alt_names)
            elif filename == 'LICENSE':
                alt_names = ['LICENSE.txt', 'LICENSE.md', 'LICENCE']
                result.license_exists = any((project_path / name).exists() for name in [filename] + alt_names)
            elif filename == 'CHANGELOG.md':
                alt_names = ['CHANGELOG.rst', 'HISTORY.md', 'changelog.md']
                result.changelog_exists = any((project_path / name).exists() for name in [filename] + alt_names)
                
            exists = file_path.exists() or any((project_path / name).exists() for name in alt_names)
            
            if not exists:
                severity = "high" if filename in ['README.md', 'LICENSE'] else "medium"
                result.issues.append(DocumentationIssue(
                    issue_type="missing",
                    doc_type=DocumentationType.README if 'README' in filename else DocumentationType.LICENSE,
                    file_path=str(project_path),
                    line_number=0,
                    element_name=filename,
                    description=f"Missing required file: {filename}",
                    suggestion=f"Create {filename} with {description}",
                    severity=severity
                ))
                
    def _check_python_file(self, file_path: Path, result: DocumentationCheckResult):
        """Check documentation in a Python file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            lines = content.splitlines()
            
            # Check module docstring
            module_doc = ast.get_docstring(tree)
            result.total_elements += 1
            
            if not module_doc:
                result.issues.append(DocumentationIssue(
                    issue_type="missing",
                    doc_type=DocumentationType.MODULE,
                    file_path=str(file_path),
                    line_number=1,
                    element_name=file_path.name,
                    description="Missing module docstring",
                    suggestion="Add a docstring at the beginning of the file describing its purpose"
                ))
            else:
                result.documented_elements += 1
                # Check if module docstring is too short
                if len(module_doc.strip()) < 20:
                    result.issues.append(DocumentationIssue(
                        issue_type="incomplete",
                        doc_type=DocumentationType.MODULE,
                        file_path=str(file_path),
                        line_number=1,
                        element_name=file_path.name,
                        description="Module docstring is too brief",
                        suggestion="Expand the module docstring to better describe the module's purpose",
                        severity="low"
                    ))
                    
            # Visit all nodes
            visitor = DocstringVisitor(file_path, lines, result)
            visitor.visit(tree)
            
        except Exception:
            pass
            
    def _check_readme_content(self, readme_path: Path, result: DocumentationCheckResult):
        """Check README content for completeness."""
        try:
            content = readme_path.read_text(encoding='utf-8')
            
            # Check for essential sections
            essential_sections = [
                ('installation', r'(?i)#.*install'),
                ('usage', r'(?i)#.*usage|#.*getting started|#.*quick start'),
                ('requirements', r'(?i)#.*require|#.*depend'),
                ('license', r'(?i)#.*license|## License'),
            ]
            
            for section_name, pattern in essential_sections:
                if not re.search(pattern, content):
                    result.issues.append(DocumentationIssue(
                        issue_type="incomplete",
                        doc_type=DocumentationType.README,
                        file_path=str(readme_path),
                        line_number=0,
                        element_name="README",
                        description=f"Missing {section_name} section in README",
                        suggestion=f"Add a {section_name} section to the README",
                        severity="medium"
                    ))
                    
            # Check for badges
            if not re.search(r'!\[.*\]\(.*\)', content):
                result.issues.append(DocumentationIssue(
                    issue_type="incomplete",
                    doc_type=DocumentationType.README,
                    file_path=str(readme_path),
                    line_number=0,
                    element_name="README",
                    description="No badges found in README",
                    suggestion="Consider adding status badges (build, coverage, version)",
                    severity="low"
                ))
                
            # Check minimum length
            if len(content.strip()) < 500:
                result.issues.append(DocumentationIssue(
                    issue_type="incomplete",
                    doc_type=DocumentationType.README,
                    file_path=str(readme_path),
                    line_number=0,
                    element_name="README",
                    description="README is too brief",
                    suggestion="Expand README with more detailed information",
                    severity="medium"
                ))
                
        except Exception:
            pass
            
    def _parse_docstring(self, docstring: str) -> DocstringInfo:
        """Parse a docstring into structured information."""
        if not docstring:
            return DocstringInfo()
            
        # Try different docstring styles
        for style, parser in self.docstring_styles.items():
            info = parser(docstring)
            if info.summary:  # Successfully parsed
                return info
                
        # Fallback: basic parsing
        lines = docstring.strip().splitlines()
        if lines:
            return DocstringInfo(summary=lines[0].strip())
            
        return DocstringInfo()
        
    def _parse_google_docstring(self, docstring: str) -> DocstringInfo:
        """Parse Google-style docstring."""
        info = DocstringInfo()
        lines = docstring.strip().splitlines()
        
        if not lines:
            return info
            
        # First line is summary
        info.summary = lines[0].strip()
        
        # Parse sections
        current_section = None
        section_content = []
        
        for line in lines[1:]:
            # Check if this is a section header
            if line.strip() in self.docstring_sections:
                # Process previous section
                if current_section:
                    self._process_docstring_section(info, current_section, section_content)
                    
                current_section = line.strip().lower()
                section_content = []
            else:
                section_content.append(line)
                
        # Process last section
        if current_section:
            self._process_docstring_section(info, current_section, section_content)
            
        return info
        
    def _parse_numpy_docstring(self, docstring: str) -> DocstringInfo:
        """Parse NumPy-style docstring."""
        info = DocstringInfo()
        lines = docstring.strip().splitlines()
        
        if not lines:
            return info
            
        # Summary is first non-empty line
        for line in lines:
            if line.strip():
                info.summary = line.strip()
                break
                
        # Parse sections (underlined with dashes)
        current_section = None
        section_content = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check if next line is all dashes (section header)
            if i + 1 < len(lines) and lines[i + 1].strip() and all(c == '-' for c in lines[i + 1].strip()):
                # Process previous section
                if current_section:
                    self._process_docstring_section(info, current_section, section_content)
                    
                current_section = line.strip().lower()
                section_content = []
                i += 2  # Skip the underline
            else:
                if current_section:
                    section_content.append(line)
                i += 1
                
        # Process last section
        if current_section:
            self._process_docstring_section(info, current_section, section_content)
            
        return info
        
    def _parse_sphinx_docstring(self, docstring: str) -> DocstringInfo:
        """Parse Sphinx-style docstring."""
        info = DocstringInfo()
        lines = docstring.strip().splitlines()
        
        if not lines:
            return info
            
        # Extract summary (first paragraph)
        summary_lines = []
        for line in lines:
            if not line.strip():
                break
            summary_lines.append(line.strip())
        info.summary = ' '.join(summary_lines)
        
        # Parse field lists
        for line in lines:
            # :param name: description
            param_match = re.match(r':param\s+(\w+):\s*(.*)', line)
            if param_match:
                info.parameters[param_match.group(1)] = param_match.group(2)
                
            # :returns: description
            returns_match = re.match(r':returns?:\s*(.*)', line)
            if returns_match:
                info.returns = returns_match.group(1)
                
            # :raises ExceptionType: description
            raises_match = re.match(r':raises?\s+(\w+):\s*(.*)', line)
            if raises_match:
                info.raises.append(f"{raises_match.group(1)}: {raises_match.group(2)}")
                
        return info
        
    def _parse_epytext_docstring(self, docstring: str) -> DocstringInfo:
        """Parse Epytext-style docstring."""
        # Similar to Sphinx but with @ instead of :
        info = DocstringInfo()
        lines = docstring.strip().splitlines()
        
        if not lines:
            return info
            
        # Extract summary
        summary_lines = []
        for line in lines:
            if not line.strip() or line.strip().startswith('@'):
                break
            summary_lines.append(line.strip())
        info.summary = ' '.join(summary_lines)
        
        # Parse fields
        for line in lines:
            # @param name: description
            param_match = re.match(r'@param\s+(\w+):\s*(.*)', line)
            if param_match:
                info.parameters[param_match.group(1)] = param_match.group(2)
                
            # @return: description
            returns_match = re.match(r'@returns?:\s*(.*)', line)
            if returns_match:
                info.returns = returns_match.group(1)
                
        return info
        
    def _process_docstring_section(self, info: DocstringInfo, section: str, content: List[str]):
        """Process a docstring section."""
        section = section.lower()
        
        if section in ['parameters', 'args', 'arguments']:
            # Parse parameter descriptions
            param_name = None
            param_desc = []
            
            for line in content:
                # Check if this is a new parameter
                match = re.match(r'\s*(\w+)\s*:\s*(.*)', line.strip())
                if match:
                    # Save previous parameter
                    if param_name:
                        info.parameters[param_name] = ' '.join(param_desc)
                    param_name = match.group(1)
                    param_desc = [match.group(2)] if match.group(2) else []
                elif param_name and line.strip():
                    param_desc.append(line.strip())
                    
            # Save last parameter
            if param_name:
                info.parameters[param_name] = ' '.join(param_desc)
                
        elif section in ['returns', 'return']:
            info.returns = '\n'.join(line.strip() for line in content if line.strip())
            
        elif section in ['raises', 'raise']:
            for line in content:
                if line.strip():
                    info.raises.append(line.strip())
                    
        elif section in ['examples', 'example']:
            info.examples.extend(line.strip() for line in content if line.strip())
            
        elif section in ['notes', 'note']:
            info.notes.extend(line.strip() for line in content if line.strip())


class DocstringVisitor(ast.NodeVisitor):
    """AST visitor for checking docstrings."""
    
    def __init__(self, file_path: Path, lines: List[str], result: DocumentationCheckResult):
        """Initialize visitor."""
        self.file_path = file_path
        self.lines = lines
        self.result = result
        self.current_class = None
        self.checker = DocumentationChecker()
        
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        self.result.total_elements += 1
        docstring = ast.get_docstring(node)
        
        if not docstring:
            self.result.issues.append(DocumentationIssue(
                issue_type="missing",
                doc_type=DocumentationType.CLASS,
                file_path=str(self.file_path),
                line_number=node.lineno,
                element_name=node.name,
                description=f"Missing docstring for class '{node.name}'",
                suggestion="Add a docstring describing the class purpose and usage"
            ))
        else:
            self.result.documented_elements += 1
            # Check docstring quality
            info = self.checker._parse_docstring(docstring)
            if len(info.summary) < 10:
                self.result.issues.append(DocumentationIssue(
                    issue_type="incomplete",
                    doc_type=DocumentationType.CLASS,
                    file_path=str(self.file_path),
                    line_number=node.lineno,
                    element_name=node.name,
                    description=f"Class '{node.name}' has a very brief docstring",
                    suggestion="Expand the docstring with more details",
                    severity="low"
                ))
                
        # Visit methods
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        # Skip private methods unless they're special methods
        if node.name.startswith('_') and not node.name.startswith('__'):
            return
            
        self.result.total_elements += 1
        docstring = ast.get_docstring(node)
        
        if not docstring:
            doc_type = DocumentationType.METHOD if self.current_class else DocumentationType.FUNCTION
            element_type = "method" if self.current_class else "function"
            
            self.result.issues.append(DocumentationIssue(
                issue_type="missing",
                doc_type=doc_type,
                file_path=str(self.file_path),
                line_number=node.lineno,
                element_name=node.name,
                description=f"Missing docstring for {element_type} '{node.name}'",
                suggestion=f"Add a docstring describing what this {element_type} does"
            ))
        else:
            self.result.documented_elements += 1
            # Check docstring completeness
            info = self.checker._parse_docstring(docstring)
            
            # Check if parameters are documented
            func_params = [arg.arg for arg in node.args.args if arg.arg != 'self']
            documented_params = set(info.parameters.keys())
            
            for param in func_params:
                if param not in documented_params:
                    self.result.issues.append(DocumentationIssue(
                        issue_type="incomplete",
                        doc_type=DocumentationType.PARAMETER,
                        file_path=str(self.file_path),
                        line_number=node.lineno,
                        element_name=f"{node.name}.{param}",
                        description=f"Parameter '{param}' is not documented",
                        suggestion=f"Add documentation for parameter '{param}'",
                        severity="medium"
                    ))
                    
            # Check if return value is documented (if function has return statements)
            has_return = any(isinstance(n, ast.Return) and n.value is not None 
                           for n in ast.walk(node))
            if has_return and not info.returns:
                self.result.issues.append(DocumentationIssue(
                    issue_type="incomplete",
                    doc_type=DocumentationType.RETURN,
                    file_path=str(self.file_path),
                    line_number=node.lineno,
                    element_name=node.name,
                    description="Return value is not documented",
                    suggestion="Add documentation for the return value",
                    severity="medium"
                ))
                
            # Check if exceptions are documented
            raises = []
            for n in ast.walk(node):
                if isinstance(n, ast.Raise):
                    if isinstance(n.exc, ast.Call) and isinstance(n.exc.func, ast.Name):
                        raises.append(n.exc.func.id)
                        
            for exc in raises:
                if exc not in ' '.join(info.raises):
                    self.result.issues.append(DocumentationIssue(
                        issue_type="incomplete",
                        doc_type=DocumentationType.RAISES,
                        file_path=str(self.file_path),
                        line_number=node.lineno,
                        element_name=f"{node.name}.{exc}",
                        description=f"Exception '{exc}' is not documented",
                        suggestion=f"Document that this function can raise {exc}",
                        severity="low"
                    ))
                    
        self.generic_visit(node)
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition."""
        # Treat same as regular function
        self.visit_FunctionDef(node)