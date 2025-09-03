"""Saidata 
loading and validation functionality."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import yaml
import jsonschema
from pydantic import ValidationError as PydanticValidationError

from ..models.saidata import SaiData
from ..models.config import SaiConfig


logger = logging.getLogger(__name__)


class SaidataNotFoundError(Exception):
    """Raised when saidata file is not found."""
    pass


@dataclass
class ValidationResult:
    """Result of saidata validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    
    @property
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0


class SaidataLoader:
    """Loads and validates saidata files with multi-path search capability."""
    
    def __init__(self, config: Optional[SaiConfig] = None):
        """Initialize the saidata loader.
        
        Args:
            config: Sai configuration object. If None, uses default paths.
        """
        self.config = config or SaiConfig()
        self._schema_cache: Optional[Dict[str, Any]] = None
        
        # Initialize saidata cache if enabled
        if self.config.cache_enabled:
            from ..utils.cache import SaidataCache
            self._saidata_cache = SaidataCache(self.config)
        else:
            self._saidata_cache = None
        
    def load_saidata(self, software_name: str, use_cache: bool = True) -> Optional[SaiData]:
        """Load and validate saidata for software.
        
        Args:
            software_name: Name of the software to load saidata for
            use_cache: Whether to use cached data if available
            
        Returns:
            SaiData object if found and valid, None otherwise
            
        Raises:
            SaidataNotFoundError: If no saidata file is found
            ValidationError: If saidata validation fails
        """
        logger.debug(f"Loading saidata for software: {software_name}")
        
        # Find all saidata files for the software
        saidata_files = self._find_saidata_files(software_name)
        
        if not saidata_files:
            raise SaidataNotFoundError(f"No saidata files found for software: {software_name}")
        
        # Check cache first if enabled and requested
        merged_data = None
        if use_cache and self._saidata_cache:
            merged_data = self._saidata_cache.get_cached_saidata(software_name, saidata_files)
            if merged_data:
                logger.debug(f"Using cached saidata for {software_name}")
        
        # Load and merge saidata files if not cached
        if merged_data is None:
            merged_data = self._merge_saidata_files(saidata_files)
            
            # Cache the merged data if caching is enabled
            if self._saidata_cache:
                self._saidata_cache.update_saidata_cache(software_name, saidata_files, merged_data)
        
        # Validate the merged data
        validation_result = self.validate_saidata(merged_data)
        if validation_result.has_errors:
            error_msg = f"Saidata validation failed for {software_name}: {'; '.join(validation_result.errors)}"
            logger.error(error_msg)
            raise ValidationError(error_msg)
        
        if validation_result.has_warnings:
            for warning in validation_result.warnings:
                logger.warning(f"Saidata validation warning for {software_name}: {warning}")
        
        # Create SaiData object
        try:
            saidata = SaiData(**merged_data)
            logger.info(f"Successfully loaded saidata for {software_name}")
            return saidata
        except PydanticValidationError as e:
            error_msg = f"Failed to create SaiData object for {software_name}: {e}"
            logger.error(error_msg)
            raise ValidationError(error_msg) from e
    
    def get_search_paths(self) -> List[Path]:
        """Return ordered list of saidata search paths.
        
        Returns:
            List of Path objects in search order (highest to lowest precedence)
        """
        paths = []
        for path_str in self.config.saidata_paths:
            path = Path(path_str).expanduser().resolve()
            if path.exists() and path.is_dir():
                paths.append(path)
            else:
                logger.debug(f"Saidata search path does not exist: {path}")
        
        return paths
    
    def validate_saidata(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate saidata against schema.
        
        Args:
            data: Raw saidata dictionary to validate
            
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors = []
        warnings = []
        
        try:
            # Load JSON schema if not cached
            if self._schema_cache is None:
                self._load_schema()
            
            # Validate against JSON schema
            jsonschema.validate(data, self._schema_cache)
            
            # Additional validation checks
            self._validate_metadata(data, errors, warnings)
            self._validate_packages(data, errors, warnings)
            self._validate_services(data, errors, warnings)
            self._validate_providers(data, errors, warnings)
            
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
        except jsonschema.SchemaError as e:
            errors.append(f"Schema error: {e.message}")
        except Exception as e:
            errors.append(f"Unexpected validation error: {str(e)}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _find_saidata_files(self, software_name: str) -> List[Path]:
        """Find all saidata files for the given software name.
        
        Args:
            software_name: Name of the software
            
        Returns:
            List of Path objects for found saidata files, ordered by precedence
        """
        found_files = []
        search_paths = self.get_search_paths()
        
        for search_path in search_paths:
            # Look for exact match files
            for extension in ['.yaml', '.yml', '.json']:
                file_path = search_path / f"{software_name}{extension}"
                if file_path.exists() and file_path.is_file():
                    found_files.append(file_path)
                    logger.debug(f"Found saidata file: {file_path}")
            
            # Look in subdirectories
            software_dir = search_path / software_name
            if software_dir.exists() and software_dir.is_dir():
                for extension in ['.yaml', '.yml', '.json']:
                    file_path = software_dir / f"saidata{extension}"
                    if file_path.exists() and file_path.is_file():
                        found_files.append(file_path)
                        logger.debug(f"Found saidata file: {file_path}")
        
        return found_files
    
    def _merge_saidata_files(self, saidata_files: List[Path]) -> Dict[str, Any]:
        """Merge multiple saidata files with precedence rules.
        
        Args:
            saidata_files: List of saidata file paths in precedence order
            
        Returns:
            Merged saidata dictionary
        """
        if not saidata_files:
            return {}
        
        # Start with the lowest precedence file (last in list)
        merged_data = self._load_saidata_file(saidata_files[-1])
        
        # Merge higher precedence files (earlier in list)
        for file_path in reversed(saidata_files[:-1]):
            file_data = self._load_saidata_file(file_path)
            merged_data = self._deep_merge(merged_data, file_data)
            logger.debug(f"Merged saidata from: {file_path}")
        
        return merged_data
    
    def _load_saidata_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a single saidata file.
        
        Args:
            file_path: Path to the saidata file
            
        Returns:
            Loaded saidata dictionary
            
        Raises:
            ValueError: If file format is not supported or parsing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() == '.json':
                    return json.load(f)
                elif file_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                else:
                    raise ValueError(f"Unsupported file format: {file_path.suffix}")
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValueError(f"Failed to parse {file_path}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load {file_path}: {e}") from e
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries with override taking precedence.
        
        Args:
            base: Base dictionary
            override: Override dictionary (higher precedence)
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            elif key in result and isinstance(result[key], list) and isinstance(value, list):
                # For lists, we merge by extending (override appends to base)
                result[key] = result[key] + value
            else:
                # For other types, override completely replaces base
                result[key] = value
        
        return result
    
    def _load_schema(self) -> None:
        """Load the JSON schema for saidata validation."""
        schema_path = Path(__file__).parent.parent.parent / "schemas" / "saidata-0.2-schema.json"
        
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                self._schema_cache = json.load(f)
            logger.debug(f"Loaded saidata schema from: {schema_path}")
        except Exception as e:
            logger.error(f"Failed to load saidata schema: {e}")
            # Use minimal schema as fallback
            self._schema_cache = {
                "type": "object",
                "properties": {
                    "version": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                },
                "required": ["version", "metadata"]
            }
    
    def _validate_metadata(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate metadata section."""
        metadata = data.get('metadata', {})
        
        if not metadata.get('name'):
            errors.append("Metadata must have a name field")
        
        if not metadata.get('description'):
            warnings.append("Metadata should have a description field")
        
        # Validate URLs if present
        urls = metadata.get('urls', {})
        if urls:
            for url_type, url in urls.items():
                if url and not isinstance(url, str):
                    errors.append(f"URL {url_type} must be a string")
    
    def _validate_packages(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate packages section."""
        packages = data.get('packages', [])
        
        if not packages:
            warnings.append("No packages defined")
            return
        
        for i, package in enumerate(packages):
            if not isinstance(package, dict):
                errors.append(f"Package {i} must be an object")
                continue
            
            if not package.get('name'):
                errors.append(f"Package {i} must have a name field")
    
    def _validate_services(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate services section."""
        services = data.get('services', [])
        
        for i, service in enumerate(services):
            if not isinstance(service, dict):
                errors.append(f"Service {i} must be an object")
                continue
            
            if not service.get('name'):
                errors.append(f"Service {i} must have a name field")
            
            service_type = service.get('type')
            if service_type and service_type not in ['systemd', 'init', 'launchd', 'windows_service', 'docker', 'kubernetes']:
                errors.append(f"Service {i} has invalid type: {service_type}")
    
    def _validate_providers(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate providers section."""
        providers = data.get('providers', {})
        
        if not providers:
            warnings.append("No provider-specific configurations defined")
            return
        
        for provider_name, provider_config in providers.items():
            if not isinstance(provider_config, dict):
                errors.append(f"Provider {provider_name} configuration must be an object")
                continue
            
            # Validate provider-specific packages
            provider_packages = provider_config.get('packages', [])
            for i, package in enumerate(provider_packages):
                if not isinstance(package, dict):
                    errors.append(f"Provider {provider_name} package {i} must be an object")
                    continue
                
                if not package.get('name'):
                    errors.append(f"Provider {provider_name} package {i} must have a name field")


class ValidationError(Exception):
    """Raised when saidata validation fails."""
    pass