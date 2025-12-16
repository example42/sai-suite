"""Tests for provider security features."""

import pytest

from sai.models.config import SaiConfig
from sai.utils.errors import SecurityError


class TestSecurityConfiguration:
    """Test security configuration features."""

    def test_default_allowed_binaries(self):
        """Test that default configuration includes common binaries."""
        config = SaiConfig()

        # Check that common binaries are included
        assert "which" in config.allowed_detection_binaries
        assert "ls" in config.allowed_detection_binaries
        assert "cat" in config.allowed_detection_binaries
        assert "dpkg" in config.allowed_detection_binaries
        assert "rpm" in config.allowed_detection_binaries
        assert "brew" in config.allowed_detection_binaries
        assert "apt" in config.allowed_detection_binaries

    def test_custom_allowed_binaries(self):
        """Test that custom binaries can be configured."""
        config = SaiConfig(
            allowed_detection_binaries=["which", "custom-tool", "my-binary"]
        )

        assert "which" in config.allowed_detection_binaries
        assert "custom-tool" in config.allowed_detection_binaries
        assert "my-binary" in config.allowed_detection_binaries
        assert len(config.allowed_detection_binaries) == 3

    def test_empty_binaries_list_raises_error(self):
        """Test that empty allowed binaries list raises validation error."""
        with pytest.raises(ValueError) as exc_info:
            SaiConfig(allowed_detection_binaries=[])

        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_binaries_stripped(self):
        """Test that whitespace in binary names is stripped."""
        config = SaiConfig(
            allowed_detection_binaries=["  which  ", " ls ", "cat"]
        )

        assert "which" in config.allowed_detection_binaries
        assert "ls" in config.allowed_detection_binaries
        assert "cat" in config.allowed_detection_binaries
        # Verify no whitespace remains
        for binary in config.allowed_detection_binaries:
            assert binary == binary.strip()

    def test_security_error_with_details(self):
        """Test SecurityError includes proper details and suggestions."""
        error = SecurityError(
            "Test blocked",
            security_issue="unauthorized_binary",
            details={"executable": "evil", "allowed_binaries": ["good"]},
            suggestions=["Add to config", "Use env var"],
        )

        assert error.message == "Test blocked"
        assert error.details["security_issue"] == "unauthorized_binary"
        assert error.details["executable"] == "evil"
        assert "Add to config" in error.suggestions
        assert "Use env var" in error.suggestions

    def test_security_error_full_message(self):
        """Test SecurityError full message includes suggestions."""
        error = SecurityError(
            "Command blocked",
            suggestions=["Suggestion 1", "Suggestion 2"],
        )

        full_message = error.get_full_message()
        assert "Command blocked" in full_message
        assert "Suggestions:" in full_message
        assert "1. Suggestion 1" in full_message
        assert "2. Suggestion 2" in full_message
