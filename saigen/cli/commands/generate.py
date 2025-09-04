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
    
    # Full implementation
    try:
        from ...core.generation_engine import GenerationEngine
        from ...models.generation import GenerationRequest, LLMProvider
        
        # Initialize generation engine
        engine = GenerationEngine(config)
        
        # Determine output path
        if not output:
            output = Path(f"{software_name}.yaml")
        
        # Check if file exists and force flag
        if output.exists() and not force:
            click.echo(f"Error: Output file '{output}' already exists. Use --force to overwrite.", err=True)
            ctx.exit(1)
        
        # Determine LLM provider
        if llm_provider:
            try:
                provider_enum = LLMProvider(llm_provider)
            except ValueError:
                click.echo(f"Error: Invalid LLM provider '{llm_provider}'. Available: {[p.value for p in LLMProvider]}", err=True)
                ctx.exit(1)
        else:
            # Use default from config or fallback
            if hasattr(config, 'llm_providers') and config.llm_providers:
                # Get first available provider from config
                first_provider = next(iter(config.llm_providers.keys()), 'openai')
                try:
                    provider_enum = LLMProvider(first_provider)
                except ValueError:
                    provider_enum = LLMProvider.OPENAI  # Fallback
            else:
                provider_enum = LLMProvider.OPENAI  # Fallback
        
        # Create generation request
        target_providers_list = list(providers) if providers else []
        request = GenerationRequest(
            software_name=software_name,
            target_providers=target_providers_list,
            llm_provider=provider_enum,
            use_rag=not no_rag,
            user_hints=None,
            existing_saidata=None
        )
        
        if verbose:
            click.echo(f"Generating saidata for: {software_name}")
            click.echo(f"LLM Provider: {provider_enum.value}")
            click.echo(f"Target providers: {request.target_providers}")
            click.echo(f"RAG enabled: {request.use_rag}")
            click.echo(f"Output file: {output}")
        
        # Generate saidata
        import asyncio
        
        async def run_generation():
            result = await engine.generate_saidata(request)
            if result.success:
                await engine.save_saidata(result.saidata, output)
            return result
        
        result = asyncio.run(run_generation())
        
        if result.success:
            
            click.echo(f"✓ Successfully generated saidata for '{software_name}'")
            click.echo(f"✓ Saved to: {output}")
            
            if verbose:
                click.echo(f"Generation time: {result.generation_time:.2f}s")
                click.echo(f"LLM provider used: {result.llm_provider_used}")
                if result.tokens_used:
                    click.echo(f"Tokens used: {result.tokens_used}")
                if result.cost_estimate:
                    click.echo(f"Estimated cost: ${result.cost_estimate:.4f}")
                if result.repository_sources_used:
                    click.echo(f"Repository sources: {', '.join(result.repository_sources_used)}")
            
            # Show warnings if any
            if result.warnings:
                click.echo("\nWarnings:")
                for warning in result.warnings:
                    click.echo(f"  - {warning}")
        
        else:
            click.echo(f"✗ Failed to generate saidata for '{software_name}'", err=True)
            
            if result.validation_errors:
                click.echo("Validation errors:", err=True)
                for error in result.validation_errors:
                    click.echo(f"  - {error.field}: {error.message}", err=True)
            
            ctx.exit(1)
            
    except Exception as e:
        click.echo(f"✗ Generation failed: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


if __name__ == '__main__':
    generate()