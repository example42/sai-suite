"""Quality Check Agent for saitest.

This agent validates and assesses the quality of generated saidata by:
1. Validating against schema 0.3 using jsonschema
2. Using LLM to assess completeness and accuracy
3. Calculating completeness_score, accuracy_score, and overall_confidence
4. Setting needs_human_review flag based on confidence threshold
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import jsonschema
from jsonschema import Draft7Validator
import yaml
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from saitest.core.state import VerificationState


logger = logging.getLogger(__name__)


# Confidence threshold for human review
CONFIDENCE_THRESHOLD = 0.7


async def quality_check_agent(state: VerificationState) -> VerificationState:
    """Quality check agent that validates and assesses generated saidata.
    
    This agent:
    1. Validates generated saidata against schema 0.3 using jsonschema
    2. Uses LLM to assess completeness and accuracy
    3. Calculates completeness_score, accuracy_score, and overall_confidence
    4. Sets needs_human_review flag if confidence is below threshold or validation errors exist
    
    Args:
        state: Current verification state with generated_saidata
    
    Returns:
        Updated verification state with quality metrics
    """
    software = state["software"]
    generated_saidata = state.get("generated_saidata")
    
    if not generated_saidata:
        logger.error(f"No generated saidata found for {software}")
        state["messages"].append("Quality check failed: No saidata to validate")
        state["validation_errors"] = ["No generated saidata available"]
        state["completeness_score"] = 0.0
        state["accuracy_score"] = 0.0
        state["overall_confidence"] = 0.0
        state["needs_human_review"] = True
        return state
    
    logger.info(f"Starting quality check for {software}")
    
    # Step 1: Schema validation
    validation_errors = await _validate_against_schema(generated_saidata)
    
    if validation_errors:
        logger.warning(
            f"Found {len(validation_errors)} schema validation errors for {software}"
        )
        for error in validation_errors[:5]:  # Log first 5 errors
            logger.warning(f"  - {error}")
    else:
        logger.info(f"Schema validation passed for {software}")
    
    state["validation_errors"] = validation_errors
    
    # Step 2: LLM quality assessment
    quality_scores = await _assess_quality_with_llm(state)
    
    if quality_scores:
        state["completeness_score"] = quality_scores["completeness"]
        state["accuracy_score"] = quality_scores["accuracy"]
        state["overall_confidence"] = quality_scores["overall"]
        
        logger.info(
            f"Quality scores for {software}: "
            f"completeness={quality_scores['completeness']:.2f}, "
            f"accuracy={quality_scores['accuracy']:.2f}, "
            f"overall={quality_scores['overall']:.2f}"
        )
    else:
        # Failed to get LLM assessment, use conservative scores
        logger.warning(f"Failed to get LLM quality assessment for {software}")
        state["completeness_score"] = 0.5
        state["accuracy_score"] = 0.5
        state["overall_confidence"] = 0.5
    
    # Step 3: Determine if human review is needed
    needs_review = (
        state["overall_confidence"] < CONFIDENCE_THRESHOLD or
        len(validation_errors) > 0
    )
    
    state["needs_human_review"] = needs_review
    
    if needs_review:
        reasons = []
        if state["overall_confidence"] < CONFIDENCE_THRESHOLD:
            reasons.append(
                f"low confidence ({state['overall_confidence']:.2f} < {CONFIDENCE_THRESHOLD})"
            )
        if validation_errors:
            reasons.append(f"{len(validation_errors)} validation errors")
        
        logger.warning(
            f"Human review needed for {software}: {', '.join(reasons)}"
        )
        state["messages"].append(
            f"Quality check complete: Human review needed ({', '.join(reasons)})"
        )
    else:
        logger.info(f"Quality check passed for {software}, no human review needed")
        state["messages"].append(
            f"Quality check complete: Confidence {state['overall_confidence']:.2f}, "
            f"no human review needed"
        )
    
    return state


async def _validate_against_schema(
    generated_saidata: Dict[str, Any]
) -> List[str]:
    """Validate generated saidata against schema 0.3 using jsonschema.
    
    Args:
        generated_saidata: Dictionary with 'default' and 'overrides' keys
    
    Returns:
        List of validation error messages (empty if valid)
    """
    validation_errors = []
    
    # Load schema
    schema_path = Path("schemas/saidata-0.3-schema.json")
    
    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        return ["Schema file not found: schemas/saidata-0.3-schema.json"]
    
    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load schema: {e}")
        return [f"Failed to load schema: {e}"]
    
    # Create validator
    validator = Draft7Validator(schema)
    
    # Validate default saidata
    default_data = generated_saidata.get("default")
    if default_data:
        try:
            errors = list(validator.iter_errors(default_data))
            for error in errors:
                # Format error message with path
                path = ".".join(str(p) for p in error.path) if error.path else "root"
                validation_errors.append(
                    f"default.yaml: {path}: {error.message}"
                )
        except Exception as e:
            logger.error(f"Error validating default saidata: {e}")
            validation_errors.append(f"default.yaml: Validation error: {e}")
    
    # Validate OS-specific overrides
    overrides = generated_saidata.get("overrides", {})
    for os_name, versions in overrides.items():
        for version, override_data in versions.items():
            try:
                errors = list(validator.iter_errors(override_data))
                for error in errors:
                    path = ".".join(str(p) for p in error.path) if error.path else "root"
                    validation_errors.append(
                        f"{os_name}/{version}.yaml: {path}: {error.message}"
                    )
            except Exception as e:
                logger.error(
                    f"Error validating {os_name}/{version} override: {e}"
                )
                validation_errors.append(
                    f"{os_name}/{version}.yaml: Validation error: {e}"
                )
    
    return validation_errors


async def _assess_quality_with_llm(
    state: VerificationState
) -> Optional[Dict[str, float]]:
    """Use LLM to assess completeness and accuracy of generated saidata.
    
    Args:
        state: Current verification state with generated_saidata and observations
    
    Returns:
        Dictionary with 'completeness', 'accuracy', and 'overall' scores (0.0 to 1.0),
        or None if assessment fails
    """
    software = state["software"]
    generated_saidata = state.get("generated_saidata", {})
    platform_results = state.get("platform_results", [])
    patterns = state.get("patterns", {})
    variations = state.get("variations", {})
    
    # Build context for LLM
    default_data = generated_saidata.get("default", {})
    overrides = generated_saidata.get("overrides", {})
    
    # Count observations
    total_observations = sum(len(result.observations) for result in platform_results)
    
    # Summarize what was tested
    tested_combinations = [
        f"{result.platform} with {result.provider} ({'success' if result.success else 'failed'})"
        for result in platform_results
    ]
    
    prompt = f"""Assess the quality of generated saidata for "{software}".

GENERATED SAIDATA:
Default configuration:
{yaml.dump(default_data, default_flow_style=False)}

OS-specific overrides: {len(overrides)} OS families, {sum(len(v) for v in overrides.values())} total files

VERIFICATION CONTEXT:
- Tested on {len(platform_results)} platform-provider combinations
- Collected {total_observations} observations
- Identified {len(patterns)} common patterns
- Identified {len(variations)} platform-specific variations

Tested combinations:
{chr(10).join(f"- {combo}" for combo in tested_combinations)}

ASSESSMENT CRITERIA:

1. COMPLETENESS (0.0 to 1.0):
   - Are all essential resources documented (packages, services, files, commands, ports)?
   - Are provider-specific overrides included where needed?
   - Are OS-specific overrides included for platform variations?
   - Is metadata complete (name, description, etc.)?
   - Score 1.0 if comprehensive, 0.5 if basic, 0.0 if minimal

2. ACCURACY (0.0 to 1.0):
   - Do the documented resources match what was observed during testing?
   - Are package names correct for each provider?
   - Are file paths accurate?
   - Are service names correct?
   - Score 1.0 if highly accurate, 0.5 if mostly accurate, 0.0 if inaccurate

3. OVERALL CONFIDENCE (0.0 to 1.0):
   - How confident are you that this saidata will work correctly?
   - Consider completeness, accuracy, and test coverage
   - Score 1.0 if very confident, 0.7 if moderately confident, 0.5 if uncertain, 0.0 if not confident

Return your assessment as a JSON object:
{{
    "completeness": 0.85,
    "accuracy": 0.90,
    "overall": 0.87,
    "reasoning": "Brief explanation of scores"
}}

Be objective and critical. If something is missing or questionable, reflect that in the scores.
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
        
        assessment = json.loads(content)
        
        # Validate scores are in range
        completeness = float(assessment.get("completeness", 0.5))
        accuracy = float(assessment.get("accuracy", 0.5))
        overall = float(assessment.get("overall", 0.5))
        
        # Clamp to valid range
        completeness = max(0.0, min(1.0, completeness))
        accuracy = max(0.0, min(1.0, accuracy))
        overall = max(0.0, min(1.0, overall))
        
        reasoning = assessment.get("reasoning", "")
        if reasoning:
            logger.info(f"LLM quality assessment reasoning: {reasoning}")
        
        return {
            "completeness": completeness,
            "accuracy": accuracy,
            "overall": overall
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM quality assessment as JSON: {e}")
        logger.debug(f"LLM response: {response.content if 'response' in locals() else 'N/A'}")
        return None
    except Exception as e:
        logger.error(f"Error during LLM quality assessment: {e}")
        return None
