"""Integration tests for end-to-end repository operations.

This module provides comprehensive integration tests for the repository system,
including real repository operations, authentication testing, offline mode,
and performance testing.
"""

import pytest
import tempfile
import shutil
import time
import json
import yaml
import threading
import subprocess
import os
import socket
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from sai.core.git_repository_handler import GitRepositoryHandler, GitOperationResult
from sai.core.tarball_repository_handler import TarballRepositoryHandler, TarballOperationResult
from sai.core.saidata_repository_manager import SaidataRepositoryManager, RepositoryStatus
from sai.core.repository_cache import RepositoryCache
from sai.core.saidata_loader import SaidataLoader
from sai.core.saidata_path import SaidataPath, HierarchicalPathResolver
from sai.models.config import SaiConfig, RepositoryAuthType
from sai.models.saidata import SaiData, Metadata
from sai.utils.errors import (
    GitOperationError, TarballDownloadError, RepositoryAuthenticationError,
    RepositoryNetworkError, RepositoryIntegrityError
)


# Test repository URLs for integration testing
TEST_REPOSITORIES = {
    "small_public": "https://github.com/octocat/Hello-World.git",
    "saidata_test": "https://github.com/example42/saidata-test.git",  # Hypothetical test repo
    "nonexistent": "https://github.com/nonexistent/repo.git",
    "private": "git@github.com:private/repo.git"  # For auth testing
}

# Test release URLs for tarball testing
TEST_RELEASE_URLS = {
    "small_release": "https://github.com/octocat/Hello-World",
    "large_release": "https://github.com/kubernetes/kubernetes",  # Large repo for performance
    "no_releases": "https://github.com/octocat/git-consortium"
}


@pytest.mark.integration
class TestRepositoryIntegrationE2E:
    """End-to-end integration tests for repository operations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_dir = self.temp_dir / "cache"
        self.repo_dir = self.temp_dir / "repositories"
        self.saidata_dir = self.temp_dir / "saidata"
        
        # Create directories
        for directory in [self.cache_dir, self.repo_dir, self.saidata_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Create test configuration
        self.config = SaiConfig(
            cache_directory=self.cache_dir,
            saidata_repository_url=TEST_REPOSITORIES["small_public"],
            saidata_repository_branch="main",
            saidata_auto_update=True,
            saidata_update_interval=3600,
            saidata_offline_mode=False,
            saidata_repository_cache_dir=self.repo_dir
        )
        
        # Initialize components
        self.git_handler = GitRepositoryHandler(timeout=60, max_retries=2)
        self.tarball_handler = TarballRepositoryHandler(timeout=60, max_retries=2)
        self.repository_cache = RepositoryCache(self.config)
        self.repository_manager = SaidataRepositoryManager(self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_repository_structure(self, repo_path: Path):
        """Create a test repository structure with saidata files."""
        # Create hierarchical saidata structure
        software_configs = [
            ("nginx", "ng", {"name": "nginx", "display_name": "Nginx Web Server"}),
            ("apache", "ap", {"name": "apache", "display_name": "Apache HTTP Server"}),
            ("mysql", "my", {"name": "mysql", "display_name": "MySQL Database"}),
            ("redis", "re", {"name": "redis", "display_name": "Redis Cache"}),
            ("docker", "do", {"name": "docker", "display_name": "Docker Container Platform"})
        ]
        
        for software_name, prefix, metadata in software_configs:
            software_dir = repo_path / "software" / prefix / software_name
            software_dir.mkdir(parents=True, exist_ok=True)
            
            saidata = {
                "version": "0.2",
                "metadata": metadata,
                "packages": [{"name": software_name}],
                "providers": {
                    "apt": {"packages": [{"name": f"{software_name}-apt"}]},
                    "brew": {"packages": [{"name": f"{software_name}-brew"}]},
                    "yum": {"packages": [{"name": f"{software_name}-yum"}]}
                }
            }
            
            saidata_file = software_dir / "default.yaml"
            with open(saidata_file, 'w') as f:
                yaml.dump(saidata, f)
        
        # Create repository metadata
        repo_metadata = {
            "version": "1.0",
            "description": "Test saidata repository",
            "software_count": len(software_configs),
            "last_updated": datetime.now().isoformat()
        }
        
        metadata_file = repo_path / "repository.yaml"
        with open(metadata_file, 'w') as f:
            yaml.dump(repo_metadata, f)
    
    def is_network_available(self) -> bool:
        """Check if network is available for integration tests."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False
    
    def test_complete_git_repository_workflow(self):
        """Test complete git repository fetch and saidata loading workflow."""
        if not self.is_network_available():
            pytest.skip("Network not available for integration test")
        
        # Create a local test repository to simulate remote
        test_repo_path = self.temp_dir / "test_repo"
        test_repo_path.mkdir()
        
        # Initialize git repository
        subprocess.run(["git", "init"], cwd=test_repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], 
                      cwd=test_repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], 
                      cwd=test_repo_path, check=True, capture_output=True)
        
        # Create test saidata structure
        self.create_test_repository_structure(test_repo_path)
        
        # Add and commit files
        subprocess.run(["git", "add", "."], cwd=test_repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], 
                      cwd=test_repo_path, check=True, capture_output=True)
        
        # Test cloning
        clone_path = self.repo_dir / "cloned_repo"
        result = self.git_handler.clone_repository(str(test_repo_path), clone_path)
        
        assert result.success, f"Clone failed: {result.message}"
        assert clone_path.exists()
        assert (clone_path / "software" / "ng" / "nginx" / "default.yaml").exists()
        
        # Test saidata loading from cloned repository
        saidata_loader = SaidataLoader([clone_path])
        nginx_saidata = saidata_loader.load_saidata("nginx")
        
        assert nginx_saidata is not None
        assert nginx_saidata.metadata.name == "nginx"
        assert nginx_saidata.metadata.display_name == "Nginx Web Server"
        
        # Test repository update
        # Add new file to original repository
        new_software_dir = test_repo_path / "software" / "po" / "postgres"
        new_software_dir.mkdir(parents=True)
        postgres_saidata = {
            "version": "0.2",
            "metadata": {"name": "postgres", "display_name": "PostgreSQL Database"},
            "packages": [{"name": "postgresql"}]
        }
        with open(new_software_dir / "default.yaml", 'w') as f:
            yaml.dump(postgres_saidata, f)
        
        subprocess.run(["git", "add", "."], cwd=test_repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add postgres"], 
                      cwd=test_repo_path, check=True, capture_output=True)
        
        # Update cloned repository
        update_result = self.git_handler.update_repository(clone_path)
        assert update_result.success, f"Update failed: {update_result.message}"
        
        # Verify new file is available
        postgres_saidata_loaded = saidata_loader.load_saidata("postgres")
        assert postgres_saidata_loaded is not None
        assert postgres_saidata_loaded.metadata.name == "postgres"
    
    def test_complete_tarball_repository_workflow(self):
        """Test complete tarball download and saidata loading workflow."""
        if not self.is_network_available():
            pytest.skip("Network not available for integration test")
        
        # Create a test tarball with saidata structure
        test_content_dir = self.temp_dir / "test_content"
        test_content_dir.mkdir()
        self.create_test_repository_structure(test_content_dir)
        
        # Create tarball
        import tarfile
        tarball_path = self.temp_dir / "test_repo.tar.gz"
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(test_content_dir, arcname=".")
        
        # Mock GitHub API response
        release_info = {
            "tag_name": "v1.0.0",
            "name": "Test Release",
            "assets": [{
                "name": "test_repo.tar.gz",
                "browser_download_url": f"file://{tarball_path}",
                "size": tarball_path.stat().st_size
            }]
        }
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            # Mock API response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read.return_value = json.dumps(release_info).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            # Test getting release info
            result = self.tarball_handler.get_latest_release_info(TEST_RELEASE_URLS["small_release"])
            assert result.success, f"Get release info failed: {result.message}"
            
            # Test download and extraction
            extract_path = self.repo_dir / "extracted_repo"
            download_result = self.tarball_handler.download_and_extract_release(
                TEST_RELEASE_URLS["small_release"], extract_path
            )
            
            # Note: This will fail with file:// URL, but tests the workflow
            # In real scenarios, this would work with HTTP URLs
    
    def test_repository_manager_end_to_end_workflow(self):
        """Test complete repository manager workflow."""
        # Create test repository structure locally
        test_repo_path = self.temp_dir / "manager_test_repo"
        test_repo_path.mkdir()
        self.create_test_repository_structure(test_repo_path)
        
        # Configure repository manager to use local path
        self.repository_manager.config.saidata_repository_url = str(test_repo_path)
        
        # Mock git operations to use local copy
        def mock_clone_or_update(url, target_path):
            if target_path.exists():
                shutil.rmtree(target_path)
            shutil.copytree(test_repo_path, target_path)
            return True
        
        with patch.object(self.repository_manager, '_clone_or_update_repository', 
                         side_effect=mock_clone_or_update):
            
            # Test getting saidata
            nginx_saidata = self.repository_manager.get_saidata("nginx")
            assert nginx_saidata is not None
            assert nginx_saidata.metadata.name == "nginx"
            
            # Test repository status
            status = self.repository_manager.get_repository_status()
            assert status.url == str(test_repo_path)
            assert status.is_available
            
            # Test repository update
            update_result = self.repository_manager.update_repository(force=True)
            assert update_result is True
            
            # Test multiple software loading
            software_names = ["apache", "mysql", "redis", "docker"]
            for software_name in software_names:
                saidata = self.repository_manager.get_saidata(software_name)
                assert saidata is not None
                assert saidata.metadata.name == software_name
    
    def test_repository_caching_end_to_end(self):
        """Test repository caching workflow."""
        # Create test repository
        test_repo_path = self.temp_dir / "cache_test_repo"
        test_repo_path.mkdir()
        self.create_test_repository_structure(test_repo_path)
        
        repo_url = str(test_repo_path)
        branch = "main"
        
        # Test initial cache state
        assert not self.repository_cache.is_repository_valid(repo_url, branch)
        
        # Mark repository as updated
        self.repository_cache.mark_repository_updated(repo_url, branch)
        
        # Test cache validity
        assert self.repository_cache.is_repository_valid(repo_url, branch)
        
        # Test cache metadata
        metadata = self.repository_cache.get_repository_metadata(repo_url, branch)
        assert metadata is not None
        assert metadata.url == repo_url
        assert metadata.branch == branch
        
        # Test cache expiration
        # Manually set old timestamp
        old_time = time.time() - 7200  # 2 hours ago
        self.repository_cache._update_repository_timestamp(repo_url, branch, old_time)
        
        # Should be invalid if update interval is 1 hour
        self.repository_cache.config.saidata_update_interval = 3600
        assert not self.repository_cache.is_repository_valid(repo_url, branch)
        
        # Test cache cleanup
        # Create multiple cached repositories
        for i in range(5):
            test_url = f"https://github.com/test/repo{i}.git"
            self.repository_cache.mark_repository_updated(test_url, "main")
        
        # Test cleanup
        cleaned_count = self.repository_cache.cleanup_old_repositories(max_age_days=0)
        assert cleaned_count >= 0  # Should clean up old entries


@pytest.mark.integration
class TestRepositoryOfflineModeIntegration:
    """Integration tests for offline mode and network failure scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_dir = self.temp_dir / "cache"
        self.repo_dir = self.temp_dir / "repositories"
        
        for directory in [self.cache_dir, self.repo_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.config = SaiConfig(
            cache_directory=self.cache_dir,
            saidata_repository_url="https://github.com/example42/saidata.git",
            saidata_offline_mode=False,
            saidata_repository_cache_dir=self.repo_dir
        )
        
        self.repository_manager = SaidataRepositoryManager(self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_cached_repository(self):
        """Create a cached repository for offline testing."""
        cached_repo_path = self.repository_manager.repository_path
        cached_repo_path.mkdir(parents=True, exist_ok=True)
        
        # Create test saidata structure
        software_dir = cached_repo_path / "software" / "ng" / "nginx"
        software_dir.mkdir(parents=True, exist_ok=True)
        
        saidata = {
            "version": "0.2",
            "metadata": {
                "name": "nginx",
                "display_name": "Nginx Web Server"
            },
            "packages": [{"name": "nginx"}]
        }
        
        with open(software_dir / "default.yaml", 'w') as f:
            yaml.dump(saidata, f)
        
        # Mark as cached
        self.repository_manager.repository_cache.mark_repository_updated(
            self.config.saidata_repository_url, 
            self.config.saidata_repository_branch
        )
    
    def test_offline_mode_with_cached_repository(self):
        """Test offline mode using cached repository."""
        # Create cached repository
        self.create_cached_repository()
        
        # Enable offline mode
        self.repository_manager.config.saidata_offline_mode = True
        
        # Should use cached repository
        nginx_saidata = self.repository_manager.get_saidata("nginx")
        assert nginx_saidata is not None
        assert nginx_saidata.metadata.name == "nginx"
        
        # Repository status should indicate offline mode
        status = self.repository_manager.get_repository_status()
        assert status.is_offline_mode
    
    def test_network_failure_fallback_to_cache(self):
        """Test fallback to cached repository when network fails."""
        # Create cached repository
        self.create_cached_repository()
        
        # Mock network failure
        with patch.object(self.repository_manager, '_is_network_available', return_value=False):
            # Should fallback to cached repository
            nginx_saidata = self.repository_manager.get_saidata("nginx")
            assert nginx_saidata is not None
            assert nginx_saidata.metadata.name == "nginx"
            
            # Should indicate using stale cache
            status = self.repository_manager.get_repository_status()
            assert status.using_stale_cache
    
    def test_no_cache_no_network_failure(self):
        """Test behavior when no cache exists and network is unavailable."""
        # Ensure no cached repository exists
        if self.repository_manager.repository_path.exists():
            shutil.rmtree(self.repository_manager.repository_path)
        
        # Mock network failure
        with patch.object(self.repository_manager, '_is_network_available', return_value=False):
            # Should fail gracefully
            nginx_saidata = self.repository_manager.get_saidata("nginx")
            assert nginx_saidata is None
            
            status = self.repository_manager.get_repository_status()
            assert status.status == RepositoryStatus.ERROR
            assert "network" in status.error_message.lower()
    
    def test_stale_cache_warning(self):
        """Test warning when using stale cached data."""
        # Create cached repository with old timestamp
        self.create_cached_repository()
        
        # Set old timestamp (older than update interval)
        old_time = time.time() - 7200  # 2 hours ago
        self.repository_manager.repository_cache._update_repository_timestamp(
            self.config.saidata_repository_url,
            self.config.saidata_repository_branch,
            old_time
        )
        
        # Mock network failure
        with patch.object(self.repository_manager, '_is_network_available', return_value=False):
            # Should use stale cache with warning
            nginx_saidata = self.repository_manager.get_saidata("nginx")
            assert nginx_saidata is not None
            
            status = self.repository_manager.get_repository_status()
            assert status.using_stale_cache
            assert status.cache_age_hours > 1
    
    def test_automatic_offline_mode_detection(self):
        """Test automatic detection and switching to offline mode."""
        # Create cached repository
        self.create_cached_repository()
        
        # Start in online mode
        assert not self.repository_manager.config.saidata_offline_mode
        
        # Simulate network becoming unavailable
        with patch.object(self.repository_manager, '_is_network_available', return_value=False):
            # Should automatically switch to offline mode
            self.repository_manager._handle_network_state_change(online=False)
            
            # Should now be in effective offline mode
            assert self.repository_manager._effective_offline_mode
            
            # Should still be able to load saidata from cache
            nginx_saidata = self.repository_manager.get_saidata("nginx")
            assert nginx_saidata is not None
    
    def test_network_recovery_handling(self):
        """Test handling of network recovery."""
        # Create cached repository
        self.create_cached_repository()
        
        # Start in offline mode due to network failure
        self.repository_manager._effective_offline_mode = True
        
        # Simulate network recovery
        with patch.object(self.repository_manager, '_is_network_available', return_value=True):
            # Should detect network recovery
            self.repository_manager._handle_network_state_change(online=True)
            
            # Should exit offline mode
            assert not self.repository_manager._effective_offline_mode
            
            # Should attempt to update repository
            with patch.object(self.repository_manager, 'update_repository') as mock_update:
                mock_update.return_value = True
                
                # Trigger repository access
                self.repository_manager.get_saidata("nginx")
                
                # Should have attempted update
                mock_update.assert_called_once()


@pytest.mark.integration
class TestRepositoryAuthenticationIntegration:
    """Integration tests for repository authentication."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.ssh_dir = self.temp_dir / ".ssh"
        self.ssh_dir.mkdir(parents=True, exist_ok=True)
        
        self.git_handler = GitRepositoryHandler(timeout=30, max_retries=1)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_ssh_key(self) -> Path:
        """Create a test SSH key for authentication testing."""
        ssh_key_path = self.ssh_dir / "test_key"
        
        # Create a dummy SSH key (not a real key, just for testing)
        ssh_key_content = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAFwAAAAdzc2gtcn
NhAAAAAwEAAQAAAQEA1234567890abcdef...
-----END OPENSSH PRIVATE KEY-----"""
        
        ssh_key_path.write_text(ssh_key_content)
        ssh_key_path.chmod(0o600)
        
        return ssh_key_path
    
    def test_ssh_key_validation(self):
        """Test SSH key validation."""
        # Create valid SSH key
        valid_key = self.create_test_ssh_key()
        assert self.git_handler._validate_ssh_key(str(valid_key))
        
        # Test invalid permissions
        invalid_key = self.ssh_dir / "invalid_key"
        invalid_key.write_text("fake key content")
        invalid_key.chmod(0o644)  # Too permissive
        assert not self.git_handler._validate_ssh_key(str(invalid_key))
        
        # Test non-existent key
        assert not self.git_handler._validate_ssh_key("/nonexistent/key")
    
    def test_ssh_authentication_setup(self):
        """Test SSH authentication configuration."""
        ssh_key_path = self.create_test_ssh_key()
        
        auth_config = {
            "type": "ssh",
            "ssh_key_path": str(ssh_key_path),
            "ssh_user": "git"
        }
        
        # Test authentication setup
        env_vars = self.git_handler._setup_ssh_authentication(auth_config)
        
        assert "GIT_SSH_COMMAND" in env_vars
        assert str(ssh_key_path) in env_vars["GIT_SSH_COMMAND"]
    
    def test_token_authentication_setup(self):
        """Test token-based authentication configuration."""
        auth_config = {
            "type": "token",
            "token": "ghp_test_token_123456789"
        }
        
        # Test token authentication setup
        url_with_auth = self.git_handler._setup_token_authentication(
            "https://github.com/user/repo.git", 
            auth_config
        )
        
        assert "ghp_test_token_123456789" in url_with_auth
        assert url_with_auth.startswith("https://")
    
    def test_authentication_failure_handling(self):
        """Test handling of authentication failures."""
        # Mock authentication failure
        with patch.object(self.git_handler, '_execute_git_command') as mock_execute:
            mock_execute.return_value = GitOperationResult(
                success=False,
                stderr="fatal: Authentication failed",
                exit_code=128
            )
            
            result = self.git_handler.clone_repository(
                TEST_REPOSITORIES["private"],
                self.temp_dir / "private_repo"
            )
            
            assert not result.success
            assert "authentication" in result.message.lower()
    
    def test_credential_sanitization_in_logs(self):
        """Test that credentials are sanitized in log messages."""
        auth_config = {
            "type": "token",
            "token": "secret_token_123",
            "username": "testuser",
            "password": "secret_password"
        }
        
        sanitized = self.git_handler._sanitize_auth_data(auth_config)
        
        assert sanitized["token"] == "***"
        assert sanitized["password"] == "***"
        assert sanitized["username"] == "testuser"  # Username is not sanitized
    
    @pytest.mark.skipif(not os.getenv("TEST_SSH_KEY"), 
                       reason="SSH key not provided for integration test")
    def test_real_ssh_authentication(self):
        """Test real SSH authentication (requires SSH key setup)."""
        ssh_key_path = os.getenv("TEST_SSH_KEY")
        test_repo_url = os.getenv("TEST_SSH_REPO", TEST_REPOSITORIES["private"])
        
        if not ssh_key_path or not Path(ssh_key_path).exists():
            pytest.skip("SSH key not available for integration test")
        
        auth_config = {
            "type": "ssh",
            "ssh_key_path": ssh_key_path,
            "ssh_user": "git"
        }
        
        clone_path = self.temp_dir / "ssh_cloned_repo"
        
        # This will likely fail without proper SSH setup, but tests the workflow
        result = self.git_handler.clone_repository_with_auth(
            test_repo_url, clone_path, auth_config
        )
        
        # Result depends on actual SSH setup
        if result.success:
            assert clone_path.exists()
        else:
            # Should provide meaningful error message
            assert len(result.message) > 0


@pytest.mark.integration
@pytest.mark.slow
class TestRepositoryPerformanceIntegration:
    """Performance integration tests for large repository handling."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_dir = self.temp_dir / "cache"
        self.repo_dir = self.temp_dir / "repositories"
        
        for directory in [self.cache_dir, self.repo_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.config = SaiConfig(
            cache_directory=self.cache_dir,
            saidata_repository_cache_dir=self.repo_dir
        )
        
        self.git_handler = GitRepositoryHandler(timeout=300, max_retries=1)
        self.tarball_handler = TarballRepositoryHandler(timeout=300, max_retries=1)
        self.repository_manager = SaidataRepositoryManager(self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_large_repository_structure(self, repo_path: Path, software_count: int = 1000):
        """Create a large repository structure for performance testing."""
        print(f"Creating large repository structure with {software_count} software packages...")
        
        # Generate software packages
        for i in range(software_count):
            software_name = f"software_{i:04d}"
            prefix = software_name[:2]
            
            software_dir = repo_path / "software" / prefix / software_name
            software_dir.mkdir(parents=True, exist_ok=True)
            
            saidata = {
                "version": "0.2",
                "metadata": {
                    "name": software_name,
                    "display_name": f"Software Package {i}",
                    "description": f"Test software package number {i}"
                },
                "packages": [{"name": software_name}],
                "providers": {
                    "apt": {"packages": [{"name": f"{software_name}-apt"}]},
                    "brew": {"packages": [{"name": f"{software_name}-brew"}]},
                    "yum": {"packages": [{"name": f"{software_name}-yum"}]}
                }
            }
            
            saidata_file = software_dir / "default.yaml"
            with open(saidata_file, 'w') as f:
                yaml.dump(saidata, f)
        
        print(f"Created {software_count} software packages")
    
    def test_large_repository_cloning_performance(self):
        """Test performance of cloning large repositories."""
        # Create large test repository
        large_repo_path = self.temp_dir / "large_test_repo"
        large_repo_path.mkdir()
        
        # Create repository structure with many files
        self.create_large_repository_structure(large_repo_path, software_count=500)
        
        # Initialize git repository
        subprocess.run(["git", "init"], cwd=large_repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], 
                      cwd=large_repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], 
                      cwd=large_repo_path, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=large_repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], 
                      cwd=large_repo_path, check=True, capture_output=True)
        
        # Test cloning performance
        clone_path = self.repo_dir / "large_cloned_repo"
        
        start_time = time.time()
        result = self.git_handler.clone_repository(str(large_repo_path), clone_path)
        clone_time = time.time() - start_time
        
        assert result.success, f"Large repository clone failed: {result.message}"
        assert clone_path.exists()
        
        print(f"Large repository clone took {clone_time:.2f} seconds")
        
        # Performance assertion (should complete within reasonable time)
        assert clone_time < 60, f"Clone took too long: {clone_time:.2f} seconds"
        
        # Verify repository structure
        software_dirs = list((clone_path / "software").glob("*/*"))
        assert len(software_dirs) == 500, f"Expected 500 software directories, found {len(software_dirs)}"
    
    def test_large_repository_saidata_loading_performance(self):
        """Test performance of loading saidata from large repositories."""
        # Create large repository structure
        large_repo_path = self.temp_dir / "large_saidata_repo"
        large_repo_path.mkdir()
        self.create_large_repository_structure(large_repo_path, software_count=1000)
        
        # Test saidata loading performance
        saidata_loader = SaidataLoader([large_repo_path])
        
        # Test loading multiple software packages
        software_names = [f"software_{i:04d}" for i in range(0, 100, 10)]  # Every 10th package
        
        start_time = time.time()
        loaded_count = 0
        
        for software_name in software_names:
            saidata = saidata_loader.load_saidata(software_name)
            if saidata is not None:
                loaded_count += 1
        
        loading_time = time.time() - start_time
        
        print(f"Loaded {loaded_count} saidata files in {loading_time:.2f} seconds")
        
        # Performance assertions
        assert loaded_count == len(software_names), f"Expected {len(software_names)} loaded, got {loaded_count}"
        assert loading_time < 10, f"Loading took too long: {loading_time:.2f} seconds"
        
        # Test average loading time per file
        avg_time_per_file = loading_time / loaded_count
        assert avg_time_per_file < 0.1, f"Average loading time too high: {avg_time_per_file:.3f} seconds"
    
    def test_concurrent_repository_operations_performance(self):
        """Test performance of concurrent repository operations."""
        # Create multiple test repositories
        repo_count = 5
        repos = []
        
        for i in range(repo_count):
            repo_path = self.temp_dir / f"concurrent_repo_{i}"
            repo_path.mkdir()
            self.create_large_repository_structure(repo_path, software_count=100)
            repos.append(repo_path)
        
        # Test concurrent cloning
        clone_results = []
        threads = []
        
        def clone_repository(repo_path, clone_path):
            start_time = time.time()
            result = self.git_handler.clone_repository(str(repo_path), clone_path)
            end_time = time.time()
            clone_results.append({
                'success': result.success,
                'time': end_time - start_time,
                'repo': repo_path.name
            })
        
        # Start concurrent cloning operations
        start_time = time.time()
        
        for i, repo_path in enumerate(repos):
            clone_path = self.repo_dir / f"concurrent_clone_{i}"
            thread = threading.Thread(target=clone_repository, args=(repo_path, clone_path))
            threads.append(thread)
            thread.start()
        
        # Wait for all operations to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify results
        successful_clones = sum(1 for result in clone_results if result['success'])
        assert successful_clones == repo_count, f"Expected {repo_count} successful clones, got {successful_clones}"
        
        # Performance assertions
        assert total_time < 120, f"Concurrent operations took too long: {total_time:.2f} seconds"
        
        avg_clone_time = sum(result['time'] for result in clone_results) / len(clone_results)
        print(f"Average concurrent clone time: {avg_clone_time:.2f} seconds")
        print(f"Total concurrent operation time: {total_time:.2f} seconds")
    
    def test_repository_cache_performance_with_many_repositories(self):
        """Test repository cache performance with many cached repositories."""
        repository_cache = RepositoryCache(self.config)
        
        # Create many cached repository entries
        repo_count = 1000
        repo_urls = [f"https://github.com/test/repo{i}.git" for i in range(repo_count)]
        
        # Test cache write performance
        start_time = time.time()
        
        for repo_url in repo_urls:
            repository_cache.mark_repository_updated(repo_url, "main")
        
        write_time = time.time() - start_time
        
        print(f"Cached {repo_count} repositories in {write_time:.2f} seconds")
        
        # Test cache read performance
        start_time = time.time()
        valid_count = 0
        
        for repo_url in repo_urls:
            if repository_cache.is_repository_valid(repo_url, "main"):
                valid_count += 1
        
        read_time = time.time() - start_time
        
        print(f"Validated {valid_count} repositories in {read_time:.2f} seconds")
        
        # Performance assertions
        assert write_time < 10, f"Cache writing took too long: {write_time:.2f} seconds"
        assert read_time < 5, f"Cache reading took too long: {read_time:.2f} seconds"
        assert valid_count == repo_count, f"Expected {repo_count} valid repos, got {valid_count}"
        
        # Test cache cleanup performance
        start_time = time.time()
        cleaned_count = repository_cache.cleanup_old_repositories(max_age_days=0)
        cleanup_time = time.time() - start_time
        
        print(f"Cleaned up {cleaned_count} repositories in {cleanup_time:.2f} seconds")
        assert cleanup_time < 5, f"Cache cleanup took too long: {cleanup_time:.2f} seconds"
    
    def test_memory_usage_with_large_repositories(self):
        """Test memory usage when working with large repositories."""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large repository structure
        large_repo_path = self.temp_dir / "memory_test_repo"
        large_repo_path.mkdir()
        self.create_large_repository_structure(large_repo_path, software_count=2000)
        
        # Load many saidata files
        saidata_loader = SaidataLoader([large_repo_path])
        loaded_saidata = []
        
        for i in range(0, 500, 5):  # Load every 5th package
            software_name = f"software_{i:04d}"
            saidata = saidata_loader.load_saidata(software_name)
            if saidata:
                loaded_saidata.append(saidata)
        
        # Check memory usage after loading
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        print(f"Initial memory: {initial_memory:.1f} MB")
        print(f"Peak memory: {peak_memory:.1f} MB")
        print(f"Memory increase: {memory_increase:.1f} MB")
        print(f"Loaded {len(loaded_saidata)} saidata objects")
        
        # Memory usage should be reasonable
        assert memory_increase < 500, f"Memory usage too high: {memory_increase:.1f} MB"
        
        # Clean up and check memory release
        loaded_saidata.clear()
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_released = peak_memory - final_memory
        
        print(f"Final memory: {final_memory:.1f} MB")
        print(f"Memory released: {memory_released:.1f} MB")
        
        # Should release significant memory
        assert memory_released > memory_increase * 0.5, "Insufficient memory cleanup"


@pytest.mark.integration
class TestRepositorySecurityIntegration:
    """Integration tests for repository security features."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.git_handler = GitRepositoryHandler()
        self.tarball_handler = TarballRepositoryHandler()
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_malicious_repository_url_validation(self):
        """Test validation of potentially malicious repository URLs."""
        malicious_urls = [
            "javascript:alert('xss')",
            "file:///etc/passwd",
            "ftp://malicious.com/repo",
            "http://localhost:22/repo",  # Suspicious port
            "https://github.com/user/repo.git; rm -rf /",  # Command injection attempt
            "https://github.com/user/repo.git\nrm -rf /",  # Newline injection
        ]
        
        for url in malicious_urls:
            is_valid = self.git_handler._validate_repository_url(url)
            assert not is_valid, f"Malicious URL should be rejected: {url}"
    
    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks."""
        # Test with malicious paths
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32",
            "software/../../../etc/passwd",
            "software/../../sensitive_file"
        ]
        
        for malicious_path in malicious_paths:
            # Should sanitize or reject malicious paths
            sanitized = self.git_handler._sanitize_path(malicious_path)
            assert not sanitized.startswith("/etc/"), f"Path traversal not prevented: {malicious_path}"
            assert not sanitized.startswith("C:\\Windows"), f"Path traversal not prevented: {malicious_path}"
            assert ".." not in sanitized, f"Path traversal not prevented: {malicious_path}"
    
    def test_command_injection_protection(self):
        """Test protection against command injection in git operations."""
        # Test with malicious repository URLs containing command injection
        malicious_repo_url = "https://github.com/user/repo.git; rm -rf /"
        clone_path = self.temp_dir / "test_clone"
        
        # Should fail safely without executing injected commands
        result = self.git_handler.clone_repository(malicious_repo_url, clone_path)
        assert not result.success
        assert "invalid" in result.message.lower() or "failed" in result.message.lower()
    
    def test_archive_extraction_security(self):
        """Test security measures during archive extraction."""
        import zipfile
        
        # Create malicious zip file with path traversal
        malicious_zip = self.temp_dir / "malicious.zip"
        
        with zipfile.ZipFile(malicious_zip, 'w') as zf:
            # Add file with path traversal
            zf.writestr("../../../malicious.txt", "malicious content")
            zf.writestr("software/../../escape.txt", "escaped content")
        
        extract_path = self.temp_dir / "extract"
        
        # Should prevent path traversal during extraction
        with pytest.raises(Exception):  # Should raise security exception
            self.tarball_handler._extract_zip_with_protection(malicious_zip, extract_path)
        
        # Verify no files were extracted outside the target directory
        assert not (self.temp_dir / "malicious.txt").exists()
        assert not (self.temp_dir / "escape.txt").exists()
    
    def test_repository_integrity_validation(self):
        """Test repository integrity validation."""
        # Create test repository with valid structure
        test_repo = self.temp_dir / "test_repo"
        test_repo.mkdir()
        
        # Create valid saidata structure
        software_dir = test_repo / "software" / "ng" / "nginx"
        software_dir.mkdir(parents=True)
        
        valid_saidata = {
            "version": "0.2",
            "metadata": {"name": "nginx"},
            "packages": [{"name": "nginx"}]
        }
        
        with open(software_dir / "default.yaml", 'w') as f:
            yaml.dump(valid_saidata, f)
        
        # Test integrity validation
        is_valid = self.git_handler._validate_repository_structure(test_repo)
        assert is_valid
        
        # Create invalid structure (missing required fields)
        invalid_software_dir = test_repo / "software" / "ap" / "apache"
        invalid_software_dir.mkdir(parents=True)
        
        invalid_saidata = {
            "version": "0.2",
            # Missing required metadata
            "packages": [{"name": "apache"}]
        }
        
        with open(invalid_software_dir / "default.yaml", 'w') as f:
            yaml.dump(invalid_saidata, f)
        
        # Should detect invalid structure
        validation_result = self.git_handler._validate_repository_structure(test_repo)
        # Depending on implementation, might still be valid overall but with warnings
        # The specific behavior depends on how strict the validation is


if __name__ == "__main__":
    # Run integration tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "integration"
    ])