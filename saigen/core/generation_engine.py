"""Core generation engine for orchestrating saidata creation."""

import asyncio
import logging
import time
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from ..models.generation import (
    GenerationRequest, 
    GenerationResult, 
    GenerationContext,
    ValidationError as GenValidationError,
    LLMProvider
)
from ..models.saidata import SaiData
from ..models.repository import RepositoryPackage
from ..llm.providers.base import BaseLLMProvider, LLMProviderError
from ..llm.providers.openai import OpenAIProvider
from .validator import SaidataValidator, ValidationResult, ValidationSeverity


logger = logging.getLogger(__name__)


class GenerationEngineError(Exception):
    """Base exception for generation engine errors."""
    pass


class ProviderNotAvailableError(GenerationEngineError):
    """LLM provider is not available or configured."""
    pass


class ValidationFailedError(GenerationEngineError):
    """Generated saidata failed validation."""
    pass


class GenerationEngine:
    """Core engine for orchestrating saidata creation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize generation engine.
        
        Args:
            config: Engine configuration dictionary
        """
        self.config = config or {}
        self.validator = SaidataValidator()
        self._llm_providers: Dict[str, BaseLLMProvider] = {}
        self._initialize_providers()
        
        # Generation tracking
        self._generation_count = 0
        self._total_tokens_used = 0
        self._total_cost = 0.0
    
    def _initialize_providers(self) -> None:
        """Initialize available LLM providers."""
        providers_config = self.config.get("llm_providers", {})
        
        # Initialize OpenAI provider if configured
        openai_config = providers_config.get("openai", {})
        if openai_config.get("api_key"):
            try:
                self._llm_providers["openai"] = OpenAIProvider(openai_config)
                logger.info("OpenAI provider initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")
        
        # Additional providers (Anthropic, Ollama) can be added here when implemented
        
        if not self._llm_providers:
            logger.warning("No LLM providers available")
    
    async def generate_saidata(self, request: GenerationRequest) -> GenerationResult:
        """Generate saidata based on the request.
        
        Args:
            request: Generation request with software name and parameters
            
        Returns:
            GenerationResult with success status and generated saidata
            
        Raises:
            GenerationEngineError: If generation fails
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting saidata generation for '{request.software_name}'")
            
            # Validate request
            self._validate_request(request)
            
            # Get LLM provider
            provider = self._get_llm_provider(request.llm_provider)
            
            # Build generation context
            context = await self._build_generation_context(request)
            
            # Generate saidata using LLM
            llm_response = await provider.generate_saidata(context)
            
            # Parse and validate generated YAML
            saidata = await self._parse_and_validate_yaml(
                llm_response.content, 
                request.software_name
            )
            
            # Track generation metrics
            self._update_metrics(llm_response)
            
            generation_time = time.time() - start_time
            
            result = GenerationResult(
                success=True,
                saidata=saidata,
                validation_errors=[],
                warnings=[],
                generation_time=generation_time,
                llm_provider_used=provider.get_provider_name(),
                repository_sources_used=self._get_repository_sources(context),
                tokens_used=llm_response.tokens_used,
                cost_estimate=llm_response.cost_estimate
            )
            
            logger.info(f"Successfully generated saidata for '{request.software_name}' in {generation_time:.2f}s")
            return result
            
        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Failed to generate saidata for '{request.software_name}': {e}")
            
            return GenerationResult(
                success=False,
                saidata=None,
                validation_errors=[GenValidationError(
                    field="generation",
                    message=str(e),
                    severity="error"
                )],
                warnings=[],
                generation_time=generation_time,
                llm_provider_used=request.llm_provider.value if hasattr(request.llm_provider, 'value') else request.llm_provider,
                repository_sources_used=[]
            )
    
    def _validate_request(self, request: GenerationRequest) -> None:
        """Validate generation request.
        
        Args:
            request: Generation request to validate
            
        Raises:
            GenerationEngineError: If request is invalid
        """
        if not request.software_name or not request.software_name.strip():
            raise GenerationEngineError("Software name is required")
        
        # Handle both enum and string values for llm_provider
        provider_name = request.llm_provider.value if hasattr(request.llm_provider, 'value') else request.llm_provider
        
        if provider_name not in self._llm_providers:
            available_providers = list(self._llm_providers.keys())
            raise ProviderNotAvailableError(
                f"LLM provider '{provider_name}' not available. "
                f"Available providers: {available_providers}"
            )
    
    def _get_llm_provider(self, provider_name: Union[LLMProvider, str]) -> BaseLLMProvider:
        """Get LLM provider instance.
        
        Args:
            provider_name: Name of the LLM provider (enum or string)
            
        Returns:
            BaseLLMProvider instance
            
        Raises:
            ProviderNotAvailableError: If provider is not available
        """
        # Handle both enum and string values
        name = provider_name.value if hasattr(provider_name, 'value') else provider_name
        
        provider = self._llm_providers.get(name)
        if not provider:
            raise ProviderNotAvailableError(f"LLM provider '{name}' not available")
        
        if not provider.is_available():
            raise ProviderNotAvailableError(f"LLM provider '{name}' not properly configured")
        
        return provider
    
    async def _build_generation_context(self, request: GenerationRequest) -> GenerationContext:
        """Build generation context from request.
        
        Args:
            request: Generation request
            
        Returns:
            GenerationContext with all necessary data
        """
        context = GenerationContext(
            software_name=request.software_name,
            target_providers=request.target_providers or ["apt", "brew", "winget"],
            user_hints=request.user_hints,
            existing_saidata=request.existing_saidata
        )
        
        # Repository data integration will be added when repository system is implemented
        # Future: RAG integration for enhanced context
        # if request.use_rag:
        #     context.repository_data = await self._get_repository_data(request.software_name)
        #     context.similar_saidata = await self._get_similar_saidata(request.software_name)
        
        return context
    
    async def _parse_and_validate_yaml(self, yaml_content: str, software_name: str) -> SaiData:
        """Parse and validate generated YAML content.
        
        Args:
            yaml_content: Generated YAML content
            software_name: Software name for error reporting
            
        Returns:
            Validated SaiData instance
            
        Raises:
            ValidationFailedError: If validation fails
        """
        try:
            # Parse YAML
            data = yaml.safe_load(yaml_content)
            if not isinstance(data, dict):
                raise ValidationFailedError("Generated content is not a valid YAML dictionary")
            
            # Validate against schema
            validation_result = self.validator.validate_data(data, f"generated:{software_name}")
            
            if not validation_result.is_valid:
                error_messages = [error.message for error in validation_result.errors]
                raise ValidationFailedError(f"Schema validation failed: {'; '.join(error_messages)}")
            
            # Convert to Pydantic model
            saidata = SaiData(**data)
            
            # Additional validation of the Pydantic model
            model_validation = self.validator.validate_pydantic_model(saidata)
            if not model_validation.is_valid:
                error_messages = [error.message for error in model_validation.errors]
                raise ValidationFailedError(f"Model validation failed: {'; '.join(error_messages)}")
            
            return saidata
            
        except yaml.YAMLError as e:
            raise ValidationFailedError(f"Invalid YAML syntax: {e}")
        except Exception as e:
            if isinstance(e, ValidationFailedError):
                raise
            raise ValidationFailedError(f"Validation error: {e}")
    
    def _get_repository_sources(self, context: GenerationContext) -> List[str]:
        """Get list of repository sources used in context.
        
        Args:
            context: Generation context
            
        Returns:
            List of repository source names
        """
        sources = []
        for package in context.repository_data:
            if package.repository_name not in sources:
                sources.append(package.repository_name)
        return sources
    
    def _update_metrics(self, llm_response) -> None:
        """Update generation metrics.
        
        Args:
            llm_response: LLM response with usage data
        """
        self._generation_count += 1
        
        if llm_response.tokens_used:
            self._total_tokens_used += llm_response.tokens_used
        
        if llm_response.cost_estimate:
            self._total_cost += llm_response.cost_estimate
    
    async def save_saidata(self, saidata: SaiData, output_path: Path) -> None:
        """Save saidata to file.
        
        Args:
            saidata: SaiData instance to save
            output_path: Path to save the file
            
        Raises:
            GenerationEngineError: If saving fails
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict and save as YAML
            data = saidata.model_dump(exclude_none=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)
            
            logger.info(f"Saved saidata to {output_path}")
            
        except Exception as e:
            raise GenerationEngineError(f"Failed to save saidata to {output_path}: {e}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available LLM providers.
        
        Returns:
            List of provider names
        """
        return [name for name, provider in self._llm_providers.items() if provider.is_available()]
    
    def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider information dictionary or None if not found
        """
        provider = self._llm_providers.get(provider_name)
        if not provider:
            return None
        
        model_info = provider.get_model_info()
        return {
            "name": provider_name,
            "available": provider.is_available(),
            "model": model_info.name,
            "max_tokens": model_info.max_tokens,
            "context_window": model_info.context_window,
            "capabilities": [cap.value for cap in model_info.capabilities],
            "cost_per_1k_tokens": model_info.cost_per_1k_tokens,
            "supports_streaming": model_info.supports_streaming
        }
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get generation statistics.
        
        Returns:
            Dictionary with generation statistics
        """
        return {
            "total_generations": self._generation_count,
            "total_tokens_used": self._total_tokens_used,
            "total_cost_estimate": self._total_cost,
            "average_tokens_per_generation": (
                self._total_tokens_used / self._generation_count 
                if self._generation_count > 0 else 0
            ),
            "average_cost_per_generation": (
                self._total_cost / self._generation_count 
                if self._generation_count > 0 else 0
            )
        }
    
    async def validate_saidata_file(self, file_path: Path) -> ValidationResult:
        """Validate an existing saidata file.
        
        Args:
            file_path: Path to saidata file
            
        Returns:
            ValidationResult with validation details
        """
        return self.validator.validate_file(file_path)
    
    def format_validation_report(self, result: ValidationResult, show_context: bool = False) -> str:
        """Format validation result as human-readable report.
        
        Args:
            result: ValidationResult to format
            show_context: Whether to include detailed context
            
        Returns:
            Formatted validation report
        """
        return self.validator.format_validation_report(result, show_context)