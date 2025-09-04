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
    "OPENAI_AVAILABLE"
]