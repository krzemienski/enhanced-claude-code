#!/usr/bin/env python3
"""Test that all modules compile successfully."""

import sys
import importlib
import traceback
from pathlib import Path

def test_module_imports():
    """Test importing all modules."""
    root_dir = Path(__file__).parent
    package_dir = root_dir / 'claude_code_builder'
    
    errors = []
    success_count = 0
    
    # Find all Python files
    for py_file in package_dir.rglob('*.py'):
        # Skip __pycache__ and test files
        if '__pycache__' in str(py_file) or 'test_' in py_file.name:
            continue
            
        # Convert file path to module name
        relative_path = py_file.relative_to(root_dir)
        module_name = str(relative_path).replace('/', '.').replace('\\', '.')[:-3]
        
        if module_name.endswith('.__init__'):
            module_name = module_name[:-9]
            
        try:
            importlib.import_module(module_name)
            success_count += 1
            print(f"✓ {module_name}")
        except Exception as e:
            errors.append((module_name, str(e)))
            print(f"✗ {module_name}: {str(e)}")
            
    print(f"\n{'='*60}")
    print(f"Successfully imported: {success_count} modules")
    print(f"Failed imports: {len(errors)}")
    
    if errors:
        print("\nErrors:")
        for module, error in errors:
            print(f"  - {module}: {error}")
        return False
    return True

if __name__ == "__main__":
    success = test_module_imports()
    sys.exit(0 if success else 1)