"""Pydantic models for SaiData structure."""

from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ServiceType(str, Enum):
    """Service management types."""

    SYSTEMD = "systemd"
    INIT = "init"
    LAUNCHD = "launchd"
    WINDOWS_SERVICE = "windows_service"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


class FileType(str, Enum):
    """File types."""

    CONFIG = "config"
    BINARY = "binary"
    LIBRARY = "library"
    DATA = "data"
    LOG = "log"
    TEMP = "temp"
    SOCKET = "socket"


class Protocol(str, Enum):
    """Network protocols."""

    TCP = "tcp"
    UDP = "udp"
    SCTP = "sctp"


class BuildSystem(str, Enum):
    """Build system types for source builds."""

    AUTOTOOLS = "autotools"
    CMAKE = "cmake"
    MAKE = "make"
    MESON = "meson"
    NINJA = "ninja"
    CUSTOM = "custom"


class RepositoryType(str, Enum):
    """Repository types."""

    UPSTREAM = "upstream"
    OS_DEFAULT = "os-default"
    OS_BACKPORTS = "os-backports"
    THIRD_PARTY = "third-party"


class Urls(BaseModel):
    """URL metadata."""

    website: Optional[str] = None
    documentation: Optional[str] = None
    source: Optional[str] = None
    issues: Optional[str] = None
    support: Optional[str] = None
    download: Optional[str] = None
    changelog: Optional[str] = None
    license: Optional[str] = None
    sbom: Optional[str] = None
    icon: Optional[str] = None


class SecurityMetadata(BaseModel):
    """Security-related metadata."""

    cve_exceptions: Optional[List[str]] = None
    security_contact: Optional[str] = None
    vulnerability_disclosure: Optional[str] = None
    sbom_url: Optional[str] = None
    signing_key: Optional[str] = None


class Metadata(BaseModel):
    """Software metadata."""

    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    tags: Optional[List[str]] = None
    license: Optional[str] = None
    language: Optional[str] = None
    maintainer: Optional[str] = None
    urls: Optional[Urls] = None
    security: Optional[SecurityMetadata] = None


class Package(BaseModel):
    """Package definition.
    
    The Package model distinguishes between:
    - name: Logical identifier used for cross-referencing within saidata
    - package_name: Actual package name used by package managers (apt, brew, etc.)
    
    This allows the same logical name to map to different actual package names
    across different providers.
    """

    name: str  # Logical identifier for cross-referencing
    package_name: str  # Actual package name used by package managers
    version: Optional[str] = None
    alternatives: Optional[List[str]] = None
    install_options: Optional[str] = None
    repository: Optional[str] = None
    checksum: Optional[str] = None
    signature: Optional[str] = None
    download_url: Optional[str] = None


class Service(BaseModel):
    """Service definition."""

    name: str
    service_name: Optional[str] = None
    type: Optional[ServiceType] = None
    enabled: Optional[bool] = None
    config_files: Optional[List[str]] = None


class File(BaseModel):
    """File definition."""

    name: str
    path: str
    type: Optional[FileType] = None
    owner: Optional[str] = None
    group: Optional[str] = None
    mode: Optional[str] = None
    backup: Optional[bool] = None


class Directory(BaseModel):
    """Directory definition."""

    name: str
    path: str
    owner: Optional[str] = None
    group: Optional[str] = None
    mode: Optional[str] = None
    recursive: Optional[bool] = None


class Command(BaseModel):
    """Command definition."""

    name: str
    path: Optional[str] = None
    arguments: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    shell_completion: Optional[bool] = None
    man_page: Optional[str] = None


class Port(BaseModel):
    """Port definition."""

    port: int
    protocol: Optional[Protocol] = None
    service: Optional[str] = None
    description: Optional[str] = None


class Container(BaseModel):
    """Container definition."""

    name: str
    image: str
    tag: Optional[str] = None
    registry: Optional[str] = None
    platform: Optional[str] = None
    ports: Optional[List[str]] = None
    volumes: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    networks: Optional[List[str]] = None
    labels: Optional[Dict[str, str]] = None


class CustomCommands(BaseModel):
    """Custom commands for overriding default behavior in installation methods.
    
    These commands allow fine-grained control over each step of the installation
    process for sources, binaries, and scripts.
    """

    download: Optional[str] = None
    extract: Optional[str] = None
    configure: Optional[str] = None
    build: Optional[str] = None
    install: Optional[str] = None
    uninstall: Optional[str] = None
    validation: Optional[str] = None
    version: Optional[str] = None


class Source(BaseModel):
    """Source build configuration.
    
    Defines how to download, build, and install software from source code.
    Supports multiple build systems and custom build commands.
    """

    name: str  # Logical name (e.g., 'main', 'stable', 'dev')
    url: str  # Download URL with template support ({{version}}, {{platform}}, etc.)
    build_system: BuildSystem
    version: Optional[str] = None
    build_dir: Optional[str] = None
    source_dir: Optional[str] = None
    install_prefix: Optional[str] = None
    configure_args: Optional[List[str]] = None
    build_args: Optional[List[str]] = None
    install_args: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    checksum: Optional[str] = None  # Format: "algorithm:hash" (e.g., "sha256:abc123...")
    custom_commands: Optional[CustomCommands] = None


class ArchiveConfig(BaseModel):
    """Archive extraction configuration for binary downloads.
    
    Defines how to extract and process downloaded binary archives.
    """

    format: Optional[str] = None  # Archive format: tar.gz, zip, tar.bz2, etc.
    strip_prefix: Optional[str] = None  # Strip leading path components
    extract_path: Optional[str] = None  # Path within archive to extract


class Binary(BaseModel):
    """Binary download configuration.
    
    Defines how to download and install pre-compiled binary software.
    Supports platform/architecture-specific URLs and archive extraction.
    """

    name: str  # Logical name (e.g., 'main', 'stable')
    url: str  # Download URL with template support ({{version}}, {{platform}}, {{architecture}})
    version: Optional[str] = None
    architecture: Optional[str] = None  # amd64, arm64, x86_64, etc.
    platform: Optional[str] = None  # linux, darwin, windows
    checksum: Optional[str] = None  # Format: "algorithm:hash" (e.g., "sha256:abc123...")
    install_path: Optional[str] = None  # Installation directory (default: /usr/local/bin)
    executable: Optional[str] = None  # Name of the executable file
    archive: Optional[ArchiveConfig] = None
    permissions: Optional[str] = None  # Octal format (e.g., "0755")
    custom_commands: Optional[CustomCommands] = None


class Script(BaseModel):
    """Script installation configuration.
    
    Defines how to download and execute installation scripts with security features.
    Includes checksum verification and timeout controls.
    """

    name: str  # Logical name (e.g., 'official', 'convenience')
    url: str  # Script download URL
    version: Optional[str] = None
    interpreter: Optional[str] = None  # bash, sh, python, python3, etc.
    checksum: Optional[str] = None  # Format: "algorithm:hash" (e.g., "sha256:abc123...")
    arguments: Optional[List[str]] = None  # Arguments to pass to the script
    environment: Optional[Dict[str, str]] = None  # Environment variables
    working_dir: Optional[str] = None  # Working directory for script execution
    timeout: Optional[int] = Field(None, ge=1, le=3600)  # Timeout in seconds (1-3600)
    custom_commands: Optional[CustomCommands] = None


class PackageSource(BaseModel):
    """Package source definition."""

    name: str
    priority: Optional[int] = None
    recommended: Optional[bool] = None
    repository: str
    packages: List[Package]
    notes: Optional[str] = None


class Repository(BaseModel):
    """Repository definition."""

    name: str
    url: Optional[str] = None
    key: Optional[str] = None
    type: Optional[RepositoryType] = None
    components: Optional[List[str]] = None
    maintainer: Optional[str] = None
    priority: Optional[int] = None
    recommended: Optional[bool] = None
    notes: Optional[str] = None
    packages: Optional[List[Package]] = None
    services: Optional[List[Service]] = None
    files: Optional[List[File]] = None
    directories: Optional[List[Directory]] = None
    commands: Optional[List[Command]] = None
    ports: Optional[List[Port]] = None
    containers: Optional[List[Container]] = None
    sources: Optional[List[Source]] = None
    binaries: Optional[List[Binary]] = None
    scripts: Optional[List[Script]] = None


class ProviderConfig(BaseModel):
    """Provider-specific configuration."""

    prerequisites: Optional[List[str]] = None
    build_commands: Optional[List[str]] = None
    packages: Optional[List[Package]] = None
    package_sources: Optional[List[PackageSource]] = None
    repositories: Optional[List[Repository]] = None
    services: Optional[List[Service]] = None
    files: Optional[List[File]] = None
    directories: Optional[List[Directory]] = None
    commands: Optional[List[Command]] = None
    ports: Optional[List[Port]] = None
    containers: Optional[List[Container]] = None
    sources: Optional[List[Source]] = None
    binaries: Optional[List[Binary]] = None
    scripts: Optional[List[Script]] = None


class CompatibilityEntry(BaseModel):
    """Compatibility matrix entry."""

    provider: str
    platform: Union[str, List[str]]
    architecture: Optional[Union[str, List[str]]] = None
    os_version: Optional[Union[str, List[str]]] = None
    supported: bool
    notes: Optional[str] = None
    tested: Optional[bool] = None
    recommended: Optional[bool] = None


class VersionCompatibility(BaseModel):
    """Version compatibility information."""

    latest: Optional[str] = None
    minimum: Optional[str] = None
    latest_lts: Optional[str] = None
    latest_minimum: Optional[str] = None


class Compatibility(BaseModel):
    """Compatibility information."""

    matrix: Optional[List[CompatibilityEntry]] = None
    versions: Optional[VersionCompatibility] = None


class SaiData(BaseModel):
    """Complete SaiData structure."""

    version: str = Field(pattern=r"^\d+\.\d+(\.\d+)?$")
    metadata: Metadata
    packages: Optional[List[Package]] = None
    services: Optional[List[Service]] = None
    files: Optional[List[File]] = None
    directories: Optional[List[Directory]] = None
    commands: Optional[List[Command]] = None
    ports: Optional[List[Port]] = None
    containers: Optional[List[Container]] = None
    sources: Optional[List[Source]] = None
    binaries: Optional[List[Binary]] = None
    scripts: Optional[List[Script]] = None
    providers: Optional[Dict[str, ProviderConfig]] = None
    compatibility: Optional[Compatibility] = None

    model_config = ConfigDict(use_enum_values=True)
