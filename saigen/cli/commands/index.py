"""CLI commands for RAG indexing management."""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...core.generation_engine import GenerationEngine
from ...repositories.cache import RepositoryCache
from ...repositories.manager import RepositoryManager
from ...utils.config import get_config
from ...utils.errors import RAGError


logger = logging.getLogger(__name__)
console = Console()


@click.group()
def index():
    """Manage RAG (Retrieval-Augmented Generation) indices for semantic search."""
    pass


@index.command()
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file path"
)
@click.option(
    "--force",
    is_flag=True,
    help="Force rebuild even if indices exist"
)
@click.option(
    "--repositories",
    multiple=True,
    help="Specific repositories to index (default: all cached repositories)"
)
@click.option(
    "--saidata-dir",
    type=click.Path(exists=True, path_type=Path),
    help="Directory containing saidata files to index"
)
async def rebuild(
    config_file: Optional[Path],
    force: bool,
    repositories: tuple,
    saidata_dir: Optional[Path]
):
    """Rebuild RAG indices from repository data and existing saidata files."""
    try:
        # Load configuration
        config = get_config()
        
        # Initialize generation engine
        engine = GenerationEngine(config.model_dump())
        
        if not engine.is_rag_available():
            console.print("[red]RAG functionality is not available. Install with: pip install sai[rag][/red]")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Rebuild package index if repository data available
            packages_task = progress.add_task("Loading repository data...", total=None)
            
            try:
                # Initialize repository cache
                cache_dir = Path(config.cache.directory).expanduser()
                cache = RepositoryCache(cache_dir)
                
                # Get cached repository data
                cache_stats = await cache.get_cache_stats()
                if cache_stats["total_packages"] > 0:
                    progress.update(packages_task, description="Indexing repository packages...")
                    
                    # For now, we'll need to implement a way to get all cached packages
                    # This is a placeholder - in a real implementation, we'd iterate through cache entries
                    console.print(f"[yellow]Found {cache_stats['total_packages']} cached packages across {len(cache_stats['repositories'])} repositories[/yellow]")
                    
                    # Note: Repository package extraction from cache requires implementation
                    # This would involve iterating through cached repository data
                    # and converting to RepositoryPackage objects for indexing
                    console.print("[yellow]Repository package indexing requires cache extraction implementation[/yellow]")
                    
                    progress.update(packages_task, description="Repository indexing completed")
                else:
                    progress.update(packages_task, description="No repository data found in cache")
                    console.print("[yellow]No repository data found. Run 'saigen repositories update' first.[/yellow]")
                
            except Exception as e:
                progress.update(packages_task, description=f"Repository indexing failed: {e}")
                logger.error(f"Failed to index repository data: {e}")
            
            # Rebuild saidata index if saidata files available
            if saidata_dir:
                saidata_task = progress.add_task("Indexing saidata files...", total=None)
                
                try:
                    # Find all saidata files
                    saidata_files = []
                    for pattern in ["*.yaml", "*.yml"]:
                        saidata_files.extend(saidata_dir.glob(f"**/{pattern}"))
                    
                    if saidata_files:
                        progress.update(saidata_task, description=f"Indexing {len(saidata_files)} saidata files...")
                        success = await engine.index_saidata_files(saidata_files)
                        
                        if success:
                            progress.update(saidata_task, description=f"Successfully indexed {len(saidata_files)} saidata files")
                            console.print(f"[green]Indexed {len(saidata_files)} saidata files[/green]")
                        else:
                            progress.update(saidata_task, description="Saidata indexing failed")
                            console.print("[red]Failed to index saidata files[/red]")
                    else:
                        progress.update(saidata_task, description="No saidata files found")
                        console.print(f"[yellow]No saidata files found in {saidata_dir}[/yellow]")
                        
                except Exception as e:
                    progress.update(saidata_task, description=f"Saidata indexing failed: {e}")
                    logger.error(f"Failed to index saidata files: {e}")
        
        # Show final stats
        stats = await engine.get_rag_stats()
        if stats:
            console.print("\n[bold]RAG Index Statistics:[/bold]")
            console.print(f"Package index: {'✓' if stats['package_index_available'] else '✗'} ({stats['package_count']} packages)")
            console.print(f"Saidata index: {'✓' if stats['saidata_index_available'] else '✗'} ({stats['saidata_count']} files)")
            console.print(f"Total index size: {stats['index_size_bytes'] / 1024 / 1024:.1f} MB")
            console.print(f"Model: {stats['model_name']}")
        
        await engine.cleanup()
        
    except Exception as e:
        console.print(f"[red]Error rebuilding indices: {e}[/red]")
        logger.error(f"Index rebuild failed: {e}")


@index.command()
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file path"
)
async def status(config_file: Optional[Path]):
    """Show RAG index status and statistics."""
    try:
        # Load configuration
        config = get_config()
        
        # Initialize generation engine
        engine = GenerationEngine(config.model_dump())
        
        if not engine.is_rag_available():
            console.print("[red]RAG functionality is not available. Install with: pip install sai[rag][/red]")
            return
        
        # Get RAG statistics
        stats = await engine.get_rag_stats()
        
        if not stats:
            console.print("[yellow]No RAG indices found[/yellow]")
            return
        
        # Create status table
        table = Table(title="RAG Index Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Count", justify="right")
        table.add_column("Details")
        
        # Package index status
        pkg_status = "Available" if stats['package_index_available'] else "Not Available"
        pkg_style = "green" if stats['package_index_available'] else "red"
        table.add_row(
            "Package Index",
            f"[{pkg_style}]{pkg_status}[/{pkg_style}]",
            str(stats['package_count']),
            f"Repository packages for semantic search"
        )
        
        # Saidata index status
        sai_status = "Available" if stats['saidata_index_available'] else "Not Available"
        sai_style = "green" if stats['saidata_index_available'] else "red"
        table.add_row(
            "Saidata Index",
            f"[{sai_style}]{sai_status}[/{sai_style}]",
            str(stats['saidata_count']),
            f"Existing saidata files for examples"
        )
        
        # Model information
        table.add_row(
            "Embedding Model",
            "[blue]Loaded[/blue]",
            "-",
            stats['model_name']
        )
        
        # Storage information
        size_mb = stats['index_size_bytes'] / 1024 / 1024
        table.add_row(
            "Storage Size",
            "[blue]Active[/blue]",
            f"{size_mb:.1f} MB",
            "Total index storage"
        )
        
        console.print(table)
        
        # Last updated information
        if stats.get('last_updated'):
            console.print(f"\n[dim]Last updated: {stats['last_updated']}[/dim]")
        
        await engine.cleanup()
        
    except Exception as e:
        console.print(f"[red]Error getting index status: {e}[/red]")
        logger.error(f"Index status failed: {e}")


@index.command()
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file path"
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt"
)
async def clear(config_file: Optional[Path], confirm: bool):
    """Clear all RAG indices."""
    try:
        if not confirm:
            if not click.confirm("This will delete all RAG indices. Continue?"):
                console.print("[yellow]Operation cancelled[/yellow]")
                return
        
        # Load configuration
        config = get_config()
        
        # Initialize generation engine
        engine = GenerationEngine(config.model_dump())
        
        if not engine.is_rag_available():
            console.print("[red]RAG functionality is not available[/red]")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Clearing RAG indices...", total=None)
            
            success = await engine.clear_rag_indices()
            
            if success:
                progress.update(task, description="RAG indices cleared successfully")
                console.print("[green]All RAG indices have been cleared[/green]")
            else:
                progress.update(task, description="Failed to clear RAG indices")
                console.print("[red]Failed to clear RAG indices[/red]")
        
        await engine.cleanup()
        
    except Exception as e:
        console.print(f"[red]Error clearing indices: {e}[/red]")
        logger.error(f"Index clear failed: {e}")


@index.command()
@click.argument("query")
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file path"
)
@click.option(
    "--limit",
    default=5,
    help="Maximum number of results to show"
)
@click.option(
    "--min-score",
    default=0.3,
    help="Minimum similarity score (0.0-1.0)"
)
async def search(
    query: str,
    config_file: Optional[Path],
    limit: int,
    min_score: float
):
    """Search for similar packages using semantic search."""
    try:
        # Load configuration
        config = get_config()
        
        # Initialize generation engine
        engine = GenerationEngine(config.model_dump())
        
        if not engine.is_rag_available():
            console.print("[red]RAG functionality is not available. Install with: pip install sai[rag][/red]")
            return
        
        console.print(f"[blue]Searching for packages similar to: {query}[/blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Searching...", total=None)
            
            # Perform semantic search
            similar_packages = await engine.rag_indexer.search_similar_packages(
                query=query,
                limit=limit,
                min_score=min_score
            )
            
            progress.update(task, description=f"Found {len(similar_packages)} results")
        
        if not similar_packages:
            console.print("[yellow]No similar packages found[/yellow]")
            return
        
        # Display results
        table = Table(title=f"Similar Packages for '{query}'")
        table.add_column("Package", style="cyan")
        table.add_column("Repository", style="green")
        table.add_column("Version")
        table.add_column("Description")
        
        for pkg in similar_packages:
            description = pkg.description[:60] + "..." if pkg.description and len(pkg.description) > 60 else pkg.description or ""
            table.add_row(
                pkg.name,
                pkg.repository_name,
                pkg.version or "unknown",
                description
            )
        
        console.print(table)
        
        await engine.cleanup()
        
    except Exception as e:
        console.print(f"[red]Error searching packages: {e}[/red]")
        logger.error(f"Package search failed: {e}")


# Async command wrapper
def run_async_command(coro):
    """Run async command in event loop."""
    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Command failed: {e}[/red]")
        logger.error(f"Async command failed: {e}")


# Store original callbacks
_rebuild_callback = rebuild.callback
_status_callback = status.callback
_clear_callback = clear.callback
_search_callback = search.callback

# Wrap async commands
rebuild.callback = lambda *args, **kwargs: run_async_command(_rebuild_callback(*args, **kwargs))
status.callback = lambda *args, **kwargs: run_async_command(_status_callback(*args, **kwargs))
clear.callback = lambda *args, **kwargs: run_async_command(_clear_callback(*args, **kwargs))
search.callback = lambda *args, **kwargs: run_async_command(_search_callback(*args, **kwargs))