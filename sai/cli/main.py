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
from ..version import get_version
from .completion import (
    complete_software_names, complete_provider_names, complete_action_names,
    complete_config_keys, complete_log_levels, complete_saidata_files
)


def format_command_execution(provider_name: str, command: str, verbose: bool = False) -> str:
    """Format command execution message with highlighting."""
    # Always show "Executing" with command in bold
    command_styled = click.style(command, bold=True)
    return f"Executing {command_styled}"


def setup_logging(config, verbose: bool = False):
    """Setup logging configuration."""
    from ..utils.logging import setup_root_logging
    
    # Set logging level based on verbose flag
    if verbose:
        setup_root_logging(config, verbose)
    else:
        # Suppress all logging except critical errors when not verbose
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.CRITICAL)
        
        # Remove all existing handlers to prevent any output
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Suppress all sai loggers by setting them to CRITICAL
        for logger_name in ['sai', 'sai.providers', 'sai.core', 'sai.utils', 
                           'sai.providers.loader', 'sai.core.execution_engine', 
                           'sai.utils.execution_tracker', 'sai.providers.base',
                           'sai.providers.template_engine']:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
            # Also remove handlers from these loggers
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path), 
              help='Path to configuration file')
@click.option('--provider', '-p', help='Force specific provider')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--yes', '-y', is_flag=True, help='Assume yes for all prompts')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-essential output')
@click.option('--json', 'output_json', is_flag=True, help='Output in JSON format')
@click.version_option(version=get_version(), prog_name="sai")
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
    # Enable quiet mode when JSON output is requested to prevent interference
    ctx.obj['quiet'] = quiet or output_json
    ctx.obj['output_json'] = output_json
    
    # Load configuration
    try:
        sai_config = get_config()
        ctx.obj['sai_config'] = sai_config
        
        # Setup logging
        setup_logging(sai_config, verbose)
        
        # Additional logging suppression for non-verbose mode
        if not verbose:
            # Disable all logging from the sai package
            import logging
            logging.getLogger('sai').disabled = True
            logging.getLogger('sai.utils.execution_tracker').disabled = True
            logging.getLogger('sai.core.execution_engine').disabled = True
        
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
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh operations')
@click.pass_context
def install(ctx: click.Context, software: str, timeout: Optional[int], no_cache: bool):
    """Install software using the best available provider."""
    _execute_software_action(ctx, 'install', software, timeout, use_cache=not no_cache)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh operations')
@click.pass_context
def uninstall(ctx: click.Context, software: str, timeout: Optional[int], no_cache: bool):
    """Uninstall software using the best available provider."""
    _execute_software_action(ctx, 'uninstall', software, timeout, use_cache=not no_cache)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh operations')
@click.pass_context
def start(ctx: click.Context, software: str, timeout: Optional[int], no_cache: bool):
    """Start software service."""
    _execute_software_action(ctx, 'start', software, timeout, use_cache=not no_cache)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh operations')
@click.pass_context
def stop(ctx: click.Context, software: str, timeout: Optional[int], no_cache: bool):
    """Stop software service."""
    _execute_software_action(ctx, 'stop', software, timeout, use_cache=not no_cache)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh operations')
@click.pass_context
def restart(ctx: click.Context, software: str, timeout: Optional[int], no_cache: bool):
    """Restart software service."""
    _execute_software_action(ctx, 'restart', software, timeout, use_cache=not no_cache)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh operations')
@click.pass_context
def status(ctx: click.Context, software: str, timeout: Optional[int], no_cache: bool):
    """Show software service status."""
    _execute_software_action(ctx, 'status', software, timeout, requires_confirmation=False, use_cache=not no_cache)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh operations')
@click.pass_context
def info(ctx: click.Context, software: str, timeout: Optional[int], no_cache: bool):
    """Show software information."""
    _execute_software_action(ctx, 'info', software, timeout, requires_confirmation=False, use_cache=not no_cache)


@cli.command()
@click.argument('term', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh operations')
@click.pass_context
def search(ctx: click.Context, term: str, timeout: Optional[int], no_cache: bool):
    """Search for available software."""
    _execute_software_action(ctx, 'search', term, timeout, requires_confirmation=False, use_cache=not no_cache)


@cli.command()
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh operations')
@click.pass_context
def list(ctx: click.Context, timeout: Optional[int], no_cache: bool):
    """List installed software managed through sai."""
    _execute_software_action(ctx, 'list', '', timeout, requires_confirmation=False, use_cache=not no_cache)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh operations')
@click.pass_context
def logs(ctx: click.Context, software: str, timeout: Optional[int], no_cache: bool):
    """Show software service logs."""
    _execute_software_action(ctx, 'logs', software, timeout, requires_confirmation=False, use_cache=not no_cache)


@cli.command()
@click.argument('software', required=True)
@click.option('--timeout', type=int, help='Command timeout in seconds')
@click.option('--no-cache', is_flag=True, help='Skip cache and perform fresh operations')
@click.pass_context
def version(ctx: click.Context, software: str, timeout: Optional[int], no_cache: bool):
    """Show software version information."""
    _execute_software_action(ctx, 'version', software, timeout, requires_confirmation=False, use_cache=not no_cache)


@cli.command()
@click.argument('action_file', type=click.Path(exists=True, path_type=Path))
@click.option('--parallel', is_flag=True, help='Execute actions in parallel when possible')
@click.option('--continue-on-error', is_flag=True, help='Continue executing remaining actions if one fails')
@click.option('--timeout', type=int, help='Default timeout for all actions in seconds')
@click.pass_context
def apply(ctx: click.Context, action_file: Path, parallel: bool, continue_on_error: bool, timeout: Optional[int]):
    """Apply multiple actions from an action file.
    
    Execute multiple software management actions defined in a YAML or JSON file.
    The action file should contain a 'config' section for execution options and
    an 'actions' section defining the operations to perform.
    
    Example action file:
    
    \b
    ---
    config:
      verbose: true
      dry_run: false
    actions:
      install:
        - nginx
        - name: docker
          provider: apt
      start:
        - nginx
    """
    try:
        from ..core.action_loader import ActionLoader, ActionFileError
        from ..core.action_executor import ActionExecutor
        from ..providers.loader import ProviderLoader
        from ..core.saidata_loader import SaidataLoader
        
        # Load and validate action file
        loader = ActionLoader()
        try:
            action_file_obj = loader.load_action_file(action_file)
        except ActionFileError as e:
            click.echo(f"Error loading action file: {e}", err=True)
            ctx.exit(1)
        
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
        
        # Sort provider instances by priority
        provider_instances.sort(key=lambda p: p.get_priority(), reverse=True)
        
        # Create execution engine and saidata loader
        engine = ExecutionEngine(provider_instances, ctx.obj['sai_config'])
        saidata_loader = SaidataLoader(ctx.obj['sai_config'])
        
        # Create action executor
        executor = ActionExecutor(engine, saidata_loader)
        
        # Prepare global configuration overrides from CLI options
        global_config = {}
        
        # Override with CLI global options
        if ctx.obj.get('verbose'):
            global_config['verbose'] = True
        if ctx.obj.get('dry_run'):
            global_config['dry_run'] = True
        if ctx.obj.get('yes'):
            global_config['yes'] = True
        if ctx.obj.get('quiet'):
            global_config['quiet'] = True
        if ctx.obj.get('provider'):
            global_config['provider'] = ctx.obj['provider']
        
        # Override with command-specific options
        if parallel:
            global_config['parallel'] = True
        if continue_on_error:
            global_config['continue_on_error'] = True
        if timeout:
            global_config['timeout'] = timeout
        
        # Show confirmation if not in quiet/yes mode and not dry run
        if (not ctx.obj['dry_run'] and not ctx.obj['yes'] and not ctx.obj['quiet']):
            total_actions = len(action_file_obj.actions.get_all_actions())
            click.echo(f"Will execute {total_actions} actions from {action_file}")
            
            # Show summary of actions
            action_summary = {}
            for action_type, item in action_file_obj.actions.get_all_actions():
                if action_type not in action_summary:
                    action_summary[action_type] = []
                software_name = item.name if hasattr(item, 'name') else str(item)
                action_summary[action_type].append(software_name)
            
            for action_type, items in action_summary.items():
                click.echo(f"  {action_type}: {', '.join(items)}")
            
            if not click.confirm("Continue?"):
                click.echo("Cancelled.")
                ctx.exit(0)
        
        # Execute actions
        result = executor.execute_action_file(action_file_obj, global_config)
        
        # Output results
        if ctx.obj['output_json']:
            import json
            output = {
                'success': result.success,
                'total_actions': result.total_actions,
                'successful_actions': result.successful_actions,
                'failed_actions': result.failed_actions,
                'success_rate': result.success_rate,
                'execution_time': result.execution_time,
                'results': []
            }
            
            for action_result in result.results:
                action_output = {
                    'action_type': action_result.action_type,
                    'software': action_result.software,
                    'success': action_result.success
                }
                
                if action_result.result:
                    action_output.update({
                        'provider_used': action_result.result.provider_used,
                        'commands_executed': action_result.result.commands_executed,
                        'execution_time': action_result.result.execution_time
                    })
                    
                    if action_result.result.stdout:
                        action_output['stdout'] = action_result.result.stdout
                    if action_result.result.stderr:
                        action_output['stderr'] = action_result.result.stderr
                
                if action_result.error:
                    action_output['error'] = action_result.error
                
                output['results'].append(action_output)
            
            click.echo(json.dumps(output, indent=2))
        else:
            # Human-readable output
            if result.success:
                if not ctx.obj['quiet']:
                    success_msg = f"✓ Successfully executed {result.successful_actions}/{result.total_actions} actions"
                    if result.failed_actions > 0:
                        success_msg += f" ({result.failed_actions} failed)"
                    click.echo(success_msg)
                    
                    if ctx.obj['verbose']:
                        click.echo(f"Execution time: {result.execution_time:.2f}s")
                        click.echo(f"Success rate: {result.success_rate:.1f}%")
                        
                        # Show individual results
                        for action_result in result.results:
                            status = "✓" if action_result.success else "✗"
                            click.echo(f"  {status} {action_result.action_type} {action_result.software}")
                            if not action_result.success and action_result.error:
                                click.echo(f"    Error: {action_result.error}")
            else:
                click.echo(f"✗ Action execution failed: {result.failed_actions}/{result.total_actions} actions failed", err=True)
                
                if ctx.obj['verbose']:
                    # Show failed actions
                    for action_result in result.results:
                        if not action_result.success:
                            click.echo(f"  ✗ {action_result.action_type} {action_result.software}: {action_result.error}", err=True)
                
                ctx.exit(1)
        
    except Exception as e:
        if ctx.obj['output_json']:
            import json
            error_output = {
                'success': False,
                'error': str(e),
                'error_type': e.__class__.__name__
            }
            click.echo(json.dumps(error_output, indent=2))
        else:
            error_msg = format_error_for_cli(e, ctx.obj['verbose'])
            click.echo(f"Error: {error_msg}", err=True)
        
        ctx.exit(1)


def _get_provider_package_info(provider, saidata):
    """Get package name and version information from a provider.
    
    Args:
        provider: Provider instance
        saidata: SaiData object
        
    Returns:
        Tuple of (package_name, version_info) or (None, None) if not available
    """
    try:
        # Try to resolve package name using template engine
        template_str = "{{sai_package(saidata, '" + provider.name + "')}}"
        package_name = provider.template_engine.resolve_template(template_str, saidata)
        if not package_name:
            package_name = saidata.metadata.name if saidata.metadata else None
        
        # Try to get version information if provider supports version action
        version_info = None
        if provider.has_action('version') and package_name:
            try:
                version_action = provider.get_action('version')
                if version_action and version_action.template:
                    version_command = provider.template_engine.resolve_template(version_action.template, saidata)
                    # For display purposes, we'll show a simplified version
                    version_info = f"version cmd available"
            except Exception:
                pass
        
        return package_name, version_info
    except Exception as e:
        # Return basic info even if template resolution fails
        package_name = saidata.metadata.name if saidata and saidata.metadata else None
        return package_name, None


def _execute_software_action(ctx: click.Context, action: str, software: str, 
                           timeout: Optional[int], requires_confirmation: bool = True, use_cache: bool = True):
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
            if provider_instance.is_available(use_cache=use_cache):
                provider_instances.append(provider_instance)
        
        # Sort provider instances by priority (highest first)
        provider_instances.sort(key=lambda p: p.get_priority(), reverse=True)
        
        if not provider_instances:
            click.echo("No available providers found.", err=True)
            ctx.exit(1)
        
        # Load saidata if software name is provided, or create minimal saidata
        saidata = None
        if software:
            try:
                saidata_loader = SaidataLoader(ctx.obj['sai_config'])
                saidata = saidata_loader.load_saidata(software, use_cache=use_cache)
            except SaidataNotFoundError:
                if not ctx.obj['quiet'] and ctx.obj['verbose']:
                    click.echo(f"Warning: No saidata found for '{software}', using basic execution", err=True)
                # Create minimal saidata
                from ..models.saidata import SaiData, Metadata
                saidata = SaiData(
                    version="0.2",
                    metadata=Metadata(name=software)
                )
        else:
            # Create minimal saidata for commands that don't require software name
            from ..models.saidata import SaiData, Metadata
            saidata = SaiData(
                version="0.2",
                metadata=Metadata(name="")
            )
        
        # Define informational actions that should run on all supporting providers
        informational_actions = {'info', 'status', 'search', 'list', 'logs', 'debug'}
        
        # Check if this is an informational action and no specific provider is requested
        if (action in informational_actions and not requires_confirmation and 
            not ctx.obj.get('provider')):
            # Execute on all providers that support this action
            _execute_informational_action_on_all_providers(
                ctx, action, software, timeout, provider_instances, saidata, use_cache
            )
            return
        
        # Create execution engine for single provider execution
        engine = ExecutionEngine(provider_instances, ctx.obj['sai_config'])
        
        # Create execution context
        execution_context = ExecutionContext(
            action=action,
            software=software,
            saidata=saidata,
            provider=ctx.obj.get('provider'),
            dry_run=ctx.obj['dry_run'],
            verbose=ctx.obj['verbose'],
            quiet=ctx.obj['quiet'],
            timeout=timeout
        )
        
        # Show confirmation if required and not in quiet/yes mode
        if (requires_confirmation and not ctx.obj['dry_run'] and 
            not ctx.obj['yes'] and not ctx.obj['quiet']):
            
            # Find suitable providers to show user
            # First filter by action support, then by ability to handle the software
            suitable_providers = [
                p for p in provider_instances 
                if p.has_action(action) and p.can_handle_software(action, saidata)
            ]
            
            # Sort providers by priority (highest first)
            suitable_providers.sort(key=lambda p: p.get_priority(), reverse=True)
            
            if not suitable_providers:
                # Check if any providers support the action at all
                action_providers = [p for p in provider_instances if p.has_action(action)]
                if action_providers:
                    click.echo(f"No providers can handle '{software}' for action '{action}'", err=True)
                    click.echo(f"Available providers for '{action}': {', '.join(p.name for p in action_providers)}", err=True)
                    click.echo(f"Hint: Check if '{software}' has packages available for these providers", err=True)
                else:
                    click.echo(f"No providers support action '{action}'", err=True)
                ctx.exit(1)
            
            if len(suitable_providers) == 1 or ctx.obj.get('provider'):
                # Single provider or forced provider
                selected = suitable_providers[0] if not ctx.obj.get('provider') else next(
                    (p for p in suitable_providers if p.name == ctx.obj['provider']), None
                )
                if not selected:
                    # Check if the provider exists but can't handle the software
                    requested_provider = next((p for p in provider_instances if p.name == ctx.obj['provider']), None)
                    if requested_provider:
                        if requested_provider.has_action(action):
                            click.echo(f"Provider '{ctx.obj['provider']}' cannot handle '{software}' for action '{action}'", err=True)
                            click.echo(f"Hint: Check if '{software}' has packages available for '{ctx.obj['provider']}'", err=True)
                        else:
                            click.echo(f"Provider '{ctx.obj['provider']}' does not support action '{action}'", err=True)
                    else:
                        click.echo(f"Requested provider '{ctx.obj['provider']}' not available", err=True)
                    ctx.exit(1)
                
                # Show what command will be executed
                try:
                    resolved = selected.resolve_action_templates(action, saidata, {})
                    if 'command' in resolved:
                        command_msg = format_command_execution(selected.name, resolved['command'], ctx.obj['verbose'])
                        click.echo(f"Will execute: {command_msg}")
                    elif 'steps' in resolved and resolved['steps']:
                        first_step = resolved['steps'][0]
                        if 'command' in first_step:
                            command_msg = format_command_execution(selected.name, first_step['command'], ctx.obj['verbose'])
                            click.echo(f"Will execute: {command_msg}")
                        else:
                            click.echo(f"Will execute: {action} {software} using {selected.name}")
                    else:
                        click.echo(f"Will execute: {action} {software} using {selected.name}")
                except Exception:
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
                    
                    # Get package information
                    package_name, version_info = _get_provider_package_info(provider, saidata)
                    
                    # Build display line
                    display_line = f"  {i}. {provider.name} (priority: {priority})"
                    if package_name:
                        display_line += f" - package: {package_name}"
                        if version_info:
                            display_line += f" ({version_info})"
                    display_line += default_marker
                    
                    click.echo(display_line)
                
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
                    # Show result output
                    if result.stdout:
                        click.echo(result.stdout.strip())
                    elif result.message and not result.message.startswith("Command executed successfully"):
                        # Always show dry run messages, otherwise only if verbose
                        if ctx.obj['verbose'] or result.dry_run:
                            click.echo(f"✓ {result.message}")
                    
                    if ctx.obj['verbose'] and result.commands_executed:
                        click.echo("Commands executed:")
                        for cmd in result.commands_executed:
                            click.echo(f"  {cmd}")
                    
                    # Add empty line at the end of output
                    click.echo()
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











def _convert_config_value(key: str, value: str, current_type: type):
    """Convert string value to appropriate type for configuration."""
    from ..models.config import LogLevel
    
    # Handle special cases
    if key == 'log_level':
        try:
            return LogLevel(value.lower())
        except ValueError:
            valid_levels = [level.value for level in LogLevel]
            raise ValueError(f"Invalid log level '{value}'. Valid levels: {', '.join(valid_levels)}")
    
    if key in ['cache_directory', 'log_file']:
        return Path(value)
    
    if key in ['saidata_paths', 'provider_paths']:
        # Handle list values - split by comma
        return [path.strip() for path in value.split(',')]
    
    if key == 'provider_priorities':
        # Handle dict values - format: "provider1:priority1,provider2:priority2"
        result = {}
        for pair in value.split(','):
            if ':' in pair:
                provider, priority = pair.split(':', 1)
                result[provider.strip()] = int(priority.strip())
        return result
    
    # Handle basic types
    if current_type == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    elif current_type == int:
        return int(value)
    elif current_type == float:
        return float(value)
    else:
        return value


def _execute_informational_action_on_all_providers(ctx: click.Context, action: str, 
                                                  software: str, timeout: Optional[int],
                                                  provider_instances: List, saidata, use_cache: bool = True):
    """Execute an informational action on all providers that support it."""
    from ..core.execution_engine import ExecutionEngine, ExecutionContext
    
    # Find providers that support this action
    supporting_providers = [
        p for p in provider_instances 
        if p.has_action(action)
    ]
    
    if not supporting_providers:
        click.echo(f"No providers support action '{action}'", err=True)
        ctx.exit(1)
    
    # Execute on each supporting provider
    results = []
    for provider in supporting_providers:
        try:
            # Commands will be shown by the execution engine before execution
            
            # Create execution engine with single provider
            engine = ExecutionEngine([provider], ctx.obj['sai_config'])
            
            # Create execution context
            execution_context = ExecutionContext(
                action=action,
                software=software,
                saidata=saidata,
                provider=provider.name,  # Force this specific provider
                dry_run=ctx.obj['dry_run'],
                verbose=ctx.obj['verbose'],
                quiet=ctx.obj['quiet'],
                timeout=timeout
            )
            
            # Execute the action
            result = engine.execute_action(execution_context)
            results.append((provider.name, result))
            
        except Exception as e:
            # Log error but continue with other providers
            if ctx.obj['verbose']:
                click.echo(f"Error executing {action} on provider {provider.name}: {e}", err=True)
            results.append((provider.name, None))
    
    # Output results
    if ctx.obj['output_json']:
        import json
        output = {
            'action': action,
            'software': software,
            'providers': []
        }
        
        for provider_name, result in results:
            provider_output = {
                'provider': provider_name,
                'success': result.success if result else False
            }
            
            if result:
                provider_output.update({
                    'status': result.status.value,
                    'message': result.message,
                    'commands_executed': result.commands_executed,
                    'execution_time': result.execution_time,
                    'dry_run': result.dry_run
                })
                
                if result.stdout:
                    provider_output['stdout'] = result.stdout
                if result.stderr:
                    provider_output['stderr'] = result.stderr
                if result.error_details:
                    provider_output['error_details'] = result.error_details
            else:
                provider_output['error'] = 'Execution failed'
            
            output['providers'].append(provider_output)
        
        click.echo(json.dumps(output, indent=2))
    else:
        # Human-readable output
        successful_results = [r for _, r in results if r and r.success]
        
        if not successful_results:
            click.echo(f"No providers successfully executed action '{action}'", err=True)
            ctx.exit(1)
        
        # Display results from all successful providers
        for provider_name, result in results:
            if result and result.success:
                if len(supporting_providers) > 1 and not ctx.obj['quiet']:
                    # Use styled separator for multiple providers
                    separator = click.style(f"--- {provider_name} ---", fg='green', bold=True)
                    click.echo(f"\n{separator}")
                
                if not ctx.obj['quiet']:
                    if result.stdout:
                        click.echo(result.stdout.strip())
                    elif result.message and result.message != f"Command executed successfully: {result.commands_executed[0] if result.commands_executed else ''}":
                        # Don't show generic success messages unless verbose
                        if ctx.obj['verbose'] or not result.message.startswith("Command executed successfully"):
                            click.echo(result.message)
                
                if ctx.obj['verbose'] and result.commands_executed:
                    click.echo("Commands executed:")
                    for cmd in result.commands_executed:
                        click.echo(f"  {cmd}")
                
                # Add empty line at the end of output
                if not ctx.obj['quiet']:
                    click.echo()
            elif ctx.obj['verbose'] and result:
                separator = click.style(f"--- {provider_name} (failed) ---", fg='red', bold=True)
                click.echo(f"\n{separator}")
                click.echo(f"✗ {result.message}", err=True)
                if result.error_details:
                    click.echo(f"Error details: {result.error_details}", err=True)
            elif not result and not ctx.obj['verbose']:
                # Show minimal error for failed providers when not verbose
                error_msg = click.style(f"✗ [{provider_name}] Failed", fg='red')
                click.echo(error_msg, err=True)


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
@click.argument('key', required=True, shell_complete=complete_config_keys)
@click.argument('value', required=True)
@click.option('--config-file', type=click.Path(path_type=Path), help='Specific config file to modify')
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str, config_file: Optional[Path]):
    """Set a configuration value."""
    try:
        from ..utils.config import get_config_manager
        
        # Get config manager
        config_manager = get_config_manager(config_file)
        current_config = config_manager.get_config()
        
        # Validate key exists
        if not hasattr(current_config, key):
            available_keys = [attr for attr in dir(current_config) if not attr.startswith('_')]
            click.echo(f"Error: Unknown configuration key '{key}'", err=True)
            click.echo(f"Available keys: {', '.join(sorted(available_keys))}", err=True)
            ctx.exit(1)
        
        # Convert value to appropriate type
        current_value = getattr(current_config, key)
        converted_value = _convert_config_value(key, value, type(current_value))
        
        # Update configuration
        updates = {key: converted_value}
        config_manager.update_config(updates)
        
        # Save configuration
        save_path = config_file or config_manager.DEFAULT_CONFIG_PATHS[0]
        config_manager.save_config(config_manager.get_config(), save_path)
        
        if ctx.obj['output_json']:
            import json
            output = {
                'success': True,
                'key': key,
                'old_value': str(current_value) if current_value is not None else None,
                'new_value': str(converted_value),
                'config_file': str(save_path)
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"✓ Set {key} = {converted_value}")
            click.echo(f"Configuration saved to: {save_path}")
    
    except Exception as e:
        error_msg = format_error_for_cli(e, ctx.obj['verbose'])
        click.echo(f"Error setting configuration: {error_msg}", err=True)
        ctx.exit(1)


@config.command('reset')
@click.argument('key', required=False, shell_complete=complete_config_keys)
@click.option('--all', 'reset_all', is_flag=True, help='Reset all configuration to defaults')
@click.option('--config-file', type=click.Path(path_type=Path), help='Specific config file to modify')
@click.pass_context
def config_reset(ctx: click.Context, key: Optional[str], reset_all: bool, config_file: Optional[Path]):
    """Reset configuration key(s) to default values."""
    try:
        from ..utils.config import get_config_manager
        from ..models.config import SaiConfig
        
        if not key and not reset_all:
            click.echo("Error: Must specify either a key or --all flag", err=True)
            ctx.exit(1)
        
        # Get config manager and current config
        config_manager = get_config_manager(config_file)
        current_config = config_manager.get_config()
        default_config = SaiConfig()
        
        if reset_all:
            if not ctx.obj['yes'] and not click.confirm("Reset all configuration to defaults?"):
                click.echo("Cancelled.")
                return
            
            # Save default configuration
            save_path = config_file or config_manager.DEFAULT_CONFIG_PATHS[0]
            config_manager.save_config(default_config, save_path)
            
            if ctx.obj['output_json']:
                import json
                output = {
                    'success': True,
                    'reset': 'all',
                    'config_file': str(save_path)
                }
                click.echo(json.dumps(output, indent=2))
            else:
                click.echo("✓ All configuration reset to defaults")
                click.echo(f"Configuration saved to: {save_path}")
        else:
            # Reset specific key
            if not hasattr(current_config, key):
                available_keys = [attr for attr in dir(current_config) if not attr.startswith('_')]
                click.echo(f"Error: Unknown configuration key '{key}'", err=True)
                click.echo(f"Available keys: {', '.join(sorted(available_keys))}", err=True)
                ctx.exit(1)
            
            old_value = getattr(current_config, key)
            default_value = getattr(default_config, key)
            
            # Update configuration
            updates = {key: default_value}
            config_manager.update_config(updates)
            
            # Save configuration
            save_path = config_file or config_manager.DEFAULT_CONFIG_PATHS[0]
            config_manager.save_config(config_manager.get_config(), save_path)
            
            if ctx.obj['output_json']:
                import json
                output = {
                    'success': True,
                    'key': key,
                    'old_value': str(old_value) if old_value is not None else None,
                    'new_value': str(default_value) if default_value is not None else None,
                    'config_file': str(save_path)
                }
                click.echo(json.dumps(output, indent=2))
            else:
                click.echo(f"✓ Reset {key} to default value: {default_value}")
                click.echo(f"Configuration saved to: {save_path}")
    
    except Exception as e:
        error_msg = format_error_for_cli(e, ctx.obj['verbose'])
        click.echo(f"Error resetting configuration: {error_msg}", err=True)
        ctx.exit(1)


@config.command('validate')
@click.option('--config-file', type=click.Path(exists=True, path_type=Path), help='Specific config file to validate')
@click.pass_context
def config_validate(ctx: click.Context, config_file: Optional[Path]):
    """Validate configuration file and settings."""
    try:
        from ..utils.config import get_config_manager
        
        # Get config manager
        config_manager = get_config_manager(config_file)
        
        # Load and validate configuration
        config = config_manager.get_config()
        issues = config_manager.validate_config()
        
        if ctx.obj['output_json']:
            import json
            output = {
                'valid': len(issues) == 0,
                'config_file': str(config_file) if config_file else 'default',
                'issues': issues
            }
            click.echo(json.dumps(output, indent=2))
        else:
            if issues:
                click.echo("Configuration validation issues found:", err=True)
                for issue in issues:
                    click.echo(f"  ⚠ {issue}", err=True)
                ctx.exit(1)
            else:
                click.echo("✓ Configuration is valid")
    
    except Exception as e:
        error_msg = format_error_for_cli(e, ctx.obj['verbose'])
        click.echo(f"Error validating configuration: {error_msg}", err=True)
        ctx.exit(1)


@config.command('paths')
@click.pass_context
def config_paths(ctx: click.Context):
    """Show configuration file search paths."""
    from ..utils.config import ConfigManager
    
    config_manager = ConfigManager()
    current_path = config_manager._find_config_file()
    
    if ctx.obj['output_json']:
        import json
        output = {
            'search_paths': [str(path) for path in config_manager.DEFAULT_CONFIG_PATHS],
            'current_config': str(current_path) if current_path else None
        }
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo("Configuration file search paths:")
        for i, path in enumerate(config_manager.DEFAULT_CONFIG_PATHS, 1):
            exists = "✓" if path.exists() else "✗"
            current = " (current)" if path == current_path else ""
            click.echo(f"  {i}. {path} {exists}{current}")


# Validation command
@cli.command()
@click.argument('saidata_files', nargs=-1, type=click.Path(exists=True))
@click.option('--strict', is_flag=True, help='Treat warnings as errors')
@click.pass_context
def validate(ctx: click.Context, saidata_files: tuple, strict: bool):
    """Validate saidata file(s) against the schema."""
    try:
        if not saidata_files:
            click.echo("No files specified for validation", err=True)
            click.echo("Usage: sai validate <file1> [file2] ...")
            ctx.exit(1)
        
        saidata_loader = SaidataLoader(ctx.obj['sai_config'])
        
        # Validate each file
        results = []
        total_valid = 0
        total_errors = 0
        total_warnings = 0
        
        for file_path_str in saidata_files:
            file_path = Path(file_path_str)
            try:
                # Load and validate the file
                import yaml
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
                
                validation_result = saidata_loader.validate_saidata(data)
                
                file_result = {
                    'file': str(file_path),
                    'valid': validation_result.valid,
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings
                }
                
                results.append(file_result)
                
                if validation_result.valid and (not strict or len(validation_result.warnings) == 0):
                    total_valid += 1
                
                total_errors += len(validation_result.errors)
                total_warnings += len(validation_result.warnings)
                
            except Exception as e:
                file_result = {
                    'file': str(file_path),
                    'valid': False,
                    'errors': [f"Failed to load file: {e}"],
                    'warnings': []
                }
                results.append(file_result)
                total_errors += 1
        
        # Output results
        if ctx.obj['output_json']:
            import json
            output = {
                'total_files': len(saidata_files),
                'valid_files': total_valid,
                'total_errors': total_errors,
                'total_warnings': total_warnings,
                'strict_mode': strict,
                'results': results
            }
            click.echo(json.dumps(output, indent=2))
        else:
            # Human-readable output
            click.echo(f"Validated {len(saidata_files)} file(s)")
            click.echo(f"Valid: {total_valid}, Errors: {total_errors}, Warnings: {total_warnings}")
            
            if strict and total_warnings > 0:
                click.echo("(Warnings treated as errors in strict mode)")
            
            click.echo()
            
            for result in results:
                file_path = result['file']
                
                if result['valid'] and (not strict or len(result['warnings']) == 0):
                    click.echo(f"✓ {file_path}")
                else:
                    click.echo(f"✗ {file_path}", err=True)
                
                # Show errors
                for error in result['errors']:
                    click.echo(f"  ✗ {error}", err=True)
                
                # Show warnings
                for warning in result['warnings']:
                    if strict:
                        click.echo(f"  ✗ {warning} (warning treated as error)", err=True)
                    else:
                        click.echo(f"  ⚠ {warning}")
        
        # Exit with error if any validation failed
        failed_files = len(saidata_files) - total_valid
        if strict:
            failed_files = sum(1 for r in results if not r['valid'] or len(r['warnings']) > 0)
        
        if failed_files > 0:
            ctx.exit(1)
    
    except Exception as e:
        if ctx.obj['output_json']:
            import json
            error_output = {
                'success': False,
                'error': str(e),
                'files': list(saidata_files) if saidata_files else []
            }
            click.echo(json.dumps(error_output, indent=2))
        else:
            click.echo(f"Error during validation: {e}", err=True)
        
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


# Configuration management commands
@cli.group()
def config():
    """Configuration management commands."""
    pass


@config.command('show')
@click.option('--key', help='Show specific configuration key')
@click.pass_context
def config_show(ctx: click.Context, key: Optional[str]):
    """Show current configuration."""
    try:
        from ..utils.config import get_config_manager
        
        config_manager = get_config_manager(ctx.obj.get('config_path'))
        sai_config = config_manager.get_config()
        
        if ctx.obj['output_json']:
            import json
            config_dict = sai_config.model_dump(exclude_none=True)
            
            # Convert Path objects and enums to strings for JSON serialization
            def convert_for_json(obj):
                if hasattr(obj, '__class__') and 'Path' in obj.__class__.__name__:
                    return str(obj)
                elif hasattr(obj, 'value'):  # Handle enums
                    return obj.value
                elif type(obj).__name__ == 'dict':
                    return {k: convert_for_json(v) for k, v in obj.items()}
                elif type(obj).__name__ == 'list':
                    return [convert_for_json(item) for item in obj]
                else:
                    return obj
            
            config_dict = convert_for_json(config_dict)
            
            if key:
                if key in config_dict:
                    click.echo(json.dumps({key: config_dict[key]}, indent=2))
                else:
                    click.echo(json.dumps({'error': f'Configuration key "{key}" not found'}, indent=2))
                    ctx.exit(1)
            else:
                click.echo(json.dumps(config_dict, indent=2))
        else:
            # Human-readable output
            if key:
                if hasattr(sai_config, key):
                    value = getattr(sai_config, key)
                    if hasattr(value, '__class__') and 'Path' in value.__class__.__name__:
                        value = str(value)
                    elif hasattr(value, 'value'):  # Handle enums
                        value = value.value
                    click.echo(f"{key}: {value}")
                else:
                    click.echo(f"Configuration key '{key}' not found", err=True)
                    ctx.exit(1)
            else:
                click.echo("Current Configuration:")
                click.echo("=" * 50)
                
                config_dict = sai_config.model_dump(exclude_none=True)
                for config_key, value in config_dict.items():
                    # Handle Path objects by checking the type name to avoid import issues
                    if hasattr(value, '__class__') and 'Path' in value.__class__.__name__:
                        value = str(value)
                    elif hasattr(value, 'value'):  # Handle enums
                        value = value.value
                    elif type(value).__name__ == 'list':
                        value = ', '.join(str(item) for item in value)
                    elif type(value).__name__ == 'dict':
                        value = ', '.join(f"{k}:{v}" for k, v in value.items())
                    
                    click.echo(f"{config_key}: {value}")
    
    except Exception as e:
        error_msg = format_error_for_cli(e, ctx.obj['verbose'])
        click.echo(f"Error showing configuration: {error_msg}", err=True)
        ctx.exit(1)


@config.command('set')
@click.argument('key', shell_complete=complete_config_keys)
@click.argument('value')
@click.option('--save', is_flag=True, help='Save configuration to file')
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str, save: bool):
    """Set configuration value."""
    try:
        from ..utils.config import get_config_manager
        
        config_manager = get_config_manager(ctx.obj.get('config_path'))
        sai_config = config_manager.get_config()
        
        # Validate key exists
        if not hasattr(sai_config, key):
            click.echo(f"Unknown configuration key: {key}", err=True)
            click.echo("Available keys:", err=True)
            for attr in dir(sai_config):
                if not attr.startswith('_') and not callable(getattr(sai_config, attr)):
                    click.echo(f"  {attr}", err=True)
            ctx.exit(1)
        
        # Get current value type for conversion
        current_value = getattr(sai_config, key)
        current_type = type(current_value)
        
        # Convert value to appropriate type
        try:
            converted_value = _convert_config_value(key, value, current_type)
        except ValueError as e:
            click.echo(f"Invalid value for {key}: {e}", err=True)
            ctx.exit(1)
        
        # Update configuration
        config_manager.update_config({key: converted_value})
        
        # Save if requested
        if save:
            config_manager.save_config(config_manager.get_config())
            click.echo(f"✓ Configuration saved: {key} = {converted_value}")
        else:
            click.echo(f"✓ Configuration updated: {key} = {converted_value}")
            click.echo("Use --save to persist changes to file")
    
    except Exception as e:
        error_msg = format_error_for_cli(e, ctx.obj['verbose'])
        click.echo(f"Error setting configuration: {error_msg}", err=True)
        ctx.exit(1)


@config.command('validate')
@click.pass_context
def config_validate(ctx: click.Context):
    """Validate current configuration."""
    try:
        from ..utils.config import get_config_manager
        
        config_manager = get_config_manager(ctx.obj.get('config_path'))
        issues = config_manager.validate_config()
        
        if ctx.obj['output_json']:
            import json
            output = {
                'valid': len(issues) == 0,
                'issues': issues
            }
            click.echo(json.dumps(output, indent=2))
        else:
            if not issues:
                click.echo("✓ Configuration is valid")
            else:
                click.echo("Configuration issues found:", err=True)
                for issue in issues:
                    click.echo(f"  • {issue}", err=True)
                ctx.exit(1)
    
    except Exception as e:
        error_msg = format_error_for_cli(e, ctx.obj['verbose'])
        click.echo(f"Error validating configuration: {error_msg}", err=True)
        ctx.exit(1)


# Saidata validation command
@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path), shell_complete=complete_saidata_files)
@click.option('--detailed', '-d', is_flag=True, help='Show detailed validation information')
@click.pass_context
def validate(ctx: click.Context, file: Path, detailed: bool):
    """Validate saidata file against schema."""
    try:
        from ..core.saidata_loader import SaidataLoader
        
        # Load the file content
        saidata_loader = SaidataLoader(ctx.obj['sai_config'])
        
        try:
            file_data = saidata_loader._load_saidata_file(file)
        except ValueError as e:
            if ctx.obj['output_json']:
                import json
                output = {
                    'valid': False,
                    'file': str(file),
                    'errors': [f"Failed to load file: {e}"],
                    'warnings': []
                }
                click.echo(json.dumps(output, indent=2))
            else:
                click.echo(f"✗ Failed to load file: {e}", err=True)
            ctx.exit(1)
        
        # Validate the data
        validation_result = saidata_loader.validate_saidata(file_data)
        
        if ctx.obj['output_json']:
            import json
            output = {
                'valid': validation_result.valid,
                'file': str(file),
                'errors': validation_result.errors,
                'warnings': validation_result.warnings
            }
            click.echo(json.dumps(output, indent=2))
        else:
            # Human-readable output
            if validation_result.valid:
                click.echo(f"✓ {file} is valid")
                if validation_result.warnings and detailed:
                    click.echo("Warnings:")
                    for warning in validation_result.warnings:
                        click.echo(f"  ⚠ {warning}")
            else:
                click.echo(f"✗ {file} validation failed", err=True)
                if validation_result.errors:
                    click.echo("Errors:", err=True)
                    for error in validation_result.errors:
                        click.echo(f"  • {error}", err=True)
                
                if validation_result.warnings and detailed:
                    click.echo("Warnings:", err=True)
                    for warning in validation_result.warnings:
                        click.echo(f"  ⚠ {warning}", err=True)
                
                ctx.exit(1)
        
        # Try to create SaiData object if validation passed
        if validation_result.valid and detailed:
            try:
                from ..models.saidata import SaiData
                saidata = SaiData(**file_data)
                
                if not ctx.obj['output_json']:
                    click.echo(f"✓ Successfully created SaiData object")
                    click.echo(f"  Software: {saidata.metadata.name}")
                    if saidata.packages:
                        click.echo(f"  Packages: {len(saidata.packages)}")
                    if saidata.services:
                        click.echo(f"  Services: {len(saidata.services)}")
                    if saidata.providers:
                        click.echo(f"  Provider configs: {len(saidata.providers)}")
            except Exception as e:
                if ctx.obj['output_json']:
                    # Update JSON output with model creation error
                    import json
                    output = json.loads(click.get_text_stream('stdout').getvalue().split('\n')[-2])
                    output['model_creation_error'] = str(e)
                    click.echo(json.dumps(output, indent=2))
                else:
                    click.echo(f"⚠ Warning: Could not create SaiData object: {e}")
    
    except Exception as e:
        if ctx.obj['output_json']:
            import json
            error_output = {
                'valid': False,
                'file': str(file),
                'error': str(e),
                'error_type': e.__class__.__name__
            }
            click.echo(json.dumps(error_output, indent=2))
        else:
            error_msg = format_error_for_cli(e, ctx.obj['verbose'])
            click.echo(f"Error validating file: {error_msg}", err=True)
        ctx.exit(1)


# Cache management commands
@cli.group()
def cache():
    """Manage cache for performance optimization."""
    pass


@cache.command('status')
@click.pass_context
def cache_status(ctx: click.Context):
    """Show comprehensive cache status and statistics."""
    try:
        from ..utils.cache import CacheManager
        
        cache_manager = CacheManager(ctx.obj['sai_config'])
        cache_info = cache_manager.get_comprehensive_status()
        
        if ctx.obj['output_json']:
            import json
            click.echo(json.dumps(cache_info, indent=2))
        else:
            click.echo("Cache Status:")
            click.echo(f"  Cache Directory: {cache_info['cache_directory']}")
            click.echo(f"  Cache Enabled: {cache_info['cache_enabled']}")
            click.echo(f"  Cache TTL: {cache_info['cache_ttl_hours']:.1f} hours")
            click.echo(f"  Total Cache Size: {cache_info['total_cache_size_mb']:.2f} MB")
            
            # Provider cache details
            provider_cache = cache_info['provider_cache']
            click.echo(f"\n  Provider Cache:")
            click.echo(f"    Size: {provider_cache['cache_size_mb']:.2f} MB")
            click.echo(f"    Cached Providers: {provider_cache['total_cached_providers']}")
            
            if provider_cache['cached_providers']:
                click.echo("    Providers:")
                for provider in provider_cache['cached_providers']:
                    status = "✓" if provider['available'] else "✗"
                    expired = " (expired)" if provider['expired'] else ""
                    age = f"{provider['age_hours']:.1f}h"
                    click.echo(f"      {status} {provider['name']} - {age} ago{expired}")
            
            # Saidata cache details
            saidata_cache = cache_info['saidata_cache']
            click.echo(f"\n  Saidata Cache:")
            click.echo(f"    Size: {saidata_cache['cache_size_mb']:.2f} MB")
            click.echo(f"    Cached Saidata: {saidata_cache['total_cached_saidata']}")
            
            if saidata_cache['cached_saidata']:
                click.echo("    Saidata:")
                for saidata in saidata_cache['cached_saidata']:
                    expired = " (expired)" if saidata['expired'] else ""
                    age = f"{saidata['age_hours']:.1f}h"
                    click.echo(f"      {saidata['software_name']} - {age} ago{expired}")
    
    except Exception as e:
        if ctx.obj['output_json']:
            import json
            error_output = {'error': str(e), 'error_type': e.__class__.__name__}
            click.echo(json.dumps(error_output, indent=2))
        else:
            click.echo(f"Error getting cache status: {e}", err=True)
        
        if ctx.obj['verbose']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        
        ctx.exit(1)


@cache.command('clear')
@click.option('--provider', '-p', help='Clear cache for specific provider only')
@click.option('--saidata', '-s', help='Clear cache for specific saidata only')
@click.option('--all', 'clear_all', is_flag=True, help='Clear all cache data')
@click.pass_context
def cache_clear(ctx: click.Context, provider: Optional[str], saidata: Optional[str], clear_all: bool):
    """Clear cache data."""
    try:
        from ..utils.cache import CacheManager
        
        cache_manager = CacheManager(ctx.obj['sai_config'])
        
        if clear_all:
            # Clear all caches
            results = cache_manager.clear_all_caches()
            
            if ctx.obj['output_json']:
                import json
                click.echo(json.dumps(results, indent=2))
            else:
                total_cleared = results['total_cleared']
                if total_cleared > 0:
                    if not ctx.obj['quiet']:
                        click.echo(f"✓ Cleared {results['provider_cache_cleared']} provider cache entries")
                        click.echo(f"✓ Cleared {results['saidata_cache_cleared']} saidata cache entries")
                        click.echo(f"✓ Total cleared: {total_cleared} entries")
                else:
                    click.echo("No cache data found to clear")
        
        elif provider:
            # Clear cache for specific provider
            cleared = cache_manager.provider_cache.clear_provider_cache(provider)
            
            if ctx.obj['output_json']:
                import json
                click.echo(json.dumps({'provider': provider, 'cleared': cleared}, indent=2))
            else:
                if cleared:
                    if not ctx.obj['quiet']:
                        click.echo(f"✓ Cleared cache for provider '{provider}'")
                else:
                    click.echo(f"No cache found for provider '{provider}'", err=True)
                    ctx.exit(1)
        
        elif saidata:
            # Clear cache for specific saidata
            cleared = cache_manager.saidata_cache.clear_saidata_cache(saidata)
            
            if ctx.obj['output_json']:
                import json
                click.echo(json.dumps({'saidata': saidata, 'cleared': cleared}, indent=2))
            else:
                if cleared > 0:
                    if not ctx.obj['quiet']:
                        click.echo(f"✓ Cleared {cleared} cache entries for saidata '{saidata}'")
                else:
                    click.echo(f"No cache found for saidata '{saidata}'", err=True)
                    ctx.exit(1)
        
        else:
            click.echo("Please specify --provider, --saidata, or --all to clear cache", err=True)
            ctx.exit(1)
    
    except Exception as e:
        if ctx.obj['output_json']:
            import json
            error_output = {'error': str(e), 'error_type': e.__class__.__name__}
            click.echo(json.dumps(error_output, indent=2))
        else:
            click.echo(f"Error clearing cache: {e}", err=True)
        
        if ctx.obj['verbose']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        
        ctx.exit(1)


@cache.command('cleanup')
@click.pass_context
def cache_cleanup(ctx: click.Context):
    """Clean up expired cache entries."""
    try:
        from ..utils.cache import CacheManager
        
        cache_manager = CacheManager(ctx.obj['sai_config'])
        results = cache_manager.cleanup_all_expired()
        
        if ctx.obj['output_json']:
            import json
            click.echo(json.dumps(results, indent=2))
        else:
            total_cleaned = results['total_cleaned']
            if total_cleaned > 0:
                if not ctx.obj['quiet']:
                    click.echo(f"✓ Cleaned up {results['provider_cache_cleaned']} expired provider cache entries")
                    click.echo(f"✓ Cleaned up {results['saidata_cache_cleaned']} expired saidata cache entries")
                    click.echo(f"✓ Total cleaned: {total_cleaned} entries")
            else:
                if not ctx.obj['quiet']:
                    click.echo("No expired cache entries found")
    
    except Exception as e:
        if ctx.obj['output_json']:
            import json
            error_output = {'error': str(e), 'error_type': e.__class__.__name__}
            click.echo(json.dumps(error_output, indent=2))
        else:
            click.echo(f"Error cleaning up cache: {e}", err=True)
        
        if ctx.obj['verbose']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        
        ctx.exit(1)


def main():
    """Main entry point."""
    cli()