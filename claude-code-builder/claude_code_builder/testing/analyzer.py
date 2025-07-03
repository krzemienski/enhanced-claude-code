"""Test result analysis and reporting."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..models.testing import TestResult, TestStatus, TestMetrics

logger = logging.getLogger(__name__)


class AnalysisLevel(Enum):
    """Analysis detail levels."""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


@dataclass
class TestAnalysis:
    """Comprehensive test analysis results."""
    summary: Dict[str, Any]
    trends: Dict[str, Any]
    recommendations: List[str]
    risk_assessment: Dict[str, Any]
    performance_insights: Dict[str, Any]
    quality_score: float


class TestAnalyzer:
    """Analyzes test results and provides insights."""
    
    def __init__(self):
        """Initialize test analyzer."""
        self.analysis_cache = {}
        logger.info("Test Analyzer initialized")
    
    def analyze_results(
        self,
        results: List[TestResult],
        level: AnalysisLevel = AnalysisLevel.DETAILED
    ) -> TestAnalysis:
        """Analyze test results and generate insights."""
        logger.info(f"Analyzing {len(results)} test results at {level.value} level")
        
        if level == AnalysisLevel.BASIC:
            return self._basic_analysis(results)
        elif level == AnalysisLevel.DETAILED:
            return self._detailed_analysis(results)
        else:
            return self._comprehensive_analysis(results)
    
    def _basic_analysis(self, results: List[TestResult]) -> TestAnalysis:
        """Perform basic analysis."""
        if not results:
            return TestAnalysis(
                summary={"total_tests": 0},
                trends={},
                recommendations=["No test results available"],
                risk_assessment={},
                performance_insights={},
                quality_score=0.0
            )
        
        # Basic metrics
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed_tests = sum(1 for r in results if r.status == TestStatus.FAILED)
        
        success_rate = passed_tests / total_tests if total_tests > 0 else 0.0
        
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate
        }
        
        recommendations = []
        if success_rate < 0.8:
            recommendations.append("Success rate below 80% - investigate failures")
        if failed_tests > 0:
            recommendations.append(f"{failed_tests} tests failed - review error messages")
        
        return TestAnalysis(
            summary=summary,
            trends={},
            recommendations=recommendations,
            risk_assessment={"overall_risk": "medium" if success_rate < 0.8 else "low"},
            performance_insights={},
            quality_score=success_rate * 100
        )
    
    def _detailed_analysis(self, results: List[TestResult]) -> TestAnalysis:
        """Perform detailed analysis."""
        basic_analysis = self._basic_analysis(results)
        
        if not results:
            return basic_analysis
        
        # Performance analysis
        avg_duration = sum(r.duration_seconds for r in results) / len(results)
        max_duration = max(r.duration_seconds for r in results)
        min_duration = min(r.duration_seconds for r in results)
        
        # Failure analysis
        failure_patterns = self._analyze_failure_patterns(results)
        
        # Test type analysis
        type_analysis = self._analyze_by_test_type(results)
        
        # Enhanced summary
        basic_analysis.summary.update({
            "avg_duration_seconds": avg_duration,
            "max_duration_seconds": max_duration,
            "min_duration_seconds": min_duration,
            "failure_patterns": failure_patterns,
            "test_types": type_analysis
        })
        
        # Performance insights
        basic_analysis.performance_insights = {
            "avg_execution_time": avg_duration,
            "performance_trend": "stable",  # Would need historical data
            "slow_tests": [
                r.test_id for r in results
                if r.duration_seconds > avg_duration * 2
            ]
        }
        
        # Enhanced recommendations
        if avg_duration > 120:  # More than 2 minutes
            basic_analysis.recommendations.append("Average test duration is high - consider optimization")
        
        if len(failure_patterns) > 3:
            basic_analysis.recommendations.append("Multiple failure patterns detected - systematic issues possible")
        
        return basic_analysis
    
    def _comprehensive_analysis(self, results: List[TestResult]) -> TestAnalysis:
        """Perform comprehensive analysis."""
        detailed_analysis = self._detailed_analysis(results)
        
        if not results:
            return detailed_analysis
        
        # Trend analysis (would need historical data)
        trends = self._analyze_trends(results)
        detailed_analysis.trends = trends
        
        # Risk assessment
        risk_assessment = self._assess_risks(results)
        detailed_analysis.risk_assessment = risk_assessment
        
        # Quality scoring
        quality_score = self._calculate_quality_score(results)
        detailed_analysis.quality_score = quality_score
        
        return detailed_analysis
    
    def _analyze_failure_patterns(self, results: List[TestResult]) -> Dict[str, int]:
        """Analyze patterns in test failures."""
        patterns = {}
        
        for result in results:
            if result.status == TestStatus.FAILED and result.error_message:
                # Extract key words from error messages
                error_words = result.error_message.lower().split()
                for word in error_words:
                    if len(word) > 4:  # Skip short words
                        patterns[word] = patterns.get(word, 0) + 1
        
        # Return top patterns
        return dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:5])
    
    def _analyze_by_test_type(self, results: List[TestResult]) -> Dict[str, Dict[str, Any]]:
        """Analyze results by test type."""
        type_analysis = {}
        
        for result in results:
            test_type = result.test_type.value if result.test_type else "unknown"
            
            if test_type not in type_analysis:
                type_analysis[test_type] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "avg_duration": 0.0
                }
            
            type_analysis[test_type]["total"] += 1
            
            if result.status == TestStatus.PASSED:
                type_analysis[test_type]["passed"] += 1
            elif result.status == TestStatus.FAILED:
                type_analysis[test_type]["failed"] += 1
            
            # Update average duration
            current_avg = type_analysis[test_type]["avg_duration"]
            total = type_analysis[test_type]["total"]
            type_analysis[test_type]["avg_duration"] = (
                (current_avg * (total - 1) + result.duration_seconds) / total
            )
        
        return type_analysis
    
    def _analyze_trends(self, results: List[TestResult]) -> Dict[str, Any]:
        """Analyze trends in test results."""
        # Sort by start time
        sorted_results = sorted(results, key=lambda r: r.start_time or datetime.min)
        
        if len(sorted_results) < 2:
            return {"trend": "insufficient_data"}
        
        # Calculate success rate trend
        recent_results = sorted_results[-5:]  # Last 5 tests
        older_results = sorted_results[:-5] if len(sorted_results) > 5 else []
        
        recent_success_rate = sum(1 for r in recent_results if r.status == TestStatus.PASSED) / len(recent_results)
        
        if older_results:
            older_success_rate = sum(1 for r in older_results if r.status == TestStatus.PASSED) / len(older_results)
            
            if recent_success_rate > older_success_rate + 0.1:
                trend = "improving"
            elif recent_success_rate < older_success_rate - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "success_rate_trend": trend,
            "recent_success_rate": recent_success_rate,
            "total_data_points": len(sorted_results)
        }
    
    def _assess_risks(self, results: List[TestResult]) -> Dict[str, Any]:
        """Assess risks based on test results."""
        if not results:
            return {"overall_risk": "unknown"}
        
        # Calculate risk factors
        failure_rate = sum(1 for r in results if r.status == TestStatus.FAILED) / len(results)
        avg_duration = sum(r.duration_seconds for r in results) / len(results)
        
        # Risk levels
        if failure_rate > 0.3:
            overall_risk = "high"
        elif failure_rate > 0.1:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        return {
            "overall_risk": overall_risk,
            "failure_rate": failure_rate,
            "performance_risk": "high" if avg_duration > 300 else "low",
            "reliability_score": (1 - failure_rate) * 100
        }
    
    def _calculate_quality_score(self, results: List[TestResult]) -> float:
        """Calculate overall quality score."""
        if not results:
            return 0.0
        
        # Factors: success rate, performance, consistency
        success_rate = sum(1 for r in results if r.status == TestStatus.PASSED) / len(results)
        
        # Performance factor (normalize to 0-1)
        avg_duration = sum(r.duration_seconds for r in results) / len(results)
        performance_factor = max(0, 1 - (avg_duration / 600))  # 10 minutes max
        
        # Consistency factor (low variance in duration)
        durations = [r.duration_seconds for r in results]
        if len(durations) > 1:
            import statistics
            variance = statistics.variance(durations)
            consistency_factor = max(0, 1 - (variance / 10000))  # Normalize variance
        else:
            consistency_factor = 1.0
        
        # Weighted score
        quality_score = (success_rate * 0.6 + performance_factor * 0.3 + consistency_factor * 0.1) * 100
        
        return min(100.0, max(0.0, quality_score))