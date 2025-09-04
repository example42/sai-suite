#!/usr/bin/env python3
"""Demo script showing saidata validation capabilities."""

import sys
import tempfile
from pathlib import Path
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from saigen.core.validator import SaidataValidator
from saigen.models.saidata import SaiData, Metadata


def demo_valid_saidata():
    """Demonstrate validation of valid saidata."""
    print("=== Valid Saidata Validation ===")
    
    valid_data = {
        "version": "0.2",
        "metadata": {
            "name": "nginx",
            "display_name": "NGINX",
            "description": "High-performance web server and reverse proxy",
            "category": "web-server",
            "license": "BSD-2-Clause"
        },
        "packages": [
            {
                "name": "nginx",
                "version": "1.24.0"
            }
        ],
        "services": [
            {
                "name": "nginx",
                "type": "systemd",
                "enabled": True
            }
        ],
        "ports": [
            {
                "port": 80,
                "protocol": "tcp",
                "service": "http"
            },
            {
                "port": 443,
                "protocol": "tcp", 
                "service": "https"
            }
        ],
        "providers": {
            "apt": {
                "packages": [
                    {
                        "name": "nginx",
                        "repository": "ubuntu-main"
                    }
                ],
                "repositories": [
                    {
                        "name": "ubuntu-main",
                        "type": "os-default"
                    }
                ]
            }
        }
    }
    
    validator = SaidataValidator()
    result = validator.validate_data(valid_data, "nginx.yaml")
    
    print(validator.format_validation_report(result))
    print()


def demo_invalid_saidata():
    """Demonstrate validation of invalid saidata with various errors."""
    print("=== Invalid Saidata Validation ===")
    
    invalid_data = {
        "version": "invalid-version",  # Invalid version format
        "metadata": {
            "name": "test-software"
            # Missing other recommended fields
        },
        "services": [
            {
                "name": "test-service",
                "type": "invalid-service-type"  # Invalid enum value
            }
        ],
        "ports": [
            {
                "port": 70000  # Invalid port range
            },
            {
                "port": 22  # Privileged port (warning)
            }
        ],
        "files": [
            {
                "name": "config",
                "path": "~/relative/config"  # Tilde path (warning)
            }
        ],
        "providers": {
            "apt": {
                "packages": [
                    {
                        "name": "  invalid package  ",  # Suspicious package name
                        "repository": "nonexistent-repo"  # Undefined repository
                    }
                ]
            }
        }
    }
    
    validator = SaidataValidator()
    result = validator.validate_data(invalid_data, "invalid.yaml")
    
    print(validator.format_validation_report(result))
    print()


def demo_file_validation():
    """Demonstrate validation of YAML files."""
    print("=== File Validation Demo ===")
    
    # Create a temporary YAML file with invalid content
    invalid_yaml_content = """
version: "0.2"
metadata:
  name: test-software
services:
  - name: test-service
    type: invalid-enum-value
ports:
  - port: 99999  # Invalid port
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(invalid_yaml_content)
        temp_path = Path(f.name)
    
    try:
        validator = SaidataValidator()
        result = validator.validate_file(temp_path)
        
        print(f"Validating file: {temp_path}")
        print(validator.format_validation_report(result))
        
    finally:
        temp_path.unlink()


def demo_pydantic_validation():
    """Demonstrate validation of Pydantic models."""
    print("=== Pydantic Model Validation ===")
    
    # Create a valid SaiData model
    saidata = SaiData(
        version="0.2",
        metadata=Metadata(
            name="redis",
            description="In-memory data structure store",
            category="database"
        )
    )
    
    validator = SaidataValidator()
    result = validator.validate_pydantic_model(saidata)
    
    print("Validating Pydantic SaiData model:")
    print(validator.format_validation_report(result))


def main():
    """Run all validation demos."""
    print("Saidata Validation System Demo")
    print("=" * 50)
    print()
    
    demo_valid_saidata()
    demo_invalid_saidata()
    demo_file_validation()
    demo_pydantic_validation()
    
    print("Demo completed!")


if __name__ == "__main__":
    main()