"""Tests for update CLI command."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from saigen.cli.commands.update import (
    update,
)


@pytest.fixture
def sample_saidata_file():
    """Create a temporary saidata file for testing."""
    saidata_content = {
        "version": "0.2",
        "metadata": {
            "name": "nginx",
            "display_name": "NGINX Web Server",
            "description": "High-performance web server",
            "version": "1.20.0",
            "category": "web",
            "tags": ["web", "server"],
            "license": "BSD-2-Clause",
        },
        "providers": {
            "apt": {"packages": [{"name": "nginx", "package_name": "nginx", "version": "1.20.0"}]}
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(saidata_content, f)
        return Path(f.name)


@pytest.fixture
def mock_config():
    """Mock configuration."""
    return {"llm_providers": {"openai": {"api_key": "test-key", "model": "gpt-4o-mini"}}}


class TestUpdateCommand:
    """Test cases for update CLI command."""

    def test_update_dry_run(self, sample_saidata_file, mock_config):
        """Test update command in dry run mode."""
        runner = CliRunner()

        mock_context = {
            "config": mock_config,
            "llm_provider": None,
            "verbose": False,
            "dry_run": True,
        }

        result = runner.invoke(update, [str(sample_saidata_file)], obj=mock_context)

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output
        assert "Would update saidata file" in result.output

    def test_update_nonexistent_file(self):
        """Test update command with nonexistent file."""
        runner = CliRunner()

        result = runner.invoke(update, ["/nonexistent/file.yaml"])

        # Click should handle this with a file existence check
        assert result.exit_code != 0


class TestUpdateCommandHelpers:
    """Test helper functions for update command."""

    def test_load_existing_saidata_success(self, sample_saidata_file):
        """Test loading valid saidata file."""
        from saigen.cli.commands.update import _load_existing_saidata

        saidata = _load_existing_saidata(sample_saidata_file)

        assert saidata.metadata.name == "nginx"
        assert saidata.version == "0.2"
        assert "apt" in saidata.providers

    def test_load_existing_saidata_invalid_yaml(self):
        """Test loading invalid YAML file."""
        import click

        from saigen.cli.commands.update import _load_existing_saidata

        # Create invalid YAML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: [")
            invalid_file = Path(f.name)

        with pytest.raises(click.ClickException) as exc_info:
            _load_existing_saidata(invalid_file)

        assert "Invalid YAML" in str(exc_info.value)

        # Clean up
        invalid_file.unlink()

    def test_get_backup_path_default(self):
        """Test getting backup path with default location."""
        from saigen.cli.commands.update import _get_backup_path

        original_path = Path("/path/to/nginx.yaml")
        backup_path = _get_backup_path(original_path)

        assert backup_path.parent == original_path.parent
        assert backup_path.name.startswith("nginx.backup.")
        assert backup_path.name.endswith(".yaml")

    def test_get_backup_path_custom_dir(self):
        """Test getting backup path with custom directory."""
        from saigen.cli.commands.update import _get_backup_path

        original_path = Path("/path/to/nginx.yaml")
        # Use a temporary directory that we can actually create
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"
            backup_path = _get_backup_path(original_path, backup_dir)

            assert backup_path.parent == backup_dir
            assert backup_path.name.startswith("nginx.backup.")
            assert backup_path.name.endswith(".yaml")

    @patch("shutil.copy2")
    def test_create_backup_success(self, mock_copy):
        """Test successful backup creation."""
        from saigen.cli.commands.update import _create_backup

        original_path = Path("/path/to/nginx.yaml")
        backup_path = _create_backup(original_path)

        mock_copy.assert_called_once()
        assert backup_path.name.startswith("nginx.backup.")

    @patch("shutil.copy2")
    def test_create_backup_failure(self, mock_copy):
        """Test backup creation failure."""
        import click

        from saigen.cli.commands.update import _create_backup

        mock_copy.side_effect = OSError("Permission denied")

        original_path = Path("/path/to/nginx.yaml")

        with pytest.raises(click.ClickException) as exc_info:
            _create_backup(original_path)

        assert "Failed to create backup" in str(exc_info.value)
