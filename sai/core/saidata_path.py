"""Hierarchical path resolution for saidata files."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SaidataPath:
    """Represents a hierarchical saidata path for a software package.

    The hierarchical structure follows the format:
    software/{first_two_letters}/{software_name}/default.yaml

    For example:
    - apache -> software/ap/apache/default.yaml
    - nginx -> software/ng/nginx/default.yaml
    - mysql -> software/my/mysql/default.yaml
    """

    software_name: str
    hierarchical_path: Path

    @classmethod
    def from_software_name(cls, software_name: str, base_path: Path) -> "SaidataPath":
        """Create a SaidataPath from a software name and base path.

        Args:
            software_name: Name of the software (e.g., "apache", "nginx")
            base_path: Base directory path where saidata is stored

        Returns:
            SaidataPath instance with hierarchical path

        Raises:
            ValueError: If software_name is empty or invalid
        """
        if not software_name or not software_name.strip():
            raise ValueError("Software name cannot be empty")

        # Normalize software name (lowercase, strip whitespace)
        normalized_name = software_name.strip().lower()

        # Validate software name contains only valid characters
        if not normalized_name.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError(
                f"Invalid software name: {software_name}. Must contain only alphanumeric characters, hyphens, underscores, and dots.")

        # Generate prefix from first two characters
        prefix = normalized_name[:2] if len(normalized_name) >= 2 else normalized_name

        # Build hierarchical path: software/{prefix}/{software_name}/default.yaml
        hierarchical_path = base_path / "software" / prefix / normalized_name / "default.yaml"

        logger.debug(f"Generated hierarchical path for '{software_name}': {hierarchical_path}")

        return cls(software_name=normalized_name, hierarchical_path=hierarchical_path)

    def exists(self) -> bool:
        """Check if the hierarchical saidata file exists.

        Returns:
            True if the file exists and is readable, False otherwise
        """
        try:
            return self.hierarchical_path.exists() and self.hierarchical_path.is_file()
        except (OSError, PermissionError) as e:
            logger.debug(f"Error checking file existence for {self.hierarchical_path}: {e}")
            return False

    def get_directory(self) -> Path:
        """Get the directory containing the saidata file.

        Returns:
            Path to the directory (software/{prefix}/{software_name}/)
        """
        return self.hierarchical_path.parent

    def get_alternative_files(self) -> List[Path]:
        """Get alternative saidata files in the same directory.

        Looks for files with different extensions in the same directory:
        - default.yml
        - default.json
        - saidata.yaml
        - saidata.yml
        - saidata.json

        Returns:
            List of existing alternative file paths
        """
        directory = self.get_directory()
        if not directory.exists():
            return []

        alternative_names = [
            "default.yml",
            "default.json",
            "saidata.yaml",
            "saidata.yml",
            "saidata.json",
        ]

        alternatives = []
        for name in alternative_names:
            alt_path = directory / name
            if alt_path.exists() and alt_path.is_file():
                alternatives.append(alt_path)
                logger.debug(f"Found alternative saidata file: {alt_path}")

        return alternatives

    def find_existing_file(self) -> Optional[Path]:
        """Find the first existing saidata file for this software.

        Searches in this order:
        1. default.yaml (primary)
        2. default.yml
        3. default.json
        4. saidata.yaml
        5. saidata.yml
        6. saidata.json

        Returns:
            Path to the first existing file, or None if no file exists
        """
        # Check primary file first
        if self.exists():
            return self.hierarchical_path

        # Check alternatives
        alternatives = self.get_alternative_files()
        if alternatives:
            return alternatives[0]  # Return first found alternative

        return None

    def validate_path(self) -> List[str]:
        """Validate the hierarchical path structure.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check if software name is valid
        if not self.software_name:
            errors.append("Software name is empty")
            return errors

        # Check path structure
        path_parts = self.hierarchical_path.parts
        if len(path_parts) < 4:
            errors.append(f"Invalid hierarchical path structure: {self.hierarchical_path}")
            return errors

        # Validate path components
        if path_parts[-4] != "software":
            errors.append(f"Path must contain 'software' directory: {self.hierarchical_path}")

        expected_prefix = (
            self.software_name[:2] if len(self.software_name) >= 2 else self.software_name
        )
        if path_parts[-3] != expected_prefix:
            errors.append(
                f"Prefix directory '{path_parts[-3]}' does not match expected '{expected_prefix}'"
            )

        if path_parts[-2] != self.software_name:
            errors.append(
                f"Software directory '{path_parts[-2]}' does not match software name '{self.software_name}'"
            )

        if path_parts[-1] != "default.yaml":
            errors.append(f"File name '{path_parts[-1]}' should be 'default.yaml'")

        return errors

    def __str__(self) -> str:
        """String representation of the SaidataPath."""
        return str(self.hierarchical_path)

    def __repr__(self) -> str:
        """Detailed string representation of the SaidataPath."""
        return f"SaidataPath(software_name='{
            self.software_name}', hierarchical_path='{
            self.hierarchical_path}')"


class HierarchicalPathResolver:
    """Resolves hierarchical saidata paths across multiple search directories."""

    def __init__(self, search_paths: List[Path]):
        """Initialize the path resolver.

        Args:
            search_paths: List of base directories to search for saidata files
        """
        self.search_paths = search_paths
        logger.debug(f"Initialized HierarchicalPathResolver with {len(search_paths)} search paths")

    def find_saidata_files(self, software_name: str) -> List[Path]:
        """Find all hierarchical saidata files for the given software.

        Args:
            software_name: Name of the software to search for

        Returns:
            List of existing saidata file paths, ordered by search path precedence

        Raises:
            ValueError: If software_name is invalid
        """
        found_files = []

        for search_path in self.search_paths:
            if not search_path.exists() or not search_path.is_dir():
                logger.debug(f"Search path does not exist or is not a directory: {search_path}")
                continue

            try:
                saidata_path = SaidataPath.from_software_name(software_name, search_path)

                # Validate the path structure
                validation_errors = saidata_path.validate_path()
                if validation_errors:
                    logger.debug(f"Path validation failed for {saidata_path}: {validation_errors}")
                    continue

                # Find existing file
                existing_file = saidata_path.find_existing_file()
                if existing_file:
                    found_files.append(existing_file)
                    logger.debug(f"Found saidata file: {existing_file}")

            except ValueError as e:
                logger.debug(
                    f"Error creating SaidataPath for '{software_name}' in {search_path}: {e}"
                )
                continue
            except Exception as e:
                logger.warning(
                    f"Unexpected error searching for '{software_name}' in {search_path}: {e}"
                )
                continue

        logger.info(f"Found {len(found_files)} saidata files for '{software_name}'")
        return found_files

    def get_expected_path(
        self, software_name: str, base_path: Optional[Path] = None
    ) -> SaidataPath:
        """Get the expected hierarchical path for a software name.

        Args:
            software_name: Name of the software
            base_path: Base path to use (uses first search path if None)

        Returns:
            SaidataPath instance with expected hierarchical path

        Raises:
            ValueError: If software_name is invalid or no search paths available
        """
        if base_path is None:
            if not self.search_paths:
                raise ValueError("No search paths available and no base_path provided")
            base_path = self.search_paths[0]

        return SaidataPath.from_software_name(software_name, base_path)

    def validate_software_name(self, software_name: str) -> List[str]:
        """Validate a software name for hierarchical path generation.

        Args:
            software_name: Software name to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not software_name or not software_name.strip():
            errors.append("Software name cannot be empty")
            return errors

        normalized_name = software_name.strip().lower()

        # Check for valid characters
        if not normalized_name.replace("-", "").replace("_", "").replace(".", "").isalnum():
            errors.append(
                "Software name must contain only alphanumeric characters, hyphens, underscores, and dots"
            )

        # Check length constraints
        if len(normalized_name) > 100:
            errors.append("Software name cannot exceed 100 characters")

        if len(normalized_name) < 1:
            errors.append("Software name must be at least 1 character")

        return errors
