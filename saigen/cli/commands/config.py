"""Config command for saigen CLI."""

from pathlib import Path
from typing import Optional

import click


@click.group()
@click.pass_context
def config(ctx: click.Context):
    """Manage saigen configuration.
    
    View current settings, update configuration values, and validate
    configuration files.
    """
    pass


@config.command('show')
@click.option('--format', 'output_format', type=click.Choice(['yaml', 'json']), 
              default='yaml', help='Output format')
@click.option('--section', help='Show only specific configuration section')
@click.pass_context
def config_show(ctx: click.Context, output_format: str, section: Optional[str]):
    """Show current configuration."""
    import yaml
    import json
    
    config_obj = ctx.obj['config']
    masked_config = config_obj.get_masked_config()
    
    # Filter to specific section if requested
    if section:
        if section in masked_config:
            display_config = {section: masked_config[section]}
        else:
            click.echo(f"Configuration section '{section}' not found", err=True)
            available_sections = list(masked_config.keys())
            click.echo(f"Available sections: {', '.join(available_sections)}", err=True)
            ctx.exit(1)
    else:
        display_config = masked_config
    
    click.echo("Current configuration:")
    if output_format == 'json':
        click.echo(json.dumps(display_config, indent=2, default=str))
    else:
        # Convert Path objects and enums to strings for cleaner YAML output
        def convert_objects(obj):
            if isinstance(obj, dict):
                return {k: convert_objects(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_objects(item) for item in obj]
            elif hasattr(obj, '__fspath__'):  # Path-like objects
                return str(obj)
            elif hasattr(obj, 'value'):  # Enum objects
                return obj.value
            else:
                return obj
        
        clean_config = convert_objects(display_config)
        click.echo(yaml.dump(clean_config, default_flow_style=False))


@config.command('set')
@click.argument('key')
@click.argument('value')
@click.option('--type', 'value_type', type=click.Choice(['string', 'int', 'float', 'bool']),
              default='string', help='Value type for proper conversion')
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str, value_type: str):
    """Set a configuration value.
    
    Use dot notation for nested keys (e.g., 'llm_providers.openai.model').
    
    Examples:
        saigen config set generation.default_providers "apt,brew"
        saigen config set cache.max_size_mb 2000 --type int
        saigen config set rag.enabled true --type bool
    """
    config_manager = ctx.obj['config_manager']
    verbose = ctx.obj['verbose']
    
    # Convert value based on type
    try:
        if value_type == 'int':
            converted_value = int(value)
        elif value_type == 'float':
            converted_value = float(value)
        elif value_type == 'bool':
            converted_value = value.lower() in ('true', '1', 'yes', 'on')
        else:
            converted_value = value
    except ValueError as e:
        click.echo(f"Error converting value to {value_type}: {e}", err=True)
        ctx.exit(1)
    
    if verbose:
        click.echo(f"Setting {key} = {converted_value} ({value_type})")
    
    try:
        # This is a simplified implementation - a full implementation would
        # need to handle nested key setting properly
        config_manager.update_config({key: converted_value})
        config_manager.save_config(config_manager.get_config())
        click.echo(f"Configuration updated: {key} = {converted_value}")
    except Exception as e:
        click.echo(f"Error updating configuration: {e}", err=True)
        ctx.exit(1)


@config.command('validate')
@click.pass_context
def config_validate(ctx: click.Context):
    """Validate current configuration."""
    config_manager = ctx.obj['config_manager']
    
    click.echo("Validating configuration...")
    issues = config_manager.validate_config()
    
    if not issues:
        click.echo("✓ Configuration is valid")
    else:
        click.echo("Configuration issues found:")
        for issue in issues:
            click.echo(f"  ✗ {issue}")
        ctx.exit(1)


@config.command('init')
@click.option('--force', is_flag=True, help='Overwrite existing configuration')
@click.pass_context
def config_init(ctx: click.Context, force: bool):
    """Initialize a new configuration file."""
    from ...models.config import SaigenConfig
    
    config_manager = ctx.obj['config_manager']
    config_path = config_manager.DEFAULT_CONFIG_PATHS[0]
    
    if config_path.exists() and not force:
        click.echo(f"Configuration file already exists: {config_path}")
        click.echo("Use --force to overwrite")
        ctx.exit(1)
    
    # Create default configuration
    default_config = SaigenConfig()
    
    try:
        config_manager.save_config(default_config, config_path)
        click.echo(f"Configuration initialized: {config_path}")
        click.echo("Edit the file to add your API keys and customize settings.")
    except Exception as e:
        click.echo(f"Error creating configuration: {e}", err=True)
        ctx.exit(1)


if __name__ == '__main__':
    config()