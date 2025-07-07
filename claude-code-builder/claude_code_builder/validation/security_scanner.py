"""
Security vulnerability detection for generated code.
"""
import re
import ast
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import secrets

from ..models.base import SerializableModel
from ..models.validation import ValidationResult, ValidationIssue, ValidationLevel, ValidationType


class VulnerabilityType(Enum):
    """Types of security vulnerabilities."""
    SQL_INJECTION = "sql_injection"
    XSS = "cross_site_scripting"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    HARDCODED_SECRETS = "hardcoded_secrets"
    WEAK_CRYPTO = "weak_cryptography"
    INSECURE_RANDOM = "insecure_random"
    UNSAFE_DESERIALIZATION = "unsafe_deserialization"
    OPEN_REDIRECT = "open_redirect"
    XXE = "xml_external_entity"
    SSRF = "server_side_request_forgery"
    INSECURE_PERMISSIONS = "insecure_permissions"
    RACE_CONDITION = "race_condition"
    BUFFER_OVERFLOW = "buffer_overflow"
    INTEGER_OVERFLOW = "integer_overflow"


@dataclass
class SecurityVulnerability:
    """Represents a security vulnerability."""
    vulnerability_type: VulnerabilityType
    severity: str  # critical, high, medium, low, info
    file_path: str
    line_number: int
    column_number: int
    description: str
    recommendation: str
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    affected_code: Optional[str] = None
    example_fix: Optional[str] = None
    references: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """String representation."""
        location = f"{self.file_path}:{self.line_number}:{self.column_number}"
        return f"{location} - {self.severity.upper()}: {self.vulnerability_type.value} - {self.description}"


@dataclass
class SecurityScanResult(ValidationResult):
    """Result of security scanning."""
    file_path: str = ""
    vulnerabilities: List[SecurityVulnerability] = field(default_factory=list)
    lines_scanned: int = 0
    secrets_found: List[str] = field(default_factory=list)
    security_score: float = 100.0  # 0-100 score
    scan_duration: float = 0.0
    
    @property
    def has_critical(self) -> bool:
        """Check if there are critical vulnerabilities."""
        return any(v.severity == "critical" for v in self.vulnerabilities)
    
    @property
    def vulnerability_count(self) -> int:
        """Total count of vulnerabilities."""
        return len(self.vulnerabilities)
    
    @property
    def severity_counts(self) -> Dict[str, int]:
        """Count vulnerabilities by severity."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for vuln in self.vulnerabilities:
            counts[vuln.severity] = counts.get(vuln.severity, 0) + 1
        return counts


class SecurityScanner:
    """Scans code for security vulnerabilities."""
    
    def __init__(self):
        """Initialize security scanner."""
        # Common patterns for various vulnerabilities
        self.sql_injection_patterns = [
            (r'f["\'].*SELECT.*WHERE.*{.*}', "SQL query with f-string interpolation"),
            (r'\".*SELECT.*WHERE.*\"\s*%\s*', "SQL query with % formatting"),
            (r'\.format\(.*\).*SELECT.*WHERE', "SQL query with .format()"),
            (r'execute\(["\'].*%s.*["\'].*%', "Parameterized query with string formatting"),
        ]
        
        self.xss_patterns = [
            (r'innerHTML\s*=\s*[^"\']', "Direct innerHTML assignment without quotes"),
            (r'document\.write\(.*\+.*\)', "document.write with concatenation"),
            (r'eval\(.*\+.*\)', "eval with string concatenation"),
            (r'\.html\(.*\+.*\)', "jQuery html() with concatenation"),
        ]
        
        self.command_injection_patterns = [
            (r'os\.system\([^"\'].*\+', "os.system with string concatenation"),
            (r'subprocess\.\w+\([^"\'].*\+', "subprocess with string concatenation"),
            (r'exec\([^"\'].*\+', "exec with string concatenation"),
            (r'shell=True.*["\'].*\+', "shell=True with string concatenation"),
        ]
        
        self.path_traversal_patterns = [
            (r'open\([^"\'].*\+.*["\']', "File open with string concatenation"),
            (r'\.\./', "Path traversal sequence"),
            (r'os\.path\.join\(.*request\.', "Path join with user input"),
        ]
        
        self.secret_patterns = [
            (r'["\']AIza[0-9A-Za-z-_]{35}["\']', "Google API Key"),
            (r'["\']sk_live_[0-9a-zA-Z]{24}["\']', "Stripe API Key"),
            (r'["\'][0-9a-f]{40}["\']', "Generic API Key/Token"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
        ]
        
        self.weak_crypto_patterns = [
            (r'hashlib\.md5\(', "MD5 hash usage"),
            (r'hashlib\.sha1\(', "SHA1 hash usage"),
            (r'DES\.new\(', "DES encryption"),
            (r'random\.random\(.*password', "Weak random for passwords"),
            (r'ECB\.new\(', "ECB mode encryption"),
        ]
        
    def scan_file(self, file_path: Path) -> SecurityScanResult:
        """Scan a single file for vulnerabilities."""
        result = SecurityScanResult(
            file_path=str(file_path),
            success=True
        )
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()
            result.lines_scanned = len(lines)
            
            # Determine file type
            suffix = file_path.suffix.lower()
            
            # Python-specific scanning
            if suffix == '.py':
                self._scan_python(content, lines, file_path, result)
                
            # JavaScript/TypeScript scanning
            elif suffix in ['.js', '.jsx', '.ts', '.tsx']:
                self._scan_javascript(content, lines, file_path, result)
                
            # Generic scanning for all files
            self._scan_generic(content, lines, file_path, result)
            
            # Calculate security score
            result.security_score = self._calculate_security_score(result)
            
            # Add issues to validation result
            for vuln in result.vulnerabilities:
                level = ValidationLevel.ERROR if vuln.severity in ["critical", "high"] else ValidationLevel.WARNING
                result.add_issue(ValidationIssue(
                    message=str(vuln),
                    level=level,
                    validation_type=ValidationType.SECURITY,
                    file_path=file_path,
                    line_number=vuln.line_number
                ))
                
            result.success = not result.has_critical
            
        except Exception as e:
            result.success = False
            result.add_issue(ValidationIssue(
                message=f"Security scan failed: {str(e)}",
                level=ValidationLevel.ERROR,
                validation_type=ValidationType.SECURITY,
                file_path=file_path
            ))
            
        return result
        
    def scan_directory(self, directory: Path,
                      recursive: bool = True,
                      include_patterns: Optional[List[str]] = None,
                      exclude_patterns: Optional[List[str]] = None) -> List[SecurityScanResult]:
        """Scan all files in a directory."""
        results = []
        
        # Default exclude patterns
        if exclude_patterns is None:
            exclude_patterns = ['__pycache__', '.git', 'node_modules', '.venv', 'venv', '*.pyc']
            
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
                    
            # Scan file
            result = self.scan_file(file_path)
            results.append(result)
            
        return results
        
    def _scan_python(self, content: str, lines: List[str], file_path: Path, result: SecurityScanResult):
        """Scan Python code for vulnerabilities."""
        # AST-based analysis
        try:
            tree = ast.parse(content)
            visitor = PythonSecurityVisitor(file_path, lines, result)
            visitor.visit(tree)
        except SyntaxError:
            # If AST parsing fails, fall back to pattern matching
            pass
            
        # Pattern-based analysis
        self._scan_patterns(lines, file_path, result, [
            (self.sql_injection_patterns, VulnerabilityType.SQL_INJECTION, "high"),
            (self.command_injection_patterns, VulnerabilityType.COMMAND_INJECTION, "critical"),
            (self.path_traversal_patterns, VulnerabilityType.PATH_TRAVERSAL, "high"),
            (self.weak_crypto_patterns, VulnerabilityType.WEAK_CRYPTO, "medium"),
        ])
        
    def _scan_javascript(self, content: str, lines: List[str], file_path: Path, result: SecurityScanResult):
        """Scan JavaScript/TypeScript code for vulnerabilities."""
        # Pattern-based analysis
        self._scan_patterns(lines, file_path, result, [
            (self.xss_patterns, VulnerabilityType.XSS, "high"),
            (self.command_injection_patterns, VulnerabilityType.COMMAND_INJECTION, "critical"),
        ])
        
        # Check for eval usage
        for line_num, line in enumerate(lines, 1):
            if 'eval(' in line and not line.strip().startswith('//'):
                result.vulnerabilities.append(SecurityVulnerability(
                    vulnerability_type=VulnerabilityType.COMMAND_INJECTION,
                    severity="high",
                    file_path=str(file_path),
                    line_number=line_num,
                    column_number=line.find('eval(') + 1,
                    description="Use of eval() can lead to code injection",
                    recommendation="Avoid eval() and use safer alternatives like JSON.parse()",
                    cwe_id="CWE-95",
                    affected_code=line.strip()
                ))
                
    def _scan_generic(self, content: str, lines: List[str], file_path: Path, result: SecurityScanResult):
        """Generic security scanning for all file types."""
        # Scan for hardcoded secrets
        for line_num, line in enumerate(lines, 1):
            for pattern, description in self.secret_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Avoid false positives for common placeholder values
                    value = match.group(0).strip('"\'')
                    if value.lower() not in ['password', 'secret', 'token', 'api_key', 'xxx', '...', 'placeholder']:
                        result.vulnerabilities.append(SecurityVulnerability(
                            vulnerability_type=VulnerabilityType.HARDCODED_SECRETS,
                            severity="high",
                            file_path=str(file_path),
                            line_number=line_num,
                            column_number=match.start() + 1,
                            description=f"Possible {description}",
                            recommendation="Use environment variables or secure key management",
                            cwe_id="CWE-798",
                            affected_code=line.strip()
                        ))
                        result.secrets_found.append(value[:10] + "...")
                        
    def _scan_patterns(self, lines: List[str], file_path: Path, result: SecurityScanResult,
                      pattern_groups: List[Tuple[List[Tuple[str, str]], VulnerabilityType, str]]):
        """Scan using regex patterns."""
        for patterns, vuln_type, severity in pattern_groups:
            for pattern, description in patterns:
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        result.vulnerabilities.append(SecurityVulnerability(
                            vulnerability_type=vuln_type,
                            severity=severity,
                            file_path=str(file_path),
                            line_number=line_num,
                            column_number=1,
                            description=description,
                            recommendation=self._get_recommendation(vuln_type),
                            cwe_id=self._get_cwe_id(vuln_type),
                            affected_code=line.strip()
                        ))
                        
    def _calculate_security_score(self, result: SecurityScanResult) -> float:
        """Calculate security score based on vulnerabilities."""
        if not result.vulnerabilities:
            return 100.0
            
        # Deduct points based on severity
        severity_weights = {
            "critical": 25,
            "high": 15,
            "medium": 8,
            "low": 3,
            "info": 1
        }
        
        total_deduction = 0
        for vuln in result.vulnerabilities:
            total_deduction += severity_weights.get(vuln.severity, 0)
            
        score = max(0, 100 - total_deduction)
        return round(score, 2)
        
    def _get_recommendation(self, vuln_type: VulnerabilityType) -> str:
        """Get recommendation for vulnerability type."""
        recommendations = {
            VulnerabilityType.SQL_INJECTION: "Use parameterized queries or prepared statements",
            VulnerabilityType.XSS: "Sanitize and escape all user input before rendering",
            VulnerabilityType.COMMAND_INJECTION: "Avoid shell commands; use safe APIs instead",
            VulnerabilityType.PATH_TRAVERSAL: "Validate and sanitize file paths",
            VulnerabilityType.HARDCODED_SECRETS: "Use environment variables or secure key management",
            VulnerabilityType.WEAK_CRYPTO: "Use strong cryptographic algorithms (AES-256, SHA-256+)",
            VulnerabilityType.INSECURE_RANDOM: "Use cryptographically secure random generators",
        }
        return recommendations.get(vuln_type, "Review and fix the security issue")
        
    def _get_cwe_id(self, vuln_type: VulnerabilityType) -> str:
        """Get CWE ID for vulnerability type."""
        cwe_mapping = {
            VulnerabilityType.SQL_INJECTION: "CWE-89",
            VulnerabilityType.XSS: "CWE-79",
            VulnerabilityType.COMMAND_INJECTION: "CWE-78",
            VulnerabilityType.PATH_TRAVERSAL: "CWE-22",
            VulnerabilityType.HARDCODED_SECRETS: "CWE-798",
            VulnerabilityType.WEAK_CRYPTO: "CWE-327",
            VulnerabilityType.INSECURE_RANDOM: "CWE-330",
        }
        return cwe_mapping.get(vuln_type, "CWE-Unknown")


class PythonSecurityVisitor(ast.NodeVisitor):
    """AST visitor for Python security analysis."""
    
    def __init__(self, file_path: Path, lines: List[str], result: SecurityScanResult):
        """Initialize visitor."""
        self.file_path = file_path
        self.lines = lines
        self.result = result
        
    def visit_Call(self, node: ast.Call):
        """Visit function calls."""
        # Check for dangerous functions
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            
            # eval/exec usage
            if func_name in ['eval', 'exec']:
                self._add_vulnerability(
                    node,
                    VulnerabilityType.COMMAND_INJECTION,
                    "high",
                    f"Use of {func_name}() can lead to code injection",
                    f"Avoid {func_name}() and use safer alternatives"
                )
                
            # pickle usage
            elif func_name == 'loads' and self._is_module_call(node, 'pickle'):
                self._add_vulnerability(
                    node,
                    VulnerabilityType.UNSAFE_DESERIALIZATION,
                    "high",
                    "Pickle deserialization of untrusted data is dangerous",
                    "Use JSON or other safe serialization formats"
                )
                
        # Check for SQL queries
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ['execute', 'executemany']:
                # Check if query uses string formatting
                if node.args and isinstance(node.args[0], ast.BinOp):
                    if isinstance(node.args[0].op, ast.Mod):
                        self._add_vulnerability(
                            node,
                            VulnerabilityType.SQL_INJECTION,
                            "high",
                            "SQL query uses string formatting",
                            "Use parameterized queries instead"
                        )
                        
        self.generic_visit(node)
        
    def visit_Import(self, node: ast.Import):
        """Visit import statements."""
        for alias in node.names:
            # Check for insecure modules
            if alias.name in ['pickle', 'marshal', 'shelve']:
                self._add_vulnerability(
                    node,
                    VulnerabilityType.UNSAFE_DESERIALIZATION,
                    "medium",
                    f"Import of {alias.name} module which can be insecure",
                    "Consider using safer alternatives like JSON"
                )
        self.generic_visit(node)
        
    def _add_vulnerability(self, node: ast.AST, vuln_type: VulnerabilityType,
                          severity: str, description: str, recommendation: str):
        """Add a vulnerability to the result."""
        self.result.vulnerabilities.append(SecurityVulnerability(
            vulnerability_type=vuln_type,
            severity=severity,
            file_path=str(self.file_path),
            line_number=node.lineno,
            column_number=node.col_offset + 1,
            description=description,
            recommendation=recommendation,
            affected_code=self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ""
        ))
        
    def _is_module_call(self, node: ast.Call, module: str) -> bool:
        """Check if a call is to a specific module."""
        # This is a simplified check
        return False  # Would need more context to properly check