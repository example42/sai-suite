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
        
        # Backward compatibility: expose providers dict for tests
        self._llm_providers = {}
        self._initialize_providers()
        
        # Generation tracking
        self._generation_count = 0
        self._total_tokens_used = 0
        self._total_cost = 0.0
    

    
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
            
            # Build generation context
            context = await self._build_generation_context(request)
            
            # Generate saidata using LLM with fallback
            provider_name = request.llm_provider.value if hasattr(request.llm_provider, 'value') else request.llm_provider
            
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
                rag_context = await self.rag_context_builder.build_context(
                    software_name=request.software_name,
                    target_providers=request.target_providers,
                    max_packages=5,
                    max_saidata=3
                )
                
                # Inject RAG data into context
                context.repository_data = rag_context.get('similar_packages', [])
                context.similar_saidata = rag_context.get('similar_saidata', [])
                
                logger.debug(f"RAG context built: {len(context.repository_data)} packages, {len(context.similar_saidata)} saidata examples")
                
            except Exception as e:
                logger.warning(f"Failed to build RAG context for {request.software_name}: {e}")
                # Continue without RAG context
        
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
                
                self.rag_context_builder = RAGContextBuilder(self.rag_indexer)
                
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