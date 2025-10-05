"""Core generation engine for orchestrating saidata creation."""

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import yaml

from ..llm.provider_manager import LLMProviderManager
from ..llm.providers.base import BaseLLMProvider
from ..models.generation import GenerationContext, GenerationRequest, GenerationResult, LLMProvider
from ..models.generation import ValidationError as GenValidationError
from ..models.repository import RepositoryPackage
from ..models.saidata import SaiData
from ..repositories.cache import RepositoryCache
from ..repositories.indexer import RAGContextBuilder, RAGIndexer
from .context_builder import EnhancedContextBuilder
from .url_filter import URLValidationFilter
from .validator import SaidataValidator, ValidationResult

if TYPE_CHECKING:
    from ..utils.generation_logger import GenerationLogger

logger = logging.getLogger(__name__)


class GenerationEngineError(Exception):
    """Base exception for generation engine errors."""


class ProviderNotAvailableError(GenerationEngineError):
    """LLM provider is not available or configured."""


class ValidationFailedError(GenerationEngineError):
    """Generated saidata failed validation."""


class GenerationEngine:
    """Core engine for orchestrating saidata creation."""

    def __init__(self, config=None):
        """Initialize generation engine.

        Args:
            config: Engine configuration (SaigenConfig instance or dict)
        """
        # Handle both Pydantic model and dict config
        if hasattr(config, "model_dump"):
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

        # Initialize enhanced context builder
        self.enhanced_context_builder = EnhancedContextBuilder(self.rag_context_builder)

        # Backward compatibility: expose providers dict for tests
        self._llm_providers = {}
        self._initialize_providers()

        # Cache for repository manager data
        self._available_providers = None

        # Generation tracking
        self._generation_count = 0
        self._total_tokens_used = 0
        self._total_cost = 0.0

        # Generation logger
        self.logger: Optional["GenerationLogger"] = None

        # URL validation filter configuration
        # Try to get from generation config first, then fall back to root config
        gen_config = self.config.get("generation", {})
        if isinstance(gen_config, dict):
            self.enable_url_filter = gen_config.get("enable_url_filter", True)
            self.url_filter_timeout = gen_config.get("url_filter_timeout", 5)
            self.url_filter_max_concurrent = gen_config.get("url_filter_max_concurrent", 10)
        else:
            # If generation config is a Pydantic model
            self.enable_url_filter = getattr(gen_config, "enable_url_filter", True)
            self.url_filter_timeout = getattr(gen_config, "url_filter_timeout", 5)
            self.url_filter_max_concurrent = getattr(gen_config, "url_filter_max_concurrent", 10)

    def set_logger(self, logger: "GenerationLogger") -> None:
        """Set the generation logger.

        Args:
            logger: GenerationLogger instance
        """
        self.logger = logger

    def _get_default_providers(self) -> List[str]:
        """Get default providers from configuration or repository manager.

        Returns:
            List of default provider names
        """
        # Try to get from config first
        if self.config_obj and hasattr(self.config_obj, "generation"):
            return self.config_obj.generation.default_providers
        elif isinstance(self.config, dict) and "generation" in self.config:
            gen_config = self.config["generation"]
            if isinstance(gen_config, dict) and "default_providers" in gen_config:
                return gen_config["default_providers"]

        # Get from repository manager if available
        if self.repository_cache and hasattr(self.repository_cache, "manager"):
            try:
                supported_types = self.repository_cache.manager.get_supported_types()
                if supported_types:
                    return supported_types[:3]  # Return first 3 as defaults
            except Exception as e:
                logger.debug(f"Could not get supported types from repository manager: {e}")

        # Fallback: return empty list, let the request specify providers
        return []

    def _get_available_providers(self) -> List[str]:
        """Get list of available providers from repository manager.

        Returns:
            List of available provider type names
        """
        if self._available_providers is not None:
            return self._available_providers

        # Get from repository manager if available
        if self.repository_cache and hasattr(self.repository_cache, "manager"):
            try:
                self._available_providers = self.repository_cache.manager.get_supported_types()
                return self._available_providers
            except Exception as e:
                logger.debug(f"Could not get supported types from repository manager: {e}")

        # Fallback: return empty list
        self._available_providers = []
        return self._available_providers

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
            logger.info(
                f"Starting saidata generation for '{request.software_name}' using 0.3 schema"
            )

            if self.logger:
                with self.logger.log_step("validate_request", "Validating generation request"):
                    # Validate request
                    self._validate_request(request)
            else:
                # Validate request
                self._validate_request(request)

            # Build enhanced generation context for 0.3 schema
            if self.logger:
                with self.logger.log_step(
                    "build_context", "Building enhanced generation context for 0.3 schema"
                ):
                    context = await self._build_enhanced_generation_context_v03(request)
                    self.logger.log_generation_context(context)
            else:
                context = await self._build_enhanced_generation_context_v03(request)

            # Generate saidata using LLM with fallback
            provider_name = (
                request.llm_provider.value
                if hasattr(request.llm_provider, "value")
                else request.llm_provider
            )

            if self.logger:
                with self.logger.log_step(
                    "llm_generation", f"Generating saidata using {provider_name}"
                ):
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
                        context=context, preferred_provider=provider_name
                    )

            # Parse and validate generated YAML
            if self.logger:
                with self.logger.log_step(
                    "parse_validate", "Parsing and validating generated YAML"
                ):
                    saidata = await self._parse_and_validate_yaml(
                        llm_response.content, request.software_name, context, provider_name
                    )
            else:
                saidata = await self._parse_and_validate_yaml(
                    llm_response.content, request.software_name, context, provider_name
                )

            # Apply URL validation filter if enabled
            if self.enable_url_filter:
                if self.logger:
                    with self.logger.log_step("url_filter", "Validating and filtering URLs"):
                        saidata = await self._apply_url_filter(saidata)
                else:
                    saidata = await self._apply_url_filter(saidata)

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
                cost_estimate=llm_response.cost_estimate,
            )

            logger.info(
                f"Successfully generated saidata for '{
                    request.software_name}' in {
                    generation_time:.2f}s")
            return result

        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Failed to generate saidata for '{request.software_name}': {e}")

            if self.logger:
                self.logger.log_error(f"Generation failed: {e}")

            return GenerationResult(
                success=False,
                saidata=None,
                validation_errors=[
                    GenValidationError(field="generation", message=str(e), severity="error")
                ],
                warnings=[],
                generation_time=generation_time,
                llm_provider_used=request.llm_provider.value
                if hasattr(request.llm_provider, "value")
                else request.llm_provider,
                repository_sources_used=[],
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
        provider_name = (
            request.llm_provider.value
            if hasattr(request.llm_provider, "value")
            else request.llm_provider
        )
        if provider_name not in available_providers:
            raise ProviderNotAvailableError(
                f"Requested provider '{provider_name}' is not available"
            )

    async def _build_generation_context(self, request: GenerationRequest) -> GenerationContext:
        """Build generation context from request.

        Args:
            request: Generation request

        Returns:
            GenerationContext with all necessary data
        """
        # Use configured default_providers if no target_providers specified
        default_providers = self._get_default_providers()

        context = GenerationContext(
            software_name=request.software_name,
            target_providers=request.target_providers or default_providers,
            user_hints=request.user_hints,
            existing_saidata=request.existing_saidata,
        )

        # RAG integration for enhanced context
        if request.use_rag and self.rag_context_builder:
            try:
                if self.logger:
                    with self.logger.log_data_op(
                        "rag_query", f"Building RAG context for {request.software_name}"
                    ) as log_output:
                        rag_context = await self.rag_context_builder.build_context(
                            software_name=request.software_name,
                            target_providers=request.target_providers,
                            max_packages=5,
                            max_saidata=3,
                        )

                        # Log the RAG results
                        log_output(
                            {
                                "similar_packages_count": len(
                                    rag_context.get("similar_packages", [])
                                ),
                                "similar_saidata_count": len(
                                    rag_context.get("similar_saidata", [])
                                ),
                                "sample_saidata_count": len(rag_context.get("sample_saidata", [])),
                            }
                        )
                else:
                    rag_context = await self.rag_context_builder.build_context(
                        software_name=request.software_name,
                        target_providers=request.target_providers,
                        max_packages=5,
                        max_saidata=3,
                    )

                # Inject RAG data into context
                context.repository_data = rag_context.get("similar_packages", [])
                context.similar_saidata = rag_context.get("similar_saidata", [])
                context.sample_saidata = rag_context.get("sample_saidata", [])

                logger.debug(
                    f"RAG context built: {
                        len(
                            context.repository_data)} packages, {
                        len(
                            context.similar_saidata)} similar saidata, {
                        len(
                            context.sample_saidata)} sample saidata")

            except Exception as e:
                logger.warning(f"Failed to build RAG context for {request.software_name}: {e}")
                if self.logger:
                    self.logger.log_error(f"RAG context building failed: {e}")
                # Continue without RAG context

        return context

    async def _build_enhanced_generation_context_v03(
        self, request: GenerationRequest
    ) -> GenerationContext:
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
                with self.logger.log_step(
                    "enhance_context_v03", "Enhancing context for 0.3 schema"
                ):
                    enhanced_context = await self.enhanced_context_builder.build_enhanced_context(
                        context
                    )

                    # Log enhancement details
                    enhancement_info = {
                        "installation_methods": getattr(
                            enhanced_context, "likely_installation_methods", []
                        ),
                        "software_category": getattr(
                            enhanced_context, "software_category", "unknown"
                        ),
                        "has_security_template": hasattr(
                            enhanced_context, "security_metadata_template"
                        ),
                        "has_compatibility_template": hasattr(
                            enhanced_context, "compatibility_matrix_template"
                        ),
                    }
                    self.logger.log_generation_context_enhancement(enhancement_info)
            else:
                enhanced_context = await self.enhanced_context_builder.build_enhanced_context(
                    context
                )

            logger.debug(f"Enhanced context built for {request.software_name} with 0.3 features")
            return enhanced_context

        except Exception as e:
            logger.warning(f"Failed to enhance context for 0.3 schema: {e}")
            if self.logger:
                self.logger.log_error(f"Context enhancement failed: {e}")
            # Return base context if enhancement fails
            return context

    async def _parse_and_validate_yaml(
        self,
        yaml_content: str,
        software_name: str,
        context: Optional[GenerationContext] = None,
        provider_name: Optional[str] = None,
        is_retry: bool = False,
    ) -> SaiData:
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
                with self.logger.log_data_op(
                    "yaml_parsing", "Parsing generated YAML content"
                ) as log_output:
                    # Clean YAML content (remove markdown code blocks if present)
                    cleaned_yaml = self._clean_yaml_content(yaml_content)

                    # Parse YAML
                    data = yaml.safe_load(cleaned_yaml)
                    if not isinstance(data, dict):
                        raise ValidationFailedError(
                            "Generated content is not a valid YAML dictionary"
                        )

                    log_output(
                        {
                            "original_length": len(yaml_content),
                            "cleaned_length": len(cleaned_yaml),
                            "parsed_keys": list(data.keys()) if isinstance(data, dict) else [],
                            "is_retry": is_retry,
                        }
                    )
            else:
                # Clean YAML content (remove markdown code blocks if present)
                cleaned_yaml = self._clean_yaml_content(yaml_content)

                # Parse YAML
                data = yaml.safe_load(cleaned_yaml)
                if not isinstance(data, dict):
                    raise ValidationFailedError("Generated content is not a valid YAML dictionary")

            if self.logger:
                with self.logger.log_data_op(
                    "schema_validation", "Validating against saidata schema"
                ) as log_output:
                    # Validate against schema
                    validation_result = self.validator.validate_data(
                        data, f"generated:{software_name}"
                    )

                    log_output(
                        {
                            "is_valid": validation_result.is_valid,
                            "error_count": len(validation_result.errors),
                            "warning_count": len(validation_result.warnings),
                            "is_retry": is_retry,
                        }
                    )

                    if not validation_result.is_valid:
                        error_messages = [error.message for error in validation_result.errors]
                        validation_error = f"Schema validation failed: {'; '.join(error_messages)}"

                        # If this is not a retry and we have context, attempt a second query
                        if not is_retry and context and provider_name:
                            return await self._retry_generation_with_validation_feedback(
                                context,
                                provider_name,
                                yaml_content,
                                validation_error,
                                error_messages,
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
                with self.logger.log_data_op(
                    "model_validation", "Validating Pydantic model"
                ) as log_output:
                    # Convert to Pydantic model
                    saidata = SaiData(**data)

                    # Additional validation of the Pydantic model
                    model_validation = self.validator.validate_pydantic_model(saidata)

                    log_output(
                        {
                            "model_created": True,
                            "model_validation_valid": model_validation.is_valid,
                            "model_error_count": len(model_validation.errors),
                            "is_retry": is_retry,
                        }
                    )

                    if not model_validation.is_valid:
                        error_messages = [error.message for error in model_validation.errors]
                        validation_error = f"Model validation failed: {'; '.join(error_messages)}"

                        # If this is not a retry and we have context, attempt a second query
                        if not is_retry and context and provider_name:
                            return await self._retry_generation_with_validation_feedback(
                                context,
                                provider_name,
                                yaml_content,
                                validation_error,
                                error_messages,
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

            # Deduplicate provider configurations before returning
            saidata = self._deduplicate_provider_configs(saidata)

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
        error_messages: List[str],
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
        logger.info(
            f"First generation attempt failed validation for '{
                context.software_name}', retrying with feedback")

        if self.logger:
            self.logger.log_error(f"First attempt validation failed: {validation_error}")
            with self.logger.log_step(
                "retry_generation", "Retrying generation with validation feedback"
            ):
                # Create enhanced context with validation feedback
                retry_context = self._create_retry_context(
                    context, failed_yaml, validation_error, error_messages
                )

                # Generate with retry context
                retry_response = await self._generate_with_logged_llm_retry(
                    retry_context, provider_name
                )

                # Parse and validate the retry response (mark as retry to prevent infinite loop)
                return await self._parse_and_validate_yaml(
                    retry_response.content, context.software_name, is_retry=True
                )
        else:
            # Create enhanced context with validation feedback
            retry_context = self._create_retry_context(
                context, failed_yaml, validation_error, error_messages
            )

            # Generate with retry context
            if provider_name in self._llm_providers:
                mock_provider = self._llm_providers[provider_name]
                retry_response = await mock_provider.generate_saidata(retry_context)
            else:
                retry_response = await self.provider_manager.generate_with_fallback(
                    context=retry_context, preferred_provider=provider_name
                )

            # Parse and validate the retry response (mark as retry to prevent infinite loop)
            return await self._parse_and_validate_yaml(
                retry_response.content, context.software_name, is_retry=True
            )

    def _create_retry_context(
        self,
        original_context: GenerationContext,
        failed_yaml: str,
        validation_error: str,
        error_messages: List[str],
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
            "failed_yaml_excerpt": failed_yaml[:500] + "..."
            if len(failed_yaml) > 500
            else failed_yaml,
            "retry_instructions": [
                "The previous generation attempt failed validation",
                "Please fix the specific validation errors mentioned above",
                "Ensure the YAML follows the exact saidata schema requirements",
                "Pay special attention to required fields and proper data types",
                "Generate only valid YAML without any markdown formatting",
            ],
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
            similar_saidata=original_context.similar_saidata,
        )

        # Copy sample_saidata if it exists
        if hasattr(original_context, "sample_saidata"):
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
                context=context, preferred_provider=provider_name
            )

            # Calculate duration
            llm_duration = time.time() - llm_start_time

            # Log the successful retry interaction
            if self.logger:
                self.logger.log_llm_interaction(
                    provider=provider_name,
                    model=getattr(llm_response, "model", "unknown"),
                    prompt=prompt,
                    response=llm_response.content,
                    tokens_used=llm_response.tokens_used,
                    cost_estimate=llm_response.cost_estimate,
                    duration_seconds=llm_duration,
                    success=True,
                    metadata={"retry_attempt": True},
                )

            return llm_response

        except Exception as e:
            # Calculate duration
            llm_duration = time.time() - llm_start_time

            # Log the failed retry interaction
            if self.logger:
                self.logger.log_llm_interaction(
                    provider=provider_name,
                    model="unknown",
                    prompt=prompt,
                    response="",
                    duration_seconds=llm_duration,
                    success=False,
                    error=str(e),
                    metadata={"retry_attempt": True},
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
                context=context, preferred_provider=provider_name
            )

            # Calculate duration
            llm_duration = time.time() - llm_start_time

            # Log the successful interaction
            if self.logger:
                self.logger.log_llm_interaction(
                    provider=provider_name,
                    model=getattr(llm_response, "model", "unknown"),
                    prompt=prompt,
                    response=llm_response.content,
                    tokens_used=llm_response.tokens_used,
                    cost_estimate=llm_response.cost_estimate,
                    duration_seconds=llm_duration,
                    success=True,
                )

            return llm_response

        except Exception as e:
            # Calculate duration
            llm_duration = time.time() - llm_start_time

            # Log the failed interaction
            if self.logger:
                self.logger.log_llm_interaction(
                    provider=provider_name,
                    model="unknown",
                    prompt=prompt,
                    response="",
                    duration_seconds=llm_duration,
                    success=False,
                    error=str(e),
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
        content = re.sub(r"^```(?:yaml|yml)?\s*\n", "", content, flags=re.MULTILINE)
        content = re.sub(r"\n```\s*$", "", content, flags=re.MULTILINE)

        # Remove any remaining ``` at the beginning or end
        content = content.strip("`").strip()

        return content

    def _deduplicate_provider_configs(self, saidata: SaiData) -> SaiData:
        """Remove redundant provider configurations that duplicate top-level definitions.

        This function compares provider-specific resources (packages, services, files, directories,
        commands, ports) with top-level definitions and removes entries that are identical.

        Args:
            saidata: SaiData instance to deduplicate

        Returns:
            SaiData instance with deduplicated provider configurations
        """
        if not saidata.providers:
            return saidata

        # Build lookup indexes for all top-level resources
        top_level_packages = self._build_resource_index(
            saidata.packages, lambda p: (p.name, p.package_name)
        )
        top_level_services = self._build_resource_index(
            saidata.services, lambda s: (s.name, s.service_name)
        )
        top_level_files = self._build_resource_index(saidata.files, lambda f: (f.name, f.path))
        top_level_directories = self._build_resource_index(
            saidata.directories, lambda d: (d.name, d.path)
        )
        top_level_commands = self._build_resource_index(
            saidata.commands, lambda c: (c.name, c.path)
        )
        top_level_ports = self._build_resource_index(saidata.ports, lambda p: (p.port, p.protocol))

        # Process each provider
        for provider_name, provider_config in saidata.providers.items():
            # Deduplicate packages
            if provider_config.packages:
                provider_config.packages = self._deduplicate_packages(
                    provider_config.packages, top_level_packages, provider_name
                )

            # Deduplicate services
            if provider_config.services:
                provider_config.services = self._deduplicate_services(
                    provider_config.services, top_level_services, provider_name
                )

            # Deduplicate files
            if provider_config.files:
                provider_config.files = self._deduplicate_files(
                    provider_config.files, top_level_files, provider_name
                )

            # Deduplicate directories
            if provider_config.directories:
                provider_config.directories = self._deduplicate_directories(
                    provider_config.directories, top_level_directories, provider_name
                )

            # Deduplicate commands
            if provider_config.commands:
                provider_config.commands = self._deduplicate_commands(
                    provider_config.commands, top_level_commands, provider_name
                )

            # Deduplicate ports
            if provider_config.ports:
                provider_config.ports = self._deduplicate_ports(
                    provider_config.ports, top_level_ports, provider_name
                )

        return saidata

    def _build_resource_index(self, resources, key_func):
        """Build an index of resources for quick lookup."""
        if not resources:
            return {}
        index = {}
        for resource in resources:
            try:
                key = key_func(resource)
                index[key] = resource
            except (AttributeError, TypeError):
                continue
        return index

    def _deduplicate_packages(self, provider_packages, top_level_index, provider_name):
        """Deduplicate provider packages against top-level."""
        filtered = []
        for pkg in provider_packages:
            key = (pkg.name, pkg.package_name)
            if key in top_level_index:
                top_pkg = top_level_index[key]
                if self._package_has_differences(pkg, top_pkg):
                    filtered.append(pkg)
                else:
                    logger.debug(
                        f"Removing duplicate package '{pkg.name}' from provider '{provider_name}'"
                    )
            else:
                filtered.append(pkg)
        return filtered if filtered else None

    def _deduplicate_services(self, provider_services, top_level_index, provider_name):
        """Deduplicate provider services against top-level."""
        filtered = []
        for svc in provider_services:
            key = (svc.name, svc.service_name)
            if key in top_level_index:
                top_svc = top_level_index[key]
                if self._service_has_differences(svc, top_svc):
                    filtered.append(svc)
                else:
                    logger.debug(
                        f"Removing duplicate service '{svc.name}' from provider '{provider_name}'"
                    )
            else:
                filtered.append(svc)
        return filtered if filtered else None

    def _deduplicate_files(self, provider_files, top_level_index, provider_name):
        """Deduplicate provider files against top-level."""
        filtered = []
        for file in provider_files:
            key = (file.name, file.path)
            if key in top_level_index:
                top_file = top_level_index[key]
                if self._file_has_differences(file, top_file):
                    filtered.append(file)
                else:
                    logger.debug(
                        f"Removing duplicate file '{file.name}' from provider '{provider_name}'"
                    )
            else:
                filtered.append(file)
        return filtered if filtered else None

    def _deduplicate_directories(self, provider_dirs, top_level_index, provider_name):
        """Deduplicate provider directories against top-level."""
        filtered = []
        for dir in provider_dirs:
            key = (dir.name, dir.path)
            if key in top_level_index:
                top_dir = top_level_index[key]
                if self._directory_has_differences(dir, top_dir):
                    filtered.append(dir)
                else:
                    logger.debug(
                        f"Removing duplicate directory '{dir.name}' from provider '{provider_name}'"
                    )
            else:
                filtered.append(dir)
        return filtered if filtered else None

    def _deduplicate_commands(self, provider_commands, top_level_index, provider_name):
        """Deduplicate provider commands against top-level."""
        filtered = []
        for cmd in provider_commands:
            key = (cmd.name, cmd.path)
            if key in top_level_index:
                top_cmd = top_level_index[key]
                if self._command_has_differences(cmd, top_cmd):
                    filtered.append(cmd)
                else:
                    logger.debug(
                        f"Removing duplicate command '{cmd.name}' from provider '{provider_name}'"
                    )
            else:
                filtered.append(cmd)
        return filtered if filtered else None

    def _deduplicate_ports(self, provider_ports, top_level_index, provider_name):
        """Deduplicate provider ports against top-level."""
        filtered = []
        for port in provider_ports:
            key = (port.port, port.protocol)
            if key in top_level_index:
                top_port = top_level_index[key]
                if self._port_has_differences(port, top_port):
                    filtered.append(port)
                else:
                    logger.debug(
                        f"Removing duplicate port {port.port} from provider '{provider_name}'"
                    )
            else:
                filtered.append(port)
        return filtered if filtered else None

    def _package_has_differences(self, pkg, top_pkg):
        """Check if package has differences from top-level."""
        return (
            (pkg.version and pkg.version != getattr(top_pkg, "version", None))
            or (pkg.alternatives and pkg.alternatives != getattr(top_pkg, "alternatives", None))
            or (
                pkg.install_options
                and pkg.install_options != getattr(top_pkg, "install_options", None)
            )
            or (pkg.repository and pkg.repository != getattr(top_pkg, "repository", None))
            or (
                hasattr(pkg, "checksum")
                and pkg.checksum
                and pkg.checksum != getattr(top_pkg, "checksum", None)
            )
            or (
                hasattr(pkg, "signature")
                and pkg.signature
                and pkg.signature != getattr(top_pkg, "signature", None)
            )
            or (
                hasattr(pkg, "download_url")
                and pkg.download_url
                and pkg.download_url != getattr(top_pkg, "download_url", None)
            )
        )

    def _service_has_differences(self, svc, top_svc):
        """Check if service has differences from top-level."""
        return (
            (hasattr(svc, "type") and svc.type != getattr(top_svc, "type", None))
            or (hasattr(svc, "enabled") and svc.enabled != getattr(top_svc, "enabled", None))
            or (
                hasattr(svc, "config_files")
                and svc.config_files != getattr(top_svc, "config_files", None)
            )
            or (
                hasattr(svc, "start_command")
                and svc.start_command != getattr(top_svc, "start_command", None)
            )
            or (
                hasattr(svc, "stop_command")
                and svc.stop_command != getattr(top_svc, "stop_command", None)
            )
        )

    def _file_has_differences(self, file, top_file):
        """Check if file has differences from top-level."""
        return (
            (hasattr(file, "type") and file.type != getattr(top_file, "type", None))
            or (hasattr(file, "owner") and file.owner != getattr(top_file, "owner", None))
            or (hasattr(file, "group") and file.group != getattr(top_file, "group", None))
            or (hasattr(file, "mode") and file.mode != getattr(top_file, "mode", None))
            or (hasattr(file, "backup") and file.backup != getattr(top_file, "backup", None))
            or (hasattr(file, "template") and file.template != getattr(top_file, "template", None))
        )

    def _directory_has_differences(self, dir, top_dir):
        """Check if directory has differences from top-level."""
        return (
            (hasattr(dir, "owner") and dir.owner != getattr(top_dir, "owner", None))
            or (hasattr(dir, "group") and dir.group != getattr(top_dir, "group", None))
            or (hasattr(dir, "mode") and dir.mode != getattr(top_dir, "mode", None))
            or (hasattr(dir, "create") and dir.create != getattr(top_dir, "create", None))
        )

    def _command_has_differences(self, cmd, top_cmd):
        """Check if command has differences from top-level."""
        return (
            (
                hasattr(cmd, "shell_completion")
                and cmd.shell_completion != getattr(top_cmd, "shell_completion", None)
            )
            or (hasattr(cmd, "man_page") and cmd.man_page != getattr(top_cmd, "man_page", None))
            or (
                hasattr(cmd, "description")
                and cmd.description != getattr(top_cmd, "description", None)
            )
        )

    def _port_has_differences(self, port, top_port):
        """Check if port has differences from top-level."""
        return (
            hasattr(port, "service") and port.service != getattr(top_port, "service", None)
        ) or (
            hasattr(port, "description")
            and port.description != getattr(top_port, "description", None)
        )

    async def _apply_url_filter(self, saidata: SaiData) -> SaiData:
        """Apply URL validation filter to saidata.

        Args:
            saidata: SaiData instance to filter

        Returns:
            Filtered SaiData instance with only reachable URLs
        """
        try:
            async with URLValidationFilter(
                timeout=self.url_filter_timeout, max_concurrent=self.url_filter_max_concurrent
            ) as url_filter:
                filtered_saidata = await url_filter.filter_saidata(saidata)
                logger.info(f"URL filtering completed for {saidata.metadata.name}")
                return filtered_saidata
        except Exception as e:
            logger.warning(f"URL filtering failed: {e}. Returning unfiltered saidata.")
            if self.logger:
                self.logger.log_error(f"URL filtering error: {e}")
            # Return original saidata if filtering fails
            return saidata

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
                with self.logger.log_data_op(
                    "file_save", f"Saving saidata to {output_path}"
                ) as log_output:
                    # Ensure output directory exists
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Convert to dict and save as YAML
                    data = saidata.model_dump(exclude_none=True)

                    with open(output_path, "w", encoding="utf-8") as f:
                        yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)

                    # Log file details
                    file_size = output_path.stat().st_size
                    log_output(
                        {
                            "output_path": str(output_path),
                            "file_size_bytes": file_size,
                            "providers_count": len(saidata.providers) if saidata.providers else 0,
                        }
                    )
            else:
                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Convert to dict and save as YAML
                data = saidata.model_dump(exclude_none=True)

                with open(output_path, "w", encoding="utf-8") as f:
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
            if hasattr(provider, "get_model_info"):
                model_info = provider.get_model_info()
                return {
                    "name": provider_name,
                    "available": True,
                    "model": model_info.name,
                    "max_tokens": model_info.max_tokens,
                    "context_window": model_info.context_window,
                    "capabilities": [cap.value for cap in model_info.capabilities],
                    "cost_per_1k_tokens": model_info.cost_per_1k_tokens,
                    "supports_streaming": model_info.supports_streaming,
                }

        # Check if provider exists in provider manager
        available_providers = self.provider_manager.get_available_providers()
        if provider_name not in available_providers:
            return None

        # For real implementation, we'd need async access to provider manager
        # For now, return basic info for compatibility
        return {"name": provider_name, "available": True, "configured": True}

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
                if self._generation_count > 0
                else 0
            ),
            "average_cost_per_generation": (
                self._total_cost / self._generation_count if self._generation_count > 0 else 0
            ),
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
                "last_error": status.last_error,
            }

            if status.model_info:
                result[name]["model_info"] = {
                    "name": status.model_info.name,
                    "provider": status.model_info.provider,
                    "max_tokens": status.model_info.max_tokens,
                    "context_window": status.model_info.context_window,
                    "capabilities": [cap.value for cap in status.model_info.capabilities],
                    "cost_per_1k_tokens": status.model_info.cost_per_1k_tokens,
                    "supports_streaming": status.model_info.supports_streaming,
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
        saidata_files: Optional[List[Path]] = None,
    ) -> Dict[str, bool]:
        """Rebuild RAG indices.

        Args:
            packages: Repository packages to index (if None, skip package index)
            saidata_files: Saidata files to index (if None, skip saidata index)

        Returns:
            Dictionary with rebuild results
        """
        if not self.rag_indexer:
            return {"package_index_rebuilt": False, "saidata_index_rebuilt": False}

        try:
            return await self.rag_indexer.rebuild_indices(packages, saidata_files)
        except Exception as e:
            logger.error(f"Failed to rebuild RAG indices: {e}")
            return {"package_index_rebuilt": False, "saidata_index_rebuilt": False}

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
        self, query: str, limit: int = 5, min_score: float = 0.3
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
        self, software_name: str, limit: int = 3, min_score: float = 0.4
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
        max_saidata: int = 3,
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
                "similar_packages": [],
                "similar_saidata": [],
                "sample_saidata": [],
                "provider_specific_packages": {},
                "context_summary": f"No RAG context available for {software_name}",
            }

        try:
            return await self.rag_context_builder.build_context(
                software_name, target_providers, max_packages, max_saidata
            )
        except Exception as e:
            logger.error(f"Failed to build RAG context: {e}")
            return {
                "similar_packages": [],
                "similar_saidata": [],
                "sample_saidata": [],
                "provider_specific_packages": {},
                "context_summary": f"Failed to build RAG context for {software_name}: {e}",
            }

    async def generate_sources(
        self, request: GenerationRequest, context: GenerationContext
    ) -> List[Dict[str, Any]]:
        """Generate source build configurations for 0.3 schema.

        Args:
            request: Generation request
            context: Generation context

        Returns:
            List of source configuration dictionaries
        """
        try:
            logger.debug(f"Generating source configurations for {request.software_name}")

            sources = []

            # Extract source URLs from repository data if available
            for pkg in context.repository_data:
                if hasattr(pkg, "source_url") and pkg.source_url:
                    source = {
                        "name": "main",
                        "url": pkg.source_url,
                        "build_system": self._detect_build_system(request.software_name, context),
                        "version": pkg.version if hasattr(pkg, "version") else "latest",
                    }

                    # Add prerequisites if available
                    prereqs = self._generate_prerequisites(request.software_name, context)
                    if prereqs:
                        source["prerequisites"] = prereqs

                    sources.append(source)
                    break  # Use first source found

            return sources

        except Exception as e:
            logger.warning(f"Failed to generate source configurations: {e}")
            return []

    async def generate_binaries(
        self, request: GenerationRequest, context: GenerationContext
    ) -> List[Dict[str, Any]]:
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

            # Extract binary download URLs from repository data if available
            for pkg in context.repository_data:
                if hasattr(pkg, "download_url") and pkg.download_url:
                    binary = {
                        "name": "main",
                        "url": pkg.download_url,
                        "version": pkg.version if hasattr(pkg, "version") else "latest",
                    }
                    binaries.append(binary)
                    break  # Use first binary found

            return binaries

        except Exception as e:
            logger.warning(f"Failed to generate binary configurations: {e}")
            return []

    async def generate_scripts(
        self, request: GenerationRequest, context: GenerationContext
    ) -> List[Dict[str, Any]]:
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

            # Extract script URLs from repository data if available
            for pkg in context.repository_data:
                if hasattr(pkg, "install_script_url") and pkg.install_script_url:
                    script = {
                        "name": "official",
                        "url": pkg.install_script_url,
                        "interpreter": "bash",
                        "timeout": 600,
                    }
                    scripts.append(script)
                    break  # Use first script found

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
        # Check repository data for build system hints
        for pkg in context.repository_data:
            if "cmake" in pkg.name.lower() or (
                pkg.description and "cmake" in pkg.description.lower()
            ):
                return "cmake"

        # Check for language-specific build systems
        name_lower = software_name.lower()
        if "rust" in name_lower or "cargo" in name_lower:
            return "custom"  # Cargo build
        elif "go" in name_lower:
            return "custom"  # Go build

        # Default fallback
        return "autotools"

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
        if "server" in software_name.lower() or "web" in software_name.lower():
            args.extend(["--with-http_ssl_module", "--with-http_v2_module"])

        if "database" in software_name.lower() or "sql" in software_name.lower():
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
            List of prerequisite packages (generic, provider-agnostic)
        """
        # Return generic build tools - specific packages should come from repository data
        prereqs = []

        # Check repository data for dependencies
        for pkg in context.repository_data:
            if pkg.dependencies:
                # Extract build-related dependencies
                for dep in pkg.dependencies:
                    if any(
                        term in dep.lower()
                        for term in ["build", "dev", "devel", "gcc", "make", "cmake"]
                    ):
                        prereqs.append(dep)

        return list(set(prereqs))  # Remove duplicates

    async def generate_enhanced_metadata(
        self, request: GenerationRequest, context: GenerationContext
    ) -> Dict[str, Any]:
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
                "version": "latest",
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
                "description": f"Software management configuration for {request.software_name}",
            }

    def _generate_enhanced_urls(
        self, software_name: str, context: GenerationContext
    ) -> Dict[str, str]:
        """Generate comprehensive URL types for enhanced metadata.

        Args:
            software_name: Name of the software
            context: Generation context

        Returns:
            Dictionary of URL types and values
        """
        urls = {}

        # Extract URLs from repository data
        for package in context.repository_data:
            if package.homepage:
                urls["website"] = package.homepage
            # Some packages have additional URL fields
            if hasattr(package, "source_url") and package.source_url:
                urls["source"] = package.source_url
            if hasattr(package, "documentation_url") and package.documentation_url:
                urls["documentation"] = package.documentation_url

        # Only return URLs we actually found from repository data
        return urls

    def _generate_security_metadata(
        self, software_name: str, context: GenerationContext
    ) -> Dict[str, Any]:
        """Generate security metadata fields for enhanced security information.

        Args:
            software_name: Name of the software
            context: Generation context

        Returns:
            Dictionary of security metadata
        """
        security = {}

        # Try to extract security information from repository data or context
        # Only include fields if we have actual data
        if hasattr(context, "security_info") and context.security_info:
            security = context.security_info

        # Return empty dict if no security metadata available
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

        # Extract tags from repository data
        for pkg in context.repository_data:
            if hasattr(pkg, "tags") and pkg.tags:
                if isinstance(pkg.tags, list):
                    tags.extend(pkg.tags)
                elif isinstance(pkg.tags, str):
                    tags.extend(pkg.tags.split(","))

            # Extract from category field
            if pkg.category:
                tags.append(pkg.category.lower())

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

        # Check repository data for category information
        for pkg in context.repository_data:
            if pkg.category:
                # Map common repository categories to our categories
                cat_lower = pkg.category.lower()
                if any(term in cat_lower for term in ["web", "httpd", "server"]):
                    return "web-server"
                elif any(term in cat_lower for term in ["database", "db"]):
                    return "database"
                elif any(term in cat_lower for term in ["devel", "development"]):
                    return "development-tool"
                elif any(term in cat_lower for term in ["admin", "system"]):
                    return "system-tool"

        # Fallback to generic keyword matching
        if any(term in name_lower for term in ["web", "server", "httpd"]):
            return "web-server"
        elif any(term in name_lower for term in ["database", "db", "sql"]):
            return "database"
        elif any(term in name_lower for term in ["cli", "command", "tool"]):
            return "cli-tool"
        elif any(term in name_lower for term in ["system", "admin", "monitor"]):
            return "system-tool"
        elif any(term in name_lower for term in ["container", "k8s", "kubernetes"]):
            return "container-tool"
        elif any(term in name_lower for term in ["runtime", "interpreter"]):
            return "runtime"

        return "application"

    def _detect_software_license(
        self, software_name: str, context: GenerationContext
    ) -> Optional[str]:
        """Detect likely software license based on repository data and context.

        Args:
            software_name: Name of the software
            context: Generation context

        Returns:
            License string or None
        """
        # Try to get license from repository data
        for pkg in context.repository_data:
            if pkg.license:
                return pkg.license

        # No license information available
        return None

    async def generate_compatibility_matrix(
        self, request: GenerationRequest, context: GenerationContext
    ) -> Dict[str, Any]:
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
                },
            }

            # Generate compatibility entries from repository data
            for pkg in context.repository_data:
                entry = {
                    "provider": pkg.repository_type
                    if hasattr(pkg, "repository_type")
                    else "unknown",
                    "supported": True,
                }

                # Add platform info if available
                if hasattr(pkg, "platform") and pkg.platform:
                    entry["platform"] = pkg.platform

                # Add architecture info if available
                if hasattr(pkg, "architecture") and pkg.architecture:
                    entry["architecture"] = pkg.architecture

                # Add version info if available
                if hasattr(pkg, "version") and pkg.version:
                    compatibility["versions"]["latest"] = pkg.version

                compatibility["matrix"].append(entry)

            return compatibility

        except Exception as e:
            logger.warning(f"Failed to generate compatibility matrix: {e}")
            return {}

    async def generate_enhanced_provider_configs(
        self, request: GenerationRequest, context: GenerationContext
    ) -> Dict[str, Any]:
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

            # Extract provider configurations from repository data
            for pkg in context.repository_data:
                if hasattr(pkg, "repository_type") and pkg.repository_type:
                    provider_name = pkg.repository_type
                    if provider_name not in providers:
                        providers[provider_name] = {
                            "package_name": pkg.name,
                            "version": pkg.version if hasattr(pkg, "version") else "latest",
                        }

                        # Add additional metadata if available
                        if hasattr(pkg, "repository_name") and pkg.repository_name:
                            providers[provider_name]["repository"] = pkg.repository_name

            return providers

        except Exception as e:
            logger.warning(f"Failed to generate enhanced provider configurations: {e}")
            return {}

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

                self.rag_indexer = RAGIndexer(index_dir=index_path, model_name=model_name)

                self.rag_context_builder = RAGContextBuilder(self.rag_indexer, config=rag_config)

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

    def _get_llm_provider(self, provider: Union[str, LLMProvider]) -> BaseLLMProvider:
        """Get LLM provider instance.

        Args:
            provider: Provider name or LLMProvider enum

        Returns:
            Provider instance

        Raises:
            ProviderNotAvailableError: If provider is not available
        """
        provider_name = provider.value if hasattr(provider, "value") else str(provider)

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
