"""DevOps Specialist research agent."""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from .base_agent import BaseResearchAgent, AgentCapability, AgentContext, AgentResponse
from ..models.research import ResearchSource

logger = logging.getLogger(__name__)


class DevOpsSpecialist(BaseResearchAgent):
    """Specializes in deployment, infrastructure, and operations."""
    
    def __init__(self):
        """Initialize DevOps Specialist agent."""
        super().__init__(
            name="DevOps Specialist",
            capabilities=[
                AgentCapability.DEPLOYMENT,
                AgentCapability.OPTIMIZATION,
                AgentCapability.ARCHITECTURE,
                AgentCapability.IMPLEMENTATION
            ]
        )
        
        # DevOps knowledge base
        self.deployment_strategies = {
            "blue_green": {
                "description": "Deploy to inactive environment, then switch",
                "benefits": ["Zero downtime", "Easy rollback", "Testing in prod environment"],
                "requirements": ["Double infrastructure", "Load balancer", "DNS control"]
            },
            "canary": {
                "description": "Gradual rollout to subset of users",
                "benefits": ["Risk mitigation", "Performance validation", "User feedback"],
                "requirements": ["Traffic routing", "Monitoring", "Feature flags"]
            },
            "rolling": {
                "description": "Update instances one at a time",
                "benefits": ["No extra infrastructure", "Gradual rollout"],
                "requirements": ["Load balancer", "Health checks", "Multiple instances"]
            },
            "recreate": {
                "description": "Stop old version, start new version",
                "benefits": ["Simple", "Clean state"],
                "requirements": ["Downtime acceptable", "Single instance OK"]
            }
        }
        
        self.container_platforms = {
            "docker": {
                "orchestrators": ["Kubernetes", "Docker Swarm", "ECS", "Nomad"],
                "registries": ["Docker Hub", "ECR", "GCR", "Harbor"],
                "tools": ["Docker Compose", "Buildkit", "Skaffold"]
            },
            "kubernetes": {
                "managed": ["EKS", "GKE", "AKS", "DOKS"],
                "tools": ["Helm", "Kustomize", "ArgoCD", "Flux"],
                "monitoring": ["Prometheus", "Grafana", "Jaeger"]
            }
        }
        
        self.cloud_providers = {
            "aws": {
                "compute": ["EC2", "Lambda", "ECS", "EKS"],
                "storage": ["S3", "EBS", "EFS"],
                "database": ["RDS", "DynamoDB", "Aurora"],
                "networking": ["VPC", "ALB", "CloudFront"],
                "devops": ["CodePipeline", "CodeBuild", "CodeDeploy"]
            },
            "gcp": {
                "compute": ["Compute Engine", "Cloud Functions", "Cloud Run", "GKE"],
                "storage": ["Cloud Storage", "Persistent Disk"],
                "database": ["Cloud SQL", "Firestore", "Bigtable"],
                "networking": ["VPC", "Load Balancing", "Cloud CDN"],
                "devops": ["Cloud Build", "Cloud Deploy"]
            },
            "azure": {
                "compute": ["Virtual Machines", "Functions", "Container Instances", "AKS"],
                "storage": ["Blob Storage", "File Storage"],
                "database": ["SQL Database", "Cosmos DB"],
                "networking": ["Virtual Network", "Load Balancer", "CDN"],
                "devops": ["Azure DevOps", "Pipelines"]
            }
        }
        
        self.cicd_tools = {
            "hosted": ["GitHub Actions", "GitLab CI", "CircleCI", "Travis CI"],
            "self_hosted": ["Jenkins", "TeamCity", "Bamboo", "GoCD"],
            "gitops": ["ArgoCD", "Flux", "Spinnaker"],
            "security": ["Snyk", "SonarQube", "Trivy", "Anchore"]
        }
        
        self.monitoring_stack = {
            "metrics": ["Prometheus", "DataDog", "New Relic", "CloudWatch"],
            "logs": ["ELK Stack", "Fluentd", "Splunk", "CloudWatch Logs"],
            "traces": ["Jaeger", "Zipkin", "AWS X-Ray", "DataDog APM"],
            "alerts": ["PagerDuty", "Opsgenie", "VictorOps"]
        }
    
    async def _initialize(self) -> None:
        """Initialize the DevOps Specialist."""
        logger.info("DevOps Specialist initialized with infrastructure knowledge")
    
    async def _perform_research(self, context: AgentContext) -> AgentResponse:
        """Perform DevOps analysis research."""
        findings = []
        recommendations = []
        
        # Analyze deployment requirements
        deployment_analysis = await self._analyze_deployment_requirements(context)
        findings.extend(deployment_analysis["findings"])
        recommendations.extend(deployment_analysis["recommendations"])
        
        # Infrastructure design
        infrastructure = await self._design_infrastructure(context)
        findings.extend(infrastructure["findings"])
        recommendations.extend(infrastructure["recommendations"])
        
        # CI/CD pipeline design
        cicd = await self._design_cicd_pipeline(context)
        findings.extend(cicd["findings"])
        recommendations.extend(cicd["recommendations"])
        
        # Monitoring and observability
        monitoring = await self._plan_monitoring(context)
        findings.extend(monitoring["findings"])
        recommendations.extend(monitoring["recommendations"])
        
        # Security and compliance
        security = await self._analyze_security_requirements(context)
        findings.extend(security["findings"])
        recommendations.extend(security["recommendations"])
        
        # Cost optimization
        cost = await self._analyze_cost_optimization(context)
        findings.extend(cost["findings"])
        recommendations.extend(cost["recommendations"])
        
        # Calculate confidence
        confidence = self._calculate_confidence(context, findings)
        
        return AgentResponse(
            agent_name=self.name,
            findings=findings,
            recommendations=self.prioritize_recommendations(recommendations, context),
            confidence=confidence,
            sources_used=[ResearchSource.DOCUMENTATION, ResearchSource.TOOLS],
            metadata={
                "deployment_strategy": deployment_analysis.get("strategy", "unknown"),
                "infrastructure_complexity": infrastructure.get("complexity", "medium")
            }
        )
    
    async def _analyze_deployment_requirements(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze deployment requirements and recommend strategy."""
        findings = []
        recommendations = []
        
        # Determine deployment scale
        scale = self._determine_deployment_scale(context)
        
        findings.append({
            "title": "Deployment Scale Analysis",
            "description": f"Project requires {scale['level']} scale deployment",
            "relevance": 1.0,
            "factors": scale["factors"]
        })
        
        # Choose deployment strategy
        strategy = self._choose_deployment_strategy(context, scale)
        
        findings.append({
            "title": f"Recommended Deployment Strategy: {strategy['name']}",
            "description": strategy["description"],
            "relevance": 0.9,
            "benefits": strategy["benefits"],
            "requirements": strategy["requirements"]
        })
        
        recommendations.append(f"Implement {strategy['name']} deployment strategy")
        
        # Environment strategy
        environments = self._plan_environments(context)
        findings.append({
            "title": "Environment Strategy",
            "description": "Recommended deployment environments",
            "relevance": 0.9,
            "environments": environments
        })
        
        for env in environments:
            recommendations.append(f"Set up {env['name']} environment: {env['purpose']}")
        
        return {
            "findings": findings,
            "recommendations": recommendations,
            "strategy": strategy["name"]
        }
    
    async def _design_infrastructure(self, context: AgentContext) -> Dict[str, Any]:
        """Design infrastructure architecture."""
        findings = []
        recommendations = []
        
        # Determine containerization needs
        containerization = self._assess_containerization(context)
        
        if containerization["needed"]:
            findings.append({
                "title": "Containerization Recommended",
                "description": "Application suitable for container deployment",
                "relevance": 0.9,
                "reasons": containerization["reasons"],
                "platform": containerization["platform"]
            })
            
            recommendations.extend([
                f"Use {containerization['platform']} for containerization",
                "Create optimized container images",
                "Implement multi-stage builds",
                "Use container registry for image storage"
            ])
            
            # Orchestration recommendations
            if containerization["orchestration_needed"]:
                orchestrator = self._recommend_orchestrator(context, containerization)
                findings.append({
                    "title": f"Container Orchestration: {orchestrator}",
                    "description": "Orchestration platform for container management",
                    "relevance": 0.8,
                    "features": self._get_orchestrator_features(orchestrator)
                })
                
                recommendations.append(f"Deploy using {orchestrator}")
        
        # Cloud provider selection
        cloud = self._recommend_cloud_provider(context)
        findings.append({
            "title": f"Cloud Provider: {cloud['provider']}",
            "description": "Recommended cloud infrastructure",
            "relevance": 0.9,
            "services": cloud["services"],
            "reasons": cloud["reasons"]
        })
        
        for service in cloud["services"][:5]:
            recommendations.append(f"Use {service} for {cloud['services'][service]}")
        
        # Infrastructure as Code
        iac = self._recommend_iac_tools(context)
        findings.append({
            "title": "Infrastructure as Code",
            "description": "Automate infrastructure provisioning",
            "relevance": 0.9,
            "tools": iac
        })
        
        recommendations.append(f"Use {iac[0]} for infrastructure automation")
        
        # Determine complexity
        complexity = self._assess_infrastructure_complexity(context)
        
        return {
            "findings": findings,
            "recommendations": recommendations,
            "complexity": complexity
        }
    
    async def _design_cicd_pipeline(self, context: AgentContext) -> Dict[str, Any]:
        """Design CI/CD pipeline."""
        findings = []
        recommendations = []
        
        # Choose CI/CD platform
        cicd_platform = self._choose_cicd_platform(context)
        
        findings.append({
            "title": f"CI/CD Platform: {cicd_platform['name']}",
            "description": cicd_platform["reason"],
            "relevance": 0.9,
            "features": cicd_platform["features"]
        })
        
        recommendations.append(f"Implement CI/CD using {cicd_platform['name']}")
        
        # Pipeline stages
        stages = self._design_pipeline_stages(context)
        
        findings.append({
            "title": "CI/CD Pipeline Design",
            "description": "Automated deployment pipeline stages",
            "relevance": 1.0,
            "stages": stages
        })
        
        for stage in stages:
            recommendations.append(f"{stage['name']}: {stage['description']}")
        
        # Security scanning
        security_tools = self._recommend_security_scanning(context)
        
        findings.append({
            "title": "Security Scanning Integration",
            "description": "Automated security checks in pipeline",
            "relevance": 0.8,
            "tools": security_tools
        })
        
        recommendations.extend([
            f"Integrate {tool} for {purpose}" 
            for tool, purpose in security_tools.items()
        ])
        
        # Artifact management
        findings.append({
            "title": "Artifact Management",
            "description": "Build artifact storage and versioning",
            "relevance": 0.8,
            "options": self._get_artifact_options(context)
        })
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _plan_monitoring(self, context: AgentContext) -> Dict[str, Any]:
        """Plan monitoring and observability strategy."""
        findings = []
        recommendations = []
        
        # Monitoring stack selection
        stack = self._design_monitoring_stack(context)
        
        findings.append({
            "title": "Monitoring Stack Design",
            "description": "Comprehensive observability solution",
            "relevance": 0.9,
            "components": stack
        })
        
        for component, tools in stack.items():
            recommendations.append(f"{component}: Use {tools[0]}")
        
        # Key metrics
        metrics = self._identify_key_metrics(context)
        
        findings.append({
            "title": "Key Performance Metrics",
            "description": "Critical metrics to monitor",
            "relevance": 0.9,
            "metrics": metrics
        })
        
        recommendations.append(f"Monitor: {', '.join(metrics[:5])}")
        
        # Alerting strategy
        alerts = self._design_alerting_strategy(context)
        
        findings.append({
            "title": "Alerting Strategy",
            "description": "Proactive incident detection",
            "relevance": 0.8,
            "alerts": alerts
        })
        
        recommendations.extend([
            "Set up alerting for critical metrics",
            "Implement escalation policies",
            "Create runbooks for common issues",
            "Set up on-call rotation"
        ])
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_security_requirements(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze security requirements for DevOps."""
        findings = []
        recommendations = []
        
        # Secret management
        findings.append({
            "title": "Secret Management Strategy",
            "description": "Secure handling of sensitive data",
            "relevance": 1.0,
            "tools": ["HashiCorp Vault", "AWS Secrets Manager", "Azure Key Vault", "Sealed Secrets"]
        })
        
        recommendations.extend([
            "Implement centralized secret management",
            "Rotate secrets regularly",
            "Use least privilege access",
            "Audit secret access"
        ])
        
        # Network security
        findings.append({
            "title": "Network Security Design",
            "description": "Secure network architecture",
            "relevance": 0.9,
            "components": [
                "Private subnets for applications",
                "Public subnet for load balancers only",
                "Network segmentation",
                "Zero-trust networking"
            ]
        })
        
        recommendations.extend([
            "Implement network segmentation",
            "Use private endpoints for services",
            "Enable network encryption",
            "Implement WAF for web applications"
        ])
        
        # Compliance automation
        if self._needs_compliance_automation(context):
            findings.append({
                "title": "Compliance Automation",
                "description": "Automated compliance checks",
                "relevance": 0.8,
                "tools": ["Cloud Custodian", "AWS Config", "Azure Policy", "OPA"]
            })
            
            recommendations.append("Automate compliance validation in CI/CD")
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    async def _analyze_cost_optimization(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze cost optimization opportunities."""
        findings = []
        recommendations = []
        
        # Resource optimization
        findings.append({
            "title": "Resource Optimization",
            "description": "Optimize infrastructure costs",
            "relevance": 0.8,
            "strategies": [
                "Right-sizing instances",
                "Auto-scaling policies",
                "Spot/Preemptible instances",
                "Reserved capacity"
            ]
        })
        
        recommendations.extend([
            "Implement auto-scaling for variable loads",
            "Use spot instances for non-critical workloads",
            "Monitor and optimize resource utilization",
            "Set up cost alerts and budgets"
        ])
        
        # Serverless opportunities
        if self._has_serverless_opportunities(context):
            findings.append({
                "title": "Serverless Opportunities",
                "description": "Functions suitable for serverless",
                "relevance": 0.7,
                "candidates": self._identify_serverless_candidates(context)
            })
            
            recommendations.append("Consider serverless for event-driven components")
        
        return {
            "findings": findings,
            "recommendations": recommendations
        }
    
    def _determine_deployment_scale(self, context: AgentContext) -> Dict[str, Any]:
        """Determine deployment scale requirements."""
        factors = []
        scale_score = 0
        
        # User scale
        if any(kw in str(context.project_spec).lower() for kw in ["millions", "global", "enterprise"]):
            factors.append("Large user base expected")
            scale_score += 3
        elif any(kw in str(context.project_spec).lower() for kw in ["thousands", "regional"]):
            factors.append("Medium user base expected")
            scale_score += 2
        else:
            factors.append("Small to medium user base")
            scale_score += 1
        
        # Availability requirements
        if any(kw in str(context.project_spec).lower() for kw in ["high availability", "24/7", "critical"]):
            factors.append("High availability required")
            scale_score += 2
        
        # Performance requirements
        if any(kw in str(context.project_spec).lower() for kw in ["real-time", "low latency", "performance"]):
            factors.append("Performance critical")
            scale_score += 2
        
        # Determine level
        if scale_score >= 6:
            level = "large"
        elif scale_score >= 4:
            level = "medium"
        else:
            level = "small"
        
        return {
            "level": level,
            "score": scale_score,
            "factors": factors
        }
    
    def _choose_deployment_strategy(self, context: AgentContext, scale: Dict[str, Any]) -> Dict[str, Any]:
        """Choose appropriate deployment strategy."""
        if scale["level"] == "large":
            # Large scale needs zero-downtime
            if any(kw in str(context.project_spec).lower() for kw in ["experiment", "test"]):
                strategy_name = "canary"
            else:
                strategy_name = "blue_green"
        elif scale["level"] == "medium":
            strategy_name = "rolling"
        else:
            strategy_name = "recreate"
        
        strategy = self.deployment_strategies[strategy_name].copy()
        strategy["name"] = strategy_name.replace("_", "-")
        
        return strategy
    
    def _plan_environments(self, context: AgentContext) -> List[Dict[str, str]]:
        """Plan deployment environments."""
        environments = [
            {"name": "Development", "purpose": "Developer testing"},
            {"name": "Staging", "purpose": "Pre-production validation"},
            {"name": "Production", "purpose": "Live environment"}
        ]
        
        # Add additional environments based on scale
        if any(kw in str(context.project_spec).lower() for kw in ["testing", "qa"]):
            environments.insert(1, {"name": "QA", "purpose": "Quality assurance testing"})
        
        if any(kw in str(context.project_spec).lower() for kw in ["demo", "sales"]):
            environments.append({"name": "Demo", "purpose": "Sales demonstrations"})
        
        return environments
    
    def _assess_containerization(self, context: AgentContext) -> Dict[str, Any]:
        """Assess containerization needs."""
        reasons = []
        needed = False
        
        # Check for microservices
        if any(kw in str(context.project_spec).lower() for kw in ["microservice", "services", "distributed"]):
            reasons.append("Microservices architecture")
            needed = True
        
        # Check for scalability needs
        if len(context.project_spec.features) > 10:
            reasons.append("Complex application with multiple components")
            needed = True
        
        # Check for technology diversity
        if len(context.project_spec.technologies) > 3:
            reasons.append("Multiple technology stack")
            needed = True
        
        # Default to containers for modern apps
        if context.project_spec.type in ["web_application", "api_service"]:
            reasons.append("Modern application deployment")
            needed = True
        
        # Determine platform
        platform = "Docker"
        orchestration_needed = len(reasons) > 2
        
        return {
            "needed": needed,
            "reasons": reasons,
            "platform": platform,
            "orchestration_needed": orchestration_needed
        }
    
    def _recommend_orchestrator(self, context: AgentContext, containerization: Dict[str, Any]) -> str:
        """Recommend container orchestrator."""
        # Default to Kubernetes for complex deployments
        if any(kw in str(context.project_spec).lower() for kw in ["scale", "enterprise", "production"]):
            return "Kubernetes"
        
        # Simpler options for smaller deployments
        if len(context.project_spec.features) < 5:
            return "Docker Compose"
        
        return "Docker Swarm"
    
    def _get_orchestrator_features(self, orchestrator: str) -> List[str]:
        """Get orchestrator features."""
        features = {
            "Kubernetes": [
                "Auto-scaling",
                "Self-healing",
                "Service discovery",
                "Load balancing",
                "Rolling updates"
            ],
            "Docker Swarm": [
                "Simple setup",
                "Native Docker integration",
                "Basic orchestration",
                "Service scaling"
            ],
            "Docker Compose": [
                "Local development",
                "Simple multi-container apps",
                "Easy configuration"
            ]
        }
        
        return features.get(orchestrator, [])
    
    def _recommend_cloud_provider(self, context: AgentContext) -> Dict[str, Any]:
        """Recommend cloud provider and services."""
        # Simple heuristic - in practice would consider more factors
        provider = "AWS"  # Default
        
        # Check for specific requirements
        if "azure" in str(context.project_spec).lower():
            provider = "Azure"
        elif "google" in str(context.project_spec).lower() or "gcp" in str(context.project_spec).lower():
            provider = "GCP"
        
        # Get relevant services
        services = {}
        provider_services = self.cloud_providers[provider.lower()]
        
        # Compute
        if context.project_spec.type == "web_application":
            services[provider_services["compute"][0]] = "Application hosting"
        
        # Storage
        if any("upload" in f.name.lower() for f in context.project_spec.features):
            services[provider_services["storage"][0]] = "File storage"
        
        # Database
        if any("database" in t.name.lower() for t in context.project_spec.technologies):
            services[provider_services["database"][0]] = "Managed database"
        
        return {
            "provider": provider,
            "services": services,
            "reasons": ["Market leader", "Comprehensive services", "Good documentation"]
        }
    
    def _recommend_iac_tools(self, context: AgentContext) -> List[str]:
        """Recommend Infrastructure as Code tools."""
        tools = []
        
        # Terraform for multi-cloud or complex infrastructure
        if any(kw in str(context.project_spec).lower() for kw in ["multi-cloud", "hybrid"]):
            tools.append("Terraform")
        else:
            tools.append("Terraform")  # Default recommendation
        
        # Cloud-specific tools
        tools.extend(["CloudFormation", "Pulumi", "Ansible"])
        
        return tools
    
    def _assess_infrastructure_complexity(self, context: AgentContext) -> str:
        """Assess infrastructure complexity."""
        complexity_score = 0
        
        # Add points for various factors
        if len(context.project_spec.technologies) > 5:
            complexity_score += 2
        
        if any(kw in str(context.project_spec).lower() for kw in ["microservice", "distributed"]):
            complexity_score += 3
        
        if any(kw in str(context.project_spec).lower() for kw in ["high availability", "multi-region"]):
            complexity_score += 2
        
        if complexity_score >= 5:
            return "high"
        elif complexity_score >= 3:
            return "medium"
        else:
            return "low"
    
    def _choose_cicd_platform(self, context: AgentContext) -> Dict[str, Any]:
        """Choose CI/CD platform."""
        # Check for existing version control
        if "github" in str(context.project_spec).lower():
            return {
                "name": "GitHub Actions",
                "reason": "Native GitHub integration",
                "features": ["Easy setup", "Good marketplace", "Free tier"]
            }
        elif "gitlab" in str(context.project_spec).lower():
            return {
                "name": "GitLab CI",
                "reason": "Native GitLab integration",
                "features": ["Built-in", "Good features", "Self-hosted option"]
            }
        
        # Default to GitHub Actions for modern projects
        return {
            "name": "GitHub Actions",
            "reason": "Modern, easy to use CI/CD",
            "features": ["YAML configuration", "Matrix builds", "Marketplace"]
        }
    
    def _design_pipeline_stages(self, context: AgentContext) -> List[Dict[str, str]]:
        """Design CI/CD pipeline stages."""
        stages = [
            {"name": "Source", "description": "Checkout code from repository"},
            {"name": "Build", "description": "Compile/package application"},
            {"name": "Test", "description": "Run automated tests"},
            {"name": "Security Scan", "description": "Scan for vulnerabilities"},
            {"name": "Package", "description": "Create deployment artifacts"},
            {"name": "Deploy Staging", "description": "Deploy to staging environment"},
            {"name": "Integration Tests", "description": "Run integration tests"},
            {"name": "Deploy Production", "description": "Deploy to production"}
        ]
        
        # Add performance testing for critical apps
        if any(kw in str(context.project_spec).lower() for kw in ["performance", "scale"]):
            stages.insert(7, {"name": "Performance Tests", "description": "Run load tests"})
        
        return stages
    
    def _recommend_security_scanning(self, context: AgentContext) -> Dict[str, str]:
        """Recommend security scanning tools."""
        tools = {
            "SonarQube": "Code quality and security",
            "Trivy": "Container vulnerability scanning"
        }
        
        # Add dependency scanning
        if "node" in str(context.project_spec.technologies).lower():
            tools["npm audit"] = "Node.js dependency scanning"
        elif "python" in str(context.project_spec.technologies).lower():
            tools["Safety"] = "Python dependency scanning"
        
        # Add SAST/DAST for web apps
        if context.project_spec.type == "web_application":
            tools["OWASP ZAP"] = "Dynamic security testing"
        
        return tools
    
    def _get_artifact_options(self, context: AgentContext) -> List[str]:
        """Get artifact storage options."""
        options = []
        
        # Container registries
        if self._assess_containerization(context)["needed"]:
            options.extend(["Docker Hub", "ECR", "GCR", "ACR"])
        
        # Package repositories
        if "node" in str(context.project_spec.technologies).lower():
            options.append("npm registry")
        elif "python" in str(context.project_spec.technologies).lower():
            options.append("PyPI")
        
        # Generic artifact storage
        options.extend(["Artifactory", "Nexus", "S3"])
        
        return options
    
    def _design_monitoring_stack(self, context: AgentContext) -> Dict[str, List[str]]:
        """Design monitoring stack."""
        stack = {}
        
        # Metrics
        if context.project_spec.type in ["web_application", "api_service"]:
            stack["Metrics"] = ["Prometheus + Grafana", "DataDog", "New Relic"]
        
        # Logs
        stack["Logs"] = ["ELK Stack", "Fluentd + CloudWatch", "Splunk"]
        
        # Traces
        if any(kw in str(context.project_spec).lower() for kw in ["microservice", "distributed"]):
            stack["Traces"] = ["Jaeger", "Zipkin", "AWS X-Ray"]
        
        # Alerts
        stack["Alerts"] = ["PagerDuty", "Prometheus Alertmanager", "CloudWatch Alarms"]
        
        return stack
    
    def _identify_key_metrics(self, context: AgentContext) -> List[str]:
        """Identify key metrics to monitor."""
        metrics = [
            "CPU utilization",
            "Memory usage",
            "Disk I/O",
            "Network traffic",
            "Error rate",
            "Response time"
        ]
        
        # Application-specific metrics
        if context.project_spec.type == "web_application":
            metrics.extend(["Page load time", "Active users", "Session duration"])
        elif context.project_spec.type == "api_service":
            metrics.extend(["API latency", "Request rate", "Success rate"])
        
        # Business metrics
        if any(kw in str(context.project_spec).lower() for kw in ["payment", "transaction"]):
            metrics.extend(["Transaction rate", "Payment success rate"])
        
        return metrics
    
    def _design_alerting_strategy(self, context: AgentContext) -> List[Dict[str, str]]:
        """Design alerting strategy."""
        alerts = [
            {"metric": "Error rate > 1%", "severity": "warning"},
            {"metric": "Response time > 1s", "severity": "warning"},
            {"metric": "CPU > 80%", "severity": "warning"},
            {"metric": "Memory > 90%", "severity": "critical"},
            {"metric": "Disk > 85%", "severity": "warning"},
            {"metric": "Service down", "severity": "critical"}
        ]
        
        return alerts
    
    def _needs_compliance_automation(self, context: AgentContext) -> bool:
        """Check if compliance automation is needed."""
        compliance_indicators = ["compliance", "audit", "regulation", "hipaa", "pci", "gdpr"]
        
        return any(
            indicator in str(context.project_spec).lower() 
            for indicator in compliance_indicators
        )
    
    def _has_serverless_opportunities(self, context: AgentContext) -> bool:
        """Check for serverless opportunities."""
        serverless_indicators = [
            "event", "trigger", "scheduled", "cron",
            "webhook", "notification", "batch"
        ]
        
        return any(
            indicator in str(context.project_spec).lower() 
            for indicator in serverless_indicators
        )
    
    def _identify_serverless_candidates(self, context: AgentContext) -> List[str]:
        """Identify components suitable for serverless."""
        candidates = []
        
        for feature in context.project_spec.features:
            feature_lower = feature.name.lower()
            if any(kw in feature_lower for kw in ["notification", "email", "scheduled"]):
                candidates.append(feature.name)
        
        return candidates
    
    def _calculate_confidence(self, context: AgentContext, findings: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for DevOps analysis."""
        base_confidence = 0.8
        
        # Higher confidence for common project types
        if context.project_spec.type in ["web_application", "api_service"]:
            base_confidence += 0.1
        
        # Adjust based on containerization assessment
        if self._assess_containerization(context)["needed"]:
            base_confidence += 0.05
        
        # Adjust based on findings
        if len(findings) > 5:
            base_confidence += 0.05
        
        return min(base_confidence, 0.95)
    
    def get_expertise_areas(self) -> List[str]:
        """Get DevOps Specialist's areas of expertise."""
        return [
            "Deployment Strategies",
            "Container Orchestration",
            "CI/CD Pipelines",
            "Infrastructure as Code",
            "Cloud Architecture",
            "Monitoring & Observability",
            "Security Automation",
            "Cost Optimization",
            "GitOps",
            "Site Reliability Engineering"
        ]
    
    def get_research_methods(self) -> List[str]:
        """Get research methods used by DevOps Specialist."""
        return [
            "Infrastructure Analysis",
            "Deployment Planning",
            "Pipeline Design",
            "Monitoring Strategy",
            "Security Assessment",
            "Cost Analysis",
            "Tool Evaluation",
            "Best Practices Review"
        ]