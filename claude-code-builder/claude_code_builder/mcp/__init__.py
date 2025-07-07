"""MCP System Integration for Claude Code Builder v3.0."""

from .discovery import MCPDiscovery, MCPServer
from .analyzer import MCPAnalyzer, ComplexityAssessment, ServerComplexity, ConfigurationRequirement
from .installer import MCPInstaller, InstallationResult, VerificationResult
from .recommender import MCPRecommender, ServerRecommendation, RecommendationPriority
from .registry import MCPRegistry, RegistryEntry
from .validator import MCPValidator, ValidationResult, ValidationStatus, ValidationCheck
from .config_generator import MCPConfigGenerator, MCPConfiguration

__all__ = [
    # Discovery
    "MCPDiscovery",
    "MCPServer",
    
    # Analysis
    "MCPAnalyzer",
    "ComplexityAssessment",
    "ServerComplexity",
    "ConfigurationRequirement",
    
    # Installation
    "MCPInstaller",
    "InstallationResult",
    "VerificationResult",
    
    # Recommendations
    "MCPRecommender",
    "ServerRecommendation",
    "RecommendationPriority",
    
    # Registry
    "MCPRegistry",
    "RegistryEntry",
    
    # Validation
    "MCPValidator",
    "ValidationResult",
    "ValidationStatus",
    "ValidationCheck",
    
    # Configuration
    "MCPConfigGenerator",
    "MCPConfiguration",
]