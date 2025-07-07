"""JSON parsing and manipulation utilities for Claude Code Builder."""
import json
import re
from typing import Any, Dict, List, Optional, Union, Iterator, Tuple
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import jsonschema
from jsonschema import Draft7Validator

from ..exceptions.base import ValidationError, ClaudeCodeBuilderError
from ..logging.logger import get_logger

logger = get_logger(__name__)


class JSONEncoder(json.JSONEncoder):
    """Enhanced JSON encoder with support for custom types."""
    
    def default(self, obj):
        """Encode custom types to JSON-serializable format.
        
        Args:
            obj: Object to encode
            
        Returns:
            JSON-serializable representation
        """
        # Handle datetime/date objects
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        
        # Handle Decimal
        elif isinstance(obj, Decimal):
            return float(obj)
        
        # Handle Path objects
        elif isinstance(obj, Path):
            return str(obj)
        
        # Handle Enum
        elif isinstance(obj, Enum):
            return obj.value
        
        # Handle dataclasses
        elif hasattr(obj, '__dataclass_fields__'):
            return asdict(obj)
        
        # Handle sets
        elif isinstance(obj, set):
            return list(obj)
        
        # Handle objects with to_dict method
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        
        # Default to base encoder
        return super().default(obj)


class StreamingJSONParser:
    """Parser for streaming JSON data."""
    
    def __init__(self):
        """Initialize streaming parser."""
        self._buffer = ""
        self._stack: List[int] = []
        self._in_string = False
        self._escape_next = False
        
    def feed(self, chunk: str) -> Iterator[Dict[str, Any]]:
        """Feed a chunk of data to the parser.
        
        Args:
            chunk: Data chunk
            
        Yields:
            Complete JSON objects
        """
        self._buffer += chunk
        
        # Try to extract complete JSON objects
        while True:
            obj, remaining = self._extract_json_object()
            if obj is None:
                break
                
            self._buffer = remaining
            
            try:
                yield json.loads(obj)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON object: {e}")
    
    def _extract_json_object(self) -> Tuple[Optional[str], str]:
        """Extract a complete JSON object from buffer.
        
        Returns:
            Tuple of (json_string, remaining_buffer)
        """
        if not self._buffer.strip():
            return None, self._buffer
        
        # Find the start of a JSON object
        start_idx = self._buffer.find('{')
        if start_idx == -1:
            return None, self._buffer
        
        # Track braces to find complete object
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(self._buffer[start_idx:], start_idx):
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    
                    if brace_count == 0:
                        # Found complete object
                        json_str = self._buffer[start_idx:i+1]
                        remaining = self._buffer[i+1:]
                        return json_str, remaining
        
        # No complete object found
        return None, self._buffer


def parse_json(
    data: Union[str, bytes, Path],
    strict: bool = True,
    encoding: str = 'utf-8'
) -> Dict[str, Any]:
    """Parse JSON data from various sources.
    
    Args:
        data: JSON data (string, bytes, or file path)
        strict: Enable strict parsing
        encoding: Encoding for bytes/file
        
    Returns:
        Parsed JSON data
        
    Raises:
        ValidationError: If JSON is invalid
    """
    try:
        # Handle different input types
        if isinstance(data, Path):
            with open(data, 'r', encoding=encoding) as f:
                json_str = f.read()
        elif isinstance(data, bytes):
            json_str = data.decode(encoding)
        else:
            json_str = data
        
        # Parse JSON
        return json.loads(json_str, strict=strict)
        
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}")
    except Exception as e:
        raise ClaudeCodeBuilderError(f"Failed to parse JSON: {e}")


def dumps_json(
    data: Any,
    pretty: bool = False,
    indent: int = 2,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
    cls: Optional[type] = None
) -> str:
    """Serialize data to JSON string.
    
    Args:
        data: Data to serialize
        pretty: Enable pretty printing
        indent: Indentation level (if pretty)
        sort_keys: Sort dictionary keys
        ensure_ascii: Ensure ASCII output
        cls: Custom encoder class
        
    Returns:
        JSON string
    """
    encoder_cls = cls or JSONEncoder
    
    if pretty:
        return json.dumps(
            data,
            indent=indent,
            sort_keys=sort_keys,
            ensure_ascii=ensure_ascii,
            cls=encoder_cls
        )
    else:
        return json.dumps(
            data,
            separators=(',', ':'),
            sort_keys=sort_keys,
            ensure_ascii=ensure_ascii,
            cls=encoder_cls
        )


def validate_json_schema(
    data: Dict[str, Any],
    schema: Dict[str, Any],
    raise_on_error: bool = True
) -> Tuple[bool, List[str]]:
    """Validate JSON data against a schema.
    
    Args:
        data: Data to validate
        schema: JSON schema
        raise_on_error: Raise exception on validation error
        
    Returns:
        Tuple of (is_valid, error_messages)
        
    Raises:
        ValidationError: If validation fails and raise_on_error is True
    """
    try:
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(data))
        
        if errors:
            error_messages = [
                f"{'.'.join(str(p) for p in error.path)}: {error.message}"
                for error in errors
            ]
            
            if raise_on_error:
                raise ValidationError(
                    f"JSON schema validation failed",
                    details={"errors": error_messages}
                )
            
            return False, error_messages
        
        return True, []
        
    except jsonschema.SchemaError as e:
        raise ValidationError(f"Invalid JSON schema: {e}")


def merge_json(
    base: Dict[str, Any],
    update: Dict[str, Any],
    deep: bool = True
) -> Dict[str, Any]:
    """Merge two JSON objects.
    
    Args:
        base: Base object
        update: Object to merge
        deep: Enable deep merge
        
    Returns:
        Merged object
    """
    result = base.copy()
    
    if not deep:
        result.update(update)
        return result
    
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge dictionaries
            result[key] = merge_json(result[key], value, deep=True)
        else:
            result[key] = value
    
    return result


def diff_json(
    old: Dict[str, Any],
    new: Dict[str, Any],
    ignore_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Calculate difference between two JSON objects.
    
    Args:
        old: Original object
        new: New object
        ignore_keys: Keys to ignore in comparison
        
    Returns:
        Dictionary with added, removed, and modified keys
    """
    ignore_keys = ignore_keys or []
    
    diff = {
        "added": {},
        "removed": {},
        "modified": {}
    }
    
    # Find added and modified keys
    for key, value in new.items():
        if key in ignore_keys:
            continue
            
        if key not in old:
            diff["added"][key] = value
        elif old[key] != value:
            diff["modified"][key] = {
                "old": old[key],
                "new": value
            }
    
    # Find removed keys
    for key, value in old.items():
        if key in ignore_keys:
            continue
            
        if key not in new:
            diff["removed"][key] = value
    
    return diff


def flatten_json(
    data: Dict[str, Any],
    separator: str = ".",
    prefix: str = ""
) -> Dict[str, Any]:
    """Flatten nested JSON structure.
    
    Args:
        data: Nested JSON data
        separator: Key separator
        prefix: Key prefix
        
    Returns:
        Flattened dictionary
    """
    result = {}
    
    def _flatten(obj, parent_key=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                _flatten(value, new_key)
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                new_key = f"{parent_key}[{i}]"
                _flatten(value, new_key)
        else:
            result[parent_key] = obj
    
    _flatten(data, prefix)
    return result


def unflatten_json(
    data: Dict[str, Any],
    separator: str = "."
) -> Dict[str, Any]:
    """Unflatten a flattened JSON structure.
    
    Args:
        data: Flattened dictionary
        separator: Key separator
        
    Returns:
        Nested JSON structure
    """
    result = {}
    
    for key, value in data.items():
        parts = key.split(separator)
        current = result
        
        for i, part in enumerate(parts[:-1]):
            # Handle array indices
            if '[' in part and ']' in part:
                array_key = part[:part.index('[')]
                index = int(part[part.index('[')+1:part.index(']')])
                
                if array_key not in current:
                    current[array_key] = []
                
                # Extend array if needed
                while len(current[array_key]) <= index:
                    current[array_key].append({})
                
                current = current[array_key][index]
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]
        
        # Set the final value
        final_key = parts[-1]
        if '[' in final_key and ']' in final_key:
            array_key = final_key[:final_key.index('[')]
            index = int(final_key[final_key.index('[')+1:final_key.index(']')])
            
            if array_key not in current:
                current[array_key] = []
            
            while len(current[array_key]) <= index:
                current[array_key].append(None)
            
            current[array_key][index] = value
        else:
            current[final_key] = value
    
    return result


def extract_json_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract JSON objects from text containing mixed content.
    
    Args:
        text: Text containing JSON
        
    Returns:
        List of extracted JSON objects
    """
    json_objects = []
    
    # Find potential JSON objects using regex
    pattern = r'\{[^{}]*\}|\{[^{}]*\{[^{}]*\}[^{}]*\}'
    
    for match in re.finditer(pattern, text):
        json_str = match.group()
        
        # Try to parse as JSON
        try:
            obj = json.loads(json_str)
            json_objects.append(obj)
        except json.JSONDecodeError:
            # Try to find complete JSON by tracking braces
            start_idx = match.start()
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i, char in enumerate(text[start_idx:], start_idx):
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                    
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        
                        if brace_count == 0:
                            # Found complete object
                            json_str = text[start_idx:i+1]
                            try:
                                obj = json.loads(json_str)
                                json_objects.append(obj)
                            except json.JSONDecodeError:
                                pass
                            break
    
    return json_objects


def json_to_yaml(data: Dict[str, Any]) -> str:
    """Convert JSON data to YAML format.
    
    Args:
        data: JSON data
        
    Returns:
        YAML string
    """
    import yaml
    
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


def json_to_toml(data: Dict[str, Any]) -> str:
    """Convert JSON data to TOML format.
    
    Args:
        data: JSON data
        
    Returns:
        TOML string
    """
    import toml
    
    return toml.dumps(data)