"""Comprehensive error hierarchy for SAI CLI tool."""

from typing import Optional, Dict, Any, List
from pathlib import Path


class SaiError(Exception):
    """Base exception for all SAI-related errors.
    
    This is the root exception class that all other SAI exceptions inherit from.
    It provides common functionality for error handling and reporting.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 suggestions: Optional[List[str]] = None, error_code: Optional[str] = None):
        """Initialize SAI error.
        
        Args:
            message: Human-readable error message
            details: Additional error details for debugging
            suggestions: List of suggested solutions
            error_code: Unique error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.suggestions = suggestions or []
        self.error_code = error_code
    
    def get_full_message(self) -> str:
        """Get full error message including suggestions.
        
        Returns:
            Complete error message with suggestions
        """
        message = self.message
        
        if self.suggestions:
            message += "\n\nSuggestions:"
            for i, suggestion in enumerate(self.suggestions, 1):
                message += f"\n  {i}. {suggestion}"
        
        return message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details,
            'suggestions': self.suggestions
        }


# Configuration and Setup Errors

class ConfigurationError(SaiError):
    """Raised when there are configuration-related issues."""
    
    def __init__(self, message: str, config_file: Optional[Path] = None, **kwargs):
        super().__init__(message, **kwargs)
        if config_file:
            self.details['config_file'] = str(config_file)


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration is invalid or malformed."""
    
    def __init__(self, message: str, validation_errors: Optional[List[str]] = None, **kwargs):
        super().__init__(message, **kwargs)
        if validation_errors:
            self.details['validation_errors'] = validation_errors
        self.suggestions = [
            "Check the configuration file syntax",
            "Refer to the documentation for valid configuration options",
            "Use 'sai config validate' to check your configuration"
        ]


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""
    
    def __init__(self, missing_key: str, **kwargs):
        message = f"Missing required configuration: {missing_key}"
        super().__init__(message, **kwargs)
        self.details['missing_key'] = missing_key
        self.suggestions = [
            f"Add the '{missing_key}' configuration option",
            "Check the documentation for required configuration options",
            "Use 'sai config show' to see current configuration"
        ]


# Provider-related Errors

class ProviderError(SaiError):
    """Base class for provider-related errors."""
    
    def __init__(self, message: str, provider_name: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if provider_name:
            self.details['provider'] = provider_name


class ProviderNotFoundError(ProviderError):
    """Raised when a requested provider is not found."""
    
    def __init__(self, provider_name: str, available_providers: Optional[List[str]] = None, **kwargs):
        message = f"Provider '{provider_name}' not found"
        super().__init__(message, provider_name=provider_name, **kwargs)
        
        if available_providers:
            self.details['available_providers'] = available_providers
            self.suggestions = [
                f"Use one of the available providers: {', '.join(available_providers)}",
                "Check if the provider is installed on your system",
                "Use 'sai providers list' to see all available providers"
            ]
        else:
            self.suggestions = [
                "Install a supported package manager",
                "Use 'sai providers detect' to refresh provider detection",
                "Check the documentation for supported providers"
            ]


class ProviderNotAvailableError(ProviderError):
    """Raised when a provider exists but is not available on the current system."""
    
    def __init__(self, provider_name: str, reason: Optional[str] = None, **kwargs):
        message = f"Provider '{provider_name}' is not available"
        if reason:
            message += f": {reason}"
        
        super().__init__(message, provider_name=provider_name, **kwargs)
        
        if reason:
            self.details['unavailable_reason'] = reason
        
        self.suggestions = [
            f"Install the required executable for provider '{provider_name}'",
            "Check if the provider is in your system PATH",
            "Use 'sai providers info {provider_name}' for more details"
        ]


class ProviderSelectionError(ProviderError):
    """Raised when provider selection fails."""
    
    def __init__(self, message: str, available_providers: Optional[List[str]] = None, **kwargs):
        super().__init__(message, **kwargs)
        
        if available_providers:
            self.details['available_providers'] = available_providers
            self.suggestions = [
                f"Use one of the available providers: {', '.join(available_providers)}",
                "Check provider availability with 'sai providers list'",
                "Install additional providers if needed"
            ]
        else:
            self.suggestions = [
                "Install a supported provider",
                "Check provider availability with 'sai providers detect'",
                "Verify your system configuration"
            ]


class ProviderValidationError(ProviderError):
    """Raised when provider configuration is invalid."""
    
    def __init__(self, provider_name: str, validation_errors: List[str], 
                 provider_file: Optional[Path] = None, **kwargs):
        message = f"Provider '{provider_name}' configuration is invalid"
        super().__init__(message, provider_name=provider_name, **kwargs)
        
        self.details['validation_errors'] = validation_errors
        if provider_file:
            self.details['provider_file'] = str(provider_file)
        
        self.suggestions = [
            "Check the provider YAML file syntax",
            "Refer to the provider schema documentation",
            "Validate the provider file against the schema"
        ]


class ProviderLoadError(ProviderError):
    """Raised when a provider fails to load."""
    
    def __init__(self, provider_name: str, provider_file: Path, 
                 original_error: Optional[Exception] = None, **kwargs):
        message = f"Failed to load provider '{provider_name}' from {provider_file}"
        super().__init__(message, provider_name=provider_name, **kwargs)
        
        self.details['provider_file'] = str(provider_file)
        if original_error:
            self.details['original_error'] = str(original_error)
        
        self.suggestions = [
            "Check if the provider file exists and is readable",
            "Verify the YAML syntax is correct",
            "Check file permissions"
        ]


# Saidata-related Errors

class SaidataError(SaiError):
    """Base class for saidata-related errors."""
    
    def __init__(self, message: str, software_name: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if software_name:
            self.details['software'] = software_name


class SaidataNotFoundError(SaidataError):
    """Raised when saidata file is not found."""
    
    def __init__(self, software_name: str, search_paths: Optional[List[str]] = None, **kwargs):
        message = f"No saidata found for software: {software_name}"
        super().__init__(message, software_name=software_name, **kwargs)
        
        if search_paths:
            self.details['search_paths'] = search_paths
        
        self.suggestions = [
            f"Create a saidata file for '{software_name}'",
            "Check if the software name is spelled correctly",
            "Use 'sai search {software_name}' to find similar software",
            "Add custom saidata paths to your configuration"
        ]


class SaidataValidationError(SaidataError):
    """Raised when saidata validation fails."""
    
    def __init__(self, software_name: str, validation_errors: List[str], 
                 saidata_file: Optional[Path] = None, **kwargs):
        message = f"Saidata validation failed for '{software_name}'"
        super().__init__(message, software_name=software_name, **kwargs)
        
        self.details['validation_errors'] = validation_errors
        if saidata_file:
            self.details['saidata_file'] = str(saidata_file)
        
        self.suggestions = [
            "Check the saidata file syntax",
            "Refer to the saidata schema documentation",
            "Use 'sai validate <file>' to check the saidata file"
        ]


class SaidataParseError(SaidataError):
    """Raised when saidata file cannot be parsed."""
    
    def __init__(self, software_name: str, saidata_file: Path, 
                 parse_error: str, **kwargs):
        message = f"Failed to parse saidata file for '{software_name}': {parse_error}"
        super().__init__(message, software_name=software_name, **kwargs)
        
        self.details['saidata_file'] = str(saidata_file)
        self.details['parse_error'] = parse_error
        
        self.suggestions = [
            "Check the file format (YAML or JSON)",
            "Verify the file syntax is correct",
            "Check for special characters or encoding issues"
        ]


# Execution-related Errors

class ExecutionError(SaiError):
    """Base class for execution-related errors."""
    
    def __init__(self, message: str, action: Optional[str] = None, 
                 software: Optional[str] = None, provider: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if action:
            self.details['action'] = action
        if software:
            self.details['software'] = software
        if provider:
            self.details['provider'] = provider


class ActionNotSupportedError(ExecutionError):
    """Raised when an action is not supported by any available provider."""
    
    def __init__(self, action: str, available_actions: Optional[List[str]] = None, **kwargs):
        message = f"Action '{action}' is not supported by any available provider"
        super().__init__(message, action=action, **kwargs)
        
        if available_actions:
            self.details['available_actions'] = available_actions
            self.suggestions = [
                f"Use one of the supported actions: {', '.join(available_actions)}",
                "Check if you have the right providers installed",
                "Use 'sai providers list' to see provider capabilities"
            ]
        else:
            self.suggestions = [
                "Install a provider that supports this action",
                "Check the documentation for supported actions"
            ]


class CommandExecutionError(ExecutionError):
    """Raised when a command execution fails."""
    
    def __init__(self, command: str, exit_code: int, stderr: Optional[str] = None,
                 timeout: bool = False, **kwargs):
        if timeout:
            message = f"Command timed out: {command}"
        else:
            message = f"Command failed with exit code {exit_code}: {command}"
        
        super().__init__(message, **kwargs)
        
        self.details['command'] = command
        self.details['exit_code'] = exit_code
        self.details['timeout'] = timeout
        
        if stderr:
            self.details['stderr'] = stderr
        
        if timeout:
            self.suggestions = [
                "Increase the timeout value",
                "Check if the command is hanging",
                "Try running the command manually"
            ]
        else:
            self.suggestions = [
                "Check the command output for error details",
                "Verify the command syntax is correct",
                "Check if you have the necessary permissions"
            ]


class PermissionError(ExecutionError):
    """Raised when execution fails due to insufficient permissions."""
    
    def __init__(self, action: str, required_permission: str = "root", **kwargs):
        message = f"Action '{action}' requires {required_permission} permissions"
        super().__init__(message, action=action, **kwargs)
        
        self.details['required_permission'] = required_permission
        
        self.suggestions = [
            f"Run the command with {required_permission} privileges",
            "Use sudo if on Unix-like systems",
            "Check if you have the necessary permissions"
        ]


class TemplateResolutionError(ExecutionError):
    """Raised when template resolution fails."""
    
    def __init__(self, template: str, resolution_error: str, **kwargs):
        message = f"Failed to resolve template: {resolution_error}"
        super().__init__(message, **kwargs)
        
        self.details['template'] = template
        self.details['resolution_error'] = resolution_error
        
        self.suggestions = [
            "Check the template syntax",
            "Verify all required variables are available",
            "Check the saidata for missing fields"
        ]


# Security-related Errors

class SecurityError(SaiError):
    """Base class for security-related errors."""
    pass


class UnsafeCommandError(SecurityError):
    """Raised when a command is deemed unsafe to execute."""
    
    def __init__(self, command: str, reason: str, **kwargs):
        message = f"Command blocked for security reasons: {reason}"
        super().__init__(message, **kwargs)
        
        self.details['command'] = command
        self.details['security_reason'] = reason
        
        self.suggestions = [
            "Review the command for potential security issues",
            "Use a safer alternative command",
            "Contact your system administrator if this is a legitimate command"
        ]


class CommandInjectionError(SecurityError):
    """Raised when potential command injection is detected."""
    
    def __init__(self, suspicious_input: str, **kwargs):
        message = "Potential command injection detected"
        super().__init__(message, **kwargs)
        
        self.details['suspicious_input'] = suspicious_input
        
        self.suggestions = [
            "Check the input for malicious characters",
            "Use proper input validation",
            "Report this as a potential security issue"
        ]


# Cache-related Errors

class CacheError(SaiError):
    """Base class for cache-related errors."""
    pass


class CacheCorruptedError(CacheError):
    """Raised when cache data is corrupted."""
    
    def __init__(self, cache_type: str, cache_key: str, **kwargs):
        message = f"Cache data corrupted: {cache_type}[{cache_key}]"
        super().__init__(message, **kwargs)
        
        self.details['cache_type'] = cache_type
        self.details['cache_key'] = cache_key
        
        self.suggestions = [
            "Clear the cache and try again",
            "Use 'sai providers clear-cache' to clear provider cache",
            "Check disk space and file permissions"
        ]


class CacheWriteError(CacheError):
    """Raised when cache write operation fails."""
    
    def __init__(self, cache_path: Path, original_error: Exception, **kwargs):
        message = f"Failed to write cache: {original_error}"
        super().__init__(message, **kwargs)
        
        self.details['cache_path'] = str(cache_path)
        self.details['original_error'] = str(original_error)
        
        self.suggestions = [
            "Check disk space",
            "Verify write permissions for cache directory",
            "Try clearing the cache directory"
        ]


# Network and External Service Errors

class NetworkError(SaiError):
    """Base class for network-related errors."""
    pass


class RepositoryError(NetworkError):
    """Raised when repository operations fail."""
    
    def __init__(self, repository_url: str, operation: str, **kwargs):
        message = f"Repository operation failed: {operation} on {repository_url}"
        super().__init__(message, **kwargs)
        
        self.details['repository_url'] = repository_url
        self.details['operation'] = operation
        
        self.suggestions = [
            "Check your internet connection",
            "Verify the repository URL is correct",
            "Try again later if the repository is temporarily unavailable"
        ]


# Utility functions for error handling

def format_error_for_cli(error: Exception, verbose: bool = False) -> str:
    """Format an error for CLI output.
    
    Args:
        error: Exception to format
        verbose: Whether to include verbose details
        
    Returns:
        Formatted error message
    """
    if isinstance(error, SaiError):
        message = error.get_full_message()
        
        if verbose and error.details:
            message += "\n\nDetails:"
            for key, value in error.details.items():
                message += f"\n  {key}: {value}"
        
        return message
    else:
        # For non-SAI errors, provide basic formatting
        message = str(error)
        
        if verbose:
            import traceback
            message += "\n\nTraceback:\n" + traceback.format_exc()
        
        return message


def get_error_suggestions(error: Exception) -> List[str]:
    """Get suggestions for resolving an error.
    
    Args:
        error: Exception to get suggestions for
        
    Returns:
        List of suggested solutions
    """
    if isinstance(error, SaiError):
        return error.suggestions
    else:
        # Generic suggestions for unknown errors
        return [
            "Check the command syntax and arguments",
            "Try running with --verbose for more details",
            "Check the documentation or help for this command"
        ]


def is_user_error(error: Exception) -> bool:
    """Check if an error is likely due to user input/configuration.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error is likely user-related
    """
    user_error_types = (
        ConfigurationError,
        SaidataNotFoundError,
        ActionNotSupportedError,
        ProviderNotFoundError
    )
    
    return isinstance(error, user_error_types)


def is_system_error(error: Exception) -> bool:
    """Check if an error is likely due to system/environment issues.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error is likely system-related
    """
    system_error_types = (
        ProviderNotAvailableError,
        PermissionError,
        CommandExecutionError,
        NetworkError,
        CacheError
    )
    
    return isinstance(error, system_error_types)