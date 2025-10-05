"""Tests for repository cache functionality."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from sai.core.repository_cache import RepositoryCache, RepositoryMetadata, RepositoryStatus
from sai.models.config import SaiConfig


class TestRepositoryMetadata:
    """Test RepositoryMetadata dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metadata = RepositoryMetadata(
            url="https://github.com/example/repo",
            branch="main",
            local_path=Path("/tmp/repo"),
            last_updated=1234567890.0,
            is_git_repo=True,
            auth_type="ssh",
            size_bytes=1024,
            file_count=10,
        )

        result = metadata.to_dict()

        assert result["url"] == "https://github.com/example/repo"
        assert result["branch"] == "main"
        assert result["local_path"] == "/tmp/repo"
        assert result["last_updated"] == 1234567890.0
        assert result["is_git_repo"] is True
        assert result["auth_type"] == "ssh"
        assert result["size_bytes"] == 1024
        assert result["file_count"] == 10

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "url": "https://github.com/example/repo",
            "branch": "main",
            "local_path": "/tmp/repo",
            "last_updated": 1234567890.0,
            "is_git_repo": True,
            "auth_type": "ssh",
            "size_bytes": 1024,
            "file_count": 10,
        }

        metadata = RepositoryMetadata.from_dict(data)

        assert metadata.url == "https://github.com/example/repo"
        assert metadata.branch == "main"
        assert metadata.local_path == Path("/tmp/repo")
        assert metadata.last_updated == 1234567890.0
        assert metadata.is_git_repo is True
        assert metadata.auth_type == "ssh"
        assert metadata.size_bytes == 1024
        assert metadata.file_count == 10


class TestRepositoryCache:
    """Test RepositoryCache class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config(self, temp_dir):
        """Create test configuration."""
        return SaiConfig(
            cache_directory=temp_dir / "cache",
            cache_enabled=True,
            saidata_update_interval=3600,  # 1 hour
            saidata_repository_cache_dir=temp_dir / "cache" / "repositories",
        )

    @pytest.fixture
    def cache(self, config):
        """Create RepositoryCache instance."""
        return RepositoryCache(config)

    def test_init(self, config, temp_dir):
        """Test RepositoryCache initialization."""
        cache = RepositoryCache(config)

        assert cache.config == config
        assert cache.cache_enabled is True
        assert cache.cache_dir == temp_dir / "cache" / "repositories"
        assert cache.update_interval == 3600
        assert cache.metadata_file == temp_dir / "cache" / "repositories" / ".repository_metadata"

        # Check that cache directory was created
        assert cache.cache_dir.exists()

    def test_init_cache_disabled(self, temp_dir):
        """Test initialization with cache disabled."""
        config = SaiConfig(cache_directory=temp_dir / "cache", cache_enabled=False)

        cache = RepositoryCache(config)

        assert cache.cache_enabled is False

    def test_get_repository_key(self, cache):
        """Test repository key generation."""
        key1 = cache._get_repository_key("https://github.com/example/repo", "main")
        key2 = cache._get_repository_key("https://github.com/example/repo", "develop")
        key3 = cache._get_repository_key("https://github.com/other/repo", "main")

        # Keys should be different for different URLs or branches
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

        # Keys should be consistent
        assert key1 == cache._get_repository_key("https://github.com/example/repo", "main")

    def test_get_repository_path(self, cache):
        """Test repository path generation."""
        path = cache._get_repository_path("https://github.com/example/repo", "main")

        assert isinstance(path, Path)
        assert path.parent == cache.cache_dir
        assert "repo" in str(path)

    def test_calculate_directory_stats_empty(self, cache, temp_dir):
        """Test directory stats calculation for empty directory."""
        test_dir = temp_dir / "empty"
        test_dir.mkdir()

        size, count = cache._calculate_directory_stats(test_dir)

        assert size == 0
        assert count == 0

    def test_calculate_directory_stats_with_files(self, cache, temp_dir):
        """Test directory stats calculation with files."""
        test_dir = temp_dir / "with_files"
        test_dir.mkdir()

        # Create test files
        (test_dir / "file1.txt").write_text("hello")
        (test_dir / "file2.txt").write_text("world")
        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("test")

        size, count = cache._calculate_directory_stats(test_dir)

        assert size > 0
        assert count == 3

    def test_calculate_directory_stats_nonexistent(self, cache, temp_dir):
        """Test directory stats calculation for nonexistent directory."""
        test_dir = temp_dir / "nonexistent"

        size, count = cache._calculate_directory_stats(test_dir)

        assert size == 0
        assert count == 0

    def test_is_repository_valid_no_cache(self, cache):
        """Test repository validity check with no cache."""
        result = cache.is_repository_valid("https://github.com/example/repo")

        assert result is False

    def test_is_repository_valid_cache_disabled(self, temp_dir):
        """Test repository validity check with cache disabled."""
        config = SaiConfig(cache_directory=temp_dir / "cache", cache_enabled=False)
        cache = RepositoryCache(config)

        result = cache.is_repository_valid("https://github.com/example/repo")

        assert result is False

    def test_mark_repository_updated(self, cache):
        """Test marking repository as updated."""
        url = "https://github.com/example/repo"
        branch = "main"

        # Create a fake repository directory
        repo_path = cache._get_repository_path(url, branch)
        repo_path.mkdir(parents=True)
        (repo_path / "test.txt").write_text("test content")

        cache.mark_repository_updated(url, branch, is_git_repo=True, auth_type="ssh")

        # Check that repository is now valid
        assert cache.is_repository_valid(url, branch) is True

        # Check metadata was saved
        assert cache.metadata_file.exists()

    def test_get_repository_path_cached(self, cache):
        """Test getting repository path for cached repository."""
        url = "https://github.com/example/repo"
        branch = "main"

        # Mark repository as updated first
        repo_path = cache._get_repository_path(url, branch)
        repo_path.mkdir(parents=True)
        cache.mark_repository_updated(url, branch)

        # Get cached path
        cached_path = cache.get_repository_path(url, branch)

        assert cached_path == repo_path

    def test_get_repository_path_not_cached(self, cache):
        """Test getting repository path for non-cached repository."""
        url = "https://github.com/example/repo"
        branch = "main"

        cached_path = cache.get_repository_path(url, branch)

        assert cached_path is None

    def test_get_repository_status_cached(self, cache):
        """Test getting repository status for cached repository."""
        url = "https://github.com/example/repo"
        branch = "main"

        # Create and mark repository
        repo_path = cache._get_repository_path(url, branch)
        repo_path.mkdir(parents=True)
        (repo_path / "test.txt").write_text("test content")
        cache.mark_repository_updated(url, branch, is_git_repo=True, auth_type="ssh")

        status = cache.get_repository_status(url, branch)

        assert isinstance(status, RepositoryStatus)
        assert status.url == url
        assert status.branch == branch
        assert status.local_path == repo_path
        assert status.is_git_repo is True
        assert status.exists is True
        assert status.last_updated is not None
        assert status.age_seconds >= 0
        assert status.is_expired is False
        assert status.size_mb > 0
        assert status.file_count == 1

    def test_get_repository_status_not_cached(self, cache):
        """Test getting repository status for non-cached repository."""
        url = "https://github.com/example/repo"
        branch = "main"

        status = cache.get_repository_status(url, branch)

        assert isinstance(status, RepositoryStatus)
        assert status.url == url
        assert status.branch == branch
        assert status.exists is False
        assert status.last_updated is None
        assert status.age_seconds == float("inf")
        assert status.is_expired is True

    def test_cleanup_expired_repositories(self, cache):
        """Test cleanup of expired repositories."""
        url = "https://github.com/example/repo"
        branch = "main"

        # Create repository and mark as updated with old timestamp
        repo_path = cache._get_repository_path(url, branch)
        repo_path.mkdir(parents=True)
        (repo_path / "test.txt").write_text("test content")

        # Manually create expired metadata
        repositories = {
            cache._get_repository_key(url, branch): RepositoryMetadata(
                url=url,
                branch=branch,
                local_path=repo_path,
                last_updated=time.time() - 7200,  # 2 hours ago (expired)
                is_git_repo=True,
                size_bytes=100,
                file_count=1,
            )
        }
        cache._save_metadata(repositories)

        # Cleanup expired repositories
        cleaned_count = cache.cleanup_expired_repositories()

        assert cleaned_count == 1
        assert not repo_path.exists()

    def test_cleanup_invalid_repositories(self, cache):
        """Test cleanup of invalid repositories."""
        url = "https://github.com/example/repo"
        branch = "main"

        # Create metadata for non-existent repository
        repo_path = cache._get_repository_path(url, branch)
        repositories = {
            cache._get_repository_key(url, branch): RepositoryMetadata(
                url=url,
                branch=branch,
                local_path=repo_path,
                last_updated=time.time(),
                is_git_repo=True,
                size_bytes=100,
                file_count=1,
            )
        }
        cache._save_metadata(repositories)

        # Cleanup invalid repositories
        cleaned_count = cache.cleanup_invalid_repositories()

        assert cleaned_count == 1

        # Check metadata was cleaned
        metadata = cache._load_metadata()
        assert len(metadata) == 0

    def test_cleanup_old_repositories(self, cache):
        """Test cleanup of old repositories."""
        url = "https://github.com/example/repo"
        branch = "main"

        # Create repository and mark as updated with old timestamp
        repo_path = cache._get_repository_path(url, branch)
        repo_path.mkdir(parents=True)
        (repo_path / "test.txt").write_text("test content")

        # Manually create old metadata (31 days ago)
        old_timestamp = time.time() - (31 * 24 * 3600)
        repositories = {
            cache._get_repository_key(url, branch): RepositoryMetadata(
                url=url,
                branch=branch,
                local_path=repo_path,
                last_updated=old_timestamp,
                is_git_repo=True,
                size_bytes=100,
                file_count=1,
            )
        }
        cache._save_metadata(repositories)

        # Cleanup old repositories (max age 30 days)
        cleaned_count = cache.cleanup_old_repositories(max_age_days=30)

        assert cleaned_count == 1
        assert not repo_path.exists()

    def test_get_all_repositories(self, cache):
        """Test getting all cached repositories."""
        # Create multiple repositories
        repos = [
            ("https://github.com/example/repo1", "main"),
            ("https://github.com/example/repo2", "develop"),
        ]

        for url, branch in repos:
            repo_path = cache._get_repository_path(url, branch)
            repo_path.mkdir(parents=True)
            (repo_path / "test.txt").write_text("test")
            cache.mark_repository_updated(url, branch)

        all_repos = cache.get_all_repositories()

        assert len(all_repos) == 2
        assert all(isinstance(repo, RepositoryStatus) for repo in all_repos)

        # Check sorting by URL then branch
        urls = [repo.url for repo in all_repos]
        assert urls == sorted(urls)

    def test_get_cache_status(self, cache):
        """Test getting cache status."""
        # Create a repository
        url = "https://github.com/example/repo"
        branch = "main"
        repo_path = cache._get_repository_path(url, branch)
        repo_path.mkdir(parents=True)
        (repo_path / "test.txt").write_text("test content")
        cache.mark_repository_updated(url, branch)

        status = cache.get_cache_status()

        assert isinstance(status, dict)
        assert "cache_enabled" in status
        assert "cache_directory" in status
        assert "total_repositories" in status
        assert "total_cache_size_bytes" in status
        assert "total_cache_size_mb" in status
        assert "repositories" in status

        assert status["cache_enabled"] is True
        assert status["total_repositories"] == 1
        assert status["total_cache_size_bytes"] > 0
        assert len(status["repositories"]) == 1

    def test_clear_repository_cache(self, cache):
        """Test clearing specific repository cache."""
        url = "https://github.com/example/repo"
        branch = "main"

        # Create repository
        repo_path = cache._get_repository_path(url, branch)
        repo_path.mkdir(parents=True)
        (repo_path / "test.txt").write_text("test")
        cache.mark_repository_updated(url, branch)

        # Clear cache
        result = cache.clear_repository_cache(url, branch)

        assert result is True
        assert not repo_path.exists()
        assert not cache.is_repository_valid(url, branch)

    def test_clear_repository_cache_not_exists(self, cache):
        """Test clearing non-existent repository cache."""
        url = "https://github.com/example/nonexistent"
        branch = "main"

        result = cache.clear_repository_cache(url, branch)

        assert result is False

    def test_clear_all_repository_cache(self, cache):
        """Test clearing all repository caches."""
        # Create multiple repositories
        repos = [
            ("https://github.com/example/repo1", "main"),
            ("https://github.com/example/repo2", "develop"),
        ]

        for url, branch in repos:
            repo_path = cache._get_repository_path(url, branch)
            repo_path.mkdir(parents=True)
            (repo_path / "test.txt").write_text("test")
            cache.mark_repository_updated(url, branch)

        # Clear all caches
        cleared_count = cache.clear_all_repository_cache()

        assert cleared_count == 2

        # Check all repositories are gone
        for url, branch in repos:
            assert not cache.is_repository_valid(url, branch)

    def test_metadata_persistence(self, cache):
        """Test that metadata persists across cache instances."""
        url = "https://github.com/example/repo"
        branch = "main"

        # Create repository with first cache instance
        repo_path = cache._get_repository_path(url, branch)
        repo_path.mkdir(parents=True)
        (repo_path / "test.txt").write_text("test")
        cache.mark_repository_updated(url, branch)

        # Create new cache instance with same config
        cache2 = RepositoryCache(cache.config)

        # Check that repository is still valid
        assert cache2.is_repository_valid(url, branch) is True

    def test_repository_expiration(self, cache):
        """Test repository expiration based on update interval."""
        url = "https://github.com/example/repo"
        branch = "main"

        # Create repository
        repo_path = cache._get_repository_path(url, branch)
        repo_path.mkdir(parents=True)
        (repo_path / "test.txt").write_text("test")

        # Manually create expired metadata
        old_timestamp = time.time() - 7200  # 2 hours ago
        repositories = {
            cache._get_repository_key(url, branch): RepositoryMetadata(
                url=url,
                branch=branch,
                local_path=repo_path,
                last_updated=old_timestamp,
                is_git_repo=True,
                size_bytes=100,
                file_count=1,
            )
        }
        cache._save_metadata(repositories)

        # Check that repository is expired (update interval is 1 hour)
        assert cache.is_repository_valid(url, branch) is False

        status = cache.get_repository_status(url, branch)
        assert status.is_expired is True

    @patch("sai.core.repository_cache.logger")
    def test_error_handling_metadata_load(self, mock_logger, cache, temp_dir):
        """Test error handling when loading corrupted metadata."""
        # Create corrupted metadata file
        cache.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        cache.metadata_file.write_text("invalid json")

        # Try to load metadata
        metadata = cache._load_metadata()

        assert metadata == {}
        mock_logger.warning.assert_called()

    @patch("sai.core.repository_cache.logger")
    def test_error_handling_metadata_save(self, mock_logger, cache, temp_dir):
        """Test error handling when saving metadata fails."""
        # Create a scenario where saving fails by using an invalid path
        original_metadata_file = cache.metadata_file
        cache.metadata_file = Path("/invalid/path/that/does/not/exist/.repository_metadata")

        try:
            repositories = {
                "test": RepositoryMetadata(
                    url="https://github.com/example/repo",
                    branch="main",
                    local_path=Path("/tmp/test"),
                    last_updated=time.time(),
                    is_git_repo=True,
                )
            }
            cache._save_metadata(repositories)

            mock_logger.error.assert_called()
        finally:
            # Restore original metadata file path
            cache.metadata_file = original_metadata_file

    def test_cache_disabled_operations(self, temp_dir):
        """Test that operations work correctly when cache is disabled."""
        config = SaiConfig(cache_directory=temp_dir / "cache", cache_enabled=False)
        cache = RepositoryCache(config)

        url = "https://github.com/example/repo"
        branch = "main"

        # All operations should return appropriate values for disabled cache
        assert cache.is_repository_valid(url, branch) is False
        assert cache.get_repository_path(url, branch) is None
        assert cache.cleanup_expired_repositories() == 0
        assert cache.cleanup_invalid_repositories() == 0
        assert cache.cleanup_old_repositories() == 0
        assert cache.clear_repository_cache(url, branch) is False
        assert cache.clear_all_repository_cache() == 0

        # mark_repository_updated should not fail but do nothing
        cache.mark_repository_updated(url, branch)  # Should not raise exception
