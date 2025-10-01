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
from ..llm.provider_manager import LLMProviderManager
from ..llm.providers.openai import OpenAIProvider
from .validator import SaidataValidator, ValidationResult, ValidationSeverity
from ..repositories.indexer import RAGIndexer, RAGContextBuilder
from ..repositories.cache import RepositoryCache
from ..utils.errors import RAGError
from .context_builder_v03 import EnhancedContextBuilderV03


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
    
    def __init__(self, config = None):
        """Initialize generation engine.
        
        Args:
            config: Engine configuration (SaigenConfig instance or dict)
        """
        # Handle both Pydantic model and dict config
        if hasattr(config, 'model_dump'):
            # Pydantic model
            self.config = config.model_dump()
            self.config_obj = config
        else:
            # Dictionary or None
            self.config = config or {}
            self.config_obj = None
        
        self.validator = SaidataValidator()
        
        # Initialize LLM provider manager
        llm_config = self.config.get("llm_providers", {})
        self.provider_manager = LLMProviderManager(llm_config)
        
        # Initialize RAG components
        self.rag_indexer: Optional[RAGIndexer] = None
        self.rag_context_builder: Optional[RAGContextBuilder] = None
        self.repository_cache: Optional[RepositoryCache] = None
        self._initialize_rag_components()
        
        # Initialize enhanced context builder for 0.3 schema
        self.enhanced_context_builder = EnhancedContextBuilderV03(self.rag_context_builder)
        
        # Backward compatibility: expose providers dict for tests
        self._llm_providers = {}
        self._initialize_providers()
        
        # Generation tracking
        self._generation_count = 0
        self._total_tokens_used = 0
        self._total_cost = 0.0
        
        # Generation logger
        self.logger: Optional['GenerationLogger'] = None
    
    def set_logger(self, logger: 'GenerationLogger') -> None:
        """Set the generation logger.
        
        Args:
            logger: GenerationLogger instance
        """
        self.logger = logger
    
    async def generate_saidata(self, request: GenerationRequest) -> GenerationResult:
        """Generate saidata based on the request using 0.3 schema.
        
        Args:
            request: Generation request with software name and parameters
            
        Returns:
            GenerationResult with success status and generated saidata
            
        Raises:
            GenerationEngineError: If generation fails
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting saidata generation for '{request.software_name}' using 0.3 schema")
            
            if self.logger:
                with self.logger.log_step("validate_request", "Validating generation request"):
                    # Validate request
                    self._validate_request(request)
            else:
                # Validate request
                self._validate_request(request)
            
            # Build enhanced generation context for 0.3 schema
            if self.logger:
                with self.logger.log_step("build_context", "Building enhanced generation context for 0.3 schema") as step:
                    context = await self._build_enhanced_generation_context_v03(request)
                    self.logger.log_generation_context(context)
            else:
                context = await self._build_enhanced_generation_context_v03(request)
            
            # Generate saidata using LLM with fallback
            provider_name = request.llm_provider.value if hasattr(request.llm_provider, 'value') else request.llm_provider
            
            if self.logger:
                with self.logger.log_step("llm_generation", f"Generating saidata using {provider_name}"):
                    # For backward compatibility with tests, use mocked providers if available
                    if provider_name in self._llm_providers:
                        mock_provider = self._llm_providers[provider_name]
                        llm_response = await mock_provider.generate_saidata(context)
                    else:
                        llm_response = await self._generate_with_logged_llm(context, provider_name)
            else:
                # For backward compatibility with tests, use mocked providers if available
                if provider_name in self._llm_providers:
                    mock_provider = self._llm_providers[provider_name]
                    llm_response = await mock_provider.generate_saidata(context)
                else:
                    llm_response = await self.provider_manager.generate_with_fallback(
                        context=context,
                        preferred_provider=provider_name
                    )
            
            # Parse and validate generated YAML
            if self.logger:
                with self.logger.log_step("parse_validate", "Parsing and validating generated YAML"):
                    saidata = await self._parse_and_validate_yaml(
                        llm_response.content, 
                        request.software_name,
                        context,
                        provider_name
                    )
            else:
                saidata = await self._parse_and_validate_yaml(
                    llm_response.content, 
                    request.software_name,
                    context,
                    provider_name
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
                llm_provider_used=provider_name,
                repository_sources_used=self._get_repository_sources(context),
                tokens_used=llm_response.tokens_used,
                cost_estimate=llm_response.cost_estimate
            )
            
            logger.info(f"Successfully generated saidata for '{request.software_name}' in {generation_time:.2f}s")
            return result
            
        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Failed to generate saidata for '{request.software_name}': {e}")
            
            if self.logger:
                self.logger.log_error(f"Generation failed: {e}")
            
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
        
        # Check if any providers are available
        available_providers = self.provider_manager.get_available_providers()
        
        # Also check mocked providers for backward compatibility
        if self._llm_providers:
            available_providers.extend(list(self._llm_providers.keys()))
        
        if not available_providers:
            raise ProviderNotAvailableError("No LLM providers are available or configured")
        
        # Check if the specific requested provider is available
        provider_name = request.llm_provider.value if hasattr(request.llm_provider, 'value') else request.llm_provider
        if provider_name not in available_providers:
            raise ProviderNotAvailableError(f"Requested provider '{provider_name}' is not available")
    

    
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
        
        # RAG integration for enhanced context
        if request.use_rag and self.rag_context_builder:
            try:
                if self.logger:
                    with self.logger.log_data_op("rag_query", f"Building RAG context for {request.software_name}") as log_output:
                        rag_context = await self.rag_context_builder.build_context(
                            software_name=request.software_name,
                            target_providers=request.target_providers,
                            max_packages=5,
                            max_saidata=3
                        )
                        
                        # Log the RAG results
                        log_output({
                            "similar_packages_count": len(rag_context.get('similar_packages', [])),
                            "similar_saidata_count": len(rag_context.get('similar_saidata', [])),
                            "sample_saidata_count": len(rag_context.get('sample_saidata', []))
                        })
                else:
                    rag_context = await self.rag_context_builder.build_context(
                        software_name=request.software_name,
                        target_providers=request.target_providers,
                        max_packages=5,
                        max_saidata=3
                    )
                
                # Inject RAG data into context
                context.repository_data = rag_context.get('similar_packages', [])
                context.similar_saidata = rag_context.get('similar_saidata', [])
                context.sample_saidata = rag_context.get('sample_saidata', [])
                
                logger.debug(f"RAG context built: {len(context.repository_data)} packages, {len(context.similar_saidata)} similar saidata, {len(context.sample_saidata)} sample saidata")
                
            except Exception as e:
                logger.warning(f"Failed to build RAG context for {request.software_name}: {e}")
                if self.logger:
                    self.logger.log_error(f"RAG context building failed: {e}")
                # Continue without RAG context
        
        return context
    
    async def _build_enhanced_generation_context_v03(self, request: GenerationRequest) -> GenerationContext:
        """Build enhanced generation context for saidata 0.3 schema.
        
        Args:
            request: Generation request
            
        Returns:
            Enhanced GenerationContext with 0.3-specific data
        """
        # Start with base context
        context = await self._build_generation_context(request)
        
        # Enhance with 0.3-specific features
        try:
            if self.logger:
                with self.logger.log_step("enhance_context_v03", "Enhancing context for 0.3 schema") as step:
                    enhanced_context = await self.enhanced_context_builder.build_enhanced_context(context)
                    
                    # Log enhancement details
                    enhancement_info = {
                        "installation_methods": getattr(enhanced_context, 'likely_installation_methods', []),
                        "software_category": getattr(enhanced_context, 'software_category', 'unknown'),
                        "has_security_template": hasattr(enhanced_context, 'security_metadata_template'),
                        "has_compatibility_template": hasattr(enhanced_context, 'compatibility_matrix_template')
                    }
                    self.logger.log_generation_context_enhancement(enhancement_info)
            else:
                enhanced_context = await self.enhanced_context_builder.build_enhanced_context(context)
            
            logger.debug(f"Enhanced context built for {request.software_name} with 0.3 features")
            return enhanced_context
            
        except Exception as e:
            logger.warning(f"Failed to enhance context for 0.3 schema: {e}")
            if self.logger:
                self.logger.log_error(f"Context enhancement failed: {e}")
            # Return base context if enhancement fails
            return context
    
    async def _parse_and_validate_yaml(self, yaml_content: str, software_name: str, context: Optional[GenerationContext] = None, provider_name: Optional[str] = None, is_retry: bool = False) -> SaiData:
        """Parse and validate generated YAML content.
        
        Args:
            yaml_content: Generated YAML content
            software_name: Software name for error reporting
            context: Generation context (for retry attempts)
            provider_name: LLM provider name (for retry attempts)
            is_retry: Whether this is a retry attempt
            
        Returns:
            Validated SaiData instance
            
        Raises:
            ValidationFailedError: If validation fails
        """
        try:
            if self.logger:
                with self.logger.log_data_op("yaml_parsing", "Parsing generated YAML content") as log_output:
                    # Clean YAML content (remove markdown code blocks if present)
                    cleaned_yaml = self._clean_yaml_content(yaml_content)
                    
                    # Parse YAML
                    data = yaml.safe_load(cleaned_yaml)
                    if not isinstance(data, dict):
                        raise ValidationFailedError("Generated content is not a valid YAML dictionary")
                    
                    log_output({
                        "original_length": len(yaml_content),
                        "cleaned_length": len(cleaned_yaml),
                        "parsed_keys": list(data.keys()) if isinstance(data, dict) else [],
                        "is_retry": is_retry
                    })
            else:
                # Clean YAML content (remove markdown code blocks if present)
                cleaned_yaml = self._clean_yaml_content(yaml_content)
                
                # Parse YAML
                data = yaml.safe_load(cleaned_yaml)
                if not isinstance(data, dict):
                    raise ValidationFailedError("Generated content is not a valid YAML dictionary")
            
            if self.logger:
                with self.logger.log_data_op("schema_validation", "Validating against saidata schema") as log_output:
                    # Validate against schema
                    validation_result = self.validator.validate_data(data, f"generated:{software_name}")
                    
                    log_output({
                        "is_valid": validation_result.is_valid,
                        "error_count": len(validation_result.errors),
                        "warning_count": len(validation_result.warnings),
                        "is_retry": is_retry
                    })
                    
                    if not validation_result.is_valid:
                        error_messages = [error.message for error in validation_result.errors]
                        validation_error = f"Schema validation failed: {'; '.join(error_messages)}"
                        
                        # If this is not a retry and we have context, attempt a second query
                        if not is_retry and context and provider_name:
                            return await self._retry_generation_with_validation_feedback(
                                context, provider_name, yaml_content, validation_error, error_messages
                            )
                        
                        raise ValidationFailedError(validation_error)
            else:
                # Validate against schema
                validation_result = self.validator.validate_data(data, f"generated:{software_name}")
                
                if not validation_result.is_valid:
                    error_messages = [error.message for error in validation_result.errors]
                    validation_error = f"Schema validation failed: {'; '.join(error_messages)}"
                    
                    # If this is not a retry and we have context, attempt a second query
                    if not is_retry and context and provider_name:
                        return await self._retry_generation_with_validation_feedback(
                            context, provider_name, yaml_content, validation_error, error_messages
                        )
                    
                    raise ValidationFailedError(validation_error)
            
            if self.logger:
                with self.logger.log_data_op("model_validation", "Validating Pydantic model") as log_output:
                    # Convert to Pydantic model
                    saidata = SaiData(**data)
                    
                    # Additional validation of the Pydantic model
                    model_validation = self.validator.validate_pydantic_model(saidata)
                    
                    log_output({
                        "model_created": True,
                        "model_validation_valid": model_validation.is_valid,
                        "model_error_count": len(model_validation.errors),
                        "is_retry": is_retry
                    })
                    
                    if not model_validation.is_valid:
                        error_messages = [error.message for error in model_validation.errors]
                        validation_error = f"Model validation failed: {'; '.join(error_messages)}"
                        
                        # If this is not a retry and we have context, attempt a second query
                        if not is_retry and context and provider_name:
                            return await self._retry_generation_with_validation_feedback(
                                context, provider_name, yaml_content, validation_error, error_messages
                            )
                        
                        raise ValidationFailedError(validation_error)
            else:
                # Convert to Pydantic model
                saidata = SaiData(**data)
                
                # Additional validation of the Pydantic model
                model_validation = self.validator.validate_pydantic_model(saidata)
                if not model_validation.is_valid:
                    error_messages = [error.message for error in model_validation.errors]
                    validation_error = f"Model validation failed: {'; '.join(error_messages)}"
                    
                    # If this is not a retry and we have context, attempt a second query
                    if not is_retry and context and provider_name:
                        return await self._retry_generation_with_validation_feedback(
                            context, provider_name, yaml_content, validation_error, error_messages
                        )
                    
                    raise ValidationFailedError(validation_error)
            
            return saidata
            
        except yaml.YAMLError as e:
            yaml_error = f"Invalid YAML syntax: {e}"
            if self.logger:
                self.logger.log_error(f"YAML parsing error: {e}")
            
            # If this is not a retry and we have context, attempt a second query
            if not is_retry and context and provider_name:
                return await self._retry_generation_with_validation_feedback(
                    context, provider_name, yaml_content, yaml_error, [str(e)]
                )
            
            raise ValidationFailedError(yaml_error)
        except Exception as e:
            if isinstance(e, ValidationFailedError):
                if self.logger:
                    self.logger.log_error(f"Validation failed: {e}")
                raise
            if self.logger:
                self.logger.log_error(f"Validation error: {e}")
            raise ValidationFailedError(f"Validation error: {e}")
    
    async def _retry_generation_with_validation_feedback(
        self, 
        context: GenerationContext, 
        provider_name: str, 
        failed_yaml: str, 
        validation_error: str, 
        error_messages: List[str]
    ) -> SaiData:
        """Retry generation with validation feedback from the first attempt.
        
        Args:
            context: Original generation context
            provider_name: LLM provider name
            failed_yaml: The YAML that failed validation
            validation_error: Summary of validation error
            error_messages: Detailed error messages
            
        Returns:
            Validated SaiData instance
            
        Raises:
            ValidationFailedError: If retry also fails
        """
        logger.info(f"First generation attempt failed validation for '{context.software_name}', retrying with feedback")
        
        if self.logger:
            self.logger.log_error(f"First attempt validation failed: {validation_error}")
            with self.logger.log_step("retry_generation", "Retrying generation with validation feedback"):
                # Create enhanced context with validation feedback
                retry_context = self._create_retry_context(context, failed_yaml, validation_error, error_messages)
                
                # Generate with retry context
                retry_response = await self._generate_with_logged_llm_retry(retry_context, provider_name)
                
                # Parse and validate the retry response (mark as retry to prevent infinite loop)
                return await self._parse_and_validate_yaml(
                    retry_response.content,
                    context.software_name,
                    is_retry=True
                )
        else:
            # Create enhanced context with validation feedback
            retry_context = self._create_retry_context(context, failed_yaml, validation_error, error_messages)
            
            # Generate with retry context
            if provider_name in self._llm_providers:
                mock_provider = self._llm_providers[provider_name]
                retry_response = await mock_provider.generate_saidata(retry_context)
            else:
                retry_response = await self.provider_manager.generate_with_fallback(
                    context=retry_context,
                    preferred_provider=provider_name
                )
            
            # Parse and validate the retry response (mark as retry to prevent infinite loop)
            return await self._parse_and_validate_yaml(
                retry_response.content,
                context.software_name,
                is_retry=True
            )
    
    def _create_retry_context(
        self, 
        original_context: GenerationContext, 
        failed_yaml: str, 
        validation_error: str, 
        error_messages: List[str]
    ) -> GenerationContext:
        """Create an enhanced context for retry generation with validation feedback.
        
        Args:
            original_context: Original generation context
            failed_yaml: The YAML that failed validation
            validation_error: Summary of validation error
            error_messages: Detailed error messages
            
        Returns:
            Enhanced GenerationContext with validation feedback
        """
        # Create validation feedback hints
        validation_feedback = {
            "validation_error": validation_error,
            "specific_errors": error_messages,
            "failed_yaml_excerpt": failed_yaml[:500] + "..." if len(failed_yaml) > 500 else failed_yaml,
            "retry_instructions": [
                "The previous generation attempt failed validation",
                "Please fix the specific validation errors mentioned above",
                "Ensure the YAML follows the exact saidata schema requirements",
                "Pay special attention to required fields and proper data types",
                "Generate only valid YAML without any markdown formatting"
            ]
        }
        
        # Combine original user hints with validation feedback
        enhanced_hints = original_context.user_hints.copy() if original_context.user_hints else {}
        enhanced_hints["validation_feedback"] = validation_feedback
        
        # Create new context with enhanced hints
        retry_context = GenerationContext(
            software_name=original_context.software_name,
            target_providers=original_context.target_providers,
            user_hints=enhanced_hints,
            existing_saidata=original_context.existing_saidata,
            repository_data=original_context.repository_data,
            similar_saidata=original_context.similar_saidata
        )
        
        # Copy sample_saidata if it exists
        if hasattr(original_context, 'sample_saidata'):
            retry_context.sample_saidata = original_context.sample_saidata
        
        return retry_context
    
    async def _generate_with_logged_llm_retry(self, context: GenerationContext, provider_name: str):
        """Generate saidata with LLM for retry attempt and log the interaction.
        
        Args:
            context: Enhanced generation context with validation feedback
            provider_name: Name of the LLM provider
            
        Returns:
            LLM response
        """
        # Get the retry prompt template
        from ..llm.prompts import PromptManager
        prompt_manager = PromptManager()
        
        # Use the retry template if available, otherwise use generation template
        try:
            template = prompt_manager.get_template("retry")
        except KeyError:
            template = prompt_manager.get_template("generation")
        
        prompt = template.render(context)
        
        # Record start time for LLM interaction
        llm_start_time = time.time()
        
        try:
            # Generate with provider manager
            llm_response = await self.provider_manager.generate_with_fallback(
                context=context,
                preferred_provider=provider_name
            )
            
            # Calculate duration
            llm_duration = time.time() - llm_start_time
            
            # Log the successful retry interaction
            if self.logger:
                self.logger.log_llm_interaction(
                    provider=provider_name,
                    model=getattr(llm_response, 'model', 'unknown'),
                    prompt=prompt,
                    response=llm_response.content,
                    tokens_used=llm_response.tokens_used,
                    cost_estimate=llm_response.cost_estimate,
                    duration_seconds=llm_duration,
                    success=True,
                    metadata={"retry_attempt": True}
                )
            
            return llm_response
            
        except Exception as e:
            # Calculate duration
            llm_duration = time.time() - llm_start_time
            
            # Log the failed retry interaction
            if self.logger:
                self.logger.log_llm_interaction(
                    provider=provider_name,
                    model='unknown',
                    prompt=prompt,
                    response='',
                    duration_seconds=llm_duration,
                    success=False,
                    error=str(e),
                    metadata={"retry_attempt": True}
                )
            
            raise
    
    async def _generate_with_logged_llm(self, context: GenerationContext, provider_name: str):
        """Generate saidata with LLM and log the interaction.
        
        Args:
            context: Generation context
            provider_name: Name of the LLM provider
            
        Returns:
            LLM response
        """
        # Get the prompt that will be sent
        from ..llm.prompts import PromptManager
        prompt_manager = PromptManager()
        template = prompt_manager.get_template("generation")
        prompt = template.render(context)
        
        # Record start time for LLM interaction
        llm_start_time = time.time()
        
        try:
            # Generate with provider manager
            llm_response = await self.provider_manager.generate_with_fallback(
                context=context,
                preferred_provider=provider_name
            )
            
            # Calculate duration
            llm_duration = time.time() - llm_start_time
            
            # Log the successful interaction
            if self.logger:
                self.logger.log_llm_interaction(
                    provider=provider_name,
                    model=getattr(llm_response, 'model', 'unknown'),
                    prompt=prompt,
                    response=llm_response.content,
                    tokens_used=llm_response.tokens_used,
                    cost_estimate=llm_response.cost_estimate,
                    duration_seconds=llm_duration,
                    success=True
                )
            
            return llm_response
            
        except Exception as e:
            # Calculate duration
            llm_duration = time.time() - llm_start_time
            
            # Log the failed interaction
            if self.logger:
                self.logger.log_llm_interaction(
                    provider=provider_name,
                    model='unknown',
                    prompt=prompt,
                    response='',
                    duration_seconds=llm_duration,
                    success=False,
                    error=str(e)
                )
            
            raise
    
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
    
    def _clean_yaml_content(self, content: str) -> str:
        """Clean YAML content by removing markdown code blocks and extra formatting.
        
        Args:
            content: Raw content from LLM that may contain markdown
            
        Returns:
            Cleaned YAML content
        """
        import re
        
        # Remove markdown code blocks
        # Pattern matches ```yaml or ``` at start and ``` at end
        content = re.sub(r'^```(?:yaml|yml)?\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n```\s*$', '', content, flags=re.MULTILINE)
        
        # Remove any remaining ``` at the beginning or end
        content = content.strip('`').strip()
        
        return content
    
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
            if self.logger:
                with self.logger.log_data_op("file_save", f"Saving saidata to {output_path}") as log_output:
                    # Ensure output directory exists
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Convert to dict and save as YAML
                    data = saidata.model_dump(exclude_none=True)
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)
                    
                    # Log file details
                    file_size = output_path.stat().st_size
                    log_output({
                        "output_path": str(output_path),
                        "file_size_bytes": file_size,
                        "providers_count": len(saidata.providers) if saidata.providers else 0
                    })
            else:
                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Convert to dict and save as YAML
                data = saidata.model_dump(exclude_none=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)
            
            logger.info(f"Saved saidata to {output_path}")
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to save saidata to {output_path}: {e}")
            raise GenerationEngineError(f"Failed to save saidata to {output_path}: {e}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available LLM providers.
        
        Returns:
            List of provider names
        """
        return self.provider_manager.get_available_providers()
    
    def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider information dictionary or None if not found
        """
        # For backward compatibility with tests, check _llm_providers first
        if provider_name in self._llm_providers:
            provider = self._llm_providers[provider_name]
            if hasattr(provider, 'get_model_info'):
                model_info = provider.get_model_info()
                return {
                    "name": provider_name,
                    "available": True,
                    "model": model_info.name,
                    "max_tokens": model_info.max_tokens,
                    "context_window": model_info.context_window,
                    "capabilities": [cap.value for cap in model_info.capabilities],
                    "cost_per_1k_tokens": model_info.cost_per_1k_tokens,
                    "supports_streaming": model_info.supports_streaming
                }
        
        # Check if provider exists in provider manager
        available_providers = self.provider_manager.get_available_providers()
        if provider_name not in available_providers:
            return None
        
        # For real implementation, we'd need async access to provider manager
        # For now, return basic info for compatibility
        return {
            "name": provider_name,
            "available": True,
            "configured": True
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
    
    async def get_all_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all configured providers.
        
        Returns:
            Dictionary mapping provider names to their status information
        """
        status_dict = await self.provider_manager.get_all_provider_status()
        
        # Convert to serializable format
        result = {}
        for name, status in status_dict.items():
            result[name] = {
                "available": status.available,
                "configured": status.configured,
                "connection_valid": status.connection_valid,
                "last_error": status.last_error
            }
            
            if status.model_info:
                result[name]["model_info"] = {
                    "name": status.model_info.name,
                    "provider": status.model_info.provider,
                    "max_tokens": status.model_info.max_tokens,
                    "context_window": status.model_info.context_window,
                    "capabilities": [cap.value for cap in status.model_info.capabilities],
                    "cost_per_1k_tokens": status.model_info.cost_per_1k_tokens,
                    "supports_streaming": status.model_info.supports_streaming
                }
        
        return result
    
    async def index_repository_data(self, packages: List[RepositoryPackage]) -> bool:
        """Index repository data for RAG.
        
        Args:
            packages: List of repository packages to index
            
        Returns:
            True if indexing succeeded, False otherwise
        """
        if not self.rag_indexer:
            logger.warning("RAG indexer not available")
            return False
        
        try:
            await self.rag_indexer.index_repository_data(packages)
            logger.info(f"Successfully indexed {len(packages)} repository packages")
            return True
        except Exception as e:
            logger.error(f"Failed to index repository data: {e}")
            return False
    
    async def index_saidata_files(self, saidata_files: List[Path]) -> bool:
        """Index existing saidata files for RAG.
        
        Args:
            saidata_files: List of paths to saidata files
            
        Returns:
            True if indexing succeeded, False otherwise
        """
        if not self.rag_indexer:
            logger.warning("RAG indexer not available")
            return False
        
        try:
            await self.rag_indexer.index_existing_saidata(saidata_files)
            logger.info(f"Successfully indexed {len(saidata_files)} saidata files")
            return True
        except Exception as e:
            logger.error(f"Failed to index saidata files: {e}")
            return False
    
    async def get_rag_stats(self) -> Optional[Dict[str, Any]]:
        """Get RAG indexing statistics.
        
        Returns:
            RAG statistics dictionary or None if RAG not available
        """
        if not self.rag_indexer:
            return None
        
        try:
            return await self.rag_indexer.get_index_stats()
        except Exception as e:
            logger.error(f"Failed to get RAG stats: {e}")
            return None
    
    async def rebuild_rag_indices(
        self,
        packages: Optional[List[RepositoryPackage]] = None,
        saidata_files: Optional[List[Path]] = None
    ) -> Dict[str, bool]:
        """Rebuild RAG indices.
        
        Args:
            packages: Repository packages to index (if None, skip package index)
            saidata_files: Saidata files to index (if None, skip saidata index)
            
        Returns:
            Dictionary with rebuild results
        """
        if not self.rag_indexer:
            return {'package_index_rebuilt': False, 'saidata_index_rebuilt': False}
        
        try:
            return await self.rag_indexer.rebuild_indices(packages, saidata_files)
        except Exception as e:
            logger.error(f"Failed to rebuild RAG indices: {e}")
            return {'package_index_rebuilt': False, 'saidata_index_rebuilt': False}
    
    async def clear_rag_indices(self) -> bool:
        """Clear all RAG indices.
        
        Returns:
            True if clearing succeeded, False otherwise
        """
        if not self.rag_indexer:
            return False
        
        try:
            await self.rag_indexer.clear_indices()
            logger.info("RAG indices cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear RAG indices: {e}")
            return False
    
    def is_rag_available(self) -> bool:
        """Check if RAG functionality is available.
        
        Returns:
            True if RAG is available, False otherwise
        """
        return self.rag_indexer is not None and self.rag_context_builder is not None
    
    async def search_similar_packages(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.3
    ) -> List[RepositoryPackage]:
        """Search for similar packages using semantic search.
        
        Args:
            query: Search query
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of similar repository packages
        """
        if not self.rag_indexer:
            logger.warning("RAG indexer not available")
            return []
        
        try:
            return await self.rag_indexer.search_similar_packages(query, limit, min_score)
        except Exception as e:
            logger.error(f"Failed to search similar packages: {e}")
            return []
    
    async def find_similar_saidata(
        self,
        software_name: str,
        limit: int = 3,
        min_score: float = 0.4
    ) -> List[SaiData]:
        """Find similar existing saidata files.
        
        Args:
            software_name: Software name to find similar saidata for
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of similar SaiData objects
        """
        if not self.rag_indexer:
            logger.warning("RAG indexer not available")
            return []
        
        try:
            return await self.rag_indexer.find_similar_saidata(software_name, limit, min_score)
        except Exception as e:
            logger.error(f"Failed to find similar saidata: {e}")
            return []
    
    async def build_rag_context(
        self,
        software_name: str,
        target_providers: Optional[List[str]] = None,
        max_packages: int = 5,
        max_saidata: int = 3
    ) -> Dict[str, Any]:
        """Build RAG context for LLM prompt injection.
        
        Args:
            software_name: Software name to build context for
            target_providers: Target providers to focus on
            max_packages: Maximum number of similar packages to include
            max_saidata: Maximum number of similar saidata to include
            
        Returns:
            Dictionary with RAG context data
        """
        if not self.rag_context_builder:
            logger.warning("RAG context builder not available")
            return {
                'similar_packages': [],
                'similar_saidata': [],
                'sample_saidata': [],
                'provider_specific_packages': {},
                'context_summary': f'No RAG context available for {software_name}'
            }
        
        try:
            return await self.rag_context_builder.build_context(
                software_name, target_providers, max_packages, max_saidata
            )
        except Exception as e:
            logger.error(f"Failed to build RAG context: {e}")
            return {
                'similar_packages': [],
                'similar_saidata': [],
                'sample_saidata': [],
                'provider_specific_packages': {},
                'context_summary': f'Failed to build RAG context for {software_name}: {e}'
            }
    
    async def generate_sources(self, request: GenerationRequest, context: GenerationContext) -> List[Dict[str, Any]]:
        """Generate source build configurations for 0.3 schema.
        
        Args:
            request: Generation request
            context: Generation context
            
        Returns:
            List of source configuration dictionaries
        """
        try:
            logger.debug(f"Generating source configurations for {request.software_name}")
            
            # Determine likely source build configurations based on software type
            sources = []
            
            # Check if software is commonly built from source
            software_category = getattr(context, 'software_category', 'unknown')
            if software_category in ['web-server', 'database', 'development-tool', 'system-tool']:
                # Generate main source configuration
                main_source = {
                    "name": "main",
                    "url": f"https://github.com/example/{request.software_name}/archive/{{{{version}}}}.tar.gz",
                    "build_system": self._detect_build_system(request.software_name, context),
                    "version": "latest",
                    "configure_args": self._generate_configure_args(request.software_name, context),
                    "prerequisites": self._generate_prerequisites(request.software_name, context),
                    "checksum": "sha256:placeholder_checksum_to_be_updated"
                }
                sources.append(main_source)
            
            return sources
            
        except Exception as e:
            logger.warning(f"Failed to generate source configurations: {e}")
            return []
    
    async def generate_binaries(self, request: GenerationRequest, context: GenerationContext) -> List[Dict[str, Any]]:
        """Generate binary download configurations for 0.3 schema.
        
        Args:
            request: Generation request
            context: Generation context
            
        Returns:
            List of binary configuration dictionaries
        """
        try:
            logger.debug(f"Generating binary configurations for {request.software_name}")
            
            binaries = []
            
            # Check if software commonly provides pre-compiled binaries
            software_category = getattr(context, 'software_category', 'unknown')
            if software_category in ['cli-tool', 'development-tool', 'system-tool']:
                # Generate main binary configuration
                main_binary = {
                    "name": "main",
                    "url": f"https://releases.example.com/{request.software_name}/{{{{version}}}}/{request.software_name}_{{{{version}}}}_{{{{platform}}}}_{{{{architecture}}}}.zip",
                    "version": "latest",
                    "install_path": "/usr/local/bin",
                    "executable": request.software_name,
                    "checksum": "sha256:placeholder_checksum_to_be_updated",
                    "permissions": "0755",
                    "archive": {
                        "format": "zip",
                        "strip_prefix": f"{request.software_name}_{{{{version}}}}_{{{{platform}}}}_{{{{architecture}}}}/",
                        "extract_path": "bin/"
                    }
                }
                binaries.append(main_binary)
            
            return binaries
            
        except Exception as e:
            logger.warning(f"Failed to generate binary configurations: {e}")
            return []
    
    async def generate_scripts(self, request: GenerationRequest, context: GenerationContext) -> List[Dict[str, Any]]:
        """Generate script installation configurations for 0.3 schema.
        
        Args:
            request: Generation request
            context: Generation context
            
        Returns:
            List of script configuration dictionaries
        """
        try:
            logger.debug(f"Generating script configurations for {request.software_name}")
            
            scripts = []
            
            # Check if software commonly provides installation scripts
            software_category = getattr(context, 'software_category', 'unknown')
            if software_category in ['runtime', 'development-tool', 'container-tool']:
                # Generate official script configuration
                official_script = {
                    "name": "official",
                    "url": f"https://get.{request.software_name}.com/install.sh",
                    "interpreter": "bash",
                    "checksum": "sha256:placeholder_checksum_to_be_updated",
                    "timeout": 600,
                    "arguments": ["--channel", "stable"],
                    "environment": {
                        "CHANNEL": "stable",
                        "INSTALL_DIR": "/usr/local/bin"
                    }
                }
                scripts.append(official_script)
            
            return scripts
            
        except Exception as e:
            logger.warning(f"Failed to generate script configurations: {e}")
            return []
    
    def _detect_build_system(self, software_name: str, context: GenerationContext) -> str:
        """Detect likely build system based on software name and context.
        
        Args:
            software_name: Name of the software
            context: Generation context
            
        Returns:
            Build system name
        """
        # Simple heuristics for build system detection
        if 'nginx' in software_name.lower() or 'apache' in software_name.lower():
            return "autotools"
        elif 'cmake' in software_name.lower() or any('cmake' in pkg.name.lower() for pkg in context.repository_data):
            return "cmake"
        elif 'rust' in software_name.lower() or 'cargo' in software_name.lower():
            return "custom"  # Cargo build
        elif 'go' in software_name.lower():
            return "custom"  # Go build
        else:
            return "autotools"  # Default fallback
    
    def _generate_configure_args(self, software_name: str, context: GenerationContext) -> List[str]:
        """Generate configure arguments based on software type.
        
        Args:
            software_name: Name of the software
            context: Generation context
            
        Returns:
            List of configure arguments
        """
        args = []
        
        # Common security and feature flags
        if 'server' in software_name.lower() or 'web' in software_name.lower():
            args.extend(["--with-http_ssl_module", "--with-http_v2_module"])
        
        if 'database' in software_name.lower() or 'sql' in software_name.lower():
            args.extend(["--enable-ssl", "--with-openssl"])
        
        # Default prefix
        args.append("--prefix=/usr/local")
        
        return args
    
    def _generate_prerequisites(self, software_name: str, context: GenerationContext) -> List[str]:
        """Generate build prerequisites based on software type.
        
        Args:
            software_name: Name of the software
            context: Generation context
            
        Returns:
            List of prerequisite packages
        """
        prereqs = ["build-essential", "gcc", "make"]
        
        # Add common development libraries
        if 'ssl' in software_name.lower() or 'crypto' in software_name.lower():
            prereqs.append("libssl-dev")
        
        if 'xml' in software_name.lower():
            prereqs.append("libxml2-dev")
        
        if 'curl' in software_name.lower() or 'http' in software_name.lower():
            prereqs.append("libcurl4-openssl-dev")
        
        return prereqs
    
    async def generate_enhanced_metadata(self, request: GenerationRequest, context: GenerationContext) -> Dict[str, Any]:
        """Generate enhanced metadata for 0.3 schema including security information.
        
        Args:
            request: Generation request
            context: Generation context
            
        Returns:
            Enhanced metadata dictionary
        """
        try:
            logger.debug(f"Generating enhanced metadata for {request.software_name}")
            
            # Start with basic metadata
            metadata = {
                "name": request.software_name,
                "description": f"Software management configuration for {request.software_name}",
                "category": self._detect_software_category(request.software_name, context),
                "version": "latest"
            }
            
            # Add enhanced URLs
            urls = self._generate_enhanced_urls(request.software_name, context)
            if urls:
                metadata["urls"] = urls
            
            # Add security metadata
            security = self._generate_security_metadata(request.software_name, context)
            if security:
                metadata["security"] = security
            
            # Add tags based on software type
            tags = self._generate_software_tags(request.software_name, context)
            if tags:
                metadata["tags"] = tags
            
            # Add license information if detectable
            license_info = self._detect_software_license(request.software_name, context)
            if license_info:
                metadata["license"] = license_info
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to generate enhanced metadata: {e}")
            # Return basic metadata as fallback
            return {
                "name": request.software_name,
                "description": f"Software management configuration for {request.software_name}"
            }
    
    def _generate_enhanced_urls(self, software_name: str, context: GenerationContext) -> Dict[str, str]:
        """Generate comprehensive URL types for enhanced metadata.
        
        Args:
            software_name: Name of the software
            context: Generation context
            
        Returns:
            Dictionary of URL types and values
        """
        urls = {}
        
        # Try to extract URLs from repository data
        for package in context.repository_data:
            if package.homepage:
                urls["website"] = package.homepage
                break
        
        # Generate common URL patterns
        base_name = software_name.lower().replace('-', '').replace('_', '')
        
        # Common website patterns
        if "website" not in urls:
            urls["website"] = f"https://{base_name}.org"
        
        # Documentation patterns
        urls["documentation"] = f"https://docs.{base_name}.org"
        
        # Source code patterns
        urls["source"] = f"https://github.com/{base_name}/{base_name}"
        
        # Issues tracker
        urls["issues"] = f"https://github.com/{base_name}/{base_name}/issues"
        
        # Download page
        urls["download"] = f"https://{base_name}.org/download"
        
        return urls
    
    def _generate_security_metadata(self, software_name: str, context: GenerationContext) -> Dict[str, Any]:
        """Generate security metadata fields for enhanced security information.
        
        Args:
            software_name: Name of the software
            context: Generation context
            
        Returns:
            Dictionary of security metadata
        """
        security = {}
        
        # Generate security contact based on software type
        base_name = software_name.lower().replace('-', '').replace('_', '')
        security["security_contact"] = f"security@{base_name}.org"
        
        # Add vulnerability disclosure policy URL
        security["vulnerability_disclosure"] = f"https://{base_name}.org/security"
        
        # Add SBOM URL for software bill of materials
        security["sbom_url"] = f"https://{base_name}.org/sbom"
        
        # Add signing key information for package verification
        security["signing_key"] = f"https://{base_name}.org/keys/release.asc"
        
        return security
    
    def _generate_software_tags(self, software_name: str, context: GenerationContext) -> List[str]:
        """Generate software tags based on category and characteristics.
        
        Args:
            software_name: Name of the software
            context: Generation context
            
        Returns:
            List of relevant tags
        """
        tags = []
        
        # Add category-based tags
        category = self._detect_software_category(software_name, context)
        if category:
            tags.append(category)
        
        # Add technology-specific tags
        name_lower = software_name.lower()
        
        if any(term in name_lower for term in ['web', 'http', 'server']):
            tags.extend(["web", "server", "http"])
        
        if any(term in name_lower for term in ['database', 'db', 'sql']):
            tags.extend(["database", "storage"])
        
        if any(term in name_lower for term in ['docker', 'container']):
            tags.extend(["container", "docker"])
        
        if any(term in name_lower for term in ['cli', 'command', 'tool']):
            tags.extend(["cli", "command-line"])
        
        if any(term in name_lower for term in ['dev', 'development']):
            tags.extend(["development", "tools"])
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(tags))
    
    def _detect_software_category(self, software_name: str, context: GenerationContext) -> str:
        """Detect software category based on name and context.
        
        Args:
            software_name: Name of the software
            context: Generation context
            
        Returns:
            Software category string
        """
        name_lower = software_name.lower()
        
        # Web servers and HTTP tools
        if any(term in name_lower for term in ['nginx', 'apache', 'httpd', 'web', 'server']):
            return "web-server"
        
        # Databases
        if any(term in name_lower for term in ['mysql', 'postgres', 'redis', 'mongo', 'database', 'db']):
            return "database"
        
        # Development tools
        if any(term in name_lower for term in ['git', 'docker', 'kubectl', 'terraform', 'ansible']):
            return "development-tool"
        
        # CLI tools
        if any(term in name_lower for term in ['cli', 'command', 'tool']):
            return "cli-tool"
        
        # System tools
        if any(term in name_lower for term in ['system', 'admin', 'monitor']):
            return "system-tool"
        
        # Container tools
        if any(term in name_lower for term in ['docker', 'container', 'k8s', 'kubernetes']):
            return "container-tool"
        
        # Runtime environments
        if any(term in name_lower for term in ['node', 'python', 'java', 'runtime']):
            return "runtime"
        
        return "application"
    
    def _detect_software_license(self, software_name: str, context: GenerationContext) -> Optional[str]:
        """Detect likely software license based on name and context.
        
        Args:
            software_name: Name of the software
            context: Generation context
            
        Returns:
            License string or None
        """
        name_lower = software_name.lower()
        
        # Common open source licenses
        if any(term in name_lower for term in ['apache', 'httpd']):
            return "Apache-2.0"
        
        if any(term in name_lower for term in ['nginx']):
            return "BSD-2-Clause"
        
        if any(term in name_lower for term in ['mysql']):
            return "GPL-2.0"
        
        if any(term in name_lower for term in ['postgres']):
            return "PostgreSQL"
        
        if any(term in name_lower for term in ['redis']):
            return "BSD-3-Clause"
        
        # Default to MIT for unknown software
        return "MIT"
    
    async def generate_compatibility_matrix(self, request: GenerationRequest, context: GenerationContext) -> Dict[str, Any]:
        """Generate compatibility matrix for cross-platform support.
        
        Args:
            request: Generation request
            context: Generation context
            
        Returns:
            Compatibility matrix dictionary
        """
        try:
            logger.debug(f"Generating compatibility matrix for {request.software_name}")
            
            compatibility = {
                "matrix": [],
                "versions": {
                    "latest": "latest",
                    "minimum": "1.0.0",
                    "latest_lts": "lts",
                    "latest_minimum": "1.0.0"
                }
            }
            
            # Generate compatibility entries for target providers
            for provider in request.target_providers or ["apt", "brew", "winget"]:
                entry = self._generate_compatibility_entry(provider, request.software_name, context)
                if entry:
                    compatibility["matrix"].append(entry)
            
            return compatibility
            
        except Exception as e:
            logger.warning(f"Failed to generate compatibility matrix: {e}")
            return {}
    
    def _generate_compatibility_entry(self, provider: str, software_name: str, context: GenerationContext) -> Dict[str, Any]:
        """Generate a single compatibility matrix entry.
        
        Args:
            provider: Provider name
            software_name: Software name
            context: Generation context
            
        Returns:
            Compatibility entry dictionary
        """
        # Map providers to typical platforms
        provider_platforms = {
            "apt": ["linux"],
            "dnf": ["linux"],
            "yum": ["linux"],
            "pacman": ["linux"],
            "brew": ["darwin", "linux"],
            "winget": ["windows"],
            "choco": ["windows"],
            "scoop": ["windows"]
        }
        
        # Map providers to typical architectures
        provider_architectures = {
            "apt": ["amd64", "arm64"],
            "dnf": ["amd64", "arm64"],
            "yum": ["amd64", "arm64"],
            "pacman": ["amd64", "arm64"],
            "brew": ["amd64", "arm64"],
            "winget": ["amd64", "arm64"],
            "choco": ["amd64"],
            "scoop": ["amd64"]
        }
        
        platforms = provider_platforms.get(provider, ["linux"])
        architectures = provider_architectures.get(provider, ["amd64"])
        
        return {
            "provider": provider,
            "platform": platforms if len(platforms) > 1 else platforms[0],
            "architecture": architectures if len(architectures) > 1 else architectures[0],
            "supported": True,
            "tested": True,
            "recommended": provider in ["apt", "brew", "winget"],
            "notes": f"Supported on {provider} package manager"
        }
    
    async def generate_enhanced_provider_configs(self, request: GenerationRequest, context: GenerationContext) -> Dict[str, Any]:
        """Generate enhanced provider configurations for new installation methods.
        
        Args:
            request: Generation request
            context: Generation context
            
        Returns:
            Dictionary of provider configurations
        """
        try:
            logger.debug(f"Generating enhanced provider configurations for {request.software_name}")
            
            providers = {}
            
            # Generate configurations for each target provider
            for provider_name in request.target_providers or ["apt", "brew", "winget"]:
                provider_config = await self._generate_single_provider_config(
                    provider_name, request.software_name, context
                )
                if provider_config:
                    providers[provider_name] = provider_config
            
            return providers
            
        except Exception as e:
            logger.warning(f"Failed to generate enhanced provider configurations: {e}")
            return {}
    
    async def _generate_single_provider_config(self, provider_name: str, software_name: str, context: GenerationContext) -> Dict[str, Any]:
        """Generate configuration for a single provider with enhanced features.
        
        Args:
            provider_name: Name of the provider
            software_name: Software name
            context: Generation context
            
        Returns:
            Provider configuration dictionary
        """
        config = {}
        
        # Add prerequisites for source compilation
        if provider_name in ["apt", "dnf", "yum", "pacman"]:
            prerequisites = self._generate_provider_prerequisites(provider_name, software_name)
            if prerequisites:
                config["prerequisites"] = prerequisites
        
        # Add build commands for source compilation
        build_commands = self._generate_provider_build_commands(provider_name, software_name)
        if build_commands:
            config["build_commands"] = build_commands
        
        # Generate package sources with priority and recommendations
        package_sources = self._generate_package_sources(provider_name, software_name, context)
        if package_sources:
            config["package_sources"] = package_sources
        
        # Generate repository configurations
        repositories = self._generate_repository_configs(provider_name, software_name, context)
        if repositories:
            config["repositories"] = repositories
        
        # Generate provider-specific packages
        packages = self._generate_provider_packages(provider_name, software_name, context)
        if packages:
            config["packages"] = packages
        
        # Generate provider-specific sources (overrides)
        sources = await self._generate_provider_sources(provider_name, software_name, context)
        if sources:
            config["sources"] = sources
        
        # Generate provider-specific binaries (overrides)
        binaries = await self._generate_provider_binaries(provider_name, software_name, context)
        if binaries:
            config["binaries"] = binaries
        
        # Generate provider-specific scripts (overrides)
        scripts = await self._generate_provider_scripts(provider_name, software_name, context)
        if scripts:
            config["scripts"] = scripts
        
        return config
    
    def _generate_provider_prerequisites(self, provider_name: str, software_name: str) -> List[str]:
        """Generate provider-specific prerequisites for source compilation.
        
        Args:
            provider_name: Name of the provider
            software_name: Software name
            
        Returns:
            List of prerequisite packages
        """
        # Base prerequisites by provider
        base_prereqs = {
            "apt": ["build-essential", "gcc", "make"],
            "dnf": ["gcc", "gcc-c++", "make", "cmake"],
            "yum": ["gcc", "gcc-c++", "make", "cmake"],
            "pacman": ["base-devel", "gcc", "make"],
            "brew": ["gcc", "make", "cmake"],
        }
        
        prereqs = base_prereqs.get(provider_name, ["gcc", "make"])
        
        # Add software-specific prerequisites
        name_lower = software_name.lower()
        
        if 'ssl' in name_lower or 'crypto' in name_lower:
            if provider_name == "apt":
                prereqs.append("libssl-dev")
            elif provider_name in ["dnf", "yum"]:
                prereqs.append("openssl-devel")
            elif provider_name == "pacman":
                prereqs.append("openssl")
        
        if 'xml' in name_lower:
            if provider_name == "apt":
                prereqs.append("libxml2-dev")
            elif provider_name in ["dnf", "yum"]:
                prereqs.append("libxml2-devel")
            elif provider_name == "pacman":
                prereqs.append("libxml2")
        
        return prereqs
    
    def _generate_provider_build_commands(self, provider_name: str, software_name: str) -> List[str]:
        """Generate provider-specific build commands.
        
        Args:
            provider_name: Name of the provider
            software_name: Software name
            
        Returns:
            List of build commands
        """
        commands = []
        
        # Standard build sequence
        commands.extend([
            "wget ${SOURCE_URL} -O source.tar.gz",
            "tar -xzf source.tar.gz",
            "cd ${SOURCE_DIR}",
            "./configure --prefix=/usr/local",
            "make -j$(nproc)",
            "sudo make install"
        ])
        
        return commands
    
    def _generate_package_sources(self, provider_name: str, software_name: str, context: GenerationContext) -> List[Dict[str, Any]]:
        """Generate package source configurations with priority and recommendations.
        
        Args:
            provider_name: Name of the provider
            software_name: Software name
            context: Generation context
            
        Returns:
            List of package source configurations
        """
        sources = []
        
        # Main repository source
        main_source = {
            "name": "main",
            "repository": self._get_main_repository(provider_name),
            "priority": 1,
            "recommended": True,
            "packages": [
                {
                    "name": "main",
                    "package_name": self._get_package_name(provider_name, software_name, context)
                }
            ]
        }
        sources.append(main_source)
        
        # Add backports or testing repository if applicable
        if provider_name == "apt":
            backports_source = {
                "name": "backports",
                "repository": "backports",
                "priority": 2,
                "recommended": False,
                "packages": [
                    {
                        "name": "main",
                        "package_name": f"{self._get_package_name(provider_name, software_name, context)}-backports"
                    }
                ],
                "notes": "Newer versions available in backports repository"
            }
            sources.append(backports_source)
        
        return sources
    
    def _generate_repository_configs(self, provider_name: str, software_name: str, context: GenerationContext) -> List[Dict[str, Any]]:
        """Generate repository configurations with enhanced metadata.
        
        Args:
            provider_name: Name of the provider
            software_name: Software name
            context: Generation context
            
        Returns:
            List of repository configurations
        """
        repositories = []
        
        # Main repository
        main_repo = {
            "name": self._get_main_repository(provider_name),
            "type": "os-default",
            "priority": 1,
            "recommended": True,
            "maintainer": self._get_repository_maintainer(provider_name),
            "notes": f"Official {provider_name} repository"
        }
        
        # Add provider-specific repository details
        if provider_name == "apt":
            main_repo.update({
                "url": "http://archive.ubuntu.com/ubuntu/",
                "components": ["main", "universe"]
            })
        elif provider_name == "dnf":
            main_repo.update({
                "url": "https://download.fedoraproject.org/pub/fedora/linux/releases/",
                "components": ["fedora", "updates"]
            })
        elif provider_name == "brew":
            main_repo.update({
                "url": "https://github.com/Homebrew/homebrew-core",
                "type": "upstream"
            })
        
        repositories.append(main_repo)
        
        return repositories
    
    def _generate_provider_packages(self, provider_name: str, software_name: str, context: GenerationContext) -> List[Dict[str, Any]]:
        """Generate provider-specific package configurations.
        
        Args:
            provider_name: Name of the provider
            software_name: Software name
            context: Generation context
            
        Returns:
            List of package configurations
        """
        packages = []
        
        # Main package
        main_package = {
            "name": "main",
            "package_name": self._get_package_name(provider_name, software_name, context),
            "version": "latest"
        }
        
        # Add alternatives if common
        alternatives = self._get_package_alternatives(provider_name, software_name)
        if alternatives:
            main_package["alternatives"] = alternatives
        
        packages.append(main_package)
        
        return packages
    
    async def _generate_provider_sources(self, provider_name: str, software_name: str, context: GenerationContext) -> List[Dict[str, Any]]:
        """Generate provider-specific source build configurations.
        
        Args:
            provider_name: Name of the provider
            software_name: Software name
            context: Generation context
            
        Returns:
            List of provider-specific source configurations
        """
        # Only generate provider-specific sources for providers that commonly build from source
        if provider_name not in ["apt", "dnf", "yum", "pacman", "brew"]:
            return []
        
        sources = []
        
        # Provider-specific source configuration
        if provider_name == "brew":
            # Homebrew often has specific build configurations
            brew_source = {
                "name": "homebrew",
                "url": f"https://github.com/Homebrew/homebrew-core/raw/HEAD/Formula/{software_name}.rb",
                "build_system": "custom",
                "custom_commands": {
                    "install": f"brew install --build-from-source {software_name}"
                }
            }
            sources.append(brew_source)
        
        return sources
    
    async def _generate_provider_binaries(self, provider_name: str, software_name: str, context: GenerationContext) -> List[Dict[str, Any]]:
        """Generate provider-specific binary download configurations.
        
        Args:
            provider_name: Name of the provider
            software_name: Software name
            context: Generation context
            
        Returns:
            List of provider-specific binary configurations
        """
        # Only generate provider-specific binaries for providers that support direct downloads
        if provider_name not in ["winget", "scoop", "choco"]:
            return []
        
        binaries = []
        
        # Windows-specific binary configuration
        if provider_name in ["winget", "scoop", "choco"]:
            windows_binary = {
                "name": "windows",
                "url": f"https://releases.example.com/{software_name}/{{{{version}}}}/{software_name}_{{{{version}}}}_windows_amd64.zip",
                "platform": "windows",
                "architecture": "amd64",
                "install_path": "C:\\Program Files\\{software_name}",
                "executable": f"{software_name}.exe",
                "archive": {
                    "format": "zip",
                    "extract_path": "bin/"
                }
            }
            binaries.append(windows_binary)
        
        return binaries
    
    async def _generate_provider_scripts(self, provider_name: str, software_name: str, context: GenerationContext) -> List[Dict[str, Any]]:
        """Generate provider-specific script installation configurations.
        
        Args:
            provider_name: Name of the provider
            software_name: Software name
            context: Generation context
            
        Returns:
            List of provider-specific script configurations
        """
        # Only generate provider-specific scripts for providers that commonly use scripts
        if provider_name not in ["brew", "winget", "scoop"]:
            return []
        
        scripts = []
        
        # Provider-specific script configuration
        if provider_name == "brew":
            # Homebrew cask installation script
            brew_script = {
                "name": "homebrew-cask",
                "url": f"https://raw.githubusercontent.com/Homebrew/homebrew-cask/HEAD/Casks/{software_name}.rb",
                "interpreter": "ruby",
                "custom_commands": {
                    "install": f"brew install --cask {software_name}"
                }
            }
            scripts.append(brew_script)
        
        return scripts
    
    def _get_main_repository(self, provider_name: str) -> str:
        """Get the main repository name for a provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Main repository name
        """
        repo_names = {
            "apt": "main",
            "dnf": "fedora",
            "yum": "base",
            "pacman": "core",
            "brew": "homebrew-core",
            "winget": "msstore",
            "choco": "chocolatey",
            "scoop": "main"
        }
        return repo_names.get(provider_name, "main")
    
    def _get_repository_maintainer(self, provider_name: str) -> str:
        """Get the repository maintainer for a provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Repository maintainer
        """
        maintainers = {
            "apt": "Ubuntu/Debian Team",
            "dnf": "Fedora Project",
            "yum": "Red Hat",
            "pacman": "Arch Linux",
            "brew": "Homebrew Team",
            "winget": "Microsoft",
            "choco": "Chocolatey Community",
            "scoop": "Scoop Community"
        }
        return maintainers.get(provider_name, "Community")
    
    def _get_package_name(self, provider_name: str, software_name: str, context: GenerationContext) -> str:
        """Get the actual package name for a provider.
        
        Args:
            provider_name: Name of the provider
            software_name: Software name
            context: Generation context
            
        Returns:
            Actual package name
        """
        # Try to find the package name from repository data
        for package in context.repository_data:
            if package.repository_name.lower() == provider_name.lower():
                return package.name
        
        # Fallback to software name with provider-specific transformations
        name = software_name.lower()
        
        # Provider-specific naming conventions
        if provider_name == "apt":
            # APT often uses lowercase with hyphens
            return name.replace('_', '-')
        elif provider_name in ["dnf", "yum"]:
            # RPM-based often use lowercase
            return name
        elif provider_name == "brew":
            # Homebrew uses lowercase
            return name
        elif provider_name == "winget":
            # WinGet often uses PascalCase
            return software_name
        
        return name
    
    def _get_package_alternatives(self, provider_name: str, software_name: str) -> List[str]:
        """Get alternative package names for a provider.
        
        Args:
            provider_name: Name of the provider
            software_name: Software name
            
        Returns:
            List of alternative package names
        """
        alternatives = []
        name_lower = software_name.lower()
        
        # Common alternatives based on software type
        if 'server' in name_lower:
            alternatives.append(f"{name_lower}-server")
            alternatives.append(f"{name_lower}-daemon")
        
        if 'client' in name_lower:
            alternatives.append(f"{name_lower}-client")
            alternatives.append(f"{name_lower}-cli")
        
        # Provider-specific alternatives
        if provider_name == "apt":
            alternatives.append(f"{name_lower}-common")
            alternatives.append(f"{name_lower}-utils")
        
        return alternatives[:3]  # Limit to 3 alternatives

    async def cleanup(self) -> None:
        """Cleanup engine resources."""
        await self.provider_manager.cleanup()
    
    def _initialize_rag_components(self) -> None:
        """Initialize RAG components if available."""
        try:
            # Get RAG configuration
            rag_config = self.config.get("rag", {})
            
            if rag_config.get("enabled", True):
                # Initialize RAG indexer
                index_dir = rag_config.get("index_dir", "~/.saigen/rag_index")
                model_name = rag_config.get("model_name", "all-MiniLM-L6-v2")
                
                # Expand user path
                index_path = Path(index_dir).expanduser()
                
                self.rag_indexer = RAGIndexer(
                    index_dir=index_path,
                    model_name=model_name
                )
                
                self.rag_context_builder = RAGContextBuilder(
                    self.rag_indexer, 
                    config=rag_config
                )
                
                logger.info(f"RAG components initialized with model: {model_name}")
            else:
                logger.info("RAG components disabled in configuration")
                
        except Exception as e:
            logger.warning(f"Failed to initialize RAG components: {e}")
            self.rag_indexer = None
            self.rag_context_builder = None
    
    def _initialize_providers(self) -> None:
        """Initialize providers for backward compatibility with tests."""
        # This method provides backward compatibility with tests that expect _llm_providers
        # In the actual implementation, we use provider_manager
        pass
    
    def _get_llm_provider(self, provider: Union[str, LLMProvider]) -> BaseLLMProvider:
        """Get LLM provider instance.
        
        Args:
            provider: Provider name or LLMProvider enum
            
        Returns:
            Provider instance
            
        Raises:
            ProviderNotAvailableError: If provider is not available
        """
        provider_name = provider.value if hasattr(provider, 'value') else str(provider)
        
        # Check if provider is available through provider manager
        available_providers = self.provider_manager.get_available_providers()
        if provider_name not in available_providers:
            raise ProviderNotAvailableError(f"Provider '{provider_name}' is not available")
        
        # For backward compatibility, return from _llm_providers if available
        if provider_name in self._llm_providers:
            return self._llm_providers[provider_name]
        
        # Otherwise, get from provider manager (this is the real implementation)
        provider_instance = self.provider_manager.get_provider(provider_name)
        if not provider_instance:
            raise ProviderNotAvailableError(f"Provider '{provider_name}' is not configured")
        
        return provider_instance