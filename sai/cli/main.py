"""Main CLI entry point for sai tool."""

import click
from pathlib import Path
from typing import Optional, Dict, List
from collections import Counter, defaultdict

from ..utils.config import get_config
from ..providers.loader import ProviderLoader


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path), 
              help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], verbose: bool, dry_run: bool):
    """SAI - Software Automation and Installation CLI tool."""
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store global options in context
    ctx.obj['config_path'] = config
    ctx.obj['verbose'] = verbose
    ctx.obj['dry_run'] = dry_run
    
    # Load configuration
    try:
        sai_config = get_config()
        ctx.obj['sai_config'] = sai_config
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.pass_context
def version(ctx: click.Context):
    """Show version information."""
    from .. import __version__
    click.echo(f"sai version {__version__}")


@cli.command()
@click.pass_context
def config_show(ctx: click.Context):
    """Show current configuration."""
    config = ctx.obj['sai_config']
    
    click.echo("SAI Configuration:")
    click.echo(f"  Config Version: {config.config_version}")
    click.echo(f"  Log Level: {config.log_level}")
    click.echo(f"  Cache Enabled: {config.cache_enabled}")
    click.echo(f"  Cache Directory: {config.cache_directory}")
    click.echo(f"  Default Provider: {config.default_provider or 'None'}")
    
    click.echo("\nSaidata Paths:")
    for i, path in enumerate(config.saidata_paths, 1):
        exists = "✓" if Path(path).exists() else "✗"
        click.echo(f"  {i}. {path} {exists}")
    
    click.echo("\nProvider Paths:")
    for i, path in enumerate(config.provider_paths, 1):
        exists = "✓" if Path(path).exists() else "✗"
        click.echo(f"  {i}. {path} {exists}")


@cli.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed statistics')
@click.option('--by-type', '-t', is_flag=True, help='Group statistics by provider type')
@click.option('--by-platform', '-p', is_flag=True, help='Group statistics by platform')
@click.option('--actions-only', '-a', is_flag=True, help='Show only action statistics')
@click.pass_context
def stats(ctx: click.Context, detailed: bool, by_type: bool, by_platform: bool, actions_only: bool):
    """Show statistics about providers and actions."""
    try:
        # Load all providers
        loader = ProviderLoader()
        providers = loader.load_all_providers()
        
        if not providers:
            click.echo("No providers found.", err=True)
            return
        
        # Basic statistics
        total_providers = len(providers)
        
        # Collect statistics
        provider_types = Counter()
        platforms = Counter()
        actions = Counter()
        capabilities = Counter()
        provider_actions = defaultdict(list)
        
        for name, provider_data in providers.items():
            provider_info = provider_data.provider
            
            # Count by type
            provider_types[provider_info.type] += 1
            
            # Count by platforms
            for platform in provider_info.platforms:
                platforms[platform] += 1
            
            # Count capabilities/actions
            for capability in provider_info.capabilities:
                capabilities[capability] += 1
                actions[capability] += 1
                provider_actions[capability].append(name)
        
        # Display statistics
        if not actions_only:
            click.echo("🔧 SAI Provider & Action Statistics")
            click.echo("=" * 40)
            
            click.echo(f"\n📊 Overview:")
            click.echo(f"  Total Providers: {total_providers}")
            click.echo(f"  Unique Actions: {len(actions)}")
            click.echo(f"  Total Action Implementations: {sum(actions.values())}")
            
            if by_type:
                click.echo(f"\n🏷️  Providers by Type:")
                for ptype, count in provider_types.most_common():
                    percentage = (count / total_providers) * 100
                    click.echo(f"  {ptype:15} {count:3d} ({percentage:5.1f}%)")
            
            if by_platform:
                click.echo(f"\n🖥️  Platform Support:")
                for platform, count in platforms.most_common():
                    percentage = (count / total_providers) * 100
                    click.echo(f"  {platform:10} {count:3d} providers ({percentage:5.1f}%)")
        
        # Action statistics
        click.echo(f"\n⚡ Action Statistics:")
        click.echo(f"{'Action':<15} {'Providers':<10} {'Coverage':<10}")
        click.echo("-" * 35)
        
        for action, count in actions.most_common():
            percentage = (count / total_providers) * 100
            click.echo(f"{action:<15} {count:<10} {percentage:5.1f}%")
        
        if detailed:
            click.echo(f"\n📋 Detailed Action Coverage:")
            for action in sorted(actions.keys()):
                count = actions[action]
                percentage = (count / total_providers) * 100
                click.echo(f"\n{action} ({count} providers, {percentage:.1f}% coverage):")
                
                # Group providers by type for this action
                action_providers = provider_actions[action]
                provider_by_type = defaultdict(list)
                
                for provider_name in action_providers:
                    provider_type = providers[provider_name].provider.type
                    provider_by_type[provider_type].append(provider_name)
                
                for ptype in sorted(provider_by_type.keys()):
                    provider_list = ", ".join(sorted(provider_by_type[ptype]))
                    click.echo(f"  {ptype}: {provider_list}")
        
        # Most/least common actions
        if not actions_only:
            click.echo(f"\n🏆 Most Common Actions:")
            for action, count in actions.most_common(5):
                percentage = (count / total_providers) * 100
                click.echo(f"  {action:<12} {count:3d} providers ({percentage:5.1f}%)")
            
            click.echo(f"\n🔍 Least Common Actions:")
            for action, count in actions.most_common()[-5:]:
                percentage = (count / total_providers) * 100
                click.echo(f"  {action:<12} {count:3d} providers ({percentage:5.1f}%)")
        
        # Provider type breakdown
        if not actions_only and not by_type:
            click.echo(f"\n🏷️  Provider Types:")
            for ptype, count in provider_types.most_common():
                percentage = (count / total_providers) * 100
                click.echo(f"  {ptype:<15} {count:3d} ({percentage:5.1f}%)")
        
    except Exception as e:
        click.echo(f"Error loading provider statistics: {e}", err=True)
        if ctx.obj.get('verbose'):
            import traceback
            traceback.print_exc()


def main():
    """Main entry point."""
    cli()