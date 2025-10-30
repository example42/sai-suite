"""Tests for PlatformResult model."""

import pytest
from saitest.models.state import PlatformResult
from saitest.models.observation import Observation


def test_platform_result_creation():
    """Test creating a PlatformResult with required fields."""
    result = PlatformResult(
        platform="ubuntu:22.04",
        provider="apt",
        success=True,
        duration=45.2
    )
    
    assert result.platform == "ubuntu:22.04"
    assert result.provider == "apt"
    assert result.success is True
    assert result.duration == 45.2
    assert result.observations == []
    assert result.errors == []


def test_platform_result_with_observations():
    """Test creating a PlatformResult with observations."""
    obs1 = Observation(
        type="file",
        platform="ubuntu:22.04",
        provider="apt",
        data={"path": "/usr/bin/nginx"}
    )
    obs2 = Observation(
        type="service",
        platform="ubuntu:22.04",
        provider="apt",
        data={"path": "/lib/systemd/system/nginx.service"}
    )
    
    result = PlatformResult(
        platform="ubuntu:22.04",
        provider="apt",
        success=True,
        observations=[obs1, obs2],
        duration=45.2
    )
    
    assert len(result.observations) == 2
    assert result.observations[0].type == "file"
    assert result.observations[1].type == "service"


def test_platform_result_with_errors():
    """Test creating a failed PlatformResult with errors."""
    result = PlatformResult(
        platform="debian:12",
        provider="pip",
        success=False,
        errors=["Package not found in pip repository"],
        duration=12.5
    )
    
    assert result.success is False
    assert len(result.errors) == 1
    assert result.errors[0] == "Package not found in pip repository"


def test_platform_result_json_serialization():
    """Test that PlatformResult can be serialized to JSON."""
    obs = Observation(
        type="file",
        platform="ubuntu:22.04",
        provider="apt",
        data={"path": "/usr/bin/nginx"}
    )
    
    result = PlatformResult(
        platform="ubuntu:22.04",
        provider="apt",
        success=True,
        observations=[obs],
        errors=[],
        duration=45.2
    )
    
    json_data = result.model_dump()
    
    assert json_data["platform"] == "ubuntu:22.04"
    assert json_data["provider"] == "apt"
    assert json_data["success"] is True
    assert len(json_data["observations"]) == 1
    assert json_data["duration"] == 45.2
