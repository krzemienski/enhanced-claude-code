"""
Dependency validation for project requirements.
"""
import re
import subprocess
import json
import toml
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pkg_resources
import importlib.metadata
from packaging import version
from packaging.specifiers import SpecifierSet
from packaging.requirements import Requirement

from ..models.base import SerializableModel
from ..models.validation import ValidationResult, ValidationIssue, ValidationLevel, ValidationType


class DependencyIssueType(Enum):
    """Types of dependency issues."""
    MISSING = "missing_dependency"
    VERSION_CONFLICT = "version_conflict"
    SECURITY_VULNERABILITY = "security_vulnerability"
    DEPRECATED = "deprecated_package"
    INCOMPATIBLE = "incompatible_versions"
    CIRCULAR = "circular_dependency"
    UNUSED = "unused_dependency"
    OUTDATED = "outdated_version"
    LICENSE_CONFLICT = "license_conflict"
    PLATFORM_INCOMPATIBLE = "platform_incompatible"


@dataclass
class DependencyIssue:
    """Represents a dependency issue."""
    issue_type: DependencyIssueType
    package_name: str
    current_version: Optional[str]
    required_version: Optional[str]
    description: str
    recommendation: str
    severity: str = "medium"  # critical, high, medium, low, info
    affected_files: List[str] = field(default_factory=list)
    conflicting_packages: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """String representation."""
        version_info = ""
        if self.current_version and self.required_version:
            version_info = f" (current: {self.current_version}, required: {self.required_version})"
        return f"{self.package_name}{version_info} - {self.issue_type.value}: {self.description}"


@dataclass
class DependencyInfo:
    """Information about a dependency."""
    name: str
    version: Optional[str] = None
    specifier: Optional[str] = None
    source_file: Optional[str] = None
    is_direct: bool = True
    dependencies: List[str] = field(default_factory=list)
    license: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None


@dataclass
class DependencyCheckResult(ValidationResult):
    """Result of dependency checking."""
    project_path: str = ""
    dependencies: List[DependencyInfo] = field(default_factory=list)
    issues: List[DependencyIssue] = field(default_factory=list)
    total_packages: int = 0
    direct_dependencies: int = 0
    transitive_dependencies: int = 0
    security_vulnerabilities: int = 0
    outdated_packages: int = 0
    missing_packages: int = 0
    
    @property
    def has_security_issues(self) -> bool:
        """Check if there are security vulnerabilities."""
        return any(issue.issue_type == DependencyIssueType.SECURITY_VULNERABILITY for issue in self.issues)
    
    @property
    def has_conflicts(self) -> bool:
        """Check if there are version conflicts."""
        return any(issue.issue_type == DependencyIssueType.VERSION_CONFLICT for issue in self.issues)
    
    @property
    def issue_count_by_type(self) -> Dict[DependencyIssueType, int]:
        """Count issues by type."""
        counts = {}
        for issue in self.issues:
            counts[issue.issue_type] = counts.get(issue.issue_type, 0) + 1
        return counts


class DependencyChecker:
    """Validates project dependencies."""
    
    def __init__(self):
        """Initialize dependency checker."""
        self.requirement_files = [
            'requirements.txt',
            'requirements-dev.txt',
            'requirements-test.txt',
            'setup.py',
            'setup.cfg',
            'pyproject.toml',
            'Pipfile',
            'poetry.lock',
            'package.json',
            'package-lock.json',
            'yarn.lock',
            'Gemfile',
            'Gemfile.lock',
            'go.mod',
            'go.sum',
            'Cargo.toml',
            'Cargo.lock'
        ]
        
        # Known security vulnerabilities (simplified database)
        self.vulnerability_db = {
            'requests': {'<2.20.0': 'CVE-2018-18074: Insufficient certificate verification'},
            'django': {'<2.2.24': 'Multiple security vulnerabilities'},
            'flask': {'<1.0': 'Security vulnerabilities in older versions'},
            'pyyaml': {'<5.4': 'CVE-2020-14343: Arbitrary code execution'},
            'pillow': {'<8.3.2': 'Multiple security vulnerabilities'},
            'urllib3': {'<1.26.5': 'CVE-2021-33503: Catastrophic backtracking vulnerability'},
        }
        
        # Deprecated packages
        self.deprecated_packages = {
            'nose': 'Use pytest instead',
            'pycrypto': 'Use pycryptodome instead',
            'distribute': 'Use setuptools instead',
            'PIL': 'Use Pillow instead',
        }
        
    def check_project(self, project_path: Path) -> DependencyCheckResult:
        """Check all dependencies in a project."""
        result = DependencyCheckResult(
            project_path=str(project_path),
            success=True
        )
        
        try:
            # Find all requirement files
            requirement_files = self._find_requirement_files(project_path)
            
            # Parse dependencies from each file
            all_dependencies = {}
            for req_file in requirement_files:
                deps = self._parse_requirement_file(req_file)
                for dep in deps:
                    if dep.name not in all_dependencies:
                        all_dependencies[dep.name] = dep
                    else:
                        # Check for conflicts
                        existing = all_dependencies[dep.name]
                        if existing.specifier != dep.specifier:
                            result.issues.append(DependencyIssue(
                                issue_type=DependencyIssueType.VERSION_CONFLICT,
                                package_name=dep.name,
                                current_version=existing.specifier,
                                required_version=dep.specifier,
                                description=f"Conflicting version requirements in {existing.source_file} and {dep.source_file}",
                                recommendation="Resolve version conflicts by using compatible version specifiers",
                                severity="high",
                                affected_files=[existing.source_file, dep.source_file]
                            ))
                            
            result.dependencies = list(all_dependencies.values())
            result.total_packages = len(result.dependencies)
            result.direct_dependencies = sum(1 for d in result.dependencies if d.is_direct)
            result.transitive_dependencies = result.total_packages - result.direct_dependencies
            
            # Check for various issues
            self._check_missing_dependencies(result, project_path)
            self._check_security_vulnerabilities(result)
            self._check_deprecated_packages(result)
            self._check_outdated_packages(result)
            self._check_circular_dependencies(result)
            self._check_unused_dependencies(result, project_path)
            self._check_license_compatibility(result)
            
            # Update counts
            result.security_vulnerabilities = sum(1 for i in result.issues 
                                                if i.issue_type == DependencyIssueType.SECURITY_VULNERABILITY)
            result.outdated_packages = sum(1 for i in result.issues 
                                         if i.issue_type == DependencyIssueType.OUTDATED)
            result.missing_packages = sum(1 for i in result.issues 
                                        if i.issue_type == DependencyIssueType.MISSING)
            
            # Add validation issues
            for issue in result.issues:
                level = ValidationLevel.ERROR if issue.severity in ["critical", "high"] else ValidationLevel.WARNING
                result.add_issue(ValidationIssue(
                    message=str(issue),
                    level=level,
                    validation_type=ValidationType.DEPENDENCY
                ))
                
            result.success = not result.has_security_issues and not result.has_conflicts
            
        except Exception as e:
            result.success = False
            result.add_issue(ValidationIssue(
                message=f"Dependency check failed: {str(e)}",
                level=ValidationLevel.ERROR,
                validation_type=ValidationType.DEPENDENCY
            ))
            
        return result
        
    def _find_requirement_files(self, project_path: Path) -> List[Path]:
        """Find all requirement files in the project."""
        found_files = []
        
        for req_file in self.requirement_files:
            file_path = project_path / req_file
            if file_path.exists():
                found_files.append(file_path)
                
        # Also search for requirements*.txt patterns
        for req_file in project_path.glob('requirements*.txt'):
            if req_file not in found_files:
                found_files.append(req_file)
                
        return found_files
        
    def _parse_requirement_file(self, file_path: Path) -> List[DependencyInfo]:
        """Parse dependencies from a requirement file."""
        dependencies = []
        
        if file_path.name == 'setup.py':
            dependencies.extend(self._parse_setup_py(file_path))
        elif file_path.name == 'pyproject.toml':
            dependencies.extend(self._parse_pyproject_toml(file_path))
        elif file_path.name == 'package.json':
            dependencies.extend(self._parse_package_json(file_path))
        elif file_path.suffix == '.txt':
            dependencies.extend(self._parse_requirements_txt(file_path))
        elif file_path.name == 'Pipfile':
            dependencies.extend(self._parse_pipfile(file_path))
            
        return dependencies
        
    def _parse_requirements_txt(self, file_path: Path) -> List[DependencyInfo]:
        """Parse requirements.txt file."""
        dependencies = []
        
        try:
            content = file_path.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                if line.startswith('-r '):
                    # Include another requirements file
                    included_file = file_path.parent / line[3:].strip()
                    if included_file.exists():
                        dependencies.extend(self._parse_requirements_txt(included_file))
                    continue
                    
                try:
                    req = Requirement(line)
                    dep = DependencyInfo(
                        name=req.name,
                        specifier=str(req.specifier) if req.specifier else None,
                        source_file=str(file_path)
                    )
                    dependencies.append(dep)
                except Exception:
                    # Skip invalid requirements
                    pass
                    
        except Exception:
            pass
            
        return dependencies
        
    def _parse_setup_py(self, file_path: Path) -> List[DependencyInfo]:
        """Parse setup.py file."""
        dependencies = []
        
        try:
            content = file_path.read_text()
            
            # Extract install_requires
            install_requires_match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if install_requires_match:
                requires_content = install_requires_match.group(1)
                for line in requires_content.split(','):
                    line = line.strip().strip('"\'')
                    if line:
                        try:
                            req = Requirement(line)
                            dep = DependencyInfo(
                                name=req.name,
                                specifier=str(req.specifier) if req.specifier else None,
                                source_file=str(file_path)
                            )
                            dependencies.append(dep)
                        except Exception:
                            pass
                            
        except Exception:
            pass
            
        return dependencies
        
    def _parse_pyproject_toml(self, file_path: Path) -> List[DependencyInfo]:
        """Parse pyproject.toml file."""
        dependencies = []
        
        try:
            content = file_path.read_text()
            data = toml.loads(content)
            
            # Poetry dependencies
            if 'tool' in data and 'poetry' in data['tool']:
                poetry_deps = data['tool']['poetry'].get('dependencies', {})
                for name, spec in poetry_deps.items():
                    if name == 'python':
                        continue
                    dep = DependencyInfo(
                        name=name,
                        specifier=spec if isinstance(spec, str) else None,
                        source_file=str(file_path)
                    )
                    dependencies.append(dep)
                    
            # PEP 621 dependencies
            if 'project' in data:
                project_deps = data['project'].get('dependencies', [])
                for dep_str in project_deps:
                    try:
                        req = Requirement(dep_str)
                        dep = DependencyInfo(
                            name=req.name,
                            specifier=str(req.specifier) if req.specifier else None,
                            source_file=str(file_path)
                        )
                        dependencies.append(dep)
                    except Exception:
                        pass
                        
        except Exception:
            pass
            
        return dependencies
        
    def _parse_package_json(self, file_path: Path) -> List[DependencyInfo]:
        """Parse package.json file."""
        dependencies = []
        
        try:
            content = file_path.read_text()
            data = json.loads(content)
            
            for dep_type in ['dependencies', 'devDependencies']:
                deps = data.get(dep_type, {})
                for name, version_spec in deps.items():
                    dep = DependencyInfo(
                        name=name,
                        specifier=version_spec,
                        source_file=str(file_path),
                        is_direct=True
                    )
                    dependencies.append(dep)
                    
        except Exception:
            pass
            
        return dependencies
        
    def _parse_pipfile(self, file_path: Path) -> List[DependencyInfo]:
        """Parse Pipfile."""
        dependencies = []
        
        try:
            content = file_path.read_text()
            data = toml.loads(content)
            
            for section in ['packages', 'dev-packages']:
                packages = data.get(section, {})
                for name, spec in packages.items():
                    version_spec = spec if isinstance(spec, str) else spec.get('version', '*')
                    dep = DependencyInfo(
                        name=name,
                        specifier=version_spec,
                        source_file=str(file_path),
                        is_direct=True
                    )
                    dependencies.append(dep)
                    
        except Exception:
            pass
            
        return dependencies
        
    def _check_missing_dependencies(self, result: DependencyCheckResult, project_path: Path):
        """Check for missing dependencies by analyzing imports."""
        # This is a simplified check - in reality would need more sophisticated analysis
        python_files = list(project_path.glob('**/*.py'))
        
        imported_modules = set()
        for py_file in python_files[:100]:  # Limit to avoid long processing
            try:
                content = py_file.read_text()
                # Simple regex to find imports
                import_pattern = r'(?:from\s+(\S+)|import\s+(\S+))'
                for match in re.finditer(import_pattern, content):
                    module = match.group(1) or match.group(2)
                    if module:
                        base_module = module.split('.')[0]
                        imported_modules.add(base_module)
            except Exception:
                pass
                
        # Check if imported modules are in dependencies
        declared_packages = {dep.name.lower() for dep in result.dependencies}
        stdlib_modules = {'os', 'sys', 'json', 'datetime', 'pathlib', 're', 'typing', 'dataclasses'}
        
        for module in imported_modules:
            if module.lower() not in declared_packages and module not in stdlib_modules:
                # Try to check if it's installed
                try:
                    importlib.metadata.version(module)
                except importlib.metadata.PackageNotFoundError:
                    result.issues.append(DependencyIssue(
                        issue_type=DependencyIssueType.MISSING,
                        package_name=module,
                        current_version=None,
                        required_version=None,
                        description=f"Package '{module}' is imported but not declared in dependencies",
                        recommendation=f"Add '{module}' to your requirements file",
                        severity="high"
                    ))
                    
    def _check_security_vulnerabilities(self, result: DependencyCheckResult):
        """Check for known security vulnerabilities."""
        for dep in result.dependencies:
            if dep.name.lower() in self.vulnerability_db:
                vulnerabilities = self.vulnerability_db[dep.name.lower()]
                
                # Get installed version
                try:
                    installed_version = importlib.metadata.version(dep.name)
                    
                    for vulnerable_spec, description in vulnerabilities.items():
                        spec = SpecifierSet(vulnerable_spec)
                        if version.parse(installed_version) in spec:
                            result.issues.append(DependencyIssue(
                                issue_type=DependencyIssueType.SECURITY_VULNERABILITY,
                                package_name=dep.name,
                                current_version=installed_version,
                                required_version=f">{vulnerable_spec.strip('<=')}",
                                description=description,
                                recommendation=f"Upgrade {dep.name} to a secure version",
                                severity="critical"
                            ))
                except Exception:
                    pass
                    
    def _check_deprecated_packages(self, result: DependencyCheckResult):
        """Check for deprecated packages."""
        for dep in result.dependencies:
            if dep.name.lower() in self.deprecated_packages:
                recommendation = self.deprecated_packages[dep.name.lower()]
                result.issues.append(DependencyIssue(
                    issue_type=DependencyIssueType.DEPRECATED,
                    package_name=dep.name,
                    current_version=dep.version,
                    required_version=None,
                    description=f"Package '{dep.name}' is deprecated",
                    recommendation=recommendation,
                    severity="medium"
                ))
                
    def _check_outdated_packages(self, result: DependencyCheckResult):
        """Check for outdated packages."""
        # This would typically check against PyPI or other package registries
        # For now, we'll do a simple check
        try:
            # Run pip list --outdated
            process = subprocess.run(
                ['pip', 'list', '--outdated', '--format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if process.returncode == 0 and process.stdout:
                outdated = json.loads(process.stdout)
                outdated_names = {pkg['name'].lower(): pkg for pkg in outdated}
                
                for dep in result.dependencies:
                    if dep.name.lower() in outdated_names:
                        pkg_info = outdated_names[dep.name.lower()]
                        result.issues.append(DependencyIssue(
                            issue_type=DependencyIssueType.OUTDATED,
                            package_name=dep.name,
                            current_version=pkg_info['version'],
                            required_version=pkg_info['latest_version'],
                            description=f"Package '{dep.name}' has a newer version available",
                            recommendation=f"Consider upgrading to version {pkg_info['latest_version']}",
                            severity="low"
                        ))
        except Exception:
            pass
            
    def _check_circular_dependencies(self, result: DependencyCheckResult):
        """Check for circular dependencies."""
        # Build dependency graph
        dep_graph = {}
        for dep in result.dependencies:
            dep_graph[dep.name] = dep.dependencies
            
        # DFS to find cycles
        def has_cycle(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dep_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
                    
            rec_stack.remove(node)
            return False
            
        visited = set()
        for node in dep_graph:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    result.issues.append(DependencyIssue(
                        issue_type=DependencyIssueType.CIRCULAR,
                        package_name=node,
                        current_version=None,
                        required_version=None,
                        description=f"Circular dependency detected involving '{node}'",
                        recommendation="Refactor to remove circular dependencies",
                        severity="high"
                    ))
                    
    def _check_unused_dependencies(self, result: DependencyCheckResult, project_path: Path):
        """Check for unused dependencies."""
        # This is a very simplified check
        # In reality, would need more sophisticated analysis
        
        # Get all imports from Python files
        imported_packages = set()
        for py_file in project_path.glob('**/*.py'):
            try:
                content = py_file.read_text()
                for match in re.finditer(r'(?:from|import)\s+(\w+)', content):
                    imported_packages.add(match.group(1).lower())
            except Exception:
                pass
                
        # Check for dependencies not imported anywhere
        for dep in result.dependencies:
            dep_name_lower = dep.name.lower().replace('-', '_')
            if dep_name_lower not in imported_packages and dep.name.lower() not in imported_packages:
                # Some packages have different import names
                import_name_map = {
                    'pillow': 'pil',
                    'beautifulsoup4': 'bs4',
                    'python-dateutil': 'dateutil',
                    'msgpack-python': 'msgpack',
                }
                
                import_name = import_name_map.get(dep.name.lower(), dep_name_lower)
                if import_name not in imported_packages:
                    result.issues.append(DependencyIssue(
                        issue_type=DependencyIssueType.UNUSED,
                        package_name=dep.name,
                        current_version=dep.version,
                        required_version=None,
                        description=f"Package '{dep.name}' appears to be unused",
                        recommendation="Consider removing unused dependencies",
                        severity="info"
                    ))
                    
    def _check_license_compatibility(self, result: DependencyCheckResult):
        """Check for license compatibility issues."""
        # This is a placeholder - real implementation would need license compatibility matrix
        copyleft_licenses = {'GPL', 'AGPL', 'LGPL'}
        permissive_licenses = {'MIT', 'Apache', 'BSD', 'ISC'}
        
        project_licenses = set()
        for dep in result.dependencies:
            if dep.license:
                project_licenses.add(dep.license)
                
        if any(lic in str(project_licenses) for lic in copyleft_licenses):
            if any(lic in str(project_licenses) for lic in permissive_licenses):
                result.issues.append(DependencyIssue(
                    issue_type=DependencyIssueType.LICENSE_CONFLICT,
                    package_name="project",
                    current_version=None,
                    required_version=None,
                    description="Potential license compatibility issues between copyleft and permissive licenses",
                    recommendation="Review license compatibility for your use case",
                    severity="medium"
                ))