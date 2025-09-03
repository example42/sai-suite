"""Provider YAML loading system."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from jsonschema import Draft7Validator, ValidationError as JsonSchemaValidationError
from pydantic import ValidationError as PydanticValidationError

from ..models.provider_data import ProviderData


logger = logging.getLogger(__name__)


class ProviderValidationError(Exception):
    """Raised when provider YAML validation fails."""
    
    def __init__(self, provider_file: Path, message: str, details: Optional[str] = None):
        self.provider_file = provider_file
        self.message = message
        self.details = details
        super().__init__(f"Provider validation failed for {provider_file}: {message}")


class ProviderLoadError(Exception):
    """Raised when provider YAML loading fails."""
    
    def __init__(self, provider_file: Path, message: str, original_error: Optional[Exception] = None):
        self.provider_file = provider_file
        self.message = message
        self.original_error = original_error
        super().__init__(f"Failed to load provider {provider_file}: {message}")


class ProviderLoader:
    """Loads and validates provider YAML files."""
    
    def __init__(self, schema_path: Optional[Path] = None, enable_caching: bool = True):
        """Initialize the provider loader.
        
        Args:
            schema_path: Path to the provider data JSON schema file.
                        If None, uses the default schema location.
            enable_caching: Whether to enable provider data caching for performance
        """
        self.schema_path = schema_path or Path(__file__).parent.parent.parent / "schemas" / "providerdata-0.1-schema.json"
        self._schema_validator: Optional[Draft7Validator] = None
        self.enable_caching = enable_caching
        self._provider_cache: Dict[Path, ProviderData] = {}
        self._load_schema()
    
    def _load_schema(self) -> None:
        """Load and compile the JSON schema for validation."""
        try:
            if not self.schema_path.exists():
                logger.warning(f"Provider schema not found at {self.schema_path}, validation will be skipped")
                return
                
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            
            self._schema_validator = Draft7Validator(schema_data)
            logger.debug(f"Loaded provider schema from {self.schema_path}")
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to load provider schema from {self.schema_path}: {e}")
            self._schema_validator = None
    
    def scan_provider_directory(self, directory: Path) -> List[Path]:
        """Scan directory for provider YAML files.
        
        Args:
            directory: Directory to scan for provider YAML files
            
        Returns:
            List of paths to provider YAML files
            
        Raises:
            FileNotFoundError: If the directory doesn't exist
        """
        if not directory.exists():
            raise FileNotFoundError(f"Provider directory not found: {directory}")
        
        if not directory.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory}")
        
        yaml_files = []
        
        # Scan for .yaml and .yml files
        for pattern in ["*.yaml", "*.yml"]:
            yaml_files.extend(directory.glob(pattern))
        
        # Also scan specialized subdirectory if it exists
        specialized_dir = directory / "specialized"
        if specialized_dir.exists() and specialized_dir.is_dir():
            for pattern in ["*.yaml", "*.yml"]:
                yaml_files.extend(specialized_dir.glob(pattern))
        
        # Sort for consistent ordering
        yaml_files.sort(key=lambda p: p.name)
        
        logger.debug(f"Found {len(yaml_files)} provider YAML files in {directory}")
        return yaml_files
    
    def validate_yaml_structure(self, data: dict, provider_file: Path) -> None:
        """Validate YAML data against JSON schema.
        
        Args:
            data: Parsed YAML data
            provider_file: Path to the provider file (for error reporting)
            
        Raises:
            ProviderValidationError: If validation fails
        """
        if self._schema_validator is None:
            logger.debug(f"Skipping JSON schema validation for {provider_file} (schema not loaded)")
            return
        
        try:
            self._schema_validator.validate(data)
            logger.debug(f"JSON schema validation passed for {provider_file}")
            
        except JsonSchemaValidationError as e:
            error_path = " -> ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            details = f"Path: {error_path}, Error: {e.message}"
            raise ProviderValidationError(
                provider_file,
                "JSON schema validation failed",
                details
            ) from e
    
    def validate_pydantic_model(self, data: dict, provider_file: Path) -> ProviderData:
        """Validate and parse YAML data using Pydantic model.
        
        Args:
            data: Parsed YAML data
            provider_file: Path to the provider file (for error reporting)
            
        Returns:
            Validated ProviderData instance
            
        Raises:
            ProviderValidationError: If validation fails
        """
        try:
            provider_data = ProviderData(**data)
            logger.debug(f"Pydantic validation passed for {provider_file}")
            return provider_data
            
        except PydanticValidationError as e:
            # Format Pydantic errors nicely
            error_details = []
            for error in e.errors():
                field_path = " -> ".join(str(p) for p in error['loc']) if error['loc'] else "root"
                error_details.append(f"Field: {field_path}, Error: {error['msg']}")
            
            details = "; ".join(error_details)
            raise ProviderValidationError(
                provider_file,
                "Pydantic model validation failed",
                details
            ) from e
    
    def load_provider_file(self, provider_file: Path) -> ProviderData:
        """Load and validate a single provider YAML file.
        
        Args:
            provider_file: Path to the provider YAML file
            
        Returns:
            Validated ProviderData instance
            
        Raises:
            ProviderLoadError: If loading fails
            ProviderValidationError: If validation fails
        """
        logger.debug(f"Loading provider file: {provider_file}")
        
        # Check cache first if enabled
        if self.enable_caching and provider_file in self._provider_cache:
            # Check if file has been modified since caching
            try:
                cached_mtime = getattr(self._provider_cache[provider_file], '_cached_mtime', 0)
                current_mtime = provider_file.stat().st_mtime
                if cached_mtime >= current_mtime:
                    logger.debug(f"Using cached provider data for {provider_file}")
                    return self._provider_cache[provider_file]
            except (OSError, AttributeError):
                # File might have been deleted or cache corrupted, continue with fresh load
                pass
        
        try:
            # Security check: limit file size to prevent DoS attacks
            file_size = provider_file.stat().st_size
            max_size = 10 * 1024 * 1024  # 10MB limit
            if file_size > max_size:
                raise ProviderLoadError(
                    provider_file,
                    f"Provider file too large: {file_size} bytes (max: {max_size})"
                )
            
            # Load YAML file
            with open(provider_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                raise ProviderLoadError(
                    provider_file,
                    f"Expected YAML object, got {type(data).__name__}"
                )
            
            # Validate against JSON schema
            self.validate_yaml_structure(data, provider_file)
            
            # Validate and parse with Pydantic
            provider_data = self.validate_pydantic_model(data, provider_file)
            
            # Cache the result if caching is enabled
            if self.enable_caching:
                # Store modification time for cache invalidation
                setattr(provider_data, '_cached_mtime', provider_file.stat().st_mtime)
                self._provider_cache[provider_file] = provider_data
            
            logger.info(f"Successfully loaded provider: {provider_data.provider.name} from {provider_file}")
            return provider_data
            
        except (yaml.YAMLError, UnicodeDecodeError) as e:
            raise ProviderLoadError(
                provider_file,
                f"Failed to parse YAML: {e}",
                e
            ) from e
        except FileNotFoundError as e:
            raise ProviderLoadError(
                provider_file,
                "File not found",
                e
            ) from e
        except PermissionError as e:
            raise ProviderLoadError(
                provider_file,
                "Permission denied",
                e
            ) from e
    
    def load_providers_from_directory(self, directory: Path) -> Dict[str, ProviderData]:
        """Load all provider YAML files from a directory.
        
        Args:
            directory: Directory containing provider YAML files
            
        Returns:
            Dictionary mapping provider names to ProviderData instances
            
        Raises:
            FileNotFoundError: If the directory doesn't exist
        """
        logger.info(f"Loading providers from directory: {directory}")
        
        provider_files = self.scan_provider_directory(directory)
        providers = {}
        errors = []
        
        for provider_file in provider_files:
            try:
                provider_data = self.load_provider_file(provider_file)
                
                # Check for duplicate provider names
                provider_name = provider_data.provider.name
                if provider_name in providers:
                    logger.warning(
                        f"Duplicate provider name '{provider_name}' found in {provider_file}, "
                        f"overriding previous definition from {providers[provider_name]}"
                    )
                
                providers[provider_name] = provider_data
                
            except (ProviderLoadError, ProviderValidationError) as e:
                logger.error(f"Failed to load provider from {provider_file}: {e}")
                errors.append(e)
                # Continue loading other providers
        
        logger.info(f"Successfully loaded {len(providers)} providers from {directory}")
        
        if errors:
            logger.warning(f"Encountered {len(errors)} errors while loading providers")
            # For now, we continue with successfully loaded providers
            # In the future, we might want to make this configurable
        
        return providers
    
    def get_default_provider_directories(self) -> List[Path]:
        """Get default directories to search for provider files.
        
        Returns:
            List of default provider directories
        """
        # Default to the providers directory in the project root
        project_root = Path(__file__).parent.parent.parent
        default_dirs = [
            project_root / "providers",
        ]
        
        # Add user-specific provider directories if they exist
        user_dirs = [
            Path.home() / ".sai" / "providers",
            Path("/etc/sai/providers"),  # System-wide on Unix
        ]
        
        # Only include directories that exist
        existing_dirs = [d for d in default_dirs + user_dirs if d.exists()]
        
        logger.debug(f"Default provider directories: {existing_dirs}")
        return existing_dirs
    
    def load_all_providers(self, additional_directories: Optional[List[Path]] = None) -> Dict[str, ProviderData]:
        """Load providers from all default and additional directories.
        
        Args:
            additional_directories: Additional directories to search for providers
            
        Returns:
            Dictionary mapping provider names to ProviderData instances
        """
        directories = self.get_default_provider_directories()
        
        if additional_directories:
            directories.extend(additional_directories)
        
        all_providers = {}
        
        for directory in directories:
            try:
                providers = self.load_providers_from_directory(directory)
                
                # Merge providers, with later directories taking precedence
                for name, provider_data in providers.items():
                    if name in all_providers:
                        logger.info(
                            f"Provider '{name}' from {directory} overrides "
                            f"previous definition"
                        )
                    all_providers[name] = provider_data
                    
            except FileNotFoundError:
                logger.debug(f"Provider directory not found: {directory}")
                continue
        
        logger.info(f"Loaded {len(all_providers)} total providers from {len(directories)} directories")
        return all_providers