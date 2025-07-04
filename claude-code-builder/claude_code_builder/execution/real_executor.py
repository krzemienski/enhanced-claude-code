"""Real execution implementation for Claude Code Builder."""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json

from anthropic import AsyncAnthropic
from ..models.project import ProjectSpec
from ..models.phase import Phase, Task, TaskStatus, TaskResult
from ..exceptions import ExecutionError
from ..utils.file_handler import FileHandler

logger = logging.getLogger(__name__)


class RealExecutor:
    """Executes actual project building using Claude API."""
    
    def __init__(self, api_key: str, output_dir: Path):
        """Initialize real executor with API key and output directory."""
        self.client = AsyncAnthropic(api_key=api_key)
        self.output_dir = output_dir
        self.file_handler = FileHandler()
        self.context = {
            "files_created": [],
            "previous_outputs": {},
            "project_structure": {}
        }
        
    async def execute_project(self, project_spec: ProjectSpec) -> Dict[str, Any]:
        """Execute the entire project build."""
        logger.info(f"Starting real project execution: {project_spec.metadata.name}")
        start_time = datetime.now()
        
        try:
            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate phases from specification
            phases = await self._generate_phases(project_spec)
            
            # Execute each phase
            phase_results = {}
            for i, phase in enumerate(phases):
                logger.info(f"Executing phase {i+1}/{len(phases)}: {phase['name']}")
                result = await self._execute_phase(phase, project_spec)
                phase_results[phase['id']] = result
                
            # Calculate final metrics
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "completed",
                "project": project_spec.metadata.name,
                "duration": duration,
                "phases": {
                    "total": len(phases),
                    "completed": len(phase_results),
                    "failed": 0
                },
                "files_created": len(self.context["files_created"]),
                "output_directory": str(self.output_dir),
                "results": phase_results
            }
            
        except Exception as e:
            logger.error(f"Project execution failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "project": project_spec.metadata.name,
                "duration": (datetime.now() - start_time).total_seconds()
            }
    
    async def _generate_phases(self, project_spec: ProjectSpec) -> List[Dict[str, Any]]:
        """Generate build phases from project specification."""
        prompt = f"""Analyze this project specification and generate a comprehensive build plan with phases.

Project: {project_spec.metadata.name}
Description: {project_spec.description}

Features:
{self._format_features(project_spec.features)}

Technologies:
{self._format_technologies(project_spec.technologies)}

Generate a JSON array of phases for building this project. Each phase should have:
- id: unique identifier (e.g., "setup", "core", "testing")
- name: descriptive phase name
- description: what this phase accomplishes
- tasks: array of tasks, each with:
  - name: task name
  - description: detailed task description
  - type: one of ["structure", "code", "documentation", "config", "test", "deployment"]
  - output_files: array of file paths this task will create (REQUIRED, must have actual paths)

CRITICAL REQUIREMENTS:
1. Include ALL necessary phases to build a complete, production-ready project
2. Every task MUST specify output_files with actual file paths
3. Consider the project type and structure appropriately
4. Include proper configuration files, documentation, and tests
5. Ensure logical ordering and dependencies between phases

Return ONLY a valid JSON array, no other text."""
        
        response = await self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract JSON from response
        content = response.content[0].text
        # Find JSON array in response
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            phases = json.loads(json_match.group())
            return phases
        else:
            # Fallback to basic phases
            return self._get_default_phases(project_spec)
    
    def _get_default_phases(self, project_spec: ProjectSpec) -> List[Dict[str, Any]]:
        """Get default phases for a project."""
        # Determine project type
        is_web = any(t.name.lower() in ['react', 'vue', 'angular', 'django', 'flask', 'fastapi'] 
                     for t in project_spec.technologies)
        is_cli = 'cli' in project_spec.metadata.name.lower() or 'command' in project_spec.description.lower()
        is_api = 'api' in project_spec.metadata.name.lower() or 'backend' in project_spec.description.lower()
        
        base_phases = [
            {
                "id": "setup",
                "name": "Project Setup",
                "description": "Initialize project structure and configuration",
                "tasks": [
                    {
                        "name": "Create directory structure",
                        "description": "Set up project directories",
                        "type": "structure",
                        "output_files": []
                    },
                    {
                        "name": "Create configuration files",
                        "description": "Set up project configuration",
                        "type": "config",
                        "output_files": self._get_config_files(project_spec)
                    }
                ]
            }
        ]
        
        # Add appropriate phases based on project type
        if is_web:
            base_phases.extend(self._get_web_phases(project_spec))
        elif is_api:
            base_phases.extend(self._get_api_phases(project_spec))
        elif is_cli:
            base_phases.extend(self._get_cli_phases(project_spec))
        else:
            base_phases.extend(self._get_generic_phases(project_spec))
        
        # Always add testing and documentation
        base_phases.extend([
            {
                "id": "testing",
                "name": "Testing Setup",
                "description": "Create test structure and initial tests",
                "tasks": [
                    {
                        "name": "Create test structure",
                        "description": "Set up testing framework",
                        "type": "test",
                        "output_files": self._get_test_files(project_spec)
                    }
                ]
            },
            {
                "id": "documentation",
                "name": "Documentation",
                "description": "Create project documentation",
                "tasks": [
                    {
                        "name": "Create documentation",
                        "description": "Generate README and docs",
                        "type": "documentation",
                        "output_files": ["README.md", "docs/ARCHITECTURE.md"]
                    }
                ]
            }
        ])
        
        return base_phases
    
    def _get_config_files(self, project_spec: ProjectSpec) -> List[str]:
        """Get configuration files based on project technologies."""
        config_files = [".gitignore"]
        
        # Language-specific configs
        for tech in project_spec.technologies:
            tech_lower = tech.name.lower()
            if 'python' in tech_lower:
                config_files.extend(["requirements.txt", "setup.py", "pyproject.toml"])
            elif 'node' in tech_lower or 'javascript' in tech_lower:
                config_files.extend(["package.json", ".eslintrc.json"])
            elif 'typescript' in tech_lower:
                config_files.extend(["tsconfig.json", "package.json"])
            elif 'rust' in tech_lower:
                config_files.append("Cargo.toml")
            elif 'go' in tech_lower:
                config_files.append("go.mod")
        
        # Add Docker if mentioned
        if any('docker' in tech.name.lower() for tech in project_spec.technologies):
            config_files.extend(["Dockerfile", "docker-compose.yml"])
        
        return list(set(config_files))  # Remove duplicates
    
    def _get_test_files(self, project_spec: ProjectSpec) -> List[str]:
        """Get test files based on project technologies."""
        test_files = []
        
        for tech in project_spec.technologies:
            tech_lower = tech.name.lower()
            if 'python' in tech_lower:
                test_files.extend(["tests/__init__.py", "tests/test_main.py", "pytest.ini"])
            elif 'javascript' in tech_lower or 'typescript' in tech_lower:
                test_files.extend(["tests/main.test.js", "jest.config.js"])
            elif 'rust' in tech_lower:
                test_files.append("tests/integration_test.rs")
            elif 'go' in tech_lower:
                test_files.append("main_test.go")
        
        return test_files
    
    def _get_web_phases(self, project_spec: ProjectSpec) -> List[Dict[str, Any]]:
        """Get phases for web projects."""
        return [
            {
                "id": "frontend",
                "name": "Frontend Implementation",
                "description": "Build the user interface",
                "tasks": [
                    {
                        "name": "Create components",
                        "description": "Build UI components",
                        "type": "code",
                        "output_files": ["src/components/App.js", "src/components/Header.js"]
                    },
                    {
                        "name": "Create pages",
                        "description": "Build application pages",
                        "type": "code",
                        "output_files": ["src/pages/Home.js", "src/pages/About.js"]
                    }
                ]
            },
            {
                "id": "backend",
                "name": "Backend Implementation",
                "description": "Build server and API",
                "tasks": [
                    {
                        "name": "Create API endpoints",
                        "description": "Implement REST API",
                        "type": "code",
                        "output_files": ["server/api.js", "server/routes.js"]
                    }
                ]
            }
        ]
    
    def _get_api_phases(self, project_spec: ProjectSpec) -> List[Dict[str, Any]]:
        """Get phases for API projects."""
        return [
            {
                "id": "models",
                "name": "Data Models",
                "description": "Define data structures",
                "tasks": [
                    {
                        "name": "Create models",
                        "description": "Define data models",
                        "type": "code",
                        "output_files": ["src/models.py", "src/schemas.py"]
                    }
                ]
            },
            {
                "id": "api",
                "name": "API Implementation",
                "description": "Build API endpoints",
                "tasks": [
                    {
                        "name": "Create endpoints",
                        "description": "Implement API routes",
                        "type": "code",
                        "output_files": ["src/api.py", "src/routes.py"]
                    }
                ]
            }
        ]
    
    def _get_cli_phases(self, project_spec: ProjectSpec) -> List[Dict[str, Any]]:
        """Get phases for CLI projects."""
        return [
            {
                "id": "cli",
                "name": "CLI Implementation",
                "description": "Build command-line interface",
                "tasks": [
                    {
                        "name": "Create CLI parser",
                        "description": "Build argument parser",
                        "type": "code",
                        "output_files": ["src/cli.py", "src/commands.py"]
                    }
                ]
            },
            {
                "id": "core",
                "name": "Core Logic",
                "description": "Implement core functionality",
                "tasks": [
                    {
                        "name": "Create core modules",
                        "description": "Build main logic",
                        "type": "code",
                        "output_files": ["src/core.py", "src/utils.py"]
                    }
                ]
            }
        ]
    
    def _get_generic_phases(self, project_spec: ProjectSpec) -> List[Dict[str, Any]]:
        """Get phases for generic projects."""
        return [
            {
                "id": "implementation",
                "name": "Core Implementation",
                "description": "Implement main project functionality",
                "tasks": [
                    {
                        "name": "Create main module",
                        "description": "Implement main application logic",
                        "type": "code",
                        "output_files": ["src/main.py", "src/__init__.py"]
                    },
                    {
                        "name": "Create utilities",
                        "description": "Implement helper functions",
                        "type": "code",
                        "output_files": ["src/utils.py", "src/helpers.py"]
                    }
                ]
            }
        ]
    
    async def _execute_phase(self, phase: Dict[str, Any], project_spec: ProjectSpec) -> Dict[str, Any]:
        """Execute a single phase."""
        logger.info(f"Executing phase: {phase['name']}")
        phase_start = datetime.now()
        
        task_results = []
        for task in phase['tasks']:
            result = await self._execute_task(task, project_spec, phase)
            task_results.append(result)
            
        return {
            "phase_id": phase['id'],
            "name": phase['name'],
            "status": "completed",
            "duration": (datetime.now() - phase_start).total_seconds(),
            "tasks_completed": len(task_results),
            "task_results": task_results
        }
    
    async def _execute_task(self, task: Dict[str, Any], project_spec: ProjectSpec, phase: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task."""
        logger.info(f"Executing task: {task['name']} (type: {task.get('type', 'unknown')})")
        
        task_type = task.get('type', '').lower()
        
        # Map task types to handlers
        if task_type in ['structure', 'create_directory', 'directory']:
            return await self._create_structure(task, project_spec)
        elif task_type in ['code', 'create_file', 'implementation']:
            return await self._generate_code(task, project_spec, phase)
        elif task_type in ['documentation', 'docs']:
            return await self._generate_documentation(task, project_spec)
        elif task_type in ['config', 'configuration', 'settings']:
            return await self._generate_config(task, project_spec)
        elif task_type in ['test', 'tests', 'testing']:
            return await self._generate_tests(task, project_spec)
        elif task_type in ['deployment', 'deploy']:
            return await self._generate_deployment(task, project_spec)
        else:
            # Default to code generation for unknown types
            logger.warning(f"Unknown task type '{task_type}', defaulting to code generation")
            return await self._generate_code(task, project_spec, phase)
    
    async def _create_structure(self, task: Dict[str, Any], project_spec: ProjectSpec) -> Dict[str, Any]:
        """Create directory structure."""
        # Determine directories based on output files and project type
        directories = set()
        
        # Extract directories from all tasks
        if 'output_files' in task:
            for file_path in task['output_files']:
                parent = Path(file_path).parent
                if parent != Path('.'):
                    directories.add(str(parent))
        
        # Add common directories based on project type
        for tech in project_spec.technologies:
            tech_lower = tech.name.lower()
            if 'python' in tech_lower:
                directories.update(['src', 'tests', 'docs'])
            elif 'javascript' in tech_lower or 'node' in tech_lower:
                directories.update(['src', 'tests', 'public', 'dist'])
            elif 'react' in tech_lower or 'vue' in tech_lower:
                directories.update(['src', 'src/components', 'src/pages', 'public'])
        
        # Create directories
        for dir_name in sorted(directories):
            dir_path = self.output_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            
        return {
            "status": "completed",
            "directories_created": list(directories)
        }
    
    async def _generate_code(self, task: Dict[str, Any], project_spec: ProjectSpec, phase: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code files using Claude."""
        files_created = []
        
        output_files = task.get('output_files', [])
        if not output_files:
            # Generate default files based on task name
            output_files = self._infer_output_files(task, project_spec, phase)
        
        for file_path in output_files:
            prompt = f"""Generate production-ready code for: {file_path}

Project: {project_spec.metadata.name}
Description: {project_spec.description}
Phase: {phase['name']}
Task: {task['description']}

Context:
- This is part of building: {project_spec.description}
- Technologies: {', '.join(t.name for t in project_spec.technologies)}
- Features: {self._format_features(project_spec.features)}

CRITICAL REQUIREMENTS:
1. Generate 100% PRODUCTION-READY code - NO placeholders, NO TODOs, NO stubs
2. Include ALL necessary imports at the top of the file
3. Implement ALL methods and functions completely with real logic
4. Add comprehensive error handling with try/except blocks where appropriate
5. Include proper type hints for all function parameters and return values
6. Add detailed docstrings for all classes, methods, and functions
7. Use appropriate libraries and best practices for the technology stack
8. Ensure the code is immediately runnable without modifications
9. Follow language-specific conventions and style guides

Generate the complete, production-ready code now:"""
            
            response = await self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            code_content = response.content[0].text
            
            # Extract code from response (remove markdown if present)
            code_content = self._extract_code(code_content)
            
            # Write file
            full_path = self.output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.file_handler.write_file(full_path, code_content)
            files_created.append(str(file_path))
            self.context["files_created"].append(str(full_path))
            
            logger.info(f"Created: {file_path}")
        
        return {
            "status": "completed",
            "files_created": files_created
        }
    
    async def _generate_documentation(self, task: Dict[str, Any], project_spec: ProjectSpec) -> Dict[str, Any]:
        """Generate documentation files."""
        files_created = []
        
        for file_path in task.get('output_files', []):
            if file_path.lower() == "readme.md":
                # Generate comprehensive README
                prompt = f"""Generate a comprehensive README.md for this project:

Project: {project_spec.metadata.name}
Description: {project_spec.description}
Technologies: {', '.join(t.name for t in project_spec.technologies)}
Features: {self._format_features(project_spec.features)}

Create a production-ready README with:
1. Clear project title and description
2. Features list with descriptions
3. Installation instructions
4. Usage examples with code snippets
5. API documentation (if applicable)
6. Configuration options
7. Testing instructions
8. Contributing guidelines
9. License information
10. Badges for build status, coverage, etc. (use placeholder URLs)

Make it professional and complete."""
                
                response = await self.client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=3000,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                content = response.content[0].text
            else:
                # Generate other documentation
                prompt = f"""Generate documentation for: {file_path}
Project: {project_spec.metadata.name}
Create comprehensive, professional documentation."""
                
                response = await self.client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                content = response.content[0].text
            
            full_path = self.output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_handler.write_file(full_path, content)
            files_created.append(str(file_path))
            self.context["files_created"].append(str(full_path))
            
        return {
            "status": "completed",
            "files_created": files_created
        }
    
    async def _generate_config(self, task: Dict[str, Any], project_spec: ProjectSpec) -> Dict[str, Any]:
        """Generate configuration files."""
        files_created = []
        
        for file_path in task.get('output_files', []):
            # Generate appropriate config based on file type
            file_name = Path(file_path).name.lower()
            
            if file_name == "requirements.txt":
                # Extract Python dependencies
                content = self._generate_requirements(project_spec)
            elif file_name == "package.json":
                content = self._generate_package_json(project_spec)
            elif file_name == ".gitignore":
                content = self._generate_gitignore(project_spec)
            elif file_name == "dockerfile":
                content = await self._generate_dockerfile(project_spec)
            else:
                # Generate generic config
                content = await self._generate_generic_config(file_path, project_spec)
            
            full_path = self.output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_handler.write_file(full_path, content)
            files_created.append(str(file_path))
            self.context["files_created"].append(str(full_path))
            
        return {
            "status": "completed",
            "files_created": files_created
        }
    
    async def _generate_tests(self, task: Dict[str, Any], project_spec: ProjectSpec) -> Dict[str, Any]:
        """Generate test files."""
        files_created = []
        
        for file_path in task.get('output_files', []):
            if "__init__.py" in file_path:
                content = '"""Test package."""\n'
            else:
                prompt = f"""Generate comprehensive test file for: {file_path}

Project: {project_spec.metadata.name}
Description: {project_spec.description}

REQUIREMENTS:
1. Generate REAL, RUNNABLE tests - NO placeholders or TODOs
2. Include multiple test cases covering different scenarios
3. Test both success and failure cases
4. Use appropriate testing framework (pytest for Python, jest for JS, etc.)
5. Include fixtures and test data setup
6. Add edge case testing
7. Include integration tests where appropriate
8. Ensure tests are immediately runnable

Generate production-ready test code:"""
                
                response = await self.client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=3000,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                content = self._extract_code(response.content[0].text)
            
            full_path = self.output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.file_handler.write_file(full_path, content)
            files_created.append(str(file_path))
            self.context["files_created"].append(str(full_path))
            
        return {
            "status": "completed",
            "files_created": files_created
        }
    
    async def _generate_deployment(self, task: Dict[str, Any], project_spec: ProjectSpec) -> Dict[str, Any]:
        """Generate deployment configuration."""
        files_created = []
        
        for file_path in task.get('output_files', []):
            prompt = f"""Generate deployment configuration for: {file_path}
Project: {project_spec.metadata.name}
Technologies: {', '.join(t.name for t in project_spec.technologies)}

Create production-ready deployment configuration."""
            
            response = await self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            full_path = self.output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.file_handler.write_file(full_path, content)
            files_created.append(str(file_path))
            self.context["files_created"].append(str(full_path))
            
        return {
            "status": "completed",
            "files_created": files_created
        }
    
    def _infer_output_files(self, task: Dict[str, Any], project_spec: ProjectSpec, phase: Dict[str, Any]) -> List[str]:
        """Infer output files when not specified."""
        task_name = task.get('name', '').lower()
        phase_id = phase.get('id', '')
        
        # Python project patterns
        if any('python' in t.name.lower() for t in project_spec.technologies):
            if 'main' in task_name or 'entry' in task_name:
                return ['src/main.py', 'src/__init__.py']
            elif 'api' in task_name:
                return ['src/api.py', 'src/routes.py']
            elif 'model' in task_name:
                return ['src/models.py']
            elif 'util' in task_name:
                return ['src/utils.py']
        
        # JavaScript/Node patterns
        if any(t.name.lower() in ['javascript', 'node', 'react', 'vue'] for t in project_spec.technologies):
            if 'main' in task_name or 'entry' in task_name:
                return ['src/index.js', 'src/app.js']
            elif 'component' in task_name:
                return ['src/components/App.js']
            elif 'api' in task_name:
                return ['src/api/index.js']
        
        # Default fallback
        return [f"src/{phase_id}.py"]
    
    def _extract_code(self, content: str) -> str:
        """Extract code from Claude's response."""
        # Remove markdown code blocks if present
        import re
        
        # Try to find code block with language
        patterns = [
            r'```(?:python|javascript|typescript|rust|go|java|cpp|c|bash|shell)\n(.*?)\n```',
            r'```\n(.*?)\n```',
            r'`(.*?)`'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1)
        
        # If no code block found, return content as-is
        return content
    
    def _format_features(self, features: List[Any]) -> str:
        """Format features for prompt."""
        if not features:
            return "No specific features defined"
        return "\n".join(f"- {f.name}: {f.description}" for f in features)
    
    def _format_technologies(self, technologies: List[Any]) -> str:
        """Format technologies for prompt."""
        if not technologies:
            return "No specific technologies defined"
        return "\n".join(f"- {t.name} {t.version if hasattr(t, 'version') else ''}" for t in technologies)
    
    def _generate_requirements(self, project_spec: ProjectSpec) -> str:
        """Generate requirements.txt content."""
        requirements = []
        
        for tech in project_spec.technologies:
            if hasattr(tech, 'dependencies'):
                requirements.extend(tech.dependencies)
        
        # Add common Python packages based on project type
        if any('web' in f.name.lower() or 'api' in f.name.lower() for f in project_spec.features):
            requirements.extend(['flask>=2.0.0', 'requests>=2.28.0'])
        
        if any('data' in f.name.lower() for f in project_spec.features):
            requirements.extend(['pandas>=1.5.0', 'numpy>=1.23.0'])
        
        if any('test' in f.name.lower() for f in project_spec.features):
            requirements.extend(['pytest>=7.0.0', 'pytest-cov>=4.0.0'])
        
        # Remove duplicates and sort
        requirements = sorted(set(requirements))
        
        return "\n".join(requirements) if requirements else "# No dependencies yet\n"
    
    def _generate_package_json(self, project_spec: ProjectSpec) -> str:
        """Generate package.json content."""
        package = {
            "name": project_spec.metadata.name.lower().replace(' ', '-'),
            "version": "1.0.0",
            "description": project_spec.description,
            "main": "src/index.js",
            "scripts": {
                "start": "node src/index.js",
                "test": "jest",
                "dev": "nodemon src/index.js"
            },
            "dependencies": {},
            "devDependencies": {
                "jest": "^29.0.0",
                "nodemon": "^3.0.0"
            }
        }
        
        # Add dependencies based on technologies
        for tech in project_spec.technologies:
            tech_lower = tech.name.lower()
            if 'express' in tech_lower:
                package["dependencies"]["express"] = "^4.18.0"
            elif 'react' in tech_lower:
                package["dependencies"]["react"] = "^18.0.0"
                package["dependencies"]["react-dom"] = "^18.0.0"
            elif 'vue' in tech_lower:
                package["dependencies"]["vue"] = "^3.0.0"
        
        return json.dumps(package, indent=2)
    
    def _generate_gitignore(self, project_spec: ProjectSpec) -> str:
        """Generate .gitignore content."""
        ignore_patterns = [
            "# IDE",
            ".vscode/",
            ".idea/",
            "*.swp",
            "*.swo",
            "",
            "# OS",
            ".DS_Store",
            "Thumbs.db",
            "",
            "# Logs",
            "*.log",
            "logs/",
            "",
            "# Environment",
            ".env",
            ".env.local",
            "*.env",
            ""
        ]
        
        # Add language-specific patterns
        for tech in project_spec.technologies:
            tech_lower = tech.name.lower()
            if 'python' in tech_lower:
                ignore_patterns.extend([
                    "# Python",
                    "__pycache__/",
                    "*.py[cod]",
                    "*$py.class",
                    "*.so",
                    ".Python",
                    "env/",
                    "venv/",
                    ".venv",
                    "pip-log.txt",
                    ".pytest_cache/",
                    ".coverage",
                    "htmlcov/",
                    "dist/",
                    "build/",
                    "*.egg-info/",
                    ""
                ])
            elif 'node' in tech_lower or 'javascript' in tech_lower:
                ignore_patterns.extend([
                    "# Node",
                    "node_modules/",
                    "npm-debug.log*",
                    "yarn-debug.log*",
                    "yarn-error.log*",
                    ".npm",
                    "dist/",
                    "build/",
                    ""
                ])
        
        return "\n".join(ignore_patterns)
    
    async def _generate_dockerfile(self, project_spec: ProjectSpec) -> str:
        """Generate Dockerfile content."""
        prompt = f"""Generate a production-ready Dockerfile for:
Project: {project_spec.metadata.name}
Technologies: {', '.join(t.name for t in project_spec.technologies)}

Create a complete, optimized Dockerfile with:
1. Appropriate base image
2. Multi-stage build if beneficial
3. Security best practices
4. Proper caching layers
5. Non-root user
6. Health checks
"""
        
        response = await self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    
    async def _generate_generic_config(self, file_path: str, project_spec: ProjectSpec) -> str:
        """Generate generic configuration file."""
        prompt = f"""Generate configuration file: {file_path}
Project: {project_spec.metadata.name}
Technologies: {', '.join(t.name for t in project_spec.technologies)}

Create appropriate configuration with sensible defaults."""
        
        response = await self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text