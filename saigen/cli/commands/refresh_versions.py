"""Refresh versions command for saigen CLI."""

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import yaml

from ...models.saidata import SaiData
from ...repositories.manager import RepositoryManager
from ...utils.errors import RepositoryError


class VersionRefreshResult:
    """Result of version refresh operation."""

    def __init__(self):
        self.software_name: str = ""
        self.total_packages: int = 0
        self.updated_packages: int = 0
        self.unchanged_packages: int = 0
        self.failed_packages: int = 0
        self.updates: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.execution_time: float = 0.0

    @property
    def success(self) -> bool:
        """Check if refresh was successful."""
        return self.failed_packages == 0 and self.updated_packages > 0


@click.command()
@click.argument("saidata_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: overwrite input file)",
)
@click.option(
    "--providers", multiple=True, help="Target specific providers (e.g., apt, brew, winget)"
)
@click.option(
    "--backup/--no-backup", default=True, help="Create backup of original file (default: enabled)"
)
@click.option(
    "--backup-dir",
    type=click.Path(path_type=Path),
    help="Directory for backup files (default: same as input file)",
)
@click.option(
    "--check-only", is_flag=True, help="Check for version updates without modifying files"
)
@click.option("--show-unchanged", is_flag=True, help="Show packages that are already up-to-date")
@click.option(
    "--use-cache/--no-cache", default=True, help="Use cached repository data (default: enabled)"
)
@click.pass_context
def refresh_versions(
    ctx: click.Context,
    saidata_file: Path,
    output: Optional[Path],
    providers: tuple,
    backup: bool,
    backup_dir: Optional[Path],
    check_only: bool,
    show_unchanged: bool,
    use_cache: bool,
):
    """Refresh package versions from repository data without LLM queries.

    Updates version information in existing saidata files by querying package
    repositories directly. This is a fast, cost-free operation that keeps your
    saidata files synchronized with upstream package versions.

    The command:
    • Loads existing saidata file
    • Queries package repositories for current versions
    • Updates version fields in packages, binaries, sources, scripts
    • Preserves all other metadata unchanged
    • Creates backup before modifying (optional)

    Examples:
        # Refresh all package versions
        saigen refresh-versions nginx.yaml

        # Check for updates without modifying
        saigen refresh-versions --check-only nginx.yaml

        # Refresh specific providers only
        saigen refresh-versions --providers apt,brew nginx.yaml

        # Save to different file
        saigen refresh-versions --output nginx-updated.yaml nginx.yaml

        # Skip cache for latest data
        saigen refresh-versions --no-cache nginx.yaml
    """
    config = ctx.obj.get("config")
    verbose = ctx.obj.get("verbose", False)
    dry_run = ctx.obj.get("dry_run", False)

    if verbose:
        click.echo(f"Refreshing versions for: {saidata_file}")
        click.echo(f"Check only: {check_only}")
        click.echo(f"Use cache: {use_cache}")
        click.echo(f"Target providers: {list(providers) if providers else 'all'}")
        click.echo(f"Dry run: {dry_run}")

    if dry_run:
        click.echo(f"[DRY RUN] Would refresh versions in: {saidata_file}")
        if output:
            click.echo(f"[DRY RUN] Would save to: {output}")
        elif not check_only:
            click.echo(f"[DRY RUN] Would overwrite: {saidata_file}")
        if backup and not check_only:
            backup_path = _get_backup_path(saidata_file, backup_dir)
            click.echo(f"[DRY RUN] Would create backup: {backup_path}")
        return

    # Full implementation
    backup_path = None
    try:
        # Load existing saidata
        saidata = _load_saidata(saidata_file)

        if verbose:
            click.echo(f"Loaded saidata: {saidata.metadata.name}")

        # Create backup if requested and not check-only
        if backup and not check_only:
            backup_path = _create_backup(saidata_file, backup_dir)
            if verbose:
                click.echo(f"Created backup: {backup_path}")

        # Refresh versions
        async def run_refresh():
            return await _refresh_versions(
                saidata=saidata,
                config=config,
                target_providers=list(providers) if providers else None,
                use_cache=use_cache,
                verbose=verbose,
            )

        result = asyncio.run(run_refresh())

        # Display results
        _display_results(result, verbose, show_unchanged, check_only)

        # Save if not check-only and updates were made
        if not check_only and result.updated_packages > 0:
            output_path = output or saidata_file
            _save_saidata(saidata, output_path)
            click.echo(f"✓ Saved updated saidata to: {output_path}")
        elif check_only and result.updated_packages > 0:
            click.echo(f"\n💡 Run without --check-only to apply {result.updated_packages} update(s)")
        elif result.updated_packages == 0:
            click.echo("✓ All versions are up-to-date")

    except Exception as e:
        click.echo(f"✗ Version refresh failed: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()

        # Restore from backup if operation failed
        if backup_path and backup_path.exists() and not check_only:
            if click.confirm("Operation failed. Restore from backup?"):
                shutil.copy2(backup_path, saidata_file)
                click.echo(f"Restored from backup: {backup_path}")

        ctx.exit(1)


async def _refresh_versions(
    saidata: SaiData,
    config: Any,
    target_providers: Optional[List[str]],
    use_cache: bool,
    verbose: bool,
) -> VersionRefreshResult:
    """Refresh versions by querying repositories.

    Args:
        saidata: Loaded saidata object
        config: Configuration object
        target_providers: List of providers to target (None = all)
        use_cache: Whether to use cached repository data
        verbose: Enable verbose output

    Returns:
        VersionRefreshResult with update information
    """
    result = VersionRefreshResult()
    result.software_name = saidata.metadata.name
    start_time = asyncio.get_event_loop().time()

    # Initialize repository manager
    cache_dir = Path.home() / ".saigen" / "cache" / "repositories"
    if hasattr(config, "repositories") and hasattr(config.repositories, "cache_directory"):
        cache_dir = Path(config.repositories.cache_directory)

    repo_manager = RepositoryManager(cache_dir=cache_dir)
    await repo_manager.initialize()

    # Collect all packages to check
    packages_to_check = _collect_packages_from_saidata(saidata, target_providers)
    result.total_packages = len(packages_to_check)

    if verbose:
        click.echo(f"Found {result.total_packages} package(s) to check")

    # Query repositories for each package
    for pkg_info in packages_to_check:
        try:
            current_version = await _query_package_version(
                repo_manager=repo_manager,
                package_name=pkg_info["package_name"],
                provider=pkg_info["provider"],
                use_cache=use_cache,
                verbose=verbose,
            )

            if current_version:
                old_version = pkg_info["current_version"]

                if current_version != old_version:
                    # Update the version in saidata
                    _update_package_version(saidata, pkg_info, current_version)

                    result.updated_packages += 1
                    result.updates.append(
                        {
                            "provider": pkg_info["provider"],
                            "package": pkg_info["package_name"],
                            "old_version": old_version,
                            "new_version": current_version,
                            "location": pkg_info["location"],
                        }
                    )
                else:
                    result.unchanged_packages += 1
            else:
                result.warnings.append(
                    f"Could not find version for {pkg_info['package_name']} "
                    f"in {pkg_info['provider']} repository"
                )
                result.unchanged_packages += 1

        except Exception as e:
            result.failed_packages += 1
            result.errors.append(
                f"Failed to check {pkg_info['package_name']} " f"({pkg_info['provider']}): {str(e)}"
            )

    result.execution_time = asyncio.get_event_loop().time() - start_time
    return result


def _collect_packages_from_saidata(
    saidata: SaiData, target_providers: Optional[List[str]]
) -> List[Dict[str, Any]]:
    """Collect all packages from saidata that need version checking.

    Args:
        saidata: SaiData object
        target_providers: List of providers to target (None = all)

    Returns:
        List of package information dictionaries
    """
    packages = []

    # Helper to check if provider should be included
    def should_include_provider(provider: str) -> bool:
        if not target_providers:
            return True
        return provider in target_providers

    # Check top-level packages
    if saidata.packages:
        for pkg in saidata.packages:
            if pkg.version:
                packages.append(
                    {
                        "provider": "default",
                        "package_name": pkg.package_name,
                        "current_version": pkg.version,
                        "location": "packages",
                        "object": pkg,
                    }
                )

    # Check provider-specific configurations
    if saidata.providers:
        for provider_name, provider_config in saidata.providers.items():
            if not should_include_provider(provider_name):
                continue

            # Check packages in provider
            if provider_config.packages:
                for pkg in provider_config.packages:
                    if pkg.version:
                        packages.append(
                            {
                                "provider": provider_name,
                                "package_name": pkg.package_name,
                                "current_version": pkg.version,
                                "location": f"providers.{provider_name}.packages",
                                "object": pkg,
                            }
                        )

            # Check package_sources
            if provider_config.package_sources:
                for pkg_source in provider_config.package_sources:
                    if pkg_source.packages:
                        for pkg in pkg_source.packages:
                            if pkg.version:
                                packages.append(
                                    {
                                        "provider": provider_name,
                                        "package_name": pkg.package_name,
                                        "current_version": pkg.version,
                                        "location": f"providers.{provider_name}.package_sources.{
                                            pkg_source.name}",
                                        "object": pkg,
                                    })

            # Check repositories
            if provider_config.repositories:
                for repo in provider_config.repositories:
                    if repo.packages:
                        for pkg in repo.packages:
                            if pkg.version:
                                packages.append(
                                    {
                                        "provider": provider_name,
                                        "package_name": pkg.package_name,
                                        "current_version": pkg.version,
                                        "location": f"providers.{provider_name}.repositories.{
                                            repo.name}",
                                        "object": pkg,
                                    })

            # Check binaries
            if provider_config.binaries:
                for binary in provider_config.binaries:
                    if binary.version:
                        packages.append(
                            {
                                "provider": provider_name,
                                "package_name": binary.name,
                                "current_version": binary.version,
                                "location": f"providers.{provider_name}.binaries",
                                "object": binary,
                            }
                        )

            # Check sources
            if provider_config.sources:
                for source in provider_config.sources:
                    if source.version:
                        packages.append(
                            {
                                "provider": provider_name,
                                "package_name": source.name,
                                "current_version": source.version,
                                "location": f"providers.{provider_name}.sources",
                                "object": source,
                            }
                        )

            # Check scripts
            if provider_config.scripts:
                for script in provider_config.scripts:
                    if script.version:
                        packages.append(
                            {
                                "provider": provider_name,
                                "package_name": script.name,
                                "current_version": script.version,
                                "location": f"providers.{provider_name}.scripts",
                                "object": script,
                            }
                        )

    return packages


async def _query_package_version(
    repo_manager: RepositoryManager,
    package_name: str,
    provider: str,
    use_cache: bool,
    verbose: bool,
) -> Optional[str]:
    """Query repository for package version.

    Args:
        repo_manager: Repository manager instance
        package_name: Name of package to query
        provider: Provider name (apt, brew, etc.)
        use_cache: Whether to use cached data (note: currently not used by search API)
        verbose: Enable verbose output

    Returns:
        Version string if found, None otherwise
    """
    try:
        # Search for the package
        # Note: search_packages doesn't support use_cache parameter
        # Cache is managed at the repository level
        search_result = await repo_manager.search_packages(
            query=package_name, repository_names=[provider] if provider != "default" else None
        )

        if search_result.packages:
            # Find exact match (case-insensitive)
            for pkg in search_result.packages:
                if pkg.name.lower() == package_name.lower():
                    if verbose:
                        click.echo(f"  Found {package_name} v{pkg.version} in {provider}")
                    return pkg.version

            # If no exact match, try the first result
            first_pkg = search_result.packages[0]
            if verbose:
                click.echo(f"  Using closest match: {first_pkg.name} v{first_pkg.version}")
            return first_pkg.version

        return None

    except RepositoryError as e:
        if verbose:
            click.echo(f"  Repository error for {package_name}: {e}")
        return None
    except Exception as e:
        if verbose:
            click.echo(f"  Error querying {package_name}: {e}")
        return None


def _update_package_version(saidata: SaiData, pkg_info: Dict[str, Any], new_version: str) -> None:
    """Update package version in saidata object.

    Args:
        saidata: SaiData object to update
        pkg_info: Package information dictionary
        new_version: New version string
    """
    # Update the version in the package object
    pkg_obj = pkg_info["object"]
    pkg_obj.version = new_version


def _display_results(
    result: VersionRefreshResult, verbose: bool, show_unchanged: bool, check_only: bool
) -> None:
    """Display refresh results to user.

    Args:
        result: VersionRefreshResult object
        verbose: Enable verbose output
        show_unchanged: Show unchanged packages
        check_only: Check-only mode
    """
    click.echo(f"\n{'Check' if check_only else 'Refresh'} Results for {result.software_name}:")
    click.echo(f"  Total packages checked: {result.total_packages}")
    click.echo(f"  Updates {'available' if check_only else 'applied'}: {result.updated_packages}")
    click.echo(f"  Already up-to-date: {result.unchanged_packages}")

    if result.failed_packages > 0:
        click.echo(f"  Failed: {result.failed_packages}")

    click.echo(f"  Execution time: {result.execution_time:.2f}s")

    # Show updates
    if result.updates:
        click.echo(f"\n{'Available' if check_only else 'Applied'} Updates:")
        for update in result.updates:
            click.echo(
                f"  • {update['provider']}/{update['package']}: "
                f"{update['old_version']} → {update['new_version']}"
            )
            if verbose:
                click.echo(f"    Location: {update['location']}")

    # Show unchanged if requested
    if show_unchanged and result.unchanged_packages > 0 and verbose:
        click.echo(f"\nUp-to-date packages: {result.unchanged_packages}")

    # Show warnings
    if result.warnings:
        click.echo("\nWarnings:")
        for warning in result.warnings:
            click.echo(f"  ⚠ {warning}")

    # Show errors
    if result.errors:
        click.echo("\nErrors:")
        for error in result.errors:
            click.echo(f"  ✗ {error}")


def _load_saidata(file_path: Path) -> SaiData:
    """Load saidata from file.

    Args:
        file_path: Path to saidata file

    Returns:
        SaiData instance

    Raises:
        click.ClickException: If file cannot be loaded
    """
    try:
        # Read file content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove Python object tags that may exist in older files
        # These tags like !!python/object/apply:saigen.models.saidata.ServiceType
        # need to be cleaned before safe_load can process them
        import re

        # Pattern to match Python object tags and extract the value
        # Example: !!python/object/apply:saigen.models.saidata.ServiceType\n  - systemd
        # Should become just: systemd
        content = re.sub(r"!!python/object/apply:[^\n]+\n\s*-\s*(\w+)", r"\1", content)

        # Also handle inline Python object tags
        content = re.sub(r"!!python/object/apply:[^\s]+\s+", "", content)

        # Parse cleaned YAML
        data = yaml.safe_load(content)

        return SaiData(**data)

    except yaml.YAMLError as e:
        raise click.ClickException(f"Invalid YAML in {file_path}: {e}")
    except Exception as e:
        raise click.ClickException(f"Failed to load {file_path}: {e}")


def _save_saidata(saidata: SaiData, output_path: Path) -> None:
    """Save saidata to file.

    Args:
        saidata: SaiData object
        output_path: Output file path

    Raises:
        click.ClickException: If file cannot be saved
    """
    try:
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and save as YAML (matching generation_engine.py approach)
        data = saidata.model_dump(exclude_none=True)

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)

    except Exception as e:
        raise click.ClickException(f"Failed to save {output_path}: {e}")


def _get_backup_path(original_path: Path, backup_dir: Optional[Path] = None) -> Path:
    """Get backup file path.

    Args:
        original_path: Original file path
        backup_dir: Directory for backup (optional)

    Returns:
        Backup file path
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{original_path.stem}.backup.{timestamp}{original_path.suffix}"

    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir / backup_name
    else:
        return original_path.parent / backup_name


def _create_backup(original_path: Path, backup_dir: Optional[Path] = None) -> Path:
    """Create backup of original file.

    Args:
        original_path: Original file path
        backup_dir: Directory for backup (optional)

    Returns:
        Backup file path

    Raises:
        click.ClickException: If backup creation fails
    """
    try:
        backup_path = _get_backup_path(original_path, backup_dir)
        shutil.copy2(original_path, backup_path)
        return backup_path

    except Exception as e:
        raise click.ClickException(f"Failed to create backup: {e}")


if __name__ == "__main__":
    refresh_versions()
