"""Ollama local LLM provider implementation."""

import asyncio
import json
from typing import Dict, Any, Optional, List
import logging

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

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


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider implementation."""
    
    # Common model configurations (can be overridden by actual model info)
    DEFAULT_MODEL_CONFIG = {
        "max_tokens": 4096,
        "context_window": 4096,
        "cost_per_1k_tokens": 0.0,  # Local models are free
        "capabilities": [
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CODE_GENERATION
        ]
    }
    
    # Known model configurations
    KNOWN_MODELS = {
        "llama2": {
            "max_tokens": 4096,
            "context_window": 4096,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION
            ]
        },
        "llama2:13b": {
            "max_tokens": 4096,
            "context_window": 4096,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION
            ]
        },
        "codellama": {
            "max_tokens": 4096,
            "context_window": 16384,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT
            ]
        },
        "mistral": {
            "max_tokens": 4096,
            "context_window": 8192,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT
            ]
        },
        "mixtral": {
            "max_tokens": 4096,
            "context_window": 32768,
            "capabilities": [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.LARGE_CONTEXT
            ]
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Ollama provider.
        
        Args:
            config: Configuration dictionary with base_url, model, etc.
        """
        if not AIOHTTP_AVAILABLE:
            raise ConfigurationError(
                "aiohttp library not available. Install with: pip install aiohttp"
            )
        
        super().__init__(config)
        
        self.base_url = self.config.get("base_url", "http://localhost:11434")
        self.model = self.config.get("model", "llama2")
        self.temperature = self.config.get("temperature", 0.1)
        self.timeout = self.config.get("timeout", 60)  # Longer timeout for local models
        
        # Initialize prompt manager
        self.prompt_manager = PromptManager()
        
        # Session for HTTP requests
        self._session = None
    
    def _validate_config(self) -> None:
        """Validate Ollama provider configuration."""
        # Validate base_url format
        base_url = self.config.get("base_url", "http://localhost:11434")
        if not base_url.startswith(("http://", "https://")):
            raise ConfigurationError("base_url must start with http:// or https://")
        
        # Validate model name
        model = self.config.get("model")
        if not model:
            raise ConfigurationError("model name is required for Ollama provider")
        
        # Validate numeric parameters
        temperature = self.config.get("temperature")
        if temperature is not None and (not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2):
            raise ConfigurationError("temperature must be between 0 and 2")
        
        timeout = self.config.get("timeout")
        if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
            raise ConfigurationError("timeout must be a positive number")
    
    async def _get_session(self):
        """Get or create HTTP session.
        
        Returns:
            aiohttp ClientSession
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def _close_session(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def generate_saidata(self, context: GenerationContext) -> LLMResponse:
        """Generate saidata using Ollama local models.
        
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
            response_data = await self._make_api_call(prompt)
            
            # Extract content
            content = response_data.get("response", "")
            if not content:
                raise GenerationError("Empty response from Ollama API")
            
            # Ollama doesn't provide token usage, so we estimate
            estimated_tokens = len(prompt.split()) + len(content.split())
            
            return LLMResponse(
                content=content,
                tokens_used=estimated_tokens,
                cost_estimate=0.0,  # Local models are free
                model_used=self.model,
                finish_reason=response_data.get("done_reason", "stop"),
                metadata={
                    "total_duration": response_data.get("total_duration"),
                    "load_duration": response_data.get("load_duration"),
                    "prompt_eval_count": response_data.get("prompt_eval_count"),
                    "eval_count": response_data.get("eval_count"),
                }
            )
            
        except aiohttp.ClientError as e:
            raise ConnectionError(f"Ollama connection failed: {e}")
        except asyncio.TimeoutError:
            raise GenerationError("Ollama request timed out")
        except Exception as e:
            raise GenerationError(f"Unexpected error during generation: {e}")
    
    async def _make_api_call(self, prompt: str) -> Dict[str, Any]:
        """Make API call to Ollama with retry logic.
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            Ollama API response data
        """
        session = await self._get_session()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            }
        }
        
        try:
            async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                if response.status == 404:
                    raise GenerationError(f"Model '{self.model}' not found. Make sure it's installed in Ollama.")
                elif response.status != 200:
                    error_text = await response.text()
                    raise GenerationError(f"Ollama API error ({response.status}): {error_text}")
                
                response_data = await response.json()
                return response_data
                
        except aiohttp.ClientError as e:
            logger.error(f"Ollama API call failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Ollama provider is properly configured and available.
        
        Returns:
            True if provider is available, False otherwise
        """
        try:
            self._validate_config()
            return True
        except ConfigurationError:
            return False
    
    async def validate_connection(self) -> bool:
        """Validate connection to Ollama server.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            session = await self._get_session()
            
            # First check if Ollama server is running
            async with session.get(f"{self.base_url}/api/tags") as response:
                if response.status != 200:
                    return False
            
            # Then check if the specific model is available
            async with session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": "Hello",
                    "stream": False,
                    "options": {"num_predict": 1}
                }
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Ollama connection validation failed: {e}")
            return False
        finally:
            await self._close_session()
    
    async def list_available_models(self) -> List[str]:
        """List models available in Ollama.
        
        Returns:
            List of available model names
        """
        try:
            session = await self._get_session()
            
            async with session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    return [model["name"] for model in models]
                else:
                    logger.warning(f"Failed to list Ollama models: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []
        finally:
            await self._close_session()
    
    def get_model_info(self) -> ModelInfo:
        """Return information about the Ollama model being used.
        
        Returns:
            ModelInfo object with model details
        """
        # Use known model config if available, otherwise use defaults
        model_config = self.KNOWN_MODELS.get(
            self.model.split(":")[0],  # Remove tag for lookup
            self.DEFAULT_MODEL_CONFIG
        )
        
        return ModelInfo(
            name=self.model,
            provider="ollama",
            max_tokens=model_config["max_tokens"],
            context_window=model_config["context_window"],
            capabilities=model_config["capabilities"],
            cost_per_1k_tokens=0.0,  # Local models are free
            supports_streaming=True
        )
    
    def get_available_models(self) -> List[str]:
        """Get list of known Ollama models.
        
        Returns:
            List of model names
        """
        return list(self.KNOWN_MODELS.keys())
    
    def set_model(self, model: str) -> None:
        """Set the model to use for generation.
        
        Args:
            model: Model name
        """
        self.model = model
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry.
        
        Args:
            model_name: Name of the model to pull
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session = await self._get_session()
            
            payload = {"name": model_name}
            
            async with session.post(f"{self.base_url}/api/pull", json=payload) as response:
                if response.status == 200:
                    logger.info(f"Successfully pulled model: {model_name}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to pull model {model_name}: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
        finally:
            await self._close_session()
    
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for token usage.
        
        Args:
            tokens: Number of tokens
            
        Returns:
            Cost estimate (always 0.0 for local models)
        """
        return 0.0
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()