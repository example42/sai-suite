"""Repository configuration management for different providers."""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field

from saigen.models.repository import RepositoryInfo
from saigen.utils.errors import ConfigurationError


@dataclass
class RepositoryConfig:
    """Configuration for a repository provider."""
    name: str
    type: str  # apt, dnf, brew, winget, etc.
    platform: str  # linux, macos, windows
    url: Optional[str] = None
    enabled: bool = True
    priority: int = 1
    cache_ttl_hours: int = 24
    timeout: int = 300
    architecture: Optional[List[str]] = None
    parsing: Dict[str, Any] = field(default_factory=dict)
    credentials: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_repository_info(self) -> RepositoryInfo:
        """Convert to RepositoryInfo model."""
        return RepositoryInfo(
            name=self.name,
            url=self.url,
            type=self.type,
            platform=self.platform,
            architecture=self.architecture,
            enabled=self.enabled,
            priority=self.priority,
            description=self.metadata.get('description'),
            maintainer=self.metadata.get('maintainer')
        )


class RepositoryConfigManager:
    """Manager for repository configurations."""
    
    def __init__(self, config_dir: Union[str, Path]):
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory containing repository configuration files
        """
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, RepositoryConfig] = {}
        self._loaded = False
    
    async def load_configs(self, reload: bool = False) -> None:
        """Load repository configurations from YAML files.
        
        Args:
            reload: Force reload even if already loaded
        """
        if self._loaded and not reload:
            return
        
        self._configs.clear()
        
        if not self.config_dir.exists():
            return
        
        # Load all YAML files in config directory
        for config_file in self.config_dir.glob("*.yaml"):
            try:
                await self._load_config_file(config_file)
            except Exception as e:
                # Log error but continue loading other configs
                print(f"Warning: Failed to load config {config_file}: {e}")
        
        # Also check for yml extension
        for config_file in self.config_dir.glob("*.yml"):
            try:
                await self._load_config_file(config_file)
            except Exception as e:
                print(f"Warning: Failed to load config {config_file}: {e}")
        
        self._loaded = True
    
    async def _load_config_file(self, config_file: Path) -> None:
        """Load a single configuration file."""
        # Use sync I/O for now (async file I/O can be added later with aiofiles)
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if not isinstance(data, dict):
            raise ConfigurationError(f"Invalid config format in {config_file}")
        
        # Handle both single repository and multiple repositories in one file
        if 'repositories' in data:
            # Multiple repositories
            for repo_data in data['repositories']:
                config = self._parse_repository_config(repo_data, config_file)
                self._configs[config.name] = config
        else:
            # Single repository
            config = self._parse_repository_config(data, config_file)
            self._configs[config.name] = config
    
    def _parse_repository_config(self, data: Dict[str, Any], source_file: Path) -> RepositoryConfig:
        """Parse repository configuration from data."""
        required_fields = ['name', 'type', 'platform']
        for field in required_fields:
            if field not in data:
                raise ConfigurationError(f"Missing required field '{field}' in {source_file}")
        
        # Security: Validate URL scheme if URL is provided
        if 'url' in data and data['url']:
            url = data['url']
            if not isinstance(url, str):
                raise ConfigurationError(f"URL must be a string in {source_file}")
            
            # Only allow safe URL schemes
            allowed_schemes = ['http', 'https', 'ftp', 'ftps']
            if '://' in url:
                scheme = url.split('://')[0].lower()
                if scheme not in allowed_schemes:
                    raise ConfigurationError(f"Unsafe URL scheme '{scheme}' in {source_file}. Allowed: {allowed_schemes}")
        
        return RepositoryConfig(
            name=data['name'],
            type=data['type'],
            platform=data['platform'],
            url=data.get('url'),
            enabled=data.get('enabled', True),
            priority=data.get('priority', 1),
            cache_ttl_hours=data.get('cache_ttl_hours', 24),
            timeout=data.get('timeout', 300),
            architecture=data.get('architecture'),
            parsing=data.get('parsing', {}),
            credentials=data.get('credentials', {}),
            metadata=data.get('metadata', {})
        )
    
    def get_config(self, name: str) -> Optional[RepositoryConfig]:
        """Get configuration by name."""
        return self._configs.get(name)
    
    def get_configs_by_type(self, repo_type: str) -> List[RepositoryConfig]:
        """Get all configurations for a specific repository type."""
        return [config for config in self._configs.values() if config.type == repo_type]
    
    def get_configs_by_platform(self, platform: str) -> List[RepositoryConfig]:
        """Get all configurations for a specific platform."""
        return [config for config in self._configs.values() if config.platform == platform]
    
    def get_enabled_configs(self) -> List[RepositoryConfig]:
        """Get all enabled configurations."""
        return [config for config in self._configs.values() if config.enabled]
    
    def get_all_configs(self) -> List[RepositoryConfig]:
        """Get all configurations."""
        return list(self._configs.values())
    
    def get_sorted_configs(self, platform: Optional[str] = None) -> List[RepositoryConfig]:
        """Get configurations sorted by priority.
        
        Args:
            platform: Filter by platform (optional)
            
        Returns:
            List of configurations sorted by priority (higher first)
        """
        configs = self.get_enabled_configs()
        
        if platform:
            configs = [c for c in configs if c.platform == platform]
        
        return sorted(configs, key=lambda c: c.priority, reverse=True)


def create_default_configs() -> List[Dict[str, Any]]:
    """Create default repository configurations."""
    return [
        {
            'name': 'ubuntu-main',
            'type': 'apt',
            'platform': 'linux',
            'url': 'http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/Packages.gz',
            'enabled': True,
            'priority': 10,
            'architecture': ['amd64'],
            'parsing': {
                'format': 'text',
                'line_pattern': r'^Package:\s*(.+)$',
                'name_group': 1,
                'version_pattern': r'^Version:\s*(.+)$',
                'description_pattern': r'^Description:\s*(.+)$'
            },
            'metadata': {
                'description': 'Ubuntu Main Repository',
                'maintainer': 'Ubuntu'
            }
        },
        {
            'name': 'homebrew-core',
            'type': 'brew',
            'platform': 'macos',
            'url': 'https://formulae.brew.sh/api/formula.json',
            'enabled': True,
            'priority': 10,
            'parsing': {
                'format': 'json',
                'field_mapping': {
                    'name': 'name',
                    'version': 'versions.stable',
                    'description': 'desc',
                    'homepage': 'homepage'
                }
            },
            'metadata': {
                'description': 'Homebrew Core Formulae',
                'maintainer': 'Homebrew'
            }
        },
        {
            'name': 'fedora-updates',
            'type': 'dnf',
            'platform': 'linux',
            'url': 'https://mirrors.fedoraproject.org/metalink?repo=updates-released-f39&arch=x86_64',
            'enabled': True,
            'priority': 8,
            'architecture': ['x86_64'],
            'parsing': {
                'format': 'xml',
                'package_xpath': './/package',
                'xml_field_mapping': {
                    'name': 'name',
                    'version': 'version/@ver',
                    'description': 'description'
                }
            },
            'metadata': {
                'description': 'Fedora Updates Repository',
                'maintainer': 'Fedora Project'
            }
        },
        {
            'name': 'winget-community',
            'type': 'winget',
            'platform': 'windows',
            'url': 'https://api.github.com/repos/microsoft/winget-pkgs/contents/manifests',
            'enabled': True,
            'priority': 10,
            'parsing': {
                'format': 'json',
                'package_path': [],
                'field_mapping': {
                    'name': 'name',
                    'version': 'PackageVersion',
                    'description': 'ShortDescription',
                    'homepage': 'PackageUrl'
                }
            },
            'metadata': {
                'description': 'Windows Package Manager Community Repository',
                'maintainer': 'Microsoft'
            }
        }
    ]


async def save_default_configs(config_dir: Union[str, Path]) -> None:
    """Save default configurations to files.
    
    Args:
        config_dir: Directory to save configuration files
    """
    config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    
    default_configs = create_default_configs()
    
    # Group by platform for organization
    platforms = {}
    for config in default_configs:
        platform = config['platform']
        if platform not in platforms:
            platforms[platform] = []
        platforms[platform].append(config)
    
    # Save one file per platform
    for platform, configs in platforms.items():
        config_file = config_dir / f"{platform}-repositories.yaml"
        
        data = {
            'repositories': configs
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)


def load_provider_configs_from_yaml(yaml_content: str) -> List[RepositoryConfig]:
    """Load repository configurations from YAML content.
    
    Args:
        yaml_content: YAML content as string
        
    Returns:
        List of repository configurations
    """
    try:
        data = yaml.safe_load(yaml_content)
        
        if not isinstance(data, dict):
            raise ConfigurationError("Invalid YAML format")
        
        configs = []
        
        if 'repositories' in data:
            for repo_data in data['repositories']:
                config = RepositoryConfig(**repo_data)
                configs.append(config)
        else:
            config = RepositoryConfig(**data)
            configs.append(config)
        
        return configs
        
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML: {str(e)}")
    except Exception as e:
        raise ConfigurationError(f"Configuration error: {str(e)}")


def validate_repository_config(config: RepositoryConfig) -> List[str]:
    """Validate repository configuration.
    
    Args:
        config: Repository configuration to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check required fields
    if not config.name:
        errors.append("Repository name is required")
    
    if not config.type:
        errors.append("Repository type is required")
    
    if not config.platform:
        errors.append("Repository platform is required")
    
    # Validate platform values
    valid_platforms = ['linux', 'macos', 'windows', 'unix']
    if config.platform not in valid_platforms:
        errors.append(f"Invalid platform '{config.platform}'. Must be one of: {valid_platforms}")
    
    # Validate repository type
    valid_types = ['apt', 'dnf', 'yum', 'brew', 'winget', 'pacman', 'zypper', 'portage', 'pkg', 'generic']
    if config.type not in valid_types:
        errors.append(f"Invalid repository type '{config.type}'. Must be one of: {valid_types}")
    
    # Validate priority
    if config.priority < 1 or config.priority > 100:
        errors.append("Priority must be between 1 and 100")
    
    # Validate cache TTL
    if config.cache_ttl_hours < 1:
        errors.append("Cache TTL must be at least 1 hour")
    
    # Validate timeout
    if config.timeout < 1:
        errors.append("Timeout must be at least 1 second")
    
    return errors