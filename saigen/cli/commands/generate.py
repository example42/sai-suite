"""Generate command for saigen CLI."""

from pathlib import Path
from typing import Optional

import click


@click.command()
@click.argument('software_name')
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='Output file path (default: <software_name>.yaml)')
@click.option('--providers', multiple=True, 
              help='Target providers for saidata (e.g., apt, brew, winget)')
@click.option('--no-rag', is_flag=True, help='Disable RAG context injection')
@click.option('--force', is_flag=True, help='Overwrite existing files')
@click.pass_context
def generate(ctx: click.Context, software_name: str, output: Optional[Path], 
             providers: tuple, no_rag: bool, force: bool):
    """Generate saidata for a software package.
    
    Creates a comprehensive saidata YAML file by combining LLM knowledge
    with repository data and existing saidata examples.
    
    Examples:
        saigen generate nginx
        saigen generate --providers apt,brew --output custom.yaml nginx
        saigen generate --no-rag --dry-run postgresql
    """
    # Input validation for security
    if not software_name or not software_name.strip():
        raise click.BadParameter("Software name cannot be empty")
    
    # Sanitize software name (allow only alphanumeric, hyphens, underscores, dots)
    import re
    if not re.match(r'^[a-zA-Z0-9._-]+$', software_name):
        raise click.BadParameter("Software name contains invalid characters")
    
    config = ctx.obj['config']
    verbose = ctx.obj['verbose']
    dry_run = ctx.obj['dry_run']
    
    # Use global LLM provider if specified, otherwise use config default
    llm_provider = ctx.obj['llm_provider']
    
    if verbose:
        click.echo(f"Generating saidata for: {software_name}")
        click.echo(f"LLM Provider: {llm_provider or 'default'}")
        click.echo(f"Target providers: {list(providers) if providers else 'default'}")
        click.echo(f"RAG enabled: {not no_rag}")
        click.echo(f"Dry run: {dry_run}")
    
    if dry_run:
        click.echo(f"[DRY RUN] Would generate saidata for '{software_name}'")
        if output:
            click.echo(f"[DRY RUN] Would save to: {output}")
        else:
            click.echo(f"[DRY RUN] Would save to: {software_name}.yaml")
        
        # Show RAG status in dry run
        if not no_rag:
            try:
                from ...core.generation_engine import GenerationEngine
                engine = GenerationEngine(config)
                if engine.is_rag_available():
                    click.echo("[DRY RUN] RAG context would be used for enhanced generation")
                else:
                    click.echo("[DRY RUN] RAG not available - would use basic generation")
            except Exception:
                click.echo("[DRY RUN] Could not check RAG availability")
        
        return
    
    # Implementation will be added in later tasks
    click.echo(f"Generating saidata for: {software_name}")
    click.echo("Note: Full implementation will be added in subsequent tasks.")


if __name__ == '__main__':
    generate()