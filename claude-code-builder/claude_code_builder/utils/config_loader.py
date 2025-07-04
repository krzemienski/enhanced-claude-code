"""Configuration file loader for Claude Code Builder."""
import os
import json
import yaml
import toml
import configparser
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Type
from dataclasses import dataclass, field
import importlib.util
import sys

from ..exceptions.base import ValidationError, FileOperationError
from ..logging.logger import get_logger
from .file_handler import FileHandler
from .path_utils import find_project_root, get_config_dir, normalize_path
from .json_utils import merge_json

logger = get_logger(__name__)


@dataclass
class ConfigSchema:
    """Configuration schema definition."""
    fields: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    defaults: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration against schema.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check required fields
        for field in self.required:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate field types
        for field, value in config.items():
            if field in self.fields:
                field_def = self.fields[field]
                expected_type = field_def.get('type')
                
                if expected_type and not isinstance(value, expected_type):
                    errors.append(
                        f"Invalid type for {field}: expected {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )
                
                # Check constraints
                if 'min' in field_def and value < field_def['min']:
                    errors.append(f"{field} must be >= {field_def['min']}")
                
                if 'max' in field_def and value > field_def['max']:
                    errors.append(f"{field} must be <= {field_def['max']}")
                
                if 'choices' in field_def and value not in field_def['choices']:
                    errors.append(f"{field} must be one of: {field_def['choices']}")
        
        return errors


class ConfigLoader:
    """Loads and manages configuration from various sources."""
    
    # Supported config file formats
    SUPPORTED_FORMATS = {
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.ini': 'ini',
        '.py': 'python'
    }
    
    def __init__(
        self,
        app_name: str = "claude_code_builder",
        schema: Optional[ConfigSchema] = None
    ):
        """Initialize config loader.
        
        Args:
            app_name: Application name
            schema: Configuration schema
        """
        self.app_name = app_name
        self.schema = schema
        self.file_handler = FileHandler()
        self._config: Dict[str, Any] = {}
        self._sources: List[str] = []
        
    def load(
        self,
        sources: Optional[List[Union[str, Path]]] = None,
        merge: bool = True,
        validate: bool = True
    ) -> Dict[str, Any]:
        """Load configuration from multiple sources.
        
        Args:
            sources: List of config sources
            merge: Merge configs from multiple sources
            validate: Validate against schema
            
        Returns:
            Loaded configuration
            
        Raises:
            ValidationError: If validation fails
        """
        if sources is None:
            sources = self._get_default_sources()
        
        configs = []
        
        for source in sources:
            try:
                config = self._load_source(source)
                if config:
                    configs.append(config)
                    self._sources.append(str(source))
            except Exception as e:
                logger.warning(f"Failed to load config from {source}: {e}")
        
        # Merge configurations
        if merge and configs:
            result = {}
            for config in configs:
                result = merge_json(result, config, deep=True)
            self._config = result
        elif configs:
            self._config = configs[-1]  # Use last config
        else:
            self._config = {}
        
        # Apply defaults from schema
        if self.schema:
            for field, default in self.schema.defaults.items():
                if field not in self._config:
                    self._config[field] = default
        
        # Validate if requested
        if validate and self.schema:
            errors = self.schema.validate(self._config)
            if errors:
                raise ValidationError(
                    "Configuration validation failed",
                    details={"errors": errors}
                )
        
        return self._config
    
    def load_file(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from a specific file.
        
        Args:
            path: Config file path
            
        Returns:
            Configuration dictionary
        """
        return self._load_source(path)
    
    def load_env(self, prefix: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from environment variables.
        
        Args:
            prefix: Environment variable prefix
            
        Returns:
            Configuration from environment
        """
        prefix = prefix or self.app_name.upper() + "_"
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix):].lower()
                
                # Convert value types
                config[config_key] = self._parse_env_value(value)
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value
            
        Returns:
            Configuration value
        """
        # Support dot notation
        parts = key.split('.')
        value = self._config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        parts = key.split('.')
        config = self._config
        
        # Navigate to parent
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
        
        # Set value
        config[parts[-1]] = value
    
    def save(
        self,
        path: Union[str, Path],
        format: Optional[str] = None
    ) -> None:
        """Save configuration to file.
        
        Args:
            path: Output file path
            format: Output format (auto-detected if not specified)
        """
        path = normalize_path(path)
        
        # Determine format
        if format is None:
            suffix = path.suffix.lower()
            format = self.SUPPORTED_FORMATS.get(suffix, 'json')
        
        # Convert and save
        if format == 'json':
            self.file_handler.write_json(path, self._config)
        elif format == 'yaml':
            self.file_handler.write_yaml(path, self._config)
        elif format == 'toml':
            self.file_handler.write_toml(path, self._config)
        elif format == 'ini':
            self._save_ini(path)
        else:
            raise ValidationError(f"Unsupported format: {format}")
        
        logger.info(f"Saved configuration to {path}")
    
    def _get_default_sources(self) -> List[Path]:
        """Get default configuration sources.
        
        Returns:
            List of config file paths
        """
        sources = []
        
        # System config
        system_config = Path('/etc') / self.app_name / 'config.yaml'
        if system_config.exists():
            sources.append(system_config)
        
        # User config directory
        user_config_dir = get_config_dir(self.app_name)
        for ext in ['.yaml', '.json', '.toml']:
            config_file = user_config_dir / f'config{ext}'
            if config_file.exists():
                sources.append(config_file)
        
        # Project config
        project_root = find_project_root()
        if project_root:
            # Check various config locations
            for name in [
                f'.{self.app_name}rc',
                f'{self.app_name}.config',
                f'config/{self.app_name}',
                '.config'
            ]:
                for ext in ['.yaml', '.json', '.toml', '']:
                    config_file = project_root / f'{name}{ext}'
                    if config_file.exists():
                        sources.append(config_file)
        
        # Environment variable config
        env_config = os.environ.get(f'{self.app_name.upper()}_CONFIG')
        if env_config:
            sources.append(Path(env_config))
        
        return sources
    
    def _load_source(self, source: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from a source.
        
        Args:
            source: Configuration source
            
        Returns:
            Configuration dictionary
        """
        path = normalize_path(source)
        
        if not path.exists():
            return {}
        
        suffix = path.suffix.lower()
        format = self.SUPPORTED_FORMATS.get(suffix)
        
        if format == 'json':
            return self.file_handler.read_json(path)
        elif format == 'yaml':
            return self.file_handler.read_yaml(path)
        elif format == 'toml':
            return self.file_handler.read_toml(path)
        elif format == 'ini':
            return self._load_ini(path)
        elif format == 'python':
            return self._load_python(path)
        else:
            # Try to detect format
            content = self.file_handler.read_file(path)
            return self._detect_and_load(content)
    
    def _load_ini(self, path: Path) -> Dict[str, Any]:
        """Load INI configuration.
        
        Args:
            path: INI file path
            
        Returns:
            Configuration dictionary
        """
        parser = configparser.ConfigParser()
        parser.read(path)
        
        config = {}
        for section in parser.sections():
            config[section] = dict(parser[section])
        
        # Include DEFAULT section if exists
        if parser.defaults():
            config['DEFAULT'] = dict(parser.defaults())
        
        return config
    
    def _save_ini(self, path: Path) -> None:
        """Save configuration as INI.
        
        Args:
            path: Output file path
        """
        parser = configparser.ConfigParser()
        
        for section, values in self._config.items():
            if isinstance(values, dict):
                parser[section] = {
                    str(k): str(v) for k, v in values.items()
                }
        
        with open(path, 'w') as f:
            parser.write(f)
    
    def _load_python(self, path: Path) -> Dict[str, Any]:
        """Load Python configuration module.
        
        Args:
            path: Python file path
            
        Returns:
            Configuration dictionary
        """
        # Load module
        spec = importlib.util.spec_from_file_location("config", path)
        if spec is None or spec.loader is None:
            raise FileOperationError(f"Cannot load Python config: {path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules["config"] = module
        spec.loader.exec_module(module)
        
        # Extract configuration
        config = {}
        for key in dir(module):
            if not key.startswith('_'):
                value = getattr(module, key)
                # Skip modules and functions
                if not callable(value) and not hasattr(value, '__module__'):
                    config[key] = value
        
        return config
    
    def _detect_and_load(self, content: str) -> Dict[str, Any]:
        """Detect format and load configuration.
        
        Args:
            content: Configuration content
            
        Returns:
            Configuration dictionary
        """
        # Try JSON
        try:
            return json.loads(content)
        except:
            pass
        
        # Try YAML
        try:
            return yaml.safe_load(content)
        except:
            pass
        
        # Try TOML
        try:
            return toml.loads(content)
        except:
            pass
        
        raise ValidationError("Cannot detect configuration format")
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value.
        
        Args:
            value: String value
            
        Returns:
            Parsed value
        """
        # Boolean
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        elif value.lower() in ('false', 'no', '0', 'off'):
            return False
        
        # Number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # List (comma-separated)
        if ',' in value:
            return [v.strip() for v in value.split(',')]
        
        # String
        return value
    
    @property
    def sources(self) -> List[str]:
        """Get list of loaded configuration sources."""
        return self._sources.copy()
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()