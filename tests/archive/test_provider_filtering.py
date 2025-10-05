"""Tests for provider filtering based on software compatibility."""

from unittest.mock import patch

import pytest

from sai.models.provider_data import Action, Provider, ProviderData, ProviderType
from sai.providers.base import BaseProvider
from saigen.models.saidata import Metadata, SaiData


class TestProviderFiltering:
    """Test provider filtering based on software compatibility."""

    def create_test_provider(self, name: str, template: str) -> BaseProvider:
        """Create a test provider with a specific template."""
        provider_data = ProviderData(
            version="0.1",
            provider=Provider(
                name=name, type=ProviderType.PACKAGE_MANAGER, executable=f"{name}-cmd"
            ),
            actions={
                "install": Action(description="Install packages", template=template, timeout=300)
            },
        )
        return BaseProvider(provider_data)

    def test_can_handle_software_success(self):
        """Test that provider can handle software when template resolves successfully."""
        # Create provider with simple template
        provider = self.create_test_provider("test", "test-cmd install {{saidata.metadata.name}}")

        # Create test saidata
        saidata = SaiData(version="0.2", metadata=Metadata(name="nginx"))

        # Should be able to handle the software
        assert provider.can_handle_software("install", saidata) is True

    def test_can_handle_software_with_detection_command(self):
        """Test that provider uses detection command when available."""
        # Create provider with detection command
        provider_data = ProviderData(
            version="0.1",
            provider=Provider(
                name="test", type=ProviderType.PACKAGE_MANAGER, executable="test-cmd"
            ),
            actions={
                "install": Action(
                    description="Install packages",
                    template="test-cmd install {{saidata.metadata.name}}",
                    detection='test-cmd search {{saidata.metadata.name}} | grep -q "^{{saidata.metadata.name}}$"',
                    timeout=300,
                )
            },
        )
        provider = BaseProvider(provider_data)
        saidata = SaiData(version="0.2", metadata=Metadata(name="nginx"))

        # Mock the detection command execution
        with patch("subprocess.run") as mock_run:
            # Test successful detection
            mock_run.return_value.returncode = 0
            assert provider.can_handle_software("install", saidata) is True

            # Test failed detection
            mock_run.return_value.returncode = 1
            assert provider.can_handle_software("install", saidata) is False

    def test_can_handle_software_unsupported_action(self):
        """Test that provider cannot handle unsupported actions."""
        provider = self.create_test_provider("test", "test-cmd install {{saidata.metadata.name}}")
        saidata = SaiData(version="0.2", metadata=Metadata(name="nginx"))

        # Should not be able to handle unsupported action
        assert provider.can_handle_software("unsupported_action", saidata) is False

    def test_can_handle_software_unexpected_error(self):
        """Test that provider handles unexpected errors gracefully."""
        provider = self.create_test_provider("test", "test-cmd install {{saidata.metadata.name}}")
        saidata = SaiData(version="0.2", metadata=Metadata(name="nginx"))

        # Mock resolve_action_templates to raise unexpected error
        with patch.object(
            provider, "resolve_action_templates", side_effect=ValueError("Unexpected error")
        ):
            # Should return True for unexpected errors (assume provider could work)
            assert provider.can_handle_software("install", saidata) is True

    def test_can_handle_software_package_availability(self):
        """Test provider package availability checking."""
        # Create provider without detection command (falls back to package availability)
        provider = self.create_test_provider("test", "test-cmd install {{saidata.metadata.name}}")

        # Test with saidata that has general packages
        from saigen.models.saidata import Package

        saidata_with_packages = SaiData(
            version="0.2", metadata=Metadata(name="nginx"), packages=[Package(name="nginx")]
        )

        # Should be able to handle because it has general packages
        assert provider.can_handle_software("install", saidata_with_packages) is True

        # Test with saidata that only has metadata name
        saidata_metadata_only = SaiData(version="0.2", metadata=Metadata(name="nginx"))

        # Should be able to handle because it has metadata name
        assert provider.can_handle_software("install", saidata_metadata_only) is True

        # Test with saidata that has no name
        saidata_no_name = SaiData(version="0.2", metadata=Metadata(name=""))

        # Should not be able to handle because no package data available
        assert provider.can_handle_software("install", saidata_no_name) is False


if __name__ == "__main__":
    pytest.main([__file__])
