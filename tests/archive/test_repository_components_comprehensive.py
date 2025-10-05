"""Comprehensive unit tests for repository components.

This module provides enhanced test coverage for all repository components,
focusing on edge cases, error conditions, and integration scenarios.
"""

import json
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sai.core.git_repository_handler import GitOperationResult, GitRepositoryHandler
from sai.core.repository_cache import RepositoryCache, RepositoryMetadata
from sai.core.saidata_path import HierarchicalPathResolver, SaidataPath
from sai.core.saidata_repository_manager import (
    RepositoryStatus,
    SaidataRepositoryManager,
)
from sai.core.tarball_repository_handler import (
    TarballOperationResult,
    TarballRepositoryHandler,
)
from sai.models.config import SaiConfig
from sai.models.saidata import SaiData
from sai.utils.errors import (
    SecurityError,
)


class TestGitRepositoryHandlerComprehensive:
    """Comprehensive tests for GitRepositoryHandler."""

    @pytest.fixture
    def handler(self):
        """Create GitRepositoryHandler instance."""
        return GitRepositoryHandler(timeout=30, max_retries=2)

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_git_handler_initialization_with_custom_params(self, handler):
        """Test GitRepositoryHandler initialization with custom parameters."""
        custom_handler = GitRepositoryHandler(
            timeout=60, max_retries=5, retry_delay=2.0, shallow_clone_depth=10
        )

        assert custom_handler.timeout == 60
        assert custom_handler.max_retries == 5
        assert custom_handler.retry_delay == 2.0
        assert custom_handler.shallow_clone_depth == 10

    @patch("subprocess.run")
    def test_git_version_detection(self, mock_run, handler):
        """Test git version detection and caching."""
        mock_run.return_value = Mock(returncode=0, stdout="git version 2.39.1", stderr="")

        # First call should execute subprocess
        version = handler.get_git_version()
        assert version == "2.39.1"
        mock_run.assert_called_once()

        # Second call should use cached version
        mock_run.reset_mock()
        version = handler.get_git_version()
        assert version == "2.39.1"
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_git_version_detection_failure(self, mock_run, handler):
        """Test git version detection failure handling."""
        mock_run.side_effect = FileNotFoundError("git not found")

        version = handler.get_git_version()
        assert version is None

    def test_repository_url_validation(self, handler):
        """Test repository URL validation."""
        valid_urls = [
            "https://github.com/user/repo.git",
            "git@github.com:user/repo.git",
            "https://gitlab.com/user/repo",
            "ssh://git@server.com/repo.git",
        ]

        for url in valid_urls:
            assert handler._validate_repository_url(url) is True

        invalid_urls = ["", "not-a-url", "ftp://invalid.com/repo", "javascript:alert('xss')"]

        for url in invalid_urls:
            assert handler._validate_repository_url(url) is False

    @patch.object(GitRepositoryHandler, "_execute_git_command")
    def test_repository_integrity_verification(self, mock_execute, handler, temp_dir):
        """Test repository integrity verification."""
        repo_dir = temp_dir / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        # Mock successful integrity check
        mock_execute.side_effect = [
            GitOperationResult(success=True, stdout="clean"),  # status check
            GitOperationResult(success=True, stdout="origin/main"),  # remote check
            GitOperationResult(success=True, stdout="abc123"),  # commit hash
        ]

        result = handler._verify_repository_integrity(repo_dir)
        assert result is True

        # Mock failed integrity check
        mock_execute.side_effect = [
            GitOperationResult(success=False, stderr="fatal: not a git repository")
        ]

        result = handler._verify_repository_integrity(repo_dir)
        assert result is False

    def test_ssh_key_validation(self, handler, temp_dir):
        """Test SSH key validation."""
        # Valid SSH key
        valid_key = temp_dir / "valid_key"
        valid_key.write_text(
            "-----BEGIN OPENSSH PRIVATE KEY-----\nfake key content\n-----END OPENSSH PRIVATE KEY-----"
        )
        valid_key.chmod(0o600)

        assert handler._validate_ssh_key(str(valid_key)) is True

        # Invalid permissions
        invalid_perms_key = temp_dir / "invalid_perms"
        invalid_perms_key.write_text("fake key")
        invalid_perms_key.chmod(0o644)

        assert handler._validate_ssh_key(str(invalid_perms_key)) is False

        # Non-existent key
        assert handler._validate_ssh_key("/nonexistent/key") is False

    @patch.object(GitRepositoryHandler, "_execute_git_command_with_retry")
    def test_clone_with_progress_callback(self, mock_execute, handler, temp_dir):
        """Test repository cloning with progress callback."""
        progress_calls = []

        def progress_callback(message):
            progress_calls.append(message)

        mock_execute.return_value = GitOperationResult(
            success=True,
            message="Success",
            stdout="Cloning into 'repo'...\nReceiving objects: 100% (10/10)",
        )

        result = handler.clone_repository(
            "https://github.com/test/repo.git",
            temp_dir / "repo",
            progress_callback=progress_callback,
        )

        assert result.success is True
        assert len(progress_calls) > 0

    def test_authentication_data_sanitization(self, handler):
        """Test that authentication data is properly sanitized in logs."""
        auth_data = {
            "token": "secret_token_123",
            "password": "secret_password",
            "ssh_key_path": "/path/to/key",
        }

        sanitized = handler._sanitize_auth_data(auth_data)

        assert sanitized["token"] == "***"
        assert sanitized["password"] == "***"
        assert sanitized["ssh_key_path"] == "/path/to/key"  # Path should not be sanitized

    @patch("subprocess.run")
    def test_command_execution_with_environment_isolation(self, mock_run, handler):
        """Test that git commands run with proper environment isolation."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        handler._execute_git_command(["git", "status"], env={"TEST_VAR": "test"})

        # Verify environment was passed to subprocess
        call_kwargs = mock_run.call_args[1]
        assert "env" in call_kwargs
        assert call_kwargs["env"]["TEST_VAR"] == "test"

    def test_concurrent_operations_handling(self, handler, temp_dir):
        """Test handling of concurrent git operations."""
        import threading

        results = []

        def clone_operation():
            with patch.object(handler, "_execute_git_command_with_retry") as mock_execute:
                mock_execute.return_value = GitOperationResult(success=True, message="Success")
                result = handler.clone_repository(
                    "https://github.com/test/repo.git",
                    temp_dir / f"repo_{threading.current_thread().ident}",
                )
                results.append(result.success)

        # Start multiple concurrent operations
        threads = []
        for i in range(3):
            thread = threading.Thread(target=clone_operation)
            threads.append(thread)
            thread.start()

        # Wait for all operations to complete
        for thread in threads:
            thread.join()

        # All operations should succeed
        assert all(results)
        assert len(results) == 3


class TestTarballRepositoryHandlerComprehensive:
    """Comprehensive tests for TarballRepositoryHandler."""

    @pytest.fixture
    def handler(self):
        """Create TarballRepositoryHandler instance."""
        return TarballRepositoryHandler(timeout=30, max_retries=2)

    def test_github_api_rate_limit_handling(self, handler):
        """Test GitHub API rate limit handling."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock rate limit response
            mock_response = Mock()
            mock_response.status = 403
            mock_response.read.return_value = json.dumps(
                {
                    "message": "API rate limit exceeded",
                    "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting",
                }
            ).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = handler.get_latest_release_info("https://github.com/test/repo")

            assert not result.success
            assert "rate limit" in result.message.lower()

    def test_release_asset_selection_priority(self, handler):
        """Test release asset selection priority logic."""
        release_data = {
            "tag_name": "v1.0.0",
            "name": "Release 1.0.0",
            "assets": [
                {
                    "name": "release.zip",
                    "browser_download_url": "https://example.com/release.zip",
                    "size": 1000000,
                },
                {
                    "name": "release.tar.gz",
                    "browser_download_url": "https://example.com/release.tar.gz",
                    "size": 900000,
                },
                {
                    "name": "release.tar.xz",
                    "browser_download_url": "https://example.com/release.tar.xz",
                    "size": 800000,
                },
            ],
        }

        result = handler._parse_release_data(release_data)

        # Should prefer tar.xz (highest compression)
        assert result.download_url == "https://example.com/release.tar.xz"
        assert result.size == 800000

    def test_download_resume_capability(self, handler, temp_dir):
        """Test download resume capability for interrupted downloads."""
        target_file = temp_dir / "partial_download.tar.gz"

        # Create partial file
        partial_content = b"partial content"
        target_file.write_bytes(partial_content)

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock server supporting range requests
            mock_response = Mock()
            mock_response.status = 206  # Partial Content
            mock_response.headers = {"Content-Range": "bytes 15-1023/1024"}
            mock_response.read.return_value = b"remaining content"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = handler._download_with_resume("https://example.com/file.tar.gz", target_file)

            assert result.success
            # File should contain both partial and remaining content
            content = target_file.read_bytes()
            assert content.startswith(partial_content)

    def test_checksum_verification_algorithms(self, handler, temp_dir):
        """Test various checksum verification algorithms."""
        test_file = temp_dir / "test_file.txt"
        test_content = b"test content for checksum verification"
        test_file.write_bytes(test_content)

        # Test different algorithms
        algorithms = {
            "md5": "5d41402abc4b2a76b9719d911017c592",  # md5 of "hello"
            "sha1": "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d",  # sha1 of "hello"
            "sha256": "2cf24dba4f21d4288094e9b9b6e13c6b8847ad1c4d8b7c8b8b8b8b8b8b8b8b8b",  # placeholder
            "sha512": "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca72323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e5c3adef46f73bcdec043",  # placeholder
        }

        for algorithm, expected_checksum in algorithms.items():
            # Calculate actual checksum
            import hashlib

            hasher = hashlib.new(algorithm)
            hasher.update(test_content)
            actual_checksum = hasher.hexdigest()

            result = handler._verify_checksum(test_file, actual_checksum, algorithm)
            assert result.success

    def test_archive_bomb_protection(self, handler, temp_dir):
        """Test protection against archive bombs (zip bombs)."""
        malicious_archive = temp_dir / "bomb.zip"

        # Create a zip file with excessive compression ratio
        with zipfile.ZipFile(malicious_archive, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add a file that would expand to a huge size
            large_content = b"0" * 1000000  # 1MB of zeros (highly compressible)
            zf.writestr("bomb.txt", large_content)

        extract_dir = temp_dir / "extract"

        # Should detect and prevent extraction of suspicious archives
        with pytest.raises(SecurityError, match="archive bomb"):
            handler._extract_zip_with_protection(malicious_archive, extract_dir)

    def test_network_timeout_handling(self, handler):
        """Test network timeout handling during downloads."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            import socket

            mock_urlopen.side_effect = socket.timeout("Connection timed out")

            result = handler._download_file_with_retry(
                "https://example.com/slow-file.tar.gz", Path("/tmp/test.tar.gz"), None, None, None
            )

            assert not result.success
            assert "timeout" in result.message.lower()

    def test_content_type_validation(self, handler):
        """Test content type validation for downloaded files."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock response with wrong content type
            mock_response = Mock()
            mock_response.status = 200
            mock_response.headers = {"Content-Type": "text/html"}
            mock_response.read.return_value = b"<html>Not Found</html>"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = handler._validate_download_content_type("https://example.com/file.tar.gz")

            assert not result.success
            assert "content type" in result.message.lower()

    def test_bandwidth_limiting(self, handler, temp_dir):
        """Test bandwidth limiting during downloads."""
        target_file = temp_dir / "limited_download.tar.gz"

        # Mock download with bandwidth limiting
        with patch.object(handler, "_download_with_bandwidth_limit") as mock_download:
            mock_download.return_value = TarballOperationResult(
                success=True, message="Download completed with bandwidth limiting"
            )

            result = handler.download_with_bandwidth_limit(
                "https://example.com/file.tar.gz", target_file, max_bandwidth_mbps=1.0
            )

            assert result.success
            mock_download.assert_called_once()


class TestSaidataRepositoryManagerComprehensive:
    """Comprehensive tests for SaidataRepositoryManager."""

    @pytest.fixture
    def config(self, temp_dir):
        """Create test configuration."""
        return SaiConfig(
            cache_directory=temp_dir / "cache",
            saidata_repository_url="https://github.com/example42/saidata",
            saidata_repository_branch="main",
            saidata_auto_update=True,
            saidata_update_interval=3600,
            saidata_offline_mode=False,
            saidata_repository_cache_dir=temp_dir / "cache" / "repositories",
        )

    @pytest.fixture
    def manager(self, config):
        """Create SaidataRepositoryManager instance."""
        return SaidataRepositoryManager(config)

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_repository_health_monitoring(self, manager):
        """Test repository health monitoring and alerting."""
        # Mock unhealthy repository
        manager._repository_status = RepositoryStatus.ERROR
        manager._last_error = "Network connectivity issues"
        manager._consecutive_failures = 3

        health_check = manager.get_repository_health()

        assert health_check.status == RepositoryStatus.ERROR
        assert not health_check.is_healthy
        assert health_check.needs_attention
        assert health_check.consecutive_failures == 3

    def test_automatic_recovery_mechanisms(self, manager):
        """Test automatic recovery from repository errors."""
        # Simulate repository corruption
        manager._repository_status = RepositoryStatus.ERROR
        manager._last_error = "Repository integrity check failed"

        with patch.object(manager, "_attempt_repository_recovery") as mock_recovery:
            mock_recovery.return_value = True

            # Trigger recovery
            result = manager.recover_repository()

            assert result is True
            mock_recovery.assert_called_once()
            assert manager._repository_status == RepositoryStatus.AVAILABLE

    def test_repository_migration_handling(self, manager, temp_dir):
        """Test handling of repository URL changes and migration."""
        old_url = "https://github.com/old/repo"
        new_url = "https://github.com/new/repo"

        # Set up old repository
        manager.config.saidata_repository_url = old_url
        old_repo_path = manager.repository_path
        old_repo_path.mkdir(parents=True)
        (old_repo_path / "test_file").write_text("old content")

        # Change to new URL
        result = manager.configure_repository(url=new_url)

        assert result is True
        assert manager.config.saidata_repository_url == new_url
        # Old repository should be cleaned up
        assert not old_repo_path.exists()

    def test_concurrent_access_handling(self, manager):
        """Test handling of concurrent access to repository."""
        import threading

        results = []

        def concurrent_access():
            try:
                # Mock saidata loading
                with patch.object(manager.saidata_loader, "load_saidata") as mock_load:
                    mock_load.return_value = Mock(spec=SaiData)
                    saidata = manager.get_saidata("test_software")
                    results.append(saidata is not None)
            except Exception:
                results.append(False)

        # Start multiple concurrent operations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_access)
            threads.append(thread)
            thread.start()

        # Wait for all operations to complete
        for thread in threads:
            thread.join()

        # All operations should succeed
        assert all(results)
        assert len(results) == 5

    def test_repository_size_monitoring(self, manager, temp_dir):
        """Test monitoring of repository size and cleanup."""
        # Create large repository
        repo_path = manager.repository_path
        repo_path.mkdir(parents=True)

        # Create large files
        for i in range(10):
            large_file = repo_path / f"large_file_{i}.txt"
            large_file.write_text("x" * 1000000)  # 1MB each

        size_info = manager.get_repository_size_info()

        assert size_info["total_size_mb"] >= 10  # At least 10MB
        assert size_info["file_count"] == 10
        assert size_info["needs_cleanup"] is False  # Unless configured threshold is exceeded

    def test_repository_backup_and_restore(self, manager, temp_dir):
        """Test repository backup and restore functionality."""
        # Create repository with content
        repo_path = manager.repository_path
        repo_path.mkdir(parents=True)
        test_file = repo_path / "important_data.yaml"
        test_content = "important: data"
        test_file.write_text(test_content)

        # Create backup
        backup_path = temp_dir / "backup"
        result = manager.create_repository_backup(backup_path)

        assert result is True
        assert (backup_path / "important_data.yaml").exists()

        # Simulate repository corruption
        test_file.unlink()

        # Restore from backup
        result = manager.restore_repository_from_backup(backup_path)

        assert result is True
        assert test_file.exists()
        assert test_file.read_text() == test_content

    def test_network_connectivity_monitoring(self, manager):
        """Test network connectivity monitoring and offline detection."""
        with patch("sai.utils.system.check_network_connectivity") as mock_connectivity:
            # Test online state
            mock_connectivity.return_value = True
            assert manager._is_network_available() is True

            # Test offline state
            mock_connectivity.return_value = False
            assert manager._is_network_available() is False

            # Should automatically switch to offline mode
            manager._handle_network_state_change(online=False)
            assert manager._effective_offline_mode is True

    def test_repository_validation_comprehensive(self, manager, temp_dir):
        """Test comprehensive repository validation."""
        repo_path = manager.repository_path
        repo_path.mkdir(parents=True)

        # Create valid repository structure
        software_dir = repo_path / "software" / "ng" / "nginx"
        software_dir.mkdir(parents=True)
        (software_dir / "default.yaml").write_text(
            """
version: "0.2"
metadata:
  name: nginx
  display_name: Nginx Web Server
"""
        )

        validation_result = manager.validate_repository_structure()

        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0
        assert validation_result.software_count > 0

    def test_repository_statistics_collection(self, manager, temp_dir):
        """Test collection of repository statistics."""
        repo_path = manager.repository_path
        repo_path.mkdir(parents=True)

        # Create sample saidata files
        for software in ["nginx", "apache", "mysql"]:
            prefix = software[:2]
            software_dir = repo_path / "software" / prefix / software
            software_dir.mkdir(parents=True)
            (software_dir / "default.yaml").write_text(
                f"""
version: "0.2"
metadata:
  name: {software}
"""
            )

        stats = manager.get_repository_statistics()

        assert stats["total_software_packages"] == 3
        assert stats["repository_size_mb"] > 0
        assert "last_updated" in stats
        assert "structure_version" in stats


class TestRepositoryCacheComprehensive:
    """Comprehensive tests for RepositoryCache."""

    @pytest.fixture
    def config(self, temp_dir):
        """Create test configuration."""
        return SaiConfig(
            cache_directory=temp_dir / "cache", cache_enabled=True, saidata_update_interval=3600
        )

    @pytest.fixture
    def cache(self, config):
        """Create RepositoryCache instance."""
        return RepositoryCache(config)

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_cache_corruption_recovery(self, cache, temp_dir):
        """Test recovery from cache corruption."""
        # Create corrupted metadata file
        cache.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        cache.metadata_file.write_text("corrupted json content {")

        # Should handle corruption gracefully
        metadata = cache._load_metadata()
        assert metadata == {}

        # Should be able to continue operating
        cache.mark_repository_updated("https://github.com/test/repo", "main")
        assert cache.is_repository_valid("https://github.com/test/repo", "main")

    def test_cache_size_limits_enforcement(self, cache, temp_dir):
        """Test enforcement of cache size limits."""
        # Configure cache size limit
        cache.max_cache_size_mb = 10

        # Create repositories that exceed limit
        for i in range(5):
            url = f"https://github.com/test/repo{i}"
            repo_path = cache._get_repository_path(url, "main")
            repo_path.mkdir(parents=True)

            # Create large files
            large_file = repo_path / "large_file.txt"
            large_file.write_text("x" * 3000000)  # 3MB each

            cache.mark_repository_updated(url, "main")

        # Trigger cleanup
        cleaned = cache.enforce_cache_size_limits()

        # Should have cleaned some repositories
        assert cleaned > 0

        # Total cache size should be under limit
        total_size = cache.get_total_cache_size_mb()
        assert total_size <= cache.max_cache_size_mb

    def test_cache_access_patterns_optimization(self, cache):
        """Test cache access pattern optimization."""
        urls = [
            "https://github.com/test/repo1",
            "https://github.com/test/repo2",
            "https://github.com/test/repo3",
        ]

        # Simulate access patterns
        for url in urls:
            cache.mark_repository_accessed(url, "main")

        # Access repo1 multiple times (should be marked as frequently used)
        for _ in range(5):
            cache.mark_repository_accessed(urls[0], "main")

        # Get access statistics
        stats = cache.get_access_statistics()

        assert stats[urls[0]]["access_count"] == 6  # 1 initial + 5 additional
        assert stats[urls[1]]["access_count"] == 1
        assert stats[urls[2]]["access_count"] == 1

    def test_cache_metadata_versioning(self, cache):
        """Test cache metadata versioning and migration."""
        # Create old version metadata
        old_metadata = {
            "version": "1.0",
            "repositories": {
                "test_key": {
                    "url": "https://github.com/test/repo",
                    "branch": "main",
                    "local_path": "/tmp/repo",
                    "last_updated": time.time(),
                }
            },
        }

        cache.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        cache.metadata_file.write_text(json.dumps(old_metadata))

        # Load metadata (should trigger migration)
        metadata = cache._load_metadata()

        # Should have migrated to new format
        assert len(metadata) > 0
        for repo_metadata in metadata.values():
            assert isinstance(repo_metadata, RepositoryMetadata)

    def test_concurrent_cache_operations(self, cache):
        """Test concurrent cache operations safety."""
        import threading

        results = []

        def cache_operation(repo_id):
            try:
                url = f"https://github.com/test/repo{repo_id}"
                cache.mark_repository_updated(url, "main")
                is_valid = cache.is_repository_valid(url, "main")
                results.append(is_valid)
            except Exception:
                results.append(False)

        # Start multiple concurrent operations
        threads = []
        for i in range(10):
            thread = threading.Thread(target=cache_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all operations to complete
        for thread in threads:
            thread.join()

        # All operations should succeed
        assert all(results)
        assert len(results) == 10


class TestHierarchicalPathResolverComprehensive:
    """Comprehensive tests for HierarchicalPathResolver."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_path_resolution_edge_cases(self, temp_dir):
        """Test path resolution edge cases."""
        resolver = HierarchicalPathResolver([temp_dir])

        # Test single character software names
        path = resolver.get_expected_path("a")
        assert path.hierarchical_path == temp_dir / "software" / "a" / "a" / "default.yaml"

        # Test software names with numbers
        path = resolver.get_expected_path("python3")
        assert path.hierarchical_path == temp_dir / "software" / "py" / "python3" / "default.yaml"

        # Test software names with special characters
        path = resolver.get_expected_path("node-js")
        assert path.hierarchical_path == temp_dir / "software" / "no" / "node-js" / "default.yaml"

    def test_case_sensitivity_handling(self, temp_dir):
        """Test case sensitivity handling in path resolution."""
        resolver = HierarchicalPathResolver([temp_dir])

        # Create files with different cases
        nginx_dir = temp_dir / "software" / "ng" / "nginx"
        nginx_dir.mkdir(parents=True)
        (nginx_dir / "default.yaml").write_text("nginx config")

        NGINX_dir = temp_dir / "software" / "NG" / "NGINX"
        NGINX_dir.mkdir(parents=True)
        (NGINX_dir / "default.yaml").write_text("NGINX config")

        # Should find the lowercase version first
        found_files = resolver.find_saidata_files("nginx")
        assert len(found_files) >= 1
        assert found_files[0].parent.name == "nginx"

    def test_symlink_handling(self, temp_dir):
        """Test handling of symbolic links in hierarchical structure."""
        resolver = HierarchicalPathResolver([temp_dir])

        # Create actual directory
        actual_dir = temp_dir / "software" / "ap" / "apache"
        actual_dir.mkdir(parents=True)
        (actual_dir / "default.yaml").write_text("apache config")

        # Create symlink
        symlink_dir = temp_dir / "software" / "ht" / "httpd"
        symlink_dir.parent.mkdir(parents=True)
        symlink_dir.symlink_to(actual_dir)

        # Should handle symlinks properly
        found_files = resolver.find_saidata_files("httpd")
        assert len(found_files) == 1
        assert found_files[0].exists()

    def test_permission_error_handling(self, temp_dir):
        """Test handling of permission errors during path resolution."""
        resolver = HierarchicalPathResolver([temp_dir])

        # Create directory with restricted permissions
        restricted_dir = temp_dir / "software" / "re" / "restricted"
        restricted_dir.mkdir(parents=True)
        (restricted_dir / "default.yaml").write_text("restricted config")
        restricted_dir.chmod(0o000)  # No permissions

        try:
            # Should handle permission errors gracefully
            found_files = resolver.find_saidata_files("restricted")
            # May or may not find files depending on system, but shouldn't crash
            assert isinstance(found_files, list)
        finally:
            # Restore permissions for cleanup
            restricted_dir.chmod(0o755)

    def test_deep_directory_structure_handling(self, temp_dir):
        """Test handling of deep directory structures."""
        resolver = HierarchicalPathResolver([temp_dir])

        # Create deeply nested structure
        deep_path = temp_dir / "software" / "de" / "deep-software" / "nested" / "very" / "deep"
        deep_path.mkdir(parents=True)
        (deep_path / "config.yaml").write_text("deep config")

        # Should handle deep structures without issues
        software_dir = temp_dir / "software" / "de" / "deep-software"
        (software_dir / "default.yaml").write_text("main config")

        found_files = resolver.find_saidata_files("deep-software")
        assert len(found_files) == 1
        assert found_files[0] == software_dir / "default.yaml"

    def test_unicode_software_names(self, temp_dir):
        """Test handling of Unicode characters in software names."""
        resolver = HierarchicalPathResolver([temp_dir])

        # Test with Unicode characters (should be handled gracefully)
        unicode_names = ["café", "naïve", "résumé"]

        for name in unicode_names:
            try:
                path = resolver.get_expected_path(name)
                # Should not crash, even if path contains Unicode
                assert isinstance(path, SaidataPath)
            except ValueError:
                # May reject Unicode names, which is acceptable
                pass

    def test_path_traversal_protection(self, temp_dir):
        """Test protection against path traversal attacks."""
        resolver = HierarchicalPathResolver([temp_dir])

        # Test malicious software names
        malicious_names = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "software/../../../sensitive",
        ]

        for name in malicious_names:
            with pytest.raises(ValueError):
                resolver.get_expected_path(name)

    def test_search_path_priority_complex(self, temp_dir):
        """Test complex search path priority scenarios."""
        # Create multiple search paths
        path1 = temp_dir / "path1"
        path2 = temp_dir / "path2"
        path3 = temp_dir / "path3"

        for path in [path1, path2, path3]:
            path.mkdir(parents=True)

        resolver = HierarchicalPathResolver([path1, path2, path3])

        # Create same software in multiple paths with different content
        for i, path in enumerate([path1, path2, path3], 1):
            software_dir = path / "software" / "ng" / "nginx"
            software_dir.mkdir(parents=True)
            (software_dir / "default.yaml").write_text(f"nginx config from path{i}")

        found_files = resolver.find_saidata_files("nginx")

        # Should find all files, ordered by search path priority
        assert len(found_files) == 3
        assert found_files[0].read_text() == "nginx config from path1"
        assert found_files[1].read_text() == "nginx config from path2"
        assert found_files[2].read_text() == "nginx config from path3"
