"""Tests for Observation model."""

import pytest
from datetime import datetime
from saitest.models.observation import Observation


def test_observation_creation():
    """Test creating an Observation with all required fields."""
    obs = Observation(
        type="file",
        platform="ubuntu:22.04",
        provider="apt",
        data={"path": "/usr/bin/nginx"}
    )
    
    assert obs.type == "file"
    assert obs.platform == "ubuntu:22.04"
    assert obs.provider == "apt"
    assert obs.data == {"path": "/usr/bin/nginx"}
    assert obs.confidence == 1.0
    assert obs.timestamp is not None


def test_observation_with_custom_confidence():
    """Test creating an Observation with custom confidence score."""
    obs = Observation(
        type="service",
        platform="debian:12",
        provider="apt",
        data={"path": "/lib/systemd/system/nginx.service"},
        confidence=0.85
    )
    
    assert obs.confidence == 0.85


def test_observation_timestamp_format():
    """Test that timestamp is in ISO 8601 format."""
    obs = Observation(
        type="port",
        platform="ubuntu:22.04",
        provider="apt",
        data={"port": 80, "protocol": "tcp"}
    )
    
    # Verify timestamp ends with Z (UTC indicator)
    assert obs.timestamp.endswith("Z")
    
    # Verify timestamp can be parsed
    timestamp_without_z = obs.timestamp[:-1]
    parsed = datetime.fromisoformat(timestamp_without_z)
    assert isinstance(parsed, datetime)


def test_observation_json_serialization():
    """Test that Observation can be serialized to JSON."""
    obs = Observation(
        type="file",
        platform="ubuntu:22.04",
        provider="apt",
        data={"path": "/usr/bin/nginx"},
        confidence=0.95
    )
    
    json_data = obs.model_dump()
    
    assert json_data["type"] == "file"
    assert json_data["platform"] == "ubuntu:22.04"
    assert json_data["provider"] == "apt"
    assert json_data["data"] == {"path": "/usr/bin/nginx"}
    assert json_data["confidence"] == 0.95
