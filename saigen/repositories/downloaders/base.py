"""Base repository downloader interface."""

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional

from saigen.models.repository import RepositoryInfo, RepositoryPackage


class BaseRepositoryDownloader(ABC):
    """Abstract base class for repository downloaders."""

    def __init__(self, repository_info: RepositoryInfo, config: Optional[Dict[str, Any]] = None):
        """Initialize the downloader with repository information.

        Args:
            repository_info: Repository metadata and configuration
            config: Additional configuration options
        """
        self.repository_info = repository_info
        self.config = config or {}
        self._session = None

    @abstractmethod
    async def download_package_list(self) -> List[RepositoryPackage]:
        """Download complete package list from repository.

        Returns:
            List of repository packages

        Raises:
            RepositoryError: If download fails
        """

    @abstractmethod
    async def search_package(self, name: str) -> List[RepositoryPackage]:
        """Search for specific package in repository.

        Args:
            name: Package name to search for

        Returns:
            List of matching packages

        Raises:
            RepositoryError: If search fails
        """

    @abstractmethod
    async def get_package_details(
        self, name: str, version: Optional[str] = None
    ) -> Optional[RepositoryPackage]:
        """Get detailed information for a specific package.

        Args:
            name: Package name
            version: Specific version (optional, gets latest if not specified)

        Returns:
            Package details or None if not found

        Raises:
            RepositoryError: If lookup fails
        """

    def get_cache_key(self) -> str:
        """Return unique cache key for this repository.

        Returns:
            Unique cache key string
        """
        key_data = {
            "name": self.repository_info.name,
            "type": self.repository_info.type,
            "url": self.repository_info.url,
            "platform": self.repository_info.platform,
            "architecture": self.repository_info.architecture,
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def get_cache_ttl(self) -> timedelta:
        """Get cache TTL for this repository.

        Returns:
            Cache time-to-live duration
        """
        # Default TTL, can be overridden by subclasses
        return timedelta(hours=self.config.get("cache_ttl_hours", 24))

    async def is_available(self) -> bool:
        """Check if repository is available and accessible.

        Returns:
            True if repository is accessible
        """
        try:
            # Try to get a small sample of packages
            await self.search_package("test")
            return True
        except Exception:
            return False

    async def get_repository_metadata(self) -> Dict[str, Any]:
        """Get repository metadata and statistics.

        Returns:
            Dictionary with repository metadata
        """
        try:
            packages = await self.download_package_list()
            return {
                "package_count": len(packages),
                "last_updated": datetime.utcnow(),
                "repository_type": self.repository_info.type,
                "platform": self.repository_info.platform,
                "architecture": self.repository_info.architecture,
            }
        except Exception as e:
            return {
                "error": str(e),
                "last_updated": datetime.utcnow(),
                "repository_type": self.repository_info.type,
                "platform": self.repository_info.platform,
            }

    async def stream_packages(
        self, batch_size: int = 1000
    ) -> AsyncIterator[List[RepositoryPackage]]:
        """Stream packages in batches for memory efficiency.

        Args:
            batch_size: Number of packages per batch

        Yields:
            Batches of repository packages
        """
        # Default implementation - subclasses can override for true streaming
        packages = await self.download_package_list()
        for i in range(0, len(packages), batch_size):
            yield packages[i : i + batch_size]

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
