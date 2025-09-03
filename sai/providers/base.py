"""Base provider class and factory for SAI CLI tool."""

import logging
from typing import Dict, List, Optional

from ..models.provider_data import ProviderData, Action
from ..utils.system import (
    is_executable_available, 
    get_executable_path, 
    get_executable_version,
    check_executable_functionality,
    is_platform_supported
)
from .loader import ProviderLoader
from .template_engine import TemplateEngine, TemplateResolutionError
from saigen.models.saidata import SaiData


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
        self.template_engine = TemplateEngine()
    
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
    
    def is_available(self) -> bool:
        """Check if provider is available on the current system.
        
        This checks:
        1. Platform compatibility
        2. Required executables are available
        3. Provider functionality (if test command is defined)
        
        Returns:
            True if provider is available and functional
        """
        try:
            # Check platform compatibility
            if not is_platform_supported(self.platforms):
                logger.debug(f"Provider '{self.name}' not supported on current platform")
                return False
            
            # Get the main executable for this provider
            main_executable = self._get_main_executable()
            if not main_executable:
                logger.debug(f"Provider '{self.name}' has no main executable defined")
                return False
            
            # Check if main executable is available
            if not is_executable_available(main_executable):
                logger.debug(f"Provider '{self.name}' executable '{main_executable}' not found")
                return False
            
            # Run functionality test if defined
            if not self._test_functionality():
                logger.debug(f"Provider '{self.name}' failed functionality test")
                return False
            
            logger.debug(f"Provider '{self.name}' is available")
            return True
            
        except Exception as e:
            logger.warning(f"Error checking availability for provider '{self.name}': {e}")
            return False
    
    def get_executable_path(self) -> Optional[str]:
        """Get the full path to the provider's main executable.
        
        Returns:
            Full path to executable if available, None otherwise
        """
        main_executable = self._get_main_executable()
        if main_executable:
            return get_executable_path(main_executable)
        return None
    
    def get_version(self) -> Optional[str]:
        """Get version information for the provider.
        
        Returns:
            Version string if available, None otherwise
        """
        main_executable = self._get_main_executable()
        if main_executable:
            return get_executable_version(main_executable)
        return None
    
    def _get_main_executable(self) -> Optional[str]:
        """Get the main executable name for this provider.
        
        This looks for executable information in the provider data.
        Different provider types may store this information differently.
        
        Returns:
            Main executable name if found, None otherwise
        """
        # Cache the result to avoid repeated computation
        if hasattr(self, '_cached_executable'):
            return self._cached_executable
        
        # Check if there's a direct executable field (not in current schema but might be added)
        if hasattr(self.provider_data.provider, 'executable'):
            self._cached_executable = self.provider_data.provider.executable
            return self._cached_executable
        
        # Look for executable in action commands (prioritize common actions)
        priority_actions = ['install', 'list', 'info', 'search']
        for action_name in priority_actions:
            if action_name in self.provider_data.actions:
                action = self.provider_data.actions[action_name]
                if action.command:
                    command_parts = action.command.strip().split()
                    if command_parts:
                        self._cached_executable = command_parts[0]
                        return self._cached_executable
        
        # Look for executable in any action commands
        for action_name, action in self.provider_data.actions.items():
            if action.command:
                command_parts = action.command.strip().split()
                if command_parts:
                    self._cached_executable = command_parts[0]
                    return self._cached_executable
        
        # Look for executable in action steps
        for action_name, action in self.provider_data.actions.items():
            if action.steps:
                for step in action.steps:
                    if step.command:
                        command_parts = step.command.strip().split()
                        if command_parts:
                            self._cached_executable = command_parts[0]
                            return self._cached_executable
        
        # If no executable found, use provider name as fallback
        logger.debug(f"No explicit executable found for provider '{self.name}', using provider name")
        self._cached_executable = self.name
        return self._cached_executable
    
    def _test_functionality(self) -> bool:
        """Test provider functionality using validation commands.
        
        Returns:
            True if functionality test passes or no test is defined
        """
        # Look for validation commands in actions
        for action_name, action in self.provider_data.actions.items():
            if action.validation and action.validation.command:
                test_command = action.validation.command.strip().split()
                expected_exit_code = action.validation.expected_exit_code
                timeout = action.validation.timeout
                
                logger.debug(f"Testing provider '{self.name}' with validation command: {test_command}")
                
                # Use the first validation command we find
                return check_executable_functionality(
                    test_command[0] if test_command else self._get_main_executable(),
                    test_command,
                    expected_exit_code,
                    timeout
                )
        
        # If no validation command is defined, assume functionality is OK
        # if the executable exists (which we already checked)
        return True
    
    def __str__(self) -> str:
        """String representation of the provider."""
        return f"{self.display_name} ({self.name})"
    
    def resolve_action_templates(self, action_name: str, saidata: SaiData, 
                               additional_context: Optional[Dict] = None) -> Dict[str, str]:
        """Resolve templates for a specific action.
        
        Args:
            action_name: Name of the action to resolve
            saidata: SaiData object for template context
            additional_context: Additional template variables
            
        Returns:
            Dictionary with resolved template values
            
        Raises:
            ValueError: If action is not supported
            TemplateResolutionError: If template resolution fails
        """
        if not self.has_action(action_name):
            raise ValueError(f"Action '{action_name}' not supported by provider '{self.name}'")
        
        action = self.provider_data.actions[action_name]
        
        try:
            return self.template_engine.resolve_action_template(action, saidata, additional_context)
        except TemplateResolutionError as e:
            logger.error(f"Failed to resolve templates for action '{action_name}' in provider '{self.name}': {e}")
            raise
    
    def resolve_template(self, template_str: str, saidata: SaiData,
                        additional_context: Optional[Dict] = None) -> str:
        """Resolve a single template string.
        
        Args:
            template_str: Template string to resolve
            saidata: SaiData object for template context
            additional_context: Additional template variables
            
        Returns:
            Resolved template string
            
        Raises:
            TemplateResolutionError: If template resolution fails
        """
        try:
            return self.template_engine.resolve_template(template_str, saidata, additional_context)
        except TemplateResolutionError as e:
            logger.error(f"Failed to resolve template in provider '{self.name}': {e}")
            raise
    
    def get_action(self, action_name: str) -> Optional[Action]:
        """Get action definition by name.
        
        Args:
            action_name: Name of the action
            
        Returns:
            Action object if found, None otherwise
        """
        return self.provider_data.actions.get(action_name)
    
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
    
    def create_available_providers(self, additional_directories: List = None) -> List[BaseProvider]:
        """Create providers and filter to only those available on the current system.
        
        Args:
            additional_directories: Additional directories to search for providers
            
        Returns:
            List of available BaseProvider instances
        """
        logger.info("Creating and detecting available providers")
        
        all_providers = self.create_providers(additional_directories)
        available_providers = []
        
        for provider in all_providers:
            try:
                if provider.is_available():
                    available_providers.append(provider)
                    logger.info(f"Provider '{provider.name}' is available")
                else:
                    logger.debug(f"Provider '{provider.name}' is not available")
                    
            except Exception as e:
                logger.error(f"Error checking availability for provider '{provider.name}': {e}")
                # Continue with other providers
        
        logger.info(f"Found {len(available_providers)} available providers out of {len(all_providers)} total")
        return available_providers
    
    def detect_providers(self, additional_directories: List = None) -> Dict[str, Dict[str, any]]:
        """Detect all providers and return detailed information about their availability.
        
        Args:
            additional_directories: Additional directories to search for providers
            
        Returns:
            Dictionary mapping provider names to their detection information
        """
        logger.info("Detecting providers and gathering information")
        
        all_providers = self.create_providers(additional_directories)
        provider_info = {}
        
        for provider in all_providers:
            try:
                info = {
                    'name': provider.name,
                    'display_name': provider.display_name,
                    'description': provider.description,
                    'type': provider.type,
                    'platforms': provider.platforms,
                    'capabilities': provider.capabilities,
                    'supported_actions': provider.get_supported_actions(),
                    'priority': provider.get_priority(),
                    'available': provider.is_available(),
                    'executable_path': provider.get_executable_path(),
                    'version': provider.get_version() if provider.is_available() else None,
                }
                
                provider_info[provider.name] = info
                
                if info['available']:
                    logger.info(f"✓ Provider '{provider.name}' is available")
                else:
                    logger.debug(f"✗ Provider '{provider.name}' is not available")
                    
            except Exception as e:
                logger.error(f"Error detecting provider '{provider.name}': {e}")
                provider_info[provider.name] = {
                    'name': provider.name,
                    'available': False,
                    'error': str(e)
                }
        
        available_count = sum(1 for info in provider_info.values() if info.get('available', False))
        logger.info(f"Detection complete: {available_count} available out of {len(provider_info)} total providers")
        
        return provider_info
    
    @classmethod
    def create_default_factory(cls) -> 'ProviderFactory':
        """Create a factory with default configuration.
        
        Returns:
            ProviderFactory instance with default loader
        """
        loader = ProviderLoader()
        return cls(loader)