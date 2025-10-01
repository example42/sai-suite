"""Saidata validation system with JSON schema validation and comprehensive error reporting."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

import jsonschema
from jsonschema import Draft7Validator
import yaml

from ..models.saidata import SaiData
from ..utils.url_templating import URLTemplateProcessor, TemplateValidationError
from ..utils.checksum_validator import ChecksumValidator, ChecksumValidationError


class ValidationSeverity(str, Enum):
    """Validation error severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationError:
    """Represents a validation error with context and helpful messages."""
    severity: ValidationSeverity
    message: str
    path: str
    code: str
    suggestion: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of saidata validation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    info: List[ValidationError]
    
    @property
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0
    
    @property
    def total_issues(self) -> int:
        """Total number of validation issues."""
        return len(self.errors) + len(self.warnings) + len(self.info)


@dataclass
class RecoveryResult:
    """Result of validation error recovery."""
    recovered_data: Dict[str, Any]
    fixed_errors: List[str]
    remaining_errors: List[ValidationError]
    recovery_notes: List[str]


class SaidataValidator:
    """Comprehensive saidata validation system."""
    
    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize validator with schema.
        
        Args:
            schema_path: Path to saidata schema JSON file. If None, uses default 0.3 schema.
        """
        self.schema_path = schema_path or Path(__file__).parent.parent.parent / "schemas" / "saidata-0.3-schema.json"
        self._schema: Optional[Dict[str, Any]] = None
        self._validator: Optional[Draft7Validator] = None
        self.url_processor = URLTemplateProcessor()
        self.checksum_validator = ChecksumValidator()
        
    def _load_schema(self) -> Dict[str, Any]:
        """Load and cache the JSON schema."""
        if self._schema is None:
            if not self.schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
            
            try:
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    self._schema = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                raise ValueError(f"Failed to load schema from {self.schema_path}: {e}")
                
        return self._schema
    
    def _get_validator(self) -> Draft7Validator:
        """Get cached JSON schema validator."""
        if self._validator is None:
            schema = self._load_schema()
            self._validator = Draft7Validator(schema)
            
        return self._validator
    
    def validate_file(self, file_path: Path) -> ValidationResult:
        """Validate a saidata file.
        
        Args:
            file_path: Path to saidata YAML file
            
        Returns:
            ValidationResult with all validation issues
        """
        try:
            # Load YAML file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            return self.validate_data(data, str(file_path))
            
        except yaml.YAMLError as e:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid YAML syntax: {str(e)}",
                    path=str(file_path),
                    code="yaml_syntax_error",
                    suggestion="Check YAML syntax and indentation"
                )],
                warnings=[],
                info=[]
            )
        except FileNotFoundError:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"File not found: {file_path}",
                    path=str(file_path),
                    code="file_not_found"
                )],
                warnings=[],
                info=[]
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    severity=ValidationSeverity.ERROR,
                    message=f"Unexpected error: {str(e)}",
                    path=str(file_path),
                    code="unexpected_error"
                )],
                warnings=[],
                info=[]
            )
    
    def validate_data(self, data: Dict[str, Any], source: str = "data") -> ValidationResult:
        """Validate saidata dictionary.
        
        Args:
            data: Saidata dictionary to validate
            source: Source identifier for error reporting
            
        Returns:
            ValidationResult with all validation issues
        """
        errors = []
        warnings = []
        info = []
        
        # JSON Schema validation
        schema_errors = self._validate_json_schema(data, source)
        errors.extend(schema_errors)
        
        # URL template validation
        url_errors, url_warnings = self._validate_url_templates(data, source)
        errors.extend(url_errors)
        warnings.extend(url_warnings)
        
        # Checksum format validation
        checksum_errors = self._validate_checksums(data, source)
        errors.extend(checksum_errors)
        
        # Custom validation rules
        custom_errors, custom_warnings, custom_info = self._validate_custom_rules(data, source)
        errors.extend(custom_errors)
        warnings.extend(custom_warnings)
        info.extend(custom_info)
        
        # Cross-reference validation
        cross_ref_errors, cross_ref_warnings = self._validate_cross_references(data, source)
        errors.extend(cross_ref_errors)
        warnings.extend(cross_ref_warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def validate_pydantic_model(self, saidata: SaiData) -> ValidationResult:
        """Validate a Pydantic SaiData model.
        
        Args:
            saidata: SaiData model instance
            
        Returns:
            ValidationResult with validation issues
        """
        # Convert to dict and validate
        data = saidata.model_dump(exclude_none=True)
        return self.validate_data(data, "pydantic_model")
    
    def _validate_json_schema(self, data: Dict[str, Any], source: str) -> List[ValidationError]:
        """Validate against JSON schema."""
        errors = []
        validator = self._get_validator()
        
        for error in validator.iter_errors(data):
            path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
            
            # Generate helpful error messages
            message, suggestion = self._format_schema_error(error)
            
            errors.append(ValidationError(
                severity=ValidationSeverity.ERROR,
                message=message,
                path=f"{source}.{path}" if path != "root" else source,
                code="schema_validation",
                suggestion=suggestion,
                context={
                    "schema_path": list(error.schema_path),
                    "failed_value": error.instance,
                    "validator": error.validator,
                    "validator_value": error.validator_value
                }
            ))
            
        return errors
    
    def _validate_url_templates(self, data: Dict[str, Any], source: str) -> tuple[List[ValidationError], List[ValidationError]]:
        """Validate URL templates in sources, binaries, and scripts sections."""
        errors = []
        warnings = []
        
        # Check global sections
        for section_name in ['sources', 'binaries', 'scripts']:
            section = data.get(section_name, [])
            if isinstance(section, list):
                for i, item in enumerate(section):
                    if isinstance(item, dict) and 'url' in item:
                        url = item['url']
                        if isinstance(url, str):
                            try:
                                result = self.url_processor.validate_template(url)
                                
                                # Add errors
                                for error_msg in result.errors:
                                    errors.append(ValidationError(
                                        severity=ValidationSeverity.ERROR,
                                        message=f"Invalid URL template in {section_name}[{i}]: {error_msg}",
                                        path=f"{source}.{section_name}[{i}].url",
                                        code="invalid_url_template",
                                        suggestion="Fix URL template syntax or use supported placeholders: {{version}}, {{platform}}, {{architecture}}"
                                    ))
                                
                                # Add warnings
                                for warning_msg in result.warnings:
                                    warnings.append(ValidationError(
                                        severity=ValidationSeverity.WARNING,
                                        message=f"URL template warning in {section_name}[{i}]: {warning_msg}",
                                        path=f"{source}.{section_name}[{i}].url",
                                        code="url_template_warning",
                                        suggestion="Consider adding version placeholder for better template functionality"
                                    ))
                                    
                            except Exception as e:
                                errors.append(ValidationError(
                                    severity=ValidationSeverity.ERROR,
                                    message=f"URL template validation failed in {section_name}[{i}]: {str(e)}",
                                    path=f"{source}.{section_name}[{i}].url",
                                    code="url_template_validation_error"
                                ))
        
        # Check provider-specific sections
        providers = data.get('providers', {})
        if isinstance(providers, dict):
            for provider_name, provider_config in providers.items():
                if isinstance(provider_config, dict):
                    for section_name in ['sources', 'binaries', 'scripts']:
                        section = provider_config.get(section_name, [])
                        if isinstance(section, list):
                            for i, item in enumerate(section):
                                if isinstance(item, dict) and 'url' in item:
                                    url = item['url']
                                    if isinstance(url, str):
                                        try:
                                            result = self.url_processor.validate_template(url)
                                            
                                            # Add errors
                                            for error_msg in result.errors:
                                                errors.append(ValidationError(
                                                    severity=ValidationSeverity.ERROR,
                                                    message=f"Invalid URL template in providers.{provider_name}.{section_name}[{i}]: {error_msg}",
                                                    path=f"{source}.providers.{provider_name}.{section_name}[{i}].url",
                                                    code="invalid_url_template",
                                                    suggestion="Fix URL template syntax or use supported placeholders"
                                                ))
                                            
                                            # Add warnings
                                            for warning_msg in result.warnings:
                                                warnings.append(ValidationError(
                                                    severity=ValidationSeverity.WARNING,
                                                    message=f"URL template warning in providers.{provider_name}.{section_name}[{i}]: {warning_msg}",
                                                    path=f"{source}.providers.{provider_name}.{section_name}[{i}].url",
                                                    code="url_template_warning"
                                                ))
                                                
                                        except Exception as e:
                                            errors.append(ValidationError(
                                                severity=ValidationSeverity.ERROR,
                                                message=f"URL template validation failed in providers.{provider_name}.{section_name}[{i}]: {str(e)}",
                                                path=f"{source}.providers.{provider_name}.{section_name}[{i}].url",
                                                code="url_template_validation_error"
                                            ))
        
        return errors, warnings
    
    def _validate_checksums(self, data: Dict[str, Any], source: str) -> List[ValidationError]:
        """Validate checksum format across all sections."""
        errors = []
        
        # Check global sections
        for section_name in ['sources', 'binaries', 'scripts']:
            section = data.get(section_name, [])
            if isinstance(section, list):
                for i, item in enumerate(section):
                    if isinstance(item, dict) and 'checksum' in item:
                        checksum = item['checksum']
                        if isinstance(checksum, str):
                            checksum_errors = self.checksum_validator.validate_checksum(checksum)
                            for error_msg in checksum_errors:
                                errors.append(ValidationError(
                                    severity=ValidationSeverity.ERROR,
                                    message=f"Invalid checksum in {section_name}[{i}]: {error_msg}",
                                    path=f"{source}.{section_name}[{i}].checksum",
                                    code="invalid_checksum_format",
                                    suggestion="Use format 'algorithm:hash' (e.g., 'sha256:abc123...')"
                                ))
        
        # Check provider-specific sections
        providers = data.get('providers', {})
        if isinstance(providers, dict):
            for provider_name, provider_config in providers.items():
                if isinstance(provider_config, dict):
                    for section_name in ['sources', 'binaries', 'scripts']:
                        section = provider_config.get(section_name, [])
                        if isinstance(section, list):
                            for i, item in enumerate(section):
                                if isinstance(item, dict) and 'checksum' in item:
                                    checksum = item['checksum']
                                    if isinstance(checksum, str):
                                        checksum_errors = self.checksum_validator.validate_checksum(checksum)
                                        for error_msg in checksum_errors:
                                            errors.append(ValidationError(
                                                severity=ValidationSeverity.ERROR,
                                                message=f"Invalid checksum in providers.{provider_name}.{section_name}[{i}]: {error_msg}",
                                                path=f"{source}.providers.{provider_name}.{section_name}[{i}].checksum",
                                                code="invalid_checksum_format",
                                                suggestion="Use format 'algorithm:hash' (e.g., 'sha256:abc123...')"
                                            ))
        
        return errors
    
    def _format_schema_error(self, error: jsonschema.ValidationError) -> tuple[str, Optional[str]]:
        """Format JSON schema error with helpful message and suggestion."""
        validator = error.validator
        instance = error.instance
        
        if validator == "required":
            missing_props = error.validator_value
            if isinstance(missing_props, list) and len(missing_props) == 1:
                prop = missing_props[0]
                return (
                    f"Missing required property: '{prop}'",
                    f"Add the '{prop}' field to this object"
                )
            else:
                props = ", ".join(f"'{p}'" for p in missing_props)
                return (
                    f"Missing required properties: {props}",
                    f"Add the following required fields: {props}"
                )
        
        elif validator == "type":
            expected_type = error.validator_value
            actual_type = type(instance).__name__
            return (
                f"Invalid type: expected {expected_type}, got {actual_type}",
                f"Change the value to be of type {expected_type}"
            )
        
        elif validator == "enum":
            valid_values = error.validator_value
            return (
                f"Invalid value '{instance}'. Must be one of: {valid_values}",
                f"Use one of the allowed values: {', '.join(str(v) for v in valid_values)}"
            )
        
        elif validator == "pattern":
            pattern = error.validator_value
            return (
                f"Value '{instance}' does not match required pattern: {pattern}",
                "Ensure the value matches the expected format"
            )
        
        elif validator == "minItems":
            min_items = error.validator_value
            actual_items = len(instance) if hasattr(instance, '__len__') else 0
            return (
                f"Array too short: has {actual_items} items, minimum is {min_items}",
                f"Add at least {min_items - actual_items} more items to the array"
            )
        
        elif validator == "maxItems":
            max_items = error.validator_value
            actual_items = len(instance) if hasattr(instance, '__len__') else 0
            return (
                f"Array too long: has {actual_items} items, maximum is {max_items}",
                f"Remove {actual_items - max_items} items from the array"
            )
        
        elif validator == "additionalProperties":
            return (
                f"Additional property not allowed: '{error.absolute_path[-1] if error.absolute_path else 'unknown'}'",
                "Remove the additional property or check for typos in property names"
            )
        
        else:
            return (error.message, None)
    
    def _validate_custom_rules(self, data: Dict[str, Any], source: str) -> tuple[List[ValidationError], List[ValidationError], List[ValidationError]]:
        """Apply custom validation rules beyond JSON schema."""
        errors = []
        warnings = []
        info = []
        
        # Validate version format
        version = data.get("version")
        if version and isinstance(version, str) and not re.match(r"^\d+\.\d+(\.\d+)?$", version):
            errors.append(ValidationError(
                severity=ValidationSeverity.ERROR,
                message=f"Invalid version format: '{version}'",
                path=f"{source}.version",
                code="invalid_version_format",
                suggestion="Use semantic versioning format (e.g., '1.0', '1.0.0')"
            ))
        
        # Validate that version is 0.3 for new schema features
        if version == "0.3":
            # Check for new 0.3 features usage
            new_sections = ['sources', 'binaries', 'scripts']
            for section_name in new_sections:
                if section_name in data:
                    info.append(ValidationError(
                        severity=ValidationSeverity.INFO,
                        message=f"Using saidata 0.3 feature: {section_name} section",
                        path=f"{source}.{section_name}",
                        code="saidata_0_3_feature"
                    ))
        
        # Validate metadata name consistency
        metadata = data.get("metadata", {})
        if isinstance(metadata, dict):
            name = metadata.get("name")
            display_name = metadata.get("display_name")
            
            if name and display_name and name.lower() != display_name.lower():
                info.append(ValidationError(
                    severity=ValidationSeverity.INFO,
                    message=f"Name '{name}' and display_name '{display_name}' differ significantly",
                    path=f"{source}.metadata",
                    code="name_display_name_mismatch",
                    suggestion="Consider if both names are necessary or if they should be more similar"
                ))
        
        # Validate package names in providers
        providers = data.get("providers", {})
        if isinstance(providers, dict):
            for provider_name, provider_config in providers.items():
                if isinstance(provider_config, dict):
                    packages = provider_config.get("packages", [])
                    if isinstance(packages, list):
                        for i, package in enumerate(packages):
                            if isinstance(package, dict):
                                pkg_name = package.get("name")
                                if pkg_name and not self._is_valid_package_name(pkg_name):
                                    warnings.append(ValidationError(
                                        severity=ValidationSeverity.WARNING,
                                        message=f"Potentially invalid package name: '{pkg_name}'",
                                        path=f"{source}.providers.{provider_name}.packages[{i}].name",
                                        code="suspicious_package_name",
                                        suggestion="Verify package name exists in the target repository"
                                    ))
        
        # Validate port ranges
        self._validate_ports(data, source, warnings)
        
        # Validate file paths
        self._validate_file_paths(data, source, warnings)
        
        # Validate enum values for 0.3 schema
        self._validate_enum_values(data, source, errors)
        
        return errors, warnings, info
    
    def _validate_cross_references(self, data: Dict[str, Any], source: str) -> tuple[List[ValidationError], List[ValidationError]]:
        """Validate cross-references within the saidata."""
        errors = []
        warnings = []
        
        # Collect all repository names
        repository_names = set()
        providers = data.get("providers", {})
        
        if isinstance(providers, dict):
            for provider_config in providers.values():
                if isinstance(provider_config, dict):
                    repositories = provider_config.get("repositories", [])
                    if isinstance(repositories, list):
                        for repo in repositories:
                            if isinstance(repo, dict) and "name" in repo:
                                repository_names.add(repo["name"])
        
        # Validate repository references in packages
        if isinstance(providers, dict):
            for provider_name, provider_config in providers.items():
                if isinstance(provider_config, dict):
                    packages = provider_config.get("packages", [])
                    if isinstance(packages, list):
                        for i, package in enumerate(packages):
                            if isinstance(package, dict):
                                repo_ref = package.get("repository")
                                if repo_ref and repo_ref not in repository_names:
                                    warnings.append(ValidationError(
                                        severity=ValidationSeverity.WARNING,
                                        message=f"Package references undefined repository: '{repo_ref}'",
                                        path=f"{source}.providers.{provider_name}.packages[{i}].repository",
                                        code="undefined_repository_reference",
                                        suggestion=f"Define repository '{repo_ref}' or use an existing one: {', '.join(repository_names) if repository_names else 'none defined'}"
                                    ))
        
        return errors, warnings
    
    def _is_valid_package_name(self, name: str) -> bool:
        """Check if package name looks valid (basic heuristics)."""
        if not name or len(name) < 2:
            return False
        
        # Check for common invalid patterns
        invalid_patterns = [
            r"^\s+|\s+$",  # Leading/trailing whitespace
            r"[<>|&;`$()]",  # Shell metacharacters
            r"^-",  # Starting with dash
            r"\s{2,}",  # Multiple consecutive spaces
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, name):
                return False
        
        return True
    
    def _validate_ports(self, data: Dict[str, Any], source: str, warnings: List[ValidationError]) -> None:
        """Validate port definitions."""
        def check_ports_list(ports_list: List[Any], path_prefix: str) -> None:
            if isinstance(ports_list, list):
                for i, port in enumerate(ports_list):
                    if isinstance(port, dict):
                        port_num = port.get("port")
                        if isinstance(port_num, int):
                            if port_num < 1 or port_num > 65535:
                                warnings.append(ValidationError(
                                    severity=ValidationSeverity.WARNING,
                                    message=f"Port number {port_num} is outside valid range (1-65535)",
                                    path=f"{path_prefix}[{i}].port",
                                    code="invalid_port_range",
                                    suggestion="Use a port number between 1 and 65535"
                                ))
                            elif port_num < 1024:
                                warnings.append(ValidationError(
                                    severity=ValidationSeverity.WARNING,
                                    message=f"Port {port_num} is in privileged range (< 1024)",
                                    path=f"{path_prefix}[{i}].port",
                                    code="privileged_port",
                                    suggestion="Consider using a port number >= 1024 for non-system services"
                                ))
        
        # Check global ports
        ports = data.get("ports", [])
        check_ports_list(ports, f"{source}.ports")
        
        # Check provider-specific ports
        providers = data.get("providers", {})
        if isinstance(providers, dict):
            for provider_name, provider_config in providers.items():
                if isinstance(provider_config, dict):
                    provider_ports = provider_config.get("ports", [])
                    check_ports_list(provider_ports, f"{source}.providers.{provider_name}.ports")
    
    def _validate_file_paths(self, data: Dict[str, Any], source: str, warnings: List[ValidationError]) -> None:
        """Validate file and directory paths."""
        def check_paths_list(items_list: List[Any], path_prefix: str, item_type: str) -> None:
            if isinstance(items_list, list):
                for i, item in enumerate(items_list):
                    if isinstance(item, dict):
                        path = item.get("path")
                        if isinstance(path, str):
                            # Check for suspicious path patterns
                            if path.startswith("~"):
                                warnings.append(ValidationError(
                                    severity=ValidationSeverity.WARNING,
                                    message=f"Path uses tilde expansion: '{path}'",
                                    path=f"{path_prefix}[{i}].path",
                                    code="tilde_path",
                                    suggestion="Consider using absolute paths or environment variables"
                                ))
                            elif not path.startswith("/") and not re.match(r"^[A-Za-z]:", path):
                                warnings.append(ValidationError(
                                    severity=ValidationSeverity.WARNING,
                                    message=f"Relative path detected: '{path}'",
                                    path=f"{path_prefix}[{i}].path",
                                    code="relative_path",
                                    suggestion="Consider using absolute paths for better portability"
                                ))
        
        # Check global files and directories
        files = data.get("files", [])
        check_paths_list(files, f"{source}.files", "file")
        
        directories = data.get("directories", [])
        check_paths_list(directories, f"{source}.directories", "directory")
        
        # Check provider-specific files and directories
        providers = data.get("providers", {})
        if isinstance(providers, dict):
            for provider_name, provider_config in providers.items():
                if isinstance(provider_config, dict):
                    provider_files = provider_config.get("files", [])
                    check_paths_list(provider_files, f"{source}.providers.{provider_name}.files", "file")
                    
                    provider_dirs = provider_config.get("directories", [])
                    check_paths_list(provider_dirs, f"{source}.providers.{provider_name}.directories", "directory")
    
    def _validate_enum_values(self, data: Dict[str, Any], source: str, errors: List[ValidationError]) -> None:
        """Validate enum values for 0.3 schema fields."""
        
        # Valid enum values for 0.3 schema
        valid_build_systems = ["autotools", "cmake", "make", "meson", "ninja", "custom"]
        valid_service_types = ["systemd", "init", "launchd", "windows_service", "docker", "kubernetes"]
        valid_file_types = ["config", "binary", "library", "data", "log", "temp", "socket"]
        valid_protocols = ["tcp", "udp", "sctp"]
        valid_repo_types = ["upstream", "os-default", "os-backports", "third-party"]
        valid_archive_formats = ["tar.gz", "tar.bz2", "tar.xz", "zip", "7z", "none"]
        
        # Check sources build_system
        sources = data.get('sources', [])
        if isinstance(sources, list):
            for i, source_item in enumerate(sources):
                if isinstance(source_item, dict):
                    build_system = source_item.get('build_system')
                    if build_system and build_system not in valid_build_systems:
                        errors.append(ValidationError(
                            severity=ValidationSeverity.ERROR,
                            message=f"Invalid build_system '{build_system}' in sources[{i}]",
                            path=f"{source}.sources[{i}].build_system",
                            code="invalid_enum_value",
                            suggestion=f"Use one of: {', '.join(valid_build_systems)}"
                        ))
        
        # Check binaries archive format
        binaries = data.get('binaries', [])
        if isinstance(binaries, list):
            for i, binary_item in enumerate(binaries):
                if isinstance(binary_item, dict):
                    archive = binary_item.get('archive', {})
                    if isinstance(archive, dict):
                        archive_format = archive.get('format')
                        if archive_format and archive_format not in valid_archive_formats:
                            errors.append(ValidationError(
                                severity=ValidationSeverity.ERROR,
                                message=f"Invalid archive format '{archive_format}' in binaries[{i}]",
                                path=f"{source}.binaries[{i}].archive.format",
                                code="invalid_enum_value",
                                suggestion=f"Use one of: {', '.join(valid_archive_formats)}"
                            ))
        
        # Check services type
        services = data.get('services', [])
        if isinstance(services, list):
            for i, service_item in enumerate(services):
                if isinstance(service_item, dict):
                    service_type = service_item.get('type')
                    if service_type and service_type not in valid_service_types:
                        errors.append(ValidationError(
                            severity=ValidationSeverity.ERROR,
                            message=f"Invalid service type '{service_type}' in services[{i}]",
                            path=f"{source}.services[{i}].type",
                            code="invalid_enum_value",
                            suggestion=f"Use one of: {', '.join(valid_service_types)}"
                        ))
        
        # Check files type
        files = data.get('files', [])
        if isinstance(files, list):
            for i, file_item in enumerate(files):
                if isinstance(file_item, dict):
                    file_type = file_item.get('type')
                    if file_type and file_type not in valid_file_types:
                        errors.append(ValidationError(
                            severity=ValidationSeverity.ERROR,
                            message=f"Invalid file type '{file_type}' in files[{i}]",
                            path=f"{source}.files[{i}].type",
                            code="invalid_enum_value",
                            suggestion=f"Use one of: {', '.join(valid_file_types)}"
                        ))
        
        # Check ports protocol
        ports = data.get('ports', [])
        if isinstance(ports, list):
            for i, port_item in enumerate(ports):
                if isinstance(port_item, dict):
                    protocol = port_item.get('protocol')
                    if protocol and protocol not in valid_protocols:
                        errors.append(ValidationError(
                            severity=ValidationSeverity.ERROR,
                            message=f"Invalid protocol '{protocol}' in ports[{i}]",
                            path=f"{source}.ports[{i}].protocol",
                            code="invalid_enum_value",
                            suggestion=f"Use one of: {', '.join(valid_protocols)}"
                        ))
        
        # Check repository types in providers
        providers = data.get('providers', {})
        if isinstance(providers, dict):
            for provider_name, provider_config in providers.items():
                if isinstance(provider_config, dict):
                    repositories = provider_config.get('repositories', [])
                    if isinstance(repositories, list):
                        for i, repo_item in enumerate(repositories):
                            if isinstance(repo_item, dict):
                                repo_type = repo_item.get('type')
                                if repo_type and repo_type not in valid_repo_types:
                                    errors.append(ValidationError(
                                        severity=ValidationSeverity.ERROR,
                                        message=f"Invalid repository type '{repo_type}' in providers.{provider_name}.repositories[{i}]",
                                        path=f"{source}.providers.{provider_name}.repositories[{i}].type",
                                        code="invalid_enum_value",
                                        suggestion=f"Use one of: {', '.join(valid_repo_types)}"
                                    ))
    
    def format_validation_report(self, result: ValidationResult, show_context: bool = False) -> str:
        """Format validation result as a human-readable report.
        
        Args:
            result: ValidationResult to format
            show_context: Whether to include detailed context information
            
        Returns:
            Formatted validation report string
        """
        lines = []
        
        # Summary
        if result.is_valid:
            lines.append("✅ Validation passed")
        else:
            lines.append("❌ Validation failed")
        
        lines.append(f"Total issues: {result.total_issues}")
        if result.has_errors:
            lines.append(f"Errors: {len(result.errors)}")
        if result.has_warnings:
            lines.append(f"Warnings: {len(result.warnings)}")
        if result.info:
            lines.append(f"Info: {len(result.info)}")
        
        lines.append("")
        
        # Detailed issues
        all_issues = result.errors + result.warnings + result.info
        
        for issue in all_issues:
            severity_icon = {
                ValidationSeverity.ERROR: "❌",
                ValidationSeverity.WARNING: "⚠️",
                ValidationSeverity.INFO: "ℹ️"
            }[issue.severity]
            
            lines.append(f"{severity_icon} {issue.severity.upper()}: {issue.message}")
            lines.append(f"   Path: {issue.path}")
            lines.append(f"   Code: {issue.code}")
            
            if issue.suggestion:
                lines.append(f"   Suggestion: {issue.suggestion}")
            
            if show_context and issue.context:
                lines.append(f"   Context: {issue.context}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def attempt_recovery(self, data: Dict[str, Any], validation_result: ValidationResult) -> RecoveryResult:
        """Attempt to automatically fix common validation errors.
        
        Args:
            data: Original saidata dictionary
            validation_result: Validation result with errors to fix
            
        Returns:
            RecoveryResult with fixed data and recovery information
        """
        recovered_data = data.copy()
        fixed_errors = []
        remaining_errors = []
        recovery_notes = []
        
        for error in validation_result.errors:
            try:
                if self._is_url_template_error(error):
                    recovered_data, fixed = self._fix_url_template_error(recovered_data, error)
                    if fixed:
                        fixed_errors.append(error.message)
                        recovery_notes.append(f"Fixed URL template in {error.path}")
                    else:
                        remaining_errors.append(error)
                        
                elif self._is_checksum_format_error(error):
                    recovered_data, fixed = self._fix_checksum_format_error(recovered_data, error)
                    if fixed:
                        fixed_errors.append(error.message)
                        recovery_notes.append(f"Fixed checksum format in {error.path}")
                    else:
                        remaining_errors.append(error)
                        
                elif self._is_enum_value_error(error):
                    recovered_data, fixed = self._fix_enum_value_error(recovered_data, error)
                    if fixed:
                        fixed_errors.append(error.message)
                        recovery_notes.append(f"Fixed enum value in {error.path}")
                    else:
                        remaining_errors.append(error)
                        
                elif self._is_missing_required_field_error(error):
                    recovered_data, fixed = self._fix_missing_required_field_error(recovered_data, error)
                    if fixed:
                        fixed_errors.append(error.message)
                        recovery_notes.append(f"Added missing required field in {error.path}")
                    else:
                        remaining_errors.append(error)
                        
                else:
                    remaining_errors.append(error)
                    
            except Exception as e:
                remaining_errors.append(error)
                recovery_notes.append(f"Recovery failed for {error.path}: {str(e)}")
        
        return RecoveryResult(
            recovered_data=recovered_data,
            fixed_errors=fixed_errors,
            remaining_errors=remaining_errors,
            recovery_notes=recovery_notes
        )
    
    def _is_url_template_error(self, error: ValidationError) -> bool:
        """Check if error is related to URL template validation."""
        return error.code in ["invalid_url_template", "url_template_validation_error"]
    
    def _is_checksum_format_error(self, error: ValidationError) -> bool:
        """Check if error is related to checksum format."""
        return error.code == "invalid_checksum_format"
    
    def _is_enum_value_error(self, error: ValidationError) -> bool:
        """Check if error is related to invalid enum values."""
        return error.code == "invalid_enum_value"
    
    def _is_missing_required_field_error(self, error: ValidationError) -> bool:
        """Check if error is related to missing required fields."""
        return error.code == "schema_validation" and "required" in error.message.lower()
    
    def _fix_url_template_error(self, data: Dict[str, Any], error: ValidationError) -> tuple[Dict[str, Any], bool]:
        """Attempt to fix URL template errors."""
        path_parts = error.path.split('.')
        
        try:
            # Navigate to the problematic URL field
            current = data
            for part in path_parts[1:-1]:  # Skip source name and 'url'
                if '[' in part and ']' in part:
                    # Handle array indices like "sources[0]"
                    array_name = part.split('[')[0]
                    index = int(part.split('[')[1].split(']')[0])
                    current = current[array_name][index]
                else:
                    current = current[part]
            
            if 'url' in current and isinstance(current['url'], str):
                original_url = current['url']
                
                # Common URL template fixes
                fixed_url = original_url
                
                # Fix single braces to double braces
                fixed_url = re.sub(r'(?<!\{)\{([^}]+)\}(?!\})', r'{{\1}}', fixed_url)
                
                # Fix common placeholder names
                placeholder_fixes = {
                    '{{ver}}': '{{version}}',
                    '{{v}}': '{{version}}',
                    '{{os}}': '{{platform}}',
                    '{{arch}}': '{{architecture}}',
                    '{{cpu}}': '{{architecture}}'
                }
                
                for old, new in placeholder_fixes.items():
                    fixed_url = fixed_url.replace(old, new)
                
                # Validate the fixed URL
                try:
                    result = self.url_processor.validate_template(fixed_url)
                    if result.is_valid:
                        current['url'] = fixed_url
                        return data, True
                except:
                    pass
                    
        except (KeyError, IndexError, ValueError):
            pass
        
        return data, False
    
    def _fix_checksum_format_error(self, data: Dict[str, Any], error: ValidationError) -> tuple[Dict[str, Any], bool]:
        """Attempt to fix checksum format errors."""
        path_parts = error.path.split('.')
        
        try:
            # Navigate to the problematic checksum field
            current = data
            for part in path_parts[1:-1]:  # Skip source name and 'checksum'
                if '[' in part and ']' in part:
                    array_name = part.split('[')[0]
                    index = int(part.split('[')[1].split(']')[0])
                    current = current[array_name][index]
                else:
                    current = current[part]
            
            if 'checksum' in current and isinstance(current['checksum'], str):
                original_checksum = current['checksum']
                
                # Common checksum format fixes
                fixed_checksum = original_checksum
                
                # If it's just a hash without algorithm, try to detect and add algorithm
                if ':' not in fixed_checksum:
                    hash_length = len(fixed_checksum)
                    if hash_length == 32:
                        fixed_checksum = f"md5:{fixed_checksum}"
                    elif hash_length == 64:
                        fixed_checksum = f"sha256:{fixed_checksum}"
                    elif hash_length == 128:
                        fixed_checksum = f"sha512:{fixed_checksum}"
                
                # Normalize algorithm names
                algorithm_fixes = {
                    'SHA256:': 'sha256:',
                    'SHA512:': 'sha512:',
                    'MD5:': 'md5:',
                    'sha-256:': 'sha256:',
                    'sha-512:': 'sha512:'
                }
                
                for old, new in algorithm_fixes.items():
                    if fixed_checksum.startswith(old):
                        fixed_checksum = fixed_checksum.replace(old, new, 1)
                        break
                
                # Validate the fixed checksum
                checksum_errors = self.checksum_validator.validate_checksum(fixed_checksum)
                if not checksum_errors:
                    current['checksum'] = fixed_checksum
                    return data, True
                    
        except (KeyError, IndexError, ValueError):
            pass
        
        return data, False
    
    def _fix_enum_value_error(self, data: Dict[str, Any], error: ValidationError) -> tuple[Dict[str, Any], bool]:
        """Attempt to fix enum value errors."""
        path_parts = error.path.split('.')
        
        try:
            # Navigate to the problematic field
            current = data
            field_name = path_parts[-1]
            
            for part in path_parts[1:-1]:  # Skip source name and field name
                if '[' in part and ']' in part:
                    array_name = part.split('[')[0]
                    index = int(part.split('[')[1].split(']')[0])
                    current = current[array_name][index]
                else:
                    current = current[part]
            
            if field_name in current:
                original_value = current[field_name]
                
                # Common enum value fixes
                enum_fixes = {
                    # Build system fixes
                    'autoconf': 'autotools',
                    'automake': 'autotools',
                    'configure': 'autotools',
                    'makefile': 'make',
                    'gnumake': 'make',
                    
                    # Service type fixes
                    'system': 'systemd',
                    'service': 'systemd',
                    'daemon': 'systemd',
                    'launchctl': 'launchd',
                    'windows': 'windows_service',
                    'win_service': 'windows_service',
                    
                    # File type fixes
                    'configuration': 'config',
                    'executable': 'binary',
                    'lib': 'library',
                    'logfile': 'log',
                    'temporary': 'temp',
                    
                    # Protocol fixes
                    'TCP': 'tcp',
                    'UDP': 'udp',
                    'SCTP': 'sctp',
                    
                    # Repository type fixes
                    'official': 'upstream',
                    'main': 'os-default',
                    'backport': 'os-backports',
                    'third_party': 'third-party',
                    'external': 'third-party',
                    
                    # Archive format fixes
                    'tgz': 'tar.gz',
                    'tbz2': 'tar.bz2',
                    'txz': 'tar.xz',
                    'tar': 'tar.gz',
                    'gzip': 'tar.gz',
                    'bzip2': 'tar.bz2',
                    'xz': 'tar.xz'
                }
                
                if isinstance(original_value, str):
                    fixed_value = enum_fixes.get(original_value.lower(), original_value)
                    if fixed_value != original_value:
                        current[field_name] = fixed_value
                        return data, True
                        
        except (KeyError, IndexError, ValueError):
            pass
        
        return data, False
    
    def _fix_missing_required_field_error(self, data: Dict[str, Any], error: ValidationError) -> tuple[Dict[str, Any], bool]:
        """Attempt to fix missing required field errors."""
        path_parts = error.path.split('.')
        
        try:
            # Navigate to the object missing the required field
            current = data
            for part in path_parts[1:]:  # Skip source name
                if '[' in part and ']' in part:
                    array_name = part.split('[')[0]
                    index = int(part.split('[')[1].split(']')[0])
                    current = current[array_name][index]
                else:
                    current = current[part]
            
            # Extract required field name from error message
            if "Missing required property:" in error.message:
                field_match = re.search(r"'([^']+)'", error.message)
                if field_match:
                    required_field = field_match.group(1)
                    
                    # Add default values for common required fields
                    default_values = {
                        'name': 'unnamed',
                        'package_name': 'unnamed-package',
                        'url': 'https://example.com/download',
                        'build_system': 'make',
                        'path': '/tmp/default',
                        'port': 8080
                    }
                    
                    if required_field in default_values:
                        current[required_field] = default_values[required_field]
                        return data, True
                        
        except (KeyError, IndexError, ValueError):
            pass
        
        return data, False   
 
    def validate_with_recovery(self, data: Dict[str, Any], source: str = "data", max_recovery_attempts: int = 3) -> tuple[ValidationResult, Optional[RecoveryResult]]:
        """Validate saidata with automatic error recovery.
        
        Args:
            data: Saidata dictionary to validate
            source: Source identifier for error reporting
            max_recovery_attempts: Maximum number of recovery attempts
            
        Returns:
            Tuple of (final_validation_result, recovery_result_if_applied)
        """
        current_data = data.copy()
        recovery_result = None
        
        for attempt in range(max_recovery_attempts + 1):
            validation_result = self.validate_data(current_data, source)
            
            if validation_result.is_valid or attempt == max_recovery_attempts:
                # Either validation passed or we've exhausted recovery attempts
                return validation_result, recovery_result
            
            # Attempt recovery
            recovery_result = self.attempt_recovery(current_data, validation_result)
            
            if not recovery_result.fixed_errors:
                # No errors were fixed, stop trying
                return validation_result, recovery_result
            
            # Use the recovered data for the next validation attempt
            current_data = recovery_result.recovered_data
        
        # This should not be reached, but return the last validation result
        final_validation = self.validate_data(current_data, source)
        return final_validation, recovery_result
    
    def format_recovery_report(self, recovery_result: RecoveryResult) -> str:
        """Format recovery result as a human-readable report.
        
        Args:
            recovery_result: RecoveryResult to format
            
        Returns:
            Formatted recovery report string
        """
        lines = []
        
        if recovery_result.fixed_errors:
            lines.append("🔧 Validation Error Recovery Report")
            lines.append(f"Fixed {len(recovery_result.fixed_errors)} error(s)")
            lines.append("")
            
            lines.append("Fixed Errors:")
            for error in recovery_result.fixed_errors:
                lines.append(f"  ✅ {error}")
            lines.append("")
            
            if recovery_result.recovery_notes:
                lines.append("Recovery Actions:")
                for note in recovery_result.recovery_notes:
                    lines.append(f"  🔧 {note}")
                lines.append("")
        
        if recovery_result.remaining_errors:
            lines.append(f"Remaining Errors: {len(recovery_result.remaining_errors)}")
            for error in recovery_result.remaining_errors:
                lines.append(f"  ❌ {error.message}")
                lines.append(f"     Path: {error.path}")
                if error.suggestion:
                    lines.append(f"     Suggestion: {error.suggestion}")
                lines.append("")
        
        return "\n".join(lines)