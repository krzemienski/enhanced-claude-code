"""Plugin system for Claude Code Builder."""
import importlib
import importlib.util
import inspect
from pathlib import Path
from typing import List, Dict, Any, Optional, Protocol, Type
from dataclasses import dataclass, field
import sys
import json

from ..exceptions.base import ClaudeCodeBuilderError, ValidationError
from ..logging.logger import get_logger
from ..utils.file_handler import FileHandler
from ..utils.path_utils import find_files, get_config_dir

logger = get_logger(__name__)


class Plugin(Protocol):
    """Plugin protocol that all plugins must implement."""
    
    @property
    def name(self) -> str:
        """Plugin name."""
        ...
    
    @property
    def version(self) -> str:
        """Plugin version."""
        ...
    
    @property
    def description(self) -> str:
        """Plugin description."""
        ...
    
    def initialize(self, context: Dict[str, Any]) -> None:
        """Initialize plugin with context."""
        ...
    
    def execute(self, **kwargs) -> Any:
        """Execute plugin functionality."""
        ...
    
    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        ...


@dataclass
class PluginInfo:
    """Information about a plugin."""
    name: str
    version: str
    description: str
    module_path: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def id(self) -> str:
        """Plugin identifier."""
        return f"{self.name}@{self.version}"


@dataclass
class PluginHook:
    """Plugin hook definition."""
    name: str
    description: str
    params: List[str] = field(default_factory=list)
    returns: Optional[str] = None


class PluginManager:
    """Manages plugins for Claude Code Builder."""
    
    # Available hooks
    HOOKS = {
        'pre_build': PluginHook(
            name='pre_build',
            description='Called before project build starts',
            params=['project_spec', 'settings'],
            returns='modified_project_spec'
        ),
        'post_build': PluginHook(
            name='post_build',
            description='Called after project build completes',
            params=['project_spec', 'result', 'output_dir']
        ),
        'pre_phase': PluginHook(
            name='pre_phase',
            description='Called before each phase execution',
            params=['phase', 'context'],
            returns='modified_phase'
        ),
        'post_phase': PluginHook(
            name='post_phase',
            description='Called after each phase execution',
            params=['phase', 'result', 'context']
        ),
        'pre_task': PluginHook(
            name='pre_task',
            description='Called before each task execution',
            params=['task', 'context'],
            returns='modified_task'
        ),
        'post_task': PluginHook(
            name='post_task',
            description='Called after each task execution',
            params=['task', 'result', 'context']
        ),
        'on_error': PluginHook(
            name='on_error',
            description='Called when an error occurs',
            params=['error', 'context'],
            returns='handled'
        ),
        'custom_command': PluginHook(
            name='custom_command',
            description='Register custom CLI commands',
            params=['parser'],
            returns='command_handlers'
        )
    }
    
    def __init__(self, plugin_dir: Optional[Path] = None):
        """Initialize plugin manager.
        
        Args:
            plugin_dir: Plugin directory
        """
        self.plugin_dir = plugin_dir or get_config_dir() / 'plugins'
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._hooks: Dict[str, List[Plugin]] = {hook: [] for hook in self.HOOKS}
        
        self.file_handler = FileHandler()
        
        # Load plugin registry
        self._load_registry()
        
        # Auto-discover plugins
        self._discover_plugins()
    
    def list_plugins(self) -> List[PluginInfo]:
        """List all available plugins.
        
        Returns:
            List of plugin info
        """
        return list(self._plugin_info.values())
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance or None
        """
        return self._plugins.get(name)
    
    def load_plugin(self, module_path: str) -> Plugin:
        """Load a plugin from module path.
        
        Args:
            module_path: Path to plugin module
            
        Returns:
            Loaded plugin
            
        Raises:
            ValidationError: If plugin is invalid
        """
        try:
            # Load module
            if module_path.endswith('.py'):
                # Load from file
                spec = importlib.util.spec_from_file_location("plugin", module_path)
                if spec is None or spec.loader is None:
                    raise ValidationError(f"Cannot load plugin from {module_path}")
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                # Load from package
                module = importlib.import_module(module_path)
            
            # Find plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, 'name') and hasattr(obj, 'execute'):
                    plugin_class = obj
                    break
            
            if plugin_class is None:
                raise ValidationError("No valid plugin class found")
            
            # Instantiate plugin
            plugin = plugin_class()
            
            # Validate plugin
            self._validate_plugin(plugin)
            
            return plugin
            
        except Exception as e:
            raise ValidationError(f"Failed to load plugin: {e}")
    
    def register_plugin(
        self,
        plugin: Plugin,
        enabled: bool = True
    ) -> None:
        """Register a plugin.
        
        Args:
            plugin: Plugin instance
            enabled: Whether plugin is enabled
        """
        # Create plugin info
        info = PluginInfo(
            name=plugin.name,
            version=plugin.version,
            description=plugin.description,
            module_path=inspect.getfile(plugin.__class__),
            enabled=enabled
        )
        
        # Register plugin
        self._plugins[plugin.name] = plugin
        self._plugin_info[plugin.name] = info
        
        # Register hooks
        for hook_name in self.HOOKS:
            if hasattr(plugin, hook_name):
                self._hooks[hook_name].append(plugin)
        
        logger.info(f"Registered plugin: {plugin.name} v{plugin.version}")
    
    def unregister_plugin(self, name: str) -> None:
        """Unregister a plugin.
        
        Args:
            name: Plugin name
        """
        if name not in self._plugins:
            return
        
        plugin = self._plugins[name]
        
        # Remove from hooks
        for hook_list in self._hooks.values():
            if plugin in hook_list:
                hook_list.remove(plugin)
        
        # Cleanup plugin
        try:
            plugin.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up plugin {name}: {e}")
        
        # Remove registration
        del self._plugins[name]
        del self._plugin_info[name]
        
        logger.info(f"Unregistered plugin: {name}")
    
    def enable_plugin(self, name: str) -> None:
        """Enable a plugin.
        
        Args:
            name: Plugin name
        """
        if name in self._plugin_info:
            self._plugin_info[name].enabled = True
            self._save_registry()
    
    def disable_plugin(self, name: str) -> None:
        """Disable a plugin.
        
        Args:
            name: Plugin name
        """
        if name in self._plugin_info:
            self._plugin_info[name].enabled = False
            self._save_registry()
    
    async def install_plugin(self, source: str) -> bool:
        """Install a plugin from source.
        
        Args:
            source: Plugin source (path, URL, or package name)
            
        Returns:
            True if successful
        """
        try:
            # Determine source type
            source_path = Path(source)
            
            if source_path.exists():
                # Local file/directory
                return await self._install_local_plugin(source_path)
            elif source.startswith(('http://', 'https://')):
                # URL
                return await self._install_url_plugin(source)
            else:
                # Package name
                return await self._install_package_plugin(source)
                
        except Exception as e:
            logger.error(f"Failed to install plugin: {e}")
            return False
    
    def execute_hook(
        self,
        hook_name: str,
        **kwargs
    ) -> Optional[Any]:
        """Execute a plugin hook.
        
        Args:
            hook_name: Hook name
            **kwargs: Hook parameters
            
        Returns:
            Hook result if any
        """
        if hook_name not in self.HOOKS:
            logger.warning(f"Unknown hook: {hook_name}")
            return None
        
        results = []
        
        for plugin in self._hooks[hook_name]:
            # Check if plugin is enabled
            info = self._plugin_info.get(plugin.name)
            if info and not info.enabled:
                continue
            
            try:
                # Get hook method
                hook_method = getattr(plugin, hook_name)
                
                # Execute hook
                result = hook_method(**kwargs)
                
                if result is not None:
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Error executing hook {hook_name} in plugin {plugin.name}: {e}")
        
        # Return results based on hook type
        hook_def = self.HOOKS[hook_name]
        if hook_def.returns:
            # Return last result for hooks that modify data
            return results[-1] if results else None
        else:
            # Return all results for notification hooks
            return results
    
    def _validate_plugin(self, plugin: Plugin) -> None:
        """Validate plugin interface.
        
        Args:
            plugin: Plugin to validate
            
        Raises:
            ValidationError: If plugin is invalid
        """
        # Check required attributes
        required_attrs = ['name', 'version', 'description']
        for attr in required_attrs:
            if not hasattr(plugin, attr):
                raise ValidationError(f"Plugin missing required attribute: {attr}")
        
        # Check required methods
        required_methods = ['initialize', 'execute', 'cleanup']
        for method in required_methods:
            if not hasattr(plugin, method) or not callable(getattr(plugin, method)):
                raise ValidationError(f"Plugin missing required method: {method}")
    
    def _discover_plugins(self) -> None:
        """Discover and load plugins from plugin directory."""
        # Find Python files
        plugin_files = find_files("*.py", self.plugin_dir, recursive=True)
        
        for plugin_file in plugin_files:
            if plugin_file.name.startswith('_'):
                continue
            
            try:
                # Load plugin
                plugin = self.load_plugin(str(plugin_file))
                
                # Check if already registered
                if plugin.name not in self._plugins:
                    self.register_plugin(plugin)
                    
            except Exception as e:
                logger.debug(f"Failed to load plugin from {plugin_file}: {e}")
    
    def _load_registry(self) -> None:
        """Load plugin registry from disk."""
        registry_file = self.plugin_dir / 'registry.json'
        
        if not registry_file.exists():
            return
        
        try:
            registry_data = self.file_handler.read_json(registry_file)
            
            for plugin_data in registry_data.get('plugins', []):
                info = PluginInfo(**plugin_data)
                
                # Try to load plugin
                try:
                    plugin = self.load_plugin(info.module_path)
                    self.register_plugin(plugin, info.enabled)
                except Exception as e:
                    logger.warning(f"Failed to load registered plugin {info.name}: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to load plugin registry: {e}")
    
    def _save_registry(self) -> None:
        """Save plugin registry to disk."""
        registry_file = self.plugin_dir / 'registry.json'
        
        registry_data = {
            'version': '1.0',
            'plugins': [
                {
                    'name': info.name,
                    'version': info.version,
                    'description': info.description,
                    'module_path': info.module_path,
                    'enabled': info.enabled,
                    'config': info.config
                }
                for info in self._plugin_info.values()
            ]
        }
        
        try:
            self.file_handler.write_json(registry_file, registry_data)
        except Exception as e:
            logger.warning(f"Failed to save plugin registry: {e}")
    
    async def _install_local_plugin(self, path: Path) -> bool:
        """Install plugin from local path.
        
        Args:
            path: Local path to plugin
            
        Returns:
            True if successful
        """
        # Copy to plugin directory
        if path.is_file():
            dest = self.plugin_dir / path.name
            self.file_handler.copy_file(path, dest)
        else:
            # Copy directory
            import shutil
            dest = self.plugin_dir / path.name
            shutil.copytree(path, dest)
        
        # Load and register plugin
        plugin = self.load_plugin(str(dest))
        self.register_plugin(plugin)
        
        # Save registry
        self._save_registry()
        
        return True
    
    async def _install_url_plugin(self, url: str) -> bool:
        """Install plugin from URL.
        
        Args:
            url: Plugin URL
            
        Returns:
            True if successful
        """
        # Download plugin
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ClaudeCodeBuilderError(f"Failed to download plugin: {response.status}")
                
                content = await response.read()
        
        # Save to plugin directory
        filename = url.split('/')[-1]
        if not filename.endswith('.py'):
            filename += '.py'
        
        plugin_file = self.plugin_dir / filename
        plugin_file.write_bytes(content)
        
        # Load and register
        plugin = self.load_plugin(str(plugin_file))
        self.register_plugin(plugin)
        
        # Save registry
        self._save_registry()
        
        return True
    
    async def _install_package_plugin(self, package: str) -> bool:
        """Install plugin from package.
        
        Args:
            package: Package name
            
        Returns:
            True if successful
        """
        # Install package
        import subprocess
        
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise ClaudeCodeBuilderError(f"Failed to install package: {result.stderr}")
        
        # Import and register
        module = importlib.import_module(package)
        
        # Find plugin class
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if hasattr(obj, 'name') and hasattr(obj, 'execute'):
                plugin = obj()
                self.register_plugin(plugin)
                break
        
        # Save registry
        self._save_registry()
        
        return True