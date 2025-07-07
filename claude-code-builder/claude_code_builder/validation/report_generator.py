"""
Validation report generation for comprehensive project analysis.
"""
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import textwrap
import statistics

from ..models.base import SerializableModel
from ..models.validation import ValidationResult, ValidationIssue, ValidationLevel, ValidationType


class ReportFormat(Enum):
    """Supported report formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    TEXT = "text"
    JUNIT = "junit"
    SARIF = "sarif"  # Static Analysis Results Interchange Format


@dataclass
class ReportSection:
    """Represents a section of the report."""
    title: str
    content: str
    level: int = 1  # Heading level (1-6)
    subsections: List['ReportSection'] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    issues: List[ValidationIssue] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Convert section to markdown."""
        lines = []
        
        # Title
        lines.append(f"{'#' * self.level} {self.title}")
        lines.append("")
        
        # Content
        if self.content:
            lines.append(self.content)
            lines.append("")
            
        # Metrics
        if self.metrics:
            lines.append("**Metrics:**")
            for key, value in self.metrics.items():
                lines.append(f"- {key}: {value}")
            lines.append("")
            
        # Issues
        if self.issues:
            lines.append("**Issues:**")
            for issue in self.issues:
                level_emoji = "🔴" if issue.level == ValidationLevel.ERROR else "⚠️"
                lines.append(f"- {level_emoji} {issue.message}")
                if issue.file_path:
                    lines.append(f"  - File: {issue.file_path}:{issue.line_number or 0}")
            lines.append("")
            
        # Subsections
        for subsection in self.subsections:
            lines.append(subsection.to_markdown())
            
        return '\n'.join(lines)


@dataclass
class ValidationReport:
    """Complete validation report."""
    project_name: str
    timestamp: datetime.datetime
    overall_score: float
    overall_status: str  # passed, failed, warning
    summary: str
    sections: List[ReportSection] = field(default_factory=list)
    all_issues: List[ValidationIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            'project_name': self.project_name,
            'timestamp': self.timestamp.isoformat(),
            'overall_score': self.overall_score,
            'overall_status': self.overall_status,
            'summary': self.summary,
            'sections': [asdict(section) for section in self.sections],
            'issues': [asdict(issue) for issue in self.all_issues],
            'metrics': self.metrics,
            'recommendations': self.recommendations
        }


class ReportGenerator:
    """Generates comprehensive validation reports."""
    
    def __init__(self):
        """Initialize report generator."""
        self.section_order = [
            'Summary',
            'Syntax Validation',
            'Security Analysis',
            'Dependency Check',
            'Code Quality',
            'Test Coverage',
            'Documentation',
            'Recommendations',
            'Detailed Issues'
        ]
        
    def generate_report(self, 
                       results: Dict[str, ValidationResult],
                       project_path: Path,
                       format: ReportFormat = ReportFormat.MARKDOWN) -> str:
        """Generate a comprehensive validation report."""
        # Create report structure
        report = self._build_report(results, project_path)
        
        # Format report
        if format == ReportFormat.MARKDOWN:
            return self._format_markdown(report)
        elif format == ReportFormat.HTML:
            return self._format_html(report)
        elif format == ReportFormat.JSON:
            return self._format_json(report)
        elif format == ReportFormat.TEXT:
            return self._format_text(report)
        elif format == ReportFormat.JUNIT:
            return self._format_junit(report)
        elif format == ReportFormat.SARIF:
            return self._format_sarif(report)
        else:
            return self._format_markdown(report)
            
    def _build_report(self, results: Dict[str, ValidationResult], 
                     project_path: Path) -> ValidationReport:
        """Build report structure from validation results."""
        # Calculate overall metrics
        total_issues = sum(len(r.issues) for r in results.values())
        error_count = sum(sum(1 for i in r.issues if i.level == ValidationLevel.ERROR) 
                         for r in results.values())
        warning_count = sum(sum(1 for i in r.issues if i.level == ValidationLevel.WARNING) 
                           for r in results.values())
        
        # Calculate overall score
        scores = []
        if 'quality' in results and hasattr(results['quality'], 'quality_score'):
            scores.append(results['quality'].quality_score)
        if 'security' in results and hasattr(results['security'], 'security_score'):
            scores.append(results['security'].security_score)
        if 'documentation' in results and hasattr(results['documentation'], 'overall_coverage'):
            scores.append(results['documentation'].overall_coverage * 100)
            
        overall_score = statistics.mean(scores) if scores else 0.0
        
        # Determine status
        if error_count > 0:
            overall_status = "failed"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "passed"
            
        # Create report
        report = ValidationReport(
            project_name=project_path.name,
            timestamp=datetime.datetime.now(),
            overall_score=overall_score,
            overall_status=overall_status,
            summary=self._generate_summary(results, error_count, warning_count),
            metrics={
                'total_issues': total_issues,
                'errors': error_count,
                'warnings': warning_count,
                'info': total_issues - error_count - warning_count
            }
        )
        
        # Add sections
        report.sections.append(self._create_summary_section(report, results))
        
        if 'syntax' in results:
            report.sections.append(self._create_syntax_section(results['syntax']))
            
        if 'security' in results:
            report.sections.append(self._create_security_section(results['security']))
            
        if 'dependencies' in results:
            report.sections.append(self._create_dependency_section(results['dependencies']))
            
        if 'quality' in results:
            report.sections.append(self._create_quality_section(results['quality']))
            
        if 'tests' in results:
            report.sections.append(self._create_test_section(results['tests']))
            
        if 'documentation' in results:
            report.sections.append(self._create_documentation_section(results['documentation']))
            
        # Add recommendations
        report.recommendations = self._generate_recommendations(results)
        report.sections.append(self._create_recommendations_section(report.recommendations))
        
        # Collect all issues
        for result in results.values():
            report.all_issues.extend(result.issues)
            
        # Add detailed issues section
        if report.all_issues:
            report.sections.append(self._create_issues_section(report.all_issues))
            
        return report
        
    def _generate_summary(self, results: Dict[str, ValidationResult], 
                         error_count: int, warning_count: int) -> str:
        """Generate executive summary."""
        if error_count > 0:
            return f"Validation failed with {error_count} errors and {warning_count} warnings."
        elif warning_count > 0:
            return f"Validation passed with {warning_count} warnings."
        else:
            return "Validation passed with no issues."
            
    def _create_summary_section(self, report: ValidationReport, 
                               results: Dict[str, ValidationResult]) -> ReportSection:
        """Create summary section."""
        content = f"""
Project: **{report.project_name}**  
Date: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}  
Overall Score: **{report.overall_score:.1f}/100**  
Status: **{report.overall_status.upper()}**

{report.summary}
"""
        
        section = ReportSection(
            title="Executive Summary",
            content=content.strip(),
            level=1,
            metrics=report.metrics
        )
        
        # Add overview subsection
        overview_content = self._create_overview_table(results)
        section.subsections.append(ReportSection(
            title="Validation Overview",
            content=overview_content,
            level=2
        ))
        
        return section
        
    def _create_overview_table(self, results: Dict[str, ValidationResult]) -> str:
        """Create overview table of all validations."""
        lines = []
        lines.append("| Validation Type | Status | Issues | Score |")
        lines.append("|-----------------|--------|--------|-------|")
        
        for val_type, result in results.items():
            status = "✅ Pass" if result.success else "❌ Fail"
            issues = len(result.issues)
            
            # Get score if available
            score = "-"
            if hasattr(result, 'security_score'):
                score = f"{result.security_score:.1f}%"
            elif hasattr(result, 'quality_score'):
                score = f"{result.quality_score:.1f}%"
            elif hasattr(result, 'overall_coverage'):
                score = f"{result.overall_coverage * 100:.1f}%"
                
            lines.append(f"| {val_type.title()} | {status} | {issues} | {score} |")
            
        return '\n'.join(lines)
        
    def _create_syntax_section(self, result: Any) -> ReportSection:
        """Create syntax validation section."""
        content = ""
        
        if hasattr(result, 'syntax_errors'):
            total_files = len(result.syntax_errors) if isinstance(result.syntax_errors, list) else 1
            error_files = sum(1 for r in result.syntax_errors if r.has_errors) if isinstance(result.syntax_errors, list) else 0
            
            content = f"Analyzed {total_files} files, found syntax errors in {error_files} files."
            
        return ReportSection(
            title="Syntax Validation",
            content=content,
            level=2,
            issues=[i for i in result.issues if i.validation_type == ValidationType.SYNTAX]
        )
        
    def _create_security_section(self, result: Any) -> ReportSection:
        """Create security analysis section."""
        content = ""
        metrics = {}
        
        if hasattr(result, 'vulnerabilities'):
            vuln_count = len(result.vulnerabilities)
            critical = sum(1 for v in result.vulnerabilities if v.severity == "critical")
            high = sum(1 for v in result.vulnerabilities if v.severity == "high")
            
            content = f"Found {vuln_count} security vulnerabilities ({critical} critical, {high} high)."
            
            if hasattr(result, 'security_score'):
                metrics['Security Score'] = f"{result.security_score:.1f}/100"
                
        return ReportSection(
            title="Security Analysis",
            content=content,
            level=2,
            metrics=metrics,
            issues=[i for i in result.issues if i.validation_type == ValidationType.SECURITY]
        )
        
    def _create_dependency_section(self, result: Any) -> ReportSection:
        """Create dependency check section."""
        content = ""
        metrics = {}
        
        if hasattr(result, 'total_packages'):
            metrics['Total Packages'] = result.total_packages
            metrics['Direct Dependencies'] = result.direct_dependencies
            metrics['Security Vulnerabilities'] = result.security_vulnerabilities
            metrics['Outdated Packages'] = result.outdated_packages
            
            content = f"Analyzed {result.total_packages} dependencies."
            
        return ReportSection(
            title="Dependency Check",
            content=content,
            level=2,
            metrics=metrics,
            issues=[i for i in result.issues if i.validation_type == ValidationType.DEPENDENCY]
        )
        
    def _create_quality_section(self, result: Any) -> ReportSection:
        """Create code quality section."""
        content = ""
        metrics = {}
        
        if hasattr(result, 'quality_score'):
            metrics['Quality Score'] = f"{result.quality_score:.1f}/100"
            metrics['Maintainability'] = f"{result.maintainability_score:.1f}/100"
            metrics['Complexity'] = f"{result.complexity_score:.1f}/100"
            
            if hasattr(result, 'code_smells'):
                smell_counts = result.smell_count_by_severity
                content = f"Found {len(result.code_smells)} code smells ({smell_counts.get('high', 0)} high severity)."
                
        return ReportSection(
            title="Code Quality",
            content=content,
            level=2,
            metrics=metrics,
            issues=[i for i in result.issues if i.validation_type == ValidationType.QUALITY]
        )
        
    def _create_test_section(self, result: Any) -> ReportSection:
        """Create test coverage section."""
        content = ""
        metrics = {}
        
        if hasattr(result, 'total_tests_generated'):
            metrics['Tests Generated'] = result.total_tests_generated
            metrics['Coverage Estimate'] = f"{result.coverage_estimate * 100:.1f}%"
            metrics['Edge Cases'] = result.edge_cases_generated
            
            content = f"Generated {result.total_tests_generated} tests covering {result.functions_covered}/{result.functions_total} functions."
            
        return ReportSection(
            title="Test Coverage",
            content=content,
            level=2,
            metrics=metrics,
            issues=[i for i in result.issues if i.validation_type == ValidationType.TEST]
        )
        
    def _create_documentation_section(self, result: Any) -> ReportSection:
        """Create documentation section."""
        content = ""
        metrics = {}
        
        if hasattr(result, 'overall_coverage'):
            metrics['Documentation Coverage'] = f"{result.overall_coverage * 100:.1f}%"
            metrics['Documented Elements'] = f"{result.documented_elements}/{result.total_elements}"
            
            content = f"Documentation coverage: {result.overall_coverage * 100:.1f}%"
            
            if hasattr(result, 'readme_exists'):
                if not result.readme_exists:
                    content += "\n⚠️ Missing README file"
                if not result.license_exists:
                    content += "\n⚠️ Missing LICENSE file"
                    
        return ReportSection(
            title="Documentation",
            content=content,
            level=2,
            metrics=metrics,
            issues=[i for i in result.issues if i.validation_type == ValidationType.DOCUMENTATION]
        )
        
    def _create_recommendations_section(self, recommendations: List[str]) -> ReportSection:
        """Create recommendations section."""
        content = ""
        
        if recommendations:
            content = "Based on the validation results, we recommend:\n\n"
            for i, rec in enumerate(recommendations, 1):
                content += f"{i}. {rec}\n"
        else:
            content = "No specific recommendations at this time."
            
        return ReportSection(
            title="Recommendations",
            content=content,
            level=2
        )
        
    def _create_issues_section(self, issues: List[ValidationIssue]) -> ReportSection:
        """Create detailed issues section."""
        # Group issues by type and severity
        by_type = {}
        for issue in issues:
            key = (issue.validation_type, issue.level)
            if key not in by_type:
                by_type[key] = []
            by_type[key].append(issue)
            
        section = ReportSection(
            title="Detailed Issues",
            content=f"Total issues found: {len(issues)}",
            level=2
        )
        
        # Add subsections for each type/level combination
        for (val_type, level), type_issues in sorted(by_type.items()):
            subsection_title = f"{val_type.value.title()} - {level.value.title()}"
            subsection_content = ""
            
            for issue in type_issues[:10]:  # Limit to first 10
                if issue.file_path:
                    subsection_content += f"- **{issue.file_path}:{issue.line_number or 0}**: {issue.message}\n"
                else:
                    subsection_content += f"- {issue.message}\n"
                    
            if len(type_issues) > 10:
                subsection_content += f"\n... and {len(type_issues) - 10} more\n"
                
            section.subsections.append(ReportSection(
                title=subsection_title,
                content=subsection_content,
                level=3
            ))
            
        return section
        
    def _generate_recommendations(self, results: Dict[str, ValidationResult]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Security recommendations
        if 'security' in results:
            sec_result = results['security']
            if hasattr(sec_result, 'vulnerabilities'):
                critical_vulns = sum(1 for v in sec_result.vulnerabilities if v.severity == "critical")
                if critical_vulns > 0:
                    recommendations.append(f"**URGENT**: Fix {critical_vulns} critical security vulnerabilities immediately")
                    
        # Dependency recommendations
        if 'dependencies' in results:
            dep_result = results['dependencies']
            if hasattr(dep_result, 'security_vulnerabilities') and dep_result.security_vulnerabilities > 0:
                recommendations.append(f"Update {dep_result.security_vulnerabilities} dependencies with known vulnerabilities")
                
        # Quality recommendations
        if 'quality' in results:
            qual_result = results['quality']
            if hasattr(qual_result, 'complexity_score') and qual_result.complexity_score < 60:
                recommendations.append("Refactor complex functions to reduce cyclomatic complexity")
                
        # Documentation recommendations
        if 'documentation' in results:
            doc_result = results['documentation']
            if hasattr(doc_result, 'overall_coverage') and doc_result.overall_coverage < 0.5:
                recommendations.append("Improve documentation coverage (currently below 50%)")
                
        # Test recommendations
        if 'tests' in results:
            test_result = results['tests']
            if hasattr(test_result, 'coverage_estimate') and test_result.coverage_estimate < 0.7:
                recommendations.append("Increase test coverage to at least 70%")
                
        return recommendations
        
    def _format_markdown(self, report: ValidationReport) -> str:
        """Format report as Markdown."""
        lines = []
        
        # Title
        lines.append(f"# Validation Report - {report.project_name}")
        lines.append("")
        
        # Sections
        for section in report.sections:
            lines.append(section.to_markdown())
            
        return '\n'.join(lines)
        
    def _format_html(self, report: ValidationReport) -> str:
        """Format report as HTML."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Validation Report - {report.project_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; }}
        .metric {{ background: #f0f0f0; padding: 10px; margin: 5px 0; }}
        .error {{ color: #d00; }}
        .warning {{ color: #f90; }}
        .success {{ color: #0a0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Validation Report - {report.project_name}</h1>
    <p>Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>Overall Score: <strong>{report.overall_score:.1f}/100</strong></p>
    <p>Status: <strong class="{report.overall_status}">{report.overall_status.upper()}</strong></p>
"""
        
        # Convert sections to HTML
        for section in report.sections:
            html += self._section_to_html(section)
            
        html += """
</body>
</html>
"""
        return html
        
    def _section_to_html(self, section: ReportSection) -> str:
        """Convert section to HTML."""
        html = f"<h{section.level}>{section.title}</h{section.level}>\n"
        
        if section.content:
            html += f"<p>{section.content.replace('\n', '<br>')}</p>\n"
            
        if section.metrics:
            html += "<div class='metrics'>\n"
            for key, value in section.metrics.items():
                html += f"<div class='metric'><strong>{key}:</strong> {value}</div>\n"
            html += "</div>\n"
            
        if section.issues:
            html += "<ul>\n"
            for issue in section.issues:
                css_class = 'error' if issue.level == ValidationLevel.ERROR else 'warning'
                html += f"<li class='{css_class}'>{issue.message}</li>\n"
            html += "</ul>\n"
            
        for subsection in section.subsections:
            html += self._section_to_html(subsection)
            
        return html
        
    def _format_json(self, report: ValidationReport) -> str:
        """Format report as JSON."""
        return json.dumps(report.to_dict(), indent=2, default=str)
        
    def _format_text(self, report: ValidationReport) -> str:
        """Format report as plain text."""
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append(f"VALIDATION REPORT - {report.project_name}")
        lines.append("=" * 80)
        lines.append(f"Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Overall Score: {report.overall_score:.1f}/100")
        lines.append(f"Status: {report.overall_status.upper()}")
        lines.append("")
        lines.append(report.summary)
        lines.append("")
        
        # Sections
        for section in report.sections:
            lines.extend(self._section_to_text(section))
            
        return '\n'.join(lines)
        
    def _section_to_text(self, section: ReportSection, indent: int = 0) -> List[str]:
        """Convert section to plain text."""
        lines = []
        prefix = "  " * indent
        
        # Title
        lines.append(prefix + section.title.upper())
        lines.append(prefix + "-" * len(section.title))
        
        # Content
        if section.content:
            for line in section.content.splitlines():
                lines.append(prefix + line)
            lines.append("")
            
        # Metrics
        if section.metrics:
            for key, value in section.metrics.items():
                lines.append(prefix + f"{key}: {value}")
            lines.append("")
            
        # Issues
        if section.issues:
            for issue in section.issues:
                lines.append(prefix + f"- {issue.message}")
            lines.append("")
            
        # Subsections
        for subsection in section.subsections:
            lines.extend(self._section_to_text(subsection, indent + 1))
            
        return lines
        
    def _format_junit(self, report: ValidationReport) -> str:
        """Format report as JUnit XML."""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="{report.project_name}" tests="{len(report.all_issues)}" 
            failures="{sum(1 for i in report.all_issues if i.level == ValidationLevel.ERROR)}"
            errors="0" time="0">
    <testsuite name="Validation" tests="{len(report.all_issues)}">
"""
        
        for issue in report.all_issues:
            test_name = f"{issue.validation_type.value}.{issue.file_path or 'general'}"
            if issue.level == ValidationLevel.ERROR:
                xml += f"""        <testcase name="{test_name}" classname="Validation">
            <failure message="{issue.message}" type="{issue.validation_type.value}"/>
        </testcase>
"""
            else:
                xml += f"""        <testcase name="{test_name}" classname="Validation"/>
"""
                
        xml += """    </testsuite>
</testsuites>
"""
        return xml
        
    def _format_sarif(self, report: ValidationReport) -> str:
        """Format report as SARIF (Static Analysis Results Interchange Format)."""
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "Claude Code Builder Validator",
                        "version": "1.0.0",
                        "informationUri": "https://github.com/example/validator"
                    }
                },
                "results": []
            }]
        }
        
        for issue in report.all_issues:
            result = {
                "ruleId": f"{issue.validation_type.value}.{issue.level.value}",
                "level": "error" if issue.level == ValidationLevel.ERROR else "warning",
                "message": {
                    "text": issue.message
                }
            }
            
            if issue.file_path:
                result["locations"] = [{
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": str(issue.file_path)
                        },
                        "region": {
                            "startLine": issue.line_number or 1
                        }
                    }
                }]
                
            sarif["runs"][0]["results"].append(result)
            
        return json.dumps(sarif, indent=2)