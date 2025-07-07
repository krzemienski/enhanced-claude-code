"""Research Synthesizer - synthesizes research findings into actionable insights."""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict
import json

from ..models.research import ResearchResult, ResearchSource
from ..models.project import ProjectSpec, Feature

logger = logging.getLogger(__name__)


class ResearchSynthesizer:
    """Synthesizes research findings from multiple agents into cohesive insights."""
    
    def __init__(self):
        """Initialize Research Synthesizer."""
        self.synthesis_strategies = {
            "consensus": self._synthesize_by_consensus,
            "priority": self._synthesize_by_priority,
            "category": self._synthesize_by_category,
            "confidence": self._synthesize_by_confidence
        }
        
        self.category_mappings = {
            "architecture": ["design", "structure", "pattern", "component"],
            "security": ["auth", "encryption", "vulnerability", "secure"],
            "performance": ["speed", "optimize", "scale", "latency", "cache"],
            "quality": ["test", "coverage", "validation", "qa"],
            "deployment": ["deploy", "ci/cd", "infrastructure", "container"],
            "development": ["code", "practice", "standard", "convention"]
        }
    
    async def synthesize(
        self,
        research_results: List[ResearchResult],
        project_spec: ProjectSpec,
        strategy: str = "consensus"
    ) -> Dict[str, Any]:
        """Synthesize multiple research results into actionable insights."""
        logger.info(f"Synthesizing {len(research_results)} research results using {strategy} strategy")
        
        # Validate strategy
        if strategy not in self.synthesis_strategies:
            logger.warning(f"Unknown strategy {strategy}, using consensus")
            strategy = "consensus"
        
        # Apply synthesis strategy
        synthesis = await self.synthesis_strategies[strategy](research_results, project_spec)
        
        # Add executive summary
        synthesis["executive_summary"] = await self._generate_executive_summary(
            synthesis, project_spec
        )
        
        # Add implementation roadmap
        synthesis["implementation_roadmap"] = await self._generate_roadmap(
            synthesis, project_spec
        )
        
        # Add risk assessment
        synthesis["risk_assessment"] = await self._assess_risks(
            synthesis, project_spec
        )
        
        # Add metadata
        synthesis["metadata"] = {
            "synthesis_timestamp": datetime.now().isoformat(),
            "strategy_used": strategy,
            "results_count": len(research_results),
            "confidence_score": self._calculate_overall_confidence(research_results)
        }
        
        return synthesis
    
    async def _synthesize_by_consensus(
        self,
        results: List[ResearchResult],
        project_spec: ProjectSpec
    ) -> Dict[str, Any]:
        """Synthesize by finding consensus among agents."""
        consensus_findings = []
        consensus_recommendations = []
        disagreements = []
        
        # Aggregate all findings and recommendations
        all_findings = []
        all_recommendations = []
        
        for result in results:
            all_findings.extend(result.findings)
            all_recommendations.extend(result.recommendations)
        
        # Find consensus in findings
        finding_groups = self._group_similar_findings(all_findings)
        
        for group_key, findings in finding_groups.items():
            if len(findings) >= 2:  # At least 2 agents agree
                consensus_findings.append({
                    "topic": group_key,
                    "agreement_count": len(findings),
                    "agents": list(set(f.get("agent", "unknown") for f in findings)),
                    "details": self._merge_finding_details(findings),
                    "confidence": sum(f.get("relevance", 0.5) for f in findings) / len(findings)
                })
            elif len(findings) == 1 and findings[0].get("relevance", 0) >= 0.9:
                # Include high-confidence single findings
                consensus_findings.append({
                    "topic": group_key,
                    "agreement_count": 1,
                    "agents": [findings[0].get("agent", "unknown")],
                    "details": findings[0],
                    "confidence": findings[0].get("relevance", 0.5)
                })
        
        # Find consensus in recommendations
        rec_groups = self._group_similar_recommendations(all_recommendations)
        
        for group_key, recommendations in rec_groups.items():
            if len(recommendations) >= 2:
                consensus_recommendations.append({
                    "recommendation": group_key,
                    "support_count": len(recommendations),
                    "agents": list(set(
                        r.get("agent", "unknown") if isinstance(r, dict) else "unknown"
                        for r in recommendations
                    )),
                    "priority": self._calculate_recommendation_priority(recommendations)
                })
        
        # Identify disagreements
        disagreements = self._identify_disagreements(all_findings)
        
        return {
            "consensus_findings": sorted(
                consensus_findings,
                key=lambda x: x["confidence"],
                reverse=True
            ),
            "consensus_recommendations": sorted(
                consensus_recommendations,
                key=lambda x: x["priority"],
                reverse=True
            ),
            "disagreements": disagreements,
            "summary": {
                "total_findings": len(all_findings),
                "consensus_findings": len(consensus_findings),
                "total_recommendations": len(all_recommendations),
                "consensus_recommendations": len(consensus_recommendations)
            }
        }
    
    async def _synthesize_by_priority(
        self,
        results: List[ResearchResult],
        project_spec: ProjectSpec
    ) -> Dict[str, Any]:
        """Synthesize by prioritizing findings and recommendations."""
        all_findings = []
        all_recommendations = []
        
        for result in results:
            all_findings.extend(result.findings)
            all_recommendations.extend(result.recommendations)
        
        # Score and prioritize findings
        scored_findings = []
        for finding in all_findings:
            score = self._calculate_finding_priority(finding, project_spec)
            scored_findings.append({
                "finding": finding,
                "priority_score": score,
                "category": self._categorize_finding(finding)
            })
        
        # Sort by priority
        scored_findings.sort(key=lambda x: x["priority_score"], reverse=True)
        
        # Group by priority level
        priority_groups = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        for item in scored_findings:
            if item["priority_score"] >= 0.9:
                priority_groups["critical"].append(item)
            elif item["priority_score"] >= 0.7:
                priority_groups["high"].append(item)
            elif item["priority_score"] >= 0.5:
                priority_groups["medium"].append(item)
            else:
                priority_groups["low"].append(item)
        
        # Prioritize recommendations
        prioritized_recommendations = self._prioritize_recommendations(
            all_recommendations, project_spec
        )
        
        return {
            "priority_findings": priority_groups,
            "prioritized_recommendations": prioritized_recommendations,
            "top_priorities": {
                "findings": scored_findings[:10],
                "recommendations": prioritized_recommendations[:10]
            }
        }
    
    async def _synthesize_by_category(
        self,
        results: List[ResearchResult],
        project_spec: ProjectSpec
    ) -> Dict[str, Any]:
        """Synthesize by categorizing findings and recommendations."""
        categorized_findings = defaultdict(list)
        categorized_recommendations = defaultdict(list)
        
        # Categorize all findings
        for result in results:
            for finding in result.findings:
                category = self._categorize_finding(finding)
                categorized_findings[category].append(finding)
            
            for rec in result.recommendations:
                category = self._categorize_recommendation(rec)
                categorized_recommendations[category].append(rec)
        
        # Summarize each category
        category_summaries = {}
        for category, findings in categorized_findings.items():
            category_summaries[category] = {
                "finding_count": len(findings),
                "key_insights": self._extract_key_insights(findings),
                "recommendations": categorized_recommendations.get(category, [])[:5],
                "priority": self._calculate_category_priority(category, project_spec)
            }
        
        return {
            "categories": category_summaries,
            "category_priorities": sorted(
                category_summaries.items(),
                key=lambda x: x[1]["priority"],
                reverse=True
            )
        }
    
    async def _synthesize_by_confidence(
        self,
        results: List[ResearchResult],
        project_spec: ProjectSpec
    ) -> Dict[str, Any]:
        """Synthesize by confidence levels."""
        confidence_tiers = {
            "very_high": {"min": 0.9, "findings": [], "recommendations": []},
            "high": {"min": 0.75, "findings": [], "recommendations": []},
            "medium": {"min": 0.5, "findings": [], "recommendations": []},
            "low": {"min": 0.0, "findings": [], "recommendations": []}
        }
        
        # Distribute findings by confidence
        for result in results:
            base_confidence = result.confidence
            
            for finding in result.findings:
                finding_confidence = finding.get("relevance", 0.5) * base_confidence
                
                for tier_name, tier in confidence_tiers.items():
                    if finding_confidence >= tier["min"]:
                        tier["findings"].append({
                            "finding": finding,
                            "confidence": finding_confidence,
                            "source": result.metadata.get("agents_used", ["unknown"])[0]
                        })
                        break
            
            # Handle recommendations (with base confidence)
            for rec in result.recommendations:
                for tier_name, tier in confidence_tiers.items():
                    if base_confidence >= tier["min"]:
                        tier["recommendations"].append({
                            "recommendation": rec,
                            "confidence": base_confidence,
                            "source": result.metadata.get("agents_used", ["unknown"])[0]
                        })
                        break
        
        return {
            "confidence_tiers": confidence_tiers,
            "high_confidence_summary": self._summarize_high_confidence_items(
                confidence_tiers["very_high"]["findings"] + confidence_tiers["high"]["findings"]
            )
        }
    
    async def _generate_executive_summary(
        self,
        synthesis: Dict[str, Any],
        project_spec: ProjectSpec
    ) -> Dict[str, Any]:
        """Generate executive summary of synthesized research."""
        summary = {
            "project": project_spec.name,
            "type": project_spec.type,
            "scope": f"{len(project_spec.features)} features, {len(project_spec.technologies)} technologies",
            "key_findings": [],
            "critical_recommendations": [],
            "risk_level": "medium",  # Will be calculated
            "readiness_score": 0.0   # Will be calculated
        }
        
        # Extract key findings based on synthesis strategy
        if "consensus_findings" in synthesis:
            summary["key_findings"] = [
                f["topic"] for f in synthesis["consensus_findings"][:5]
            ]
        elif "top_priorities" in synthesis:
            summary["key_findings"] = [
                item["finding"].get("title", "Unknown")
                for item in synthesis["top_priorities"]["findings"][:5]
            ]
        
        # Extract critical recommendations
        if "consensus_recommendations" in synthesis:
            summary["critical_recommendations"] = [
                r["recommendation"] for r in synthesis["consensus_recommendations"][:5]
            ]
        elif "prioritized_recommendations" in synthesis:
            summary["critical_recommendations"] = synthesis["prioritized_recommendations"][:5]
        
        # Calculate risk level
        summary["risk_level"] = self._calculate_risk_level(synthesis)
        
        # Calculate readiness score
        summary["readiness_score"] = self._calculate_readiness_score(synthesis, project_spec)
        
        return summary
    
    async def _generate_roadmap(
        self,
        synthesis: Dict[str, Any],
        project_spec: ProjectSpec
    ) -> List[Dict[str, Any]]:
        """Generate implementation roadmap from synthesis."""
        phases = []
        
        # Phase 1: Foundation
        foundation_items = self._extract_foundation_items(synthesis)
        if foundation_items:
            phases.append({
                "phase": 1,
                "name": "Foundation & Setup",
                "duration": "1-2 weeks",
                "items": foundation_items,
                "dependencies": []
            })
        
        # Phase 2: Core Development
        core_items = self._extract_core_items(synthesis, project_spec)
        if core_items:
            phases.append({
                "phase": 2,
                "name": "Core Development",
                "duration": "4-6 weeks",
                "items": core_items,
                "dependencies": [1] if foundation_items else []
            })
        
        # Phase 3: Integration & Testing
        integration_items = self._extract_integration_items(synthesis)
        if integration_items:
            phases.append({
                "phase": 3,
                "name": "Integration & Testing",
                "duration": "2-3 weeks",
                "items": integration_items,
                "dependencies": [2] if core_items else [1]
            })
        
        # Phase 4: Deployment & Operations
        deployment_items = self._extract_deployment_items(synthesis)
        if deployment_items:
            phases.append({
                "phase": 4,
                "name": "Deployment & Operations",
                "duration": "1-2 weeks",
                "items": deployment_items,
                "dependencies": [3] if integration_items else [2]
            })
        
        return phases
    
    async def _assess_risks(
        self,
        synthesis: Dict[str, Any],
        project_spec: ProjectSpec
    ) -> Dict[str, Any]:
        """Assess risks based on synthesized research."""
        risks = {
            "technical": [],
            "security": [],
            "operational": [],
            "compliance": []
        }
        
        # Analyze findings for risk indicators
        all_findings = []
        if "consensus_findings" in synthesis:
            all_findings.extend(synthesis["consensus_findings"])
        elif "priority_findings" in synthesis:
            for priority_level, items in synthesis["priority_findings"].items():
                all_findings.extend(items)
        
        for finding in all_findings:
            risk_category, risk_item = self._analyze_finding_for_risk(finding)
            if risk_category and risk_item:
                risks[risk_category].append(risk_item)
        
        # Add disagreements as risks
        if "disagreements" in synthesis:
            for disagreement in synthesis["disagreements"]:
                risks["technical"].append({
                    "risk": f"Conflicting recommendations: {disagreement['topic']}",
                    "impact": "medium",
                    "mitigation": "Further analysis needed to resolve conflicts"
                })
        
        # Calculate overall risk score
        risk_score = self._calculate_risk_score(risks)
        
        return {
            "risks": risks,
            "overall_risk_score": risk_score,
            "risk_level": self._get_risk_level(risk_score),
            "mitigation_priority": self._prioritize_risk_mitigation(risks)
        }
    
    def _group_similar_findings(
        self,
        findings: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group similar findings together."""
        groups = defaultdict(list)
        
        for finding in findings:
            # Create a key based on title and category
            title = finding.get("title", "").lower()
            category = self._categorize_finding(finding)
            
            # Simple grouping by title similarity
            key = f"{category}:{self._normalize_text(title)}"
            groups[key].append(finding)
        
        return dict(groups)
    
    def _group_similar_recommendations(
        self,
        recommendations: List[Any]
    ) -> Dict[str, List[Any]]:
        """Group similar recommendations together."""
        groups = defaultdict(list)
        
        for rec in recommendations:
            # Handle both string and dict recommendations
            if isinstance(rec, dict):
                text = rec.get("text", str(rec))
            else:
                text = str(rec)
            
            # Normalize and group
            key = self._normalize_text(text)
            groups[key].append(rec)
        
        return dict(groups)
    
    def _merge_finding_details(
        self,
        findings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge details from multiple similar findings."""
        merged = {
            "description": findings[0].get("description", ""),
            "relevance": max(f.get("relevance", 0.5) for f in findings),
            "sources": list(set(f.get("agent", "unknown") for f in findings))
        }
        
        # Merge additional details
        all_details = {}
        for finding in findings:
            if "details" in finding:
                all_details.update(finding["details"])
        
        if all_details:
            merged["combined_details"] = all_details
        
        return merged
    
    def _calculate_recommendation_priority(
        self,
        recommendations: List[Any]
    ) -> float:
        """Calculate priority score for a recommendation."""
        # More agents recommending = higher priority
        base_priority = len(recommendations) / 5.0  # Normalize by max expected agents
        
        # Look for priority indicators in the text
        priority_keywords = {
            "critical": 1.0,
            "must": 0.9,
            "should": 0.7,
            "consider": 0.5,
            "optional": 0.3
        }
        
        text = str(recommendations[0]).lower()
        keyword_boost = max(
            score for keyword, score in priority_keywords.items()
            if keyword in text
        )
        
        return min(base_priority + keyword_boost * 0.3, 1.0)
    
    def _identify_disagreements(
        self,
        findings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify conflicting findings or recommendations."""
        disagreements = []
        
        # Group by topic
        topic_groups = defaultdict(list)
        for finding in findings:
            topic = self._extract_topic(finding)
            topic_groups[topic].append(finding)
        
        # Look for conflicts within topics
        for topic, group_findings in topic_groups.items():
            if len(group_findings) > 1:
                # Check for conflicting information
                if self._has_conflicts(group_findings):
                    disagreements.append({
                        "topic": topic,
                        "conflicting_views": [
                            {
                                "agent": f.get("agent", "unknown"),
                                "view": f.get("description", "")
                            }
                            for f in group_findings
                        ]
                    })
        
        return disagreements
    
    def _categorize_finding(self, finding: Dict[str, Any]) -> str:
        """Categorize a finding."""
        text = (
            finding.get("title", "") + " " +
            finding.get("description", "")
        ).lower()
        
        for category, keywords in self.category_mappings.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return "general"
    
    def _categorize_recommendation(self, recommendation: Any) -> str:
        """Categorize a recommendation."""
        text = str(recommendation).lower()
        
        for category, keywords in self.category_mappings.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return "general"
    
    def _calculate_finding_priority(
        self,
        finding: Dict[str, Any],
        project_spec: ProjectSpec
    ) -> float:
        """Calculate priority score for a finding."""
        priority = finding.get("relevance", 0.5)
        
        # Boost for severity
        severity = finding.get("severity", "").lower()
        severity_scores = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3
        }
        priority *= severity_scores.get(severity, 0.7)
        
        # Boost for project type match
        if project_spec.type in str(finding).lower():
            priority *= 1.2
        
        return min(priority, 1.0)
    
    def _prioritize_recommendations(
        self,
        recommendations: List[Any],
        project_spec: ProjectSpec
    ) -> List[str]:
        """Prioritize recommendations based on project needs."""
        scored_recs = []
        
        for rec in recommendations:
            text = str(rec)
            score = 0.5  # Base score
            
            # Boost for security recommendations
            if any(kw in text.lower() for kw in ["security", "auth", "encrypt"]):
                score += 0.3
            
            # Boost for performance recommendations
            if any(kw in text.lower() for kw in ["performance", "optimize", "cache"]):
                score += 0.2
            
            # Boost for testing recommendations
            if any(kw in text.lower() for kw in ["test", "coverage", "quality"]):
                score += 0.2
            
            scored_recs.append((text, score))
        
        # Sort by score
        scored_recs.sort(key=lambda x: x[1], reverse=True)
        
        return [rec[0] for rec in scored_recs]
    
    def _extract_key_insights(
        self,
        findings: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract key insights from findings."""
        insights = []
        
        # Sort by relevance
        sorted_findings = sorted(
            findings,
            key=lambda x: x.get("relevance", 0),
            reverse=True
        )
        
        for finding in sorted_findings[:3]:
            insight = finding.get("title", "")
            if finding.get("description"):
                insight += f": {finding['description']}"
            insights.append(insight)
        
        return insights
    
    def _calculate_category_priority(
        self,
        category: str,
        project_spec: ProjectSpec
    ) -> float:
        """Calculate priority for a category."""
        # Base priorities
        category_priorities = {
            "security": 0.9,
            "architecture": 0.8,
            "performance": 0.7,
            "quality": 0.7,
            "deployment": 0.6,
            "development": 0.5,
            "general": 0.3
        }
        
        priority = category_priorities.get(category, 0.5)
        
        # Adjust based on project type
        if project_spec.type == "web_application" and category == "security":
            priority += 0.1
        elif project_spec.type == "api_service" and category == "performance":
            priority += 0.1
        
        return min(priority, 1.0)
    
    def _summarize_high_confidence_items(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Summarize high confidence findings and recommendations."""
        return {
            "count": len(items),
            "top_findings": [
                item["finding"].get("title", "Unknown")
                for item in items
                if "finding" in item
            ][:5],
            "confidence_range": {
                "min": min(item["confidence"] for item in items) if items else 0,
                "max": max(item["confidence"] for item in items) if items else 0,
                "average": sum(item["confidence"] for item in items) / len(items) if items else 0
            }
        }
    
    def _calculate_risk_level(self, synthesis: Dict[str, Any]) -> str:
        """Calculate overall risk level from synthesis."""
        risk_indicators = 0
        
        # Check for critical findings
        if "priority_findings" in synthesis:
            risk_indicators += len(synthesis["priority_findings"].get("critical", []))
        
        # Check for disagreements
        if "disagreements" in synthesis:
            risk_indicators += len(synthesis["disagreements"]) * 0.5
        
        if risk_indicators >= 5:
            return "high"
        elif risk_indicators >= 2:
            return "medium"
        else:
            return "low"
    
    def _calculate_readiness_score(
        self,
        synthesis: Dict[str, Any],
        project_spec: ProjectSpec
    ) -> float:
        """Calculate project readiness score."""
        score = 0.5  # Base score
        
        # Positive indicators
        if "consensus_findings" in synthesis:
            score += min(len(synthesis["consensus_findings"]) * 0.02, 0.2)
        
        if "consensus_recommendations" in synthesis:
            score += min(len(synthesis["consensus_recommendations"]) * 0.01, 0.1)
        
        # Negative indicators
        if "disagreements" in synthesis:
            score -= len(synthesis["disagreements"]) * 0.05
        
        # Confidence boost
        if "metadata" in synthesis:
            score += synthesis["metadata"].get("confidence_score", 0) * 0.2
        
        return max(0.0, min(score, 1.0))
    
    def _extract_foundation_items(self, synthesis: Dict[str, Any]) -> List[str]:
        """Extract foundation/setup items from synthesis."""
        items = []
        keywords = ["setup", "install", "configure", "initialize", "create"]
        
        all_recommendations = []
        if "consensus_recommendations" in synthesis:
            all_recommendations.extend([r["recommendation"] for r in synthesis["consensus_recommendations"]])
        elif "prioritized_recommendations" in synthesis:
            all_recommendations.extend(synthesis["prioritized_recommendations"])
        
        for rec in all_recommendations:
            if any(kw in rec.lower() for kw in keywords):
                items.append(rec)
        
        return items[:5]
    
    def _extract_core_items(
        self,
        synthesis: Dict[str, Any],
        project_spec: ProjectSpec
    ) -> List[str]:
        """Extract core development items from synthesis."""
        items = []
        keywords = ["implement", "develop", "build", "create", "design"]
        
        all_recommendations = []
        if "consensus_recommendations" in synthesis:
            all_recommendations.extend([r["recommendation"] for r in synthesis["consensus_recommendations"]])
        elif "prioritized_recommendations" in synthesis:
            all_recommendations.extend(synthesis["prioritized_recommendations"])
        
        for rec in all_recommendations:
            if any(kw in rec.lower() for kw in keywords):
                items.append(rec)
        
        return items[:8]
    
    def _extract_integration_items(self, synthesis: Dict[str, Any]) -> List[str]:
        """Extract integration and testing items from synthesis."""
        items = []
        keywords = ["test", "integrate", "validate", "verify", "quality"]
        
        all_recommendations = []
        if "consensus_recommendations" in synthesis:
            all_recommendations.extend([r["recommendation"] for r in synthesis["consensus_recommendations"]])
        elif "prioritized_recommendations" in synthesis:
            all_recommendations.extend(synthesis["prioritized_recommendations"])
        
        for rec in all_recommendations:
            if any(kw in rec.lower() for kw in keywords):
                items.append(rec)
        
        return items[:5]
    
    def _extract_deployment_items(self, synthesis: Dict[str, Any]) -> List[str]:
        """Extract deployment items from synthesis."""
        items = []
        keywords = ["deploy", "monitor", "ci/cd", "pipeline", "infrastructure"]
        
        all_recommendations = []
        if "consensus_recommendations" in synthesis:
            all_recommendations.extend([r["recommendation"] for r in synthesis["consensus_recommendations"]])
        elif "prioritized_recommendations" in synthesis:
            all_recommendations.extend(synthesis["prioritized_recommendations"])
        
        for rec in all_recommendations:
            if any(kw in rec.lower() for kw in keywords):
                items.append(rec)
        
        return items[:5]
    
    def _analyze_finding_for_risk(
        self,
        finding: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
        """Analyze a finding for risk indicators."""
        text = str(finding).lower()
        
        # Security risks
        if any(kw in text for kw in ["vulnerability", "insecure", "exposure"]):
            return "security", {
                "risk": finding.get("title", "Security vulnerability"),
                "impact": finding.get("severity", "medium"),
                "mitigation": "Implement security best practices"
            }
        
        # Technical risks
        if any(kw in text for kw in ["incompatible", "deprecated", "legacy"]):
            return "technical", {
                "risk": finding.get("title", "Technical debt"),
                "impact": "medium",
                "mitigation": "Plan for technology updates"
            }
        
        # Operational risks
        if any(kw in text for kw in ["scalability", "performance", "availability"]):
            return "operational", {
                "risk": finding.get("title", "Operational concern"),
                "impact": "medium",
                "mitigation": "Implement monitoring and scaling"
            }
        
        return None, None
    
    def _calculate_risk_score(self, risks: Dict[str, List[Dict[str, str]]]) -> float:
        """Calculate overall risk score."""
        score = 0.0
        
        # Weight different risk categories
        weights = {
            "security": 0.4,
            "technical": 0.3,
            "operational": 0.2,
            "compliance": 0.1
        }
        
        for category, weight in weights.items():
            category_risks = risks.get(category, [])
            if category_risks:
                # Calculate category score based on count and impact
                category_score = len(category_risks) * 0.1
                for risk in category_risks:
                    if risk.get("impact") == "critical":
                        category_score += 0.3
                    elif risk.get("impact") == "high":
                        category_score += 0.2
                    elif risk.get("impact") == "medium":
                        category_score += 0.1
                
                score += min(category_score, 1.0) * weight
        
        return min(score, 1.0)
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Get risk level from score."""
        if risk_score >= 0.7:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _prioritize_risk_mitigation(
        self,
        risks: Dict[str, List[Dict[str, str]]]
    ) -> List[Dict[str, str]]:
        """Prioritize risk mitigation actions."""
        all_risks = []
        
        # Flatten and score all risks
        for category, category_risks in risks.items():
            for risk in category_risks:
                scored_risk = risk.copy()
                scored_risk["category"] = category
                
                # Score based on impact and category
                impact_scores = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.2}
                category_scores = {"security": 1.0, "technical": 0.8, "operational": 0.6, "compliance": 0.7}
                
                score = (
                    impact_scores.get(risk.get("impact", "medium"), 0.4) *
                    category_scores.get(category, 0.5)
                )
                scored_risk["priority_score"] = score
                
                all_risks.append(scored_risk)
        
        # Sort by priority
        all_risks.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return all_risks[:10]  # Top 10 risks
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Simple normalization - could be enhanced
        normalized = text.lower().strip()
        
        # Remove common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        words = normalized.split()
        words = [w for w in words if w not in stop_words]
        
        return " ".join(words)
    
    def _extract_topic(self, finding: Dict[str, Any]) -> str:
        """Extract topic from finding."""
        title = finding.get("title", "")
        
        # Extract main topic (first few words)
        words = title.split()[:3]
        return " ".join(words).lower()
    
    def _has_conflicts(self, findings: List[Dict[str, Any]]) -> bool:
        """Check if findings have conflicting information."""
        # Simple conflict detection - could be enhanced
        descriptions = [f.get("description", "").lower() for f in findings]
        
        # Look for opposite terms
        conflict_pairs = [
            ("recommended", "not recommended"),
            ("use", "avoid"),
            ("enable", "disable"),
            ("required", "optional")
        ]
        
        for desc1 in descriptions:
            for desc2 in descriptions:
                if desc1 != desc2:
                    for pos, neg in conflict_pairs:
                        if pos in desc1 and neg in desc2:
                            return True
        
        return False
    
    def _calculate_overall_confidence(self, results: List[ResearchResult]) -> float:
        """Calculate overall confidence from all results."""
        if not results:
            return 0.0
        
        confidences = [r.confidence for r in results]
        return sum(confidences) / len(confidences)