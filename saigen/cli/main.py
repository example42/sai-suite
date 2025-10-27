"""Main CLI entry point for saigen tool."""

from .commands.quality import quality
from .commands.index import index
from .repositories import repositories
from .commands.batch import batch
from .commands import cache, config, generate, refresh_versions, test, test_system, update, validate
from .commands.validate import validate_overrides
from ..version import get_version
from ..utils.config import get_config_manager
import logging
import warnings
from pathlib import Path
from typing import Optional

import click

# Suppress urllib3 SSL warnings on macOS
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL 1.1.1+")


@click.group()
@click.option(
    "--config", type=click.Path(exists=True, path_type=Path), help="Configuration file path"
)
@click.option("--llm-provider", help="LLM provider name from config (e.g., openai, ollama_qwen3)")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
@click.version_option(version=get_version(), prog_name="saigen")
@click.pass_context
def cli(
    ctx: click.Context,
    config: Optional[Path],
    llm_provider: Optional[str],
    verbose: bool,
    dry_run: bool,
):
    """saigen - AI-powered saidata generation tool.

    Generate, validate, and manage software metadata (saidata) files.

    \b
    Supports multiple LLM providers (OpenAI, Anthropic, Ollama, vLLM), with RAG info
    based on package repositories (apt, brew, npm, pypi, cargo, winget, and more) to
    handle different installation methods (packages, sources, binaries, scripts).
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["llm_provider"] = llm_provider
    ctx.obj["verbose"] = verbose
    ctx.obj["dry_run"] = dry_run

    # Set up logging based on verbose flag
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Load configuration
    try:
        config_manager = get_config_manager(config)
        config_obj = config_manager.get_config()
        ctx.obj["config"] = config_obj
        ctx.obj["config_manager"] = config_manager

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
cli.add_command(validate_overrides)
cli.add_command(generate)
cli.add_command(config)
cli.add_command(cache)
cli.add_command(test)
cli.add_command(update)
cli.add_command(refresh_versions)

# Add batch command

cli.add_command(batch)

# Add repositories command

cli.add_command(repositories)

# Add index command for RAG management

cli.add_command(index)

# Add quality command for advanced validation

cli.add_command(quality)

# Add test-system command for real system testing
cli.add_command(test_system)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
