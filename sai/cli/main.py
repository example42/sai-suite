"""Main CLI entry point for sai tool."""

import click
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, List
from collections import Counter, defaultdict

from ..utils.config import get_config
from ..providers.loader import ProviderLoader
from ..core.execution_engine import ExecutionEngine, ExecutionContext
from ..core.saidata_loader import SaidataLoader, SaidataNotFoundError, ValidationError
from ..models.config import LogLevel
from ..utils.errors import (
    SaiError, format_error_for_cli, get_error_suggestions, 
    is_user_error, is_system_error
)
from ..utils.logging import get_logger
from .completion import (
    complete_software_names, complete_provider_names, complete_action_names,
    complete_config_keys, complete_log_levels, complete_saidata_files
)


def setup_logging(config, verbose: bool = False):
    """Setup logging configuration."""
    from ..utils.logging import setup_root_logging
    setup_root_logging(config, verbose)


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path), 
              help='Path to configuration file')
@click.option('--provider', '-p', help='Force specific provider')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--yes', '-y', is_flag=True, help='Assume yes for all prompts')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-essential output')
@click.option('--json', 'output_json', is_flag=True, help='Output in JSON format')
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], provider: Optional[str], 
        verbose: bool, dry_run: bool, yes: bool, quiet: bool, output_json: bool):
    """SAI - Software Automation and Installation CLI tool.
    
    A cross-platform software management utility that detects locally available 
    package managers and providers, then executes software management actions 
    based on saidata definitions.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store global options in context
    ctx.obj['config_path'] = config
    ctx.obj['provider'] = provider
    ctx.obj['verbose'] = verbose
    ctx.obj['dry_run'] = dry_run
    ctx.obj['yes'] = yes
    ctx.obj['quiet'] = quiet
    ctx.obj['output_json'] = output_json
    
    # Load configuration
    try:
        sai_config = get_config()
        ctx.obj['sai_config'] = sai_config
        
        # Setup logging
        setup_logging(sai_config, verbose)
        
    except Exception as e:
        error_msg = format_error_for_cli(e, verbose)
        click.echo(f"Error loading configuration: {error_msg}", err=True)
        
        if isinstance(e, SaiError):
            suggestions = get_error_suggestions(e)
            if suggestions:
                click.echo("\nSuggestions:", err=True)
                for suggestion in suggestions:
                    click.echo(f"  • {suggestion}", err=True)
        
        ctx.exit(1)


# Software management commands
@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.pass_context
def install(ctx: click.Context, software: str, timeout: Optional[int]):
    """Install software using the best available provider."""
    _execute_software_action(ctx, 'install', software, timeout)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.pass_context
def uninstall(ctx: click.Context, software: str, timeout: Optional[int]):
    """Uninstall software using the best available provider."""
    _execute_software_action(ctx, 'uninstall', software, timeout)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.pass_context
def start(ctx: click.Context, software: str, timeout: Optional[int]):
    """Start software service."""
    _execute_software_action(ctx, 'start', software, timeout)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.pass_context
def stop(ctx: click.Context, software: str, timeout: Optional[int]):
    """Stop software service."""
    _execute_software_action(ctx, 'stop', software, timeout)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.pass_context
def restart(ctx: click.Context, software: str, timeout: Optional[int]):
    """Restart software service."""
    _execute_software_action(ctx, 'restart', software, timeout)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.pass_context
def status(ctx: click.Context, software: str, timeout: Optional[int]):
    """Show software service status."""
    _execute_software_action(ctx, 'status', software, timeout, requires_confirmation=False)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.pass_context
def info(ctx: click.Context, software: str, timeout: Optional[int]):
    """Show software information."""
    _execute_software_action(ctx, 'info', software, timeout, requires_confirmation=False)


@cli.command()
@click.argument('term', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.pass_context
def search(ctx: click.Context, term: str, timeout: Optional[int]):
    """Search for available software."""
    _execute_software_action(ctx, 'search', term, timeout, requires_confirmation=False)


@cli.command()
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.pass_context
def list(ctx: click.Context, timeout: Optional[int]):
    """List installed software managed through sai."""
    _execute_software_action(ctx, 'list', '', timeout, requires_confirmation=False)


def _execute_software_action(ctx: click.Context, action: str, software: str, 
                           timeout: Optional[int], requires_confirmation: bool = True):
    """Execute a software management action."""
    try:
        # Load providers
        provider_loader = ProviderLoader()
        providers = provider_loader.load_all_providers()
        
        if not providers:
            click.echo("No providers found. Please install a package manager.", err=True)
            ctx.exit(1)
        
        # Create provider instances
        provider_instances = []
        for name, provider_data in providers.items():
            from ..providers.base import BaseProvider
            provider_instance = BaseProvider(provider_data)
            if provider_instance.is_available():
                provider_instances.append(provider_instance)
        
        if not provider_instances:
            click.echo("No available providers found.", err=True)
            ctx.exit(1)
        
        # Load saidata if software name is provided
        saidata = None
        if software:
            try:
                saidata_loader = SaidataLoader(ctx.obj['sai_config'])
                saidata = saidata_loader.load_saidata(software)
            except SaidataNotFoundError:
                if not ctx.obj['quiet']:
                    click.echo(f"Warning: No saidata found for '{software}', using basic execution", err=True)
                # Create minimal saidata
                from ..models.saidata import SaiData, Metadata
                saidata = SaiData(
                    version="0.2",
                    metadata=Metadata(name=software)
                )
        
        # Create execution engine
        engine = ExecutionEngine(provider_instances, ctx.obj['sai_config'])
        
        # Create execution context
        execution_context = ExecutionContext(
            action=action,
            software=software,
            saidata=saidata,
            provider=ctx.obj.get('provider'),
            dry_run=ctx.obj['dry_run'],
            verbose=ctx.obj['verbose'],
            timeout=timeout
        )
        
        # Show confirmation if required and not in quiet/yes mode
        if (requires_confirmation and not ctx.obj['dry_run'] and 
            not ctx.obj['yes'] and not ctx.obj['quiet']):
            
            # Find suitable providers to show user
            suitable_providers = [
                p for p in provider_instances 
                if p.has_action(action)
            ]
            
            if not suitable_providers:
                click.echo(f"No providers support action '{action}'", err=True)
                ctx.exit(1)
            
            if len(suitable_providers) == 1 or ctx.obj.get('provider'):
                # Single provider or forced provider
                selected = suitable_providers[0] if not ctx.obj.get('provider') else next(
                    (p for p in suitable_providers if p.name == ctx.obj['provider']), None
                )
                if not selected:
                    click.echo(f"Requested provider '{ctx.obj['provider']}' not available", err=True)
                    ctx.exit(1)
                
                click.echo(f"Will execute: {action} {software} using {selected.name}")
                if not click.confirm("Continue?"):
                    click.echo("Cancelled.")
                    ctx.exit(0)
            else:
                # Multiple providers available
                click.echo(f"Multiple providers available for action '{action}':")
                for i, provider in enumerate(suitable_providers, 1):
                    priority = provider.get_priority()
                    default_marker = " (default)" if i == 1 else ""
                    click.echo(f"  {i}. {provider.name} (priority: {priority}){default_marker}")
                
                choice = click.prompt(
                    "Select provider (enter for default, number to choose)",
                    default="1",
                    show_default=False
                )
                
                try:
                    if choice == "":
                        choice = "1"
                    provider_index = int(choice) - 1
                    if provider_index < 0 or provider_index >= len(suitable_providers):
                        raise ValueError()
                    execution_context.provider = suitable_providers[provider_index].name
                except (ValueError, IndexError):
                    click.echo("Invalid selection.", err=True)
                    ctx.exit(1)
        
        # Execute the action
        result = engine.execute_action(execution_context)
        
        # Output results
        if ctx.obj['output_json']:
            import json
            output = {
                'success': result.success,
                'status': result.status.value,
                'message': result.message,
                'provider_used': result.provider_used,
                'action_name': result.action_name,
                'commands_executed': result.commands_executed,
                'execution_time': result.execution_time,
                'dry_run': result.dry_run
            }
            if result.stdout:
                output['stdout'] = result.stdout
            if result.stderr:
                output['stderr'] = result.stderr
            if result.error_details:
                output['error_details'] = result.error_details
            
            click.echo(json.dumps(output, indent=2))
        else:
            # Human-readable output
            if result.success:
                if not ctx.obj['quiet']:
                    click.echo(f"✓ {result.message}")
                    if ctx.obj['verbose'] and result.commands_executed:
                        click.echo("Commands executed:")
                        for cmd in result.commands_executed:
                            click.echo(f"  {cmd}")
            else:
                click.echo(f"✗ {result.message}", err=True)
                if result.error_details and ctx.obj['verbose']:
                    click.echo(f"Error details: {result.error_details}", err=True)
                ctx.exit(1)
        
    except Exception as e:
        if ctx.obj['output_json']:
            import json
            error_output = {
                'success': False,
                'error': str(e),
                'error_type': e.__class__.__name__,
                'action': action,
                'software': software
            }
            
            # Add SAI error details if available
            if isinstance(e, SaiError):
                error_output.update(e.to_dict())
            
            click.echo(json.dumps(error_output, indent=2))
        else:
            # Format error for human-readable output
            error_msg = format_error_for_cli(e, ctx.obj['verbose'])
            click.echo(f"Error: {error_msg}", err=True)
            
            # Show suggestions for SAI errors
            if isinstance(e, SaiError):
                suggestions = get_error_suggestions(e)
                if suggestions:
                    click.echo("\nSuggestions:", err=True)
                    for suggestion in suggestions:
                        click.echo(f"  • {suggestion}", err=True)
        
        # Determine exit code based on error type
        if is_user_error(e):
            ctx.exit(2)  # User error
        elif is_system_error(e):
            ctx.exit(3)  # System error
        else:
            ctx.exit(1)  # General error


@cli.command()
@click.pass_context
def version(ctx: click.Context):
    """Show version information."""
    from .. import __version__
    if ctx.obj['output_json']:
        import json
        click.echo(json.dumps({'version': __version__}))
    else:
        click.echo(f"sai version {__version__}")


# Execution history and metrics commands
@cli.group()
def history():
    """View execution history and metrics."""
    pass


@history.command('list')
@click.option('--limit', '-n', type=int, default=10, help='Number of executions to show')
@click.option('--action', help='Filter by action')
@click.option('--software', help='Filter by software')
@click.option('--provider', help='Filter by provider')
@click.option('--success-only', is_flag=True, help='Show only successful executions')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed execution information')
@click.pass_context
def history_list(ctx: click.Context, limit: int, action: Optional[str], 
                software: Optional[str], provider: Optional[str], 
                success_only: bool, detailed: bool):
    """List recent execution history."""
    try:
        from ..utils.execution_tracker import get_execution_tracker
        
        tracker = get_execution_tracker(ctx.obj['sai_config'])
        executions = tracker.get_execution_history(
            limit=limit,
            action_filter=action,
            software_filter=software,
            provider_filter=provider,
            success_only=success_only
        )
        
        if ctx.obj['output_json']:
            import json
            output = {
                'executions': [exec.to_dict() for exec in executions],
                'total_shown': len(executions),
                'filters': {
                    'action': action,
                    'software': software,
                    'provider': provider,
                    'success_only': success_only
                }
            }
            click.echo(json.dumps(output, indent=2))
        else:
            if not executions:
                click.echo("No executions found matching criteria.")
                return
            
            click.echo(f"Recent Executions ({len(executions)} shown):")
            click.echo()
            
            for execution in executions:
                if detailed:
                    click.echo(execution.get_detailed_report())
                    click.echo("-" * 50)
                else:
                    click.echo(execution.get_summary())
    
    except Exception as e:
        error_msg = format_error_for_cli(e, ctx.obj['verbose'])
        click.echo(f"Error retrieving execution history: {error_msg}", err=True)
        ctx.exit(1)


@history.command('metrics')
@click.pass_context
def history_metrics(ctx: click.Context):
    """Show execution metrics and statistics."""
    try:
        from ..utils.execution_tracker import get_execution_tracker
        
        tracker = get_execution_tracker(ctx.obj['sai_config'])
        metrics = tracker.get_metrics()
        
        if ctx.obj['output_json']:
            import json
            click.echo(json.dumps(metrics.to_dict(), indent=2))
        else:
            click.echo("Execution Metrics:")
            click.echo(f"  Total Executions: {metrics.total_executions}")
            click.echo(f"  Successful: {metrics.successful_executions}")
            click.echo(f"  Failed: {metrics.failed_executions}")
            
            if metrics.total_executions > 0:
                success_rate = (metrics.successful_executions / metrics.total_executions) * 100
                click.echo(f"  Success Rate: {success_rate:.1f}%")
            
            click.echo(f"  Total Execution Time: {metrics.total_execution_time:.2f}s")
            click.echo(f"  Average Execution Time: {metrics.average_execution_time:.2f}s")
            click.echo(f"  Commands Executed: {metrics.commands_executed}")
            click.echo(f"  Cache Hits: {metrics.cache_hits}")
            click.echo(f"  Cache Misses: {metrics.cache_misses}")
            
            if metrics.cache_hits + metrics.cache_misses > 0:
                cache_hit_rate = (metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses)) * 100
                click.echo(f"  Cache Hit Rate: {cache_hit_rate:.1f}%")
    
    except Exception as e:
        error_msg = format_error_for_cli(e, ctx.obj['verbose'])
        click.echo(f"Error retrieving metrics: {error_msg}", err=True)
        ctx.exit(1)


@history.command('clear')
@click.option('--older-than', type=int, help='Clear executions older than N days')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def history_clear(ctx: click.Context, older_than: Optional[int], confirm: bool):
    """Clear execution history."""
    try:
        from ..utils.execution_tracker import get_execution_tracker
        
        if not confirm and not ctx.obj['yes']:
            if older_than:
                message = f"Clear executions older than {older_than} days?"
            else:
                message = "Clear all execution history?"
            
            if not click.confirm(message):
                click.echo("Cancelled.")
                return
        
        tracker = get_execution_tracker(ctx.obj['sai_config'])
        cleared_count = tracker.clear_history(older_than_days=older_than)
        
        if ctx.obj['output_json']:
            import json
            output = {
                'success': True,
                'cleared_count': cleared_count,
                'older_than_days': older_than
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"✓ Cleared {cleared_count} execution record(s)")
    
    except Exception as e:
        error_msg = format_error_for_cli(e, ctx.obj['verbose'])
        click.echo(f"Error clearing history: {error_msg}", err=True)
        ctx.exit(1)


# Provider management commands
@cli.group()
def providers():
    """Manage and inspect providers."""
    pass


@providers.command('list')
@click.option('--available-only', is_flag=True, help='Show only available providers')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed provider information')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh detection')
@click.pass_context
def providers_list(ctx: click.Context, available_only: bool, detailed: bool, no_cache: bool):
    """List all providers and their status."""
    try:
        provider_loader = ProviderLoader()
        providers = provider_loader.load_all_providers()
        
        if not providers:
            click.echo("No providers found.")
            return
        
        # Create provider instances to check availability
        provider_info = []
        use_cache = not no_cache
        
        for name, provider_data in providers.items():
            from ..providers.base import BaseProvider
            provider_instance = BaseProvider(provider_data)
            is_available = provider_instance.is_available(use_cache=use_cache)
            
            if available_only and not is_available:
                continue
            
            provider_info.append({
                'name': name,
                'available': is_available,
                'priority': provider_instance.get_priority(),
                'actions': provider_instance.get_supported_actions(),
                'platforms': provider_data.provider.platforms or [],
                'type': provider_data.provider.type.value,
                'executable': getattr(provider_data.provider, 'executable', 'N/A')
            })
        
        if ctx.obj['output_json']:
            import json
            click.echo(json.dumps(provider_info, indent=2))
        else:
            # Human-readable output
            if not provider_info:
                click.echo("No providers found matching criteria.")
                return
            
            click.echo(f"Found {len(provider_info)} provider(s):")
            click.echo()
            
            for info in sorted(provider_info, key=lambda x: (-x['priority'], x['name'])):
                status = "✓ Available" if info['available'] else "✗ Not available"
                click.echo(f"{info['name']} ({info['type']}) - {status}")
                
                if detailed:
                    click.echo(f"  Executable: {info['executable']}")
                    click.echo(f"  Priority: {info['priority']}")
                    click.echo(f"  Platforms: {', '.join(info['platforms'])}")
                    click.echo(f"  Actions: {', '.join(sorted(info['actions']))}")
                    click.echo()
    
    except Exception as e:
        click.echo(f"Error listing providers: {e}", err=True)
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@providers.command('detect')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh detection')
@click.pass_context
def providers_detect(ctx: click.Context, no_cache: bool):
    """Detect and refresh provider availability."""
    try:
        provider_loader = ProviderLoader()
        providers = provider_loader.load_all_providers()
        
        if not providers:
            click.echo("No providers found.")
            return
        
        available_count = 0
        total_count = len(providers)
        
        if not ctx.obj['quiet']:
            click.echo("Detecting provider availability...")
        
        results = []
        use_cache = not no_cache
        
        for name, provider_data in providers.items():
            from ..providers.base import BaseProvider
            provider_instance = BaseProvider(provider_data)
            is_available = provider_instance.is_available(use_cache=use_cache)
            
            if is_available:
                available_count += 1
            
            results.append({
                'name': name,
                'available': is_available,
                'executable': getattr(provider_data.provider, 'executable', 'N/A')
            })
            
            if ctx.obj['verbose']:
                status = "✓" if is_available else "✗"
                click.echo(f"  {status} {name}")
        
        if ctx.obj['output_json']:
            import json
            output = {
                'total_providers': total_count,
                'available_providers': available_count,
                'providers': results
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"\nDetection complete: {available_count}/{total_count} providers available")
    
    except Exception as e:
        click.echo(f"Error detecting providers: {e}", err=True)
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@providers.command('info')
@click.argument('provider_name', required=True)
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh detection')
@click.pass_context
def providers_info(ctx: click.Context, provider_name: str, no_cache: bool):
    """Show detailed information about a specific provider."""
    try:
        provider_loader = ProviderLoader()
        providers = provider_loader.load_all_providers()
        
        if provider_name not in providers:
            click.echo(f"Provider '{provider_name}' not found.", err=True)
            ctx.exit(1)
        
        provider_data = providers[provider_name]
        from ..providers.base import BaseProvider
        provider_instance = BaseProvider(provider_data)
        
        use_cache = not no_cache
        is_available = provider_instance.is_available(use_cache=use_cache)
        
        info = {
            'name': provider_name,
            'type': provider_data.provider.type.value,
            'executable': getattr(provider_data.provider, 'executable', 'N/A'),
            'available': is_available,
            'priority': provider_instance.get_priority(),
            'platforms': provider_data.provider.platforms or [],
            'capabilities': provider_data.provider.capabilities or [],
            'actions': {}
        }
        
        # Get action details
        for action_name in provider_instance.get_supported_actions():
            action = provider_instance.get_action(action_name)
            if action:
                info['actions'][action_name] = {
                    'requires_root': action.requires_root,
                    'timeout': action.timeout,
                    'has_steps': bool(action.steps)
                }
        
        if ctx.obj['output_json']:
            import json
            click.echo(json.dumps(info, indent=2))
        else:
            # Human-readable output
            status = "✓ Available" if info['available'] else "✗ Not available"
            click.echo(f"Provider: {provider_name}")
            click.echo(f"Type: {info['type']}")
            click.echo(f"Executable: {info['executable']}")
            click.echo(f"Status: {status}")
            click.echo(f"Priority: {info['priority']}")
            click.echo(f"Platforms: {', '.join(info['platforms'])}")
            click.echo(f"Capabilities: {', '.join(info['capabilities'])}")
            
            if info['actions']:
                click.echo("\nSupported Actions:")
                for action_name, action_info in sorted(info['actions'].items()):
                    root_req = " (requires root)" if action_info['requires_root'] else ""
                    timeout_info = f" (timeout: {action_info['timeout']}s)" if action_info['timeout'] != 300 else ""
                    click.echo(f"  {action_name}{root_req}{timeout_info}")
    
    except Exception as e:
        click.echo(f"Error getting provider info: {e}", err=True)
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@providers.command('clear-cache')
@click.option('--provider', '-p', help='Clear cache for specific provider only')
@click.pass_context
def providers_clear_cache(ctx: click.Context, provider: Optional[str]):
    """Clear provider detection cache."""
    try:
        from ..utils.cache import ProviderCache
        
        cache = ProviderCache(ctx.obj['sai_config'])
        
        if provider:
            # Clear cache for specific provider
            cleared = cache.clear_provider_cache(provider)
            if cleared:
                if not ctx.obj['quiet']:
                    click.echo(f"✓ Cleared cache for provider '{provider}'")
            else:
                click.echo(f"No cache found for provider '{provider}'", err=True)
                ctx.exit(1)
        else:
            # Clear all provider cache
            cleared_count = cache.clear_all_provider_cache()
            if not ctx.obj['quiet']:
                click.echo(f"✓ Cleared cache for {cleared_count} provider(s)")
        
        if ctx.obj['output_json']:
            import json
            output = {
                'success': True,
                'provider': provider,
                'cleared_count': 1 if provider else cleared_count
            }
            click.echo(json.dumps(output, indent=2))
    
    except Exception as e:
        if ctx.obj['output_json']:
            import json
            error_output = {
                'success': False,
                'error': str(e),
                'provider': provider
            }
            click.echo(json.dumps(error_output, indent=2))
        else:
            click.echo(f"Error clearing cache: {e}", err=True)
        
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@providers.command('cache-status')
@click.pass_context
def providers_cache_status(ctx: click.Context):
    """Show provider cache status and statistics."""
    try:
        from ..utils.cache import ProviderCache
        
        cache = ProviderCache(ctx.obj['sai_config'])
        cache_info = cache.get_cache_status()
        
        if ctx.obj['output_json']:
            import json
            click.echo(json.dumps(cache_info, indent=2))
        else:
            click.echo("Provider Cache Status:")
            click.echo(f"  Cache Directory: {cache_info['cache_directory']}")
            click.echo(f"  Cache Enabled: {cache_info['cache_enabled']}")
            click.echo(f"  Total Cached Providers: {cache_info['total_cached_providers']}")
            click.echo(f"  Cache Size: {cache_info['cache_size_mb']:.2f} MB")
            
            if cache_info['cached_providers']:
                click.echo("\nCached Providers:")
                for provider_info in cache_info['cached_providers']:
                    age_str = f"({provider_info['age_hours']:.1f}h ago)" if provider_info['age_hours'] < 24 else f"({provider_info['age_days']:.1f}d ago)"
                    status = "✓ Available" if provider_info['available'] else "✗ Not available"
                    click.echo(f"  {provider_info['name']}: {status} {age_str}")
            else:
                click.echo("\nNo providers currently cached.")
    
    except Exception as e:
        if ctx.obj['output_json']:
            import json
            error_output = {
                'success': False,
                'error': str(e)
            }
            click.echo(json.dumps(error_output, indent=2))
        else:
            click.echo(f"Error getting cache status: {e}", err=True)
        
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@providers.command('refresh-cache')
@click.option('--provider', '-p', help='Refresh cache for specific provider only')
@click.pass_context
def providers_refresh_cache(ctx: click.Context, provider: Optional[str]):
    """Refresh provider detection cache."""
    try:
        from ..utils.cache import ProviderCache
        
        cache = ProviderCache(ctx.obj['sai_config'])
        
        if not ctx.obj['quiet']:
            if provider:
                click.echo(f"Refreshing cache for provider '{provider}'...")
            else:
                click.echo("Refreshing provider detection cache...")
        
        # Load providers and refresh cache
        provider_loader = ProviderLoader()
        providers = provider_loader.load_all_providers()
        
        if not providers:
            click.echo("No providers found to cache.", err=True)
            ctx.exit(1)
        
        refreshed_count = 0
        results = []
        
        for name, provider_data in providers.items():
            if provider and name != provider:
                continue
                
            from ..providers.base import BaseProvider
            provider_instance = BaseProvider(provider_data)
            is_available = provider_instance.is_available()
            
            # Update cache
            cache.update_provider_cache(name, {
                'available': is_available,
                'executable_path': provider_instance.get_executable_path(),
                'version': provider_instance.get_version() if is_available else None,
                'priority': provider_instance.get_priority(),
                'actions': provider_instance.get_supported_actions(),
                'platforms': provider_data.provider.platforms or [],
                'type': provider_data.provider.type.value
            })
            
            refreshed_count += 1
            results.append({
                'name': name,
                'available': is_available
            })
            
            if ctx.obj['verbose']:
                status = "✓" if is_available else "✗"
                click.echo(f"  {status} {name}")
        
        if ctx.obj['output_json']:
            import json
            output = {
                'success': True,
                'refreshed_count': refreshed_count,
                'providers': results
            }
            click.echo(json.dumps(output, indent=2))
        else:
            if not ctx.obj['quiet']:
                if provider:
                    click.echo(f"✓ Refreshed cache for provider '{provider}'")
                else:
                    click.echo(f"✓ Refreshed cache for {refreshed_count} provider(s)")
    
    except Exception as e:
        if ctx.obj['output_json']:
            import json
            error_output = {
                'success': False,
                'error': str(e),
                'provider': provider
            }
            click.echo(json.dumps(error_output, indent=2))
        else:
            click.echo(f"Error refreshing cache: {e}", err=True)
        
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


# Configuration management commands
@cli.group()
def config():
    """Manage sai configuration."""
    pass


@config.command('show')
@click.pass_context
def config_show(ctx: click.Context):
    """Show current configuration."""
    config = ctx.obj['sai_config']
    
    if ctx.obj['output_json']:
        import json
        config_dict = {
            'config_version': config.config_version,
            'log_level': config.log_level.value,
            'cache_enabled': config.cache_enabled,
            'cache_directory': str(config.cache_directory),
            'default_provider': config.default_provider,
            'saidata_paths': config.saidata_paths,
            'provider_paths': config.provider_paths,
            'provider_priorities': config.provider_priorities,
            'max_concurrent_actions': config.max_concurrent_actions,
            'action_timeout': config.action_timeout,
            'require_confirmation': config.require_confirmation,
            'dry_run_default': config.dry_run_default
        }
        click.echo(json.dumps(config_dict, indent=2))
    else:
        click.echo("SAI Configuration:")
        click.echo(f"  Config Version: {config.config_version}")
        click.echo(f"  Log Level: {config.log_level.value}")
        click.echo(f"  Cache Enabled: {config.cache_enabled}")
        click.echo(f"  Cache Directory: {config.cache_directory}")
        click.echo(f"  Default Provider: {config.default_provider or 'None'}")
        click.echo(f"  Action Timeout: {config.action_timeout}s")
        click.echo(f"  Require Confirmation: {config.require_confirmation}")
        
        click.echo("\nSaidata Paths:")
        for i, path in enumerate(config.saidata_paths, 1):
            exists = "✓" if Path(path).exists() else "✗"
            click.echo(f"  {i}. {path} {exists}")
        
        click.echo("\nProvider Paths:")
        for i, path in enumerate(config.provider_paths, 1):
            exists = "✓" if Path(path).exists() else "✗"
            click.echo(f"  {i}. {path} {exists}")
        
        if config.provider_priorities:
            click.echo("\nProvider Priorities:")
            for provider, priority in sorted(config.provider_priorities.items()):
                click.echo(f"  {provider}: {priority}")


@config.command('set')
@click.argument('key', required=True)
@click.argument('value', required=True)
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str):
    """Set a configuration value."""
    # This is a placeholder - in a real implementation, this would
    # modify the configuration file
    click.echo(f"Setting {key} = {value}")
    click.echo("Note: Configuration modification not yet implemented.")


# Validation command
@cli.command()
@click.argument('saidata_file', type=click.Path(exists=True, path_type=Path), required=True)
@click.pass_context
def validate(ctx: click.Context, saidata_file: Path):
    """Validate a saidata file against the schema."""
    try:
        saidata_loader = SaidataLoader(ctx.obj['sai_config'])
        
        # Load and validate the file
        import yaml
        with open(saidata_file, 'r') as f:
            data = yaml.safe_load(f)
        
        validation_result = saidata_loader.validate_saidata(data)
        
        if ctx.obj['output_json']:
            import json
            output = {
                'file': str(saidata_file),
                'valid': validation_result.valid,
                'errors': validation_result.errors,
                'warnings': validation_result.warnings
            }
            click.echo(json.dumps(output, indent=2))
        else:
            if validation_result.valid:
                click.echo(f"✓ {saidata_file} is valid")
                if validation_result.warnings:
                    click.echo("\nWarnings:")
                    for warning in validation_result.warnings:
                        click.echo(f"  ⚠ {warning}")
            else:
                click.echo(f"✗ {saidata_file} is invalid", err=True)
                click.echo("\nErrors:")
                for error in validation_result.errors:
                    click.echo(f"  ✗ {error}", err=True)
                
                if validation_result.warnings:
                    click.echo("\nWarnings:")
                    for warning in validation_result.warnings:
                        click.echo(f"  ⚠ {warning}")
                
                ctx.exit(1)
    
    except Exception as e:
        if ctx.obj['output_json']:
            import json
            error_output = {
                'file': str(saidata_file),
                'valid': False,
                'error': str(e)
            }
            click.echo(json.dumps(error_output, indent=2))
        else:
            click.echo(f"Error validating {saidata_file}: {e}", err=True)
        
        if ctx.obj['verbose']:
            import traceback
            traceback.print_exc()
        
        ctx.exit(1)


@cli.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed statistics')
@click.option('--by-type', '-t', is_flag=True, help='Group statistics by provider type')
@click.option('--by-platform', '-p', is_flag=True, help='Group statistics by platform')
@click.option('--actions-only', '-a', is_flag=True, help='Show only action statistics')
@click.pass_context
def stats(ctx: click.Context, detailed: bool, by_type: bool, by_platform: bool, actions_only: bool):
    """Show statistics about providers and actions."""
    try:
        # Load all providers
        loader = ProviderLoader()
        providers = loader.load_all_providers()
        
        if not providers:
            click.echo("No providers found.", err=True)
            return
        
        # Basic statistics
        total_providers = len(providers)
        
        # Collect statistics
        provider_types = Counter()
        platforms = Counter()
        actions = Counter()
        capabilities = Counter()
        provider_actions = defaultdict(list)
        
        for name, provider_data in providers.items():
            provider_info = provider_data.provider
            
            # Count by type
            provider_types[provider_info.type] += 1
            
            # Count by platforms
            for platform in provider_info.platforms:
                platforms[platform] += 1
            
            # Count capabilities/actions
            for capability in provider_info.capabilities:
                capabilities[capability] += 1
                actions[capability] += 1
                provider_actions[capability].append(name)
        
        # Display statistics
        if not actions_only:
            click.echo("🔧 SAI Provider & Action Statistics")
            click.echo("=" * 40)
            
            click.echo(f"\n📊 Overview:")
            click.echo(f"  Total Providers: {total_providers}")
            click.echo(f"  Unique Actions: {len(actions)}")
            click.echo(f"  Total Action Implementations: {sum(actions.values())}")
            
            if by_type:
                click.echo(f"\n🏷️  Providers by Type:")
                for ptype, count in provider_types.most_common():
                    percentage = (count / total_providers) * 100
                    click.echo(f"  {ptype:15} {count:3d} ({percentage:5.1f}%)")
            
            if by_platform:
                click.echo(f"\n🖥️  Platform Support:")
                for platform, count in platforms.most_common():
                    percentage = (count / total_providers) * 100
                    click.echo(f"  {platform:10} {count:3d} providers ({percentage:5.1f}%)")
        
        # Action statistics
        click.echo(f"\n⚡ Action Statistics:")
        click.echo(f"{'Action':<15} {'Providers':<10} {'Coverage':<10}")
        click.echo("-" * 35)
        
        for action, count in actions.most_common():
            percentage = (count / total_providers) * 100
            click.echo(f"{action:<15} {count:<10} {percentage:5.1f}%")
        
        if detailed:
            click.echo(f"\n📋 Detailed Action Coverage:")
            for action in sorted(actions.keys()):
                count = actions[action]
                percentage = (count / total_providers) * 100
                click.echo(f"\n{action} ({count} providers, {percentage:.1f}% coverage):")
                
                # Group providers by type for this action
                action_providers = provider_actions[action]
                provider_by_type = defaultdict(list)
                
                for provider_name in action_providers:
                    provider_type = providers[provider_name].provider.type
                    provider_by_type[provider_type].append(provider_name)
                
                for ptype in sorted(provider_by_type.keys()):
                    provider_list = ", ".join(sorted(provider_by_type[ptype]))
                    click.echo(f"  {ptype}: {provider_list}")
        
        # Most/least common actions
        if not actions_only:
            click.echo(f"\n🏆 Most Common Actions:")
            for action, count in actions.most_common(5):
                percentage = (count / total_providers) * 100
                click.echo(f"  {action:<12} {count:3d} providers ({percentage:5.1f}%)")
            
            click.echo(f"\n🔍 Least Common Actions:")
            for action, count in actions.most_common()[-5:]:
                percentage = (count / total_providers) * 100
                click.echo(f"  {action:<12} {count:3d} providers ({percentage:5.1f}%)")
        
        # Provider type breakdown
        if not actions_only and not by_type:
            click.echo(f"\n🏷️  Provider Types:")
            for ptype, count in provider_types.most_common():
                percentage = (count / total_providers) * 100
                click.echo(f"  {ptype:<15} {count:3d} ({percentage:5.1f}%)")
        
    except Exception as e:
        click.echo(f"Error loading provider statistics: {e}", err=True)
        if ctx.obj.get('verbose'):
            import traceback
            traceback.print_exc()


# Shell completion commands
@cli.group()
def completion():
    """Shell completion management."""
    pass


@completion.command('install')
@click.option('--shell', type=click.Choice(['bash', 'zsh', 'fish']), 
              help='Shell type (auto-detected if not specified)')
@click.pass_context
def completion_install(ctx: click.Context, shell: Optional[str]):
    """Install shell completion for sai command."""
    import os
    
    if not shell:
        # Auto-detect shell
        shell_path = os.environ.get('SHELL', '')
        if 'bash' in shell_path:
            shell = 'bash'
        elif 'zsh' in shell_path:
            shell = 'zsh'
        elif 'fish' in shell_path:
            shell = 'fish'
        else:
            click.echo("Could not auto-detect shell. Please specify --shell option.", err=True)
            ctx.exit(1)
    
    # Generate completion script
    if shell == 'bash':
        completion_script = '''
# SAI completion for bash
_sai_completion() {
    local IFS=$'\\n'
    COMPREPLY=( $(env COMP_WORDS="${COMP_WORDS[*]}" \\
                     COMP_CWORD=$COMP_CWORD \\
                     _SAI_COMPLETE=complete $1) )
}
complete -F _sai_completion -o default sai
'''
        completion_file = Path.home() / '.bash_completion.d' / 'sai'
        source_line = 'source ~/.bash_completion.d/sai'
        rc_file = Path.home() / '.bashrc'
        
    elif shell == 'zsh':
        completion_script = '''
# SAI completion for zsh
_sai_completion() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    response=("${(@f)$( env COMP_WORDS="${words[*]}" \\
                        COMP_CWORD=$((CURRENT-1)) \\
                        _SAI_COMPLETE=complete $words[1] )}")
    
    for key descr in ${(kv)response}; do
        if [[ "$descr" == "_" ]]; then
            completions+=("$key")
        else
            completions_with_descriptions+=("$key:$descr")
        fi
    done
    
    if [ -n "$completions_with_descriptions" ]; then
        _describe -V unsorted completions_with_descriptions -U
    fi
    
    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
    compstate[insert]="automenu"
}
compdef _sai_completion sai
'''
        completion_file = Path.home() / '.zsh' / 'completions' / '_sai'
        completion_file.parent.mkdir(parents=True, exist_ok=True)
        source_line = 'fpath=(~/.zsh/completions $fpath)'
        rc_file = Path.home() / '.zshrc'
        
    elif shell == 'fish':
        completion_script = '''
# SAI completion for fish
function __fish_sai_complete
    set -lx COMP_WORDS (commandline -cp)
    set -lx COMP_CWORD (math (count $COMP_WORDS) - 1)
    env _SAI_COMPLETE=complete sai
end

complete -f -c sai -a "(__fish_sai_complete)"
'''
        completion_file = Path.home() / '.config' / 'fish' / 'completions' / 'sai.fish'
        completion_file.parent.mkdir(parents=True, exist_ok=True)
        source_line = None  # Fish auto-loads completions
        rc_file = None
    
    try:
        # Write completion script
        completion_file.parent.mkdir(parents=True, exist_ok=True)
        with open(completion_file, 'w') as f:
            f.write(completion_script.strip())
        
        click.echo(f"✓ Completion script installed to {completion_file}")
        
        # Add source line to rc file if needed
        if source_line and rc_file:
            if rc_file.exists():
                with open(rc_file, 'r') as f:
                    content = f.read()
                
                if source_line not in content:
                    with open(rc_file, 'a') as f:
                        f.write(f'\n# SAI completion\n{source_line}\n')
                    click.echo(f"✓ Added completion source to {rc_file}")
                else:
                    click.echo(f"✓ Completion already sourced in {rc_file}")
            else:
                click.echo(f"⚠ {rc_file} not found. Add this line to your shell config:")
                click.echo(f"  {source_line}")
        
        if shell in ['bash', 'zsh']:
            click.echo(f"\nTo enable completion in current session, run:")
            click.echo(f"  source {completion_file}")
        
        click.echo(f"\nCompletion installed for {shell}. Restart your shell or source your config file.")
        
    except Exception as e:
        click.echo(f"Error installing completion: {e}", err=True)
        ctx.exit(1)


@completion.command('uninstall')
@click.option('--shell', type=click.Choice(['bash', 'zsh', 'fish']), 
              help='Shell type (auto-detected if not specified)')
@click.pass_context
def completion_uninstall(ctx: click.Context, shell: Optional[str]):
    """Uninstall shell completion for sai command."""
    import os
    
    if not shell:
        # Auto-detect shell
        shell_path = os.environ.get('SHELL', '')
        if 'bash' in shell_path:
            shell = 'bash'
        elif 'zsh' in shell_path:
            shell = 'zsh'
        elif 'fish' in shell_path:
            shell = 'fish'
        else:
            click.echo("Could not auto-detect shell. Please specify --shell option.", err=True)
            ctx.exit(1)
    
    # Determine completion file location
    if shell == 'bash':
        completion_file = Path.home() / '.bash_completion.d' / 'sai'
    elif shell == 'zsh':
        completion_file = Path.home() / '.zsh' / 'completions' / '_sai'
    elif shell == 'fish':
        completion_file = Path.home() / '.config' / 'fish' / 'completions' / 'sai.fish'
    
    try:
        if completion_file.exists():
            completion_file.unlink()
            click.echo(f"✓ Removed completion script from {completion_file}")
        else:
            click.echo(f"⚠ Completion script not found at {completion_file}")
        
        click.echo(f"Completion uninstalled for {shell}. Restart your shell to take effect.")
        
    except Exception as e:
        click.echo(f"Error uninstalling completion: {e}", err=True)
        ctx.exit(1)


def main():
    """Main entry point."""
    cli()