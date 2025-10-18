"""Config command for saigen CLI."""

from pathlib import Path
from typing import Any, Optional

import click


def _set_nested_value(obj: Any, key: str, value: Any) -> None:
    """Set a nested value using dot notation.

    Args:
        obj: The object to modify
        key: Dot-separated key path (e.g., 'llm_providers.openai.max_retries')
        value: The value to set
    """
    keys = key.split(".")
    current = obj

    # Navigate to the parent of the target key
    for k in keys[:-1]:
        if hasattr(current, k):
            current = getattr(current, k)
        elif isinstance(current, dict) and k in current:
            current = current[k]
        else:
            raise ValueError(f"Configuration path '{'.'.join(keys[:keys.index(k) + 1])}' not found")

    # Set the final value
    final_key = keys[-1]
    if hasattr(current, final_key):
        setattr(current, final_key, value)
    elif isinstance(current, dict):
        current[final_key] = value
    else:
        raise ValueError(f"Cannot set '{final_key}' on {type(current).__name__}")


@click.group()
@click.pass_context
def config(ctx: click.Context):
    """Manage saigen configuration.

    View current settings, update configuration values, and validate
    configuration files.
    """


@config.command("show")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format",
)
@click.option("--section", help="Show only specific configuration section")
@click.pass_context
def config_show(ctx: click.Context, output_format: str, section: Optional[str]):
    """Show current configuration."""
    import json

    import yaml

    config_obj = ctx.obj["config"]
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
    if output_format == "json":
        click.echo(json.dumps(display_config, indent=2, default=str))
    else:
        # Convert Path objects and enums to strings for cleaner YAML output
        def convert_objects(obj):
            if isinstance(obj, dict):
                return {k: convert_objects(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_objects(item) for item in obj]
            elif hasattr(obj, "__fspath__"):  # Path-like objects
                return str(obj)
            elif hasattr(obj, "value"):  # Enum objects
                return obj.value
            else:
                return obj

        clean_config = convert_objects(display_config)
        click.echo(yaml.dump(clean_config, default_flow_style=False))


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.option(
    "--type",
    "value_type",
    type=click.Choice(["string", "int", "float", "bool"]),
    default="string",
    help="Value type for proper conversion",
)
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str, value_type: str):
    """Set a configuration value.

    Use dot notation for nested keys (e.g., 'llm_providers.openai.model').

    Examples:
        saigen config set generation.default_providers "apt,brew"
        saigen config set cache.max_size_mb 2000 --type int
        saigen config set rag.enabled true --type bool
    """
    config_manager = ctx.obj["config_manager"]
    verbose = ctx.obj["verbose"]

    # Convert value based on type
    try:
        if value_type == "int":
            converted_value = int(value)
        elif value_type == "float":
            converted_value = float(value)
        elif value_type == "bool":
            converted_value = value.lower() in ("true", "1", "yes", "on")
        else:
            converted_value = value
    except ValueError as e:
        click.echo(f"Error converting value to {value_type}: {e}", err=True)
        ctx.exit(1)

    if verbose:
        click.echo(f"Setting {key} = {converted_value} ({value_type})")

    try:
        # Handle nested key setting using dot notation
        config_obj = config_manager.get_config()
        _set_nested_value(config_obj, key, converted_value)
        config_manager.save_config(config_obj)
        click.echo(f"Configuration updated: {key} = {converted_value}")
    except Exception as e:
        click.echo(f"Error updating configuration: {e}", err=True)
        ctx.exit(1)


@config.command("validate")
@click.pass_context
def config_validate(ctx: click.Context):
    """Validate current configuration."""
    config_manager = ctx.obj["config_manager"]

    click.echo("Validating configuration...")
    issues = config_manager.validate_config()

    if not issues:
        click.echo("✓ Configuration is valid")
    else:
        click.echo("Configuration issues found:")
        for issue in issues:
            click.echo(f"  ✗ {issue}")
        ctx.exit(1)


@config.command("init")
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.pass_context
def config_init(ctx: click.Context, force: bool):
    """Initialize a new configuration file."""
    from ...models.config import SaigenConfig

    config_manager = ctx.obj["config_manager"]
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


@config.command("samples")
@click.option(
    "--directory",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Set custom sample directory path",
)
@click.option("--auto-detect", is_flag=True, help="Auto-detect sample directory")
@click.option("--disable", is_flag=True, help="Disable use of sample data")
@click.pass_context
def config_samples(ctx: click.Context, directory: Optional[Path], auto_detect: bool, disable: bool):
    """Configure sample saidata directory for LLM examples.

    The sample directory contains reference saidata files that are used as
    examples in LLM prompts to improve generation quality and consistency.

    Examples:
        saigen config samples --auto-detect
        saigen config samples --directory /path/to/samples
        saigen config samples --disable
    """
    from ...utils.config import configure_sample_directory, setup_default_sample_directory

    config_manager = ctx.obj["config_manager"]
    config_obj = config_manager.get_config()
    verbose = ctx.obj["verbose"]

    if disable:
        # Disable sample data usage
        config_obj.rag.use_default_samples = False
        config_obj.rag.default_samples_directory = None
        config_manager.save_config(config_obj)
        click.echo("Sample data usage disabled")
        return

    if directory:
        # Set custom directory
        if not directory.exists():
            click.echo(f"Directory does not exist: {directory}", err=True)
            ctx.exit(1)

        # Check if directory contains YAML files (including subdirectories)
        yaml_files = list(directory.glob("**/*.yaml")) + list(directory.glob("**/*.yml"))
        if not yaml_files:
            click.echo(f"Warning: No YAML files found in {directory}")

        configure_sample_directory(directory, config_obj)
        config_obj.rag.use_default_samples = True
        config_manager.save_config(config_obj)

        click.echo(f"Sample directory configured: {directory}")
        if verbose and yaml_files:
            click.echo(f"Found {len(yaml_files)} sample files:")
            for yaml_file in yaml_files[:5]:  # Show first 5
                click.echo(f"  - {yaml_file.name}")
            if len(yaml_files) > 5:
                click.echo(f"  ... and {len(yaml_files) - 5} more")

    elif auto_detect:
        # Auto-detect sample directory
        sample_dir = setup_default_sample_directory(config_obj)

        if sample_dir.exists():
            yaml_files = list(sample_dir.glob("**/*.yaml")) + list(sample_dir.glob("**/*.yml"))
            config_obj.rag.use_default_samples = True
            config_manager.save_config(config_obj)

            click.echo(f"Auto-detected sample directory: {sample_dir}")
            if yaml_files:
                click.echo(f"Found {len(yaml_files)} sample files")
                if verbose:
                    for yaml_file in yaml_files[:5]:
                        click.echo(f"  - {yaml_file.name}")
                    if len(yaml_files) > 5:
                        click.echo(f"  ... and {len(yaml_files) - 5} more")
            else:
                click.echo("Warning: No sample files found in detected directory")
        else:
            click.echo(f"Could not auto-detect sample directory. Tried:")
            click.echo(f"  - docs/saidata_samples (relative to current directory)")
            click.echo(f"  - ../docs/saidata_samples")
            click.echo(f"Use --directory to specify a custom path")
            ctx.exit(1)

    else:
        # Show current configuration
        current_dir = config_obj.rag.default_samples_directory
        use_samples = config_obj.rag.use_default_samples

        click.echo("Current sample configuration:")
        click.echo(f"  Use samples: {use_samples}")
        click.echo(f"  Directory: {current_dir or 'Not configured'}")

        if current_dir and Path(current_dir).exists():
            yaml_files = list(Path(current_dir).glob("**/*.yaml")) + list(
                Path(current_dir).glob("**/*.yml")
            )
            # Filter out README files
            yaml_files = [
                f
                for f in yaml_files
                if f.name.lower() != "readme.yaml" and f.name.lower() != "readme.yml"
            ]
            click.echo(f"  Available samples: {len(yaml_files)}")
            if verbose and yaml_files:
                click.echo("\n  Sample files:")
                for yaml_file in sorted(yaml_files):
                    # Show relative path from sample directory
                    rel_path = yaml_file.relative_to(current_dir)
                    click.echo(f"    - {rel_path}")
        elif current_dir:
            click.echo(f"  Status: Directory not found")

        if not use_samples:
            click.echo("\nSample data is currently disabled.")
            click.echo("Use --auto-detect or --directory to enable.")
        elif not current_dir:
            click.echo("\nNo sample directory configured.")
            click.echo("Use --auto-detect to find samples automatically.")
            click.echo("Use --directory to specify a custom path.")


if __name__ == "__main__":
    config()
