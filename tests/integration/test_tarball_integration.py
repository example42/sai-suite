"""Integration tests for TarballRepositoryHandler with real GitHub repositories."""

import tempfile
from pathlib import Path
import pytest

from sai.core.tarball_repository_handler import TarballRepositoryHandler


class TestTarballIntegration:
    """Integration tests for TarballRepositoryHandler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = TarballRepositoryHandler(timeout=60, max_retries=2)
    
    @pytest.mark.integration
    def test_get_release_info_real_repo(self):
        """Test getting release info from a real GitHub repository."""
        # Use a small, stable repository for testing
        repo_url = "https://github.com/octocat/Hello-World"
        
        result = self.handler.get_latest_release_info(repo_url)
        
        # This repository might not have releases, so we just test that the API call works
        # and doesn't crash (it should return success=False with appropriate message)
        assert result is not None
        assert isinstance(result.success, bool)
        assert isinstance(result.message, str)
        
        if not result.success:
            # Expected for repositories without releases
            assert "no releases" in result.message.lower() or "not found" in result.message.lower()
    
    @pytest.mark.integration
    def test_download_nonexistent_repo(self):
        """Test downloading from a non-existent repository."""
        repo_url = "https://github.com/nonexistent/nonexistent-repo-12345"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "target"
            
            result = self.handler.download_latest_release(repo_url, target_dir)
            
            assert not result.success
            assert "404" in result.message or "not found" in result.message.lower()
    
    @pytest.mark.integration
    def test_invalid_github_url(self):
        """Test with invalid GitHub URL."""
        invalid_url = "https://example.com/not-github"
        
        result = self.handler.get_latest_release_info(invalid_url)
        
        assert not result.success
        assert "Invalid GitHub repository URL" in result.message
    
    def test_parse_github_urls_comprehensive(self):
        """Test parsing various GitHub URL formats."""
        test_cases = [
            # Valid URLs
            ("https://github.com/example42/saidata", ("example42", "saidata")),
            ("https://github.com/example42/saidata.git", ("example42", "saidata")),
            ("https://github.com/example42/saidata/", ("example42", "saidata")),
            ("https://github.com/octocat/Hello-World", ("octocat", "Hello-World")),
            
            # Invalid URLs
            ("https://gitlab.com/owner/repo", (None, None)),
            ("https://github.com/owner", (None, None)),
            ("https://github.com/", (None, None)),
            ("not-a-url", (None, None)),
            ("", (None, None)),
        ]
        
        for url, expected in test_cases:
            result = self.handler._parse_github_url(url)
            assert result == expected, f"Failed for URL: {url}"
    
    def test_file_extension_detection_comprehensive(self):
        """Test comprehensive file extension detection."""
        test_cases = [
            # Tarball formats
            ("https://github.com/owner/repo/releases/download/v1.0.0/release.tar.gz", "tar.gz"),
            ("https://github.com/owner/repo/releases/download/v1.0.0/release.tgz", "tar.gz"),
            ("https://github.com/owner/repo/releases/download/v1.0.0/release.tar.bz2", "tar.bz2"),
            ("https://github.com/owner/repo/releases/download/v1.0.0/release.tar.xz", "tar.xz"),
            
            # Zip formats
            ("https://github.com/owner/repo/releases/download/v1.0.0/release.zip", "zip"),
            
            # GitHub API URLs
            ("https://api.github.com/repos/owner/repo/tarball/main", "tar.gz"),
            ("https://api.github.com/repos/owner/repo/zipball/main", "zip"),
            
            # Unknown formats (should default to tar.gz)
            ("https://example.com/unknown-file", "tar.gz"),
            ("https://example.com/file.unknown", "tar.gz"),
        ]
        
        for url, expected in test_cases:
            result = self.handler._get_file_extension(url)
            assert result == expected, f"Failed for URL: {url}"


# Mark all tests in this class as integration tests
pytestmark = pytest.mark.integration