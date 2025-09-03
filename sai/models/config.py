"""Configuration models for sai CLI tool."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from pathlib import Path
from enum import Enum


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SaiConfig(BaseModel):
    """Main sai CLI configuration."""
    # Core settings
    config_version: str = "0.1.0"
    log_level: LogLevel = LogLevel.INFO
    log_file: Optional[Path] = None
    
    # CLI-specific settings
    provider_priorities: Dict[str, int] = Field(default_factory=dict)
    saidata_paths: List[str] = Field(default_factory=lambda: [
        ".",
        str(Path.home() / ".sai" / "saidata"),
        "/usr/local/share/sai/saidata",
        "/usr/share/sai/saidata"
    ])
    provider_paths: List[str] = Field(default_factory=lambda: [
        "providers",
        str(Path.home() / ".sai" / "providers"),
        "/usr/local/share/sai/providers",
        "/usr/share/sai/providers"
    ])
    cache_enabled: bool = True
    cache_directory: Path = Path.home() / ".sai" / "cache"
    cache_ttl: int = 3600  # seconds
    default_provider: Optional[str] = None
    
    # Advanced settings
    max_concurrent_actions: int = 3
    action_timeout: int = 300  # seconds
    require_confirmation: bool = True
    dry_run_default: bool = False
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        use_enum_values = True