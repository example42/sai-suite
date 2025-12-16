"""Saidata override validation system for detecting unnecessary duplications."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml
import shutil
from datetime import datetime


class OverrideValidator:
    """Validates OS-specific saidata files against default.yaml to detect unnecessary duplications."""

    def compare_saidata_files(
        self, os_specific_file: Path, default_file: Path
    ) -> Dict[str, List[str]]:
        """
        Compare OS-specific saidata with default.yaml to find duplicates.

        Args:
            os_specific_file: Path to OS-specific saidata file (e.g., ubuntu/22.04.yaml)
            default_file: Path to default.yaml file

        Returns:
            Dict with:
            - 'identical_fields': List of field paths that are identical (unnecessary duplicates)
            - 'different_fields': List of field paths that differ (necessary overrides)
            - 'os_only_fields': List of fields only in OS-specific file

        Example:
            {
                'identical_fields': ['providers.apt.packages[0].package_name'],
                'different_fields': ['providers.apt.packages[0].version'],
                'os_only_fields': ['providers.apt.repositories[0]']
            }
        """
        # Load both files
        os_data = self._load_yaml(os_specific_file)
        default_data = self._load_yaml(default_file)

        identical = []
        different = []
        os_only = []

        # Compare recursively
        self._compare_recursive(
            os_data=os_data,
            default_data=default_data,
            path="",
            identical=identical,
            different=different,
            os_only=os_only,
        )

        return {
            "identical_fields": identical,
            "different_fields": different,
            "os_only_fields": os_only,
        }

    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file and return as dictionary."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML structure in {file_path}: expected dictionary")

        return data

    def _compare_recursive(
        self,
        os_data: Any,
        default_data: Any,
        path: str,
        identical: List[str],
        different: List[str],
        os_only: List[str],
    ) -> None:
        """
        Recursively compare two data structures and categorize differences.

        Args:
            os_data: Data from OS-specific file
            default_data: Data from default file
            path: Current path in the data structure (for reporting)
            identical: List to accumulate identical field paths
            different: List to accumulate different field paths
            os_only: List to accumulate OS-only field paths
        """
        # Skip version field - it's metadata, not an override
        if path == "version":
            return

        # Handle dictionaries
        if isinstance(os_data, dict) and isinstance(default_data, dict):
            # Check all keys in OS-specific data
            for key in os_data.keys():
                new_path = f"{path}.{key}" if path else key

                if key not in default_data:
                    # Field only exists in OS-specific file
                    os_only.append(new_path)
                else:
                    # Field exists in both - recurse
                    self._compare_recursive(
                        os_data[key],
                        default_data[key],
                        new_path,
                        identical,
                        different,
                        os_only,
                    )

        # Handle lists
        elif isinstance(os_data, list) and isinstance(default_data, list):
            # For lists, we need to match items by a key (typically 'name')
            # This is important for packages, services, etc.
            self._compare_lists(
                os_data, default_data, path, identical, different, os_only
            )

        # Handle scalar values
        else:
            # Compare values
            if os_data == default_data:
                identical.append(path)
            else:
                different.append(path)

    def _compare_lists(
        self,
        os_list: List[Any],
        default_list: List[Any],
        path: str,
        identical: List[str],
        different: List[str],
        os_only: List[str],
    ) -> None:
        """
        Compare two lists, matching items by 'name' field if available.

        Args:
            os_list: List from OS-specific file
            default_list: List from default file
            path: Current path in the data structure
            identical: List to accumulate identical field paths
            different: List to accumulate different field paths
            os_only: List to accumulate OS-only field paths
        """
        # Try to match items by 'name' field
        if os_list and isinstance(os_list[0], dict) and "name" in os_list[0]:
            # Build index of default items by name
            default_by_name = {}
            for item in default_list:
                if isinstance(item, dict) and "name" in item:
                    default_by_name[item["name"]] = item

            # Compare each OS item with corresponding default item
            for i, os_item in enumerate(os_list):
                if isinstance(os_item, dict) and "name" in os_item:
                    item_name = os_item["name"]
                    item_path = f"{path}[{i}]"

                    if item_name in default_by_name:
                        # Item exists in both - compare recursively
                        self._compare_recursive(
                            os_item,
                            default_by_name[item_name],
                            item_path,
                            identical,
                            different,
                            os_only,
                        )
                    else:
                        # Item only in OS-specific file
                        os_only.append(item_path)
        else:
            # Lists without 'name' field - compare by index
            for i in range(len(os_list)):
                item_path = f"{path}[{i}]"

                if i < len(default_list):
                    # Item exists in both - compare recursively
                    self._compare_recursive(
                        os_list[i],
                        default_list[i],
                        item_path,
                        identical,
                        different,
                        os_only,
                    )
                else:
                    # Item only in OS-specific file
                    os_only.append(item_path)

    def remove_duplicate_fields(
        self,
        os_specific_file: Path,
        identical_fields: List[str],
        backup: bool = True,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Remove fields from OS-specific file that are identical to default.yaml.

        Args:
            os_specific_file: Path to OS-specific saidata file
            identical_fields: List of field paths to remove
            backup: Whether to create a backup before modification

        Returns:
            Tuple of (cleaned_data, removed_fields)
            - cleaned_data: The cleaned data structure
            - removed_fields: List of field paths that were actually removed

        Note:
            This function creates a backup and modifies the file in place.
        """
        # Create backup if requested
        if backup:
            self._create_backup(os_specific_file)

        # Load OS-specific file
        os_data = self._load_yaml(os_specific_file)

        # Remove identical fields
        removed_fields = []
        for field_path in identical_fields:
            if self._remove_field(os_data, field_path):
                removed_fields.append(field_path)

        return os_data, removed_fields

    def _create_backup(self, file_path: Path) -> Path:
        """
        Create a backup of the file with timestamp.

        Args:
            file_path: Path to file to backup

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f".{timestamp}.backup")

        shutil.copy2(file_path, backup_path)

        return backup_path

    def _remove_field(self, data: Dict[str, Any], field_path: str) -> bool:
        """
        Remove a field from the data structure by path.

        Args:
            data: Data structure to modify
            field_path: Dot-separated path to field (e.g., 'providers.apt.packages[0].version')

        Returns:
            True if field was removed, False if not found
        """
        # Parse the path
        parts = self._parse_field_path(field_path)

        if not parts:
            return False

        # Navigate to parent
        current = data
        for part in parts[:-1]:
            if isinstance(part, str):
                # Dictionary key
                if not isinstance(current, dict) or part not in current:
                    return False
                current = current[part]
            elif isinstance(part, int):
                # List index
                if not isinstance(current, list) or part >= len(current):
                    return False
                current = current[part]

        # Remove the final field
        final_part = parts[-1]
        if isinstance(final_part, str):
            # Dictionary key
            if isinstance(current, dict) and final_part in current:
                del current[final_part]
                return True
        elif isinstance(final_part, int):
            # List index
            if isinstance(current, list) and final_part < len(current):
                current.pop(final_part)
                return True

        return False

    def _parse_field_path(self, field_path: str) -> List[Any]:
        """
        Parse a field path into a list of keys and indices.

        Args:
            field_path: Dot-separated path (e.g., 'providers.apt.packages[0].version')

        Returns:
            List of keys (str) and indices (int)

        Example:
            'providers.apt.packages[0].version' -> ['providers', 'apt', 'packages', 0, 'version']
        """
        parts = []
        current = ""

        i = 0
        while i < len(field_path):
            char = field_path[i]

            if char == ".":
                # End of current part
                if current:
                    parts.append(current)
                    current = ""
            elif char == "[":
                # Start of array index
                if current:
                    parts.append(current)
                    current = ""

                # Find closing bracket
                j = i + 1
                while j < len(field_path) and field_path[j] != "]":
                    j += 1

                if j < len(field_path):
                    # Extract index
                    index_str = field_path[i + 1 : j]
                    try:
                        parts.append(int(index_str))
                    except ValueError:
                        # Invalid index - treat as string
                        parts.append(index_str)

                    i = j  # Skip to closing bracket
            else:
                current += char

            i += 1

        # Add final part
        if current:
            parts.append(current)

        return parts

    def save_cleaned_data(self, data: Dict[str, Any], file_path: Path) -> None:
        """
        Save cleaned data to file.

        Args:
            data: Data to save
            file_path: Path to save to
        """
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                sort_keys=False,
                indent=2,
                allow_unicode=True,
            )
