"""GitHub-specific parsers for repository data."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from saigen.models.repository import RepositoryInfo, RepositoryPackage
from saigen.utils.errors import RepositoryError

logger = logging.getLogger(__name__)


async def parse_github_directory(
    content: str, config: Dict[str, Any], repository_info: RepositoryInfo
) -> List[RepositoryPackage]:
    """Parse GitHub API directory listing to extract package names.

    GitHub API returns a list of files in a directory. For package repositories
    like Scoop and winget, each file represents a package manifest.

    Example response:
    [
      {
        "name": "package-name.json",
        "path": "bucket/package-name.json",
        "download_url": "https://raw.githubusercontent.com/.../package-name.json",
        "type": "file"
      }
    ]
    """
    import json

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise RepositoryError(f"Invalid JSON format: {str(e)}")

    if not isinstance(data, list):
        raise RepositoryError(f"Expected list of files, got {type(data)}")

    packages = []
    config.get("fields", {})

    # Get file extension to remove (default: .json)
    file_extension = config.get("patterns", {}).get("file_extension", ".json")

    for item in data:
        if not isinstance(item, dict):
            continue

        # Only process files, not directories
        if item.get("type") != "file":
            continue

        filename = item.get("name", "")
        if not filename:
            continue

        # Extract package name from filename
        package_name = filename
        if package_name.endswith(file_extension):
            package_name = package_name[: -len(file_extension)]

        # Skip helper files or special files
        if package_name.startswith(".") or package_name.startswith("_"):
            continue

        # Create package entry
        package = RepositoryPackage(
            name=package_name,
            version="unknown",  # Would need to fetch individual file for version
            description=None,
            download_url=item.get("download_url"),
            repository_name=repository_info.name,
            platform=repository_info.platform,
            last_updated=datetime.utcnow(),
        )
        packages.append(package)

    logger.debug(f"Extracted {len(packages)} packages from GitHub directory listing")
    return packages


async def parse_github_directory_with_details(
    content: str,
    config: Dict[str, Any],
    repository_info: RepositoryInfo,
    fetch_details: bool = False,
) -> List[RepositoryPackage]:
    """Parse GitHub directory and optionally fetch individual package details.

    This is a more advanced version that can fetch individual package manifests
    to get complete package information. Use with caution due to API rate limits.
    """
    # First get the basic package list
    packages = await parse_github_directory(content, config, repository_info)

    if not fetch_details:
        return packages

    # TODO: Implement fetching individual package details
    # This would require:
    # 1. Making additional HTTP requests for each package
    # 2. Parsing the individual manifest files
    # 3. Respecting GitHub API rate limits
    # 4. Implementing proper error handling and retries

    logger.warning("Fetching individual package details not yet implemented")
    return packages
