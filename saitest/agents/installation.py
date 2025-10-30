"""Installation Agent for saitest.

This agent executes software installation on a specific platform-provider
combination by:
1. Binding the install_package tool to an LLM
2. Executing installation for the current platform-provider combination
3. Creating Observation objects from installation results
4. Creating PlatformResult with provider field
5. Handling installation failures gracefully
"""

import asyncio
import logging
import time
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

from saitest.core.state import VerificationState
from saitest.models.observation import Observation
from saitest.models.state import PlatformResult
from saitest.tools.package import install_package


logger = logging.getLogger(__name__)


async def installation_agent(state: VerificationState) -> VerificationState:
    """Installation agent that executes software installation.
    
    This agent:
    1. Gets the current platform-provider combination from state
    2. Binds the install_package tool to an LLM
    3. Executes installation using the tool
    4. Creates Observation objects from the installation results
    5. Creates a PlatformResult with all observations and metadata
    6. Handles installation failures gracefully
    7. Updates VerificationState with the platform result
    
    Args:
        state: Current verification state with current_platform and current_provider
    
    Returns:
        Updated verification state with new PlatformResult added
    """
    software = state["software"]
    platform = state.get("current_platform")
    provider = state.get("current_provider")
    
    if not platform or not provider:
        error_msg = "Installation agent called without platform or provider set"
        logger.error(error_msg)
        state["messages"].append(error_msg)
        return state
    
    logger.info(
        f"Starting installation of {software} on {platform} using {provider}"
    )
    
    start_time = time.time()
    
    try:
        # Bind install_package tool to LLM
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        llm_with_tools = llm.bind_tools([install_package])
        
        # Create prompt for the LLM
        prompt = f"""Install the software "{software}" on platform "{platform}" using provider "{provider}".

Use the install_package tool with these parameters:
- platform: "{platform}"
- provider: "{provider}"
- package: "{software}"

Execute the installation and report the results.
"""
        
        logger.debug(f"Sending installation request to LLM")
        
        # Invoke LLM with tool
        response = await llm_with_tools.ainvoke([HumanMessage(content=prompt)])
        
        # Check if LLM called the tool
        if not hasattr(response, 'tool_calls') or not response.tool_calls:
            error_msg = (
                f"LLM did not call install_package tool for {software} "
                f"on {platform} with {provider}"
            )
            logger.error(error_msg)
            
            # Create failed PlatformResult
            platform_result = PlatformResult(
                platform=platform,
                provider=provider,
                success=False,
                observations=[],
                errors=[error_msg],
                duration=time.time() - start_time
            )
            
            state["platform_results"].append(platform_result)
            state["messages"].append(
                f"Installation failed on {platform} with {provider}: LLM did not call tool"
            )
            
            return state
        
        # Get tool call result
        tool_call = response.tool_calls[0]
        logger.debug(f"LLM called tool: {tool_call['name']} with args: {tool_call['args']}")
        
        # Execute the tool directly (since we're in async context)
        # The tool function is synchronous, so we run it in executor
        loop = asyncio.get_event_loop()
        tool_result = await loop.run_in_executor(
            None,
            install_package.invoke,
            tool_call['args']
        )
        
        logger.info(
            f"Installation tool completed: success={tool_result.get('success', False)}, "
            f"observations={len(tool_result.get('observations', []))}"
        )
        
        # Parse observations from tool result
        observations = []
        for obs_dict in tool_result.get("observations", []):
            try:
                obs = Observation(**obs_dict)
                observations.append(obs)
            except Exception as e:
                logger.warning(f"Failed to parse observation: {e}")
        
        # Create PlatformResult
        platform_result = PlatformResult(
            platform=platform,
            provider=provider,
            success=tool_result.get("success", False),
            observations=observations,
            errors=tool_result.get("errors", []),
            duration=tool_result.get("duration", time.time() - start_time)
        )
        
        # Add to state
        state["platform_results"].append(platform_result)
        
        # Update messages
        if platform_result.success:
            state["messages"].append(
                f"Successfully installed {software} on {platform} with {provider} "
                f"({len(observations)} observations)"
            )
            logger.info(
                f"Installation succeeded: {len(observations)} observations, "
                f"{len(platform_result.errors)} errors"
            )
        else:
            state["messages"].append(
                f"Installation failed on {platform} with {provider}: "
                f"{', '.join(platform_result.errors)}"
            )
            logger.warning(
                f"Installation failed: {', '.join(platform_result.errors)}"
            )
    
    except Exception as e:
        # Handle unexpected errors gracefully
        error_msg = f"Unexpected error during installation: {e}"
        logger.error(error_msg, exc_info=True)
        
        # Create failed PlatformResult
        platform_result = PlatformResult(
            platform=platform,
            provider=provider,
            success=False,
            observations=[],
            errors=[error_msg],
            duration=time.time() - start_time
        )
        
        state["platform_results"].append(platform_result)
        state["messages"].append(
            f"Installation failed on {platform} with {provider}: {error_msg}"
        )
    
    return state


def get_next_combination(state: VerificationState) -> bool:
    """Check if there are more platform-provider combinations to test.
    
    This function checks the provider_combinations list against the
    platform_results to determine if there are untested combinations.
    If there are, it sets current_platform and current_provider for
    the next combination.
    
    Args:
        state: Current verification state
    
    Returns:
        True if there are more combinations to test, False otherwise
    """
    # Get tested combinations
    tested = {
        (result.platform, result.provider)
        for result in state["platform_results"]
    }
    
    # Find remaining combinations
    remaining = [
        combo for combo in state["provider_combinations"]
        if combo not in tested
    ]
    
    if remaining:
        # Set next combination
        next_platform, next_provider = remaining[0]
        state["current_platform"] = next_platform
        state["current_provider"] = next_provider
        
        logger.info(
            f"Next combination: {next_platform} with {next_provider} "
            f"({len(remaining)} remaining)"
        )
        
        return True
    else:
        # No more combinations
        state["current_platform"] = None
        state["current_provider"] = None
        
        logger.info("All platform-provider combinations tested")
        
        return False
