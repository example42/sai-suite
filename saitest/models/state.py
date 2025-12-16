"""State data models for saitest.

This module defines the PlatformResult model that represents the results
from testing one platform with one provider.
"""

from typing import List
from pydantic import BaseModel, Field

from .observation import Observation


class PlatformResult(BaseModel):
    """Results from testing one platform with one provider.
    
    PlatformResult captures all observations, errors, and metadata from
    testing a specific platform-provider combination.
    
    Attributes:
        platform: Platform identifier (e.g., "ubuntu:22.04")
        provider: Provider used for installation (e.g., "apt", "pip", "source")
        success: Whether the installation succeeded
        observations: List of observations collected during installation
        errors: List of error messages encountered
        duration: Time taken for installation in seconds
    """
    
    platform: str = Field(
        ...,
        description="Platform identifier (e.g., 'ubuntu:22.04')"
    )
    provider: str = Field(
        ...,
        description="Provider used for installation (e.g., 'apt', 'pip', 'source')"
    )
    success: bool = Field(
        ...,
        description="Whether the installation succeeded"
    )
    observations: List[Observation] = Field(
        default_factory=list,
        description="List of observations collected during installation"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages encountered"
    )
    duration: float = Field(
        ...,
        description="Time taken for installation in seconds"
    )
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "examples": [
                {
                    "platform": "ubuntu:22.04",
                    "provider": "apt",
                    "success": True,
                    "observations": [
                        {
                            "type": "file",
                            "platform": "ubuntu:22.04",
                            "provider": "apt",
                            "timestamp": "2025-10-30T10:30:00Z",
                            "data": {"path": "/usr/bin/nginx"},
                            "confidence": 1.0
                        }
                    ],
                    "errors": [],
                    "duration": 45.2
                },
                {
                    "platform": "debian:12",
                    "provider": "pip",
                    "success": False,
                    "observations": [],
                    "errors": ["Package not found in pip repository"],
                    "duration": 12.5
                }
            ]
        }
