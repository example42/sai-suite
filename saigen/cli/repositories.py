"""Repository management CLI commands."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import click
import yaml

from saigen.repositories.manager import RepositoryManager

# Try to import tabulate, fall back to simple formatting if not available
try:
    from tabulate import tabulate

    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

    def tabulate(data, headers=None, tablefmt="grid"):
        """Simple fallback table formatting."""
        if not data:
            return ""

        if headers:
            # Calculate column widths
            col_widths = [len(str(h)) for h in headers]
            for row in data:
                for i, cell in enumerate(row):
                    if i < len(col_widths):
                        col_widths[i] = max(col_widths[i], len(str(cell)))

            # Format table
            lines = []

            # Header
            header_line = " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
            lines.append(header_line)
            lines.append("-" * len(header_line))

            # Data rows
            for row in data:
                row_line = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
                lines.append(row_line)

            return "\n".join(lines)
        else:
            return "\n".join(" | ".join(str(cell) for cell in row) for row in data)


def get_repository_manager(
    cache_dir: Optional[str], config_dir: Optional[str]
) -> RepositoryManager:
    """Get configured repository manager."""
    cache_dir = cache_dir or "~/.saigen/cache"
    config_dir = config_dir or "~/.saigen/config"

    return RepositoryManager(
        cache_dir=Path(cache_dir).expanduser(), config_dir=Path(config_dir).expanduser()
    )


logger = logging.getLogger(__name__)


def _matches_os(repo, os_filter: str) -> bool:
    """Check if repository matches OS filter."""
    # Check if OS is in repository name (e.g., apt-ubuntu-jammy)
    if os_filter.lower() in repo.name.lower():
        return True
    
    # Check version_mapping if available
    if repo.version_mapping:
        # For repositories with version_mapping, check if any codename suggests this OS
        # This is a heuristic - repository names typically include OS
        return os_filter.lower() in repo.name.lower()
    
    return False


def _matches_version(repo, version_filter: str) -> bool:
    """Check if repository supports the specified version."""
    if not repo.version_mapping:
        return False
    
    # Check if version is in the version_mapping keys
    return version_filter in repo.version_mapping


def _format_os_versions(repo) -> str:
    """Format OS versions and codenames for display."""
    if not repo.version_mapping:
        return "N/A"
    
    # Format as "version (codename)"
    versions = []
    for version, codename in repo.version_mapping.items():
        versions.append(f"{version} ({codename})")
    
    result = ", ".join(versions)
    # Truncate if too long
    if len(result) > 30:
        return result[:27] + "..."
    return result


@click.group()
def repositories():
    """Manage 50+ package repositories across all platforms.

    SAIGEN supports universal repository management with 50+ package managers
    including apt, brew, npm, pypi, cargo, winget, and many more. Search packages,
    get statistics, and manage repository caches with concurrent operations.

    Examples:
      saigen repositories list-repos --platform linux
      saigen repositories search "redis" --limit 10
      saigen repositories info "nginx" --platform linux
      saigen repositories stats --format json
    """


@repositories.command()
@click.option("--platform", help="Filter by platform (linux, macos, windows, universal)")
@click.option(
    "--type", "repo_type", help="Filter by repository type (apt, brew, npm, pypi, cargo, etc.)"
)
@click.option("--os", help="Filter by OS (ubuntu, debian, fedora, etc.)")
@click.option("--version", help="Filter by OS version (22.04, 11, 39, etc.)")
@click.option("--eol", is_flag=True, help="Show only EOL (end-of-life) repositories")
@click.option("--active", is_flag=True, help="Show only active (non-EOL) repositories")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json", "yaml"]),
    help="Output format",
)
@click.option("--cache-dir", help="Cache directory path")
@click.option("--config-dir", help="Configuration directory path")
def list_repos(
    platform: Optional[str],
    repo_type: Optional[str],
    os: Optional[str],
    version: Optional[str],
    eol: bool,
    active: bool,
    output_format: str,
    cache_dir: Optional[str],
    config_dir: Optional[str],
):
    """List available repositories from 50+ supported package managers.

    Shows all configured repositories with their status, priority, and metadata.
    Supports filtering by platform, repository type, OS, OS version, and EOL status.

    Examples:
      saigen repositories list-repos
      saigen repositories list-repos --platform linux
      saigen repositories list-repos --type npm --format json
      saigen repositories list-repos --os ubuntu --version 22.04
      saigen repositories list-repos --eol
      saigen repositories list-repos --active
    """
    asyncio.run(_list_repositories(platform, repo_type, os, version, eol, active, output_format, cache_dir, config_dir))


async def _list_repositories(
    platform: Optional[str],
    repo_type: Optional[str],
    os: Optional[str],
    version: Optional[str],
    eol: bool,
    active: bool,
    output_format: str,
    cache_dir: Optional[str],
    config_dir: Optional[str],
):
    """Async implementation of list repositories."""
    try:
        # Initialize repository manager
        manager = get_repository_manager(cache_dir, config_dir)

        async with manager:
            # Get repository information
            repositories = manager.get_all_repository_info(platform)

            # Filter by type if specified
            if repo_type:
                repositories = [r for r in repositories if r.type == repo_type]
            
            # Filter by OS if specified
            if os:
                repositories = [r for r in repositories if _matches_os(r, os)]
            
            # Filter by version if specified
            if version:
                repositories = [r for r in repositories if _matches_version(r, version)]
            
            # Filter by EOL status if specified
            if eol:
                repositories = [r for r in repositories if r.eol]
            elif active:
                repositories = [r for r in repositories if not r.eol]

            if output_format == "json":
                data = [repo.model_dump() for repo in repositories]
                click.echo(json.dumps(data, indent=2, default=str))

            elif output_format == "yaml":
                data = [repo.model_dump() for repo in repositories]
                click.echo(yaml.dump(data, default_flow_style=False))

            else:  # table format
                if not repositories:
                    click.echo("No repositories found.")
                    return

                headers = ["Name", "Type", "Platform", "OS Versions", "Status", "Priority", "Enabled", "Description"]
                rows = []

                for repo in repositories:
                    # Format OS versions and codenames
                    os_versions = _format_os_versions(repo)
                    
                    # Format status with EOL badge
                    status = "[EOL]" if repo.eol else "Active"
                    
                    rows.append(
                        [
                            repo.name,
                            repo.type,
                            repo.platform,
                            os_versions,
                            status,
                            repo.priority,
                            "✓" if repo.enabled else "✗",
                            (repo.description or "")[:35]
                            + ("..." if len(repo.description or "") > 35 else ""),
                        ]
                    )

                click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
                click.echo(f"\nTotal: {len(repositories)} repositories")
                
                # Show EOL count if any
                eol_count = sum(1 for r in repositories if r.eol)
                if eol_count > 0:
                    click.echo(f"EOL repositories: {eol_count}")

    except Exception as e:
        logger.error(f"Failed to list repositories: {e}")
        click.echo(f"Error: {e}", err=True)


@repositories.command()
@click.argument("query")
@click.option("--platform", help="Filter by platform (linux, macos, windows, universal)")
@click.option("--type", "repo_type", help="Filter by repository type (apt, brew, npm, pypi, etc.)")
@click.option("--limit", type=int, default=20, help="Maximum number of results")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json", "yaml"]),
    help="Output format",
)
@click.option("--cache-dir", help="Cache directory path")
@click.option("--config-dir", help="Configuration directory path")
def search(
    query: str,
    platform: Optional[str],
    repo_type: Optional[str],
    limit: int,
    output_format: str,
    cache_dir: Optional[str],
    config_dir: Optional[str],
):
    """Search for packages across all 50+ repositories concurrently.

    Performs concurrent searches across multiple package repositories including
    apt, brew, npm, pypi, cargo, winget, and many more. Results include package
    name, version, repository, platform, and description.

    Examples:
      saigen repositories search "redis"
      saigen repositories search "nginx" --platform linux --limit 10
      saigen repositories search "react" --type npm --format json
    """
    asyncio.run(
        _search_packages(query, platform, repo_type, limit, output_format, cache_dir, config_dir)
    )


async def _search_packages(
    query: str,
    platform: Optional[str],
    repo_type: Optional[str],
    limit: int,
    output_format: str,
    cache_dir: Optional[str],
    config_dir: Optional[str],
):
    """Async implementation of package search."""
    try:
        # Initialize repository manager
        manager = get_repository_manager(cache_dir, config_dir)

        async with manager:
            click.echo(f"Searching for '{query}'...")

            # Search packages
            result = await manager.search_packages(
                query=query, platform=platform, repository_names=None
            )

            # Apply limit
            packages = result.packages[:limit] if limit else result.packages

            if output_format == "json":
                data = {
                    "query": result.query,
                    "total_results": result.total_results,
                    "search_time": result.search_time,
                    "repository_sources": result.repository_sources,
                    "packages": [pkg.model_dump() for pkg in packages],
                }
                click.echo(json.dumps(data, indent=2, default=str))

            elif output_format == "yaml":
                data = {
                    "query": result.query,
                    "total_results": result.total_results,
                    "search_time": result.search_time,
                    "repository_sources": result.repository_sources,
                    "packages": [pkg.model_dump() for pkg in packages],
                }
                click.echo(yaml.dump(data, default_flow_style=False))

            else:  # table format
                if not packages:
                    click.echo("No packages found.")
                    return

                headers = ["Name", "Version", "Repository", "Platform", "Description"]
                rows = []

                for pkg in packages:
                    description = (pkg.description or "")[:60]
                    if len(pkg.description or "") > 60:
                        description += "..."

                    rows.append(
                        [pkg.name, pkg.version, pkg.repository_name, pkg.platform, description]
                    )

                click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
                click.echo(f"\nFound {result.total_results} packages in {result.search_time:.2f}s")
                click.echo(f"Searched repositories: {', '.join(result.repository_sources)}")

    except Exception as e:
        logger.error(f"Failed to search packages: {e}")
        click.echo(f"Error: {e}", err=True)


@repositories.command()
@click.option("--platform", help="Filter by platform (linux, macos, windows, universal)")
@click.option("--type", "repo_type", help="Filter by repository type (apt, brew, npm, etc.)")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json", "yaml"]),
    help="Output format",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed error messages")
@click.option("--cache-dir", help="Cache directory path")
@click.option("--config-dir", help="Configuration directory path")
def stats(
    platform: Optional[str],
    repo_type: Optional[str],
    output_format: str,
    verbose: bool,
    cache_dir: Optional[str],
    config_dir: Optional[str],
):
    """Show comprehensive repository statistics and health information.

    Displays statistics for all repositories including package counts, cache status,
    hit rates, and per-repository health. Shows supported platforms and types.

    Examples:
      saigen repositories stats
      saigen repositories stats --platform linux
      saigen repositories stats --format json
      saigen repositories stats --verbose
    """
    asyncio.run(
        _show_statistics(platform, repo_type, output_format, verbose, cache_dir, config_dir)
    )


async def _show_statistics(
    platform: Optional[str],
    repo_type: Optional[str],
    output_format: str,
    verbose: bool,
    cache_dir: Optional[str],
    config_dir: Optional[str],
):
    """Async implementation of show statistics."""
    manager = None
    try:
        # Initialize repository manager
        manager = get_repository_manager(cache_dir, config_dir)

        async with manager:
            # Get statistics
            stats = await manager.get_statistics()

            if output_format == "json":
                click.echo(json.dumps(stats, indent=2, default=str))

            elif output_format == "yaml":
                click.echo(yaml.dump(stats, default_flow_style=False))

            else:  # table format
                click.echo("Repository Statistics")
                click.echo("=" * 50)

                # General statistics
                click.echo(f"Total repositories: {stats.get('total_repositories', 0)}")
                click.echo(f"Enabled repositories: {stats.get('enabled_repositories', 0)}")
                click.echo(
                    f"Supported platforms: {
                        ', '.join(
                            sorted(
                                stats.get(
                                    'supported_platforms',
                                    [])))}")
                click.echo(
                    f"Supported types: {', '.join(sorted(stats.get('supported_types', [])))}"
                )

                # Cache statistics
                cache_stats = stats.get("cache", {})
                if cache_stats:
                    click.echo(f"\nCache Statistics:")
                    click.echo(f"  Total entries: {cache_stats.get('total_entries', 0)}")
                    click.echo(f"  Cache size: {cache_stats.get('total_size_mb', 0):.1f} MB")
                    click.echo(f"  Hit rate: {cache_stats.get('hit_rate', 0):.1%}")

                # Repository-specific statistics
                repo_stats = stats.get("repositories", {})
                if repo_stats:
                    click.echo(f"\nPer-Repository Statistics:")

                    headers = ["Repository", "Packages", "Status", "Last Updated"]
                    rows = []
                    errors_detail = []

                    for repo_name, repo_data in repo_stats.items():
                        if isinstance(repo_data, dict):
                            package_count = repo_data.get("package_count", "N/A")
                            error = repo_data.get("error")
                            status = "Error" if error else "OK"
                            last_updated = repo_data.get("last_updated", "N/A")

                            if isinstance(last_updated, str) and last_updated != "N/A":
                                try:
                                    from datetime import datetime

                                    dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                                    last_updated = dt.strftime("%Y-%m-%d %H:%M")
                                except BaseException:
                                    pass

                            rows.append([repo_name, package_count, status, last_updated])

                            # Collect error details for verbose output
                            if error and verbose:
                                errors_detail.append((repo_name, error))

                    if rows:
                        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))

                    # Show detailed error messages in verbose mode
                    if errors_detail and verbose:
                        click.echo("\n" + "=" * 50)
                        click.echo("Detailed Error Messages:")
                        click.echo("=" * 50)
                        for repo_name, error_msg in errors_detail:
                            click.echo(f"\n{repo_name}:")
                            click.echo(f"  {error_msg}")

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        click.echo(f"Error: {e}", err=True)
    finally:
        # Ensure cleanup
        if manager:
            try:
                await manager.close()
            except Exception as e:
                logger.debug(f"Error during cleanup: {e}")


@repositories.command()
@click.option("--repository", help="Specific repository to update")
@click.option("--force", is_flag=True, help="Force update even if cache is valid")
@click.option("--cache-dir", help="Cache directory path")
@click.option("--config-dir", help="Configuration directory path")
def update_cache(
    repository: Optional[str], force: bool, cache_dir: Optional[str], config_dir: Optional[str]
):
    """Update repository cache."""
    asyncio.run(_update_cache(repository, force, cache_dir, config_dir))


async def _update_cache(
    repository: Optional[str], force: bool, cache_dir: Optional[str], config_dir: Optional[str]
):
    """Async implementation of cache update."""
    try:
        # Initialize repository manager
        manager = get_repository_manager(cache_dir, config_dir)

        async with manager:
            repository_names = [repository] if repository else None

            click.echo("Updating repository cache...")

            results = await manager.update_cache(repository_names, force)

            # Show results
            headers = ["Repository", "Status"]
            rows = []

            success_count = 0
            for repo_name, success in results.items():
                status = "✓ Success" if success else "✗ Failed"
                if success:
                    success_count += 1
                rows.append([repo_name, status])

            click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
            click.echo(f"\nUpdated {success_count}/{len(results)} repositories successfully")

    except Exception as e:
        logger.error(f"Failed to update cache: {e}")
        click.echo(f"Error: {e}", err=True)


@repositories.command()
@click.argument("package_name")
@click.option("--version", help="Specific version to get details for")
@click.option("--platform", help="Filter by platform")
@click.option(
    "--format",
    "output_format",
    default="yaml",
    type=click.Choice(["table", "json", "yaml"]),
    help="Output format",
)
@click.option("--cache-dir", help="Cache directory path")
@click.option("--config-dir", help="Configuration directory path")
def info(
    package_name: str,
    version: Optional[str],
    platform: Optional[str],
    output_format: str,
    cache_dir: Optional[str],
    config_dir: Optional[str],
):
    """Get detailed information about a package."""
    asyncio.run(
        _get_package_info(package_name, version, platform, output_format, cache_dir, config_dir)
    )


async def _get_package_info(
    package_name: str,
    version: Optional[str],
    platform: Optional[str],
    output_format: str,
    cache_dir: Optional[str],
    config_dir: Optional[str],
):
    """Async implementation of get package info."""
    try:
        # Initialize repository manager
        manager = get_repository_manager(cache_dir, config_dir)

        async with manager:
            click.echo(f"Getting information for '{package_name}'...")

            package = await manager.get_package_details(package_name, version, platform)

            if not package:
                click.echo(f"Package '{package_name}' not found.")
                return

            if output_format == "json":
                click.echo(json.dumps(package.model_dump(), indent=2, default=str))

            elif output_format == "yaml":
                click.echo(yaml.dump(package.model_dump(), default_flow_style=False))

            else:  # table format
                click.echo(f"Package Information: {package.name}")
                click.echo("=" * 50)

                info_data = [
                    ["Name", package.name],
                    ["Version", package.version],
                    ["Repository", package.repository_name],
                    ["Platform", package.platform],
                    ["Description", package.description or "N/A"],
                    ["Homepage", package.homepage or "N/A"],
                    ["License", package.license or "N/A"],
                    ["Maintainer", package.maintainer or "N/A"],
                    ["Category", package.category or "N/A"],
                    ["Size", f"{package.size} bytes" if package.size else "N/A"],
                    [
                        "Dependencies",
                        ", ".join(package.dependencies) if package.dependencies else "None",
                    ],
                    ["Tags", ", ".join(package.tags) if package.tags else "None"],
                    ["Download URL", package.download_url or "N/A"],
                    [
                        "Last Updated",
                        package.last_updated.strftime("%Y-%m-%d %H:%M:%S")
                        if package.last_updated
                        else "N/A",
                    ],
                ]

                click.echo(tabulate(info_data, tablefmt="grid"))

    except Exception as e:
        logger.error(f"Failed to get package info: {e}")
        click.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    repositories()
