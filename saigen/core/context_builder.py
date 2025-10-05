"""Enhanced context builder for saidata 0.3 generation."""

import logging
from typing import Dict, Any, Optional, List
from ..models.generation import GenerationContext
from ..repositories.indexer import RAGContextBuilder


logger = logging.getLogger(__name__)


class ContextBuilderV03:
    """Context builder with installation method examples for 0.3 generation."""
    
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
                        'prerequisites': ['build-essential', 'libssl-dev', 'libpcre3-dev']
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
                        'timeout': 600
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


class EnhancedContextBuilder:
    """Enhanced context builder for saidata generation with installation method examples and security metadata."""
    
    def __init__(self, rag_context_builder: Optional[RAGContextBuilder] = None):
        """Initialize enhanced context builder.
        
        Args:
            rag_context_builder: Optional RAG context builder for repository data
        """
        self.rag_context_builder = rag_context_builder
        self.v03_context_builder = ContextBuilderV03()
        
        # Installation method detection patterns
        self.source_indicators = [
            'source', 'compile', 'build', 'cmake', 'autotools', 'make', 'configure',
            'gcc', 'clang', 'development', 'dev', 'devel'
        ]
        
        self.binary_indicators = [
            'binary', 'executable', 'release', 'download', 'precompiled',
            'standalone', 'portable', 'static'
        ]
        
        self.script_indicators = [
            'script', 'installer', 'install.sh', 'setup', 'bootstrap',
            'get.', 'curl', 'wget', 'convenience'
        ]
        
        # Security metadata patterns by category
        self.security_patterns = {
            'web_server': {
                'common_cves': ['CVE-2023-44487', 'CVE-2022-41742'],
                'security_contacts': ['security@nginx.org', 'security@apache.org'],
                'vulnerability_urls': [
                    'https://nginx.org/en/security_advisories.html',
                    'https://httpd.apache.org/security/vulnerabilities_24.html'
                ]
            },
            'database': {
                'common_cves': ['CVE-2023-2976', 'CVE-2022-31144'],
                'security_contacts': ['security@postgresql.org', 'security@mysql.com'],
                'vulnerability_urls': [
                    'https://www.postgresql.org/support/security/',
                    'https://www.mysql.com/support/security/'
                ]
            },
            'container': {
                'common_cves': ['CVE-2023-28840', 'CVE-2022-36109'],
                'security_contacts': ['security@docker.com', 'security@containerd.io'],
                'vulnerability_urls': [
                    'https://docs.docker.com/engine/security/',
                    'https://github.com/containerd/containerd/security'
                ]
            },
            'programming': {
                'common_cves': ['CVE-2023-29383', 'CVE-2022-46175'],
                'security_contacts': ['security@nodejs.org', 'security@python.org'],
                'vulnerability_urls': [
                    'https://nodejs.org/en/security/',
                    'https://www.python.org/news/security/'
                ]
            }
        }
        
        # Compatibility matrix templates
        self.compatibility_templates = {
            'cross_platform': [
                {
                    'provider': 'apt',
                    'platform': ['linux'],
                    'architecture': ['amd64', 'arm64'],
                    'os_version': ['ubuntu-20.04', 'ubuntu-22.04', 'debian-11', 'debian-12'],
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
                },
                {
                    'provider': 'winget',
                    'platform': ['windows'],
                    'architecture': ['amd64', 'arm64'],
                    'os_version': ['windows-10', 'windows-11'],
                    'supported': True,
                    'tested': False,
                    'recommended': True
                }
            ],
            'linux_only': [
                {
                    'provider': 'apt',
                    'platform': ['linux'],
                    'architecture': ['amd64', 'arm64'],
                    'os_version': ['ubuntu-20.04', 'ubuntu-22.04', 'debian-11', 'debian-12'],
                    'supported': True,
                    'tested': True,
                    'recommended': True
                },
                {
                    'provider': 'dnf',
                    'platform': ['linux'],
                    'architecture': ['amd64', 'arm64'],
                    'os_version': ['fedora-38', 'fedora-39', 'rhel-8', 'rhel-9'],
                    'supported': True,
                    'tested': True,
                    'recommended': True
                }
            ]
        }
    
    async def build_enhanced_context(self, context: GenerationContext) -> GenerationContext:
        """Build enhanced context with 0.3-specific data.
        
        Args:
            context: Base generation context
            
        Returns:
            Enhanced context with installation methods, security metadata, and compatibility info
        """
        try:
            # Add installation method examples based on software characteristics
            context = await self._add_installation_method_context(context)
            
            # Add security metadata context
            context = await self._add_security_metadata_context(context)
            
            # Add compatibility matrix context
            context = await self._add_compatibility_matrix_context(context)
            
            # Add URL templating examples
            context = await self._add_url_templating_context(context)
            
            # Add provider enhancement examples
            context = await self._add_provider_enhancement_context(context)
            
            logger.debug(f"Enhanced context built for {context.software_name} with 0.3 features")
            
        except Exception as e:
            logger.warning(f"Failed to build enhanced context for {context.software_name}: {e}")
        
        return context
    
    async def _add_installation_method_context(self, context: GenerationContext) -> GenerationContext:
        """Add installation method examples and guidance to context."""
        
        try:
            # Determine likely installation methods based on software name and repository data
            likely_methods = self._detect_installation_methods(context)
            
            # Get relevant examples for each method
            installation_examples = {}
            
            if 'sources' in likely_methods:
                source_examples = self._get_source_examples(context)
                if source_examples:
                    installation_examples['sources'] = source_examples
            
            if 'binaries' in likely_methods:
                binary_examples = self._get_binary_examples(context)
                if binary_examples:
                    installation_examples['binaries'] = binary_examples
            
            if 'scripts' in likely_methods:
                script_examples = self._get_script_examples(context)
                if script_examples:
                    installation_examples['scripts'] = script_examples
            
            # Add to context
            context.installation_method_examples = installation_examples
            context.likely_installation_methods = likely_methods
        except Exception as e:
            logger.warning(f"Failed to add installation method context: {e}")
        
        return context
    
    async def _add_security_metadata_context(self, context: GenerationContext) -> GenerationContext:
        """Add security metadata examples and guidance to context."""
        
        try:
            # Detect software category for relevant security patterns
            software_category = self._detect_software_category(context)
            
            # Get security metadata template
            security_template = self._get_security_metadata_template(software_category)
            
            # Add to context
            context.security_metadata_template = security_template
            context.software_category = software_category
        except Exception as e:
            logger.warning(f"Failed to add security metadata context: {e}")
        
        return context
    
    async def _add_compatibility_matrix_context(self, context: GenerationContext) -> GenerationContext:
        """Add compatibility matrix examples to context."""
        
        try:
            # Ensure target_providers is not None
            target_providers = context.target_providers or []
            
            # Determine compatibility scope based on target providers
            compatibility_scope = self._determine_compatibility_scope(target_providers)
            
            # Get compatibility matrix template
            compatibility_template = self.compatibility_templates.get(
                compatibility_scope, 
                self.compatibility_templates['cross_platform']
            )
            
            # Filter template based on actual target providers
            filtered_template = []
            if target_providers:
                for entry in compatibility_template:
                    if entry and entry.get('provider') in target_providers:
                        filtered_template.append(entry)
            
            # Add to context
            context.compatibility_matrix_template = filtered_template or compatibility_template
        except Exception as e:
            logger.warning(f"Failed to add compatibility matrix context: {e}")
        
        return context
    
    async def _add_url_templating_context(self, context: GenerationContext) -> GenerationContext:
        """Add URL templating examples and patterns to context."""
        
        try:
            url_templating_examples = {
                'version_only': [
                    'https://github.com/user/repo/archive/v{{version}}.tar.gz',
                    'https://releases.example.com/{{version}}/software.zip'
                ],
                'platform_architecture': [
                    'https://releases.example.com/{{version}}/software_{{platform}}_{{architecture}}.zip',
                    'https://github.com/user/repo/releases/download/v{{version}}/binary-{{platform}}-{{architecture}}.tar.gz'
                ],
                'complex_patterns': [
                    'https://dl.k8s.io/release/{{version}}/bin/{{platform}}/{{architecture}}/kubectl',
                    'https://releases.hashicorp.com/terraform/{{version}}/terraform_{{version}}_{{platform}}_{{architecture}}.zip'
                ]
            }
            
            # Add to context
            context.url_templating_examples = url_templating_examples
        except Exception as e:
            logger.warning(f"Failed to add URL templating context: {e}")
        
        return context
    
    async def _add_provider_enhancement_context(self, context: GenerationContext) -> GenerationContext:
        """Add provider enhancement examples for 0.3 schema."""
        
        try:
            provider_enhancements = {
                'package_sources': [
                    {
                        'name': 'official',
                        'repository': 'main',
                        'packages': [{'name': 'software', 'package_name': 'software-package'}],
                        'priority': 1,
                        'recommended': True
                    }
                ],
                'repositories': [
                    {
                        'name': 'official',
                        'url': 'https://packages.example.com',
                        'type': 'deb',
                        'priority': 1,
                        'recommended': True
                    }
                ],
                'prerequisites': [
                    'build-essential',
                    'libssl-dev',
                    'pkg-config'
                ],
                'build_commands': [
                    './configure --prefix=/usr/local',
                    'make -j$(nproc)',
                    'make install'
                ]
            }
            
            # Add to context
            context.provider_enhancement_examples = provider_enhancements
        except Exception as e:
            logger.warning(f"Failed to add provider enhancement context: {e}")
        
        return context
    
    def _detect_installation_methods(self, context: GenerationContext) -> List[str]:
        """Detect likely installation methods based on software characteristics."""
        methods = []
        software_name = context.software_name.lower()
        
        # Check repository data for clues
        has_dev_packages = False
        has_binary_releases = False
        
        if context.repository_data:
            for pkg in context.repository_data:
                pkg_name = pkg.name.lower()
                pkg_desc = (pkg.description or '').lower()
                
                # Check for development/source indicators
                if any(indicator in pkg_name or indicator in pkg_desc 
                       for indicator in self.source_indicators):
                    has_dev_packages = True
                
                # Check for binary indicators
                if any(indicator in pkg_name or indicator in pkg_desc 
                       for indicator in self.binary_indicators):
                    has_binary_releases = True
        
        # Check software name for indicators
        if any(indicator in software_name for indicator in self.source_indicators):
            has_dev_packages = True
        
        if any(indicator in software_name for indicator in self.binary_indicators):
            has_binary_releases = True
        
        if any(indicator in software_name for indicator in self.script_indicators):
            methods.append('scripts')
        
        # Determine methods based on analysis
        if has_dev_packages or software_name in ['nginx', 'redis', 'postgresql', 'mysql']:
            methods.append('sources')
        
        if has_binary_releases or software_name in ['terraform', 'kubectl', 'docker', 'helm']:
            methods.append('binaries')
        
        # Popular software that commonly has installation scripts
        if software_name in ['docker', 'kubernetes', 'rustup', 'nvm', 'pyenv']:
            methods.append('scripts')
        
        # Default to at least one method if none detected
        if not methods:
            methods = ['sources']  # Most software can be built from source
        
        return methods
    
    def _get_source_examples(self, context: GenerationContext) -> List[Dict[str, Any]]:
        """Get relevant source build examples."""
        examples = self.v03_context_builder.installation_method_examples['sources']
        
        # Filter examples based on software characteristics
        software_name = context.software_name.lower()
        
        if 'web' in software_name or 'http' in software_name or 'server' in software_name:
            # Prefer web server examples
            return [ex for ex in examples if ex['name'] in ['nginx', 'apache']] or examples[:2]
        
        if 'database' in software_name or 'db' in software_name:
            # Prefer database examples
            return [ex for ex in examples if ex['name'] in ['redis', 'postgresql']] or examples[:2]
        
        return examples[:2]  # Default to first 2 examples
    
    def _get_binary_examples(self, context: GenerationContext) -> List[Dict[str, Any]]:
        """Get relevant binary download examples."""
        examples = self.v03_context_builder.installation_method_examples['binaries']
        
        # Filter examples based on software characteristics
        software_name = context.software_name.lower()
        
        if 'terraform' in software_name or 'hashicorp' in software_name:
            return [ex for ex in examples if ex['name'] == 'terraform'] or examples[:1]
        
        if 'kubernetes' in software_name or 'k8s' in software_name or 'kubectl' in software_name:
            return [ex for ex in examples if ex['name'] == 'kubectl'] or examples[:1]
        
        return examples[:2]  # Default to first 2 examples
    
    def _get_script_examples(self, context: GenerationContext) -> List[Dict[str, Any]]:
        """Get relevant script installation examples."""
        examples = self.v03_context_builder.installation_method_examples['scripts']
        
        # Filter examples based on software characteristics
        software_name = context.software_name.lower()
        
        if 'docker' in software_name:
            return [ex for ex in examples if ex['name'] == 'docker'] or examples[:1]
        
        if 'rust' in software_name or 'cargo' in software_name:
            return [ex for ex in examples if ex['name'] == 'rustup'] or examples[:1]
        
        return examples[:2]  # Default to first 2 examples
    
    def _detect_software_category(self, context: GenerationContext) -> str:
        """Detect software category for security metadata."""
        software_name = context.software_name.lower()
        
        # Web servers
        if any(term in software_name for term in ['nginx', 'apache', 'httpd', 'web', 'server']):
            return 'web_server'
        
        # Databases
        if any(term in software_name for term in ['mysql', 'postgresql', 'redis', 'mongodb', 'database', 'db']):
            return 'database'
        
        # Containers
        if any(term in software_name for term in ['docker', 'containerd', 'podman', 'container']):
            return 'container'
        
        # Programming languages/tools
        if any(term in software_name for term in ['python', 'node', 'nodejs', 'java', 'go', 'rust', 'compiler']):
            return 'programming'
        
        return 'web_server'  # Default category
    
    def _get_security_metadata_template(self, category: str) -> Dict[str, Any]:
        """Get security metadata template for category."""
        return self.security_patterns.get(category, self.security_patterns['web_server'])
    
    def _determine_compatibility_scope(self, target_providers: Optional[List[str]]) -> str:
        """Determine compatibility scope based on target providers."""
        if not target_providers:
            return 'cross_platform'
        
        # Check if providers span multiple platforms
        linux_providers = {'apt', 'dnf', 'yum', 'pacman', 'zypper'}
        macos_providers = {'brew'}
        windows_providers = {'winget', 'choco'}
        
        has_linux = any(p in linux_providers for p in target_providers)
        has_macos = any(p in macos_providers for p in target_providers)
        has_windows = any(p in windows_providers for p in target_providers)
        
        platform_count = sum([has_linux, has_macos, has_windows])
        
        if platform_count > 1:
            return 'cross_platform'
        elif has_linux:
            return 'linux_only'
        else:
            return 'cross_platform'  # Default to cross-platform