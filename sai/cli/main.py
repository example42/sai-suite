"""Main CLI entry point for sai tool."""

import click
from pathlib import Path
from typing import Optional

from ..utils.config import get_config


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


def main():
    """Main entry point."""
    cli()