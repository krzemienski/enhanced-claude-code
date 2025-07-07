#!/usr/bin/env python3
"""Comprehensive fix for all dataclass issues."""

import re
from pathlib import Path

def fix_file(file_path):
    """Fix dataclass issues in a single file."""
    content = file_path.read_text()
    
    # Pattern to find field declarations that need defaults
    field_pattern = r'(\s+)(\w+): ([^=\n]+)(?!=)'
    
    # Common default values by type
    defaults = {
        'str': '""',
        'int': '0',
        'float': '0.0',
        'bool': 'False',
        'List[str]': 'field(default_factory=list)',
        'List[int]': 'field(default_factory=list)',
        'List[float]': 'field(default_factory=list)',
        'List[Dict[str, Any]]': 'field(default_factory=list)',
        'Dict[str, Any]': 'field(default_factory=dict)',
        'Dict[str, str]': 'field(default_factory=dict)',
        'Set[str]': 'field(default_factory=set)',
    }
    
    # Add enum defaults
    enum_defaults = {
        'ResearchTaskType': 'ResearchTaskType.DOCUMENTATION',
        'ResearchStatus': 'ResearchStatus.PENDING',
        'TestType': 'TestType.UNIT',
        'TestStatus': 'TestStatus.PENDING',
        'TestStage': 'TestStage.SETUP',
        'AlertType': 'AlertType.INFO',
        'PerformanceCategory': 'PerformanceCategory.EXECUTION',
        'MetricType': 'MetricType.COUNTER',
    }
    
    # Find all dataclass blocks
    dataclass_pattern = r'@dataclass\nclass (\w+)[^:]*:\s*\n((?:    [^\n]*\n)*?)(?=\n(?:@|\w|class|\Z))'
    
    def fix_dataclass_block(match):
        class_name = match.group(1)
        class_body = match.group(2)
        
        # Split into lines and process each field
        lines = class_body.split('\n')
        new_lines = []
        in_dataclass_fields = False
        
        for line in lines:
            if '"""' in line:
                in_dataclass_fields = not in_dataclass_fields
                new_lines.append(line)
                continue
                
            if not in_dataclass_fields or not line.strip():
                new_lines.append(line)
                continue
                
            # Check if this is a field declaration
            field_match = re.match(r'(\s+)(\w+): ([^=\n]+)$', line)
            if field_match:
                indent = field_match.group(1)
                field_name = field_match.group(2)
                field_type = field_match.group(3).strip()
                
                # Try to find appropriate default
                default_value = None
                
                # Check for exact type match
                if field_type in defaults:
                    default_value = defaults[field_type]
                # Check for enum types
                elif field_type in enum_defaults:
                    default_value = enum_defaults[field_type]
                # Check for Optional types
                elif field_type.startswith('Optional['):
                    default_value = 'None'
                # Check for List types
                elif field_type.startswith('List[') and field_type not in defaults:
                    default_value = 'field(default_factory=list)'
                # Check for Dict types
                elif field_type.startswith('Dict[') and field_type not in defaults:
                    default_value = 'field(default_factory=dict)'
                # Check for Set types
                elif field_type.startswith('Set['):
                    default_value = 'field(default_factory=set)'
                # Basic types
                elif 'str' in field_type.lower():
                    default_value = '""'
                elif 'int' in field_type.lower():
                    default_value = '0'
                elif 'float' in field_type.lower():
                    default_value = '0.0'
                elif 'bool' in field_type.lower():
                    default_value = 'False'
                
                if default_value:
                    new_line = f"{indent}{field_name}: {field_type} = {default_value}"
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        return f"@dataclass\nclass {class_name}{match.group(0).split(':')[0].split(class_name)[1]}:\n" + '\n'.join(new_lines)
    
    # Apply fixes
    new_content = re.sub(dataclass_pattern, fix_dataclass_block, content, flags=re.MULTILINE | re.DOTALL)
    
    if new_content != content:
        file_path.write_text(new_content)
        return True
    return False

def main():
    """Fix all model files."""
    models_dir = Path("claude_code_builder/models")
    
    for py_file in models_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
            
        print(f"Processing {py_file}")
        if fix_file(py_file):
            print(f"  Fixed {py_file}")
        else:
            print(f"  No changes needed for {py_file}")

if __name__ == "__main__":
    main()