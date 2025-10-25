"""Codename resolution utilities for OS version to codename mapping."""

import logging
from typing import Dict, Optional

from saigen.models.repository import RepositoryInfo

logger = logging.getLogger(__name__)


def resolve_codename(repository_info: RepositoryInfo, version: str) -> Optional[str]:
    """Resolve OS version to codename from repository's version_mapping.
    
    Args:
        repository_info: Repository configuration with version_mapping
        version: OS version (e.g., "22.04", "11", "39")
        
    Returns:
        Codename string (e.g., "jammy", "bullseye", "f39") or None if not found
        
    Examples:
        >>> repo = RepositoryInfo(name="apt-ubuntu-jammy", version_mapping={"22.04": "jammy"}, ...)
        >>> resolve_codename(repo, "22.04")
        'jammy'
        
        >>> resolve_codename(repo, "24.04")
        None
    """
    if not repository_info.version_mapping:
        logger.debug(
            f"Repository {repository_info.name} has no version_mapping"
        )
        return None
    
    codename = repository_info.version_mapping.get(version)
    
    if codename:
        logger.debug(
            f"Resolved version {version} to codename '{codename}' "
            f"for repository {repository_info.name}"
        )
    else:
        logger.debug(
            f"No codename mapping found for version {version} "
            f"in repository {repository_info.name}"
        )
    
    return codename


def resolve_repository_name(
    provider: str,
    os: Optional[str],
    version: Optional[str],
    repositories: Dict[str, RepositoryInfo]
) -> str:
    """Build repository name from provider, OS, and version.
    
    This function searches through available repositories to find one that:
    1. Matches the provider type
    2. Supports the given OS (via distribution field)
    3. Has a version_mapping entry for the given version
    
    Args:
        provider: Provider name (apt, dnf, brew, etc.)
        os: OS name (ubuntu, debian, etc.) or None
        version: OS version (e.g., "22.04", "11") or None
        repositories: Available repository configurations (dict of name -> RepositoryInfo)
        
    Returns:
        Repository name (e.g., "apt-ubuntu-jammy", "apt", "brew-macos")
        Falls back to provider name if no specific match found
        
    Logic:
        1. If os and version provided:
           - Iterate through all repositories
           - Find repos matching: type==provider
           - Check each repo's version_mapping for the given version
           - If found, extract codename and return "{provider}-{os}-{codename}"
        2. If only provider: return provider name
        3. If no match: return provider name (fallback)
        
    Examples:
        >>> repos = {
        ...     "apt-ubuntu-jammy": RepositoryInfo(
        ...         name="apt-ubuntu-jammy",
        ...         type="apt",
        ...         version_mapping={"22.04": "jammy"},
        ...         ...
        ...     )
        ... }
        >>> resolve_repository_name("apt", "ubuntu", "22.04", repos)
        'apt-ubuntu-jammy'
        
        >>> resolve_repository_name("apt", None, None, repos)
        'apt'
        
        >>> resolve_repository_name("apt", "ubuntu", "99.99", repos)
        'apt'
    """
    # If no OS or version provided, return provider name
    if not os or not version:
        logger.debug(
            f"No OS or version provided, using provider name: {provider}"
        )
        return provider
    
    # Search for matching repository
    for repo_name, repo_info in repositories.items():
        # Check if repository type matches provider
        if repo_info.type != provider:
            continue
        
        # Check if repository has version_mapping
        if not repo_info.version_mapping:
            continue
        
        # Check if version exists in version_mapping
        codename = repo_info.version_mapping.get(version)
        if not codename:
            continue
        
        # Verify the repository name follows expected pattern
        # Expected: {provider}-{os}-{codename}
        expected_name = f"{provider}-{os}-{codename}"
        if repo_name == expected_name:
            logger.info(
                f"Resolved repository: {expected_name} "
                f"(provider={provider}, os={os}, version={version})"
            )
            return expected_name
        
        # Also accept if the repo name matches and contains the codename
        # This handles cases where naming might vary slightly
        if codename in repo_name and provider in repo_name:
            logger.info(
                f"Resolved repository: {repo_name} "
                f"(provider={provider}, os={os}, version={version}, codename={codename})"
            )
            return repo_name
    
    # No matching repository found, fall back to provider name
    logger.warning(
        f"No repository found for provider={provider}, os={os}, version={version}. "
        f"Falling back to provider name: {provider}"
    )
    return provider
