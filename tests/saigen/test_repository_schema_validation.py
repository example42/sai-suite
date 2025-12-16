"""Tests for repository schema validation with version_mapping, eol, and query_type fields."""

import pytest
import tempfile
from pathlib import Path
import yaml

from saigen.repositories.universal_manager import UniversalRepositoryManager
from saigen.utils.errors import ConfigurationError


class TestRepositorySchemaValidation:
    """Test repository configuration schema validation."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_valid_version_mapping(self, temp_config_dir):
        """Test valid version_mapping configuration."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "apt-ubuntu-jammy",
                    "type": "apt",
                    "platform": "linux",
                    "distribution": ["ubuntu"],
                    "version_mapping": {"22.04": "jammy"},
                    "endpoints": {"packages": "http://example.com/packages"},
                    "parsing": {"format": "debian_packages"},
                }
            ],
        }

        config_file = temp_config_dir / "apt.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = UniversalRepositoryManager("cache", [str(temp_config_dir)])
        # Should not raise any exception
        assert manager is not None

    def test_valid_eol_field(self, temp_config_dir):
        """Test valid eol field configuration."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "apt-ubuntu-focal",
                    "type": "apt",
                    "platform": "linux",
                    "distribution": ["ubuntu"],
                    "version_mapping": {"20.04": "focal"},
                    "eol": True,
                    "endpoints": {"packages": "http://example.com/packages"},
                    "parsing": {"format": "debian_packages"},
                }
            ],
        }

        config_file = temp_config_dir / "apt.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = UniversalRepositoryManager("cache", [str(temp_config_dir)])
        assert manager is not None

    def test_valid_query_type_bulk_download(self, temp_config_dir):
        """Test valid query_type field with bulk_download."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "apt-debian-bookworm",
                    "type": "apt",
                    "platform": "linux",
                    "distribution": ["debian"],
                    "version_mapping": {"12": "bookworm"},
                    "query_type": "bulk_download",
                    "endpoints": {"packages": "http://example.com/packages"},
                    "parsing": {"format": "debian_packages"},
                }
            ],
        }

        config_file = temp_config_dir / "apt.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = UniversalRepositoryManager("cache", [str(temp_config_dir)])
        assert manager is not None

    def test_valid_query_type_api(self, temp_config_dir):
        """Test valid query_type field with api."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "npm-registry",
                    "type": "npm",
                    "platform": "universal",
                    "query_type": "api",
                    "endpoints": {"packages": "https://registry.npmjs.org"},
                    "parsing": {"format": "json"},
                }
            ],
        }

        config_file = temp_config_dir / "npm.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = UniversalRepositoryManager("cache", [str(temp_config_dir)])
        assert manager is not None

    def test_invalid_version_mapping_not_dict(self, temp_config_dir):
        """Test invalid version_mapping that is not a dictionary."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "apt-ubuntu-jammy",
                    "type": "apt",
                    "platform": "linux",
                    "version_mapping": "22.04:jammy",  # Invalid: should be dict
                    "endpoints": {"packages": "http://example.com/packages"},
                    "parsing": {"format": "debian_packages"},
                }
            ],
        }

        config_file = temp_config_dir / "apt.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = UniversalRepositoryManager("cache", [str(temp_config_dir)])
        # The manager logs errors but doesn't raise during initialization
        # Check that the repository was not loaded
        assert len(manager._configs) == 0

    def test_invalid_version_mapping_bad_version_format(self, temp_config_dir):
        """Test invalid version_mapping with non-numeric version."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "apt-ubuntu-jammy",
                    "type": "apt",
                    "platform": "linux",
                    "version_mapping": {"jammy": "22.04"},  # Invalid: version should be numeric
                    "endpoints": {"packages": "http://example.com/packages"},
                    "parsing": {"format": "debian_packages"},
                }
            ],
        }

        config_file = temp_config_dir / "apt.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = UniversalRepositoryManager("cache", [str(temp_config_dir)])
        # Check that the repository was not loaded due to validation error
        assert len(manager._configs) == 0

    def test_invalid_version_mapping_bad_codename_format(self, temp_config_dir):
        """Test invalid version_mapping with uppercase codename."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "apt-ubuntu-jammy",
                    "type": "apt",
                    "platform": "linux",
                    "version_mapping": {"22.04": "Jammy"},  # Invalid: should be lowercase
                    "endpoints": {"packages": "http://example.com/packages"},
                    "parsing": {"format": "debian_packages"},
                }
            ],
        }

        config_file = temp_config_dir / "apt.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = UniversalRepositoryManager("cache", [str(temp_config_dir)])
        # Check that the repository was not loaded due to validation error
        assert len(manager._configs) == 0

    def test_invalid_eol_not_boolean(self, temp_config_dir):
        """Test invalid eol field that is not a boolean."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "apt-ubuntu-focal",
                    "type": "apt",
                    "platform": "linux",
                    "eol": "yes",  # Invalid: should be boolean
                    "endpoints": {"packages": "http://example.com/packages"},
                    "parsing": {"format": "debian_packages"},
                }
            ],
        }

        config_file = temp_config_dir / "apt.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = UniversalRepositoryManager("cache", [str(temp_config_dir)])
        # Check that the repository was not loaded due to validation error
        assert len(manager._configs) == 0

    def test_invalid_query_type(self, temp_config_dir):
        """Test invalid query_type value."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "npm-registry",
                    "type": "npm",
                    "platform": "universal",
                    "query_type": "streaming",  # Invalid: must be bulk_download or api
                    "endpoints": {"packages": "https://registry.npmjs.org"},
                    "parsing": {"format": "json"},
                }
            ],
        }

        config_file = temp_config_dir / "npm.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = UniversalRepositoryManager("cache", [str(temp_config_dir)])
        # Check that the repository was not loaded due to validation error
        assert len(manager._configs) == 0

    @pytest.mark.asyncio
    async def test_all_new_fields_together(self, temp_config_dir):
        """Test all new fields together in a valid configuration."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "apt-ubuntu-focal",
                    "type": "apt",
                    "platform": "linux",
                    "distribution": ["ubuntu"],
                    "version_mapping": {"20.04": "focal"},
                    "eol": True,
                    "query_type": "bulk_download",
                    "endpoints": {"packages": "http://example.com/packages"},
                    "parsing": {"format": "debian_packages"},
                }
            ],
        }

        config_file = temp_config_dir / "apt.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = UniversalRepositoryManager("cache", [str(temp_config_dir)])
        await manager.initialize()
        assert manager is not None
        # Verify the configuration was loaded
        assert "apt-ubuntu-focal" in manager._configs

    @pytest.mark.asyncio
    async def test_multiple_version_mappings(self, temp_config_dir):
        """Test repository with multiple version mappings (though typically one per repo)."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "fedora-multi",
                    "type": "dnf",
                    "platform": "linux",
                    "distribution": ["fedora"],
                    "version_mapping": {"38": "f38", "39": "f39", "40": "f40"},
                    "endpoints": {"packages": "http://example.com/packages"},
                    "parsing": {"format": "rpm_metadata"},
                }
            ],
        }

        config_file = temp_config_dir / "dnf.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = UniversalRepositoryManager("cache", [str(temp_config_dir)])
        await manager.initialize()
        assert manager is not None
        assert "fedora-multi" in manager._configs
