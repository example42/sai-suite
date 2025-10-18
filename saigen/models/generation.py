"""Pydantic models for generation requests and responses."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .repository import RepositoryPackage
from .saidata import SaiData


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    VLLM = "vllm"


class GenerationMode(str, Enum):
    """Generation modes."""

    CREATE = "create"
    UPDATE = "update"
    ENHANCE = "enhance"


class GenerationRequest(BaseModel):
    """Request for saidata generation."""

    software_name: str
    target_providers: List[str] = Field(default_factory=list)
    llm_provider: LLMProvider = LLMProvider.OPENAI
    use_rag: bool = True
    user_hints: Optional[Dict[str, Any]] = None
    output_path: Optional[Path] = None
    update_mode: bool = False
    generation_mode: GenerationMode = GenerationMode.CREATE
    existing_saidata: Optional[SaiData] = None

    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)


class GenerationContext(BaseModel):
    """Context data for LLM generation."""

    software_name: str
    repository_data: List[RepositoryPackage] = Field(default_factory=list)
    similar_saidata: List[SaiData] = Field(default_factory=list)
    sample_saidata: List[SaiData] = Field(default_factory=list)
    user_hints: Optional[Dict[str, Any]] = None
    target_providers: List[str] = Field(default_factory=list)
    existing_saidata: Optional[SaiData] = None

    # Enhanced context fields for 0.3 schema generation
    installation_method_examples: Optional[Dict[str, Any]] = None
    likely_installation_methods: Optional[List[str]] = None
    security_metadata_template: Optional[Dict[str, Any]] = None
    software_category: Optional[str] = None
    compatibility_matrix_template: Optional[List[Dict[str, Any]]] = None
    url_templating_examples: Optional[Dict[str, Any]] = None
    provider_enhancement_examples: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(validate_assignment=True, extra="allow")


class ValidationError(BaseModel):
    """Validation error details."""

    field: str
    message: str
    severity: str = "error"  # error, warning, info
    suggestion: Optional[str] = None


class GenerationResult(BaseModel):
    """Result of saidata generation."""

    success: bool
    saidata: Optional[SaiData] = None
    validation_errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    generation_time: float
    llm_provider_used: str
    repository_sources_used: List[str] = Field(default_factory=list)
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None

    model_config = ConfigDict(validate_assignment=True)


class BatchGenerationRequest(BaseModel):
    """Request for batch saidata generation."""

    software_list: List[str]
    target_providers: List[str] = Field(default_factory=list)
    llm_provider: LLMProvider = LLMProvider.OPENAI
    use_rag: bool = True
    output_directory: Optional[Path] = None
    max_concurrent: int = 3
    continue_on_error: bool = True
    category_filter: Optional[str] = None
    force: bool = False

    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)


class BatchGenerationResult(BaseModel):
    """Result of batch saidata generation."""

    total_requested: int
    successful: int
    failed: int
    results: List[GenerationResult] = Field(default_factory=list)
    failed_software: List[str] = Field(default_factory=list)
    total_time: float
    average_time_per_item: float

    model_config = ConfigDict(validate_assignment=True)


# Backward compatibility aliases for tests
BatchResult = BatchGenerationResult


class BatchProgress(BaseModel):
    """Progress tracking for batch operations."""

    total: int
    completed: int
    successful: int
    failed: int
    current_item: Optional[str] = None
    elapsed_time: float = 0.0
    estimated_remaining: Optional[float] = None

    model_config = ConfigDict(validate_assignment=True)


class BatchError(Exception):
    """Base exception for batch processing errors."""


class BatchProcessingError(BatchError):
    """Error during batch processing."""

    def __init__(self, message: str, software_name: Optional[str] = None):
        if software_name:
            message = f"{message} (software: {software_name})"
        super().__init__(message)
        self.software_name = software_name
