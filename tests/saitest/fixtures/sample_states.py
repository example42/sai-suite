"""Sample VerificationState fixtures for testing.

This module provides pre-configured VerificationState objects for use in tests.
"""

from typing import Dict, Any
from saitest.core.state import VerificationState, create_initial_state
from saitest.models.state import PlatformResult
from .sample_observations import (
    NGINX_OBSERVATIONS_APT,
    NGINX_OBSERVATIONS_PIP,
    DEBIAN_OBSERVATIONS
)


def create_discovery_complete_state() -> VerificationState:
    """Create a state after discovery phase completion."""
    state = create_initial_state(software="nginx")
    state["discovery_complete"] = True
    state["installation_methods"] = ["apt", "pip", "source"]
    state["expected_services"] = ["nginx"]
    state["expected_files"] = ["/usr/bin/nginx", "/etc/nginx/nginx.conf"]
    state["expected_ports"] = [80, 443]
    state["package_versions"] = {
        "apt": "1.18.0",
        "pip": "0.5.2"
    }
    state["expected_dependencies"] = {
        "apt": ["libssl-dev", "libpcre3-dev"],
        "pip": []
    }
    return state


def create_platform_selected_state() -> VerificationState:
    """Create a state after platform selection."""
    state = create_discovery_complete_state()
    state["selected_platforms"] = ["ubuntu:22.04", "debian:12"]
    state["provider_combinations"] = [
        ("ubuntu:22.04", "apt"),
        ("ubuntu:22.04", "pip"),
        ("debian:12", "apt")
    ]
    state["current_platform"] = "ubuntu:22.04"
    state["current_provider"] = "apt"
    return state


def create_installation_complete_state() -> VerificationState:
    """Create a state after installation phase completion."""
    state = create_platform_selected_state()
    
    # Add platform results
    result_ubuntu_apt = PlatformResult(
        platform="ubuntu:22.04",
        provider="apt",
        success=True,
        observations=NGINX_OBSERVATIONS_APT,
        errors=[],
        duration=45.2
    )
    
    result_ubuntu_pip = PlatformResult(
        platform="ubuntu:22.04",
        provider="pip",
        success=True,
        observations=NGINX_OBSERVATIONS_PIP,
        errors=[],
        duration=32.1
    )
    
    result_debian_apt = PlatformResult(
        platform="debian:12",
        provider="apt",
        success=True,
        observations=DEBIAN_OBSERVATIONS,
        errors=[],
        duration=48.7
    )
    
    state["platform_results"] = [
        result_ubuntu_apt,
        result_ubuntu_pip,
        result_debian_apt
    ]
    
    return state


def create_analysis_complete_state() -> VerificationState:
    """Create a state after analysis phase completion."""
    state = create_installation_complete_state()
    
    # Add aggregated observations
    state["aggregated_observations"] = {
        "file": [obs for obs in NGINX_OBSERVATIONS_APT if obs.type == "file"],
        "service": [obs for obs in NGINX_OBSERVATIONS_APT if obs.type == "service"],
        "port": [obs for obs in NGINX_OBSERVATIONS_APT if obs.type == "port"],
        "command": [obs for obs in NGINX_OBSERVATIONS_APT if obs.type == "command"],
        "package": [obs for obs in NGINX_OBSERVATIONS_APT if obs.type == "package"]
    }
    
    # Add patterns (common across platforms)
    state["patterns"] = {
        "services": ["nginx"],
        "ports": [80, 443],
        "commands": [{"name": "nginx", "path": "/usr/bin/nginx"}]
    }
    
    # Add variations (platform-specific)
    state["variations"] = {
        "ubuntu:22.04": {
            "apt": {
                "package_name": "nginx-full",
                "version": "1.18.0",
                "config_path": "/etc/nginx/nginx.conf"
            },
            "pip": {
                "package_name": "nginx-config-builder",
                "version": "0.5.2"
            }
        },
        "debian:12": {
            "apt": {
                "package_name": "nginx-light",
                "version": "1.22.1",
                "config_path": "/etc/nginx/nginx.conf"
            }
        }
    }
    
    # Add confidence scores
    state["confidence_scores"] = {
        "services": 0.9,
        "ports": 0.8,
        "files": 0.95,
        "commands": 1.0,
        "packages": 0.85
    }
    
    return state


def create_generation_complete_state() -> VerificationState:
    """Create a state after generation phase completion."""
    state = create_analysis_complete_state()
    
    # Add generated saidata
    state["generated_saidata"] = {
        "default": {
            "version": "0.3",
            "metadata": {
                "name": "nginx",
                "description": "High-performance HTTP server",
                "homepage": "https://nginx.org",
                "license": "BSD-2-Clause"
            },
            "packages": [
                {
                    "name": "nginx",
                    "package_name": "nginx"
                }
            ],
            "services": [
                {
                    "name": "nginx",
                    "type": "systemd",
                    "enabled": True
                }
            ],
            "files": [
                {
                    "path": "/usr/bin/nginx",
                    "purpose": "binary"
                },
                {
                    "path": "/etc/nginx/nginx.conf",
                    "purpose": "config"
                }
            ],
            "commands": [
                {
                    "name": "nginx",
                    "path": "/usr/bin/nginx"
                }
            ],
            "ports": [
                {
                    "number": 80,
                    "protocol": "tcp"
                },
                {
                    "number": 443,
                    "protocol": "tcp"
                }
            ]
        },
        "overrides": {
            "ubuntu": {
                "22.04": {
                    "version": "0.3",
                    "providers": {
                        "apt": {
                            "packages": [
                                {
                                    "name": "nginx",
                                    "package_name": "nginx-full",
                                    "version": "1.18.0"
                                }
                            ]
                        },
                        "pip": {
                            "packages": [
                                {
                                    "name": "nginx",
                                    "package_name": "nginx-config-builder",
                                    "version": "0.5.2"
                                }
                            ]
                        }
                    }
                }
            },
            "debian": {
                "12": {
                    "version": "0.3",
                    "providers": {
                        "apt": {
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
        }
    }
    
    return state


def create_quality_check_complete_state(high_confidence: bool = True) -> VerificationState:
    """Create a state after quality check phase completion.
    
    Args:
        high_confidence: If True, create state with high confidence scores.
                        If False, create state with low confidence requiring review.
    """
    state = create_generation_complete_state()
    
    if high_confidence:
        state["validation_errors"] = []
        state["completeness_score"] = 0.92
        state["accuracy_score"] = 0.88
        state["overall_confidence"] = 0.90
        state["needs_human_review"] = False
    else:
        state["validation_errors"] = [
            "Missing required field: metadata.license",
            "Invalid port number: -1"
        ]
        state["completeness_score"] = 0.65
        state["accuracy_score"] = 0.58
        state["overall_confidence"] = 0.62
        state["needs_human_review"] = True
    
    return state


def create_failed_installation_state() -> VerificationState:
    """Create a state with failed installation results."""
    state = create_platform_selected_state()
    
    # Add failed platform result
    failed_result = PlatformResult(
        platform="ubuntu:22.04",
        provider="pip",
        success=False,
        observations=[],
        errors=["Package not found in pip repository", "Installation timeout"],
        duration=120.0
    )
    
    state["platform_results"] = [failed_result]
    state["retry_count"] = 1
    
    return state


def create_retry_state() -> VerificationState:
    """Create a state that needs retry."""
    state = create_quality_check_complete_state(high_confidence=False)
    state["retry_count"] = 1
    state["overall_confidence"] = 0.45  # Below retry threshold
    return state


def create_max_retries_state() -> VerificationState:
    """Create a state that has reached max retries."""
    state = create_retry_state()
    state["retry_count"] = 2  # Reached max_retries
    return state


# Dictionary of all sample states for easy access
SAMPLE_STATES: Dict[str, VerificationState] = {
    "initial": create_initial_state(software="nginx"),
    "discovery_complete": create_discovery_complete_state(),
    "platform_selected": create_platform_selected_state(),
    "installation_complete": create_installation_complete_state(),
    "analysis_complete": create_analysis_complete_state(),
    "generation_complete": create_generation_complete_state(),
    "quality_check_high": create_quality_check_complete_state(high_confidence=True),
    "quality_check_low": create_quality_check_complete_state(high_confidence=False),
    "failed_installation": create_failed_installation_state(),
    "retry": create_retry_state(),
    "max_retries": create_max_retries_state()
}
