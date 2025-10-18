"""Saidata repository manager for SAI saidata management."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models.config import RepositoryAuthType, SaiConfig
from ..models.saidata import SaiData
from ..utils.errors import (
    RepositoryError,
)
from ..utils.system import (
    NetworkConnectivityTracker,
    check_url_accessibility,
    detect_offline_mode,
)
from .git_repository_handler import GitOperationResult, GitRepositoryHandler, RepositoryInfo
from .repository_cache import RepositoryCache
from .saidata_loader import SaidataLoader, SaidataNotFoundError
from .tarball_repository_handler import TarballOperationResult, TarballRepositoryHandler

logger = logging.getLogger(__name__)


class RepositoryStatus(str, Enum):
    """Repository status enumeration."""

    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UPDATING = "updating"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class RepositoryHealthCheck:
    """Repository health check result."""

    status: RepositoryStatus
    last_updated: Optional[datetime] = None
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    repository_info: Optional[RepositoryInfo] = None
    cache_valid: bool = False
    update_available: bool = False

    @property
    def is_healthy(self) -> bool:
        """Check if repository is in a healthy state."""
        return self.status in [RepositoryStatus.AVAILABLE, RepositoryStatus.OFFLINE]

    @property
    def needs_update(self) -> bool:
        """Check if repository needs an update."""
        return self.update_available or self.status == RepositoryStatus.ERROR


class SaidataRepositoryManager:
    """Central coordinator for saidata repository operations and lifecycle management."""

    def __init__(self, config: Optional[SaiConfig] = None):
        """Initialize the repository manager.

        Args:
            config: SAI configuration object. If None, uses default configuration.
        """
        self.config = config or SaiConfig()

        # Initialize repository cache
        self.repository_cache = RepositoryCache(self.config)

        # Initialize repository handlers with security features
        from ..utils.security import SecurityLevel

        security_level = getattr(config, "security_level", SecurityLevel.MODERATE)

        self.git_handler = GitRepositoryHandler(
            timeout=self.config.saidata_repository_timeout,
            max_retries=3,
            security_level=security_level,
        )
        self.tarball_handler = TarballRepositoryHandler(
            timeout=self.config.saidata_repository_timeout,
            max_retries=3,
            security_level=security_level,
        )

        # Initialize saidata loader with repository-aware configuration
        self._setup_repository_paths()
        self.saidata_loader = SaidataLoader(self.config, repository_manager=self)

        # Repository state tracking
        self._last_update_check: Optional[datetime] = None
        self._repository_status: RepositoryStatus = RepositoryStatus.UNKNOWN
        self._last_error: Optional[str] = None

        # Offline mode and network tracking
        self._network_tracker = NetworkConnectivityTracker()
        self._offline_mode_detected: Optional[bool] = None
        self._last_network_check: Optional[datetime] = None
        self._network_check_interval = 300  # Check network every 5 minutes

        # Ensure repository cache directory exists
        self.repository_cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def repository_cache_dir(self) -> Path:
        """Get the repository cache directory."""
        return self.config.saidata_repository_cache_dir

    @property
    def repository_path(self) -> Path:
        """Get the path to the cached repository."""
        # Use repository cache to get the path
        cached_path = self.repository_cache.get_repository_path(
            self.config.saidata_repository_url, self.config.saidata_repository_branch
        )
        if cached_path:
            return cached_path

        # Fall back to generating path if not cached
        repo_name = self._get_repository_name()
        return self.repository_cache_dir / repo_name

    def get_saidata(self, software_name: str, force_update: bool = False) -> Optional[SaiData]:
        """Get saidata for the specified software.

        Args:
            software_name: Name of the software to get saidata for
            force_update: Whether to force a repository update before loading

        Returns:
            SaiData object if found, None otherwise

        Raises:
            SaidataNotFoundError: If saidata is not found
            RepositoryError: If repository operations fail and no cached data is available
        """
        logger.info(f"Getting saidata for software: {software_name}")
        logger.debug(f"Parameters: force_update={force_update}")

        # Log repository status before operation
        health_check = self.get_repository_status()
        logger.debug(
            f"Repository status: {health_check.status}, cache_valid={health_check.cache_valid}"
        )

        # Check if we're in offline mode and warn about cache usage
        if self.is_offline_mode() and self.repository_path.exists():
            cache_age = self.get_cached_repository_age()
            if cache_age:
                self.warn_about_stale_cache(cache_age)

        # Update repository if needed (unless in offline mode)
        if (force_update or self._should_update_repository()) and not self.is_offline_mode():
            logger.info(f"Repository update required for {software_name}")
            try:
                update_result = self.update_repository(force=force_update)
                if not update_result and not self.repository_path.exists():
                    error_msg = f"Failed to fetch repository and no cached data available for {software_name}"
                    logger.error(error_msg)
                    raise RepositoryError(
                        self.config.saidata_repository_url,
                        "fetch_saidata",
                        details={"software_name": software_name},
                    )
            except Exception as e:
                if not self.repository_path.exists():
                    logger.error(f"Repository update failed and no cache available: {e}")
                    raise
                else:
                    logger.warning(f"Repository update failed, using cached data: {e}")
        elif self.is_offline_mode():
            logger.debug(f"Offline mode active, skipping repository update for {software_name}")

        # Load saidata using the repository-aware loader
        try:
            logger.debug(f"Loading saidata for {software_name} from repository")
            saidata = self.saidata_loader.load_saidata(software_name)
            logger.info(f"Successfully loaded saidata for {software_name}")
            return saidata

        except SaidataNotFoundError:
            # If not found and we haven't updated recently, try updating once (unless offline)
            if not force_update and self._should_retry_with_update() and not self.is_offline_mode():
                logger.info(
                    f"Saidata not found for {software_name}, attempting repository update..."
                )
                try:
                    update_result = self.update_repository(force=True)
                    if update_result:
                        logger.debug(
                            f"Repository updated, retrying saidata load for {software_name}"
                        )
                        return self.saidata_loader.load_saidata(software_name)
                    else:
                        logger.warning(f"Repository update failed during retry for {software_name}")
                except Exception as e:
                    logger.warning(f"Repository update failed during retry: {e}")
            elif self.is_offline_mode():
                logger.debug(
                    f"Saidata not found for {software_name} and offline mode active - no retry attempted")

            # Log detailed information about the failed search
            self._log_saidata_search_failure(software_name)
            raise

    def update_repository(self, force: bool = False) -> bool:
        """Update the saidata repository.

        Args:
            force: Whether to force update regardless of cache validity

        Returns:
            True if update was successful, False otherwise
        """
        logger.info(f"Starting repository update: {self.config.saidata_repository_url}")
        logger.debug(
            f"Update parameters: force={force}, offline_mode={self.config.saidata_offline_mode}"
        )

        # Check offline mode (both explicit and detected)
        if self.is_offline_mode():
            logger.info("Offline mode active, skipping repository update")
            cache_exists = self.repository_path.exists()
            if cache_exists:
                cache_age = self.get_cached_repository_age()
                if cache_age:
                    self.warn_about_stale_cache(cache_age)
                logger.info("Using existing cached repository in offline mode")
            else:
                logger.warning("No cached repository available in offline mode")
            return cache_exists

        # Check if we should attempt network operations based on failure history
        should_attempt, delay = self.should_attempt_network_operation()
        if not should_attempt:
            logger.warning("Network operations blocked due to repeated failures")
            cache_exists = self.repository_path.exists()
            if cache_exists:
                cache_age = self.get_cached_repository_age()
                if cache_age:
                    self.warn_about_stale_cache(cache_age)
                logger.info("Using cached repository due to network issues")
            return cache_exists

        # Apply exponential backoff delay if needed
        if delay > 0:
            logger.info(f"Applying network backoff delay: {delay}s")
            time.sleep(delay)

        # Check repository cache validity
        if not force and self.repository_cache.is_repository_valid(
            self.config.saidata_repository_url, self.config.saidata_repository_branch
        ):
            logger.debug("Repository cache is valid, no update needed")
            return True

        # Log current repository status
        current_status = self.get_repository_status()
        logger.debug(f"Current repository status: {current_status.status}")
        if current_status.last_updated:
            age = datetime.now() - current_status.last_updated
            logger.debug(f"Repository age: {age.total_seconds():.0f} seconds")

        logger.info(f"Updating saidata repository from {self.config.saidata_repository_url}")
        self._repository_status = RepositoryStatus.UPDATING

        update_start_time = datetime.now()

        try:
            # Try git first if available
            if self.git_handler.is_git_available():
                logger.info("Attempting git-based repository update")
                result = self._update_with_git()
                if result:
                    update_duration = (datetime.now() - update_start_time).total_seconds()
                    logger.info(
                        f"Git repository update completed successfully in {update_duration:.2f}s"
                    )
                    self._mark_update_successful(is_git_repo=True)
                    self._validate_repository_structure()
                    return True

                logger.warning("Git update failed, falling back to tarball download")
            else:
                logger.info("Git not available, using tarball download method")

            # Fall back to tarball download
            logger.info("Attempting tarball-based repository update")
            result = self._update_with_tarball()
            if result:
                update_duration = (datetime.now() - update_start_time).total_seconds()
                logger.info(
                    f"Tarball repository update completed successfully in {update_duration:.2f}s"
                )
                self._mark_update_successful(is_git_repo=False)
                self._validate_repository_structure()
                return True

            # Both methods failed - record network failure and check for cached fallback
            error_msg = "Both git and tarball update methods failed"
            logger.error(error_msg)
            self._network_tracker.record_failure()
            self._mark_update_failed(error_msg)

            # Check if we can fall back to cached repository
            if self.repository_path.exists():
                cache_age = self.get_cached_repository_age()
                if cache_age:
                    self.warn_about_stale_cache(cache_age)

                logger.warning("Repository update failed, falling back to cached version")
                logger.info("The cached repository will be used for this operation")

                # Check if cache is very old and suggest actions
                if cache_age and cache_age.days > 7:
                    logger.warning("Cached repository is quite old. Consider:")
                    logger.warning("  - Checking your internet connection")
                    logger.warning("  - Trying the update again later")
                    logger.warning("  - Verifying the repository URL is correct")

                return True  # Return True since we have cached data to use
            else:
                logger.error("No cached repository available and update failed")
                logger.error("Cannot proceed without repository data")
                logger.info("Troubleshooting suggestions:")
                logger.info("  - Check your internet connection")
                logger.info("  - Verify the repository URL is correct")
                logger.info("  - Check authentication credentials if using a private repository")
                logger.info("  - Try again when network connectivity is restored")
                return False

        except Exception as e:
            error_msg = f"Unexpected error during repository update: {e}"
            logger.error(error_msg, exc_info=True)
            self._network_tracker.record_failure()
            self._mark_update_failed(error_msg)

            # Even with unexpected errors, try to use cached data if available
            if self.repository_path.exists():
                cache_age = self.get_cached_repository_age()
                if cache_age:
                    self.warn_about_stale_cache(cache_age)

                logger.warning("Unexpected error during update, falling back to cached repository")
                return True

            return False

    def get_repository_status(self) -> RepositoryHealthCheck:
        """Get comprehensive repository status and health information.

        Returns:
            RepositoryHealthCheck with current repository status
        """
        health_check = RepositoryHealthCheck(
            status=self._repository_status,
            last_check=datetime.now(),
            error_message=self._last_error,
        )

        # Check offline mode first
        if self.is_offline_mode():
            if self.repository_path.exists():
                # Get repository information
                repo_info = self.git_handler.get_repository_info(self.repository_path)
                health_check.repository_info = repo_info
                health_check.last_updated = self._get_last_update_time()
                health_check.status = RepositoryStatus.OFFLINE
                health_check.error_message = "Operating in offline mode"

                # In offline mode, cache is considered "valid" if it exists
                health_check.cache_valid = True
                health_check.update_available = False  # Can't update in offline mode
            else:
                health_check.status = RepositoryStatus.OFFLINE
                health_check.error_message = "Repository not cached and offline mode active"
                health_check.cache_valid = False
        elif self.repository_path.exists():
            # Get repository information
            repo_info = self.git_handler.get_repository_info(self.repository_path)
            health_check.repository_info = repo_info

            # Check cache validity
            health_check.cache_valid = self._is_cache_valid()
            health_check.last_updated = self._get_last_update_time()

            # Determine if update is available (simplified check)
            if not health_check.cache_valid:
                health_check.update_available = True

            # Update status based on repository state and network connectivity
            if self._repository_status == RepositoryStatus.UNKNOWN:
                # Check network accessibility to determine if we're effectively offline
                is_accessible, error_msg = self.check_repository_accessibility()
                if is_accessible:
                    health_check.status = RepositoryStatus.AVAILABLE
                else:
                    health_check.status = RepositoryStatus.OFFLINE
                    health_check.error_message = f"Repository not accessible: {error_msg}"
            else:
                health_check.status = self._repository_status
        else:
            # Repository doesn't exist locally
            if self.is_offline_mode():
                health_check.status = RepositoryStatus.OFFLINE
                health_check.error_message = "Repository not cached and offline mode active"
            else:
                health_check.status = RepositoryStatus.ERROR
                health_check.error_message = "Repository not found locally"

        return health_check

    def configure_repository(
        self,
        url: str,
        branch: str = "main",
        auth_type: Optional[RepositoryAuthType] = None,
        auth_data: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Configure repository settings.

        Args:
            url: Repository URL
            branch: Repository branch
            auth_type: Authentication type
            auth_data: Authentication data

        Returns:
            True if configuration was successful, False otherwise
        """
        try:
            # Validate URL format
            if not url or not any(
                url.startswith(prefix)
                for prefix in ["http://", "https://", "git://", "ssh://", "git@"]
            ):
                logger.error(f"Invalid repository URL format: {url}")
                return False

            # Store old repository path before updating configuration
            old_url = self.config.saidata_repository_url
            old_repository_path = self.repository_path

            # Update configuration
            self.config.saidata_repository_url = url
            self.config.saidata_repository_branch = branch
            self.config.saidata_repository_auth_type = auth_type
            self.config.saidata_repository_auth_data = auth_data or {}

            # If URL changed, remove old repository cache
            if old_url != url and old_repository_path.exists():
                logger.info("Repository URL changed, clearing old cache")
                import shutil

                shutil.rmtree(old_repository_path)

            # Update repository paths
            self._setup_repository_paths()

            # Reset status to trigger fresh update
            self._repository_status = RepositoryStatus.UNKNOWN
            self._last_update_check = None

            logger.info(f"Repository configured: {url} (branch: {branch})")
            return True

        except Exception as e:
            logger.error(f"Failed to configure repository: {e}")
            return False

    def cleanup_old_repositories(self, keep_days: int = 7) -> int:
        """Clean up old repository caches.

        Args:
            keep_days: Number of days to keep old repositories

        Returns:
            Number of repositories cleaned up
        """
        # Use repository cache cleanup methods
        expired_count = self.repository_cache.cleanup_expired_repositories()
        old_count = self.repository_cache.cleanup_old_repositories(max_age_days=keep_days)
        invalid_count = self.repository_cache.cleanup_invalid_repositories()

        total_cleaned = expired_count + old_count + invalid_count

        if total_cleaned > 0:
            logger.info(
                f"Cleaned up {total_cleaned} repository caches "
                f"(expired: {expired_count}, old: {old_count}, invalid: {invalid_count})"
            )

        return total_cleaned

    def get_cache_status(self) -> Dict[str, Any]:
        """Get comprehensive repository cache status.

        Returns:
            Dictionary with cache status information
        """
        return self.repository_cache.get_cache_status()

    def clear_repository_cache(self, url: Optional[str] = None, branch: str = "main") -> bool:
        """Clear repository cache.

        Args:
            url: Repository URL to clear, or None for current repository
            branch: Repository branch to clear

        Returns:
            True if cache was cleared, False if no cache existed
        """
        target_url = url or self.config.saidata_repository_url
        return self.repository_cache.clear_repository_cache(target_url, branch)

    def clear_all_repository_cache(self) -> int:
        """Clear all repository caches.

        Returns:
            Number of repositories cleared
        """
        return self.repository_cache.clear_all_repository_cache()

    def get_all_cached_repositories(self) -> List[Dict[str, Any]]:
        """Get status information for all cached repositories.

        Returns:
            List of repository status information
        """
        repositories = self.repository_cache.get_all_repositories()
        return [
            {
                "url": repo.url,
                "branch": repo.branch,
                "local_path": str(repo.local_path),
                "is_git_repo": repo.is_git_repo,
                "last_updated": repo.last_updated.isoformat() if repo.last_updated else None,
                "age_seconds": repo.age_seconds,
                "age_hours": repo.age_hours,
                "age_days": repo.age_days,
                "is_expired": repo.is_expired,
                "size_mb": repo.size_mb,
                "file_count": repo.file_count,
                "exists": repo.exists,
                "error_message": repo.error_message,
            }
            for repo in repositories
        ]

    def get_network_status(self) -> Dict[str, Any]:
        """Get network connectivity and failure status.

        Returns:
            Dictionary with network status information
        """
        is_offline = self.is_offline_mode()
        failure_count = self._network_tracker.get_failure_count()
        backoff_delay = self._network_tracker.get_backoff_delay()

        status = {
            "offline_mode_configured": self.config.saidata_offline_mode,
            "offline_mode_detected": self._offline_mode_detected,
            "offline_mode_active": is_offline,
            "network_failure_count": failure_count,
            "current_backoff_delay": backoff_delay,
            "last_network_check": self._last_network_check.isoformat()
            if self._last_network_check
            else None,
        }

        # Add repository accessibility status if not offline
        if not is_offline:
            is_accessible, error_msg = self.check_repository_accessibility()
            status["repository_accessible"] = is_accessible
            if error_msg:
                status["repository_error"] = error_msg

        return status

    def reset_network_failures(self) -> None:
        """Reset network failure tracking.

        This can be useful for testing or when network issues are resolved.
        """
        logger.info("Resetting network failure tracking")
        self._network_tracker.record_success()
        self._offline_mode_detected = None
        self._last_network_check = None

    def _setup_repository_paths(self) -> None:
        """Setup saidata paths to prioritize repository cache."""
        repo_path = str(self.repository_path)

        # Ensure repository path is first in saidata_paths
        if repo_path not in self.config.saidata_paths:
            self.config.saidata_paths.insert(0, repo_path)
        elif self.config.saidata_paths[0] != repo_path:
            # Move to front if not already there
            self.config.saidata_paths.remove(repo_path)
            self.config.saidata_paths.insert(0, repo_path)

        # Update the saidata loader if it exists
        if hasattr(self, "saidata_loader") and self.saidata_loader:
            # Reinitialize the path resolver with updated paths
            from .saidata_path import HierarchicalPathResolver

            search_paths = self.saidata_loader.get_search_paths()
            self.saidata_loader._path_resolver = HierarchicalPathResolver(search_paths)

    def is_offline_mode(self) -> bool:
        """Check if the system should operate in offline mode.

        Returns:
            True if offline mode is enabled or detected, False otherwise
        """
        # Check explicit offline mode configuration
        if self.config.saidata_offline_mode:
            logger.debug("Offline mode explicitly enabled in configuration")
            return True

        # Check if we need to refresh network detection
        now = datetime.now()
        if (
            self._last_network_check is None
            or (now - self._last_network_check).total_seconds() > self._network_check_interval
        ):
            logger.debug("Checking network connectivity for offline mode detection")
            is_offline, reason = detect_offline_mode()
            self._offline_mode_detected = is_offline
            self._last_network_check = now

            if is_offline:
                logger.info(f"Offline mode detected: {reason}")
            else:
                logger.debug(f"Network connectivity available: {reason}")

        return self._offline_mode_detected or False

    def check_repository_accessibility(self) -> Tuple[bool, Optional[str]]:
        """Check if the configured repository is accessible.

        Returns:
            Tuple of (is_accessible, error_message)
        """
        if self.is_offline_mode():
            return False, "Operating in offline mode"

        url = self.config.saidata_repository_url
        logger.debug(f"Checking accessibility of repository: {url}")

        is_accessible, error_msg = check_url_accessibility(url, timeout=10)

        if not is_accessible:
            logger.debug(f"Repository not accessible: {error_msg}")
            self._network_tracker.record_failure()
        else:
            logger.debug("Repository is accessible")
            self._network_tracker.record_success()

        return is_accessible, error_msg

    def should_attempt_network_operation(self) -> Tuple[bool, float]:
        """Check if we should attempt a network operation based on failure history.

        Returns:
            Tuple of (should_attempt, delay_seconds)
        """
        if self.is_offline_mode():
            return False, 0.0

        should_retry, delay = self._network_tracker.should_retry()

        if not should_retry:
            logger.debug("Network operation blocked due to failure history")
            return False, 0.0

        if delay > 0:
            logger.info(f"Network operation delayed due to previous failures: {delay}s")

        return True, delay

    def get_cached_repository_age(self) -> Optional[timedelta]:
        """Get the age of the cached repository.

        Returns:
            Age of cached repository, or None if no cache exists
        """
        if not self.repository_path.exists():
            return None

        last_updated = self._get_last_update_time()
        if last_updated:
            return datetime.now() - last_updated

        return None

    def warn_about_stale_cache(self, cache_age: timedelta) -> None:
        """Log appropriate warnings about using stale cached data.

        Args:
            cache_age: Age of the cached data
        """
        age_hours = cache_age.total_seconds() / 3600
        age_days = cache_age.days

        if age_days > 7:
            logger.warning(
                f"Using cached repository data that is {age_days} days old. "
                f"Consider updating when network is available."
            )
        elif age_hours > 24:
            logger.warning(
                f"Using cached repository data that is {age_days} days, {
                    age_hours %
                    24:.0f} hours old. " f"Data may be outdated.")
        elif age_hours > 6:
            logger.info(f"Using cached repository data that is {age_hours:.0f} hours old.")
        else:
            logger.debug(f"Using cached repository data (age: {age_hours:.1f} hours)")

    def _get_repository_name(self) -> str:
        """Generate a safe directory name from repository URL and branch."""
        import hashlib
        import re

        # Extract repository name from URL
        url = self.config.saidata_repository_url
        branch = self.config.saidata_repository_branch

        # Try to extract a meaningful name
        if "github.com" in url:
            # Extract owner/repo from GitHub URL
            match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
            if match:
                owner, repo = match.groups()
                base_name = f"{owner}-{repo}"
            else:
                base_name = "saidata"
        else:
            # Use generic name for other URLs
            base_name = "saidata"

        # Add branch if not main/master
        if branch not in ["main", "master"]:
            base_name += f"-{branch}"

        # Ensure safe filename
        safe_name = re.sub(r"[^\w\-_.]", "_", base_name)

        # Add hash suffix to handle URL changes
        url_hash = hashlib.md5(f"{url}#{branch}".encode()).hexdigest()[:8]

        return f"{safe_name}-{url_hash}"

    def _should_update_repository(self) -> bool:
        """Check if repository should be updated based on configuration and cache state."""
        if not self.config.saidata_auto_update:
            return False

        # Check both explicit and detected offline mode
        if self.is_offline_mode():
            return False

        # Check network failure history - don't update if we're in backoff
        should_attempt, _ = self.should_attempt_network_operation()
        if not should_attempt:
            return False

        # Use repository cache to check validity
        return not self.repository_cache.is_repository_valid(
            self.config.saidata_repository_url, self.config.saidata_repository_branch
        )

    def _should_retry_with_update(self) -> bool:
        """Check if we should retry with a repository update when saidata is not found."""
        # Only retry if we haven't updated recently
        if self._last_update_check:
            time_since_check = datetime.now() - self._last_update_check
            # Don't retry if we updated within the last 5 minutes
            return time_since_check.total_seconds() > 300

        return True

    def _is_cache_valid(self) -> bool:
        """Check if the repository cache is valid based on update interval."""
        return self.repository_cache.is_repository_valid(
            self.config.saidata_repository_url, self.config.saidata_repository_branch
        )

    def _get_last_update_time(self) -> Optional[datetime]:
        """Get the last update time of the repository."""
        if not self.repository_path.exists():
            return None

        # Try to get git repository info first
        repo_info = self.git_handler.get_repository_info(self.repository_path)
        if repo_info and repo_info.last_updated:
            return repo_info.last_updated

        # Fall back to directory modification time
        try:
            mtime = self.repository_path.stat().st_mtime
            return datetime.fromtimestamp(mtime)
        except Exception:
            return None

    def _update_with_git(self) -> bool:
        """Update repository using git operations.

        Returns:
            True if successful, False otherwise
        """
        operation_start = datetime.now()

        try:
            auth_type = self.config.saidata_repository_auth_type
            auth_data = self.config.saidata_repository_auth_data

            logger.debug(
                f"Git update parameters: auth_type={auth_type}, shallow={
                    self.config.saidata_shallow_clone}")

            if self.repository_path.exists():
                # Update existing repository
                logger.debug("Updating existing git repository")
                operation = "git_update"
                result = self.git_handler.update_repository(
                    self.repository_path, auth_type, auth_data
                )
            else:
                # Clone new repository
                logger.debug("Cloning new git repository")
                operation = "git_clone"
                result = self.git_handler.clone_repository(
                    self.config.saidata_repository_url,
                    self.repository_path,
                    self.config.saidata_repository_branch,
                    self.config.saidata_shallow_clone,
                    auth_type,
                    auth_data,
                )

            duration = (datetime.now() - operation_start).total_seconds()

            if result.success:
                logger.info(f"Git repository {operation} successful")
                self._network_tracker.record_success()
                self._log_repository_operation_summary(
                    operation,
                    True,
                    duration,
                    {"method": "git", "repository_size_mb": self._get_repository_size_mb()},
                )
                return True
            else:
                logger.error(f"Git repository {operation} failed: {result.message}")
                self._network_tracker.record_failure()
                self._log_repository_operation_summary(
                    operation,
                    False,
                    duration,
                    {"method": "git", "error_message": result.message, "stderr": result.stderr},
                )

                # Analyze and log specific error guidance
                self._analyze_git_operation_failure(result, operation)
                return False

        except Exception as e:
            duration = (datetime.now() - operation_start).total_seconds()
            logger.error(f"Git update error: {e}", exc_info=True)
            self._network_tracker.record_failure()
            self._log_repository_operation_summary(
                "git_operation", False, duration, {"method": "git", "exception": str(e)}
            )
            return False

    def _update_with_tarball(self) -> bool:
        """Update repository using tarball download.

        Returns:
            True if successful, False otherwise
        """
        operation_start = datetime.now()

        try:
            auth_type = self.config.saidata_repository_auth_type
            auth_data = self.config.saidata_repository_auth_data

            logger.debug(f"Tarball update parameters: auth_type={auth_type}")

            # Remove existing repository if it exists
            if self.repository_path.exists():
                logger.debug("Removing existing repository for tarball update")
                import shutil

                try:
                    shutil.rmtree(self.repository_path)
                    logger.debug("Existing repository removed successfully")
                except Exception as e:
                    logger.warning(f"Failed to remove existing repository: {e}")
                    # Continue anyway, tarball extraction might overwrite

            # Download and extract tarball
            logger.debug("Downloading repository tarball")

            # Setup progress callback for large downloads
            def progress_callback(downloaded: int, total: int):
                if total > 10 * 1024 * 1024:  # Only log for downloads > 10MB
                    percent = (downloaded / total) * 100 if total > 0 else 0
                    if percent % 25 < 1:  # Log every 25%
                        mb_downloaded = downloaded / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        logger.info(
                            f"Download progress: {percent:.0f}% ({mb_downloaded:.1f}MB / {mb_total:.1f}MB)"
                        )

            result = self.tarball_handler.download_latest_release(
                self.config.saidata_repository_url,
                self.repository_path,
                auth_type,
                auth_data,
                progress_callback,
            )

            duration = (datetime.now() - operation_start).total_seconds()

            if result.success:
                logger.info("Tarball repository update successful")
                self._network_tracker.record_success()

                # Log release information if available
                if result.release_info:
                    logger.info(f"Downloaded release: {result.release_info.tag_name}")
                    if result.release_info.size:
                        size_mb = result.release_info.size / (1024 * 1024)
                        logger.debug(f"Release size: {size_mb:.1f}MB")

                self._log_repository_operation_summary(
                    "tarball_download",
                    True,
                    duration,
                    {
                        "method": "tarball",
                        "release_tag": result.release_info.tag_name
                        if result.release_info
                        else None,
                        "repository_size_mb": self._get_repository_size_mb(),
                    },
                )
                return True
            else:
                logger.error(f"Tarball repository update failed: {result.message}")
                self._network_tracker.record_failure()
                if result.error_details:
                    logger.debug(f"Error details: {result.error_details}")

                self._log_repository_operation_summary(
                    "tarball_download",
                    False,
                    duration,
                    {
                        "method": "tarball",
                        "error_message": result.message,
                        "error_details": result.error_details,
                    },
                )

                # Analyze and log specific error guidance
                self._analyze_tarball_operation_failure(result)
                return False

        except Exception as e:
            duration = (datetime.now() - operation_start).total_seconds()
            logger.error(f"Tarball update error: {e}", exc_info=True)
            self._network_tracker.record_failure()
            self._log_repository_operation_summary(
                "tarball_operation", False, duration, {"method": "tarball", "exception": str(e)}
            )
            return False

    def _mark_update_successful(self, is_git_repo: bool = True) -> None:
        """Mark repository update as successful.

        Args:
            is_git_repo: Whether this is a git repository or tarball
        """
        self._repository_status = RepositoryStatus.AVAILABLE
        self._last_update_check = datetime.now()
        self._last_error = None

        # Update repository cache metadata
        auth_type = None
        if self.config.saidata_repository_auth_type:
            auth_type = self.config.saidata_repository_auth_type.value

        self.repository_cache.mark_repository_updated(
            self.config.saidata_repository_url,
            self.config.saidata_repository_branch,
            is_git_repo,
            auth_type,
        )

        logger.debug("Repository update marked as successful")

    def _mark_update_failed(self, error_message: str) -> None:
        """Mark repository update as failed.

        Args:
            error_message: Error message describing the failure
        """
        self._repository_status = RepositoryStatus.ERROR
        self._last_update_check = datetime.now()
        self._last_error = error_message
        logger.error(f"Repository update marked as failed: {error_message}")

    def _validate_repository_structure(self) -> bool:
        """Validate that the repository has the expected saidata structure.

        Returns:
            True if structure is valid, False otherwise
        """
        try:
            logger.debug(f"Validating repository structure: {self.repository_path}")

            if not self.repository_path.exists():
                logger.error("Repository path does not exist")
                return False

            # Check for expected directory structure
            software_dir = self.repository_path / "software"
            if not software_dir.exists():
                logger.warning(
                    f"Expected 'software' directory not found in repository: {self.repository_path}"
                )
                # Check for legacy flat structure
                yaml_files = list(self.repository_path.glob("*.yaml"))
                if yaml_files:
                    logger.info(f"Found {len(yaml_files)} YAML files in flat structure")
                    return True
                else:
                    logger.error("No saidata files found in repository")
                    return False

            # Count saidata files in hierarchical structure
            saidata_files = list(software_dir.glob("*/*/default.yaml"))
            logger.info(f"Found {len(saidata_files)} saidata files in hierarchical structure")

            if len(saidata_files) == 0:
                logger.warning("No saidata files found in hierarchical structure")
                return False

            # Validate a few sample files
            sample_files = saidata_files[:5]  # Check first 5 files
            valid_files = 0

            for saidata_file in sample_files:
                try:
                    # Basic validation - check if file is readable and has content
                    with open(saidata_file, "r") as f:
                        content = f.read().strip()
                        if content:
                            valid_files += 1
                        else:
                            logger.warning(f"Empty saidata file: {saidata_file}")
                except Exception as e:
                    logger.warning(f"Cannot read saidata file {saidata_file}: {e}")

            if valid_files == 0:
                logger.error("No valid saidata files found in repository")
                return False

            logger.info(
                f"Repository structure validation passed ({valid_files}/{len(sample_files)} sample files valid)"
            )
            return True

        except Exception as e:
            logger.error(f"Repository structure validation failed: {e}")
            return False

    def _log_saidata_search_failure(self, software_name: str) -> None:
        """Log detailed information about saidata search failure.

        Args:
            software_name: Name of software that was not found
        """
        logger.error(f"Saidata not found for software: {software_name}")

        # Log search paths
        search_paths = self.saidata_loader.get_search_paths()
        logger.debug(f"Searched in {len(search_paths)} paths:")
        for i, path in enumerate(search_paths, 1):
            logger.debug(f"  {i}. {path}")

        # Log expected hierarchical path
        if self.repository_path.exists():
            from .saidata_path import SaidataPath

            expected_path = SaidataPath.from_software_name(software_name, self.repository_path)
            logger.info(f"Expected hierarchical path: {expected_path.hierarchical_path}")

            # Check if directory structure exists
            software_dir = self.repository_path / "software"
            if software_dir.exists():
                prefix = software_name[:2].lower()
                prefix_dir = software_dir / prefix
                if prefix_dir.exists():
                    software_specific_dir = prefix_dir / software_name
                    if software_specific_dir.exists():
                        logger.info(
                            f"Software directory exists but no default.yaml found: {software_specific_dir}")
                        # List what files are in the directory
                        files = list(software_specific_dir.iterdir())
                        if files:
                            logger.debug(
                                f"Files in {software_specific_dir}: {[f.name for f in files]}"
                            )
                    else:
                        logger.info(
                            f"Software-specific directory does not exist: {software_specific_dir}"
                        )
                        # List available software in prefix directory
                        available_software = [d.name for d in prefix_dir.iterdir() if d.is_dir()]
                        if available_software:
                            logger.debug(
                                f"Available software with prefix '{prefix}': {available_software[:10]}"
                            )
                else:
                    logger.info(f"Prefix directory does not exist: {prefix_dir}")
                    # List available prefixes
                    available_prefixes = [d.name for d in software_dir.iterdir() if d.is_dir()]
                    if available_prefixes:
                        logger.debug(f"Available prefixes: {available_prefixes[:20]}")
            else:
                logger.warning("Software directory does not exist in repository")

        # Suggest similar software names
        self._suggest_similar_software(software_name)

    def _suggest_similar_software(self, software_name: str) -> None:
        """Suggest similar software names based on available saidata.

        Args:
            software_name: Name of software that was not found
        """
        try:
            if not self.repository_path.exists():
                return

            software_dir = self.repository_path / "software"
            if not software_dir.exists():
                return

            # Collect available software names
            available_software = []
            for prefix_dir in software_dir.iterdir():
                if prefix_dir.is_dir():
                    for software_specific_dir in prefix_dir.iterdir():
                        if (
                            software_specific_dir.is_dir()
                            and (software_specific_dir / "default.yaml").exists()
                        ):
                            available_software.append(software_specific_dir.name)

            if not available_software:
                return

            # Find similar names using simple string matching
            software_lower = software_name.lower()
            suggestions = []

            # Exact substring matches
            for name in available_software:
                if software_lower in name.lower() or name.lower() in software_lower:
                    suggestions.append(name)

            # If no substring matches, try prefix/suffix matches
            if not suggestions:
                for name in available_software:
                    name_lower = name.lower()
                    if (
                        software_lower.startswith(name_lower[:3])
                        or name_lower.startswith(software_lower[:3])
                        or software_lower.endswith(name_lower[-3:])
                        or name_lower.endswith(software_lower[-3:])
                    ):
                        suggestions.append(name)

            # Limit suggestions
            suggestions = list(set(suggestions))[:5]

            if suggestions:
                logger.info(f"Similar software names found: {', '.join(suggestions)}")
            else:
                logger.debug(f"No similar software names found for '{software_name}'")
                # Log a few random examples
                examples = available_software[:5]
                logger.debug(f"Available software examples: {', '.join(examples)}")

        except Exception as e:
            logger.debug(f"Failed to suggest similar software names: {e}")

    def _log_repository_operation_summary(
        self,
        operation: str,
        success: bool,
        duration: float,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a summary of repository operation for monitoring and debugging.

        Args:
            operation: Operation name (clone, update, fetch, etc.)
            success: Whether operation was successful
            duration: Operation duration in seconds
            details: Additional operation details
        """
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"Repository operation {status}: {operation} completed in {duration:.2f}s")

        # Log operation details
        operation_details = {
            "operation": operation,
            "repository_url": self.config.saidata_repository_url,
            "branch": self.config.saidata_repository_branch,
            "success": success,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat(),
            **(details or {}),
        }

        logger.debug(f"Operation details: {operation_details}")

        # Log performance metrics
        if success and duration > 30:  # Log slow operations
            logger.warning(f"Repository operation took longer than expected: {duration:.2f}s")
        elif success and duration < 1:  # Log very fast operations (might indicate cache hit)
            logger.debug(f"Repository operation completed quickly: {duration:.2f}s (likely cached)")

    def _handle_repository_authentication_error(self, error: Exception, operation: str) -> None:
        """Handle and log repository authentication errors with specific guidance.

        Args:
            error: Authentication error
            operation: Repository operation that failed
        """
        logger.error(f"Repository authentication failed during {operation}: {error}")

        auth_type = self.config.saidata_repository_auth_type

        logger.info("Authentication troubleshooting:")

        if auth_type == RepositoryAuthType.SSH:
            logger.info("  SSH Authentication:")
            logger.info("    - Ensure your SSH key is added to your SSH agent")
            logger.info("    - Verify the SSH key is associated with your account")
            logger.info("    - Test SSH connection: ssh -T git@github.com")
            logger.info("    - Check SSH key permissions (should be 600)")

        elif auth_type == RepositoryAuthType.TOKEN:
            logger.info("  Token Authentication:")
            logger.info("    - Verify your access token is valid and not expired")
            logger.info("    - Ensure the token has the required permissions (repo access)")
            logger.info("    - Check if the token is correctly configured")
            logger.info("    - For GitHub, verify the token has 'repo' or 'public_repo' scope")

        elif auth_type == RepositoryAuthType.BASIC:
            logger.info("  Basic Authentication:")
            logger.info("    - Verify your username and password are correct")
            logger.info("    - Check if two-factor authentication is enabled")
            logger.info("    - Consider using a personal access token instead of password")

        else:
            logger.info("  General Authentication:")
            logger.info("    - Configure authentication using 'sai config auth'")
            logger.info("    - For private repositories, authentication is required")
            logger.info("    - Check repository access permissions")

        logger.info(f"  Repository URL: {self.config.saidata_repository_url}")
        logger.info("  Use 'sai repository status' to check repository configuration")

    def _get_repository_size_mb(self) -> Optional[float]:
        """Get repository size in megabytes.

        Returns:
            Repository size in MB, or None if cannot be determined
        """
        try:
            if not self.repository_path.exists():
                return None

            total_size = 0
            for file_path in self.repository_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size

            return total_size / (1024 * 1024)  # Convert to MB

        except Exception:
            return None

    def _analyze_git_operation_failure(self, result: GitOperationResult, operation: str) -> None:
        """Analyze git operation failure and provide specific guidance.

        Args:
            result: Failed GitOperationResult
            operation: Git operation that failed
        """
        stderr = result.stderr or ""
        stderr_lower = stderr.lower()

        logger.error(f"Analyzing git {operation} failure:")

        # Check for common error patterns and provide guidance
        if "authentication failed" in stderr_lower or "permission denied" in stderr_lower:
            self._handle_repository_authentication_error(Exception(stderr), operation)

        elif "could not resolve host" in stderr_lower or "network is unreachable" in stderr_lower:
            logger.error("Network connectivity issue detected")
            logger.info("Network troubleshooting:")
            logger.info("  - Check your internet connection")
            logger.info("  - Verify DNS resolution is working")
            logger.info("  - Check if you're behind a firewall or proxy")
            logger.info("  - Try again in a few moments")

        elif "repository not found" in stderr_lower or "does not exist" in stderr_lower:
            logger.error("Repository not found or inaccessible")
            logger.info("Repository troubleshooting:")
            logger.info(f"  - Verify repository URL: {self.config.saidata_repository_url}")
            logger.info("  - Check if repository exists and is accessible")
            logger.info("  - For private repositories, ensure proper authentication")

        elif "no space left" in stderr_lower or "disk full" in stderr_lower:
            logger.error("Insufficient disk space")
            logger.info("Disk space troubleshooting:")
            logger.info("  - Free up disk space on your system")
            logger.info(f"  - Check space in cache directory: {self.repository_cache_dir}")
            logger.info("  - Consider clearing old repository caches")

        else:
            logger.info("General git troubleshooting:")
            logger.info("  - Try running the operation again")
            logger.info("  - Check git configuration and version")
            logger.info("  - Verify repository URL and branch name")

    def _analyze_tarball_operation_failure(self, result: TarballOperationResult) -> None:
        """Analyze tarball operation failure and provide specific guidance.

        Args:
            result: Failed TarballOperationResult
        """
        error_message = result.message or ""
        result.error_details or ""

        logger.error("Analyzing tarball download failure:")

        # Check for common error patterns
        if "404" in error_message or "not found" in error_message.lower():
            logger.error("Repository or release not found")
            logger.info("Repository troubleshooting:")
            logger.info(f"  - Verify repository URL: {self.config.saidata_repository_url}")
            logger.info("  - Check if repository has published releases")
            logger.info("  - Ensure repository is accessible")

        elif "403" in error_message or "forbidden" in error_message.lower():
            logger.error("Access forbidden - authentication or rate limiting issue")
            logger.info("Access troubleshooting:")
            logger.info("  - Check if authentication is required")
            logger.info("  - Verify access token permissions")
            logger.info("  - Check if you've hit API rate limits")

        elif "timeout" in error_message.lower() or "timed out" in error_message.lower():
            logger.error("Download timeout - network or server issue")
            logger.info("Timeout troubleshooting:")
            logger.info("  - Check your internet connection speed")
            logger.info("  - Try again later if server is overloaded")
            logger.info("  - Consider increasing timeout settings")

        elif "checksum" in error_message.lower() or "verification" in error_message.lower():
            logger.error("File integrity verification failed")
            logger.info("Integrity troubleshooting:")
            logger.info("  - Try downloading again (file may have been corrupted)")
            logger.info("  - Check if the release was updated recently")
            logger.info("  - Contact repository maintainer if issue persists")

        else:
            logger.info("General download troubleshooting:")
            logger.info("  - Check your internet connection")
            logger.info("  - Try again in a few moments")
            logger.info("  - Verify the repository has releases available")
            logger.info("  - Consider using git method if available")
