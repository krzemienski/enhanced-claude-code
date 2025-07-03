"""Base research agent framework."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple
from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from ..models.base import BaseModel
from ..models.research import ResearchQuery, ResearchResult, ResearchSource
from ..models.project import ProjectSpec
from ..exceptions.base import ClaudeCodeBuilderError, ResearchError

logger = logging.getLogger(__name__)


class AgentCapability(Enum):
    """Research agent capabilities."""
    ANALYSIS = "analysis"
    RECOMMENDATION = "recommendation"
    VALIDATION = "validation"
    OPTIMIZATION = "optimization"
    DOCUMENTATION = "documentation"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"


@dataclass
class AgentContext:
    """Context for research agent operations."""
    project_spec: ProjectSpec
    query: ResearchQuery
    previous_results: List[ResearchResult] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_result(self, result: ResearchResult) -> None:
        """Add a research result to context."""
        self.previous_results.append(result)
    
    def get_results_by_source(self, source: ResearchSource) -> List[ResearchResult]:
        """Get results from a specific source."""
        return [r for r in self.previous_results if r.source == source]


@dataclass
class AgentResponse:
    """Response from a research agent."""
    agent_name: str
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    confidence: float  # 0-1
    sources_used: List[ResearchSource]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_research_result(self) -> ResearchResult:
        """Convert to research result."""
        return ResearchResult(
            query_id=self.metadata.get("query_id", ""),
            source=ResearchSource.AI_ANALYSIS,
            content=self.findings,
            confidence_score=self.confidence,
            metadata={
                "agent": self.agent_name,
                "recommendations": self.recommendations,
                "sources": [s.value for s in self.sources_used]
            }
        )


class BaseResearchAgent(ABC):
    """Base class for all research agents."""
    
    def __init__(self, name: str, capabilities: List[AgentCapability]):
        """
        Initialize research agent.
        
        Args:
            name: Agent name
            capabilities: Agent capabilities
        """
        self.name = name
        self.capabilities = set(capabilities)
        self.initialized = False
        self._cache: Dict[str, Any] = {}
    
    async def initialize(self) -> None:
        """Initialize the agent."""
        if self.initialized:
            return
        
        logger.info(f"Initializing {self.name} agent")
        await self._initialize()
        self.initialized = True
    
    @abstractmethod
    async def _initialize(self) -> None:
        """Agent-specific initialization."""
        pass
    
    async def research(self, context: AgentContext) -> AgentResponse:
        """
        Conduct research based on context.
        
        Args:
            context: Research context
            
        Returns:
            Agent response
        """
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"{self.name} starting research for query: {context.query.query}")
        
        try:
            # Check cache
            cache_key = self._generate_cache_key(context)
            if cache_key in self._cache:
                logger.debug(f"{self.name} returning cached response")
                return self._cache[cache_key]
            
            # Perform research
            response = await self._perform_research(context)
            
            # Validate response
            if not self._validate_response(response):
                raise ResearchError(f"Invalid response from {self.name}")
            
            # Cache response
            self._cache[cache_key] = response
            
            return response
            
        except Exception as e:
            logger.error(f"{self.name} research failed: {e}")
            # Return minimal response on error
            return AgentResponse(
                agent_name=self.name,
                findings=[],
                recommendations=[],
                confidence=0.0,
                sources_used=[],
                metadata={"error": str(e)}
            )
    
    @abstractmethod
    async def _perform_research(self, context: AgentContext) -> AgentResponse:
        """
        Perform agent-specific research.
        
        Args:
            context: Research context
            
        Returns:
            Agent response
        """
        pass
    
    def _validate_response(self, response: AgentResponse) -> bool:
        """Validate agent response."""
        return (
            response.agent_name == self.name and
            response.confidence >= 0.0 and
            response.confidence <= 1.0 and
            isinstance(response.findings, list) and
            isinstance(response.recommendations, list)
        )
    
    def _generate_cache_key(self, context: AgentContext) -> str:
        """Generate cache key for context."""
        # Simple cache key based on query and project type
        return f"{self.name}:{context.project_spec.type}:{context.query.query}"
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a capability."""
        return capability in self.capabilities
    
    def clear_cache(self) -> None:
        """Clear agent cache."""
        self._cache.clear()
    
    async def collaborate(
        self,
        other_agent: "BaseResearchAgent",
        context: AgentContext
    ) -> AgentResponse:
        """
        Collaborate with another agent.
        
        Args:
            other_agent: Agent to collaborate with
            context: Research context
            
        Returns:
            Combined response
        """
        # Get responses from both agents
        tasks = [
            self.research(context),
            other_agent.research(context)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Combine responses
        combined_findings = []
        combined_recommendations = []
        combined_sources = set()
        
        for response in responses:
            combined_findings.extend(response.findings)
            combined_recommendations.extend(response.recommendations)
            combined_sources.update(response.sources_used)
        
        # Average confidence
        avg_confidence = sum(r.confidence for r in responses) / len(responses)
        
        return AgentResponse(
            agent_name=f"{self.name} + {other_agent.name}",
            findings=combined_findings,
            recommendations=list(set(combined_recommendations)),  # Deduplicate
            confidence=avg_confidence,
            sources_used=list(combined_sources),
            metadata={
                "collaboration": True,
                "agents": [self.name, other_agent.name]
            }
        )
    
    @abstractmethod
    def get_expertise_areas(self) -> List[str]:
        """Get agent's areas of expertise."""
        pass
    
    @abstractmethod
    def get_research_methods(self) -> List[str]:
        """Get research methods used by agent."""
        pass
    
    def matches_query(self, query: ResearchQuery) -> float:
        """
        Calculate how well agent matches query.
        
        Args:
            query: Research query
            
        Returns:
            Match score (0-1)
        """
        score = 0.0
        
        # Check category match
        if query.category in [cap.value for cap in self.capabilities]:
            score += 0.5
        
        # Check expertise match
        query_lower = query.query.lower()
        expertise_areas = self.get_expertise_areas()
        
        for area in expertise_areas:
            if area.lower() in query_lower:
                score += 0.3
                break
        
        # Check context match
        if query.context:
            context_str = str(query.context).lower()
            for area in expertise_areas:
                if area.lower() in context_str:
                    score += 0.2
                    break
        
        return min(score, 1.0)
    
    async def validate_findings(
        self,
        findings: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate research findings.
        
        Args:
            findings: Findings to validate
            
        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []
        
        for finding in findings:
            # Check required fields
            if "title" not in finding:
                issues.append("Finding missing title")
            if "description" not in finding:
                issues.append("Finding missing description")
            if "relevance" not in finding:
                issues.append("Finding missing relevance score")
            elif not (0 <= finding["relevance"] <= 1):
                issues.append("Invalid relevance score")
        
        return len(issues) == 0, issues
    
    def format_findings(
        self,
        findings: List[Dict[str, Any]]
    ) -> str:
        """Format findings as readable text."""
        if not findings:
            return "No findings available."
        
        formatted = f"=== {self.name} Research Findings ===\n\n"
        
        for i, finding in enumerate(findings, 1):
            formatted += f"{i}. {finding.get('title', 'Untitled')}\n"
            formatted += f"   {finding.get('description', 'No description')}\n"
            
            if "relevance" in finding:
                formatted += f"   Relevance: {finding['relevance']:.2f}\n"
            
            if "source" in finding:
                formatted += f"   Source: {finding['source']}\n"
            
            formatted += "\n"
        
        return formatted
    
    def prioritize_recommendations(
        self,
        recommendations: List[str],
        context: AgentContext
    ) -> List[str]:
        """
        Prioritize recommendations based on context.
        
        Args:
            recommendations: Recommendations to prioritize
            context: Agent context
            
        Returns:
            Prioritized recommendations
        """
        # Simple prioritization based on project type
        priority_keywords = {
            "web_application": ["performance", "security", "scalability", "user experience"],
            "api_service": ["performance", "security", "reliability", "documentation"],
            "cli_tool": ["usability", "performance", "documentation", "testing"],
            "data_pipeline": ["reliability", "performance", "monitoring", "scalability"],
            "automation": ["reliability", "monitoring", "error handling", "logging"]
        }
        
        project_keywords = priority_keywords.get(context.project_spec.type, [])
        
        # Score each recommendation
        scored_recs = []
        for rec in recommendations:
            rec_lower = rec.lower()
            score = sum(1 for keyword in project_keywords if keyword in rec_lower)
            scored_recs.append((score, rec))
        
        # Sort by score (descending)
        scored_recs.sort(key=lambda x: x[0], reverse=True)
        
        return [rec for _, rec in scored_recs]