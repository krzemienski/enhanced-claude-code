"""
Validation and quality assurance components for Claude Code Builder.
"""

from .syntax_validator import SyntaxValidator, SyntaxError, SyntaxValidationResult
from .security_scanner import SecurityScanner, SecurityVulnerability, SecurityScanResult
from .dependency_checker import DependencyChecker, DependencyIssue, DependencyCheckResult
from .quality_analyzer import QualityAnalyzer, QualityMetric, CodeSmell, QualityAnalysisResult
from .test_generator import TestGenerator, GeneratedTest, TestSuite, TestGenerationResult
from .documentation_checker import DocumentationChecker, DocumentationIssue, DocumentationCheckResult
from .report_generator import ReportGenerator, ReportSection, ValidationReport, ReportFormat

__all__ = [
    # Syntax validation
    'SyntaxValidator',
    'SyntaxError',
    'SyntaxValidationResult',
    
    # Security scanning
    'SecurityScanner',
    'SecurityVulnerability',
    'SecurityScanResult',
    
    # Dependency checking
    'DependencyChecker',
    'DependencyIssue',
    'DependencyCheckResult',
    
    # Quality analysis
    'QualityAnalyzer',
    'QualityMetric',
    'CodeSmell',
    'QualityAnalysisResult',
    
    # Test generation
    'TestGenerator',
    'GeneratedTest',
    'TestSuite',
    'TestGenerationResult',
    
    # Documentation checking
    'DocumentationChecker',
    'DocumentationIssue',
    'DocumentationCheckResult',
    
    # Report generation
    'ReportGenerator',
    'ReportSection',
    'ValidationReport',
    'ReportFormat'
]