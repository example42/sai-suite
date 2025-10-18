"""Tests for SaidataRepositoryManager."""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sai.core.git_repository_handler import GitOperationResult, RepositoryInfo
from sai.core.saidata_loader import SaidataNotFoundError
from sai.core.saidata_repository_manager import (
    RepositoryHealthCheck,
    RepositoryStatus,
    SaidataRepositoryManager,
)
from sai.core.tarball_repository_handler import TarballOperationResult
from sai.models.config import RepositoryAuthType, SaiConfig
from sai.models.saidata import SaiData


class TestSaidataRepositoryManager:
    """Test cases for SaidataRepositoryManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def config(self, temp_dir):
        """Create a test configuration."""
        return SaiConfig(
            cache_directory=temp_dir / "cache",
            saidata_repository_url="https://github.com/example42/saidata",
            saidata_repository_branch="main",
            saidata_auto_update=True,
            saidata_update_interval=3600,
            saidata_offline_mode=False,
        )

    @pytest.fixture
    def manager(self, config):
        """Create a SaidataRepositoryManager instance."""
        return SaidataRepositoryManager(config)

    def test_init_creates_cache_directory(self, config, temp_dir):
        """Test that initialization creates the cache directory."""
        manager = SaidataRepositoryManager(config)
        assert manager.repository_cache_dir.exists()
        assert manager.repository_cache_dir.is_dir()

    def test_repository_path_generation(self, manager):
        """Test repository path generation from URL."""
        path = manager.repository_path
        assert path.name.startswith("example42-saidata")
        assert path.parent == manager.repository_cache_dir

    def test_repository_name_with_branch(self, config, temp_dir):
        """Test repository name generation with different branch."""
        config.saidata_repository_branch = "develop"
        manager = SaidataRepositoryManager(config)
        path = manager.repository_path
        assert "develop" in path.name

    def test_get_saidata_success(self, manager):
        """Test successful saidata retrieval."""
        # Mock the loader
        mock_saidata = Mock(spec=SaiData)
        manager.saidata_loader.load_saidata = Mock(return_value=mock_saidata)

        # Mock repository exists and is valid
        manager.repository_path.mkdir(parents=True, exist_ok=True)
        manager._is_cache_valid = Mock(return_value=True)

        result = manager.get_saidata("apache")

        assert result == mock_saidata
        manager.saidata_loader.load_saidata.assert_called_once_with("apache")

    def test_get_saidata_with_force_update(self, manager):
        """Test saidata retrieval with forced update."""
        # Mock the loader
        mock_saidata = Mock(spec=SaiData)
        manager.saidata_loader.load_saidata = Mock(return_value=mock_saidata)

        # Mock successful update
        manager.update_repository = Mock(return_value=True)

        result = manager.get_saidata("apache", force_update=True)

        assert result == mock_saidata
        manager.update_repository.assert_called_once_with(force=True)

    def test_get_saidata_not_found_retry(self, manager):
        """Test saidata not found with retry logic."""
        # Mock the loader
        manager.saidata_loader.load_saidata = Mock(
            side_effect=[SaidataNotFoundError("Not found", "apache"), Mock(spec=SaiData)]
        )

        # Mock successful update and retry conditions
        manager.update_repository = Mock(return_value=True)
        manager._should_retry_with_update = Mock(return_value=True)
        manager._should_update_repository = Mock(return_value=False)  # Don't update initially

        result = manager.get_saidata("apache")

        assert result is not None
        assert manager.saidata_loader.load_saidata.call_count == 2
        # Should be called once with force=True during retry
        manager.update_repository.assert_called_with(force=True)

    def test_update_repository_offline_mode(self, manager):
        """Test update repository in offline mode."""
        manager.config.saidata_offline_mode = True
        manager.repository_path.mkdir(parents=True, exist_ok=True)

        result = manager.update_repository()

        assert result is True

    def test_update_repository_no_update_needed(self, manager):
        """Test update repository when no update is needed."""
        manager._should_update_repository = Mock(return_value=False)

        result = manager.update_repository()

        assert result is True

    @patch("sai.core.saidata_repository_manager.GitRepositoryHandler")
    def test_update_repository_git_success(self, mock_git_handler_class, manager):
        """Test successful repository update with git."""
        # Mock git handler
        mock_git_handler = Mock()
        mock_git_handler.is_git_available.return_value = True
        mock_git_handler_class.return_value = mock_git_handler

        # Mock successful git operation
        manager._update_with_git = Mock(return_value=True)
        manager._should_update_repository = Mock(return_value=True)

        result = manager.update_repository()

        assert result is True
        manager._update_with_git.assert_called_once()

    @patch("sai.core.saidata_repository_manager.GitRepositoryHandler")
    def test_update_repository_git_fallback_to_tarball(self, mock_git_handler_class, manager):
        """Test repository update fallback from git to tarball."""
        # Mock git handler
        mock_git_handler = Mock()
        mock_git_handler.is_git_available.return_value = True
        mock_git_handler_class.return_value = mock_git_handler

        # Mock git failure, tarball success
        manager._update_with_git = Mock(return_value=False)
        manager._update_with_tarball = Mock(return_value=True)
        manager._should_update_repository = Mock(return_value=True)

        result = manager.update_repository()

        assert result is True
        manager._update_with_git.assert_called_once()
        manager._update_with_tarball.assert_called_once()

    def test_update_repository_both_methods_fail(self, manager):
        """Test repository update when both git and tarball fail."""
        manager._should_update_repository = Mock(return_value=True)
        manager._update_with_git = Mock(return_value=False)
        manager._update_with_tarball = Mock(return_value=False)

        result = manager.update_repository()

        assert result is False
        assert manager._repository_status == RepositoryStatus.ERROR

    def test_get_repository_status_available(self, manager):
        """Test repository status when repository is available."""
        # Create repository directory
        manager.repository_path.mkdir(parents=True, exist_ok=True)
        manager._repository_status = RepositoryStatus.AVAILABLE
        manager._is_cache_valid = Mock(return_value=True)

        status = manager.get_repository_status()

        assert status.status == RepositoryStatus.AVAILABLE
        assert status.cache_valid is True
        assert status.is_healthy is True

    def test_get_repository_status_offline_mode(self, manager):
        """Test repository status in offline mode."""
        manager.config.saidata_offline_mode = True

        status = manager.get_repository_status()

        assert status.status == RepositoryStatus.OFFLINE
        assert "offline mode" in status.error_message.lower()

    def test_configure_repository_success(self, manager):
        """Test successful repository configuration."""
        new_url = "https://github.com/newowner/newrepo"

        result = manager.configure_repository(
            url=new_url,
            branch="develop",
            auth_type=RepositoryAuthType.TOKEN,
            auth_data={"token": "test_token"},
        )

        assert result is True
        assert manager.config.saidata_repository_url == new_url
        assert manager.config.saidata_repository_branch == "develop"
        assert manager.config.saidata_repository_auth_type == RepositoryAuthType.TOKEN

    def test_configure_repository_invalid_url(self, manager):
        """Test repository configuration with invalid URL."""
        result = manager.configure_repository(url="invalid-url")

        assert result is False

    def test_configure_repository_url_change_clears_cache(self, manager):
        """Test that changing repository URL clears old cache."""
        # Create existing repository
        manager.repository_path.mkdir(parents=True, exist_ok=True)
        (manager.repository_path / "test_file").touch()

        old_path = manager.repository_path
        new_url = "https://github.com/newowner/newrepo"

        # Mock shutil.rmtree to verify it's called
        with patch("shutil.rmtree") as mock_rmtree:
            result = manager.configure_repository(url=new_url)

            assert result is True
            # Verify that the old repository was removed
            mock_rmtree.assert_called_once_with(old_path)

    def test_cleanup_old_repositories(self, manager, temp_dir):
        """Test cleanup of old repository caches."""
        # Create some old repository directories
        old_repo1 = manager.repository_cache_dir / "old-repo-1"
        old_repo2 = manager.repository_cache_dir / "old-repo-2"
        current_repo = manager.repository_path

        old_repo1.mkdir(parents=True)
        old_repo2.mkdir(parents=True)
        current_repo.mkdir(parents=True)

        # Set old modification times
        old_time = datetime.now() - timedelta(days=10)
        import os

        os.utime(old_repo1, (old_time.timestamp(), old_time.timestamp()))
        os.utime(old_repo2, (old_time.timestamp(), old_time.timestamp()))

        cleanup_count = manager.cleanup_old_repositories(keep_days=7)

        assert cleanup_count == 2
        assert not old_repo1.exists()
        assert not old_repo2.exists()
        assert current_repo.exists()  # Current repo should not be cleaned

    def test_should_update_repository_auto_update_disabled(self, manager):
        """Test should update when auto update is disabled."""
        manager.config.saidata_auto_update = False

        result = manager._should_update_repository()

        assert result is False

    def test_should_update_repository_offline_mode(self, manager):
        """Test should update in offline mode."""
        manager.config.saidata_offline_mode = True

        result = manager._should_update_repository()

        assert result is False

    def test_should_update_repository_no_cache(self, manager):
        """Test should update when no cache exists."""
        result = manager._should_update_repository()

        assert result is True

    def test_should_update_repository_cache_expired(self, manager):
        """Test should update when cache is expired."""
        manager.repository_path.mkdir(parents=True, exist_ok=True)
        manager._is_cache_valid = Mock(return_value=False)

        result = manager._should_update_repository()

        assert result is True

    def test_should_update_repository_recent_check(self, manager):
        """Test should update with recent check."""
        manager.repository_path.mkdir(parents=True, exist_ok=True)
        manager._last_update_check = datetime.now() - timedelta(seconds=30)
        manager._is_cache_valid = Mock(return_value=True)

        result = manager._should_update_repository()

        assert result is False

    def test_is_cache_valid_no_repository(self, manager):
        """Test cache validity when repository doesn't exist."""
        result = manager._is_cache_valid()

        assert result is False

    def test_is_cache_valid_recent_update(self, manager):
        """Test cache validity with recent update."""
        manager.repository_path.mkdir(parents=True, exist_ok=True)
        manager._get_last_update_time = Mock(return_value=datetime.now() - timedelta(seconds=30))

        result = manager._is_cache_valid()

        assert result is True

    def test_is_cache_valid_old_update(self, manager):
        """Test cache validity with old update."""
        manager.repository_path.mkdir(parents=True, exist_ok=True)
        manager._get_last_update_time = Mock(return_value=datetime.now() - timedelta(hours=2))

        result = manager._is_cache_valid()

        assert result is False

    def test_get_last_update_time_git_info(self, manager):
        """Test getting last update time from git info."""
        manager.repository_path.mkdir(parents=True, exist_ok=True)

        test_time = datetime.now() - timedelta(hours=1)
        mock_repo_info = RepositoryInfo(url="test_url", branch="main", last_updated=test_time)

        manager.git_handler.get_repository_info = Mock(return_value=mock_repo_info)

        result = manager._get_last_update_time()

        assert result == test_time

    def test_get_last_update_time_fallback_to_mtime(self, manager):
        """Test getting last update time fallback to directory mtime."""
        manager.repository_path.mkdir(parents=True, exist_ok=True)

        # Mock git handler to return None
        manager.git_handler.get_repository_info = Mock(return_value=None)

        result = manager._get_last_update_time()

        assert result is not None
        assert isinstance(result, datetime)

    def test_update_with_git_clone_new(self, manager):
        """Test git update with new clone."""
        mock_result = GitOperationResult(success=True, message="Success")
        manager.git_handler.clone_repository = Mock(return_value=mock_result)

        result = manager._update_with_git()

        assert result is True
        manager.git_handler.clone_repository.assert_called_once()

    def test_update_with_git_update_existing(self, manager):
        """Test git update with existing repository."""
        manager.repository_path.mkdir(parents=True, exist_ok=True)

        mock_result = GitOperationResult(success=True, message="Success")
        manager.git_handler.update_repository = Mock(return_value=mock_result)

        result = manager._update_with_git()

        assert result is True
        manager.git_handler.update_repository.assert_called_once()

    def test_update_with_git_failure(self, manager):
        """Test git update failure."""
        mock_result = GitOperationResult(success=False, message="Failed")
        manager.git_handler.clone_repository = Mock(return_value=mock_result)

        result = manager._update_with_git()

        assert result is False

    def test_update_with_tarball_success(self, manager):
        """Test successful tarball update."""
        mock_result = TarballOperationResult(success=True, message="Success")
        manager.tarball_handler.download_latest_release = Mock(return_value=mock_result)

        result = manager._update_with_tarball()

        assert result is True
        manager.tarball_handler.download_latest_release.assert_called_once()

    def test_update_with_tarball_removes_existing(self, manager):
        """Test tarball update removes existing repository."""
        manager.repository_path.mkdir(parents=True, exist_ok=True)
        (manager.repository_path / "test_file").touch()

        mock_result = TarballOperationResult(success=True, message="Success")
        manager.tarball_handler.download_latest_release = Mock(return_value=mock_result)

        result = manager._update_with_tarball()

        assert result is True
        # Repository should be recreated by the tarball handler

    def test_update_with_tarball_failure(self, manager):
        """Test tarball update failure."""
        mock_result = TarballOperationResult(success=False, message="Failed")
        manager.tarball_handler.download_latest_release = Mock(return_value=mock_result)

        result = manager._update_with_tarball()

        assert result is False

    def test_mark_update_successful(self, manager):
        """Test marking update as successful."""
        manager._mark_update_successful()

        assert manager._repository_status == RepositoryStatus.AVAILABLE
        assert manager._last_update_check is not None
        assert manager._last_error is None

    def test_mark_update_failed(self, manager):
        """Test marking update as failed."""
        error_msg = "Test error"
        manager._mark_update_failed(error_msg)

        assert manager._repository_status == RepositoryStatus.ERROR
        assert manager._last_update_check is not None
        assert manager._last_error == error_msg

    def test_setup_repository_paths(self, manager):
        """Test setup of repository paths in configuration."""
        manager.config.saidata_paths.copy()
        repo_path = str(manager.repository_path)

        # Remove repo path if it exists
        if repo_path in manager.config.saidata_paths:
            manager.config.saidata_paths.remove(repo_path)

        manager._setup_repository_paths()

        assert manager.config.saidata_paths[0] == repo_path

    def test_should_retry_with_update_no_recent_check(self, manager):
        """Test should retry with update when no recent check."""
        result = manager._should_retry_with_update()

        assert result is True

    def test_should_retry_with_update_recent_check(self, manager):
        """Test should retry with update after recent check."""
        manager._last_update_check = datetime.now() - timedelta(minutes=2)

        result = manager._should_retry_with_update()

        assert result is False

    def test_should_retry_with_update_old_check(self, manager):
        """Test should retry with update after old check."""
        manager._last_update_check = datetime.now() - timedelta(minutes=10)

        result = manager._should_retry_with_update()

        assert result is True


class TestRepositoryHealthCheck:
    """Test cases for RepositoryHealthCheck."""

    def test_is_healthy_available(self):
        """Test is_healthy with available status."""
        health_check = RepositoryHealthCheck(status=RepositoryStatus.AVAILABLE)
        assert health_check.is_healthy is True

    def test_is_healthy_offline(self):
        """Test is_healthy with offline status."""
        health_check = RepositoryHealthCheck(status=RepositoryStatus.OFFLINE)
        assert health_check.is_healthy is True

    def test_is_healthy_error(self):
        """Test is_healthy with error status."""
        health_check = RepositoryHealthCheck(status=RepositoryStatus.ERROR)
        assert health_check.is_healthy is False

    def test_is_healthy_updating(self):
        """Test is_healthy with updating status."""
        health_check = RepositoryHealthCheck(status=RepositoryStatus.UPDATING)
        assert health_check.is_healthy is False

    def test_needs_update_with_update_available(self):
        """Test needs_update when update is available."""
        health_check = RepositoryHealthCheck(
            status=RepositoryStatus.AVAILABLE, update_available=True
        )
        assert health_check.needs_update is True

    def test_needs_update_with_error_status(self):
        """Test needs_update with error status."""
        health_check = RepositoryHealthCheck(status=RepositoryStatus.ERROR)
        assert health_check.needs_update is True

    def test_needs_update_healthy_no_updates(self):
        """Test needs_update when healthy with no updates."""
        health_check = RepositoryHealthCheck(
            status=RepositoryStatus.AVAILABLE, update_available=False
        )
        assert health_check.needs_update is False
