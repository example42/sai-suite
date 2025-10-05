"""LLM provider management and selection logic."""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from ..models.generation import GenerationContext, LLMProvider
from .providers.base import (
    AuthenticationError,
    BaseLLMProvider,
    ConfigurationError,
    ConnectionError,
    GenerationError,
    LLMResponse,
    ModelInfo,
    RateLimitError,
)

try:
    from .providers.openai import OPENAI_AVAILABLE, OpenAIProvider
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAIProvider = None


logger = logging.getLogger(__name__)


# Import providers with availability checks
try:
    from .providers.anthropic import ANTHROPIC_AVAILABLE, AnthropicProvider
except ImportError:
    ANTHROPIC_AVAILABLE = False
    AnthropicProvider = None

try:
    from .providers.ollama import OllamaProvider

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    OllamaProvider = None

try:
    from .providers.vllm import VLLMProvider

    VLLM_AVAILABLE = True
except ImportError:
    VLLM_AVAILABLE = False
    VLLMProvider = None


class ProviderPriority(str, Enum):
    """Provider priority levels for fallback."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ProviderConfig:
    """Configuration for a specific provider."""

    provider_class: Type[BaseLLMProvider]
    config: Dict[str, Any]
    priority: ProviderPriority = ProviderPriority.MEDIUM
    enabled: bool = True
    max_retries: int = 2


@dataclass
class ProviderStatus:
    """Status information for a provider."""

    name: str
    available: bool
    configured: bool
    connection_valid: bool
    last_error: Optional[str] = None
    model_info: Optional[ModelInfo] = None


class LLMProviderManager:
    """Manager for LLM providers with fallback and selection logic."""

    # Registry of available provider classes
    PROVIDER_REGISTRY = {
        LLMProvider.OPENAI: OpenAIProvider if OPENAI_AVAILABLE else None,
        LLMProvider.ANTHROPIC: AnthropicProvider if ANTHROPIC_AVAILABLE else None,
        LLMProvider.OLLAMA: OllamaProvider if OLLAMA_AVAILABLE else None,
        LLMProvider.VLLM: VLLMProvider if VLLM_AVAILABLE else None,
    }

    def __init__(self, config: Dict[str, Dict[str, Any]]):
        """Initialize provider manager.

        Args:
            config: Dictionary mapping provider names to their configurations
        """
        self.config = config
        self.providers: Dict[str, ProviderConfig] = {}
        self.provider_instances: Dict[str, BaseLLMProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize provider configurations."""
        for provider_name, provider_config in self.config.items():
            try:
                provider_enum = LLMProvider(provider_name.lower())
                provider_class = self.PROVIDER_REGISTRY.get(provider_enum)

                if provider_class is None:
                    logger.warning(f"Provider '{provider_name}' not available or not installed")
                    continue

                # Handle both dict and Pydantic model configs
                if hasattr(provider_config, "model_dump"):
                    # Pydantic model
                    config_dict = provider_config.model_dump()
                elif hasattr(provider_config, "dict"):
                    # Pydantic v1 model
                    config_dict = provider_config.dict()
                else:
                    # Regular dict
                    config_dict = (
                        provider_config.copy()
                        if hasattr(provider_config, "copy")
                        else dict(provider_config)
                    )

                # Extract provider-specific config
                priority = ProviderPriority(config_dict.pop("priority", "medium"))
                enabled = config_dict.pop("enabled", True)
                max_retries = config_dict.pop("max_retries", 2)

                # Remove provider field if present (not needed for provider initialization)
                config_dict.pop("provider", None)

                self.providers[provider_name] = ProviderConfig(
                    provider_class=provider_class,
                    config=config_dict,
                    priority=priority,
                    enabled=enabled,
                    max_retries=max_retries,
                )

                logger.debug(f"Configured provider: {provider_name}")

            except (ValueError, KeyError) as e:
                logger.error(f"Invalid provider configuration for '{provider_name}': {e}")

    def get_provider(self, provider_name: str) -> Optional[BaseLLMProvider]:
        """Get a provider instance by name.

        Args:
            provider_name: Name of the provider

        Returns:
            Provider instance or None if not available
        """
        if provider_name not in self.provider_instances:
            provider_config = self.providers.get(provider_name)
            if not provider_config or not provider_config.enabled:
                return None

            try:
                instance = provider_config.provider_class(provider_config.config)
                self.provider_instances[provider_name] = instance
                logger.debug(f"Created provider instance: {provider_name}")
            except Exception as e:
                logger.error(f"Failed to create provider instance '{provider_name}': {e}")
                return None

        return self.provider_instances.get(provider_name)

    def get_available_providers(self) -> List[str]:
        """Get list of available and enabled providers.

        Returns:
            List of provider names
        """
        available = []
        for name, config in self.providers.items():
            if config.enabled:
                provider = self.get_provider(name)
                if provider and provider.is_available():
                    available.append(name)
        return available

    async def get_provider_status(self, provider_name: str) -> ProviderStatus:
        """Get detailed status for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            ProviderStatus object
        """
        provider = self.get_provider(provider_name)

        if not provider:
            return ProviderStatus(
                name=provider_name,
                available=False,
                configured=False,
                connection_valid=False,
                last_error="Provider not available or not configured",
            )

        try:
            available = provider.is_available()
            connection_valid = await provider.validate_connection() if available else False
            model_info = provider.get_model_info() if available else None

            return ProviderStatus(
                name=provider_name,
                available=available,
                configured=True,
                connection_valid=connection_valid,
                model_info=model_info,
            )

        except Exception as e:
            return ProviderStatus(
                name=provider_name,
                available=False,
                configured=True,
                connection_valid=False,
                last_error=str(e),
            )

    async def get_all_provider_status(self) -> Dict[str, ProviderStatus]:
        """Get status for all configured providers.

        Returns:
            Dictionary mapping provider names to their status
        """
        status_tasks = {name: self.get_provider_status(name) for name in self.providers.keys()}

        results = await asyncio.gather(*status_tasks.values(), return_exceptions=True)

        status_dict = {}
        for name, result in zip(status_tasks.keys(), results):
            if isinstance(result, Exception):
                status_dict[name] = ProviderStatus(
                    name=name,
                    available=False,
                    configured=False,
                    connection_valid=False,
                    last_error=str(result),
                )
            else:
                status_dict[name] = result

        return status_dict

    def select_best_provider(
        self,
        preferred_provider: Optional[str] = None,
        exclude_providers: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Select the best available provider based on priority and availability.

        Args:
            preferred_provider: Preferred provider name
            exclude_providers: List of providers to exclude

        Returns:
            Selected provider name or None if none available
        """
        exclude_providers = exclude_providers or []

        # If preferred provider is specified and available, use it
        if preferred_provider and preferred_provider not in exclude_providers:
            if preferred_provider in self.providers:
                provider = self.get_provider(preferred_provider)
                if provider and provider.is_available():
                    return preferred_provider

        # Sort providers by priority and select the best available one
        available_providers = []
        for name, config in self.providers.items():
            if name in exclude_providers or not config.enabled:
                continue

            provider = self.get_provider(name)
            if provider and provider.is_available():
                available_providers.append((name, config.priority))

        if not available_providers:
            return None

        # Sort by priority (HIGH > MEDIUM > LOW)
        priority_order = {
            ProviderPriority.HIGH: 3,
            ProviderPriority.MEDIUM: 2,
            ProviderPriority.LOW: 1,
        }

        available_providers.sort(key=lambda x: priority_order[x[1]], reverse=True)
        return available_providers[0][0]

    async def generate_with_fallback(
        self,
        context: GenerationContext,
        preferred_provider: Optional[str] = None,
        max_fallback_attempts: int = 3,
    ) -> LLMResponse:
        """Generate saidata with automatic fallback to other providers.

        Args:
            context: Generation context
            preferred_provider: Preferred provider name
            max_fallback_attempts: Maximum number of fallback attempts

        Returns:
            LLMResponse from successful provider

        Raises:
            GenerationError: If all providers fail
        """
        attempted_providers = []
        last_error = None

        for attempt in range(max_fallback_attempts):
            # Select provider (excluding already attempted ones)
            provider_name = self.select_best_provider(
                preferred_provider=preferred_provider if attempt == 0 else None,
                exclude_providers=attempted_providers,
            )

            if not provider_name:
                break

            attempted_providers.append(provider_name)
            provider = self.get_provider(provider_name)

            if not provider:
                continue

            try:
                logger.info(f"Attempting generation with provider: {provider_name}")
                response = await self._generate_with_retry(provider, context, provider_name)
                logger.info(f"Successfully generated saidata using provider: {provider_name}")
                return response

            except (RateLimitError, AuthenticationError) as e:
                # These errors are provider-specific, try next provider
                logger.warning(f"Provider {provider_name} failed with {type(e).__name__}: {e}")
                last_error = e
                continue

            except (ConnectionError, GenerationError) as e:
                # These might be temporary, try next provider
                logger.warning(f"Provider {provider_name} failed: {e}")
                last_error = e
                continue

            except Exception as e:
                # Unexpected error, log and try next provider
                logger.error(f"Unexpected error with provider {provider_name}: {e}")
                last_error = e
                continue

        # All providers failed
        error_msg = f"All providers failed. Attempted: {attempted_providers}"
        if last_error:
            error_msg += f". Last error: {last_error}"

        raise GenerationError(error_msg)

    async def _generate_with_retry(
        self, provider: BaseLLMProvider, context: GenerationContext, provider_name: str
    ) -> LLMResponse:
        """Generate with retry logic for a specific provider.

        Args:
            provider: Provider instance
            context: Generation context
            provider_name: Provider name for logging

        Returns:
            LLMResponse from provider

        Raises:
            LLMProviderError: If generation fails after retries
        """
        provider_config = self.providers[provider_name]
        max_retries = provider_config.max_retries

        for retry in range(max_retries + 1):
            try:
                return await provider.generate_saidata(context)

            except RateLimitError:
                if retry < max_retries:
                    # Exponential backoff for rate limits
                    wait_time = 2**retry
                    logger.info(
                        f"Rate limited, waiting {wait_time}s before retry {retry + 1}/{max_retries}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise

            except (ConnectionError, GenerationError) as e:
                if retry < max_retries:
                    # Short wait for connection/generation errors
                    wait_time = 1
                    logger.info(f"Retrying after error, attempt {retry + 1}/{max_retries}: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                raise

            except (AuthenticationError, ConfigurationError):
                # Don't retry these errors
                raise

    async def cleanup(self) -> None:
        """Cleanup provider resources."""
        for provider in self.provider_instances.values():
            if hasattr(provider, "__aexit__"):
                try:
                    await provider.__aexit__(None, None, None)
                except Exception as e:
                    logger.error(f"Error cleaning up provider: {e}")

        self.provider_instances.clear()
