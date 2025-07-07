"""Example projects and specifications for Claude Code Builder."""
from .simple_project import SimpleProjectExample, get_simple_calculator_spec, get_todo_app_spec
from .advanced_project import AdvancedProjectExample
from .custom_instructions import CustomInstructionsExample  
from .plugin_example import PluginExample

__all__ = [
    'SimpleProjectExample',
    'get_simple_calculator_spec',
    'get_todo_app_spec',
    'AdvancedProjectExample',
    'CustomInstructionsExample',
    'PluginExample'
]