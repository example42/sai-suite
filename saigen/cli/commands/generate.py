"""Generate command for saigen CLI."""

from pathlib import Path
from typing import Optional

import click


@click.command()
@click.argument("software_name", required=False)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: hierarchical structure in configured output_directory)",
)
@click.option(
    "--providers",
    multiple=True,
    help="Target providers for saidata (e.g., apt, brew, winget, binary, source, script)",
)
@click.option("--no-rag", is_flag=True, help="Disable RAG context injection")
@click.option("--force", is_flag=True, help="Overwrite existing files")
@click.option(
    "--log-file",
    type=click.Path(path_type=Path),
    help="Log file path for detailed generation process logging (default: auto-generated)",
)
@click.pass_context
def generate(
    ctx: click.Context,
    software_name: str,
    output: Optional[Path],
    providers: tuple,
    no_rag: bool,
    force: bool,
    log_file: Optional[Path],
):
    """Generate saidata for a software package using 0.3 schema.

    Creates a comprehensive saidata YAML file using the latest schema format
    by combining LLM knowledge with repository data and existing saidata examples.

    \b
    Examples:

    • Basic generation\n
        saigen generate nginx

    • Target specific providers including new installation methods\n
        saigen generate --providers apt,brew,binary,source terraform

    • Generate with comprehensive logging\n
        saigen generate --log-file ./generation.json --verbose kubernetes

    • Dry run to preview generation output\n
        saigen generate --dry-run --verbose docker

    • Force overwrite with custom output\n
        saigen generate --force --output custom-nginx.yaml nginx
    """
    # Show help if software_name is missing
    if not software_name:
        click.echo(ctx.get_help())
        click.echo("\n" + "=" * 70)
        click.echo("ERROR: Missing required argument SOFTWARE_NAME")
        click.echo("=" * 70)
        ctx.exit(2)
    
    # Input validation for security
    if not software_name.strip():
        raise click.BadParameter("Software name cannot be empty")

    # Sanitize software name (allow only alphanumeric, hyphens, underscores, dots)
    import re

    if not re.match(r"^[a-zA-Z0-9._-]+$", software_name):
        raise click.BadParameter("Software name contains invalid characters")

    config = ctx.obj["config"]
    verbose = ctx.obj["verbose"]
    dry_run = ctx.obj["dry_run"]

    # Use global LLM provider if specified, otherwise use config default
    llm_provider = ctx.obj["llm_provider"]

    # Set up generation logging if requested
    generation_logger = None
    if log_file or not dry_run:  # Always log for actual generation
        if not log_file:
            # Auto-generate log filename
            from ...utils.generation_logger import create_generation_log_filename

            log_dir = Path.home() / ".saigen" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_filename = create_generation_log_filename(software_name)
            log_file = log_dir / log_filename

        if not dry_run:  # Only create logger for actual generation
            from ...utils.generation_logger import GenerationLogger

            generation_logger = GenerationLogger(log_file, software_name)

    if verbose:
        click.echo(f"Generating saidata for: {software_name}")
        click.echo(f"Schema version: 0.3")
        click.echo(f"LLM Provider: {llm_provider or 'default'}")
        click.echo(f"Target providers: {list(providers) if providers else 'default'}")
        click.echo(f"RAG enabled: {not no_rag}")

        # Show sample data configuration
        if not no_rag and config.rag.use_default_samples:
            sample_dir = config.rag.default_samples_directory
            if sample_dir and Path(sample_dir).exists():
                yaml_files = list(Path(sample_dir).glob("**/*.yaml")) + list(
                    Path(sample_dir).glob("**/*.yml")
                )
                click.echo(f"Sample data: {len(yaml_files)} files from {sample_dir}")
            else:
                click.echo("Sample data: Configured but directory not found")
        elif not no_rag:
            click.echo("Sample data: Not configured (use 'saigen config samples --auto-detect')")

        click.echo(f"Dry run: {dry_run}")

        # Show log file path
        if log_file:
            click.echo(f"Generation log: {log_file}")

    if dry_run:
        click.echo(f"[DRY RUN] Would generate saidata 0.3 for '{software_name}'")
        if output:
            click.echo(f"[DRY RUN] Would save to: {output}")
        else:
            click.echo(f"[DRY RUN] Would save to: {software_name}.yaml")

        if log_file:
            click.echo(f"[DRY RUN] Would log generation process to: {log_file}")

        # Show RAG status in dry run
        if not no_rag:
            try:
                from ...core.generation_engine import GenerationEngine

                engine = GenerationEngine(config)
                if engine.is_rag_available():
                    click.echo("[DRY RUN] RAG context would be used for enhanced generation")

                    # Show sample data status
                    if config.rag.use_default_samples:
                        sample_dir = config.rag.default_samples_directory
                        if sample_dir and Path(sample_dir).exists():
                            yaml_files = list(Path(sample_dir).glob("**/*.yaml")) + list(
                                Path(sample_dir).glob("**/*.yml")
                            )
                            click.echo(
                                f"[DRY RUN] Would use {
                                    len(yaml_files)} sample saidata files as examples")
                        else:
                            click.echo("[DRY RUN] Sample data configured but directory not found")
                    else:
                        click.echo(
                            "[DRY RUN] Sample data disabled - would use only repository data"
                        )
                else:
                    click.echo("[DRY RUN] RAG not available - would use basic generation")
            except Exception:
                click.echo("[DRY RUN] Could not check RAG availability")

        return

    # Full implementation
    try:
        from ...core.generation_engine import GenerationEngine
        from ...models.generation import GenerationRequest, LLMProvider

        # Initialize generation engine with logger
        engine = GenerationEngine(config)
        if generation_logger:
            engine.set_logger(generation_logger)

        # Determine output path
        if not output:
            # Use configured output_directory with hierarchical structure
            from ...utils.path_utils import get_hierarchical_output_path

            base_output_dir = config.generation.output_directory
            output = get_hierarchical_output_path(software_name, base_output_dir)

            # Create parent directories if they don't exist
            output.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists and force flag
        if output.exists() and not force:
            error_msg = f"Output file '{output}' already exists. Use --force to overwrite."
            if generation_logger:
                generation_logger.log_error(error_msg)
            click.echo(f"Error: {error_msg}", err=True)
            ctx.exit(1)

        # Determine LLM provider
        if llm_provider:
            # Validate that the provider exists in config
            if not config.llm_providers or llm_provider not in config.llm_providers:
                available = list(config.llm_providers.keys()) if config.llm_providers else []
                error_msg = (
                    f"Invalid LLM provider '{llm_provider}'. "
                    f"Available providers: {', '.join(available) if available else 'none configured'}"
                )
                if generation_logger:
                    generation_logger.log_error(error_msg)
                click.echo(f"Error: {error_msg}", err=True)
                ctx.exit(1)
            provider_name = llm_provider
        else:
            # Use default from config or fallback
            if hasattr(config, "llm_providers") and config.llm_providers:
                # Get first enabled provider from config
                first_provider = None
                for prov_name, provider_config in config.llm_providers.items():
                    if provider_config.enabled:
                        first_provider = prov_name
                        break

                if not first_provider:
                    # No enabled providers, use first one anyway
                    first_provider = next(iter(config.llm_providers.keys()), "openai")

                provider_name = first_provider
            else:
                provider_name = "openai"  # Fallback

        # Create generation request
        target_providers_list = list(providers) if providers else []
        request = GenerationRequest(
            software_name=software_name,
            target_providers=target_providers_list,
            llm_provider=provider_name,
            use_rag=not no_rag,
            user_hints=None,
            existing_saidata=None,
        )

        # Log the generation request
        if generation_logger:
            generation_logger.log_generation_request(request)

        if verbose:
            click.echo(f"Generating saidata for: {software_name}")
            click.echo(f"Schema version: 0.3")
            click.echo(f"LLM Provider: {provider_name}")
            click.echo(f"Target providers: {request.target_providers}")
            click.echo(f"RAG enabled: {request.use_rag}")
            click.echo(f"Output file: {output}")

        # Generate saidata
        import asyncio

        async def run_generation():
            result = await engine.generate_saidata(request)
            if result.success:
                # Get model name from the result
                model_name = engine._get_model_name(result.llm_provider_used)
                await engine.save_saidata(result.saidata, output, model_name=model_name)
            return result

        result = asyncio.run(run_generation())

        # Log final result
        if generation_logger:
            generation_logger.log_final_result(
                success=result.success,
                saidata=result.saidata if result.success else None,
                validation_errors=[f"{e.field}: {e.message}" for e in result.validation_errors]
                if result.validation_errors
                else None,
                output_file=output if result.success else None,
            )

        if result.success:
            click.echo(f"✓ Successfully generated saidata 0.3 for '{software_name}'")
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

            # Show log file location
            if generation_logger:
                click.echo(f"✓ Generation log saved to: {generation_logger.log_file_path}")
                if verbose:
                    summary = generation_logger.get_summary()
                    click.echo(
                        f"Log summary: {summary['llm_interactions_count']} LLM interactions, "
                        f"{summary['data_operations_count']} data operations, "
                        f"{summary['process_steps_count']} process steps"
                    )

            # Show warnings if any
            if result.warnings:
                click.echo("\nWarnings:")
                for warning in result.warnings:
                    click.echo(f"  - {warning}")
                    if generation_logger:
                        generation_logger.log_warning(warning)

        else:
            click.echo(f"✗ Failed to generate saidata for '{software_name}'", err=True)

            if result.validation_errors:
                click.echo("Validation errors:", err=True)
                for error in result.validation_errors:
                    click.echo(f"  - {error.field}: {error.message}", err=True)
                    if generation_logger:
                        generation_logger.log_error(f"{error.field}: {error.message}")

            # Show log file location even on failure
            if generation_logger:
                click.echo(f"Generation log saved to: {generation_logger.log_file_path}", err=True)

            ctx.exit(1)

    except Exception as e:
        if generation_logger:
            generation_logger.log_error(f"Generation failed: {e}")
            generation_logger.log_final_result(success=False, validation_errors=[str(e)])

        click.echo(f"✗ Generation failed: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()

        # Show log file location even on exception
        if generation_logger:
            click.echo(f"Generation log saved to: {generation_logger.log_file_path}", err=True)

        ctx.exit(1)


if __name__ == "__main__":
    generate()
