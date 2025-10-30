"""Observation data model for saitest.

This module defines the Observation model that represents a single data point
collected during software installation monitoring.
"""

from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field


class Observation(BaseModel):
    """Single data point collected during software installation.
    
    Observations represent system changes detected during installation,
    such as files created, services registered, ports opened, etc.
    
    Attributes:
        type: Type of observation (file, service, port, command, package)
        platform: Platform identifier (e.g., "ubuntu:22.04")
        provider: Provider used for installation (e.g., "apt", "pip", "source")
        timestamp: ISO 8601 timestamp when observation was made
        data: Dictionary containing observation-specific data
        confidence: Confidence score for this observation (0.0 to 1.0)
    """
    
    type: str = Field(
        ...,
        description="Type of observation (file, service, port, command, package)"
    )
    platform: str = Field(
        ...,
        description="Platform identifier (e.g., 'ubuntu:22.04')"
    )
    provider: str = Field(
        ...,
        description="Provider used for installation (e.g., 'apt', 'pip', 'source')"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 timestamp when observation was made"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Observation-specific data (e.g., {'path': '/usr/bin/nginx'})"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for this observation (0.0 to 1.0)"
    )
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "examples": [
                {
                    "type": "file",
                    "platform": "ubuntu:22.04",
                    "provider": "apt",
                    "timestamp": "2025-10-30T10:30:00Z",
                    "data": {"path": "/usr/bin/nginx"},
                    "confidence": 1.0
                },
                {
                    "type": "service",
                    "platform": "ubuntu:22.04",
                    "provider": "apt",
                    "timestamp": "2025-10-30T10:30:00Z",
                    "data": {"path": "/lib/systemd/system/nginx.service"},
                    "confidence": 0.9
                },
                {
                    "type": "port",
                    "platform": "debian:12",
                    "provider": "apt",
                    "timestamp": "2025-10-30T10:30:00Z",
                    "data": {"port": 80, "protocol": "tcp"},
                    "confidence": 0.8
                }
            ]
        }
