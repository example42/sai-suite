"""OpenAI LLM provider implementation."""

import logging
from typing import Any, Dict, List

try:
    import openai
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

from ...models.generation import GenerationContext
from ..prompts import PromptManager
from .base import (
    AuthenticationError,
    BaseLLMProvider,
    ConfigurationError,
    ConnectionError,
    GenerationError,
    LLMResponse,
    ModelCapability,
    ModelInfo,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider implementation."""

    # Model configurations
    MODELS = {
        "gpt-4o": {
            "max_tokens": 16384,
            "context_window": 128000,
            "cost_per_1k_tokens": 0.005,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.LARGE_CONTEXT,
            ],
        },
        "gpt-4o-mini": {
            "max_tokens": 16384,
            "context_window": 128000,
            "cost_per_1k_tokens": 0.00015,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.LARGE_CONTEXT,
            ],
        },
        "gpt-4-turbo": {
            "max_tokens": 4096,
            "context_window": 128000,
            "cost_per_1k_tokens": 0.01,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.LARGE_CONTEXT,
            ],
        },
        "gpt-4": {
            "max_tokens": 8192,
            "context_window": 8192,
            "cost_per_1k_tokens": 0.03,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.FUNCTION_CALLING,
            ],
        },
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI provider.

        Args:
            config: Configuration dictionary with api_key, model, etc.
        """
        if not OPENAI_AVAILABLE:
            raise ConfigurationError(
                "OpenAI library not available. Install with: pip install openai"
            )

        super().__init__(config)

        # Initialize OpenAI client
        api_key = self.config.get("api_key")
        if hasattr(api_key, "get_secret_value"):
            api_key = api_key.get_secret_value()

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.config.get("api_base"),
            timeout=self.config.get("timeout", 30),
            max_retries=self.config.get("max_retries", 3),
        )

        self.model = self.config.get("model") or "gpt-4o-mini"
        self.max_tokens = self.config.get("max_tokens") or 4000
        self.temperature = (
            self.config.get("temperature") if self.config.get("temperature") is not None else 0.1
        )

        # Initialize prompt manager
        self.prompt_manager = PromptManager()

    def _validate_config(self) -> None:
        """Validate OpenAI provider configuration."""
        required_fields = ["api_key"]

        for field in required_fields:
            if field not in self.config or not self.config[field]:
                raise ConfigurationError(f"Missing required configuration field: {field}")

        # Validate model
        model = self.config.get("model") or "gpt-4o-mini"
        if model and model not in self.MODELS:
            logger.warning(f"Unknown model '{model}', using default configuration")

        # Validate numeric parameters
        max_tokens = self.config.get("max_tokens")
        if max_tokens is not None and (not isinstance(max_tokens, int) or max_tokens <= 0):
            raise ConfigurationError("max_tokens must be a positive integer")

        temperature = self.config.get("temperature")
        if temperature is not None and (
            not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2
        ):
            raise ConfigurationError("temperature must be between 0 and 2")

    async def generate_saidata(self, context: GenerationContext) -> LLMResponse:
        """Generate saidata using OpenAI GPT models.

        Args:
            context: Generation context with software name, repository data, etc.

        Returns:
            LLMResponse containing generated saidata YAML content

        Raises:
            GenerationError: If generation fails
        """
        try:
            # Select appropriate template based on context
            template_name = "update" if context.existing_saidata else "generation"
            template = self.prompt_manager.get_template(template_name)

            # Render prompt
            prompt = template.render(context)

            logger.debug(f"Generated prompt for {context.software_name} ({len(prompt)} chars)")

            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert system administrator specializing in software metadata generation.",
                },
                {"role": "user", "content": prompt},
            ]

            # Make API call
            response = await self._make_api_call(messages)

            # Extract content
            content = response.choices[0].message.content
            if not content:
                raise GenerationError("Empty response from OpenAI API")

            # Calculate cost estimate
            tokens_used = response.usage.total_tokens if response.usage else None
            cost_estimate = self.estimate_cost(tokens_used) if tokens_used else None

            return LLMResponse(
                content=content,
                tokens_used=tokens_used,
                cost_estimate=cost_estimate,
                model_used=self.model,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens
                    if response.usage
                    else None,
                },
            )

        except openai.RateLimitError as e:
            raise RateLimitError(f"OpenAI rate limit exceeded: {e}")
        except openai.AuthenticationError as e:
            raise AuthenticationError(f"OpenAI authentication failed: {e}")
        except openai.APIConnectionError as e:
            raise ConnectionError(f"OpenAI connection failed: {e}")
        except openai.APIError as e:
            raise GenerationError(f"OpenAI API error: {e}")
        except Exception as e:
            raise GenerationError(f"Unexpected error during generation: {e}")

    async def _make_api_call(self, messages: List[Dict[str, str]]) -> Any:
        """Make API call to OpenAI with retry logic.

        Args:
            messages: List of message dictionaries

        Returns:
            OpenAI API response
        """
        try:
            # Use max_completion_tokens for newer models, max_tokens for older ones
            # Models like gpt-4o, gpt-4o-mini, o1, o1-mini require max_completion_tokens
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "response_format": {"type": "text"},
            }

            # Determine which parameter to use based on model
            if self.model and any(x in self.model.lower() for x in ["gpt-4o", "o1", "gpt-5"]):
                params["max_completion_tokens"] = self.max_tokens
            else:
                params["max_tokens"] = self.max_tokens

            response = await self.client.chat.completions.create(**params)
            return response
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    def is_available(self) -> bool:
        """Check if OpenAI provider is properly configured and available.

        Returns:
            True if provider is available, False otherwise
        """
        if not OPENAI_AVAILABLE:
            return False

        try:
            self._validate_config()
            return True
        except ConfigurationError:
            return False

    async def validate_connection(self) -> bool:
        """Validate connection to OpenAI API.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Make a simple API call to test connection
            response = await self.client.chat.completions.create(
                model=self.model, messages=[{"role": "user", "content": "Hello"}], max_tokens=5
            )
            return bool(response.choices)
        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {e}")
            return False

    def get_model_info(self) -> ModelInfo:
        """Return information about the OpenAI model being used.

        Returns:
            ModelInfo object with model details
        """
        model_config = self.MODELS.get(
            self.model,
            {
                "max_tokens": 4096,
                "context_window": 4096,
                "cost_per_1k_tokens": 0.002,
                "capabilities": [ModelCapability.TEXT_GENERATION],
            },
        )

        return ModelInfo(
            name=self.model,
            provider="openai",
            max_tokens=model_config["max_tokens"],
            context_window=model_config["context_window"],
            capabilities=model_config["capabilities"],
            cost_per_1k_tokens=model_config["cost_per_1k_tokens"],
            supports_streaming=True,
        )

    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models.

        Returns:
            List of model names
        """
        return list(self.MODELS.keys())

    def set_model(self, model: str) -> None:
        """Set the model to use for generation.

        Args:
            model: Model name

        Raises:
            ValueError: If model is not supported
        """
        if model not in self.MODELS:
            raise ValueError(f"Unsupported model: {model}. Available: {list(self.MODELS.keys())}")

        self.model = model

        # Update max_tokens based on model if not explicitly set
        if "max_tokens" not in self.config:
            self.max_tokens = min(self.MODELS[model]["max_tokens"], 4000)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for the provider.

        Returns:
            Dictionary with usage statistics
        """
        return {
            "provider": "openai",
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "available": self.is_available(),
        }
