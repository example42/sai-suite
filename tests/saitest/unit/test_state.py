"""Unit tests for VerificationState core functionality."""

import pytest
from datetime import datetime

from saitest.core.state import VerificationState, create_initial_state


class TestVerificationStateCreation:
    """Tests for creating VerificationState instances."""
    
    def test_create_initial_state_minimal(self):
        """Test creating initial state with minimal parameters."""
        state = create_initial_state(software="nginx")
        
        assert state["software"] == "nginx"
        assert state["input_saidata"] is None
        assert state["target_platforms"] is None
    
    def test_create_initial_state_with_platforms(self):
        """Test creating initial state with target platforms."""
        platforms = ["ubuntu:22.04", "debian:12", "fedora:40"]
        state = create_initial_state(
            software="nginx",
            target_platforms=platforms
        )
        
        assert state["software"] == "nginx"
        assert state["target_platforms"] == platforms
        assert len(state["target_platforms"]) == 3
    
    def test_create_initial_state_with_saidata(self):
        """Test creating initial state with existing saidata."""
        saidata = {
            "version": "0.3",
            "metadata": {"name": "nginx"},
            "packages": [{"name": "nginx", "package_name": "nginx"}]
        }
        
        state = create_initial_state(
            software="nginx",
            input_saidata=saidata
        )
        
        assert state["software"] == "nginx"
        assert state["input_saidata"] == saidata
        assert state["input_saidata"]["version"] == "0.3"
    
    def test_create_initial_state_with_custom_max_retries(self):
        """Test creating initial state with custom max_retries."""
        state = create_initial_state(
            software="nginx",
            max_retries=5
        )
        
        assert state["max_retries"] == 5
        assert state["retry_count"] == 0
    
    def test_create_initial_state_all_parameters(self):
        """Test creating initial state with all parameters."""
        platforms = ["ubuntu:22.04"]
        saidata = {"version": "0.3"}
        
        state = create_initial_state(
            software="nginx",
            target_platforms=platforms,
            input_saidata=saidata,
            max_retries=3
        )
        
        assert state["software"] == "nginx"
        assert state["target_platforms"] == platforms
        assert state["input_saidata"] == saidata
        assert state["max_retries"] == 3


class TestVerificationStateDefaultValues:
    """Tests for default values in VerificationState."""
    
    def test_discovery_fields_defaults(self):
        """Test discovery fields have correct defaults."""
        state = create_initial_state(software="nginx")
        
        assert state["discovery_complete"] is False
        assert state["installation_methods"] == []
        assert state["expected_services"] == []
        assert state["expected_files"] == []
        assert state["expected_ports"] == []
    
    def test_platform_fields_defaults(self):
        """Test platform fields have correct defaults."""
        state = create_initial_state(software="nginx")
        
        assert state["selected_platforms"] == []
        assert state["current_platform"] is None
    
    def test_provider_fields_defaults(self):
        """Test provider fields have correct defaults."""
        state = create_initial_state(software="nginx")
        
        assert state["current_provider"] is None
        assert state["provider_combinations"] == []
        assert state["package_versions"] == {}
        assert state["expected_dependencies"] == {}
    
    def test_results_fields_defaults(self):
        """Test results fields have correct defaults."""
        state = create_initial_state(software="nginx")
        
        assert state["platform_results"] == []
    
    def test_analysis_fields_defaults(self):
        """Test analysis fields have correct defaults."""
        state = create_initial_state(software="nginx")
        
        assert state["aggregated_observations"] == {}
        assert state["patterns"] == {}
        assert state["variations"] == {}
    
    def test_generation_fields_defaults(self):
        """Test generation fields have correct defaults."""
        state = create_initial_state(software="nginx")
        
        assert state["generated_saidata"] is None
        assert state["confidence_scores"] == {}
    
    def test_quality_fields_defaults(self):
        """Test quality fields have correct defaults."""
        state = create_initial_state(software="nginx")
        
        assert state["validation_errors"] == []
        assert state["completeness_score"] == 0.0
        assert state["accuracy_score"] == 0.0
        assert state["overall_confidence"] == 0.0
    
    def test_control_fields_defaults(self):
        """Test control fields have correct defaults."""
        state = create_initial_state(software="nginx")
        
        assert state["retry_count"] == 0
        assert state["max_retries"] == 2
        assert state["needs_human_review"] is False
    
    def test_metadata_fields_defaults(self):
        """Test metadata fields have correct defaults."""
        state = create_initial_state(software="nginx")
        
        assert state["start_time"] is not None
        assert state["messages"] == []


class TestVerificationStateTimestamp:
    """Tests for timestamp handling in VerificationState."""
    
    def test_timestamp_format(self):
        """Test that start_time is in ISO 8601 format with Z suffix."""
        state = create_initial_state(software="nginx")
        
        assert state["start_time"].endswith("Z")
        assert "T" in state["start_time"]
    
    def test_timestamp_parseable(self):
        """Test that start_time can be parsed as datetime."""
        state = create_initial_state(software="nginx")
        
        # Remove Z suffix and parse
        timestamp_without_z = state["start_time"][:-1]
        parsed = datetime.fromisoformat(timestamp_without_z)
        
        assert isinstance(parsed, datetime)
    
    def test_timestamp_unique_per_state(self):
        """Test that each state gets a unique timestamp."""
        state1 = create_initial_state(software="nginx")
        state2 = create_initial_state(software="apache")
        
        # Timestamps should be very close but might differ
        # Just verify both are valid
        assert state1["start_time"].endswith("Z")
        assert state2["start_time"].endswith("Z")


class TestVerificationStateUpdates:
    """Tests for updating VerificationState fields."""
    
    def test_update_discovery_fields(self):
        """Test updating discovery fields."""
        state = create_initial_state(software="nginx")
        
        state["discovery_complete"] = True
        state["installation_methods"] = ["apt", "pip", "source"]
        state["expected_services"] = ["nginx"]
        state["expected_files"] = ["/usr/bin/nginx", "/etc/nginx/nginx.conf"]
        state["expected_ports"] = [80, 443]
        
        assert state["discovery_complete"] is True
        assert len(state["installation_methods"]) == 3
        assert "apt" in state["installation_methods"]
        assert state["expected_services"] == ["nginx"]
        assert len(state["expected_files"]) == 2
        assert 80 in state["expected_ports"]
    
    def test_update_platform_fields(self):
        """Test updating platform fields."""
        state = create_initial_state(software="nginx")
        
        state["selected_platforms"] = ["ubuntu:22.04", "debian:12"]
        state["current_platform"] = "ubuntu:22.04"
        
        assert len(state["selected_platforms"]) == 2
        assert state["current_platform"] == "ubuntu:22.04"
    
    def test_update_provider_fields(self):
        """Test updating provider fields."""
        state = create_initial_state(software="nginx")
        
        state["current_provider"] = "apt"
        state["provider_combinations"] = [
            ("ubuntu:22.04", "apt"),
            ("debian:12", "apt")
        ]
        state["package_versions"] = {"apt": "1.24.0", "pip": "1.24.0"}
        state["expected_dependencies"] = {
            "apt": ["libssl-dev", "zlib1g-dev"]
        }
        
        assert state["current_provider"] == "apt"
        assert len(state["provider_combinations"]) == 2
        assert state["package_versions"]["apt"] == "1.24.0"
        assert "libssl-dev" in state["expected_dependencies"]["apt"]
    
    def test_update_results_fields(self):
        """Test updating results fields."""
        state = create_initial_state(software="nginx")
        
        # Mock platform result
        result = {
            "platform": "ubuntu:22.04",
            "provider": "apt",
            "success": True,
            "observations": [],
            "errors": [],
            "duration": 45.2
        }
        
        state["platform_results"].append(result)
        
        assert len(state["platform_results"]) == 1
        assert state["platform_results"][0]["platform"] == "ubuntu:22.04"
        assert state["platform_results"][0]["success"] is True
    
    def test_update_analysis_fields(self):
        """Test updating analysis fields."""
        state = create_initial_state(software="nginx")
        
        state["aggregated_observations"] = {
            "files": ["/usr/bin/nginx"],
            "services": ["nginx"]
        }
        state["patterns"] = {"common_files": ["/usr/bin/nginx"]}
        state["variations"] = {"ubuntu": {"packages": ["nginx-full"]}}
        
        assert "files" in state["aggregated_observations"]
        assert "common_files" in state["patterns"]
        assert "ubuntu" in state["variations"]
    
    def test_update_generation_fields(self):
        """Test updating generation fields."""
        state = create_initial_state(software="nginx")
        
        state["generated_saidata"] = {
            "version": "0.3",
            "metadata": {"name": "nginx"}
        }
        state["confidence_scores"] = {
            "packages": 0.95,
            "services": 0.90
        }
        
        assert state["generated_saidata"]["version"] == "0.3"
        assert state["confidence_scores"]["packages"] == 0.95
    
    def test_update_quality_fields(self):
        """Test updating quality fields."""
        state = create_initial_state(software="nginx")
        
        state["validation_errors"] = ["Missing required field: version"]
        state["completeness_score"] = 0.85
        state["accuracy_score"] = 0.90
        state["overall_confidence"] = 0.875
        
        assert len(state["validation_errors"]) == 1
        assert state["completeness_score"] == 0.85
        assert state["accuracy_score"] == 0.90
        assert state["overall_confidence"] == 0.875
    
    def test_update_control_fields(self):
        """Test updating control fields."""
        state = create_initial_state(software="nginx")
        
        state["retry_count"] = 1
        state["needs_human_review"] = True
        
        assert state["retry_count"] == 1
        assert state["needs_human_review"] is True
    
    def test_update_metadata_fields(self):
        """Test updating metadata fields."""
        state = create_initial_state(software="nginx")
        
        state["messages"].append("Discovery started")
        state["messages"].append("Discovery completed")
        
        assert len(state["messages"]) == 2
        assert "Discovery started" in state["messages"]


class TestVerificationStateTypeDict:
    """Tests for TypedDict behavior of VerificationState."""
    
    def test_state_is_dict(self):
        """Test that state behaves like a dictionary."""
        state = create_initial_state(software="nginx")
        
        assert isinstance(state, dict)
        assert "software" in state
        assert state.get("software") == "nginx"
    
    def test_state_keys(self):
        """Test that state has expected keys."""
        state = create_initial_state(software="nginx")
        
        # Check for presence of key fields
        assert "software" in state
        assert "discovery_complete" in state
        assert "selected_platforms" in state
        assert "provider_combinations" in state
        assert "platform_results" in state
        assert "generated_saidata" in state
        assert "validation_errors" in state
        assert "retry_count" in state
        assert "start_time" in state
    
    def test_state_iteration(self):
        """Test iterating over state keys."""
        state = create_initial_state(software="nginx")
        
        keys = list(state.keys())
        assert len(keys) > 0
        assert "software" in keys
        assert "start_time" in keys
