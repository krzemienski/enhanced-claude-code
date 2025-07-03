"""Loader for custom instruction rules from various sources."""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json
import yaml
from datetime import datetime
import hashlib
from urllib.parse import urlparse
import requests

from ..models.custom_instructions import (
    InstructionRule, InstructionSet, Priority
)
from .parser import InstructionParser
from .validator import InstructionValidator

logger = logging.getLogger(__name__)


class RuleLoader:
    """Loads instruction rules from various sources."""
    
    def __init__(self):
        """Initialize the rule loader."""
        self.parser = InstructionParser()
        self.validator = InstructionValidator()
        self.loaded_sets: Dict[str, InstructionSet] = {}
        self.load_history: List[Dict[str, Any]] = []
        
        # Cache for remote resources
        self.cache_dir = Path.home() / ".claude_code_builder" / "rule_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Default locations
        self.default_locations = [
            Path.home() / ".claude_code_builder" / "rules",
            Path.cwd() / "rules",
            Path.cwd() / ".claude" / "rules"
        ]
    
    def load_from_file(
        self,
        file_path: Union[str, Path],
        validate: bool = True
    ) -> InstructionSet:
        """Load rules from a file."""
        logger.info(f"Loading rules from file: {file_path}")
        
        try:
            # Parse the file
            instruction_set = self.parser.parse_file(file_path)
            
            # Validate if requested
            if validate:
                validation_result = self.validator.validate_instruction_set(
                    instruction_set
                )
                if not validation_result.is_valid:
                    raise ValueError(
                        f"Validation failed: {validation_result.errors}"
                    )
                elif validation_result.warnings:
                    logger.warning(
                        f"Validation warnings: {validation_result.warnings}"
                    )
            
            # Store the loaded set
            set_id = self._generate_set_id(instruction_set)
            self.loaded_sets[set_id] = instruction_set
            
            # Record in history
            self._record_load(file_path, "file", set_id, True)
            
            return instruction_set
            
        except Exception as e:
            logger.error(f"Failed to load from file {file_path}: {e}")
            self._record_load(file_path, "file", None, False, str(e))
            raise
    
    def load_from_url(
        self,
        url: str,
        cache: bool = True,
        validate: bool = True
    ) -> InstructionSet:
        """Load rules from a URL."""
        logger.info(f"Loading rules from URL: {url}")
        
        try:
            # Check cache first
            if cache:
                cached = self._get_cached_url(url)
                if cached:
                    return self.load_from_string(
                        cached["content"],
                        format_hint=cached["format"],
                        validate=validate
                    )
            
            # Fetch from URL
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content = response.text
            
            # Determine format from URL or content-type
            format_hint = self._detect_format_from_url(url, response)
            
            # Cache if enabled
            if cache:
                self._cache_url_content(url, content, format_hint)
            
            # Parse and validate
            instruction_set = self.load_from_string(
                content, format_hint, validate
            )
            
            # Add URL metadata
            instruction_set.metadata["source_url"] = url
            
            # Record in history
            set_id = self._generate_set_id(instruction_set)
            self._record_load(url, "url", set_id, True)
            
            return instruction_set
            
        except Exception as e:
            logger.error(f"Failed to load from URL {url}: {e}")
            self._record_load(url, "url", None, False, str(e))
            raise
    
    def load_from_string(
        self,
        content: str,
        format_hint: str = "auto",
        validate: bool = True
    ) -> InstructionSet:
        """Load rules from a string."""
        logger.info(f"Loading rules from string (format: {format_hint})")
        
        try:
            # Parse the string
            instruction_set = self.parser.parse_string(content, format_hint)
            
            # Validate if requested
            if validate:
                validation_result = self.validator.validate_instruction_set(
                    instruction_set
                )
                if not validation_result.is_valid:
                    raise ValueError(
                        f"Validation failed: {validation_result.errors}"
                    )
            
            # Store the loaded set
            set_id = self._generate_set_id(instruction_set)
            self.loaded_sets[set_id] = instruction_set
            
            return instruction_set
            
        except Exception as e:
            logger.error(f"Failed to load from string: {e}")
            raise
    
    def load_from_directory(
        self,
        directory: Union[str, Path],
        pattern: str = "*.{json,yaml,yml,txt,md}",
        recursive: bool = True,
        validate: bool = True
    ) -> List[InstructionSet]:
        """Load all rule files from a directory."""
        dir_path = Path(directory)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        logger.info(f"Loading rules from directory: {directory}")
        
        loaded_sets = []
        
        # Find matching files
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        
        # Load each file
        for file_path in files:
            try:
                instruction_set = self.load_from_file(file_path, validate)
                loaded_sets.append(instruction_set)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                # Continue with other files
        
        logger.info(f"Loaded {len(loaded_sets)} rule sets from {directory}")
        return loaded_sets
    
    def load_defaults(self, validate: bool = True) -> List[InstructionSet]:
        """Load rules from default locations."""
        logger.info("Loading rules from default locations")
        
        all_sets = []
        
        for location in self.default_locations:
            if location.exists() and location.is_dir():
                try:
                    sets = self.load_from_directory(
                        location, recursive=True, validate=validate
                    )
                    all_sets.extend(sets)
                except Exception as e:
                    logger.warning(f"Failed to load from {location}: {e}")
        
        return all_sets
    
    def merge_sets(
        self,
        *instruction_sets: InstructionSet,
        name: Optional[str] = None,
        resolve_conflicts: str = "priority"
    ) -> InstructionSet:
        """Merge multiple instruction sets."""
        if not instruction_sets:
            raise ValueError("No instruction sets to merge")
        
        # Create merged set
        merged = InstructionSet(
            name=name or "Merged Rules",
            version="1.0.0",
            rules=[],
            metadata={
                "merged_at": datetime.now().isoformat(),
                "merge_strategy": resolve_conflicts,
                "source_sets": []
            }
        )
        
        # Track rule names for conflict resolution
        rule_registry = {}
        
        for inst_set in instruction_sets:
            merged.metadata["source_sets"].append({
                "name": inst_set.name,
                "version": inst_set.version,
                "rule_count": len(inst_set.rules)
            })
            
            for rule in inst_set.rules:
                # Handle conflicts
                if rule.name in rule_registry:
                    rule = self._resolve_conflict(
                        rule_registry[rule.name],
                        rule,
                        resolve_conflicts
                    )
                
                rule_registry[rule.name] = rule
        
        # Add all resolved rules
        merged.rules = list(rule_registry.values())
        
        # Store the merged set
        set_id = self._generate_set_id(merged)
        self.loaded_sets[set_id] = merged
        
        logger.info(
            f"Merged {len(instruction_sets)} sets into "
            f"{len(merged.rules)} rules"
        )
        
        return merged
    
    def get_loaded_set(self, set_id: str) -> Optional[InstructionSet]:
        """Get a loaded instruction set by ID."""
        return self.loaded_sets.get(set_id)
    
    def list_loaded_sets(self) -> List[Dict[str, Any]]:
        """List all loaded instruction sets."""
        return [
            {
                "id": set_id,
                "name": inst_set.name,
                "version": inst_set.version,
                "rule_count": len(inst_set.rules),
                "source": inst_set.metadata.get("source_file") or 
                         inst_set.metadata.get("source_url", "string")
            }
            for set_id, inst_set in self.loaded_sets.items()
        ]
    
    def clear_loaded_sets(self) -> None:
        """Clear all loaded instruction sets."""
        self.loaded_sets.clear()
        logger.info("Cleared all loaded instruction sets")
    
    def export_set(
        self,
        set_id: str,
        file_path: Union[str, Path],
        format: str = "json"
    ) -> None:
        """Export an instruction set to a file."""
        inst_set = self.loaded_sets.get(set_id)
        if not inst_set:
            raise ValueError(f"Instruction set not found: {set_id}")
        
        file_path = Path(file_path)
        
        # Prepare data
        data = {
            "name": inst_set.name,
            "version": inst_set.version,
            "metadata": inst_set.metadata,
            "rules": [
                {
                    "name": rule.name,
                    "pattern": rule.pattern,
                    "action": rule.action,
                    "priority": rule.priority.name.lower(),
                    "conditions": rule.conditions,
                    "metadata": rule.metadata
                }
                for rule in inst_set.rules
            ]
        }
        
        # Write based on format
        if format == "json":
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        elif format in ["yaml", "yml"]:
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"Exported instruction set to {file_path}")
    
    def _generate_set_id(self, instruction_set: InstructionSet) -> str:
        """Generate unique ID for instruction set."""
        # Create hash from name, version, and rule count
        content = f"{instruction_set.name}:{instruction_set.version}:{len(instruction_set.rules)}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _record_load(
        self,
        source: Any,
        source_type: str,
        set_id: Optional[str],
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Record load operation in history."""
        self.load_history.append({
            "timestamp": datetime.now().isoformat(),
            "source": str(source),
            "source_type": source_type,
            "set_id": set_id,
            "success": success,
            "error": error
        })
    
    def _get_cached_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached content for URL."""
        cache_file = self._get_cache_path(url)
        
        if cache_file.exists():
            # Check cache age (default 24 hours)
            age = datetime.now().timestamp() - cache_file.stat().st_mtime
            if age < 86400:  # 24 hours
                try:
                    with open(cache_file, 'r') as f:
                        return json.load(f)
                except:
                    pass
        
        return None
    
    def _cache_url_content(
        self,
        url: str,
        content: str,
        format_hint: str
    ) -> None:
        """Cache URL content."""
        cache_file = self._get_cache_path(url)
        
        cache_data = {
            "url": url,
            "content": content,
            "format": format_hint,
            "cached_at": datetime.now().isoformat()
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to cache URL content: {e}")
    
    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path for URL."""
        # Create safe filename from URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"url_{url_hash}.json"
    
    def _detect_format_from_url(
        self,
        url: str,
        response: requests.Response
    ) -> str:
        """Detect format from URL or response."""
        # Check URL extension
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        if path.endswith('.json'):
            return "json"
        elif path.endswith(('.yaml', '.yml')):
            return "yaml"
        elif path.endswith('.md'):
            return "markdown"
        elif path.endswith('.txt'):
            return "text"
        
        # Check content-type
        content_type = response.headers.get('content-type', '').lower()
        if 'json' in content_type:
            return "json"
        elif 'yaml' in content_type:
            return "yaml"
        
        # Default to auto-detection
        return "auto"
    
    def _resolve_conflict(
        self,
        existing: InstructionRule,
        new: InstructionRule,
        strategy: str
    ) -> InstructionRule:
        """Resolve conflict between rules."""
        if strategy == "priority":
            # Keep higher priority rule
            if new.priority.value > existing.priority.value:
                return new
            else:
                return existing
        elif strategy == "newest":
            # Always use the newer rule
            return new
        elif strategy == "merge":
            # Merge metadata and conditions
            merged = InstructionRule(
                name=existing.name,
                pattern=new.pattern or existing.pattern,
                action=new.action or existing.action,
                priority=max(existing.priority, new.priority, key=lambda p: p.value),
                conditions={**existing.conditions, **new.conditions},
                metadata={**existing.metadata, **new.metadata}
            )
            return merged
        else:
            # Default to keeping existing
            return existing
    
    def create_rule_package(
        self,
        name: str,
        rules: List[InstructionRule],
        metadata: Optional[Dict[str, Any]] = None
    ) -> InstructionSet:
        """Create a new rule package."""
        package = InstructionSet(
            name=name,
            version="1.0.0",
            rules=rules,
            metadata=metadata or {}
        )
        
        # Add package metadata
        package.metadata.update({
            "created_at": datetime.now().isoformat(),
            "rule_count": len(rules),
            "priority_distribution": self._get_priority_distribution(rules)
        })
        
        # Validate the package
        validation = self.validator.validate_instruction_set(package)
        if not validation.is_valid:
            raise ValueError(f"Invalid rule package: {validation.errors}")
        
        # Store the package
        set_id = self._generate_set_id(package)
        self.loaded_sets[set_id] = package
        
        return package
    
    def _get_priority_distribution(
        self,
        rules: List[InstructionRule]
    ) -> Dict[str, int]:
        """Get distribution of rule priorities."""
        distribution = {}
        
        for rule in rules:
            priority_name = rule.priority.name
            distribution[priority_name] = distribution.get(priority_name, 0) + 1
        
        return distribution