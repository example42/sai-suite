"""Repository integration for saitest.

This module provides functionality to query saigen's repository cache
and cross-reference with available providerdata to discover valid
installation providers for software packages.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from saigen.repositories import RepositoryManager
from saigen.models.repository import RepositoryPackage

from saitest.utils.provider_executor import ProviderCommandExecutor


logger = logging.getLogger(__name__)


class RepositoryIntegrationError(Exception):
    """Exception raised when repository integration fails."""
    pass


class RepositoryIntegration:
    """Integration with saigen's repository system.
    
    This class provides methods to query repository data and cross-reference
    with available providerdata to discover valid installation providers.
    
    Attributes:
        repository_manager: Saigen's repository manager for querying package data
        provider_executor: Provider command executor for checking providerdata availability
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        providers_dir: Optional[Path] = None
    ):
        """Initialize repository integration.
        
        Args:
            cache_dir: Directory for repository cache (default: ~/.sai/cache/repositories)
            providers_dir: Directory containing providerdata files (default: providers/)
        """
        self._logger = logging.getLogger(__name__)
        
        # Initialize repository manager
        if cache_dir is None:
            # Use default saigen cache location
            cache_dir = Path.home() / ".sai" / "cache" / "repositories"
        
        self.repository_manager = RepositoryManager(cache_dir=cache_dir)
        
        # Initialize provider executor to check providerdata availability
        self.provider_executor = ProviderCommandExecutor(providers_dir=providers_dir)
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the repository integration.
        
        This must be called before using any query methods.
        """
        if not self._initialized:
            await self.repository_manager.initialize()
            self._initialized = True
            self._logger.info("Repository integration initialized")
    
    def get_available_providers(self) -> List[str]:
        """Get list of providers that have valid providerdata.
        
        This scans the providers/ directory and returns all providers
        that have valid providerdata definitions.
        
        Returns:
            List of provider names with valid providerdata
        """
        return self.provider_executor.get_available_providers()
    
    async def query_repositories_for_package(
        self,
        package_name: str,
        platform: Optional[str] = None
    ) -> Dict[str, List[RepositoryPackage]]:
        """Query all repositories for a specific package.
        
        Args:
            package_name: Name of the package to search for
            platform: Optional platform filter (e.g., "linux", "macos")
        
        Returns:
            Dictionary mapping provider names to lists of matching packages
            
        Raises:
            RepositoryIntegrationError: If query fails
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Search across all repositories
            search_result = await self.repository_manager.search_packages(
                query=package_name,
                platform=platform,
                limit=None  # Get all results
            )
            
            # Group results by repository (which maps to provider)
            results_by_provider: Dict[str, List[RepositoryPackage]] = {}
            
            for package in search_result.packages:
                # Repository name typically maps to provider name
                # (e.g., "apt" repository -> "apt" provider)
                provider_name = package.repository_name
                
                if provider_name not in results_by_provider:
                    results_by_provider[provider_name] = []
                
                results_by_provider[provider_name].append(package)
            
            self._logger.info(
                f"Found package '{package_name}' in {len(results_by_provider)} repositories"
            )
            
            return results_by_provider
            
        except Exception as e:
            self._logger.error(f"Error querying repositories for '{package_name}': {e}")
            raise RepositoryIntegrationError(
                f"Failed to query repositories for package '{package_name}': {e}"
            ) from e
    
    async def discover_providers_for_package(
        self,
        package_name: str,
        platform: Optional[str] = None
    ) -> Tuple[List[str], Dict[str, str]]:
        """Discover valid providers for a package.
        
        This method queries repositories for the package and cross-references
        with available providerdata to find providers that have both:
        1. Package data in repositories
        2. Valid providerdata definitions
        
        Args:
            package_name: Name of the package to search for
            platform: Optional platform filter
        
        Returns:
            Tuple of (valid_providers, package_versions) where:
            - valid_providers: List of provider names that can install this package
            - package_versions: Dict mapping provider names to package versions
            
        Raises:
            RepositoryIntegrationError: If discovery fails
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get available providerdata
            available_providers = set(self.get_available_providers())
            
            if not available_providers:
                self._logger.warning("No providers with valid providerdata found")
                return [], {}
            
            # Query repositories for package
            repo_results = await self.query_repositories_for_package(
                package_name,
                platform
            )
            
            # Cross-reference: only include providers that have both
            # repository data AND providerdata
            valid_providers: List[str] = []
            package_versions: Dict[str, str] = {}
            
            for provider_name, packages in repo_results.items():
                if provider_name in available_providers:
                    valid_providers.append(provider_name)
                    
                    # Get the latest version from packages
                    if packages:
                        # Use the first package's version (typically the latest)
                        package_versions[provider_name] = packages[0].version or "unknown"
                    
                    self._logger.debug(
                        f"Provider '{provider_name}' is valid: has both repository data and providerdata"
                    )
                else:
                    self._logger.debug(
                        f"Provider '{provider_name}' skipped: no providerdata found"
                    )
            
            if valid_providers:
                self._logger.info(
                    f"Discovered {len(valid_providers)} valid providers for '{package_name}': "
                    f"{', '.join(valid_providers)}"
                )
            else:
                self._logger.warning(
                    f"No valid providers found for '{package_name}'. "
                    f"Repository results: {list(repo_results.keys())}, "
                    f"Available providerdata: {list(available_providers)}"
                )
            
            return valid_providers, package_versions
            
        except Exception as e:
            self._logger.error(f"Error discovering providers for '{package_name}': {e}")
            raise RepositoryIntegrationError(
                f"Failed to discover providers for package '{package_name}': {e}"
            ) from e
    
    async def get_package_details(
        self,
        package_name: str,
        provider_name: str,
        version: Optional[str] = None
    ) -> Optional[RepositoryPackage]:
        """Get detailed package information from a specific provider's repository.
        
        Args:
            package_name: Name of the package
            provider_name: Provider/repository name
            version: Optional specific version
        
        Returns:
            Package details or None if not found
            
        Raises:
            RepositoryIntegrationError: If query fails
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Query repository manager for package details
            package = await self.repository_manager.get_package_details(
                package_name=package_name,
                version=version,
                repository_type=provider_name
            )
            
            if package:
                self._logger.debug(
                    f"Found package details for '{package_name}' in '{provider_name}'"
                )
            else:
                self._logger.debug(
                    f"Package '{package_name}' not found in '{provider_name}'"
                )
            
            return package
            
        except Exception as e:
            self._logger.error(
                f"Error getting package details for '{package_name}' from '{provider_name}': {e}"
            )
            raise RepositoryIntegrationError(
                f"Failed to get package details for '{package_name}' from '{provider_name}': {e}"
            ) from e
    
    async def get_all_packages_for_provider(
        self,
        provider_name: str,
        use_cache: bool = True
    ) -> List[RepositoryPackage]:
        """Get all packages from a specific provider's repository.
        
        Args:
            provider_name: Provider/repository name
            use_cache: Whether to use cached data
        
        Returns:
            List of all packages from the provider's repository
            
        Raises:
            RepositoryIntegrationError: If query fails
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            packages = await self.repository_manager.get_packages(
                repository_name=provider_name,
                use_cache=use_cache
            )
            
            self._logger.info(
                f"Retrieved {len(packages)} packages from '{provider_name}' repository"
            )
            
            return packages
            
        except Exception as e:
            self._logger.error(
                f"Error getting packages from '{provider_name}': {e}"
            )
            raise RepositoryIntegrationError(
                f"Failed to get packages from '{provider_name}': {e}"
            ) from e
    
    def validate_provider_has_both_data_and_providerdata(
        self,
        provider_name: str,
        has_repository_data: bool
    ) -> bool:
        """Validate that a provider has both repository data and providerdata.
        
        Args:
            provider_name: Name of the provider to validate
            has_repository_data: Whether repository data exists for this provider
        
        Returns:
            True if provider has both repository data and providerdata
        """
        has_providerdata = self.provider_executor.has_provider(provider_name)
        
        is_valid = has_repository_data and has_providerdata
        
        if not is_valid:
            if not has_repository_data:
                self._logger.debug(
                    f"Provider '{provider_name}' missing repository data"
                )
            if not has_providerdata:
                self._logger.debug(
                    f"Provider '{provider_name}' missing providerdata"
                )
        
        return is_valid
    
    async def close(self) -> None:
        """Close repository manager connections."""
        if self._initialized:
            await self.repository_manager.close()
            self._logger.info("Repository integration closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


async def get_available_providers_with_validation(
    cache_dir: Optional[Path] = None,
    providers_dir: Optional[Path] = None
) -> List[str]:
    """Get list of available providers that have valid providerdata.
    
    This is a convenience function that creates a RepositoryIntegration
    instance and returns the list of available providers.
    
    Args:
        cache_dir: Directory for repository cache
        providers_dir: Directory containing providerdata files
    
    Returns:
        List of provider names with valid providerdata
    """
    integration = RepositoryIntegration(
        cache_dir=cache_dir,
        providers_dir=providers_dir
    )
    
    # No need to initialize for this operation since it only checks providerdata
    return integration.get_available_providers()


async def discover_providers(
    package_name: str,
    platform: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    providers_dir: Optional[Path] = None
) -> Tuple[List[str], Dict[str, str]]:
    """Discover valid providers for a package.
    
    This is a convenience function that creates a RepositoryIntegration
    instance and discovers providers for the given package.
    
    Args:
        package_name: Name of the package to search for
        platform: Optional platform filter
        cache_dir: Directory for repository cache
        providers_dir: Directory containing providerdata files
    
    Returns:
        Tuple of (valid_providers, package_versions)
    """
    async with RepositoryIntegration(
        cache_dir=cache_dir,
        providers_dir=providers_dir
    ) as integration:
        return await integration.discover_providers_for_package(
            package_name,
            platform
        )
