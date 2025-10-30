"""Generation Agent for saitest.

This agent generates saidata YAML files by:
1. Using LLM to generate default.yaml with common configuration across all platforms
2. Using LLM to generate OS-specific override files for platform variations
3. Including provider-specific overrides for all tested providers
4. Parsing YAML and storing in VerificationState
5. Writing files to proper directory structure
"""

import json
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from saitest.core.state import VerificationState


logger = logging.getLogger(__name__)


async def generation_agent(state: VerificationState) -> VerificationState:
    """Generation agent that creates saidata YAML files.
    
    This agent:
    1. Uses LLM to generate default.yaml with common patterns
    2. Uses LLM to generate OS-specific override files for variations
    3. Includes provider-specific overrides for all tested providers
    4. Parses YAML and stores in VerificationState
    5. Prepares file structure for writing
    
    Args:
        state: Current verification state with patterns and variations
    
    Returns:
        Updated verification state with generated_saidata
    """
    software = state["software"]
    patterns = state.get("patterns", {})
    variations = state.get("variations", {})
    
    if not patterns:
        logger.warning(f"No patterns found for {software}, cannot generate saidata")
        state["messages"].append("Generation skipped: No patterns available")
        state["generated_saidata"] = None
        return state
    
    logger.info(f"Starting saidata generation for {software}")
    
    # Step 1: Generate default.yaml with common patterns
    default_saidata = await _generate_default_saidata(software, patterns, state)
    
    if not default_saidata:
        logger.error(f"Failed to generate default saidata for {software}")
        state["messages"].append("Generation failed: Could not generate default.yaml")
        state["generated_saidata"] = None
        return state
    
    logger.info(f"Generated default.yaml for {software}")
    
    # Step 2: Generate OS-specific overrides for variations
    os_overrides = await _generate_os_overrides(software, variations, patterns)
    
    logger.info(
        f"Generated {sum(len(versions) for versions in os_overrides.values())} "
        f"OS-specific override files"
    )
    
    # Step 3: Store in state
    state["generated_saidata"] = {
        "default": default_saidata,
        "overrides": os_overrides
    }
    
    # Update messages
    state["messages"].append(
        f"Generation complete: default.yaml + "
        f"{sum(len(versions) for versions in os_overrides.values())} override files"
    )
    
    return state


async def _generate_default_saidata(
    software: str,
    patterns: Dict[str, Any],
    state: VerificationState
) -> Optional[Dict[str, Any]]:
    """Generate default.yaml with common configuration across all platforms.
    
    Args:
        software: Name of the software
        patterns: Common patterns identified across platforms
        state: Current verification state for additional context
    
    Returns:
        Dictionary representing default saidata, or None if generation fails
    """
    # Build context from patterns
    patterns_summary = json.dumps(patterns, indent=2)
    
    # Get tested combinations for context
    platform_results = state.get("platform_results", [])
    combinations = [
        f"{result.platform} with {result.provider}"
        for result in platform_results
    ]
    
    prompt = f"""Generate a default saidata YAML file for "{software}" following schema version 0.3.

This file should contain ONLY the common configuration that applies across ALL platforms.

Common patterns identified:
{patterns_summary}

Tested on these platform-provider combinations:
{chr(10).join(f"- {combo}" for combo in combinations)}

Generate a complete saidata structure with these sections:
1. version: "0.3"
2. metadata: name, description, homepage (if known), license (if known)
3. packages: List of packages with name and package_name fields
4. services: List of services (if any)
5. files: List of important files (binaries, configs)
6. commands: List of commands (if any)
7. ports: List of network ports (if any)

IMPORTANT RULES:
- Only include resources that are common across ALL or MOST platforms
- Use generic paths that work across platforms
- Do NOT include platform-specific variations
- Do NOT include provider-specific overrides
- Keep it minimal and focused on what's truly common
- Both 'name' and 'package_name' fields are REQUIRED for packages

Return ONLY valid YAML, no markdown formatting or explanations.
"""
    
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        # Extract YAML content
        content = response.content.strip()
        
        # Remove markdown code blocks if present
        if "```yaml" in content:
            content = content.split("```yaml")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Parse YAML
        default_saidata = yaml.safe_load(content)
        
        # Validate basic structure
        if not isinstance(default_saidata, dict):
            logger.error("Generated default saidata is not a dictionary")
            return None
        
        if "version" not in default_saidata:
            logger.warning("Adding missing version field to default saidata")
            default_saidata["version"] = "0.3"
        
        if "metadata" not in default_saidata:
            logger.warning("Adding missing metadata to default saidata")
            default_saidata["metadata"] = {"name": software}
        
        logger.debug(f"Generated default saidata: {json.dumps(default_saidata, indent=2)}")
        
        return default_saidata
        
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse generated YAML: {e}")
        logger.debug(f"LLM response: {response.content if 'response' in locals() else 'N/A'}")
        return None
    except Exception as e:
        logger.error(f"Error generating default saidata: {e}")
        return None


async def _generate_os_overrides(
    software: str,
    variations: Dict[str, Any],
    patterns: Dict[str, Any]
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Generate OS-specific override files for platform variations.
    
    Args:
        software: Name of the software
        variations: Platform-specific and provider-specific variations
        patterns: Common patterns (for context)
    
    Returns:
        Nested dictionary: {os_name: {version: override_data}}
    """
    os_overrides = {}
    
    if not variations:
        logger.info("No variations found, skipping OS-specific overrides")
        return os_overrides
    
    # Group variations by OS and version
    # variations keys are like "ubuntu:22.04:apt" or "debian:12:dnf"
    variations_by_os = {}
    for combo_key, variation_data in variations.items():
        # Parse combo_key: "platform:provider" or "platform:version:provider"
        parts = combo_key.split(":")
        
        if len(parts) >= 2:
            # Extract OS and version
            if len(parts) == 2:
                # Format: "platform:provider" (e.g., "ubuntu:apt")
                # Skip these, we need version info
                continue
            elif len(parts) == 3:
                # Format: "os:version:provider" (e.g., "ubuntu:22.04:apt")
                os_name = parts[0]
                version = parts[1]
                provider = parts[2]
            else:
                # Unexpected format, skip
                logger.warning(f"Unexpected combo_key format: {combo_key}")
                continue
            
            # Create nested structure
            if os_name not in variations_by_os:
                variations_by_os[os_name] = {}
            if version not in variations_by_os[os_name]:
                variations_by_os[os_name][version] = {}
            
            # Merge variation data for this OS/version
            # Multiple providers may have variations for the same OS/version
            if not variations_by_os[os_name][version]:
                variations_by_os[os_name][version] = variation_data
            else:
                # Merge provider-specific variations
                _merge_variations(
                    variations_by_os[os_name][version],
                    variation_data
                )
    
    # Generate override file for each OS/version combination
    for os_name, versions in variations_by_os.items():
        os_overrides[os_name] = {}
        
        for version, variation_data in versions.items():
            override_saidata = await _generate_single_override(
                software,
                os_name,
                version,
                variation_data,
                patterns
            )
            
            if override_saidata:
                os_overrides[os_name][version] = override_saidata
                logger.debug(
                    f"Generated override for {os_name}/{version}: "
                    f"{json.dumps(override_saidata, indent=2)}"
                )
    
    return os_overrides


async def _generate_single_override(
    software: str,
    os_name: str,
    version: str,
    variation_data: Dict[str, Any],
    patterns: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Generate a single OS-specific override file.
    
    Args:
        software: Name of the software
        os_name: OS name (e.g., "ubuntu", "debian")
        version: OS version (e.g., "22.04", "12")
        variation_data: Platform-specific variations
        patterns: Common patterns (for context)
    
    Returns:
        Dictionary representing override saidata, or None if generation fails
    """
    variation_summary = json.dumps(variation_data, indent=2)
    patterns_summary = json.dumps(patterns, indent=2)
    
    prompt = f"""Generate an OS-specific override saidata file for "{software}" on {os_name} {version}.

This file should contain ONLY the differences from the default configuration.

Platform-specific variations for {os_name} {version}:
{variation_summary}

Common patterns (for reference):
{patterns_summary}

Generate a saidata structure with these rules:
1. version: "0.3" (always include)
2. Include ONLY fields that differ from the default
3. If package names differ, include the packages section
4. If file paths differ, include the files section
5. If service configurations differ, include the services section
6. Include provider-specific overrides if multiple providers were tested

IMPORTANT RULES:
- Only include what's DIFFERENT from default.yaml
- If something is the same as default, omit it
- Keep it minimal - only the variations
- Both 'name' and 'package_name' fields are REQUIRED if including packages

Return ONLY valid YAML, no markdown formatting or explanations.
"""
    
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        # Extract YAML content
        content = response.content.strip()
        
        # Remove markdown code blocks if present
        if "```yaml" in content:
            content = content.split("```yaml")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Parse YAML
        override_saidata = yaml.safe_load(content)
        
        # Validate basic structure
        if not isinstance(override_saidata, dict):
            logger.error(f"Generated override for {os_name}/{version} is not a dictionary")
            return None
        
        # Ensure version field is present
        if "version" not in override_saidata:
            override_saidata["version"] = "0.3"
        
        return override_saidata
        
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse generated YAML for {os_name}/{version}: {e}")
        logger.debug(f"LLM response: {response.content if 'response' in locals() else 'N/A'}")
        return None
    except Exception as e:
        logger.error(f"Error generating override for {os_name}/{version}: {e}")
        return None


def _merge_variations(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """Merge variation data from source into target.
    
    This is used when multiple providers have variations for the same OS/version.
    
    Args:
        target: Target dictionary to merge into (modified in place)
        source: Source dictionary to merge from
    """
    for key, value in source.items():
        if key not in target:
            target[key] = value
        elif isinstance(value, list) and isinstance(target[key], list):
            # Merge lists, avoiding duplicates
            for item in value:
                if item not in target[key]:
                    target[key].append(item)
        elif isinstance(value, dict) and isinstance(target[key], dict):
            # Recursively merge dictionaries
            _merge_variations(target[key], value)
        # For other types, keep the existing value (first one wins)


def write_saidata_files(
    software: str,
    saidata: Dict[str, Any],
    output_dir: Path
) -> None:
    """Write saidata to files with OS-specific overrides.
    
    Creates a directory structure like:
        output_dir/
        └── software/
            ├── default.yaml
            ├── ubuntu/
            │   ├── 22.04.yaml
            │   └── 24.04.yaml
            └── debian/
                └── 12.yaml
    
    Args:
        software: Name of the software
        saidata: Generated saidata with 'default' and 'overrides' keys
        output_dir: Base output directory
    """
    # Create software directory
    software_dir = output_dir / software
    software_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Writing saidata files to {software_dir}")
    
    # Write default.yaml
    default_data = saidata.get("default")
    if default_data:
        default_file = software_dir / "default.yaml"
        with open(default_file, 'w') as f:
            yaml.dump(
                default_data,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )
        logger.info(f"Wrote {default_file}")
    else:
        logger.warning("No default saidata to write")
    
    # Write OS-specific overrides
    overrides = saidata.get("overrides", {})
    for os_name, versions in overrides.items():
        os_dir = software_dir / os_name
        os_dir.mkdir(exist_ok=True)
        
        for version, override_data in versions.items():
            override_file = os_dir / f"{version}.yaml"
            with open(override_file, 'w') as f:
                yaml.dump(
                    override_data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )
            logger.info(f"Wrote {override_file}")
    
    logger.info(
        f"Successfully wrote saidata: 1 default file + "
        f"{sum(len(versions) for versions in overrides.values())} override files"
    )
