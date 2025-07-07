"""Configuration management for Claude Code Builder CLI."""
from pathlib import Path
from typing import Dict, Any, Optional, List
import os

from ..config.settings import Settings
from ..utils.config_loader import ConfigLoader, ConfigSchema
from ..utils.file_handler import FileHandler
from ..utils.path_utils import get_config_dir, find_project_root
from ..logging.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """Manages configuration for Claude Code Builder."""
    
    # Configuration file names in order of precedence
    CONFIG_FILES = [
        '.claude-code-builder.yaml',
        '.claude-code-builder.yml',
        '.claude-code-builder.json',
        '.claude-code-builder.toml',
        'claude-code-builder.config.yaml',
        'claude-code-builder.config.json'
    ]
    
    def __init__(self, settings: Settings):
        """Initialize configuration manager.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.config_loader = ConfigLoader("claude_code_builder")
        self.file_handler = FileHandler()
        
        # Define configuration schema
        self._schema = ConfigSchema(
            fields={
                'api_key': {
                    'type': str,
                    'description': 'Anthropic API key'
                },
                'model': {
                    'type': str,
                    'description': 'Claude model to use',
                    'choices': [
                        'claude-3-opus-20240229',
                        'claude-3-sonnet-20240229',
                        'claude-3-haiku-20240307'
                    ]
                },
                'max_tokens': {
                    'type': int,
                    'description': 'Maximum tokens per phase',
                    'min': 1000,
                    'max': 200000
                },
                'mcp_servers': {
                    'type': dict,
                    'description': 'MCP server configurations'
                },
                'research': {
                    'type': dict,
                    'description': 'Research configuration',
                    'fields': {
                        'enabled': {'type': bool},
                        'api_key': {'type': str},
                        'max_queries': {'type': int, 'min': 1, 'max': 50}
                    }
                },
                'ui': {
                    'type': dict,
                    'description': 'UI configuration',
                    'fields': {
                        'rich': {'type': bool},
                        'color': {'type': bool},
                        'progress_style': {'type': str}
                    }
                },
                'cache': {
                    'type': dict,
                    'description': 'Cache configuration',
                    'fields': {
                        'enabled': {'type': bool},
                        'ttl': {'type': int, 'min': 0},
                        'max_size': {'type': int, 'min': 0}
                    }
                },
                'execution': {
                    'type': dict,
                    'description': 'Execution configuration',
                    'fields': {
                        'parallel_tasks': {'type': int, 'min': 1, 'max': 10},
                        'timeout': {'type': int, 'min': 0},
                        'retry_attempts': {'type': int, 'min': 0, 'max': 10}
                    }
                },
                'logging': {
                    'type': dict,
                    'description': 'Logging configuration',
                    'fields': {
                        'level': {
                            'type': str,
                            'choices': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                        },
                        'file': {'type': str},
                        'format': {'type': str}
                    }
                }
            },
            required=[],  # API key required only for certain commands
            defaults={
                'model': 'claude-3-sonnet-20240229',
                'max_tokens': 100000,
                'mcp_servers': {},
                'research': {
                    'enabled': True,
                    'max_queries': 10
                },
                'ui': {
                    'rich': True,
                    'color': True,
                    'progress_style': 'default'
                },
                'cache': {
                    'enabled': True,
                    'ttl': 3600,
                    'max_size': 1000
                },
                'execution': {
                    'parallel_tasks': 3,
                    'timeout': 300,
                    'retry_attempts': 3
                },
                'logging': {
                    'level': 'INFO'
                }
            }
        )
        
        self.config_loader.schema = self._schema
        
        # Load configuration
        self._config = self._load_all_configs()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value
            
        Returns:
            Configuration value
        """
        return self.config_loader.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            value: Value to set
        """
        self.config_loader.set(key, value)
        self._config = self.config_loader.config
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values.
        
        Returns:
            Configuration dictionary
        """
        return self._config.copy()
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to file.
        
        Args:
            path: Optional path to save to
        """
        if path is None:
            # Find existing config file or create new one
            path = self._find_config_file() or Path.cwd() / self.CONFIG_FILES[0]
        
        # Determine format from extension
        self.config_loader.save(path)
        logger.info(f"Saved configuration to {path}")
    
    def load_project_config(self, project_dir: Path) -> Dict[str, Any]:
        """Load project-specific configuration.
        
        Args:
            project_dir: Project directory
            
        Returns:
            Project configuration
        """
        # Look for config files in project
        for config_name in self.CONFIG_FILES:
            config_path = project_dir / config_name
            if config_path.exists():
                return self.config_loader.load_file(config_path)
        
        return {}
    
    def merge_environment_vars(self) -> None:
        """Merge environment variables into configuration."""
        env_config = self.config_loader.load_env("CLAUDE_CODE_BUILDER_")
        
        # Special handling for common env vars
        if 'ANTHROPIC_API_KEY' in os.environ:
            env_config['api_key'] = os.environ['ANTHROPIC_API_KEY']
        
        # Merge into config
        for key, value in env_config.items():
            self.set(key, value)
    
    def validate(self) -> List[str]:
        """Validate current configuration.
        
        Returns:
            List of validation errors
        """
        return self._schema.validate(self._config)
    
    def _load_all_configs(self) -> Dict[str, Any]:
        """Load configuration from all sources.
        
        Returns:
            Merged configuration
        """
        sources = []
        
        # System config
        system_config = Path('/etc/claude-code-builder/config.yaml')
        if system_config.exists():
            sources.append(system_config)
        
        # User config
        user_config_dir = get_config_dir()
        for config_name in self.CONFIG_FILES:
            config_path = user_config_dir / config_name
            if config_path.exists():
                sources.append(config_path)
                break
        
        # Project config
        project_root = find_project_root()
        if project_root:
            for config_name in self.CONFIG_FILES:
                config_path = project_root / config_name
                if config_path.exists():
                    sources.append(config_path)
                    break
        
        # Current directory config
        for config_name in self.CONFIG_FILES:
            config_path = Path.cwd() / config_name
            if config_path.exists() and config_path not in sources:
                sources.append(config_path)
                break
        
        # Load and merge all configs
        config = self.config_loader.load(sources)
        
        # Merge environment variables
        self.merge_environment_vars()
        
        return config
    
    def _find_config_file(self) -> Optional[Path]:
        """Find existing configuration file.
        
        Returns:
            Path to config file or None
        """
        # Check current directory
        for config_name in self.CONFIG_FILES:
            config_path = Path.cwd() / config_name
            if config_path.exists():
                return config_path
        
        # Check project root
        project_root = find_project_root()
        if project_root:
            for config_name in self.CONFIG_FILES:
                config_path = project_root / config_name
                if config_path.exists():
                    return config_path
        
        # Check user config
        user_config_dir = get_config_dir()
        for config_name in self.CONFIG_FILES:
            config_path = user_config_dir / config_name
            if config_path.exists():
                return config_path
        
        return None
    
    def create_default_config(self, path: Path) -> None:
        """Create default configuration file.
        
        Args:
            path: Path to create config file
        """
        default_config = {
            'api_key': 'your-api-key-here',
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 100000,
            'mcp_servers': {
                '# example': {
                    'command': 'npx',
                    'args': ['-y', '@modelcontextprotocol/server-filesystem']
                }
            },
            'research': {
                'enabled': True,
                'api_key': '# Optional Perplexity API key',
                'max_queries': 10
            },
            'ui': {
                'rich': True,
                'color': True,
                'progress_style': 'default'
            },
            'cache': {
                'enabled': True,
                'ttl': 3600,
                'max_size': 1000
            },
            'execution': {
                'parallel_tasks': 3,
                'timeout': 300,
                'retry_attempts': 3
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        # Add comments
        config_with_comments = f"""# Claude Code Builder Configuration
# 
# This file contains configuration for Claude Code Builder.
# You can override any setting using environment variables
# with the prefix CLAUDE_CODE_BUILDER_ (e.g., CLAUDE_CODE_BUILDER_MODEL)
#
# API key can also be set using ANTHROPIC_API_KEY environment variable

{self._dict_to_yaml_with_comments(default_config)}
"""
        
        self.file_handler.write_file(path, config_with_comments)
    
    def _dict_to_yaml_with_comments(self, data: Dict[str, Any], indent: int = 0) -> str:
        """Convert dictionary to YAML with comments.
        
        Args:
            data: Dictionary to convert
            indent: Current indentation level
            
        Returns:
            YAML string with comments
        """
        import yaml
        
        # Use custom YAML dumper that preserves comments
        yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
        
        # Add field descriptions as comments
        lines = []
        for line in yaml_str.split('\n'):
            if ':' in line and not line.strip().startswith('#'):
                key = line.split(':')[0].strip()
                if key in self._schema.fields:
                    field_info = self._schema.fields[key]
                    if 'description' in field_info:
                        lines.append(f"# {field_info['description']}")
            lines.append(line)
        
        return '\n'.join(lines)