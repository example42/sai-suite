"""Batch command for saigen CLI."""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List

import click

from ...core.batch_engine import BatchGenerationEngine, SoftwareListParser
from ...core.generation_engine import GenerationEngine
from ...models.generation import LLMProvider


@click.command()
@click.option('--input-file', '-f', type=click.Path(exists=True, path_type=Path),
              help='Input file containing software names (one per line)')
@click.option('--software-list', '-s', multiple=True,
              help='Software names to process (can be specified multiple times)')
@click.option('--output-dir', '-o', type=click.Path(path_type=Path),
              help='Output directory for generated saidata files')
@click.option('--providers', multiple=True,
              help='Target providers for saidata 0.3 (e.g., apt, brew, binary, source, script)')
@click.option('--category-filter', '-c',
              help='Filter by category using regex pattern (e.g., "web|database")')
@click.option('--max-concurrent', '-j', type=int, default=3,
              help='Maximum number of concurrent generations (default: 3)')
@click.option('--no-rag', is_flag=True,
              help='Disable RAG context injection')
@click.option('--stop-on-error', is_flag=True,
              help='Stop processing on first error (default: continue on errors)')
@click.option('--force', is_flag=True,
              help='Overwrite existing files')
@click.option('--preview', is_flag=True,
              help='Preview what would be processed without generating')
@click.pass_context
def batch(ctx: click.Context, input_file: Optional[Path], software_list: tuple,
          output_dir: Optional[Path], providers: tuple, category_filter: Optional[str],
          max_concurrent: int, no_rag: bool, stop_on_error: bool, force: bool,
          preview: bool):
    """Generate saidata 0.3 for multiple software packages in batch.
    
    Process multiple software packages efficiently using parallel generation
    with the latest 0.3 schema format. Each generated file includes:
    
    🆕 NEW 0.3 FEATURES:
    • Multiple installation methods (sources, binaries, scripts)
    • URL templating with {{version}}, {{platform}}, {{architecture}}
    • Enhanced security metadata and checksum validation
    • Provider-specific configurations and overrides
    • Comprehensive compatibility matrices
    
    📊 BATCH PROCESSING:
    • Parallel generation with configurable concurrency
    • Category filtering for targeted generation
    • Progress tracking and error handling
    • Automatic file organization and naming
    
    Examples:
        # Generate 0.3 saidata from file list
        saigen batch -f software_list.txt -o output/
        
        # Generate with specific installation methods
        saigen batch -s nginx -s terraform --providers apt,brew,binary,source -o output/
        
        # Filter by category with parallel processing
        saigen batch -f web_tools.txt -c "database|cache" -j 5 -o output/
        
        # Preview what would be generated
        saigen batch -f software_list.txt --preview --verbose
        
        # Generate with enhanced security focus
        saigen batch -f security_tools.txt --providers binary,source -o secure/
    """
    config = ctx.obj['config']
    verbose = ctx.obj['verbose']
    dry_run = ctx.obj['dry_run'] or preview
    
    # Use global LLM provider if specified, otherwise use config default
    llm_provider_name = ctx.obj['llm_provider']
    if llm_provider_name:
        try:
            llm_provider = LLMProvider(llm_provider_name)
        except ValueError:
            raise click.BadParameter(f"Invalid LLM provider: {llm_provider_name}")
    else:
        # Use default from config or fallback
        if hasattr(config, 'llm_providers') and config.llm_providers:
            # Get first enabled provider from config
            first_provider = None
            for provider_name, provider_config in config.llm_providers.items():
                if provider_config.enabled:
                    first_provider = provider_name
                    break
            
            if not first_provider:
                # No enabled providers, use first one anyway
                first_provider = next(iter(config.llm_providers.keys()), 'openai')
            
            try:
                llm_provider = LLMProvider(first_provider)
            except ValueError:
                llm_provider = LLMProvider.OPENAI  # Fallback
        else:
            llm_provider = LLMProvider.OPENAI  # Fallback
    
    # Validate input sources
    if not input_file and not software_list:
        raise click.BadParameter("Must specify either --input-file or --software-list")
    
    if input_file and software_list:
        raise click.BadParameter("Cannot specify both --input-file and --software-list")
    
    # Validate concurrency
    if max_concurrent < 1 or max_concurrent > 20:
        raise click.BadParameter("max-concurrent must be between 1 and 20")
    
    # Get software list
    try:
        if input_file:
            software_names = SoftwareListParser.parse_file(input_file, category_filter)
            if verbose:
                click.echo(f"Loaded {len(software_names)} software packages from {input_file}")
                if category_filter:
                    click.echo(f"Applied category filter: {category_filter}")
        else:
            software_names = list(software_list)
            if verbose:
                click.echo(f"Processing {len(software_names)} software packages from command line")
        
        if not software_names:
            click.echo("No software packages found to process", err=True)
            ctx.exit(1)
        
        # Validate software names
        valid_names = SoftwareListParser.validate_software_names(software_names)
        if len(valid_names) != len(software_names):
            invalid_count = len(software_names) - len(valid_names)
            click.echo(f"Warning: {invalid_count} invalid software names were skipped", err=True)
        
        if not valid_names:
            click.echo("No valid software names found", err=True)
            ctx.exit(1)
        
        software_names = valid_names
        
    except Exception as e:
        click.echo(f"Error processing software list: {e}", err=True)
        ctx.exit(1)
    
    # Use configured output directory if not specified
    if not output_dir:
        output_dir = config.generation.output_directory
        if verbose:
            click.echo(f"Using configured output directory: {output_dir}")
    
    # Preview mode
    if preview:
        click.echo(f"Preview: Would process {len(software_names)} software packages (saidata 0.3)")
        click.echo(f"LLM Provider: {llm_provider.value}")
        click.echo(f"Target providers: {list(providers) if providers else 'default'}")
        click.echo(f"Max concurrent: {max_concurrent}")
        click.echo(f"RAG enabled: {not no_rag}")
        click.echo(f"Continue on error: {not stop_on_error}")
        click.echo(f"Output directory: {output_dir}")
        
        if verbose:
            click.echo("\nSoftware packages to process:")
            for i, name in enumerate(software_names[:20], 1):  # Show first 20
                click.echo(f"  {i:2d}. {name}")
            if len(software_names) > 20:
                click.echo(f"  ... and {len(software_names) - 20} more")
        
        return
    
    # Dry run mode
    if dry_run:
        click.echo(f"[DRY RUN] Would process {len(software_names)} software packages (saidata 0.3)")
        if output_dir:
            click.echo(f"[DRY RUN] Would save files to: {output_dir}")
        return
    
    # Validate output directory
    if output_dir:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            if not output_dir.is_dir():
                raise click.BadParameter(f"Output path is not a directory: {output_dir}")
        except Exception as e:
            raise click.BadParameter(f"Cannot create output directory: {e}")
        
        # Check for existing files if not forcing
        if not force:
            existing_files = []
            for name in software_names:
                output_file = output_dir / f"{name}.yaml"
                if output_file.exists():
                    existing_files.append(output_file)
            
            if existing_files:
                click.echo(f"Warning: {len(existing_files)} files already exist in output directory")
                if not click.confirm("Continue and overwrite existing files?"):
                    ctx.exit(0)
    
    # Initialize engines
    try:
        generation_engine = GenerationEngine(config)
        batch_engine = BatchGenerationEngine(generation_engine)
    except Exception as e:
        click.echo(f"Error initializing generation engines: {e}", err=True)
        ctx.exit(1)
    
    # Progress callback for CLI output
    def progress_callback(software_name: str, success: bool) -> None:
        if verbose:
            status = "✓" if success else "✗"
            click.echo(f"{status} {software_name}")
    
    # Run batch generation
    try:
        if verbose:
            click.echo(f"Starting batch generation with {max_concurrent} concurrent workers...")
        
        # Run async batch generation
        result = asyncio.run(
            batch_engine.generate_from_list(
                software_names=software_names,
                target_providers=list(providers) if providers else [],
                llm_provider=llm_provider,
                output_directory=output_dir,
                max_concurrent=max_concurrent,
                continue_on_error=not stop_on_error,
                use_rag=not no_rag,
                progress_callback=progress_callback if verbose else None
            )
        )
        
        # Display results
        click.echo(batch_engine.get_statistics_summary(result))
        
        # Exit with error code if any failures occurred
        if result.failed > 0:
            if stop_on_error:
                click.echo("Batch processing stopped due to errors", err=True)
                ctx.exit(1)
            else:
                click.echo(f"Batch processing completed with {result.failed} failures", err=True)
                ctx.exit(2)  # Different exit code for partial success
        else:
            click.echo("Batch processing completed successfully")
    
    except KeyboardInterrupt:
        click.echo("\nBatch processing interrupted by user", err=True)
        ctx.exit(130)
    except Exception as e:
        click.echo(f"Batch processing failed: {e}", err=True)
        ctx.exit(1)
    finally:
        # Cleanup
        try:
            asyncio.run(batch_engine.cleanup())
            asyncio.run(generation_engine.cleanup())
        except Exception:
            pass  # Ignore cleanup errors


if __name__ == '__main__':
    batch()