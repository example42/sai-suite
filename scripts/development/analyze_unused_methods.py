#!/usr/bin/env python3
"""Analyze saigen codebase for unused methods."""

import ast
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List, Tuple

class MethodAnalyzer(ast.NodeVisitor):
    """Analyze Python files for method definitions and calls."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.defined_methods: Set[str] = set()
        self.called_methods: Set[str] = set()
        self.class_methods: Dict[str, Set[str]] = defaultdict(set)
        self.current_class = None
        
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        """Visit function/method definitions."""
        method_name = node.name
        
        # Skip special methods
        if method_name.startswith('__') and method_name.endswith('__'):
            self.generic_visit(node)
            return
            
        if self.current_class:
            full_name = f"{self.current_class}.{method_name}"
            self.class_methods[self.current_class].add(method_name)
        else:
            full_name = method_name
            
        self.defined_methods.add(full_name)
        self.generic_visit(node)
        
    def visit_Call(self, node):
        """Visit function/method calls."""
        # Handle method calls (obj.method())
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            self.called_methods.add(method_name)
            
        # Handle direct function calls
        elif isinstance(node.func, ast.Name):
            func_name = node.func.id
            self.called_methods.add(func_name)
            
        self.generic_visit(node)

def analyze_file(filepath: Path) -> MethodAnalyzer:
    """Analyze a single Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content, filename=str(filepath))
        analyzer = MethodAnalyzer(str(filepath))
        analyzer.visit(tree)
        return analyzer
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return None

def find_python_files(directory: str) -> List[Path]:
    """Find all Python files in directory."""
    return list(Path(directory).rglob("*.py"))

def main():
    """Main analysis function."""
    saigen_dir = "saigen"
    
    # Collect all defined and called methods
    all_defined: Dict[str, List[str]] = defaultdict(list)
    all_called: Set[str] = set()
    
    python_files = find_python_files(saigen_dir)
    print(f"Analyzing {len(python_files)} Python files...\n")
    
    # First pass: collect all definitions and calls
    for filepath in python_files:
        analyzer = analyze_file(filepath)
        if analyzer:
            for method in analyzer.defined_methods:
                all_defined[method].append(str(filepath))
            all_called.update(analyzer.called_methods)
    
    # Find potentially unused methods
    unused_methods: Dict[str, List[str]] = defaultdict(list)
    
    for method_full_name, files in all_defined.items():
        # Extract just the method name (without class prefix)
        if '.' in method_full_name:
            _, method_name = method_full_name.rsplit('.', 1)
        else:
            method_name = method_full_name
        
        # Skip if method is called anywhere
        if method_name in all_called:
            continue
            
        # Skip common patterns that might be used externally
        if method_name in ['main', 'run', 'execute', 'initialize', 'cleanup']:
            continue
            
        # Skip test methods
        if method_name.startswith('test_'):
            continue
            
        # Skip property methods
        if method_name.startswith('get_') or method_name.startswith('set_'):
            continue
            
        # This method appears unused
        for filepath in files:
            unused_methods[filepath].append(method_full_name)
    
    # Print results
    print("=" * 80)
    print("POTENTIALLY UNUSED METHODS")
    print("=" * 80)
    print()
    
    if not unused_methods:
        print("No unused methods found!")
        return
    
    # Sort by file
    for filepath in sorted(unused_methods.keys()):
        methods = unused_methods[filepath]
        if methods:
            print(f"\n{filepath}")
            print("-" * len(filepath))
            for method in sorted(methods):
                print(f"  - {method}")
    
    print(f"\n\nTotal potentially unused methods: {sum(len(m) for m in unused_methods.values())}")
    print("\nNote: This is a heuristic analysis. Some methods may be:")
    print("  - Used via getattr() or other dynamic calls")
    print("  - Part of public API")
    print("  - Used in tests")
    print("  - Required for inheritance/interfaces")

if __name__ == "__main__":
    main()
