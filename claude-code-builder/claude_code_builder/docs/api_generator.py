"""API documentation generator for Claude Code Builder."""
import inspect
import ast
from pathlib import Path
from typing import Dict, List, Optional, Any, Type, Union, Tuple
import re
from dataclasses import dataclass
import importlib
import pkgutil

from ..utils.template_engine import TemplateEngine
from ..logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class APIItem:
    """Represents an API item (class, function, method)."""
    name: str
    type: str  # 'class', 'function', 'method', 'property'
    module: str
    signature: Optional[str] = None
    docstring: Optional[str] = None
    parameters: List[Dict[str, Any]] = None
    returns: Optional[str] = None
    raises: List[str] = None
    examples: List[str] = None
    deprecated: bool = False
    since: Optional[str] = None
    see_also: List[str] = None
    notes: List[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.parameters is None:
            self.parameters = []
        if self.raises is None:
            self.raises = []
        if self.examples is None:
            self.examples = []
        if self.see_also is None:
            self.see_also = []
        if self.notes is None:
            self.notes = []


class APIDocumentationGenerator:
    """Generate API documentation from Python code."""
    
    def __init__(self, template_engine: Optional[TemplateEngine] = None):
        """Initialize API documentation generator.
        
        Args:
            template_engine: Template engine instance
        """
        self.template_engine = template_engine or TemplateEngine()
        self._api_items: Dict[str, List[APIItem]] = {}
        
    def generate_api_docs(
        self,
        package_path: Union[str, Path],
        output_dir: Path,
        include_private: bool = False,
        include_tests: bool = False,
        format: str = "markdown"
    ) -> Path:
        """Generate API documentation for a package.
        
        Args:
            package_path: Path to Python package
            output_dir: Output directory for documentation
            include_private: Include private members
            include_tests: Include test modules
            format: Output format (markdown, html, rst)
            
        Returns:
            Path to generated documentation
        """
        package_path = Path(package_path)
        
        # Discover and analyze modules
        self._discover_modules(package_path, include_tests)
        
        # Extract API information
        for module_name in self._api_items:
            self._extract_module_api(module_name, include_private)
        
        # Generate documentation
        if format == "markdown":
            return self._generate_markdown_docs(output_dir)
        elif format == "html":
            return self._generate_html_docs(output_dir)
        elif format == "rst":
            return self._generate_rst_docs(output_dir)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def generate_module_docs(
        self,
        module_name: str,
        output_path: Path,
        include_private: bool = False
    ) -> Path:
        """Generate documentation for a single module.
        
        Args:
            module_name: Module name to document
            output_path: Output file path
            include_private: Include private members
            
        Returns:
            Path to generated documentation
        """
        # Import and analyze module
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            logger.error(f"Failed to import module {module_name}: {e}")
            raise
        
        # Extract API items
        items = self._extract_module_api(module_name, include_private)
        
        # Generate documentation
        template = self._get_module_template()
        context = {
            'module_name': module_name,
            'module_doc': inspect.getdoc(module) or "No module documentation",
            'classes': [item for item in items if item.type == 'class'],
            'functions': [item for item in items if item.type == 'function'],
            'constants': self._extract_constants(module)
        }
        
        content = self.template_engine.render(template, context)
        output_path.write_text(content)
        
        return output_path
    
    def _discover_modules(self, package_path: Path, include_tests: bool) -> None:
        """Discover Python modules in a package.
        
        Args:
            package_path: Package path
            include_tests: Include test modules
        """
        package_name = package_path.name
        
        # Add package path to sys.path temporarily
        import sys
        sys.path.insert(0, str(package_path.parent))
        
        try:
            # Import package
            package = importlib.import_module(package_name)
            
            # Walk through package
            for importer, modname, ispkg in pkgutil.walk_packages(
                package.__path__,
                prefix=package.__name__ + "."
            ):
                # Skip test modules if not included
                if not include_tests and ('test' in modname or 'tests' in modname):
                    continue
                
                # Initialize module list
                if modname not in self._api_items:
                    self._api_items[modname] = []
                    
        finally:
            # Remove from sys.path
            sys.path.pop(0)
    
    def _extract_module_api(
        self,
        module_name: str,
        include_private: bool
    ) -> List[APIItem]:
        """Extract API items from a module.
        
        Args:
            module_name: Module name
            include_private: Include private members
            
        Returns:
            List of API items
        """
        items = []
        
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            logger.warning(f"Could not import module: {module_name}")
            return items
        
        # Extract classes
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if not include_private and name.startswith('_'):
                continue
            if obj.__module__ != module_name:
                continue  # Skip imported classes
                
            item = self._create_class_item(name, obj, module_name)
            items.append(item)
            
            # Extract methods
            for method_name, method in inspect.getmembers(obj):
                if not include_private and method_name.startswith('_'):
                    if method_name not in ['__init__', '__str__', '__repr__']:
                        continue
                        
                if inspect.ismethod(method) or inspect.isfunction(method):
                    method_item = self._create_method_item(
                        method_name, method, module_name, name
                    )
                    items.append(method_item)
        
        # Extract functions
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if not include_private and name.startswith('_'):
                continue
            if obj.__module__ != module_name:
                continue  # Skip imported functions
                
            item = self._create_function_item(name, obj, module_name)
            items.append(item)
        
        self._api_items[module_name] = items
        return items
    
    def _create_class_item(self, name: str, cls: Type, module: str) -> APIItem:
        """Create API item for a class.
        
        Args:
            name: Class name
            cls: Class object
            module: Module name
            
        Returns:
            API item
        """
        # Get signature
        try:
            sig = inspect.signature(cls.__init__)
            params = []
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                params.append({
                    'name': param_name,
                    'type': self._get_type_hint(param.annotation),
                    'default': self._format_default(param.default),
                    'required': param.default == inspect.Parameter.empty
                })
            signature = f"{name}({self._format_parameters(params)})"
        except:
            signature = f"{name}(...)"
            params = []
        
        # Parse docstring
        doc_info = self._parse_docstring(inspect.getdoc(cls))
        
        return APIItem(
            name=name,
            type='class',
            module=module,
            signature=signature,
            docstring=doc_info.get('description'),
            parameters=params,
            returns=doc_info.get('returns'),
            raises=doc_info.get('raises', []),
            examples=doc_info.get('examples', []),
            deprecated=doc_info.get('deprecated', False),
            since=doc_info.get('since'),
            see_also=doc_info.get('see_also', []),
            notes=doc_info.get('notes', [])
        )
    
    def _create_function_item(self, name: str, func: Any, module: str) -> APIItem:
        """Create API item for a function.
        
        Args:
            name: Function name
            func: Function object
            module: Module name
            
        Returns:
            API item
        """
        # Get signature
        try:
            sig = inspect.signature(func)
            params = []
            for param_name, param in sig.parameters.items():
                params.append({
                    'name': param_name,
                    'type': self._get_type_hint(param.annotation),
                    'default': self._format_default(param.default),
                    'required': param.default == inspect.Parameter.empty
                })
            signature = f"{name}({self._format_parameters(params)})"
            
            # Get return type
            return_type = self._get_type_hint(sig.return_annotation)
        except:
            signature = f"{name}(...)"
            params = []
            return_type = None
        
        # Parse docstring
        doc_info = self._parse_docstring(inspect.getdoc(func))
        
        return APIItem(
            name=name,
            type='function',
            module=module,
            signature=signature,
            docstring=doc_info.get('description'),
            parameters=params,
            returns=return_type or doc_info.get('returns'),
            raises=doc_info.get('raises', []),
            examples=doc_info.get('examples', []),
            deprecated=doc_info.get('deprecated', False),
            since=doc_info.get('since'),
            see_also=doc_info.get('see_also', []),
            notes=doc_info.get('notes', [])
        )
    
    def _create_method_item(
        self,
        name: str,
        method: Any,
        module: str,
        class_name: str
    ) -> APIItem:
        """Create API item for a method.
        
        Args:
            name: Method name
            method: Method object
            module: Module name
            class_name: Parent class name
            
        Returns:
            API item
        """
        item = self._create_function_item(name, method, module)
        item.type = 'method'
        item.name = f"{class_name}.{name}"
        
        # Adjust signature
        if item.signature:
            item.signature = item.signature.replace(f"{name}(", f"{class_name}.{name}(")
        
        return item
    
    def _parse_docstring(self, docstring: Optional[str]) -> Dict[str, Any]:
        """Parse docstring into structured format.
        
        Args:
            docstring: Docstring text
            
        Returns:
            Parsed docstring information
        """
        if not docstring:
            return {}
        
        info = {
            'description': '',
            'params': {},
            'returns': None,
            'raises': [],
            'examples': [],
            'deprecated': False,
            'since': None,
            'see_also': [],
            'notes': []
        }
        
        lines = docstring.strip().split('\n')
        current_section = 'description'
        current_content = []
        
        for line in lines:
            line = line.rstrip()
            
            # Check for section headers
            if line.strip() in ['Args:', 'Arguments:', 'Parameters:', 'Params:']:
                info[current_section] = '\n'.join(current_content).strip()
                current_section = 'params'
                current_content = []
            elif line.strip() in ['Returns:', 'Return:']:
                if current_section == 'params':
                    self._parse_params(current_content, info['params'])
                else:
                    info[current_section] = '\n'.join(current_content).strip()
                current_section = 'returns'
                current_content = []
            elif line.strip() in ['Raises:', 'Raise:', 'Throws:']:
                info[current_section] = '\n'.join(current_content).strip()
                current_section = 'raises'
                current_content = []
            elif line.strip() in ['Example:', 'Examples:']:
                info[current_section] = '\n'.join(current_content).strip()
                current_section = 'examples'
                current_content = []
            elif line.strip() in ['Note:', 'Notes:']:
                info[current_section] = '\n'.join(current_content).strip()
                current_section = 'notes'
                current_content = []
            elif line.strip().startswith('.. deprecated::'):
                info['deprecated'] = True
                info['since'] = line.split('::')[1].strip()
            elif line.strip().startswith('.. since::'):
                info['since'] = line.split('::')[1].strip()
            elif line.strip() in ['See Also:', 'See also:']:
                info[current_section] = '\n'.join(current_content).strip()
                current_section = 'see_also'
                current_content = []
            else:
                current_content.append(line)
        
        # Handle last section
        if current_section == 'params':
            self._parse_params(current_content, info['params'])
        elif current_section == 'raises':
            info['raises'] = [line.strip() for line in current_content if line.strip()]
        elif current_section == 'examples':
            info['examples'] = self._extract_code_blocks('\n'.join(current_content))
        elif current_section == 'see_also':
            info['see_also'] = [line.strip() for line in current_content if line.strip()]
        elif current_section == 'notes':
            info['notes'] = [line.strip() for line in current_content if line.strip()]
        else:
            info[current_section] = '\n'.join(current_content).strip()
        
        return info
    
    def _parse_params(self, lines: List[str], params: Dict[str, str]) -> None:
        """Parse parameter descriptions.
        
        Args:
            lines: Parameter lines
            params: Parameter dictionary to update
        """
        current_param = None
        current_desc = []
        
        for line in lines:
            # Check if this is a new parameter
            match = re.match(r'^\s*(\w+)\s*:\s*(.*)$', line)
            if match:
                # Save previous parameter
                if current_param:
                    params[current_param] = ' '.join(current_desc).strip()
                
                current_param = match.group(1)
                current_desc = [match.group(2)]
            elif current_param and line.strip():
                # Continuation of current parameter
                current_desc.append(line.strip())
        
        # Save last parameter
        if current_param:
            params[current_param] = ' '.join(current_desc).strip()
    
    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract code blocks from text.
        
        Args:
            text: Text containing code blocks
            
        Returns:
            List of code blocks
        """
        blocks = []
        
        # Match ```language blocks
        pattern = r'```(?:\w+)?\n(.*?)\n```'
        matches = re.findall(pattern, text, re.DOTALL)
        blocks.extend(matches)
        
        # Match indented blocks
        lines = text.split('\n')
        current_block = []
        in_block = False
        
        for line in lines:
            if line.startswith('    ') or line.startswith('\t'):
                current_block.append(line[4:] if line.startswith('    ') else line[1:])
                in_block = True
            elif in_block and line.strip() == '':
                current_block.append('')
            elif in_block:
                if current_block:
                    blocks.append('\n'.join(current_block))
                current_block = []
                in_block = False
        
        if current_block:
            blocks.append('\n'.join(current_block))
        
        return blocks
    
    def _get_type_hint(self, annotation: Any) -> Optional[str]:
        """Get type hint as string.
        
        Args:
            annotation: Type annotation
            
        Returns:
            Type hint string
        """
        if annotation == inspect.Parameter.empty:
            return None
        
        if hasattr(annotation, '__name__'):
            return annotation.__name__
        
        return str(annotation)
    
    def _format_default(self, default: Any) -> Optional[str]:
        """Format parameter default value.
        
        Args:
            default: Default value
            
        Returns:
            Formatted default
        """
        if default == inspect.Parameter.empty:
            return None
        
        if default is None:
            return 'None'
        
        if isinstance(default, str):
            return f'"{default}"'
        
        return str(default)
    
    def _format_parameters(self, params: List[Dict[str, Any]]) -> str:
        """Format parameter list for signature.
        
        Args:
            params: Parameter list
            
        Returns:
            Formatted parameters
        """
        parts = []
        
        for param in params:
            part = param['name']
            
            if param.get('type'):
                part += f": {param['type']}"
            
            if param.get('default'):
                part += f" = {param['default']}"
            
            parts.append(part)
        
        return ', '.join(parts)
    
    def _extract_constants(self, module: Any) -> List[Dict[str, Any]]:
        """Extract module constants.
        
        Args:
            module: Module object
            
        Returns:
            List of constants
        """
        constants = []
        
        for name, value in inspect.getmembers(module):
            # Skip private, imported, and callable items
            if name.startswith('_'):
                continue
            if callable(value):
                continue
            if hasattr(value, '__module__') and value.__module__ != module.__name__:
                continue
            
            # Check if it's likely a constant (uppercase name)
            if name.isupper() or name.startswith('DEFAULT_'):
                constants.append({
                    'name': name,
                    'value': repr(value),
                    'type': type(value).__name__
                })
        
        return constants
    
    def _get_module_template(self) -> str:
        """Get module documentation template.
        
        Returns:
            Template string
        """
        return '''# {{ module_name }}

{{ module_doc }}

{% if constants %}
## Constants

{% for const in constants %}
### {{ const.name }}

- **Type**: `{{ const.type }}`
- **Value**: `{{ const.value }}`
{% endfor %}
{% endif %}

{% if functions %}
## Functions

{% for func in functions %}
### {{ func.signature }}

{{ func.docstring }}

{% if func.parameters %}
**Parameters:**
{% for param in func.parameters %}
- **{{ param.name }}**{% if param.type %} (`{{ param.type }}`){% endif %}{% if not param.required %}, optional{% endif %}{% if param.default %}, default: `{{ param.default }}`{% endif %}
{% endfor %}
{% endif %}

{% if func.returns %}
**Returns:**
- {{ func.returns }}
{% endif %}

{% if func.raises %}
**Raises:**
{% for exc in func.raises %}
- {{ exc }}
{% endfor %}
{% endif %}

{% if func.examples %}
**Examples:**
{% for example in func.examples %}
```python
{{ example }}
```
{% endfor %}
{% endif %}

{% if func.deprecated %}
**Deprecated:** Since version {{ func.since }}
{% endif %}

{% if func.see_also %}
**See Also:**
{% for ref in func.see_also %}
- {{ ref }}
{% endfor %}
{% endif %}

---

{% endfor %}
{% endif %}

{% if classes %}
## Classes

{% for cls in classes %}
### {{ cls.signature }}

{{ cls.docstring }}

{% if cls.parameters %}
**Parameters:**
{% for param in cls.parameters %}
- **{{ param.name }}**{% if param.type %} (`{{ param.type }}`){% endif %}{% if not param.required %}, optional{% endif %}{% if param.default %}, default: `{{ param.default }}`{% endif %}
{% endfor %}
{% endif %}

{% if cls.examples %}
**Examples:**
{% for example in cls.examples %}
```python
{{ example }}
```
{% endfor %}
{% endif %}

---

{% endfor %}
{% endif %}
'''
    
    def _generate_markdown_docs(self, output_dir: Path) -> Path:
        """Generate markdown documentation.
        
        Args:
            output_dir: Output directory
            
        Returns:
            Path to documentation
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate index
        index_path = output_dir / 'index.md'
        self._generate_index(index_path)
        
        # Generate module documentation
        for module_name, items in self._api_items.items():
            module_file = module_name.replace('.', '_') + '.md'
            module_path = output_dir / module_file
            
            template = self._get_module_template()
            context = {
                'module_name': module_name,
                'module_doc': self._get_module_docstring(module_name),
                'classes': [item for item in items if item.type == 'class'],
                'functions': [item for item in items if item.type == 'function'],
                'constants': []  # TODO: Extract constants
            }
            
            content = self.template_engine.render(template, context)
            module_path.write_text(content)
        
        return output_dir
    
    def _generate_index(self, index_path: Path) -> None:
        """Generate documentation index.
        
        Args:
            index_path: Path to index file
        """
        template = '''# API Documentation

## Modules

{% for module in modules %}
- [{{ module }}]({{ module.replace('.', '_') }}.md)
{% endfor %}

## Quick Links

- [Getting Started](../README.md)
- [User Guide](user_guide.md)
- [Examples](examples.md)

---

Generated with Claude Code Builder
'''
        
        context = {
            'modules': sorted(self._api_items.keys())
        }
        
        content = self.template_engine.render(template, context)
        index_path.write_text(content)
    
    def _get_module_docstring(self, module_name: str) -> str:
        """Get module docstring.
        
        Args:
            module_name: Module name
            
        Returns:
            Module docstring
        """
        try:
            module = importlib.import_module(module_name)
            return inspect.getdoc(module) or "No module documentation"
        except:
            return "Module documentation unavailable"
    
    def _generate_html_docs(self, output_dir: Path) -> Path:
        """Generate HTML documentation.
        
        Args:
            output_dir: Output directory
            
        Returns:
            Path to documentation
        """
        # TODO: Implement HTML generation
        raise NotImplementedError("HTML documentation generation not yet implemented")
    
    def _generate_rst_docs(self, output_dir: Path) -> Path:
        """Generate reStructuredText documentation.
        
        Args:
            output_dir: Output directory
            
        Returns:
            Path to documentation
        """
        # TODO: Implement RST generation
        raise NotImplementedError("RST documentation generation not yet implemented")