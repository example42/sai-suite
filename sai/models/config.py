"""Configuration models for sai CLI tool."""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class RepositoryAuthType(str, Enum):
    """Repository authentication types."""

    SSH = "ssh"
    TOKEN = "token"
    BASIC = "basic"


class SaiConfig(BaseModel):
    """Main sai CLI configuration."""

    # Core settings
    config_version: str = "0.1.0"
    log_level: LogLevel = LogLevel.INFO
    log_file: Optional[Path] = Field(
        default_factory=lambda: Path.home() / ".sai" / "logs" / "sai.log"
    )

    # CLI-specific settings
    provider_priorities: Dict[str, int] = Field(default_factory=dict)
    saidata_paths: List[str] = Field(
        default_factory=lambda: [
            str(Path.home() / ".sai" / "cache" / "repositories" / "saidata-main"),
            str(Path.home() / ".sai" / "saidata"),
            "/usr/local/share/sai/saidata",
            "/usr/share/sai/saidata",
        ]
    )
    provider_paths: List[str] = Field(
        default_factory=lambda: [
            "providers",
            str(Path.home() / ".sai" / "providers"),
            "/usr/local/share/sai/providers",
            "/usr/share/sai/providers",
        ]
    )
    cache_enabled: bool = True
    cache_directory: Path = Path.home() / ".sai" / "cache"
    cache_ttl: int = 3600  # seconds
    default_provider: Optional[str] = None

    # Repository settings
    saidata_repository_url: str = "https://github.com/example42/saidata"
    saidata_repository_branch: str = "main"
    saidata_repository_auth_type: Optional[RepositoryAuthType] = None
    saidata_repository_auth_data: Optional[Dict[str, str]] = Field(default_factory=dict)
    saidata_auto_update: bool = True
    saidata_update_interval: int = 86400  # 24 hours in seconds
    saidata_offline_mode: bool = False
    saidata_repository_cache_dir: Optional[Path] = None  # Defaults to cache_directory/repositories
    saidata_shallow_clone: bool = True
    saidata_repository_timeout: int = 300  # seconds

    # Security settings
    saidata_verify_signatures: bool = True
    saidata_require_checksums: bool = False
    saidata_security_level: str = "moderate"  # strict, moderate, permissive
    saidata_allow_insecure_urls: bool = False

    # Advanced settings
    max_concurrent_actions: int = 3
    action_timeout: int = 300  # seconds
    require_confirmation: bool = True
    dry_run_default: bool = False

    model_config = ConfigDict(validate_assignment=True)

    @model_validator(mode="after")
    def set_default_repository_cache_dir(self):
        """Set default repository cache directory if not specified."""
        if self.saidata_repository_cache_dir is None:
            self.saidata_repository_cache_dir = self.cache_directory / "repositories"
        return self

    @field_validator("saidata_repository_url")
    @classmethod
    def validate_repository_url(cls, v):
        """Validate repository URL format."""
        if not v:
            raise ValueError("Repository URL cannot be empty")

        # Basic URL validation - should start with http/https or git protocols
        valid_prefixes = ("http://", "https://", "git://", "ssh://", "git@")
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Invalid repository URL format: {v}")

        return v

    @field_validator("saidata_update_interval")
    @classmethod
    def validate_update_interval(cls, v):
        """Validate update interval is reasonable."""
        if v < 60:  # Minimum 1 minute
            raise ValueError("Update interval must be at least 60 seconds")
        if v > 604800:  # Maximum 1 week
            raise ValueError("Update interval cannot exceed 604800 seconds (1 week)")
        return v

    @field_validator("saidata_repository_timeout")
    @classmethod
    def validate_repository_timeout(cls, v):
        """Validate repository timeout is reasonable."""
        if v < 10:  # Minimum 10 seconds
            raise ValueError("Repository timeout must be at least 10 seconds")
        if v > 3600:  # Maximum 1 hour
            raise ValueError("Repository timeout cannot exceed 3600 seconds (1 hour)")
        return v

    @field_validator("saidata_security_level")
    @classmethod
    def validate_security_level(cls, v):
        """Validate security level is valid."""
        valid_levels = ["strict", "moderate", "permissive"]
        if v.lower() not in valid_levels:
            raise ValueError(f"Security level must be one of: {', '.join(valid_levels)}")
        return v.lower()
