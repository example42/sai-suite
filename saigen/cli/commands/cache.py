"""Cache management CLI commands."""

import asyncio
import click
from pathlib import Path
from typing import Optional, List
import logging

from saigen.repositories import RepositoryManager
from saigen.utils.config import get_config


logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def cache(ctx: click.Context):
    """Manage repository data cache.
    
    Commands for updating, clearing, and inspecting the repository cache.
    """
    pass


@cache.command()
@click.option('--repository', '-r', multiple=True, help='Specific repositories to update')
@click.option('--force', '-f', is_flag=True, help='Force update even if cache is valid')
@click.option('--platform', help='Filter repositories by platform')
@click.pass_context
def update(ctx: click.Context, repository: tuple, force: bool, platform: Optional[str]):
    """Update repository cache data.
    
    Downloads fresh package data from repositories and updates the cache.
    By default, only updates expired cache entries unless --force is used.
    """
    config = ctx.obj.get('config')
    if not config:
        click.echo("Error: Configuration not loaded", err=True)
        ctx.exit(1)
    
    verbose = ctx.obj.get('verbose', False)
    dry_run = ctx.obj.get('dry_run', False)
    
    if dry_run:
        click.echo("DRY RUN: Would update repository cache")
        if repository:
            click.echo(f"  Repositories: {', '.join(repository)}")
        if platform:
            click.echo(f"  Platform: {platform}")
        if force:
            click.echo("  Force update: Yes")
        return
    
    async def _update_cache():
        cache_dir = config.cache.directory
        # Use a default config directory - repositories have built-in configs
        config_dir = Path.home() / ".saigen" / "repository_configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        async with RepositoryManager(cache_dir, config_dir) as repo_manager:
            # Filter repositories if specified
            repo_names = list(repository) if repository else None
            
            if platform:
                # Get repositories for platform
                all_repos = repo_manager.get_all_repository_info(platform)
                if repo_names:
                    # Intersect with specified repositories
                    platform_repo_names = {repo.name for repo in all_repos}
                    repo_names = [name for name in repo_names if name in platform_repo_names]
                else:
                    repo_names = [repo.name for repo in all_repos]
            
            if verbose:
                if repo_names:
                    click.echo(f"Updating cache for repositories: {', '.join(repo_names)}")
                else:
                    click.echo("Updating cache for all repositories")
            
            # Update cache
            results = await repo_manager.update_cache(repo_names, force)
            
            # Report results
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            click.echo(f"Cache update completed: {success_count}/{total_count} repositories updated")
            
            if verbose:
                for repo_name, success in results.items():
                    status = "✓" if success else "✗"
                    click.echo(f"  {status} {repo_name}")
    
    try:
        asyncio.run(_update_cache())
    except Exception as e:
        click.echo(f"Error updating cache: {e}", err=True)
        ctx.exit(1)


@cache.command()
@click.option('--repository', '-r', multiple=True, help='Specific repositories to clear')
@click.option('--all', 'clear_all', is_flag=True, help='Clear all cache entries')
@click.confirmation_option(prompt='Are you sure you want to clear the cache?')
@click.pass_context
def clear(ctx: click.Context, repository: tuple, clear_all: bool):
    """Clear repository cache data.
    
    Removes cached package data. Use --all to clear everything,
    or specify repositories with --repository.
    """
    config = ctx.obj.get('config')
    if not config:
        click.echo("Error: Configuration not loaded", err=True)
        ctx.exit(1)
    
    verbose = ctx.obj.get('verbose', False)
    dry_run = ctx.obj.get('dry_run', False)
    
    if not clear_all and not repository:
        click.echo("Error: Must specify --all or --repository", err=True)
        ctx.exit(1)
    
    if dry_run:
        click.echo("DRY RUN: Would clear repository cache")
        if clear_all:
            click.echo("  Clear all cache entries")
        elif repository:
            click.echo(f"  Clear repositories: {', '.join(repository)}")
        return
    
    async def _clear_cache():
        cache_dir = config.cache.directory
        # Use a default config directory - repositories have built-in configs
        config_dir = Path.home() / ".saigen" / "repository_configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        async with RepositoryManager(cache_dir, config_dir) as repo_manager:
            if clear_all:
                removed_count = await repo_manager.clear_cache()
                click.echo(f"Cleared all cache entries: {removed_count} entries removed")
            else:
                repo_names = list(repository)
                removed_count = await repo_manager.clear_cache(repo_names)
                click.echo(f"Cleared cache for {len(repo_names)} repositories: {removed_count} entries removed")
                
                if verbose:
                    for repo_name in repo_names:
                        click.echo(f"  Cleared {repo_name}")
    
    try:
        asyncio.run(_clear_cache())
    except Exception as e:
        click.echo(f"Error clearing cache: {e}", err=True)
        ctx.exit(1)


@cache.command()
@click.pass_context
def cleanup(ctx: click.Context):
    """Clean up expired cache entries.
    
    Removes cache entries that have exceeded their TTL.
    """
    config = ctx.obj.get('config')
    if not config:
        click.echo("Error: Configuration not loaded", err=True)
        ctx.exit(1)
    
    verbose = ctx.obj.get('verbose', False)
    dry_run = ctx.obj.get('dry_run', False)
    
    if dry_run:
        click.echo("DRY RUN: Would clean up expired cache entries")
        return
    
    async def _cleanup_cache():
        cache_dir = config.cache.directory
        # Use a default config directory - repositories have built-in configs
        config_dir = Path.home() / ".saigen" / "repository_configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        async with RepositoryManager(cache_dir, config_dir) as repo_manager:
            stats = await repo_manager.cleanup_cache()
            
            expired_removed = stats.get('expired_removed', 0)
            click.echo(f"Cache cleanup completed: {expired_removed} expired entries removed")
    
    try:
        asyncio.run(_cleanup_cache())
    except Exception as e:
        click.echo(f"Error cleaning up cache: {e}", err=True)
        ctx.exit(1)


@cache.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed statistics')
@click.pass_context
def status(ctx: click.Context, detailed: bool):
    """Show cache status and statistics.
    
    Displays information about cached repository data including
    entry counts, sizes, and expiration status.
    """
    config = ctx.obj.get('config')
    if not config:
        click.echo("Error: Configuration not loaded", err=True)
        ctx.exit(1)
    
    async def _show_status():
        cache_dir = config.cache.directory
        # Use a default config directory - repositories have built-in configs
        config_dir = Path.home() / ".saigen" / "repository_configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        async with RepositoryManager(cache_dir, config_dir) as repo_manager:
            stats = await repo_manager.get_cache_stats()
            
            # Basic statistics
            click.echo("Cache Status:")
            click.echo(f"  Total entries: {stats.get('total_entries', 0)}")
            click.echo(f"  Expired entries: {stats.get('expired_entries', 0)}")
            click.echo(f"  Total packages: {stats.get('total_packages', 0):,}")
            
            # Size information
            total_size = stats.get('total_size_bytes', 0)
            if total_size > 0:
                if total_size > 1024 * 1024 * 1024:  # GB
                    size_str = f"{total_size / (1024 * 1024 * 1024):.1f} GB"
                elif total_size > 1024 * 1024:  # MB
                    size_str = f"{total_size / (1024 * 1024):.1f} MB"
                else:  # KB
                    size_str = f"{total_size / 1024:.1f} KB"
                click.echo(f"  Total cache size: {size_str}")
            
            # Time information
            if stats.get('oldest_entry'):
                click.echo(f"  Oldest entry: {stats['oldest_entry']}")
            if stats.get('newest_entry'):
                click.echo(f"  Newest entry: {stats['newest_entry']}")
            
            # Repository breakdown
            repositories = stats.get('repositories', {})
            if repositories and detailed:
                click.echo("\nRepository Breakdown:")
                for repo_name, repo_stats in repositories.items():
                    entries = repo_stats.get('entries', 0)
                    packages = repo_stats.get('packages', 0)
                    expired = repo_stats.get('expired', 0)
                    
                    status_indicator = "⚠️" if expired > 0 else "✓"
                    click.echo(f"  {status_indicator} {repo_name}: {entries} entries, {packages:,} packages")
                    if expired > 0:
                        click.echo(f"    ({expired} expired)")
            elif repositories:
                click.echo(f"\nRepositories cached: {len(repositories)}")
    
    try:
        asyncio.run(_show_status())
    except Exception as e:
        click.echo(f"Error getting cache status: {e}", err=True)
        ctx.exit(1)