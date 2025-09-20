#!/usr/bin/env python3
"""
Provider Data Validation Script

Validates all provider YAML files in the providers directory against the
providerdata-0.1-schema.json schema.
"""

import json
import sys
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple
import jsonschema
from jsonschema import validate, ValidationError, Draft7Validator
import argparse


class ProviderValidator:
    """Validates provider files against the providerdata schema."""
    
    def __init__(self, schema_path: str = "schemas/providerdata-0.1-schema.json"):
        """Initialize validator with schema file."""
        self.schema_path = Path(schema_path)
        self.schema = self._load_schema()
        self.validator = Draft7Validator(self.schema)
        
    def _load_schema(self) -> Dict[str, Any]:
        """Load and parse the JSON schema."""
        try:
            with open(self.schema_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Schema file not found: {self.schema_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in schema file: {e}")
            sys.exit(1)
    
    def _load_yaml_file(self, file_path: Path) -> Tuple[Dict[str, Any], bool]:
        """Load and parse a YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data is None:
                    return {}, False
                return data, True
        except yaml.YAMLError as e:
            print(f"❌ YAML parsing error in {file_path}: {e}")
            return {}, False
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return {}, False
    
    def validate_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Validate a single provider file."""
        data, loaded = self._load_yaml_file(file_path)
        if not loaded:
            return False, ["Failed to load YAML file"]
        
        errors = []
        try:
            validate(instance=data, schema=self.schema)
            return True, []
        except ValidationError as e:
            # Collect all validation errors
            for error in self.validator.iter_errors(data):
                error_path = " -> ".join(str(p) for p in error.absolute_path)
                if error_path:
                    errors.append(f"Path '{error_path}': {error.message}")
                else:
                    errors.append(f"Root: {error.message}")
            return False, errors
    
    def find_provider_files(self, providers_dir: str = "providers") -> List[Path]:
        """Find all YAML provider files."""
        providers_path = Path(providers_dir)
        if not providers_path.exists():
            print(f"❌ Providers directory not found: {providers_path}")
            sys.exit(1)
        
        yaml_files = []
        # Find all .yaml and .yml files recursively
        for pattern in ["**/*.yaml", "**/*.yml"]:
            yaml_files.extend(providers_path.glob(pattern))
        
        # Filter out README and other non-provider files
        provider_files = [f for f in yaml_files if not f.name.upper().startswith('README')]
        
        return sorted(provider_files)
    
    def validate_all(self, providers_dir: str = "providers", verbose: bool = False) -> bool:
        """Validate all provider files."""
        provider_files = self.find_provider_files(providers_dir)
        
        if not provider_files:
            print(f"❌ No provider files found in {providers_dir}")
            return False
        
        print(f"🔍 Found {len(provider_files)} provider files to validate")
        print(f"📋 Using schema: {self.schema_path}")
        print()
        
        valid_count = 0
        invalid_count = 0
        
        for file_path in provider_files:
            relative_path = file_path.relative_to(Path(providers_dir).parent)
            is_valid, errors = self.validate_file(file_path)
            
            if is_valid:
                valid_count += 1
                if verbose:
                    print(f"✅ {relative_path}")
            else:
                invalid_count += 1
                print(f"❌ {relative_path}")
                for error in errors:
                    print(f"   • {error}")
                print()
        
        print(f"📊 Validation Summary:")
        print(f"   ✅ Valid files: {valid_count}")
        print(f"   ❌ Invalid files: {invalid_count}")
        print(f"   📁 Total files: {len(provider_files)}")
        
        if invalid_count == 0:
            print(f"\n🎉 All provider files are valid!")
            return True
        else:
            print(f"\n💥 {invalid_count} files have validation errors")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate provider YAML files against the providerdata schema"
    )
    parser.add_argument(
        "--providers-dir", 
        default="providers",
        help="Directory containing provider files (default: providers)"
    )
    parser.add_argument(
        "--schema", 
        default="schemas/providerdata-0.1-schema.json",
        help="Path to schema file (default: schemas/providerdata-0.1-schema.json)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show all files being validated, not just errors"
    )
    parser.add_argument(
        "--file",
        help="Validate a specific file instead of all files"
    )
    
    args = parser.parse_args()
    
    validator = ProviderValidator(args.schema)
    
    if args.file:
        # Validate single file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
        
        print(f"🔍 Validating single file: {file_path}")
        print(f"📋 Using schema: {args.schema}")
        print()
        
        is_valid, errors = validator.validate_file(file_path)
        if is_valid:
            print(f"✅ {file_path} is valid")
            sys.exit(0)
        else:
            print(f"❌ {file_path} has validation errors:")
            for error in errors:
                print(f"   • {error}")
            sys.exit(1)
    else:
        # Validate all files
        success = validator.validate_all(args.providers_dir, args.verbose)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()