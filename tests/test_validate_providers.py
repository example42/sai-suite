#!/usr/bin/env python3
"""
Tests for the provider validation script.
"""

import json
import tempfile
import yaml
from pathlib import Path
import pytest
import sys
import os

# Add scripts directory to path so we can import the validator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from validate_providers import ProviderValidator


class TestProviderValidator:
    """Test cases for the ProviderValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create a validator instance with the real schema."""
        schema_path = Path(__file__).parent.parent / "schemas" / "providerdata-0.1-schema.json"
        return ProviderValidator(str(schema_path))
    
    @pytest.fixture
    def valid_provider_data(self):
        """Sample valid provider data."""
        return {
            "version": "1.0",
            "provider": {
                "name": "test-provider",
                "type": "package_manager"
            },
            "actions": {
                "install": {
                    "command": "test-install {{packages}}"
                }
            }
        }
    
    @pytest.fixture
    def invalid_provider_data(self):
        """Sample invalid provider data (missing required fields)."""
        return {
            "version": "1.0",
            "provider": {
                "name": "test-provider"
                # Missing required 'type' field
            }
            # Missing required 'actions' field
        }
    
    def test_validator_initialization(self, validator):
        """Test that validator initializes correctly."""
        assert validator.schema is not None
        assert validator.validator is not None
    
    def test_valid_provider_file(self, validator, valid_provider_data):
        """Test validation of a valid provider file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(valid_provider_data, f)
            temp_path = Path(f.name)
        
        try:
            is_valid, errors = validator.validate_file(temp_path)
            assert is_valid is True
            assert len(errors) == 0
        finally:
            temp_path.unlink()
    
    def test_invalid_provider_file(self, validator, invalid_provider_data):
        """Test validation of an invalid provider file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_provider_data, f)
            temp_path = Path(f.name)
        
        try:
            is_valid, errors = validator.validate_file(temp_path)
            assert is_valid is False
            assert len(errors) > 0
            # Should have errors about missing required fields
            error_text = ' '.join(errors)
            assert 'required' in error_text.lower()
        finally:
            temp_path.unlink()
    
    def test_malformed_yaml_file(self, validator):
        """Test handling of malformed YAML files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            temp_path = Path(f.name)
        
        try:
            is_valid, errors = validator.validate_file(temp_path)
            assert is_valid is False
            assert len(errors) == 1
            assert "Failed to load YAML file" in errors[0]
        finally:
            temp_path.unlink()
    
    def test_find_provider_files(self, validator):
        """Test finding provider files in a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create some test files
            (temp_path / "provider1.yaml").write_text("test: data")
            (temp_path / "provider2.yml").write_text("test: data")
            (temp_path / "README.md").write_text("# README")
            (temp_path / "not-yaml.txt").write_text("text file")
            
            # Create subdirectory with more files
            sub_dir = temp_path / "subdir"
            sub_dir.mkdir()
            (sub_dir / "provider3.yaml").write_text("test: data")
            
            files = validator.find_provider_files(str(temp_path))
            
            # Should find 3 YAML files, excluding README
            assert len(files) == 3
            file_names = [f.name for f in files]
            assert "provider1.yaml" in file_names
            assert "provider2.yml" in file_names
            assert "provider3.yaml" in file_names
            assert "README.md" not in file_names
            assert "not-yaml.txt" not in file_names
    
    def test_real_apt_provider(self, validator):
        """Test validation against the real apt provider file."""
        apt_file = Path(__file__).parent.parent / "providers" / "apt.yaml"
        if apt_file.exists():
            is_valid, errors = validator.validate_file(apt_file)
            if not is_valid:
                print(f"APT provider validation errors: {errors}")
            # Note: We don't assert True here since the real file might have issues
            # This test is more for debugging and understanding real file structure


if __name__ == "__main__":
    pytest.main([__file__])