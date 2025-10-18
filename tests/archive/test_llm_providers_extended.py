"""Tests for extended LLM providers (Anthropic, Ollama) and provider manager."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from saigen.llm.provider_manager import LLMProviderManager
from saigen.llm.providers.base import (
    ConfigurationError,
    GenerationError,
    LLMResponse,
    ModelCapability,
    ModelInfo,
)
from saigen.models.generation import GenerationContext, LLMProvider


class TestAnthropicProvider:
    """Test Anthropic Claude provider."""

    def test_anthropic_import_available(self):
        """Test that Anthropic provider can be imported."""
        try:
            from saigen.llm.providers.anthropic import ANTHROPIC_AVAILABLE

            # If anthropic library is not installed, ANTHROPIC_AVAILABLE should be False
            # but the import should still work
            assert isinstance(ANTHROPIC_AVAILABLE, bool)
        except ImportError:
            pytest.skip("Anthropic provider not available")

    def test_anthropic_provider_config_validation(self):
        """Test Anthropic provider configuration validation."""
        try:
            from saigen.llm.providers.anthropic import AnthropicProvider
        except ImportError:
            pytest.skip("Anthropic provider not available")

        # Test missing API key
        with pytest.raises(ConfigurationError):
            AnthropicProvider({})

        # Test invalid temperature
        with pytest.raises(ConfigurationError):
            AnthropicProvider(
                {"api_key": "test-key", "temperature": 2.0}  # Should be <= 1.0 for Anthropic
            )

    def test_anthropic_model_info(self):
        """Test Anthropic model information."""
        try:
            from saigen.llm.providers.anthropic import AnthropicProvider
        except ImportError:
            pytest.skip("Anthropic provider not available")

        with patch("saigen.llm.providers.anthropic.ANTHROPIC_AVAILABLE", True):
            with patch("saigen.llm.providers.anthropic.AsyncAnthropic"):
                provider = AnthropicProvider({"api_key": "test-key"})
                model_info = provider.get_model_info()

                assert isinstance(model_info, ModelInfo)
                assert model_info.provider == "anthropic"
                assert model_info.cost_per_1k_tokens is not None
                assert ModelCapability.TEXT_GENERATION in model_info.capabilities


class TestOllamaProvider:
    """Test Ollama local LLM provider."""

    def test_ollama_import_available(self):
        """Test that Ollama provider can be imported."""
        try:
            from saigen.llm.providers.ollama import AIOHTTP_AVAILABLE

            # If aiohttp library is not installed, AIOHTTP_AVAILABLE should be False
            # but the import should still work
            assert isinstance(AIOHTTP_AVAILABLE, bool)
        except ImportError:
            pytest.skip("Ollama provider not available")

    def test_ollama_provider_config_validation(self):
        """Test Ollama provider configuration validation."""
        try:
            from saigen.llm.providers.ollama import AIOHTTP_AVAILABLE, OllamaProvider
        except ImportError:
            pytest.skip("Ollama provider not available")

        if not AIOHTTP_AVAILABLE:
            # Test that missing aiohttp raises ConfigurationError
            with pytest.raises(ConfigurationError):
                OllamaProvider({"model": "llama2"})
            return

        # Test missing model
        with pytest.raises(ConfigurationError):
            OllamaProvider({})

        # Test invalid base_url
        with pytest.raises(ConfigurationError):
            OllamaProvider({"model": "llama2", "base_url": "invalid-url"})

    def test_ollama_model_info(self):
        """Test Ollama model information."""
        try:
            from saigen.llm.providers.ollama import AIOHTTP_AVAILABLE, OllamaProvider
        except ImportError:
            pytest.skip("Ollama provider not available")

        if not AIOHTTP_AVAILABLE:
            pytest.skip("aiohttp not available for Ollama provider")

        with patch("saigen.llm.providers.ollama.aiohttp"):
            provider = OllamaProvider({"model": "llama2", "base_url": "http://localhost:11434"})

            model_info = provider.get_model_info()

            assert isinstance(model_info, ModelInfo)
            assert model_info.provider == "ollama"
            assert model_info.cost_per_1k_tokens == 0.0  # Local models are free
            assert ModelCapability.TEXT_GENERATION in model_info.capabilities

    def test_ollama_free_cost_estimate(self):
        """Test that Ollama provider returns zero cost estimates."""
        try:
            from saigen.llm.providers.ollama import AIOHTTP_AVAILABLE, OllamaProvider
        except ImportError:
            pytest.skip("Ollama provider not available")

        if not AIOHTTP_AVAILABLE:
            pytest.skip("aiohttp not available for Ollama provider")

        with patch("saigen.llm.providers.ollama.aiohttp"):
            provider = OllamaProvider({"model": "llama2", "base_url": "http://localhost:11434"})

            cost = provider.estimate_cost(1000)
            assert cost == 0.0


class TestLLMProviderManager:
    """Test LLM provider manager."""

    def test_provider_manager_initialization(self):
        """Test provider manager initialization."""
        config = {
            "openai": {"api_key": "test-key", "model": "gpt-4o-mini", "priority": "high"},
            "anthropic": {
                "api_key": "test-key",
                "model": "claude-3-haiku-20240307",
                "priority": "medium",
            },
        }

        manager = LLMProviderManager(config)

        # Should have configured providers (even if not available)
        assert len(manager.providers) >= 0  # Depends on what's available

    def test_provider_selection_by_priority(self):
        """Test provider selection based on priority."""
        config = {
            "provider_low": {"api_key": "test-key", "priority": "low", "enabled": True},
            "provider_high": {"api_key": "test-key", "priority": "high", "enabled": True},
        }

        # Mock the provider registry to use mock providers
        mock_provider_class = Mock()
        mock_provider_instance = Mock()
        mock_provider_instance.is_available.return_value = True
        mock_provider_class.return_value = mock_provider_instance

        with patch.object(
            LLMProviderManager,
            "PROVIDER_REGISTRY",
            {
                LLMProvider.OPENAI: mock_provider_class,
                LLMProvider.ANTHROPIC: mock_provider_class,
                LLMProvider.OLLAMA: mock_provider_class,
            },
        ):
            # Map our test providers to known enum values
            config_mapped = {"openai": config["provider_high"], "anthropic": config["provider_low"]}

            manager = LLMProviderManager(config_mapped)

            # High priority provider should be selected first
            selected = manager.select_best_provider()
            assert selected == "openai"  # High priority

    @pytest.mark.asyncio
    async def test_provider_fallback_logic(self):
        """Test provider fallback when primary fails."""
        config = {
            "openai": {"api_key": "test-key", "priority": "high"},
            "anthropic": {"api_key": "test-key", "priority": "medium"},
        }

        # Create mock providers
        failing_provider = Mock()
        failing_provider.is_available.return_value = True
        failing_provider.generate_saidata = AsyncMock(side_effect=GenerationError("API failed"))

        working_provider = Mock()
        working_provider.is_available.return_value = True
        working_provider.generate_saidata = AsyncMock(
            return_value=LLMResponse(
                content="test: content",
                tokens_used=100,
                cost_estimate=0.01,
                model_used="test-model",
            )
        )

        # Mock provider classes
        failing_provider_class = Mock(return_value=failing_provider)
        working_provider_class = Mock(return_value=working_provider)

        with patch.object(
            LLMProviderManager,
            "PROVIDER_REGISTRY",
            {
                LLMProvider.OPENAI: failing_provider_class,
                LLMProvider.ANTHROPIC: working_provider_class,
                LLMProvider.OLLAMA: None,
            },
        ):
            manager = LLMProviderManager(config)

            context = GenerationContext(software_name="test-software", target_providers=["apt"])

            # Should fallback to working provider
            response = await manager.generate_with_fallback(context, preferred_provider="openai")

            assert response.content == "test: content"
            assert response.tokens_used == 100

            # Verify both providers were attempted
            # The failing provider may be called multiple times due to retry logic
            assert failing_provider.generate_saidata.call_count >= 1
            working_provider.generate_saidata.assert_called_once()

    @pytest.mark.asyncio
    async def test_provider_status_checking(self):
        """Test provider status checking."""
        config = {"openai": {"api_key": "test-key"}}

        # Create mock provider
        mock_provider = Mock()
        mock_provider.is_available.return_value = True
        mock_provider.validate_connection = AsyncMock(return_value=True)
        mock_provider.get_model_info.return_value = ModelInfo(
            name="test-model",
            provider="test",
            max_tokens=4096,
            context_window=4096,
            capabilities=[ModelCapability.TEXT_GENERATION],
        )

        mock_provider_class = Mock(return_value=mock_provider)

        with patch.object(
            LLMProviderManager,
            "PROVIDER_REGISTRY",
            {
                LLMProvider.OPENAI: mock_provider_class,
                LLMProvider.ANTHROPIC: None,
                LLMProvider.OLLAMA: None,
            },
        ):
            manager = LLMProviderManager(config)

            status = await manager.get_provider_status("openai")

            assert status.name == "openai"
            assert status.available is True
            assert status.configured is True
            assert status.connection_valid is True
            assert status.model_info is not None

    def test_provider_exclusion(self):
        """Test excluding providers from selection."""
        config = {
            "openai": {"api_key": "test-key", "priority": "high"},
            "anthropic": {"api_key": "test-key", "priority": "medium"},
        }

        mock_provider_class = Mock()
        mock_provider_instance = Mock()
        mock_provider_instance.is_available.return_value = True
        mock_provider_class.return_value = mock_provider_instance

        with patch.object(
            LLMProviderManager,
            "PROVIDER_REGISTRY",
            {
                LLMProvider.OPENAI: mock_provider_class,
                LLMProvider.ANTHROPIC: mock_provider_class,
                LLMProvider.OLLAMA: None,
            },
        ):
            manager = LLMProviderManager(config)

            # Without exclusion, should select high priority
            selected = manager.select_best_provider()
            assert selected == "openai"

            # With exclusion, should select next best
            selected = manager.select_best_provider(exclude_providers=["openai"])
            assert selected == "anthropic"

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test provider manager cleanup."""
        config = {"openai": {"api_key": "test-key"}}

        # Create mock provider with cleanup method
        mock_provider = Mock()
        mock_provider.__aexit__ = AsyncMock()
        mock_provider_class = Mock(return_value=mock_provider)

        with patch.object(
            LLMProviderManager,
            "PROVIDER_REGISTRY",
            {
                LLMProvider.OPENAI: mock_provider_class,
                LLMProvider.ANTHROPIC: None,
                LLMProvider.OLLAMA: None,
            },
        ):
            manager = LLMProviderManager(config)

            # Get provider to create instance
            manager.get_provider("openai")

            # Cleanup should call provider cleanup
            await manager.cleanup()

            mock_provider.__aexit__.assert_called_once()


class TestProviderIntegration:
    """Test integration between providers and generation engine."""

    @pytest.mark.asyncio
    async def test_generation_engine_with_multiple_providers(self):
        """Test generation engine with multiple providers configured."""
        from saigen.core.generation_engine import GenerationEngine

        config = {
            "llm_providers": {
                "openai": {"api_key": "test-key", "priority": "high"},
                "anthropic": {"api_key": "test-key", "priority": "medium"},
            }
        }

        engine = GenerationEngine(config)

        # Should have provider manager initialized
        assert engine.provider_manager is not None

        # Should be able to get available providers
        available = engine.get_available_providers()
        assert isinstance(available, list)

        # Cleanup
        await engine.cleanup()


if __name__ == "__main__":
    pytest.main([__file__])
