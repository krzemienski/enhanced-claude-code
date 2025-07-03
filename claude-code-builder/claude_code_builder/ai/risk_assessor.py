"""Risk assessor for AI planning."""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import re

from ..models import ProjectSpec, MemoryStore, MemoryType
from ..config import AIConfig
from ..logging import logger
from ..exceptions import PlanningError


@dataclass
class Risk:
    """Project risk definition."""
    
    id: str
    category: str
    severity: str  # low, medium, high, critical
    probability: str  # unlikely, possible, likely, certain
    title: str
    description: str
    impact: str
    mitigation: str
    
    # Risk metadata
    affected_areas: List[str]
    dependencies: List[str]
    detection_source: str
    confidence: float = 0.8
    
    def get_score(self) -> float:
        """Calculate risk score (0-10)."""
        severity_scores = {
            "low": 1,
            "medium": 3,
            "high": 6,
            "critical": 9
        }
        
        probability_scores = {
            "unlikely": 0.2,
            "possible": 0.5,
            "likely": 0.8,
            "certain": 1.0
        }
        
        severity_val = severity_scores.get(self.severity, 3)
        probability_val = probability_scores.get(self.probability, 0.5)
        
        return severity_val * probability_val


class RiskAssessor:
    """Assesses project risks for planning."""
    
    def __init__(self, ai_config: AIConfig, memory_store: MemoryStore):
        """Initialize risk assessor."""
        self.ai_config = ai_config
        self.memory_store = memory_store
        
        # Risk patterns
        self._init_risk_patterns()
        
        # Risk ID counter
        self.risk_counter = 0
    
    def _init_risk_patterns(self):
        """Initialize risk detection patterns."""
        self.risk_patterns = {
            "technical": {
                "bleeding_edge": {
                    "pattern": r"(experimental|alpha|beta|unstable|preview)",
                    "severity": "high",
                    "probability": "likely",
                    "impact": "Technology may have breaking changes or bugs"
                },
                "legacy_tech": {
                    "pattern": r"(legacy|deprecated|outdated|end.of.life)",
                    "severity": "medium",
                    "probability": "possible",
                    "impact": "Limited support and security vulnerabilities"
                },
                "complex_integration": {
                    "pattern": r"(integrate|connect|sync|federate).*(multiple|several|various)",
                    "severity": "high",
                    "probability": "likely",
                    "impact": "Integration complexity may cause delays"
                }
            },
            "performance": {
                "high_throughput": {
                    "threshold": 10000,  # RPS
                    "severity": "high",
                    "probability": "likely",
                    "impact": "Performance requirements may need specialized architecture"
                },
                "low_latency": {
                    "threshold": 50,  # ms
                    "severity": "high",
                    "probability": "possible",
                    "impact": "Low latency requirements need optimization"
                },
                "high_concurrent_users": {
                    "threshold": 10000,
                    "severity": "medium",
                    "probability": "possible",
                    "impact": "Scalability challenges under high load"
                }
            },
            "security": {
                "compliance": {
                    "keywords": ["gdpr", "hipaa", "pci", "sox", "iso"],
                    "severity": "critical",
                    "probability": "certain",
                    "impact": "Compliance violations can result in penalties"
                },
                "sensitive_data": {
                    "keywords": ["personal", "financial", "medical", "confidential"],
                    "severity": "high",
                    "probability": "likely",
                    "impact": "Data breaches can cause significant damage"
                },
                "public_api": {
                    "keywords": ["public api", "open api", "external api"],
                    "severity": "medium",
                    "probability": "likely",
                    "impact": "Public APIs are targets for attacks"
                }
            },
            "project": {
                "tight_deadline": {
                    "severity": "high",
                    "probability": "possible",
                    "impact": "Rushed development may compromise quality"
                },
                "unclear_requirements": {
                    "keywords": ["tbd", "to be determined", "unclear", "vague"],
                    "severity": "high",
                    "probability": "likely",
                    "impact": "Unclear requirements lead to rework"
                },
                "high_complexity": {
                    "threshold": 7,  # complexity score
                    "severity": "medium",
                    "probability": "possible",
                    "impact": "Complex projects have higher failure rates"
                }
            }
        }
    
    async def assess(
        self,
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Assess project risks."""
        logger.info("Assessing project risks")
        
        try:
            # Check memory for similar risk assessments
            cached_risks = self._check_memory_cache(project_spec)
            if cached_risks:
                logger.info("Using cached risk assessment")
                return cached_risks
            
            risks = []
            
            # Technical risks
            tech_risks = self._assess_technical_risks(project_spec, analysis_results)
            risks.extend(tech_risks)
            
            # Performance risks
            perf_risks = self._assess_performance_risks(project_spec)
            risks.extend(perf_risks)
            
            # Security risks
            sec_risks = self._assess_security_risks(project_spec)
            risks.extend(sec_risks)
            
            # Project management risks
            proj_risks = self._assess_project_risks(project_spec, analysis_results)
            risks.extend(proj_risks)
            
            # Integration risks
            int_risks = self._assess_integration_risks(project_spec, analysis_results)
            risks.extend(int_risks)
            
            # Data risks
            data_risks = self._assess_data_risks(project_spec)
            risks.extend(data_risks)
            
            # Sort by score
            risks.sort(key=lambda r: r.get_score(), reverse=True)
            
            # Store in memory
            self._store_risks(project_spec, risks)
            
            # Convert to dict format
            risk_dicts = [self._risk_to_dict(r) for r in risks]
            
            logger.info(
                f"Identified {len(risks)} risks: "
                f"{sum(1 for r in risks if r.severity == 'critical')} critical, "
                f"{sum(1 for r in risks if r.severity == 'high')} high"
            )
            
            return risk_dicts
            
        except Exception as e:
            logger.error("Risk assessment failed", error=str(e))
            raise PlanningError(f"Failed to assess risks: {str(e)}", cause=e)
    
    def _check_memory_cache(self, project_spec: ProjectSpec) -> Optional[List[Dict[str, Any]]]:
        """Check memory for cached risk assessment."""
        cache_key = f"risk_assessment_{project_spec.metadata.name}_{project_spec.version}"
        
        entry = self.memory_store.get_by_key(cache_key)
        if entry:
            logger.info("Found cached risk assessment")
            return entry.value
        
        return None
    
    def _assess_technical_risks(
        self,
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any]
    ) -> List[Risk]:
        """Assess technical risks."""
        risks = []
        
        # Check for bleeding edge technologies
        for tech in project_spec.technologies:
            tech_text = f"{tech.name} {tech.version or ''}"
            
            if re.search(self.risk_patterns["technical"]["bleeding_edge"]["pattern"], tech_text, re.I):
                risks.append(Risk(
                    id=self._get_risk_id(),
                    category="technical",
                    severity=self.risk_patterns["technical"]["bleeding_edge"]["severity"],
                    probability=self.risk_patterns["technical"]["bleeding_edge"]["probability"],
                    title=f"Bleeding edge technology: {tech.name}",
                    description=f"{tech.name} appears to be experimental or in preview",
                    impact=self.risk_patterns["technical"]["bleeding_edge"]["impact"],
                    mitigation="Plan for potential API changes, have fallback options",
                    affected_areas=[tech.name],
                    dependencies=[],
                    detection_source="technology_analysis"
                ))
        
        # Check technology diversity
        tech_count = len(project_spec.technologies)
        if tech_count > 15:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="technical",
                severity="high",
                probability="likely",
                title="High technology diversity",
                description=f"Project uses {tech_count} different technologies",
                impact="Integration complexity and maintenance overhead",
                mitigation="Standardize technology choices where possible",
                affected_areas=["architecture", "maintenance"],
                dependencies=[],
                detection_source="technology_analysis"
            ))
        
        # Check for incompatible technologies
        incompatible_pairs = [
            ("react", "angular"),
            ("mysql", "postgresql"),  # If using both
            ("redis", "memcached")  # If using both
        ]
        
        tech_names = [t.name.lower() for t in project_spec.technologies]
        for tech1, tech2 in incompatible_pairs:
            if tech1 in tech_names and tech2 in tech_names:
                risks.append(Risk(
                    id=self._get_risk_id(),
                    category="technical",
                    severity="medium",
                    probability="certain",
                    title=f"Potentially incompatible technologies: {tech1} and {tech2}",
                    description=f"Using both {tech1} and {tech2} may cause conflicts",
                    impact="Increased complexity and potential conflicts",
                    mitigation="Choose one technology or ensure clear separation",
                    affected_areas=[tech1, tech2],
                    dependencies=[],
                    detection_source="compatibility_check"
                ))
        
        return risks
    
    def _assess_performance_risks(self, project_spec: ProjectSpec) -> List[Risk]:
        """Assess performance-related risks."""
        risks = []
        perf_req = project_spec.performance_requirements
        
        # High throughput risk
        if perf_req.throughput_rps > self.risk_patterns["performance"]["high_throughput"]["threshold"]:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="performance",
                severity=self.risk_patterns["performance"]["high_throughput"]["severity"],
                probability=self.risk_patterns["performance"]["high_throughput"]["probability"],
                title=f"High throughput requirement: {perf_req.throughput_rps} RPS",
                description="Very high request rate requires specialized architecture",
                impact=self.risk_patterns["performance"]["high_throughput"]["impact"],
                mitigation="Implement caching, load balancing, and horizontal scaling",
                affected_areas=["architecture", "infrastructure"],
                dependencies=[],
                detection_source="performance_requirements"
            ))
        
        # Low latency risk
        if perf_req.response_time_ms < self.risk_patterns["performance"]["low_latency"]["threshold"]:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="performance",
                severity=self.risk_patterns["performance"]["low_latency"]["severity"],
                probability=self.risk_patterns["performance"]["low_latency"]["probability"],
                title=f"Low latency requirement: {perf_req.response_time_ms}ms",
                description="Ultra-low latency requires optimization at all levels",
                impact=self.risk_patterns["performance"]["low_latency"]["impact"],
                mitigation="Use edge computing, optimize algorithms, minimize network hops",
                affected_areas=["architecture", "algorithms", "infrastructure"],
                dependencies=[],
                detection_source="performance_requirements"
            ))
        
        # Concurrent users risk
        if perf_req.concurrent_users > self.risk_patterns["performance"]["high_concurrent_users"]["threshold"]:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="performance",
                severity=self.risk_patterns["performance"]["high_concurrent_users"]["severity"],
                probability=self.risk_patterns["performance"]["high_concurrent_users"]["probability"],
                title=f"High concurrent users: {perf_req.concurrent_users}",
                description="Large number of concurrent users requires scalable architecture",
                impact=self.risk_patterns["performance"]["high_concurrent_users"]["impact"],
                mitigation="Implement auto-scaling, connection pooling, and efficient state management",
                affected_areas=["infrastructure", "database", "sessions"],
                dependencies=[],
                detection_source="performance_requirements"
            ))
        
        return risks
    
    def _assess_security_risks(self, project_spec: ProjectSpec) -> List[Risk]:
        """Assess security-related risks."""
        risks = []
        sec_req = project_spec.security_requirements
        
        # Compliance risks
        if sec_req.compliance_standards:
            for standard in sec_req.compliance_standards:
                if standard.lower() in self.risk_patterns["security"]["compliance"]["keywords"]:
                    risks.append(Risk(
                        id=self._get_risk_id(),
                        category="security",
                        severity=self.risk_patterns["security"]["compliance"]["severity"],
                        probability=self.risk_patterns["security"]["compliance"]["probability"],
                        title=f"Compliance requirement: {standard}",
                        description=f"Must comply with {standard} regulations",
                        impact=self.risk_patterns["security"]["compliance"]["impact"],
                        mitigation="Implement compliance checklist, regular audits, documentation",
                        affected_areas=["data_handling", "security", "documentation"],
                        dependencies=[],
                        detection_source="security_requirements"
                    ))
        
        # Authentication complexity
        if len(sec_req.authentication_methods) > 3:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="security",
                severity="medium",
                probability="likely",
                title="Complex authentication requirements",
                description=f"Supporting {len(sec_req.authentication_methods)} authentication methods",
                impact="Increased attack surface and complexity",
                mitigation="Implement robust authentication framework with proper testing",
                affected_areas=["authentication", "user_management"],
                dependencies=[],
                detection_source="security_requirements"
            ))
        
        # Public API exposure
        if project_spec.api_endpoints and any(not ep.authentication for ep in project_spec.api_endpoints):
            risks.append(Risk(
                id=self._get_risk_id(),
                category="security",
                severity="high",
                probability="certain",
                title="Public API endpoints without authentication",
                description="Some API endpoints do not require authentication",
                impact="Potential for abuse, DDoS attacks, data exposure",
                mitigation="Implement rate limiting, input validation, monitoring",
                affected_areas=["api", "security"],
                dependencies=[],
                detection_source="api_analysis"
            ))
        
        return risks
    
    def _assess_project_risks(
        self,
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any]
    ) -> List[Risk]:
        """Assess project management risks."""
        risks = []
        
        # Complexity risk
        complexity = analysis_results.get("complexity", {}).get("overall", 5)
        if complexity > self.risk_patterns["project"]["high_complexity"]["threshold"]:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="project",
                severity=self.risk_patterns["project"]["high_complexity"]["severity"],
                probability=self.risk_patterns["project"]["high_complexity"]["probability"],
                title=f"High project complexity: {complexity:.1f}/10",
                description="Project has high technical and structural complexity",
                impact=self.risk_patterns["project"]["high_complexity"]["impact"],
                mitigation="Break down into smaller milestones, increase testing coverage",
                affected_areas=["project_management", "quality"],
                dependencies=[],
                detection_source="complexity_analysis"
            ))
        
        # Feature scope risk
        if len(project_spec.features) > 20:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="project",
                severity="high",
                probability="likely",
                title=f"Large feature scope: {len(project_spec.features)} features",
                description="Large number of features increases project risk",
                impact="Scope creep, delayed delivery, quality issues",
                mitigation="Prioritize features, implement MVP first, iterative delivery",
                affected_areas=["scope", "timeline"],
                dependencies=[],
                detection_source="feature_analysis"
            ))
        
        # Unclear requirements
        unclear_count = 0
        for feature in project_spec.features:
            if any(keyword in feature.description.lower() 
                   for keyword in self.risk_patterns["project"]["unclear_requirements"]["keywords"]):
                unclear_count += 1
        
        if unclear_count > 3:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="project",
                severity=self.risk_patterns["project"]["unclear_requirements"]["severity"],
                probability=self.risk_patterns["project"]["unclear_requirements"]["probability"],
                title=f"Unclear requirements in {unclear_count} features",
                description="Multiple features have vague or undefined requirements",
                impact=self.risk_patterns["project"]["unclear_requirements"]["impact"],
                mitigation="Clarify requirements before implementation, prototype unclear features",
                affected_areas=["requirements", "scope"],
                dependencies=[],
                detection_source="requirement_analysis"
            ))
        
        return risks
    
    def _assess_integration_risks(
        self,
        project_spec: ProjectSpec,
        analysis_results: Dict[str, Any]
    ) -> List[Risk]:
        """Assess integration-related risks."""
        risks = []
        
        # External service dependencies
        external_services = [
            t for t in project_spec.technologies 
            if t.category == "service"
        ]
        
        if len(external_services) > 5:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="integration",
                severity="high",
                probability="likely",
                title=f"Multiple external dependencies: {len(external_services)} services",
                description="Many external service dependencies increase failure points",
                impact="Service outages, API changes, rate limits can affect system",
                mitigation="Implement circuit breakers, fallback mechanisms, caching",
                affected_areas=["reliability", "performance"],
                dependencies=[s.name for s in external_services],
                detection_source="dependency_analysis"
            ))
        
        # API versioning risk
        if len(project_spec.api_endpoints) > 30 and not any(
            "version" in ep.path.lower() or "v1" in ep.path.lower() or "v2" in ep.path.lower()
            for ep in project_spec.api_endpoints
        ):
            risks.append(Risk(
                id=self._get_risk_id(),
                category="integration",
                severity="medium",
                probability="likely",
                title="No API versioning detected",
                description="Large API without versioning makes updates difficult",
                impact="Breaking changes affect API consumers",
                mitigation="Implement API versioning strategy from the start",
                affected_areas=["api", "maintenance"],
                dependencies=[],
                detection_source="api_analysis"
            ))
        
        # Real-time integration complexity
        if analysis_results.get("requirements", {}).get("has_realtime", False):
            risks.append(Risk(
                id=self._get_risk_id(),
                category="integration",
                severity="high",
                probability="possible",
                title="Real-time integration complexity",
                description="Real-time features add significant complexity",
                impact="Connection management, state synchronization challenges",
                mitigation="Use proven real-time frameworks, implement reconnection logic",
                affected_areas=["real-time", "state_management"],
                dependencies=[],
                detection_source="feature_analysis"
            ))
        
        return risks
    
    def _assess_data_risks(self, project_spec: ProjectSpec) -> List[Risk]:
        """Assess data-related risks."""
        risks = []
        
        # Multiple databases
        databases = [t for t in project_spec.technologies if t.category == "database"]
        if len(databases) > 2:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="data",
                severity="high",
                probability="likely",
                title=f"Multiple databases: {', '.join(d.name for d in databases)}",
                description="Using multiple databases increases complexity",
                impact="Data consistency, transaction management, operational overhead",
                mitigation="Implement clear data boundaries, consider event sourcing",
                affected_areas=["data_layer", "consistency"],
                dependencies=[d.name for d in databases],
                detection_source="technology_analysis"
            ))
        
        # NoSQL without clear schema
        nosql_dbs = ["mongodb", "dynamodb", "cassandra", "couchdb"]
        if any(db.name.lower() in nosql_dbs for db in databases) and not project_spec.database_schema:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="data",
                severity="medium",
                probability="likely",
                title="NoSQL database without defined schema",
                description="Using NoSQL without clear schema definition",
                impact="Data inconsistency, migration difficulties",
                mitigation="Define and document data models, implement validation",
                affected_areas=["data_modeling", "validation"],
                dependencies=[],
                detection_source="database_analysis"
            ))
        
        # Sensitive data handling
        sensitive_features = [
            f for f in project_spec.features
            if any(keyword in f.description.lower() 
                   for keyword in ["personal", "payment", "medical", "financial"])
        ]
        
        if sensitive_features:
            risks.append(Risk(
                id=self._get_risk_id(),
                category="data",
                severity="critical",
                probability="certain",
                title=f"Sensitive data in {len(sensitive_features)} features",
                description="Handling sensitive user data requires special care",
                impact="Data breaches can result in legal and reputational damage",
                mitigation="Implement encryption, access controls, audit logging, GDPR compliance",
                affected_areas=["security", "compliance", "data_handling"],
                dependencies=[],
                detection_source="feature_analysis",
                confidence=0.95
            ))
        
        return risks
    
    def _get_risk_id(self) -> str:
        """Generate unique risk ID."""
        self.risk_counter += 1
        return f"RISK-{self.risk_counter:03d}"
    
    def _risk_to_dict(self, risk: Risk) -> Dict[str, Any]:
        """Convert Risk to dictionary."""
        return {
            "id": risk.id,
            "category": risk.category,
            "severity": risk.severity,
            "probability": risk.probability,
            "title": risk.title,
            "description": risk.description,
            "impact": risk.impact,
            "mitigation": risk.mitigation,
            "score": risk.get_score(),
            "affected_areas": risk.affected_areas,
            "dependencies": risk.dependencies,
            "detection_source": risk.detection_source,
            "confidence": risk.confidence
        }
    
    def _store_risks(self, project_spec: ProjectSpec, risks: List[Risk]) -> None:
        """Store risk assessment in memory."""
        cache_key = f"risk_assessment_{project_spec.metadata.name}_{project_spec.version}"
        
        risk_dicts = [self._risk_to_dict(r) for r in risks]
        
        self.memory_store.add(
            key=cache_key,
            value=risk_dicts,
            entry_type=MemoryType.RESULT,
            phase="planning",
            tags={"risks", "assessment", project_spec.metadata.name},
            importance=8.0
        )
        
        # Store high-priority risks separately
        high_risks = [r for r in risks if r.severity in ["high", "critical"]]
        if high_risks:
            self.memory_store.add(
                key=f"high_priority_risks_{project_spec.metadata.name}",
                value=[self._risk_to_dict(r) for r in high_risks],
                entry_type=MemoryType.CONTEXT,
                phase="planning",
                tags={"risks", "high_priority"},
                importance=9.0
            )