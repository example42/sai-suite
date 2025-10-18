"""Comprehensive error hierarchy for SAI CLI tool."""

from pathlib import Path
from typing import Any, Dict, List, Optional


class SaiError(Exception):
    """Base exception for all SAI-related errors.

    This is the root exception class that all other SAI exceptions inherit from.
    It provides common functionality for error handling and reporting.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        error_code: Optional[str] = None,
    ):
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
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "suggestions": self.suggestions,
        }


# Configuration and Setup Errors


class ConfigurationError(SaiError):
    """Raised when there are configuration-related issues."""

    def __init__(self, message: str, config_file: Optional[Path] = None, **kwargs):
        super().__init__(message, **kwargs)
        if config_file:
            self.details["config_file"] = str(config_file)


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration is invalid or malformed."""

    def __init__(self, message: str, validation_errors: Optional[List[str]] = None, **kwargs):
        super().__init__(message, **kwargs)
        if validation_errors:
            self.details["validation_errors"] = validation_errors
        self.suggestions = [
            "Check the configuration file syntax",
            "Refer to the documentation for valid configuration options",
            "Use 'sai config validate' to check your configuration",
        ]


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""

    def __init__(self, missing_key: str, **kwargs):
        message = f"Missing required configuration: {missing_key}"
        super().__init__(message, **kwargs)
        self.details["missing_key"] = missing_key
        self.suggestions = [
            f"Add the '{missing_key}' configuration option",
            "Check the documentation for required configuration options",
            "Use 'sai config show' to see current configuration",
        ]


# Provider-related Errors


class ProviderError(SaiError):
    """Base class for provider-related errors."""

    def __init__(self, message: str, provider_name: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if provider_name:
            self.details["provider"] = provider_name


class ProviderNotFoundError(ProviderError):
    """Raised when a requested provider is not found."""

    def __init__(
        self, provider_name: str, available_providers: Optional[List[str]] = None, **kwargs
    ):
        message = f"Provider '{provider_name}' not found"
        super().__init__(message, provider_name=provider_name, **kwargs)

        if available_providers:
            self.details["available_providers"] = available_providers
            self.suggestions = [
                f"Use one of the available providers: {', '.join(available_providers)}",
                "Check if the provider is installed on your system",
                "Use 'sai providers list' to see all available providers",
            ]
        else:
            self.suggestions = [
                "Install a supported package manager",
                "Use 'sai providers detect' to refresh provider detection",
                "Check the documentation for supported providers",
            ]


class ProviderNotAvailableError(ProviderError):
    """Raised when a provider exists but is not available on the current system."""

    def __init__(self, provider_name: str, reason: Optional[str] = None, **kwargs):
        message = f"Provider '{provider_name}' is not available"
        if reason:
            message += f": {reason}"

        super().__init__(message, provider_name=provider_name, **kwargs)

        if reason:
            self.details["unavailable_reason"] = reason

        self.suggestions = [
            f"Install the required executable for provider '{provider_name}'",
            "Check if the provider is in your system PATH",
            "Use 'sai providers info {provider_name}' for more details",
        ]


class ProviderSelectionError(ProviderError):
    """Raised when provider selection fails."""

    def __init__(self, message: str, available_providers: Optional[List[str]] = None, **kwargs):
        super().__init__(message, **kwargs)

        if available_providers:
            self.details["available_providers"] = available_providers
            self.suggestions = [
                f"Use one of the available providers: {', '.join(available_providers)}",
                "Check provider availability with 'sai providers list'",
                "Install additional providers if needed",
            ]
        else:
            self.suggestions = [
                "Install a supported provider",
                "Check provider availability with 'sai providers detect'",
                "Verify your system configuration",
            ]


class ProviderValidationError(ProviderError):
    """Raised when provider configuration is invalid."""

    def __init__(
        self,
        provider_name: str,
        validation_errors: List[str],
        provider_file: Optional[Path] = None,
        **kwargs,
    ):
        message = f"Provider '{provider_name}' configuration is invalid"
        super().__init__(message, provider_name=provider_name, **kwargs)

        self.details["validation_errors"] = validation_errors
        if provider_file:
            self.details["provider_file"] = str(provider_file)

        self.suggestions = [
            "Check the provider YAML file syntax",
            "Refer to the provider schema documentation",
            "Validate the provider file against the schema",
        ]


class ProviderLoadError(ProviderError):
    """Raised when a provider fails to load."""

    def __init__(
        self,
        provider_name: str,
        provider_file: Path,
        original_error: Optional[Exception] = None,
        **kwargs,
    ):
        message = f"Failed to load provider '{provider_name}' from {provider_file}"
        super().__init__(message, provider_name=provider_name, **kwargs)

        self.details["provider_file"] = str(provider_file)
        if original_error:
            self.details["original_error"] = str(original_error)

        self.suggestions = [
            "Check if the provider file exists and is readable",
            "Verify the YAML syntax is correct",
            "Check file permissions",
        ]


# Saidata-related Errors


class SaidataError(SaiError):
    """Base class for saidata-related errors."""

    def __init__(self, message: str, software_name: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if software_name:
            self.details["software"] = software_name


class SaidataNotFoundError(SaidataError):
    """Raised when saidata file is not found."""

    def __init__(self, software_name: str, search_paths: Optional[List[str]] = None, **kwargs):
        message = f"No saidata found for software: {software_name}"
        super().__init__(message, software_name=software_name, **kwargs)

        if search_paths:
            self.details["search_paths"] = search_paths

        self.suggestions = [
            f"Create a saidata file for '{software_name}'",
            "Check if the software name is spelled correctly",
            "Use 'sai search {software_name}' to find similar software",
            "Add custom saidata paths to your configuration",
        ]


class SaidataValidationError(SaidataError):
    """Raised when saidata validation fails."""

    def __init__(
        self,
        software_name: str,
        validation_errors: List[str],
        saidata_file: Optional[Path] = None,
        **kwargs,
    ):
        message = f"Saidata validation failed for '{software_name}'"
        super().__init__(message, software_name=software_name, **kwargs)

        self.details["validation_errors"] = validation_errors
        if saidata_file:
            self.details["saidata_file"] = str(saidata_file)

        self.suggestions = [
            "Check the saidata file syntax",
            "Refer to the saidata schema documentation",
            "Use 'sai validate <file>' to check the saidata file",
        ]


class SaidataParseError(SaidataError):
    """Raised when saidata file cannot be parsed."""

    def __init__(self, software_name: str, saidata_file: Path, parse_error: str, **kwargs):
        message = f"Failed to parse saidata file for '{software_name}': {parse_error}"
        super().__init__(message, software_name=software_name, **kwargs)

        self.details["saidata_file"] = str(saidata_file)
        self.details["parse_error"] = parse_error

        self.suggestions = [
            "Check the file format (YAML or JSON)",
            "Verify the file syntax is correct",
            "Check for special characters or encoding issues",
        ]


# Execution-related Errors


class ExecutionError(SaiError):
    """Base class for execution-related errors."""

    def __init__(
        self,
        message: str,
        action: Optional[str] = None,
        software: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if action:
            self.details["action"] = action
        if software:
            self.details["software"] = software
        if provider:
            self.details["provider"] = provider


class ActionNotSupportedError(ExecutionError):
    """Raised when an action is not supported by any available provider."""

    def __init__(self, action: str, available_actions: Optional[List[str]] = None, **kwargs):
        message = f"Action '{action}' is not supported by any available provider"
        super().__init__(message, action=action, **kwargs)

        if available_actions:
            self.details["available_actions"] = available_actions
            self.suggestions = [
                f"Use one of the supported actions: {', '.join(available_actions)}",
                "Check if you have the right providers installed",
                "Use 'sai providers list' to see provider capabilities",
            ]
        else:
            self.suggestions = [
                "Install a provider that supports this action",
                "Check the documentation for supported actions",
            ]


class CommandExecutionError(ExecutionError):
    """Raised when a command execution fails."""

    def __init__(
        self,
        command: str,
        exit_code: int,
        stderr: Optional[str] = None,
        timeout: bool = False,
        **kwargs,
    ):
        if timeout:
            message = f"Command timed out: {command}"
        else:
            message = f"Command failed with exit code {exit_code}: {command}"

        super().__init__(message, **kwargs)

        self.details["command"] = command
        self.details["exit_code"] = exit_code
        self.details["timeout"] = timeout

        if stderr:
            self.details["stderr"] = stderr

        if timeout:
            self.suggestions = [
                "Increase the timeout value",
                "Check if the command is hanging",
                "Try running the command manually",
            ]
        else:
            self.suggestions = [
                "Check the command output for error details",
                "Verify the command syntax is correct",
                "Check if you have the necessary permissions",
            ]


class PermissionError(ExecutionError):
    """Raised when execution fails due to insufficient permissions."""

    def __init__(self, action: str, required_permission: str = "root", **kwargs):
        message = f"Action '{action}' requires {required_permission} permissions"
        super().__init__(message, action=action, **kwargs)

        self.details["required_permission"] = required_permission

        self.suggestions = [
            f"Run the command with {required_permission} privileges",
            "Use sudo if on Unix-like systems",
            "Check if you have the necessary permissions",
        ]


class TemplateResolutionError(ExecutionError):
    """Raised when template resolution fails."""

    def __init__(self, template: str, resolution_error: str, **kwargs):
        message = f"Failed to resolve template: {resolution_error}"
        super().__init__(message, **kwargs)

        self.details["template"] = template
        self.details["resolution_error"] = resolution_error

        self.suggestions = [
            "Check the template syntax",
            "Verify all required variables are available",
            "Check the saidata for missing fields",
        ]


# Security-related Errors


class SecurityError(SaiError):
    """Base class for security-related errors."""

    def __init__(self, message: str, security_issue: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if security_issue:
            self.details["security_issue"] = security_issue


class UnsafeCommandError(SecurityError):
    """Raised when a command is deemed unsafe to execute."""

    def __init__(self, command: str, reason: str, **kwargs):
        message = f"Command blocked for security reasons: {reason}"
        super().__init__(message, **kwargs)

        self.details["command"] = command
        self.details["security_reason"] = reason

        self.suggestions = [
            "Review the command for potential security issues",
            "Use a safer alternative command",
            "Contact your system administrator if this is a legitimate command",
        ]


class CommandInjectionError(SecurityError):
    """Raised when potential command injection is detected."""

    def __init__(self, suspicious_input: str, **kwargs):
        message = "Potential command injection detected"
        super().__init__(message, **kwargs)

        self.details["suspicious_input"] = suspicious_input

        self.suggestions = [
            "Check the input for malicious characters",
            "Use proper input validation",
            "Report this as a potential security issue",
        ]


# Cache-related Errors


class CacheError(SaiError):
    """Base class for cache-related errors."""


class CacheCorruptedError(CacheError):
    """Raised when cache data is corrupted."""

    def __init__(self, cache_type: str, cache_key: str, **kwargs):
        message = f"Cache data corrupted: {cache_type}[{cache_key}]"
        super().__init__(message, **kwargs)

        self.details["cache_type"] = cache_type
        self.details["cache_key"] = cache_key

        self.suggestions = [
            "Clear the cache and try again",
            "Use 'sai providers clear-cache' to clear provider cache",
            "Check disk space and file permissions",
        ]


class CacheWriteError(CacheError):
    """Raised when cache write operation fails."""

    def __init__(self, cache_path: Path, original_error: Exception, **kwargs):
        message = f"Failed to write cache: {original_error}"
        super().__init__(message, **kwargs)

        self.details["cache_path"] = str(cache_path)
        self.details["original_error"] = str(original_error)

        self.suggestions = [
            "Check disk space",
            "Verify write permissions for cache directory",
            "Try clearing the cache directory",
        ]


# Network and External Service Errors


class NetworkError(SaiError):
    """Base class for network-related errors."""


class RepositoryError(NetworkError):
    """Base class for repository-related errors."""

    def __init__(self, repository_url: str, operation: str, **kwargs):
        message = f"Repository operation failed: {operation} on {repository_url}"
        super().__init__(message, **kwargs)

        self.details["repository_url"] = repository_url
        self.details["operation"] = operation


class RepositoryNotFoundError(RepositoryError):
    """Raised when repository is not found or inaccessible."""

    def __init__(self, repository_url: str, **kwargs):
        super().__init__(repository_url, "access", **kwargs)
        self.message = f"Repository not found or inaccessible: {repository_url}"

        self.suggestions = [
            "Verify the repository URL is correct",
            "Check if the repository exists and is public",
            "Ensure you have access permissions for private repositories",
            "Check your internet connection",
        ]


class RepositoryAuthenticationError(RepositoryError):
    """Raised when repository authentication fails."""

    def __init__(self, repository_url: str, auth_type: Optional[str] = None, **kwargs):
        super().__init__(repository_url, "authentication", **kwargs)
        self.message = f"Authentication failed for repository: {repository_url}"

        if auth_type:
            self.details["auth_type"] = auth_type
            self.message += f" (using {auth_type})"

        self.suggestions = [
            "Check your authentication credentials",
            "Verify SSH keys are properly configured (for SSH authentication)",
            "Ensure access tokens have the correct permissions (for token authentication)",
            "Check if two-factor authentication is required",
            "Use 'sai config auth' to configure authentication",
        ]


class RepositoryNetworkError(RepositoryError):
    """Raised when network connectivity issues prevent repository operations."""

    def __init__(
        self, repository_url: str, network_error: str, is_temporary: bool = True, **kwargs
    ):
        operation = "network_access"
        super().__init__(repository_url, operation, **kwargs)

        self.message = f"Network error accessing repository {repository_url}: {network_error}"
        self.details["network_error"] = network_error
        self.details["is_temporary"] = is_temporary

        if is_temporary:
            self.suggestions = [
                "Check your internet connection",
                "Try again in a few moments",
                "Check if there are network connectivity issues",
                "Verify DNS resolution is working",
            ]
        else:
            self.suggestions = [
                "Check your internet connection",
                "Verify the repository URL is correct",
                "Check if the repository service is down",
                "Try using a different network connection",
            ]


class RepositoryIntegrityError(RepositoryError):
    """Raised when repository integrity validation fails."""

    def __init__(self, repository_url: str, integrity_issue: str, **kwargs):
        super().__init__(repository_url, "integrity_validation", **kwargs)
        self.message = f"Repository integrity validation failed: {integrity_issue}"

        self.details["integrity_issue"] = integrity_issue

        self.suggestions = [
            "Try updating the repository again",
            "Clear the repository cache and re-download",
            "Verify the repository source is trusted",
            "Check if the repository has been compromised",
        ]


class RepositoryStructureError(RepositoryError):
    """Raised when repository structure is invalid or unexpected."""

    def __init__(
        self,
        repository_url: str,
        structure_issue: str,
        expected_structure: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(repository_url, "structure_validation", **kwargs)
        self.message = f"Invalid repository structure: {structure_issue}"

        self.details["structure_issue"] = structure_issue
        if expected_structure:
            self.details["expected_structure"] = expected_structure

        self.suggestions = [
            "Verify you are using the correct repository URL",
            "Check if the repository follows the expected saidata structure",
            "Ensure the repository contains the required directories and files",
            "Contact the repository maintainer if structure is incorrect",
        ]


class GitOperationError(RepositoryError):
    """Raised when git operations fail."""

    def __init__(
        self,
        repository_url: str,
        git_command: str,
        exit_code: int,
        stderr: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(repository_url, f"git_{git_command}", **kwargs)

        self.message = f"Git {git_command} failed for {repository_url} (exit code: {exit_code})"
        self.details["git_command"] = git_command
        self.details["exit_code"] = exit_code

        if stderr:
            self.details["stderr"] = stderr
            # Include first line of stderr in message for context
            first_line = stderr.split("\n")[0] if stderr else ""
            if first_line:
                self.message += f": {first_line}"

        self.suggestions = [
            "Check if git is installed and available",
            "Verify the repository URL is correct",
            "Check your git authentication setup",
            "Try running the git command manually for more details",
        ]


class TarballDownloadError(RepositoryError):
    """Raised when tarball download operations fail."""

    def __init__(self, repository_url: str, download_url: str, error_details: str, **kwargs):
        super().__init__(repository_url, "tarball_download", **kwargs)

        self.message = f"Failed to download tarball from {download_url}: {error_details}"
        self.details["download_url"] = download_url
        self.details["error_details"] = error_details

        self.suggestions = [
            "Check your internet connection",
            "Verify the download URL is accessible",
            "Try again later if the server is temporarily unavailable",
            "Check if authentication is required for the download",
        ]


class ChecksumValidationError(RepositoryError):
    """Raised when checksum validation fails."""

    def __init__(
        self,
        repository_url: str,
        expected_checksum: str,
        actual_checksum: str,
        algorithm: str = "sha256",
        **kwargs,
    ):
        super().__init__(repository_url, "checksum_validation", **kwargs)

        self.message = (
            f"Checksum validation failed: expected {expected_checksum}, got {actual_checksum}"
        )
        self.details["expected_checksum"] = expected_checksum
        self.details["actual_checksum"] = actual_checksum
        self.details["algorithm"] = algorithm

        self.suggestions = [
            "Try downloading the file again",
            "Check if the file was corrupted during download",
            "Verify the expected checksum is correct",
            "Contact the repository maintainer if checksums consistently fail",
        ]


class RepositoryCacheError(CacheError):
    """Raised when repository cache operations fail."""

    def __init__(self, repository_url: str, cache_operation: str, error_details: str, **kwargs):
        super().__init__(
            f"Repository cache {cache_operation} failed for {repository_url}: {error_details}",
            **kwargs,
        )

        self.details["repository_url"] = repository_url
        self.details["cache_operation"] = cache_operation
        self.details["error_details"] = error_details

        self.suggestions = [
            "Check disk space in the cache directory",
            "Verify write permissions for the cache directory",
            "Try clearing the repository cache",
            "Check if the cache directory is accessible",
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

        # Always show line number information for better debugging
        import traceback

        tb = traceback.extract_tb(error.__traceback__)
        if tb:
            # Get the last frame (where the error occurred)
            last_frame = tb[-1]
            filename = last_frame.filename
            line_number = last_frame.lineno
            function_name = last_frame.name

            # Show just the filename (not full path) for cleaner output
            import os

            filename = os.path.basename(filename)

            message += f" (at {filename}:{line_number} in {function_name})"

        if verbose:
            message += "\n\nFull Traceback:\n" + traceback.format_exc()

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
            "Check the documentation or help for this command",
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
        ProviderNotFoundError,
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
        CacheError,
    )

    return isinstance(error, system_error_types)
