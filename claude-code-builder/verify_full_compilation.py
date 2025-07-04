#!/usr/bin/env python3
"""Comprehensive compilation verification for Claude Code Builder v3."""

import sys
import importlib
import ast
from pathlib import Path
import traceback

def verify_compilation():
    """Verify all modules compile and are syntactically correct."""
    root_dir = Path(__file__).parent
    package_dir = root_dir / 'claude_code_builder'
    
    errors = []
    success_count = 0
    syntax_errors = []
    import_errors = []
    
    print("=== Claude Code Builder v3 Compilation Verification ===\n")
    
    # Find all Python files
    py_files = list(package_dir.rglob('*.py'))
    py_files = [f for f in py_files if '__pycache__' not in str(f)]
    
    print(f"Found {len(py_files)} Python files to verify\n")
    
    # First, check syntax of all files
    print("Phase 1: Syntax Verification")
    print("-" * 40)
    
    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            print(f"✓ Syntax OK: {py_file.relative_to(root_dir)}")
        except SyntaxError as e:
            error_msg = f"Syntax Error in {py_file.relative_to(root_dir)}: Line {e.lineno}: {e.msg}"
            syntax_errors.append(error_msg)
            print(f"✗ {error_msg}")
    
    print(f"\nSyntax Check Complete: {len(py_files) - len(syntax_errors)}/{len(py_files)} files valid\n")
    
    # Second, try importing all modules
    print("Phase 2: Import Verification")
    print("-" * 40)
    
    for py_file in py_files:
        if py_file.name == '__init__.py' and py_file.parent == package_dir:
            continue  # Skip top-level __init__.py
            
        # Convert file path to module name
        relative_path = py_file.relative_to(root_dir)
        module_name = str(relative_path).replace('/', '.').replace('\\', '.')[:-3]
        
        if module_name.endswith('.__init__'):
            module_name = module_name[:-9]
            
        try:
            importlib.import_module(module_name)
            success_count += 1
            print(f"✓ Import OK: {module_name}")
        except Exception as e:
            error_msg = f"Import Error in {module_name}: {type(e).__name__}: {str(e)}"
            import_errors.append((module_name, e))
            print(f"✗ {error_msg}")
    
    # Summary
    print("\n" + "=" * 60)
    print("COMPILATION VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Total Python files: {len(py_files)}")
    print(f"Syntax errors: {len(syntax_errors)}")
    print(f"Import errors: {len(import_errors)}")
    print(f"Successfully imported modules: {success_count}")
    
    # Detailed error report
    if syntax_errors:
        print("\n" + "=" * 60)
        print("SYNTAX ERRORS:")
        print("=" * 60)
        for error in syntax_errors:
            print(f"  - {error}")
    
    if import_errors:
        print("\n" + "=" * 60)
        print("IMPORT ERRORS:")
        print("=" * 60)
        for module, error in import_errors:
            print(f"\n  Module: {module}")
            print(f"  Error: {type(error).__name__}: {str(error)}")
            if hasattr(error, '__traceback__'):
                print("  Traceback:")
                for line in traceback.format_tb(error.__traceback__)[-3:]:
                    print(f"    {line.strip()}")
    
    # Final verdict
    print("\n" + "=" * 60)
    if syntax_errors or import_errors:
        print("❌ COMPILATION FAILED - Errors found!")
        print("=" * 60)
        return False
    else:
        print("✅ COMPILATION SUCCESSFUL - All modules compile and import correctly!")
        print("=" * 60)
        return True

if __name__ == "__main__":
    success = verify_compilation()
    sys.exit(0 if success else 1)