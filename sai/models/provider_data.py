"""Pydantic models for ProviderData structure."""

from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class ProviderType(str, Enum):
    """Provider types."""
    PACKAGE_MANAGER = "package_manager"
    CONTAINER = "container"
    BINARY = "binary"
    SOURCE = "source"
    CLOUD = "cloud"
    CUSTOM = "custom"
    DEBUG = "debug"
    TRACE = "trace"
    PROFILE = "profile"
    SECURITY = "security"
    SBOM = "sbom"
    TROUBLESHOOT = "troubleshoot"
    NETWORK = "network"
    AUDIT = "audit"
    BACKUP = "backup"
    FILESYSTEM = "filesystem"
    SYSTEM = "system"
    MONITORING = "monitoring"
    IO = "io"
    MEMORY = "memory"
    MONITOR = "monitor"
    PROCESS = "process"


class BackoffType(str, Enum):
    """Backoff types for retry configuration."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class Provider(BaseModel):
    """Provider metadata."""
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    type: ProviderType
    platforms: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    priority: Optional[int] = None
    executable: Optional[str] = None  # Main executable command name for availability detection


class RetryConfig(BaseModel):
    """Retry configuration for actions."""
    attempts: int = 3
    delay: int = 5
    backoff: BackoffType = BackoffType.LINEAR


class Validation(BaseModel):
    """Validation configuration for actions."""
    command: str
    expected_exit_code: int = 0
    expected_output: Optional[str] = None
    timeout: int = 30


class Step(BaseModel):
    """Individual step in a multi-step action."""
    name: Optional[str] = None
    command: str
    condition: Optional[str] = None
    ignore_failure: bool = False
    timeout: Optional[int] = None


class Action(BaseModel):
    """Action definition for providers."""
    description: Optional[str] = None
    template: Optional[str] = None
    command: Optional[str] = None
    script: Optional[str] = None
    steps: Optional[List[Step]] = None
    requires_root: bool = False
    timeout: int = 300
    retry: Optional[RetryConfig] = None
    validation: Optional[Validation] = None
    rollback: Optional[str] = None
    variables: Optional[Dict[str, str]] = None

    model_config = ConfigDict(validate_assignment=True)


class PackageMapping(BaseModel):
    """Package mapping for providers."""
    name: str
    version: Optional[str] = None
    repository: Optional[str] = None
    alternatives: Optional[List[str]] = None
    install_options: Optional[str] = None


class ServiceMapping(BaseModel):
    """Service mapping for providers."""
    name: str
    type: Optional[str] = None
    config_files: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None


class FileMapping(BaseModel):
    """File mapping for providers."""
    path: str
    owner: Optional[str] = None
    group: Optional[str] = None
    mode: Optional[str] = None
    template: Optional[str] = None


class DirectoryMapping(BaseModel):
    """Directory mapping for providers."""
    path: str
    owner: Optional[str] = None
    group: Optional[str] = None
    mode: Optional[str] = None
    create: bool = True


class CommandMapping(BaseModel):
    """Command mapping for providers."""
    path: str
    alternatives: Optional[List[str]] = None
    wrapper: Optional[str] = None


class PortMapping(BaseModel):
    """Port mapping for providers."""
    port: Optional[Union[int, str]] = None
    configurable: bool = True
    config_key: Optional[str] = None


class VariableMapping(BaseModel):
    """Variable mapping for providers."""
    value: Optional[Union[str, int, bool]] = None
    config_key: Optional[str] = None
    environment: Optional[str] = None


class Mappings(BaseModel):
    """Provider mappings for saidata components."""
    packages: Optional[Dict[str, PackageMapping]] = None
    services: Optional[Dict[str, ServiceMapping]] = None
    files: Optional[Dict[str, FileMapping]] = None
    directories: Optional[Dict[str, DirectoryMapping]] = None
    commands: Optional[Dict[str, CommandMapping]] = None
    ports: Optional[Dict[str, PortMapping]] = None
    variables: Optional[Dict[str, Union[VariableMapping, str]]] = None


class ProviderData(BaseModel):
    """Complete ProviderData structure."""
    version: str = Field(pattern=r"^\d+\.\d+(\.\d+)?$")
    provider: Provider
    actions: Dict[str, Action]
    mappings: Optional[Mappings] = None

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid"
    )