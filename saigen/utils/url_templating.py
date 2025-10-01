"""URL templating system for saidata 0.3 schema.

This module provides URL template validation and rendering capabilities
for sources, binaries, and scripts sections in saidata files.
"""

import re
import platform
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class TemplateValidationError(Exception):
    """Raised when URL template validation fails."""
    pass


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
    def auto_detect(cls) -> 'TemplateContext':
        """Auto-detect platform and architecture from current system."""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Normalize platform names
        platform_map = {
            'linux': 'linux',
            'darwin': 'darwin',
            'windows': 'windows'
        }
        
        # Normalize architecture names
        arch_map = {
            'x86_64': 'amd64',
            'amd64': 'amd64',
            'arm64': 'arm64',
            'aarch64': 'arm64',
            'i386': '386',
            'i686': '386'
        }
        
        detected_platform = platform_map.get(system, system)
        detected_arch = arch_map.get(machine, machine)
        
        return cls(
            platform=detected_platform,
            architecture=detected_arch
        )


class URLTemplateProcessor:
    """Handles URL templating with placeholders for saidata 0.3 schema."""
    
    # Supported placeholders and their descriptions
    SUPPORTED_PLACEHOLDERS = {
        'version': 'Software version',
        'platform': 'Target platform (linux, darwin, windows)',
        'architecture': 'Target architecture (amd64, arm64, 386)'
    }
    
    # Regular expression for finding placeholders
    PLACEHOLDER_PATTERN = re.compile(r'\{\{(\w+)\}\}')
    
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
        malformed_matches = re.findall(r'\{[^}]*\}(?!\})', url_template)
        for match in malformed_matches:
            if not match.startswith('{{') or not match.endswith('}}'):
                errors.append(f"Malformed placeholder: {match}")
        
        # Check for unbalanced braces
        open_braces = url_template.count('{')
        close_braces = url_template.count('}')
        if open_braces != close_braces:
            errors.append("Unbalanced braces in URL template")
        
        # Validate URL structure (basic check)
        if not self._is_valid_url_structure(url_template):
            errors.append("Invalid URL structure")
        
        # Warnings for common issues
        if '{{version}}' not in url_template:
            warnings.append("Template does not include version placeholder - consider adding {{version}}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def render_template(self, url_template: str, context: TemplateContext) -> str:
        """Render URL template with provided context.
        
        Args:
            url_template: The URL template string to render
            context: Template context with placeholder values
            
        Returns:
            Rendered URL string
            
        Raises:
            TemplateValidationError: If template validation fails
            ValueError: If required placeholders are missing from context
        """
        # Validate template first
        validation_result = self.validate_template(url_template)
        if not validation_result.is_valid:
            raise TemplateValidationError(f"Invalid template: {', '.join(validation_result.errors)}")
        
        # Extract placeholders
        placeholders = self.extract_placeholders(url_template)
        
        # Build substitution dictionary
        substitutions = {}
        context_dict = {
            'version': context.version,
            'platform': context.platform,
            'architecture': context.architecture
        }
        
        # Check for missing required values
        missing_values = []
        for placeholder in placeholders:
            value = context_dict.get(placeholder)
            if value is None:
                missing_values.append(placeholder)
            else:
                substitutions[placeholder] = value
        
        if missing_values:
            raise ValueError(f"Missing values for placeholders: {', '.join(missing_values)}")
        
        # Perform substitution
        rendered_url = url_template
        for placeholder, value in substitutions.items():
            rendered_url = rendered_url.replace(f'{{{{{placeholder}}}}}', value)
        
        return rendered_url
    
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
        temp_url = self.PLACEHOLDER_PATTERN.sub('placeholder', url_template)
        
        # Basic URL pattern check
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(temp_url))
    
    def get_supported_placeholders(self) -> Dict[str, str]:
        """Get dictionary of supported placeholders and their descriptions.
        
        Returns:
            Dictionary mapping placeholder names to descriptions
        """
        return self.SUPPORTED_PLACEHOLDERS.copy()