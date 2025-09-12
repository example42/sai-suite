"""Repository caching system for managing cached saidata repositories."""

import json
import logging
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from ..models.config import SaiConfig


logger = logging.getLogger(__name__)


@dataclass
class RepositoryMetadata:
    """Metadata for a cached repository."""
    url: str
    branch: str
    local_path: Path
    last_updated: float
    is_git_repo: bool
    auth_type: Optional[str] = None
    size_bytes: int = 0
    file_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['local_path'] = str(data['local_path'])
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepositoryMetadata':
        """Create from dictionary loaded from JSON."""
        data = data.copy()
        data['local_path'] = Path(data['local_path'])
        return cls(**data)


@dataclass
class RepositoryStatus:
    """Status information for a repository."""
    url: str
    branch: str
    local_path: Path
    is_git_repo: bool
    last_updated: Optional[datetime]
    age_seconds: float
    age_hours: float
    age_days: float
    is_expired: bool
    size_mb: float
    file_count: int
    exists: bool
    error_message: Optional[str] = None


class RepositoryCache:
    """Manages cached repositories for saidata."""
    
    def __init__(self, config: SaiConfig):
        """Initialize repository cache.
        
        Args:
            config: SAI configuration object
        """
        self.config = config
        self.cache_enabled = config.cache_enabled
        self.cache_dir = config.saidata_repository_cache_dir or (config.cache_directory / "repositories")
        self.update_interval = config.saidata_update_interval
        self.metadata_file = self.cache_dir / ".repository_metadata"
        
        # Ensure cache directory exists
        if self.cache_enabled:
            self._ensure_cache_directory()
    
    def _ensure_cache_directory(self) -> None:
        """Ensure cache directory exists and is writable."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = self.cache_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            
        except (OSError, PermissionError) as e:
            logger.warning(f"Cannot create or write to repository cache directory {self.cache_dir}: {e}")
            self.cache_enabled = False
    
    def _load_metadata(self) -> Dict[str, RepositoryMetadata]:
        """Load repository metadata from disk.
        
        Returns:
            Dictionary mapping repository keys to metadata
        """
        if not self.cache_enabled or not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate metadata structure
            if not isinstance(data, dict) or 'repositories' not in data:
                logger.warning("Invalid repository metadata file structure, ignoring cache")
                return {}
            
            # Convert to RepositoryMetadata objects
            repositories = {}
            for repo_key, repo_data in data['repositories'].items():
                try:
                    repositories[repo_key] = RepositoryMetadata.from_dict(repo_data)
                except (KeyError, TypeError, ValueError) as e:
                    logger.warning(f"Invalid metadata for repository '{repo_key}': {e}")
                    continue
            
            return repositories
            
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load repository metadata: {e}")
            return {}
    
    def _save_metadata(self, repositories: Dict[str, RepositoryMetadata]) -> None:
        """Save repository metadata to disk.
        
        Args:
            repositories: Dictionary of repository metadata to save
        """
        if not self.cache_enabled:
            return
        
        try:
            # Convert to serializable format
            data = {
                'cache_version': '1.0',
                'last_updated': time.time(),
                'repositories': {
                    repo_key: repo_meta.to_dict()
                    for repo_key, repo_meta in repositories.items()
                }
            }
            
            # Write atomically by writing to temp file first
            temp_file = self.metadata_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Atomic move
            temp_file.replace(self.metadata_file)
            
            logger.debug(f"Saved repository metadata to {self.metadata_file}")
            
        except (OSError, ValueError) as e:
            logger.error(f"Failed to save repository metadata: {e}")
    
    def _get_repository_key(self, url: str, branch: str) -> str:
        """Generate a unique key for a repository.
        
        Args:
            url: Repository URL
            branch: Repository branch
            
        Returns:
            Unique repository key
        """
        # Create a safe filename from URL and branch
        import hashlib
        key_content = f"{url}#{branch}"
        hash_suffix = hashlib.sha256(key_content.encode()).hexdigest()[:8]
        
        # Extract repository name from URL
        repo_name = url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        
        # Combine name, branch, and hash for uniqueness
        if branch != 'main':
            return f"{repo_name}-{branch}-{hash_suffix}"
        else:
            return f"{repo_name}-{hash_suffix}"
    
    def _get_repository_path(self, url: str, branch: str) -> Path:
        """Get the local path for a repository.
        
        Args:
            url: Repository URL
            branch: Repository branch
            
        Returns:
            Local path where repository should be cached
        """
        repo_key = self._get_repository_key(url, branch)
        return self.cache_dir / repo_key
    
    def _calculate_directory_stats(self, directory: Path) -> tuple[int, int]:
        """Calculate size and file count for a directory.
        
        Args:
            directory: Directory to analyze
            
        Returns:
            Tuple of (size_bytes, file_count)
        """
        if not directory.exists():
            return 0, 0
        
        total_size = 0
        file_count = 0
        
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                        file_count += 1
                    except (OSError, IOError):
                        # Skip files we can't read
                        pass
        except (OSError, IOError):
            # Skip directories we can't read
            pass
        
        return total_size, file_count
    
    def is_repository_valid(self, url: str, branch: str = "main") -> bool:
        """Check if a cached repository is valid and not expired.
        
        Args:
            url: Repository URL
            branch: Repository branch
            
        Returns:
            True if repository is cached and valid
        """
        if not self.cache_enabled:
            return False
        
        repositories = self._load_metadata()
        repo_key = self._get_repository_key(url, branch)
        
        if repo_key not in repositories:
            return False
        
        repo_meta = repositories[repo_key]
        
        # Check if repository directory exists
        if not repo_meta.local_path.exists():
            logger.debug(f"Repository cache directory missing: {repo_meta.local_path}")
            return False
        
        # Check if repository is expired
        current_time = time.time()
        age_seconds = current_time - repo_meta.last_updated
        
        if age_seconds > self.update_interval:
            logger.debug(f"Repository cache expired for '{url}#{branch}' (age: {age_seconds}s)")
            return False
        
        return True
    
    def get_repository_path(self, url: str, branch: str = "main") -> Optional[Path]:
        """Get the local path for a cached repository if valid.
        
        Args:
            url: Repository URL
            branch: Repository branch
            
        Returns:
            Local path if repository is cached and valid, None otherwise
        """
        if not self.is_repository_valid(url, branch):
            return None
        
        return self._get_repository_path(url, branch)
    
    def mark_repository_updated(self, url: str, branch: str = "main", 
                              is_git_repo: bool = True, auth_type: Optional[str] = None) -> None:
        """Mark a repository as updated in the cache.
        
        Args:
            url: Repository URL
            branch: Repository branch
            is_git_repo: Whether this is a git repository or tarball
            auth_type: Authentication type used
        """
        if not self.cache_enabled:
            return
        
        repositories = self._load_metadata()
        repo_key = self._get_repository_key(url, branch)
        local_path = self._get_repository_path(url, branch)
        
        # Calculate directory statistics
        size_bytes, file_count = self._calculate_directory_stats(local_path)
        
        # Create or update metadata
        repositories[repo_key] = RepositoryMetadata(
            url=url,
            branch=branch,
            local_path=local_path,
            last_updated=time.time(),
            is_git_repo=is_git_repo,
            auth_type=auth_type,
            size_bytes=size_bytes,
            file_count=file_count
        )
        
        self._save_metadata(repositories)
        logger.debug(f"Marked repository '{url}#{branch}' as updated")
    
    def get_repository_status(self, url: str, branch: str = "main") -> RepositoryStatus:
        """Get detailed status information for a repository.
        
        Args:
            url: Repository URL
            branch: Repository branch
            
        Returns:
            Repository status information
        """
        repositories = self._load_metadata()
        repo_key = self._get_repository_key(url, branch)
        local_path = self._get_repository_path(url, branch)
        
        # Default values
        last_updated = None
        age_seconds = float('inf')
        is_git_repo = True
        size_bytes = 0
        file_count = 0
        exists = local_path.exists() if local_path else False
        error_message = None
        
        if repo_key in repositories:
            repo_meta = repositories[repo_key]
            last_updated = datetime.fromtimestamp(repo_meta.last_updated)
            age_seconds = time.time() - repo_meta.last_updated
            is_git_repo = repo_meta.is_git_repo
            size_bytes = repo_meta.size_bytes
            file_count = repo_meta.file_count
        elif exists:
            # Repository exists but no metadata - calculate stats
            size_bytes, file_count = self._calculate_directory_stats(local_path)
            error_message = "Repository exists but no metadata found"
        
        age_hours = age_seconds / 3600
        age_days = age_hours / 24
        is_expired = age_seconds > self.update_interval
        size_mb = size_bytes / (1024 * 1024)
        
        return RepositoryStatus(
            url=url,
            branch=branch,
            local_path=local_path,
            is_git_repo=is_git_repo,
            last_updated=last_updated,
            age_seconds=age_seconds,
            age_hours=age_hours,
            age_days=age_days,
            is_expired=is_expired,
            size_mb=size_mb,
            file_count=file_count,
            exists=exists,
            error_message=error_message
        )
    
    def cleanup_expired_repositories(self) -> int:
        """Remove expired repository caches.
        
        Returns:
            Number of repositories cleaned up
        """
        if not self.cache_enabled:
            return 0
        
        repositories = self._load_metadata()
        current_time = time.time()
        expired_repos = []
        
        for repo_key, repo_meta in repositories.items():
            age_seconds = current_time - repo_meta.last_updated
            if age_seconds > self.update_interval:
                expired_repos.append((repo_key, repo_meta))
        
        # Remove expired repositories
        cleaned_count = 0
        for repo_key, repo_meta in expired_repos:
            try:
                if repo_meta.local_path.exists():
                    shutil.rmtree(repo_meta.local_path)
                    logger.debug(f"Removed expired repository cache: {repo_meta.local_path}")
                
                del repositories[repo_key]
                cleaned_count += 1
                
            except (OSError, IOError) as e:
                logger.warning(f"Failed to remove expired repository {repo_meta.local_path}: {e}")
        
        if cleaned_count > 0:
            self._save_metadata(repositories)
            logger.info(f"Cleaned up {cleaned_count} expired repository caches")
        
        return cleaned_count
    
    def cleanup_invalid_repositories(self) -> int:
        """Remove repository caches that no longer exist on disk.
        
        Returns:
            Number of invalid repositories cleaned up
        """
        if not self.cache_enabled:
            return 0
        
        repositories = self._load_metadata()
        invalid_repos = []
        
        for repo_key, repo_meta in repositories.items():
            if not repo_meta.local_path.exists():
                invalid_repos.append(repo_key)
        
        # Remove invalid repositories from metadata
        cleaned_count = len(invalid_repos)
        for repo_key in invalid_repos:
            del repositories[repo_key]
            logger.debug(f"Removed invalid repository metadata: {repo_key}")
        
        if cleaned_count > 0:
            self._save_metadata(repositories)
            logger.info(f"Cleaned up {cleaned_count} invalid repository metadata entries")
        
        return cleaned_count
    
    def cleanup_old_repositories(self, max_age_days: int = 30) -> int:
        """Remove repository caches older than specified age.
        
        Args:
            max_age_days: Maximum age in days before removal
            
        Returns:
            Number of old repositories cleaned up
        """
        if not self.cache_enabled:
            return 0
        
        repositories = self._load_metadata()
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600
        old_repos = []
        
        for repo_key, repo_meta in repositories.items():
            age_seconds = current_time - repo_meta.last_updated
            if age_seconds > max_age_seconds:
                old_repos.append((repo_key, repo_meta))
        
        # Remove old repositories
        cleaned_count = 0
        for repo_key, repo_meta in old_repos:
            try:
                if repo_meta.local_path.exists():
                    shutil.rmtree(repo_meta.local_path)
                    logger.debug(f"Removed old repository cache: {repo_meta.local_path}")
                
                del repositories[repo_key]
                cleaned_count += 1
                
            except (OSError, IOError) as e:
                logger.warning(f"Failed to remove old repository {repo_meta.local_path}: {e}")
        
        if cleaned_count > 0:
            self._save_metadata(repositories)
            logger.info(f"Cleaned up {cleaned_count} old repository caches")
        
        return cleaned_count
    
    def get_all_repositories(self) -> List[RepositoryStatus]:
        """Get status information for all cached repositories.
        
        Returns:
            List of repository status information
        """
        repositories = self._load_metadata()
        status_list = []
        
        for repo_key, repo_meta in repositories.items():
            status = self.get_repository_status(repo_meta.url, repo_meta.branch)
            status_list.append(status)
        
        # Sort by URL then branch
        status_list.sort(key=lambda x: (x.url, x.branch))
        return status_list
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get comprehensive cache status information.
        
        Returns:
            Dictionary with cache status information
        """
        repositories = self._load_metadata()
        
        # Calculate total cache size
        total_size_bytes = 0
        total_file_count = 0
        expired_count = 0
        current_time = time.time()
        
        for repo_meta in repositories.values():
            total_size_bytes += repo_meta.size_bytes
            total_file_count += repo_meta.file_count
            
            age_seconds = current_time - repo_meta.last_updated
            if age_seconds > self.update_interval:
                expired_count += 1
        
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        # Get metadata file size
        metadata_size_bytes = 0
        if self.metadata_file.exists():
            try:
                metadata_size_bytes = self.metadata_file.stat().st_size
            except OSError:
                pass
        
        return {
            'cache_enabled': self.cache_enabled,
            'cache_directory': str(self.cache_dir),
            'metadata_file': str(self.metadata_file),
            'update_interval_seconds': self.update_interval,
            'update_interval_hours': self.update_interval / 3600,
            'update_interval_days': self.update_interval / 86400,
            'total_repositories': len(repositories),
            'expired_repositories': expired_count,
            'total_cache_size_bytes': total_size_bytes,
            'total_cache_size_mb': total_size_mb,
            'total_file_count': total_file_count,
            'metadata_size_bytes': metadata_size_bytes,
            'repositories': [
                {
                    'url': repo_meta.url,
                    'branch': repo_meta.branch,
                    'local_path': str(repo_meta.local_path),
                    'last_updated': datetime.fromtimestamp(repo_meta.last_updated).isoformat(),
                    'is_git_repo': repo_meta.is_git_repo,
                    'auth_type': repo_meta.auth_type,
                    'size_bytes': repo_meta.size_bytes,
                    'size_mb': repo_meta.size_bytes / (1024 * 1024),
                    'file_count': repo_meta.file_count,
                    'age_seconds': current_time - repo_meta.last_updated,
                    'age_hours': (current_time - repo_meta.last_updated) / 3600,
                    'age_days': (current_time - repo_meta.last_updated) / 86400,
                    'is_expired': (current_time - repo_meta.last_updated) > self.update_interval
                }
                for repo_meta in repositories.values()
            ]
        }
    
    def clear_repository_cache(self, url: str, branch: str = "main") -> bool:
        """Clear cache for a specific repository.
        
        Args:
            url: Repository URL
            branch: Repository branch
            
        Returns:
            True if cache was cleared, False if no cache existed
        """
        if not self.cache_enabled:
            return False
        
        repositories = self._load_metadata()
        repo_key = self._get_repository_key(url, branch)
        
        if repo_key not in repositories:
            return False
        
        repo_meta = repositories[repo_key]
        
        # Remove repository directory
        try:
            if repo_meta.local_path.exists():
                shutil.rmtree(repo_meta.local_path)
                logger.debug(f"Removed repository cache: {repo_meta.local_path}")
        except (OSError, IOError) as e:
            logger.warning(f"Failed to remove repository cache {repo_meta.local_path}: {e}")
        
        # Remove from metadata
        del repositories[repo_key]
        self._save_metadata(repositories)
        
        logger.info(f"Cleared cache for repository '{url}#{branch}'")
        return True
    
    def clear_all_repository_cache(self) -> int:
        """Clear all repository caches.
        
        Returns:
            Number of repositories cleared
        """
        if not self.cache_enabled:
            return 0
        
        repositories = self._load_metadata()
        cleared_count = 0
        
        # Remove all repository directories
        for repo_meta in repositories.values():
            try:
                if repo_meta.local_path.exists():
                    shutil.rmtree(repo_meta.local_path)
                    logger.debug(f"Removed repository cache: {repo_meta.local_path}")
                cleared_count += 1
            except (OSError, IOError) as e:
                logger.warning(f"Failed to remove repository cache {repo_meta.local_path}: {e}")
        
        # Clear metadata
        if cleared_count > 0:
            self._save_metadata({})
            logger.info(f"Cleared all repository caches ({cleared_count} repositories)")
        
        return cleared_count