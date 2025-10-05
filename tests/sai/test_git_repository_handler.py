"""Tests for GitRepositoryHandler."""

import pytest
import subprocess
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from sai.core.git_repository_handler import (
    GitRepositoryHandler,
    RepositoryInfo,
    GitOperationResult
)
from sai.models.config import RepositoryAuthType


class TestGitRepositoryHandler:
    """Test cases for GitRepositoryHandler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = GitRepositoryHandler(timeout=30, max_retries=2)
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('subprocess.run')
    def test_is_git_available_success(self, mock_run):
        """Test git availability detection when git is available."""
        mock_run.return_value = Mock(returncode=0, stdout="git version 2.34.1")
        
        handler = GitRepositoryHandler()
        assert handler.is_git_available() is True
        
        # Should cache the result
        mock_run.reset_mock()
        assert handler.is_git_available() is True
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_is_git_available_failure(self, mock_run):
        """Test git availability detection when git is not available."""
        mock_run.side_effect = FileNotFoundError("git not found")
        
        handler = GitRepositoryHandler()
        assert handler.is_git_available() is False
    
    @patch('subprocess.run')
    def test_is_git_available_timeout(self, mock_run):
        """Test git availability detection with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 10)
        
        handler = GitRepositoryHandler()
        assert handler.is_git_available() is False
    
    @patch.object(GitRepositoryHandler, 'is_git_available')
    def test_clone_repository_git_unavailable(self, mock_git_available):
        """Test clone repository when git is not available."""
        mock_git_available.return_value = False
        
        result = self.handler.clone_repository(
            "https://github.com/example/repo.git",
            self.temp_dir / "repo"
        )
        
        assert result.success is False
        assert "Git is not available" in result.message
    
    @patch.object(GitRepositoryHandler, 'is_git_available')
    @patch.object(GitRepositoryHandler, '_execute_git_command_with_retry')
    def test_clone_repository_success(self, mock_execute, mock_git_available):
        """Test successful repository cloning."""
        mock_git_available.return_value = True
        mock_execute.return_value = GitOperationResult(
            success=True,
            message="Repository cloned successfully",
            stdout="Cloning into 'repo'...",
            stderr=""
        )
        
        result = self.handler.clone_repository(
            "https://github.com/example/repo.git",
            self.temp_dir / "repo",
            branch="main",
            shallow=True
        )
        
        assert result.success is True
        assert "Repository cloned successfully" in result.message
        
        # Verify the command was called with correct arguments
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0][0]  # First positional argument (cmd)
        assert "git" in call_args
        assert "clone" in call_args
        assert "--depth" in call_args
        assert "1" in call_args
        assert "--branch" in call_args
        assert "main" in call_args
        assert "https://github.com/example/repo.git" in call_args
    
    @patch.object(GitRepositoryHandler, 'is_git_available')
    @patch.object(GitRepositoryHandler, '_execute_git_command_with_retry')
    def test_clone_repository_with_ssh_auth(self, mock_execute, mock_git_available):
        """Test repository cloning with SSH authentication."""
        mock_git_available.return_value = True
        mock_execute.return_value = GitOperationResult(success=True, message="Success")
        
        # Create a temporary SSH key file
        ssh_key_path = self.temp_dir / "id_rsa"
        ssh_key_path.write_text("fake ssh key")
        
        result = self.handler.clone_repository(
            "git@github.com:example/repo.git",
            self.temp_dir / "repo",
            auth_type=RepositoryAuthType.SSH,
            auth_data={"ssh_key_path": str(ssh_key_path)}
        )
        
        assert result.success is True
        
        # Verify environment was set up for SSH
        call_kwargs = mock_execute.call_args[1]  # Keyword arguments
        env = call_kwargs.get('env')
        assert env is not None
        assert 'GIT_SSH_COMMAND' in env
        assert str(ssh_key_path) in env['GIT_SSH_COMMAND']
    
    @patch.object(GitRepositoryHandler, 'is_git_available')
    @patch.object(GitRepositoryHandler, '_execute_git_command_with_retry')
    def test_clone_repository_with_token_auth(self, mock_execute, mock_git_available):
        """Test repository cloning with token authentication."""
        mock_git_available.return_value = True
        mock_execute.return_value = GitOperationResult(success=True, message="Success")
        
        result = self.handler.clone_repository(
            "https://github.com/example/repo.git",
            self.temp_dir / "repo",
            auth_type=RepositoryAuthType.TOKEN,
            auth_data={"token": "ghp_1234567890", "username": "user"}
        )
        
        assert result.success is True
        
        # Verify environment was set up for token auth
        call_kwargs = mock_execute.call_args[1]
        env = call_kwargs.get('env')
        assert env is not None
        assert env.get('GIT_USERNAME') == 'user'
        assert env.get('GIT_PASSWORD') == 'ghp_1234567890'
    
    @patch.object(GitRepositoryHandler, 'is_git_available')
    def test_update_repository_git_unavailable(self, mock_git_available):
        """Test update repository when git is not available."""
        mock_git_available.return_value = False
        
        result = self.handler.update_repository(self.temp_dir / "repo")
        
        assert result.success is False
        assert "Git is not available" in result.message
    
    @patch.object(GitRepositoryHandler, 'is_git_available')
    def test_update_repository_invalid_directory(self, mock_git_available):
        """Test update repository with invalid directory."""
        mock_git_available.return_value = True
        
        result = self.handler.update_repository(self.temp_dir / "nonexistent")
        
        assert result.success is False
        assert "Repository directory does not exist" in result.message
    
    @patch.object(GitRepositoryHandler, 'is_git_available')
    @patch.object(GitRepositoryHandler, '_execute_git_command_with_retry')
    @patch.object(GitRepositoryHandler, '_execute_git_command')
    @patch.object(GitRepositoryHandler, 'get_repository_info')
    @patch.object(GitRepositoryHandler, '_verify_repository_integrity')
    def test_update_repository_success(self, mock_verify, mock_repo_info, mock_execute, mock_execute_retry, mock_git_available):
        """Test successful repository update."""
        mock_git_available.return_value = True
        mock_verify.return_value = True
        
        # Mock repository info before and after update
        mock_repo_info.side_effect = [
            RepositoryInfo(url="https://github.com/test/repo", branch="main", commit_hash="abc123"),  # before update
            RepositoryInfo(url="https://github.com/test/repo", branch="main", commit_hash="def456")   # after update
        ]
        
        # Create fake git directory
        repo_dir = self.temp_dir / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()
        
        # Mock fetch success
        mock_execute_retry.return_value = GitOperationResult(
            success=True,
            message="Fetch successful",
            stdout="From origin\n   abc123..def456  main -> origin/main"
        )
        
        # Mock branch detection, status check, and reset
        mock_execute.side_effect = [
            GitOperationResult(success=True, message="Branch detected", stdout="main\n"),  # branch detection
            GitOperationResult(success=True, message="Status check", stdout=""),  # status check
            GitOperationResult(success=True, message="Reset successful", stdout="HEAD is now at def456\n")  # reset
        ]
        
        result = self.handler.update_repository(repo_dir)
        
        assert result.success is True
        assert "Repository updated successfully" in result.message
        
        # Verify fetch was called
        mock_execute_retry.assert_called_once()
        fetch_cmd = mock_execute_retry.call_args[0][0]
        assert "fetch" in fetch_cmd
        assert "origin" in fetch_cmd
        
        # Verify branch detection, status check, and reset were called
        assert mock_execute.call_count == 3
    
    @patch.object(GitRepositoryHandler, '_execute_git_command')
    def test_get_repository_info_success(self, mock_execute):
        """Test getting repository information successfully."""
        # Create fake git directory
        repo_dir = self.temp_dir / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()
        
        # Mock git command responses
        mock_execute.side_effect = [
            GitOperationResult(success=True, message="Remote URL", stdout="https://github.com/example/repo.git\n"),  # remote URL
            GitOperationResult(success=True, message="Branch", stdout="main\n"),  # branch
            GitOperationResult(success=True, message="Commit hash", stdout="abc123def456\n"),  # commit hash
            GitOperationResult(success=True, message="Status", stdout=""),  # status (clean)
            GitOperationResult(success=True, message="Last commit", stdout="2023-12-01 10:30:00 +0000\n")  # last commit date
        ]
        
        info = self.handler.get_repository_info(repo_dir)
        
        assert info is not None
        assert info.url == "https://github.com/example/repo.git"
        assert info.branch == "main"
        assert info.commit_hash == "abc123def456"
        assert info.is_dirty is False
        assert info.remote_url == "https://github.com/example/repo.git"
        assert info.last_updated is not None
    
    def test_get_repository_info_invalid_directory(self):
        """Test getting repository info for invalid directory."""
        info = self.handler.get_repository_info(self.temp_dir / "nonexistent")
        assert info is None
    
    def test_get_repository_info_not_git_repo(self):
        """Test getting repository info for non-git directory."""
        regular_dir = self.temp_dir / "regular"
        regular_dir.mkdir()
        
        info = self.handler.get_repository_info(regular_dir)
        assert info is None
    
    def test_setup_git_environment_no_auth(self):
        """Test git environment setup with no authentication."""
        env = self.handler._setup_git_environment(None, None)
        assert env is None
    
    def test_setup_git_environment_ssh_auth(self):
        """Test git environment setup with SSH authentication."""
        ssh_key_path = self.temp_dir / "id_rsa"
        ssh_key_path.write_text("fake key")
        
        env = self.handler._setup_git_environment(
            RepositoryAuthType.SSH,
            {"ssh_key_path": str(ssh_key_path)}
        )
        
        assert env is not None
        assert 'GIT_SSH_COMMAND' in env
        assert str(ssh_key_path) in env['GIT_SSH_COMMAND']
        assert 'StrictHostKeyChecking=no' in env['GIT_SSH_COMMAND']
    
    def test_setup_git_environment_token_auth(self):
        """Test git environment setup with token authentication."""
        env = self.handler._setup_git_environment(
            RepositoryAuthType.TOKEN,
            {"token": "ghp_1234567890", "username": "user"}
        )
        
        assert env is not None
        assert env['GIT_USERNAME'] == 'user'
        assert env['GIT_PASSWORD'] == 'ghp_1234567890'
        assert env['GIT_ASKPASS'] == 'echo'
    
    def test_setup_git_environment_basic_auth(self):
        """Test git environment setup with basic authentication."""
        env = self.handler._setup_git_environment(
            RepositoryAuthType.BASIC,
            {"username": "user", "password": "pass"}
        )
        
        assert env is not None
        assert env['GIT_USERNAME'] == 'user'
        assert env['GIT_PASSWORD'] == 'pass'
        assert env['GIT_ASKPASS'] == 'echo'
    
    @patch('subprocess.run')
    def test_execute_git_command_success(self, mock_run):
        """Test successful git command execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Command output",
            stderr=""
        )
        
        result = self.handler._execute_git_command(["git", "status"])
        
        assert result.success is True
        assert result.stdout == "Command output"
        assert result.return_code == 0
    
    @patch('subprocess.run')
    def test_execute_git_command_failure(self, mock_run):
        """Test failed git command execution."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error message"
        )
        
        result = self.handler._execute_git_command(["git", "invalid"])
        
        assert result.success is False
        assert result.stderr == "Error message"
        assert result.return_code == 1
    
    @patch('subprocess.run')
    def test_execute_git_command_timeout(self, mock_run):
        """Test git command execution with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)
        
        result = self.handler._execute_git_command(["git", "clone", "large-repo"])
        
        assert result.success is False
        assert "timed out" in result.message
        assert result.return_code == -1
    
    @patch.object(GitRepositoryHandler, '_execute_git_command')
    def test_execute_git_command_with_retry_success_first_attempt(self, mock_execute):
        """Test git command with retry - success on first attempt."""
        mock_execute.return_value = GitOperationResult(success=True, message="Success")
        
        result = self.handler._execute_git_command_with_retry(["git", "status"])
        
        assert result.success is True
        mock_execute.assert_called_once()
    
    @patch.object(GitRepositoryHandler, '_execute_git_command')
    @patch('time.sleep')
    def test_execute_git_command_with_retry_success_second_attempt(self, mock_sleep, mock_execute):
        """Test git command with retry - success on second attempt."""
        mock_execute.side_effect = [
            GitOperationResult(success=False, message="Network error"),
            GitOperationResult(success=True, message="Success")
        ]
        
        result = self.handler._execute_git_command_with_retry(["git", "fetch"])
        
        assert result.success is True
        assert mock_execute.call_count == 2
        mock_sleep.assert_called_once_with(1)  # First retry delay
    
    @patch.object(GitRepositoryHandler, '_execute_git_command')
    @patch('time.sleep')
    def test_execute_git_command_with_retry_all_attempts_fail(self, mock_sleep, mock_execute):
        """Test git command with retry - all attempts fail."""
        mock_execute.return_value = GitOperationResult(success=False, message="Persistent error")
        
        handler = GitRepositoryHandler(max_retries=2)
        result = handler._execute_git_command_with_retry(["git", "fetch"])
        
        assert result.success is False
        assert mock_execute.call_count == 2
        assert mock_sleep.call_count == 1  # Only one sleep between attempts


@pytest.fixture
def git_handler():
    """Fixture for GitRepositoryHandler."""
    return GitRepositoryHandler(timeout=30, max_retries=2)


@pytest.fixture
def temp_repo_dir():
    """Fixture for temporary repository directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)