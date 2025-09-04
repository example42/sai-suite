"""Main CLI entry point for saigen tool."""

import click
from pathlib import Path
from typing import Optional
import logging

from ..utils.config import get_config_manager, get_config
from ..version import get_version
from .commands import validate, generate, config


@click.group()
@click.option('--config', type=click.Path(exists=True, path_type=Path), 
              help='Configuration file path')
@click.option('--llm-provider', help='LLM provider to use (openai, anthropic, ollama)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.version_option(version=get_version(), prog_name="saigen")
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], llm_provider: Optional[str], 
        verbose: bool, dry_run: bool):
    """saigen - AI-powered saidata generation tool.
    
    Generate, validate, and manage software metadata (saidata) files using AI
    and repository data. Supports multiple LLM providers and package repositories.
    """
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['llm_provider'] = llm_provider
    ctx.obj['verbose'] = verbose
    ctx.obj['dry_run'] = dry_run
    
    # Set up logging based on verbose flag
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # Load configuration
    try:
        config_manager = get_config_manager(config)
        config_obj = config_manager.get_config()
        ctx.obj['config'] = config_obj
        ctx.obj['config_manager'] = config_manager
        
        # Validate configuration
        issues = config_manager.validate_config()
        if issues and verbose:
            click.echo("Configuration issues found:", err=True)
            for issue in issues:
                click.echo(f"  - {issue}", err=True)
                
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        ctx.exit(1)


# Add commands to the CLI group
cli.add_command(validate)
cli.add_command(generate)
cli.add_command(config)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()