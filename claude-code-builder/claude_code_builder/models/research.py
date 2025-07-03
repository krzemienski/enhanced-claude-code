"""Research models for agent-based analysis."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum

from .base import SerializableModel, TimestampedModel, IdentifiedModel
from ..exceptions import ResearchError


class ResearchStatus(Enum):
    """Research query status."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CACHED = "cached"


class ConfidenceLevel(Enum):
    """Confidence level for research results."""
    
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95
    
    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """Get confidence level from numeric score."""
        if score >= 0.95:
            return cls.VERY_HIGH
        elif score >= 0.8:
            return cls.HIGH
        elif score >= 0.6:
            return cls.MEDIUM
        elif score >= 0.4:
            return cls.LOW
        else:
            return cls.VERY_LOW


@dataclass
class ResearchSource:
    """Source of research information."""
    
    name: str
    url: Optional[str] = None
    relevance_score: float = 1.0
    credibility_score: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Source metadata
    source_type: str = "general"
    author: Optional[str] = None
    publication_date: Optional[datetime] = None
    
    def validate(self) -> None:
        """Validate source data."""
        if not 0 <= self.relevance_score <= 1:
            raise ResearchError("Relevance score must be between 0 and 1")
        
        if not 0 <= self.credibility_score <= 1:
            raise ResearchError("Credibility score must be between 0 and 1")


@dataclass
class ResearchFinding:
    """Individual research finding or insight."""
    
    finding: str
    confidence: float
    supporting_evidence: List[str] = field(default_factory=list)
    sources: List[ResearchSource] = field(default_factory=list)
    
    # Finding metadata
    category: str = "general"
    tags: Set[str] = field(default_factory=set)
    implications: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Validate finding data."""
        if not self.finding:
            raise ResearchError("Finding cannot be empty")
        
        if not 0 <= self.confidence <= 1:
            raise ResearchError("Confidence must be between 0 and 1")
        
        for source in self.sources:
            source.validate()
    
    def get_confidence_level(self) -> ConfidenceLevel:
        """Get confidence level enum."""
        return ConfidenceLevel.from_score(self.confidence)
    
    def get_weighted_confidence(self) -> float:
        """Calculate confidence weighted by source credibility."""
        if not self.sources:
            return self.confidence
        
        total_weight = sum(s.credibility_score for s in self.sources)
        if total_weight == 0:
            return self.confidence
        
        weighted_confidence = sum(
            s.credibility_score * self.confidence for s in self.sources
        ) / total_weight
        
        return weighted_confidence


@dataclass
class ResearchQuery(SerializableModel, TimestampedModel, IdentifiedModel):
    """Research query request."""
    
    query: str
    context: str = ""
    
    # Query parameters
    max_results: int = 10
    min_confidence: float = 0.6
    timeout: timedelta = timedelta(minutes=5)
    use_cache: bool = True
    
    # Query scope
    domains: List[str] = field(default_factory=list)
    exclude_domains: List[str] = field(default_factory=list)
    date_range: Optional[tuple[datetime, datetime]] = None
    
    # Agent selection
    required_agents: List[str] = field(default_factory=list)
    optional_agents: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Validate query parameters."""
        if not self.query:
            raise ResearchError("Query cannot be empty")
        
        if not 0 <= self.min_confidence <= 1:
            raise ResearchError("Min confidence must be between 0 and 1")
        
        if self.max_results < 1:
            raise ResearchError("Max results must be at least 1")
        
        if self.date_range:
            start, end = self.date_range
            if start >= end:
                raise ResearchError("Date range start must be before end")


@dataclass
class AgentResponse:
    """Response from a research agent."""
    
    agent_name: str
    agent_type: str
    findings: List[ResearchFinding] = field(default_factory=list)
    
    # Response metadata
    processing_time: Optional[timedelta] = None
    tokens_used: int = 0
    cost: float = 0.0
    
    # Agent assessment
    query_relevance: float = 1.0
    response_quality: float = 1.0
    
    # Additional data
    raw_response: Optional[str] = None
    structured_data: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Validate agent response."""
        if not self.agent_name:
            raise ResearchError("Agent name is required")
        
        if not 0 <= self.query_relevance <= 1:
            raise ResearchError("Query relevance must be between 0 and 1")
        
        if not 0 <= self.response_quality <= 1:
            raise ResearchError("Response quality must be between 0 and 1")
        
        for finding in self.findings:
            finding.validate()
    
    def get_best_findings(self, n: int = 5) -> List[ResearchFinding]:
        """Get top N findings by confidence."""
        sorted_findings = sorted(
            self.findings,
            key=lambda f: f.get_weighted_confidence(),
            reverse=True
        )
        return sorted_findings[:n]


@dataclass
class ResearchResult(SerializableModel, TimestampedModel):
    """Complete research result with synthesis."""
    
    query: ResearchQuery
    status: ResearchStatus = ResearchStatus.PENDING
    
    # Agent responses
    agent_responses: List[AgentResponse] = field(default_factory=list)
    
    # Synthesized results
    synthesis: Optional[str] = None
    key_findings: List[ResearchFinding] = field(default_factory=list)
    consensus_level: float = 0.0
    
    # Execution details
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_cost: float = 0.0
    total_tokens: int = 0
    
    # Error handling
    errors: List[str] = field(default_factory=list)
    partial_results: bool = False
    
    # Caching
    cached: bool = False
    cache_hit: bool = False
    cache_key: Optional[str] = None
    
    def start(self) -> None:
        """Mark research as started."""
        self.status = ResearchStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.update_timestamp()
    
    def complete(self) -> None:
        """Mark research as completed."""
        self.status = ResearchStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self._calculate_totals()
        self.update_timestamp()
    
    def fail(self, error: str) -> None:
        """Mark research as failed."""
        self.status = ResearchStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.errors.append(error)
        self.update_timestamp()
    
    def timeout(self) -> None:
        """Mark research as timed out."""
        self.status = ResearchStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
        self.partial_results = True
        self.update_timestamp()
    
    def add_agent_response(self, response: AgentResponse) -> None:
        """Add agent response to results."""
        response.validate()
        self.agent_responses.append(response)
        self._update_key_findings()
        self._calculate_consensus()
    
    def _calculate_totals(self) -> None:
        """Calculate total cost and tokens."""
        self.total_cost = sum(r.cost for r in self.agent_responses)
        self.total_tokens = sum(r.tokens_used for r in self.agent_responses)
    
    def _update_key_findings(self) -> None:
        """Update key findings from all agents."""
        # Collect all findings
        all_findings = []
        for response in self.agent_responses:
            all_findings.extend(response.findings)
        
        # Sort by weighted confidence
        all_findings.sort(
            key=lambda f: f.get_weighted_confidence(),
            reverse=True
        )
        
        # Take top findings that meet minimum confidence
        self.key_findings = [
            f for f in all_findings
            if f.get_weighted_confidence() >= self.query.min_confidence
        ][:self.query.max_results]
    
    def _calculate_consensus(self) -> None:
        """Calculate consensus level among agents."""
        if len(self.agent_responses) < 2:
            self.consensus_level = 1.0
            return
        
        # Group findings by similarity (simplified)
        finding_groups: Dict[str, List[ResearchFinding]] = {}
        
        for response in self.agent_responses:
            for finding in response.findings:
                # Simple grouping by first 50 chars
                key = finding.finding[:50].lower()
                if key not in finding_groups:
                    finding_groups[key] = []
                finding_groups[key].append(finding)
        
        # Calculate consensus based on agreement
        total_findings = sum(len(r.findings) for r in self.agent_responses)
        agreed_findings = sum(
            len(group) for group in finding_groups.values()
            if len(group) > 1
        )
        
        self.consensus_level = agreed_findings / total_findings if total_findings > 0 else 0
    
    def synthesize(self, synthesis_strategy: str = "weighted_consensus") -> str:
        """Synthesize findings into coherent summary."""
        if not self.agent_responses:
            return "No research findings available."
        
        # Simple synthesis implementation
        sections = []
        
        # Key findings section
        if self.key_findings:
            sections.append("Key Findings:")
            for i, finding in enumerate(self.key_findings[:5], 1):
                confidence = finding.get_confidence_level().name.replace("_", " ").title()
                sections.append(f"{i}. {finding.finding} ({confidence} confidence)")
        
        # Agent consensus section
        sections.append(f"\nAgent Consensus: {self.consensus_level:.1%}")
        
        # Recommendations section
        all_recommendations = []
        for response in self.agent_responses:
            all_recommendations.extend(response.recommendations)
        
        if all_recommendations:
            sections.append("\nRecommendations:")
            for i, rec in enumerate(set(all_recommendations)[:5], 1):
                sections.append(f"{i}. {rec}")
        
        self.synthesis = "\n".join(sections)
        return self.synthesis
    
    def get_duration(self) -> Optional[timedelta]:
        """Get research duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def get_agent_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of agent contributions."""
        summary = {}
        
        for response in self.agent_responses:
            summary[response.agent_name] = {
                "type": response.agent_type,
                "findings_count": len(response.findings),
                "avg_confidence": sum(f.confidence for f in response.findings) / len(response.findings) if response.findings else 0,
                "processing_time": response.processing_time.total_seconds() if response.processing_time else None,
                "cost": response.cost,
                "quality": response.response_quality
            }
        
        return summary
    
    def to_report(self) -> str:
        """Generate human-readable research report."""
        lines = [
            f"Research Report: {self.query.query}",
            "=" * 60,
            f"Status: {self.status.value}",
            f"Agents Used: {len(self.agent_responses)}",
            f"Total Cost: ${self.total_cost:.4f}",
            f"Consensus Level: {self.consensus_level:.1%}",
            ""
        ]
        
        if self.synthesis:
            lines.extend([
                "Executive Summary:",
                "-" * 40,
                self.synthesis,
                ""
            ])
        
        # Agent details
        lines.append("Agent Contributions:")
        lines.append("-" * 40)
        
        for response in self.agent_responses:
            lines.extend([
                f"\n{response.agent_name} ({response.agent_type}):",
                f"  Findings: {len(response.findings)}",
                f"  Quality: {response.response_quality:.1%}",
                f"  Cost: ${response.cost:.4f}"
            ])
            
            # Top findings from this agent
            top_findings = response.get_best_findings(3)
            if top_findings:
                lines.append("  Top Findings:")
                for finding in top_findings:
                    lines.append(f"    - {finding.finding[:100]}...")
        
        if self.errors:
            lines.extend([
                "",
                "Errors:",
                "-" * 40
            ])
            for error in self.errors:
                lines.append(f"  - {error}")
        
        return "\n".join(lines)
    
    def validate(self) -> None:
        """Validate research result."""
        self.query.validate()
        
        for response in self.agent_responses:
            response.validate()
        
        if not 0 <= self.consensus_level <= 1:
            raise ResearchError("Consensus level must be between 0 and 1")