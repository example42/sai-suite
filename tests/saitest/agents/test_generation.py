"""Tests for generation agent."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import yaml

from saitest.agents.generation import generation_agent, write_saidata_files
from saitest.core.state import create_initial_state


@pytest.mark.asyncio
async def test_generation_agent_success():
    """Test generation agent with successful generation."""
    # Create initial state with patterns and variations
    state = create_initial_state("nginx")
    state["patterns"] = {
        "packages": [
            {
                "name": "nginx",
                "package_name": "nginx",
                "description": "High-performance HTTP server"
            }
        ],
        "services": [
            {
                "name": "nginx",
                "type": "systemd"
            }
        ],
        "files": [
            {
                "path": "/usr/sbin/nginx",
                "purpose": "binary"
            }
        ],
        "ports": [
            {
                "number": 80,
                "protocol": "tcp"
            }
        ]
    }
    
    state["variations"] = {
        "ubuntu:22.04:apt": {
            "packages": [
                {
                    "name": "nginx",
                    "package_name": "nginx-full",
                    "version": "1.18.0"
                }
            ]
        },
        "debian:12:apt": {
            "packages": [
                {
                    "name": "nginx",
                    "package_name": "nginx-light",
                    "version": "1.22.1"
                }
            ]
        }
    }
    
    # Mock LLM responses
    default_yaml = """version: "0.3"
metadata:
  name: nginx
  description: High-performance HTTP server
packages:
  - name: nginx
    package_name: nginx
services:
  - name: nginx
    type: systemd
files:
  - path: /usr/sbin/nginx
    purpose: binary
ports:
  - number: 80
    protocol: tcp
"""
    
    ubuntu_override_yaml = """version: "0.3"
packages:
  - name: nginx
    package_name: nginx-full
    version: "1.18.0"
"""
    
    debian_override_yaml = """version: "0.3"
packages:
  - name: nginx
    package_name: nginx-light
    version: "1.22.1"
"""
    
    # Mock LLM to return YAML responses
    with patch("saitest.agents.generation.ChatOpenAI") as mock_llm_class:
        mock_llm = Mock()
        
        # Create mock responses for each LLM call
        mock_default_response = Mock()
        mock_default_response.content = default_yaml
        
        mock_ubuntu_response = Mock()
        mock_ubuntu_response.content = ubuntu_override_yaml
        
        mock_debian_response = Mock()
        mock_debian_response.content = debian_override_yaml
        
        # Set up ainvoke to return different responses
        mock_llm.ainvoke = AsyncMock(
            side_effect=[mock_default_response, mock_ubuntu_response, mock_debian_response]
        )
        
        mock_llm_class.return_value = mock_llm
        
        # Run the agent
        result_state = await generation_agent(state)
    
    # Verify results
    assert result_state["generated_saidata"] is not None
    assert "default" in result_state["generated_saidata"]
    assert "overrides" in result_state["generated_saidata"]
    
    # Verify default saidata
    default_data = result_state["generated_saidata"]["default"]
    assert default_data["version"] == "0.3"
    assert default_data["metadata"]["name"] == "nginx"
    assert len(default_data["packages"]) == 1
    assert default_data["packages"][0]["name"] == "nginx"
    
    # Verify overrides
    overrides = result_state["generated_saidata"]["overrides"]
    assert "ubuntu" in overrides
    assert "22.04" in overrides["ubuntu"]
    assert "debian" in overrides
    assert "12" in overrides["debian"]
    
    # Verify messages
    assert any("Generation complete" in msg for msg in result_state["messages"])


@pytest.mark.asyncio
async def test_generation_agent_no_patterns():
    """Test generation agent when no patterns are available."""
    # Create initial state without patterns
    state = create_initial_state("nginx")
    state["patterns"] = {}
    
    # Run the agent
    result_state = await generation_agent(state)
    
    # Verify error handling
    assert result_state["generated_saidata"] is None
    assert any("Generation skipped" in msg for msg in result_state["messages"])


def test_write_saidata_files():
    """Test writing saidata files to disk."""
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Create test saidata
        saidata = {
            "default": {
                "version": "0.3",
                "metadata": {
                    "name": "nginx",
                    "description": "High-performance HTTP server"
                },
                "packages": [
                    {
                        "name": "nginx",
                        "package_name": "nginx"
                    }
                ]
            },
            "overrides": {
                "ubuntu": {
                    "22.04": {
                        "version": "0.3",
                        "packages": [
                            {
                                "name": "nginx",
                                "package_name": "nginx-full",
                                "version": "1.18.0"
                            }
                        ]
                    }
                },
                "debian": {
                    "12": {
                        "version": "0.3",
                        "packages": [
                            {
                                "name": "nginx",
                                "package_name": "nginx-light",
                                "version": "1.22.1"
                            }
                        ]
                    }
                }
            }
        }
        
        # Write files
        write_saidata_files("nginx", saidata, output_dir)
        
        # Verify files were created
        software_dir = output_dir / "nginx"
        assert software_dir.exists()
        
        # Verify default.yaml
        default_file = software_dir / "default.yaml"
        assert default_file.exists()
        with open(default_file) as f:
            default_data = yaml.safe_load(f)
        assert default_data["version"] == "0.3"
        assert default_data["metadata"]["name"] == "nginx"
        
        # Verify ubuntu override
        ubuntu_file = software_dir / "ubuntu" / "22.04.yaml"
        assert ubuntu_file.exists()
        with open(ubuntu_file) as f:
            ubuntu_data = yaml.safe_load(f)
        assert ubuntu_data["version"] == "0.3"
        assert ubuntu_data["packages"][0]["package_name"] == "nginx-full"
        
        # Verify debian override
        debian_file = software_dir / "debian" / "12.yaml"
        assert debian_file.exists()
        with open(debian_file) as f:
            debian_data = yaml.safe_load(f)
        assert debian_data["version"] == "0.3"
        assert debian_data["packages"][0]["package_name"] == "nginx-light"
