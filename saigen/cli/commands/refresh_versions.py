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
from ...utils.path_utils import extract_os_info
from ...core.validator import SaidataValidator


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
@click.option(
    "--skip-default", is_flag=True, help="Skip default.yaml files (useful for directory processing)"
)
@click.option(
    "--all-variants", is_flag=True, help="Process all saidata files in directory (default.yaml + OS-specific)"
)
@click.option(
    "--create-missing", is_flag=True, help="Create OS-specific files that don't exist (requires directory input)"
)
@click.option(
    "--interactive", is_flag=True, help="Show diff and prompt before applying changes"
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
    skip_default: bool,
    all_variants: bool,
    create_missing: bool,
    interactive: bool,
):
    """Refresh package versions from repository data without LLM queries.

    Updates version information in existing saidata files by querying package
    repositories directly. This is a fast, cost-free operation that keeps your
    saidata files synchronized with upstream package versions.

    \b
    The command:
    • Loads existing saidata file or scans directory for saidata files
    • Queries package repositories for current versions
    • Updates version fields in packages, binaries, sources, scripts
    • Preserves all other metadata unchanged
    • Creates backup before modifying (optional)
    • Supports OS-specific repository selection

    \b
    OS-Specific Behavior:
    • For default.yaml: queries generic repositories (upstream versions)
    • For OS-specific files (e.g., ubuntu/22.04.yaml): queries OS-specific repositories
    • Use --skip-default to skip default.yaml files (useful for batch processing)

    \b
    Directory Processing:
    • Use --all-variants to process all saidata files in a directory
    • Scans recursively for .yaml files with 'version' and 'metadata' fields
    • Processes default.yaml and OS-specific variants (ubuntu/22.04.yaml, etc.)
    • Each file is updated in place (--output not supported for directories)
    • Displays summary table with results for all files

    \b
    Creating Missing OS-Specific Files:
    • Use --create-missing to create OS-specific files that don't exist
    • Requires directory input (not supported for single file)
    • Creates files based on configured repositories (ubuntu/22.04.yaml, etc.)
    • Only includes fields that differ from default.yaml
    • Always includes provider-specific version information
    • Creates necessary directory structure automatically

    \b
    Examples:
        # Refresh all package versions in a single file
        saigen refresh-versions nginx.yaml

        # Process all saidata files in a directory
        saigen refresh-versions --all-variants software/ng/nginx/

        # Process directory, skip default.yaml
        saigen refresh-versions --all-variants --skip-default software/ng/nginx/

        # Create missing OS-specific files
        saigen refresh-versions --all-variants --create-missing software/ng/nginx/

        # Check for updates without modifying
        saigen refresh-versions --check-only nginx.yaml

        # Interactive mode: review changes before applying
        saigen refresh-versions --interactive nginx.yaml

        # Refresh specific providers only
        saigen refresh-versions --providers apt,brew nginx.yaml

        # Save to different file (single file only)
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
        click.echo(f"All variants: {all_variants}")
        click.echo(f"Create missing: {create_missing}")
        click.echo(f"Dry run: {dry_run}")

    # Validate --create-missing flag
    if create_missing and not saidata_file.is_dir():
        raise click.ClickException(
            "--create-missing requires a directory input, not a single file."
        )

    # Check if input is a directory
    if saidata_file.is_dir():
        if not all_variants and not create_missing:
            raise click.ClickException(
                f"{saidata_file} is a directory. Use --all-variants to process all saidata files in the directory."
            )
        
        if output:
            raise click.ClickException(
                "--output option is not supported for directory processing. Files are updated in place."
            )
        
        # Directory processing mode
        if dry_run:
            click.echo(f"[DRY RUN] Would scan directory: {saidata_file}")
            click.echo(f"[DRY RUN] Would process all saidata files found")
            return
        
        # Scan directory for saidata files
        files_to_process = _scan_directory_for_saidata(saidata_file, verbose)
        
        if not files_to_process:
            click.echo(f"No saidata files found in {saidata_file}")
            return
        
        # Process multiple files
        _process_multiple_files(
            ctx=ctx,
            files=files_to_process,
            providers=providers,
            backup=backup,
            backup_dir=backup_dir,
            check_only=check_only,
            show_unchanged=show_unchanged,
            use_cache=use_cache,
            skip_default=skip_default,
            create_missing=create_missing,
            directory=saidata_file,
            verbose=verbose,
            interactive=interactive,
        )
        return

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

    # Full implementation for single file
    backup_path = None
    try:
        # Extract OS information from file path
        os_info = extract_os_info(saidata_file)
        
        # Check if we should skip default.yaml
        if skip_default and os_info['is_default']:
            if verbose:
                click.echo(f"Skipping default.yaml due to --skip-default flag")
            click.echo("✓ Skipped default.yaml (--skip-default)")
            return
        
        if verbose:
            if os_info['is_default']:
                click.echo(f"Detected file type: default.yaml (OS-agnostic)")
            elif os_info['os'] and os_info['version']:
                click.echo(f"Detected OS context: {os_info['os']} {os_info['version']}")
            else:
                click.echo(f"No OS context detected from path")
        
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
                os_context=os_info,
                target_providers=list(providers) if providers else None,
                use_cache=use_cache,
                verbose=verbose,
            )

        result = asyncio.run(run_refresh())

        # Display results
        _display_results(result, verbose, show_unchanged, check_only)

        # Interactive mode: show diff and prompt before saving
        if interactive and not check_only and result.updated_packages > 0:
            _display_interactive_diff(result)
            if not click.confirm("Apply these changes?"):
                click.echo("Changes not applied.")
                return

        # Save if not check-only and updates were made
        if not check_only and result.updated_packages > 0:
            output_path = output or saidata_file
            _save_saidata(saidata, output_path, backup_path)
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
    os_context: Optional[Dict[str, Optional[str]]],
    target_providers: Optional[List[str]],
    use_cache: bool,
    verbose: bool,
) -> VersionRefreshResult:
    """Refresh versions by querying repositories.

    Args:
        saidata: Loaded saidata object
        config: Configuration object
        os_context: Dict with 'os', 'version', and 'is_default' keys (from extract_os_info)
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
            query_result = await _query_package_version(
                repo_manager=repo_manager,
                package_name=pkg_info["package_name"],
                provider=pkg_info["provider"],
                os_context=os_context,
                use_cache=use_cache,
                verbose=verbose,
            )

            if query_result:
                old_version = pkg_info["current_version"]
                new_version = query_result['version']
                new_package_name = query_result['name']
                old_package_name = pkg_info["package_name"]
                
                # Check if package name changed
                name_changed = new_package_name != old_package_name
                version_changed = new_version != old_version

                if version_changed or name_changed:
                    # Update the version and/or package name in saidata
                    _update_package_version(
                        saidata, 
                        pkg_info, 
                        new_version,
                        new_package_name if name_changed else None
                    )

                    result.updated_packages += 1
                    update_info = {
                        "provider": pkg_info["provider"],
                        "package": old_package_name,
                        "old_version": old_version,
                        "new_version": new_version,
                        "location": pkg_info["location"],
                    }
                    
                    # Track name changes separately
                    if name_changed:
                        update_info["old_name"] = old_package_name
                        update_info["new_name"] = new_package_name
                    
                    result.updates.append(update_info)
                else:
                    result.unchanged_packages += 1
            else:
                # Package not found - log warning, leave package_name unchanged, continue
                # The _query_package_version function returns None for both
                # missing repository and package not found
                if verbose:
                    click.echo(f"  ⚠ Package not found: {pkg_info['package_name']}")
                
                if os_context and not os_context.get('is_default'):
                    os_name = os_context.get('os')
                    os_version = os_context.get('version')
                    if os_name and os_version:
                        from ...repositories.codename_resolver import resolve_repository_name
                        all_repo_infos = repo_manager.get_all_repository_info()
                        all_repos = {repo.name: repo for repo in all_repo_infos}
                        resolved_repo = resolve_repository_name(
                            provider=pkg_info["provider"],
                            os=os_name,
                            version=os_version,
                            repositories=all_repos
                        )
                        repo_info = repo_manager.get_repository_info(resolved_repo)
                        if not repo_info and resolved_repo != pkg_info["provider"]:
                            warning_msg = (
                                f"Repository {resolved_repo} not configured for "
                                f"{pkg_info['package_name']}"
                            )
                            result.warnings.append(warning_msg)
                            if verbose:
                                click.echo(f"  ⚠ {warning_msg}")
                        else:
                            warning_msg = (
                                f"Package '{pkg_info['package_name']}' not found "
                                f"in {pkg_info['provider']} repository"
                            )
                            result.warnings.append(warning_msg)
                            if verbose:
                                click.echo(f"  ⚠ {warning_msg}")
                    else:
                        warning_msg = (
                            f"Package '{pkg_info['package_name']}' not found "
                            f"in {pkg_info['provider']} repository"
                        )
                        result.warnings.append(warning_msg)
                        if verbose:
                            click.echo(f"  ⚠ {warning_msg}")
                else:
                    warning_msg = (
                        f"Package '{pkg_info['package_name']}' not found "
                        f"in {pkg_info['provider']} repository"
                    )
                    result.warnings.append(warning_msg)
                    if verbose:
                        click.echo(f"  ⚠ {warning_msg}")
                
                # Leave package unchanged and continue processing
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
    os_context: Optional[Dict[str, Optional[str]]],
    use_cache: bool,
    verbose: bool,
) -> Optional[Dict[str, str]]:
    """Query repository for package name and version.

    Args:
        repo_manager: Repository manager instance
        package_name: Name of package to query
        provider: Provider name (apt, brew, etc.)
        os_context: Dict with 'os', 'version', and 'is_default' keys (from extract_os_info)
        use_cache: Whether to use cached data (note: currently not used by search API)
        verbose: Enable verbose output

    Returns:
        Dict with 'name' and 'version' keys if found, None otherwise
    """
    try:
        # Determine which repository to query based on OS context
        repository_name = provider
        
        if os_context and not os_context.get('is_default'):
            # For OS-specific files, resolve to OS-specific repository
            os_name = os_context.get('os')
            os_version = os_context.get('version')
            
            if os_name and os_version:
                # Import codename resolver
                from ...repositories.codename_resolver import resolve_repository_name
                
                # Get all repositories as RepositoryInfo objects
                all_repo_infos = repo_manager.get_all_repository_info()
                
                # Convert to dict for resolve_repository_name
                all_repos = {repo.name: repo for repo in all_repo_infos}
                
                # Resolve to OS-specific repository name
                repository_name = resolve_repository_name(
                    provider=provider,
                    os=os_name,
                    version=os_version,
                    repositories=all_repos
                )
                
                if verbose:
                    if repository_name != provider:
                        click.echo(f"  Resolved to OS-specific repository: {repository_name}")
                    else:
                        click.echo(f"  Using generic provider: {provider} (no OS-specific repo found)")
        else:
            # For default.yaml or no OS context, use generic provider
            if verbose and os_context and os_context.get('is_default'):
                click.echo(f"  Using generic provider for default.yaml: {provider}")
        
        # Check if repository exists
        repo_info = repo_manager.get_repository_info(repository_name)
        if not repo_info and repository_name != provider:
            # OS-specific repository not found, log warning
            warning_msg = f"Repository {repository_name} not configured"
            if verbose:
                click.echo(f"  ⚠ {warning_msg}")
            # Return None to indicate repository not available
            # The caller will add this to warnings list
            return None
        
        # Log which repository is being queried
        if verbose:
            click.echo(f"  Querying repository: {repository_name} for package: {package_name}")
        
        # Search for the package
        # Note: search_packages doesn't support use_cache parameter
        # Cache is managed at the repository level
        search_result = await repo_manager.search_packages(
            query=package_name, repository_names=[repository_name] if provider != "default" else None
        )

        if search_result.packages:
            # Find exact match (case-insensitive)
            for pkg in search_result.packages:
                if pkg.name.lower() == package_name.lower():
                    if verbose:
                        click.echo(f"  Found {package_name} v{pkg.version} in {provider}")
                    return {'name': pkg.name, 'version': pkg.version}

            # If no exact match, try the first result
            first_pkg = search_result.packages[0]
            if verbose:
                click.echo(f"  Using closest match: {first_pkg.name} v{first_pkg.version}")
            return {'name': first_pkg.name, 'version': first_pkg.version}

        return None

    except RepositoryError as e:
        if verbose:
            click.echo(f"  Repository error for {package_name}: {e}")
        return None
    except Exception as e:
        if verbose:
            click.echo(f"  Error querying {package_name}: {e}")
        return None


def _update_package_version(
    saidata: SaiData, 
    pkg_info: Dict[str, Any], 
    new_version: str,
    new_package_name: Optional[str] = None
) -> None:
    """Update package version and optionally package name in saidata object.

    Args:
        saidata: SaiData object to update
        pkg_info: Package information dictionary
        new_version: New version string
        new_package_name: New package name if it differs, or None to keep current
    """
    # Update the version in the package object
    pkg_obj = pkg_info["object"]
    pkg_obj.version = new_version
    
    # Update package name if provided and different
    if new_package_name and hasattr(pkg_obj, 'package_name'):
        old_name = pkg_obj.package_name
        if new_package_name != old_name:
            pkg_obj.package_name = new_package_name
            # Note: pkg_obj.name (logical name) is never changed


def _display_interactive_diff(result: VersionRefreshResult) -> None:
    """Display interactive diff of changes with color coding.

    Args:
        result: VersionRefreshResult with update information
    """
    if not result.updates:
        return
    
    click.echo("\n" + "=" * 60)
    click.echo(click.style("Proposed Changes", bold=True, fg="cyan"))
    click.echo("=" * 60)
    
    for update in result.updates:
        # Check if name changed
        if 'old_name' in update and 'new_name' in update:
            # Name and version changed
            click.echo(f"\n{click.style('Provider:', bold=True)} {update['provider']}")
            click.echo(f"{click.style('Location:', bold=True)} {update['location']}")
            click.echo(
                f"{click.style('Package:', bold=True)} "
                f"{click.style(update['old_name'], fg='red', strikethrough=True)} → "
                f"{click.style(update['new_name'], fg='green')}"
            )
            click.echo(
                f"{click.style('Version:', bold=True)} "
                f"{click.style(update['old_version'], fg='red', strikethrough=True)} → "
                f"{click.style(update['new_version'], fg='green')}"
            )
        else:
            # Only version changed
            click.echo(f"\n{click.style('Provider:', bold=True)} {update['provider']}")
            click.echo(f"{click.style('Package:', bold=True)} {update['package']}")
            click.echo(f"{click.style('Location:', bold=True)} {update['location']}")
            click.echo(
                f"{click.style('Version:', bold=True)} "
                f"{click.style(update['old_version'], fg='red', strikethrough=True)} → "
                f"{click.style(update['new_version'], fg='green')}"
            )
    
    click.echo("\n" + "=" * 60)
    click.echo(f"Total changes: {click.style(str(len(result.updates)), bold=True, fg='yellow')}")
    click.echo("=" * 60 + "\n")


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
            # Check if name changed
            if 'old_name' in update and 'new_name' in update:
                # Name changed: format as "provider: old_name v1.0 → new_name v2.0"
                click.echo(
                    f"  ⚡ {update['provider']}: "
                    f"{update['old_name']} v{update['old_version']} → "
                    f"{update['new_name']} v{update['new_version']}"
                )
            else:
                # Only version changed: keep current format "provider/package: v1.0 → v2.0"
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


def _save_saidata(saidata: SaiData, output_path: Path, backup_path: Optional[Path] = None) -> None:
    """Save saidata to file with schema validation.

    Args:
        saidata: SaiData object
        output_path: Output file path
        backup_path: Backup file path for rollback on validation failure

    Raises:
        click.ClickException: If file cannot be saved or validation fails
    """
    try:
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and save as YAML (matching generation_engine.py approach)
        data = saidata.model_dump(exclude_none=True)

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)

        # Validate against schema after saving
        validator = SaidataValidator()
        validation_result = validator.validate_file(output_path)
        
        if not validation_result.is_valid:
            # Validation failed - restore from backup if available
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, output_path)
                click.echo(f"⚠ Validation failed. Restored from backup: {backup_path}", err=True)
            
            # Collect error messages
            error_messages = [f"  • {error.message}" for error in validation_result.errors[:5]]
            if len(validation_result.errors) > 5:
                error_messages.append(f"  • ... and {len(validation_result.errors) - 5} more errors")
            
            error_details = "\n".join(error_messages)
            raise click.ClickException(
                f"Updated saidata failed schema validation:\n{error_details}"
            )

    except click.ClickException:
        # Re-raise ClickException as-is
        raise
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


def _scan_directory_for_saidata(directory: Path, verbose: bool = False) -> List[Path]:
    """Scan directory recursively for saidata YAML files.

    Args:
        directory: Directory path to scan
        verbose: Enable verbose output

    Returns:
        List of Path objects for saidata files found

    Note:
        Filters for saidata files by checking for 'version' and 'metadata' fields.
        Includes both default.yaml and OS-specific files (e.g., ubuntu/22.04.yaml).
    """
    saidata_files = []
    
    if verbose:
        click.echo(f"Scanning directory: {directory}")
    
    # Recursively find all .yaml and .yml files
    yaml_files = list(directory.rglob("*.yaml")) + list(directory.rglob("*.yml"))
    
    for yaml_file in yaml_files:
        try:
            # Quick check if this is a saidata file
            with open(yaml_file, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                
            # Check for saidata markers: 'version' and 'metadata' fields
            if isinstance(content, dict) and 'version' in content and 'metadata' in content:
                saidata_files.append(yaml_file)
                if verbose:
                    click.echo(f"  Found saidata file: {yaml_file.relative_to(directory)}")
        except Exception as e:
            # Skip files that can't be parsed or read
            if verbose:
                click.echo(f"  Skipping {yaml_file.name}: {e}")
            continue
    
    if verbose:
        click.echo(f"Found {len(saidata_files)} saidata file(s)")
    
    return saidata_files


def _identify_missing_os_files(
    directory: Path,
    repo_manager: RepositoryManager,
    verbose: bool = False
) -> List[Dict[str, str]]:
    """Identify potential OS-specific files that don't exist.

    Args:
        directory: Directory path to scan (e.g., software/ng/nginx/)
        repo_manager: Repository manager to get configured repositories
        verbose: Enable verbose output

    Returns:
        List of dicts with 'os', 'version', and 'path' keys for missing files

    Note:
        Checks for pattern: if default.yaml exists, check for OS-specific files
        based on configured repositories (ubuntu/22.04.yaml, debian/11.yaml, etc.)
    """
    missing_files = []
    
    # Check if default.yaml exists
    default_file = directory / "default.yaml"
    if not default_file.exists():
        if verbose:
            click.echo(f"  No default.yaml found in {directory}, skipping OS file detection")
        return missing_files
    
    if verbose:
        click.echo(f"  Checking for missing OS-specific files based on configured repositories")
    
    # Get all configured repositories
    all_repos = repo_manager.get_all_repository_info()
    
    # Build a set of OS/version combinations from repositories
    os_versions = set()
    for repo in all_repos:
        # Check if repository has version_mapping
        if hasattr(repo, 'version_mapping') and repo.version_mapping:
            # Extract OS from repository name or distribution field
            # Repository names follow pattern: {provider}-{os}-{codename}
            # e.g., apt-ubuntu-jammy, dnf-fedora-f39
            parts = repo.name.split('-')
            if len(parts) >= 3:
                # Extract OS (second part)
                os_name = parts[1]
                
                # Get versions from version_mapping
                for version in repo.version_mapping.keys():
                    os_versions.add((os_name, version))
    
    # Check which OS-specific files are missing
    for os_name, version in sorted(os_versions):
        os_file_path = directory / os_name / f"{version}.yaml"
        if not os_file_path.exists():
            missing_files.append({
                'os': os_name,
                'version': version,
                'path': str(os_file_path)
            })
            if verbose:
                click.echo(f"    Missing: {os_name}/{version}.yaml")
    
    if verbose and missing_files:
        click.echo(f"  Found {len(missing_files)} missing OS-specific file(s)")
    
    return missing_files


async def _create_os_specific_file(
    software_dir: Path,
    os: str,
    version: str,
    default_saidata: SaiData,
    repo_manager: RepositoryManager,
    config: Any,
    providers: Optional[List[str]],
    use_cache: bool,
    verbose: bool
) -> bool:
    """Create OS-specific saidata file with minimal overrides.

    Args:
        software_dir: Base directory (e.g., software/ng/nginx/)
        os: OS name (ubuntu, debian, etc.)
        version: OS version (22.04, 11, etc.)
        default_saidata: Loaded default.yaml for comparison
        repo_manager: Repository manager for queries
        config: Configuration object
        providers: List of providers to query (None = all)
        use_cache: Whether to use cached repository data
        verbose: Enable verbose output

    Returns:
        True if file was created successfully, False otherwise

    Creates:
        {software_dir}/{os}/{version}.yaml with minimal structure:

        version: "0.3"
        providers:
          apt:
            packages:
              - name: nginx
                package_name: nginx-full  # Only if differs from default
                version: "1.18.0"  # Always included
    """
    try:
        # 1. Create directory structure (mkdir with parents=True, exist_ok=True)
        os_dir = software_dir / os
        os_dir.mkdir(parents=True, exist_ok=True)
        
        if verbose:
            click.echo(f"    Created directory: {os_dir}")
        
        # 2. Build OS context for repository queries
        os_context = {'os': os, 'version': version, 'is_default': False}
        
        # 3. Query repositories for OS-specific data
        provider_data = {}
        
        # Determine which providers to query
        providers_to_query = providers if providers else []
        
        # If no providers specified, get providers from default.yaml
        if not providers_to_query and default_saidata.providers:
            providers_to_query = list(default_saidata.providers.keys())
        
        # Query each provider
        for provider in providers_to_query:
            packages = []
            
            # Query packages from default.yaml
            if default_saidata.packages:
                for pkg in default_saidata.packages:
                    result = await _query_package_version(
                        repo_manager=repo_manager,
                        package_name=pkg.package_name,
                        provider=provider,
                        os_context=os_context,
                        use_cache=use_cache,
                        verbose=verbose
                    )
                    
                    if result:
                        # Build package data with name and version
                        pkg_data = {
                            'name': pkg.name,
                            'version': result['version']
                        }
                        
                        # Only include package_name if it differs from default.yaml
                        if result['name'] != pkg.package_name:
                            pkg_data['package_name'] = result['name']
                        
                        packages.append(pkg_data)
            
            # Add provider data if we found packages
            if packages:
                provider_data[provider] = {'packages': packages}
        
        # 4. Build minimal YAML structure (only providers section with necessary overrides)
        if not provider_data:
            if verbose:
                click.echo(f"    No package data found for {os}/{version}, skipping file creation")
            return False
        
        os_specific_data = {
            'version': '0.3',
            'providers': provider_data
        }
        
        # 5. Write file using yaml.dump() with proper formatting
        output_path = os_dir / f"{version}.yaml"
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(os_specific_data, f, default_flow_style=False, sort_keys=False, indent=2)
        
        if verbose:
            click.echo(f"    Created OS-specific file: {output_path}")
        
        return True
        
    except Exception as e:
        if verbose:
            click.echo(f"    Failed to create {os}/{version}.yaml: {e}")
        return False


def _display_multi_file_results(
    results: List[tuple],
    check_only: bool,
    verbose: bool,
) -> None:
    """Display summary results for multiple file processing.

    Args:
        results: List of tuples (file_path, result, error_msg)
        check_only: Check-only mode
        verbose: Enable verbose output
    """
    click.echo(f"\n{'='*80}")
    click.echo(f"Summary - {'Check' if check_only else 'Refresh'} Results")
    click.echo(f"{'='*80}")
    
    # Calculate totals
    total_files = len(results)
    successful_files = sum(1 for _, result, error in results if result is not None)
    failed_files = sum(1 for _, result, error in results if error is not None)
    total_updates = sum(result.updated_packages for _, result, _ in results if result is not None)
    total_unchanged = sum(result.unchanged_packages for _, result, _ in results if result is not None)
    total_failed_packages = sum(result.failed_packages for _, result, _ in results if result is not None)
    total_time = sum(result.execution_time for _, result, _ in results if result is not None)
    
    # Display table header
    click.echo(f"\n{'File':<40} {'Updates':<10} {'Unchanged':<12} {'Failed':<10} {'Time':<10}")
    click.echo(f"{'-'*40} {'-'*10} {'-'*12} {'-'*10} {'-'*10}")
    
    # Display each file's results
    for file_path, result, error in results:
        file_name = file_path.name
        if len(file_name) > 38:
            file_name = file_name[:35] + "..."
        
        if error:
            click.echo(f"{file_name:<40} {'ERROR':<10} {'-':<12} {'-':<10} {'-':<10}")
        elif result:
            updates = result.updated_packages
            unchanged = result.unchanged_packages
            failed = result.failed_packages
            time_str = f"{result.execution_time:.2f}s"
            
            click.echo(f"{file_name:<40} {updates:<10} {unchanged:<12} {failed:<10} {time_str:<10}")
    
    # Display totals
    click.echo(f"{'-'*40} {'-'*10} {'-'*12} {'-'*10} {'-'*10}")
    click.echo(f"{'TOTAL':<40} {total_updates:<10} {total_unchanged:<12} {total_failed_packages:<10} {f'{total_time:.2f}s':<10}")
    
    # Display summary statistics
    click.echo(f"\n{'='*80}")
    click.echo(f"Files processed: {total_files}")
    click.echo(f"  Successful: {successful_files}")
    click.echo(f"  Failed: {failed_files}")
    click.echo(f"Total updates {'available' if check_only else 'applied'}: {total_updates}")
    click.echo(f"Total execution time: {total_time:.2f}s")
    
    # List failed files with error messages
    if failed_files > 0:
        click.echo(f"\n{'='*80}")
        click.echo("Failed Files:")
        for file_path, result, error in results:
            if error:
                click.echo(f"  ✗ {file_path}: {error}")
    
    # Show action hint for check-only mode
    if check_only and total_updates > 0:
        click.echo(f"\n💡 Run without --check-only to apply {total_updates} update(s) across {successful_files} file(s)")
    elif total_updates == 0 and failed_files == 0:
        click.echo("\n✓ All versions are up-to-date across all files")


def _process_multiple_files(
    ctx: click.Context,
    files: List[Path],
    providers: tuple,
    backup: bool,
    backup_dir: Optional[Path],
    check_only: bool,
    show_unchanged: bool,
    use_cache: bool,
    skip_default: bool,
    create_missing: bool,
    directory: Path,
    verbose: bool,
    interactive: bool = False,
) -> None:
    """Process multiple saidata files.

    Args:
        ctx: Click context
        files: List of file paths to process
        providers: Target providers tuple
        backup: Whether to create backups
        backup_dir: Directory for backups
        check_only: Check-only mode
        show_unchanged: Show unchanged packages
        use_cache: Use cached repository data
        skip_default: Skip default.yaml files
        create_missing: Create missing OS-specific files
        directory: Directory being processed
        verbose: Enable verbose output
        interactive: Show diff and prompt before applying changes
    """
    config = ctx.obj.get("config")
    results = []
    
    # Handle --create-missing flag
    if create_missing:
        # Initialize repository manager to identify missing files
        cache_dir = Path.home() / ".saigen" / "cache" / "repositories"
        if hasattr(config, "repositories") and hasattr(config.repositories, "cache_directory"):
            cache_dir = Path(config.repositories.cache_directory)
        
        repo_manager = RepositoryManager(cache_dir=cache_dir)
        asyncio.run(repo_manager.initialize())
        
        # Identify missing OS-specific files
        missing_files = _identify_missing_os_files(directory, repo_manager, verbose)
        
        if missing_files:
            click.echo(f"\nFound {len(missing_files)} missing OS-specific file(s)")
            
            # Load default.yaml for comparison
            default_file = directory / "default.yaml"
            if default_file.exists():
                try:
                    default_saidata = _load_saidata(default_file)
                    
                    # Create each missing file
                    created_count = 0
                    for missing in missing_files:
                        if verbose:
                            click.echo(f"\nCreating {missing['os']}/{missing['version']}.yaml...")
                        else:
                            click.echo(f"Creating {missing['os']}/{missing['version']}.yaml...", nl=False)
                        
                        async def create_file():
                            return await _create_os_specific_file(
                                software_dir=directory,
                                os=missing['os'],
                                version=missing['version'],
                                default_saidata=default_saidata,
                                repo_manager=repo_manager,
                                config=config,
                                providers=list(providers) if providers else None,
                                use_cache=use_cache,
                                verbose=verbose
                            )
                        
                        success = asyncio.run(create_file())
                        
                        if success:
                            created_count += 1
                            if not verbose:
                                click.echo(" ✓")
                            # Add created file to files list for processing
                            created_path = Path(missing['path'])
                            if created_path.exists():
                                files.append(created_path)
                        else:
                            if not verbose:
                                click.echo(" ✗")
                    
                    click.echo(f"\nCreated {created_count} of {len(missing_files)} OS-specific file(s)")
                    
                except Exception as e:
                    click.echo(f"Failed to load default.yaml: {e}", err=True)
            else:
                click.echo("Warning: default.yaml not found, cannot create OS-specific files")
        else:
            click.echo("\nNo missing OS-specific files found")
    
    if not files:
        click.echo("No files to process")
        return
    
    click.echo(f"\nProcessing {len(files)} saidata file(s)...\n")
    
    for file_path in files:
        backup_path = None
        try:
            # Extract OS information from file path
            os_info = extract_os_info(file_path)
            
            # Check if we should skip default.yaml
            if skip_default and os_info['is_default']:
                if verbose:
                    click.echo(f"Skipping {file_path.name} (--skip-default)")
                continue
            
            if verbose:
                click.echo(f"\n{'='*60}")
                click.echo(f"Processing: {file_path}")
                if os_info['is_default']:
                    click.echo(f"File type: default.yaml (OS-agnostic)")
                elif os_info['os'] and os_info['version']:
                    click.echo(f"OS context: {os_info['os']} {os_info['version']}")
            else:
                click.echo(f"Processing: {file_path.name}...", nl=False)
            
            # Load existing saidata
            saidata = _load_saidata(file_path)
            
            # Create backup if requested and not check-only
            if backup and not check_only:
                backup_path = _create_backup(file_path, backup_dir)
                if verbose:
                    click.echo(f"Created backup: {backup_path}")
            
            # Refresh versions
            async def run_refresh():
                return await _refresh_versions(
                    saidata=saidata,
                    config=config,
                    os_context=os_info,
                    target_providers=list(providers) if providers else None,
                    use_cache=use_cache,
                    verbose=verbose,
                )
            
            result = asyncio.run(run_refresh())
            
            # Interactive mode: show diff and prompt before saving
            should_save = True
            if interactive and not check_only and result.updated_packages > 0:
                if verbose:
                    click.echo(f"\n{'='*60}")
                _display_interactive_diff(result)
                should_save = click.confirm(f"Apply changes to {file_path.name}?")
                if not should_save:
                    if verbose:
                        click.echo("Changes not applied.")
            
            # Save if not check-only and updates were made and user confirmed (if interactive)
            if not check_only and result.updated_packages > 0 and should_save:
                _save_saidata(saidata, file_path, backup_path)
                if verbose:
                    click.echo(f"Saved updated saidata to: {file_path}")
            
            # Store result with file path
            results.append((file_path, result, None))
            
            if not verbose:
                if result.updated_packages > 0:
                    click.echo(f" ✓ {result.updated_packages} update(s)")
                else:
                    click.echo(" ✓ up-to-date")
        
        except Exception as e:
            error_msg = str(e)
            results.append((file_path, None, error_msg))
            
            if not verbose:
                click.echo(f" ✗ failed")
            
            if verbose:
                click.echo(f"✗ Failed to process {file_path}: {error_msg}", err=True)
                import traceback
                traceback.print_exc()
            
            # Restore from backup if operation failed
            if backup_path and backup_path.exists() and not check_only:
                try:
                    shutil.copy2(backup_path, file_path)
                    if verbose:
                        click.echo(f"Restored from backup: {backup_path}")
                except Exception as restore_error:
                    if verbose:
                        click.echo(f"Failed to restore from backup: {restore_error}", err=True)
    
    # Display summary
    _display_multi_file_results(results, check_only, verbose)


if __name__ == "__main__":
    refresh_versions()
