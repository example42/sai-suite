"""Tests for saigen repository manager."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from saigen.repositories.manager import RepositoryManager
from saigen.utils.errors import RepositoryError, ConfigurationError

# Define missing error classes for backward compatibility
class RepositoryNotFoundError(RepositoryError):
    pass
from saigen.repositories.universal_manager import UniversalRepositoryManager
from saigen.models.repository import RepositoryPackage, RepositoryInfo
from saigen.repositories.cache import RepositoryCache


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
                homepage="https://nginx.org"
            ),
            RepositoryPackage(
                name="apache2",
                version="2.4.41",
                description="Apache HTTP Server",
                repository_name="apt",
                platform="linux",
                category="web-server",
                homepage="https://httpd.apache.org"
            )
        ]
    
    @pytest.fixture
    def repository_manager(self, temp_cache_dir, mock_cache):
        """Create repository manager with mock dependencies."""
        config = {
            "repositories": {
                "apt": {
                    "enabled": True,
                    "priority": 80,
                    "cache_ttl": 3600
                },
                "brew": {
                    "enabled": True,
                    "priority": 70,
                    "cache_ttl": 7200
                }
            },
            "cache_directory": str(temp_cache_dir)
        }
        
        manager = RepositoryManager(config)
        manager._cache = mock_cache
        return manager
    
    def test_repository_manager_initialization(self, temp_cache_dir):
        """Test repository manager initialization."""
        config = {
            "repositories": {
                "apt": {"enabled": True, "priority": 80},
                "brew": {"enabled": True, "priority": 70}
            },
            "cache_directory": str(temp_cache_dir)
        }
        
        manager = RepositoryManager(config)
        
        assert manager.cache_directory == temp_cache_dir
        assert len(manager.enabled_repositories) == 2
        assert "apt" in manager.enabled_repositories
        assert "brew" in manager.enabled_repositories
    
    def test_repository_manager_default_config(self):
        """Test repository manager with default configuration."""
        manager = RepositoryManager()
        
        # Should have default repositories enabled
        assert len(manager.enabled_repositories) > 0
        assert manager.cache_directory.name == "cache"
    
    @pytest.mark.asyncio
    async def test_get_packages_from_cache(self, repository_manager, mock_cache, sample_packages):
        """Test getting packages from cache."""
        # Mock cache hit
        mock_cache.get_cached_data.return_value = sample_packages
        mock_cache.is_expired.return_value = False
        
        packages = await repository_manager.get_packages("apt")
        
        assert packages == sample_packages
        mock_cache.get_cached_data.assert_called_once_with("apt")
    
    @pytest.mark.asyncio
    async def test_get_packages_cache_miss(self, repository_manager, mock_cache, sample_packages):
        """Test getting packages when cache misses."""
        # Mock cache miss
        mock_cache.get_cached_data.return_value = None
        
        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_packages = AsyncMock(return_value=sample_packages)
        
        with patch.object(repository_manager, '_get_downloader', return_value=mock_downloader):
            packages = await repository_manager.get_packages("apt")
            
            assert packages == sample_packages
            mock_downloader.download_packages.assert_called_once()
            mock_cache.store_data.assert_called_once_with("apt", sample_packages)
    
    @pytest.mark.asyncio
    async def test_get_packages_cache_expired(self, repository_manager, mock_cache, sample_packages):
        """Test getting packages when cache is expired."""
        # Mock expired cache
        mock_cache.get_cached_data.return_value = sample_packages
        mock_cache.is_expired.return_value = True
        
        # Mock downloader
        mock_downloader = Mock()
        mock_downloader.download_packages = AsyncMock(return_value=sample_packages)
        
        with patch.object(repository_manager, '_get_downloader', return_value=mock_downloader):
            packages = await repository_manager.get_packages("apt", force_refresh=True)
            
            # Should fetch fresh data
            mock_downloader.download_packages.assert_called_once()
            mock_cache.store_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_packages(self, repository_manager, mock_cache, sample_packages):
        """Test searching packages across repositories."""
        # Mock cache returns for multiple repositories
        def mock_get_cached(repo_name):
            if repo_name == "apt":
                return sample_packages
            elif repo_name == "brew":
                return [RepositoryPackage(
                    name="nginx",
                    version="1.21.0",
                    description="HTTP server",
                    repository_name="brew",
                    platform="macos"
                )]
            return []
        
        mock_cache.get_cached_data.side_effect = mock_get_cached
        mock_cache.is_expired.return_value = False
        
        results = await repository_manager.search_packages("nginx")
        
        assert len(results) == 2  # One from apt, one from brew
        assert all(pkg.name == "nginx" for pkg in results)
        assert any(pkg.repository_name == "apt" for pkg in results)
        assert any(pkg.repository_name == "brew" for pkg in results)
    
    @pytest.mark.asyncio
    async def test_search_packages_with_filters(self, repository_manager, mock_cache, sample_packages):
        """Test searching packages with filters."""
        mock_cache.get_cached_data.return_value = sample_packages
        mock_cache.is_expired.return_value = False
        
        # Search with category filter
        results = await repository_manager.search_packages(
            query="server",
            category="web-server",
            repositories=["apt"]
        )
        
        # Should only return web-server category packages
        assert all(pkg.category == "web-server" for pkg in results if pkg.category)
    
    @pytest.mark.asyncio
    async def test_get_package_info(self, repository_manager, mock_cache, sample_packages):
        """Test getting specific package information."""
        mock_cache.get_cached_data.return_value = sample_packages
        mock_cache.is_expired.return_value = False
        
        package = await repository_manager.get_package_info("nginx", "apt")
        
        assert package is not None
        assert package.name == "nginx"
        assert package.repository_name == "apt"
    
    @pytest.mark.asyncio
    async def test_get_package_info_not_found(self, repository_manager, mock_cache):
        """Test getting package info when package not found."""
        mock_cache.get_cached_data.return_value = []
        mock_cache.is_expired.return_value = False
        
        package = await repository_manager.get_package_info("nonexistent", "apt")
        
        assert package is None
    
    @pytest.mark.asyncio
    async def test_update_cache(self, repository_manager, mock_cache, sample_packages):
        """Test updating repository cache."""
        # Mock downloaders
        mock_apt_downloader = Mock()
        mock_apt_downloader.download_packages = AsyncMock(return_value=sample_packages)
        
        mock_brew_downloader = Mock()
        mock_brew_downloader.download_packages = AsyncMock(return_value=[])
        
        def mock_get_downloader(repo_name):
            if repo_name == "apt":
                return mock_apt_downloader
            elif repo_name == "brew":
                return mock_brew_downloader
            return None
        
        with patch.object(repository_manager, '_get_downloader', side_effect=mock_get_downloader):
            result = await repository_manager.update_cache()
            
            assert result["updated_repositories"] == 2
            assert result["total_packages"] >= 0
            assert "apt" in result["repository_stats"]
            assert "brew" in result["repository_stats"]
    
    @pytest.mark.asyncio
    async def test_update_cache_specific_repositories(self, repository_manager, mock_cache, sample_packages):
        """Test updating cache for specific repositories."""
        mock_downloader = Mock()
        mock_downloader.download_packages = AsyncMock(return_value=sample_packages)
        
        with patch.object(repository_manager, '_get_downloader', return_value=mock_downloader):
            result = await repository_manager.update_cache(repositories=["apt"])
            
            assert result["updated_repositories"] == 1
            assert "apt" in result["repository_stats"]
            assert "brew" not in result["repository_stats"]
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, repository_manager, mock_cache):
        """Test clearing repository cache."""
        await repository_manager.clear_cache()
        
        mock_cache.clear_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, repository_manager, mock_cache):
        """Test getting cache statistics."""
        mock_stats = {
            "total_repositories": 2,
            "cached_repositories": 1,
            "cache_size": "10.5 MB",
            "last_updated": datetime.now().isoformat()
        }
        
        mock_cache.get_stats = AsyncMock(return_value=mock_stats)
        
        stats = await repository_manager.get_cache_stats()
        
        assert stats == mock_stats
        mock_cache.get_stats.assert_called_once()
    
    def test_get_enabled_repositories(self, repository_manager):
        """Test getting enabled repositories."""
        enabled = repository_manager.get_enabled_repositories()
        
        assert "apt" in enabled
        assert "brew" in enabled
        assert all(isinstance(config, dict) for config in enabled.values())
    
    def test_get_repository_priority(self, repository_manager):
        """Test getting repository priority."""
        apt_priority = repository_manager.get_repository_priority("apt")
        brew_priority = repository_manager.get_repository_priority("brew")
        
        assert apt_priority == 80
        assert brew_priority == 70
        assert apt_priority > brew_priority  # apt has higher priority
    
    def test_is_repository_enabled(self, repository_manager):
        """Test checking if repository is enabled."""
        assert repository_manager.is_repository_enabled("apt")
        assert repository_manager.is_repository_enabled("brew")
        assert not repository_manager.is_repository_enabled("nonexistent")
    
    @pytest.mark.asyncio
    async def test_repository_not_found_error(self, repository_manager):
        """Test repository not found error handling."""
        with pytest.raises(RepositoryNotFoundError):
            await repository_manager.get_packages("nonexistent")
    
    @pytest.mark.asyncio
    async def test_downloader_error_handling(self, repository_manager, mock_cache):
        """Test error handling when downloader fails."""
        mock_cache.get_cached_data.return_value = None
        
        mock_downloader = Mock()
        mock_downloader.download_packages = AsyncMock(side_effect=Exception("Download failed"))
        
        with patch.object(repository_manager, '_get_downloader', return_value=mock_downloader):
            with pytest.raises(RepositoryManagerError):
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
                    "urls": {
                        "package_list": "http://packages.ubuntu.com/packages.txt"
                    },
                    "parser": {
                        "format": "text",
                        "delimiter": "\n",
                        "fields": ["name", "version", "description"]
                    }
                }
            }
        }
        
        config_file = temp_config_dir / "repositories.yaml"
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        return config_file
    
    def test_universal_manager_initialization(self, sample_repository_config):
        """Test universal repository manager initialization."""
        manager = UniversalRepositoryManager("cache", [str(sample_repository_config.parent)])
        
        assert len(manager.repository_configs) == 1
        assert "apt" in manager.repository_configs
        assert manager.repository_configs["apt"]["enabled"]
    
    @pytest.mark.asyncio
    async def test_universal_manager_download(self, sample_repository_config):
        """Test universal manager package download."""
        manager = UniversalRepositoryManager("cache", [str(sample_repository_config.parent)])
        
        # Mock HTTP response
        mock_response_text = "nginx\t1.20.1\tHTTP server\napache2\t2.4.41\tApache server"
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.text = AsyncMock(return_value=mock_response_text)
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            packages = await manager.download_packages("apt")
            
            assert len(packages) == 2
            assert packages[0].name == "nginx"
            assert packages[1].name == "apache2"
    
    def test_universal_manager_get_supported_repositories(self, sample_repository_config):
        """Test getting supported repositories."""
        manager = UniversalRepositoryManager("cache", [str(sample_repository_config.parent)])
        
        supported = manager.get_supported_repositories()
        
        assert "apt" in supported
        assert supported["apt"]["enabled"]
        assert supported["apt"]["priority"] == 80
    
    @pytest.mark.asyncio
    async def test_universal_manager_error_handling(self, sample_repository_config):
        """Test universal manager error handling."""
        manager = UniversalRepositoryManager("cache", [str(sample_repository_config.parent)])
        
        # Mock HTTP error
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            with pytest.raises(Exception):
                await manager.download_packages("apt")
    
    def test_universal_manager_invalid_config(self):
        """Test universal manager with invalid config file."""
        with pytest.raises((FileNotFoundError, ConfigurationError)):
            UniversalRepositoryManager("cache", ["/nonexistent/"])


@pytest.mark.integration
class TestRepositoryManagerIntegration:
    """Integration tests for repository manager."""
    
    @pytest.mark.asyncio
    async def test_full_repository_workflow(self):
        """Test complete repository management workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            
            config = {
                "repositories": {
                    "test_repo": {
                        "enabled": True,
                        "priority": 90,
                        "cache_ttl": 3600
                    }
                },
                "cache_directory": str(cache_dir)
            }
            
            manager = RepositoryManager(config)
            
            # Mock a simple downloader
            mock_packages = [
                RepositoryPackage(
                    name="test-package",
                    version="1.0.0",
                    description="Test package",
                    repository_name="test_repo",
                    platform="linux"
                )
            ]
            
            mock_downloader = Mock()
            mock_downloader.download_packages = AsyncMock(return_value=mock_packages)
            
            with patch.object(manager, '_get_downloader', return_value=mock_downloader):
                # Test cache update
                update_result = await manager.update_cache(repositories=["test_repo"])
                assert update_result["updated_repositories"] == 1
                
                # Test package retrieval
                packages = await manager.get_packages("test_repo")
                assert len(packages) == 1
                assert packages[0].name == "test-package"
                
                # Test package search
                search_results = await manager.search_packages("test")
                assert len(search_results) >= 1
                
                # Test cache stats
                stats = await manager.get_cache_stats()
                assert isinstance(stats, dict)
                
                # Test cache clear
                await manager.clear_cache()