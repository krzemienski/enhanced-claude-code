"""Test report generation in multiple formats."""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from ..models.testing import TestResult, TestStatus
from .analyzer import TestAnalyzer, TestAnalysis

logger = logging.getLogger(__name__)


class TestReportGenerator:
    """Generates test reports in various formats."""
    
    def __init__(self, analyzer: Optional[TestAnalyzer] = None):
        """Initialize report generator."""
        self.analyzer = analyzer or TestAnalyzer()
        logger.info("Test Report Generator initialized")
    
    def generate_json_report(
        self,
        results: List[TestResult],
        output_path: Path,
        include_analysis: bool = True
    ) -> None:
        """Generate JSON format test report."""
        logger.info(f"Generating JSON report to {output_path}")
        
        report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_tests": len(results),
                "report_version": "1.0"
            },
            "test_results": [
                {
                    "test_id": result.test_id,
                    "test_type": result.test_type.value if result.test_type else None,
                    "status": result.status.value,
                    "start_time": result.start_time.isoformat() if result.start_time else None,
                    "end_time": result.end_time.isoformat() if result.end_time else None,
                    "duration_seconds": result.duration_seconds,
                    "tests_passed": result.tests_passed,
                    "tests_failed": result.tests_failed,
                    "tests_skipped": result.tests_skipped,
                    "error_message": result.error_message,
                    "project_id": result.project_id,
                    "execution_id": result.execution_id,
                    "metrics": result.metrics.__dict__ if result.metrics else None,
                    "metadata": result.metadata
                }
                for result in results
            ]
        }
        
        if include_analysis and results:
            analysis = self.analyzer.analyze_results(results)
            report_data["analysis"] = {
                "summary": analysis.summary,
                "trends": analysis.trends,
                "recommendations": analysis.recommendations,
                "risk_assessment": analysis.risk_assessment,
                "performance_insights": analysis.performance_insights,
                "quality_score": analysis.quality_score
            }
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"JSON report generated: {output_path}")
    
    def generate_html_report(
        self,
        results: List[TestResult],
        output_path: Path,
        include_analysis: bool = True
    ) -> None:
        """Generate HTML format test report."""
        logger.info(f"Generating HTML report to {output_path}")
        
        # Generate analysis if requested
        analysis = None
        if include_analysis and results:
            analysis = self.analyzer.analyze_results(results)
        
        # Create HTML content
        html_content = self._create_html_template(results, analysis)
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {output_path}")
    
    def generate_summary_report(
        self,
        results: List[TestResult],
        output_path: Path
    ) -> None:
        """Generate summary text report."""
        logger.info(f"Generating summary report to {output_path}")
        
        if not results:
            summary = "No test results available.\n"
        else:
            analysis = self.analyzer.analyze_results(results)
            
            summary = f"""Test Execution Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Overall Results:
- Total Tests: {analysis.summary.get('total_tests', 0)}
- Passed: {analysis.summary.get('passed_tests', 0)}
- Failed: {analysis.summary.get('failed_tests', 0)}
- Success Rate: {analysis.summary.get('success_rate', 0):.1%}
- Quality Score: {analysis.quality_score:.1f}/100

Performance:
- Average Duration: {analysis.summary.get('avg_duration_seconds', 0):.1f}s
- Max Duration: {analysis.summary.get('max_duration_seconds', 0):.1f}s

Recommendations:
{chr(10).join(f'- {rec}' for rec in analysis.recommendations)}

Risk Assessment:
- Overall Risk: {analysis.risk_assessment.get('overall_risk', 'unknown').upper()}
- Reliability Score: {analysis.risk_assessment.get('reliability_score', 0):.1f}%
"""
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(summary)
        
        logger.info(f"Summary report generated: {output_path}")
    
    def _create_html_template(
        self,
        results: List[TestResult],
        analysis: Optional[TestAnalysis]
    ) -> str:
        """Create HTML report template."""
        
        # Calculate basic stats
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed_tests = sum(1 for r in results if r.status == TestStatus.FAILED)
        
        # Status color mapping
        def status_color(status):
            colors = {
                TestStatus.PASSED: "#28a745",
                TestStatus.FAILED: "#dc3545",
                TestStatus.SKIPPED: "#ffc107",
                TestStatus.RUNNING: "#17a2b8"
            }
            return colors.get(status, "#6c757d")
        
        # Generate test results table
        results_rows = ""
        for result in results:
            status_badge = f'<span style="background-color: {status_color(result.status)}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;">{result.status.value.upper()}</span>'
            
            results_rows += f"""
            <tr>
                <td>{result.test_id}</td>
                <td>{result.test_type.value if result.test_type else 'N/A'}</td>
                <td>{status_badge}</td>
                <td>{result.duration_seconds:.1f}s</td>
                <td>{result.tests_passed}</td>
                <td>{result.tests_failed}</td>
                <td>{result.error_message[:100] + '...' if result.error_message and len(result.error_message) > 100 else (result.error_message or '')}</td>
            </tr>
            """
        
        # Analysis section
        analysis_section = ""
        if analysis:
            analysis_section = f"""
            <div class="analysis-section">
                <h2>Test Analysis</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h3>Quality Score</h3>
                        <div class="metric-value">{analysis.quality_score:.1f}/100</div>
                    </div>
                    <div class="metric-card">
                        <h3>Success Rate</h3>
                        <div class="metric-value">{analysis.summary.get('success_rate', 0):.1%}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Avg Duration</h3>
                        <div class="metric-value">{analysis.summary.get('avg_duration_seconds', 0):.1f}s</div>
                    </div>
                    <div class="metric-card">
                        <h3>Risk Level</h3>
                        <div class="metric-value">{analysis.risk_assessment.get('overall_risk', 'unknown').upper()}</div>
                    </div>
                </div>
                
                <h3>Recommendations</h3>
                <ul>
                    {''.join(f'<li>{rec}</li>' for rec in analysis.recommendations)}
                </ul>
            </div>
            """
        
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Report - Claude Code Builder</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 30px; }}
        h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #495057; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; border-left: 4px solid #007bff; }}
        .summary-card h3 {{ margin: 0 0 10px 0; color: #6c757d; font-size: 0.9em; text-transform: uppercase; }}
        .summary-card .value {{ font-size: 2em; font-weight: bold; color: #333; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric-card {{ background: #e9ecef; padding: 15px; border-radius: 6px; text-align: center; }}
        .metric-card h3 {{ margin: 0 0 8px 0; font-size: 0.8em; color: #6c757d; text-transform: uppercase; }}
        .metric-value {{ font-size: 1.5em; font-weight: bold; color: #495057; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }}
        th {{ background-color: #e9ecef; font-weight: 600; color: #495057; }}
        tr:hover {{ background-color: #f8f9fa; }}
        .analysis-section {{ margin-top: 30px; padding-top: 20px; border-top: 2px solid #e9ecef; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 5px 0; }}
        .timestamp {{ color: #6c757d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Claude Code Builder - Test Report</h1>
        <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Tests</h3>
                <div class="value">{total_tests}</div>
            </div>
            <div class="summary-card">
                <h3>Passed</h3>
                <div class="value" style="color: #28a745;">{passed_tests}</div>
            </div>
            <div class="summary-card">
                <h3>Failed</h3>
                <div class="value" style="color: #dc3545;">{failed_tests}</div>
            </div>
            <div class="summary-card">
                <h3>Success Rate</h3>
                <div class="value">{(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%</div>
            </div>
        </div>
        
        {analysis_section}
        
        <h2>Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Test ID</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Error Message</th>
                </tr>
            </thead>
            <tbody>
                {results_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
        """
        
        return html_template