"""Configuration management utilities for sai CLI tool."""

import os
import json
import yaml
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import ValidationError

from ..models.config import SaiConfig


class ConfigManager:
    """Manages sai CLI configuration loading and saving."""
    
    DEFAULT_CONFIG_PATHS = [
        Path.home() / ".sai" / "config.yaml",
        Path.home() / ".sai" / "config.json",
        Path.cwd() / ".sai.yaml",
        Path.cwd() / ".sai.json",
        Path.cwd() / "sai.yaml",
        Path.cwd() / "sai.json",
    ]
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager."""
        self.config_path = config_path
        self._config: Optional[SaiConfig] = None
    
    def load_config(self) -> SaiConfig:
        """Load configuration from file or create default."""
        if self._config is not None:
            return self._config
        
        config_path = self._find_config_file()
        
        if config_path and config_path.exists():
            try:
                config_data = self._load_config_file(config_path)
                self._config = SaiConfig(**config_data)
            except (ValidationError, Exception) as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")
                self._config = self._create_default_config()
        else:
            self._config = self._create_default_config()
        
        # Load environment variables
        self._load_env_overrides()
        
        return self._config
    
    def save_config(self, config: SaiConfig, path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        save_path = path or self.config_path or self.DEFAULT_CONFIG_PATHS[0]
        
        # Ensure parent directory exists with secure permissions
        save_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        config_data = config.dict(exclude_none=True)
        
        # Convert Path objects and enums to strings for serialization
        def convert_for_serialization(obj):
            if isinstance(obj, Path):
                return str(obj)
            elif hasattr(obj, 'value'):  # Handle enums
                return obj.value
            elif isinstance(obj, dict):
                return {k: convert_for_serialization(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_serialization(item) for item in obj]
            else:
                return obj
        
        config_data = convert_for_serialization(config_data)
        
        try:
            if save_path.suffix.lower() == '.json':
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, default=str)
            else:
                with open(save_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False)
            
            # Set secure file permissions (readable only by owner)
            save_path.chmod(0o600)
        except (IOError, OSError) as e:
            raise ValueError(f"Failed to save configuration to {save_path}: {e}")
    
    def _find_config_file(self) -> Optional[Path]:
        """Find the first existing configuration file."""
        if self.config_path:
            return self.config_path
        
        for path in self.DEFAULT_CONFIG_PATHS:
            if path.exists():
                return path
        
        return None
    
    def _load_config_file(self, path: Path) -> Dict[str, Any]:
        """Load configuration data from file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    # Use safe_load to prevent code execution
                    return yaml.safe_load(f) or {}
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValueError(f"Invalid configuration file format in {path}: {e}")
        except UnicodeDecodeError as e:
            raise ValueError(f"Configuration file encoding error in {path}: {e}")
    
    def _create_default_config(self) -> SaiConfig:
        """Create default configuration."""
        return SaiConfig()
    
    def _load_env_overrides(self) -> None:
        """Load configuration overrides from environment variables."""
        if not self._config:
            return
        
        # Environment overrides for sai CLI
        env_overrides = {
            'SAI_LOG_LEVEL': lambda val: setattr(self._config, 'log_level', val),
            'SAI_CACHE_DIR': lambda val: setattr(self._config, 'cache_directory', Path(val)),
            'SAI_DEFAULT_PROVIDER': lambda val: setattr(self._config, 'default_provider', val),
            'SAI_REQUIRE_CONFIRMATION': lambda val: setattr(self._config, 'require_confirmation', val.lower() == 'true'),
            
            # Repository configuration overrides
            'SAI_REPOSITORY_URL': lambda val: setattr(self._config, 'saidata_repository_url', val),
            'SAI_REPOSITORY_BRANCH': lambda val: setattr(self._config, 'saidata_repository_branch', val),
            'SAI_REPOSITORY_AUTH_TYPE': lambda val: setattr(self._config, 'saidata_repository_auth_type', val),
            'SAI_AUTO_UPDATE': lambda val: setattr(self._config, 'saidata_auto_update', val.lower() == 'true'),
            'SAI_UPDATE_INTERVAL': lambda val: setattr(self._config, 'saidata_update_interval', int(val)),
            'SAI_OFFLINE_MODE': lambda val: setattr(self._config, 'saidata_offline_mode', val.lower() == 'true'),
            'SAI_REPOSITORY_CACHE_DIR': lambda val: setattr(self._config, 'saidata_repository_cache_dir', Path(val)),
            'SAI_SHALLOW_CLONE': lambda val: setattr(self._config, 'saidata_shallow_clone', val.lower() == 'true'),
            'SAI_REPOSITORY_TIMEOUT': lambda val: setattr(self._config, 'saidata_repository_timeout', int(val)),
        }
        
        for env_var, setter in env_overrides.items():
            value = os.getenv(env_var)
            if value:
                try:
                    setter(value)
                except (ValueError, TypeError) as e:
                    print(f"Warning: Invalid value for {env_var}: {value} ({e})")
    
    def get_config(self) -> SaiConfig:
        """Get current configuration."""
        return self.load_config()
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        if not self._config:
            self.load_config()
        
        # Apply updates with proper validation
        for key, value in updates.items():
            if hasattr(self._config, key):
                # Handle special cases for complex types
                if key == 'provider_priorities' and isinstance(value, dict):
                    # Merge with existing priorities
                    current_priorities = getattr(self._config, key) or {}
                    current_priorities.update(value)
                    setattr(self._config, key, current_priorities)
                elif key in ['saidata_paths', 'provider_paths'] and isinstance(value, list):
                    # Replace the entire list
                    setattr(self._config, key, value)
                else:
                    setattr(self._config, key, value)
            else:
                raise ValueError(f"Unknown configuration key: {key}")
    
    def validate_config(self) -> List[str]:
        """Validate current configuration and return any issues."""
        issues = []
        config = self.get_config()
        
        # Check cache directory permissions
        try:
            config.cache_directory.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            issues.append(f"Cannot create cache directory: {config.cache_directory}")
        
        # Check repository cache directory permissions
        try:
            config.saidata_repository_cache_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            issues.append(f"Cannot create repository cache directory: {config.saidata_repository_cache_dir}")
        
        # Validate repository URL format
        try:
            # This will trigger the validator
            from ..models.config import SaiConfig
            SaiConfig.validate_repository_url(config.saidata_repository_url)
        except ValueError as e:
            issues.append(f"Invalid repository URL: {e}")
        
        # Check repository authentication configuration
        if config.saidata_repository_auth_type and not config.saidata_repository_auth_data:
            issues.append("Repository authentication type specified but no authentication data provided")
        
        # Validate update interval and timeout
        if config.saidata_update_interval < 60:
            issues.append("Repository update interval is too short (minimum 60 seconds)")
        
        if config.saidata_repository_timeout < 10:
            issues.append("Repository timeout is too short (minimum 10 seconds)")
        
        # Check saidata paths exist (repository cache path gets priority)
        saidata_paths_exist = False
        for path_str in config.saidata_paths:
            path = Path(path_str)
            if path.exists():
                saidata_paths_exist = True
                break
        
        if not saidata_paths_exist and not config.saidata_auto_update:
            issues.append("No saidata paths exist and auto-update is disabled - you may need to initialize saidata or enable auto-update")
        
        return issues


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[Path] = None) -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None or config_path is not None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


def get_config() -> SaiConfig:
    """Get current configuration."""
    return get_config_manager().get_config()