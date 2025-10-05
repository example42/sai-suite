"""Saidata loading and validation functionality with repository-based hierarchical structure."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import jsonschema
import yaml
from pydantic import ValidationError as PydanticValidationError

from ..models.config import SaiConfig
from ..models.saidata import SaiData
from .saidata_path import HierarchicalPathResolver, SaidataPath

if TYPE_CHECKING:
    from .saidata_repository_manager import SaidataRepositoryManager


logger = logging.getLogger(__name__)


class SaidataNotFoundError(Exception):
    """Raised when saidata file is not found."""

    def __init__(
        self, message: str, software_name: str, expected_paths: Optional[List[Path]] = None
    ):
        """Initialize the exception with detailed information.

        Args:
            message: Error message
            software_name: Name of the software that was not found
            expected_paths: List of paths that were searched
        """
        super().__init__(message)
        self.software_name = software_name
        self.expected_paths = expected_paths or []


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
    """Loads and validates saidata files using repository-based hierarchical structure exclusively."""

    def __init__(
        self,
        config: Optional[SaiConfig] = None,
        repository_manager: Optional["SaidataRepositoryManager"] = None,
    ):
        """Initialize the saidata loader.

        Args:
            config: Sai configuration object. If None, uses default paths.
            repository_manager: Repository manager for accessing saidata repositories.
        """
        self.config = config or SaiConfig()
        self._repository_manager = repository_manager
        self._schema_cache: Optional[Dict[str, Any]] = None

        # Initialize hierarchical path resolver
        search_paths = self.get_search_paths()
        self._path_resolver = HierarchicalPathResolver(search_paths)

        # Initialize saidata cache if enabled
        if self.config.cache_enabled:
            from ..utils.cache import SaidataCache

            self._saidata_cache = SaidataCache(self.config)
        else:
            self._saidata_cache = None

    def load_saidata(self, software_name: str, use_cache: bool = True) -> Optional[SaiData]:
        """Load and validate saidata for software using hierarchical structure exclusively.

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

        # Validate software name
        validation_errors = self._path_resolver.validate_software_name(software_name)
        if validation_errors:
            raise ValueError(
                f"Invalid software name '{software_name}': {'; '.join(validation_errors)}"
            )

        # Ensure repository is available if repository manager is configured
        if self._repository_manager:
            try:
                # This will update repository if needed and ensure it's available
                repo_status = self._repository_manager.get_repository_status()
                if (
                    not repo_status.is_healthy
                    and not self._repository_manager.repository_path.exists()
                ):
                    logger.warning(
                        f"Repository not available, attempting update for {software_name}"
                    )
                    self._repository_manager.update_repository(force=False)
            except Exception as e:
                logger.warning(f"Repository check failed for {software_name}: {e}")

        # Find all hierarchical saidata files for the software (hierarchical structure only)
        saidata_files = self._find_hierarchical_saidata_files(software_name)

        if not saidata_files:
            # Generate comprehensive error message with expected hierarchical paths
            expected_paths = self._generate_expected_hierarchical_paths(software_name)

            error_msg = self._build_saidata_not_found_error(software_name, expected_paths)
            raise SaidataNotFoundError(error_msg, software_name, expected_paths)

        # Check cache first if enabled and requested
        merged_data = None
        if use_cache and self._saidata_cache:
            merged_data = self._saidata_cache.get_cached_saidata(software_name, saidata_files)
            if merged_data:
                logger.debug(f"Using cached saidata for {software_name}")

        # Load and merge saidata files if not cached
        if merged_data is None:
            merged_data = self._merge_hierarchical_saidata_files(saidata_files)

            # Cache the merged data if caching is enabled
            if self._saidata_cache:
                self._saidata_cache.update_saidata_cache(software_name, saidata_files, merged_data)

        # Validate the merged data
        validation_result = self.validate_saidata(merged_data)
        if validation_result.has_errors:
            error_msg = f"Saidata validation failed for {software_name}: {
                '; '.join(
                    validation_result.errors)}"
            logger.error(error_msg)
            raise ValidationError(error_msg)

        if validation_result.has_warnings:
            for warning in validation_result.warnings:
                logger.warning(f"Saidata validation warning for {software_name}: {warning}")

        # Create SaiData object
        try:
            saidata = SaiData(**merged_data)
            logger.info(f"Successfully loaded hierarchical saidata for {software_name}")
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

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def get_expected_hierarchical_path(
        self, software_name: str, base_path: Optional[Path] = None
    ) -> SaidataPath:
        """Get the expected hierarchical path for a software name.

        Args:
            software_name: Name of the software
            base_path: Base path to use (uses first search path if None)

        Returns:
            SaidataPath instance with expected hierarchical path

        Raises:
            ValueError: If software_name is invalid
        """
        return self._path_resolver.get_expected_path(software_name, base_path)

    def validate_hierarchical_structure(self, base_path: Path) -> List[str]:
        """Validate that a directory follows the hierarchical saidata structure.

        Args:
            base_path: Base directory to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not base_path.exists():
            errors.append(f"Base path does not exist: {base_path}")
            return errors

        if not base_path.is_dir():
            errors.append(f"Base path is not a directory: {base_path}")
            return errors

        software_dir = base_path / "software"
        if not software_dir.exists():
            errors.append(f"Missing 'software' directory in: {base_path}")
            return errors

        if not software_dir.is_dir():
            errors.append(f"'software' is not a directory in: {base_path}")
            return errors

        # Check for valid prefix directories (2-character subdirectories)
        try:
            prefix_dirs = [d for d in software_dir.iterdir() if d.is_dir()]
            if not prefix_dirs:
                errors.append(f"No prefix directories found in: {software_dir}")
            else:
                for prefix_dir in prefix_dirs:
                    if len(prefix_dir.name) > 2:
                        errors.append(
                            f"Invalid prefix directory name (should be 1-2 characters): {prefix_dir.name}"
                        )
        except (OSError, PermissionError) as e:
            errors.append(f"Error reading software directory {software_dir}: {e}")

        return errors

    def find_all_hierarchical_software(self, base_path: Path) -> List[str]:
        """Find all software names in a hierarchical saidata structure.

        Args:
            base_path: Base directory to search

        Returns:
            List of software names found in the hierarchical structure
        """
        software_names = []
        software_dir = base_path / "software"

        if not software_dir.exists() or not software_dir.is_dir():
            logger.debug(f"Software directory not found: {software_dir}")
            return software_names

        try:
            # Iterate through prefix directories
            for prefix_dir in software_dir.iterdir():
                if not prefix_dir.is_dir():
                    continue

                # Iterate through software directories
                for software_dir_path in prefix_dir.iterdir():
                    if not software_dir_path.is_dir():
                        continue

                    # Check if default saidata file exists
                    saidata_path = SaidataPath.from_software_name(software_dir_path.name, base_path)
                    if saidata_path.find_existing_file():
                        software_names.append(software_dir_path.name)
                        logger.debug(f"Found hierarchical software: {software_dir_path.name}")

        except (OSError, PermissionError) as e:
            logger.warning(f"Error scanning hierarchical structure in {base_path}: {e}")

        return sorted(software_names)

    def _find_hierarchical_saidata_files(self, software_name: str) -> List[Path]:
        """Find saidata files using hierarchical structure exclusively.

        Args:
            software_name: Name of the software to find saidata for

        Returns:
            List of hierarchical saidata file paths in precedence order
        """
        saidata_files = []

        # Search only in hierarchical structure across all search paths
        for search_path in self.get_search_paths():
            try:
                saidata_path = SaidataPath.from_software_name(software_name, search_path)
                existing_file = saidata_path.find_existing_file()
                if existing_file:
                    saidata_files.append(existing_file)
                    logger.debug(f"Found hierarchical saidata file: {existing_file}")
            except ValueError as e:
                logger.debug(f"Invalid software name for path {search_path}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error searching for saidata in {search_path}: {e}")
                continue

        return saidata_files

    def _generate_expected_hierarchical_paths(self, software_name: str) -> List[Path]:
        """Generate expected hierarchical paths for error reporting.

        Args:
            software_name: Name of the software

        Returns:
            List of expected hierarchical paths
        """
        expected_paths = []

        for search_path in self.get_search_paths():
            try:
                saidata_path = SaidataPath.from_software_name(software_name, search_path)
                expected_paths.append(saidata_path.hierarchical_path)
            except ValueError:
                # Skip invalid paths
                continue

        return expected_paths

    def _build_saidata_not_found_error(self, software_name: str, expected_paths: List[Path]) -> str:
        """Build comprehensive error message for missing saidata.

        Args:
            software_name: Name of the software that was not found
            expected_paths: List of expected hierarchical paths

        Returns:
            Detailed error message
        """
        error_lines = [
            f"No saidata found for software '{software_name}' in hierarchical structure.",
            "",
            "The hierarchical saidata structure requires files to be located at:",
            f"  software/{software_name[:2].lower()}/{software_name}/default.yaml",
            "",
            "Searched the following hierarchical paths:",
        ]

        for i, path in enumerate(expected_paths, 1):
            exists_status = "✓ exists" if path.exists() else "✗ not found"
            error_lines.append(f"  {i}. {path} ({exists_status})")

        if self._repository_manager:
            repo_status = self._repository_manager.get_repository_status()
            error_lines.extend(
                [
                    "",
                    "Repository information:",
                    f"  URL: {self.config.saidata_repository_url}",
                    f"  Status: {repo_status.status.value}",
                    f"  Local path: {self._repository_manager.repository_path}",
                ]
            )

            if repo_status.error_message:
                error_lines.append(f"  Error: {repo_status.error_message}")

            if not repo_status.is_healthy:
                error_lines.extend(
                    [
                        "",
                        "Suggestions:",
                        "  1. Check your internet connection",
                        "  2. Verify the repository URL is correct",
                        "  3. Try running with --force-update to refresh the repository",
                        "  4. Check if the software name is spelled correctly",
                    ]
                )
        else:
            error_lines.extend(
                [
                    "",
                    "Suggestions:",
                    "  1. Check if the software name is spelled correctly",
                    "  2. Verify the saidata paths in your configuration",
                    "  3. Ensure saidata files follow the hierarchical structure",
                ]
            )

        return "\n".join(error_lines)

    def _merge_hierarchical_saidata_files(self, saidata_files: List[Path]) -> Dict[str, Any]:
        """Merge multiple hierarchical saidata files with precedence rules.

        Args:
            saidata_files: List of hierarchical saidata file paths in precedence order
                          (higher precedence files first)

        Returns:
            Merged saidata dictionary

        Raises:
            ValueError: If no files provided or files cannot be loaded
        """
        if not saidata_files:
            raise ValueError("No saidata files provided for merging")

        logger.debug(f"Merging {len(saidata_files)} hierarchical saidata files")

        # Start with the lowest precedence file (last in list)
        try:
            merged_data = self._load_hierarchical_saidata_file(saidata_files[-1])
            logger.debug(f"Base saidata loaded from: {saidata_files[-1]}")
        except Exception as e:
            raise ValueError(f"Failed to load base saidata file {saidata_files[-1]}: {e}") from e

        # Merge higher precedence files (earlier in list)
        for file_path in reversed(saidata_files[:-1]):
            try:
                file_data = self._load_hierarchical_saidata_file(file_path)
                merged_data = self._deep_merge_hierarchical(merged_data, file_data)
                logger.debug(f"Merged hierarchical saidata from: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to merge saidata file {file_path}: {e}")
                # Continue with other files rather than failing completely
                continue

        # Validate merged data has required structure
        if not isinstance(merged_data, dict):
            raise ValueError("Merged saidata must be a dictionary")

        if "metadata" not in merged_data:
            logger.warning("Merged saidata missing metadata section")

        return merged_data

    def _load_hierarchical_saidata_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a single hierarchical saidata file with validation.

        Args:
            file_path: Path to the hierarchical saidata file

        Returns:
            Loaded saidata dictionary

        Raises:
            ValueError: If file format is not supported or parsing fails
        """
        if not file_path.exists():
            raise ValueError(f"Saidata file does not exist: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Validate file is in hierarchical structure
        if not self._is_hierarchical_path(file_path):
            logger.warning(f"File not in hierarchical structure: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if file_path.suffix.lower() == ".json":
                    data = json.load(f)
                elif file_path.suffix.lower() in [".yaml", ".yml"]:
                    data = yaml.safe_load(f) or {}
                else:
                    raise ValueError(f"Unsupported file format: {file_path.suffix}")

            # Basic validation of loaded data
            if not isinstance(data, dict):
                raise ValueError(f"Saidata file must contain a dictionary, got {type(data)}")

            logger.debug(f"Successfully loaded hierarchical saidata from: {file_path}")
            return data

        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValueError(f"Failed to parse hierarchical saidata {file_path}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load hierarchical saidata {file_path}: {e}") from e

    def _is_hierarchical_path(self, file_path: Path) -> bool:
        """Check if a file path follows the hierarchical structure.

        Args:
            file_path: Path to check

        Returns:
            True if path follows hierarchical structure
        """
        try:
            parts = file_path.parts
            # Look for pattern: .../software/{prefix}/{software_name}/default.yaml
            software_idx = None
            for i, part in enumerate(parts):
                if part == "software":
                    software_idx = i
                    break

            if software_idx is None:
                return False

            # Check if we have at least 3 more parts: prefix, software_name, filename
            if len(parts) < software_idx + 4:
                return False

            prefix = parts[software_idx + 1]
            software_name = parts[software_idx + 2]
            filename = parts[software_idx + 3]

            # Validate structure
            return (
                len(prefix) <= 2
                and len(software_name) > 0  # Prefix should be 1-2 characters
                and filename  # Software name should exist
                in ["default.yaml", "default.yml", "default.json"]  # Standard filename
            )
        except (IndexError, AttributeError):
            return False

    def _deep_merge_hierarchical(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two hierarchical saidata dictionaries with override taking precedence.

        This method implements saidata-specific merge logic for hierarchical files:
        - Metadata sections are merged with override precedence
        - Package lists are merged intelligently (by name when possible)
        - Service lists are merged intelligently (by name when possible)
        - Provider configurations are merged with override precedence

        Args:
            base: Base saidata dictionary (lower precedence)
            override: Override saidata dictionary (higher precedence)

        Returns:
            Merged saidata dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key not in result:
                # New key from override
                result[key] = value
            elif key == "packages" and isinstance(result[key], list) and isinstance(value, list):
                # Merge package lists intelligently
                result[key] = self._merge_package_lists(result[key], value)
            elif key == "services" and isinstance(result[key], list) and isinstance(value, list):
                # Merge service lists intelligently
                result[key] = self._merge_service_lists(result[key], value)
            elif isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                result[key] = self._deep_merge_hierarchical(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                # For other lists, extend with override values
                result[key] = result[key] + value
            else:
                # For other types, override completely replaces base
                result[key] = value

        return result

    def _merge_package_lists(
        self, base_packages: List[Dict[str, Any]], override_packages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge package lists intelligently by package name.

        Args:
            base_packages: Base package list
            override_packages: Override package list

        Returns:
            Merged package list
        """
        # Create a map of base packages by name
        base_map = {}
        for pkg in base_packages:
            if isinstance(pkg, dict) and "name" in pkg:
                base_map[pkg["name"]] = pkg

        result = []
        used_names = set()

        # Add override packages (they take precedence)
        for pkg in override_packages:
            if isinstance(pkg, dict) and "name" in pkg:
                result.append(pkg)
                used_names.add(pkg["name"])
            else:
                result.append(pkg)

        # Add base packages that weren't overridden
        for pkg in base_packages:
            if isinstance(pkg, dict) and "name" in pkg:
                if pkg["name"] not in used_names:
                    result.append(pkg)
            else:
                # Add packages without names as-is
                result.append(pkg)

        return result

    def _merge_service_lists(
        self, base_services: List[Dict[str, Any]], override_services: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge service lists intelligently by service name.

        Args:
            base_services: Base service list
            override_services: Override service list

        Returns:
            Merged service list
        """
        # Create a map of base services by name
        base_map = {}
        for svc in base_services:
            if isinstance(svc, dict) and "name" in svc:
                base_map[svc["name"]] = svc

        result = []
        used_names = set()

        # Add override services (they take precedence)
        for svc in override_services:
            if isinstance(svc, dict) and "name" in svc:
                result.append(svc)
                used_names.add(svc["name"])
            else:
                result.append(svc)

        # Add base services that weren't overridden
        for svc in base_services:
            if isinstance(svc, dict) and "name" in svc:
                if svc["name"] not in used_names:
                    result.append(svc)
            else:
                # Add services without names as-is
                result.append(svc)

        return result

    def _load_schema(self) -> None:
        """Load the JSON schema for saidata validation."""
        schema_path = Path(__file__).parent.parent.parent / "schemas" / "saidata-0.2-schema.json"

        try:
            with open(schema_path, "r", encoding="utf-8") as f:
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
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                },
                "required": ["version", "metadata"],
            }

    def _validate_metadata(
        self, data: Dict[str, Any], errors: List[str], warnings: List[str]
    ) -> None:
        """Validate metadata section."""
        metadata = data.get("metadata", {})

        if not metadata.get("name"):
            errors.append("Metadata must have a name field")

        if not metadata.get("description"):
            warnings.append("Metadata should have a description field")

        # Validate URLs if present
        urls = metadata.get("urls", {})
        if urls:
            for url_type, url in urls.items():
                if url and not isinstance(url, str):
                    errors.append(f"URL {url_type} must be a string")

    def _validate_packages(
        self, data: Dict[str, Any], errors: List[str], warnings: List[str]
    ) -> None:
        """Validate packages section."""
        packages = data.get("packages", [])

        if not packages:
            warnings.append("No packages defined")
            return

        for i, package in enumerate(packages):
            if not isinstance(package, dict):
                errors.append(f"Package {i} must be an object")
                continue

            if not package.get("name"):
                errors.append(f"Package {i} must have a name field")

    def _validate_services(
        self, data: Dict[str, Any], errors: List[str], warnings: List[str]
    ) -> None:
        """Validate services section."""
        services = data.get("services", [])

        for i, service in enumerate(services):
            if not isinstance(service, dict):
                errors.append(f"Service {i} must be an object")
                continue

            if not service.get("name"):
                errors.append(f"Service {i} must have a name field")

            service_type = service.get("type")
            if service_type and service_type not in [
                "systemd",
                "init",
                "launchd",
                "windows_service",
                "docker",
                "kubernetes",
            ]:
                errors.append(f"Service {i} has invalid type: {service_type}")

    def _validate_providers(
        self, data: Dict[str, Any], errors: List[str], warnings: List[str]
    ) -> None:
        """Validate providers section."""
        providers = data.get("providers", {})

        if not providers:
            warnings.append("No provider-specific configurations defined")
            return

        for provider_name, provider_config in providers.items():
            if not isinstance(provider_config, dict):
                errors.append(f"Provider {provider_name} configuration must be an object")
                continue

            # Validate provider-specific packages
            provider_packages = provider_config.get("packages", [])
            for i, package in enumerate(provider_packages):
                if not isinstance(package, dict):
                    errors.append(f"Provider {provider_name} package {i} must be an object")
                    continue

                if not package.get("name"):
                    errors.append(f"Provider {provider_name} package {i} must have a name field")


class ValidationError(Exception):
    """Raised when saidata validation fails."""
