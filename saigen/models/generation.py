"""Pydantic models for generation requests and responses."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from pathlib import Path
from datetime import datetime
from enum import Enum

from .saidata import SaiData
from .repository import RepositoryPackage


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


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
    user_hints: Optional[Dict[str, Any]] = None
    target_providers: List[str] = Field(default_factory=list)
    existing_saidata: Optional[SaiData] = None
    
    model_config = ConfigDict(validate_assignment=True)


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