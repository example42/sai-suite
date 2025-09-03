"""Base provider class and factory for SAI CLI tool."""

import logging
from typing import Dict, List

from ..models.provider_data import ProviderData
from .loader import ProviderLoader


logger = logging.getLogger(__name__)


class BaseProvider:
    """Base class for all providers."""
    
    def __init__(self, provider_data: ProviderData):
        """Initialize provider with data from YAML file.
        
        Args:
            provider_data: Validated provider data from YAML
        """
        self.provider_data = provider_data
        self.name = provider_data.provider.name
        self.display_name = provider_data.provider.display_name or self.name
        self.description = provider_data.provider.description
        self.type = provider_data.provider.type
        self.platforms = provider_data.provider.platforms or []
        self.capabilities = provider_data.provider.capabilities or []
    
    def get_supported_actions(self) -> List[str]:
        """Return actions defined in provider YAML.
        
        Returns:
            List of supported action names
        """
        return list(self.provider_data.actions.keys())
    
    def has_action(self, action: str) -> bool:
        """Check if provider supports a specific action.
        
        Args:
            action: Action name to check
            
        Returns:
            True if action is supported
        """
        return action in self.provider_data.actions
    
    def get_priority(self) -> int:
        """Return provider priority.
        
        Returns:
            Provider priority (higher = more preferred), defaults to 50
        """
        # Priority can be added to the provider data model later
        # For now, return a default priority
        return 50
    
    def __str__(self) -> str:
        """String representation of the provider."""
        return f"{self.display_name} ({self.name})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the provider."""
        return (
            f"BaseProvider(name='{self.name}', type='{self.type}', "
            f"platforms={self.platforms}, actions={len(self.get_supported_actions())})"
        )


class ProviderFactory:
    """Factory for creating provider instances."""
    
    def __init__(self, loader: ProviderLoader):
        """Initialize the factory with a provider loader.
        
        Args:
            loader: ProviderLoader instance for loading provider data
        """
        self.loader = loader
    
    def create_providers(self, additional_directories: List = None) -> List[BaseProvider]:
        """Dynamically create providers from YAML files.
        
        Args:
            additional_directories: Additional directories to search for providers
            
        Returns:
            List of BaseProvider instances
        """
        logger.info("Creating providers from YAML files")
        
        provider_data_dict = self.loader.load_all_providers(additional_directories)
        providers = []
        
        for name, provider_data in provider_data_dict.items():
            try:
                provider = BaseProvider(provider_data)
                providers.append(provider)
                logger.debug(f"Created provider: {provider}")
                
            except Exception as e:
                logger.error(f"Failed to create provider '{name}': {e}")
                # Continue with other providers
        
        logger.info(f"Successfully created {len(providers)} providers")
        return providers
    
    @classmethod
    def create_default_factory(cls) -> 'ProviderFactory':
        """Create a factory with default configuration.
        
        Returns:
            ProviderFactory instance with default loader
        """
        loader = ProviderLoader()
        return cls(loader)