"""LLM provider implementations."""

from .base import (
    BaseLLMProvider,
    LLMResponse,
    ModelInfo,
    ModelCapability,
    LLMProviderError,
    ConfigurationError,
    ConnectionError,
    GenerationError,
    RateLimitError,
    AuthenticationError
)

try:
    from .openai import OpenAIProvider
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAIProvider = None

try:
    from .anthropic import AnthropicProvider
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    AnthropicProvider = None

try:
    from .ollama import OllamaProvider, AIOHTTP_AVAILABLE
    OLLAMA_AVAILABLE = AIOHTTP_AVAILABLE
except ImportError:
    OLLAMA_AVAILABLE = False
    OllamaProvider = None

try:
    from .vllm import VLLMProvider
    VLLM_AVAILABLE = True
except ImportError:
    VLLM_AVAILABLE = False
    VLLMProvider = None

__all__ = [
    "BaseLLMProvider",
    "LLMResponse", 
    "ModelInfo",
    "ModelCapability",
    "LLMProviderError",
    "ConfigurationError",
    "ConnectionError", 
    "GenerationError",
    "RateLimitError",
    "AuthenticationError",
    "OpenAIProvider",
    "OPENAI_AVAILABLE",
    "AnthropicProvider", 
    "ANTHROPIC_AVAILABLE",
    "OllamaProvider",
    "OLLAMA_AVAILABLE",
    "VLLMProvider",
    "VLLM_AVAILABLE"
]