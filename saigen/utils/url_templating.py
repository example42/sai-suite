"""URL templating system for saidata 0.3 schema.

This module provides URL template validation and rendering capabilities
for sources, binaries, and scripts sections in saidata files.
"""

import platform
import re
from dataclasses import dataclass
from typing import List, Optional


class TemplateValidationError(Exception):
    """Raised when URL template validation fails."""


@dataclass
class ValidationResult:
    """Result of template validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]


@dataclass
class TemplateContext:
    """Context for URL template rendering."""

    version: Optional[str] = None
    platform: Optional[str] = None
    architecture: Optional[str] = None

    @classmethod
    def auto_detect(cls) -> "TemplateContext":
        """Auto-detect platform and architecture from current system."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Normalize platform names
        platform_map = {"linux": "linux", "darwin": "darwin", "windows": "windows"}

        # Normalize architecture names
        arch_map = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "arm64": "arm64",
            "aarch64": "arm64",
            "i386": "386",
            "i686": "386",
        }

        detected_platform = platform_map.get(system, system)
        detected_arch = arch_map.get(machine, machine)

        return cls(platform=detected_platform, architecture=detected_arch)


class URLTemplateProcessor:
    """Handles URL templating with placeholders for saidata 0.3 schema."""

    # Supported placeholders and their descriptions
    SUPPORTED_PLACEHOLDERS = {
        "version": "Software version",
        "platform": "Target platform (linux, darwin, windows)",
        "architecture": "Target architecture (amd64, arm64, 386)",
    }

    # Regular expression for finding placeholders
    PLACEHOLDER_PATTERN = re.compile(r"\{\{(\w+)\}\}")

    def validate_template(self, url_template: str) -> ValidationResult:
        """Validate URL template syntax and placeholders.

        Args:
            url_template: The URL template string to validate

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors = []
        warnings = []

        if not url_template:
            errors.append("URL template cannot be empty")
            return ValidationResult(False, errors, warnings)

        if not isinstance(url_template, str):
            errors.append("URL template must be a string")
            return ValidationResult(False, errors, warnings)

        # Extract placeholders from template
        placeholders = self.extract_placeholders(url_template)

        # Check for unsupported placeholders
        for placeholder in placeholders:
            if placeholder not in self.SUPPORTED_PLACEHOLDERS:
                errors.append(f"Unsupported placeholder: {{{{{placeholder}}}}}")

        # Check for malformed placeholders
        malformed_matches = re.findall(r"\{[^}]*\}(?!\})", url_template)
        for match in malformed_matches:
            if not match.startswith("{{") or not match.endswith("}}"):
                errors.append(f"Malformed placeholder: {match}")

        # Check for unbalanced braces
        open_braces = url_template.count("{")
        close_braces = url_template.count("}")
        if open_braces != close_braces:
            errors.append("Unbalanced braces in URL template")

        # Validate URL structure (basic check)
        if not self._is_valid_url_structure(url_template):
            errors.append("Invalid URL structure")

        # Warnings for common issues
        if "{{version}}" not in url_template:
            warnings.append(
                "Template does not include version placeholder - consider adding {{version}}"
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def extract_placeholders(self, url_template: str) -> List[str]:
        """Extract all placeholders from URL template.

        Args:
            url_template: The URL template string

        Returns:
            List of placeholder names (without braces)
        """
        matches = self.PLACEHOLDER_PATTERN.findall(url_template)
        return list(set(matches))  # Remove duplicates

    def _is_valid_url_structure(self, url_template: str) -> bool:
        """Basic validation of URL structure.

        Args:
            url_template: The URL template to validate

        Returns:
            True if URL structure appears valid
        """
        # Remove placeholders for basic URL validation
        temp_url = self.PLACEHOLDER_PATTERN.sub("placeholder", url_template)

        # Basic URL pattern check
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        return bool(url_pattern.match(temp_url))
