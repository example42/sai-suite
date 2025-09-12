"""Git repository handler for SAI saidata management."""

import logging
import subprocess
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..models.config import RepositoryAuthType
from ..utils.errors import (
    GitOperationError, RepositoryAuthenticationError, RepositoryNetworkError,
    RepositoryIntegrityError, RepositoryNotFoundError, SecurityError
)
from ..utils.security import (
    RepositorySecurityValidator, GitSignatureVerifier, SecurityLevel,
    SecurityValidationResult, GitSignatureInfo
)
from ..utils.credentials import CredentialManager


logger = logging.getLogger(__name__)


@dataclass
class RepositoryInfo:
    """Information about a git repository."""
    url: str
    branch: str
    commit_hash: Optional[str] = None
    last_updated: Optional[datetime] = None
    is_dirty: bool = False
    remote_url: Optional[str] = None


@dataclass
class GitOperationResult:
    """Result of a git operation."""
    success: bool
    message: str
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0


class GitRepositoryHandler:
    """Handles git-based repository operations for SAI saidata management."""
    
    def __init__(self, timeout: int = 300, max_retries: int = 3, security_level: SecurityLevel = SecurityLevel.MODERATE):
        """Initialize the git repository handler.
        
        Args:
            timeout: Timeout for git operations in seconds
            max_retries: Maximum number of retries for failed operations
            security_level: Security validation level
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self._git_available = None
        
        # Initialize security components
        self.security_validator = RepositorySecurityValidator(security_level)
        self.signature_verifier = GitSignatureVerifier()
        self.credential_manager = CredentialManager()
        
        logger.debug(f"Git repository handler initialized with security level: {security_level}")
    
    def is_git_available(self) -> bool:
        """Check if git is available on the system.
        
        Returns:
            True if git is available, False otherwise
        """
        if self._git_available is not None:
            return self._git_available
        
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self._git_available = result.returncode == 0
            if self._git_available:
                logger.debug(f"Git available: {result.stdout.strip()}")
            else:
                logger.warning("Git not available or not working properly")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.warning(f"Git availability check failed: {e}")
            self._git_available = False
        
        return self._git_available
    
    def clone_repository(
        self,
        url: str,
        target_dir: Path,
        branch: str = "main",
        shallow: bool = True,
        auth_type: Optional[RepositoryAuthType] = None,
        auth_data: Optional[Dict[str, str]] = None,
        verify_signatures: bool = True
    ) -> GitOperationResult:
        """Clone a git repository with security validation.
        
        Args:
            url: Repository URL to clone
            target_dir: Target directory for the clone
            branch: Branch to clone (default: main)
            shallow: Whether to perform a shallow clone
            auth_type: Authentication type (ssh, token, basic)
            auth_data: Authentication data (keys, tokens, credentials)
            verify_signatures: Whether to verify git signatures after clone
            
        Returns:
            GitOperationResult with operation status and details
        """
        logger.info(f"Starting git clone operation: {url} -> {target_dir}")
        logger.debug(f"Clone parameters: branch={branch}, shallow={shallow}, auth_type={auth_type}, verify_signatures={verify_signatures}")
        
        # Security validation of repository URL
        url_validation = self.security_validator.validate_repository_url(url)
        if not url_validation.is_valid:
            error_msg = f"Repository URL failed security validation: {', '.join(url_validation.issues)}"
            logger.error(error_msg)
            return GitOperationResult(
                success=False,
                message=error_msg
            )
        
        # Log security warnings if any
        if url_validation.has_warnings:
            for warning in url_validation.warnings:
                logger.warning(f"Repository URL security warning: {warning}")
        
        if not self.is_git_available():
            error_msg = "Git is not available on the system"
            logger.error(error_msg)
            return GitOperationResult(
                success=False,
                message=error_msg
            )
        
        # Validate inputs
        if not url or not target_dir:
            error_msg = "Repository URL and target directory are required"
            logger.error(error_msg)
            return GitOperationResult(
                success=False,
                message=error_msg
            )
        
        # Ensure target directory parent exists
        try:
            target_dir.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            error_msg = f"Failed to create parent directory for {target_dir}: {e}"
            logger.error(error_msg)
            return GitOperationResult(
                success=False,
                message=error_msg
            )
        
        # Prepare clone command
        cmd = ["git", "clone"]
        
        if shallow:
            cmd.extend(["--depth", "1"])
        
        cmd.extend(["--branch", branch, url, str(target_dir)])
        
        # Setup environment for authentication (with credential manager integration)
        env = self._setup_git_environment_secure(url, auth_type, auth_data)
        
        # Execute clone with retries and enhanced error handling
        result = self._execute_git_command_with_retry(cmd, env=env)
        
        if result.success:
            logger.info(f"Git clone completed successfully: {url}")
            
            # Verify the cloned repository
            if not self._verify_repository_integrity(target_dir, url, branch):
                logger.warning(f"Repository integrity verification failed for {url}")
            
            # Verify git signatures if requested
            if verify_signatures:
                signature_result = self._verify_repository_signatures(target_dir)
                if signature_result.has_warnings:
                    for warning in signature_result.warnings:
                        logger.warning(f"Git signature warning: {warning}")
        else:
            logger.error(f"Git clone failed for {url}: {result.message}")
            self._log_git_error_details(result, url, "clone")
        
        return result
    
    def update_repository(
        self,
        repo_dir: Path,
        auth_type: Optional[RepositoryAuthType] = None,
        auth_data: Optional[Dict[str, str]] = None
    ) -> GitOperationResult:
        """Update an existing git repository.
        
        Args:
            repo_dir: Path to the repository directory
            auth_type: Authentication type (ssh, token, basic)
            auth_data: Authentication data (keys, tokens, credentials)
            
        Returns:
            GitOperationResult with operation status and details
        """
        logger.info(f"Starting git update operation for repository: {repo_dir}")
        logger.debug(f"Update parameters: auth_type={auth_type}")
        
        if not self.is_git_available():
            error_msg = "Git is not available on the system"
            logger.error(error_msg)
            return GitOperationResult(
                success=False,
                message=error_msg
            )
        
        if not repo_dir.exists():
            error_msg = f"Repository directory does not exist: {repo_dir}"
            logger.error(error_msg)
            return GitOperationResult(
                success=False,
                message=error_msg
            )
        
        if not (repo_dir / ".git").exists():
            error_msg = f"Directory is not a git repository: {repo_dir}"
            logger.error(error_msg)
            return GitOperationResult(
                success=False,
                message=error_msg
            )
        
        # Get repository info before update
        repo_info = self.get_repository_info(repo_dir)
        if repo_info:
            logger.debug(f"Repository info before update: branch={repo_info.branch}, commit={repo_info.commit_hash}")
        
        # Setup environment for authentication
        env = self._setup_git_environment(auth_type, auth_data)
        
        # First, fetch the latest changes
        logger.debug("Fetching latest changes from remote")
        fetch_cmd = ["git", "-C", str(repo_dir), "fetch", "origin"]
        fetch_result = self._execute_git_command_with_retry(fetch_cmd, env=env)
        
        if not fetch_result.success:
            logger.error(f"Git fetch failed: {fetch_result.message}")
            self._log_git_error_details(fetch_result, str(repo_dir), "fetch")
            return fetch_result
        
        # Get the current branch
        logger.debug("Determining current branch")
        branch_cmd = ["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"]
        branch_result = self._execute_git_command(branch_cmd)
        
        if not branch_result.success:
            error_msg = f"Failed to determine current branch: {branch_result.message}"
            logger.error(error_msg)
            return GitOperationResult(
                success=False,
                message=error_msg
            )
        
        current_branch = branch_result.stdout.strip()
        logger.debug(f"Current branch: {current_branch}")
        
        # Check if there are any changes to pull
        status_cmd = ["git", "-C", str(repo_dir), "status", "--porcelain", "--ahead-behind"]
        status_result = self._execute_git_command(status_cmd)
        
        # Reset to origin/branch
        logger.debug(f"Resetting to origin/{current_branch}")
        reset_cmd = ["git", "-C", str(repo_dir), "reset", "--hard", f"origin/{current_branch}"]
        reset_result = self._execute_git_command(reset_cmd)
        
        if reset_result.success:
            # Get repository info after update
            updated_repo_info = self.get_repository_info(repo_dir)
            if updated_repo_info and repo_info:
                if updated_repo_info.commit_hash != repo_info.commit_hash:
                    logger.info(f"Repository updated: {repo_info.commit_hash} -> {updated_repo_info.commit_hash}")
                else:
                    logger.info("Repository was already up to date")
            
            # Verify repository integrity after update
            if not self._verify_repository_integrity(repo_dir):
                logger.warning(f"Repository integrity verification failed after update: {repo_dir}")
            
            return GitOperationResult(
                success=True,
                message=f"Repository updated successfully to latest {current_branch}",
                stdout=f"{fetch_result.stdout}\n{reset_result.stdout}",
                stderr=f"{fetch_result.stderr}\n{reset_result.stderr}"
            )
        else:
            logger.error(f"Git reset failed: {reset_result.message}")
            self._log_git_error_details(reset_result, str(repo_dir), "reset")
            return reset_result
    
    def get_repository_info(self, repo_dir: Path) -> Optional[RepositoryInfo]:
        """Get information about a git repository.
        
        Args:
            repo_dir: Path to the repository directory
            
        Returns:
            RepositoryInfo object or None if not a valid repository
        """
        if not repo_dir.exists() or not (repo_dir / ".git").exists():
            return None
        
        try:
            # Get remote URL
            remote_cmd = ["git", "-C", str(repo_dir), "remote", "get-url", "origin"]
            remote_result = self._execute_git_command(remote_cmd)
            remote_url = remote_result.stdout.strip() if remote_result.success else None
            
            # Get current branch
            branch_cmd = ["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"]
            branch_result = self._execute_git_command(branch_cmd)
            branch = branch_result.stdout.strip() if branch_result.success else "unknown"
            
            # Get commit hash
            commit_cmd = ["git", "-C", str(repo_dir), "rev-parse", "HEAD"]
            commit_result = self._execute_git_command(commit_cmd)
            commit_hash = commit_result.stdout.strip() if commit_result.success else None
            
            # Check if repository is dirty
            status_cmd = ["git", "-C", str(repo_dir), "status", "--porcelain"]
            status_result = self._execute_git_command(status_cmd)
            is_dirty = bool(status_result.stdout.strip()) if status_result.success else False
            
            # Get last commit date
            date_cmd = ["git", "-C", str(repo_dir), "log", "-1", "--format=%ci"]
            date_result = self._execute_git_command(date_cmd)
            last_updated = None
            if date_result.success and date_result.stdout.strip():
                try:
                    from datetime import datetime
                    # Parse git date format: "2023-12-01 10:30:00 +0000"
                    date_str = date_result.stdout.strip()
                    # Remove timezone info for simpler parsing
                    if ' +' in date_str or ' -' in date_str:
                        date_str = date_str.rsplit(' ', 1)[0]
                    last_updated = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                except (ValueError, IndexError):
                    logger.warning(f"Failed to parse git date: {date_result.stdout.strip()}")
            
            return RepositoryInfo(
                url=remote_url or "unknown",
                branch=branch,
                commit_hash=commit_hash,
                last_updated=last_updated,
                is_dirty=is_dirty,
                remote_url=remote_url
            )
            
        except Exception as e:
            logger.error(f"Failed to get repository info for {repo_dir}: {e}")
            return None
    
    def _setup_git_environment(
        self,
        auth_type: Optional[RepositoryAuthType],
        auth_data: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """Setup environment variables for git authentication.
        
        Args:
            auth_type: Authentication type
            auth_data: Authentication data
            
        Returns:
            Environment variables dict or None
        """
        if not auth_type or not auth_data:
            return None
        
        env = {}
        
        if auth_type == RepositoryAuthType.TOKEN:
            # For token authentication, we can use credential helper
            token = auth_data.get("token")
            if token:
                # Set up credential helper for token authentication
                env["GIT_ASKPASS"] = "echo"
                env["GIT_USERNAME"] = auth_data.get("username", "token")
                env["GIT_PASSWORD"] = token
        
        elif auth_type == RepositoryAuthType.SSH:
            # For SSH authentication, set SSH key path
            ssh_key_path = auth_data.get("ssh_key_path")
            if ssh_key_path and Path(ssh_key_path).exists():
                env["GIT_SSH_COMMAND"] = f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no"
        
        elif auth_type == RepositoryAuthType.BASIC:
            # For basic authentication
            username = auth_data.get("username")
            password = auth_data.get("password")
            if username and password:
                env["GIT_ASKPASS"] = "echo"
                env["GIT_USERNAME"] = username
                env["GIT_PASSWORD"] = password
        
        return env if env else None
    
    def _setup_git_environment_secure(
        self,
        repository_url: str,
        auth_type: Optional[RepositoryAuthType],
        auth_data: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """Setup environment variables for git authentication with credential manager integration.
        
        Args:
            repository_url: Repository URL for credential lookup
            auth_type: Authentication type
            auth_data: Authentication data
            
        Returns:
            Environment variables dict or None
        """
        # First try provided auth_data
        if auth_type and auth_data:
            return self._setup_git_environment(auth_type, auth_data)
        
        # Try to get credentials from credential manager
        stored_credentials = self.credential_manager.get_credentials(repository_url)
        if stored_credentials:
            logger.debug(f"Using stored credentials for {repository_url}")
            
            auth_type_str = stored_credentials.get('auth_type')
            if auth_type_str == 'ssh':
                return self._setup_git_environment(
                    RepositoryAuthType.SSH,
                    {'ssh_key_path': stored_credentials.get('ssh_key_path')}
                )
            elif auth_type_str == 'token':
                return self._setup_git_environment(
                    RepositoryAuthType.TOKEN,
                    {'token': stored_credentials.get('token')}
                )
            elif auth_type_str == 'basic':
                return self._setup_git_environment(
                    RepositoryAuthType.BASIC,
                    {
                        'username': stored_credentials.get('username'),
                        'password': stored_credentials.get('password')
                    }
                )
        
        return None
    
    def _verify_repository_signatures(self, repo_path: Path) -> SecurityValidationResult:
        """Verify git signatures in the repository.
        
        Args:
            repo_path: Path to git repository
            
        Returns:
            SecurityValidationResult with signature verification details
        """
        issues = []
        warnings = []
        recommendations = []
        
        logger.debug(f"Verifying git signatures in {repo_path}")
        
        # Check if GPG is available for signature verification
        if not self.signature_verifier.is_gpg_available():
            warnings.append("GPG not available - cannot verify commit signatures")
            recommendations.append("Install GPG to enable signature verification")
        else:
            # Verify HEAD commit signature
            head_signature = self.signature_verifier.verify_commit_signature(repo_path)
            
            if head_signature.is_signed:
                if head_signature.is_valid:
                    logger.info(f"HEAD commit signature is valid (signer: {head_signature.signer})")
                else:
                    warnings.append(f"HEAD commit signature is invalid: {head_signature.error_message}")
                    recommendations.append("Verify the repository source and consider using a different branch or commit")
            else:
                warnings.append("HEAD commit is not signed")
                recommendations.append("Consider using repositories with signed commits for better security")
            
            # Check for signed tags
            try:
                # Get recent tags
                result = subprocess.run(
                    ['git', '-C', str(repo_path), 'tag', '--sort=-version:refname'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    tags = result.stdout.strip().split('\n')[:5]  # Check up to 5 recent tags
                    signed_tags = 0
                    
                    for tag in tags:
                        tag_signature = self.signature_verifier.verify_tag_signature(repo_path, tag.strip())
                        if tag_signature.is_signed and tag_signature.is_valid:
                            signed_tags += 1
                    
                    if signed_tags > 0:
                        logger.info(f"Found {signed_tags} signed tags out of {len(tags)} recent tags")
                    else:
                        warnings.append("No signed tags found in recent releases")
                        recommendations.append("Consider using repositories with signed releases")
                        
            except Exception as e:
                logger.debug(f"Could not check tag signatures: {e}")
        
        is_valid = len(issues) == 0
        
        return SecurityValidationResult(
            is_valid=is_valid,
            security_level=self.security_validator.security_level,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def store_repository_credentials(
        self,
        repository_url: str,
        auth_type: RepositoryAuthType,
        auth_data: Dict[str, str]
    ) -> bool:
        """Store repository credentials securely.
        
        Args:
            repository_url: Repository URL
            auth_type: Authentication type
            auth_data: Authentication data
            
        Returns:
            True if stored successfully, False otherwise
        """
        logger.debug(f"Storing credentials for repository: {repository_url}")
        
        try:
            if auth_type == RepositoryAuthType.SSH:
                ssh_key_path = auth_data.get('ssh_key_path')
                if ssh_key_path:
                    return self.credential_manager.store_ssh_key(
                        repository_url,
                        ssh_key_path,
                        auth_data.get('username')
                    )
            
            elif auth_type == RepositoryAuthType.TOKEN:
                token = auth_data.get('token')
                if token:
                    return self.credential_manager.store_access_token(
                        repository_url,
                        token,
                        auth_data.get('username')
                    )
            
            elif auth_type == RepositoryAuthType.BASIC:
                username = auth_data.get('username')
                password = auth_data.get('password')
                if username and password:
                    return self.credential_manager.store_username_password(
                        repository_url,
                        username,
                        password
                    )
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to store repository credentials: {e}")
            return False
    
    def get_repository_signature_info(self, repo_path: Path) -> Dict[str, Any]:
        """Get comprehensive signature information for a repository.
        
        Args:
            repo_path: Path to git repository
            
        Returns:
            Dictionary with signature information
        """
        info = {
            'gpg_available': self.signature_verifier.is_gpg_available(),
            'head_commit_signature': None,
            'recent_tags_signatures': [],
            'signature_summary': {
                'signed_commits': 0,
                'valid_signatures': 0,
                'signed_tags': 0,
                'valid_tag_signatures': 0
            }
        }
        
        if not info['gpg_available']:
            return info
        
        try:
            # Check HEAD commit
            head_signature = self.signature_verifier.verify_commit_signature(repo_path)
            info['head_commit_signature'] = {
                'is_signed': head_signature.is_signed,
                'is_valid': head_signature.is_valid,
                'signer': head_signature.signer,
                'key_id': head_signature.key_id,
                'error_message': head_signature.error_message
            }
            
            if head_signature.is_signed:
                info['signature_summary']['signed_commits'] = 1
                if head_signature.is_valid:
                    info['signature_summary']['valid_signatures'] = 1
            
            # Check recent tags
            result = subprocess.run(
                ['git', '-C', str(repo_path), 'tag', '--sort=-version:refname'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                tags = result.stdout.strip().split('\n')[:10]  # Check up to 10 recent tags
                
                for tag in tags:
                    tag = tag.strip()
                    if not tag:
                        continue
                    
                    tag_signature = self.signature_verifier.verify_tag_signature(repo_path, tag)
                    tag_info = {
                        'tag': tag,
                        'is_signed': tag_signature.is_signed,
                        'is_valid': tag_signature.is_valid,
                        'signer': tag_signature.signer,
                        'key_id': tag_signature.key_id,
                        'error_message': tag_signature.error_message
                    }
                    
                    info['recent_tags_signatures'].append(tag_info)
                    
                    if tag_signature.is_signed:
                        info['signature_summary']['signed_tags'] += 1
                        if tag_signature.is_valid:
                            info['signature_summary']['valid_tag_signatures'] += 1
        
        except Exception as e:
            logger.error(f"Failed to get signature information: {e}")
        
        return info
    
    def _execute_git_command(
        self,
        cmd: list,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Path] = None
    ) -> GitOperationResult:
        """Execute a git command.
        
        Args:
            cmd: Command to execute
            env: Environment variables
            cwd: Working directory
            
        Returns:
            GitOperationResult with command execution details
        """
        try:
            # Merge environment variables
            full_env = None
            if env:
                import os
                full_env = os.environ.copy()
                full_env.update(env)
            
            logger.debug(f"Executing git command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=full_env,
                cwd=cwd
            )
            
            success = result.returncode == 0
            message = "Command executed successfully" if success else f"Command failed with return code {result.returncode}"
            
            if not success:
                logger.error(f"Git command failed: {' '.join(cmd)}")
                logger.error(f"Stderr: {result.stderr}")
            
            return GitOperationResult(
                success=success,
                message=message,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
            
        except subprocess.TimeoutExpired:
            error_msg = f"Git command timed out after {self.timeout} seconds"
            logger.error(error_msg)
            return GitOperationResult(
                success=False,
                message=error_msg,
                return_code=-1
            )
        
        except Exception as e:
            error_msg = f"Failed to execute git command: {e}"
            logger.error(error_msg)
            return GitOperationResult(
                success=False,
                message=error_msg,
                return_code=-1
            )
    
    def _execute_git_command_with_retry(
        self,
        cmd: list,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Path] = None
    ) -> GitOperationResult:
        """Execute a git command with retry logic.
        
        Args:
            cmd: Command to execute
            env: Environment variables
            cwd: Working directory
            
        Returns:
            GitOperationResult with command execution details
        """
        last_result = None
        
        for attempt in range(self.max_retries):
            result = self._execute_git_command(cmd, env, cwd)
            
            if result.success:
                if attempt > 0:
                    logger.info(f"Git command succeeded on attempt {attempt + 1}")
                return result
            
            last_result = result
            
            if attempt < self.max_retries - 1:
                # Exponential backoff: 1s, 2s, 4s, etc.
                delay = 2 ** attempt
                logger.warning(f"Git command failed (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s...")
                time.sleep(delay)
        
        logger.error(f"Git command failed after {self.max_retries} attempts")
        return last_result or GitOperationResult(
            success=False,
            message=f"Command failed after {self.max_retries} attempts"
        )
    
    def _verify_repository_integrity(self, repo_dir: Path, expected_url: Optional[str] = None, 
                                   expected_branch: Optional[str] = None) -> bool:
        """Verify repository integrity after clone/update operations.
        
        Args:
            repo_dir: Path to repository directory
            expected_url: Expected repository URL (for clone verification)
            expected_branch: Expected branch name (for clone verification)
            
        Returns:
            True if repository integrity is verified, False otherwise
        """
        try:
            logger.debug(f"Verifying repository integrity: {repo_dir}")
            
            # Check if .git directory exists
            if not (repo_dir / ".git").exists():
                logger.error(f"Repository integrity check failed: .git directory missing in {repo_dir}")
                return False
            
            # Get repository info
            repo_info = self.get_repository_info(repo_dir)
            if not repo_info:
                logger.error(f"Repository integrity check failed: unable to get repository info for {repo_dir}")
                return False
            
            # Verify remote URL if provided
            if expected_url and repo_info.remote_url:
                # Normalize URLs for comparison (handle .git suffix, trailing slashes, etc.)
                normalized_expected = self._normalize_git_url(expected_url)
                normalized_actual = self._normalize_git_url(repo_info.remote_url)
                
                if normalized_expected != normalized_actual:
                    logger.error(f"Repository integrity check failed: URL mismatch. "
                               f"Expected: {normalized_expected}, Actual: {normalized_actual}")
                    return False
            
            # Verify branch if provided
            if expected_branch and repo_info.branch != expected_branch:
                logger.error(f"Repository integrity check failed: branch mismatch. "
                           f"Expected: {expected_branch}, Actual: {repo_info.branch}")
                return False
            
            # Check if repository is in a clean state (no uncommitted changes)
            if repo_info.is_dirty:
                logger.warning(f"Repository has uncommitted changes: {repo_dir}")
            
            # Verify we have a valid commit hash
            if not repo_info.commit_hash:
                logger.error(f"Repository integrity check failed: no valid commit hash for {repo_dir}")
                return False
            
            logger.debug(f"Repository integrity verification passed for {repo_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Repository integrity verification failed with exception: {e}")
            return False
    
    def _normalize_git_url(self, url: str) -> str:
        """Normalize git URL for comparison.
        
        Args:
            url: Git URL to normalize
            
        Returns:
            Normalized URL
        """
        # Remove .git suffix if present
        if url.endswith('.git'):
            url = url[:-4]
        
        # Remove trailing slash
        url = url.rstrip('/')
        
        # Convert SSH URLs to HTTPS for comparison
        if url.startswith('git@github.com:'):
            url = url.replace('git@github.com:', 'https://github.com/')
        
        return url.lower()
    
    def _log_git_error_details(self, result: GitOperationResult, repository_url: str, operation: str) -> None:
        """Log detailed error information for git operation failures.
        
        Args:
            result: Failed GitOperationResult
            repository_url: Repository URL
            operation: Git operation that failed
        """
        logger.error(f"Git {operation} operation failed for {repository_url}")
        logger.error(f"Exit code: {result.return_code}")
        
        if result.stderr:
            # Log stderr with context
            stderr_lines = result.stderr.strip().split('\n')
            logger.error(f"Git stderr ({len(stderr_lines)} lines):")
            for i, line in enumerate(stderr_lines[:10]):  # Log first 10 lines
                logger.error(f"  {i+1}: {line}")
            if len(stderr_lines) > 10:
                logger.error(f"  ... and {len(stderr_lines) - 10} more lines")
        
        if result.stdout:
            # Log stdout for debugging
            stdout_lines = result.stdout.strip().split('\n')
            logger.debug(f"Git stdout ({len(stdout_lines)} lines):")
            for i, line in enumerate(stdout_lines[:5]):  # Log first 5 lines
                logger.debug(f"  {i+1}: {line}")
        
        # Analyze error and provide specific guidance
        self._analyze_git_error(result.stderr or "", repository_url, operation)
    
    def _analyze_git_error(self, stderr: str, repository_url: str, operation: str) -> None:
        """Analyze git error output and provide specific guidance.
        
        Args:
            stderr: Git command stderr output
            repository_url: Repository URL
            operation: Git operation that failed
        """
        stderr_lower = stderr.lower()
        
        # Authentication errors
        if any(phrase in stderr_lower for phrase in [
            'authentication failed', 'permission denied', 'access denied',
            'could not read username', 'could not read password'
        ]):
            logger.error("Git authentication failed - check your credentials")
            logger.info("Authentication troubleshooting:")
            logger.info("  - For HTTPS: ensure your username/password or token is correct")
            logger.info("  - For SSH: verify your SSH key is configured and added to your SSH agent")
            logger.info("  - For private repositories: ensure you have access permissions")
        
        # Network connectivity errors
        elif any(phrase in stderr_lower for phrase in [
            'could not resolve host', 'connection timed out', 'network is unreachable',
            'temporary failure in name resolution'
        ]):
            logger.error("Network connectivity issue detected")
            logger.info("Network troubleshooting:")
            logger.info("  - Check your internet connection")
            logger.info("  - Verify DNS resolution is working")
            logger.info("  - Check if you're behind a firewall or proxy")
        
        # Repository not found errors
        elif any(phrase in stderr_lower for phrase in [
            'repository not found', 'does not exist', 'not found'
        ]):
            logger.error("Repository not found or inaccessible")
            logger.info("Repository troubleshooting:")
            logger.info(f"  - Verify the repository URL is correct: {repository_url}")
            logger.info("  - Check if the repository exists and is accessible")
            logger.info("  - For private repositories: ensure you have access permissions")
        
        # Branch/reference errors
        elif any(phrase in stderr_lower for phrase in [
            'remote branch', 'does not exist', 'reference not found'
        ]):
            logger.error("Branch or reference not found")
            logger.info("Branch troubleshooting:")
            logger.info("  - Check if the specified branch exists in the remote repository")
            logger.info("  - Verify the branch name is spelled correctly")
            logger.info("  - Try using 'main' or 'master' as the branch name")
        
        # Disk space errors
        elif any(phrase in stderr_lower for phrase in [
            'no space left', 'disk full', 'insufficient space'
        ]):
            logger.error("Insufficient disk space for git operation")
            logger.info("Disk space troubleshooting:")
            logger.info("  - Free up disk space on your system")
            logger.info("  - Check available space in the target directory")
            logger.info("  - Consider using a different location with more space")
        
        # Permission errors
        elif any(phrase in stderr_lower for phrase in [
            'permission denied', 'access denied', 'operation not permitted'
        ]):
            logger.error("Permission denied for git operation")
            logger.info("Permission troubleshooting:")
            logger.info("  - Check file/directory permissions")
            logger.info("  - Ensure you have write access to the target directory")
            logger.info("  - Try running with appropriate privileges if needed")
        
        else:
            # Generic error guidance
            logger.info("General git troubleshooting:")
            logger.info("  - Try running the git command manually for more details")
            logger.info("  - Check git configuration with 'git config --list'")
            logger.info("  - Ensure git is properly installed and up to date")