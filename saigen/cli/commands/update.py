"""Update command for saigen CLI."""

import asyncio
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import click
import yaml


@click.command()
@click.argument('saidata_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='Output file path (default: overwrite input file)')
@click.option('--backup/--no-backup', default=True,
              help='Create backup of original file (default: enabled)')
@click.option('--backup-dir', type=click.Path(path_type=Path),
              help='Directory for backup files (default: same as input file)')
@click.option('--force-update', is_flag=True,
              help='Regenerate the file completely, ignoring existing content')
@click.option('--merge-strategy', 
              type=click.Choice(['preserve', 'enhance', 'replace'], case_sensitive=False),
              default='enhance',
              help='Strategy for handling conflicts (default: enhance)')
@click.option('--providers', multiple=True, 
              help='Target providers for updated saidata (e.g., apt, brew, winget)')
@click.option('--no-rag', is_flag=True, help='Disable RAG context injection')
@click.option('--interactive', is_flag=True,
              help='Prompt for conflict resolution interactively')
@click.pass_context
def update(ctx: click.Context, saidata_file: Path, output: Optional[Path], 
           backup: bool, backup_dir: Optional[Path], force_update: bool,
           merge_strategy: str, providers: tuple, no_rag: bool, interactive: bool):
    """Update existing saidata file with new information.
    
    Enhances existing saidata files by combining current content with fresh
    data from LLMs and repositories. Preserves manual customizations while
    adding new information.
    
    Examples:
        saigen update nginx.yaml
        saigen update --force-update --output nginx-v2.yaml nginx.yaml
        saigen update --merge-strategy preserve --interactive nginx.yaml
    """
    # Handle both test context and real context
    if ctx.obj is None:
        ctx.obj = {}
    
    config = ctx.obj.get('config', {})
    verbose = ctx.obj.get('verbose', False)
    dry_run = ctx.obj.get('dry_run', False)
    
    # Use global LLM provider if specified, otherwise use config default
    llm_provider = ctx.obj.get('llm_provider')
    
    if verbose:
        click.echo(f"Updating saidata file: {saidata_file}")
        click.echo(f"Force update: {force_update}")
        click.echo(f"Merge strategy: {merge_strategy}")
        click.echo(f"Create backup: {backup}")
        click.echo(f"Interactive mode: {interactive}")
        click.echo(f"Dry run: {dry_run}")
    
    if dry_run:
        click.echo(f"[DRY RUN] Would update saidata file: {saidata_file}")
        if output:
            click.echo(f"[DRY RUN] Would save to: {output}")
        else:
            click.echo(f"[DRY RUN] Would overwrite: {saidata_file}")
        
        if backup:
            backup_path = _get_backup_path(saidata_file, backup_dir)
            click.echo(f"[DRY RUN] Would create backup: {backup_path}")
        
        click.echo(f"[DRY RUN] Would use merge strategy: {merge_strategy}")
        return
    
    # Full implementation
    try:
        from ...core.generation_engine import GenerationEngine
        from ...core.update_engine import UpdateEngine
        from ...models.generation import GenerationRequest, LLMProvider, GenerationMode
        from ...models.saidata import SaiData
        
        # Load existing saidata
        existing_saidata = _load_existing_saidata(saidata_file)
        
        if verbose:
            click.echo(f"Loaded existing saidata: {existing_saidata.metadata.name}")
        
        # Create backup if requested
        if backup:
            backup_path = _create_backup(saidata_file, backup_dir)
            if verbose:
                click.echo(f"Created backup: {backup_path}")
        
        # Initialize engines
        generation_engine = GenerationEngine(config)
        update_engine = UpdateEngine(config, generation_engine)
        
        # Determine output path
        output_path = output or saidata_file
        
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
                first_provider = next(iter(config.llm_providers.keys()), 'openai')
                try:
                    provider_enum = LLMProvider(first_provider)
                except ValueError:
                    provider_enum = LLMProvider.OPENAI
            else:
                provider_enum = LLMProvider.OPENAI
        
        # Create update request
        target_providers_list = list(providers) if providers else []
        
        async def run_update():
            if force_update:
                # Force update: regenerate completely
                request = GenerationRequest(
                    software_name=existing_saidata.metadata.name,
                    target_providers=target_providers_list,
                    llm_provider=provider_enum,
                    use_rag=not no_rag,
                    generation_mode=GenerationMode.CREATE,
                    existing_saidata=None  # Don't use existing data for force update
                )
                
                if verbose:
                    click.echo("Performing force update (complete regeneration)")
                
                return await generation_engine.generate_saidata(request)
                
            else:
                # Smart update: merge with existing data
                if verbose:
                    click.echo(f"Performing smart update with merge strategy: {merge_strategy}")
                
                return await update_engine.update_saidata(
                    existing_saidata=existing_saidata,
                    target_providers=target_providers_list,
                    llm_provider=provider_enum,
                    use_rag=not no_rag,
                    merge_strategy=merge_strategy,
                    interactive=interactive
                )
        
        result = asyncio.run(run_update())
        
        if result.success:
            # Save updated saidata
            async def save_result():
                await generation_engine.save_saidata(result.saidata, output_path)
            
            asyncio.run(save_result())
            
            click.echo(f"✓ Successfully updated saidata file")
            click.echo(f"✓ Saved to: {output_path}")
            
            if verbose:
                click.echo(f"Update time: {result.generation_time:.2f}s")
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
            click.echo(f"✗ Failed to update saidata file", err=True)
            
            if result.validation_errors:
                click.echo("Validation errors:", err=True)
                for error in result.validation_errors:
                    click.echo(f"  - {error.field}: {error.message}", err=True)
            
            # Restore from backup if update failed and backup was created
            if backup and backup_path.exists():
                if click.confirm("Update failed. Restore from backup?"):
                    shutil.copy2(backup_path, saidata_file)
                    click.echo(f"Restored from backup: {backup_path}")
            
            ctx.exit(1)
            
    except Exception as e:
        click.echo(f"✗ Update failed: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        
        # Restore from backup if update failed and backup was created
        if backup and 'backup_path' in locals() and backup_path.exists():
            if click.confirm("Update failed. Restore from backup?"):
                shutil.copy2(backup_path, saidata_file)
                click.echo(f"Restored from backup: {backup_path}")
        
        ctx.exit(1)


def _load_existing_saidata(file_path: Path) -> 'SaiData':
    """Load existing saidata from file.
    
    Args:
        file_path: Path to saidata file
        
    Returns:
        SaiData instance
        
    Raises:
        click.ClickException: If file cannot be loaded
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        from ...models.saidata import SaiData
        return SaiData(**data)
        
    except yaml.YAMLError as e:
        raise click.ClickException(f"Invalid YAML in {file_path}: {e}")
    except Exception as e:
        raise click.ClickException(f"Failed to load {file_path}: {e}")


def _get_backup_path(original_path: Path, backup_dir: Optional[Path] = None) -> Path:
    """Get backup file path.
    
    Args:
        original_path: Original file path
        backup_dir: Directory for backup (optional)
        
    Returns:
        Backup file path
    """
    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_name = f"{original_path.stem}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}{original_path.suffix}"
        return backup_dir / backup_name
    else:
        backup_name = f"{original_path.stem}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}{original_path.suffix}"
        return original_path.parent / backup_name


def _create_backup(original_path: Path, backup_dir: Optional[Path] = None) -> Path:
    """Create backup of original file.
    
    Args:
        original_path: Original file path
        backup_dir: Directory for backup (optional)
        
    Returns:
        Backup file path
        
    Raises:
        click.ClickException: If backup creation fails
    """
    try:
        backup_path = _get_backup_path(original_path, backup_dir)
        shutil.copy2(original_path, backup_path)
        return backup_path
        
    except Exception as e:
        raise click.ClickException(f"Failed to create backup: {e}")


if __name__ == '__main__':
    update()