"""Configuration loader for saitest.

This module provides utilities for loading and accessing saitest configuration.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging


logger = logging.getLogger(__name__)


# Default configuration values
DEFAULT_CONFIG = {
    "containers": {
        "timeout": 600,
        "pull_timeout": 600,
        "startup_timeout": 30,
        "max_concurrent": 4,
    },
    "verification": {
        "filesystem": {
            "scan_timeout": 120,
            "max_depth": 10,
            "monitored_paths": [],
        }
    }
}


class ConfigLoader:
    """Load and manage saitest configuration.
    
    Configuration is loaded from:
    1. Default config.yaml in saitest package
    2. User config at ~/.saitest/config.yaml (if exists)
    3. Environment variables (SAITEST_*)
    
    Attributes:
        config: Loaded configuration dictionary
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize config loader.
        
        Args:
            config_path: Optional path to custom config file
        """
        self.config = DEFAULT_CONFIG.copy()
        self._load_config(config_path)
    
    def _load_config(self, config_path: Optional[str] = None) -> None:
        """Load configuration from file and environment.
        
        Args:
            config_path: Optional path to custom config file
        """
        # Try to load default config from package
        default_config_path = Path(__file__).parent.parent / "config.yaml"
        if default_config_path.exists():
            try:
                with open(default_config_path) as f:
                    default_config = yaml.safe_load(f)
                    if default_config:
                        self._deep_merge(self.config, default_config)
                        logger.debug(f"Loaded default config from {default_config_path}")
            except Exception as e:
                logger.warning(f"Failed to load default config: {e}")
        
        # Try to load user config
        user_config_path = Path.home() / ".saitest" / "config.yaml"
        if user_config_path.exists():
            try:
                with open(user_config_path) as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self._deep_merge(self.config, user_config)
                        logger.debug(f"Loaded user config from {user_config_path}")
            except Exception as e:
                logger.warning(f"Failed to load user config: {e}")
        
        # Load custom config if provided
        if config_path:
            config_file = Path(config_path)
            if config_file.exists():
                try:
                    with open(config_file) as f:
                        custom_config = yaml.safe_load(f)
                        if custom_config:
                            self._deep_merge(self.config, custom_config)
                            logger.debug(f"Loaded custom config from {config_path}")
                except Exception as e:
                    logger.warning(f"Failed to load custom config: {e}")
        
        # Override with environment variables
        self._load_env_overrides()
    
    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """Deep merge override dict into base dict.
        
        Args:
            base: Base dictionary to merge into
            override: Override dictionary to merge from
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _load_env_overrides(self) -> None:
        """Load configuration overrides from environment variables."""
        # Container timeouts
        if "SAITEST_CONTAINER_TIMEOUT" in os.environ:
            try:
                self.config["containers"]["timeout"] = int(
                    os.environ["SAITEST_CONTAINER_TIMEOUT"]
                )
            except ValueError:
                logger.warning("Invalid SAITEST_CONTAINER_TIMEOUT value")
        
        if "SAITEST_PULL_TIMEOUT" in os.environ:
            try:
                self.config["containers"]["pull_timeout"] = int(
                    os.environ["SAITEST_PULL_TIMEOUT"]
                )
            except ValueError:
                logger.warning("Invalid SAITEST_PULL_TIMEOUT value")
        
        if "SAITEST_STARTUP_TIMEOUT" in os.environ:
            try:
                self.config["containers"]["startup_timeout"] = int(
                    os.environ["SAITEST_STARTUP_TIMEOUT"]
                )
            except ValueError:
                logger.warning("Invalid SAITEST_STARTUP_TIMEOUT value")
        
        # Filesystem scan timeout
        if "SAITEST_SCAN_TIMEOUT" in os.environ:
            try:
                self.config["verification"]["filesystem"]["scan_timeout"] = int(
                    os.environ["SAITEST_SCAN_TIMEOUT"]
                )
            except ValueError:
                logger.warning("Invalid SAITEST_SCAN_TIMEOUT value")
        
        # Filesystem max depth
        if "SAITEST_MAX_DEPTH" in os.environ:
            try:
                self.config["verification"]["filesystem"]["max_depth"] = int(
                    os.environ["SAITEST_MAX_DEPTH"]
                )
            except ValueError:
                logger.warning("Invalid SAITEST_MAX_DEPTH value")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key path.
        
        Args:
            key_path: Dot-separated key path (e.g., "containers.timeout")
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        
        Example:
            >>> config = ConfigLoader()
            >>> timeout = config.get("containers.timeout", 600)
        """
        keys = key_path.split(".")
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value


# Global config instance
_config_instance: Optional[ConfigLoader] = None


def get_config(config_path: Optional[str] = None) -> ConfigLoader:
    """Get or create global config instance.
    
    Args:
        config_path: Optional path to custom config file
    
    Returns:
        ConfigLoader instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader(config_path)
    return _config_instance


def reset_config() -> None:
    """Reset global config instance.
    
    Useful for testing or reloading configuration.
    """
    global _config_instance
    _config_instance = None
