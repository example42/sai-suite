"""ETL (Extract, Transform, Load) for converting repository data to saidata."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from saigen.models.repository import RepositoryPackage
from saigen.models.saidata import (
    Metadata,
    Package,
    ProviderConfig,
    Repository,
    RepositoryType,
    SaiData,
    Urls,
)
from saigen.repositories.manager import RepositoryManager

logger = logging.getLogger(__name__)


class RepositoryToSaidataETL:
    """ETL pipeline for converting repository data to saidata format."""

    def __init__(self, repository_manager: RepositoryManager):
        """Initialize ETL with repository manager.

        Args:
            repository_manager: Repository manager instance
        """
        self.repository_manager = repository_manager

        # Provider mappings for different repository types
        self.provider_mappings = {
            "apt": {
                "install": "apt install {package_name}",
                "remove": "apt remove {package_name}",
                "update": "apt update",
                "search": "apt search {query}",
                "info": "apt show {package_name}",
            },
            "brew": {
                "install": "brew install {package_name}",
                "remove": "brew uninstall {package_name}",
                "update": "brew update && brew upgrade {package_name}",
                "search": "brew search {query}",
                "info": "brew info {package_name}",
            },
            "dnf": {
                "install": "dnf install {package_name}",
                "remove": "dnf remove {package_name}",
                "update": "dnf update {package_name}",
                "search": "dnf search {query}",
                "info": "dnf info {package_name}",
            },
        }

    async def extract_packages(
        self, software_name: str, platforms: Optional[List[str]] = None
    ) -> Dict[str, List[RepositoryPackage]]:
        """Extract packages for a software from repositories.

        Args:
            software_name: Name of the software to extract
            platforms: Platforms to search (optional)

        Returns:
            Dictionary mapping repository names to matching packages
        """
        logger.info(f"Extracting packages for software: {software_name}")

        # Search across repositories
        search_result = await self.repository_manager.search_packages(
            query=software_name, platform=None  # Search all platforms initially
        )

        # Group packages by repository
        packages_by_repo = {}
        for package in search_result.packages:
            repo_name = package.repository_name
            if repo_name not in packages_by_repo:
                packages_by_repo[repo_name] = []
            packages_by_repo[repo_name].append(package)

        # Filter by platforms if specified
        if platforms:
            filtered_packages = {}
            for repo_name, packages in packages_by_repo.items():
                filtered = [pkg for pkg in packages if pkg.platform in platforms]
                if filtered:
                    filtered_packages[repo_name] = filtered
            packages_by_repo = filtered_packages

        logger.debug(f"Found packages in {len(packages_by_repo)} repositories")
        return packages_by_repo

    def transform_packages_to_saidata(
        self,
        software_name: str,
        packages_by_repo: Dict[str, List[RepositoryPackage]],
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> SaiData:
        """Transform repository packages into saidata format.

        Args:
            software_name: Name of the software
            packages_by_repo: Packages grouped by repository
            additional_metadata: Additional metadata to include

        Returns:
            SaiData object
        """
        logger.info(f"Transforming packages to saidata for: {software_name}")

        # Determine the best package name and metadata
        primary_package = self._select_primary_package(packages_by_repo)

        # Build metadata
        metadata_dict = self._build_metadata_dict(
            primary_package, packages_by_repo, additional_metadata
        )

        # Create metadata object
        metadata = Metadata(
            name=software_name,
            display_name=metadata_dict.get("display_name"),
            description=metadata_dict.get("description"),
            version=metadata_dict.get("version"),
            category=metadata_dict.get("category"),
            tags=metadata_dict.get("tags"),
            license=metadata_dict.get("license"),
            maintainer=metadata_dict.get("maintainer"),
            urls=self._build_urls(primary_package) if primary_package else None,
        )

        # Build providers dictionary
        providers = {}
        for repo_name, packages in packages_by_repo.items():
            repo_info = self.repository_manager.get_repository_info(repo_name)
            if not repo_info:
                continue

            provider_config = self._create_provider_config_from_packages(repo_info.type, packages)
            if provider_config:
                providers[repo_info.type] = provider_config

        # Create SaiData object
        saidata = SaiData(
            version="0.2", metadata=metadata, providers=providers if providers else None
        )

        logger.debug(f"Created saidata with {len(providers)} providers")
        return saidata

    def _select_primary_package(
        self, packages_by_repo: Dict[str, List[RepositoryPackage]]
    ) -> Optional[RepositoryPackage]:
        """Select the primary package to use for metadata.

        Args:
            packages_by_repo: Packages grouped by repository

        Returns:
            Primary package or None
        """
        # Priority order for repository types
        repo_priority = ["brew", "apt", "dnf", "generic"]

        # Find the best package based on repository priority
        for repo_type in repo_priority:
            for repo_name, packages in packages_by_repo.items():
                repo_info = self.repository_manager.get_repository_info(repo_name)
                if repo_info and repo_info.type == repo_type and packages:
                    # Return the first package from highest priority repo
                    return packages[0]

        # Fall back to any package
        for packages in packages_by_repo.values():
            if packages:
                return packages[0]

        return None

    def _create_provider_config_from_packages(
        self, repo_type: str, packages: List[RepositoryPackage]
    ) -> Optional[ProviderConfig]:
        """Create a provider config from repository packages.

        Args:
            repo_type: Repository type (apt, brew, dnf, etc.)
            packages: List of packages from the repository

        Returns:
            ProviderConfig object or None
        """
        if not packages:
            return None

        # Create packages list
        sai_packages = []
        for pkg in packages:
            sai_package = Package(name=pkg.name, version=pkg.version, download_url=pkg.download_url)
            sai_packages.append(sai_package)

        # Create repository info
        primary_package = packages[0]
        repository = Repository(
            name=primary_package.repository_name,
            type=RepositoryType.OS_DEFAULT,  # Default type
            maintainer=primary_package.maintainer,
            packages=sai_packages,
        )

        # Create provider config
        provider_config = ProviderConfig(repositories=[repository], packages=sai_packages)

        return provider_config

    def _build_metadata_dict(
        self,
        primary_package: Optional[RepositoryPackage],
        packages_by_repo: Dict[str, List[RepositoryPackage]],
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build metadata dictionary from packages.

        Args:
            primary_package: Primary package for metadata
            packages_by_repo: All packages grouped by repository
            additional_metadata: Additional metadata to include

        Returns:
            Metadata dictionary
        """
        metadata = {}

        if primary_package:
            metadata.update(
                {
                    "description": primary_package.description,
                    "version": primary_package.version,
                    "license": primary_package.license,
                    "maintainer": primary_package.maintainer,
                    "tags": primary_package.tags,
                    "category": primary_package.category,
                }
            )

        # Merge additional metadata
        if additional_metadata:
            metadata.update(additional_metadata)

        # Clean up None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return metadata

    def _build_urls(self, package: RepositoryPackage) -> Optional[Urls]:
        """Build URLs object from package information.

        Args:
            package: Repository package

        Returns:
            Urls object or None
        """
        if not package.homepage and not package.download_url:
            return None

        return Urls(website=package.homepage, download=package.download_url)

    async def load_saidata(self, saidata: SaiData, output_path: Path, format: str = "yaml") -> None:
        """Load (save) saidata to file.

        Args:
            saidata: SaiData object to save
            output_path: Path to save the file
            format: Output format ('yaml' or 'json')
        """
        logger.info(f"Saving saidata to: {output_path}")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dictionary
        data = saidata.model_dump(exclude_none=True)

        # Save in specified format
        if format.lower() == "json":
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        else:  # Default to YAML
            with open(output_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, indent=2, sort_keys=False)

        logger.info(f"Saidata saved successfully")

    async def process_software(
        self,
        software_name: str,
        output_path: Path,
        platforms: Optional[List[str]] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
        format: str = "yaml",
    ) -> SaiData:
        """Complete ETL process for a software.

        Args:
            software_name: Name of the software to process
            output_path: Path to save the saidata file
            platforms: Platforms to include (optional)
            additional_metadata: Additional metadata to include
            format: Output format ('yaml' or 'json')

        Returns:
            Generated SaiData object
        """
        logger.info(f"Starting ETL process for software: {software_name}")

        try:
            # Extract
            packages_by_repo = await self.extract_packages(software_name, platforms)

            if not packages_by_repo:
                raise ValueError(f"No packages found for software: {software_name}")

            # Transform
            saidata = self.transform_packages_to_saidata(
                software_name, packages_by_repo, additional_metadata
            )

            # Load
            await self.load_saidata(saidata, output_path, format)

            logger.info(f"ETL process completed successfully for: {software_name}")
            return saidata

        except Exception as e:
            logger.error(f"ETL process failed for {software_name}: {e}")
            raise

    async def batch_process(
        self,
        software_list: List[str],
        output_dir: Path,
        platforms: Optional[List[str]] = None,
        format: str = "yaml",
    ) -> Dict[str, bool]:
        """Process multiple software packages in batch.

        Args:
            software_list: List of software names to process
            output_dir: Directory to save saidata files
            platforms: Platforms to include (optional)
            format: Output format ('yaml' or 'json')

        Returns:
            Dictionary mapping software names to success status
        """
        logger.info(f"Starting batch ETL process for {len(software_list)} software packages")

        results = {}

        for software_name in software_list:
            try:
                # Create output path
                safe_name = software_name.replace("/", "_").replace(" ", "_")
                output_path = output_dir / f"{safe_name}.{format}"

                # Process software
                await self.process_software(
                    software_name=software_name,
                    output_path=output_path,
                    platforms=platforms,
                    format=format,
                )

                results[software_name] = True
                logger.info(f"✓ Processed: {software_name}")

            except Exception as e:
                results[software_name] = False
                logger.error(f"✗ Failed to process {software_name}: {e}")

        success_count = sum(1 for success in results.values() if success)
        logger.info(f"Batch ETL completed: {success_count}/{len(software_list)} successful")

        return results
