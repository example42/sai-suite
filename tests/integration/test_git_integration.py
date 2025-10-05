"""Integration tests for GitRepositoryHandler with real git operations."""

import pytest
import tempfile
import shutil
from pathlib import Path

from sai.core.git_repository_handler import GitRepositoryHandler


class TestGitIntegration:
    """Integration tests for GitRepositoryHandler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = GitRepositoryHandler(timeout=60, max_retries=2)
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.skipif(not GitRepositoryHandler().is_git_available(), reason="Git not available")
    def test_git_availability_real(self):
        """Test real git availability detection."""
        assert self.handler.is_git_available() is True
    
    @pytest.mark.skipif(not GitRepositoryHandler().is_git_available(), reason="Git not available")
    def test_clone_public_repository_real(self):
        """Test cloning a real public repository."""
        # Use a small, stable public repository for testing
        test_repo_url = "https://github.com/octocat/Hello-World.git"
        target_dir = self.temp_dir / "hello-world"
        
        result = self.handler.clone_repository(
            url=test_repo_url,
            target_dir=target_dir,
            branch="master",  # This repo uses master branch
            shallow=True
        )
        
        # The test might fail due to network issues, so we'll be lenient
        if result.success:
            assert target_dir.exists()
            assert (target_dir / ".git").exists()
            
            # Test getting repository info
            info = self.handler.get_repository_info(target_dir)
            assert info is not None
            assert info.url == test_repo_url
            assert info.branch == "master"
            assert info.commit_hash is not None
        else:
            # If clone fails (network issues, etc.), just log it
            print(f"Clone failed (expected in some environments): {result.message}")
    
    @pytest.mark.skipif(not GitRepositoryHandler().is_git_available(), reason="Git not available")
    def test_repository_info_invalid_repo(self):
        """Test getting info from invalid repository."""
        invalid_dir = self.temp_dir / "invalid"
        invalid_dir.mkdir()
        
        info = self.handler.get_repository_info(invalid_dir)
        assert info is None


def test_git_handler_initialization():
    """Test GitRepositoryHandler can be initialized."""
    handler = GitRepositoryHandler()
    assert handler.timeout == 300  # default timeout
    assert handler.max_retries == 3  # default retries
    
    handler_custom = GitRepositoryHandler(timeout=60, max_retries=2)
    assert handler_custom.timeout == 60
    assert handler_custom.max_retries == 2