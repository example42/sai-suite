"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ...models.generation import GenerationContext, GenerationResult
from ...models.saidata import SaiData


class ModelCapability(str, Enum):
    """Model capabilities."""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    STRUCTURED_OUTPUT = "structured_output"
    FUNCTION_CALLING = "function_calling"
    LARGE_CONTEXT = "large_context"


@dataclass
class ModelInfo:
    """Information about an LLM model."""
    name: str
    provider: str
    max_tokens: int
    context_window: int
    capabilities: List[ModelCapability]
    cost_per_1k_tokens: Optional[float] = None
    supports_streaming: bool = False


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    model_used: Optional[str] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the LLM provider with configuration.
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        pass
    
    @abstractmethod
    async def generate_saidata(self, context: GenerationContext) -> LLMResponse:
        """Generate saidata using LLM with provided context.
        
        Args:
            context: Generation context with software name, repository data, etc.
            
        Returns:
            LLMResponse containing generated saidata YAML content
            
        Raises:
            LLMProviderError: If generation fails
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if LLM provider is properly configured and available.
        
        Returns:
            True if provider is available, False otherwise
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """Return information about the model being used.
        
        Returns:
            ModelInfo object with model details
        """
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate connection to the LLM provider.
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get the provider name.
        
        Returns:
            Provider name string
        """
        return self.__class__.__name__.replace('Provider', '').lower()
    
    def estimate_cost(self, tokens: int) -> Optional[float]:
        """Estimate cost for given number of tokens.
        
        Args:
            tokens: Number of tokens
            
        Returns:
            Estimated cost in USD, or None if not available
        """
        model_info = self.get_model_info()
        if model_info.cost_per_1k_tokens:
            return (tokens / 1000) * model_info.cost_per_1k_tokens
        return None
    
    def supports_capability(self, capability: ModelCapability) -> bool:
        """Check if model supports a specific capability.
        
        Args:
            capability: Capability to check
            
        Returns:
            True if capability is supported
        """
        model_info = self.get_model_info()
        return capability in model_info.capabilities


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class ConfigurationError(LLMProviderError):
    """Configuration-related errors."""
    pass


class ConnectionError(LLMProviderError):
    """Connection-related errors."""
    pass


class GenerationError(LLMProviderError):
    """Generation-related errors."""
    pass


class RateLimitError(LLMProviderError):
    """Rate limit exceeded errors."""
    pass


class AuthenticationError(LLMProviderError):
    """Authentication-related errors."""
    pass