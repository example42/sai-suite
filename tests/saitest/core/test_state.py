"""Tests for VerificationState."""

import pytest
from datetime import datetime
from saitest.core.state import VerificationState, create_initial_state


def test_create_initial_state():
    """Test creating an initial VerificationState."""
    state = create_initial_state(software="nginx")
    
    # Input fields
    assert state["software"] == "nginx"
    assert state["input_saidata"] is None
    assert state["target_platforms"] is None
    
    # Discovery fields
    assert state["discovery_complete"] is False
    assert state["installation_methods"] == []
    assert state["expected_services"] == []
    assert state["expected_files"] == []
    assert state["expected_ports"] == []
    
    # Platform fields
    assert state["selected_platforms"] == []
    assert state["current_platform"] is None
    
    # Provider fields
    assert state["current_provider"] is None
    assert state["provider_combinations"] == []
    assert state["package_versions"] == {}
    assert state["expected_dependencies"] == {}
    
    # Results fields
    assert state["platform_results"] == []
    
    # Analysis fields
    assert state["aggregated_observations"] == {}
    assert state["patterns"] == {}
    assert state["variations"] == {}
    
    # Generation fields
    assert state["generated_saidata"] is None
    assert state["confidence_scores"] == {}
    
    # Quality fields
    assert state["validation_errors"] == []
    assert state["completeness_score"] == 0.0
    assert state["accuracy_score"] == 0.0
    assert state["overall_confidence"] == 0.0
    
    # Control fields
    assert state["retry_count"] == 0
    assert state["max_retries"] == 2
    assert state["needs_human_review"] is False
    
    # Metadata fields
    assert state["start_time"] is not None
    assert state["messages"] == []


def test_create_initial_state_with_platforms():
    """Test creating an initial state with target platforms."""
    platforms = ["ubuntu:22.04", "debian:12"]
    state = create_initial_state(
        software="nginx",
        target_platforms=platforms
    )
    
    assert state["software"] == "nginx"
    assert state["target_platforms"] == platforms


def test_create_initial_state_with_custom_max_retries():
    """Test creating an initial state with custom max_retries."""
    state = create_initial_state(
        software="nginx",
        max_retries=5
    )
    
    assert state["max_retries"] == 5


def test_state_timestamp_format():
    """Test that start_time is in ISO 8601 format."""
    state = create_initial_state(software="nginx")
    
    # Verify timestamp ends with Z (UTC indicator)
    assert state["start_time"].endswith("Z")
    
    # Verify timestamp can be parsed
    timestamp_without_z = state["start_time"][:-1]
    parsed = datetime.fromisoformat(timestamp_without_z)
    assert isinstance(parsed, datetime)


def test_state_updates():
    """Test updating state fields."""
    state = create_initial_state(software="nginx")
    
    # Update discovery fields
    state["discovery_complete"] = True
    state["installation_methods"] = ["apt", "pip"]
    state["expected_services"] = ["nginx"]
    
    assert state["discovery_complete"] is True
    assert len(state["installation_methods"]) == 2
    assert state["expected_services"] == ["nginx"]
    
    # Update platform fields
    state["selected_platforms"] = ["ubuntu:22.04", "debian:12"]
    state["current_platform"] = "ubuntu:22.04"
    
    assert len(state["selected_platforms"]) == 2
    assert state["current_platform"] == "ubuntu:22.04"
    
    # Update provider fields
    state["current_provider"] = "apt"
    state["provider_combinations"] = [("ubuntu:22.04", "apt"), ("debian:12", "apt")]
    state["package_versions"] = {"apt": "1.24.0"}
    state["expected_dependencies"] = {"apt": ["libssl-dev"]}
    
    assert state["current_provider"] == "apt"
    assert len(state["provider_combinations"]) == 2
    assert state["package_versions"]["apt"] == "1.24.0"
    assert state["expected_dependencies"]["apt"] == ["libssl-dev"]
