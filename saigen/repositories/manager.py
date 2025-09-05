"""Repository manager - Universal YAML-driven system."""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from saigen.models.repository import RepositoryPackage, RepositoryInfo, SearchResult
from saigen.repositories.universal_manager import UniversalRepositoryManager
from saigen.utils.errors import RepositoryError


logger = logging.getLogger(__name__)


class RepositoryManager:
    """Universal repository manager using YAML-driven configuration.
    
    This is the main interface for repository management, now powered by
    the universal system that supports 50+ package managers through YAML configuration.
    """
    
    def __init__(self, cache_dir: Union[str, Path], config_dir: Union[str, Path]):
        """Initialize repository manager.
        
        Args:
            cache_dir: Directory for caching repository data
            config_dir: Directory containing repository configurations
        """
        # Initialize universal manager with config directories
        config_dirs = [
            Path(config_dir),
            Path(__file__).parent / "configs"  # Built-in configs
        ]
        self.universal_manager = UniversalRepositoryManager(cache_dir, config_dirs)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the repository manager."""
        if not self._initialized:
            await self.universal_manager.initialize()
            self._initialized = True
            logger.info("Repository Manager initialized with Universal system")
    
    async def get_packages(self, repository_name: str, use_cache: bool = True) -> List[RepositoryPackage]:
        """Get packages from a specific repository.
        
        Args:
            repository_name: Name of the repository
            use_cache: Whether to use cached data
            
        Returns:
            List of packages from the repository
            
        Raises:
            RepositoryError: If repository not found or data retrieval fails
        """
        if not self._initialized:
            await self.initialize()
        return await self.universal_manager.get_packages(repository_name, use_cache)
    
    async def get_all_packages(self, platform: Optional[str] = None, 
                             repository_type: Optional[str] = None,
                             use_cache: bool = True) -> Dict[str, List[RepositoryPackage]]:
        """Get packages from all repositories.
        
        Args:
            platform: Filter by platform (optional)
            repository_type: Filter by repository type (optional)
            use_cache: Whether to use cached data
            
        Returns:
            Dictionary mapping repository names to package lists
        """
        if not self._initialized:
            await self.initialize()
        return await self.universal_manager.get_all_packages(platform, repository_type, use_cache)
    
    async def search_packages(self, query: str, platform: Optional[str] = None,
                            repository_type: Optional[str] = None,
                            repository_names: Optional[List[str]] = None,
                            limit: Optional[int] = None) -> SearchResult:
        """Search for packages across repositories.
        
        Args:
            query: Search query
            platform: Filter by platform (optional)
            repository_type: Filter by repository type (optional)
            repository_names: Specific repositories to search (optional)
            limit: Maximum number of results (optional)
            
        Returns:
            Search results with packages from all matching repositories
        """
        if not self._initialized:
            await self.initialize()
        return await self.universal_manager.search_packages(
            query, platform, repository_type, repository_names, limit
        )
    
    async def get_package_details(self, package_name: str, version: Optional[str] = None,
                                platform: Optional[str] = None,
                                repository_type: Optional[str] = None) -> Optional[RepositoryPackage]:
        """Get detailed information for a specific package.
        
        Args:
            package_name: Name of the package
            version: Specific version (optional)
            platform: Filter by platform (optional)
            repository_type: Filter by repository type (optional)
            
        Returns:
            Package details or None if not found
        """
        if not self._initialized:
            await self.initialize()
        return await self.universal_manager.get_package_details(
            package_name, version, platform, repository_type
        )
    
    async def update_cache(self, repository_names: Optional[List[str]] = None,
                         force: bool = False) -> Dict[str, bool]:
        """Update repository cache.
        
        Args:
            repository_names: Specific repositories to update (optional)
            force: Force update even if cache is valid
            
        Returns:
            Dictionary mapping repository names to update success
        """
        if not self._initialized:
            await self.initialize()
        return await self.universal_manager.update_cache(repository_names, force)
    
    def get_repository_info(self, repository_name: str) -> Optional[RepositoryInfo]:
        """Get repository information.
        
        Args:
            repository_name: Name of the repository
            
        Returns:
            Repository information or None if not found
        """
        return self.universal_manager.get_repository_info(repository_name)
    
    def get_all_repository_info(self, platform: Optional[str] = None,
                              repository_type: Optional[str] = None) -> List[RepositoryInfo]:
        """Get information for all repositories.
        
        Args:
            platform: Filter by platform (optional)
            repository_type: Filter by repository type (optional)
            
        Returns:
            List of repository information
        """
        return self.universal_manager.get_all_repository_info(platform, repository_type)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive repository statistics.
        
        Returns:
            Dictionary with repository statistics
        """
        if not self._initialized:
            await self.initialize()
        return await self.universal_manager.get_repository_statistics()
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self._initialized:
            await self.initialize()
        return await self.universal_manager.cache.get_cache_stats()
    
    async def clear_cache(self, repository_names: Optional[List[str]] = None) -> int:
        """Clear repository cache.
        
        Args:
            repository_names: Specific repositories to clear (optional)
            
        Returns:
            Number of cache entries removed
        """
        if not self._initialized:
            await self.initialize()
        
        if repository_names is None:
            # Clear all cache
            return await self.universal_manager.cache.clear_all()
        else:
            # Clear specific repositories
            removed_count = 0
            for repo_name in repository_names:
                # Clear cache entries for this repository
                cache_key = f"{repo_name}_packages"
                if await self.universal_manager.cache.has_key(cache_key):
                    await self.universal_manager.cache.delete(cache_key)
                    removed_count += 1
            return removed_count
    
    async def cleanup_cache(self) -> Dict[str, int]:
        """Clean up expired cache entries.
        
        Returns:
            Dictionary with cleanup statistics
        """
        if not self._initialized:
            await self.initialize()
        
        expired_removed = await self.universal_manager.cache.cleanup_expired()
        return {'expired_removed': expired_removed}
    
    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platforms.
        
        Returns:
            List of supported platforms
        """
        return self.universal_manager.get_supported_platforms()
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported repository types.
        
        Returns:
            List of supported repository types
        """
        return self.universal_manager.get_supported_types()
    
    async def reload_configurations(self) -> None:
        """Reload repository configurations and reinitialize."""
        await self.universal_manager.reload_configurations()
    
    async def add_repository_config(self, config: Dict[str, Any]) -> bool:
        """Add a new repository configuration at runtime.
        
        Args:
            config: Repository configuration dictionary
            
        Returns:
            True if repository was added successfully
        """
        return await self.universal_manager.add_repository_config(config)
    
    async def remove_repository(self, repository_name: str) -> bool:
        """Remove a repository.
        
        Args:
            repository_name: Name of the repository to remove
            
        Returns:
            True if repository was removed successfully
        """
        return await self.universal_manager.remove_repository(repository_name)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.universal_manager.__aexit__(exc_type, exc_val, exc_tb)
    
    async def close(self):
        """Explicitly close all connections."""
        await self.universal_manager.close()


# Alias for backward compatibility
EnhancedRepositoryManager = RepositoryManager