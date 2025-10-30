"""Discovery Agent for saitest.

This agent discovers available installation methods for software by:
1. Querying saigen's repository cache for package metadata
2. Scanning providers/ directory for available providerdata
3. Cross-referencing to find valid providers
4. Using LLM for research if no repository data is available
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from saitest.core.state import VerificationState
from saitest.utils.provider_executor import ProviderCommandExecutor
from saigen.repositories.manager import RepositoryManager


logger = logging.getLogger(__name__)


async def discovery_agent(state: VerificationState) -> VerificationState:
    """Discovery agent that identifies available installation methods.
    
    This agent:
    1. Queries saigen's repository cache for package metadata
    2. Scans providers/ directory for available providerdata
    3. Cross-references to find valid providers (those with both package data AND providerdata)
    4. Falls back to LLM research if no repository data is available
    5. Updates VerificationState with discovered installation methods
    
    Args:
        state: Current verification state
    
    Returns:
        Updated verification state with discovery results
    """
    software = state["software"]
    logger.info(f"Starting discovery for software: {software}")
    
    # Initialize provider executor to get available providerdata
    provider_executor = ProviderCommandExecutor()
    available_providers = provider_executor.get_available_providers()
    
    logger.info(f"Found {len(available_providers)} providers with providerdata: {', '.join(available_providers)}")
    
    # Query repository cache for package metadata
    providers_with_packages = await _query_repository_cache(software, available_providers)
    
    if providers_with_packages:
        # We found package data in repositories
        logger.info(
            f"Found package data in repositories for {len(providers_with_packages)} providers: "
            f"{', '.join(providers_with_packages.keys())}"
        )
        
        # Update state with discovered providers
        state["installation_methods"] = list(providers_with_packages.keys())
        state["package_versions"] = {
            provider: info["version"]
            for provider, info in providers_with_packages.items()
            if info.get("version")
        }
        state["expected_dependencies"] = {
            provider: info.get("dependencies", [])
            for provider, info in providers_with_packages.items()
        }
        
        # Use LLM to predict expected services, files, and ports
        await _predict_expected_resources(state, providers_with_packages)
        
        state["discovery_complete"] = True
        state["messages"].append(
            f"Discovery complete: Found {len(providers_with_packages)} installation methods"
        )
        
    else:
        # No repository data found, use LLM for research
        logger.info(f"No repository data found for {software}, using LLM for research")
        
        success = await _llm_discovery(state, available_providers)
        
        if success:
            state["discovery_complete"] = True
            state["messages"].append(
                f"Discovery complete via LLM: Found {len(state['installation_methods'])} installation methods"
            )
        else:
            state["discovery_complete"] = False
            state["messages"].append(
                f"Discovery failed: Could not find installation methods for {software}"
            )
            logger.error(f"Discovery failed for {software}")
    
    return state


async def _query_repository_cache(
    software: str,
    available_providers: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Query saigen's repository cache for package metadata.
    
    Args:
        software: Name of the software to search for
        available_providers: List of providers that have providerdata
    
    Returns:
        Dictionary mapping provider names to package information
    """
    providers_with_packages = {}
    
    try:
        # Initialize repository manager
        async with RepositoryManager() as repo_manager:
            # Search for the software across all repositories
            search_result = await repo_manager.search_packages(
                query=software,
                limit=50  # Get top 50 results
            )
            
            if not search_result.packages:
                logger.info(f"No packages found in repository cache for {software}")
                return providers_with_packages
            
            logger.info(
                f"Found {len(search_result.packages)} package results for {software} "
                f"from repositories: {', '.join(search_result.repository_sources)}"
            )
            
            # Map repository types to provider names
            # Repository types (apt, dnf, brew, etc.) should match provider names
            for package in search_result.packages:
                repo_type = package.repository_name.split('_')[0]  # e.g., "apt_ubuntu_22.04" -> "apt"
                
                # Check if this provider has providerdata
                if repo_type in available_providers:
                    # Only include exact matches or very close matches
                    if package.name.lower() == software.lower():
                        if repo_type not in providers_with_packages:
                            providers_with_packages[repo_type] = {
                                "version": package.version,
                                "description": package.description,
                                "dependencies": package.dependencies or [],
                                "homepage": package.homepage,
                                "license": package.license,
                                "repository": package.repository_name,
                                "platform": package.platform
                            }
                            logger.debug(
                                f"Found {software} in {repo_type}: version {package.version}"
                            )
            
            # If no exact matches, try case-insensitive partial matches
            if not providers_with_packages:
                for package in search_result.packages:
                    repo_type = package.repository_name.split('_')[0]
                    
                    if repo_type in available_providers:
                        if software.lower() in package.name.lower():
                            if repo_type not in providers_with_packages:
                                providers_with_packages[repo_type] = {
                                    "version": package.version,
                                    "description": package.description,
                                    "dependencies": package.dependencies or [],
                                    "homepage": package.homepage,
                                    "license": package.license,
                                    "repository": package.repository_name,
                                    "platform": package.platform
                                }
                                logger.debug(
                                    f"Found partial match {package.name} in {repo_type}: "
                                    f"version {package.version}"
                                )
    
    except Exception as e:
        logger.warning(f"Error querying repository cache: {e}")
        # Continue with empty results - will fall back to LLM
    
    return providers_with_packages


async def _predict_expected_resources(
    state: VerificationState,
    providers_with_packages: Dict[str, Dict[str, Any]]
) -> None:
    """Use LLM to predict expected services, files, and ports.
    
    Args:
        state: Current verification state
        providers_with_packages: Dictionary of providers with package information
    """
    software = state["software"]
    
    # Build context from package information
    package_info = []
    for provider, info in providers_with_packages.items():
        package_info.append(
            f"- {provider}: version {info.get('version', 'unknown')}, "
            f"description: {info.get('description', 'N/A')}"
        )
    
    package_context = "\n".join(package_info)
    
    prompt = f"""Analyze the software "{software}" and predict what resources it will create when installed.

Package information from repositories:
{package_context}

Based on this software, predict:
1. Service names (systemd services, daemons, etc.)
2. Important file paths (binaries, config files, etc.)
3. Network ports it typically uses
4. Configuration file locations

Return your response as a JSON object with this structure:
{{
    "services": ["service1", "service2"],
    "files": ["/path/to/binary", "/path/to/config"],
    "ports": [80, 443],
    "config_locations": ["/etc/software", "/usr/local/etc/software"]
}}

Be specific and realistic. Only include resources that are very likely to exist.
If you're unsure about something, omit it rather than guessing.
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
        
        predictions = json.loads(content)
        
        # Update state with predictions
        state["expected_services"] = predictions.get("services", [])
        state["expected_files"] = predictions.get("files", [])
        state["expected_ports"] = predictions.get("ports", [])
        
        logger.info(
            f"Predicted resources for {software}: "
            f"{len(state['expected_services'])} services, "
            f"{len(state['expected_files'])} files, "
            f"{len(state['expected_ports'])} ports"
        )
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}")
        # Set empty defaults
        state["expected_services"] = []
        state["expected_files"] = []
        state["expected_ports"] = []
    except Exception as e:
        logger.warning(f"Error predicting expected resources: {e}")
        # Set empty defaults
        state["expected_services"] = []
        state["expected_files"] = []
        state["expected_ports"] = []


async def _llm_discovery(
    state: VerificationState,
    available_providers: List[str]
) -> bool:
    """Use LLM to research installation methods when no repository data is available.
    
    Args:
        state: Current verification state
        available_providers: List of providers that have providerdata
    
    Returns:
        True if discovery succeeded, False otherwise
    """
    software = state["software"]
    
    prompt = f"""Research the software "{software}" and identify how it can be installed.

Available package managers and installation methods:
{', '.join(available_providers)}

For each installation method that applies to this software, provide:
1. The provider/package manager name (must be from the available list above)
2. The typical package name
3. Expected version (if known)
4. Expected services, files, ports, and configuration locations

Return your response as a JSON object with this structure:
{{
    "providers": [
        {{
            "name": "apt",
            "package_name": "nginx",
            "version": "1.24.0",
            "description": "High-performance HTTP server"
        }}
    ],
    "expected_services": ["nginx"],
    "expected_files": ["/usr/sbin/nginx", "/etc/nginx/nginx.conf"],
    "expected_ports": [80, 443],
    "config_locations": ["/etc/nginx"]
}}

Only include providers from the available list. Be specific and realistic.
If you're not sure about something, omit it rather than guessing.
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
        
        discovery_data = json.loads(content)
        
        # Extract providers
        providers = discovery_data.get("providers", [])
        
        if not providers:
            logger.warning(f"LLM did not identify any providers for {software}")
            return False
        
        # Validate providers against available providerdata
        valid_providers = []
        package_versions = {}
        
        for provider_info in providers:
            provider_name = provider_info.get("name")
            if provider_name in available_providers:
                valid_providers.append(provider_name)
                if "version" in provider_info:
                    package_versions[provider_name] = provider_info["version"]
                logger.debug(f"LLM identified valid provider: {provider_name}")
            else:
                logger.debug(
                    f"LLM identified provider {provider_name} but no providerdata available"
                )
        
        if not valid_providers:
            logger.warning(
                f"LLM identified providers but none have providerdata: "
                f"{[p.get('name') for p in providers]}"
            )
            return False
        
        # Update state
        state["installation_methods"] = valid_providers
        state["package_versions"] = package_versions
        state["expected_services"] = discovery_data.get("expected_services", [])
        state["expected_files"] = discovery_data.get("expected_files", [])
        state["expected_ports"] = discovery_data.get("expected_ports", [])
        state["expected_dependencies"] = {}  # LLM doesn't provide dependencies
        
        logger.info(
            f"LLM discovery found {len(valid_providers)} valid providers: "
            f"{', '.join(valid_providers)}"
        )
        
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"LLM response content: {response.content if 'response' in locals() else 'N/A'}")
        return False
    except Exception as e:
        logger.error(f"Error during LLM discovery: {e}")
        return False


def get_available_providers() -> List[str]:
    """Get list of available providers from providerdata.
    
    This is a convenience function that wraps ProviderCommandExecutor.
    
    Returns:
        List of provider names that have valid providerdata
    """
    executor = ProviderCommandExecutor()
    return executor.get_available_providers()
