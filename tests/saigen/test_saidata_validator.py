"""Tests for saidata validation system."""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest
import yaml

from saigen.core.validator import SaidataValidator, ValidationSeverity, ValidationResult
from saigen.models.saidata import SaiData, Metadata


class TestSaidataValidator:
    """Test cases for SaidataValidator."""
    
    @pytest.fixture
    def validator(self) -> SaidataValidator:
        """Create validator instance."""
        return SaidataValidator()
    
    @pytest.fixture
    def valid_saidata(self) -> Dict[str, Any]:
        """Valid saidata for testing."""
        return {
            "version": "0.2",
            "metadata": {
                "name": "test-software",
                "description": "Test software for validation",
                "category": "testing"
            },
            "packages": [
                {
                    "name": "test-package",
                    "version": "1.0.0"
                }
            ],
            "providers": {
                "apt": {
                    "packages": [
                        {
                            "name": "test-package-apt",
                            "version": "1.0.0"
                        }
                    ]
                }
            }
        }
    
    def test_validate_valid_data(self, validator: SaidataValidator, valid_saidata: Dict[str, Any]):
        """Test validation of valid saidata."""
        result = validator.validate_data(valid_saidata)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert not result.has_errors
    
    def test_validate_missing_required_fields(self, validator: SaidataValidator):
        """Test validation with missing required fields."""
        invalid_data = {
            "version": "0.2"
            # Missing required metadata
        }
        
        result = validator.validate_data(invalid_data)
        
        assert not result.is_valid
        assert result.has_errors
        assert len(result.errors) > 0
        
        # Check for specific error about missing metadata
        error_messages = [error.message for error in result.errors]
        assert any("metadata" in msg.lower() for msg in error_messages)
    
    def test_validate_invalid_version_format(self, validator: SaidataValidator):
        """Test validation with invalid version format."""
        invalid_data = {
            "version": "invalid-version",
            "metadata": {
                "name": "test"
            }
        }
        
        result = validator.validate_data(invalid_data)
        
        assert not result.is_valid
        assert result.has_errors
        
        # Should have both schema error and custom validation error
        version_errors = [error for error in result.errors if "version" in error.path]
        assert len(version_errors) > 0
    
    def test_validate_invalid_enum_value(self, validator: SaidataValidator, valid_saidata: Dict[str, Any]):
        """Test validation with invalid enum values."""
        valid_saidata["services"] = [
            {
                "name": "test-service",
                "type": "invalid-service-type"  # Invalid enum value
            }
        ]
        
        result = validator.validate_data(valid_saidata)
        
        assert not result.is_valid
        assert result.has_errors
        
        # Check for enum validation error
        enum_errors = [error for error in result.errors if "enum" in error.code or "one of" in error.message.lower()]
        assert len(enum_errors) > 0
    
    def test_validate_invalid_port_range(self, validator: SaidataValidator, valid_saidata: Dict[str, Any]):
        """Test validation with invalid port numbers."""
        valid_saidata["ports"] = [
            {
                "port": 70000  # Invalid port number
            }
        ]
        
        result = validator.validate_data(valid_saidata)
        
        # Should pass schema validation but have warnings
        assert result.is_valid  # Schema allows this
        assert result.has_warnings
        
        port_warnings = [warning for warning in result.warnings if "port" in warning.message.lower()]
        assert len(port_warnings) > 0
    
    def test_validate_privileged_port_warning(self, validator: SaidataValidator, valid_saidata: Dict[str, Any]):
        """Test warning for privileged ports."""
        valid_saidata["ports"] = [
            {
                "port": 80  # Privileged port
            }
        ]
        
        result = validator.validate_data(valid_saidata)
        
        assert result.is_valid
        assert result.has_warnings
        
        privileged_warnings = [warning for warning in result.warnings if "privileged" in warning.message.lower()]
        assert len(privileged_warnings) > 0
    
    def test_validate_suspicious_package_name(self, validator: SaidataValidator, valid_saidata: Dict[str, Any]):
        """Test warning for suspicious package names."""
        valid_saidata["providers"]["apt"]["packages"] = [
            {
                "name": "  invalid-package  ",  # Leading/trailing spaces
            }
        ]
        
        result = validator.validate_data(valid_saidata)
        
        assert result.is_valid  # Schema allows this
        assert result.has_warnings
        
        package_warnings = [warning for warning in result.warnings if "package name" in warning.message.lower()]
        assert len(package_warnings) > 0
    
    def test_validate_cross_references(self, validator: SaidataValidator, valid_saidata: Dict[str, Any]):
        """Test cross-reference validation."""
        valid_saidata["providers"]["apt"]["packages"] = [
            {
                "name": "test-package",
                "repository": "nonexistent-repo"  # References undefined repository
            }
        ]
        
        result = validator.validate_data(valid_saidata)
        
        assert result.is_valid  # Schema allows this
        assert result.has_warnings
        
        cross_ref_warnings = [warning for warning in result.warnings if "undefined repository" in warning.message.lower()]
        assert len(cross_ref_warnings) > 0
    
    def test_validate_file_paths(self, validator: SaidataValidator, valid_saidata: Dict[str, Any]):
        """Test file path validation warnings."""
        valid_saidata["files"] = [
            {
                "name": "config",
                "path": "~/relative/path"  # Tilde expansion
            },
            {
                "name": "data",
                "path": "relative/path"  # Relative path
            }
        ]
        
        result = validator.validate_data(valid_saidata)
        
        assert result.is_valid
        assert result.has_warnings
        
        path_warnings = [warning for warning in result.warnings if "path" in warning.message.lower()]
        assert len(path_warnings) >= 2  # Should have warnings for both paths
    
    def test_validate_pydantic_model(self, validator: SaidataValidator):
        """Test validation of Pydantic model."""
        saidata = SaiData(
            version="0.2",
            metadata=Metadata(name="test-software")
        )
        
        result = validator.validate_pydantic_model(saidata)
        
        assert result.is_valid
        assert not result.has_errors
    
    def test_validate_file_valid_yaml(self, validator: SaidataValidator, valid_saidata: Dict[str, Any]):
        """Test validation of YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(valid_saidata, f)
            temp_path = Path(f.name)
        
        try:
            result = validator.validate_file(temp_path)
            
            assert result.is_valid
            assert not result.has_errors
        finally:
            temp_path.unlink()
    
    def test_validate_file_invalid_yaml(self, validator: SaidataValidator):
        """Test validation of invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")  # Invalid YAML
            temp_path = Path(f.name)
        
        try:
            result = validator.validate_file(temp_path)
            
            assert not result.is_valid
            assert result.has_errors
            
            yaml_errors = [error for error in result.errors if "yaml" in error.code.lower()]
            assert len(yaml_errors) > 0
        finally:
            temp_path.unlink()
    
    def test_validate_file_not_found(self, validator: SaidataValidator):
        """Test validation of non-existent file."""
        result = validator.validate_file(Path("/nonexistent/file.yaml"))
        
        assert not result.is_valid
        assert result.has_errors
        
        not_found_errors = [error for error in result.errors if "not found" in error.message.lower()]
        assert len(not_found_errors) > 0
    
    def test_format_validation_report(self, validator: SaidataValidator):
        """Test formatting of validation report."""
        invalid_data = {
            "version": "invalid",
            "metadata": {
                "name": "test"
            },
            "ports": [
                {
                    "port": 70000
                }
            ]
        }
        
        result = validator.validate_data(invalid_data)
        report = validator.format_validation_report(result)
        
        assert "❌ Validation failed" in report
        assert "Total issues:" in report
        assert "Errors:" in report
        assert "Warnings:" in report
        
        # Should contain specific error information
        assert "version" in report.lower()
        assert "port" in report.lower()
    
    def test_format_validation_report_with_context(self, validator: SaidataValidator):
        """Test formatting of validation report with context."""
        invalid_data = {
            "version": "0.2",
            "metadata": {
                "name": "test"
            },
            "services": [
                {
                    "name": "test-service",
                    "type": "invalid-type"
                }
            ]
        }
        
        result = validator.validate_data(invalid_data)
        report = validator.format_validation_report(result, show_context=True)
        
        assert "Context:" in report
    
    def test_validation_error_properties(self, validator: SaidataValidator):
        """Test ValidationResult properties."""
        invalid_data = {
            "version": "invalid",
            "metadata": {
                "name": "test"
            },
            "ports": [
                {
                    "port": 80  # Privileged port (warning)
                }
            ]
        }
        
        result = validator.validate_data(invalid_data)
        
        assert not result.is_valid
        assert result.has_errors
        assert result.has_warnings
        assert result.total_issues > 0
        assert result.total_issues == len(result.errors) + len(result.warnings) + len(result.info)
    
    def test_schema_error_formatting(self, validator: SaidataValidator):
        """Test specific schema error message formatting."""
        # Test missing required field
        result = validator.validate_data({"version": "0.2"})
        
        required_errors = [error for error in result.errors if "required" in error.message.lower()]
        assert len(required_errors) > 0
        
        error = required_errors[0]
        assert error.suggestion is not None
        assert "metadata" in error.suggestion.lower()
    
    def test_custom_schema_path(self):
        """Test validator with custom schema path."""
        # Create a minimal schema for testing
        minimal_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "test": {"type": "string"}
            },
            "required": ["test"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(minimal_schema, f)
            schema_path = Path(f.name)
        
        try:
            validator = SaidataValidator(schema_path=schema_path)
            result = validator.validate_data({"test": "value"})
            
            assert result.is_valid
        finally:
            schema_path.unlink()
    
    def test_invalid_schema_path(self):
        """Test validator with invalid schema path."""
        with pytest.raises(FileNotFoundError):
            validator = SaidataValidator(schema_path=Path("/nonexistent/schema.json"))
            validator.validate_data({"test": "data"})


class TestValidationErrorFormatting:
    """Test specific error message formatting."""
    
    @pytest.fixture
    def validator(self) -> SaidataValidator:
        """Create validator instance."""
        return SaidataValidator()
    
    def test_type_error_formatting(self, validator: SaidataValidator):
        """Test type error message formatting."""
        invalid_data = {
            "version": 123,  # Should be string
            "metadata": {
                "name": "test"
            }
        }
        
        result = validator.validate_data(invalid_data)
        
        type_errors = [error for error in result.errors if "type" in error.message.lower()]
        assert len(type_errors) > 0
        
        error = type_errors[0]
        assert "expected" in error.message.lower()
        assert "got" in error.message.lower()
    
    def test_enum_error_formatting(self, validator: SaidataValidator):
        """Test enum error message formatting."""
        invalid_data = {
            "version": "0.2",
            "metadata": {
                "name": "test"
            },
            "services": [
                {
                    "name": "test-service",
                    "type": "invalid-enum-value"
                }
            ]
        }
        
        result = validator.validate_data(invalid_data)
        
        enum_errors = [error for error in result.errors if "must be one of" in error.message.lower()]
        assert len(enum_errors) > 0
        
        error = enum_errors[0]
        assert error.suggestion is not None
        assert "allowed values" in error.suggestion.lower()
    
    def test_pattern_error_formatting(self, validator: SaidataValidator):
        """Test pattern error message formatting."""
        invalid_data = {
            "version": "invalid-pattern",  # Doesn't match version pattern
            "metadata": {
                "name": "test"
            }
        }
        
        result = validator.validate_data(invalid_data)
        
        pattern_errors = [error for error in result.errors if "pattern" in error.message.lower()]
        assert len(pattern_errors) > 0
        
        error = pattern_errors[0]
        assert "does not match" in error.message.lower()