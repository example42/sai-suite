"""Tests for installation agent."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from saitest.agents.installation import installation_agent, get_next_combination
from saitest.core.state import create_initial_state
from saitest.models.observation import Observation
from saitest.models.state import PlatformResult


@pytest.mark.asyncio
async def test_installation_agent_success():
    """Test installation agent with successful installation."""
    # Create initial state
    state = create_initial_state("nginx")
    state["current_platform"] = "ubuntu:22.04"
    state["current_provider"] = "apt"
    state["provider_combinations"] = [("ubuntu:22.04", "apt")]
    
    # Mock the LLM and tool
    mock_tool_result = {
        "provider": "apt",
        "platform": "ubuntu:22.04",
        "success": True,
        "output": "Installation successful",
        "test_output": "nginx is installed",
        "test_success": True,
        "files_created": ["/usr/bin/nginx", "/etc/nginx/nginx.conf"],
        "services_found": ["/lib/systemd/system/nginx.service"],
        "binaries_found": ["/usr/bin/nginx"],
        "observations": [
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
            }
        ],
        "errors": [],
        "duration": 45.2
    }
    
    # Mock the LLM response with tool call
    mock_response = Mock()
    mock_response.tool_calls = [
        {
            "name": "install_package",
            "args": {
                "platform": "ubuntu:22.04",
                "provider": "apt",
                "package": "nginx"
            }
        }
    ]
    
    with patch("saitest.agents.installation.ChatOpenAI") as mock_llm_class:
        mock_llm = Mock()
        mock_llm_with_tools = AsyncMock()
        mock_llm_with_tools.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = Mock(return_value=mock_llm_with_tools)
        mock_llm_class.return_value = mock_llm
        
        with patch("saitest.agents.installation.install_package") as mock_tool:
            mock_tool.invoke.return_value = mock_tool_result
            
            # Run the agent
            result_state = await installation_agent(state)
    
    # Verify results
    assert len(result_state["platform_results"]) == 1
    
    platform_result = result_state["platform_results"][0]
    assert platform_result.platform == "ubuntu:22.04"
    assert platform_result.provider == "apt"
    assert platform_result.success is True
    assert len(platform_result.observations) == 2
    assert len(platform_result.errors) == 0
    assert platform_result.duration > 0
    
    # Verify observations
    assert platform_result.observations[0].type == "file"
    assert platform_result.observations[0].data["path"] == "/usr/bin/nginx"
    assert platform_result.observations[1].type == "service"
    
    # Verify messages
    assert any("Successfully installed" in msg for msg in result_state["messages"])


@pytest.mark.asyncio
async def test_installation_agent_failure():
    """Test installation agent with failed installation."""
    # Create initial state
    state = create_initial_state("nonexistent")
    state["current_platform"] = "ubuntu:22.04"
    state["current_provider"] = "apt"
    state["provider_combinations"] = [("ubuntu:22.04", "apt")]
    
    # Mock failed tool result
    mock_tool_result = {
        "provider": "apt",
        "platform": "ubuntu:22.04",
        "success": False,
        "output": "Package not found",
        "test_output": None,
        "test_success": None,
        "files_created": [],
        "services_found": [],
        "binaries_found": [],
        "observations": [],
        "errors": ["Package 'nonexistent' not found in apt repository"],
        "duration": 5.0
    }
    
    # Mock the LLM response with tool call
    mock_response = Mock()
    mock_response.tool_calls = [
        {
            "name": "install_package",
            "args": {
                "platform": "ubuntu:22.04",
                "provider": "apt",
                "package": "nonexistent"
            }
        }
    ]
    
    with patch("saitest.agents.installation.ChatOpenAI") as mock_llm_class:
        mock_llm = Mock()
        mock_llm_with_tools = AsyncMock()
        mock_llm_with_tools.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = Mock(return_value=mock_llm_with_tools)
        mock_llm_class.return_value = mock_llm
        
        with patch("saitest.agents.installation.install_package") as mock_tool:
            mock_tool.invoke.return_value = mock_tool_result
            
            # Run the agent
            result_state = await installation_agent(state)
    
    # Verify results
    assert len(result_state["platform_results"]) == 1
    
    platform_result = result_state["platform_results"][0]
    assert platform_result.platform == "ubuntu:22.04"
    assert platform_result.provider == "apt"
    assert platform_result.success is False
    assert len(platform_result.observations) == 0
    assert len(platform_result.errors) == 1
    assert "not found" in platform_result.errors[0]
    
    # Verify messages
    assert any("Installation failed" in msg for msg in result_state["messages"])


@pytest.mark.asyncio
async def test_installation_agent_no_platform():
    """Test installation agent when platform is not set."""
    # Create initial state without platform
    state = create_initial_state("nginx")
    
    # Run the agent
    result_state = await installation_agent(state)
    
    # Verify error handling
    assert len(result_state["platform_results"]) == 0
    assert any("without platform or provider" in msg for msg in result_state["messages"])


def test_get_next_combination():
    """Test get_next_combination function."""
    # Create state with multiple combinations
    state = create_initial_state("nginx")
    state["provider_combinations"] = [
        ("ubuntu:22.04", "apt"),
        ("ubuntu:22.04", "snap"),
        ("debian:12", "apt")
    ]
    
    # No results yet - should return first combination
    has_more = get_next_combination(state)
    assert has_more is True
    assert state["current_platform"] == "ubuntu:22.04"
    assert state["current_provider"] == "apt"
    
    # Add first result
    state["platform_results"].append(
        PlatformResult(
            platform="ubuntu:22.04",
            provider="apt",
            success=True,
            observations=[],
            errors=[],
            duration=10.0
        )
    )
    
    # Should return second combination
    has_more = get_next_combination(state)
    assert has_more is True
    assert state["current_platform"] == "ubuntu:22.04"
    assert state["current_provider"] == "snap"
    
    # Add second result
    state["platform_results"].append(
        PlatformResult(
            platform="ubuntu:22.04",
            provider="snap",
            success=True,
            observations=[],
            errors=[],
            duration=10.0
        )
    )
    
    # Should return third combination
    has_more = get_next_combination(state)
    assert has_more is True
    assert state["current_platform"] == "debian:12"
    assert state["current_provider"] == "apt"
    
    # Add third result
    state["platform_results"].append(
        PlatformResult(
            platform="debian:12",
            provider="apt",
            success=True,
            observations=[],
            errors=[],
            duration=10.0
        )
    )
    
    # No more combinations
    has_more = get_next_combination(state)
    assert has_more is False
    assert state["current_platform"] is None
    assert state["current_provider"] is None


def test_get_next_combination_empty():
    """Test get_next_combination with no combinations."""
    state = create_initial_state("nginx")
    state["provider_combinations"] = []
    
    has_more = get_next_combination(state)
    assert has_more is False
    assert state["current_platform"] is None
    assert state["current_provider"] is None
