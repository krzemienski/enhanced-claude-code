"""Examples generator for Claude Code Builder."""
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import yaml
from datetime import datetime

from ..utils.template_engine import TemplateEngine
from ..models.project import ProjectSpec
from ..models.phase import Phase
from ..__init__ import __version__


class ExamplesGenerator:
    """Generate example projects and code snippets."""
    
    def __init__(self, template_engine: Optional[TemplateEngine] = None):
        """Initialize examples generator.
        
        Args:
            template_engine: Template engine instance
        """
        self.template_engine = template_engine or TemplateEngine()
        
    def generate_example_collection(
        self,
        output_dir: Path,
        categories: Optional[List[str]] = None
    ) -> Path:
        """Generate a collection of example projects.
        
        Args:
            output_dir: Output directory
            categories: Categories to include (default: all)
            
        Returns:
            Path to examples directory
        """
        output_dir = output_dir / 'examples'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default categories
        if categories is None:
            categories = [
                'simple',
                'cli',
                'web',
                'api',
                'data',
                'automation',
                'advanced'
            ]
        
        # Generate examples for each category
        for category in categories:
            self._generate_category_examples(output_dir, category)
        
        # Generate index
        self._generate_examples_index(output_dir)
        
        return output_dir
    
    def generate_example_project(
        self,
        example_type: str,
        output_path: Path,
        include_build_script: bool = True
    ) -> Path:
        """Generate a specific example project specification.
        
        Args:
            example_type: Type of example project
            output_path: Output file path
            include_build_script: Include build script
            
        Returns:
            Path to generated example
        """
        examples = self._get_example_definitions()
        
        if example_type not in examples:
            raise ValueError(f"Unknown example type: {example_type}")
        
        example = examples[example_type]
        
        # Generate specification
        template = self._get_specification_template()
        content = self.template_engine.render(template, example)
        
        # Write specification
        spec_path = output_path.with_suffix('.md')
        spec_path.write_text(content)
        
        # Generate build script if requested
        if include_build_script:
            script_path = output_path.with_suffix('.sh')
            script_content = self._generate_build_script(example_type, spec_path)
            script_path.write_text(script_content)
            script_path.chmod(0o755)
        
        # Generate custom instructions if applicable
        if example.get('custom_instructions'):
            instructions_path = output_path.parent / f'.claude-instructions-{example_type}.yaml'
            yaml.dump(
                example['custom_instructions'],
                instructions_path.open('w'),
                default_flow_style=False
            )
        
        return spec_path
    
    def generate_code_snippet(
        self,
        snippet_type: str,
        language: str = "python"
    ) -> str:
        """Generate a code snippet example.
        
        Args:
            snippet_type: Type of snippet
            language: Programming language
            
        Returns:
            Code snippet
        """
        snippets = self._get_code_snippets()
        
        key = f"{snippet_type}_{language}"
        if key not in snippets:
            # Try without language
            if snippet_type not in snippets:
                raise ValueError(f"Unknown snippet type: {snippet_type}")
            return snippets[snippet_type]
        
        return snippets[key]
    
    def _generate_category_examples(self, output_dir: Path, category: str) -> None:
        """Generate examples for a category.
        
        Args:
            output_dir: Output directory
            category: Example category
        """
        category_dir = output_dir / category
        category_dir.mkdir(exist_ok=True)
        
        # Get examples for category
        examples = self._get_category_examples(category)
        
        for example_name, example_data in examples.items():
            # Generate example
            example_path = category_dir / example_name
            self.generate_example_project(
                example_name,
                example_path,
                include_build_script=True
            )
            
            # Generate README for example
            readme_path = category_dir / f"{example_name}-README.md"
            readme_content = self._generate_example_readme(example_data)
            readme_path.write_text(readme_content)
    
    def _generate_examples_index(self, output_dir: Path) -> None:
        """Generate examples index.
        
        Args:
            output_dir: Output directory
        """
        template = '''# Claude Code Builder Examples

This directory contains example project specifications demonstrating various use cases and features.

## Categories

### Simple Projects
Basic examples to get started:
- `hello_world` - Minimal project example
- `calculator` - Simple calculator application
- `file_reader` - Basic file operations

### CLI Applications
Command-line interface examples:
- `task_manager` - Task management CLI
- `file_organizer` - File organization tool
- `git_helper` - Git workflow automation

### Web Applications
Web development examples:
- `blog_api` - RESTful blog API
- `todo_app` - Full stack todo application
- `auth_service` - Authentication microservice

### Data Processing
Data-focused examples:
- `data_pipeline` - ETL pipeline
- `report_generator` - Automated reporting
- `data_analyzer` - Data analysis tools

### Automation
Automation and scripting examples:
- `backup_tool` - Automated backup system
- `deployment_script` - Deployment automation
- `monitor_service` - System monitoring

### Advanced Projects
Complex, multi-component examples:
- `microservices` - Microservices architecture
- `ml_pipeline` - Machine learning pipeline
- `realtime_app` - Real-time application

## Using Examples

### Quick Start

1. Choose an example that matches your needs
2. Copy the specification file
3. Modify it for your requirements
4. Build with Claude Code Builder:

```bash
claude-code-builder build examples/simple/calculator.md
```

### With Custom Instructions

Some examples include custom instructions:

```bash
# Copy instructions
cp examples/web/blog_api/.claude-instructions.yaml .

# Build with instructions
claude-code-builder build examples/web/blog_api.md
```

### Build Scripts

Each example includes a build script:

```bash
./examples/cli/task_manager.sh
```

## Example Structure

Each example contains:
- `{name}.md` - Project specification
- `{name}.sh` - Build script
- `{name}-README.md` - Example documentation
- `.claude-instructions-{name}.yaml` - Custom instructions (if applicable)

## Contributing Examples

To contribute new examples:

1. Create a specification following the template
2. Test the build process
3. Document any special requirements
4. Submit a pull request

---

For more information, see the [User Guide](../docs/user_guide.md).
'''
        
        index_path = output_dir / 'README.md'
        index_path.write_text(template)
    
    def _get_specification_template(self) -> str:
        """Get project specification template.
        
        Returns:
            Template string
        """
        return '''# {{ title }}

{{ description }}

{% if overview %}
## Overview

{{ overview }}
{% endif %}

## Features

{% for feature in features %}
- {{ feature }}
{% endfor %}

{% if technical_requirements %}
## Technical Requirements

{% for req in technical_requirements %}
- {{ req }}
{% endfor %}
{% endif %}

{% if architecture %}
## Architecture

{{ architecture }}
{% endif %}

{% if api_endpoints %}
## API Endpoints

{% for endpoint in api_endpoints %}
- `{{ endpoint.method }} {{ endpoint.path }}` - {{ endpoint.description }}
{% endfor %}
{% endif %}

{% if data_model %}
## Data Model

{{ data_model }}
{% endif %}

{% if ui_requirements %}
## UI Requirements

{{ ui_requirements }}
{% endif %}

{% if integration_requirements %}
## Integration Requirements

{% for integration in integration_requirements %}
- {{ integration }}
{% endfor %}
{% endif %}

{% if performance_requirements %}
## Performance Requirements

{% for req in performance_requirements %}
- {{ req }}
{% endfor %}
{% endif %}

{% if security_requirements %}
## Security Requirements

{% for req in security_requirements %}
- {{ req }}
{% endfor %}
{% endif %}

{% if testing_requirements %}
## Testing Requirements

{% for req in testing_requirements %}
- {{ req }}
{% endfor %}
{% endif %}

{% if deployment %}
## Deployment

{{ deployment }}
{% endif %}

{% if additional_notes %}
## Additional Notes

{{ additional_notes }}
{% endif %}
'''
    
    def _generate_build_script(self, example_type: str, spec_path: Path) -> str:
        """Generate build script for example.
        
        Args:
            example_type: Type of example
            spec_path: Path to specification
            
        Returns:
            Build script content
        """
        return f'''#!/bin/bash
# Build script for {example_type} example
# Generated by Claude Code Builder v{__version__}

set -e

# Colors for output
GREEN='\\033[0;32m'
BLUE='\\033[0;34m'
RED='\\033[0;31m'
NC='\\033[0m' # No Color

echo -e "${{BLUE}}Building {example_type} example...${{NC}}"

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${{RED}}Error: ANTHROPIC_API_KEY not set${{NC}}"
    echo "Please set your API key:"
    echo "  export ANTHROPIC_API_KEY='your-key-here'"
    exit 1
fi

# Set output directory
OUTPUT_DIR="./{example_type}-output"

# Clean previous build
if [ -d "$OUTPUT_DIR" ]; then
    echo -e "${{BLUE}}Cleaning previous build...${{NC}}"
    rm -rf "$OUTPUT_DIR"
fi

# Build the project
echo -e "${{BLUE}}Running Claude Code Builder...${{NC}}"
claude-code-builder build "{spec_path.name}" \\
    --output-dir "$OUTPUT_DIR" \\
    --no-color \\
    "$@"  # Pass any additional arguments

# Check if build succeeded
if [ $? -eq 0 ]; then
    echo -e "${{GREEN}}Build completed successfully!${{NC}}"
    echo -e "${{BLUE}}Project generated at: $OUTPUT_DIR${{NC}}"
    
    # Show next steps
    echo -e "\\n${{BLUE}}Next steps:${{NC}}"
    echo "  cd $OUTPUT_DIR"
    echo "  cat README.md"
    
    # Language-specific instructions
    if [ -f "$OUTPUT_DIR/requirements.txt" ]; then
        echo "  pip install -r requirements.txt"
    elif [ -f "$OUTPUT_DIR/package.json" ]; then
        echo "  npm install"
    elif [ -f "$OUTPUT_DIR/go.mod" ]; then
        echo "  go mod download"
    fi
else
    echo -e "${{RED}}Build failed!${{NC}}"
    exit 1
fi
'''
    
    def _generate_example_readme(self, example_data: Dict[str, Any]) -> str:
        """Generate README for an example.
        
        Args:
            example_data: Example data
            
        Returns:
            README content
        """
        template = '''# {{ title }} Example

{{ description }}

## What This Example Demonstrates

{% for point in demonstrates %}
- {{ point }}
{% endfor %}

## Prerequisites

{% for prereq in prerequisites %}
- {{ prereq }}
{% endfor %}

## Building the Example

### Quick Build

```bash
./{{ name }}.sh
```

### Manual Build

```bash
claude-code-builder build {{ name }}.md --output-dir ./output
```

### With Custom Options

```bash
# Specify phases
claude-code-builder build {{ name }}.md --phases {{ phases | default(6) }}

# Skip research
claude-code-builder build {{ name }}.md --no-research

# Dry run
claude-code-builder build {{ name }}.md --dry-run
```

## Project Structure

After building, you'll have:

```
{{ structure }}
```

## Key Files

{% for file in key_files %}
- `{{ file.path }}` - {{ file.description }}
{% endfor %}

## Customization

To customize this example:

1. **Modify the specification** - Edit `{{ name }}.md`
2. **Add custom instructions** - Create `.claude-instructions.yaml`
3. **Change requirements** - Update technical requirements section
4. **Extend features** - Add new features to the specification

## Common Modifications

{% for mod in modifications %}
### {{ mod.title }}

{{ mod.description }}

```{{ mod.language | default("markdown") }}
{{ mod.code }}
```

{% endfor %}

## Troubleshooting

{% for issue in troubleshooting %}
### {{ issue.problem }}

**Solution**: {{ issue.solution }}

{% endfor %}

## Learn More

- [User Guide](../../docs/user_guide.md)
- [API Documentation](../../docs/api/)
- [More Examples](../)
'''
        
        return self.template_engine.render(template, example_data)
    
    def _get_example_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get all example definitions.
        
        Returns:
            Dictionary of example definitions
        """
        return {
            'hello_world': {
                'title': 'Hello World',
                'description': 'The simplest possible project to test your setup.',
                'features': [
                    'Print "Hello, World!"',
                    'Accept name parameter',
                    'Include unit test'
                ],
                'technical_requirements': [
                    'Python 3.8+',
                    'No external dependencies'
                ]
            },
            'calculator': {
                'title': 'Calculator CLI',
                'description': 'A command-line calculator with basic operations.',
                'features': [
                    'Basic arithmetic operations (+, -, *, /)',
                    'Support for decimal numbers',
                    'Error handling',
                    'Interactive and single-operation modes',
                    'Operation history'
                ],
                'technical_requirements': [
                    'Python 3.8+',
                    'Click for CLI',
                    'Comprehensive tests'
                ]
            },
            'task_manager': {
                'title': 'Task Manager CLI',
                'description': 'A feature-rich command-line task management tool.',
                'features': [
                    'Add, update, and delete tasks',
                    'Task priorities and due dates',
                    'Categories and tags',
                    'Search and filter tasks',
                    'Export to multiple formats',
                    'Data persistence with SQLite'
                ],
                'technical_requirements': [
                    'Python 3.8+',
                    'Click for CLI',
                    'Rich for terminal UI',
                    'SQLAlchemy for database',
                    'Pydantic for validation'
                ],
                'custom_instructions': {
                    'code_style': [
                        'Use type hints for all functions',
                        'Follow PEP 8 strictly',
                        'Add comprehensive docstrings'
                    ],
                    'architecture': [
                        'Separate business logic from CLI',
                        'Use repository pattern for data access',
                        'Implement proper error handling'
                    ]
                }
            },
            'blog_api': {
                'title': 'Blog REST API',
                'description': 'A RESTful API for a blogging platform with authentication.',
                'features': [
                    'User authentication with JWT',
                    'CRUD operations for posts',
                    'Comments system',
                    'Categories and tags',
                    'Search functionality',
                    'API documentation'
                ],
                'technical_requirements': [
                    'Python 3.8+',
                    'FastAPI framework',
                    'PostgreSQL database',
                    'SQLAlchemy ORM',
                    'Alembic for migrations',
                    'pytest for testing'
                ],
                'api_endpoints': [
                    {
                        'method': 'POST',
                        'path': '/api/auth/register',
                        'description': 'Register new user'
                    },
                    {
                        'method': 'POST',
                        'path': '/api/auth/login',
                        'description': 'Login user'
                    },
                    {
                        'method': 'GET',
                        'path': '/api/posts',
                        'description': 'List posts with pagination'
                    },
                    {
                        'method': 'POST',
                        'path': '/api/posts',
                        'description': 'Create new post'
                    },
                    {
                        'method': 'GET',
                        'path': '/api/posts/{id}',
                        'description': 'Get post details'
                    }
                ],
                'security_requirements': [
                    'Password hashing with bcrypt',
                    'JWT token expiration',
                    'Rate limiting',
                    'Input validation',
                    'SQL injection prevention'
                ]
            },
            'data_pipeline': {
                'title': 'Data Processing Pipeline',
                'description': 'An ETL pipeline for processing data from multiple sources.',
                'features': [
                    'Extract data from CSV, JSON, and APIs',
                    'Transform data with configurable rules',
                    'Load to multiple destinations',
                    'Error handling and retry logic',
                    'Progress tracking',
                    'Scheduling support'
                ],
                'technical_requirements': [
                    'Python 3.8+',
                    'Apache Airflow for orchestration',
                    'Pandas for data processing',
                    'SQLAlchemy for database operations',
                    'Redis for caching',
                    'Docker for deployment'
                ],
                'architecture': '''The pipeline follows a modular architecture:

1. **Extractors** - Modules for different data sources
2. **Transformers** - Data cleaning and transformation
3. **Validators** - Data quality checks
4. **Loaders** - Output to various destinations
5. **Orchestrator** - Manages pipeline execution'''
            },
            'microservices': {
                'title': 'Microservices Architecture',
                'description': 'A microservices-based e-commerce platform.',
                'features': [
                    'User service with authentication',
                    'Product catalog service',
                    'Order management service',
                    'Payment processing service',
                    'API Gateway',
                    'Service discovery',
                    'Message queue integration'
                ],
                'technical_requirements': [
                    'Python 3.8+ / Node.js for services',
                    'Docker and Kubernetes',
                    'RabbitMQ for messaging',
                    'Redis for caching',
                    'PostgreSQL for data',
                    'NGINX for API Gateway',
                    'Prometheus for monitoring'
                ],
                'architecture': '''Microservices communicate via:

- **Synchronous**: REST APIs for real-time operations
- **Asynchronous**: Message queues for events
- **Service Mesh**: Istio for traffic management

Each service has its own:
- Database (database per service pattern)
- API documentation
- Test suite
- Deployment configuration''',
                'deployment': '''Deploy using Kubernetes:

```bash
# Build images
docker-compose build

# Deploy to k8s
kubectl apply -f k8s/

# Check status
kubectl get pods -n ecommerce
```'''
            }
        }
    
    def _get_category_examples(self, category: str) -> Dict[str, Dict[str, Any]]:
        """Get examples for a specific category.
        
        Args:
            category: Example category
            
        Returns:
            Dictionary of examples
        """
        all_examples = self._get_example_definitions()
        
        category_mapping = {
            'simple': ['hello_world', 'calculator', 'file_reader'],
            'cli': ['task_manager', 'file_organizer', 'git_helper'],
            'web': ['blog_api', 'todo_app', 'auth_service'],
            'api': ['blog_api', 'graphql_api', 'websocket_server'],
            'data': ['data_pipeline', 'report_generator', 'data_analyzer'],
            'automation': ['backup_tool', 'deployment_script', 'monitor_service'],
            'advanced': ['microservices', 'ml_pipeline', 'realtime_app']
        }
        
        example_names = category_mapping.get(category, [])
        
        # Add example metadata
        examples = {}
        for name in example_names:
            if name in all_examples:
                example = all_examples[name].copy()
                example['name'] = name
                example['demonstrates'] = self._get_example_demonstrations(name)
                example['prerequisites'] = self._get_example_prerequisites(name)
                example['structure'] = self._get_example_structure(name)
                example['key_files'] = self._get_example_key_files(name)
                example['modifications'] = self._get_example_modifications(name)
                example['troubleshooting'] = self._get_example_troubleshooting(name)
                examples[name] = example
        
        return examples
    
    def _get_example_demonstrations(self, example_name: str) -> List[str]:
        """Get what an example demonstrates.
        
        Args:
            example_name: Example name
            
        Returns:
            List of demonstrations
        """
        demonstrations = {
            'hello_world': [
                'Basic project structure',
                'Entry point creation',
                'Simple testing setup'
            ],
            'calculator': [
                'CLI argument parsing',
                'Error handling',
                'Unit testing',
                'Code organization'
            ],
            'task_manager': [
                'Complex CLI with subcommands',
                'Database integration',
                'Rich terminal output',
                'Configuration management',
                'Data export functionality'
            ],
            'blog_api': [
                'RESTful API design',
                'Authentication implementation',
                'Database relationships',
                'API documentation',
                'Security best practices'
            ],
            'data_pipeline': [
                'ETL architecture',
                'Error handling and retries',
                'Progress monitoring',
                'Modular design',
                'Configuration-driven processing'
            ],
            'microservices': [
                'Service decomposition',
                'Inter-service communication',
                'Container orchestration',
                'API Gateway pattern',
                'Distributed system design'
            ]
        }
        
        return demonstrations.get(example_name, [
            'Project structure',
            'Code organization',
            'Testing approach'
        ])
    
    def _get_example_prerequisites(self, example_name: str) -> List[str]:
        """Get prerequisites for an example.
        
        Args:
            example_name: Example name
            
        Returns:
            List of prerequisites
        """
        base_prereqs = [
            'Claude Code Builder installed',
            'API key configured'
        ]
        
        specific_prereqs = {
            'hello_world': [],
            'calculator': ['Basic Python knowledge'],
            'task_manager': [
                'Understanding of CLI applications',
                'Basic SQL knowledge'
            ],
            'blog_api': [
                'REST API concepts',
                'Basic database knowledge',
                'Understanding of authentication'
            ],
            'data_pipeline': [
                'ETL concepts',
                'Data processing experience',
                'Docker basics'
            ],
            'microservices': [
                'Microservices architecture knowledge',
                'Docker and Kubernetes experience',
                'Distributed systems concepts'
            ]
        }
        
        return base_prereqs + specific_prereqs.get(example_name, [])
    
    def _get_example_structure(self, example_name: str) -> str:
        """Get expected project structure.
        
        Args:
            example_name: Example name
            
        Returns:
            Structure diagram
        """
        structures = {
            'hello_world': '''hello_world/
├── src/
│   └── main.py
├── tests/
│   └── test_main.py
├── README.md
└── requirements.txt''',
            
            'calculator': '''calculator/
├── calculator/
│   ├── __init__.py
│   ├── cli.py
│   ├── operations.py
│   └── calculator.py
├── tests/
│   ├── test_operations.py
│   └── test_cli.py
├── README.md
├── setup.py
└── requirements.txt''',
            
            'task_manager': '''task_manager/
├── task_manager/
│   ├── __init__.py
│   ├── cli.py
│   ├── commands/
│   ├── models/
│   ├── database.py
│   └── config.py
├── tests/
├── README.md
└── requirements.txt''',
            
            'blog_api': '''blog_api/
├── app/
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── database.py
│   └── main.py
├── tests/
├── alembic/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt''',
            
            'microservices': '''microservices/
├── services/
│   ├── user-service/
│   ├── product-service/
│   ├── order-service/
│   └── payment-service/
├── api-gateway/
├── k8s/
├── docker-compose.yml
└── README.md'''
        }
        
        return structures.get(example_name, '''project/
├── src/
├── tests/
├── README.md
└── requirements.txt''')
    
    def _get_example_key_files(self, example_name: str) -> List[Dict[str, str]]:
        """Get key files for an example.
        
        Args:
            example_name: Example name
            
        Returns:
            List of key files
        """
        key_files = {
            'hello_world': [
                {
                    'path': 'src/main.py',
                    'description': 'Main entry point'
                },
                {
                    'path': 'tests/test_main.py',
                    'description': 'Test suite'
                }
            ],
            'calculator': [
                {
                    'path': 'calculator/cli.py',
                    'description': 'CLI interface'
                },
                {
                    'path': 'calculator/operations.py',
                    'description': 'Mathematical operations'
                },
                {
                    'path': 'tests/',
                    'description': 'Comprehensive test suite'
                }
            ],
            'task_manager': [
                {
                    'path': 'task_manager/cli.py',
                    'description': 'Main CLI entry point'
                },
                {
                    'path': 'task_manager/models/',
                    'description': 'Data models'
                },
                {
                    'path': 'task_manager/database.py',
                    'description': 'Database operations'
                },
                {
                    'path': 'task_manager/config.py',
                    'description': 'Configuration management'
                }
            ],
            'blog_api': [
                {
                    'path': 'app/main.py',
                    'description': 'FastAPI application'
                },
                {
                    'path': 'app/api/',
                    'description': 'API endpoints'
                },
                {
                    'path': 'app/models/',
                    'description': 'Database models'
                },
                {
                    'path': 'docker-compose.yml',
                    'description': 'Docker configuration'
                }
            ]
        }
        
        return key_files.get(example_name, [
            {
                'path': 'src/',
                'description': 'Source code'
            },
            {
                'path': 'tests/',
                'description': 'Test suite'
            }
        ])
    
    def _get_example_modifications(self, example_name: str) -> List[Dict[str, Any]]:
        """Get common modifications for an example.
        
        Args:
            example_name: Example name
            
        Returns:
            List of modifications
        """
        modifications = {
            'calculator': [
                {
                    'title': 'Add Scientific Functions',
                    'description': 'Extend with trigonometric and logarithmic functions',
                    'code': '''## Features

- Basic arithmetic operations (+, -, *, /)
- Scientific functions (sin, cos, tan, log, exp)
- Support for constants (pi, e)
- Expression evaluation'''
                },
                {
                    'title': 'Add GUI',
                    'description': 'Create a graphical interface',
                    'code': '''## UI Requirements

- Tkinter-based GUI
- Button layout for digits and operations
- Display for current calculation
- History panel'''
                }
            ],
            'task_manager': [
                {
                    'title': 'Add Collaboration',
                    'description': 'Enable task sharing between users',
                    'code': '''## Features

- User authentication
- Task sharing and assignment
- Team workspaces
- Activity notifications'''
                },
                {
                    'title': 'Add Recurring Tasks',
                    'description': 'Support for recurring tasks',
                    'code': '''## Features

- Recurring task patterns (daily, weekly, monthly)
- Task templates
- Automatic task generation
- Recurrence editing'''
                }
            ],
            'blog_api': [
                {
                    'title': 'Add GraphQL',
                    'description': 'Add GraphQL endpoint alongside REST',
                    'code': '''## API Structure

### REST Endpoints
[existing endpoints]

### GraphQL Endpoint
- POST /graphql - GraphQL queries and mutations

## Technical Requirements
- FastAPI framework
- Strawberry GraphQL
- Shared business logic between REST and GraphQL'''
                },
                {
                    'title': 'Add Real-time Features',
                    'description': 'WebSocket support for real-time updates',
                    'code': '''## Features

- Real-time comment notifications
- Live post updates
- Online user presence
- WebSocket authentication

## Technical Requirements
- FastAPI WebSocket support
- Redis for pub/sub
- Connection management'''
                }
            ]
        }
        
        return modifications.get(example_name, [])
    
    def _get_example_troubleshooting(self, example_name: str) -> List[Dict[str, str]]:
        """Get troubleshooting items for an example.
        
        Args:
            example_name: Example name
            
        Returns:
            List of troubleshooting items
        """
        common_issues = [
            {
                'problem': 'Build fails with API error',
                'solution': 'Check your API key is set correctly and has sufficient credits'
            },
            {
                'problem': 'Dependencies not installing',
                'solution': 'Ensure you have the correct Python version and pip is up to date'
            }
        ]
        
        specific_issues = {
            'task_manager': [
                {
                    'problem': 'Database connection error',
                    'solution': 'The example uses SQLite which should work out of the box. Check file permissions in the output directory.'
                }
            ],
            'blog_api': [
                {
                    'problem': 'PostgreSQL connection fails',
                    'solution': 'Ensure PostgreSQL is running. The example includes docker-compose.yml for easy setup.'
                },
                {
                    'problem': 'Port already in use',
                    'solution': 'Change the port in the .env file or stop the conflicting service'
                }
            ],
            'microservices': [
                {
                    'problem': 'Services cannot communicate',
                    'solution': 'Check that all services are running and the service discovery is configured correctly'
                },
                {
                    'problem': 'Kubernetes deployment fails',
                    'solution': 'Ensure kubectl is configured and you have a running cluster'
                }
            ]
        }
        
        return common_issues + specific_issues.get(example_name, [])
    
    def _get_code_snippets(self) -> Dict[str, str]:
        """Get code snippet examples.
        
        Returns:
            Dictionary of code snippets
        """
        return {
            'plugin_python': '''from claude_code_builder.cli.plugins import Plugin, PluginHook

class CustomPlugin(Plugin):
    """Example plugin for Claude Code Builder."""
    
    name = "custom_plugin"
    version = "1.0.0"
    description = "Adds custom functionality to builds"
    
    def on_pre_build(self, context):
        """Called before build starts."""
        project = context['project']
        self.logger.info(f"Starting build for: {project.name}")
        
        # Add custom validation
        if not self._validate_project(project):
            raise ValueError("Project validation failed")
    
    def on_post_phase(self, context):
        """Called after each phase completes."""
        phase = context['phase']
        self.logger.info(f"Completed phase: {phase.name}")
        
        # Generate phase report
        self._generate_phase_report(phase)
    
    def on_build_complete(self, context):
        """Called when build completes successfully."""
        output_dir = context['output_dir']
        
        # Generate final report
        report_path = output_dir / 'build-report.md'
        self._generate_final_report(report_path, context)
    
    def _validate_project(self, project):
        """Custom project validation logic."""
        # Add your validation logic here
        return True
    
    def _generate_phase_report(self, phase):
        """Generate report for a phase."""
        # Add reporting logic here
        pass
    
    def _generate_final_report(self, path, context):
        """Generate final build report."""
        # Add report generation logic here
        pass
''',
            'custom_instructions_yaml': '''# Custom Instructions for Project
code_style:
  - Use type hints for all function parameters and return values
  - Follow PEP 8 style guide strictly
  - Maximum line length of 88 characters (Black formatter)
  - Use descriptive variable names, avoid abbreviations
  - Add docstrings to all public functions and classes

architecture:
  - Follow clean architecture principles
  - Separate business logic from infrastructure
  - Use dependency injection for external services
  - Implement repository pattern for data access
  - Create interfaces for all external dependencies

error_handling:
  - Never use bare except clauses
  - Log all errors with appropriate context
  - Raise custom exceptions for business logic errors
  - Implement retry logic for transient failures
  - Provide meaningful error messages to users

testing:
  - Minimum 80% code coverage
  - Write unit tests for all business logic
  - Include integration tests for API endpoints
  - Use pytest fixtures for test data
  - Mock external dependencies in unit tests

security:
  - Validate all user input
  - Use parameterized queries for database access
  - Hash passwords with bcrypt
  - Implement rate limiting for API endpoints
  - Follow OWASP security guidelines

documentation:
  - Include README with setup instructions
  - Document all API endpoints with examples
  - Add inline comments for complex logic
  - Create architecture diagrams
  - Maintain changelog for versions
''',
            'specification_template': '''# Project Name

Brief description of what the project does and its main purpose.

## Overview

Provide a more detailed explanation of the project, including:
- The problem it solves
- The target audience
- Key benefits

## Features

List all major features:
- Feature 1: Description
- Feature 2: Description
- Feature 3: Description

## Technical Requirements

### Language and Framework
- Primary language: Python 3.8+
- Web framework: FastAPI
- Database: PostgreSQL
- Cache: Redis

### External Services
- Authentication: JWT
- File storage: S3-compatible
- Email: SMTP service

### Development Tools
- Testing: pytest
- Linting: flake8, black
- Type checking: mypy

## Architecture

Describe the high-level architecture:
- API layer: RESTful endpoints
- Business logic: Service classes
- Data access: Repository pattern
- External integrations: Adapter pattern

## API Endpoints (if applicable)

### Authentication
- POST /auth/register - Register new user
- POST /auth/login - User login
- POST /auth/refresh - Refresh token

### Core Resources
- GET /resources - List resources
- POST /resources - Create resource
- GET /resources/{id} - Get resource
- PUT /resources/{id} - Update resource
- DELETE /resources/{id} - Delete resource

## Data Model

Define main entities and relationships:

### User
- id: UUID
- email: string (unique)
- password_hash: string
- created_at: datetime
- updated_at: datetime

### Resource
- id: UUID
- user_id: UUID (foreign key)
- name: string
- description: text
- created_at: datetime
- updated_at: datetime

## Security Requirements

- All passwords must be hashed
- API requires authentication
- Rate limiting on all endpoints
- Input validation and sanitization
- SQL injection prevention

## Performance Requirements

- API response time < 200ms
- Support 1000 concurrent users
- Database query optimization
- Caching for frequently accessed data

## Testing Requirements

- Unit tests for all business logic
- Integration tests for API endpoints
- Load testing for performance
- Security testing for vulnerabilities

## Deployment

- Containerized with Docker
- Environment-based configuration
- Health check endpoints
- Graceful shutdown handling

## Additional Notes

Any other important information or constraints.
'''
        }