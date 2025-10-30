"""Platform Selection Agent for saitest.

This agent selects platforms for testing by:
1. Using user-specified platforms if provided
2. Otherwise using LLM to select 2-4 representative platforms
3. Generating platform-provider combinations for testing
"""

import asyncio
import json
import logging
from typing import List, Tuple

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from saitest.core.state import VerificationState


logger = logging.getLogger(__name__)


async def platform_selection_agent(state: VerificationState) -> VerificationState:
    """Platform selection agent that chooses platforms for testing.
    
    This agent:
    1. Uses user-specified platforms if provided in target_platforms
    2. Otherwise uses LLM to select 2-4 representative platforms
    3. Falls back to default platforms (ubuntu:22.04, debian:12) if LLM fails
    4. Generates platform-provider combinations for testing
    5. Updates VerificationState with selected platforms and combinations
    
    Args:
        state: Current verification state
    
    Returns:
        Updated verification state with platform selection results
    """
    software = state["software"]
    installation_methods = state.get("installation_methods", [])
    
    logger.info(f"Starting platform selection for software: {software}")
    
    # Check if user specified target platforms
    if state.get("target_platforms"):
        selected_platforms = state["target_platforms"]
        logger.info(
            f"Using user-specified platforms: {', '.join(selected_platforms)}"
        )
        state["messages"].append(
            f"Using {len(selected_platforms)} user-specified platforms"
        )
    else:
        # Use LLM to select representative platforms
        logger.info("No user-specified platforms, using LLM to select platforms")
        selected_platforms = await _llm_select_platforms(
            software,
            installation_methods
        )
        
        if not selected_platforms:
            # Fall back to default platforms
            selected_platforms = ["ubuntu:22.04", "debian:12"]
            logger.warning(
                f"LLM platform selection failed, using defaults: "
                f"{', '.join(selected_platforms)}"
            )
            state["messages"].append(
                "Platform selection failed, using default platforms"
            )
        else:
            logger.info(
                f"LLM selected {len(selected_platforms)} platforms: "
                f"{', '.join(selected_platforms)}"
            )
            state["messages"].append(
                f"Selected {len(selected_platforms)} representative platforms"
            )
    
    # Update state with selected platforms
    state["selected_platforms"] = selected_platforms
    
    # Generate platform-provider combinations
    combinations = create_provider_combinations(state)
    state["provider_combinations"] = combinations
    
    logger.info(
        f"Generated {len(combinations)} platform-provider combinations to test"
    )
    state["messages"].append(
        f"Will test {len(combinations)} platform-provider combinations"
    )
    
    return state


async def _llm_select_platforms(
    software: str,
    installation_methods: List[str]
) -> List[str]:
    """Use LLM to select 2-4 representative platforms for testing.
    
    Args:
        software: Name of the software being tested
        installation_methods: List of available installation providers
    
    Returns:
        List of platform identifiers (e.g., ["ubuntu:22.04", "debian:12"])
    """
    prompt = f"""Select 2-4 representative platforms to test the software "{software}".

Available installation methods: {', '.join(installation_methods)}

Consider:
1. Different package managers (apt, dnf, brew, etc.)
2. Popular distributions (Ubuntu, Debian, CentOS, Rocky, Fedora, etc.)
3. Different OS families (Debian-based, RedHat-based, etc.)
4. Current stable versions

Return your response as a JSON object with this structure:
{{
    "platforms": [
        "ubuntu:22.04",
        "debian:12",
        "rockylinux:8",
        "fedora:40"
    ],
    "reasoning": "Brief explanation of why these platforms were selected"
}}

Select platforms that provide good coverage of different package managers and OS families.
Prefer current stable versions. Limit to 2-4 platforms for efficiency.
"""
    
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        # Parse JSON response
        content = response.content.strip()
        
        # Extract JSON from markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        selection_data = json.loads(content)
        
        platforms = selection_data.get("platforms", [])
        reasoning = selection_data.get("reasoning", "")
        
        if platforms:
            logger.info(f"LLM platform selection reasoning: {reasoning}")
            logger.debug(f"Selected platforms: {platforms}")
            return platforms
        else:
            logger.warning("LLM returned empty platform list")
            return []
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(
            f"LLM response content: {response.content if 'response' in locals() else 'N/A'}"
        )
        return []
    except Exception as e:
        logger.error(f"Error during LLM platform selection: {e}")
        return []


def create_provider_combinations(state: VerificationState) -> List[Tuple[str, str]]:
    """Create all platform-provider combinations to test.
    
    This function generates a list of (platform, provider) tuples representing
    all combinations that need to be tested. Each combination will be tested
    in a fresh container.
    
    Args:
        state: Current verification state with selected_platforms and installation_methods
    
    Returns:
        List of (platform, provider) tuples
    
    Example:
        If selected_platforms = ["ubuntu:22.04", "debian:12"]
        and installation_methods = ["apt", "snap"]
        
        Returns: [
            ("ubuntu:22.04", "apt"),
            ("ubuntu:22.04", "snap"),
            ("debian:12", "apt"),
            ("debian:12", "snap")
        ]
    """
    combinations = []
    
    selected_platforms = state.get("selected_platforms", [])
    installation_methods = state.get("installation_methods", [])
    
    for platform in selected_platforms:
        for provider in installation_methods:
            combinations.append((platform, provider))
    
    logger.debug(
        f"Created {len(combinations)} combinations from "
        f"{len(selected_platforms)} platforms and "
        f"{len(installation_methods)} providers"
    )
    
    return combinations
