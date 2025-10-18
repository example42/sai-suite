"""Tests for error handling utilities."""

from pathlib import Path

import pytest

from sai.utils.errors import (
    ConfigurationError,
    InvalidConfigurationError,
    MissingConfigurationError,
    SaiError,
    format_error_for_cli,
    get_error_suggestions,
    is_system_error,
    is_user_error,
)


class TestSaiError:
    """Test base SaiError functionality."""

    def test_basic_error_creation(self):
        """Test basic error creation."""
        error = SaiError("Test error message")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details == {}
        assert error.suggestions == []
        assert error.error_code is None

    def test_error_with_details(self):
        """Test error creation with details."""
        details = {"file": "test.yaml", "line": 42}
        error = SaiError("Test error", details=details)

        assert error.details == details

    def test_error_with_suggestions(self):
        """Test error creation with suggestions."""
        suggestions = ["Try this", "Or this"]
        error = SaiError("Test error", suggestions=suggestions)

        assert error.suggestions == suggestions

    def test_error_with_code(self):
        """Test error creation with error code."""
        error = SaiError("Test error", error_code="TEST_001")

        assert error.error_code == "TEST_001"

    def test_get_full_message(self):
        """Test full message generation."""
        error = SaiError("Test error", suggestions=["Fix this", "Try that"])

        full_message = error.get_full_message()

        assert "Test error" in full_message
        assert "Suggestions:" in full_message
        assert "1. Fix this" in full_message
        assert "2. Try that" in full_message

    def test_get_full_message_no_suggestions(self):
        """Test full message without suggestions."""
        error = SaiError("Test error")

        full_message = error.get_full_message()

        assert full_message == "Test error"
        assert "Suggestions:" not in full_message

    def test_to_dict(self):
        """Test dictionary conversion."""
        error = SaiError(
            "Test error",
            details={"key": "value"},
            suggestions=["suggestion"],
            error_code="TEST_001",
        )

        result = error.to_dict()

        expected = {
            "error_type": "SaiError",
            "message": "Test error",
            "error_code": "TEST_001",
            "details": {"key": "value"},
            "suggestions": ["suggestion"],
        }

        assert result == expected


class TestConfigurationErrors:
    """Test configuration-related errors."""

    def test_configuration_error(self):
        """Test basic configuration error."""
        config_file = Path("/path/to/config.yaml")
        error = ConfigurationError("Config error", config_file=config_file)

        assert error.message == "Config error"
        assert error.details["config_file"] == str(config_file)

    def test_invalid_configuration_error(self):
        """Test invalid configuration error."""
        validation_errors = ["Missing required field", "Invalid value"]
        error = InvalidConfigurationError("Invalid config", validation_errors=validation_errors)

        assert error.message == "Invalid config"
        assert error.details["validation_errors"] == validation_errors
        assert len(error.suggestions) > 0
        assert any("syntax" in suggestion.lower() for suggestion in error.suggestions)

    def test_missing_configuration_error(self):
        """Test missing configuration error."""
        error = MissingConfigurationError("required_key")

        assert "Missing required configuration: required_key" in error.message
        assert error.details["missing_key"] == "required_key"
        assert len(error.suggestions) > 0
        assert any("required_key" in suggestion for suggestion in error.suggestions)


class TestErrorUtilities:
    """Test error utility functions."""

    def test_format_error_for_cli_simple(self):
        """Test simple error formatting for CLI."""
        error = Exception("Simple error")

        result = format_error_for_cli(error, verbose=False)

        assert result == "Simple error"

    def test_format_error_for_cli_verbose(self):
        """Test verbose error formatting for CLI."""
        error = Exception("Simple error")

        result = format_error_for_cli(error, verbose=True)

        # Should include traceback in verbose mode
        assert "Simple error" in result
        assert "Full Traceback:" in result

    def test_format_error_for_cli_sai_error(self):
        """Test SAI error formatting for CLI."""
        error = SaiError("SAI error", error_code="SAI_001")

        result = format_error_for_cli(error, verbose=False)

        assert result == "SAI error"

    def test_format_error_for_cli_sai_error_verbose(self):
        """Test verbose SAI error formatting for CLI."""
        error = SaiError("SAI error", error_code="SAI_001", details={"key": "value"})

        result = format_error_for_cli(error, verbose=True)

        assert "SAI error" in result
        assert "Details:" in result
        assert "key: value" in result

    def test_get_error_suggestions_sai_error(self):
        """Test getting suggestions from SAI error."""
        suggestions = ["Try this", "Or that"]
        error = SaiError("Test error", suggestions=suggestions)

        result = get_error_suggestions(error)

        assert result == suggestions

    def test_get_error_suggestions_non_sai_error(self):
        """Test getting suggestions from non-SAI error."""
        error = Exception("Regular error")

        result = get_error_suggestions(error)

        # Should return generic suggestions for non-SAI errors
        assert len(result) > 0
        assert any("command syntax" in suggestion.lower() for suggestion in result)

    def test_is_user_error(self):
        """Test user error detection."""
        # Test with user error types
        user_errors = [
            InvalidConfigurationError("Invalid config"),
            MissingConfigurationError("missing_key"),
        ]

        for error in user_errors:
            assert is_user_error(error) is True

        # Test with non-user errors
        system_error = Exception("System error")
        assert is_user_error(system_error) is False

    def test_is_system_error(self):
        """Test system error detection."""
        # Import the specific error types used in the function
        from sai.utils.errors import (
            CacheError,
            CommandExecutionError,
            NetworkError,
            ProviderNotAvailableError,
        )

        # Test with system error types
        system_errors = [
            ProviderNotAvailableError("provider", "not available"),
            CommandExecutionError("command", "failed", 1),
            NetworkError("Network error"),
            CacheError("Cache error"),
        ]

        for error in system_errors:
            assert is_system_error(error) is True

        # Test with non-system errors
        user_error = InvalidConfigurationError("Invalid config")
        assert is_system_error(user_error) is False

    def test_error_inheritance(self):
        """Test error class inheritance."""
        # All configuration errors should inherit from SaiError
        config_error = ConfigurationError("Config error")
        invalid_config_error = InvalidConfigurationError("Invalid config")
        missing_config_error = MissingConfigurationError("missing_key")

        assert isinstance(config_error, SaiError)
        assert isinstance(invalid_config_error, SaiError)
        assert isinstance(invalid_config_error, ConfigurationError)
        assert isinstance(missing_config_error, SaiError)
        assert isinstance(missing_config_error, ConfigurationError)


if __name__ == "__main__":
    pytest.main([__file__])
