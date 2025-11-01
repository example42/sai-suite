"""Tests to verify fixture integrity and usability."""

import pytest
import json
import yaml
from pathlib import Path

from saitest.models.observation import Observation
from saitest.models.state import PlatformResult
from saitest.core.state import VerificationState

from .sample_observations import (
    FILE_OBSERVATION_NGINX_BINARY,
    SERVICE_OBSERVATION_NGINX,
    PORT_OBSERVATION_HTTP,
    NGINX_OBSERVATIONS_APT,
    ALL_OBSERVATIONS
)
from .sample_states import (
    SAMPLE_STATES,
    create_initial_state,
    create_discovery_complete_state,
    create_quality_check_complete_state
)


class TestSampleObservations:
    """Test sample observation fixtures."""
    
    def test_file_observation_structure(self):
        """Test that file observation has correct structure."""
        assert FILE_OBSERVATION_NGINX_BINARY.type == "file"
        assert FILE_OBSERVATION_NGINX_BINARY.platform == "ubuntu:22.04"
        assert FILE_OBSERVATION_NGINX_BINARY.provider == "apt"
        assert "path" in FILE_OBSERVATION_NGINX_BINARY.data
        assert FILE_OBSERVATION_NGINX_BINARY.confidence == 1.0
    
    def test_service_observation_structure(self):
        """Test that service observation has correct structure."""
        assert SERVICE_OBSERVATION_NGINX.type == "service"
        assert "path" in SERVICE_OBSERVATION_NGINX.data
        assert "name" in SERVICE_OBSERVATION_NGINX.data
    
    def test_port_observation_structure(self):
        """Test that port observation has correct structure."""
        assert PORT_OBSERVATION_HTTP.type == "port"
        assert "port" in PORT_OBSERVATION_HTTP.data
        assert "protocol" in PORT_OBSERVATION_HTTP.data
    
    def test_nginx_observations_apt_list(self):
        """Test that nginx apt observations list is valid."""
        assert len(NGINX_OBSERVATIONS_APT) > 0
        assert all(isinstance(obs, Observation) for obs in NGINX_OBSERVATIONS_APT)
        assert all(obs.provider == "apt" for obs in NGINX_OBSERVATIONS_APT)
    
    def test_all_observations_list(self):
        """Test that all observations list is valid."""
        assert len(ALL_OBSERVATIONS) > 0
        assert all(isinstance(obs, Observation) for obs in ALL_OBSERVATIONS)
        
        # Check we have multiple types
        types = {obs.type for obs in ALL_OBSERVATIONS}
        assert "file" in types
        assert "service" in types
        assert "port" in types


class TestSampleStates:
    """Test sample state fixtures."""
    
    def test_initial_state(self):
        """Test initial state fixture."""
        state = SAMPLE_STATES["initial"]
        assert state["software"] == "nginx"
        assert state["discovery_complete"] is False
        assert state["retry_count"] == 0
    
    def test_discovery_complete_state(self):
        """Test discovery complete state fixture."""
        state = SAMPLE_STATES["discovery_complete"]
        assert state["discovery_complete"] is True
        assert len(state["installation_methods"]) > 0
        assert len(state["expected_services"]) > 0
    
    def test_platform_selected_state(self):
        """Test platform selected state fixture."""
        state = SAMPLE_STATES["platform_selected"]
        assert len(state["selected_platforms"]) > 0
        assert len(state["provider_combinations"]) > 0
        assert state["current_platform"] is not None
        assert state["current_provider"] is not None
    
    def test_installation_complete_state(self):
        """Test installation complete state fixture."""
        state = SAMPLE_STATES["installation_complete"]
        assert len(state["platform_results"]) > 0
        
        # Verify platform results are valid
        for result in state["platform_results"]:
            assert isinstance(result, PlatformResult)
            assert result.platform is not None
            assert result.provider is not None
    
    def test_analysis_complete_state(self):
        """Test analysis complete state fixture."""
        state = SAMPLE_STATES["analysis_complete"]
        assert len(state["aggregated_observations"]) > 0
        assert len(state["patterns"]) > 0
        assert len(state["variations"]) > 0
        assert len(state["confidence_scores"]) > 0
    
    def test_generation_complete_state(self):
        """Test generation complete state fixture."""
        state = SAMPLE_STATES["generation_complete"]
        assert state["generated_saidata"] is not None
        assert "default" in state["generated_saidata"]
        assert "overrides" in state["generated_saidata"]
        
        # Verify default saidata structure
        default = state["generated_saidata"]["default"]
        assert "version" in default
        assert "metadata" in default
        assert "packages" in default
    
    def test_quality_check_high_confidence_state(self):
        """Test quality check state with high confidence."""
        state = SAMPLE_STATES["quality_check_high"]
        assert state["overall_confidence"] >= 0.7
        assert state["needs_human_review"] is False
        assert len(state["validation_errors"]) == 0
    
    def test_quality_check_low_confidence_state(self):
        """Test quality check state with low confidence."""
        state = SAMPLE_STATES["quality_check_low"]
        assert state["overall_confidence"] < 0.7
        assert state["needs_human_review"] is True
        assert len(state["validation_errors"]) > 0
    
    def test_failed_installation_state(self):
        """Test failed installation state fixture."""
        state = SAMPLE_STATES["failed_installation"]
        assert len(state["platform_results"]) > 0
        
        # At least one result should be failed
        failed_results = [r for r in state["platform_results"] if not r.success]
        assert len(failed_results) > 0
        assert len(failed_results[0].errors) > 0
    
    def test_retry_state(self):
        """Test retry state fixture."""
        state = SAMPLE_STATES["retry"]
        assert state["retry_count"] > 0
        assert state["retry_count"] < state["max_retries"]
    
    def test_max_retries_state(self):
        """Test max retries state fixture."""
        state = SAMPLE_STATES["max_retries"]
        assert state["retry_count"] == state["max_retries"]


class TestSampleSaidata:
    """Test sample saidata YAML fixture."""
    
    def test_saidata_file_exists(self):
        """Test that sample saidata file exists."""
        fixture_path = Path(__file__).parent / "sample_saidata.yaml"
        assert fixture_path.exists()
    
    def test_saidata_is_valid_yaml(self):
        """Test that sample saidata is valid YAML."""
        fixture_path = Path(__file__).parent / "sample_saidata.yaml"
        with open(fixture_path) as f:
            data = yaml.safe_load(f)
        
        assert data is not None
        assert isinstance(data, dict)
    
    def test_saidata_has_required_fields(self):
        """Test that sample saidata has required fields."""
        fixture_path = Path(__file__).parent / "sample_saidata.yaml"
        with open(fixture_path) as f:
            data = yaml.safe_load(f)
        
        assert "version" in data
        assert "metadata" in data
        assert "name" in data["metadata"]
        assert "packages" in data
    
    def test_saidata_has_provider_overrides(self):
        """Test that sample saidata has provider overrides."""
        fixture_path = Path(__file__).parent / "sample_saidata.yaml"
        with open(fixture_path) as f:
            data = yaml.safe_load(f)
        
        assert "providers" in data
        assert len(data["providers"]) > 0


class TestMockLLMResponses:
    """Test mock LLM response fixtures."""
    
    def test_mock_responses_file_exists(self):
        """Test that mock LLM responses file exists."""
        fixture_path = Path(__file__).parent / "mock_llm_responses.json"
        assert fixture_path.exists()
    
    def test_mock_responses_is_valid_json(self):
        """Test that mock responses is valid JSON."""
        fixture_path = Path(__file__).parent / "mock_llm_responses.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        assert data is not None
        assert isinstance(data, dict)
    
    def test_mock_responses_has_agent_sections(self):
        """Test that mock responses has sections for each agent."""
        fixture_path = Path(__file__).parent / "mock_llm_responses.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        expected_agents = [
            "discovery_agent",
            "platform_selection_agent",
            "analysis_agent",
            "generation_agent",
            "quality_check_agent"
        ]
        
        for agent in expected_agents:
            assert agent in data
    
    def test_discovery_agent_responses(self):
        """Test discovery agent mock responses."""
        fixture_path = Path(__file__).parent / "mock_llm_responses.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        discovery = data["discovery_agent"]
        assert "success" in discovery
        assert "installation_methods" in discovery["success"]
        assert "expected_services" in discovery["success"]
    
    def test_quality_check_agent_responses(self):
        """Test quality check agent mock responses."""
        fixture_path = Path(__file__).parent / "mock_llm_responses.json"
        with open(fixture_path) as f:
            data = json.load(f)
        
        quality = data["quality_check_agent"]
        assert "high_quality" in quality
        assert "low_quality" in quality
        
        # High quality should have no errors
        assert len(quality["high_quality"]["validation_errors"]) == 0
        assert quality["high_quality"]["needs_human_review"] is False
        
        # Low quality should have errors
        assert len(quality["low_quality"]["validation_errors"]) > 0
        assert quality["low_quality"]["needs_human_review"] is True
