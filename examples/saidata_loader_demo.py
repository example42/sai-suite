#!/usr/bin/env python3
"""
Demo script showing SaidataLoader functionality.

This script demonstrates how to use the SaidataLoader to:
1. Load saidata files from multiple search paths
2. Merge saidata files with precedence rules
3. Validate saidata against the schema
4. Handle errors and warnings
"""

import tempfile
import yaml
from pathlib import Path
from sai.core.saidata_loader import SaidataLoader, SaidataNotFoundError, ValidationError
from sai.models.config import SaiConfig


def create_demo_saidata():
    """Create demo saidata files for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create system-level saidata (lower precedence)
    system_dir = temp_dir / "system"
    system_dir.mkdir()
    
    system_nginx = {
        "version": "0.2.0",
        "metadata": {
            "name": "nginx",
            "description": "System default nginx configuration",
            "category": "web-server",
            "license": "BSD-2-Clause"
        },
        "packages": [
            {
                "name": "nginx",
                "version": "1.20.0"
            }
        ],
        "services": [
            {
                "name": "nginx",
                "service_name": "nginx",
                "type": "systemd",
                "enabled": True
            }
        ],
        "providers": {
            "apt": {
                "packages": [
                    {
                        "name": "nginx",
                        "version": "1.20.0"
                    }
                ]
            }
        }
    }
    
    # Create user-level saidata (higher precedence)
    user_dir = temp_dir / "user"
    user_dir.mkdir()
    
    user_nginx = {
        "version": "0.2.0",
        "metadata": {
            "name": "nginx",
            "description": "User customized nginx with SSL support",
            "tags": ["web", "proxy", "ssl"]
        },
        "packages": [
            {
                "name": "nginx-extras",
                "version": "1.22.0"
            }
        ],
        "providers": {
            "apt": {
                "packages": [
                    {
                        "name": "nginx-full",
                        "version": "1.22.0"
                    }
                ]
            },
            "brew": {
                "packages": [
                    {
                        "name": "nginx",
                        "version": "1.22.0"
                    }
                ]
            }
        }
    }
    
    # Write saidata files
    with open(system_dir / "nginx.yaml", 'w') as f:
        yaml.dump(system_nginx, f)
    
    with open(user_dir / "nginx.yaml", 'w') as f:
        yaml.dump(user_nginx, f)
    
    return temp_dir, user_dir, system_dir


def demo_basic_loading():
    """Demonstrate basic saidata loading."""
    print("=== Basic Saidata Loading Demo ===")
    
    temp_dir, user_dir, system_dir = create_demo_saidata()
    
    try:
        # Create config with search paths (user has higher precedence)
        config = SaiConfig(saidata_paths=[str(user_dir), str(system_dir)])
        loader = SaidataLoader(config)
        
        print(f"Search paths: {[str(p) for p in loader.get_search_paths()]}")
        
        # Load nginx saidata
        saidata = loader.load_saidata("nginx")
        
        print(f"\nLoaded saidata for: {saidata.metadata.name}")
        print(f"Description: {saidata.metadata.description}")
        print(f"Category: {saidata.metadata.category}")
        print(f"License: {saidata.metadata.license}")
        print(f"Tags: {saidata.metadata.tags}")
        
        print(f"\nPackages ({len(saidata.packages or [])}):")
        for pkg in saidata.packages or []:
            print(f"  - {pkg.name} ({pkg.version})")
        
        print(f"\nServices ({len(saidata.services or [])}):")
        for svc in saidata.services or []:
            print(f"  - {svc.name} ({svc.type})")
        
        print(f"\nProviders ({len(saidata.providers or {})}):")
        for provider_name, provider_config in (saidata.providers or {}).items():
            pkg_count = len(provider_config.packages or [])
            print(f"  - {provider_name}: {pkg_count} packages")
            for pkg in provider_config.packages or []:
                print(f"    * {pkg.name} ({pkg.version})")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)


def demo_validation():
    """Demonstrate saidata validation."""
    print("\n=== Saidata Validation Demo ===")
    
    loader = SaidataLoader()
    
    # Test valid saidata
    valid_data = {
        "version": "0.2.0",
        "metadata": {
            "name": "valid-software",
            "description": "This is valid saidata"
        },
        "packages": [{"name": "valid-package"}],
        "providers": {
            "apt": {"packages": [{"name": "valid-package"}]}
        }
    }
    
    result = loader.validate_saidata(valid_data)
    print(f"Valid saidata: {result.valid}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
    
    # Test invalid saidata
    invalid_data = {
        "version": "0.2.0"
        # Missing required metadata
    }
    
    result = loader.validate_saidata(invalid_data)
    print(f"\nInvalid saidata: {result.valid}")
    print(f"Errors: {result.errors}")
    
    # Test saidata with warnings
    warning_data = {
        "version": "0.2.0",
        "metadata": {
            "name": "minimal-software"
            # Missing description - will generate warning
        }
        # No packages - will generate warning
    }
    
    result = loader.validate_saidata(warning_data)
    print(f"\nSaidata with warnings: {result.valid}")
    print(f"Warnings: {result.warnings}")


def demo_error_handling():
    """Demonstrate error handling."""
    print("\n=== Error Handling Demo ===")
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        config = SaiConfig(saidata_paths=[str(temp_dir)])
        loader = SaidataLoader(config)
        
        # Test file not found
        try:
            loader.load_saidata("nonexistent")
        except SaidataNotFoundError as e:
            print(f"Caught SaidataNotFoundError: {e}")
        
        # Test validation error
        invalid_data = {
            "version": "0.2.0"
            # Missing metadata
        }
        
        invalid_file = temp_dir / "invalid.yaml"
        with open(invalid_file, 'w') as f:
            yaml.dump(invalid_data, f)
        
        try:
            loader.load_saidata("invalid")
        except ValidationError as e:
            print(f"Caught ValidationError: {e}")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    demo_basic_loading()
    demo_validation()
    demo_error_handling()
    print("\n=== Demo Complete ===")