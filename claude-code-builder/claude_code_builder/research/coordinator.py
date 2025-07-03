"""Research Coordinator - orchestrates research agents."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass

from .base_agent import BaseResearchAgent, AgentContext, AgentResponse, AgentCapability
from .technology_analyst import TechnologyAnalyst
from .security_specialist import SecuritySpecialist
from .performance_engineer import PerformanceEngineer
from .solutions_architect import SolutionsArchitect
from .best_practices_advisor import BestPracticesAdvisor
from .quality_assurance_expert import QualityAssuranceExpert
from .devops_specialist import DevOpsSpecialist
from ..models.research import ResearchQuery, ResearchResult, ResearchSource

logger = logging.getLogger(__name__)


@dataclass
class AgentAssignment:
    """Assignment of agents to research tasks."""
    agent_name: str
    relevance_score: float
    capabilities: List[AgentCapability]
    reason: str


class ResearchCoordinator:
    """Coordinates multiple research agents for comprehensive analysis."""
    
    def __init__(self):
        """Initialize Research Coordinator."""
        self.agents = self._initialize_agents()
        self.capability_map = self._build_capability_map()
        
    def _initialize_agents(self) -> Dict[str, BaseResearchAgent]:
        """Initialize all research agents."""
        return {
            "technology_analyst": TechnologyAnalyst(),
            "security_specialist": SecuritySpecialist(),
            "performance_engineer": PerformanceEngineer(),
            "solutions_architect": SolutionsArchitect(),
            "best_practices_advisor": BestPracticesAdvisor(),
            "quality_assurance_expert": QualityAssuranceExpert(),
            "devops_specialist": DevOpsSpecialist()
        }
    
    def _build_capability_map(self) -> Dict[AgentCapability, List[str]]:
        """Build mapping of capabilities to agents."""
        capability_map = {}
        
        for agent_name, agent in self.agents.items():
            for capability in agent.capabilities:
                if capability not in capability_map:
                    capability_map[capability] = []
                capability_map[capability].append(agent_name)
        
        return capability_map
    
    async def coordinate_research(
        self,
        query: ResearchQuery,
        context: AgentContext,
        max_agents: int = 5,
        parallel: bool = True
    ) -> ResearchResult:
        """Coordinate research across multiple agents."""
        logger.info(f"Coordinating research for: {query.query}")
        
        # Select appropriate agents
        selected_agents = await self._select_agents(query, context, max_agents)
        
        logger.info(f"Selected {len(selected_agents)} agents for research")
        
        # Execute research
        if parallel:
            responses = await self._execute_parallel_research(
                selected_agents, context
            )
        else:
            responses = await self._execute_sequential_research(
                selected_agents, context
            )
        
        # Synthesize results
        result = await self._synthesize_results(query, responses)
        
        return result
    
    async def _select_agents(
        self,
        query: ResearchQuery,
        context: AgentContext,
        max_agents: int
    ) -> List[AgentAssignment]:
        """Select appropriate agents for the research query."""
        assignments = []
        
        # Analyze query to determine needed capabilities
        needed_capabilities = self._analyze_query_capabilities(query)
        
        # Score each agent
        agent_scores = {}
        
        for agent_name, agent in self.agents.items():
            score = self._score_agent(agent, query, context, needed_capabilities)
            if score > 0:
                agent_scores[agent_name] = AgentAssignment(
                    agent_name=agent_name,
                    relevance_score=score,
                    capabilities=agent.capabilities,
                    reason=self._get_selection_reason(agent, query)
                )
        
        # Sort by relevance and select top agents
        sorted_assignments = sorted(
            agent_scores.values(),
            key=lambda x: x.relevance_score,
            reverse=True
        )
        
        return sorted_assignments[:max_agents]
    
    def _analyze_query_capabilities(self, query: ResearchQuery) -> Set[AgentCapability]:
        """Analyze query to determine needed capabilities."""
        capabilities = set()
        query_lower = query.query.lower()
        
        # Map keywords to capabilities
        capability_keywords = {
            AgentCapability.ARCHITECTURE: [
                "architecture", "design", "structure", "pattern", "component"
            ],
            AgentCapability.SECURITY: [
                "security", "auth", "encryption", "vulnerability", "secure"
            ],
            AgentCapability.PERFORMANCE: [
                "performance", "speed", "optimize", "scale", "latency"
            ],
            AgentCapability.TESTING: [
                "test", "quality", "qa", "coverage", "validation"
            ],
            AgentCapability.DEPLOYMENT: [
                "deploy", "ci/cd", "devops", "infrastructure", "container"
            ],
            AgentCapability.ANALYSIS: [
                "analyze", "assess", "evaluate", "review", "examine"
            ],
            AgentCapability.RECOMMENDATION: [
                "recommend", "suggest", "best", "should", "advice"
            ]
        }
        
        for capability, keywords in capability_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                capabilities.add(capability)
        
        # Default capabilities if none detected
        if not capabilities:
            capabilities.update([
                AgentCapability.ANALYSIS,
                AgentCapability.RECOMMENDATION
            ])
        
        return capabilities
    
    def _score_agent(
        self,
        agent: BaseResearchAgent,
        query: ResearchQuery,
        context: AgentContext,
        needed_capabilities: Set[AgentCapability]
    ) -> float:
        """Score an agent's relevance to the query."""
        score = 0.0
        
        # Capability match (40% weight)
        capability_overlap = len(
            set(agent.capabilities).intersection(needed_capabilities)
        )
        capability_score = capability_overlap / len(needed_capabilities) if needed_capabilities else 0
        score += capability_score * 0.4
        
        # Expertise area match (30% weight)
        expertise_score = self._score_expertise_match(agent, query, context)
        score += expertise_score * 0.3
        
        # Context relevance (20% weight)
        context_score = self._score_context_relevance(agent, context)
        score += context_score * 0.2
        
        # Query specificity (10% weight)
        specificity_score = self._score_query_specificity(agent, query)
        score += specificity_score * 0.1
        
        return score
    
    def _score_expertise_match(
        self,
        agent: BaseResearchAgent,
        query: ResearchQuery,
        context: AgentContext
    ) -> float:
        """Score how well agent expertise matches the query."""
        query_lower = query.query.lower()
        expertise_areas = agent.get_expertise_areas()
        
        matches = sum(
            1 for area in expertise_areas
            if area.lower() in query_lower or 
            any(word in query_lower for word in area.lower().split())
        )
        
        return min(matches / 3, 1.0)  # Normalize to max 1.0
    
    def _score_context_relevance(
        self,
        agent: BaseResearchAgent,
        context: AgentContext
    ) -> float:
        """Score agent relevance to project context."""
        relevance = 0.0
        
        # Project type relevance
        type_relevance = {
            "TechnologyAnalyst": ["web_application", "api_service", "cli_tool"],
            "SecuritySpecialist": ["web_application", "api_service"],
            "PerformanceEngineer": ["web_application", "api_service", "data_pipeline"],
            "SolutionsArchitect": ["all"],
            "BestPracticesAdvisor": ["all"],
            "QualityAssuranceExpert": ["all"],
            "DevOpsSpecialist": ["web_application", "api_service", "microservices"]
        }
        
        agent_type = type(agent).__name__
        if agent_type in type_relevance:
            relevant_types = type_relevance[agent_type]
            if "all" in relevant_types or context.project_spec.type in relevant_types:
                relevance += 0.5
        
        # Technology stack relevance
        if hasattr(agent, "tech_ecosystems"):
            tech_matches = sum(
                1 for tech in context.project_spec.technologies
                if any(eco in tech.name.lower() for eco in agent.tech_ecosystems.keys())
            )
            relevance += min(tech_matches * 0.1, 0.5)
        
        return relevance
    
    def _score_query_specificity(
        self,
        agent: BaseResearchAgent,
        query: ResearchQuery
    ) -> float:
        """Score how specifically the query targets this agent."""
        query_lower = query.query.lower()
        agent_keywords = {
            "TechnologyAnalyst": ["technology", "tech", "stack", "framework"],
            "SecuritySpecialist": ["security", "secure", "vulnerability", "auth"],
            "PerformanceEngineer": ["performance", "speed", "optimize", "scale"],
            "SolutionsArchitect": ["architecture", "design", "structure"],
            "BestPracticesAdvisor": ["best practice", "standard", "convention"],
            "QualityAssuranceExpert": ["test", "quality", "qa", "coverage"],
            "DevOpsSpecialist": ["devops", "deploy", "ci/cd", "infrastructure"]
        }
        
        agent_type = type(agent).__name__
        if agent_type in agent_keywords:
            keywords = agent_keywords[agent_type]
            if any(keyword in query_lower for keyword in keywords):
                return 1.0
        
        return 0.0
    
    def _get_selection_reason(
        self,
        agent: BaseResearchAgent,
        query: ResearchQuery
    ) -> str:
        """Get reason for selecting an agent."""
        agent_type = type(agent).__name__
        
        reasons = {
            "TechnologyAnalyst": "Technology stack analysis and recommendations",
            "SecuritySpecialist": "Security assessment and vulnerability analysis",
            "PerformanceEngineer": "Performance optimization and scalability",
            "SolutionsArchitect": "System architecture and design patterns",
            "BestPracticesAdvisor": "Coding standards and best practices",
            "QualityAssuranceExpert": "Testing strategy and quality assurance",
            "DevOpsSpecialist": "Deployment and infrastructure planning"
        }
        
        return reasons.get(agent_type, "General analysis and recommendations")
    
    async def _execute_parallel_research(
        self,
        assignments: List[AgentAssignment],
        context: AgentContext
    ) -> Dict[str, AgentResponse]:
        """Execute research in parallel across selected agents."""
        tasks = []
        
        for assignment in assignments:
            agent = self.agents[assignment.agent_name]
            task = asyncio.create_task(
                self._execute_agent_research(agent, context, assignment)
            )
            tasks.append((assignment.agent_name, task))
        
        # Wait for all tasks to complete
        responses = {}
        for agent_name, task in tasks:
            try:
                response = await task
                responses[agent_name] = response
            except Exception as e:
                logger.error(f"Error in {agent_name} research: {e}")
                # Continue with other agents
        
        return responses
    
    async def _execute_sequential_research(
        self,
        assignments: List[AgentAssignment],
        context: AgentContext
    ) -> Dict[str, AgentResponse]:
        """Execute research sequentially across selected agents."""
        responses = {}
        
        for assignment in assignments:
            agent = self.agents[assignment.agent_name]
            try:
                response = await self._execute_agent_research(
                    agent, context, assignment
                )
                responses[assignment.agent_name] = response
                
                # Update context with findings for next agent
                context = self._update_context_with_findings(context, response)
                
            except Exception as e:
                logger.error(f"Error in {assignment.agent_name} research: {e}")
                # Continue with other agents
        
        return responses
    
    async def _execute_agent_research(
        self,
        agent: BaseResearchAgent,
        context: AgentContext,
        assignment: AgentAssignment
    ) -> AgentResponse:
        """Execute research for a single agent."""
        logger.info(
            f"Executing {agent.name} research "
            f"(relevance: {assignment.relevance_score:.2f})"
        )
        
        # Initialize agent if needed
        if not agent._initialized:
            await agent.initialize()
        
        # Perform research
        response = await agent.research(context)
        
        logger.info(
            f"{agent.name} completed with {len(response.findings)} findings "
            f"and {len(response.recommendations)} recommendations"
        )
        
        return response
    
    def _update_context_with_findings(
        self,
        context: AgentContext,
        response: AgentResponse
    ) -> AgentContext:
        """Update context with findings from previous agent."""
        # Create new context with additional information
        # This allows later agents to build on previous findings
        
        # Add high-relevance findings to context metadata
        important_findings = [
            f for f in response.findings
            if f.get("relevance", 0) >= 0.8
        ]
        
        if important_findings:
            if "research_findings" not in context.metadata:
                context.metadata["research_findings"] = []
            
            context.metadata["research_findings"].extend([
                {
                    "agent": response.agent_name,
                    "title": f.get("title"),
                    "description": f.get("description")
                }
                for f in important_findings
            ])
        
        return context
    
    async def _synthesize_results(
        self,
        query: ResearchQuery,
        responses: Dict[str, AgentResponse]
    ) -> ResearchResult:
        """Synthesize results from multiple agents."""
        all_findings = []
        all_recommendations = []
        sources_used = set()
        
        # Aggregate findings and recommendations
        for agent_name, response in responses.items():
            # Add agent attribution to findings
            for finding in response.findings:
                finding["agent"] = response.agent_name
                all_findings.append(finding)
            
            # Add agent attribution to recommendations
            for rec in response.recommendations:
                rec_dict = rec if isinstance(rec, dict) else {"text": rec}
                rec_dict["agent"] = response.agent_name
                all_recommendations.append(rec_dict)
            
            # Collect sources
            sources_used.update(response.sources_used)
        
        # Sort findings by relevance
        all_findings.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        # Deduplicate recommendations
        unique_recommendations = self._deduplicate_recommendations(all_recommendations)
        
        # Calculate overall confidence
        confidence_scores = [r.confidence for r in responses.values()]
        overall_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores else 0.5
        )
        
        # Create research result
        result = ResearchResult(
            query=query.query,
            findings=all_findings[:20],  # Top 20 findings
            recommendations=unique_recommendations[:15],  # Top 15 recommendations
            confidence=overall_confidence,
            sources=list(sources_used),
            metadata={
                "agents_used": list(responses.keys()),
                "total_findings": len(all_findings),
                "total_recommendations": len(all_recommendations),
                "synthesis_timestamp": datetime.now().isoformat()
            }
        )
        
        return result
    
    def _deduplicate_recommendations(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[str]:
        """Deduplicate and prioritize recommendations."""
        # Group similar recommendations
        unique_recs = {}
        
        for rec in recommendations:
            text = rec.get("text", str(rec))
            
            # Simple deduplication by lowercase comparison
            key = text.lower().strip()
            
            if key not in unique_recs:
                unique_recs[key] = {
                    "text": text,
                    "agents": [rec.get("agent", "unknown")],
                    "count": 1
                }
            else:
                unique_recs[key]["agents"].append(rec.get("agent", "unknown"))
                unique_recs[key]["count"] += 1
        
        # Sort by count (more agents recommending = higher priority)
        sorted_recs = sorted(
            unique_recs.values(),
            key=lambda x: x["count"],
            reverse=True
        )
        
        # Format recommendations with agent attribution
        formatted_recs = []
        for rec in sorted_recs:
            if rec["count"] > 1:
                agents_str = ", ".join(set(rec["agents"]))
                formatted_recs.append(
                    f"{rec['text']} (recommended by: {agents_str})"
                )
            else:
                formatted_recs.append(rec["text"])
        
        return formatted_recs
    
    async def get_agent_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all agents."""
        capabilities = {}
        
        for agent_name, agent in self.agents.items():
            capabilities[agent_name] = {
                "capabilities": [cap.value for cap in agent.capabilities],
                "expertise": agent.get_expertise_areas(),
                "methods": agent.get_research_methods()
            }
        
        return capabilities
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all agents."""
        health_status = {}
        
        for agent_name, agent in self.agents.items():
            try:
                # Try to initialize agent
                if not agent._initialized:
                    await agent.initialize()
                health_status[agent_name] = True
            except Exception as e:
                logger.error(f"Health check failed for {agent_name}: {e}")
                health_status[agent_name] = False
        
        return health_status