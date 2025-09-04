"""Anthropic Claude LLM provider implementation."""

import asyncio
import json
from typing import Dict, Any, Optional, List
import logging

try:
    import anthropic
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    AsyncAnthropic = None

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
from ...models.generation import GenerationContext
from ..prompts import PromptManager


logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider implementation."""
    
    # Model configurations
    MODELS = {
        "claude-3-5-sonnet-20241022": {
            "max_tokens": 8192,
            "context_window": 200000,
            "cost_per_1k_tokens": 0.003,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.LARGE_CONTEXT
            ]
        },
        "claude-3-haiku-20240307": {
            "max_tokens": 4096,
            "context_window": 200000,
            "cost_per_1k_tokens": 0.00025,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.LARGE_CONTEXT
            ]
        },
        "claude-3-opus-20240229": {
            "max_tokens": 4096,
            "context_window": 200000,
            "cost_per_1k_tokens": 0.015,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.LARGE_CONTEXT
            ]
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Anthropic provider.
        
        Args:
            config: Configuration dictionary with api_key, model, etc.
        """
        if not ANTHROPIC_AVAILABLE:
            raise ConfigurationError(
                "Anthropic library not available. Install with: pip install anthropic"
            )
        
        super().__init__(config)
        
        # Initialize Anthropic client
        api_key = self.config.get("api_key")
        if hasattr(api_key, 'get_secret_value'):
            api_key = api_key.get_secret_value()
        
        self.client = AsyncAnthropic(
            api_key=api_key,
            base_url=self.config.get("api_base"),
            timeout=self.config.get("timeout", 30),
            max_retries=self.config.get("max_retries", 3)
        )
        
        self.model = self.config.get("model", "claude-3-5-sonnet-20241022")
        self.max_tokens = self.config.get("max_tokens", 4000)
        self.temperature = self.config.get("temperature", 0.1)
        
        # Initialize prompt manager
        self.prompt_manager = PromptManager()
    
    def _validate_config(self) -> None:
        """Validate Anthropic provider configuration."""
        required_fields = ["api_key"]
        
        for field in required_fields:
            if field not in self.config or not self.config[field]:
                raise ConfigurationError(f"Missing required configuration field: {field}")
        
        # Validate model
        model = self.config.get("model", "claude-3-5-sonnet-20241022")
        if model not in self.MODELS:
            logger.warning(f"Unknown model '{model}', using default configuration")
        
        # Validate numeric parameters
        max_tokens = self.config.get("max_tokens")
        if max_tokens is not None and (not isinstance(max_tokens, int) or max_tokens <= 0):
            raise ConfigurationError("max_tokens must be a positive integer")
        
        temperature = self.config.get("temperature")
        if temperature is not None and (not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 1):
            raise ConfigurationError("temperature must be between 0 and 1")
    
    async def generate_saidata(self, context: GenerationContext) -> LLMResponse:
        """Generate saidata using Anthropic Claude models.
        
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
            
            # Make API call
            response = await self._make_api_call(prompt)
            
            # Extract content
            content = response.content[0].text if response.content else None
            if not content:
                raise GenerationError("Empty response from Anthropic API")
            
            # Calculate cost estimate
            tokens_used = response.usage.input_tokens + response.usage.output_tokens if response.usage else None
            cost_estimate = self.estimate_cost(tokens_used) if tokens_used else None
            
            return LLMResponse(
                content=content,
                tokens_used=tokens_used,
                cost_estimate=cost_estimate,
                model_used=self.model,
                finish_reason=response.stop_reason,
                metadata={
                    "input_tokens": response.usage.input_tokens if response.usage else None,
                    "output_tokens": response.usage.output_tokens if response.usage else None,
                }
            )
            
        except anthropic.RateLimitError as e:
            raise RateLimitError(f"Anthropic rate limit exceeded: {e}")
        except anthropic.AuthenticationError as e:
            raise AuthenticationError(f"Anthropic authentication failed: {e}")
        except anthropic.APIConnectionError as e:
            raise ConnectionError(f"Anthropic connection failed: {e}")
        except anthropic.APIError as e:
            raise GenerationError(f"Anthropic API error: {e}")
        except Exception as e:
            raise GenerationError(f"Unexpected error during generation: {e}")
    
    async def _make_api_call(self, prompt: str) -> Any:
        """Make API call to Anthropic with retry logic.
        
        Args:
            prompt: The prompt to send to Claude
            
        Returns:
            Anthropic API response
        """
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return response
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Anthropic provider is properly configured and available.
        
        Returns:
            True if provider is available, False otherwise
        """
        if not ANTHROPIC_AVAILABLE:
            return False
        
        try:
            self._validate_config()
            return True
        except ConfigurationError:
            return False
    
    async def validate_connection(self) -> bool:
        """Validate connection to Anthropic API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Make a simple API call to test connection
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "Hello"}]
            )
            return bool(response.content)
        except Exception as e:
            logger.error(f"Anthropic connection validation failed: {e}")
            return False
    
    def get_model_info(self) -> ModelInfo:
        """Return information about the Anthropic model being used.
        
        Returns:
            ModelInfo object with model details
        """
        model_config = self.MODELS.get(self.model, {
            "max_tokens": 4096,
            "context_window": 200000,
            "cost_per_1k_tokens": 0.003,
            "capabilities": [ModelCapability.TEXT_GENERATION]
        })
        
        return ModelInfo(
            name=self.model,
            provider="anthropic",
            max_tokens=model_config["max_tokens"],
            context_window=model_config["context_window"],
            capabilities=model_config["capabilities"],
            cost_per_1k_tokens=model_config["cost_per_1k_tokens"],
            supports_streaming=True
        )
    
    def get_available_models(self) -> List[str]:
        """Get list of available Anthropic models.
        
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
            "provider": "anthropic",
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "available": self.is_available()
        }