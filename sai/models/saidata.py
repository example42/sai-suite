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
    """Package definition."""

    name: str
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
    providers: Optional[Dict[str, ProviderConfig]] = None
    compatibility: Optional[Compatibility] = None

    model_config = ConfigDict(use_enum_values=True)
