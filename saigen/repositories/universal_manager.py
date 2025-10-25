"""Universal repository manager with YAML-driven configuration."""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from saigen.models.repository import RepositoryInfo, RepositoryPackage, SearchResult
from saigen.repositories.cache import CacheManager, RepositoryCache
from saigen.repositories.codename_resolver import resolve_codename, resolve_repository_name
from saigen.repositories.downloaders.universal import UniversalRepositoryDownloader
from saigen.repositories.downloaders.api_downloader import APIRepositoryDownloader
from saigen.repositories.parsers import ParserRegistry
from saigen.utils.errors import ConfigurationError, RepositoryError

logger = logging.getLogger(__name__)


class UniversalRepositoryManager:
    """Universal repository manager supporting all package managers via YAML configuration."""

    def __init__(self, cache_dir: Union[str, Path], config_dirs: List[Union[str, Path]]):
        """Initialize universal repository manager.

        Args:
            cache_dir: Directory for caching repository data
            config_dirs: List of directories containing repository configurations
        """
        self.cache_dir = Path(cache_dir)
        self.config_dirs = [Path(d) for d in config_dirs]

        # Initialize components
        self.cache = RepositoryCache(self.cache_dir)
        self.cache_manager = CacheManager(self.cache)
        self.parser_registry = ParserRegistry()

        # Repository configurations and downloaders
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._downloaders: Dict[str, UniversalRepositoryDownloader] = {}
        self._initialized = False

        # Statistics
        self._stats = {
            "total_repositories": 0,
            "enabled_repositories": 0,
            "supported_platforms": set(),
            "supported_types": set(),
            "last_loaded": None,
        }

    async def initialize(self) -> None:
        """Initialize the repository manager."""
        if self._initialized:
            return

        logger.info("Initializing Universal Repository Manager")

        # Load repository configurations
        await self._load_all_configurations()

        # Initialize downloaders for enabled repositories
        await self._initialize_downloaders()

        # Update statistics
        self._update_statistics()

        self._initialized = True
        logger.info(
            f"Universal Repository Manager initialized with {len(self._downloaders)} repositories"
        )

    async def _load_all_configurations(self) -> None:
        """Load repository configurations from all config directories."""
        self._configs.clear()

        for config_dir in self.config_dirs:
            if not config_dir.exists():
                logger.warning(f"Configuration directory not found: {config_dir}")
                continue

            # Load all YAML files in the directory
            for config_file in config_dir.glob("*.yaml"):
                try:
                    await self._load_config_file(config_file)
                except Exception as e:
                    logger.error(f"Failed to load config {config_file}: {e}")

            # Also check for .yml extension
            for config_file in config_dir.glob("*.yml"):
                try:
                    await self._load_config_file(config_file)
                except Exception as e:
                    logger.error(f"Failed to load config {config_file}: {e}")

        logger.info(f"Loaded {len(self._configs)} repository configurations")

    async def _load_config_file(self, config_file: Path) -> None:
        """Load a single configuration file."""
        logger.debug(f"Loading configuration from: {config_file}")

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict) or "repositories" not in data:
            raise ConfigurationError(f"Invalid config format in {config_file}")

        # Validate schema version
        version = data.get("version", "1.0")
        if version != "1.0":
            logger.warning(f"Unsupported config version {version} in {config_file}")

        # Load repositories
        for repo_config in data["repositories"]:
            try:
                repo_name = repo_config["name"]

                # Validate required fields
                self._validate_repository_config(repo_config, config_file)

                # Store configuration
                self._configs[repo_name] = repo_config
                logger.debug(f"Loaded repository config: {repo_name}")

            except Exception as e:
                logger.error(f"Failed to load repository config in {config_file}: {e}")

    def _validate_repository_config(self, config: Dict[str, Any], source_file: Path) -> None:
        """Validate repository configuration."""
        required_fields = ["name", "type", "platform", "endpoints", "parsing"]

        for field in required_fields:
            if field not in config:
                raise ConfigurationError(f"Missing required field '{field}' in {source_file}")

        # Validate endpoints
        endpoints = config["endpoints"]
        if not isinstance(endpoints, dict) or "packages" not in endpoints:
            raise ConfigurationError(f"Invalid endpoints configuration in {source_file}")

        # Validate parsing configuration
        parsing = config["parsing"]
        if not isinstance(parsing, dict) or "format" not in parsing:
            raise ConfigurationError(f"Invalid parsing configuration in {source_file}")

        # Security: Validate URLs
        for endpoint_name, url in endpoints.items():
            if url and isinstance(url, str):
                if not url.startswith(("http://", "https://")):
                    raise ConfigurationError(f"Invalid URL scheme in {endpoint_name}: {url}")
        
        # Validate version_mapping if present
        if "version_mapping" in config:
            self._validate_version_mapping(config["version_mapping"], config["name"], source_file)
        
        # Validate eol if present
        if "eol" in config and not isinstance(config["eol"], bool):
            raise ConfigurationError(
                f"Repository {config['name']}: 'eol' field must be a boolean in {source_file}"
            )
        
        # Validate query_type if present
        if "query_type" in config:
            query_type = config["query_type"]
            if query_type not in ["bulk_download", "api"]:
                raise ConfigurationError(
                    f"Repository {config['name']}: 'query_type' must be 'bulk_download' or 'api' in {source_file}"
                )
    
    def _validate_version_mapping(
        self, version_mapping: Any, repo_name: str, source_file: Path
    ) -> None:
        """Validate version_mapping field structure.
        
        Args:
            version_mapping: The version_mapping value to validate
            repo_name: Repository name for error messages
            source_file: Source file path for error messages
        """
        if not isinstance(version_mapping, dict):
            raise ConfigurationError(
                f"Repository {repo_name}: version_mapping must be a dictionary in {source_file}"
            )
        
        for version, codename in version_mapping.items():
            if not isinstance(version, str) or not isinstance(codename, str):
                raise ConfigurationError(
                    f"Repository {repo_name}: version_mapping entries must be string:string, "
                    f"got {version}:{codename} in {source_file}"
                )
            
            # Validate version format (must be numeric with optional dots)
            if not re.match(r'^[0-9.]+$', version):
                raise ConfigurationError(
                    f"Repository {repo_name}: version_mapping key '{version}' "
                    f"must match pattern ^[0-9.]+$ in {source_file}"
                )
            
            # Validate codename format (lowercase alphanumeric with hyphens)
            if not re.match(r'^[a-z0-9-]+$', codename):
                raise ConfigurationError(
                    f"Repository {repo_name}: version_mapping value '{codename}' "
                    f"must match pattern ^[a-z0-9-]+$ in {source_file}"
                )

    async def _initialize_downloaders(self) -> None:
        """Initialize downloaders for all enabled repositories."""
        enabled_configs = [
            config
            for config in self._configs.values()
            if config.get("metadata", {}).get("enabled", True)
        ]

        for config in enabled_configs:
            try:
                downloader = await self._create_downloader(config)
                if downloader:
                    self._downloaders[config["name"]] = downloader
                    logger.debug(f"Initialized downloader for {config['name']}")
            except Exception as e:
                logger.warning(f"Failed to initialize downloader for {config['name']}: {e}")

    async def _create_downloader(
        self, config: Dict[str, Any]
    ) -> Optional[UniversalRepositoryDownloader]:
        """Create a downloader instance for a repository configuration."""
        try:
            # Convert config to repository info
            repo_info = self._config_to_repository_info(config)

            # Create appropriate downloader based on query_type
            query_type = config.get("query_type", "bulk_download")
            if query_type == "api":
                downloader = APIRepositoryDownloader(
                    repository_info=repo_info, config=config, parser_registry=self.parser_registry
                )
            else:
                downloader = UniversalRepositoryDownloader(
                    repository_info=repo_info, config=config, parser_registry=self.parser_registry
                )

            # Test availability if configured (with timeout)
            metadata = config.get("metadata", {})
            # Default to False for test_availability to prevent connection issues
            # during initialization
            if metadata.get("test_availability", False):
                try:
                    # Use asyncio.wait_for to add a timeout to availability check
                    is_available = await asyncio.wait_for(
                        downloader.is_available(),
                        timeout=5.0,  # 5 second timeout for availability check
                    )
                    if not is_available:
                        logger.warning(f"Repository {config['name']} is not available")
                        return None
                except asyncio.TimeoutError:
                    logger.warning(f"Repository {config['name']} availability check timed out")
                    return None
                except Exception as e:
                    logger.warning(f"Repository {config['name']} availability check failed: {e}")
                    return None

            return downloader

        except Exception as e:
            logger.error(f"Failed to create downloader for {config['name']}: {e}")
            return None

    def _config_to_repository_info(self, config: Dict[str, Any]) -> RepositoryInfo:
        """Convert configuration dictionary to RepositoryInfo."""
        metadata = config.get("metadata", {})

        return RepositoryInfo(
            name=config["name"],
            url=config["endpoints"]["packages"],
            type=config["type"],
            platform=config["platform"],
            architecture=config.get("architecture"),
            enabled=metadata.get("enabled", True),
            priority=metadata.get("priority", 50),
            description=metadata.get("description"),
            maintainer=metadata.get("maintainer"),
            version_mapping=config.get("version_mapping"),
            eol=config.get("eol", False),
            query_type=config.get("query_type", "bulk_download"),
        )

    def _update_statistics(self) -> None:
        """Update internal statistics."""
        self._stats["total_repositories"] = len(self._configs)
        self._stats["enabled_repositories"] = len(self._downloaders)
        self._stats["supported_platforms"] = set(
            config["platform"] for config in self._configs.values()
        )
        self._stats["supported_types"] = set(config["type"] for config in self._configs.values())
        self._stats["last_loaded"] = datetime.utcnow()

    async def get_packages(
        self, repository_name: str, use_cache: bool = True
    ) -> List[RepositoryPackage]:
        """Get packages from a specific repository."""
        if not self._initialized:
            await self.initialize()

        downloader = self._downloaders.get(repository_name)
        if not downloader:
            raise RepositoryError(f"Repository '{repository_name}' not found or not available")

        try:
            if use_cache:
                return await self.cache.get_or_fetch(downloader)
            else:
                return await downloader.download_package_list()
        except Exception as e:
            raise RepositoryError(f"Failed to get packages from {repository_name}: {str(e)}")

    async def get_all_packages(
        self,
        platform: Optional[str] = None,
        repository_type: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, List[RepositoryPackage]]:
        """Get packages from all repositories with optional filtering.
        
        Note: API-based repositories are skipped as they don't support bulk downloads.
        Use query_package() or query_packages_batch() for API-based repositories.
        """
        if not self._initialized:
            await self.initialize()

        # Filter downloaders
        downloaders = self._filter_downloaders(platform, repository_type)

        results = {}

        # Fetch packages from all repositories concurrently
        tasks = []
        for name, downloader in downloaders.items():
            # Skip API-based repositories as they don't support bulk downloads
            if isinstance(downloader, APIRepositoryDownloader):
                logger.debug(f"Skipping API-based repository {name} (use query_package instead)")
                continue
            
            if use_cache:
                task = asyncio.create_task(
                    self.cache.get_or_fetch(downloader), name=f"fetch_{name}"
                )
            else:
                task = asyncio.create_task(
                    downloader.download_package_list(), name=f"download_{name}"
                )
            tasks.append((name, task))

        # Collect results
        for name, task in tasks:
            try:
                packages = await task
                results[name] = packages
                logger.debug(f"Retrieved {len(packages)} packages from {name}")
            except Exception as e:
                logger.error(f"Failed to get packages from {name}: {e}")
                results[name] = []

        return results

    def _filter_downloaders(
        self, platform: Optional[str] = None, repository_type: Optional[str] = None
    ) -> Dict[str, UniversalRepositoryDownloader]:
        """Filter downloaders based on criteria."""
        filtered = {}

        for name, downloader in self._downloaders.items():
            repo_info = downloader.repository_info

            # Filter by platform
            if platform and repo_info.platform != platform and repo_info.platform != "universal":
                continue

            # Filter by repository type
            if repository_type and repo_info.type != repository_type:
                continue

            filtered[name] = downloader

        return filtered

    async def search_packages(
        self,
        query: str,
        platform: Optional[str] = None,
        repository_type: Optional[str] = None,
        repository_names: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> SearchResult:
        """Search for packages across repositories."""
        if not self._initialized:
            await self.initialize()

        start_time = datetime.utcnow()

        # Determine which repositories to search
        if repository_names:
            downloaders = {
                name: self._downloaders[name]
                for name in repository_names
                if name in self._downloaders
            }
        else:
            downloaders = self._filter_downloaders(platform, repository_type)

        all_packages = []
        repository_sources = []

        # Search in all repositories concurrently
        tasks = []
        for name, downloader in downloaders.items():
            task = asyncio.create_task(downloader.search_package(query), name=f"search_{name}")
            tasks.append((name, task))

        # Collect search results
        for name, task in tasks:
            try:
                packages = await task
                if packages:
                    # Apply limit per repository if specified
                    if limit:
                        packages = packages[:limit]

                    all_packages.extend(packages)
                    repository_sources.append(name)
                    logger.debug(f"Found {len(packages)} matches in {name}")
            except Exception as e:
                logger.error(f"Search failed in {name}: {e}")

        # Apply global limit if specified
        if limit and len(all_packages) > limit:
            all_packages = all_packages[:limit]

        # Calculate search time
        search_time = (datetime.utcnow() - start_time).total_seconds()

        return SearchResult(
            query=query,
            packages=all_packages,
            total_results=len(all_packages),
            search_time=search_time,
            repository_sources=repository_sources,
        )

    async def get_package_details(
        self,
        package_name: str,
        version: Optional[str] = None,
        platform: Optional[str] = None,
        repository_type: Optional[str] = None,
    ) -> Optional[RepositoryPackage]:
        """Get detailed information for a specific package."""
        if not self._initialized:
            await self.initialize()

        # Filter downloaders
        downloaders = self._filter_downloaders(platform, repository_type)

        # Search in repositories by priority order
        sorted_downloaders = sorted(
            downloaders.items(), key=lambda x: x[1].repository_info.priority, reverse=True
        )

        for name, downloader in sorted_downloaders:
            try:
                package = await downloader.get_package_details(package_name, version)
                if package:
                    return package
            except Exception as e:
                logger.debug(f"Failed to get package details from {name}: {e}")

        return None
    
    async def query_package_from_repository(
        self,
        repository_name: str,
        package_name: str,
        use_cache: bool = True
    ) -> Optional[RepositoryPackage]:
        """Query a specific package from a specific repository.
        
        This is optimized for API-based repositories where querying individual
        packages is more efficient than downloading the full package list.
        
        Args:
            repository_name: Name of the repository to query
            package_name: Name of the package to query
            use_cache: Whether to use cached response
            
        Returns:
            RepositoryPackage if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        downloader = self._downloaders.get(repository_name)
        if not downloader:
            raise RepositoryError(f"Repository '{repository_name}' not found or not available")
        
        try:
            # Check if this is an API-based downloader
            if isinstance(downloader, APIRepositoryDownloader):
                return await downloader.query_package(package_name, use_cache=use_cache)
            else:
                # Fall back to get_package_details for bulk download repos
                return await downloader.get_package_details(package_name)
        except Exception as e:
            logger.error(f"Failed to query package {package_name} from {repository_name}: {e}")
            return None
    
    async def query_packages_batch(
        self,
        repository_name: str,
        package_names: List[str],
        use_cache: bool = True
    ) -> Dict[str, Optional[RepositoryPackage]]:
        """Query multiple packages from a specific repository.
        
        This is optimized for API-based repositories where querying individual
        packages concurrently is more efficient than downloading the full package list.
        
        Args:
            repository_name: Name of the repository to query
            package_names: List of package names to query
            use_cache: Whether to use cached responses
            
        Returns:
            Dict mapping package names to RepositoryPackage (or None if not found)
        """
        if not self._initialized:
            await self.initialize()
        
        downloader = self._downloaders.get(repository_name)
        if not downloader:
            raise RepositoryError(f"Repository '{repository_name}' not found or not available")
        
        try:
            # Check if this is an API-based downloader
            if isinstance(downloader, APIRepositoryDownloader):
                return await downloader.query_packages_batch(package_names, use_cache=use_cache)
            else:
                # Fall back to sequential queries for bulk download repos
                results = {}
                for package_name in package_names:
                    try:
                        package = await downloader.get_package_details(package_name)
                        results[package_name] = package
                    except Exception as e:
                        logger.debug(f"Failed to query package {package_name}: {e}")
                        results[package_name] = None
                return results
        except Exception as e:
            logger.error(f"Failed to query packages from {repository_name}: {e}")
            return {name: None for name in package_names}

    async def update_cache(
        self, repository_names: Optional[List[str]] = None, force: bool = False
    ) -> Dict[str, bool]:
        """Update repository cache."""
        if not self._initialized:
            await self.initialize()

        # Determine which repositories to update
        if repository_names:
            downloaders = [
                self._downloaders[name] for name in repository_names if name in self._downloaders
            ]
        else:
            downloaders = list(self._downloaders.values())

        return await self.cache_manager.update_all_repositories(downloaders, force)

    async def get_repository_statistics(self) -> Dict[str, Any]:
        """Get comprehensive repository statistics."""
        if not self._initialized:
            await self.initialize()

        stats = self._stats.copy()

        # Add cache statistics
        cache_stats = await self.cache.get_cache_stats()
        stats["cache"] = cache_stats

        # Add per-repository statistics
        repo_stats = {}
        for name, downloader in self._downloaders.items():
            try:
                # For API-based repositories, don't try to get full package list
                if isinstance(downloader, APIRepositoryDownloader):
                    repo_stats[name] = {
                        "query_type": "api",
                        "status": "API",
                        "last_updated": datetime.utcnow(),
                        "repository_type": downloader.repository_info.type,
                        "platform": downloader.repository_info.platform,
                        "note": "API-based repository - use query_package() for individual lookups"
                    }
                else:
                    repo_metadata = await downloader.get_repository_metadata()
                    repo_stats[name] = repo_metadata
            except Exception as e:
                repo_stats[name] = {"error": str(e), "status": "Error", "last_updated": datetime.utcnow()}

        stats["repositories"] = repo_stats

        return stats

    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platforms."""
        return sorted(self._stats["supported_platforms"])

    def get_supported_types(self) -> List[str]:
        """Get list of supported repository types."""
        return sorted(self._stats["supported_types"])

    def get_repository_info(self, repository_name: str) -> Optional[RepositoryInfo]:
        """Get repository information."""
        downloader = self._downloaders.get(repository_name)
        return downloader.repository_info if downloader else None

    def get_all_repository_info(
        self, platform: Optional[str] = None, repository_type: Optional[str] = None
    ) -> List[RepositoryInfo]:
        """Get information for all repositories with optional filtering."""
        repositories = []

        for downloader in self._downloaders.values():
            repo_info = downloader.repository_info

            # Apply filters
            if platform and repo_info.platform != platform and repo_info.platform != "universal":
                continue

            if repository_type and repo_info.type != repository_type:
                continue

            repositories.append(repo_info)

        # Sort by priority
        return sorted(repositories, key=lambda r: r.priority, reverse=True)

    async def reload_configurations(self) -> None:
        """Reload repository configurations and reinitialize."""
        logger.info("Reloading repository configurations")

        # Clear existing state
        self._downloaders.clear()
        self._configs.clear()

        # Reload configurations
        await self._load_all_configurations()

        # Reinitialize downloaders
        await self._initialize_downloaders()

        # Update statistics
        self._update_statistics()

        logger.info(f"Reloaded configurations, {len(self._downloaders)} repositories available")

    async def add_repository_config(self, config: Dict[str, Any]) -> bool:
        """Add a new repository configuration at runtime."""
        try:
            # Validate configuration
            self._validate_repository_config(config, Path("runtime"))

            # Store configuration
            repo_name = config["name"]
            self._configs[repo_name] = config

            # Create and initialize downloader if enabled
            metadata = config.get("metadata", {})
            if metadata.get("enabled", True):
                downloader = await self._create_downloader(config)
                if downloader:
                    self._downloaders[repo_name] = downloader
                    logger.info(f"Added repository {repo_name}")
                    self._update_statistics()
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to add repository configuration: {e}")
            return False

    async def remove_repository(self, repository_name: str) -> bool:
        """Remove a repository."""
        if repository_name in self._downloaders:
            del self._downloaders[repository_name]

        if repository_name in self._configs:
            del self._configs[repository_name]

        # Clear cache
        await self.cache.invalidate_repository(repository_name)

        logger.info(f"Removed repository {repository_name}")
        self._update_statistics()
        return True

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Close any open connections in downloaders
        for downloader in self._downloaders.values():
            if hasattr(downloader, "__aexit__"):
                try:
                    await downloader.__aexit__(exc_type, exc_val, exc_tb)
                except Exception as e:
                    logger.debug(f"Error closing downloader: {e}")

    def resolve_codename_for_repository(
        self, repository_name: str, version: str
    ) -> Optional[str]:
        """Resolve OS version to codename for a specific repository.
        
        Args:
            repository_name: Name of the repository
            version: OS version (e.g., "22.04", "11", "39")
            
        Returns:
            Codename string or None if not found
            
        Example:
            >>> manager.resolve_codename_for_repository("apt-ubuntu-jammy", "22.04")
            'jammy'
        """
        repo_info = self.get_repository_info(repository_name)
        if not repo_info:
            logger.warning(f"Repository {repository_name} not found")
            return None
        
        return resolve_codename(repo_info, version)
    
    def resolve_repository_name_from_context(
        self, provider: str, os: Optional[str], version: Optional[str]
    ) -> str:
        """Resolve repository name from provider, OS, and version context.
        
        This method uses the codename resolver to find the appropriate repository
        name based on the OS context. It searches through all available repositories
        to find one that matches the provider type and has a version_mapping entry
        for the given OS version.
        
        Args:
            provider: Provider name (apt, dnf, brew, etc.)
            os: OS name (ubuntu, debian, etc.) or None
            version: OS version (e.g., "22.04", "11") or None
            
        Returns:
            Repository name (e.g., "apt-ubuntu-jammy") or provider name as fallback
            
        Example:
            >>> manager.resolve_repository_name_from_context("apt", "ubuntu", "22.04")
            'apt-ubuntu-jammy'
        """
        # Build a dict of all repository info for the resolver
        repositories = {
            name: downloader.repository_info
            for name, downloader in self._downloaders.items()
        }
        
        resolved_name = resolve_repository_name(provider, os, version, repositories)
        
        # Log if EOL repository is being used
        if resolved_name in self._downloaders:
            repo_info = self._downloaders[resolved_name].repository_info
            if repo_info.eol:
                logger.info(
                    f"Using EOL (end-of-life) repository: {resolved_name} "
                    f"for {os} {version}"
                )
        
        return resolved_name
    
    def has_repository(self, repository_name: str) -> bool:
        """Check if a repository exists and is available.
        
        Args:
            repository_name: Name of the repository to check
            
        Returns:
            True if repository exists and is available, False otherwise
        """
        return repository_name in self._downloaders
    
    def get_version_mappings(
        self, provider: Optional[str] = None
    ) -> Dict[str, Dict[str, Dict[str, str]]]:
        """Get all version mappings from repositories.
        
        This is useful for debugging and displaying available OS versions.
        
        Args:
            provider: Optional provider filter (apt, dnf, etc.)
            
        Returns:
            Dict mapping repository names to their version_mapping dicts
            Format: {repo_name: {version: codename}}
            
        Example:
            >>> mappings = manager.get_version_mappings("apt")
            >>> print(mappings)
            {
                'apt-ubuntu-jammy': {'22.04': 'jammy'},
                'apt-ubuntu-focal': {'20.04': 'focal'},
                'apt-debian-bookworm': {'12': 'bookworm'}
            }
        """
        mappings = {}
        
        for name, downloader in self._downloaders.items():
            repo_info = downloader.repository_info
            
            # Filter by provider if specified
            if provider and repo_info.type != provider:
                continue
            
            # Only include repositories with version_mapping
            if repo_info.version_mapping:
                mappings[name] = repo_info.version_mapping
        
        return mappings

    async def close(self):
        """Explicitly close all connections."""
        await self.__aexit__(None, None, None)
