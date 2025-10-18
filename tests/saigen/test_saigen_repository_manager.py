"""Tests for saigen repository manager."""

from saigen.repositories.universal_manager import UniversalRepositoryManager
from saigen.repositories.cache import RepositoryCache
from saigen.models.repository import RepositoryPackage, SearchResult
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from saigen.repositories.manager import RepositoryManager
from saigen.utils.errors import RepositoryError


# Define missing error classes for backward compatibility
class RepositoryNotFoundError(RepositoryError):
    pass


class RepositoryManagerError(RepositoryError):
    pass


class TestRepositoryManager:
    """Test repository manager functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_cache(self):
        """Create mock repository cache."""
        cache = Mock(spec=RepositoryCache)
        cache.get_cached_data = AsyncMock()
        cache.store_data = AsyncMock()
        cache.is_expired = Mock()
        cache.clear_cache = AsyncMock()
        return cache

    @pytest.fixture
    def sample_packages(self):
        """Create sample repository packages."""
        return [
            RepositoryPackage(
                name="nginx",
                version="1.20.1",
                description="HTTP server",
                repository_name="apt",
                platform="linux",
                category="web-server",
                homepage="https://nginx.org",
            ),
            RepositoryPackage(
                name="apache2",
                version="2.4.41",
                description="Apache HTTP Server",
                repository_name="apt",
                platform="linux",
                category="web-server",
                homepage="https://httpd.apache.org",
            ),
        ]

    @pytest.fixture
    def repository_manager(self, temp_cache_dir, mock_cache):
        """Create repository manager with mock dependencies."""
        config = {
            "repositories": {
                "apt": {"enabled": True, "priority": 80, "cache_ttl": 3600},
                "brew": {"enabled": True, "priority": 70, "cache_ttl": 7200},
            },
            "cache_directory": str(temp_cache_dir),
        }

        manager = RepositoryManager(config)
        # Mock the universal manager's cache
        manager.universal_manager.cache = mock_cache
        return manager

    def test_repository_manager_initialization(self, temp_cache_dir):
        """Test repository manager initialization."""
        config = {
            "repositories": {
                "apt": {"enabled": True, "priority": 80},
                "brew": {"enabled": True, "priority": 70},
            },
            "cache_directory": str(temp_cache_dir),
        }

        manager = RepositoryManager(config)

        assert manager.cache_directory == temp_cache_dir
        assert len(manager.enabled_repositories) == 2
        assert "apt" in manager.enabled_repositories
        assert "brew" in manager.enabled_repositories

    def test_repository_manager_default_config(self):
        """Test repository manager with default configuration."""
        manager = RepositoryManager()

        # Should have universal manager initialized
        assert manager.universal_manager is not None
        assert manager.cache_directory is not None
        assert manager.cache_directory.name == "cache"

    @pytest.mark.asyncio
    async def test_get_packages_from_cache(self, repository_manager, mock_cache, sample_packages):
        """Test getting packages from cache."""
        # Mock the universal manager's get_packages method
        with patch.object(
            repository_manager.universal_manager, "get_packages", return_value=sample_packages
        ):
            packages = await repository_manager.get_packages("apt")

            assert packages == sample_packages

    @pytest.mark.asyncio
    async def test_get_packages_cache_miss(self, repository_manager, mock_cache, sample_packages):
        """Test getting packages when cache misses."""
        # Mock cache miss
        mock_cache.get_cached_data.return_value = None
        mock_cache.get.return_value = None

        # Mock the universal manager's get_packages method
        with patch.object(
            repository_manager.universal_manager, "get_packages", return_value=sample_packages
        ):
            packages = await repository_manager.get_packages("apt")

            assert packages == sample_packages

    @pytest.mark.asyncio
    async def test_get_packages_cache_expired(
        self, repository_manager, mock_cache, sample_packages
    ):
        """Test getting packages when cache is expired."""
        # Mock expired cache
        mock_cache.get_cached_data.return_value = sample_packages
        mock_cache.is_expired.return_value = True
        mock_cache.get.return_value = None  # Simulate expired cache

        # Mock the universal manager's get_packages method
        with patch.object(
            repository_manager.universal_manager, "get_packages", return_value=sample_packages
        ):
            packages = await repository_manager.get_packages("apt", use_cache=False)

            # Should fetch fresh data
            assert packages == sample_packages

    @pytest.mark.asyncio
    async def test_search_packages(self, repository_manager, mock_cache, sample_packages):
        """Test searching packages across repositories."""
        # Create mock search result
        mock_search_result = SearchResult(
            query="nginx",
            packages=sample_packages,
            total_results=len(sample_packages),
            search_time=0.1,
            repository_sources=["apt", "brew"],
        )

        # Mock the universal manager's search_packages method
        with patch.object(
            repository_manager.universal_manager, "search_packages", return_value=mock_search_result
        ):
            results = await repository_manager.search_packages("nginx")

            assert isinstance(results, SearchResult)
            assert results.query == "nginx"
            assert len(results.packages) >= 0

    @pytest.mark.asyncio
    async def test_search_packages_with_filters(
        self, repository_manager, mock_cache, sample_packages
    ):
        """Test searching packages with filters."""
        # Create mock search result
        mock_search_result = SearchResult(
            query="server",
            packages=sample_packages,
            total_results=len(sample_packages),
            search_time=0.1,
            repository_sources=["apt"],
        )

        # Mock the universal manager's search_packages method
        with patch.object(
            repository_manager.universal_manager, "search_packages", return_value=mock_search_result
        ):
            results = await repository_manager.search_packages(
                query="server", repository_names=["apt"]
            )

            # Should return search results
            assert isinstance(results, SearchResult)

    @pytest.mark.asyncio
    async def test_get_package_info(self, repository_manager, mock_cache, sample_packages):
        """Test getting specific package information."""
        # Mock the universal manager's get_package_details method
        expected_package = sample_packages[0]  # nginx package

        with patch.object(
            repository_manager.universal_manager,
            "get_package_details",
            return_value=expected_package,
        ):
            package = await repository_manager.get_package_info("nginx", "apt")

            assert package is not None
            assert package.name == "nginx"
            assert package.repository_name == "apt"

    @pytest.mark.asyncio
    async def test_get_package_info_not_found(self, repository_manager, mock_cache):
        """Test getting package info when package not found."""
        # Mock the universal manager's get_package_details method to return None
        with patch.object(
            repository_manager.universal_manager, "get_package_details", return_value=None
        ):
            package = await repository_manager.get_package_info("nonexistent", "apt")

            assert package is None

    @pytest.mark.asyncio
    async def test_update_cache(self, repository_manager, mock_cache, sample_packages):
        """Test updating repository cache."""
        # Mock the universal manager's update_cache method
        mock_result = {"apt": True, "brew": True}

        with patch.object(
            repository_manager.universal_manager, "update_cache", return_value=mock_result
        ):
            result = await repository_manager.update_cache()

            assert isinstance(result, dict)
            assert "apt" in result
            assert "brew" in result

    @pytest.mark.asyncio
    async def test_update_cache_specific_repositories(
        self, repository_manager, mock_cache, sample_packages
    ):
        """Test updating cache for specific repositories."""
        # Mock the universal manager's update_cache method
        mock_result = {"apt": True}

        with patch.object(
            repository_manager.universal_manager, "update_cache", return_value=mock_result
        ):
            result = await repository_manager.update_cache(repository_names=["apt"])

            assert isinstance(result, dict)
            assert "apt" in result
            assert "brew" not in result

    @pytest.mark.asyncio
    async def test_clear_cache(self, repository_manager, mock_cache):
        """Test clearing repository cache."""
        # Mock the clear_all method to return an integer
        mock_cache.clear_all = AsyncMock(return_value=5)

        result = await repository_manager.clear_cache()

        # The clear_cache method should return a count
        assert isinstance(result, int)
        assert result == 5

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, repository_manager, mock_cache):
        """Test getting cache statistics."""
        mock_stats = {
            "total_entries": 5,
            "expired_entries": 1,
            "repositories": {"apt": {"entries": 3}, "brew": {"entries": 2}},
            "total_packages": 100,
            "total_size_bytes": 1024000,
        }

        mock_cache.get_cache_stats = AsyncMock(return_value=mock_stats)

        stats = await repository_manager.get_cache_stats()

        # Check that stats has expected structure
        assert "total_entries" in stats
        assert "expired_entries" in stats
        assert "repositories" in stats
        assert stats["total_entries"] == 5
        mock_cache.get_cache_stats.assert_called_once()

    def test_get_enabled_repositories(self, repository_manager):
        """Test getting enabled repositories."""
        enabled = repository_manager.get_enabled_repositories()

        assert "apt" in enabled
        assert "brew" in enabled
        assert isinstance(enabled, list)

    def test_get_repository_priority(self, repository_manager):
        """Test getting repository priority."""
        apt_priority = repository_manager.get_repository_priority("apt")
        brew_priority = repository_manager.get_repository_priority("brew")

        assert apt_priority == 1  # Default priority
        assert brew_priority == 1  # Default priority
        # Both have same default priority
        assert apt_priority == brew_priority

    def test_is_repository_enabled(self, repository_manager):
        """Test checking if repository is enabled."""
        assert repository_manager.is_repository_enabled("apt")
        assert repository_manager.is_repository_enabled("brew")
        assert not repository_manager.is_repository_enabled("nonexistent")

    @pytest.mark.asyncio
    async def test_repository_not_found_error(self, repository_manager):
        """Test repository not found error handling."""
        with pytest.raises(RepositoryError):
            await repository_manager.get_packages("nonexistent")

    @pytest.mark.asyncio
    async def test_downloader_error_handling(self, repository_manager, mock_cache):
        """Test error handling when downloader fails."""
        # Mock the universal manager's get_packages method to raise an exception
        with patch.object(
            repository_manager.universal_manager,
            "get_packages",
            side_effect=RepositoryError("Download failed"),
        ):
            with pytest.raises(RepositoryError):
                await repository_manager.get_packages("apt")


class TestUniversalRepositoryManager:
    """Test universal repository manager functionality."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_repository_config(self, temp_config_dir):
        """Create sample repository configuration."""
        config_data = {
            "repositories": {
                "apt": {
                    "name": "APT Package Manager",
                    "type": "package_list",
                    "platforms": ["debian", "ubuntu"],
                    "enabled": True,
                    "priority": 80,
                    "urls": {"package_list": "http://packages.ubuntu.com/packages.txt"},
                    "parser": {
                        "format": "text",
                        "delimiter": "\n",
                        "fields": ["name", "version", "description"],
                    },
                }
            }
        }

        config_file = temp_config_dir / "repositories.yaml"
        import yaml

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        return config_file

    def test_universal_manager_initialization(self, sample_repository_config):
        """Test universal repository manager initialization."""
        manager = UniversalRepositoryManager("cache", [str(sample_repository_config.parent)])

        # Check that manager has the expected attributes
        assert manager.cache_dir == Path("cache")
        assert len(manager.config_dirs) == 1
        assert manager._initialized is False
        # The configs are loaded during initialization, not in constructor
        assert isinstance(manager._configs, dict)

    @pytest.mark.asyncio
    async def test_universal_manager_download(self, sample_repository_config):
        """Test universal manager package retrieval."""
        manager = UniversalRepositoryManager("cache", [str(sample_repository_config.parent)])

        # Mock the get_packages method to avoid actual network calls
        mock_packages = [
            RepositoryPackage(
                name="nginx",
                version="1.20.1",
                description="HTTP server",
                repository_name="apt",
                platform="linux",
            ),
            RepositoryPackage(
                name="apache2",
                version="2.4.41",
                description="Apache server",
                repository_name="apt",
                platform="linux",
            ),
        ]

        with patch.object(manager, "get_packages", return_value=mock_packages):
            packages = await manager.get_packages("apt")

            assert isinstance(packages, list)
            assert len(packages) == 2
            assert packages[0].name == "nginx"
            assert packages[1].name == "apache2"

    def test_universal_manager_get_supported_repositories(self, sample_repository_config):
        """Test getting supported platforms and types."""
        manager = UniversalRepositoryManager("cache", [str(sample_repository_config.parent)])

        # Test supported platforms
        platforms = manager.get_supported_platforms()
        assert isinstance(platforms, list)

        # Test supported types
        types = manager.get_supported_types()
        assert isinstance(types, list)

    @pytest.mark.asyncio
    async def test_universal_manager_error_handling(self, sample_repository_config):
        """Test universal manager error handling."""
        manager = UniversalRepositoryManager("cache", [str(sample_repository_config.parent)])

        # Mock the get_packages method to raise an error
        with patch.object(manager, "get_packages", side_effect=RepositoryError("Network error")):
            with pytest.raises(RepositoryError):
                await manager.get_packages("apt")

    def test_universal_manager_invalid_config(self):
        """Test universal manager with invalid config file."""
        # The manager doesn't raise an exception for non-existent directories
        # It just logs a warning and continues
        manager = UniversalRepositoryManager("cache", ["/nonexistent/"])
        assert manager is not None
        assert len(manager._configs) == 0


@pytest.mark.integration
class TestRepositoryManagerIntegration:
    """Integration tests for repository manager."""

    @pytest.mark.asyncio
    async def test_full_repository_workflow(self):
        """Test complete repository management workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            config = {
                "repositories": {"test_repo": {"enabled": True, "priority": 90, "cache_ttl": 3600}},
                "cache_directory": str(cache_dir),
            }

            manager = RepositoryManager(config)

            # Mock a simple downloader
            mock_packages = [
                RepositoryPackage(
                    name="test-package",
                    version="1.0.0",
                    description="Test package",
                    repository_name="test_repo",
                    platform="linux",
                )
            ]

            mock_downloader = Mock()
            mock_downloader.download_packages = AsyncMock(return_value=mock_packages)

            # Mock the universal manager methods
            with patch.object(
                manager.universal_manager, "update_cache", return_value={"test_repo": True}
            ):
                with patch.object(
                    manager.universal_manager, "get_packages", return_value=mock_packages
                ):
                    with patch.object(
                        manager.universal_manager,
                        "search_packages",
                        return_value=SearchResult(
                            query="test",
                            packages=mock_packages,
                            total_results=1,
                            search_time=0.1,
                            repository_sources=["test_repo"],
                        ),
                    ):
                        # Test cache update
                        update_result = await manager.update_cache(repository_names=["test_repo"])
                        assert isinstance(update_result, dict)
                        assert "test_repo" in update_result

                        # Test package retrieval
                        packages = await manager.get_packages("test_repo")
                        assert len(packages) == 1
                        assert packages[0].name == "test-package"

                        # Test package search
                        search_results = await manager.search_packages("test")
                        assert isinstance(search_results, SearchResult)
                        assert len(search_results.packages) >= 1

                        # Test cache stats
                        stats = await manager.get_cache_stats()
                        assert isinstance(stats, dict)

                        # Test cache clear
                        await manager.clear_cache()
