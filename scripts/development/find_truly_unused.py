#!/usr/bin/env python3
"""Find truly unused methods by checking all usage including tests."""

import ast
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List

class MethodCollector(ast.NodeVisitor):
    """Collect all method definitions and calls."""
    
    def __init__(self):
        self.defined_methods: Dict[str, str] = {}  # method_name -> file
        self.called_methods: Set[str] = set()
        self.current_class = None
        
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        method_name = node.name
        
        # Skip special methods
        if method_name.startswith('__') and method_name.endswith('__'):
            self.generic_visit(node)
            return
            
        self.defined_methods[method_name] = self.current_class or "module"
        self.generic_visit(node)
        
    def visit_Call(self, node):
        # Handle method calls
        if isinstance(node.func, ast.Attribute):
            self.called_methods.add(node.func.attr)
        elif isinstance(node.func, ast.Name):
            self.called_methods.add(node.func.id)
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        """Also catch attribute access (for properties)."""
        self.called_methods.add(node.attr)
        self.generic_visit(node)

def analyze_directory(directory: str) -> MethodCollector:
    """Analyze all Python files in directory."""
    collector = MethodCollector()
    
    for filepath in Path(directory).rglob("*.py"):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(filepath))
            collector.visit(tree)
        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")
    
    return collector

def main():
    # Analyze saigen code
    print("Analyzing saigen code...")
    saigen_collector = analyze_directory("saigen")
    
    # Analyze tests
    print("Analyzing tests...")
    test_collector = analyze_directory("tests")
    
    # Combine all called methods
    all_called = saigen_collector.called_methods | test_collector.called_methods
    
    # Find unused methods
    unused = []
    for method_name, context in saigen_collector.defined_methods.items():
        # Skip if called
        if method_name in all_called:
            continue
            
        # Skip common patterns
        if method_name in ['main', 'run', 'execute', 'initialize', 'cleanup', 'setup', 'teardown']:
            continue
        if method_name.startswith('test_'):
            continue
        
        unused.append((method_name, context))
    
    # Print results
    print("\n" + "=" * 80)
    print("TRULY UNUSED METHODS (not called in code or tests)")
    print("=" * 80)
    
    if not unused:
        print("\nNo unused methods found!")
        return
    
    # Group by context
    by_context = defaultdict(list)
    for method, context in unused:
        by_context[context].append(method)
    
    for context in sorted(by_context.keys()):
        methods = sorted(by_context[context])
        print(f"\n{context}:")
        for method in methods:
            print(f"  - {method}")
    
    print(f"\n\nTotal unused methods: {len(unused)}")

if __name__ == "__main__":
    main()
