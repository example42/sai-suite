"""Auto-completion support for sai CLI."""

import click
from typing import List, Optional
from pathlib import Path

from ..providers.loader import ProviderLoader
from ..core.saidata_loader import SaidataLoader
from ..utils.config import get_config


def complete_software_names(ctx: click.Context, param: click.Parameter, incomplete: str) -> List[str]:
    """Complete software names from available saidata files."""
    try:
        config = get_config()
        saidata_loader = SaidataLoader(config)
        search_paths = saidata_loader.get_search_paths()
        
        software_names = set()
        for path in search_paths:
            if path.exists() and path.is_dir():
                for saidata_file in path.glob("*.yaml"):
                    name = saidata_file.stem
                    if name.startswith(incomplete):
                        software_names.add(name)
                
                for saidata_file in path.glob("*.yml"):
                    name = saidata_file.stem
                    if name.startswith(incomplete):
                        software_names.add(name)
        
        return sorted(list(software_names))
    except Exception:
        return []


def complete_provider_names(ctx: click.Context, param: click.Parameter, incomplete: str) -> List[str]:
    """Complete provider names from available providers."""
    try:
        provider_loader = ProviderLoader()
        providers = provider_loader.load_all_providers()
        
        provider_names = [
            name for name in providers.keys()
            if name.startswith(incomplete)
        ]
        
        return sorted(provider_names)
    except Exception:
        return []


def complete_action_names(ctx: click.Context, param: click.Parameter, incomplete: str) -> List[str]:
    """Complete action names from available provider actions."""
    try:
        provider_loader = ProviderLoader()
        providers = provider_loader.load_all_providers()
        
        actions = set()
        for provider_data in providers.values():
            from ..providers.base import BaseProvider
            provider_instance = BaseProvider(provider_data)
            if provider_instance.is_available():
                actions.update(provider_instance.get_supported_actions())
        
        return sorted([action for action in actions if action.startswith(incomplete)])
    except Exception:
        return []


def complete_config_keys(ctx: click.Context, param: click.Parameter, incomplete: str) -> List[str]:
    """Complete configuration keys."""
    config_keys = [
        'log_level',
        'cache_enabled',
        'cache_directory',
        'default_provider',
        'action_timeout',
        'require_confirmation',
        'dry_run_default',
        'max_concurrent_actions'
    ]
    
    return [key for key in config_keys if key.startswith(incomplete)]


def complete_log_levels(ctx: click.Context, param: click.Parameter, incomplete: str) -> List[str]:
    """Complete log level values."""
    log_levels = ['debug', 'info', 'warning', 'error']
    return [level for level in log_levels if level.startswith(incomplete)]


def complete_saidata_files(ctx: click.Context, param: click.Parameter, incomplete: str) -> List[str]:
    """Complete saidata file paths."""
    try:
        # Complete files in current directory and common saidata paths
        paths_to_check = [Path('.')]
        
        try:
            config = get_config()
            paths_to_check.extend([Path(p) for p in config.saidata_paths])
        except Exception:
            pass
        
        completions = []
        for base_path in paths_to_check:
            if not base_path.exists():
                continue
            
            # Complete YAML files
            for pattern in ['*.yaml', '*.yml']:
                for file_path in base_path.glob(pattern):
                    file_str = str(file_path)
                    if file_str.startswith(incomplete):
                        completions.append(file_str)
        
        return sorted(completions)
    except Exception:
        return []