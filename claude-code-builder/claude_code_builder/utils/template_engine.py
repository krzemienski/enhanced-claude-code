"""Template rendering engine for Claude Code Builder."""
import re
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from datetime import datetime
import json
from string import Template as StringTemplate
from dataclasses import dataclass, field

from ..exceptions.base import ValidationError, ClaudeCodeBuilderError
from ..logging.logger import get_logger
from .string_utils import clean_string, camel_case, snake_case, kebab_case
from .file_handler import FileHandler

logger = get_logger(__name__)


@dataclass
class TemplateContext:
    """Template rendering context."""
    variables: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Callable] = field(default_factory=dict)
    globals: Dict[str, Any] = field(default_factory=dict)
    
    def merge(self, other: 'TemplateContext') -> 'TemplateContext':
        """Merge with another context.
        
        Args:
            other: Context to merge
            
        Returns:
            New merged context
        """
        return TemplateContext(
            variables={**self.variables, **other.variables},
            filters={**self.filters, **other.filters},
            globals={**self.globals, **other.globals}
        )


class TemplateEngine:
    """Advanced template rendering engine."""
    
    # Default template patterns
    VARIABLE_PATTERN = re.compile(r'\{\{\s*([^}]+)\s*\}\}')
    BLOCK_PATTERN = re.compile(r'\{%\s*([^%]+)\s*%\}')
    COMMENT_PATTERN = re.compile(r'\{#[^#]*#\}')
    
    def __init__(self):
        """Initialize template engine."""
        self.file_handler = FileHandler()
        self._default_filters = self._setup_default_filters()
        self._default_globals = self._setup_default_globals()
        
    def render(
        self,
        template: str,
        context: Optional[Dict[str, Any]] = None,
        strict: bool = False
    ) -> str:
        """Render template with context.
        
        Args:
            template: Template string
            context: Template context
            strict: Raise error on missing variables
            
        Returns:
            Rendered string
            
        Raises:
            ValidationError: If template is invalid
        """
        context = context or {}
        
        # Create rendering context
        render_context = TemplateContext(
            variables=context,
            filters=self._default_filters.copy(),
            globals=self._default_globals.copy()
        )
        
        try:
            # Remove comments
            result = self._remove_comments(template)
            
            # Process blocks (control structures)
            result = self._process_blocks(result, render_context)
            
            # Process variables
            result = self._process_variables(result, render_context, strict)
            
            return result
            
        except Exception as e:
            raise ValidationError(f"Template rendering failed: {e}")
    
    def render_file(
        self,
        template_path: Union[str, Path],
        context: Optional[Dict[str, Any]] = None,
        output_path: Optional[Union[str, Path]] = None,
        strict: bool = False
    ) -> str:
        """Render template file.
        
        Args:
            template_path: Path to template file
            context: Template context
            output_path: Optional output file path
            strict: Raise error on missing variables
            
        Returns:
            Rendered content
        """
        # Read template
        template = self.file_handler.read_file(template_path)
        
        # Render template
        result = self.render(template, context, strict)
        
        # Write output if path provided
        if output_path:
            self.file_handler.write_file(output_path, result)
        
        return result
    
    def render_string(
        self,
        template: str,
        **kwargs: Any
    ) -> str:
        """Simple string template rendering.
        
        Args:
            template: Template string with $variables
            **kwargs: Variable values
            
        Returns:
            Rendered string
        """
        tmpl = StringTemplate(template)
        return tmpl.safe_substitute(**kwargs)
    
    def _remove_comments(self, template: str) -> str:
        """Remove comments from template.
        
        Args:
            template: Template string
            
        Returns:
            Template without comments
        """
        return self.COMMENT_PATTERN.sub('', template)
    
    def _process_blocks(self, template: str, context: TemplateContext) -> str:
        """Process template blocks (control structures).
        
        Args:
            template: Template string
            context: Rendering context
            
        Returns:
            Processed template
        """
        # Process if blocks
        template = self._process_if_blocks(template, context)
        
        # Process for loops
        template = self._process_for_loops(template, context)
        
        # Process include blocks
        template = self._process_includes(template, context)
        
        return template
    
    def _process_if_blocks(self, template: str, context: TemplateContext) -> str:
        """Process if/else blocks.
        
        Args:
            template: Template string
            context: Rendering context
            
        Returns:
            Processed template
        """
        # Pattern for if blocks
        if_pattern = re.compile(
            r'\{%\s*if\s+(.+?)\s*%\}(.*?)'
            r'(?:\{%\s*else\s*%\}(.*?))?'
            r'\{%\s*endif\s*%\}',
            re.DOTALL
        )
        
        def replace_if(match):
            condition = match.group(1)
            if_content = match.group(2)
            else_content = match.group(3) or ''
            
            # Evaluate condition
            try:
                result = self._evaluate_expression(condition, context)
                return if_content if result else else_content
            except Exception:
                return else_content
        
        return if_pattern.sub(replace_if, template)
    
    def _process_for_loops(self, template: str, context: TemplateContext) -> str:
        """Process for loops.
        
        Args:
            template: Template string
            context: Rendering context
            
        Returns:
            Processed template
        """
        # Pattern for for loops
        for_pattern = re.compile(
            r'\{%\s*for\s+(\w+)\s+in\s+(.+?)\s*%\}(.*?)'
            r'\{%\s*endfor\s*%\}',
            re.DOTALL
        )
        
        def replace_for(match):
            var_name = match.group(1)
            iterable_expr = match.group(2)
            loop_content = match.group(3)
            
            # Get iterable
            try:
                iterable = self._evaluate_expression(iterable_expr, context)
                if not hasattr(iterable, '__iter__'):
                    return ''
                
                # Render loop content for each item
                results = []
                for i, item in enumerate(iterable):
                    # Create loop context
                    loop_context = context.variables.copy()
                    loop_context[var_name] = item
                    loop_context['loop'] = {
                        'index': i,
                        'index0': i,
                        'index1': i + 1,
                        'first': i == 0,
                        'last': i == len(list(iterable)) - 1,
                        'length': len(list(iterable))
                    }
                    
                    # Render with loop context
                    loop_ctx = TemplateContext(
                        variables=loop_context,
                        filters=context.filters,
                        globals=context.globals
                    )
                    
                    rendered = self._process_variables(loop_content, loop_ctx, False)
                    results.append(rendered)
                
                return ''.join(results)
                
            except Exception:
                return ''
        
        return for_pattern.sub(replace_for, template)
    
    def _process_includes(self, template: str, context: TemplateContext) -> str:
        """Process include statements.
        
        Args:
            template: Template string
            context: Rendering context
            
        Returns:
            Processed template
        """
        # Pattern for includes
        include_pattern = re.compile(r'\{%\s*include\s+"([^"]+)"\s*%\}')
        
        def replace_include(match):
            include_path = match.group(1)
            
            try:
                # Read included template
                included = self.file_handler.read_file(include_path)
                
                # Render included template
                return self.render(included, context.variables, strict=False)
                
            except Exception as e:
                logger.warning(f"Failed to include {include_path}: {e}")
                return f"<!-- Include failed: {include_path} -->"
        
        return include_pattern.sub(replace_include, template)
    
    def _process_variables(
        self,
        template: str,
        context: TemplateContext,
        strict: bool
    ) -> str:
        """Process template variables.
        
        Args:
            template: Template string
            context: Rendering context
            strict: Raise error on missing variables
            
        Returns:
            Processed template
        """
        def replace_variable(match):
            expr = match.group(1).strip()
            
            try:
                # Parse expression (variable | filter | filter ...)
                parts = [p.strip() for p in expr.split('|')]
                var_expr = parts[0]
                filters = parts[1:] if len(parts) > 1 else []
                
                # Get variable value
                value = self._evaluate_expression(var_expr, context)
                
                # Apply filters
                for filter_expr in filters:
                    value = self._apply_filter(value, filter_expr, context)
                
                return str(value)
                
            except Exception as e:
                if strict:
                    raise ValidationError(f"Variable error: {expr} - {e}")
                return match.group(0)  # Return original if error
        
        return self.VARIABLE_PATTERN.sub(replace_variable, template)
    
    def _evaluate_expression(
        self,
        expr: str,
        context: TemplateContext
    ) -> Any:
        """Evaluate template expression.
        
        Args:
            expr: Expression string
            context: Template context
            
        Returns:
            Expression value
        """
        # Handle dot notation (e.g., user.name)
        parts = expr.split('.')
        
        # Start with variables, then check globals
        if parts[0] in context.variables:
            value = context.variables[parts[0]]
        elif parts[0] in context.globals:
            value = context.globals[parts[0]]
        else:
            raise KeyError(f"Variable not found: {parts[0]}")
        
        # Navigate through attributes
        for part in parts[1:]:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = getattr(value, part, None)
            
            if value is None:
                break
        
        return value
    
    def _apply_filter(
        self,
        value: Any,
        filter_expr: str,
        context: TemplateContext
    ) -> Any:
        """Apply filter to value.
        
        Args:
            value: Value to filter
            filter_expr: Filter expression
            context: Template context
            
        Returns:
            Filtered value
        """
        # Parse filter and arguments
        match = re.match(r'(\w+)(?:\((.*?)\))?', filter_expr)
        if not match:
            return value
        
        filter_name = match.group(1)
        args_str = match.group(2) or ''
        
        # Get filter function
        if filter_name not in context.filters:
            logger.warning(f"Unknown filter: {filter_name}")
            return value
        
        filter_func = context.filters[filter_name]
        
        # Parse arguments
        args = []
        if args_str:
            # Simple argument parsing (comma-separated)
            for arg in args_str.split(','):
                arg = arg.strip()
                # Try to evaluate as literal
                try:
                    if arg.startswith('"') and arg.endswith('"'):
                        args.append(arg[1:-1])
                    elif arg.startswith("'") and arg.endswith("'"):
                        args.append(arg[1:-1])
                    elif arg.isdigit():
                        args.append(int(arg))
                    elif arg.replace('.', '').isdigit():
                        args.append(float(arg))
                    elif arg in ('True', 'true'):
                        args.append(True)
                    elif arg in ('False', 'false'):
                        args.append(False)
                    else:
                        args.append(arg)
                except:
                    args.append(arg)
        
        # Apply filter
        try:
            return filter_func(value, *args)
        except Exception as e:
            logger.warning(f"Filter error: {filter_name} - {e}")
            return value
    
    def _setup_default_filters(self) -> Dict[str, Callable]:
        """Setup default template filters.
        
        Returns:
            Dictionary of filter functions
        """
        return {
            # String filters
            'upper': lambda s: str(s).upper(),
            'lower': lambda s: str(s).lower(),
            'capitalize': lambda s: str(s).capitalize(),
            'title': lambda s: str(s).title(),
            'strip': lambda s: str(s).strip(),
            'clean': lambda s: clean_string(str(s)),
            'truncate': lambda s, length=50: str(s)[:length] + '...' if len(str(s)) > length else str(s),
            'default': lambda v, default='': v if v is not None else default,
            'snake_case': lambda s: snake_case(str(s)),
            'camel_case': lambda s: camel_case(str(s)),
            'kebab_case': lambda s: kebab_case(str(s)),
            
            # Number filters
            'int': lambda v: int(float(v)) if v is not None else 0,
            'float': lambda v: float(v) if v is not None else 0.0,
            'round': lambda v, precision=2: round(float(v), precision),
            'abs': lambda v: abs(float(v)),
            
            # List filters
            'length': lambda v: len(v) if hasattr(v, '__len__') else 0,
            'first': lambda v: v[0] if v else None,
            'last': lambda v: v[-1] if v else None,
            'join': lambda v, sep=', ': sep.join(str(i) for i in v) if hasattr(v, '__iter__') else str(v),
            'sort': lambda v: sorted(v) if hasattr(v, '__iter__') else [v],
            'unique': lambda v: list(set(v)) if hasattr(v, '__iter__') else [v],
            
            # Date filters
            'date': lambda v, fmt='%Y-%m-%d': v.strftime(fmt) if hasattr(v, 'strftime') else str(v),
            'time': lambda v, fmt='%H:%M:%S': v.strftime(fmt) if hasattr(v, 'strftime') else str(v),
            
            # JSON filter
            'json': lambda v: json.dumps(v, indent=2, default=str),
            'json_compact': lambda v: json.dumps(v, separators=(',', ':'), default=str),
        }
    
    def _setup_default_globals(self) -> Dict[str, Any]:
        """Setup default template globals.
        
        Returns:
            Dictionary of global values
        """
        return {
            'now': datetime.now(),
            'today': datetime.now().date(),
            'true': True,
            'false': False,
            'none': None,
        }
    
    def add_filter(self, name: str, func: Callable) -> None:
        """Add custom filter.
        
        Args:
            name: Filter name
            func: Filter function
        """
        self._default_filters[name] = func
    
    def add_global(self, name: str, value: Any) -> None:
        """Add global variable.
        
        Args:
            name: Variable name
            value: Variable value
        """
        self._default_globals[name] = value