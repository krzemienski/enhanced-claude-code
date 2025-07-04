"""CLI package for Claude Code Builder."""

from .cli import CLI
from .commands import CommandHandler
from .plugins import PluginManager, Plugin, PluginInfo, PluginHook
from .config_manager import ConfigManager

# Import main from __main__ for backwards compatibility
from claude_code_builder.__main__ import main

__all__ = [
    'CLI',
    'CommandHandler',
    'PluginManager',
    'Plugin',
    'PluginInfo',
    'PluginHook',
    'ConfigManager',
    'main'
]