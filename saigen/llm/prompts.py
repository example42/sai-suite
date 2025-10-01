"""Prompt templates for saidata generation."""

from typing import Dict, List, Optional, Any
from string import Template
from dataclasses import dataclass
import json
from pathlib import Path

from ..models.generation import GenerationContext
from ..models.repository import RepositoryPackage
from ..models.saidata import SaiData


def load_saidata_schema() -> str:
    """Load the saidata JSON schema for inclusion in prompts.
    
    Returns:
        JSON schema as formatted string, or fallback text if schema not found
    """
    try:
        # Try to find the 0.3 schema file relative to this module
        current_dir = Path(__file__).parent
        schema_path = current_dir.parent.parent / "schemas" / "saidata-0.3-schema.json"
        
        if schema_path.exists():
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            
            # Format the schema for better readability in prompts
            return json.dumps(schema_data, indent=2)
        else:
            return "Schema file not found - using basic requirements"
    except Exception:
        return "Schema loading failed - using basic requirements"
from pathlib import Path


@dataclass
class PromptSection:
    """A section of a prompt template."""
    name: str
    template: str
    required: bool = True
    condition: Optional[str] = None


class PromptTemplate:
    """Template for generating LLM prompts."""
    
    def __init__(self, name: str, sections: List[PromptSection]):
        """Initialize prompt template.
        
        Args:
            name: Template name
            sections: List of prompt sections
        """
        self.name = name
        self.sections = sections
    
    def render(self, context: GenerationContext) -> str:
        """Render prompt with context data.
        
        Args:
            context: Generation context
            
        Returns:
            Rendered prompt string
        """
        rendered_sections = []
        
        for section in self.sections:
            if self._should_include_section(section, context):
                rendered_content = self._render_section(section, context)
                if rendered_content.strip():
                    rendered_sections.append(rendered_content)
        
        return "\n\n".join(rendered_sections)
    
    def _should_include_section(self, section: PromptSection, context: GenerationContext) -> bool:
        """Check if section should be included based on conditions.
        
        Args:
            section: Prompt section
            context: Generation context
            
        Returns:
            True if section should be included
        """
        if not section.condition:
            return True
        
        # Simple condition evaluation
        if section.condition == "has_repository_data":
            return bool(context.repository_data)
        elif section.condition == "has_similar_saidata":
            return bool(context.similar_saidata)
        elif section.condition == "has_sample_saidata":
            return bool(getattr(context, 'sample_saidata', []))
        elif section.condition == "has_user_hints":
            return bool(context.user_hints)
        elif section.condition == "has_existing_saidata":
            return bool(context.existing_saidata)
        elif section.condition == "has_validation_feedback":
            return bool(context.user_hints and context.user_hints.get("validation_feedback"))
        elif section.condition == "include_json_schema":
            return True  # Always include when requested
        
        return True
    
    def _render_section(self, section: PromptSection, context: GenerationContext) -> str:
        """Render a single section.
        
        Args:
            section: Prompt section to render
            context: Generation context
            
        Returns:
            Rendered section content
        """
        template_vars = self._build_template_variables(context)
        
        try:
            # Cache compiled templates for better performance
            if not hasattr(section, '_compiled_template'):
                section._compiled_template = Template(section.template)
            return section._compiled_template.safe_substitute(template_vars)
        except Exception as e:
            if section.required:
                raise ValueError(f"Failed to render required section '{section.name}': {e}")
            return ""
    
    def _build_template_variables(self, context: GenerationContext) -> Dict[str, str]:
        """Build template variables from context.
        
        Args:
            context: Generation context
            
        Returns:
            Dictionary of template variables
        """
        # Combine similar saidata and sample saidata for examples
        all_saidata_examples = context.similar_saidata.copy()
        if hasattr(context, 'sample_saidata') and context.sample_saidata:
            all_saidata_examples.extend(context.sample_saidata)
        
        variables = {
            "software_name": context.software_name,
            "target_providers": ", ".join(context.target_providers) if context.target_providers else "apt, brew, winget",
            "repository_context": self._format_repository_data(context.repository_data),
            "similar_saidata_examples": self._format_similar_saidata(all_saidata_examples),
            "sample_saidata_examples": self._format_sample_saidata(getattr(context, 'sample_saidata', [])),
            "user_hints": self._format_user_hints(context.user_hints),
            "existing_saidata": self._format_existing_saidata(context.existing_saidata),
            "validation_feedback": self._format_validation_feedback(context.user_hints),
            "json_schema": self._format_json_schema(context),
        }
        
        return variables
    
    def _format_repository_data(self, packages: List[RepositoryPackage]) -> str:
        """Format repository data for prompt inclusion.
        
        Args:
            packages: List of repository packages
            
        Returns:
            Formatted repository data string
        """
        if not packages:
            return "No repository data available."
        
        # Group packages by repository for better organization
        from collections import defaultdict
        repo_groups = defaultdict(list)
        for pkg in packages:
            repo_groups[pkg.repository_name].append(pkg)
        
        formatted_sections = []
        total_shown = 0
        max_packages = 8  # Show more packages for better context
        
        for repo_name, repo_packages in repo_groups.items():
            if total_shown >= max_packages:
                break
                
            section_packages = []
            for pkg in repo_packages[:3]:  # Max 3 per repository
                if total_shown >= max_packages:
                    break
                    
                pkg_info = f"  - {pkg.name}"
                if pkg.version:
                    pkg_info += f" (v{pkg.version})"
                if pkg.description:
                    pkg_info += f": {pkg.description[:80]}..."
                if pkg.homepage:
                    pkg_info += f" [Homepage: {pkg.homepage}]"
                    
                section_packages.append(pkg_info)
                total_shown += 1
            
            if section_packages:
                formatted_sections.append(f"{repo_name} repository:")
                formatted_sections.extend(section_packages)
        
        result = "Repository packages found:\n" + "\n".join(formatted_sections)
        
        total_packages = len(packages)
        if total_shown < total_packages:
            result += f"\n... and {total_packages - total_shown} more packages across {len(repo_groups)} repositories"
        
        return result
    
    def _format_similar_saidata(self, similar_saidata: List[SaiData]) -> str:
        """Format similar saidata for prompt inclusion.
        
        Args:
            similar_saidata: List of similar saidata files
            
        Returns:
            Formatted similar saidata string
        """
        if not similar_saidata:
            return "No similar saidata examples available."
        
        examples = []
        for i, saidata in enumerate(similar_saidata[:3], 1):  # Limit to 3 examples
            example_parts = [f"Example {i}: {saidata.metadata.name}"]
            
            if saidata.metadata.description:
                example_parts.append(f"  Description: {saidata.metadata.description[:100]}...")
            
            if saidata.metadata.category:
                example_parts.append(f"  Category: {saidata.metadata.category}")
            
            if saidata.providers:
                providers = list(saidata.providers.keys())
                example_parts.append(f"  Providers: {', '.join(providers)}")
                
                # Show sample package names from providers
                sample_packages = []
                for provider_name, provider_config in list(saidata.providers.items())[:2]:
                    if provider_config.packages:
                        pkg_names = [pkg.name for pkg in provider_config.packages[:2]]
                        if pkg_names:
                            sample_packages.append(f"{provider_name}: {', '.join(pkg_names)}")
                
                if sample_packages:
                    example_parts.append(f"  Sample packages: {'; '.join(sample_packages)}")
            
            examples.append("\n".join(example_parts))
        
        return "Similar software examples:\n\n" + "\n\n".join(examples)
    
    def _format_sample_saidata(self, sample_saidata: List[SaiData]) -> str:
        """Format sample saidata for prompt inclusion.
        
        Args:
            sample_saidata: List of sample saidata files
            
        Returns:
            Formatted sample saidata string
        """
        if not sample_saidata:
            return "No sample saidata available."
        
        examples = []
        for i, saidata in enumerate(sample_saidata[:3], 1):  # Limit to 3 examples
            example_parts = [f"Sample {i}: {saidata.metadata.name}"]
            
            if saidata.metadata.description:
                example_parts.append(f"  Description: {saidata.metadata.description}")
            
            if saidata.metadata.category:
                example_parts.append(f"  Category: {saidata.metadata.category}")
            
            if saidata.providers:
                providers = list(saidata.providers.keys())
                example_parts.append(f"  Providers: {', '.join(providers)}")
                
                # Show complete structure for one provider as example
                first_provider = list(saidata.providers.items())[0]
                provider_name, provider_config = first_provider
                
                config_details = []
                if provider_config.packages:
                    pkg_details = []
                    for pkg in provider_config.packages[:2]:
                        pkg_str = f"name: {pkg.name}"
                        if pkg.version:
                            pkg_str += f", version: {pkg.version}"
                        pkg_details.append(pkg_str)
                    config_details.append(f"packages: [{'; '.join(pkg_details)}]")
                
                if provider_config.services:
                    svc_details = []
                    for svc in provider_config.services[:2]:
                        svc_str = f"name: {svc.name}"
                        if hasattr(svc, 'enabled') and svc.enabled is not None:
                            svc_str += f", enabled: {svc.enabled}"
                        svc_details.append(svc_str)
                    config_details.append(f"services: [{'; '.join(svc_details)}]")
                
                if config_details:
                    example_parts.append(f"  {provider_name} config: {', '.join(config_details)}")
            
            examples.append("\n".join(example_parts))
        
        return "Reference saidata samples:\n\n" + "\n\n".join(examples)
    
    def _format_user_hints(self, user_hints: Optional[Dict[str, Any]]) -> str:
        """Format user hints for prompt inclusion.
        
        Args:
            user_hints: User-provided hints
            
        Returns:
            Formatted user hints string
        """
        if not user_hints:
            return "No user hints provided."
        
        formatted_hints = []
        for key, value in user_hints.items():
            formatted_hints.append(f"- {key}: {value}")
        
        return "User hints:\n" + "\n".join(formatted_hints)
    
    def _format_existing_saidata(self, existing_saidata: Optional[SaiData]) -> str:
        """Format existing saidata for update mode.
        
        Args:
            existing_saidata: Existing saidata to update
            
        Returns:
            Formatted existing saidata string
        """
        if not existing_saidata:
            return "No existing saidata provided."
        
        info = f"Existing saidata for {existing_saidata.metadata.name}"
        if existing_saidata.metadata.version:
            info += f" v{existing_saidata.metadata.version}"
        if existing_saidata.providers:
            providers = list(existing_saidata.providers.keys())
            info += f" (Current providers: {', '.join(providers)})"
        
        return info
    
    def _format_validation_feedback(self, user_hints: Optional[Dict[str, Any]]) -> str:
        """Format validation feedback for retry prompts.
        
        Args:
            user_hints: User hints that may contain validation feedback
            
        Returns:
            Formatted validation feedback string
        """
        if not user_hints or "validation_feedback" not in user_hints:
            return "No validation feedback available."
        
        feedback = user_hints["validation_feedback"]
        
        formatted_parts = []
        
        # Add main validation error
        if "validation_error" in feedback:
            formatted_parts.append(f"VALIDATION ERROR: {feedback['validation_error']}")
        
        # Add specific errors
        if "specific_errors" in feedback and feedback["specific_errors"]:
            formatted_parts.append("SPECIFIC ERRORS:")
            for i, error in enumerate(feedback["specific_errors"], 1):
                formatted_parts.append(f"  {i}. {error}")
        
        # Add failed YAML excerpt
        if "failed_yaml_excerpt" in feedback:
            formatted_parts.append("FAILED YAML EXCERPT:")
            formatted_parts.append(f"```yaml\n{feedback['failed_yaml_excerpt']}\n```")
        
        # Add retry instructions
        if "retry_instructions" in feedback and feedback["retry_instructions"]:
            formatted_parts.append("RETRY INSTRUCTIONS:")
            for instruction in feedback["retry_instructions"]:
                formatted_parts.append(f"- {instruction}")
        
        return "\n\n".join(formatted_parts)
    
    def _format_json_schema(self, context: GenerationContext) -> str:
        """Format JSON schema for prompt inclusion.
        
        Args:
            context: Generation context (unused but kept for consistency)
            
        Returns:
            Formatted JSON schema string
        """
        schema_content = load_saidata_schema()
        
        if "Schema file not found" in schema_content or "Schema loading failed" in schema_content:
            return schema_content
        
        return f"COMPLETE JSON SCHEMA:\n```json\n{schema_content}\n```\n\nThis is the exact schema your YAML output must validate against."


# Predefined prompt templates
SAIDATA_GENERATION_TEMPLATE = PromptTemplate(
    name="saidata_generation",
    sections=[
        PromptSection(
            name="system_instruction",
            template="""You are an expert system administrator and software metadata specialist. Your task is to generate a comprehensive saidata YAML file for software packages. The saidata format is used by the SAI (Software Action Interface) tool for cross-platform software management.

CRITICAL REQUIREMENTS:
1. Generate ONLY valid YAML content that follows the saidata schema
2. Use accurate package names from repository data when available
3. Include comprehensive metadata and provider configurations
4. Ensure cross-platform compatibility where possible
5. Follow semantic versioning for the saidata version field
6. Include security considerations and best practices""",
            required=True
        ),
        PromptSection(
            name="software_specification",
            template="""SOFTWARE TO GENERATE SAIDATA FOR: $software_name

TARGET PROVIDERS: $target_providers

Generate saidata that supports the specified providers with accurate package names, installation commands, and configuration details.""",
            required=True
        ),
        PromptSection(
            name="repository_context",
            template="""REPOSITORY DATA CONTEXT:
$repository_context

IMPORTANT: Use this repository information to ensure accurate package names, versions, and availability across different platforms. The package names shown here are verified to exist in the respective repositories.""",
            condition="has_repository_data"
        ),
        PromptSection(
            name="similar_examples",
            template="""SIMILAR SOFTWARE EXAMPLES:
$similar_saidata_examples

Use these examples as reference for structure, provider configurations, and best practices. Pay attention to how similar software is configured across different providers, but ensure the generated saidata is specific to the requested software.""",
            condition="has_similar_saidata"
        ),
        PromptSection(
            name="sample_examples",
            template="""REFERENCE SAIDATA SAMPLES:
$sample_saidata_examples

These are high-quality reference examples showing proper saidata structure, formatting, and best practices. Use these as templates for structure and formatting, adapting the content for the specific software being generated.""",
            condition="has_sample_saidata"
        ),
        PromptSection(
            name="user_guidance",
            template="""USER HINTS AND PREFERENCES:
$user_hints

Incorporate these user preferences and hints into the generated saidata.""",
            condition="has_user_hints"
        ),
        PromptSection(
            name="schema_requirements",
            template="""SAIDATA SCHEMA REQUIREMENTS (VERSION 0.3):

The saidata YAML must follow this exact JSON schema structure for version 0.3:

**Root Level (Required):**
- version: string (must be "0.3")
- metadata: object (required)
- packages: array of package objects (optional)
- services: array of service objects (optional)
- files: array of file objects (optional)
- directories: array of directory objects (optional)
- commands: array of command objects (optional)
- ports: array of port objects (optional)
- containers: array of container objects (optional)
- sources: array of source build objects (NEW in 0.3)
- binaries: array of binary download objects (NEW in 0.3)
- scripts: array of script installation objects (NEW in 0.3)
- providers: object (provider configurations)
- compatibility: object (compatibility matrix)

**Enhanced Metadata Object (Required):**
- name: string (required)
- display_name: string (optional)
- description: string (optional but recommended)
- version: string (optional)
- category: string (optional but recommended)
- subcategory: string (optional)
- tags: array of strings (optional)
- license: string (optional)
- language: string (optional)
- maintainer: string (optional)
- urls: object with website, documentation, source, issues, support, download, changelog, license, sbom, icon (optional)
- security: object with cve_exceptions, security_contact, vulnerability_disclosure, sbom_url, signing_key (NEW in 0.3)

**NEW: Source Build Objects:**
- name: string (required) - logical name like "main", "stable"
- url: string (required) - supports {{version}}, {{platform}}, {{architecture}} templating
- build_system: string (required) - autotools, cmake, make, meson, ninja, custom
- version: string (optional)
- configure_args: array of strings (optional)
- build_args: array of strings (optional)
- install_args: array of strings (optional)
- prerequisites: array of strings (optional)
- environment: object (optional)
- checksum: string (optional) - format "algorithm:hash"
- custom_commands: object (optional)

**NEW: Binary Download Objects:**
- name: string (required) - logical name like "main", "stable"
- url: string (required) - supports {{version}}, {{platform}}, {{architecture}} templating
- version: string (optional)
- architecture: string (optional) - amd64, arm64, 386
- platform: string (optional) - linux, darwin, windows
- checksum: string (optional) - format "algorithm:hash"
- install_path: string (optional) - defaults to /usr/local/bin
- executable: string (optional)
- archive: object (optional) - format, strip_prefix, extract_path
- permissions: string (optional) - octal format like "0755"
- custom_commands: object (optional)

**NEW: Script Installation Objects:**
- name: string (required) - logical name like "official", "convenience"
- url: string (required) - should use HTTPS for security
- version: string (optional)
- interpreter: string (optional) - bash, sh, python, python3
- checksum: string (required for security) - format "algorithm:hash"
- arguments: array of strings (optional)
- environment: object (optional)
- working_dir: string (optional)
- timeout: integer (optional) - 1-3600 seconds
- custom_commands: object (optional)

**Enhanced Package Object:**
- name: string (required) - logical name
- package_name: string (required) - actual package name
- version: string (optional)
- alternatives: array of strings (optional)
- install_options: string (optional)
- repository: string (optional)
- checksum: string (optional)
- signature: string (optional)
- download_url: string (optional)

**Enhanced Provider Configuration:**
Each provider can now contain all resource types including:
- prerequisites: array of strings (for source builds)
- build_commands: array of strings (for source builds)
- package_sources: array of package source objects
- repositories: array of repository objects
- sources: array of source objects (provider-specific overrides)
- binaries: array of binary objects (provider-specific overrides)
- scripts: array of script objects (provider-specific overrides)

**CRITICAL DATA TYPE REQUIREMENTS:**
- version must be "0.3" (string)
- All resource arrays (packages, services, sources, binaries, scripts, etc.) must be ARRAYS of OBJECTS
- checksum must follow format "algorithm:hash" (e.g., "sha256:abc123...")
- timeout must be integer between 1 and 3600
- permissions must be octal string (e.g., "0755")
- port numbers must be INTEGERS
- enabled must be BOOLEAN (true/false)

**EXAMPLE 0.3 STRUCTURE:**
```yaml
version: "0.3"
metadata:
  name: "example-software"
  description: "Example software description"
  category: "web-server"
  urls:
    website: "https://example.com"
    documentation: "https://docs.example.com"
  security:
    security_contact: "security@example.com"
sources:
  - name: "main"
    url: "https://example.com/software-{{version}}.tar.gz"
    build_system: "autotools"
    configure_args: ["--enable-ssl", "--with-modules"]
    prerequisites: ["build-essential", "libssl-dev"]
    checksum: "sha256:abc123..."
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/software_{{version}}_{{platform}}_{{architecture}}.zip"
    install_path: "/usr/local/bin"
    checksum: "sha256:def456..."
scripts:
  - name: "official"
    url: "https://get.example.com/install.sh"
    interpreter: "bash"
    checksum: "sha256:ghi789..."
    timeout: 600
providers:
  apt:
    packages:
      - name: "main"
        package_name: "example-software"
```

Generate complete, valid YAML following this 0.3 structure exactly.""",
            required=True
        ),
        PromptSection(
            name="output_instruction",
            template="""OUTPUT INSTRUCTIONS:
1. Generate ONLY the YAML content - no explanations or markdown formatting
2. Start directly with the YAML (version: "0.3")
3. Ensure all YAML syntax is correct and properly indented
4. Include comprehensive provider configurations with 0.3 features
5. Use accurate package names from repository data
6. Include relevant metadata, services, and configuration details
7. Include sources, binaries, and/or scripts sections when appropriate
8. Include enhanced metadata with security information when relevant
9. Ensure the output is production-ready and follows 0.3 schema best practices

Generate the saidata YAML now:""",
            required=True
        )
    ]
)

UPDATE_SAIDATA_TEMPLATE = PromptTemplate(
    name="saidata_update",
    sections=[
        PromptSection(
            name="system_instruction",
            template="""You are updating an existing saidata file. Your task is to enhance and improve the existing configuration while preserving user customizations and ensuring compatibility.

CRITICAL REQUIREMENTS:
1. Preserve existing user customizations and manual additions
2. Update package versions and repository information
3. Add missing providers or configurations
4. Improve metadata and descriptions
5. Maintain backward compatibility
6. Generate ONLY valid YAML content""",
            required=True
        ),
        PromptSection(
            name="existing_saidata_context",
            template="""EXISTING SAIDATA TO UPDATE:
$existing_saidata

Enhance this existing configuration with new information while preserving customizations.""",
            condition="has_existing_saidata",
            required=True
        ),
        PromptSection(
            name="repository_updates",
            template="""UPDATED REPOSITORY DATA:
$repository_context

Use this updated repository information to refresh package names, versions, and availability.""",
            condition="has_repository_data"
        ),
        PromptSection(
            name="enhancement_guidance",
            template="""ENHANCEMENT GUIDANCE:
$user_hints

Apply these enhancement requests to the existing saidata.""",
            condition="has_user_hints"
        ),
        PromptSection(
            name="output_instruction",
            template="""OUTPUT INSTRUCTIONS:
1. Generate the complete updated YAML content
2. Preserve all existing customizations and user additions
3. Update outdated information with current data
4. Add missing provider configurations where appropriate
5. Improve metadata and descriptions
6. Ensure all YAML syntax is correct

Generate the updated saidata YAML now:""",
            required=True
        )
    ]
)

RETRY_SAIDATA_TEMPLATE = PromptTemplate(
    name="saidata_retry",
    sections=[
        PromptSection(
            name="system_instruction",
            template="""You are an expert system administrator and software metadata specialist. Your previous attempt to generate saidata YAML failed validation. You must now fix the validation errors and generate a corrected version.

CRITICAL REQUIREMENTS:
1. Generate ONLY valid YAML content that follows the saidata schema exactly
2. Fix all validation errors from the previous attempt
3. Use accurate package names from repository data when available
4. Ensure all required fields are present and properly formatted
5. Follow semantic versioning for the saidata version field
6. Pay special attention to data types and field requirements""",
            required=True
        ),
        PromptSection(
            name="validation_feedback",
            template="""VALIDATION ERRORS FROM PREVIOUS ATTEMPT:
$validation_feedback

CRITICAL: You must fix ALL of these validation errors in your corrected output. Pay close attention to:
- Required fields that may be missing
- Incorrect data types (strings vs numbers vs booleans vs arrays)
- Invalid field names or structure
- YAML syntax errors
- Schema compliance issues""",
            condition="has_validation_feedback",
            required=True
        ),
        PromptSection(
            name="software_specification",
            template="""SOFTWARE TO GENERATE SAIDATA FOR: $software_name

TARGET PROVIDERS: $target_providers

Generate corrected saidata that supports the specified providers with accurate package names, installation commands, and configuration details.""",
            required=True
        ),
        PromptSection(
            name="repository_context",
            template="""REPOSITORY DATA CONTEXT:
$repository_context

IMPORTANT: Use this repository information to ensure accurate package names, versions, and availability across different platforms. The package names shown here are verified to exist in the respective repositories.""",
            condition="has_repository_data"
        ),
        PromptSection(
            name="similar_examples",
            template="""SIMILAR SOFTWARE EXAMPLES:
$similar_saidata_examples

Use these examples as reference for structure, provider configurations, and best practices. Pay attention to how similar software is configured across different providers, but ensure the generated saidata is specific to the requested software.""",
            condition="has_similar_saidata"
        ),
        PromptSection(
            name="sample_examples",
            template="""REFERENCE SAIDATA SAMPLES:
$sample_saidata_examples

These are high-quality reference examples showing proper saidata structure, formatting, and best practices. Use these as templates for structure and formatting, adapting the content for the specific software being generated.""",
            condition="has_sample_saidata"
        ),
        PromptSection(
            name="json_schema_reference",
            template="""JSON SCHEMA REFERENCE:
$json_schema

This is the complete JSON schema that your YAML output must validate against. Pay special attention to data types and required fields.""",
            condition="include_json_schema"
        ),
        PromptSection(
            name="schema_requirements",
            template="""SAIDATA SCHEMA REQUIREMENTS (VERSION 0.3):

The saidata YAML must follow this exact JSON schema structure for version 0.3:

**Root Level (Required):**
- version: string (must be "0.3")
- metadata: object (required)
- packages: array of package objects (optional)
- services: array of service objects (optional)
- files: array of file objects (optional)
- directories: array of directory objects (optional)
- commands: array of command objects (optional)
- ports: array of port objects (optional)
- containers: array of container objects (optional)
- sources: array of source build objects (NEW in 0.3)
- binaries: array of binary download objects (NEW in 0.3)
- scripts: array of script installation objects (NEW in 0.3)
- providers: object (provider configurations)
- compatibility: object (compatibility matrix)

**Enhanced Metadata Object (Required):**
- name: string (required)
- display_name: string (optional)
- description: string (optional but recommended)
- version: string (optional)
- category: string (optional but recommended)
- subcategory: string (optional)
- tags: array of strings (optional)
- license: string (optional)
- language: string (optional)
- maintainer: string (optional)
- urls: object with website, documentation, source, issues, support, download, changelog, license, sbom, icon (optional)
- security: object with cve_exceptions, security_contact, vulnerability_disclosure, sbom_url, signing_key (NEW in 0.3)

**NEW: Source Build Objects:**
- name: string (required) - logical name like "main", "stable"
- url: string (required) - supports {{version}}, {{platform}}, {{architecture}} templating
- build_system: string (required) - autotools, cmake, make, meson, ninja, custom
- version: string (optional)
- configure_args: array of strings (optional)
- build_args: array of strings (optional)
- install_args: array of strings (optional)
- prerequisites: array of strings (optional)
- environment: object (optional)
- checksum: string (optional) - format "algorithm:hash"
- custom_commands: object (optional)

**NEW: Binary Download Objects:**
- name: string (required) - logical name like "main", "stable"
- url: string (required) - supports {{version}}, {{platform}}, {{architecture}} templating
- version: string (optional)
- architecture: string (optional) - amd64, arm64, 386
- platform: string (optional) - linux, darwin, windows
- checksum: string (optional) - format "algorithm:hash"
- install_path: string (optional) - defaults to /usr/local/bin
- executable: string (optional)
- archive: object (optional) - format, strip_prefix, extract_path
- permissions: string (optional) - octal format like "0755"
- custom_commands: object (optional)

**NEW: Script Installation Objects:**
- name: string (required) - logical name like "official", "convenience"
- url: string (required) - should use HTTPS for security
- version: string (optional)
- interpreter: string (optional) - bash, sh, python, python3
- checksum: string (required for security) - format "algorithm:hash"
- arguments: array of strings (optional)
- environment: object (optional)
- working_dir: string (optional)
- timeout: integer (optional) - 1-3600 seconds
- custom_commands: object (optional)

**Enhanced Package Object:**
- name: string (required) - logical name
- package_name: string (required) - actual package name
- version: string (optional)
- alternatives: array of strings (optional)
- install_options: string (optional)
- repository: string (optional)
- checksum: string (optional)
- signature: string (optional)
- download_url: string (optional)

**Enhanced Provider Configuration:**
Each provider can now contain all resource types including:
- prerequisites: array of strings (for source builds)
- build_commands: array of strings (for source builds)
- package_sources: array of package source objects
- repositories: array of repository objects
- sources: array of source objects (provider-specific overrides)
- binaries: array of binary objects (provider-specific overrides)
- scripts: array of script objects (provider-specific overrides)

**CRITICAL DATA TYPE REQUIREMENTS:**
- version must be "0.3" (string, not "0.2")
- All resource arrays (packages, services, sources, binaries, scripts, etc.) must be ARRAYS of OBJECTS
- checksum must follow format "algorithm:hash" (e.g., "sha256:abc123...")
- timeout must be integer between 1 and 3600
- permissions must be octal string (e.g., "0755")
- port numbers must be INTEGERS
- enabled must be BOOLEAN (true/false)
- DO NOT use shorthand syntax - use full object syntax

**CORRECT 0.3 EXAMPLE:**
```yaml
version: "0.3"
metadata:
  name: "example-software"
  description: "Example software description"
  category: "web-server"
  urls:
    website: "https://example.com"
  security:
    security_contact: "security@example.com"
sources:
  - name: "main"
    url: "https://example.com/software-{{version}}.tar.gz"
    build_system: "autotools"
    checksum: "sha256:abc123..."
binaries:
  - name: "main"
    url: "https://releases.example.com/{{version}}/software_{{version}}_{{platform}}_{{architecture}}.zip"
    install_path: "/usr/local/bin"
    checksum: "sha256:def456..."
scripts:
  - name: "official"
    url: "https://get.example.com/install.sh"
    interpreter: "bash"
    checksum: "sha256:ghi789..."
providers:
  apt:
    packages:
      - name: "main"
        package_name: "example-software"
```

**INCORRECT EXAMPLES TO AVOID:**
```yaml
# WRONG - version 0.2 instead of 0.3
version: "0.2"  # WRONG - must be "0.3"

# WRONG - missing package_name in package objects
providers:
  apt:
    packages:
      - name: "software"  # WRONG - missing package_name field

# WRONG - missing required fields in new sections
sources:
  - url: "https://example.com/source.tar.gz"  # WRONG - missing name and build_system

# WRONG - invalid checksum format
sources:
  - name: "main"
    checksum: "abc123"  # WRONG - should be "sha256:abc123..."
```

Generate complete, valid YAML following this 0.3 structure exactly and fixing all validation errors.""",
            required=True
        ),
        PromptSection(
            name="output_instruction",
            template="""OUTPUT INSTRUCTIONS:
1. Generate ONLY the corrected YAML content - no explanations or markdown formatting
2. Start directly with the YAML (version: "0.3")
3. Fix ALL validation errors from the previous attempt
4. Ensure all YAML syntax is correct and properly indented
5. Include all required fields with correct data types for 0.3 schema
6. Use accurate package names from repository data
7. Include sources, binaries, and/or scripts sections when appropriate
8. Ensure the output passes 0.3 schema validation

Generate the corrected saidata YAML now:""",
            required=True
        )
    ]
)


class PromptManager:
    """Manager for prompt templates."""
    
    def __init__(self):
        """Initialize prompt manager with default templates."""
        self.templates = {
            "generation": SAIDATA_GENERATION_TEMPLATE,
            "update": UPDATE_SAIDATA_TEMPLATE,
            "retry": RETRY_SAIDATA_TEMPLATE,
        }
    
    def get_template(self, template_name: str) -> PromptTemplate:
        """Get a prompt template by name.
        
        Args:
            template_name: Name of the template
            
        Returns:
            PromptTemplate instance
            
        Raises:
            KeyError: If template not found
        """
        if template_name not in self.templates:
            raise KeyError(f"Template '{template_name}' not found. Available: {list(self.templates.keys())}")
        
        return self.templates[template_name]
    
    def register_template(self, name: str, template: PromptTemplate) -> None:
        """Register a new prompt template.
        
        Args:
            name: Template name
            template: PromptTemplate instance
        """
        self.templates[name] = template
    
    def list_templates(self) -> List[str]:
        """List available template names.
        
        Returns:
            List of template names
        """
        return list(self.templates.keys())