"""Tests for repository component error handling and edge cases."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sai.core.git_repository_handler import GitRepositoryHandler
from sai.core.repository_cache import RepositoryCache
from sai.core.saidata_repository_manager import RepositoryStatus, SaidataRepositoryManager
from sai.core.tarball_repository_handler import TarballRepositoryHandler
from sai.models.config import RepositoryAuthType, SaiConfig
from sai.utils.errors import (
    SecurityError,
)


class TestGitRepositoryErrorHandling:
    """Test error handling in GitRepositoryHandler."""

    @pytest.fixture
    def handler(self):
        return GitRepositoryHandler(timeout=30, max_retries=2)

    @pytest.fixture
    def temp_dir(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_network_error_handling(self, handler):
        """Test handling of network errors during git operations."""
        with patch("subprocess.run") as mock_run:
            # Simulate network error
            mock_run.side_effect = subprocess.CalledProcessError(
                128,
                ["git", "clone"],
                stderr="fatal: unable to access 'https://github.com/test/repo.git/': Could not resolve host",
            )

            result = handler.clone_repository(
                "https://github.com/test/repo.git", Path("/tmp/test_repo")
            )

            assert not result.success
            assert "network" in result.message.lower() or "resolve host" in result.message.lower()

    def test_authentication_error_handling(self, handler):
        """Test handling of authentication errors."""
        with patch("subprocess.run") as mock_run:
            # Simulate authentication error
            mock_run.side_effect = subprocess.CalledProcessError(
                128, ["git", "clone"], stderr="fatal: Authentication failed"
            )

            result = handler.clone_repository(
                "git@github.com:private/repo.git",
                Path("/tmp/test_repo"),
                auth_type=RepositoryAuthType.SSH,
                auth_data={"ssh_key_path": "/nonexistent/key"},
            )

            assert not result.success
            assert "authentication" in result.message.lower()

    def test_disk_space_error_handling(self, handler, temp_dir):
        """Test handling of disk space errors."""
        with patch("subprocess.run") as mock_run:
            # Simulate disk space error
            mock_run.side_effect = subprocess.CalledProcessError(
                128, ["git", "clone"], stderr="fatal: write error: No space left on device"
            )

            result = handler.clone_repository("https://github.com/test/repo.git", temp_dir / "repo")

            assert not result.success
            assert "space" in result.message.lower()

    def test_corrupted_repository_handling(self, handler, temp_dir):
        """Test handling of corrupted repositories."""
        # Create a fake corrupted repository
        repo_dir = temp_dir / "corrupted_repo"
        repo_dir.mkdir()
        git_dir = repo_dir / ".git"
        git_dir.mkdir()

        # Create corrupted git files
        (git_dir / "HEAD").write_text("invalid content")
        (git_dir / "config").write_text("corrupted config")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                128,
                ["git", "status"],
                stderr="fatal: not a git repository (or any of the parent directories): .git",
            )

            result = handler.get_repository_info(repo_dir)

            assert result is None

    def test_permission_error_handling(self, handler, temp_dir):
        """Test handling of permission errors."""
        # Create directory with restricted permissions
        restricted_dir = temp_dir / "restricted"
        restricted_dir.mkdir()
        restricted_dir.chmod(0o000)

        try:
            result = handler.clone_repository(
                "https://github.com/test/repo.git", restricted_dir / "repo"
            )

            assert not result.success
            assert "permission" in result.message.lower()
        finally:
            # Restore permissions for cleanup
            restricted_dir.chmod(0o755)

    def test_git_command_injection_protection(self, handler):
        """Test protection against command injection in git operations."""
        malicious_urls = [
            "https://github.com/test/repo.git; rm -rf /",
            "https://github.com/test/repo.git && malicious_command",
            "https://github.com/test/repo.git | evil_script",
        ]

        for url in malicious_urls:
            result = handler._validate_repository_url(url)
            assert not result, f"Should reject malicious URL: {url}"

    def test_timeout_handling_with_cleanup(self, handler, temp_dir):
        """Test timeout handling with proper cleanup."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(["git", "clone"], 30)

            result = handler.clone_repository(
                "https://github.com/large/repo.git", temp_dir / "repo"
            )

            assert not result.success
            assert "timeout" in result.message.lower()
            # Partial clone directory should be cleaned up
            assert not (temp_dir / "repo").exists()


class TestTarballRepositoryErrorHandling:
    """Test error handling in TarballRepositoryHandler."""

    @pytest.fixture
    def handler(self):
        return TarballRepositoryHandler(timeout=30, max_retries=2)

    @pytest.fixture
    def temp_dir(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_http_error_handling(self, handler):
        """Test handling of various HTTP errors."""
        import urllib.error

        error_codes = [
            (404, "Not Found"),
            (403, "Forbidden"),
            (500, "Internal Server Error"),
            (503, "Service Unavailable"),
        ]

        for code, msg in error_codes:
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = urllib.error.HTTPError(
                    url="https://api.github.com/repos/test/repo/releases/latest",
                    code=code,
                    msg=msg,
                    hdrs={},
                    fp=None,
                )

                result = handler.get_latest_release_info("https://github.com/test/repo")

                assert not result.success
                assert str(code) in result.message

    def test_malformed_json_handling(self, handler):
        """Test handling of malformed JSON responses."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read.return_value = b"invalid json content {"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = handler.get_latest_release_info("https://github.com/test/repo")

            assert not result.success
            assert "json" in result.message.lower() or "parse" in result.message.lower()

    def test_checksum_mismatch_handling(self, handler, temp_dir):
        """Test handling of checksum mismatches."""
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")

        # Use wrong checksum
        wrong_checksum = "0" * 64

        result = handler._verify_checksum(test_file, wrong_checksum, "sha256")

        assert not result.success
        assert "checksum" in result.message.lower()
        assert "mismatch" in result.message.lower()

    def test_archive_extraction_errors(self, handler, temp_dir):
        """Test handling of archive extraction errors."""
        # Create invalid archive
        invalid_archive = temp_dir / "invalid.tar.gz"
        invalid_archive.write_text("not a valid archive")

        extract_dir = temp_dir / "extract"

        with pytest.raises(Exception):
            handler._extract_tar(invalid_archive, extract_dir)

    def test_download_interruption_handling(self, handler, temp_dir):
        """Test handling of download interruptions."""
        target_file = temp_dir / "interrupted_download.tar.gz"

        with patch("urllib.request.urlretrieve") as mock_retrieve:
            # Simulate download interruption
            mock_retrieve.side_effect = ConnectionError("Connection lost")

            result = handler._download_file_with_retry(
                "https://example.com/file.tar.gz", target_file, None, None, None
            )

            assert not result.success
            assert "connection" in result.message.lower()

    def test_security_validation_errors(self, handler, temp_dir):
        """Test security validation error handling."""
        # Test path traversal in archive
        malicious_archive = temp_dir / "malicious.tar.gz"

        import tarfile

        with tarfile.open(malicious_archive, "w:gz") as tar:
            # Add file with path traversal
            import io

            tarinfo = tarfile.TarInfo(name="../../../etc/passwd")
            tarinfo.size = 0
            tar.addfile(tarinfo, io.BytesIO(b""))

        extract_dir = temp_dir / "extract"

        with pytest.raises(SecurityError):
            handler._extract_tar(malicious_archive, extract_dir)


class TestRepositoryManagerErrorHandling:
    """Test error handling in SaidataRepositoryManager."""

    @pytest.fixture
    def config(self, temp_dir):
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
        return SaidataRepositoryManager(config)

    @pytest.fixture
    def temp_dir(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_repository_unavailable_handling(self, manager):
        """Test handling when repository is completely unavailable."""
        # Mock both git and tarball failures
        manager._update_with_git = Mock(return_value=False)
        manager._update_with_tarball = Mock(return_value=False)
        manager._should_update_repository = Mock(return_value=True)

        result = manager.update_repository()

        assert not result
        assert manager._repository_status == RepositoryStatus.ERROR

    def test_saidata_not_found_handling(self, manager):
        """Test handling when saidata is not found."""
        from sai.core.saidata_loader import SaidataNotFoundError

        # Mock saidata not found
        manager.saidata_loader.load_saidata = Mock(
            side_effect=SaidataNotFoundError("Not found", "nonexistent_software")
        )
        manager._should_retry_with_update = Mock(return_value=False)

        with pytest.raises(SaidataNotFoundError):
            manager.get_saidata("nonexistent_software")

    def test_configuration_validation_errors(self, manager):
        """Test handling of configuration validation errors."""
        # Test invalid repository URL
        result = manager.configure_repository(url="invalid-url")
        assert not result

        # Test invalid branch name
        result = manager.configure_repository(
            url="https://github.com/test/repo", branch="invalid/branch/name"
        )
        assert not result

    def test_cache_corruption_recovery(self, manager, temp_dir):
        """Test recovery from cache corruption."""
        # Corrupt the repository cache
        cache_dir = manager.repository_cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create corrupted cache files
        (cache_dir / "corrupted_file").write_text("corrupted content")

        # Should handle corruption and continue
        result = manager.update_repository(force=True)
        # Result depends on mocked handlers, but should not crash
        assert isinstance(result, bool)

    def test_concurrent_update_conflicts(self, manager):
        """Test handling of concurrent update conflicts."""
        import threading

        results = []

        def concurrent_update():
            try:
                # Mock successful update
                with patch.object(manager, "_update_with_git", return_value=True):
                    result = manager.update_repository()
                    results.append(result)
            except Exception:
                results.append(False)

        # Start multiple concurrent updates
        threads = []
        for i in range(3):
            thread = threading.Thread(target=concurrent_update)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # At least one should succeed, others should handle conflicts gracefully
        assert any(results)

    def test_offline_mode_fallback(self, manager, temp_dir):
        """Test fallback to offline mode when network is unavailable."""
        # Create cached repository
        repo_path = manager.repository_path
        repo_path.mkdir(parents=True)
        (repo_path / "test_file").write_text("cached content")

        # Simulate network unavailable
        with patch("sai.utils.system.check_network_connectivity", return_value=False):
            manager._handle_network_state_change(online=False)

            # Should use cached data
            result = manager.update_repository()
            assert result is True  # Should succeed using cache

    def test_repository_integrity_validation_failure(self, manager, temp_dir):
        """Test handling of repository integrity validation failures."""
        # Create repository with integrity issues
        repo_path = manager.repository_path
        repo_path.mkdir(parents=True)

        # Create invalid saidata structure
        (repo_path / "invalid_structure").write_text("not saidata")

        with patch.object(manager, "_validate_repository_integrity", return_value=False):
            manager.update_repository()
            # Should handle integrity failure
            assert manager._repository_status == RepositoryStatus.ERROR


class TestRepositoryCacheErrorHandling:
    """Test error handling in RepositoryCache."""

    @pytest.fixture
    def config(self, temp_dir):
        return SaiConfig(
            cache_directory=temp_dir / "cache", cache_enabled=True, saidata_update_interval=3600
        )

    @pytest.fixture
    def cache(self, config):
        return RepositoryCache(config)

    @pytest.fixture
    def temp_dir(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_metadata_file_corruption_handling(self, cache):
        """Test handling of metadata file corruption."""
        # Create corrupted metadata file
        cache.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        cache.metadata_file.write_text("corrupted json {")

        # Should handle corruption gracefully
        metadata = cache._load_metadata()
        assert metadata == {}

        # Should be able to save new metadata
        cache.mark_repository_updated("https://github.com/test/repo", "main")
        assert cache.is_repository_valid("https://github.com/test/repo", "main")

    def test_permission_denied_handling(self, cache, temp_dir):
        """Test handling of permission denied errors."""
        # Create directory with restricted permissions
        restricted_cache_dir = temp_dir / "restricted_cache"
        restricted_cache_dir.mkdir()
        restricted_cache_dir.chmod(0o000)

        try:
            # Update cache config to use restricted directory
            cache.cache_dir = restricted_cache_dir

            # Should handle permission errors gracefully
            result = cache.mark_repository_updated("https://github.com/test/repo", "main")
            # Should not crash, may return False or handle gracefully
            assert isinstance(result, (bool, type(None)))
        finally:
            # Restore permissions for cleanup
            restricted_cache_dir.chmod(0o755)

    def test_disk_full_handling(self, cache, temp_dir):
        """Test handling of disk full errors."""
        with patch("builtins.open", side_effect=OSError("No space left on device")):
            # Should handle disk full errors gracefully
            result = cache.mark_repository_updated("https://github.com/test/repo", "main")
            # Should not crash
            assert isinstance(result, (bool, type(None)))

    def test_concurrent_access_conflicts(self, cache):
        """Test handling of concurrent access conflicts."""
        import threading

        results = []

        def concurrent_cache_operation(repo_id):
            try:
                url = f"https://github.com/test/repo{repo_id}"
                cache.mark_repository_updated(url, "main")
                is_valid = cache.is_repository_valid(url, "main")
                results.append(is_valid)
            except Exception:
                results.append(False)

        # Start multiple concurrent operations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_cache_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Should handle concurrent access without corruption
        assert len(results) == 5
        # Most operations should succeed
        assert sum(results) >= 3

    def test_cache_size_calculation_errors(self, cache, temp_dir):
        """Test handling of errors during cache size calculation."""
        # Create repository with inaccessible files
        repo_path = cache._get_repository_path("https://github.com/test/repo", "main")
        repo_path.mkdir(parents=True)

        inaccessible_file = repo_path / "inaccessible"
        inaccessible_file.write_text("content")
        inaccessible_file.chmod(0o000)

        try:
            # Should handle permission errors during size calculation
            size, count = cache._calculate_directory_stats(repo_path)
            # Should return some values without crashing
            assert isinstance(size, int)
            assert isinstance(count, int)
        finally:
            # Restore permissions for cleanup
            inaccessible_file.chmod(0o644)

    def test_cleanup_operation_errors(self, cache, temp_dir):
        """Test handling of errors during cleanup operations."""
        # Create repository that cannot be deleted
        repo_path = cache._get_repository_path("https://github.com/test/repo", "main")
        repo_path.mkdir(parents=True)

        # Create file that cannot be deleted (simulate system file)
        protected_file = repo_path / "protected"
        protected_file.write_text("protected content")

        with patch("shutil.rmtree", side_effect=PermissionError("Cannot delete")):
            # Should handle cleanup errors gracefully
            cleaned_count = cache.cleanup_expired_repositories()
            # Should not crash, may return 0 or partial count
            assert isinstance(cleaned_count, int)
