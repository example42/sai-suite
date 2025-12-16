"""Integration tests for full saitest workflow.

These tests verify the complete workflow with real Docker containers,
testing actual software installations and saidata generation.

Note: These tests are marked as integration tests and can be skipped
with --no-integration flag. Full integration tests require Docker and LLM API access.
"""

import pytest
from pathlib import Path

from saitest.core.orchestrator import run_verification
from saitest.core.state import create_initial_state


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestWorkflowBasic:
    """Basic integration tests for workflow structure."""
    
    def test_workflow_can_be_invoked(self):
        """Test that workflow can be created and invoked without crashing."""
        # This test verifies the workflow structure is valid
        # It will fail at agent execution due to missing LLM/Docker, but that's expected
        
        result = run_verification(
            software="nginx",
            platforms=["ubuntu:22.04"]
        )
        
        # Verify basic structure exists
        assert result is not None
        assert result["software"] == "nginx"
        assert "messages" in result
        assert "platform_results" in result
        assert isinstance(result["overall_confidence"], (int, float))
    
    def test_state_initialization(self):
        """Test that initial state is properly created."""
        state = create_initial_state(
            software="nginx",
            target_platforms=["ubuntu:22.04"],
            max_retries=3
        )
        
        # Verify all required fields are present
        assert state["software"] == "nginx"
        assert state["target_platforms"] == ["ubuntu:22.04"]
        assert state["max_retries"] == 3
        assert state["retry_count"] == 0
        assert state["discovery_complete"] is False
        assert state["overall_confidence"] == 0.0
        assert isinstance(state["messages"], list)
        assert isinstance(state["platform_results"], list)


class TestWorkflowWithRealContainers:
    """Integration tests with real Docker containers (requires Docker)."""
    
    @pytest.mark.slow
    @pytest.mark.requires_system
    def test_nginx_installation_ubuntu(self):
        """Test nginx installation on Ubuntu with real container.
        
        This test requires:
        - Docker installed and running
        - LLM API key configured (OPENAI_API_KEY or ANTHROPIC_API_KEY)
        - Internet connection for pulling Docker images
        
        Skip this test in CI unless explicitly enabled.
        """
        pytest.skip("Requires Docker, LLM API, and is slow - enable manually for full integration testing")
        
        # Run actual verification
        result = run_verification(
            software="nginx",
            platforms=["ubuntu:22.04"]
        )
        
        # Verify results
        assert result is not None
        assert result["software"] == "nginx"
        assert len(result["platform_results"]) > 0
        
        # Check that observations were collected
        for platform_result in result["platform_results"]:
            assert platform_result.platform == "ubuntu:22.04"
            # Should have some observations (files, services, etc.) if successful
            if platform_result.success:
                assert len(platform_result.observations) > 0


class TestWorkflowErrorScenarios:
    """Test error handling in various scenarios."""
    
    def test_workflow_with_invalid_config(self):
        """Test workflow handles invalid configuration gracefully."""
        # Test with invalid max_retries
        result = run_verification(
            software="nginx",
            platforms=["ubuntu:22.04"],
            config={"max_retries": -1}  # Invalid value
        )
        
        # Should handle gracefully
        assert result is not None
        assert result["software"] == "nginx"
    
    def test_workflow_with_empty_platforms(self):
        """Test workflow with empty platform list."""
        result = run_verification(
            software="nginx",
            platforms=[]
        )
        
        # Should complete but may have low confidence
        assert result is not None
        assert result["software"] == "nginx"


class TestWorkflowStateManagement:
    """Test state management throughout the workflow."""
    
    def test_state_has_all_required_fields(self):
        """Test that state contains all required fields."""
        state = create_initial_state(software="test")
        
        # Input fields
        assert "software" in state
        assert "input_saidata" in state
        assert "target_platforms" in state
        
        # Discovery fields
        assert "discovery_complete" in state
        assert "installation_methods" in state
        assert "expected_services" in state
        assert "expected_files" in state
        assert "expected_ports" in state
        
        # Platform fields
        assert "selected_platforms" in state
        assert "current_platform" in state
        
        # Provider fields
        assert "current_provider" in state
        assert "provider_combinations" in state
        assert "package_versions" in state
        assert "expected_dependencies" in state
        
        # Results fields
        assert "platform_results" in state
        
        # Analysis fields
        assert "aggregated_observations" in state
        assert "patterns" in state
        assert "variations" in state
        
        # Generation fields
        assert "generated_saidata" in state
        assert "confidence_scores" in state
        
        # Quality fields
        assert "validation_errors" in state
        assert "completeness_score" in state
        assert "accuracy_score" in state
        assert "overall_confidence" in state
        
        # Control fields
        assert "retry_count" in state
        assert "max_retries" in state
        assert "needs_human_review" in state
        
        # Metadata fields
        assert "start_time" in state
        assert "messages" in state


# Note: More comprehensive integration tests would require:
# 1. Mock LLM responses for predictable testing
# 2. Mock Docker containers to avoid actual container operations
# 3. Test fixtures for known software packages
# 4. Validation of generated saidata against schema
#
# These are intentionally kept minimal to focus on workflow structure
# and basic error handling. Full integration testing should be done
# manually or in a dedicated CI environment with Docker and LLM access.
