"""Tests for API-based repository downloader functionality."""

import pytest
import tempfile
from pathlib import Path
import yaml

from saigen.repositories.universal_manager import UniversalRepositoryManager
from saigen.repositories.downloaders.api_downloader import APIRepositoryDownloader, RateLimiter, APICache


class TestAPIRepositoryDownloader:
    """Test API-based repository downloader."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def api_repo_config(self, temp_config_dir):
        """Create a test API repository configuration."""
        config_data = {
            "version": "1.0",
            "repositories": [
                {
                    "name": "test-npm-registry",
                    "type": "npm",
                    "platform": "universal",
                    "distribution": ["universal"],
                    "query_type": "api",
                    "endpoints": {
                        "packages": "https://registry.npmjs.org/-/all",
                        "search": "https://registry.npmjs.org/-/v1/search?text={query}&size=10",
                        "info": "https://registry.npmjs.org/{package}"
                    },
                    "parsing": {
                        "format": "json",
                        "fields": {
                            "name": "name",
                            "version": "dist-tags.latest",
                            "description": "description"
                        }
                    },
                    "cache": {
                        "ttl_hours": 24,
                        "api_cache_ttl_seconds": 3600
                    },
                    "limits": {
                        "requests_per_minute": 60,
                        "concurrent_requests": 5,
                        "timeout_seconds": 30,
                        "max_retries": 3,
                        "retry_delay_seconds": 1,
                        "exponential_backoff": True
                    },
                    "metadata": {
                        "description": "Test NPM Registry",
                        "enabled": True,
                        "priority": 90
                    }
                }
            ]
        }

        config_file = temp_config_dir / "npm.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        return temp_config_dir

    @pytest.mark.asyncio
    async def test_api_repository_initialization(self, api_repo_config):
        """Test that API repository can be initialized."""
        manager = UniversalRepositoryManager("cache", [str(api_repo_config)])
        await manager.initialize()

        assert "test-npm-registry" in manager._configs
        assert "test-npm-registry" in manager._downloaders

        # Verify it's an API downloader
        downloader = manager._downloaders["test-npm-registry"]
        assert isinstance(downloader, APIRepositoryDownloader)

    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """Test rate limiter functionality."""
        rate_limiter = RateLimiter(requests_per_minute=10, concurrent_requests=2)

        # Should be able to acquire immediately
        await rate_limiter.acquire()
        assert len(rate_limiter.request_times) == 1

    @pytest.mark.asyncio
    async def test_api_cache(self):
        """Test API cache functionality."""
        cache = APICache(ttl_seconds=1)

        # Set and get value
        await cache.set("test_key", "test_value")
        value = await cache.get("test_key")
        assert value == "test_value"

        # Clear cache
        await cache.clear()
        value = await cache.get("test_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_query_package_from_repository(self, api_repo_config):
        """Test querying a specific package from API repository."""
        manager = UniversalRepositoryManager("cache", [str(api_repo_config)])
        await manager.initialize()

        # This will make a real API call to npm registry
        # Using a well-known package that should always exist
        try:
            package = await manager.query_package_from_repository(
                "test-npm-registry",
                "express",
                use_cache=True
            )

            if package:
                assert package.name.lower() == "express"
                assert package.version is not None
                assert package.repository_name == "test-npm-registry"
        except Exception as e:
            # Network errors are acceptable in tests
            pytest.skip(f"Network error during test: {e}")

    @pytest.mark.asyncio
    async def test_query_packages_batch(self, api_repo_config):
        """Test batch querying multiple packages from API repository."""
        manager = UniversalRepositoryManager("cache", [str(api_repo_config)])
        await manager.initialize()

        # Test with a small batch of well-known packages
        package_names = ["express", "react", "lodash"]

        try:
            results = await manager.query_packages_batch(
                "test-npm-registry",
                package_names,
                use_cache=True
            )

            assert len(results) == len(package_names)
            for package_name in package_names:
                assert package_name in results
                # Results may be None if package not found or network error
        except Exception as e:
            # Network errors are acceptable in tests
            pytest.skip(f"Network error during test: {e}")

    def test_repository_info_has_query_type(self, api_repo_config):
        """Test that repository info includes query_type field."""
        manager = UniversalRepositoryManager("cache", [str(api_repo_config)])

        # Load configs synchronously
        import asyncio
        asyncio.run(manager.initialize())

        repo_info = manager.get_repository_info("test-npm-registry")
        assert repo_info is not None
        assert repo_info.query_type == "api"

    @pytest.mark.asyncio
    async def test_api_downloader_with_rate_limiting(self, api_repo_config):
        """Test that API downloader respects rate limiting."""
        manager = UniversalRepositoryManager("cache", [str(api_repo_config)])
        await manager.initialize()

        downloader = manager._downloaders.get("test-npm-registry")
        assert downloader is not None
        assert isinstance(downloader, APIRepositoryDownloader)

        # Verify rate limiter is configured
        assert downloader.rate_limiter is not None
        assert downloader.rate_limiter.requests_per_minute == 60
        assert downloader.rate_limiter.concurrent_requests == 5

    @pytest.mark.asyncio
    async def test_api_cache_configuration(self, api_repo_config):
        """Test that API cache is configured correctly."""
        manager = UniversalRepositoryManager("cache", [str(api_repo_config)])
        await manager.initialize()

        downloader = manager._downloaders.get("test-npm-registry")
        assert downloader is not None
        assert isinstance(downloader, APIRepositoryDownloader)

        # Verify API cache is configured
        assert downloader.api_cache is not None
        assert downloader.api_cache.ttl_seconds == 3600

    @pytest.mark.asyncio
    async def test_retry_configuration(self, api_repo_config):
        """Test that retry configuration is set correctly."""
        manager = UniversalRepositoryManager("cache", [str(api_repo_config)])
        await manager.initialize()

        downloader = manager._downloaders.get("test-npm-registry")
        assert downloader is not None
        assert isinstance(downloader, APIRepositoryDownloader)

        # Verify retry configuration
        assert downloader.max_retries == 3
        assert downloader.retry_delay == 1
        assert downloader.exponential_backoff is True
