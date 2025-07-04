"""Custom instructions examples for Claude Code Builder."""
from pathlib import Path
from typing import Dict, Any, List
import yaml
import json


class CustomInstructionsExample:
    """Examples of custom instructions for different scenarios."""
    
    @staticmethod
    def get_all_examples() -> Dict[str, Dict[str, Any]]:
        """Get all custom instruction examples.
        
        Returns:
            Dictionary of instruction examples
        """
        return {
            'enterprise_python': CustomInstructionsExample.enterprise_python_instructions(),
            'startup_fast': CustomInstructionsExample.startup_fast_instructions(),
            'data_science': CustomInstructionsExample.data_science_instructions(),
            'web_api': CustomInstructionsExample.web_api_instructions(),
            'microservices': CustomInstructionsExample.microservices_instructions(),
            'security_focused': CustomInstructionsExample.security_focused_instructions(),
            'performance_critical': CustomInstructionsExample.performance_critical_instructions(),
            'educational': CustomInstructionsExample.educational_instructions()
        }
    
    @staticmethod
    def enterprise_python_instructions() -> Dict[str, Any]:
        """Enterprise Python project instructions.
        
        Returns:
            Instruction configuration
        """
        return {
            'name': 'Enterprise Python Standards',
            'description': 'Strict standards for enterprise Python applications',
            'instructions': {
                'code_style': [
                    'Follow PEP 8 strictly with 79 character line limit',
                    'Use type hints for all function signatures',
                    'Docstrings must follow Google style guide',
                    'Class names in PascalCase, functions in snake_case',
                    'Private methods prefixed with single underscore',
                    'Constants in UPPER_SNAKE_CASE'
                ],
                'architecture': [
                    'Use Domain-Driven Design principles',
                    'Implement Repository pattern for data access',
                    'Service layer for business logic',
                    'Dependency injection for loose coupling',
                    'Separate concerns into distinct modules',
                    'Use interfaces (ABC) for contracts'
                ],
                'error_handling': [
                    'Never use bare except clauses',
                    'Create custom exception hierarchy',
                    'Log all errors with full context',
                    'Use structured logging (JSON format)',
                    'Implement circuit breakers for external services',
                    'Graceful degradation for non-critical failures'
                ],
                'testing': [
                    'Minimum 90% code coverage',
                    'Unit tests for all public methods',
                    'Integration tests for API endpoints',
                    'Use pytest with fixtures',
                    'Mock all external dependencies',
                    'Property-based testing where applicable',
                    'Performance tests for critical paths'
                ],
                'security': [
                    'Input validation on all user data',
                    'Parameterized queries only',
                    'Secrets in environment variables',
                    'Rate limiting on all endpoints',
                    'Audit logging for sensitive operations',
                    'Regular dependency vulnerability scanning'
                ],
                'documentation': [
                    'README with architecture overview',
                    'API documentation with OpenAPI',
                    'Deployment guide with troubleshooting',
                    'Code comments for complex logic only',
                    'ADRs for architectural decisions',
                    'Changelog following Keep a Changelog format'
                ],
                'performance': [
                    'Profile before optimizing',
                    'Lazy loading where appropriate',
                    'Connection pooling for databases',
                    'Implement caching strategy',
                    'Async I/O for concurrent operations',
                    'Monitor memory usage patterns'
                ]
            }
        }
    
    @staticmethod
    def startup_fast_instructions() -> Dict[str, Any]:
        """Fast-moving startup project instructions.
        
        Returns:
            Instruction configuration
        """
        return {
            'name': 'Startup Speed',
            'description': 'Optimize for development speed and iteration',
            'instructions': {
                'code_style': [
                    'Readable code over clever code',
                    'Use modern Python features (3.10+)',
                    'Type hints optional but recommended',
                    'Short functions (max 20 lines)',
                    'Descriptive variable names'
                ],
                'architecture': [
                    'Start monolithic, prepare for microservices',
                    'Use frameworks defaults where possible',
                    'Database migrations from day one',
                    'Feature flags for easy rollback',
                    'API-first design'
                ],
                'development': [
                    'Hot reload in development',
                    'Docker Compose for local setup',
                    'One-command setup script',
                    'Automated code formatting (Black)',
                    'Pre-commit hooks for quality'
                ],
                'testing': [
                    'Focus on integration tests',
                    'Test critical paths first',
                    'Quick smoke tests for deploys',
                    'Manual testing acceptable initially',
                    'Add tests when fixing bugs'
                ],
                'deployment': [
                    'Deploy on every merge to main',
                    'Blue-green deployments',
                    'Rollback capability within 1 minute',
                    'Infrastructure as code',
                    'Monitoring before optimization'
                ]
            }
        }
    
    @staticmethod
    def data_science_instructions() -> Dict[str, Any]:
        """Data science project instructions.
        
        Returns:
            Instruction configuration
        """
        return {
            'name': 'Data Science Standards',
            'description': 'Best practices for ML and data science projects',
            'instructions': {
                'code_style': [
                    'Jupyter notebooks for exploration only',
                    'Production code in .py files',
                    'Clear separation of data, models, and evaluation',
                    'Reproducible random seeds',
                    'Vectorized operations over loops'
                ],
                'data_handling': [
                    'Version control for datasets (DVC)',
                    'Data validation on ingestion',
                    'Handle missing values explicitly',
                    'Document data sources and licenses',
                    'Separate train/validation/test sets',
                    'No data leakage between sets'
                ],
                'model_development': [
                    'Start with baseline models',
                    'Track all experiments (MLflow)',
                    'Cross-validation for model selection',
                    'Feature importance analysis',
                    'Model interpretability tools',
                    'Bias and fairness evaluation'
                ],
                'pipeline': [
                    'Modular pipeline components',
                    'Config-driven parameters',
                    'Checkpointing for long runs',
                    'Parallel processing where possible',
                    'Resource monitoring',
                    'Automated retraining triggers'
                ],
                'documentation': [
                    'Document assumptions clearly',
                    'Explain feature engineering',
                    'Model card for each model',
                    'Performance metrics definitions',
                    'Limitations and biases section',
                    'Reproducibility instructions'
                ]
            }
        }
    
    @staticmethod
    def web_api_instructions() -> Dict[str, Any]:
        """Web API project instructions.
        
        Returns:
            Instruction configuration
        """
        return {
            'name': 'RESTful API Standards',
            'description': 'Building robust and scalable web APIs',
            'instructions': {
                'api_design': [
                    'Follow REST principles strictly',
                    'Consistent naming conventions',
                    'Versioning from v1',
                    'HATEOAS where appropriate',
                    'Proper HTTP status codes',
                    'JSON:API or similar standard'
                ],
                'request_handling': [
                    'Request validation with Pydantic',
                    'Rate limiting by API key',
                    'Request ID for tracing',
                    'Pagination for list endpoints',
                    'Field filtering support',
                    'Consistent error format'
                ],
                'security': [
                    'JWT tokens with refresh',
                    'OAuth2 for third-party',
                    'CORS configuration',
                    'API key management',
                    'Request signing for webhooks',
                    'SQL injection prevention'
                ],
                'performance': [
                    'Response time < 200ms',
                    'Database query optimization',
                    'Redis caching layer',
                    'Async request handling',
                    'Connection pooling',
                    'CDN for static assets'
                ],
                'documentation': [
                    'OpenAPI 3.0 specification',
                    'Interactive API explorer',
                    'Example requests/responses',
                    'Authentication guide',
                    'Rate limit documentation',
                    'Webhook integration guide'
                ]
            }
        }
    
    @staticmethod
    def microservices_instructions() -> Dict[str, Any]:
        """Microservices architecture instructions.
        
        Returns:
            Instruction configuration
        """
        return {
            'name': 'Microservices Patterns',
            'description': 'Building resilient microservices systems',
            'instructions': {
                'service_design': [
                    'Single responsibility per service',
                    'Domain boundaries clearly defined',
                    'Shared nothing architecture',
                    'Service contracts with schemas',
                    'Backward compatibility',
                    'Database per service'
                ],
                'communication': [
                    'REST for synchronous',
                    'Message queues for async',
                    'Service mesh for routing',
                    'Circuit breakers mandatory',
                    'Retry with exponential backoff',
                    'Distributed tracing'
                ],
                'resilience': [
                    'Graceful degradation',
                    'Bulkhead pattern',
                    'Health check endpoints',
                    'Timeout configurations',
                    'Chaos engineering tests',
                    'Automatic failover'
                ],
                'deployment': [
                    'Container per service',
                    'Kubernetes orchestration',
                    'Service discovery',
                    'Blue-green deployments',
                    'Canary releases',
                    'Rollback automation'
                ],
                'observability': [
                    'Structured logging',
                    'Metrics with Prometheus',
                    'Distributed tracing',
                    'Error tracking',
                    'Performance monitoring',
                    'Business metrics'
                ]
            }
        }
    
    @staticmethod
    def security_focused_instructions() -> Dict[str, Any]:
        """Security-focused project instructions.
        
        Returns:
            Instruction configuration
        """
        return {
            'name': 'Security First',
            'description': 'Maximum security for sensitive applications',
            'instructions': {
                'secure_coding': [
                    'OWASP Top 10 compliance',
                    'Input validation everything',
                    'Output encoding always',
                    'Parameterized queries only',
                    'No dynamic code execution',
                    'Secure random for tokens'
                ],
                'authentication': [
                    'Multi-factor authentication',
                    'Password complexity rules',
                    'Account lockout policies',
                    'Session timeout controls',
                    'Secure password storage (Argon2)',
                    'Token rotation strategy'
                ],
                'data_protection': [
                    'Encryption at rest (AES-256)',
                    'TLS 1.3 for transit',
                    'Key management service',
                    'Data classification',
                    'PII identification and masking',
                    'Secure deletion procedures'
                ],
                'access_control': [
                    'Principle of least privilege',
                    'Role-based access control',
                    'Attribute-based when needed',
                    'Regular permission audits',
                    'Segregation of duties',
                    'Zero trust architecture'
                ],
                'monitoring': [
                    'Security event logging',
                    'Intrusion detection',
                    'Anomaly detection',
                    'Failed login monitoring',
                    'File integrity monitoring',
                    'Regular security scans'
                ],
                'compliance': [
                    'GDPR compliance built-in',
                    'Right to deletion',
                    'Data portability',
                    'Consent management',
                    'Audit trail complete',
                    'Regular penetration testing'
                ]
            }
        }
    
    @staticmethod
    def performance_critical_instructions() -> Dict[str, Any]:
        """Performance-critical application instructions.
        
        Returns:
            Instruction configuration
        """
        return {
            'name': 'Performance Optimized',
            'description': 'For applications where every millisecond counts',
            'instructions': {
                'code_optimization': [
                    'Profile before optimizing',
                    'Algorithmic optimization first',
                    'Memory allocation patterns',
                    'Cache-friendly data structures',
                    'Vectorization where possible',
                    'Avoid premature optimization'
                ],
                'concurrency': [
                    'Async/await for I/O',
                    'Thread pools for CPU work',
                    'Lock-free data structures',
                    'Minimize context switching',
                    'Batch operations',
                    'Connection pooling'
                ],
                'caching': [
                    'Multi-level cache strategy',
                    'Cache warming on startup',
                    'TTL based on data volatility',
                    'Cache invalidation strategy',
                    'Distributed caching',
                    'Edge caching with CDN'
                ],
                'database': [
                    'Query optimization mandatory',
                    'Proper indexing strategy',
                    'Read replicas for scaling',
                    'Connection pooling',
                    'Prepared statements',
                    'Denormalization where needed'
                ],
                'monitoring': [
                    'APM integration required',
                    'Custom performance metrics',
                    'Latency percentiles (p50, p95, p99)',
                    'Resource utilization tracking',
                    'Slow query logging',
                    'Performance regression alerts'
                ]
            }
        }
    
    @staticmethod
    def educational_instructions() -> Dict[str, Any]:
        """Educational project instructions.
        
        Returns:
            Instruction configuration
        """
        return {
            'name': 'Educational Code',
            'description': 'Code optimized for learning and understanding',
            'instructions': {
                'code_style': [
                    'Explicit over implicit',
                    'Verbose variable names',
                    'Step-by-step logic',
                    'Avoid advanced features initially',
                    'Consistent patterns throughout',
                    'Comments explain "why" not "what"'
                ],
                'documentation': [
                    'Comprehensive README',
                    'Getting started guide',
                    'Concept explanations',
                    'Visual diagrams',
                    'Common pitfalls section',
                    'Further reading links'
                ],
                'examples': [
                    'Working examples for everything',
                    'Progressive complexity',
                    'Common use cases covered',
                    'Error scenarios demonstrated',
                    'Best practices highlighted',
                    'Anti-patterns explained'
                ],
                'structure': [
                    'Logical module organization',
                    'Clear separation of concerns',
                    'Consistent naming throughout',
                    'Minimal dependencies',
                    'Easy to navigate',
                    'Self-contained components'
                ],
                'learning_path': [
                    'Start with basics',
                    'Build on previous concepts',
                    'Exercises after each section',
                    'Solutions provided separately',
                    'Challenges for advanced users',
                    'Real-world applications'
                ]
            }
        }
    
    @staticmethod
    def create_instruction_file(
        instruction_type: str,
        output_path: Path,
        format: str = "yaml"
    ) -> Path:
        """Create a custom instruction file.
        
        Args:
            instruction_type: Type of instructions
            output_path: Output file path
            format: Output format (yaml or json)
            
        Returns:
            Path to created file
        """
        examples = CustomInstructionsExample.get_all_examples()
        
        if instruction_type not in examples:
            raise ValueError(f"Unknown instruction type: {instruction_type}")
        
        instructions = examples[instruction_type]['instructions']
        
        if format == "yaml":
            output_path = output_path.with_suffix('.yaml')
            with open(output_path, 'w') as f:
                yaml.dump(instructions, f, default_flow_style=False, sort_keys=False)
        else:
            output_path = output_path.with_suffix('.json')
            with open(output_path, 'w') as f:
                json.dump(instructions, f, indent=2)
        
        return output_path
    
    @staticmethod
    def combine_instructions(
        instruction_types: List[str],
        output_path: Path
    ) -> Path:
        """Combine multiple instruction sets.
        
        Args:
            instruction_types: List of instruction types to combine
            output_path: Output file path
            
        Returns:
            Path to created file
        """
        examples = CustomInstructionsExample.get_all_examples()
        combined = {}
        
        for inst_type in instruction_types:
            if inst_type not in examples:
                continue
            
            instructions = examples[inst_type]['instructions']
            for category, rules in instructions.items():
                if category not in combined:
                    combined[category] = []
                
                # Merge rules, avoiding duplicates
                for rule in rules:
                    if rule not in combined[category]:
                        combined[category].append(rule)
        
        output_path = output_path.with_suffix('.yaml')
        with open(output_path, 'w') as f:
            yaml.dump(combined, f, default_flow_style=False, sort_keys=False)
        
        return output_path
    
    @staticmethod
    def generate_examples_readme() -> str:
        """Generate README for custom instructions examples.
        
        Returns:
            README content
        """
        return """# Custom Instructions Examples

This directory contains examples of custom instructions for different project types and scenarios.

## Available Instruction Sets

### Enterprise Python (`enterprise_python`)
Strict standards for enterprise-grade Python applications:
- Comprehensive testing requirements (90% coverage)
- Domain-Driven Design architecture
- Extensive error handling and logging
- Security-first approach

### Startup Fast (`startup_fast`)
Optimized for rapid development and iteration:
- Pragmatic over perfect
- Quick deployment cycles
- Focus on core features
- Monitoring before optimization

### Data Science (`data_science`)
Best practices for ML and data projects:
- Reproducible experiments
- Data versioning
- Model tracking
- Pipeline automation

### Web API (`web_api`)
Building robust RESTful APIs:
- Consistent API design
- Performance optimization
- Security best practices
- Comprehensive documentation

### Microservices (`microservices`)
Distributed systems patterns:
- Service boundaries
- Resilience patterns
- Observability
- Container orchestration

### Security Focused (`security_focused`)
Maximum security applications:
- OWASP compliance
- Defense in depth
- Audit trails
- Compliance ready

### Performance Critical (`performance_critical`)
When every millisecond counts:
- Profiling-driven optimization
- Caching strategies
- Concurrency patterns
- Resource monitoring

### Educational (`educational`)
Code optimized for learning:
- Clear explanations
- Progressive examples
- Best practices
- Common pitfalls

## Using Custom Instructions

### Method 1: Create .claude-instructions.yaml file

```bash
# Copy an example
cp examples/instructions/enterprise_python.yaml .claude-instructions.yaml

# Build with instructions
claude-code-builder build project.md
```

### Method 2: Specify in project specification

```markdown
# My Project

## Custom Instructions

Use the enterprise_python instruction set for this project.
```

### Method 3: Command line flag

```bash
claude-code-builder build project.md --instructions enterprise_python
```

## Combining Instructions

You can combine multiple instruction sets:

```python
from claude_code_builder.examples.custom_instructions import CustomInstructionsExample

# Combine startup speed with security focus
CustomInstructionsExample.combine_instructions(
    ['startup_fast', 'security_focused'],
    Path('.claude-instructions.yaml')
)
```

## Creating Custom Instructions

Create your own instructions following this structure:

```yaml
code_style:
  - Your code style rules here
  
architecture:
  - Your architecture patterns
  
testing:
  - Your testing requirements
  
# Add more categories as needed
```

## Best Practices

1. **Start Simple**: Don't over-specify initially
2. **Iterate**: Refine instructions based on results
3. **Be Specific**: Vague instructions lead to inconsistent results
4. **Prioritize**: List most important rules first
5. **Context Matters**: Different projects need different rules

## Examples in Action

See the `/examples` directory for projects built with these instructions:
- `enterprise_api/` - Built with enterprise_python instructions
- `startup_mvp/` - Built with startup_fast instructions
- `ml_pipeline/` - Built with data_science instructions
"""


def create_instruction_examples(output_dir: Path) -> None:
    """Create all instruction example files.
    
    Args:
        output_dir: Output directory
    """
    instructions_dir = output_dir / "instructions"
    instructions_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate all instruction files
    for name, config in CustomInstructionsExample.get_all_examples().items():
        # YAML format
        yaml_path = instructions_dir / f"{name}.yaml"
        CustomInstructionsExample.create_instruction_file(name, yaml_path, "yaml")
        
        # JSON format
        json_path = instructions_dir / f"{name}.json"
        CustomInstructionsExample.create_instruction_file(name, json_path, "json")
        
        # Create description file
        desc_path = instructions_dir / f"{name}.md"
        desc_path.write_text(f"""# {config['name']}

{config['description']}

## Categories

""")
        
        for category, rules in config['instructions'].items():
            desc_path.write_text(
                desc_path.read_text() + f"### {category.replace('_', ' ').title()}\n\n"
            )
            for rule in rules[:3]:  # Show first 3 rules
                desc_path.write_text(
                    desc_path.read_text() + f"- {rule}\n"
                )
            if len(rules) > 3:
                desc_path.write_text(
                    desc_path.read_text() + f"- ... and {len(rules) - 3} more\n"
                )
            desc_path.write_text(desc_path.read_text() + "\n")
    
    # Create combined examples
    combined_dir = instructions_dir / "combined"
    combined_dir.mkdir(exist_ok=True)
    
    # Startup + Security
    CustomInstructionsExample.combine_instructions(
        ['startup_fast', 'security_focused'],
        combined_dir / 'startup_secure.yaml'
    )
    
    # API + Performance
    CustomInstructionsExample.combine_instructions(
        ['web_api', 'performance_critical'],
        combined_dir / 'high_performance_api.yaml'
    )
    
    # Create README
    readme_path = instructions_dir / "README.md"
    readme_path.write_text(CustomInstructionsExample.generate_examples_readme())


if __name__ == "__main__":
    # Example usage
    output_dir = Path("generated_instructions")
    create_instruction_examples(output_dir)
    print(f"Instruction examples created in: {output_dir}")