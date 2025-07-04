#!/usr/bin/env python3
"""Generate proper phases for Awesome Researcher project."""

import json

phases = [
    {
        "id": "foundation",
        "name": "Project Foundation",
        "description": "Set up project structure, configuration, and base infrastructure",
        "tasks": [
            {
                "name": "Create project structure",
                "description": "Set up directories and package structure",
                "type": "structure",
                "output_files": []
            },
            {
                "name": "Create package files",
                "description": "Initialize Python package with proper structure",
                "type": "code",
                "output_files": [
                    "awesome_researcher/__init__.py",
                    "awesome_researcher/main.py",
                    "awesome_researcher/config.py",
                    "awesome_researcher/exceptions.py"
                ]
            },
            {
                "name": "Create configuration",
                "description": "Set up project configuration and dependencies",
                "type": "config",
                "output_files": [
                    "pyproject.toml",
                    "requirements.txt",
                    ".gitignore",
                    "Dockerfile",
                    "build-and-run.sh"
                ]
            },
            {
                "name": "Create documentation",
                "description": "Initialize project documentation",
                "type": "documentation",
                "output_files": [
                    "README.md",
                    "docs/ARCHITECTURE.md",
                    "docs/TROUBLESHOOTING.md"
                ]
            }
        ]
    },
    {
        "id": "utils",
        "name": "Utilities and Helpers",
        "description": "Implement utility modules for logging, cost tracking, and helpers",
        "tasks": [
            {
                "name": "Create utils package",
                "description": "Initialize utils package",
                "type": "code",
                "output_files": [
                    "awesome_researcher/utils/__init__.py"
                ]
            },
            {
                "name": "Implement logging utilities",
                "description": "Create comprehensive logging system",
                "type": "code",
                "output_files": [
                    "awesome_researcher/utils/logging.py"
                ]
            },
            {
                "name": "Implement cost tracking",
                "description": "Create cost tracking for API calls",
                "type": "code",
                "output_files": [
                    "awesome_researcher/utils/cost_tracking.py"
                ]
            },
            {
                "name": "Implement helpers",
                "description": "Create general helper functions",
                "type": "code",
                "output_files": [
                    "awesome_researcher/utils/helpers.py"
                ]
            }
        ]
    },
    {
        "id": "parsers",
        "name": "Parsers and Data Models",
        "description": "Implement parsers for Awesome lists and markdown files",
        "tasks": [
            {
                "name": "Create parsers package",
                "description": "Initialize parsers package",
                "type": "code",
                "output_files": [
                    "awesome_researcher/parsers/__init__.py"
                ]
            },
            {
                "name": "Implement Awesome parser",
                "description": "Create parser for Awesome list format",
                "type": "code",
                "output_files": [
                    "awesome_researcher/parsers/awesome_parser.py"
                ]
            },
            {
                "name": "Implement markdown parser",
                "description": "Create general markdown parser",
                "type": "code",
                "output_files": [
                    "awesome_researcher/parsers/markdown_parser.py"
                ]
            }
        ]
    },
    {
        "id": "core",
        "name": "Core Search and Memory",
        "description": "Implement core search memory and deduplication logic",
        "tasks": [
            {
                "name": "Create core package",
                "description": "Initialize core package",
                "type": "code",
                "output_files": [
                    "awesome_researcher/core/__init__.py"
                ]
            },
            {
                "name": "Implement search memory",
                "description": "Create search memory system with progressive refinement",
                "type": "code",
                "output_files": [
                    "awesome_researcher/core/search_memory.py"
                ]
            },
            {
                "name": "Implement deduplication",
                "description": "Create deduplication logic",
                "type": "code",
                "output_files": [
                    "awesome_researcher/core/deduplication.py"
                ]
            },
            {
                "name": "Implement quality scorer",
                "description": "Create quality scoring system",
                "type": "code",
                "output_files": [
                    "awesome_researcher/core/quality_scorer.py"
                ]
            },
            {
                "name": "Implement progressive search",
                "description": "Create progressive search refinement",
                "type": "code",
                "output_files": [
                    "awesome_researcher/core/progressive_search.py"
                ]
            }
        ]
    },
    {
        "id": "agents",
        "name": "AI Agent System",
        "description": "Implement all AI agents for research and analysis",
        "tasks": [
            {
                "name": "Create agents package",
                "description": "Initialize agents package",
                "type": "code",
                "output_files": [
                    "awesome_researcher/agents/__init__.py"
                ]
            },
            {
                "name": "Implement base agent",
                "description": "Create base agent class",
                "type": "code",
                "output_files": [
                    "awesome_researcher/agents/base_agent.py"
                ]
            },
            {
                "name": "Implement content analyzer",
                "description": "Create content analysis agent",
                "type": "code",
                "output_files": [
                    "awesome_researcher/agents/content_analyzer.py"
                ]
            },
            {
                "name": "Implement term expander",
                "description": "Create search term expansion agent",
                "type": "code",
                "output_files": [
                    "awesome_researcher/agents/term_expander.py"
                ]
            },
            {
                "name": "Implement gap analyzer",
                "description": "Create gap analysis agent",
                "type": "code",
                "output_files": [
                    "awesome_researcher/agents/gap_analyzer.py"
                ]
            },
            {
                "name": "Implement query planner",
                "description": "Create query planning agent",
                "type": "code",
                "output_files": [
                    "awesome_researcher/agents/query_planner.py"
                ]
            },
            {
                "name": "Implement search orchestrator",
                "description": "Create search orchestration agent",
                "type": "code",
                "output_files": [
                    "awesome_researcher/agents/search_orchestrator.py"
                ]
            },
            {
                "name": "Implement validator",
                "description": "Create validation agent",
                "type": "code",
                "output_files": [
                    "awesome_researcher/agents/validator.py"
                ]
            }
        ]
    },
    {
        "id": "renderers",
        "name": "Renderers and Output",
        "description": "Implement output rendering and report generation",
        "tasks": [
            {
                "name": "Create renderers package",
                "description": "Initialize renderers package",
                "type": "code",
                "output_files": [
                    "awesome_researcher/renderers/__init__.py"
                ]
            },
            {
                "name": "Implement list renderer",
                "description": "Create Awesome list renderer",
                "type": "code",
                "output_files": [
                    "awesome_researcher/renderers/list_renderer.py"
                ]
            },
            {
                "name": "Implement report generator",
                "description": "Create report generation",
                "type": "code",
                "output_files": [
                    "awesome_researcher/renderers/report_generator.py"
                ]
            },
            {
                "name": "Implement timeline visualizer",
                "description": "Create timeline visualization",
                "type": "code",
                "output_files": [
                    "awesome_researcher/renderers/timeline_visualizer.py"
                ]
            }
        ]
    },
    {
        "id": "prompts_data",
        "name": "Prompts and Data Layer",
        "description": "Implement prompt templates and data models",
        "tasks": [
            {
                "name": "Create prompts package",
                "description": "Initialize prompts package",
                "type": "code",
                "output_files": [
                    "awesome_researcher/prompts/__init__.py",
                    "awesome_researcher/prompts/templates.py"
                ]
            },
            {
                "name": "Create data package",
                "description": "Initialize data package",
                "type": "code",
                "output_files": [
                    "awesome_researcher/data/__init__.py"
                ]
            },
            {
                "name": "Implement data models",
                "description": "Create data model classes",
                "type": "code",
                "output_files": [
                    "awesome_researcher/data/models.py"
                ]
            },
            {
                "name": "Implement repositories",
                "description": "Create data repositories",
                "type": "code",
                "output_files": [
                    "awesome_researcher/data/repositories.py"
                ]
            },
            {
                "name": "Implement validators",
                "description": "Create data validators",
                "type": "code",
                "output_files": [
                    "awesome_researcher/data/validators.py"
                ]
            },
            {
                "name": "Implement migrations",
                "description": "Create database migrations",
                "type": "code",
                "output_files": [
                    "awesome_researcher/data/migrations.py"
                ]
            }
        ]
    },
    {
        "id": "testing",
        "name": "Testing and Scripts",
        "description": "Create test structure and execution scripts",
        "tasks": [
            {
                "name": "Create test structure",
                "description": "Set up test directory and files",
                "type": "test",
                "output_files": [
                    "tests/__init__.py",
                    "tests/test_parsers.py",
                    "tests/test_core.py",
                    "tests/test_agents.py"
                ]
            },
            {
                "name": "Create test scripts",
                "description": "Create end-to-end test scripts",
                "type": "code",
                "output_files": [
                    "tests/run_e2e.sh",
                    "tests/verify_logs.sh"
                ]
            },
            {
                "name": "Create run directory",
                "description": "Set up runs directory for outputs",
                "type": "structure",
                "output_files": []
            }
        ]
    }
]

# Print phases as JSON
print(json.dumps(phases, indent=2))