"""Main CLI entry point for saigen tool."""

import click
from pathlib import Path
from typing import Optional

from ..utils.config import get_config
from ..version import get_version


@click.group()
@click.option('--config', type=click.Path(exists=True, path_type=Path), 
              help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.version_option(version=get_version(), prog_name="saigen")
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], verbose: bool, dry_run: bool):
    """saigen - AI-powered saidata generation tool."""
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['verbose'] = verbose
    ctx.obj['dry_run'] = dry_run
    
    # Load configuration
    try:
        config_obj = get_config()
        ctx.obj['config'] = config_obj
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument('software_name')
@click.option('--llm-provider', help='LLM provider to use')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file path')
@click.option('--providers', multiple=True, help='Target providers for saidata')
@click.pass_context
def generate(ctx: click.Context, software_name: str, llm_provider: Optional[str], 
             output: Optional[Path], providers: tuple):
    """Generate saidata for a software package."""
    click.echo(f"Generating saidata for: {software_name}")
    # Implementation will be added in later tasks


@cli.command()
@click.option('--show', is_flag=True, help='Show current configuration')
@click.pass_context
def config(ctx: click.Context, show: bool):
    """Manage saigen configuration."""
    if show:
        config_obj = ctx.obj['config']
        masked_config = config_obj.get_masked_config()
        click.echo("Current configuration:")
        import yaml
        click.echo(yaml.dump(masked_config, default_flow_style=False))


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()