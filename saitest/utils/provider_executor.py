"""Provider command executor for saitest.

This module provides functionality to load providerdata and execute
provider-specific commands using sai's template engine.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Any

import yaml

from sai.providers.loader import ProviderLoader, ProviderLoadError, ProviderValidationError
from sai.providers.template_engine import TemplateEngine, TemplateResolutionError
from sai.models.provider_data import ProviderData
from saigen.models.saidata import SaiData


logger = logging.getLogger(__name__)


class ProviderExecutorError(Exception):
    """Exception raised when provider command execution fails."""
    pass


class ProviderCommandExecutor:
    """Execute provider commands using providerdata definitions.
    
    This class loads providerdata from the providers/ directory and uses
    sai's template engine to resolve command templates with saidata context.
    
    Attributes:
        providers: Dictionary mapping provider names to ProviderData instances
        template_engine: Template engine for variable substitution
    """
    
    def __init__(self, providers_dir: Optional[Path] = None):
        """Initialize provider command executor.
        
        Args:
            providers_dir: Directory containing providerdata files.
                          If None, uses default providers/ directory.
        """
        self._logger = logging.getLogger(__name__)
        self.providers: Dict[str, ProviderData] = {}
        self.template_engine = TemplateEngine()
        
        # Determine providers directory
        if providers_dir is None:
            # Default to providers/ directory in project root
            project_root = Path(__file__).parent.parent.parent
            providers_dir = project_root / "providers"
        
        self.providers_dir = providers_dir
        
        # Load providers
        self._load_providers()
    
    def _load_providers(self) -> None:
        """Load all providerdata files from providers directory.
        
        Scans the providers/ directory and loads all valid providerdata files.
        Invalid files are logged as warnings but don't stop the loading process.
        """
        if not self.providers_dir.exists():
            self._logger.warning(
                f"Providers directory not found: {self.providers_dir}. "
                "No providers will be available."
            )
            return
        
        self._logger.info(f"Loading providers from {self.providers_dir}")
        
        # Use sai's ProviderLoader for consistent loading
        loader = ProviderLoader()
        
        try:
            # Load all providers from directory
            self.providers = loader.load_providers_from_directory(self.providers_dir)
            
            # Validate each loaded provider
            self._validate_providers()
            
            self._logger.info(
                f"Successfully loaded {len(self.providers)} providers: "
                f"{', '.join(self.providers.keys())}"
            )
            
        except FileNotFoundError:
            self._logger.warning(
                f"Providers directory not found: {self.providers_dir}. "
                "No providers will be available."
            )
        except Exception as e:
            self._logger.error(f"Error loading providers: {e}")
            # Continue with empty providers dict
    
    def _validate_providers(self) -> None:
        """Validate loaded providers and log warnings for invalid ones.
        
        Checks that each provider has required actions and valid structure.
        Invalid providers are removed from the providers dictionary.
        """
        invalid_providers = []
        
        for provider_name, provider_data in self.providers.items():
            try:
                # Validate provider has provider info
                if not provider_data.provider:
                    self._logger.warning(
                        f"Provider '{provider_name}' missing provider info"
                    )
                    invalid_providers.append(provider_name)
                    continue
                
                # Validate provider has actions
                if not provider_data.actions or len(provider_data.actions) == 0:
                    self._logger.warning(
                        f"Provider '{provider_name}' has no actions defined"
                    )
                    invalid_providers.append(provider_name)
                    continue
                
                # Validate provider has install action (actions is a Dict)
                if "install" not in provider_data.actions:
                    self._logger.warning(
                        f"Provider '{provider_name}' missing required 'install' action"
                    )
                    invalid_providers.append(provider_name)
                    continue
                
                # Validate install action has command, template, or steps
                install_action = provider_data.actions["install"]
                has_command = install_action.command or install_action.template
                has_steps = hasattr(install_action, 'steps') and install_action.steps
                
                if not (has_command or has_steps):
                    self._logger.warning(
                        f"Provider '{provider_name}' install action missing command/template/steps"
                    )
                    invalid_providers.append(provider_name)
                    continue
                
                self._logger.debug(f"Provider '{provider_name}' validated successfully")
                
            except Exception as e:
                self._logger.warning(
                    f"Error validating provider '{provider_name}': {e}"
                )
                invalid_providers.append(provider_name)
        
        # Remove invalid providers
        for provider_name in invalid_providers:
            del self.providers[provider_name]
            self._logger.info(f"Removed invalid provider: {provider_name}")
        
        if invalid_providers:
            self._logger.warning(
                f"Removed {len(invalid_providers)} invalid providers: "
                f"{', '.join(invalid_providers)}"
            )
    
    def get_available_providers(self) -> list[str]:
        """Get list of available provider names.
        
        Returns:
            List of provider names that have valid providerdata
        """
        return list(self.providers.keys())
    
    def has_provider(self, provider_name: str) -> bool:
        """Check if a provider is available.
        
        Args:
            provider_name: Name of the provider to check
        
        Returns:
            True if provider has valid providerdata, False otherwise
        """
        return provider_name in self.providers
    
    def get_install_command(
        self,
        provider_name: str,
        saidata: Optional[SaiData] = None,
        package_name: Optional[str] = None
    ) -> str:
        """Get installation command from providerdata.
        
        Args:
            provider_name: Name of the provider (e.g., "apt", "dnf", "pip")
            saidata: SaiData object for template resolution
            package_name: Package name for simple substitution (used if saidata is None)
        
        Returns:
            Resolved installation command
        
        Raises:
            ProviderExecutorError: If provider not found or command resolution fails
        """
        # Validate inputs
        if not provider_name:
            raise ProviderExecutorError("Provider name cannot be empty")
        
        if not saidata and not package_name:
            raise ProviderExecutorError(
                "Either saidata or package_name must be provided for template resolution"
            )
        
        # Check if provider exists
        if provider_name not in self.providers:
            available = ', '.join(self.providers.keys()) if self.providers else 'none'
            raise ProviderExecutorError(
                f"Provider '{provider_name}' not found. "
                f"Available providers: {available}"
            )
        
        provider_data = self.providers[provider_name]
        
        # Get install action (actions is a Dict)
        install_action = provider_data.actions.get("install")
        
        if not install_action:
            raise ProviderExecutorError(
                f"Install action not found for provider '{provider_name}'"
            )
        
        # Get command template - check for steps, command, or template
        command_template = None
        
        # Check if action uses steps (multi-step commands)
        if hasattr(install_action, 'steps') and install_action.steps:
            # Combine all steps into a single command with &&
            step_commands = []
            for step in install_action.steps:
                if hasattr(step, 'command') and step.command:
                    step_commands.append(step.command)
            
            if step_commands:
                command_template = " && ".join(step_commands)
                self._logger.debug(
                    f"Provider '{provider_name}' uses steps, combined into: {command_template}"
                )
        
        # Fall back to single command or template
        if not command_template:
            command_template = install_action.command or install_action.template
        
        if not command_template:
            raise ProviderExecutorError(
                f"No command, template, or steps found for install action in provider '{provider_name}'"
            )
        
        # Resolve template
        try:
            if saidata:
                # Use template engine with full saidata context
                resolved_command = self.template_engine.resolve_template(
                    command_template,
                    saidata
                )
            elif package_name:
                # Simple substitution for basic package name
                # This is a fallback when we don't have full saidata
                resolved_command = command_template.replace(
                    "{{sai_packages(saidata, '" + provider_name + "')}}", 
                    package_name
                ).replace(
                    "{{sai_package(saidata, 0, 'package_name', '" + provider_name + "')}}", 
                    package_name
                )
            
            # Validate resolved command is not empty
            if not resolved_command or not resolved_command.strip():
                raise ProviderExecutorError(
                    f"Resolved command is empty for provider '{provider_name}'. "
                    "This may indicate missing saidata or incorrect template."
                )
            
            self._logger.debug(
                f"Resolved install command for {provider_name}: {resolved_command}"
            )
            return resolved_command.strip()
            
        except TemplateResolutionError as e:
            self._logger.error(
                f"Template resolution failed for provider '{provider_name}': {e}"
            )
            raise ProviderExecutorError(
                f"Failed to resolve install command template for '{provider_name}': {e}"
            ) from e
        except Exception as e:
            self._logger.error(
                f"Unexpected error resolving command for provider '{provider_name}': {e}"
            )
            raise ProviderExecutorError(
                f"Unexpected error resolving install command for '{provider_name}': {e}"
            ) from e
    
    def get_test_command(
        self,
        provider_name: str,
        saidata: Optional[SaiData] = None,
        package_name: Optional[str] = None
    ) -> Optional[str]:
        """Get test/verification command from providerdata.
        
        Args:
            provider_name: Name of the provider
            saidata: SaiData object for template resolution
            package_name: Package name for simple substitution (used if saidata is None)
        
        Returns:
            Resolved test command, or None if no test action available
        
        Raises:
            ProviderExecutorError: If provider not found
        """
        # Validate inputs
        if not provider_name:
            raise ProviderExecutorError("Provider name cannot be empty")
        
        # Check if provider exists
        if provider_name not in self.providers:
            available = ', '.join(self.providers.keys()) if self.providers else 'none'
            raise ProviderExecutorError(
                f"Provider '{provider_name}' not found. "
                f"Available providers: {available}"
            )
        
        provider_data = self.providers[provider_name]
        
        # Look for test/status/verify action (actions is a Dict)
        test_action = None
        for action_name in ["status", "test", "verify"]:
            if action_name in provider_data.actions:
                test_action = provider_data.actions[action_name]
                break
        
        if not test_action:
            self._logger.debug(
                f"No test action found for provider '{provider_name}'"
            )
            return None
        
        # Get command template - check for steps, command, or template
        command_template = None
        
        # Check if action uses steps (multi-step commands)
        if hasattr(test_action, 'steps') and test_action.steps:
            # Combine all steps into a single command with &&
            step_commands = []
            for step in test_action.steps:
                if hasattr(step, 'command') and step.command:
                    step_commands.append(step.command)
            
            if step_commands:
                command_template = " && ".join(step_commands)
                self._logger.debug(
                    f"Provider '{provider_name}' test action uses steps, combined into: {command_template}"
                )
        
        # Fall back to single command or template
        if not command_template:
            command_template = test_action.command or test_action.template
        
        if not command_template:
            self._logger.debug(
                f"No command template found for test action in provider '{provider_name}'"
            )
            return None
        
        # Resolve template
        try:
            if saidata:
                # Use template engine with full saidata context
                resolved_command = self.template_engine.resolve_template(
                    command_template,
                    saidata
                )
            elif package_name:
                # Simple substitution for basic package name
                resolved_command = command_template.replace(
                    "{{sai_packages(saidata, '" + provider_name + "')}}", 
                    package_name
                ).replace(
                    "{{sai_package(saidata, 0, 'package_name', '" + provider_name + "')}}", 
                    package_name
                )
            else:
                self._logger.warning(
                    f"Neither saidata nor package_name provided for test command resolution "
                    f"for provider '{provider_name}'"
                )
                return None
            
            # Validate resolved command is not empty
            if not resolved_command or not resolved_command.strip():
                self._logger.warning(
                    f"Resolved test command is empty for provider '{provider_name}'"
                )
                return None
            
            self._logger.debug(
                f"Resolved test command for {provider_name}: {resolved_command}"
            )
            return resolved_command.strip()
            
        except TemplateResolutionError as e:
            self._logger.warning(
                f"Failed to resolve test command template for '{provider_name}': {e}"
            )
            return None
        except Exception as e:
            self._logger.warning(
                f"Unexpected error resolving test command for '{provider_name}': {e}"
            )
            return None
    
    def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a provider.
        
        Args:
            provider_name: Name of the provider
        
        Returns:
            Dictionary with provider information, or None if provider not found
        """
        if provider_name not in self.providers:
            return None
        
        provider_data = self.providers[provider_name]
        
        return {
            "name": provider_data.provider.name,
            "type": provider_data.provider.type,
            "description": provider_data.provider.description or "",
            "platforms": provider_data.provider.platforms or [],
            "actions": list(provider_data.actions.keys())
        }
