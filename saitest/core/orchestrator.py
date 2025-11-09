"""LangGraph workflow orchestrator for saitest.

This module creates and manages the LangGraph workflow that orchestrates
all agents in the verification process.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
import time

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Note: For production use, consider using SqliteSaver or PostgresSaver
# from langgraph-checkpoint-sqlite or langgraph-checkpoint-postgres packages

from saitest.core.state import VerificationState, create_initial_state
from saitest.agents.discovery import discovery_agent
from saitest.agents.platform import platform_selection_agent
from saitest.agents.installation import installation_agent
from saitest.agents.analysis import analysis_agent
from saitest.agents.generation import generation_agent
from saitest.agents.quality import quality_check_agent
from saitest.utils.logging_config import get_logger, ProgressIndicator, log_exception, log_operation_complete


logger = get_logger(__name__)


def create_verification_workflow(
    checkpoint_dir: Optional[Path] = None
) -> Any:
    """Create the LangGraph workflow for verification.
    
    This function builds the complete workflow graph with all agent nodes
    and routing logic. The workflow follows this structure:
    
    1. Discovery Agent - Identifies installation methods
    2. Platform Selection Agent - Selects platforms to test
    3. Installation Agent - Tests each platform-provider combination
    4. Analysis Agent - Analyzes results across all platforms
    5. Generation Agent - Generates saidata files
    6. Quality Check Agent - Validates and scores results
    
    The workflow includes checkpointing for state persistence, allowing
    the workflow to be resumed if interrupted.
    
    Args:
        checkpoint_dir: Optional directory for workflow checkpointing.
                       If None, uses default .saitest_checkpoints directory.
    
    Returns:
        Compiled workflow graph ready for execution
    """
    logger.info("Creating verification workflow")
    
    # Create the state graph
    workflow = StateGraph(VerificationState)
    
    # Add agent nodes
    workflow.add_node("discovery", discovery_agent)
    workflow.add_node("platform_selection", platform_selection_agent)
    workflow.add_node("installation", installation_agent)
    workflow.add_node("analysis", analysis_agent)
    workflow.add_node("generation", generation_agent)
    workflow.add_node("quality_check", quality_check_agent)
    
    # Set entry point
    workflow.set_entry_point("discovery")
    
    # Add edges
    # Discovery -> Platform Selection (always)
    workflow.add_edge("discovery", "platform_selection")
    
    # Platform Selection -> Installation or Analysis (conditional)
    workflow.add_conditional_edges(
        "platform_selection",
        route_to_platforms,
        {
            "installation": "installation",
            "analysis": "analysis"
        }
    )
    
    # Installation -> Installation or Analysis (conditional - loop for multiple combinations)
    workflow.add_conditional_edges(
        "installation",
        check_more_combinations,
        {
            "installation": "installation",
            "analysis": "analysis"
        }
    )
    
    # Analysis -> Generation (always)
    workflow.add_edge("analysis", "generation")
    
    # Generation -> Quality Check (always)
    workflow.add_edge("generation", "quality_check")
    
    # Quality Check -> END (always)
    workflow.add_conditional_edges(
        "quality_check",
        route_after_quality_check,
        {
            "end": END
        }
    )
    
    logger.info("Workflow structure created with routing logic")
    
    # Configure checkpointing
    # Using MemorySaver for now - for production, consider SqliteSaver or PostgresSaver
    # from langgraph-checkpoint-sqlite or langgraph-checkpoint-postgres packages
    checkpointer = MemorySaver()
    
    if checkpoint_dir is not None:
        logger.info(
            f"Checkpoint directory specified ({checkpoint_dir}) but using MemorySaver. "
            "Install langgraph-checkpoint-sqlite for persistent checkpointing."
        )
    
    logger.info("Configuring in-memory checkpointing")
    
    # Compile workflow with checkpointer
    compiled_workflow = workflow.compile(checkpointer=checkpointer)
    
    logger.info("Workflow compiled with checkpointing enabled")
    
    return compiled_workflow


def route_to_platforms(state: VerificationState) -> str:
    """Route from platform selection to installation or analysis.
    
    If platform-provider combinations exist, route to installation.
    Otherwise, skip to analysis (no platforms to test).
    
    Args:
        state: Current verification state
    
    Returns:
        "installation" if combinations exist, "analysis" otherwise
    """
    combinations = state.get("provider_combinations", [])
    
    if combinations:
        platform, provider = combinations[0]
        
        logger.info(
            f"Routing to installation: {len(combinations)} combinations to test, "
            f"starting with {platform} + {provider}"
        )
        return "installation"
    else:
        logger.warning("No platform-provider combinations to test, skipping to analysis")
        return "analysis"


def check_more_combinations(state: VerificationState) -> str:
    """Check if more platform-provider combinations need testing.
    
    This function determines if there are remaining combinations to test.
    If yes, routes back to installation (which will set the next combination).
    If no, routes to analysis.
    
    Args:
        state: Current verification state
    
    Returns:
        "installation" if more combinations remain, "analysis" otherwise
    """
    # Get all combinations and tested results
    all_combinations = state.get("provider_combinations", [])
    platform_results = state.get("platform_results", [])
    
    # Build set of tested combinations
    tested = {(r.platform, r.provider) for r in platform_results}
    
    # Find remaining combinations
    remaining = [c for c in all_combinations if c not in tested]
    
    if remaining:
        platform, provider = remaining[0]
        
        logger.info(
            f"More combinations to test: {len(remaining)} remaining, "
            f"next is {platform} + {provider}"
        )
        return "installation"
    else:
        logger.info(
            f"All {len(all_combinations)} platform-provider combinations tested, "
            f"routing to analysis"
        )
        return "analysis"


def route_after_quality_check(state: VerificationState) -> str:
    """Route after quality check based on confidence and retry count.
    
    This function decides whether to:
    - End the workflow (confidence is acceptable or max retries reached)
    
    Note: Retry logic is disabled to prevent recursion issues. The workflow
    will complete after the first quality check regardless of confidence.
    
    Args:
        state: Current verification state
    
    Returns:
        "end" to finish workflow
    """
    overall_confidence = state.get("overall_confidence", 0.0)
    
    # Check if confidence is acceptable (>= 0.5)
    if overall_confidence >= 0.5:
        logger.info(
            f"Quality check passed with confidence {overall_confidence:.2f}, "
            f"ending workflow"
        )
    else:
        logger.warning(
            f"Quality check completed with low confidence {overall_confidence:.2f}, "
            f"ending workflow (retry disabled)"
        )
        state["messages"].append(
            f"Completed with low confidence {overall_confidence:.2f} - manual review recommended"
        )
    
    return "end"


async def run_verification(
    software: str,
    platforms: Optional[list] = None,
    config: Optional[Dict[str, Any]] = None
) -> VerificationState:
    """Execute the verification workflow for a software package.
    
    This is the main entry point for running a verification workflow. It:
    1. Creates the workflow graph
    2. Initializes the verification state with input parameters
    3. Invokes the workflow to execute all agents
    4. Returns the final state with results
    
    The workflow will automatically:
    - Discover installation methods
    - Select platforms (or use provided ones)
    - Test installations on each platform-provider combination
    - Analyze results and identify patterns
    - Generate saidata files
    - Perform quality checks
    
    Args:
        software: Name of the software to verify (e.g., "nginx", "apache")
        platforms: Optional list of platform identifiers to test
                  (e.g., ["ubuntu:22.04", "debian:12"])
                  If None, the workflow will select platforms automatically
        config: Optional configuration dictionary with settings:
                - max_retries: Maximum retry attempts (default: 2)
                - checkpoint_dir: Directory for workflow checkpointing
                - input_saidata: Existing saidata for testing
    
    Returns:
        VerificationState containing all results, including:
        - platform_results: Results from each platform-provider test
        - generated_saidata: Generated saidata structure
        - overall_confidence: Confidence score (0.0 to 1.0)
        - validation_errors: Any schema validation errors
        - messages: Log messages from the workflow
    
    Example:
        >>> result = await run_verification("nginx", platforms=["ubuntu:22.04"])
        >>> print(f"Confidence: {result['overall_confidence']}")
        >>> print(f"Platforms tested: {len(result['platform_results'])}")
    """
    logger.info(f"Starting verification workflow for software: {software}")
    
    # Extract configuration
    config = config or {}
    max_retries = config.get("max_retries", 2)
    checkpoint_dir = config.get("checkpoint_dir")
    input_saidata = config.get("input_saidata")
    
    # Create the workflow
    logger.info("Creating verification workflow graph")
    workflow = create_verification_workflow(checkpoint_dir=checkpoint_dir)
    
    # Initialize state
    logger.info(f"Initializing verification state for {software}")
    initial_state = create_initial_state(
        software=software,
        target_platforms=platforms,
        input_saidata=input_saidata,
        max_retries=max_retries
    )
    
    logger.info(
        f"Configuration: max_retries={max_retries}, "
        f"target_platforms={platforms or 'auto-select'}"
    )
    
    # Invoke workflow with progress tracking
    logger.info("Invoking workflow - starting agent execution")
    workflow_start = time.time()
    
    try:
        with ProgressIndicator("Verification workflow", logger) as progress:
            # Run the workflow with the initial state
            # The workflow will execute all agents and return the final state
            # Provide a thread_id for checkpointing
            config_dict = {"configurable": {"thread_id": f"verify-{software}"}}
            
            progress.update("Discovering installation methods...")
            final_state = await workflow.ainvoke(initial_state, config=config_dict)
            
            workflow_duration = time.time() - workflow_start
            
            log_operation_complete(
                logger,
                "Verification workflow",
                success=True,
                duration=workflow_duration,
                confidence=final_state.get('overall_confidence', 0.0),
                platforms_tested=len(final_state.get('platform_results', []))
            )
        
        return final_state
        
    except KeyboardInterrupt:
        logger.warning("Workflow interrupted by user")
        error_state = initial_state.copy()
        error_state["messages"].append("Workflow interrupted by user")
        error_state["overall_confidence"] = 0.0
        error_state["needs_human_review"] = True
        return error_state
        
    except Exception as e:
        workflow_duration = time.time() - workflow_start
        log_exception(logger, "Workflow execution failed", e, include_traceback=True)
        log_operation_complete(
            logger,
            "Verification workflow",
            success=False,
            duration=workflow_duration
        )
        
        # Return state with error information
        error_state = initial_state.copy()
        error_state["messages"].append(f"Workflow failed with error: {type(e).__name__}: {str(e)}")
        error_state["overall_confidence"] = 0.0
        error_state["needs_human_review"] = True
        
        return error_state
