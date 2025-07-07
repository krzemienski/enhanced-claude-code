"""Security Specialist research agent."""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from .base_agent import BaseResearchAgent, AgentCapability, AgentContext, AgentResponse
from ..models.research import ResearchSource
from ..models.project import Feature

logger = logging.getLogger(__name__)


class SecuritySpecialist(BaseResearchAgent):
    """Specializes in security analysis and recommendations."""
    
    def __init__(self):
        """Initialize Security Specialist agent."""
        super().__init__(
            name="Security Specialist",
            capabilities=[
                AgentCapability.SECURITY,
                AgentCapability.ANALYSIS,
                AgentCapability.VALIDATION,
                AgentCapability.RECOMMENDATION
            ]
        )
        
        # Security knowledge base
        self.owasp_top_10 = {
            "A01": {
                "name": "Broken Access Control",
                "mitigations": [
                    "Implement proper access control checks",
                    "Use least privilege principle",
                    "Validate permissions server-side",
                    "Log access control failures"
                ]
            },
            "A02": {
                "name": "Cryptographic Failures",
                "mitigations": [
                    "Use strong encryption algorithms",
                    "Properly manage encryption keys",
                    "Use HTTPS everywhere",
                    "Hash passwords with bcrypt/scrypt/argon2"
                ]
            },
            "A03": {
                "name": "Injection",
                "mitigations": [
                    "Use parameterized queries",
                    "Validate all input",
                    "Escape special characters",
                    "Use ORMs properly"
                ]
            },
            "A04": {
                "name": "Insecure Design",
                "mitigations": [
                    "Threat modeling",
                    "Secure design patterns",
                    "Security requirements analysis",
                    "Defense in depth"
                ]
            },
            "A05": {
                "name": "Security Misconfiguration",
                "mitigations": [
                    "Secure default configurations",
                    "Remove unnecessary features",
                    "Regular security updates",
                    "Security headers configuration"
                ]
            }
        }
        
        self.security_headers = {
            "Content-Security-Policy": "Prevent XSS attacks",
            "X-Frame-Options": "Prevent clickjacking",
            "X-Content-Type-Options": "Prevent MIME sniffing",
            "Strict-Transport-Security": "Force HTTPS",
            "X-XSS-Protection": "Enable XSS filter",
            "Referrer-Policy": "Control referrer information"
        }
        
        self.auth_methods = {
            "jwt": {
                "pros": ["Stateless", "Scalable", "Mobile-friendly"],
                "cons": ["Token size", "No built-in revocation"],
                "best_for": ["APIs", "Microservices", "Mobile apps"]
            },
            "oauth2": {
                "pros": ["Industry standard", "Third-party integration", "Granular permissions"],
                "cons": ["Complex implementation", "Multiple flows"],
                "best_for": ["Third-party integrations", "Social login"]
            },
            "session": {
                "pros": ["Simple", "Server control", "Easy revocation"],
                "cons": ["Stateful", "Scaling challenges"],
                "best_for": ["Traditional web apps", "Simple applications"]
            }
        }
    
    async def _initialize(self) -> None:
        """Initialize the Security Specialist."""
        logger.info("Security Specialist initialized with OWASP knowledge base")
    
    async def _perform_research(self, context: AgentContext) -> AgentResponse:
        """Perform security analysis research."""
        findings = []
        recommendations = []
        
        # Perform security assessment
        security_assessment = await self._assess_security_requirements(context)
        findings.extend(security_assessment["findings"])
        recommendations.extend(security_assessment["recommendations"])
        
        # Analyze authentication needs
        auth_analysis = await self._analyze_authentication(context)
        findings.extend(auth_analysis["findings"])
        recommendations.extend(auth_analysis["recommendations"])
        
        # Check for common vulnerabilities
        vuln_check = await self._check_vulnerabilities(context)
        findings.extend(vuln_check["findings"])
        recommendations.extend(vuln_check["recommendations"])
        
        # Data protection analysis
        data_protection = await self._analyze_data_protection(context)
        findings.extend(data_protection["findings"])
        recommendations.extend(data_protection["recommendations"])
        
        # Infrastructure security
        infra_security = await self._analyze_infrastructure_security(context)
        findings.extend(infra_security["findings"])
        recommendations.extend(infra_security["recommendations"])
        
        # Calculate confidence
        confidence = self._calculate_confidence(context, findings)
        
        return AgentResponse(
            agent_name=self.name,
            findings=findings,
            recommendations=self.prioritize_recommendations(recommendations, context),
            confidence=confidence,
            sources_used=[ResearchSource.DOCUMENTATION, ResearchSource.COMMUNITY],
            metadata={
                "owasp_coverage": self._calculate_owasp_coverage(findings),
                "critical_issues": len([f for f in findings if f.get("severity") == "critical"])
            }
        )
    
    async def _assess_security_requirements(self, context: AgentContext) -> Dict[str, Any]:
        """Assess security requirements based on project type."""
        findings = []
        recommendations = []
        
        # Base security requirements by project type
        security_levels = {
            "web_application": {
                "level": "high",
                "focus": ["Authentication", "Authorization", "XSS", "CSRF", "SQL Injection"],
                "requirements": [
                    "User authentication system",
                    "Role-based access control",
                    "Input validation",
                    "Security headers",
                    "HTTPS enforcement"
                ]
            },
            "api_service": {
                "level": "high",
                "focus": ["Authentication", "Authorization", "Rate limiting", "Input validation"],
                "requirements": [
                    "API authentication (JWT/OAuth)",
                    "Rate limiting",
                    "Input validation",
                    "API versioning",
                    "Audit logging"
                ]
            },
            "cli_tool": {
                "level": "medium",
                "focus": ["Secure storage", "Update mechanism", "Code signing"],
                "requirements": [
                    "Secure credential storage",
                    "Secure update mechanism",
                    "Input validation"
                ]
            },
            "data_pipeline": {
                "level": "high",
                "focus": ["Data encryption", "Access control", "Audit logging"],
                "requirements": [
                    "Encryption at rest",
                    "Encryption in transit",
                    "Access control",
                    "Data masking",
                    "Audit trails"
                ]
            }
        }
        
        project_type = context.project_spec.type
        if project_type in security_levels:
            security_info = security_levels[project_type]
            
            findings.append({
                "title": "Security Level Assessment",
                "description": f"Project requires {security_info['level']} security level",
                "relevance": 1.0,
                "security_level": security_info["level"],
                "focus_areas": security_info["focus"]
            })
            
            # Check which requirements are addressed
            features = {f.name.lower() for f in context.project_spec.features}
            for req in security_info["requirements"]:
                if not self._is_requirement_addressed(req, features):
                    findings.append({
                        "title": f"Missing Security Requirement: {req}",
                        "description": f"Security requirement '{req}' not explicitly addressed",
                        "relevance": 0.8,
                        "severity": "high"
                    })
                    recommendations.append(f"Implement {req}")
        
        # Check for sensitive data handling
        if self._handles_sensitive_data(context):
            findings.append({
                "title": "Sensitive Data Handling Detected",
                "description": "Project will handle sensitive user data",
                "relevance": 1.0,
                "severity": "critical"
            })
            
            recommendations.extend([
                "Implement data encryption at rest and in transit",
                "Follow data protection regulations (GDPR, CCPA)",
                "Implement proper data retention policies",
                "Use secure data storage mechanisms"
            ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_authentication(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze authentication requirements."""
        findings = []
        recommendations = []
        
        # Check if authentication is needed
        needs_auth = any(
            keyword in str(context.project_spec.features).lower()
            for keyword in ["user", "auth", "login", "account", "admin"]
        )
        
        if needs_auth:
            findings.append({
                "title": "Authentication Required",
                "description": "Project requires user authentication system",
                "relevance": 1.0,
                "requirement": "authentication"
            })
            
            # Recommend authentication method based on project type
            if context.project_spec.type == "api_service":
                auth_method = "jwt"
                findings.append({
                    "title": "Recommended Authentication: JWT",
                    "description": "JWT tokens recommended for API authentication",
                    "relevance": 0.9,
                    "details": self.auth_methods["jwt"]
                })
                
                recommendations.extend([
                    "Implement JWT-based authentication",
                    "Use refresh tokens for better security",
                    "Implement token expiration and rotation",
                    "Store tokens securely on client side"
                ])
                
            elif context.project_spec.type == "web_application":
                # Check if it's a SPA or traditional app
                is_spa = any(
                    tech.name.lower() in ["react", "vue", "angular"]
                    for tech in context.project_spec.technologies
                )
                
                if is_spa:
                    auth_method = "jwt"
                    recommendations.append("Use JWT with HttpOnly cookies for SPA authentication")
                else:
                    auth_method = "session"
                    recommendations.append("Use secure session-based authentication")
            
            # Multi-factor authentication
            if context.project_spec.metadata.get("high_security", False):
                findings.append({
                    "title": "Multi-Factor Authentication Recommended",
                    "description": "High security project should implement MFA",
                    "relevance": 0.9,
                    "severity": "high"
                })
                recommendations.append("Implement multi-factor authentication (TOTP/SMS/Email)")
        
        # Password requirements
        if needs_auth:
            recommendations.extend([
                "Implement strong password requirements",
                "Use bcrypt/scrypt/argon2 for password hashing",
                "Implement account lockout after failed attempts",
                "Add password reset functionality with secure tokens"
            ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _check_vulnerabilities(self, context: AgentContext) -> Dict[str, Any]:
        """Check for common vulnerabilities based on OWASP Top 10."""
        findings = []
        recommendations = []
        
        # Check each OWASP category
        for code, vuln_info in self.owasp_top_10.items():
            risk_level = self._assess_vulnerability_risk(vuln_info["name"], context)
            
            if risk_level > 0:
                findings.append({
                    "title": f"OWASP {code}: {vuln_info['name']}",
                    "description": f"Potential risk of {vuln_info['name']}",
                    "relevance": risk_level,
                    "severity": "high" if risk_level > 0.7 else "medium",
                    "owasp_category": code
                })
                
                # Add specific mitigations
                for mitigation in vuln_info["mitigations"]:
                    recommendations.append(f"{code}: {mitigation}")
        
        # Technology-specific vulnerabilities
        tech_vulns = await self._check_technology_vulnerabilities(context)
        findings.extend(tech_vulns["findings"])
        recommendations.extend(tech_vulns["recommendations"])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_data_protection(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze data protection requirements."""
        findings = []
        recommendations = []
        
        # Check for database usage
        uses_database = any(
            "database" in feature.name.lower() or "data" in feature.name.lower()
            for feature in context.project_spec.features
        )
        
        if uses_database:
            findings.append({
                "title": "Database Security Required",
                "description": "Project uses database, requiring data protection measures",
                "relevance": 0.9,
                "area": "data_protection"
            })
            
            recommendations.extend([
                "Encrypt sensitive data at rest",
                "Use encrypted connections to database",
                "Implement database access controls",
                "Regular database backups with encryption",
                "Implement data masking for sensitive fields"
            ])
        
        # Check for file uploads
        if any("upload" in f.name.lower() for f in context.project_spec.features):
            findings.append({
                "title": "File Upload Security",
                "description": "File upload functionality requires security measures",
                "relevance": 0.8,
                "severity": "high"
            })
            
            recommendations.extend([
                "Validate file types and sizes",
                "Scan uploaded files for malware",
                "Store uploads outside web root",
                "Generate unique filenames",
                "Implement access controls for uploaded files"
            ])
        
        # PII handling
        if self._handles_pii(context):
            findings.append({
                "title": "PII Data Handling",
                "description": "Project handles Personally Identifiable Information",
                "relevance": 1.0,
                "severity": "critical",
                "compliance": ["GDPR", "CCPA"]
            })
            
            recommendations.extend([
                "Implement data minimization principles",
                "Add data retention and deletion policies",
                "Implement user data export functionality",
                "Add consent management",
                "Log all PII access"
            ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_infrastructure_security(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze infrastructure security needs."""
        findings = []
        recommendations = []
        
        # Container security
        if any(tech.name.lower() in ["docker", "kubernetes"] for tech in context.project_spec.technologies):
            findings.append({
                "title": "Container Security",
                "description": "Containerized deployment requires additional security measures",
                "relevance": 0.8,
                "area": "infrastructure"
            })
            
            recommendations.extend([
                "Use minimal base images",
                "Scan images for vulnerabilities",
                "Don't run containers as root",
                "Use secrets management for sensitive data",
                "Implement network policies"
            ])
        
        # API security
        if context.project_spec.type == "api_service":
            findings.append({
                "title": "API Security Requirements",
                "description": "API services need specific security measures",
                "relevance": 0.9,
                "area": "api_security"
            })
            
            recommendations.extend([
                "Implement rate limiting",
                "Use API versioning",
                "Add request/response validation",
                "Implement CORS properly",
                "Use API keys or OAuth for authentication",
                "Log all API access"
            ])
        
        # Web application security
        if context.project_spec.type == "web_application":
            findings.append({
                "title": "Web Security Headers",
                "description": "Web applications need security headers",
                "relevance": 0.8,
                "area": "web_security"
            })
            
            # Add security headers recommendations
            for header, purpose in self.security_headers.items():
                recommendations.append(f"Implement {header} header: {purpose}")
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    def _is_requirement_addressed(self, requirement: str, features: Set[str]) -> bool:
        """Check if a security requirement is addressed by features."""
        requirement_keywords = {
            "authentication": ["auth", "login", "user", "account"],
            "authorization": ["role", "permission", "access"],
            "encryption": ["encrypt", "secure", "crypto"],
            "audit": ["log", "audit", "track"]
        }
        
        req_lower = requirement.lower()
        for key, keywords in requirement_keywords.items():
            if key in req_lower:
                return any(kw in feat for feat in features for kw in keywords)
        
        return False
    
    def _handles_sensitive_data(self, context: AgentContext) -> bool:
        """Check if project handles sensitive data."""
        sensitive_indicators = [
            "payment", "credit card", "financial",
            "health", "medical", "patient",
            "personal", "private", "confidential",
            "password", "secret", "key"
        ]
        
        # Check features and description
        project_text = (
            context.project_spec.description.lower() +
            " ".join(f.name.lower() for f in context.project_spec.features)
        )
        
        return any(indicator in project_text for indicator in sensitive_indicators)
    
    def _handles_pii(self, context: AgentContext) -> bool:
        """Check if project handles PII."""
        pii_indicators = [
            "user", "profile", "account", "registration",
            "email", "phone", "address", "name",
            "identity", "personal"
        ]
        
        project_text = (
            context.project_spec.description.lower() +
            " ".join(f.name.lower() for f in context.project_spec.features)
        )
        
        return sum(1 for indicator in pii_indicators if indicator in project_text) >= 2
    
    def _assess_vulnerability_risk(self, vulnerability: str, context: AgentContext) -> float:
        """Assess risk level for a specific vulnerability."""
        risk_factors = {
            "Broken Access Control": {
                "indicators": ["user", "role", "permission", "admin"],
                "base_risk": 0.7
            },
            "Cryptographic Failures": {
                "indicators": ["password", "encrypt", "secure", "token"],
                "base_risk": 0.8
            },
            "Injection": {
                "indicators": ["database", "query", "input", "form"],
                "base_risk": 0.9
            },
            "Insecure Design": {
                "indicators": ["architecture", "design", "api"],
                "base_risk": 0.6
            },
            "Security Misconfiguration": {
                "indicators": ["deploy", "config", "environment"],
                "base_risk": 0.7
            }
        }
        
        if vulnerability not in risk_factors:
            return 0.5
        
        risk_info = risk_factors[vulnerability]
        project_text = (
            context.project_spec.description.lower() +
            " ".join(f.name.lower() for f in context.project_spec.features)
        )
        
        # Calculate risk based on indicators
        indicator_count = sum(
            1 for indicator in risk_info["indicators"]
            if indicator in project_text
        )
        
        if indicator_count == 0:
            return 0.0
        
        return min(risk_info["base_risk"] + (0.1 * indicator_count), 1.0)
    
    async def _check_technology_vulnerabilities(self, context: AgentContext) -> Dict[str, Any]:
        """Check for technology-specific vulnerabilities."""
        findings = []
        recommendations = []
        
        tech_vulnerabilities = {
            "node.js": {
                "vulnerabilities": ["Prototype pollution", "ReDoS", "Command injection"],
                "recommendations": [
                    "Keep dependencies updated",
                    "Use npm audit regularly",
                    "Validate all user input",
                    "Use parameterized commands"
                ]
            },
            "python": {
                "vulnerabilities": ["Code injection", "Pickle deserialization", "Path traversal"],
                "recommendations": [
                    "Use virtual environments",
                    "Keep dependencies updated",
                    "Avoid eval() and exec()",
                    "Validate file paths"
                ]
            },
            "php": {
                "vulnerabilities": ["SQL injection", "File inclusion", "Session hijacking"],
                "recommendations": [
                    "Use prepared statements",
                    "Disable dangerous functions",
                    "Secure session configuration"
                ]
            }
        }
        
        for tech in context.project_spec.technologies:
            tech_lower = tech.name.lower()
            
            for vuln_tech, vuln_info in tech_vulnerabilities.items():
                if vuln_tech in tech_lower:
                    findings.append({
                        "title": f"{tech.name} Security Considerations",
                        "description": f"Common vulnerabilities in {tech.name}",
                        "relevance": 0.7,
                        "vulnerabilities": vuln_info["vulnerabilities"]
                    })
                    
                    recommendations.extend(
                        f"{tech.name}: {rec}" for rec in vuln_info["recommendations"]
                    )
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    def _calculate_owasp_coverage(self, findings: List[Dict[str, Any]]) -> float:
        """Calculate OWASP coverage from findings."""
        covered_categories = set()
        
        for finding in findings:
            if "owasp_category" in finding:
                covered_categories.add(finding["owasp_category"])
        
        return len(covered_categories) / len(self.owasp_top_10)
    
    def _calculate_confidence(self, context: AgentContext, findings: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for security analysis."""
        base_confidence = 0.8
        
        # Adjust based on project type knowledge
        if context.project_spec.type in ["web_application", "api_service"]:
            base_confidence += 0.1
        
        # Adjust based on findings
        if findings:
            critical_findings = len([f for f in findings if f.get("severity") == "critical"])
            if critical_findings > 0:
                base_confidence += 0.05
        
        return min(base_confidence, 0.95)
    
    def get_expertise_areas(self) -> List[str]:
        """Get Security Specialist's areas of expertise."""
        return [
            "Application Security",
            "OWASP Top 10",
            "Authentication & Authorization",
            "Cryptography",
            "Data Protection",
            "Security Headers",
            "Vulnerability Assessment",
            "Compliance (GDPR, CCPA)",
            "Infrastructure Security",
            "API Security"
        ]
    
    def get_research_methods(self) -> List[str]:
        """Get research methods used by Security Specialist."""
        return [
            "Threat Modeling",
            "Vulnerability Assessment",
            "Security Requirements Analysis",
            "OWASP Guidelines Review",
            "Compliance Checking",
            "Risk Assessment",
            "Security Best Practices",
            "Technology-Specific Security Analysis"
        ]