#!/usr/bin/env python3
"""
Demonstration of hierarchical saidata path resolution system.

This script shows how the new hierarchical path resolution works,
replacing the legacy flat file structure with an organized hierarchy.
"""

import tempfile
import yaml
from pathlib import Path

from sai.core.saidata_path import SaidataPath, HierarchicalPathResolver
from sai.core.saidata_loader import SaidataLoader
from sai.models.config import SaiConfig


def create_sample_hierarchical_structure(base_path: Path):
    """Create a sample hierarchical saidata structure."""
    print(f"Creating hierarchical saidata structure in: {base_path}")
    
    # Sample software definitions
    software_data = {
        "apache": {
            "version": "0.2",
            "metadata": {
                "name": "apache",
                "display_name": "Apache HTTP Server",
                "description": "The Apache HTTP Server Project",
                "category": "web-server",
                "license": "Apache-2.0"
            },
            "packages": [
                {"name": "apache2"},
                {"name": "httpd"}
            ]
        },
        "nginx": {
            "version": "0.2",
            "metadata": {
                "name": "nginx",
                "display_name": "Nginx",
                "description": "High-performance HTTP server and reverse proxy",
                "category": "web-server",
                "license": "BSD-2-Clause"
            },
            "packages": [
                {"name": "nginx"}
            ]
        },
        "mysql": {
            "version": "0.2",
            "metadata": {
                "name": "mysql",
                "display_name": "MySQL",
                "description": "MySQL Database Server",
                "category": "database",
                "license": "GPL-2.0"
            },
            "packages": [
                {"name": "mysql-server"},
                {"name": "mysql-client"}
            ]
        },
        "redis": {
            "version": "0.2",
            "metadata": {
                "name": "redis",
                "display_name": "Redis",
                "description": "In-memory data structure store",
                "category": "database",
                "license": "BSD-3-Clause"
            },
            "packages": [
                {"name": "redis-server"}
            ]
        },
        "docker": {
            "version": "0.2",
            "metadata": {
                "name": "docker",
                "display_name": "Docker",
                "description": "Container platform",
                "category": "containerization",
                "license": "Apache-2.0"
            },
            "packages": [
                {"name": "docker.io"},
                {"name": "docker-ce"}
            ]
        }
    }
    
    created_paths = []
    
    for software_name, data in software_data.items():
        # Generate hierarchical path
        saidata_path = SaidataPath.from_software_name(software_name, base_path)
        
        # Create directory structure
        saidata_path.get_directory().mkdir(parents=True, exist_ok=True)
        
        # Write saidata file
        with open(saidata_path.hierarchical_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
        
        created_paths.append(saidata_path)
        print(f"  Created: {saidata_path.hierarchical_path.relative_to(base_path)}")
    
    return created_paths


def demonstrate_path_generation():
    """Demonstrate hierarchical path generation."""
    print("\n" + "="*60)
    print("HIERARCHICAL PATH GENERATION DEMONSTRATION")
    print("="*60)
    
    base_path = Path("/example/saidata")
    
    test_software = [
        "apache", "nginx", "mysql", "redis", "docker",
        "kubernetes", "postgresql", "mongodb", "elasticsearch",
        "grafana", "prometheus", "jenkins", "terraform"
    ]
    
    print(f"\nBase path: {base_path}")
    print("\nHierarchical path generation:")
    print("Software Name        -> Hierarchical Path")
    print("-" * 60)
    
    for software in test_software:
        saidata_path = SaidataPath.from_software_name(software, base_path)
        relative_path = saidata_path.hierarchical_path.relative_to(base_path)
        print(f"{software:<20} -> {relative_path}")


def demonstrate_path_resolver():
    """Demonstrate hierarchical path resolver functionality."""
    print("\n" + "="*60)
    print("HIERARCHICAL PATH RESOLVER DEMONSTRATION")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        
        # Create sample structure
        created_paths = create_sample_hierarchical_structure(base_path)
        
        # Initialize resolver
        resolver = HierarchicalPathResolver([base_path])
        
        print(f"\nTesting path resolver with base path: {base_path}")
        
        # Test finding existing software
        test_software = ["apache", "nginx", "mysql", "redis", "docker"]
        
        print("\nFinding existing saidata files:")
        for software in test_software:
            found_files = resolver.find_saidata_files(software)
            if found_files:
                relative_path = found_files[0].relative_to(base_path)
                print(f"  {software:<10} -> Found: {relative_path}")
            else:
                print(f"  {software:<10} -> Not found")
        
        # Test finding non-existent software
        print("\nTesting non-existent software:")
        non_existent = ["nonexistent", "missing", "invalid"]
        for software in non_existent:
            found_files = resolver.find_saidata_files(software)
            print(f"  {software:<12} -> Found: {len(found_files)} files")
        
        # Test expected path generation
        print("\nExpected paths for new software:")
        new_software = ["kubernetes", "prometheus", "grafana"]
        for software in new_software:
            expected_path = resolver.get_expected_path(software)
            relative_path = expected_path.hierarchical_path.relative_to(base_path)
            print(f"  {software:<12} -> {relative_path}")


def demonstrate_saidata_loader():
    """Demonstrate SaidataLoader with hierarchical paths."""
    print("\n" + "="*60)
    print("SAIDATA LOADER WITH HIERARCHICAL PATHS DEMONSTRATION")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        
        # Create sample structure
        created_paths = create_sample_hierarchical_structure(base_path)
        
        # Configure loader
        config = SaiConfig(saidata_paths=[str(base_path)])
        loader = SaidataLoader(config)
        
        print(f"\nLoading saidata from hierarchical structure: {base_path}")
        
        # Load and display saidata
        test_software = ["apache", "nginx", "mysql"]
        
        for software in test_software:
            try:
                saidata = loader.load_saidata(software)
                print(f"\n{software.upper()}:")
                print(f"  Display Name: {saidata.metadata.display_name}")
                print(f"  Description:  {saidata.metadata.description}")
                print(f"  Category:     {saidata.metadata.category}")
                print(f"  License:      {saidata.metadata.license}")
                print(f"  Packages:     {', '.join(pkg.name for pkg in saidata.packages)}")
            except Exception as e:
                print(f"\n{software.upper()}: Error loading - {e}")
        
        # Test validation
        print(f"\nValidating hierarchical structure:")
        errors = loader.validate_hierarchical_structure(base_path)
        if errors:
            print("  Validation errors found:")
            for error in errors:
                print(f"    - {error}")
        else:
            print("  ✓ Structure is valid")
        
        # Find all software
        all_software = loader.find_all_hierarchical_software(base_path)
        print(f"\nAll software found in structure: {', '.join(all_software)}")


def demonstrate_error_handling():
    """Demonstrate error handling and validation."""
    print("\n" + "="*60)
    print("ERROR HANDLING AND VALIDATION DEMONSTRATION")
    print("="*60)
    
    # Test invalid software names
    print("\nTesting invalid software names:")
    invalid_names = ["", "  ", "invalid@name", "software/with/slashes", "a" * 101]
    
    resolver = HierarchicalPathResolver([Path("/tmp")])
    
    for name in invalid_names:
        errors = resolver.validate_software_name(name)
        if errors:
            print(f"  '{name}' -> Invalid: {errors[0]}")
        else:
            print(f"  '{name}' -> Valid")
    
    # Test path validation
    print("\nTesting path validation:")
    base_path = Path("/test/base")
    
    test_cases = [
        ("apache", "software/ap/apache/default.yaml", True),
        ("nginx", "software/ng/nginx/default.yaml", True),
        ("apache", "software/ng/apache/default.yaml", False),  # Wrong prefix
        ("apache", "software/ap/nginx/default.yaml", False),   # Wrong software dir
        ("apache", "software/ap/apache/saidata.yaml", False),  # Wrong filename
    ]
    
    for software, path_str, should_be_valid in test_cases:
        path = base_path / path_str
        saidata_path = SaidataPath(software, path)
        errors = saidata_path.validate_path()
        
        is_valid = len(errors) == 0
        status = "✓ Valid" if is_valid else f"✗ Invalid: {errors[0] if errors else 'Unknown error'}"
        expected = "✓" if should_be_valid else "✗"
        
        print(f"  {software} -> {path_str}")
        print(f"    Expected: {expected}, Got: {status}")


def main():
    """Run all demonstrations."""
    print("HIERARCHICAL SAIDATA PATH RESOLUTION SYSTEM DEMONSTRATION")
    print("=" * 80)
    
    demonstrate_path_generation()
    demonstrate_path_resolver()
    demonstrate_saidata_loader()
    demonstrate_error_handling()
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nKey Benefits of Hierarchical Structure:")
    print("• Organized: software/{prefix}/{name}/default.yaml")
    print("• Scalable: Handles thousands of software packages efficiently")
    print("• Consistent: Predictable path generation")
    print("• Flexible: Supports multiple file formats (YAML, JSON)")
    print("• Robust: Comprehensive validation and error handling")
    print("• Backward Compatible: Graceful handling of missing files")


if __name__ == "__main__":
    main()