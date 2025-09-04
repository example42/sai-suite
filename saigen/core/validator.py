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


class SaidataValidator:
    """Comprehensive saidata validation system."""
    
    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize validator with schema.
        
        Args:
            schema_path: Path to saidata schema JSON file. If None, uses default.
        """
        self.schema_path = schema_path or Path(__file__).parent.parent.parent / "schemas" / "saidata-0.2-schema.json"
        self._schema: Optional[Dict[str, Any]] = None
        self._validator: Optional[Draft7Validator] = None
        
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