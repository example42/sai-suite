"""Tests for repository CLI commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import AsyncMock, MagicMock, patch

from saigen.cli.repositories import list_repos
from saigen.models.repository import RepositoryInfo


class TestListReposCLI:
    """Test list-repos CLI command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repository data."""
        return [
            RepositoryInfo(
                name="apt-ubuntu-jammy",
                type="apt",
                platform="linux",
                description="Ubuntu 22.04 (Jammy) Main Repository",
                enabled=True,
                priority=90,
                version_mapping={"22.04": "jammy"},
                eol=False,
                query_type="bulk_download"
            ),
            RepositoryInfo(
                name="apt-ubuntu-focal",
                type="apt",
                platform="linux",
                description="Ubuntu 20.04 (Focal) Main Repository",
                enabled=True,
                priority=85,
                version_mapping={"20.04": "focal"},
                eol=False,
                query_type="bulk_download"
            ),
            RepositoryInfo(
                name="apt-debian-bullseye",
                type="apt",
                platform="linux",
                description="Debian 11 (Bullseye) Main Repository",
                enabled=True,
                priority=90,
                version_mapping={"11": "bullseye"},
                eol=False,
                query_type="bulk_download"
            ),
            RepositoryInfo(
                name="apt-debian-buster",
                type="apt",
                platform="linux",
                description="Debian 10 (Buster) Main Repository",
                enabled=True,
                priority=80,
                version_mapping={"10": "buster"},
                eol=True,
                query_type="bulk_download"
            ),
            RepositoryInfo(
                name="brew-macos",
                type="brew",
                platform="macos",
                description="Homebrew Package Manager",
                enabled=True,
                priority=95,
                version_mapping=None,
                eol=False,
                query_type="bulk_download"
            ),
        ]

    def test_list_repos_help(self, runner):
        """Test list-repos command help."""
        result = runner.invoke(list_repos, ["--help"])
        assert result.exit_code == 0
        assert "List available repositories" in result.output
        assert "--platform" in result.output
        assert "--type" in result.output
        assert "--os" in result.output
        assert "--version" in result.output
        assert "--eol" in result.output
        assert "--active" in result.output

    @patch("saigen.cli.repositories.get_repository_manager")
    def test_list_repos_basic(self, mock_get_manager, runner, mock_repositories):
        """Test basic list-repos command."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
        mock_manager.__aexit__ = AsyncMock(return_value=None)
        mock_manager.get_all_repository_info = MagicMock(return_value=mock_repositories)
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(list_repos, [])
        
        assert result.exit_code == 0
        assert "apt-ubuntu-jammy" in result.output
        assert "apt-debian-bullseye" in result.output
        assert "brew-macos" in result.output
        assert "Total: 5 repositories" in result.output

    @patch("saigen.cli.repositories.get_repository_manager")
    def test_list_repos_with_version_mapping(self, mock_get_manager, runner, mock_repositories):
        """Test that version_mapping is displayed."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
        mock_manager.__aexit__ = AsyncMock(return_value=None)
        mock_manager.get_all_repository_info = MagicMock(return_value=mock_repositories)
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(list_repos, [])
        
        assert result.exit_code == 0
        # Check that version mappings are shown
        assert "22.04 (jammy)" in result.output or "jammy" in result.output
        assert "11 (bullseye)" in result.output or "bullseye" in result.output

    @patch("saigen.cli.repositories.get_repository_manager")
    def test_list_repos_eol_status(self, mock_get_manager, runner, mock_repositories):
        """Test EOL status display."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
        mock_manager.__aexit__ = AsyncMock(return_value=None)
        mock_manager.get_all_repository_info = MagicMock(return_value=mock_repositories)
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(list_repos, [])
        
        assert result.exit_code == 0
        assert "[EOL]" in result.output
        assert "Active" in result.output
        assert "EOL repositories: 1" in result.output

    @patch("saigen.cli.repositories.get_repository_manager")
    def test_list_repos_filter_os(self, mock_get_manager, runner, mock_repositories):
        """Test filtering by OS."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
        mock_manager.__aexit__ = AsyncMock(return_value=None)
        mock_manager.get_all_repository_info = MagicMock(return_value=mock_repositories)
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(list_repos, ["--os", "ubuntu"])
        
        assert result.exit_code == 0
        assert "apt-ubuntu-jammy" in result.output
        assert "apt-ubuntu-focal" in result.output
        assert "apt-debian-bullseye" not in result.output
        assert "Total: 2 repositories" in result.output

    @patch("saigen.cli.repositories.get_repository_manager")
    def test_list_repos_filter_version(self, mock_get_manager, runner, mock_repositories):
        """Test filtering by version."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
        mock_manager.__aexit__ = AsyncMock(return_value=None)
        mock_manager.get_all_repository_info = MagicMock(return_value=mock_repositories)
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(list_repos, ["--version", "22.04"])
        
        assert result.exit_code == 0
        assert "apt-ubuntu-jammy" in result.output
        assert "apt-ubuntu-focal" not in result.output
        assert "Total: 1 repositories" in result.output

    @patch("saigen.cli.repositories.get_repository_manager")
    def test_list_repos_filter_eol(self, mock_get_manager, runner, mock_repositories):
        """Test filtering for EOL repositories only."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
        mock_manager.__aexit__ = AsyncMock(return_value=None)
        mock_manager.get_all_repository_info = MagicMock(return_value=mock_repositories)
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(list_repos, ["--eol"])
        
        assert result.exit_code == 0
        assert "apt-debian-buster" in result.output
        assert "apt-ubuntu-jammy" not in result.output
        assert "Total: 1 repositories" in result.output

    @patch("saigen.cli.repositories.get_repository_manager")
    def test_list_repos_filter_active(self, mock_get_manager, runner, mock_repositories):
        """Test filtering for active repositories only."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
        mock_manager.__aexit__ = AsyncMock(return_value=None)
        mock_manager.get_all_repository_info = MagicMock(return_value=mock_repositories)
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(list_repos, ["--active"])
        
        assert result.exit_code == 0
        assert "apt-ubuntu-jammy" in result.output
        assert "apt-debian-buster" not in result.output
        assert "Total: 4 repositories" in result.output

    @patch("saigen.cli.repositories.get_repository_manager")
    def test_list_repos_json_format(self, mock_get_manager, runner, mock_repositories):
        """Test JSON output format."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
        mock_manager.__aexit__ = AsyncMock(return_value=None)
        mock_manager.get_all_repository_info = MagicMock(return_value=mock_repositories)
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(list_repos, ["--format", "json"])
        
        assert result.exit_code == 0
        assert '"name": "apt-ubuntu-jammy"' in result.output
        assert '"version_mapping"' in result.output
        assert '"eol"' in result.output

    @patch("saigen.cli.repositories.get_repository_manager")
    def test_list_repos_combined_filters(self, mock_get_manager, runner, mock_repositories):
        """Test combining multiple filters."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
        mock_manager.__aexit__ = AsyncMock(return_value=None)
        mock_manager.get_all_repository_info = MagicMock(return_value=mock_repositories)
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(list_repos, ["--os", "ubuntu", "--active"])
        
        assert result.exit_code == 0
        assert "apt-ubuntu-jammy" in result.output
        assert "apt-ubuntu-focal" in result.output
        assert "apt-debian-buster" not in result.output
        assert "Total: 2 repositories" in result.output
