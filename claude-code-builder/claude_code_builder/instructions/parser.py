"""Parser for custom instructions and rules."""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import re
import json
import yaml
from pathlib import Path
from datetime import datetime

from ..models.custom_instructions import (
    InstructionRule, InstructionSet, Priority,
    ValidationResult
)

logger = logging.getLogger(__name__)


class InstructionParser:
    """Parser for various instruction formats."""
    
    def __init__(self):
        """Initialize the instruction parser."""
        self.supported_formats = {
            ".json": self._parse_json,
            ".yaml": self._parse_yaml,
            ".yml": self._parse_yaml,
            ".txt": self._parse_text,
            ".md": self._parse_markdown
        }
        
        # Pattern definitions for text parsing
        self.patterns = {
            "rule_header": re.compile(r"^#{1,3}\s*(.+)$", re.MULTILINE),
            "pattern": re.compile(r"^pattern:\s*(.+)$", re.MULTILINE),
            "action": re.compile(r"^action:\s*(.+)$", re.MULTILINE),
            "priority": re.compile(r"^priority:\s*(\w+)$", re.MULTILINE),
            "condition": re.compile(r"^if\s+(.+?):\s*(.+)$", re.MULTILINE),
            "metadata": re.compile(r"^@(\w+):\s*(.+)$", re.MULTILINE)
        }
        
        # Priority mapping
        self.priority_map = {
            "critical": Priority.CRITICAL,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW,
            "info": Priority.INFO
        }
    
    def parse_file(self, file_path: Union[str, Path]) -> InstructionSet:
        """Parse instruction file based on extension."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Instruction file not found: {file_path}")
        
        ext = path.suffix.lower()
        if ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {ext}")
        
        logger.info(f"Parsing instruction file: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parser_func = self.supported_formats[ext]
            instruction_set = parser_func(content, path.name)
            
            # Add file metadata
            instruction_set.metadata["source_file"] = str(path)
            instruction_set.metadata["parsed_at"] = datetime.now().isoformat()
            
            return instruction_set
            
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            raise
    
    def parse_string(
        self,
        content: str,
        format_hint: str = "auto"
    ) -> InstructionSet:
        """Parse instruction string with format hint."""
        if format_hint == "auto":
            # Try to detect format
            content_stripped = content.strip()
            if content_stripped.startswith("{") or content_stripped.startswith("["):
                format_hint = "json"
            elif ":" in content_stripped.split("\n")[0]:
                format_hint = "yaml"
            elif content_stripped.startswith("#"):
                format_hint = "markdown"
            else:
                format_hint = "text"
        
        logger.info(f"Parsing instruction string as {format_hint}")
        
        if format_hint == "json":
            return self._parse_json(content, "inline")
        elif format_hint in ["yaml", "yml"]:
            return self._parse_yaml(content, "inline")
        elif format_hint == "markdown":
            return self._parse_markdown(content, "inline")
        else:
            return self._parse_text(content, "inline")
    
    def _parse_json(self, content: str, source: str) -> InstructionSet:
        """Parse JSON format instructions."""
        try:
            data = json.loads(content)
            return self._parse_structured_data(data, source, "json")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise ValueError(f"Invalid JSON format: {e}")
    
    def _parse_yaml(self, content: str, source: str) -> InstructionSet:
        """Parse YAML format instructions."""
        try:
            data = yaml.safe_load(content)
            return self._parse_structured_data(data, source, "yaml")
        except yaml.YAMLError as e:
            logger.error(f"YAML parse error: {e}")
            raise ValueError(f"Invalid YAML format: {e}")
    
    def _parse_structured_data(
        self,
        data: Dict[str, Any],
        source: str,
        format_type: str
    ) -> InstructionSet:
        """Parse structured data (JSON/YAML) into instruction set."""
        # Extract metadata
        metadata = data.get("metadata", {})
        metadata["format"] = format_type
        
        # Create instruction set
        instruction_set = InstructionSet(
            name=data.get("name", f"Rules from {source}"),
            version=data.get("version", "1.0.0"),
            rules=[],
            metadata=metadata
        )
        
        # Parse rules
        rules_data = data.get("rules", [])
        for rule_data in rules_data:
            rule = self._parse_structured_rule(rule_data)
            instruction_set.rules.append(rule)
        
        # Parse global settings
        if "globals" in data:
            self._apply_global_settings(instruction_set, data["globals"])
        
        return instruction_set
    
    def _parse_structured_rule(self, rule_data: Dict[str, Any]) -> InstructionRule:
        """Parse a single rule from structured data."""
        # Parse priority
        priority_str = rule_data.get("priority", "medium").lower()
        priority = self.priority_map.get(priority_str, Priority.MEDIUM)
        
        # Parse conditions
        conditions = {}
        if "conditions" in rule_data:
            conditions = self._parse_conditions(rule_data["conditions"])
        
        # Parse metadata
        metadata = rule_data.get("metadata", {})
        
        # Handle special metadata fields
        if "depends_on" in rule_data:
            metadata["depends_on"] = rule_data["depends_on"]
        if "excludes" in rule_data:
            metadata["excludes"] = rule_data["excludes"]
        if "tags" in rule_data:
            metadata["tags"] = rule_data["tags"]
        
        return InstructionRule(
            name=rule_data.get("name", "Unnamed Rule"),
            pattern=rule_data.get("pattern"),
            action=rule_data.get("action", ""),
            priority=priority,
            conditions=conditions,
            metadata=metadata
        )
    
    def _parse_text(self, content: str, source: str) -> InstructionSet:
        """Parse plain text format instructions."""
        instruction_set = InstructionSet(
            name=f"Rules from {source}",
            version="1.0.0",
            rules=[],
            metadata={"format": "text"}
        )
        
        # Split into rule blocks
        rule_blocks = self._split_text_rules(content)
        
        for block in rule_blocks:
            rule = self._parse_text_rule(block)
            if rule:
                instruction_set.rules.append(rule)
        
        return instruction_set
    
    def _parse_markdown(self, content: str, source: str) -> InstructionSet:
        """Parse markdown format instructions."""
        instruction_set = InstructionSet(
            name=f"Rules from {source}",
            version="1.0.0",
            rules=[],
            metadata={"format": "markdown"}
        )
        
        # Extract title if present
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            instruction_set.name = title_match.group(1)
        
        # Split by rule headers
        rule_sections = re.split(r"^#{2,3}\s+", content, flags=re.MULTILINE)
        
        for section in rule_sections[1:]:  # Skip content before first rule
            lines = section.strip().split("\n")
            if lines:
                rule_name = lines[0]
                rule_content = "\n".join(lines[1:])
                
                rule = self._parse_markdown_rule(rule_name, rule_content)
                if rule:
                    instruction_set.rules.append(rule)
        
        return instruction_set
    
    def _split_text_rules(self, content: str) -> List[str]:
        """Split text content into rule blocks."""
        blocks = []
        current_block = []
        
        for line in content.split("\n"):
            line = line.strip()
            
            # Detect rule separator
            if line.startswith("---") or line.startswith("==="):
                if current_block:
                    blocks.append("\n".join(current_block))
                    current_block = []
            elif line or current_block:  # Include line if non-empty or continuing block
                current_block.append(line)
        
        # Add last block
        if current_block:
            blocks.append("\n".join(current_block))
        
        return blocks
    
    def _parse_text_rule(self, block: str) -> Optional[InstructionRule]:
        """Parse a single rule from text block."""
        lines = block.strip().split("\n")
        if not lines:
            return None
        
        # First line is typically the rule name
        name = lines[0].strip()
        content = "\n".join(lines[1:]) if len(lines) > 1 else ""
        
        # Extract components
        pattern = None
        pattern_match = self.patterns["pattern"].search(content)
        if pattern_match:
            pattern = pattern_match.group(1).strip()
        
        action = "notify:Rule matched"
        action_match = self.patterns["action"].search(content)
        if action_match:
            action = action_match.group(1).strip()
        
        priority = Priority.MEDIUM
        priority_match = self.patterns["priority"].search(content)
        if priority_match:
            priority_str = priority_match.group(1).lower()
            priority = self.priority_map.get(priority_str, Priority.MEDIUM)
        
        # Extract conditions
        conditions = {}
        for condition_match in self.patterns["condition"].finditer(content):
            field = condition_match.group(1).strip()
            value = condition_match.group(2).strip()
            conditions[field] = self._parse_condition_value(value)
        
        # Extract metadata
        metadata = {}
        for meta_match in self.patterns["metadata"].finditer(content):
            key = meta_match.group(1)
            value = meta_match.group(2).strip()
            metadata[key] = self._parse_metadata_value(value)
        
        return InstructionRule(
            name=name,
            pattern=pattern,
            action=action,
            priority=priority,
            conditions=conditions,
            metadata=metadata
        )
    
    def _parse_markdown_rule(
        self,
        name: str,
        content: str
    ) -> Optional[InstructionRule]:
        """Parse a single rule from markdown content."""
        # Similar to text parsing but with markdown-specific handling
        rule = self._parse_text_rule(f"{name}\n{content}")
        
        if rule:
            # Extract code blocks as patterns or actions
            code_blocks = re.findall(r"```(\w*)\n(.*?)\n```", content, re.DOTALL)
            
            for lang, code in code_blocks:
                if lang == "regex" or lang == "pattern":
                    rule.pattern = code.strip()
                elif lang == "action":
                    rule.action = code.strip()
                elif lang == "condition":
                    # Parse condition code block
                    condition_data = self._parse_condition_block(code)
                    rule.conditions.update(condition_data)
        
        return rule
    
    def _parse_conditions(
        self,
        conditions_data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Parse conditions from structured data."""
        if isinstance(conditions_data, list):
            # Convert list of conditions to dict
            conditions = {}
            for cond in conditions_data:
                if isinstance(cond, dict) and "field" in cond:
                    field = cond["field"]
                    conditions[field] = self._parse_single_condition(cond)
            return conditions
        else:
            # Already a dict
            parsed = {}
            for field, condition in conditions_data.items():
                parsed[field] = self._parse_single_condition(condition)
            return parsed
    
    def _parse_single_condition(
        self,
        condition: Union[str, Dict[str, Any]]
    ) -> Union[Any, Dict[str, Any]]:
        """Parse a single condition value."""
        if isinstance(condition, dict):
            # Complex condition with operator
            return condition
        else:
            # Simple value condition
            return condition
    
    def _parse_condition_value(self, value: str) -> Any:
        """Parse condition value from string."""
        value = value.strip()
        
        # Try to parse as JSON
        try:
            return json.loads(value)
        except:
            pass
        
        # Check for special values
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        elif value.lower() == "null":
            return None
        
        # Check for numeric values
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except:
            pass
        
        # Return as string
        return value
    
    def _parse_metadata_value(self, value: str) -> Any:
        """Parse metadata value from string."""
        # Similar to condition value parsing
        return self._parse_condition_value(value)
    
    def _parse_condition_block(self, code: str) -> Dict[str, Any]:
        """Parse a condition code block."""
        conditions = {}
        
        # Simple parser for condition expressions
        for line in code.strip().split("\n"):
            if "==" in line:
                parts = line.split("==", 1)
                field = parts[0].strip()
                value = self._parse_condition_value(parts[1].strip())
                conditions[field] = value
            elif "!=" in line:
                parts = line.split("!=", 1)
                field = parts[0].strip()
                value = self._parse_condition_value(parts[1].strip())
                conditions[field] = {"operator": "ne", "value": value}
            elif ">" in line:
                parts = line.split(">", 1)
                field = parts[0].strip()
                value = self._parse_condition_value(parts[1].strip())
                conditions[field] = {"operator": "gt", "value": value}
            elif "<" in line:
                parts = line.split("<", 1)
                field = parts[0].strip()
                value = self._parse_condition_value(parts[1].strip())
                conditions[field] = {"operator": "lt", "value": value}
        
        return conditions
    
    def _apply_global_settings(
        self,
        instruction_set: InstructionSet,
        globals_data: Dict[str, Any]
    ) -> None:
        """Apply global settings to instruction set."""
        # Apply default priority
        if "default_priority" in globals_data:
            default_priority = self.priority_map.get(
                globals_data["default_priority"].lower(),
                Priority.MEDIUM
            )
            
            # Apply to rules without explicit priority
            for rule in instruction_set.rules:
                if "default_priority" in rule.metadata:
                    rule.priority = default_priority
        
        # Apply global metadata
        if "metadata" in globals_data:
            for rule in instruction_set.rules:
                # Merge with existing metadata (rule metadata takes precedence)
                global_meta = globals_data["metadata"].copy()
                global_meta.update(rule.metadata)
                rule.metadata = global_meta
        
        # Apply global tags
        if "tags" in globals_data:
            global_tags = set(globals_data["tags"])
            for rule in instruction_set.rules:
                rule_tags = set(rule.metadata.get("tags", []))
                rule.metadata["tags"] = list(rule_tags.union(global_tags))
    
    def validate_instruction_set(
        self,
        instruction_set: InstructionSet
    ) -> ValidationResult:
        """Validate parsed instruction set."""
        errors = []
        warnings = []
        
        # Check for empty rules
        if not instruction_set.rules:
            warnings.append("Instruction set contains no rules")
        
        # Validate each rule
        rule_names = set()
        for i, rule in enumerate(instruction_set.rules):
            # Check for duplicate names
            if rule.name in rule_names:
                errors.append(f"Duplicate rule name: '{rule.name}'")
            rule_names.add(rule.name)
            
            # Validate pattern if present
            if rule.pattern:
                try:
                    re.compile(rule.pattern)
                except re.error as e:
                    errors.append(f"Invalid regex in rule '{rule.name}': {e}")
            
            # Validate action
            if not rule.action:
                warnings.append(f"Rule '{rule.name}' has no action defined")
            else:
                # Check action format
                if ":" not in rule.action:
                    warnings.append(
                        f"Rule '{rule.name}' action should be in format 'type:params'"
                    )
            
            # Check dependencies
            if "depends_on" in rule.metadata:
                deps = rule.metadata["depends_on"]
                if isinstance(deps, list):
                    for dep in deps:
                        if dep not in rule_names and dep != rule.name:
                            warnings.append(
                                f"Rule '{rule.name}' depends on unknown rule '{dep}'"
                            )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata={
                "rule_count": len(instruction_set.rules),
                "format": instruction_set.metadata.get("format", "unknown")
            }
        )
    
    def merge_instruction_sets(
        self,
        *instruction_sets: InstructionSet
    ) -> InstructionSet:
        """Merge multiple instruction sets into one."""
        if not instruction_sets:
            raise ValueError("No instruction sets provided to merge")
        
        # Start with first set as base
        merged = InstructionSet(
            name="Merged Instructions",
            version="1.0.0",
            rules=[],
            metadata={"merged_from": []}
        )
        
        # Track rule names to handle conflicts
        rule_names = {}
        
        for inst_set in instruction_sets:
            merged.metadata["merged_from"].append(inst_set.name)
            
            for rule in inst_set.rules:
                # Handle name conflicts
                original_name = rule.name
                counter = 1
                while rule.name in rule_names:
                    rule.name = f"{original_name}_{counter}"
                    counter += 1
                
                rule_names[rule.name] = inst_set.name
                merged.rules.append(rule)
        
        logger.info(
            f"Merged {len(instruction_sets)} instruction sets "
            f"into {len(merged.rules)} rules"
        )
        
        return merged