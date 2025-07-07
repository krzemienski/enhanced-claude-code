"""
Syntax validation for generated code.
"""
import ast
import json
import yaml
import toml
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import tempfile
import re

from ..models.base import SerializableModel
from ..models.validation import ValidationResult, ValidationIssue, ValidationLevel, ValidationType


class FileType(Enum):
    """Supported file types for validation."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    MARKDOWN = "markdown"
    DOCKERFILE = "dockerfile"
    SHELL = "shell"
    SQL = "sql"
    HTML = "html"
    CSS = "css"
    UNKNOWN = "unknown"


@dataclass
class SyntaxError:
    """Represents a syntax error in code."""
    file_path: str
    line: int
    column: int
    message: str
    severity: str = "error"  # error, warning, info
    code: Optional[str] = None
    suggestion: Optional[str] = None
    context: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation."""
        location = f"{self.file_path}:{self.line}:{self.column}"
        return f"{location} - {self.severity}: {self.message}"


@dataclass
class SyntaxValidationResult(ValidationResult):
    """Result of syntax validation."""
    file_path: str = ""
    file_type: FileType = FileType.UNKNOWN
    syntax_errors: List[SyntaxError] = field(default_factory=list)
    line_count: int = 0
    char_count: int = 0
    encoding: str = "utf-8"
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return any(e.severity == "error" for e in self.syntax_errors)
    
    @property
    def error_count(self) -> int:
        """Count of errors."""
        return sum(1 for e in self.syntax_errors if e.severity == "error")
    
    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return sum(1 for e in self.syntax_errors if e.severity == "warning")


class SyntaxValidator:
    """Validates syntax of generated code."""
    
    def __init__(self):
        """Initialize syntax validator."""
        self.file_type_map = {
            '.py': FileType.PYTHON,
            '.js': FileType.JAVASCRIPT,
            '.jsx': FileType.JAVASCRIPT,
            '.ts': FileType.TYPESCRIPT,
            '.tsx': FileType.TYPESCRIPT,
            '.json': FileType.JSON,
            '.yaml': FileType.YAML,
            '.yml': FileType.YAML,
            '.toml': FileType.TOML,
            '.md': FileType.MARKDOWN,
            '.dockerfile': FileType.DOCKERFILE,
            'Dockerfile': FileType.DOCKERFILE,
            '.sh': FileType.SHELL,
            '.bash': FileType.SHELL,
            '.sql': FileType.SQL,
            '.html': FileType.HTML,
            '.htm': FileType.HTML,
            '.css': FileType.CSS
        }
        
    def validate_file(self, file_path: Path) -> SyntaxValidationResult:
        """Validate a single file."""
        # Determine file type
        file_type = self._get_file_type(file_path)
        
        # Read file content
        try:
            content = file_path.read_text(encoding='utf-8')
            line_count = len(content.splitlines())
            char_count = len(content)
        except Exception as e:
            return SyntaxValidationResult(
                file_path=str(file_path),
                file_type=file_type,
                success=False,
                line_count=0,
                char_count=0
            )
            
        # Create result
        result = SyntaxValidationResult(
            file_path=str(file_path),
            file_type=file_type,
            success=True,
            line_count=line_count,
            char_count=char_count
        )
        
        # Validate based on file type
        validators = {
            FileType.PYTHON: self._validate_python,
            FileType.JAVASCRIPT: self._validate_javascript,
            FileType.TYPESCRIPT: self._validate_typescript,
            FileType.JSON: self._validate_json,
            FileType.YAML: self._validate_yaml,
            FileType.TOML: self._validate_toml,
            FileType.DOCKERFILE: self._validate_dockerfile,
            FileType.SHELL: self._validate_shell,
            FileType.SQL: self._validate_sql,
            FileType.HTML: self._validate_html,
            FileType.CSS: self._validate_css
        }
        
        validator = validators.get(file_type)
        if validator:
            syntax_errors = validator(content, file_path)
            result.syntax_errors.extend(syntax_errors)
            result.success = not result.has_errors
            if result.has_errors:
                for e in syntax_errors:
                    if e.severity == "error":
                        result.add_issue(ValidationIssue(
                            message=str(e),
                            level=ValidationLevel.ERROR,
                            validation_type=ValidationType.SYNTAX,
                            file_path=Path(e.file_path),
                            line_number=e.line
                        ))
            
        return result
        
    def validate_directory(self, directory: Path, 
                         recursive: bool = True,
                         include_patterns: Optional[List[str]] = None,
                         exclude_patterns: Optional[List[str]] = None) -> List[SyntaxValidationResult]:
        """Validate all files in a directory."""
        results = []
        
        # Default exclude patterns
        if exclude_patterns is None:
            exclude_patterns = ['__pycache__', '.git', 'node_modules', '.venv', 'venv']
            
        # Find files
        pattern = '**/*' if recursive else '*'
        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue
                
            # Check exclude patterns
            if any(pattern in str(file_path) for pattern in exclude_patterns):
                continue
                
            # Check include patterns
            if include_patterns:
                if not any(file_path.match(pattern) for pattern in include_patterns):
                    continue
                    
            # Validate file
            result = self.validate_file(file_path)
            results.append(result)
            
        return results
        
    def _get_file_type(self, file_path: Path) -> FileType:
        """Determine file type from extension."""
        # Check full filename first (for Dockerfile)
        if file_path.name in self.file_type_map:
            return self.file_type_map[file_path.name]
            
        # Check extension
        suffix = file_path.suffix.lower()
        return self.file_type_map.get(suffix, FileType.UNKNOWN)
        
    def _validate_python(self, content: str, file_path: Path) -> List[SyntaxError]:
        """Validate Python syntax."""
        errors = []
        
        try:
            # Parse with AST
            ast.parse(content)
        except SyntaxError as e:
            errors.append(SyntaxError(
                file_path=str(file_path),
                line=e.lineno or 1,
                column=e.offset or 1,
                message=e.msg,
                context=e.text
            ))
            
        # Additional checks with external tools if available
        try:
            # Try pyflakes
            result = subprocess.run(
                ['pyflakes', str(file_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout:
                errors.extend(self._parse_pyflakes_output(result.stdout, file_path))
        except (subprocess.SubprocessError, FileNotFoundError):
            # Tool not available
            pass
            
        return errors
        
    def _validate_javascript(self, content: str, file_path: Path) -> List[SyntaxError]:
        """Validate JavaScript syntax."""
        errors = []
        
        # Basic regex checks for common errors
        patterns = [
            (r'}\s*else', "Missing semicolon before 'else'"),
            (r'if\s*\(.*\)\s*{.*}\s*\n\s*else', "Possible missing semicolon after if block"),
            (r'function\s+\w+\s*\([^)]*\)\s*[^{]', "Missing opening brace for function"),
        ]
        
        lines = content.splitlines()
        for line_num, line in enumerate(lines, 1):
            for pattern, message in patterns:
                if re.search(pattern, line):
                    errors.append(SyntaxError(
                        file_path=str(file_path),
                        line=line_num,
                        column=1,
                        message=message,
                        severity="warning",
                        context=line.strip()
                    ))
                    
        # Try external tools if available
        try:
            # Try eslint
            with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False) as f:
                f.write(content)
                f.flush()
                
                result = subprocess.run(
                    ['eslint', '--format=json', f.name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.stdout:
                    errors.extend(self._parse_eslint_output(result.stdout, file_path))
                    
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
            
        return errors
        
    def _validate_typescript(self, content: str, file_path: Path) -> List[SyntaxError]:
        """Validate TypeScript syntax."""
        # Similar to JavaScript but with TypeScript-specific checks
        errors = self._validate_javascript(content, file_path)
        
        # Add TypeScript-specific patterns
        ts_patterns = [
            (r':\s*any\b', "Avoid using 'any' type"),
            (r'@ts-ignore', "Avoid using @ts-ignore"),
        ]
        
        lines = content.splitlines()
        for line_num, line in enumerate(lines, 1):
            for pattern, message in ts_patterns:
                if re.search(pattern, line):
                    errors.append(SyntaxError(
                        file_path=str(file_path),
                        line=line_num,
                        column=1,
                        message=message,
                        severity="warning",
                        context=line.strip()
                    ))
                    
        return errors
        
    def _validate_json(self, content: str, file_path: Path) -> List[SyntaxError]:
        """Validate JSON syntax."""
        errors = []
        
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            errors.append(SyntaxError(
                file_path=str(file_path),
                line=e.lineno,
                column=e.colno,
                message=e.msg
            ))
            
        return errors
        
    def _validate_yaml(self, content: str, file_path: Path) -> List[SyntaxError]:
        """Validate YAML syntax."""
        errors = []
        
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            # Parse error location if available
            if hasattr(e, 'problem_mark'):
                line = e.problem_mark.line + 1
                column = e.problem_mark.column + 1
            else:
                line = 1
                column = 1
                
            errors.append(SyntaxError(
                file_path=str(file_path),
                line=line,
                column=column,
                message=str(e)
            ))
            
        return errors
        
    def _validate_toml(self, content: str, file_path: Path) -> List[SyntaxError]:
        """Validate TOML syntax."""
        errors = []
        
        try:
            toml.loads(content)
        except toml.TomlDecodeError as e:
            # Extract line number from error message if possible
            line_match = re.search(r'line (\d+)', str(e))
            line = int(line_match.group(1)) if line_match else 1
            
            errors.append(SyntaxError(
                file_path=str(file_path),
                line=line,
                column=1,
                message=str(e)
            ))
            
        return errors
        
    def _validate_dockerfile(self, content: str, file_path: Path) -> List[SyntaxError]:
        """Validate Dockerfile syntax."""
        errors = []
        
        # Check for common Dockerfile issues
        lines = content.splitlines()
        has_from = False
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith('#'):
                continue
                
            # Check for FROM instruction
            if stripped.upper().startswith('FROM'):
                has_from = True
                
            # Check for invalid instructions
            valid_instructions = [
                'FROM', 'RUN', 'CMD', 'LABEL', 'EXPOSE', 'ENV', 'ADD',
                'COPY', 'ENTRYPOINT', 'VOLUME', 'USER', 'WORKDIR', 'ARG',
                'ONBUILD', 'STOPSIGNAL', 'HEALTHCHECK', 'SHELL'
            ]
            
            instruction = stripped.split()[0].upper() if stripped else ''
            if instruction and instruction not in valid_instructions:
                errors.append(SyntaxError(
                    file_path=str(file_path),
                    line=line_num,
                    column=1,
                    message=f"Unknown instruction: {instruction}",
                    context=stripped
                ))
                
        # Check for required FROM instruction
        if not has_from:
            errors.append(SyntaxError(
                file_path=str(file_path),
                line=1,
                column=1,
                message="Dockerfile must have at least one FROM instruction"
            ))
            
        return errors
        
    def _validate_shell(self, content: str, file_path: Path) -> List[SyntaxError]:
        """Validate shell script syntax."""
        errors = []
        
        # Try shellcheck if available
        try:
            with tempfile.NamedTemporaryFile(suffix='.sh', mode='w', delete=False) as f:
                f.write(content)
                f.flush()
                
                result = subprocess.run(
                    ['shellcheck', '-f', 'json', f.name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.stdout:
                    errors.extend(self._parse_shellcheck_output(result.stdout, file_path))
                    
        except (subprocess.SubprocessError, FileNotFoundError):
            # Fallback to basic checks
            patterns = [
                (r'^\s*fi\b', "Possible missing 'then' for if statement"),
                (r'^\s*done\b', "Possible missing 'do' for loop"),
                (r'\$\(.*\)\)', "Possible syntax error in command substitution"),
            ]
            
            lines = content.splitlines()
            for line_num, line in enumerate(lines, 1):
                for pattern, message in patterns:
                    if re.search(pattern, line):
                        errors.append(SyntaxError(
                            file_path=str(file_path),
                            line=line_num,
                            column=1,
                            message=message,
                            severity="warning",
                            context=line.strip()
                        ))
                        
        return errors
        
    def _validate_sql(self, content: str, file_path: Path) -> List[SyntaxError]:
        """Validate SQL syntax."""
        errors = []
        
        # Basic SQL syntax checks
        # Check for unmatched parentheses
        open_parens = content.count('(')
        close_parens = content.count(')')
        if open_parens != close_parens:
            errors.append(SyntaxError(
                file_path=str(file_path),
                line=1,
                column=1,
                message=f"Unmatched parentheses: {open_parens} opening, {close_parens} closing"
            ))
            
        # Check for missing semicolons
        statements = content.strip().split(';')
        if len(statements) > 1 and statements[-1].strip():
            errors.append(SyntaxError(
                file_path=str(file_path),
                line=len(content.splitlines()),
                column=1,
                message="Missing semicolon at end of statement",
                severity="warning"
            ))
            
        return errors
        
    def _validate_html(self, content: str, file_path: Path) -> List[SyntaxError]:
        """Validate HTML syntax."""
        errors = []
        
        # Check for basic HTML structure
        if '<html' not in content.lower():
            errors.append(SyntaxError(
                file_path=str(file_path),
                line=1,
                column=1,
                message="Missing <html> tag",
                severity="warning"
            ))
            
        # Check for unclosed tags
        tag_pattern = r'<(\w+)(?:\s[^>]*)?>(?!</\1>)'
        matches = re.finditer(tag_pattern, content)
        for match in matches:
            tag = match.group(1)
            if tag.lower() not in ['br', 'hr', 'img', 'input', 'meta', 'link']:
                line_num = content[:match.start()].count('\n') + 1
                errors.append(SyntaxError(
                    file_path=str(file_path),
                    line=line_num,
                    column=1,
                    message=f"Possibly unclosed <{tag}> tag",
                    severity="warning"
                ))
                
        return errors
        
    def _validate_css(self, content: str, file_path: Path) -> List[SyntaxError]:
        """Validate CSS syntax."""
        errors = []
        
        # Check for unmatched braces
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            errors.append(SyntaxError(
                file_path=str(file_path),
                line=1,
                column=1,
                message=f"Unmatched braces: {open_braces} opening, {close_braces} closing"
            ))
            
        # Check for missing semicolons
        lines = content.splitlines()
        for line_num, line in enumerate(lines, 1):
            # Skip lines with only braces or comments
            stripped = line.strip()
            if stripped and not stripped.startswith('/*') and \
               not stripped.endswith('{') and not stripped.endswith('}') and \
               not stripped.endswith(';') and ':' in stripped:
                errors.append(SyntaxError(
                    file_path=str(file_path),
                    line=line_num,
                    column=len(line),
                    message="Missing semicolon",
                    severity="warning",
                    context=stripped
                ))
                
        return errors
        
    def _parse_pyflakes_output(self, output: str, file_path: Path) -> List[SyntaxError]:
        """Parse pyflakes output."""
        errors = []
        for line in output.splitlines():
            # Format: file.py:line:column: message
            match = re.match(r'.*:(\d+):(\d+):\s*(.+)', line)
            if match:
                errors.append(SyntaxError(
                    file_path=str(file_path),
                    line=int(match.group(1)),
                    column=int(match.group(2)),
                    message=match.group(3),
                    severity="warning"
                ))
        return errors
        
    def _parse_eslint_output(self, output: str, file_path: Path) -> List[SyntaxError]:
        """Parse ESLint JSON output."""
        errors = []
        try:
            data = json.loads(output)
            for file_data in data:
                for message in file_data.get('messages', []):
                    severity = 'error' if message.get('severity') == 2 else 'warning'
                    errors.append(SyntaxError(
                        file_path=str(file_path),
                        line=message.get('line', 1),
                        column=message.get('column', 1),
                        message=message.get('message', 'Unknown error'),
                        severity=severity,
                        code=message.get('ruleId')
                    ))
        except json.JSONDecodeError:
            pass
        return errors
        
    def _parse_shellcheck_output(self, output: str, file_path: Path) -> List[SyntaxError]:
        """Parse ShellCheck JSON output."""
        errors = []
        try:
            data = json.loads(output)
            for issue in data:
                severity_map = {
                    'error': 'error',
                    'warning': 'warning',
                    'info': 'info',
                    'style': 'info'
                }
                errors.append(SyntaxError(
                    file_path=str(file_path),
                    line=issue.get('line', 1),
                    column=issue.get('column', 1),
                    message=issue.get('message', 'Unknown error'),
                    severity=severity_map.get(issue.get('level', 'error'), 'error'),
                    code=f"SC{issue.get('code', '')}",
                    suggestion=issue.get('fix', {}).get('replacements', [{}])[0].get('replacement')
                ))
        except json.JSONDecodeError:
            pass
        return errors