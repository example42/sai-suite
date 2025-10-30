"""Analysis Agent for saitest.

This agent analyzes observations from all platform-provider combinations to:
1. Aggregate observations by type and provider
2. Use LLM to identify common patterns across platforms
3. Use LLM to identify provider-specific variations
4. Calculate confidence scores for findings
5. Update VerificationState with patterns, variations, and confidence scores
"""

import json
import logging
from typing import Dict, List, Any
from collections import defaultdict

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from saitest.core.state import VerificationState
from saitest.models.observation import Observation
from saitest.models.state import PlatformResult


logger = logging.getLogger(__name__)


async def analysis_agent(state: VerificationState) -> VerificationState:
    """Analysis agent that identifies patterns and variations across platforms.
    
    This agent:
    1. Aggregates observations by type (file, service, port, etc.) and provider
    2. Uses LLM to identify common patterns across all platforms
    3. Uses LLM to identify platform-specific and provider-specific variations
    4. Calculates confidence scores for each finding
    5. Updates VerificationState with analysis results
    
    Args:
        state: Current verification state with platform_results
    
    Returns:
        Updated verification state with patterns, variations, and confidence scores
    """
    software = state["software"]
    platform_results = state["platform_results"]
    
    if not platform_results:
        logger.warning(f"No platform results to analyze for {software}")
        state["messages"].append("Analysis skipped: No platform results available")
        return state
    
    logger.info(
        f"Starting analysis for {software}: "
        f"{len(platform_results)} platform-provider combinations tested"
    )
    
    # Step 1: Aggregate observations by type and provider
    aggregated = _aggregate_observations(platform_results)
    state["aggregated_observations"] = aggregated
    
    logger.info(
        f"Aggregated observations: "
        f"{sum(len(obs) for obs in aggregated.values())} total observations "
        f"across {len(aggregated)} types"
    )
    
    # Step 2: Identify common patterns using LLM
    patterns = await _identify_patterns(software, aggregated, platform_results)
    state["patterns"] = patterns
    
    logger.info(f"Identified {len(patterns)} common patterns")
    
    # Step 3: Identify platform-specific and provider-specific variations using LLM
    variations = await _identify_variations(software, aggregated, platform_results)
    state["variations"] = variations
    
    logger.info(
        f"Identified variations for {len(variations)} platform-provider combinations"
    )
    
    # Step 4: Calculate confidence scores
    confidence_scores = _calculate_confidence_scores(
        platform_results,
        patterns,
        variations
    )
    state["confidence_scores"] = confidence_scores
    
    logger.info(
        f"Calculated confidence scores: "
        f"pattern={confidence_scores.get('pattern_confidence', 0):.2f}, "
        f"variation={confidence_scores.get('variation_confidence', 0):.2f}, "
        f"overall={confidence_scores.get('overall_confidence', 0):.2f}"
    )
    
    # Update messages
    state["messages"].append(
        f"Analysis complete: {len(patterns)} patterns, "
        f"{len(variations)} variations, "
        f"confidence={confidence_scores.get('overall_confidence', 0):.2f}"
    )
    
    return state


def _aggregate_observations(
    platform_results: List[PlatformResult]
) -> Dict[str, List[Dict[str, Any]]]:
    """Aggregate observations by type and provider.
    
    Groups observations by their type (file, service, port, etc.) and includes
    platform and provider information for each observation.
    
    Args:
        platform_results: List of PlatformResult objects
    
    Returns:
        Dictionary mapping observation types to lists of observation data
    """
    aggregated = defaultdict(list)
    
    for result in platform_results:
        for obs in result.observations:
            # Convert Observation to dict and add platform/provider context
            obs_dict = obs.model_dump()
            
            # Add to aggregated list by type
            aggregated[obs.type].append(obs_dict)
    
    # Convert defaultdict to regular dict
    return dict(aggregated)


async def _identify_patterns(
    software: str,
    aggregated_observations: Dict[str, List[Dict[str, Any]]],
    platform_results: List[PlatformResult]
) -> Dict[str, Any]:
    """Use LLM to identify common patterns across all platforms.
    
    Analyzes aggregated observations to find resources that appear consistently
    across all or most platform-provider combinations.
    
    Args:
        software: Name of the software being analyzed
        aggregated_observations: Observations grouped by type
        platform_results: List of all platform results
    
    Returns:
        Dictionary containing common patterns identified
    """
    # Build summary of observations for LLM
    observation_summary = _build_observation_summary(aggregated_observations)
    
    # Get list of tested combinations
    combinations = [
        f"{result.platform} with {result.provider}"
        for result in platform_results
    ]
    
    prompt = f"""Analyze the observations from installing "{software}" across multiple platform-provider combinations.

Tested combinations:
{chr(10).join(f"- {combo}" for combo in combinations)}

Observations by type:
{observation_summary}

Identify COMMON PATTERNS that appear across ALL or MOST platform-provider combinations.
Focus on:
1. Files that appear in the same locations across platforms
2. Services with consistent names
3. Ports that are consistently used
4. Commands that are consistently available
5. Package names that are consistent

Return your response as a JSON object with this structure:
{{
    "packages": [
        {{
            "name": "nginx",
            "package_name": "nginx",
            "description": "Common package name across most platforms"
        }}
    ],
    "services": [
        {{
            "name": "nginx",
            "type": "systemd",
            "description": "Service found on all systemd platforms"
        }}
    ],
    "files": [
        {{
            "path": "/usr/sbin/nginx",
            "purpose": "binary",
            "description": "Main binary found on most platforms"
        }}
    ],
    "commands": [
        {{
            "name": "nginx",
            "path": "/usr/sbin/nginx",
            "description": "Main command available on all platforms"
        }}
    ],
    "ports": [
        {{
            "number": 80,
            "protocol": "tcp",
            "description": "Default HTTP port"
        }}
    ]
}}

Only include patterns that are truly common across platforms. Be conservative.
If something only appears on one or two platforms, it's a variation, not a pattern.
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
        
        patterns = json.loads(content)
        
        logger.debug(f"Identified patterns: {json.dumps(patterns, indent=2)}")
        
        return patterns
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"LLM response: {response.content if 'response' in locals() else 'N/A'}")
        # Return empty patterns
        return {
            "packages": [],
            "services": [],
            "files": [],
            "commands": [],
            "ports": []
        }
    except Exception as e:
        logger.error(f"Error identifying patterns: {e}")
        # Return empty patterns
        return {
            "packages": [],
            "services": [],
            "files": [],
            "commands": [],
            "ports": []
        }


async def _identify_variations(
    software: str,
    aggregated_observations: Dict[str, List[Dict[str, Any]]],
    platform_results: List[PlatformResult]
) -> Dict[str, Any]:
    """Use LLM to identify platform-specific and provider-specific variations.
    
    Analyzes observations to find resources that differ between platforms
    or providers, such as different package names, file paths, or configurations.
    
    Args:
        software: Name of the software being analyzed
        aggregated_observations: Observations grouped by type
        platform_results: List of all platform results
    
    Returns:
        Dictionary mapping platform-provider combinations to their variations
    """
    # Build detailed observations by platform-provider
    observations_by_combo = {}
    for result in platform_results:
        combo_key = f"{result.platform}:{result.provider}"
        observations_by_combo[combo_key] = {
            "platform": result.platform,
            "provider": result.provider,
            "success": result.success,
            "observations": [obs.model_dump() for obs in result.observations]
        }
    
    # Build summary for LLM
    combo_summaries = []
    for combo_key, data in observations_by_combo.items():
        obs_counts = defaultdict(int)
        for obs in data["observations"]:
            obs_counts[obs["type"]] += 1
        
        summary = f"{combo_key}: {dict(obs_counts)}"
        combo_summaries.append(summary)
    
    prompt = f"""Analyze the observations from installing "{software}" and identify PLATFORM-SPECIFIC and PROVIDER-SPECIFIC variations.

Observations by platform-provider combination:
{chr(10).join(combo_summaries)}

Detailed observations:
{json.dumps(observations_by_combo, indent=2)}

Identify VARIATIONS that are specific to certain platforms or providers.
Focus on:
1. Different package names for different providers (e.g., nginx vs nginx-full)
2. Different file paths on different platforms
3. Different service configurations
4. Provider-specific installation artifacts
5. Platform-specific dependencies

Return your response as a JSON object mapping each platform-provider combination to its variations:
{{
    "ubuntu:22.04:apt": {{
        "packages": [
            {{
                "name": "nginx",
                "package_name": "nginx-full",
                "version": "1.18.0",
                "description": "Ubuntu uses nginx-full package"
            }}
        ],
        "files": [
            {{
                "path": "/etc/nginx/sites-available/default",
                "purpose": "config",
                "description": "Ubuntu-specific sites-available structure"
            }}
        ]
    }},
    "debian:12:apt": {{
        "packages": [
            {{
                "name": "nginx",
                "package_name": "nginx-light",
                "version": "1.22.1",
                "description": "Debian uses nginx-light package"
            }}
        ]
    }}
}}

Only include actual variations - things that differ from the common patterns.
If a platform-provider combination has no variations, omit it or use an empty object.
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
        
        variations = json.loads(content)
        
        logger.debug(f"Identified variations: {json.dumps(variations, indent=2)}")
        
        return variations
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"LLM response: {response.content if 'response' in locals() else 'N/A'}")
        # Return empty variations
        return {}
    except Exception as e:
        logger.error(f"Error identifying variations: {e}")
        # Return empty variations
        return {}


def _calculate_confidence_scores(
    platform_results: List[PlatformResult],
    patterns: Dict[str, Any],
    variations: Dict[str, Any]
) -> Dict[str, float]:
    """Calculate confidence scores for the analysis results.
    
    Confidence is based on:
    - Number of successful installations
    - Consistency of observations across platforms
    - Number of patterns identified
    - Coverage of expected resources
    
    Args:
        platform_results: List of all platform results
        patterns: Common patterns identified
        variations: Platform-specific variations identified
    
    Returns:
        Dictionary containing various confidence scores
    """
    # Calculate success rate
    total_tests = len(platform_results)
    successful_tests = sum(1 for result in platform_results if result.success)
    success_rate = successful_tests / total_tests if total_tests > 0 else 0.0
    
    # Calculate pattern confidence based on number of patterns found
    pattern_types = ["packages", "services", "files", "commands", "ports"]
    patterns_found = sum(
        1 for ptype in pattern_types
        if patterns.get(ptype) and len(patterns[ptype]) > 0
    )
    pattern_confidence = patterns_found / len(pattern_types)
    
    # Calculate variation confidence based on coverage
    # Higher confidence if we have variations documented for most combinations
    expected_variations = total_tests
    documented_variations = len(variations)
    variation_confidence = min(documented_variations / expected_variations, 1.0) if expected_variations > 0 else 0.0
    
    # Calculate observation consistency
    # Check if observations are consistent across successful tests
    if successful_tests > 1:
        # Count observations by type across successful tests
        obs_counts_by_type = defaultdict(list)
        for result in platform_results:
            if result.success:
                type_counts = defaultdict(int)
                for obs in result.observations:
                    type_counts[obs.type] += 1
                for obs_type, count in type_counts.items():
                    obs_counts_by_type[obs_type].append(count)
        
        # Calculate consistency (lower variance = higher consistency)
        consistency_scores = []
        for obs_type, counts in obs_counts_by_type.items():
            if len(counts) > 1:
                avg = sum(counts) / len(counts)
                variance = sum((c - avg) ** 2 for c in counts) / len(counts)
                # Normalize variance to 0-1 scale (lower is better)
                consistency = 1.0 / (1.0 + variance)
                consistency_scores.append(consistency)
        
        observation_consistency = (
            sum(consistency_scores) / len(consistency_scores)
            if consistency_scores else 0.5
        )
    else:
        observation_consistency = 0.5  # Neutral score with only one test
    
    # Calculate overall confidence as weighted average
    overall_confidence = (
        success_rate * 0.4 +
        pattern_confidence * 0.3 +
        observation_consistency * 0.2 +
        variation_confidence * 0.1
    )
    
    return {
        "success_rate": round(success_rate, 3),
        "pattern_confidence": round(pattern_confidence, 3),
        "variation_confidence": round(variation_confidence, 3),
        "observation_consistency": round(observation_consistency, 3),
        "overall_confidence": round(overall_confidence, 3)
    }


def _build_observation_summary(
    aggregated_observations: Dict[str, List[Dict[str, Any]]]
) -> str:
    """Build a human-readable summary of aggregated observations.
    
    Args:
        aggregated_observations: Observations grouped by type
    
    Returns:
        Formatted string summarizing observations
    """
    summary_lines = []
    
    for obs_type, observations in aggregated_observations.items():
        summary_lines.append(f"\n{obs_type.upper()} ({len(observations)} observations):")
        
        # Group by platform-provider for summary
        by_combo = defaultdict(list)
        for obs in observations:
            combo = f"{obs['platform']}:{obs['provider']}"
            by_combo[combo].append(obs)
        
        for combo, obs_list in by_combo.items():
            # Show sample data from first observation
            if obs_list:
                sample_data = obs_list[0].get("data", {})
                summary_lines.append(f"  - {combo}: {len(obs_list)} items, sample: {sample_data}")
    
    return "\n".join(summary_lines)
