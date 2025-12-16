"""Repository data caching system with TTL management."""

import asyncio
import hashlib
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from saigen.models.repository import CacheEntry, RepositoryPackage
from saigen.repositories.downloaders.base import BaseRepositoryDownloader
from saigen.utils.errors import CacheError


class RepositoryCache:
    """Repository data cache with TTL management."""

    def __init__(self, cache_dir: Union[str, Path], default_ttl: timedelta = timedelta(hours=24)):
        """Initialize repository cache.

        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default time-to-live for cache entries
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self._locks: Dict[str, asyncio.Lock] = {}

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for a given key."""
        # Security: Sanitize cache key to prevent path traversal
        safe_key = self._sanitize_cache_key(cache_key)
        return self.cache_dir / f"{safe_key}.cache"

    def _get_metadata_path(self, cache_key: str) -> Path:
        """Get metadata file path for a given key."""
        # Security: Sanitize cache key to prevent path traversal
        safe_key = self._sanitize_cache_key(cache_key)
        return self.cache_dir / f"{safe_key}.meta"

    def _sanitize_cache_key(self, cache_key: str) -> str:
        """Sanitize cache key to prevent path traversal attacks."""
        import re

        # Remove any path separators and dangerous characters
        # Replace dots and slashes with underscores for security
        safe_key = re.sub(r"[./\\]", "_", cache_key)
        safe_key = re.sub(r"[^\w\-_]", "_", safe_key)
        # Limit length to prevent filesystem issues
        if len(safe_key) > 200:
            safe_key = safe_key[:200]
        return safe_key

    def _get_lock(self, cache_key: str) -> asyncio.Lock:
        """Get or create lock for cache key."""
        if cache_key not in self._locks:
            self._locks[cache_key] = asyncio.Lock()
        return self._locks[cache_key]

    async def get(self, cache_key: str) -> Optional[CacheEntry]:
        """Get cache entry by key.

        Args:
            cache_key: Cache key to retrieve

        Returns:
            Cache entry if found and not expired, None otherwise
        """
        async with self._get_lock(cache_key):
            cache_path = self._get_cache_path(cache_key)
            meta_path = self._get_metadata_path(cache_key)

            if not cache_path.exists() or not meta_path.exists():
                return None

            try:
                # Load metadata first
                with open(meta_path, "r") as f:
                    meta_content = f.read()
                    metadata = json.loads(meta_content)

                # Check if expired
                expires_at = datetime.fromisoformat(metadata["expires_at"])
                if datetime.utcnow() > expires_at:
                    # Clean up expired entry
                    await self._remove_cache_files(cache_key)
                    return None

                # Load cache data with memory optimization
                with open(cache_path, "rb") as f:
                    # Stream large files to avoid memory spikes
                    file_size = cache_path.stat().st_size
                    if file_size > 50 * 1024 * 1024:  # 50MB threshold
                        # For large files, use streaming approach
                        packages = pickle.load(f)
                    else:
                        cache_content = f.read()
                        packages = pickle.loads(cache_content)

                return CacheEntry(
                    repository_name=metadata["repository_name"],
                    data=packages,
                    timestamp=datetime.fromisoformat(metadata["timestamp"]),
                    expires_at=expires_at,
                    checksum=metadata["checksum"],
                    metadata=metadata.get("metadata", {}),
                )

            except Exception:
                # Clean up corrupted cache
                await self._remove_cache_files(cache_key)
                return None

    async def set(
        self,
        cache_key: str,
        packages: List[RepositoryPackage],
        repository_name: str,
        ttl: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set cache entry.

        Args:
            cache_key: Cache key
            packages: List of repository packages
            repository_name: Name of the repository
            ttl: Time-to-live (uses default if not specified)
            metadata: Additional metadata to store
        """
        async with self._get_lock(cache_key):
            ttl = ttl or self.default_ttl
            now = datetime.utcnow()
            expires_at = now + ttl

            # Calculate checksum
            package_data = [pkg.model_dump() for pkg in packages]
            checksum = self._calculate_checksum(package_data)

            # Prepare metadata (ensure JSON serializable)
            serializable_metadata = {}
            if metadata:
                for key, value in metadata.items():
                    if isinstance(value, datetime):
                        serializable_metadata[key] = value.isoformat()
                    else:
                        serializable_metadata[key] = value

            meta_data = {
                "repository_name": repository_name,
                "timestamp": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "checksum": checksum,
                "package_count": len(packages),
                "metadata": serializable_metadata,
            }

            try:
                # Write cache data with secure permissions
                cache_path = self._get_cache_path(cache_key)
                with open(cache_path, "wb") as f:
                    cache_content = pickle.dumps(packages)
                    f.write(cache_content)
                # Set secure file permissions (owner read/write only)
                cache_path.chmod(0o600)

                # Write metadata with secure permissions
                meta_path = self._get_metadata_path(cache_key)
                with open(meta_path, "w") as f:
                    f.write(json.dumps(meta_data, indent=2))
                meta_path.chmod(0o600)

            except Exception as e:
                # Clean up partial writes
                await self._remove_cache_files(cache_key)
                raise CacheError(f"Failed to write cache entry: {str(e)}")

    async def get_or_fetch(self, downloader: BaseRepositoryDownloader) -> List[RepositoryPackage]:
        """Get from cache or fetch fresh data.

        Args:
            downloader: Repository downloader to use if cache miss

        Returns:
            List of repository packages
        """
        cache_key = downloader.get_cache_key()

        # Try to get from cache first
        cache_entry = await self.get(cache_key)
        if cache_entry:
            return cache_entry.data

        # Cache miss - fetch fresh data
        try:
            # Check if this is an API-based repository
            from saigen.repositories.downloaders.api_downloader import APIRepositoryDownloader
            
            if isinstance(downloader, APIRepositoryDownloader):
                # Skip fetching for API-based repositories during cache update
                # API repositories should be queried on-demand, not bulk downloaded
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(
                    f"Skipping bulk download for API-based repository {downloader.repository_info.name}. "
                    "Use query_package() or query_packages_batch() for on-demand queries."
                )
                return []
            
            packages = await downloader.download_package_list()

            # Store in cache
            ttl = downloader.get_cache_ttl()
            metadata = await downloader.get_repository_metadata()

            await self.set(
                cache_key=cache_key,
                packages=packages,
                repository_name=downloader.repository_info.name,
                ttl=ttl,
                metadata=metadata,
            )

            return packages

        except Exception as e:
            raise CacheError(
                f"Failed to fetch data for {downloader.repository_info.name}: {str(e)}"
            )

    async def invalidate(self, cache_key: str) -> bool:
        """Invalidate specific cache entry.

        Args:
            cache_key: Cache key to invalidate

        Returns:
            True if entry was removed, False if not found
        """
        async with self._get_lock(cache_key):
            return await self._remove_cache_files(cache_key)

    async def invalidate_repository(self, repository_name: str) -> int:
        """Invalidate all cache entries for a repository.

        Args:
            repository_name: Repository name to invalidate

        Returns:
            Number of entries removed
        """
        removed_count = 0

        # Find all cache files for this repository
        for meta_file in self.cache_dir.glob("*.meta"):
            try:
                with open(meta_file, "r") as f:
                    content = f.read()
                    metadata = json.loads(content)

                if metadata.get("repository_name") == repository_name:
                    cache_key = meta_file.stem
                    if await self.invalidate(cache_key):
                        removed_count += 1

            except Exception:
                continue

        return removed_count

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        removed_count = 0
        now = datetime.utcnow()

        # Check all metadata files
        for meta_file in self.cache_dir.glob("*.meta"):
            try:
                with open(meta_file, "r") as f:
                    content = f.read()
                    metadata = json.loads(content)

                expires_at = datetime.fromisoformat(metadata["expires_at"])
                if now > expires_at:
                    cache_key = meta_file.stem
                    if await self.invalidate(cache_key):
                        removed_count += 1

            except Exception:
                # Remove corrupted metadata files
                try:
                    meta_file.unlink()
                    cache_file = self.cache_dir / f"{meta_file.stem}.cache"
                    if cache_file.exists():
                        cache_file.unlink()
                    removed_count += 1
                except Exception:
                    pass

        return removed_count

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "total_entries": 0,
            "expired_entries": 0,
            "total_packages": 0,
            "total_size_bytes": 0,
            "repositories": {},
            "oldest_entry": None,
            "newest_entry": None,
        }

        now = datetime.utcnow()
        oldest_time = None
        newest_time = None

        for meta_file in self.cache_dir.glob("*.meta"):
            try:
                with open(meta_file, "r") as f:
                    content = f.read()
                    metadata = json.loads(content)

                stats["total_entries"] += 1

                # Check if expired
                expires_at = datetime.fromisoformat(metadata["expires_at"])
                if now > expires_at:
                    stats["expired_entries"] += 1

                # Track packages and size
                package_count = metadata.get("package_count", 0)
                stats["total_packages"] += package_count

                cache_file = self.cache_dir / f"{meta_file.stem}.cache"
                if cache_file.exists():
                    stats["total_size_bytes"] += cache_file.stat().st_size

                # Track by repository
                repo_name = metadata.get("repository_name", "unknown")
                if repo_name not in stats["repositories"]:
                    stats["repositories"][repo_name] = {"entries": 0, "packages": 0, "expired": 0}

                stats["repositories"][repo_name]["entries"] += 1
                stats["repositories"][repo_name]["packages"] += package_count
                if now > expires_at:
                    stats["repositories"][repo_name]["expired"] += 1

                # Track oldest/newest
                timestamp = datetime.fromisoformat(metadata["timestamp"])
                if oldest_time is None or timestamp < oldest_time:
                    oldest_time = timestamp
                    stats["oldest_entry"] = timestamp.isoformat()
                if newest_time is None or timestamp > newest_time:
                    newest_time = timestamp
                    stats["newest_entry"] = timestamp.isoformat()

            except Exception:
                continue

        return stats

    async def get_all_packages(self, include_expired: bool = False) -> List[RepositoryPackage]:
        """Get all cached packages from all repositories.

        Args:
            include_expired: Whether to include packages from expired cache entries

        Returns:
            List of all cached repository packages
        """
        all_packages = []
        now = datetime.utcnow()

        for meta_file in self.cache_dir.glob("*.meta"):
            try:
                with open(meta_file, "r") as f:
                    content = f.read()
                    metadata = json.loads(content)

                # Check if expired
                expires_at = datetime.fromisoformat(metadata["expires_at"])
                if not include_expired and now > expires_at:
                    continue

                # Load cache entry
                cache_key = meta_file.stem
                cache_entry = await self.get(cache_key)

                if cache_entry and cache_entry.data:
                    all_packages.extend(cache_entry.data)

            except Exception as e:
                # Log error but continue with other entries
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to load packages from cache entry {meta_file}: {e}")
                continue

        return all_packages

    async def get_packages_by_repository(self, repository_name: str) -> List[RepositoryPackage]:
        """Get all cached packages from a specific repository.

        Args:
            repository_name: Name of the repository

        Returns:
            List of cached packages from the specified repository
        """
        packages = []

        for meta_file in self.cache_dir.glob("*.meta"):
            try:
                with open(meta_file, "r") as f:
                    content = f.read()
                    metadata = json.loads(content)

                # Check if this is the repository we want
                if metadata.get("repository_name") != repository_name:
                    continue

                # Check if expired
                now = datetime.utcnow()
                expires_at = datetime.fromisoformat(metadata["expires_at"])
                if now > expires_at:
                    continue

                # Load cache entry
                cache_key = meta_file.stem
                cache_entry = await self.get(cache_key)

                if cache_entry and cache_entry.data:
                    packages.extend(cache_entry.data)

            except Exception as e:
                # Log error but continue with other entries
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to load packages from cache entry {meta_file}: {e}")
                continue

        return packages

    async def list_cached_repositories(self) -> List[str]:
        """List all repositories that have cached data.

        Returns:
            List of repository names with cached data
        """
        repositories = set()
        now = datetime.utcnow()

        for meta_file in self.cache_dir.glob("*.meta"):
            try:
                with open(meta_file, "r") as f:
                    content = f.read()
                    metadata = json.loads(content)

                # Check if expired
                expires_at = datetime.fromisoformat(metadata["expires_at"])
                if now > expires_at:
                    continue

                repo_name = metadata.get("repository_name")
                if repo_name:
                    repositories.add(repo_name)

            except Exception:
                continue

        return sorted(list(repositories))

    async def clear_all(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries removed
        """
        removed_count = 0

        # Remove all cache and metadata files
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                cache_file.unlink()
                removed_count += 1
            except Exception:
                pass

        for meta_file in self.cache_dir.glob("*.meta"):
            try:
                meta_file.unlink()
            except Exception:
                pass

        return removed_count

    async def has_key(self, cache_key: str) -> bool:
        """Check if cache key exists.

        Args:
            cache_key: Cache key to check

        Returns:
            True if key exists and is not expired
        """
        cache_entry = await self.get(cache_key)
        return cache_entry is not None

    async def delete(self, cache_key: str) -> bool:
        """Delete cache entry by key.

        Args:
            cache_key: Cache key to delete

        Returns:
            True if entry was deleted
        """
        return await self.invalidate(cache_key)

    async def get_cached_data(self, repository_name: str) -> Optional[List[RepositoryPackage]]:
        """Get cached data for a repository - backward compatibility method.

        Args:
            repository_name: Repository name

        Returns:
            List of cached packages or None if not found
        """
        packages = await self.get_packages_by_repository(repository_name)
        return packages if packages else None

    def is_expired(self, cache_key: str) -> bool:
        """Check if cache entry is expired - synchronous method for backward compatibility.

        Args:
            cache_key: Cache key to check

        Returns:
            True if expired or not found
        """
        meta_path = self._get_metadata_path(cache_key)

        if not meta_path.exists():
            return True

        try:
            with open(meta_path, "r") as f:
                content = f.read()
                metadata = json.loads(content)

            expires_at = datetime.fromisoformat(metadata["expires_at"])
            return datetime.utcnow() > expires_at
        except Exception:
            return True

    async def store_data(self, repository_name: str, packages: List[RepositoryPackage]) -> None:
        """Store data for a repository - backward compatibility method.

        Args:
            repository_name: Repository name
            packages: List of packages to store
        """
        cache_key = f"{repository_name}_packages"
        await self.set(cache_key, packages, repository_name)

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics - backward compatibility method.

        Returns:
            Dictionary with cache statistics
        """
        return await self.get_cache_stats()

    async def _remove_cache_files(self, cache_key: str) -> bool:
        """Remove cache and metadata files for a key."""
        removed = False

        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_metadata_path(cache_key)

        try:
            if cache_path.exists():
                cache_path.unlink()
                removed = True
        except Exception:
            pass

        try:
            if meta_path.exists():
                meta_path.unlink()
        except Exception:
            pass

        return removed

    def _calculate_checksum(self, data: Any) -> str:
        """Calculate checksum for data."""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()


class CacheManager:
    """High-level cache management interface."""

    def __init__(self, cache: RepositoryCache):
        """Initialize cache manager.

        Args:
            cache: Repository cache instance
        """
        self.cache = cache

    async def update_repository(
        self, downloader: BaseRepositoryDownloader, force: bool = False
    ) -> bool:
        """Update cache for a specific repository.

        Args:
            downloader: Repository downloader
            force: Force update even if cache is valid

        Returns:
            True if cache was updated
        """
        # Skip API-based repositories - they should be queried on-demand
        from saigen.repositories.downloaders.api_downloader import APIRepositoryDownloader
        
        if isinstance(downloader, APIRepositoryDownloader):
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(
                f"Skipping cache update for API-based repository {downloader.repository_info.name}. "
                "API repositories are queried on-demand."
            )
            return False
        
        cache_key = downloader.get_cache_key()

        if not force:
            # Check if cache is still valid
            cache_entry = await self.cache.get(cache_key)
            if cache_entry:
                return False

        try:
            # Force refresh
            await self.cache.invalidate(cache_key)
            await self.cache.get_or_fetch(downloader)
            return True
        except Exception:
            return False

    async def update_all_repositories(
        self, downloaders: List[BaseRepositoryDownloader], force: bool = False
    ) -> Dict[str, bool]:
        """Update cache for multiple repositories.

        Args:
            downloaders: List of repository downloaders
            force: Force update even if cache is valid

        Returns:
            Dictionary mapping repository names to update success
        """
        results = {}

        # Update repositories concurrently
        tasks = []
        for downloader in downloaders:
            task = asyncio.create_task(
                self.update_repository(downloader, force),
                name=f"update_{downloader.repository_info.name}",
            )
            tasks.append((downloader.repository_info.name, task))

        for repo_name, task in tasks:
            try:
                results[repo_name] = await task
            except Exception:
                results[repo_name] = False

        return results

    async def maintenance(self) -> Dict[str, int]:
        """Perform cache maintenance.

        Returns:
            Dictionary with maintenance statistics
        """
        expired_removed = await self.cache.cleanup_expired()

        return {"expired_removed": expired_removed}
