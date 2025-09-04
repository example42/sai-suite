"""Tests for repository cache system."""

import pytest
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from saigen.models.repository import RepositoryPackage, RepositoryInfo, CacheEntry
from saigen.repositories.cache import RepositoryCache, CacheManager
from saigen.repositories.downloaders.base import BaseRepositoryDownloader
from saigen.utils.errors import CacheError


class MockRepositoryDownloader(BaseRepositoryDownloader):
    """Mock repository downloader for testing."""
    
    def __init__(self, repository_info: RepositoryInfo, packages: list = None):
        super().__init__(repository_info)
        self.mock_packages = packages or []
        self.download_called = False
        self.metadata_called = False
    
    async def download_package_list(self):
        """Mock download implementation."""
        self.download_called = True
        return self.mock_packages
    
    async def search_package(self, name: str):
        """Mock search implementation."""
        return [pkg for pkg in self.mock_packages if name.lower() in pkg.name.lower()]
    
    async def get_package_details(self, name: str, version=None):
        """Mock package details implementation."""
        for pkg in self.mock_packages:
            if pkg.name == name and (version is None or pkg.version == version):
                return pkg
        return None
    
    async def get_repository_metadata(self):
        """Mock metadata implementation."""
        self.metadata_called = True
        return {
            'package_count': len(self.mock_packages),
            'last_updated': datetime.utcnow(),
            'test_metadata': True
        }


class TestRepositoryCache:
    """Test RepositoryCache functionality."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_packages(self):
        """Sample repository packages."""
        return [
            RepositoryPackage(
                name="nginx",
                version="1.24.0",
                description="HTTP server",
                repository_name="test-repo",
                platform="linux"
            ),
            RepositoryPackage(
                name="apache2",
                version="2.4.57",
                description="Apache HTTP Server",
                repository_name="test-repo",
                platform="linux"
            )
        ]
    
    @pytest.fixture
    def repository_info(self):
        """Sample repository info."""
        return RepositoryInfo(
            name="test-repo",
            type="apt",
            platform="linux",
            url="https://example.com/repo"
        )
    
    def test_cache_initialization(self, temp_cache_dir):
        """Test cache initialization."""
        cache = RepositoryCache(temp_cache_dir)
        
        assert cache.cache_dir == temp_cache_dir
        assert cache.default_ttl == timedelta(hours=24)
        assert temp_cache_dir.exists()
    
    def test_cache_key_sanitization(self, temp_cache_dir):
        """Test cache key sanitization."""
        cache = RepositoryCache(temp_cache_dir)
        
        # Test dangerous characters
        dangerous_key = "../../../etc/passwd"
        safe_key = cache._sanitize_cache_key(dangerous_key)
        assert "../" not in safe_key
        assert safe_key == "_________etc_passwd"
        
        # Test long key
        long_key = "a" * 300
        safe_long_key = cache._sanitize_cache_key(long_key)
        assert len(safe_long_key) <= 200
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, temp_cache_dir, sample_packages):
        """Test setting and getting cache entries."""
        cache = RepositoryCache(temp_cache_dir)
        cache_key = "test-key"
        
        # Set cache entry
        await cache.set(
            cache_key=cache_key,
            packages=sample_packages,
            repository_name="test-repo",
            ttl=timedelta(hours=1)
        )
        
        # Get cache entry
        entry = await cache.get(cache_key)
        
        assert entry is not None
        assert entry.repository_name == "test-repo"
        assert len(entry.data) == 2
        assert entry.data[0].name == "nginx"
        assert entry.data[1].name == "apache2"
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, temp_cache_dir, sample_packages):
        """Test cache entry expiration."""
        cache = RepositoryCache(temp_cache_dir)
        cache_key = "expiring-key"
        
        # Set cache entry with very short TTL
        await cache.set(
            cache_key=cache_key,
            packages=sample_packages,
            repository_name="test-repo",
            ttl=timedelta(milliseconds=1)
        )
        
        # Wait for expiration
        await asyncio.sleep(0.01)
        
        # Should return None for expired entry
        entry = await cache.get(cache_key)
        assert entry is None
        
        # Cache files should be cleaned up
        cache_path = cache._get_cache_path(cache_key)
        meta_path = cache._get_metadata_path(cache_key)
        assert not cache_path.exists()
        assert not meta_path.exists()
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, temp_cache_dir, sample_packages):
        """Test cache invalidation."""
        cache = RepositoryCache(temp_cache_dir)
        cache_key = "invalidate-key"
        
        # Set cache entry
        await cache.set(
            cache_key=cache_key,
            packages=sample_packages,
            repository_name="test-repo"
        )
        
        # Verify entry exists
        entry = await cache.get(cache_key)
        assert entry is not None
        
        # Invalidate entry
        result = await cache.invalidate(cache_key)
        assert result is True
        
        # Verify entry is gone
        entry = await cache.get(cache_key)
        assert entry is None
    
    @pytest.mark.asyncio
    async def test_cache_get_or_fetch(self, temp_cache_dir, sample_packages, repository_info):
        """Test get_or_fetch functionality."""
        cache = RepositoryCache(temp_cache_dir)
        downloader = MockRepositoryDownloader(repository_info, sample_packages)
        
        # First call should fetch from downloader
        packages = await cache.get_or_fetch(downloader)
        
        assert len(packages) == 2
        assert downloader.download_called is True
        assert downloader.metadata_called is True
        
        # Reset mock flags
        downloader.download_called = False
        downloader.metadata_called = False
        
        # Second call should use cache
        packages = await cache.get_or_fetch(downloader)
        
        assert len(packages) == 2
        assert downloader.download_called is False  # Should not call downloader again
        assert downloader.metadata_called is False
    
    @pytest.mark.asyncio
    async def test_cache_invalidate_repository(self, temp_cache_dir, sample_packages):
        """Test invalidating all entries for a repository."""
        cache = RepositoryCache(temp_cache_dir)
        
        # Set multiple cache entries for same repository
        await cache.set("key1", sample_packages, "test-repo")
        await cache.set("key2", sample_packages, "test-repo")
        await cache.set("key3", sample_packages, "other-repo")
        
        # Invalidate entries for test-repo
        removed_count = await cache.invalidate_repository("test-repo")
        
        assert removed_count == 2
        
        # Verify correct entries were removed
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is not None  # Different repo, should remain
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_expired(self, temp_cache_dir, sample_packages):
        """Test cleanup of expired entries."""
        cache = RepositoryCache(temp_cache_dir)
        
        # Set entries with different TTLs
        await cache.set("fresh", sample_packages, "repo1", ttl=timedelta(hours=1))
        await cache.set("expired1", sample_packages, "repo2", ttl=timedelta(milliseconds=1))
        await cache.set("expired2", sample_packages, "repo3", ttl=timedelta(milliseconds=1))
        
        # Wait for expiration
        await asyncio.sleep(0.01)
        
        # Cleanup expired entries
        removed_count = await cache.cleanup_expired()
        
        assert removed_count == 2
        
        # Verify correct entries remain
        assert await cache.get("fresh") is not None
        assert await cache.get("expired1") is None
        assert await cache.get("expired2") is None
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, temp_cache_dir, sample_packages):
        """Test cache statistics."""
        cache = RepositoryCache(temp_cache_dir)
        
        # Set some cache entries
        await cache.set("key1", sample_packages, "repo1")
        await cache.set("key2", sample_packages[:1], "repo2")
        
        stats = await cache.get_cache_stats()
        
        assert stats['total_entries'] == 2
        assert stats['expired_entries'] == 0
        assert stats['total_packages'] == 3  # 2 + 1
        assert stats['total_size_bytes'] > 0
        assert 'repo1' in stats['repositories']
        assert 'repo2' in stats['repositories']
        assert stats['repositories']['repo1']['packages'] == 2
        assert stats['repositories']['repo2']['packages'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_clear_all(self, temp_cache_dir, sample_packages):
        """Test clearing all cache entries."""
        cache = RepositoryCache(temp_cache_dir)
        
        # Set multiple cache entries
        await cache.set("key1", sample_packages, "repo1")
        await cache.set("key2", sample_packages, "repo2")
        await cache.set("key3", sample_packages, "repo3")
        
        # Clear all entries
        removed_count = await cache.clear_all()
        
        assert removed_count == 3
        
        # Verify all entries are gone
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None
    
    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self, temp_cache_dir, sample_packages):
        """Test concurrent cache access."""
        cache = RepositoryCache(temp_cache_dir)
        cache_key = "concurrent-key"
        
        async def set_cache():
            await cache.set(cache_key, sample_packages, "test-repo")
        
        async def get_cache():
            return await cache.get(cache_key)
        
        # Run concurrent operations
        tasks = [set_cache(), get_cache(), get_cache()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should not raise exceptions
        for result in results:
            assert not isinstance(result, Exception)
    
    @pytest.mark.asyncio
    async def test_cache_corrupted_files(self, temp_cache_dir):
        """Test handling of corrupted cache files."""
        cache = RepositoryCache(temp_cache_dir)
        cache_key = "corrupted-key"
        
        # Create corrupted cache files
        cache_path = cache._get_cache_path(cache_key)
        meta_path = cache._get_metadata_path(cache_key)
        
        cache_path.write_bytes(b"corrupted data")
        meta_path.write_text("invalid json")
        
        # Should return None for corrupted cache
        entry = await cache.get(cache_key)
        assert entry is None
        
        # Files should be cleaned up
        assert not cache_path.exists()
        assert not meta_path.exists()


class TestCacheManager:
    """Test CacheManager functionality."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_packages(self):
        """Sample repository packages."""
        return [
            RepositoryPackage(
                name="test-package",
                version="1.0.0",
                description="Test package",
                repository_name="test-repo",
                platform="linux"
            )
        ]
    
    @pytest.fixture
    def repository_info(self):
        """Sample repository info."""
        return RepositoryInfo(
            name="test-repo",
            type="apt",
            platform="linux",
            url="https://example.com/repo"
        )
    
    @pytest.mark.asyncio
    async def test_update_repository_cache_miss(self, temp_cache_dir, sample_packages, repository_info):
        """Test updating repository when cache is empty."""
        cache = RepositoryCache(temp_cache_dir)
        manager = CacheManager(cache)
        downloader = MockRepositoryDownloader(repository_info, sample_packages)
        
        # Update repository (cache miss)
        result = await manager.update_repository(downloader, force=False)
        
        assert result is True
        assert downloader.download_called is True
    
    @pytest.mark.asyncio
    async def test_update_repository_cache_hit(self, temp_cache_dir, sample_packages, repository_info):
        """Test updating repository when cache is valid."""
        cache = RepositoryCache(temp_cache_dir)
        manager = CacheManager(cache)
        downloader = MockRepositoryDownloader(repository_info, sample_packages)
        
        # Pre-populate cache
        await cache.set(
            downloader.get_cache_key(),
            sample_packages,
            "test-repo",
            ttl=timedelta(hours=1)
        )
        
        # Update repository (cache hit)
        result = await manager.update_repository(downloader, force=False)
        
        assert result is False  # No update needed
        assert downloader.download_called is False
    
    @pytest.mark.asyncio
    async def test_update_repository_force(self, temp_cache_dir, sample_packages, repository_info):
        """Test force updating repository."""
        cache = RepositoryCache(temp_cache_dir)
        manager = CacheManager(cache)
        downloader = MockRepositoryDownloader(repository_info, sample_packages)
        
        # Pre-populate cache
        await cache.set(
            downloader.get_cache_key(),
            sample_packages,
            "test-repo",
            ttl=timedelta(hours=1)
        )
        
        # Force update repository
        result = await manager.update_repository(downloader, force=True)
        
        assert result is True
        assert downloader.download_called is True
    
    @pytest.mark.asyncio
    async def test_update_all_repositories(self, temp_cache_dir, sample_packages):
        """Test updating multiple repositories."""
        cache = RepositoryCache(temp_cache_dir)
        manager = CacheManager(cache)
        
        # Create multiple downloaders
        repo1 = RepositoryInfo(name="repo1", type="apt", platform="linux")
        repo2 = RepositoryInfo(name="repo2", type="brew", platform="macos")
        
        downloader1 = MockRepositoryDownloader(repo1, sample_packages)
        downloader2 = MockRepositoryDownloader(repo2, sample_packages)
        
        # Update all repositories
        results = await manager.update_all_repositories([downloader1, downloader2])
        
        assert len(results) == 2
        assert results["repo1"] is True
        assert results["repo2"] is True
        assert downloader1.download_called is True
        assert downloader2.download_called is True
    
    @pytest.mark.asyncio
    async def test_maintenance(self, temp_cache_dir, sample_packages):
        """Test cache maintenance."""
        cache = RepositoryCache(temp_cache_dir)
        manager = CacheManager(cache)
        
        # Set expired entries
        await cache.set("expired1", sample_packages, "repo1", ttl=timedelta(milliseconds=1))
        await cache.set("expired2", sample_packages, "repo2", ttl=timedelta(milliseconds=1))
        
        # Wait for expiration
        await asyncio.sleep(0.01)
        
        # Run maintenance
        stats = await manager.maintenance()
        
        assert stats['expired_removed'] == 2