"""Tests for LLM provider implementations."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from saigen.llm.prompts import PromptManager, PromptSection, PromptTemplate
from saigen.llm.providers.base import (
    BaseLLMProvider,
    ConfigurationError,
    LLMResponse,
    ModelCapability,
    ModelInfo,
)
from saigen.llm.providers.openai import OpenAIProvider
from saigen.models.generation import GenerationContext
from saigen.models.repository import RepositoryPackage


class TestBaseLLMProvider:
    """Test base LLM provider functionality."""

    def test_abstract_methods_raise_not_implemented(self):
        """Test that abstract methods raise NotImplementedError."""

        class TestProvider(BaseLLMProvider):
            def _validate_config(self):
                pass

        # Should not be able to instantiate due to abstract methods
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            TestProvider({})

    def test_estimate_cost_calculation(self):
        """Test cost estimation calculation."""

        class TestProvider(BaseLLMProvider):
            def _validate_config(self):
                pass

            async def generate_saidata(self, context):
                pass

            def is_available(self):
                return True

            def get_model_info(self):
                return ModelInfo(
                    name="test-model",
                    provider="test",
                    max_tokens=1000,
                    context_window=1000,
                    capabilities=[ModelCapability.TEXT_GENERATION],
                    cost_per_1k_tokens=0.002,
                )

            async def validate_connection(self):
                return True

        provider = TestProvider({})

        # Test cost calculation
        cost = provider.estimate_cost(1000)
        assert cost == 0.002

        cost = provider.estimate_cost(500)
        assert cost == 0.001

    def test_supports_capability(self):
        """Test capability checking."""

        class TestProvider(BaseLLMProvider):
            def _validate_config(self):
                pass

            async def generate_saidata(self, context):
                pass

            def is_available(self):
                return True

            def get_model_info(self):
                return ModelInfo(
                    name="test-model",
                    provider="test",
                    max_tokens=1000,
                    context_window=1000,
                    capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.CODE_GENERATION],
                )

            async def validate_connection(self):
                return True

        provider = TestProvider({})

        assert provider.supports_capability(ModelCapability.TEXT_GENERATION)
        assert provider.supports_capability(ModelCapability.CODE_GENERATION)
        assert not provider.supports_capability(ModelCapability.FUNCTION_CALLING)


class TestPromptManager:
    """Test prompt management functionality."""

    def test_prompt_manager_initialization(self):
        """Test prompt manager initializes with default templates."""
        manager = PromptManager()

        templates = manager.list_templates()
        assert "generation" in templates
        assert "update" in templates

    def test_get_template(self):
        """Test getting templates by name."""
        manager = PromptManager()

        template = manager.get_template("generation")
        assert isinstance(template, PromptTemplate)
        assert template.name == "saidata_generation"

    def test_get_nonexistent_template_raises_error(self):
        """Test that getting nonexistent template raises KeyError."""
        manager = PromptManager()

        with pytest.raises(KeyError):
            manager.get_template("nonexistent")

    def test_register_custom_template(self):
        """Test registering custom templates."""
        manager = PromptManager()

        custom_template = PromptTemplate(
            name="custom", sections=[PromptSection(name="test", template="Test: $software_name")]
        )

        manager.register_template("custom", custom_template)

        retrieved = manager.get_template("custom")
        assert retrieved.name == "custom"


class TestPromptTemplate:
    """Test prompt template functionality."""

    def test_simple_template_rendering(self):
        """Test basic template rendering."""
        template = PromptTemplate(
            name="test",
            sections=[
                PromptSection(
                    name="basic", template="Software: $software_name\nProviders: $target_providers"
                )
            ],
        )

        context = GenerationContext(software_name="nginx", target_providers=["apt", "brew"])

        result = template.render(context)
        assert "Software: nginx" in result
        assert "Providers: apt, brew" in result

    def test_conditional_sections(self):
        """Test conditional section inclusion."""
        template = PromptTemplate(
            name="test",
            sections=[
                PromptSection(name="always", template="Always included: $software_name"),
                PromptSection(
                    name="conditional",
                    template="Repository data: $repository_context",
                    condition="has_repository_data",
                ),
            ],
        )

        # Test without repository data
        context = GenerationContext(software_name="nginx")
        result = template.render(context)
        assert "Always included: nginx" in result
        assert "Repository data:" not in result

        # Test with repository data
        context.repository_data = [
            RepositoryPackage(
                name="nginx", version="1.20.0", repository_name="apt", platform="linux"
            )
        ]
        result = template.render(context)
        assert "Always included: nginx" in result
        assert "Repository data:" in result


@pytest.mark.skipif(
    not hasattr(pytest, "importorskip")
    or pytest.importorskip("openai", reason="OpenAI library not available") is None,
    reason="OpenAI library not available",
)
class TestOpenAIProvider:
    """Test OpenAI provider implementation."""

    def test_configuration_validation(self):
        """Test configuration validation."""
        # Test missing API key
        with pytest.raises(ConfigurationError):
            OpenAIProvider({})

        # Test invalid max_tokens
        with pytest.raises(ConfigurationError):
            OpenAIProvider({"api_key": "test-key", "max_tokens": -1})

        # Test invalid temperature
        with pytest.raises(ConfigurationError):
            OpenAIProvider({"api_key": "test-key", "temperature": 3.0})

    def test_model_info(self):
        """Test model information retrieval."""
        provider = OpenAIProvider({"api_key": "test-key", "model": "gpt-4o-mini"})

        model_info = provider.get_model_info()
        assert model_info.name == "gpt-4o-mini"
        assert model_info.provider == "openai"
        assert ModelCapability.TEXT_GENERATION in model_info.capabilities

    def test_available_models(self):
        """Test getting available models."""
        provider = OpenAIProvider({"api_key": "test-key"})

        models = provider.get_available_models()
        assert "gpt-4o-mini" in models
        assert "gpt-4" in models

    def test_set_model(self):
        """Test setting model."""
        provider = OpenAIProvider({"api_key": "test-key"})

        provider.set_model("gpt-4")
        assert provider.model == "gpt-4"

        with pytest.raises(ValueError):
            provider.set_model("invalid-model")

    @patch("saigen.llm.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_generate_saidata_success(self, mock_openai):
        """Test successful saidata generation."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "version: '0.2'\nmetadata:\n  name: nginx"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.total_tokens = 100
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 50

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = OpenAIProvider({"api_key": "test-key"})

        context = GenerationContext(software_name="nginx", target_providers=["apt", "brew"])

        result = await provider.generate_saidata(context)

        assert isinstance(result, LLMResponse)
        assert "nginx" in result.content
        assert result.tokens_used == 100
        assert result.model_used == "gpt-4o-mini"

    def test_is_available(self):
        """Test availability checking."""
        # Test with valid config
        provider = OpenAIProvider({"api_key": "test-key"})
        assert provider.is_available()

        # Test with invalid config would require mocking the validation
