"""Core state management for saitest verification workflow.

This module defines the VerificationState TypedDict that is passed between
all agents in the LangGraph workflow.
"""

from typing import TypedDict, Optional, List, Dict, Tuple, Any


class VerificationState(TypedDict, total=False):
    """Central state object passed between all agents in the workflow.
    
    This TypedDict defines the complete state structure for the verification
    workflow. It tracks all information from discovery through generation,
    including platform results, analysis, and quality metrics.
    
    Input Fields:
        software: Name of the software to verify
        input_saidata: Optional existing saidata for testing
        target_platforms: Optional list of platforms to test
    
    Discovery Fields:
        discovery_complete: Whether discovery phase completed successfully
        installation_methods: List of available installation providers
        expected_services: List of expected service names
        expected_files: List of expected file paths
        expected_ports: List of expected port numbers
    
    Platform Fields:
        selected_platforms: List of platforms selected for testing
        current_platform: Currently active platform being tested
    
    Provider Fields:
        current_provider: Currently active provider being tested
        provider_combinations: List of (platform, provider) tuples to test
        package_versions: Dictionary mapping provider to version string
        expected_dependencies: Dictionary mapping provider to list of dependencies
    
    Results Fields:
        platform_results: List of PlatformResult objects from all tests
    
    Analysis Fields:
        aggregated_observations: Observations grouped by type
        patterns: Common patterns identified across platforms
        variations: Platform-specific variations
    
    Generation Fields:
        generated_saidata: Generated saidata structure
        confidence_scores: Confidence scores for generated data
    
    Quality Fields:
        validation_errors: List of schema validation errors
        completeness_score: Score for data completeness (0.0 to 1.0)
        accuracy_score: Score for data accuracy (0.0 to 1.0)
        overall_confidence: Overall confidence in results (0.0 to 1.0)
    
    Control Fields:
        retry_count: Number of retries attempted
        max_retries: Maximum number of retries allowed
        needs_human_review: Whether results need human review
    
    Metadata Fields:
        start_time: Workflow start timestamp
        messages: List of log messages
    """
    
    # Input fields
    software: str
    input_saidata: Optional[Dict[str, Any]]
    target_platforms: Optional[List[str]]
    
    # Discovery fields
    discovery_complete: bool
    installation_methods: List[str]
    expected_services: List[str]
    expected_files: List[str]
    expected_ports: List[int]
    
    # Platform fields
    selected_platforms: List[str]
    current_platform: Optional[str]
    
    # Provider fields
    current_provider: Optional[str]
    provider_combinations: List[Tuple[str, str]]
    package_versions: Dict[str, str]
    expected_dependencies: Dict[str, List[str]]
    
    # Results fields
    platform_results: List[Any]  # List[PlatformResult] - using Any to avoid circular import
    
    # Analysis fields
    aggregated_observations: Dict[str, List[Any]]  # Dict[str, List[Observation]]
    patterns: Dict[str, Any]
    variations: Dict[str, Any]
    
    # Generation fields
    generated_saidata: Optional[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    
    # Quality fields
    validation_errors: List[str]
    completeness_score: float
    accuracy_score: float
    overall_confidence: float
    
    # Control fields
    retry_count: int
    max_retries: int
    needs_human_review: bool
    
    # Metadata fields
    start_time: str
    messages: List[str]


def create_initial_state(
    software: str,
    target_platforms: Optional[List[str]] = None,
    input_saidata: Optional[Dict[str, Any]] = None,
    max_retries: int = 2
) -> VerificationState:
    """Create an initial VerificationState with default values.
    
    Args:
        software: Name of the software to verify
        target_platforms: Optional list of platforms to test
        input_saidata: Optional existing saidata for testing
        max_retries: Maximum number of retries allowed (default: 2)
    
    Returns:
        VerificationState with initialized fields
    """
    from datetime import datetime
    
    state: VerificationState = {
        # Input fields
        "software": software,
        "input_saidata": input_saidata,
        "target_platforms": target_platforms,
        
        # Discovery fields
        "discovery_complete": False,
        "installation_methods": [],
        "expected_services": [],
        "expected_files": [],
        "expected_ports": [],
        
        # Platform fields
        "selected_platforms": [],
        "current_platform": None,
        
        # Provider fields
        "current_provider": None,
        "provider_combinations": [],
        "package_versions": {},
        "expected_dependencies": {},
        
        # Results fields
        "platform_results": [],
        
        # Analysis fields
        "aggregated_observations": {},
        "patterns": {},
        "variations": {},
        
        # Generation fields
        "generated_saidata": None,
        "confidence_scores": {},
        
        # Quality fields
        "validation_errors": [],
        "completeness_score": 0.0,
        "accuracy_score": 0.0,
        "overall_confidence": 0.0,
        
        # Control fields
        "retry_count": 0,
        "max_retries": max_retries,
        "needs_human_review": False,
        
        # Metadata fields
        "start_time": datetime.utcnow().isoformat() + "Z",
        "messages": []
    }
    
    return state
