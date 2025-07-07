"""User guide generator for Claude Code Builder."""
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from ..utils.template_engine import TemplateEngine
from ..config.settings import BuilderConfig
from ..models.project import ProjectSpec
from ..__init__ import __version__


class UserGuideGenerator:
    """Generate user guides and tutorials."""
    
    def __init__(self, template_engine: Optional[TemplateEngine] = None):
        """Initialize user guide generator.
        
        Args:
            template_engine: Template engine instance
        """
        self.template_engine = template_engine or TemplateEngine()
        
    def generate_user_guide(
        self,
        output_path: Path,
        config: Optional[BuilderConfig] = None
    ) -> Path:
        """Generate comprehensive user guide.
        
        Args:
            output_path: Output file path
            config: Builder configuration
            
        Returns:
            Path to generated guide
        """
        template = self._get_user_guide_template()
        
        context = {
            'version': __version__,
            'generated_at': datetime.now().strftime('%Y-%m-%d'),
            'sections': self._get_guide_sections(),
            'tutorials': self._get_tutorials(),
            'faqs': self._get_faqs(),
            'troubleshooting': self._get_troubleshooting(),
            'best_practices': self._get_best_practices()
        }
        
        content = self.template_engine.render(template, context)
        output_path.write_text(content)
        
        return output_path
    
    def generate_quickstart_guide(self, output_path: Path) -> Path:
        """Generate quick start guide.
        
        Args:
            output_path: Output file path
            
        Returns:
            Path to generated guide
        """
        template = self._get_quickstart_template()
        
        context = {
            'version': __version__,
            'steps': self._get_quickstart_steps(),
            'examples': self._get_quickstart_examples()
        }
        
        content = self.template_engine.render(template, context)
        output_path.write_text(content)
        
        return output_path
    
    def generate_tutorial(
        self,
        tutorial_name: str,
        output_path: Path,
        difficulty: str = "beginner"
    ) -> Path:
        """Generate a specific tutorial.
        
        Args:
            tutorial_name: Tutorial identifier
            output_path: Output file path
            difficulty: Tutorial difficulty level
            
        Returns:
            Path to generated tutorial
        """
        tutorials = {
            'first_project': self._get_first_project_tutorial(),
            'cli_tool': self._get_cli_tool_tutorial(),
            'web_api': self._get_web_api_tutorial(),
            'full_stack': self._get_full_stack_tutorial(),
            'mcp_integration': self._get_mcp_tutorial(),
            'custom_instructions': self._get_custom_instructions_tutorial(),
            'plugin_development': self._get_plugin_tutorial()
        }
        
        if tutorial_name not in tutorials:
            raise ValueError(f"Unknown tutorial: {tutorial_name}")
        
        tutorial_data = tutorials[tutorial_name]
        template = self._get_tutorial_template()
        
        context = {
            'title': tutorial_data['title'],
            'difficulty': difficulty,
            'duration': tutorial_data['duration'],
            'prerequisites': tutorial_data['prerequisites'],
            'objectives': tutorial_data['objectives'],
            'steps': tutorial_data['steps'],
            'summary': tutorial_data['summary'],
            'next_steps': tutorial_data['next_steps']
        }
        
        content = self.template_engine.render(template, context)
        output_path.write_text(content)
        
        return output_path
    
    def _get_user_guide_template(self) -> str:
        """Get user guide template.
        
        Returns:
            Template string
        """
        return '''# Claude Code Builder User Guide

Version {{ version }} - Generated {{ generated_at }}

## Table of Contents

{% for section in sections %}
{{ loop.index }}. [{{ section.title }}](#{{ section.id }})
{% endfor %}

---

{% for section in sections %}
## {{ section.title }}

{{ section.content }}

{% if section.subsections %}
{% for subsection in section.subsections %}
### {{ subsection.title }}

{{ subsection.content }}

{% endfor %}
{% endif %}

---

{% endfor %}

## Tutorials

{% for tutorial in tutorials %}
### {{ tutorial.title }}

**Difficulty**: {{ tutorial.difficulty }}  
**Duration**: {{ tutorial.duration }}

{{ tutorial.description }}

[Start Tutorial →](tutorials/{{ tutorial.id }}.md)

{% endfor %}

## Frequently Asked Questions

{% for faq in faqs %}
### Q: {{ faq.question }}

**A**: {{ faq.answer }}

{% if faq.example %}
Example:
```{{ faq.language | default("bash") }}
{{ faq.example }}
```
{% endif %}

{% endfor %}

## Troubleshooting

{% for issue in troubleshooting %}
### {{ issue.problem }}

**Symptoms**: {{ issue.symptoms }}

**Solution**: {{ issue.solution }}

{% if issue.prevention %}
**Prevention**: {{ issue.prevention }}
{% endif %}

{% endfor %}

## Best Practices

{% for practice in best_practices %}
### {{ practice.title }}

{{ practice.description }}

{% if practice.dos %}
**Do:**
{% for do in practice.dos %}
- {{ do }}
{% endfor %}
{% endif %}

{% if practice.donts %}
**Don't:**
{% for dont in practice.donts %}
- {{ dont }}
{% endfor %}
{% endif %}

{% endfor %}

---

For more information, visit the [official documentation](https://github.com/yourusername/claude-code-builder).
'''
    
    def _get_quickstart_template(self) -> str:
        """Get quickstart template.
        
        Returns:
            Template string
        """
        return '''# Quick Start Guide

Get up and running with Claude Code Builder in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- Anthropic API key
- Git (optional but recommended)

## Installation

```bash
pip install claude-code-builder
```

## Configuration

Set your API key:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Your First Project

{% for step in steps %}
### Step {{ loop.index }}: {{ step.title }}

{{ step.description }}

```{{ step.language | default("bash") }}
{{ step.code }}
```

{% if step.note %}
**Note**: {{ step.note }}
{% endif %}

{% endfor %}

## Example Projects

{% for example in examples %}
### {{ example.name }}

{{ example.description }}

**Specification** (`{{ example.filename }}`):
```markdown
{{ example.specification }}
```

**Build Command**:
```bash
{{ example.command }}
```

**Expected Output**:
{{ example.output }}

{% endfor %}

## Next Steps

- Read the [User Guide](user_guide.md) for detailed information
- Explore [example projects](../examples/)
- Learn about [custom instructions](tutorials/custom_instructions.md)
- Join our [community](https://github.com/yourusername/claude-code-builder/discussions)

Happy building! 🚀
'''
    
    def _get_tutorial_template(self) -> str:
        """Get tutorial template.
        
        Returns:
            Template string
        """
        return '''# Tutorial: {{ title }}

**Difficulty**: {{ difficulty }}  
**Estimated Duration**: {{ duration }}

## Prerequisites

{% for prereq in prerequisites %}
- {{ prereq }}
{% endfor %}

## Learning Objectives

By the end of this tutorial, you will:

{% for objective in objectives %}
- {{ objective }}
{% endfor %}

## Tutorial Steps

{% for step in steps %}
### Step {{ loop.index }}: {{ step.title }}

{{ step.description }}

{% if step.code %}
```{{ step.language | default("bash") }}
{{ step.code }}
```
{% endif %}

{% if step.explanation %}
**Explanation**: {{ step.explanation }}
{% endif %}

{% if step.checkpoint %}
**Checkpoint**: {{ step.checkpoint }}
{% endif %}

{% if step.troubleshooting %}
**Common Issues**:
{% for issue in step.troubleshooting %}
- **Problem**: {{ issue.problem }}
  **Solution**: {{ issue.solution }}
{% endfor %}
{% endif %}

{% endfor %}

## Summary

{{ summary }}

## Next Steps

{% for next in next_steps %}
- {{ next }}
{% endfor %}

---

[← Back to Tutorials](../tutorials.md) | [User Guide →](../user_guide.md)
'''
    
    def _get_guide_sections(self) -> List[Dict[str, Any]]:
        """Get user guide sections.
        
        Returns:
            List of guide sections
        """
        return [
            {
                'id': 'getting-started',
                'title': 'Getting Started',
                'content': '''Claude Code Builder is an AI-powered tool that transforms markdown specifications into complete software projects. This guide will help you understand how to use it effectively.

### What is Claude Code Builder?

Claude Code Builder uses advanced AI to:
- Analyze project specifications written in markdown
- Plan multi-phase development strategies
- Generate production-ready code
- Validate and test the generated project
- Provide comprehensive documentation

### Key Concepts

- **Project Specification**: A markdown file describing your project
- **Phases**: Development stages that build upon each other
- **MCP Servers**: Model Context Protocol servers for enhanced capabilities
- **Custom Instructions**: Project-specific guidelines for code generation
- **Validation**: Automated checks for code quality and security''',
                'subsections': [
                    {
                        'title': 'System Requirements',
                        'content': '''- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended)
- Internet connection for AI features
- Git for version control (optional)
- Docker for containerized projects (optional)'''
                    },
                    {
                        'title': 'Installation Options',
                        'content': '''**Standard Installation**:
```bash
pip install claude-code-builder
```

**Development Installation**:
```bash
git clone https://github.com/yourusername/claude-code-builder
cd claude-code-builder
pip install -e .
```

**With Optional Features**:
```bash
pip install claude-code-builder[mcp,research,ui]
```'''
                    }
                ]
            },
            {
                'id': 'writing-specifications',
                'title': 'Writing Project Specifications',
                'content': '''Project specifications are the heart of Claude Code Builder. A well-written specification leads to better generated code.''',
                'subsections': [
                    {
                        'title': 'Specification Structure',
                        'content': '''A good specification includes:

1. **Project Title and Description**
2. **Features and Requirements**
3. **Technical Constraints**
4. **Architecture Preferences**
5. **Integration Requirements**

Example structure:
```markdown
# Project Name

Brief description of what the project does.

## Features

- Feature 1: Description
- Feature 2: Description

## Technical Requirements

- Language: Python 3.8+
- Framework: FastAPI
- Database: PostgreSQL

## Architecture

Describe the desired architecture...
```'''
                    },
                    {
                        'title': 'Best Practices',
                        'content': '''- Be specific about requirements
- Include examples of desired behavior
- Specify error handling needs
- Mention performance requirements
- Define API contracts clearly
- Include security considerations'''
                    }
                ]
            },
            {
                'id': 'cli-reference',
                'title': 'CLI Command Reference',
                'content': '''Claude Code Builder provides a comprehensive command-line interface for all operations.''',
                'subsections': [
                    {
                        'title': 'Core Commands',
                        'content': '''**build** - Build a project from specification
```bash
claude-code-builder build project.md --output-dir ./myproject
```

**plan** - Generate project plan without building
```bash
claude-code-builder plan project.md --format json
```

**resume** - Resume interrupted build
```bash
claude-code-builder resume --checkpoint latest
```

**validate** - Validate specification
```bash
claude-code-builder validate project.md --strict
```'''
                    },
                    {
                        'title': 'MCP Commands',
                        'content': '''**mcp list** - List available MCP servers
```bash
claude-code-builder mcp list --installed
```

**mcp install** - Install MCP server
```bash
claude-code-builder mcp install filesystem
```

**mcp discover** - Find relevant MCP servers
```bash
claude-code-builder mcp discover project.md
```'''
                    }
                ]
            },
            {
                'id': 'configuration',
                'title': 'Configuration',
                'content': '''Claude Code Builder supports multiple configuration methods with clear precedence rules.''',
                'subsections': [
                    {
                        'title': 'Configuration Files',
                        'content': '''Supported formats:
- `.claude-code-builder.yaml` (recommended)
- `.claude-code-builder.json`
- `.claude-code-builder.toml`
- `.claude-code-builder.ini`

Example YAML configuration:
```yaml
api_key: ${ANTHROPIC_API_KEY}
model: claude-3-sonnet-20240229
max_tokens: 100000

mcp_servers:
  filesystem:
    enabled: true
  github:
    enabled: true
    token: ${GITHUB_TOKEN}

ui:
  rich: true
  theme: monokai
```'''
                    },
                    {
                        'title': 'Environment Variables',
                        'content': '''All configuration options can be set via environment variables:

```bash
export CLAUDE_CODE_BUILDER_API_KEY="sk-ant-..."
export CLAUDE_CODE_BUILDER_MODEL="claude-3-sonnet-20240229"
export CLAUDE_CODE_BUILDER_MAX_TOKENS="100000"
export CLAUDE_CODE_BUILDER_MCP_SERVERS_GITHUB_TOKEN="ghp_..."
```'''
                    }
                ]
            },
            {
                'id': 'advanced-features',
                'title': 'Advanced Features',
                'content': '''Claude Code Builder includes powerful features for complex projects.''',
                'subsections': [
                    {
                        'title': 'Custom Instructions',
                        'content': '''Add project-specific guidelines:

```yaml
# .claude-instructions.yaml
code_style:
  - Use type hints for all functions
  - Follow PEP 8 strictly
  - Add comprehensive docstrings

architecture:
  - Implement repository pattern
  - Use dependency injection
  - Separate business logic from infrastructure

testing:
  - Minimum 80% code coverage
  - Include integration tests
  - Use pytest fixtures
```'''
                    },
                    {
                        'title': 'Plugin System',
                        'content': '''Extend functionality with plugins:

```python
# myplugin.py
from claude_code_builder.cli.plugins import Plugin

class MyPlugin(Plugin):
    name = "myplugin"
    version = "1.0.0"
    
    def on_pre_build(self, context):
        print("Starting build...")
    
    def on_post_phase(self, context):
        phase = context['phase']
        print(f"Completed: {phase.name}")
```

Install and use:
```bash
claude-code-builder plugin install ./myplugin.py
```'''
                    }
                ]
            }
        ]
    
    def _get_tutorials(self) -> List[Dict[str, str]]:
        """Get available tutorials.
        
        Returns:
            List of tutorials
        """
        return [
            {
                'id': 'first_project',
                'title': 'Your First Project',
                'difficulty': 'Beginner',
                'duration': '15 minutes',
                'description': 'Learn the basics by building a simple CLI tool'
            },
            {
                'id': 'cli_tool',
                'title': 'Building a CLI Application',
                'difficulty': 'Beginner',
                'duration': '30 minutes',
                'description': 'Create a feature-rich command-line application'
            },
            {
                'id': 'web_api',
                'title': 'Creating a RESTful API',
                'difficulty': 'Intermediate',
                'duration': '45 minutes',
                'description': 'Build a complete REST API with authentication'
            },
            {
                'id': 'full_stack',
                'title': 'Full Stack Application',
                'difficulty': 'Advanced',
                'duration': '2 hours',
                'description': 'Develop a complete web application with frontend and backend'
            },
            {
                'id': 'mcp_integration',
                'title': 'Using MCP Servers',
                'difficulty': 'Intermediate',
                'duration': '30 minutes',
                'description': 'Leverage MCP servers for enhanced capabilities'
            },
            {
                'id': 'custom_instructions',
                'title': 'Custom Instructions',
                'difficulty': 'Intermediate',
                'duration': '20 minutes',
                'description': 'Guide code generation with custom rules'
            },
            {
                'id': 'plugin_development',
                'title': 'Creating Plugins',
                'difficulty': 'Advanced',
                'duration': '1 hour',
                'description': 'Extend Claude Code Builder with custom plugins'
            }
        ]
    
    def _get_faqs(self) -> List[Dict[str, str]]:
        """Get frequently asked questions.
        
        Returns:
            List of FAQs
        """
        return [
            {
                'question': 'How do I set my API key?',
                'answer': 'You can set your API key using environment variables, configuration files, or command-line arguments. The recommended approach is using an environment variable.',
                'example': 'export ANTHROPIC_API_KEY="sk-ant-api03-..."',
                'language': 'bash'
            },
            {
                'question': 'What languages are supported?',
                'answer': 'Claude Code Builder can generate code in any programming language. Popular choices include Python, JavaScript/TypeScript, Go, Rust, Java, and C++. The AI adapts to your specification requirements.'
            },
            {
                'question': 'Can I resume an interrupted build?',
                'answer': 'Yes! Claude Code Builder automatically saves checkpoints during the build process. You can resume from the latest checkpoint or a specific one.',
                'example': 'claude-code-builder resume --checkpoint latest',
                'language': 'bash'
            },
            {
                'question': 'How do I add custom coding standards?',
                'answer': 'Create a `.claude-instructions.yaml` file in your project directory with your coding standards, architectural preferences, and other guidelines.',
                'example': '''code_style:
  - Use async/await for all I/O operations
  - Implement proper error handling
  - Add type hints to all functions''',
                'language': 'yaml'
            },
            {
                'question': 'What are MCP servers?',
                'answer': 'Model Context Protocol (MCP) servers provide additional capabilities like filesystem access, GitHub integration, and web browsing. They enhance what Claude Code Builder can do during project generation.'
            },
            {
                'question': 'How do I debug build failures?',
                'answer': 'Use the --debug flag to get detailed output. Check the logs in .claude-code-builder/logs/ for more information. You can also validate your specification before building.',
                'example': 'claude-code-builder build project.md --debug',
                'language': 'bash'
            }
        ]
    
    def _get_troubleshooting(self) -> List[Dict[str, str]]:
        """Get troubleshooting guide.
        
        Returns:
            List of troubleshooting items
        """
        return [
            {
                'problem': 'API Key Not Found',
                'symptoms': 'Error message: "No API key provided"',
                'solution': 'Ensure your API key is set correctly. Check environment variables, config files, and command-line arguments in that order.',
                'prevention': 'Add your API key to your shell profile or use a .env file with python-dotenv.'
            },
            {
                'problem': 'Build Timeout',
                'symptoms': 'Build process stops responding or times out',
                'solution': 'Increase the timeout setting or break your project into smaller phases. Consider using --dry-run first to check the plan.',
                'prevention': 'Keep individual phases focused and use checkpointing for large projects.'
            },
            {
                'problem': 'Import Errors in Generated Code',
                'symptoms': 'Generated code has missing imports or circular dependencies',
                'solution': 'Add explicit architecture guidelines in your specification or custom instructions. Use the validate command before building.',
                'prevention': 'Provide clear module structure in your specification.'
            },
            {
                'problem': 'MCP Server Connection Failed',
                'symptoms': 'MCP server errors or connection timeouts',
                'solution': 'Check that the MCP server is installed and running. Verify any required authentication tokens.',
                'prevention': 'Test MCP servers individually before using in builds.'
            },
            {
                'problem': 'Out of Memory',
                'symptoms': 'Process killed or memory errors during build',
                'solution': 'Reduce max_tokens setting or process phases sequentially instead of in parallel.',
                'prevention': 'Monitor memory usage and adjust settings based on your system.'
            }
        ]
    
    def _get_best_practices(self) -> List[Dict[str, Any]]:
        """Get best practices.
        
        Returns:
            List of best practices
        """
        return [
            {
                'title': 'Writing Specifications',
                'description': 'Clear specifications lead to better generated code.',
                'dos': [
                    'Be specific about requirements and constraints',
                    'Include examples of expected behavior',
                    'Specify error handling requirements',
                    'Define clear API contracts',
                    'Mention performance requirements'
                ],
                'donts': [
                    'Use vague descriptions',
                    'Assume implicit requirements',
                    'Forget about error cases',
                    'Ignore security considerations'
                ]
            },
            {
                'title': 'Project Organization',
                'description': 'Good organization improves maintainability.',
                'dos': [
                    'Use meaningful phase names',
                    'Keep phases focused and cohesive',
                    'Document architectural decisions',
                    'Follow language-specific conventions',
                    'Include comprehensive tests'
                ],
                'donts': [
                    'Create monolithic phases',
                    'Mix concerns in single phases',
                    'Skip documentation',
                    'Ignore testing requirements'
                ]
            },
            {
                'title': 'Performance Optimization',
                'description': 'Optimize build performance for large projects.',
                'dos': [
                    'Use checkpointing for long builds',
                    'Cache dependencies when possible',
                    'Leverage MCP servers appropriately',
                    'Monitor token usage',
                    'Run validation before full builds'
                ],
                'donts': [
                    'Disable checkpointing',
                    'Use excessive max_tokens',
                    'Skip dry runs for complex projects',
                    'Ignore resource constraints'
                ]
            },
            {
                'title': 'Security Considerations',
                'description': 'Keep your projects and API keys secure.',
                'dos': [
                    'Use environment variables for secrets',
                    'Review generated code for security issues',
                    'Enable security scanning in validation',
                    'Keep dependencies updated',
                    'Use .gitignore for sensitive files'
                ],
                'donts': [
                    'Commit API keys to version control',
                    'Disable security validation',
                    'Ignore dependency vulnerabilities',
                    'Skip code review of generated output'
                ]
            }
        ]
    
    def _get_quickstart_steps(self) -> List[Dict[str, str]]:
        """Get quickstart steps.
        
        Returns:
            List of steps
        """
        return [
            {
                'title': 'Install Claude Code Builder',
                'description': 'Install the package using pip:',
                'code': 'pip install claude-code-builder',
                'language': 'bash'
            },
            {
                'title': 'Set Your API Key',
                'description': 'Configure your Anthropic API key:',
                'code': 'export ANTHROPIC_API_KEY="your-api-key-here"',
                'language': 'bash',
                'note': 'Get your API key from https://console.anthropic.com'
            },
            {
                'title': 'Create a Project Specification',
                'description': 'Write a simple specification file:',
                'code': '''# Todo CLI

A command-line todo list manager.

## Features
- Add tasks
- List tasks
- Mark tasks as complete
- Delete tasks
- Persistent storage

## Technical Requirements
- Language: Python 3.8+
- CLI framework: Click
- Storage: JSON file
- Include tests''',
                'language': 'markdown'
            },
            {
                'title': 'Build Your Project',
                'description': 'Run the build command:',
                'code': 'claude-code-builder build todo-cli.md --output-dir ./todo-cli',
                'language': 'bash'
            },
            {
                'title': 'Explore the Generated Project',
                'description': 'Navigate to your new project:',
                'code': '''cd todo-cli
ls -la
cat README.md''',
                'language': 'bash'
            }
        ]
    
    def _get_quickstart_examples(self) -> List[Dict[str, str]]:
        """Get quickstart examples.
        
        Returns:
            List of examples
        """
        return [
            {
                'name': 'Simple Web API',
                'description': 'A RESTful API with basic CRUD operations',
                'filename': 'simple-api.md',
                'specification': '''# User Management API

RESTful API for user management with authentication.

## Features
- User registration and login
- JWT authentication
- User profile CRUD operations
- Password reset functionality

## Technical Stack
- Framework: FastAPI
- Database: SQLite (dev) / PostgreSQL (prod)
- Authentication: JWT tokens
- Validation: Pydantic''',
                'command': 'claude-code-builder build simple-api.md',
                'output': '''Generated structure:
user-management-api/
├── src/
│   ├── api/
│   ├── models/
│   ├── services/
│   └── utils/
├── tests/
├── requirements.txt
├── Dockerfile
└── README.md'''
            },
            {
                'name': 'CLI Tool',
                'description': 'A command-line utility with subcommands',
                'filename': 'file-organizer.md',
                'specification': '''# File Organizer CLI

Organize files in directories based on rules.

## Features
- Organize by file type
- Organize by date
- Custom organization rules
- Dry run mode
- Undo operations

## Requirements
- Python 3.8+
- Click for CLI
- Rich for output formatting''',
                'command': 'claude-code-builder build file-organizer.md',
                'output': '''Generated structure:
file-organizer/
├── file_organizer/
│   ├── cli.py
│   ├── organizers/
│   ├── rules/
│   └── utils/
├── tests/
├── setup.py
└── README.md'''
            }
        ]
    
    def _get_first_project_tutorial(self) -> Dict[str, Any]:
        """Get first project tutorial.
        
        Returns:
            Tutorial data
        """
        return {
            'title': 'Building Your First Project',
            'duration': '15 minutes',
            'prerequisites': [
                'Claude Code Builder installed',
                'API key configured',
                'Basic command-line knowledge'
            ],
            'objectives': [
                'Understand project specifications',
                'Build a simple project',
                'Explore generated code',
                'Run and test the project'
            ],
            'steps': [
                {
                    'title': 'Create Project Specification',
                    'description': 'Create a file called `calculator.md` with a simple calculator specification.',
                    'code': '''# Calculator CLI

A simple command-line calculator.

## Features
- Basic arithmetic operations (+, -, *, /)
- Support for decimal numbers
- Error handling for division by zero
- Interactive mode and single calculation mode

## Requirements
- Python 3.8+
- No external dependencies
- Include unit tests''',
                    'language': 'markdown',
                    'explanation': 'This specification describes what we want to build. Claude Code Builder will analyze it and generate the appropriate code.'
                },
                {
                    'title': 'Build the Project',
                    'description': 'Run the build command to generate your calculator:',
                    'code': 'claude-code-builder build calculator.md --output-dir ./calculator',
                    'language': 'bash',
                    'checkpoint': 'You should see progress bars showing each phase of the build process.'
                },
                {
                    'title': 'Explore Generated Code',
                    'description': 'Look at what was generated:',
                    'code': '''cd calculator
tree  # or use 'ls -la' if tree is not installed
cat src/calculator.py''',
                    'language': 'bash',
                    'explanation': 'Claude Code Builder creates a complete project structure with source code, tests, and documentation.'
                },
                {
                    'title': 'Run the Calculator',
                    'description': 'Test your new calculator:',
                    'code': '''python -m calculator add 5 3
python -m calculator multiply 4.5 2
python -m calculator divide 10 0  # This should show error handling''',
                    'language': 'bash'
                },
                {
                    'title': 'Run Tests',
                    'description': 'Execute the generated tests:',
                    'code': '''pytest tests/
# or
python -m pytest tests/ -v''',
                    'language': 'bash',
                    'checkpoint': 'All tests should pass, demonstrating that the generated code works correctly.'
                }
            ],
            'summary': "You've successfully built your first project with Claude Code Builder! The tool analyzed your specification, planned the implementation, and generated a complete, working calculator application with tests.",
            'next_steps': [
                'Try modifying the specification to add new features',
                'Build a more complex project like a web API',
                'Learn about custom instructions to control code style',
                'Explore MCP servers for enhanced capabilities'
            ]
        }
    
    def _get_cli_tool_tutorial(self) -> Dict[str, Any]:
        """Get CLI tool tutorial.
        
        Returns:
            Tutorial data
        """
        return {
            'title': 'Building a CLI Application',
            'duration': '30 minutes',
            'prerequisites': [
                'Completed "Your First Project" tutorial',
                'Familiarity with command-line interfaces',
                'Basic Python knowledge'
            ],
            'objectives': [
                'Create a feature-rich CLI application',
                'Implement subcommands and options',
                'Add configuration management',
                'Include progress bars and rich output'
            ],
            'steps': [
                {
                    'title': 'Design the Specification',
                    'description': 'Create `task-tracker.md` with a comprehensive CLI specification:',
                    'code': '''# Task Tracker CLI

A powerful command-line task management tool.

## Features

### Core Functionality
- Add, update, and delete tasks
- List tasks with filtering and sorting
- Mark tasks as complete/incomplete
- Task priorities and due dates
- Categories and tags
- Task search

### CLI Features
- Subcommands for different operations
- Interactive mode
- Configuration file support
- Export to various formats (JSON, CSV, Markdown)
- Rich terminal output with colors
- Progress indicators for long operations

### Data Management
- Persistent storage using SQLite
- Data backup and restore
- Data migration support

## Technical Requirements
- Python 3.8+
- Click for CLI framework
- Rich for terminal UI
- SQLAlchemy for database
- Comprehensive test coverage

## Command Structure
```
task add "Task description" --priority high --due tomorrow
task list --filter "status:pending" --sort due
task complete 123
task export --format markdown
```''',
                    'language': 'markdown'
                },
                {
                    'title': 'Build with Advanced Options',
                    'description': 'Build the project with specific phases:',
                    'code': 'claude-code-builder build task-tracker.md --output-dir ./task-tracker --phases 8',
                    'language': 'bash',
                    'explanation': 'Specifying phases helps organize complex projects into logical development stages.'
                },
                {
                    'title': 'Examine the CLI Structure',
                    'description': 'Look at the generated CLI code:',
                    'code': '''cd task-tracker
cat src/cli.py  # Main CLI entry point
cat src/commands/  # Subcommands''',
                    'language': 'bash'
                },
                {
                    'title': 'Test the CLI',
                    'description': 'Try various commands:',
                    'code': '''# Get help
python -m task_tracker --help

# Add tasks
python -m task_tracker add "Write documentation" --priority high
python -m task_tracker add "Review PR" --due tomorrow

# List tasks
python -m task_tracker list
python -m task_tracker list --filter "priority:high"

# Complete a task
python -m task_tracker complete 1

# Export tasks
python -m task_tracker export --format markdown > tasks.md''',
                    'language': 'bash'
                },
                {
                    'title': 'Customize with Configuration',
                    'description': 'Create a configuration file:',
                    'code': '''# Create config directory
mkdir -p ~/.task-tracker

# Create config file
cat > ~/.task-tracker/config.yaml << EOF
default_priority: medium
date_format: "%Y-%m-%d"
output:
  colors: true
  icons: true
  
export:
  default_format: markdown
  include_completed: false
EOF''',
                    'language': 'bash'
                }
            ],
            'summary': "You've built a sophisticated CLI application with subcommands, configuration management, and rich output. This demonstrates Claude Code Builder's ability to create production-ready tools.",
            'next_steps': [
                'Add custom instructions for specific coding patterns',
                'Integrate MCP servers for enhanced functionality',
                'Create plugins to extend the CLI',
                'Build a web API version of the task tracker'
            ]
        }
    
    def _get_web_api_tutorial(self) -> Dict[str, Any]:
        """Get web API tutorial.
        
        Returns:
            Tutorial data
        """
        return {
            'title': 'Creating a RESTful API',
            'duration': '45 minutes',
            'prerequisites': [
                'Basic understanding of REST APIs',
                'Familiarity with HTTP methods',
                'Python web framework knowledge helpful'
            ],
            'objectives': [
                'Design and build a RESTful API',
                'Implement authentication and authorization',
                'Add data validation and error handling',
                'Include API documentation'
            ],
            'steps': [
                {
                    'title': 'Create API Specification',
                    'description': 'Write a comprehensive API specification:',
                    'code': '''# Blog API

A RESTful API for a blogging platform.

## Features

### Core Endpoints
- User registration and authentication
- CRUD operations for blog posts
- Comments system
- Categories and tags
- Search functionality
- User profiles

### API Features
- JWT-based authentication
- Rate limiting
- Pagination
- Filtering and sorting
- Field selection
- API versioning
- OpenAPI/Swagger documentation

### Security
- Password hashing (bcrypt)
- Input validation
- SQL injection prevention
- CORS configuration
- API key management

## Technical Stack
- Framework: FastAPI
- Database: PostgreSQL
- ORM: SQLAlchemy
- Authentication: JWT
- Validation: Pydantic
- Documentation: Auto-generated OpenAPI

## API Structure
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/posts
POST   /api/v1/posts
GET    /api/v1/posts/{id}
PUT    /api/v1/posts/{id}
DELETE /api/v1/posts/{id}
POST   /api/v1/posts/{id}/comments
```''',
                    'language': 'markdown'
                }
            ],
            'summary': 'You have created a full-featured RESTful API with authentication, validation, and documentation.',
            'next_steps': [
                'Deploy the API to a cloud platform',
                'Add GraphQL support',
                'Implement websockets for real-time features',
                'Create a frontend application'
            ]
        }
    
    def _get_full_stack_tutorial(self) -> Dict[str, Any]:
        """Get full stack tutorial.
        
        Returns:
            Tutorial data
        """
        return {
            'title': 'Full Stack Application',
            'duration': '2 hours',
            'prerequisites': [
                'Completed web API tutorial',
                'Basic frontend development knowledge',
                'Understanding of full stack architecture'
            ],
            'objectives': [
                'Build a complete web application',
                'Integrate frontend and backend',
                'Implement real-time features',
                'Deploy the application'
            ],
            'steps': [],  # Simplified for brevity
            'summary': 'You have built a complete full stack application with modern architecture.',
            'next_steps': [
                'Add CI/CD pipeline',
                'Implement monitoring and logging',
                'Scale with microservices',
                'Add mobile app support'
            ]
        }
    
    def _get_mcp_tutorial(self) -> Dict[str, Any]:
        """Get MCP tutorial.
        
        Returns:
            Tutorial data
        """
        return {
            'title': 'Using MCP Servers',
            'duration': '30 minutes',
            'prerequisites': [
                'Claude Code Builder installed',
                'Basic understanding of MCP concept'
            ],
            'objectives': [
                'Understand MCP servers',
                'Install and configure MCP servers',
                'Use MCP in project builds',
                'Create custom MCP integrations'
            ],
            'steps': [],  # Simplified for brevity
            'summary': 'You have learned how to leverage MCP servers for enhanced project capabilities.',
            'next_steps': [
                'Explore additional MCP servers',
                'Create custom MCP servers',
                'Integrate multiple MCP servers',
                'Build MCP-powered tools'
            ]
        }
    
    def _get_custom_instructions_tutorial(self) -> Dict[str, Any]:
        """Get custom instructions tutorial.
        
        Returns:
            Tutorial data
        """
        return {
            'title': 'Custom Instructions',
            'duration': '20 minutes',
            'prerequisites': [
                'Experience building projects',
                'Understanding of code style preferences'
            ],
            'objectives': [
                'Create custom instruction files',
                'Control code generation style',
                'Enforce architectural patterns',
                'Add project-specific rules'
            ],
            'steps': [],  # Simplified for brevity
            'summary': 'You can now guide code generation with custom instructions.',
            'next_steps': [
                'Create instruction templates',
                'Share instructions across projects',
                'Build instruction libraries',
                'Automate instruction generation'
            ]
        }
    
    def _get_plugin_tutorial(self) -> Dict[str, Any]:
        """Get plugin tutorial.
        
        Returns:
            Tutorial data
        """
        return {
            'title': 'Creating Plugins',
            'duration': '1 hour',
            'prerequisites': [
                'Python programming experience',
                'Understanding of Claude Code Builder architecture'
            ],
            'objectives': [
                'Understand plugin architecture',
                'Create a custom plugin',
                'Hook into build events',
                'Package and distribute plugins'
            ],
            'steps': [],  # Simplified for brevity
            'summary': 'You have created a custom plugin to extend Claude Code Builder.',
            'next_steps': [
                'Create more complex plugins',
                'Publish plugins to PyPI',
                'Build plugin ecosystems',
                'Contribute to core plugins'
            ]
        }