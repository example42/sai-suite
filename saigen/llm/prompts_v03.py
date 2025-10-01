"""Prompt templates for saidata 0.3 generation."""

import logging
from typing import Dict, List, Optional, Any
from string import Template
from dataclasses import dataclass
import json
from pathlib import Path

from ..models.generation import GenerationContext
from ..models.repository import RepositoryPackage
from ..models.saidata import SaiData
from .prompts import PromptSection, PromptTemplate


logger = logging.getLogger(__name__)


def load_saidata_schema_v03() -> str:
    """Load the saidata 0.3 JSON schema for inclusion in prompts.
    
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


class SaiDataV03Prompts:
    """Updated prompts for saidata 0.3 generation"""
    
    BASE_PROMPT = """
Generate a saidata YAML file for the software: {software_name}
Use saidata schema version 0.3 with the following structure:

version: "0.3"
metadata:
  name: {software_name}
  # Include enhanced metadata with security information and URLs
sources:
  # Source build configurations with build systems
binaries:
  # Binary download configurations with templating
scripts:
  # Script installation configurations with security
providers:
  # Provider-specific configurations and overrides
compatibility:
  # Compatibility matrix and version information
"""

    SOURCES_PROMPT = """
Generate source build configurations for {software_name}:

Include:
- URL with templating: {{{{version}}}}, {{{{platform}}}}, {{{{architecture}}}}
- build_system: autotools, cmake, make, meson, ninja, or custom
- configure_args, build_args, install_args arrays
- prerequisites for build dependencies
- checksum in format "algorithm:hash"
- custom_commands for overriding default behavior

Example:
sources:
  - name: main
    url: "https://example.com/{{{{version}}}}/source.tar.gz"
    build_system: autotools
    configure_args: ["--enable-ssl", "--with-modules"]
    prerequisites: ["build-essential", "libssl-dev"]
    checksum: "sha256:abc123..."
"""

    BINARIES_PROMPT = """
Generate binary download configurations for {software_name}:

Include:
- URL with templating for platform/architecture
- install_path (default: /usr/local/bin)
- archive configuration for extraction
- permissions in octal format
- custom_commands for installation steps

Example:
binaries:
  - name: main
    url: "https://releases.example.com/{{{{version}}}}/binary_{{{{platform}}}}_{{{{architecture}}}}.zip"
    install_path: "/usr/local/bin"
    executable: "binary_name"
    checksum: "sha256:def456..."
"""

    SCRIPTS_PROMPT = """
Generate script installation configurations for {software_name}:

Include:
- HTTPS URLs for security
- checksum for verification
- interpreter (bash, sh, python, etc.)
- timeout (default 300, max 3600 seconds)
- arguments and environment variables

Example:
scripts:
  - name: official
    url: "https://get.example.com/install.sh"
    checksum: "sha256:ghi789..."
    interpreter: "bash"
    timeout: 600
    arguments: ["--channel", "stable"]
"""


# Enhanced prompt templates for saidata 0.3 generation
SAIDATA_V03_GENERATION_TEMPLATE = PromptTemplate(
    name="saidata_v03_generation",
    sections=[
        PromptSection(
            name="system_instruction",
            template="""You are an expert system administrator and software metadata specialist. Your task is to generate a comprehensive saidata YAML file for software packages using the NEW saidata 0.3 schema format. The saidata format is used by the SAI (Software Action Interface) tool for cross-platform software management.

CRITICAL REQUIREMENTS FOR 0.3 SCHEMA:
1. Generate ONLY valid YAML content that follows the saidata 0.3 schema
2. Use version "0.3" (not "0.2")
3. Include NEW installation methods: sources, binaries, scripts
4. Include enhanced metadata with security information and URLs
5. Use accurate package names from repository data when available
6. Include comprehensive provider configurations with new fields
7. Follow URL templating syntax with {{version}}, {{platform}}, {{architecture}}
8. Include security considerations and checksum validation
9. Support compatibility matrix for cross-platform deployment""",
            required=True
        ),
        PromptSection(
            name="software_specification",
            template="""SOFTWARE TO GENERATE SAIDATA FOR: $software_name

TARGET PROVIDERS: $target_providers

Generate saidata 0.3 that supports the specified providers with accurate package names, installation commands, and the NEW installation methods (sources, binaries, scripts) where applicable.""",
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

Use these examples as reference for structure, provider configurations, and best practices. Pay attention to how similar software is configured across different providers, but ensure the generated saidata uses the NEW 0.3 schema format.""",
            condition="has_similar_saidata"
        ),
        PromptSection(
            name="sample_examples",
            template="""REFERENCE SAIDATA SAMPLES:
$sample_saidata_examples

These are high-quality reference examples showing proper saidata structure, formatting, and best practices. Adapt these for the NEW 0.3 schema format with enhanced installation methods.""",
            condition="has_sample_saidata"
        ),
        PromptSection(
            name="user_guidance",
            template="""USER HINTS AND PREFERENCES:
$user_hints

Incorporate these user preferences and hints into the generated saidata 0.3 format.""",
            condition="has_user_hints"
        ),
        PromptSection(
            name="installation_methods_guidance",
            template="""INSTALLATION METHODS GUIDANCE (NEW in 0.3):

The 0.3 schema introduces three new installation methods that should be included when applicable:

**SOURCES** - For building from source code:
- Use when software can be compiled from source
- Include build_system (autotools, cmake, make, meson, ninja, custom)
- Add configure_args, build_args, install_args as needed
- Include prerequisites for build dependencies
- Use URL templating: https://example.com/software-{{version}}.tar.gz
- Always include checksum for security

**BINARIES** - For pre-compiled executables:
- Use when official binaries are available
- Include platform/architecture templating: {{platform}}_{{architecture}}
- Set install_path (default: /usr/local/bin)
- Configure archive extraction if needed
- Set proper permissions (default: 0755)
- Always include checksum for security

**SCRIPTS** - For installation scripts:
- Use when official installation scripts exist
- Always use HTTPS URLs for security
- Include checksum for script verification
- Set appropriate timeout (default 300, max 3600 seconds)
- Specify interpreter (bash, sh, python, etc.)
- Add arguments and environment variables as needed

Include these installation methods alongside traditional package manager installations to provide comprehensive deployment options.""",
            required=True
        ),
        PromptSection(
            name="schema_requirements_v03",
            template="""SAIDATA 0.3 SCHEMA REQUIREMENTS:

The saidata YAML must follow this exact 0.3 JSON schema structure:

**Root Level (Required):**
- version: string "0.3" (REQUIRED - use "0.3" not "0.2")
- metadata: object (required with enhanced fields)
- packages: array (optional - default package definitions)
- services: array (optional - default service definitions)
- files: array (optional - default file definitions)
- directories: array (optional - default directory definitions)
- commands: array (optional - default command definitions)
- ports: array (optional - default port definitions)
- containers: array (optional - default container definitions)
- sources: array (NEW - source build configurations)
- binaries: array (NEW - binary download configurations)
- scripts: array (NEW - script installation configurations)
- providers: object (provider-specific configurations)
- compatibility: object (compatibility matrix and versions)

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
- urls: object (NEW - enhanced URL structure)
- security: object (NEW - security metadata)

**NEW URLs Object:**
- website: string (optional)
- documentation: string (optional)
- source: string (optional)
- issues: string (optional)
- support: string (optional)
- download: string (optional)
- changelog: string (optional)
- license: string (optional)
- sbom: string (optional)
- icon: string (optional)

**NEW Security Metadata Object:**
- cve_exceptions: array of strings (optional)
- security_contact: string (optional)
- vulnerability_disclosure: string (optional)
- sbom_url: string (optional)
- signing_key: string (optional)

**NEW Source Object:**
- name: string (required - e.g., "main", "stable")
- url: string (required - supports {{version}}, {{platform}}, {{architecture}})
- build_system: enum (required - autotools, cmake, make, meson, ninja, custom)
- version: string (optional)
- build_dir: string (optional)
- source_dir: string (optional)
- install_prefix: string (optional - default: /usr/local)
- configure_args: array of strings (optional)
- build_args: array of strings (optional)
- install_args: array of strings (optional)
- prerequisites: array of strings (optional)
- environment: object (optional)
- checksum: string (optional - format: "algorithm:hash")
- custom_commands: object (optional)

**NEW Binary Object:**
- name: string (required - e.g., "main", "stable")
- url: string (required - supports {{version}}, {{platform}}, {{architecture}})
- version: string (optional)
- architecture: string (optional - auto-detected)
- platform: string (optional - auto-detected)
- checksum: string (optional - format: "algorithm:hash")
- install_path: string (optional - default: /usr/local/bin)
- executable: string (optional)
- archive: object (optional)
- permissions: string (optional - octal format)
- custom_commands: object (optional)

**NEW Script Object:**
- name: string (required - e.g., "official", "convenience")
- url: string (required - should use HTTPS)
- version: string (optional)
- interpreter: string (optional - auto-detected from shebang)
- checksum: string (optional - format: "algorithm:hash")
- arguments: array of strings (optional)
- environment: object (optional)
- working_dir: string (optional)
- timeout: integer (optional - default 300, max 3600)
- custom_commands: object (optional)

**Enhanced Provider Configuration:**
Each provider can now contain all resource types including the new ones:
- prerequisites: array of strings (NEW)
- build_commands: array of strings (NEW)
- packages: array of package objects
- package_sources: array of package source objects (NEW)
- repositories: array of repository objects (NEW)
- services: array of service objects
- files: array of file objects
- directories: array of directory objects
- commands: array of command objects
- ports: array of port objects
- containers: array of container objects
- sources: array of source objects (NEW)
- binaries: array of binary objects (NEW)
- scripts: array of script objects (NEW)

**Package Object (Enhanced):**
- name: string (required - logical name)
- package_name: string (required - actual package name)
- version: string (optional)
- alternatives: array of strings (optional)
- install_options: string (optional)
- repository: string (optional)
- checksum: string (optional)
- signature: string (optional)
- download_url: string (optional)

**CRITICAL DATA TYPE REQUIREMENTS:**
- All arrays must be ARRAYS, not objects or strings
- version must be STRING "0.3"
- port numbers must be INTEGERS
- enabled must be BOOLEAN (true/false)
- checksum format: "algorithm:hash" (e.g., "sha256:abc123...")
- permissions format: octal string (e.g., "0755")
- timeout must be INTEGER (seconds)

Generate complete, valid YAML following this 0.3 structure exactly.""",
            required=True
        ),
        PromptSection(
            name="output_instruction",
            template="""OUTPUT INSTRUCTIONS:
1. Generate ONLY the YAML content - no explanations or markdown formatting
2. Start directly with the YAML (version: "0.3")
3. Ensure all YAML syntax is correct and properly indented
4. Include comprehensive provider configurations
5. Use accurate package names from repository data
6. Include relevant metadata with enhanced URLs and security fields
7. Add sources, binaries, and/or scripts sections when applicable
8. Include compatibility matrix when relevant
9. Ensure the output is production-ready and follows 0.3 schema

Generate the saidata 0.3 YAML now:""",
            required=True
        )
    ]
)


# Enhanced context builder for 0.3 generation
class ContextBuilderV03:
    """Enhanced context builder for 0.3 generation with installation method examples"""
    
    def __init__(self):
        self.installation_method_examples = {
            'sources': [
                {
                    'name': 'nginx',
                    'example': {
                        'name': 'main',
                        'url': 'https://nginx.org/download/nginx-{{version}}.tar.gz',
                        'build_system': 'autotools',
                        'configure_args': ['--with-http_ssl_module', '--with-http_v2_module'],
                        'prerequisites': ['build-essential', 'libssl-dev', 'libpcre3-dev'],
                        'checksum': 'sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7'
                    }
                },
                {
                    'name': 'redis',
                    'example': {
                        'name': 'stable',
                        'url': 'https://download.redis.io/redis-stable.tar.gz',
                        'build_system': 'make',
                        'build_args': ['-j4'],
                        'install_prefix': '/usr/local',
                        'prerequisites': ['build-essential', 'tcl']
                    }
                }
            ],
            'binaries': [
                {
                    'name': 'terraform',
                    'example': {
                        'name': 'main',
                        'url': 'https://releases.hashicorp.com/terraform/{{version}}/terraform_{{version}}_{{platform}}_{{architecture}}.zip',
                        'install_path': '/usr/local/bin',
                        'executable': 'terraform',
                        'checksum': 'sha256:fa16d72a078210a54c47dd5bef2f8b9b8a01d94909a51453956b3ec6442ea4c5',
                        'archive': {
                            'format': 'zip'
                        }
                    }
                },
                {
                    'name': 'kubectl',
                    'example': {
                        'name': 'stable',
                        'url': 'https://dl.k8s.io/release/{{version}}/bin/{{platform}}/{{architecture}}/kubectl',
                        'install_path': '/usr/local/bin',
                        'permissions': '0755',
                        'archive': {
                            'format': 'none'
                        }
                    }
                }
            ],
            'scripts': [
                {
                    'name': 'docker',
                    'example': {
                        'name': 'official',
                        'url': 'https://get.docker.com',
                        'interpreter': 'bash',
                        'timeout': 600,
                        'checksum': 'sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7'
                    }
                },
                {
                    'name': 'rustup',
                    'example': {
                        'name': 'convenience',
                        'url': 'https://sh.rustup.rs',
                        'interpreter': 'sh',
                        'arguments': ['-s', '--', '--default-toolchain', 'stable'],
                        'timeout': 300
                    }
                }
            ]
        }
        
        self.security_metadata_examples = {
            'web_server': {
                'security_contact': 'security@example.com',
                'vulnerability_disclosure': 'https://example.com/security',
                'cve_exceptions': ['CVE-2023-1234']
            },
            'database': {
                'security_contact': 'security@database.org',
                'sbom_url': 'https://database.org/sbom.json',
                'signing_key': 'https://database.org/keys/release.asc'
            }
        }
        
        self.compatibility_matrix_examples = [
            {
                'provider': 'apt',
                'platform': ['linux'],
                'architecture': ['amd64', 'arm64'],
                'os_version': ['ubuntu-20.04', 'ubuntu-22.04', 'debian-11'],
                'supported': True,
                'tested': True,
                'recommended': True
            },
            {
                'provider': 'brew',
                'platform': ['darwin'],
                'architecture': ['amd64', 'arm64'],
                'supported': True,
                'tested': True,
                'recommended': True
            }
        ]
    
    def get_installation_method_examples(self, software_category: str = None) -> Dict[str, List[Dict]]:
        """Get relevant installation method examples based on software category"""
        return self.installation_method_examples
    
    def get_security_metadata_example(self, software_category: str = None) -> Dict[str, Any]:
        """Get relevant security metadata example based on software category"""
        if software_category and software_category in self.security_metadata_examples:
            return self.security_metadata_examples[software_category]
        return self.security_metadata_examples.get('web_server', {})
    
    def get_compatibility_matrix_example(self, target_providers: List[str] = None) -> List[Dict]:
        """Get relevant compatibility matrix example based on target providers"""
        if not target_providers:
            return self.compatibility_matrix_examples
        
        # Filter examples based on target providers
        filtered_examples = []
        for example in self.compatibility_matrix_examples:
            if example['provider'] in target_providers:
                filtered_examples.append(example)
        
        return filtered_examples or self.compatibility_matrix_examples


# Updated prompt manager for 0.3 templates
class PromptManagerV03:
    """Manager for 0.3 prompt templates"""
    
    def __init__(self):
        self.templates = {
            "saidata_v03_generation": SAIDATA_V03_GENERATION_TEMPLATE,
        }
        self.context_builder = ContextBuilderV03()
    
    def get_template(self, template_name: str) -> PromptTemplate:
        """Get a prompt template by name"""
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")
        return self.templates[template_name]
    
    def render_prompt(self, template_name: str, context: GenerationContext) -> str:
        """Render a prompt template with context"""
        template = self.get_template(template_name)
        return template.render(context)
    
    def enhance_context_for_v03(self, context: GenerationContext) -> GenerationContext:
        """Enhance generation context with 0.3-specific examples and metadata"""
        # Add installation method examples
        context.installation_method_examples = self.context_builder.get_installation_method_examples(
            getattr(context, 'software_category', None)
        )
        
        # Add security metadata examples
        context.security_metadata_example = self.context_builder.get_security_metadata_example(
            getattr(context, 'software_category', None)
        )
        
        # Add compatibility matrix examples
        context.compatibility_matrix_example = self.context_builder.get_compatibility_matrix_example(
            context.target_providers
        )
        
        return context


# Integration function to update existing prompt manager with 0.3 templates
def integrate_v03_prompts():
    """Integrate 0.3 prompts into the existing prompt system.
    
    This function can be called to add 0.3 templates to the existing PromptManager.
    """
    try:
        from .prompts import PromptManager
        
        # Get existing prompt manager instance or create new one
        existing_manager = PromptManager()
        
        # Add 0.3 templates to existing manager
        existing_manager.templates["saidata_v03_generation"] = SAIDATA_V03_GENERATION_TEMPLATE
        
        logger.info("Successfully integrated 0.3 prompts into existing prompt manager")
        return existing_manager
        
    except ImportError as e:
        logger.warning(f"Could not integrate with existing prompt manager: {e}")
        # Return new 0.3 manager as fallback
        return PromptManagerV03()


# Example usage for 0.3 prompt system
async def example_v03_generation():
    """Example of how to use the 0.3 prompt system for enhanced saidata generation.
    
    This example shows how to:
    1. Create a generation context
    2. Enhance it with 0.3-specific features
    3. Render prompts with installation methods, security metadata, and compatibility info
    """
    # Create base generation context
    context = GenerationContext(
        software_name="nginx",
        target_providers=["apt", "brew", "winget"],
        user_hints={"category": "web_server"}
    )
    
    # Initialize 0.3 prompt manager
    prompt_manager = PromptManagerV03()
    
    # Enhance context with 0.3 features
    enhanced_context = prompt_manager.enhance_context_for_v03(context)
    
    # Render 0.3 generation prompt
    prompt = prompt_manager.render_prompt("saidata_v03_generation", enhanced_context)
    
    logger.info(f"Generated 0.3 prompt for {context.software_name}")
    return prompt


# Template validation function
def validate_v03_templates():
    """Validate that all 0.3 templates are properly structured."""
    manager = PromptManagerV03()
    
    validation_results = {}
    
    for template_name, template in manager.templates.items():
        try:
            # Check that template has required sections
            required_sections = ["system_instruction", "software_specification", "output_instruction"]
            template_sections = [section.name for section in template.sections]
            
            missing_sections = [req for req in required_sections if req not in template_sections]
            
            validation_results[template_name] = {
                "valid": len(missing_sections) == 0,
                "missing_sections": missing_sections,
                "total_sections": len(template.sections)
            }
            
        except Exception as e:
            validation_results[template_name] = {
                "valid": False,
                "error": str(e)
            }
    
    return validation_results