"""vLLM local LLM provider implementation optimized for NVIDIA GPUs."""

import logging
from typing import Any, Dict, List, Optional

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
    BaseLLMProvider,
    ConfigurationError,
    ConnectionError,
    GenerationError,
    LLMResponse,
    ModelCapability,
    ModelInfo,
)

logger = logging.getLogger(__name__)


class VLLMProvider(BaseLLMProvider):
    """vLLM local LLM provider implementation for high-performance GPU inference.

    vLLM is optimized for NVIDIA GPUs and provides:
    - High throughput batch inference
    - Continuous batching for better GPU utilization
    - PagedAttention for efficient memory management
    - OpenAI-compatible API

    Ideal for DGX systems and other high-end NVIDIA hardware.
    """

    # Popular models optimized for vLLM
    KNOWN_MODELS = {
        "meta-llama/Llama-2-7b-chat-hf": {
            "max_tokens": 4096,
            "context_window": 4096,
            "capabilities": [ModelCapability.TEXT_GENERATION, ModelCapability.CODE_GENERATION],
            "gpu_memory_gb": 16,
        },
        "meta-llama/Llama-2-13b-chat-hf": {
            "max_tokens": 4096,
            "context_window": 4096,
            "capabilities": [ModelCapability.TEXT_GENERATION, ModelCapability.CODE_GENERATION],
            "gpu_memory_gb": 28,
        },
        "meta-llama/Llama-2-70b-chat-hf": {
            "max_tokens": 4096,
            "context_window": 4096,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.LARGE_CONTEXT,
            ],
            "gpu_memory_gb": 140,
        },
        "meta-llama/Meta-Llama-3-8B-Instruct": {
            "max_tokens": 8192,
            "context_window": 8192,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
            ],
            "gpu_memory_gb": 18,
        },
        "meta-llama/Meta-Llama-3-70B-Instruct": {
            "max_tokens": 8192,
            "context_window": 8192,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.LARGE_CONTEXT,
            ],
            "gpu_memory_gb": 140,
        },
        "mistralai/Mistral-7B-Instruct-v0.2": {
            "max_tokens": 8192,
            "context_window": 32768,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.LARGE_CONTEXT,
            ],
            "gpu_memory_gb": 16,
        },
        "mistralai/Mixtral-8x7B-Instruct-v0.1": {
            "max_tokens": 8192,
            "context_window": 32768,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.LARGE_CONTEXT,
            ],
            "gpu_memory_gb": 90,
        },
        "codellama/CodeLlama-34b-Instruct-hf": {
            "max_tokens": 16384,
            "context_window": 16384,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.LARGE_CONTEXT,
            ],
            "gpu_memory_gb": 70,
        },
        "Qwen/Qwen2-72B-Instruct": {
            "max_tokens": 32768,
            "context_window": 32768,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.LARGE_CONTEXT,
            ],
            "gpu_memory_gb": 145,
        },
    }

    DEFAULT_MODEL_CONFIG = {
        "max_tokens": 4096,
        "context_window": 4096,
        "cost_per_1k_tokens": 0.0,  # Local models are free
        "capabilities": [ModelCapability.TEXT_GENERATION, ModelCapability.CODE_GENERATION],
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize vLLM provider.

        Args:
            config: Configuration dictionary with base_url, model, etc.
        """
        if not OPENAI_AVAILABLE:
            raise ConfigurationError(
                "OpenAI library not available. Install with: pip install openai"
            )

        super().__init__(config)

        self.base_url = self.config.get("base_url", "http://localhost:8000/v1")
        self.model = self.config.get("model", "meta-llama/Meta-Llama-3-8B-Instruct")
        self.temperature = self.config.get("temperature", 0.1)
        self.max_tokens = self.config.get("max_tokens", 4096)
        self.timeout = self.config.get("timeout", 120)  # Longer timeout for large models

        # vLLM-specific parameters
        self.tensor_parallel_size = self.config.get("tensor_parallel_size", 1)
        self.gpu_memory_utilization = self.config.get("gpu_memory_utilization", 0.9)

        # Initialize OpenAI client (vLLM uses OpenAI-compatible API)
        self.client = AsyncOpenAI(
            api_key="not-needed",  # vLLM doesn't require API key
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.config.get("max_retries", 2),
        )

        # Initialize prompt manager
        self.prompt_manager = PromptManager()

    def _validate_config(self) -> None:
        """Validate vLLM provider configuration."""
        # Validate base_url format
        base_url = self.config.get("base_url", "http://localhost:8000/v1")
        if not base_url.startswith(("http://", "https://")):
            raise ConfigurationError("base_url must start with http:// or https://")

        # Validate model name
        model = self.config.get("model")
        if not model:
            raise ConfigurationError("model name is required for vLLM provider")

        # Validate numeric parameters
        temperature = self.config.get("temperature")
        if temperature is not None and (
            not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2
        ):
            raise ConfigurationError("temperature must be between 0 and 2")

        timeout = self.config.get("timeout")
        if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
            raise ConfigurationError("timeout must be a positive number")

        # Validate vLLM-specific parameters
        tensor_parallel_size = self.config.get("tensor_parallel_size")
        if tensor_parallel_size is not None and (
            not isinstance(tensor_parallel_size, int) or tensor_parallel_size < 1
        ):
            raise ConfigurationError("tensor_parallel_size must be a positive integer")

        gpu_memory_utilization = self.config.get("gpu_memory_utilization")
        if gpu_memory_utilization is not None and (
            not isinstance(gpu_memory_utilization, (int, float))
            or gpu_memory_utilization <= 0
            or gpu_memory_utilization > 1
        ):
            raise ConfigurationError("gpu_memory_utilization must be between 0 and 1")

    async def generate_saidata(self, context: GenerationContext) -> LLMResponse:
        """Generate saidata using vLLM local models.

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

            # Make API call using OpenAI-compatible interface
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at generating software metadata in YAML format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Extract content
            content = response.choices[0].message.content
            if not content:
                raise GenerationError("Empty response from vLLM API")

            # Extract token usage
            tokens_used = None
            if hasattr(response, "usage") and response.usage:
                tokens_used = response.usage.total_tokens

            return LLMResponse(
                content=content,
                tokens_used=tokens_used,
                cost_estimate=0.0,  # Local models are free
                model_used=self.model,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    "tensor_parallel_size": self.tensor_parallel_size,
                    "gpu_memory_utilization": self.gpu_memory_utilization,
                },
            )

        except openai.APIConnectionError as e:
            raise ConnectionError(f"vLLM connection failed: {e}")
        except openai.APITimeoutError:
            raise GenerationError("vLLM request timed out")
        except openai.APIError as e:
            raise GenerationError(f"vLLM API error: {e}")
        except Exception as e:
            raise GenerationError(f"Unexpected error during generation: {e}")

    def is_available(self) -> bool:
        """Check if vLLM provider is properly configured and available.

        Returns:
            True if provider is available, False otherwise
        """
        try:
            self._validate_config()
            return True
        except ConfigurationError:
            return False

    async def validate_connection(self) -> bool:
        """Validate connection to vLLM server.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to list models to check if server is running
            await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"vLLM connection validation failed: {e}")
            return False

    def get_model_info(self) -> ModelInfo:
        """Return information about the vLLM model being used.

        Returns:
            ModelInfo object with model details
        """
        # Use known model config if available, otherwise use defaults
        model_config = self.KNOWN_MODELS.get(self.model, self.DEFAULT_MODEL_CONFIG)

        return ModelInfo(
            name=self.model,
            provider="vllm",
            max_tokens=model_config["max_tokens"],
            context_window=model_config["context_window"],
            capabilities=model_config["capabilities"],
            cost_per_1k_tokens=0.0,  # Local models are free
            supports_streaming=True,
        )

    def get_available_models(self) -> List[str]:
        """Get list of known vLLM-compatible models.

        Returns:
            List of model names
        """
        return list(self.KNOWN_MODELS.keys())

    def get_model_requirements(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get hardware requirements for a specific model.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary with hardware requirements or None if unknown
        """
        model_config = self.KNOWN_MODELS.get(model_name)
        if model_config:
            return {
                "gpu_memory_gb": model_config.get("gpu_memory_gb"),
                "recommended_tensor_parallel": max(1, model_config.get("gpu_memory_gb", 0) // 40),
                "context_window": model_config["context_window"],
            }
        return None

    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for token usage.

        Args:
            tokens: Number of tokens

        Returns:
            Cost estimate (always 0.0 for local models)
        """
        return 0.0
