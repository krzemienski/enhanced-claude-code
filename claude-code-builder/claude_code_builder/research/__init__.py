"""Research Agent System for Claude Code Builder."""

from .base_agent import BaseResearchAgent, AgentCapability, AgentContext, AgentResponse
from .technology_analyst import TechnologyAnalyst
from .security_specialist import SecuritySpecialist
from .performance_engineer import PerformanceEngineer
from .solutions_architect import SolutionsArchitect
from .best_practices_advisor import BestPracticesAdvisor
from .quality_assurance_expert import QualityAssuranceExpert
from .devops_specialist import DevOpsSpecialist
from .coordinator import ResearchCoordinator, AgentAssignment
from .synthesizer import ResearchSynthesizer

__all__ = [
    # Base classes
    "BaseResearchAgent",
    "AgentCapability", 
    "AgentContext",
    "AgentResponse",
    
    # Research agents
    "TechnologyAnalyst",
    "SecuritySpecialist",
    "PerformanceEngineer",
    "SolutionsArchitect",
    "BestPracticesAdvisor",
    "QualityAssuranceExpert",
    "DevOpsSpecialist",
    
    # Coordination
    "ResearchCoordinator",
    "AgentAssignment",
    "ResearchSynthesizer"
]