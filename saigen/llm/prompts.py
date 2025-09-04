"""Prompt templates for saidata generation."""

from typing import Dict, List, Optional, Any
from string import Template
from dataclasses import dataclass

from ..models.generation import GenerationContext
from ..models.repository import RepositoryPackage
from ..models.saidata import SaiData


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
        elif section.condition == "has_user_hints":
            return bool(context.user_hints)
        elif section.condition == "has_existing_saidata":
            return bool(context.existing_saidata)
        
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
        variables = {
            "software_name": context.software_name,
            "target_providers": ", ".join(context.target_providers) if context.target_providers else "apt, brew, winget",
            "repository_context": self._format_repository_data(context.repository_data),
            "similar_saidata_examples": self._format_similar_saidata(context.similar_saidata),
            "user_hints": self._format_user_hints(context.user_hints),
            "existing_saidata": self._format_existing_saidata(context.existing_saidata),
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
            name="user_guidance",
            template="""USER HINTS AND PREFERENCES:
$user_hints

Incorporate these user preferences and hints into the generated saidata.""",
            condition="has_user_hints"
        ),
        PromptSection(
            name="schema_requirements",
            template="""SAIDATA SCHEMA REQUIREMENTS:
- version: Must be semantic version (e.g., "0.2")
- metadata: Required section with name, description, category, etc.
- providers: Dictionary of provider-specific configurations
- packages: List of packages for each provider
- services: Optional service definitions
- files/directories: Optional file system resources
- commands: Optional command definitions
- ports: Optional network port definitions
- compatibility: Optional compatibility matrix

EXAMPLE STRUCTURE:
```yaml
version: "0.2"
metadata:
  name: "software-name"
  display_name: "Software Display Name"
  description: "Brief description of the software"
  category: "category"
  license: "license-type"
  urls:
    website: "https://example.com"
    documentation: "https://docs.example.com"

providers:
  apt:
    packages:
      - name: "package-name"
        version: "latest"
    services:
      - name: "service-name"
        enabled: true
  
  brew:
    packages:
      - name: "package-name"
        
  winget:
    packages:
      - name: "Publisher.PackageName"
```

Generate complete, valid YAML following this structure.""",
            required=True
        ),
        PromptSection(
            name="output_instruction",
            template="""OUTPUT INSTRUCTIONS:
1. Generate ONLY the YAML content - no explanations or markdown formatting
2. Start directly with the YAML (version: "0.2")
3. Ensure all YAML syntax is correct and properly indented
4. Include comprehensive provider configurations
5. Use accurate package names from repository data
6. Include relevant metadata, services, and configuration details
7. Ensure the output is production-ready and follows best practices

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


class PromptManager:
    """Manager for prompt templates."""
    
    def __init__(self):
        """Initialize prompt manager with default templates."""
        self.templates = {
            "generation": SAIDATA_GENERATION_TEMPLATE,
            "update": UPDATE_SAIDATA_TEMPLATE,
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