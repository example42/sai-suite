"""Tests for workflow orchestrator."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from saitest.core.orchestrator import (
    run_verification,
    create_verification_workflow,
    route_to_platforms,
    check_more_combinations,
    route_after_quality_check
)
from saitest.core.state import create_initial_state
from saitest.models.state import PlatformResult


def test_run_verification_basic():
    """Test run_verification function with basic parameters."""
    # Mock the workflow to avoid actual execution
    with patch('saitest.core.orchestrator.create_verification_workflow') as mock_create_workflow:
        # Create a mock workflow that returns a state
        mock_workflow = MagicMock()
        mock_final_state = create_initial_state(software="nginx")
        mock_final_state["overall_confidence"] = 0.8
        mock_final_state["platform_results"] = []
        mock_workflow.invoke.return_value = mock_final_state
        mock_create_workflow.return_value = mock_workflow
        
        # Call run_verification
        result = run_verification(software="nginx")
        
        # Verify the workflow was created and invoked
        mock_create_workflow.assert_called_once()
        mock_workflow.invoke.assert_called_once()
        
        # Verify result structure
        assert result["software"] == "nginx"
        assert result["overall_confidence"] == 0.8
        assert isinstance(result["platform_results"], list)


def test_run_verification_with_platforms():
    """Test run_verification with specified platforms."""
    platforms = ["ubuntu:22.04", "debian:12"]
    
    with patch('saitest.core.orchestrator.create_verification_workflow') as mock_create_workflow:
        mock_workflow = MagicMock()
        mock_final_state = create_initial_state(
            software="nginx",
            target_platforms=platforms
        )
        mock_workflow.invoke.return_value = mock_final_state
        mock_create_workflow.return_value = mock_workflow
        
        result = run_verification(software="nginx", platforms=platforms)
        
        # Verify platforms were passed to initial state
        assert result["target_platforms"] == platforms


def test_run_verification_with_config():
    """Test run_verification with custom configuration."""
    config = {
        "max_retries": 5,
        "checkpoint_dir": "/tmp/checkpoints"
    }
    
    with patch('saitest.core.orchestrator.create_verification_workflow') as mock_create_workflow:
        mock_workflow = MagicMock()
        mock_final_state = create_initial_state(software="nginx", max_retries=5)
        mock_workflow.invoke.return_value = mock_final_state
        mock_create_workflow.return_value = mock_workflow
        
        result = run_verification(software="nginx", config=config)
        
        # Verify max_retries was set
        assert result["max_retries"] == 5
        
        # Verify checkpoint_dir was passed to workflow creation
        mock_create_workflow.assert_called_once_with(checkpoint_dir="/tmp/checkpoints")


def test_run_verification_error_handling():
    """Test run_verification handles workflow errors gracefully."""
    with patch('saitest.core.orchestrator.create_verification_workflow') as mock_create_workflow:
        mock_workflow = MagicMock()
        mock_workflow.invoke.side_effect = Exception("Workflow failed")
        mock_create_workflow.return_value = mock_workflow
        
        result = run_verification(software="nginx")
        
        # Verify error state is returned
        assert result["overall_confidence"] == 0.0
        assert result["needs_human_review"] is True
        assert any("Workflow failed" in msg for msg in result["messages"])


def test_route_to_platforms_with_combinations():
    """Test routing to platforms when combinations exist."""
    state = create_initial_state(software="nginx")
    state["provider_combinations"] = [
        ("ubuntu:22.04", "apt"),
        ("debian:12", "apt")
    ]
    
    result = route_to_platforms(state)
    
    assert result == "installation"
    assert state["current_platform"] == "ubuntu:22.04"
    assert state["current_provider"] == "apt"


def test_route_to_platforms_without_combinations():
    """Test routing to analysis when no combinations exist."""
    state = create_initial_state(software="nginx")
    state["provider_combinations"] = []
    
    result = route_to_platforms(state)
    
    assert result == "analysis"


def test_check_more_combinations_with_remaining():
    """Test checking for more combinations when some remain."""
    state = create_initial_state(software="nginx")
    state["provider_combinations"] = [
        ("ubuntu:22.04", "apt"),
        ("debian:12", "apt")
    ]
    
    # Simulate one combination tested
    result1 = PlatformResult(
        platform="ubuntu:22.04",
        provider="apt",
        success=True,
        observations=[],
        errors=[],
        duration=10.0
    )
    state["platform_results"] = [result1]
    
    result = check_more_combinations(state)
    
    assert result == "installation"
    assert state["current_platform"] == "debian:12"
    assert state["current_provider"] == "apt"


def test_check_more_combinations_all_tested():
    """Test checking for more combinations when all are tested."""
    state = create_initial_state(software="nginx")
    state["provider_combinations"] = [
        ("ubuntu:22.04", "apt"),
        ("debian:12", "apt")
    ]
    
    # Simulate both combinations tested
    result1 = PlatformResult(
        platform="ubuntu:22.04",
        provider="apt",
        success=True,
        observations=[],
        errors=[],
        duration=10.0
    )
    result2 = PlatformResult(
        platform="debian:12",
        provider="apt",
        success=True,
        observations=[],
        errors=[],
        duration=12.0
    )
    state["platform_results"] = [result1, result2]
    
    result = check_more_combinations(state)
    
    assert result == "analysis"


def test_route_after_quality_check_high_confidence():
    """Test routing after quality check with high confidence."""
    state = create_initial_state(software="nginx")
    state["overall_confidence"] = 0.8
    
    result = route_after_quality_check(state)
    
    assert result == "end"


def test_route_after_quality_check_low_confidence_retry():
    """Test routing after quality check with low confidence and retries available."""
    state = create_initial_state(software="nginx")
    state["overall_confidence"] = 0.3
    state["retry_count"] = 0
    state["max_retries"] = 2
    
    result = route_after_quality_check(state)
    
    assert result == "retry"
    assert state["retry_count"] == 1


def test_route_after_quality_check_max_retries_reached():
    """Test routing after quality check when max retries reached."""
    state = create_initial_state(software="nginx")
    state["overall_confidence"] = 0.3
    state["retry_count"] = 2
    state["max_retries"] = 2
    
    result = route_after_quality_check(state)
    
    assert result == "end"
    assert any("Max retries reached" in msg for msg in state["messages"])


def test_create_verification_workflow():
    """Test creating the verification workflow."""
    workflow = create_verification_workflow()
    
    # Verify workflow is created (basic check)
    assert workflow is not None
