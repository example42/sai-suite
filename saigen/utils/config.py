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
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = config.dict(exclude_none=True)
        
        if save_path.suffix.lower() == '.json':
            with open(save_path, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
        else:
            with open(save_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
    
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
        with open(path, 'r') as f:
            if path.suffix.lower() == '.json':
                return json.load(f)
            else:
                return yaml.safe_load(f) or {}
    
    def _create_default_config(self) -> SaigenConfig:
        """Create default configuration."""
        return SaigenConfig()
    
    def _load_env_overrides(self) -> None:
        """Load configuration overrides from environment variables."""
        if not self._config:
            return
        
        # LLM provider API keys
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            if 'openai' not in self._config.llm_providers:
                self._config.llm_providers['openai'] = LLMConfig(provider='openai')
            self._config.llm_providers['openai'].api_key = openai_key
        
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            if 'anthropic' not in self._config.llm_providers:
                self._config.llm_providers['anthropic'] = LLMConfig(provider='anthropic')
            self._config.llm_providers['anthropic'].api_key = anthropic_key
        
        # Other environment overrides
        if os.getenv('SAIGEN_LOG_LEVEL'):
            self._config.log_level = os.getenv('SAIGEN_LOG_LEVEL')
        
        if os.getenv('SAIGEN_CACHE_DIR'):
            self._config.cache.directory = Path(os.getenv('SAIGEN_CACHE_DIR'))
        
        if os.getenv('SAIGEN_OUTPUT_DIR'):
            self._config.generation.output_directory = Path(os.getenv('SAIGEN_OUTPUT_DIR'))
    
    def get_config(self) -> SaigenConfig:
        """Get current configuration."""
        return self.load_config()
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        if not self._config:
            self.load_config()
        
        # Apply updates (simplified - in practice would need deep merge)
        for key, value in updates.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
    
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