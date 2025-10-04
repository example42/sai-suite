"""Configuration management utilities."""

import os
import json
import yaml
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import ValidationError

from ..models.config import SaigenConfig, LLMConfig, RepositoryConfig


class ConfigManager:
    """Manages saigen configuration loading and saving."""
    
    DEFAULT_CONFIG_PATHS = [
        Path.home() / ".saigen" / "config.yaml",
        Path.home() / ".saigen" / "config.json",
        Path.cwd() / ".saigen.yaml",
        Path.cwd() / ".saigen.json",
        Path.cwd() / "saigen.yaml",
        Path.cwd() / "saigen.json",
    ]
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager."""
        self.config_path = config_path
        self._config: Optional[SaigenConfig] = None
    
    def load_config(self) -> SaigenConfig:
        """Load configuration from file or create default."""
        if self._config is not None:
            return self._config
        
        config_path = self._find_config_file()
        
        if config_path and config_path.exists():
            try:
                config_data = self._load_config_file(config_path)
                self._config = SaigenConfig(**config_data)
            except (ValidationError, Exception) as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")
                self._config = self._create_default_config()
        else:
            self._config = self._create_default_config()
        
        # Load environment variables
        self._load_env_overrides()
        
        return self._config
    
    def save_config(self, config: SaigenConfig, path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        save_path = path or self.config_path or self.DEFAULT_CONFIG_PATHS[0]
        
        # Ensure parent directory exists with secure permissions
        save_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        config_data = config.model_dump(exclude_none=True)
        
        # Convert objects for serialization
        def convert_for_serialization(obj):
            if isinstance(obj, dict):
                return {k: convert_for_serialization(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_serialization(item) for item in obj]
            elif hasattr(obj, '__fspath__'):  # Path-like objects
                return str(obj)
            elif hasattr(obj, 'value'):  # Enum objects
                return obj.value
            elif hasattr(obj, 'get_secret_value'):  # SecretStr objects
                return obj.get_secret_value()
            else:
                return obj
        
        clean_config_data = convert_for_serialization(config_data)
        
        try:
            if save_path.suffix.lower() == '.json':
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(clean_config_data, f, indent=2, default=str)
            else:
                with open(save_path, 'w', encoding='utf-8') as f:
                    yaml.dump(clean_config_data, f, default_flow_style=False)
            
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
                    # First try safe_load
                    try:
                        data = yaml.safe_load(f) or {}
                        return self._fix_secret_str_values(data)
                    except yaml.constructor.ConstructorError as e:
                        # If safe_load fails due to Python objects, try to fix the file content
                        if 'SecretStr' in str(e):
                            f.seek(0)
                            content = f.read()
                            fixed_content = self._fix_secret_str_yaml(content)
                            data = yaml.safe_load(fixed_content) or {}
                            return self._fix_secret_str_values(data)
                        else:
                            raise
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValueError(f"Invalid configuration file format in {path}: {e}")
        except UnicodeDecodeError as e:
            raise ValueError(f"Configuration file encoding error in {path}: {e}")
    
    def _fix_secret_str_yaml(self, content: str) -> str:
        """Fix SecretStr YAML serialization in file content.
        
        Args:
            content: YAML file content with SecretStr objects
            
        Returns:
            Fixed YAML content
        """
        import re
        
        # Pattern to match SecretStr YAML objects and extract the secret value
        pattern = r'!!python/object:pydantic\.types\.SecretStr\s*\n\s*_secret_value:\s*(.+)'
        
        def replace_secret_str(match):
            secret_value = match.group(1).strip()
            return secret_value
        
        return re.sub(pattern, replace_secret_str, content)
    
    def _fix_secret_str_values(self, data: Any) -> Any:
        """Fix SecretStr serialization issues in loaded data.
        
        Args:
            data: Configuration data that may contain SecretStr objects
            
        Returns:
            Fixed configuration data
        """
        if isinstance(data, dict):
            # Check for SecretStr object patterns
            if '_secret_value' in data and len(data) == 1:
                # This looks like a serialized SecretStr, extract the value
                return data['_secret_value']
            else:
                # Recursively fix nested dictionaries
                return {k: self._fix_secret_str_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            # Recursively fix list items
            return [self._fix_secret_str_values(item) for item in data]
        else:
            return data
    
    def _fix_secret_str_values(self, data: Any) -> Any:
        """Fix SecretStr serialization issues in loaded data.
        
        Args:
            data: Configuration data that may contain SecretStr objects
            
        Returns:
            Fixed configuration data
        """
        if isinstance(data, dict):
            # Check for SecretStr object patterns
            if '_secret_value' in data and len(data) == 1:
                # This looks like a serialized SecretStr, extract the value
                return data['_secret_value']
            else:
                # Recursively fix nested dictionaries
                return {k: self._fix_secret_str_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            # Recursively fix list items
            return [self._fix_secret_str_values(item) for item in data]
        else:
            return data
    
    def _create_default_config(self) -> SaigenConfig:
        """Create default configuration."""
        return SaigenConfig()
    
    def _load_env_overrides(self) -> None:
        """Load configuration overrides from environment variables."""
        if not self._config:
            return
        
        # LLM provider API keys - use a mapping for cleaner code
        llm_env_mapping = {
            'OPENAI_API_KEY': ('openai', 'openai'),
            'ANTHROPIC_API_KEY': ('anthropic', 'anthropic'),
        }
        
        for env_var, (provider_key, provider_name) in llm_env_mapping.items():
            api_key = os.getenv(env_var)
            if api_key:
                if provider_key not in self._config.llm_providers:
                    self._config.llm_providers[provider_key] = LLMConfig(provider=provider_name)
                self._config.llm_providers[provider_key].api_key = api_key
        
        # Other environment overrides - use mapping for better maintainability
        env_overrides = {
            'SAIGEN_LOG_LEVEL': lambda val: setattr(self._config, 'log_level', val),
            'SAIGEN_CACHE_DIR': lambda val: setattr(self._config.cache, 'directory', Path(val)),
            'SAIGEN_OUTPUT_DIR': lambda val: setattr(self._config.generation, 'output_directory', Path(val)),
        }
        
        for env_var, setter in env_overrides.items():
            value = os.getenv(env_var)
            if value:
                setter(value)
    
    def get_config(self) -> SaigenConfig:
        """Get current configuration."""
        return self.load_config()
    
    def validate_config(self) -> List[str]:
        """Validate current configuration and return any issues."""
        issues = []
        config = self.get_config()
        
        # Check for required API keys
        if not config.llm_providers:
            issues.append("No LLM providers configured")
        else:
            for name, provider in config.llm_providers.items():
                if provider.enabled and not provider.api_key:
                    issues.append(f"LLM provider '{name}' is enabled but missing API key")
        
        # Check cache directory permissions
        try:
            config.cache.directory.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            issues.append(f"Cannot create cache directory: {config.cache.directory}")
        
        return issues


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[Path] = None) -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None or config_path is not None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


def get_config() -> SaigenConfig:
    """Get current configuration."""
    return get_config_manager().get_config()


def setup_default_sample_directory(config: Optional[SaigenConfig] = None) -> Path:
    """Set up and return the default sample directory path.
    
    Args:
        config: Optional configuration to update
        
    Returns:
        Path to the default sample directory
    """
    if config is None:
        config = get_config()
    
    # If already configured, return it
    if config.rag.default_samples_directory:
        return Path(config.rag.default_samples_directory)
    
    # Try to find docs/saidata_samples relative to current working directory
    import os
    cwd = Path(os.getcwd())
    potential_paths = [
        cwd / "docs" / "saidata_samples",
        cwd.parent / "docs" / "saidata_samples",
        Path(__file__).parent.parent.parent / "docs" / "saidata_samples"
    ]
    
    for path in potential_paths:
        if path.exists() and path.is_dir():
            # Update configuration
            config.rag.default_samples_directory = path
            return path
    
    # Default fallback - create in user's config directory
    default_path = Path.home() / ".saigen" / "samples"
    config.rag.default_samples_directory = default_path
    return default_path


def configure_sample_directory(sample_dir: Path, config: Optional[SaigenConfig] = None) -> None:
    """Configure the sample directory in the configuration.
    
    Args:
        sample_dir: Path to the sample directory
        config: Optional configuration to update
    """
    if config is None:
        config = get_config()
    
    config.rag.default_samples_directory = sample_dir
    
    # Save the updated configuration
    config_manager = get_config_manager()
    config_manager.save_config(config)