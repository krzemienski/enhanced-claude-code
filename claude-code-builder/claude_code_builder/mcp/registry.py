"""MCP server registry management."""

import json
import logging
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
import hashlib

from ..models.base import BaseModel
from ..exceptions.base import ClaudeCodeBuilderError, ConfigurationError
from .discovery import MCPServer

logger = logging.getLogger(__name__)


@dataclass
class RegistryEntry:
    """Entry in the MCP server registry."""
    server: MCPServer
    registered_at: datetime
    last_updated: datetime
    usage_count: int = 0
    last_used: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)
    custom_config: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "server": self.server.to_dict(),
            "registered_at": self.registered_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "tags": list(self.tags),
            "custom_config": self.custom_config,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegistryEntry":
        """Create from dictionary."""
        server_data = data["server"]
        server = MCPServer(
            name=server_data["name"],
            command=server_data["command"],
            args=server_data["args"],
            description=server_data.get("description"),
            version=server_data.get("version"),
            author=server_data.get("author"),
            capabilities=server_data.get("capabilities", []),
            schema=server_data.get("schema"),
            installed=server_data.get("installed", False),
            installation_path=Path(server_data["installation_path"]) if server_data.get("installation_path") else None,
            metadata=server_data.get("metadata", {})
        )
        
        return cls(
            server=server,
            registered_at=datetime.fromisoformat(data["registered_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            usage_count=data.get("usage_count", 0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            tags=set(data.get("tags", [])),
            custom_config=data.get("custom_config", {}),
            notes=data.get("notes", "")
        )


class MCPRegistry:
    """Manages registry of MCP servers."""
    
    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize MCP registry.
        
        Args:
            registry_path: Path to registry file
        """
        self.registry_path = registry_path or Path.home() / ".claude" / "mcp-registry.json"
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.entries: Dict[str, RegistryEntry] = {}
        self.load_registry()
    
    def load_registry(self) -> None:
        """Load registry from disk."""
        if not self.registry_path.exists():
            logger.info("No existing registry found, starting fresh")
            return
        
        try:
            with open(self.registry_path, "r") as f:
                data = json.load(f)
            
            for name, entry_data in data.get("entries", {}).items():
                try:
                    entry = RegistryEntry.from_dict(entry_data)
                    self.entries[name] = entry
                except Exception as e:
                    logger.warning(f"Failed to load registry entry {name}: {e}")
            
            logger.info(f"Loaded {len(self.entries)} entries from registry")
            
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
    
    def save_registry(self) -> None:
        """Save registry to disk."""
        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "entries": {
                    name: entry.to_dict()
                    for name, entry in self.entries.items()
                }
            }
            
            with open(self.registry_path, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self.entries)} entries to registry")
            
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
            raise ConfigurationError(f"Could not save registry: {e}")
    
    def register_server(
        self,
        server: MCPServer,
        tags: Optional[Set[str]] = None,
        custom_config: Optional[Dict[str, Any]] = None,
        notes: str = ""
    ) -> RegistryEntry:
        """
        Register a new MCP server.
        
        Args:
            server: Server to register
            tags: Optional tags
            custom_config: Custom configuration
            notes: Optional notes
            
        Returns:
            Registry entry
        """
        now = datetime.now()
        
        if server.name in self.entries:
            # Update existing entry
            entry = self.entries[server.name]
            entry.server = server
            entry.last_updated = now
            
            if tags:
                entry.tags.update(tags)
            if custom_config:
                entry.custom_config.update(custom_config)
            if notes:
                entry.notes = notes
        else:
            # Create new entry
            entry = RegistryEntry(
                server=server,
                registered_at=now,
                last_updated=now,
                tags=tags or set(),
                custom_config=custom_config or {},
                notes=notes
            )
            self.entries[server.name] = entry
        
        self.save_registry()
        logger.info(f"Registered server: {server.name}")
        
        return entry
    
    def unregister_server(self, server_name: str) -> bool:
        """
        Unregister a server.
        
        Args:
            server_name: Name of server to unregister
            
        Returns:
            True if unregistered
        """
        if server_name in self.entries:
            del self.entries[server_name]
            self.save_registry()
            logger.info(f"Unregistered server: {server_name}")
            return True
        
        return False
    
    def get_server(self, server_name: str) -> Optional[MCPServer]:
        """
        Get a registered server.
        
        Args:
            server_name: Server name
            
        Returns:
            Server if found
        """
        entry = self.entries.get(server_name)
        return entry.server if entry else None
    
    def get_entry(self, server_name: str) -> Optional[RegistryEntry]:
        """
        Get a registry entry.
        
        Args:
            server_name: Server name
            
        Returns:
            Registry entry if found
        """
        return self.entries.get(server_name)
    
    def list_servers(
        self,
        tags: Optional[Set[str]] = None,
        installed_only: bool = False
    ) -> List[MCPServer]:
        """
        List registered servers.
        
        Args:
            tags: Filter by tags
            installed_only: Only return installed servers
            
        Returns:
            List of servers
        """
        servers = []
        
        for entry in self.entries.values():
            # Apply filters
            if tags and not tags.intersection(entry.tags):
                continue
            
            if installed_only and not entry.server.installed:
                continue
            
            servers.append(entry.server)
        
        return servers
    
    def search_servers(
        self,
        query: str,
        search_tags: bool = True,
        search_notes: bool = True
    ) -> List[MCPServer]:
        """
        Search for servers.
        
        Args:
            query: Search query
            search_tags: Search in tags
            search_notes: Search in notes
            
        Returns:
            Matching servers
        """
        query_lower = query.lower()
        matches = []
        
        for entry in self.entries.values():
            # Search in server details
            if (query_lower in entry.server.name.lower() or
                (entry.server.description and query_lower in entry.server.description.lower())):
                matches.append(entry.server)
                continue
            
            # Search in tags
            if search_tags:
                if any(query_lower in tag.lower() for tag in entry.tags):
                    matches.append(entry.server)
                    continue
            
            # Search in notes
            if search_notes and query_lower in entry.notes.lower():
                matches.append(entry.server)
        
        return matches
    
    def add_tags(self, server_name: str, tags: Set[str]) -> bool:
        """
        Add tags to a server.
        
        Args:
            server_name: Server name
            tags: Tags to add
            
        Returns:
            True if successful
        """
        entry = self.entries.get(server_name)
        if not entry:
            return False
        
        entry.tags.update(tags)
        entry.last_updated = datetime.now()
        self.save_registry()
        
        return True
    
    def remove_tags(self, server_name: str, tags: Set[str]) -> bool:
        """
        Remove tags from a server.
        
        Args:
            server_name: Server name
            tags: Tags to remove
            
        Returns:
            True if successful
        """
        entry = self.entries.get(server_name)
        if not entry:
            return False
        
        entry.tags.difference_update(tags)
        entry.last_updated = datetime.now()
        self.save_registry()
        
        return True
    
    def update_custom_config(
        self,
        server_name: str,
        config: Dict[str, Any],
        merge: bool = True
    ) -> bool:
        """
        Update custom configuration.
        
        Args:
            server_name: Server name
            config: Configuration to update
            merge: Whether to merge or replace
            
        Returns:
            True if successful
        """
        entry = self.entries.get(server_name)
        if not entry:
            return False
        
        if merge:
            entry.custom_config.update(config)
        else:
            entry.custom_config = config
        
        entry.last_updated = datetime.now()
        self.save_registry()
        
        return True
    
    def record_usage(self, server_name: str) -> bool:
        """
        Record server usage.
        
        Args:
            server_name: Server name
            
        Returns:
            True if successful
        """
        entry = self.entries.get(server_name)
        if not entry:
            return False
        
        entry.usage_count += 1
        entry.last_used = datetime.now()
        self.save_registry()
        
        return True
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        total_servers = len(self.entries)
        installed_servers = sum(1 for e in self.entries.values() if e.server.installed)
        
        # Most used servers
        sorted_by_usage = sorted(
            self.entries.values(),
            key=lambda e: e.usage_count,
            reverse=True
        )
        
        most_used = [
            {
                "name": e.server.name,
                "usage_count": e.usage_count,
                "last_used": e.last_used.isoformat() if e.last_used else None
            }
            for e in sorted_by_usage[:5]
        ]
        
        # Tag statistics
        tag_counts = {}
        for entry in self.entries.values():
            for tag in entry.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            "total_servers": total_servers,
            "installed_servers": installed_servers,
            "installation_rate": installed_servers / total_servers if total_servers > 0 else 0,
            "most_used_servers": most_used,
            "popular_tags": sorted(
                tag_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "total_usage": sum(e.usage_count for e in self.entries.values())
        }
    
    def export_configuration(
        self,
        server_names: Optional[List[str]] = None,
        include_custom_config: bool = True
    ) -> Dict[str, Any]:
        """
        Export server configurations.
        
        Args:
            server_names: Specific servers to export
            include_custom_config: Include custom configurations
            
        Returns:
            Export data
        """
        if server_names:
            entries_to_export = {
                name: entry
                for name, entry in self.entries.items()
                if name in server_names
            }
        else:
            entries_to_export = self.entries
        
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "servers": {}
        }
        
        for name, entry in entries_to_export.items():
            server_data = {
                "command": entry.server.command,
                "args": entry.server.args,
                "description": entry.server.description,
                "tags": list(entry.tags)
            }
            
            if include_custom_config and entry.custom_config:
                server_data["config"] = entry.custom_config
            
            if entry.server.schema:
                server_data["schema"] = entry.server.schema
            
            export_data["servers"][name] = server_data
        
        return export_data
    
    def import_configuration(
        self,
        import_data: Dict[str, Any],
        overwrite: bool = False
    ) -> int:
        """
        Import server configurations.
        
        Args:
            import_data: Data to import
            overwrite: Overwrite existing entries
            
        Returns:
            Number of servers imported
        """
        imported = 0
        
        for name, server_data in import_data.get("servers", {}).items():
            if name in self.entries and not overwrite:
                logger.info(f"Skipping existing server: {name}")
                continue
            
            # Create server
            server = MCPServer(
                name=name,
                command=server_data["command"],
                args=server_data["args"],
                description=server_data.get("description"),
                schema=server_data.get("schema")
            )
            
            # Register with tags and config
            self.register_server(
                server=server,
                tags=set(server_data.get("tags", [])),
                custom_config=server_data.get("config", {})
            )
            
            imported += 1
        
        logger.info(f"Imported {imported} servers")
        return imported
    
    def generate_mcp_config(
        self,
        server_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate MCP configuration for Claude Code.
        
        Args:
            server_names: Specific servers to include
            
        Returns:
            MCP configuration
        """
        config = {
            "mcpServers": {}
        }
        
        servers_to_include = server_names or list(self.entries.keys())
        
        for name in servers_to_include:
            entry = self.entries.get(name)
            if entry and entry.server.installed:
                server_config = entry.server.to_mcp_config()
                
                # Apply custom config
                if entry.custom_config:
                    server_config.update(entry.custom_config)
                
                config["mcpServers"][name] = server_config
        
        return config