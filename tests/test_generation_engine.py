"""Tests for the GenerationEngine class."""

import pytest
import asyncio
import yaml
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from saigen.core.generation_engine import (
    GenerationEngine, 
    GenerationEngineError, 
    ProviderNotAvailableError,
    ValidationFailedError
)
from saigen.models.generation import (
    GenerationRequest, 
    GenerationResult, 
    GenerationContext,
    LLMProvider
)
from saigen.models.saidata import SaiData, Metadata
from saigen.llm.providers.base import LLMResponse, ModelInfo, ModelCapability


class TestGenerationEngine:
    """Test cases for GenerationEngine."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            "llm_providers": {
                "openai": {
                    "api_key": "test-api-key",
                    "model": "gpt-3.5-turbo"
                }
            }
        }
    
    @pytest.fixture
    def generation_engine(self, mock_config):
        """Create GenerationEngine instance for testing."""
        with patch('saigen.core.generation_engine.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_provider.get_provider_name.return_value = "openai"
            mock_provider_class.return_value = mock_provider
            
            engine = GenerationEngine(mock_config)
            engine._llm_providers["openai"] = mock_provider
            return engine
    
    @pytest.fixture
    def sample_request(self):
        """Sample generation request."""
        return GenerationRequest(
            software_name="nginx",
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.OPENAI,
            use_rag=True
        )
    
    @pytest.fixture
    def sample_saidata_yaml(self):
        """Sample valid saidata YAML content."""
        return """
version: "0.2"
metadata:
  name: "nginx"
  display_name: "Nginx"
  description: "High-performance web server"
  category: "web-server"
  license: "BSD-2-Clause"
  urls:
    website: "https://nginx.org"
    documentation: "https://nginx.org/en/docs/"

providers:
  apt:
    packages:
      - name: "nginx"
        version: "latest"
    services:
      - name: "nginx"
        enabled: true
  
  brew:
    packages:
      - name: "nginx"
"""
    
    def test_initialization_with_config(self, mock_config):
        """Test GenerationEngine initialization with configuration."""
        with patch('saigen.core.generation_engine.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_provider_class.return_value = mock_provider
            
            engine = GenerationEngine(mock_config)
            
            assert engine.config == mock_config
            assert isinstance(engine.validator, type(engine.validator))
            assert engine._generation_count == 0
            assert engine._total_tokens_used == 0
            assert engine._total_cost == 0.0
    
    def test_initialization_without_config(self):
        """Test GenerationEngine initialization without configuration."""
        engine = GenerationEngine()
        
        assert engine.config == {}
        assert len(engine._llm_providers) == 0
    
    @pytest.mark.asyncio
    async def test_generate_saidata_success(self, generation_engine, sample_request, sample_saidata_yaml):
        """Test successful saidata generation."""
        # Mock LLM response
        mock_llm_response = LLMResponse(
            content=sample_saidata_yaml,
            tokens_used=1000,
            cost_estimate=0.002,
            model_used="gpt-3.5-turbo",
            finish_reason="stop"
        )
        
        # Mock provider
        mock_provider = generation_engine._llm_providers["openai"]
        mock_provider.generate_saidata = AsyncMock(return_value=mock_llm_response)
        
        # Execute generation
        result = await generation_engine.generate_saidata(sample_request)
        
        # Verify result
        assert result.success is True
        assert result.saidata is not None
        assert result.saidata.metadata.name == "nginx"
        assert result.llm_provider_used == "openai"
        assert result.tokens_used == 1000
        assert result.cost_estimate == 0.002
        assert result.generation_time > 0
        assert len(result.validation_errors) == 0
    
    @pytest.mark.asyncio
    async def test_generate_saidata_invalid_yaml(self, generation_engine, sample_request):
        """Test generation with invalid YAML content."""
        # Mock LLM response with invalid YAML
        mock_llm_response = LLMResponse(
            content="invalid: yaml: content: [unclosed",
            tokens_used=500,
            cost_estimate=0.001
        )
        
        mock_provider = generation_engine._llm_providers["openai"]
        mock_provider.generate_saidata = AsyncMock(return_value=mock_llm_response)
        
        result = await generation_engine.generate_saidata(sample_request)
        
        assert result.success is False
        assert result.saidata is None
        assert len(result.validation_errors) > 0
        assert "YAML syntax" in result.validation_errors[0].message
    
    @pytest.mark.asyncio
    async def test_generate_saidata_schema_validation_failure(self, generation_engine, sample_request):
        """Test generation with schema validation failure."""
        # Mock LLM response with invalid schema
        invalid_yaml = """
version: "invalid-version"
metadata:
  name: "nginx"
"""
        
        mock_llm_response = LLMResponse(
            content=invalid_yaml,
            tokens_used=300,
            cost_estimate=0.0006
        )
        
        mock_provider = generation_engine._llm_providers["openai"]
        mock_provider.generate_saidata = AsyncMock(return_value=mock_llm_response)
        
        result = await generation_engine.generate_saidata(sample_request)
        
        assert result.success is False
        assert result.saidata is None
        assert len(result.validation_errors) > 0
    
    def test_validate_request_empty_software_name(self, generation_engine):
        """Test request validation with empty software name."""
        request = GenerationRequest(
            software_name="",
            llm_provider=LLMProvider.OPENAI
        )
        
        with pytest.raises(GenerationEngineError, match="Software name is required"):
            generation_engine._validate_request(request)
    
    def test_validate_request_unavailable_provider(self, generation_engine):
        """Test request validation with unavailable provider."""
        request = GenerationRequest(
            software_name="nginx",
            llm_provider=LLMProvider.ANTHROPIC  # Not configured
        )
        
        with pytest.raises(ProviderNotAvailableError):
            generation_engine._validate_request(request)
    
    def test_get_llm_provider_success(self, generation_engine):
        """Test getting available LLM provider."""
        provider = generation_engine._get_llm_provider(LLMProvider.OPENAI)
        assert provider is not None
        assert provider.get_provider_name() == "openai"
    
    def test_get_llm_provider_not_available(self, generation_engine):
        """Test getting unavailable LLM provider."""
        with pytest.raises(ProviderNotAvailableError):
            generation_engine._get_llm_provider(LLMProvider.ANTHROPIC)
    
    @pytest.mark.asyncio
    async def test_build_generation_context(self, generation_engine, sample_request):
        """Test building generation context."""
        context = await generation_engine._build_generation_context(sample_request)
        
        assert context.software_name == "nginx"
        assert context.target_providers == ["apt", "brew"]
        assert context.user_hints is None
        assert context.existing_saidata is None
        assert isinstance(context.repository_data, list)
        assert isinstance(context.similar_saidata, list)
    
    @pytest.mark.asyncio
    async def test_parse_and_validate_yaml_success(self, generation_engine, sample_saidata_yaml):
        """Test successful YAML parsing and validation."""
        saidata = await generation_engine._parse_and_validate_yaml(sample_saidata_yaml, "nginx")
        
        assert isinstance(saidata, SaiData)
        assert saidata.metadata.name == "nginx"
        assert saidata.version == "0.2"
        assert "apt" in saidata.providers
        assert "brew" in saidata.providers
    
    @pytest.mark.asyncio
    async def test_parse_and_validate_yaml_invalid_syntax(self, generation_engine):
        """Test YAML parsing with invalid syntax."""
        invalid_yaml = "invalid: yaml: [unclosed"
        
        with pytest.raises(ValidationFailedError, match="Invalid YAML syntax"):
            await generation_engine._parse_and_validate_yaml(invalid_yaml, "nginx")
    
    @pytest.mark.asyncio
    async def test_save_saidata(self, generation_engine, tmp_path):
        """Test saving saidata to file."""
        saidata = SaiData(
            version="0.2",
            metadata=Metadata(name="test-software", description="Test software")
        )
        
        output_path = tmp_path / "test.yaml"
        await generation_engine.save_saidata(saidata, output_path)
        
        assert output_path.exists()
        
        # Verify content
        with open(output_path, 'r') as f:
            content = yaml.safe_load(f)
        
        assert content["version"] == "0.2"
        assert content["metadata"]["name"] == "test-software"
    
    def test_get_available_providers(self, generation_engine):
        """Test getting available providers."""
        providers = generation_engine.get_available_providers()
        assert "openai" in providers
    
    def test_get_provider_info(self, generation_engine):
        """Test getting provider information."""
        # Mock model info
        mock_model_info = ModelInfo(
            name="gpt-3.5-turbo",
            provider="openai",
            max_tokens=4096,
            context_window=4096,
            capabilities=[ModelCapability.TEXT_GENERATION],
            cost_per_1k_tokens=0.002,
            supports_streaming=True
        )
        
        mock_provider = generation_engine._llm_providers["openai"]
        mock_provider.get_model_info.return_value = mock_model_info
        
        info = generation_engine.get_provider_info("openai")
        
        assert info is not None
        assert info["name"] == "openai"
        assert info["model"] == "gpt-3.5-turbo"
        assert info["max_tokens"] == 4096
        assert info["available"] is True
    
    def test_get_provider_info_not_found(self, generation_engine):
        """Test getting info for non-existent provider."""
        info = generation_engine.get_provider_info("nonexistent")
        assert info is None
    
    def test_get_generation_stats_initial(self, generation_engine):
        """Test getting initial generation statistics."""
        stats = generation_engine.get_generation_stats()
        
        assert stats["total_generations"] == 0
        assert stats["total_tokens_used"] == 0
        assert stats["total_cost_estimate"] == 0.0
        assert stats["average_tokens_per_generation"] == 0
        assert stats["average_cost_per_generation"] == 0
    
    def test_update_metrics(self, generation_engine):
        """Test updating generation metrics."""
        mock_response = Mock()
        mock_response.tokens_used = 1000
        mock_response.cost_estimate = 0.002
        
        generation_engine._update_metrics(mock_response)
        
        assert generation_engine._generation_count == 1
        assert generation_engine._total_tokens_used == 1000
        assert generation_engine._total_cost == 0.002
        
        stats = generation_engine.get_generation_stats()
        assert stats["total_generations"] == 1
        assert stats["average_tokens_per_generation"] == 1000
        assert stats["average_cost_per_generation"] == 0.002
    
    @pytest.mark.asyncio
    async def test_validate_saidata_file(self, generation_engine, tmp_path):
        """Test validating saidata file."""
        # Create a test saidata file
        test_data = {
            "version": "0.2",
            "metadata": {
                "name": "test-software",
                "description": "Test software"
            }
        }
        
        test_file = tmp_path / "test.yaml"
        with open(test_file, 'w') as f:
            yaml.dump(test_data, f)
        
        result = await generation_engine.validate_saidata_file(test_file)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_format_validation_report(self, generation_engine):
        """Test formatting validation report."""
        # This will use the validator's format method
        # We'll test with a mock validation result
        from saigen.core.validator import ValidationResult, ValidationError, ValidationSeverity
        
        mock_result = ValidationResult(
            is_valid=False,
            errors=[ValidationError(
                severity=ValidationSeverity.ERROR,
                message="Test error",
                path="test.field",
                code="test_error"
            )],
            warnings=[],
            info=[]
        )
        
        report = generation_engine.format_validation_report(mock_result)
        
        assert "❌ Validation failed" in report
        assert "Test error" in report
        assert "test.field" in report


@pytest.mark.asyncio
async def test_generation_engine_integration():
    """Integration test for GenerationEngine with mocked dependencies."""
    config = {
        "llm_providers": {
            "openai": {
                "api_key": "test-key",
                "model": "gpt-3.5-turbo"
            }
        }
    }
    
    sample_yaml = """
version: "0.2"
metadata:
  name: "redis"
  display_name: "Redis"
  description: "In-memory data structure store"
  category: "database"

providers:
  apt:
    packages:
      - name: "redis-server"
"""
    
    with patch('saigen.core.generation_engine.OpenAIProvider') as mock_provider_class:
        # Mock provider
        mock_provider = Mock()
        mock_provider.is_available.return_value = True
        mock_provider.get_provider_name.return_value = "openai"
        mock_provider.generate_saidata = AsyncMock(return_value=LLMResponse(
            content=sample_yaml,
            tokens_used=800,
            cost_estimate=0.0016
        ))
        mock_provider_class.return_value = mock_provider
        
        # Create engine and request
        engine = GenerationEngine(config)
        engine._llm_providers["openai"] = mock_provider  # Add mocked provider for compatibility
        request = GenerationRequest(
            software_name="redis",
            llm_provider=LLMProvider.OPENAI
        )
        
        # Execute generation
        result = await engine.generate_saidata(request)
        
        # Verify integration
        assert result.success is True
        assert result.saidata.metadata.name == "redis"
        assert result.tokens_used == 800
        assert result.cost_estimate == 0.0016
        
        # Verify metrics were updated
        stats = engine.get_generation_stats()
        assert stats["total_generations"] == 1
        assert stats["total_tokens_used"] == 800