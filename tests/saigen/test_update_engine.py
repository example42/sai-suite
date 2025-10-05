"""Tests for update engine functionality."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from saigen.core.update_engine import UpdateEngine, MergeStrategy, UpdateResult
from saigen.core.generation_engine import GenerationEngine
from saigen.models.saidata import SaiData, Metadata
from saigen.models.generation import GenerationResult, LLMProvider


@pytest.fixture
def sample_existing_saidata():
    """Sample existing saidata for testing."""
    return SaiData(
        version="0.2",
        metadata=Metadata(
            name="nginx",
            display_name="NGINX Web Server",
            description="High-performance web server",
            version="1.20.0",
            category="web",
            tags=["web", "server"],
            license="BSD-2-Clause"
        ),
        providers={
            "apt": {
                "packages": [
                    {"name": "nginx", "version": "1.20.0"}
                ]
            }
        }
    )


@pytest.fixture
def sample_fresh_saidata():
    """Sample fresh saidata for testing."""
    return SaiData(
        version="0.2",
        metadata=Metadata(
            name="nginx",
            display_name="NGINX Web Server",
            description="High-performance HTTP server and reverse proxy",
            version="1.22.0",
            category="web",
            subcategory="http-server",
            tags=["web", "server", "proxy", "load-balancer"],
            license="BSD-2-Clause",
            maintainer="NGINX Team"
        ),
        providers={
            "apt": {
                "packages": [
                    {"name": "nginx", "version": "1.22.0"}
                ]
            },
            "brew": {
                "packages": [
                    {"name": "nginx", "version": "1.22.0"}
                ]
            }
        },
        ports=[
            {"port": 80, "protocol": "tcp", "service": "http"},
            {"port": 443, "protocol": "tcp", "service": "https"}
        ]
    )


@pytest.fixture
def mock_generation_engine():
    """Mock generation engine."""
    engine = Mock(spec=GenerationEngine)
    engine.generate_saidata = AsyncMock()
    engine.validate_saidata_file = AsyncMock()
    return engine


@pytest.fixture
def update_engine(mock_generation_engine):
    """Update engine with mocked dependencies."""
    return UpdateEngine(config={}, generation_engine=mock_generation_engine)


class TestUpdateEngine:
    """Test cases for UpdateEngine."""
    
    @pytest.mark.asyncio
    async def test_update_saidata_force_update(self, update_engine, sample_existing_saidata, sample_fresh_saidata, mock_generation_engine):
        """Test force update mode."""
        # Mock generation result
        mock_generation_engine.generate_saidata.return_value = GenerationResult(
            success=True,
            saidata=sample_fresh_saidata,
            validation_errors=[],
            warnings=[],
            generation_time=1.5,
            llm_provider_used="openai",
            repository_sources_used=["apt", "brew"],
            tokens_used=1000,
            cost_estimate=0.02
        )
        
        # Test force update (should not use merge logic)
        result = await update_engine.update_saidata(
            existing_saidata=sample_existing_saidata,
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.OPENAI,
            merge_strategy="enhance",
            interactive=False
        )
        
        assert result.success
        assert result.saidata is not None
        assert result.llm_provider_used == "openai"
        assert "apt" in result.repository_sources_used
        assert "brew" in result.repository_sources_used
        
        # Verify generation was called with correct parameters
        mock_generation_engine.generate_saidata.assert_called_once()
        call_args = mock_generation_engine.generate_saidata.call_args[0][0]
        assert call_args.software_name == "nginx"
        assert call_args.existing_saidata == sample_existing_saidata
    
    @pytest.mark.asyncio
    async def test_merge_preserve_strategy(self, update_engine, sample_existing_saidata, sample_fresh_saidata):
        """Test preserve merge strategy."""
        existing_dict = sample_existing_saidata.model_dump(exclude_none=True)
        fresh_dict = sample_fresh_saidata.model_dump(exclude_none=True)
        
        merged_dict, stats = await update_engine._merge_preserve(existing_dict, fresh_dict, False)
        
        # Should preserve existing metadata description
        assert merged_dict['metadata']['description'] == "High-performance web server"
        
        # Should add new fields
        assert 'ports' in merged_dict
        assert merged_dict['providers']['brew'] is not None
        
        # Check stats
        assert stats['fields_added'] > 0
        assert stats['conflicts_resolved'] == 0  # No conflicts in non-interactive mode
    
    @pytest.mark.asyncio
    async def test_merge_enhance_strategy(self, update_engine, sample_existing_saidata, sample_fresh_saidata):
        """Test enhance merge strategy."""
        existing_dict = sample_existing_saidata.model_dump(exclude_none=True)
        fresh_dict = sample_fresh_saidata.model_dump(exclude_none=True)
        
        merged_dict, stats = await update_engine._merge_enhance(existing_dict, fresh_dict, False)
        
        # Should enhance metadata with new information
        assert merged_dict['metadata']['subcategory'] == "http-server"
        assert merged_dict['metadata']['maintainer'] == "NGINX Team"
        
        # Should merge tags
        merged_tags = set(merged_dict['metadata']['tags'])
        expected_tags = {"web", "server", "proxy", "load-balancer"}
        assert expected_tags.issubset(merged_tags)
        
        # Should add new providers
        assert 'brew' in merged_dict['providers']
        
        # Should add new top-level fields
        assert 'ports' in merged_dict
        
        # Check stats
        assert stats['fields_added'] > 0
        assert stats['fields_updated'] > 0
    
    @pytest.mark.asyncio
    async def test_merge_replace_strategy(self, update_engine, sample_existing_saidata, sample_fresh_saidata):
        """Test replace merge strategy."""
        existing_dict = sample_existing_saidata.model_dump(exclude_none=True)
        fresh_dict = sample_fresh_saidata.model_dump(exclude_none=True)
        
        merged_dict, stats = await update_engine._merge_replace(existing_dict, fresh_dict, False)
        
        # Should use fresh data
        assert merged_dict['metadata']['description'] == "High-performance HTTP server and reverse proxy"
        assert merged_dict['metadata']['version'] == "1.22.0"
        assert 'ports' in merged_dict
        assert 'brew' in merged_dict['providers']
        
        # Check stats
        assert stats['fields_updated'] > 0
    
    @pytest.mark.asyncio
    async def test_merge_metadata_enhance(self, update_engine):
        """Test metadata enhancement."""
        existing_metadata = {
            "name": "nginx",
            "description": "Web server",
            "tags": ["web", "server"]
        }
        
        fresh_metadata = {
            "name": "nginx",
            "description": "High-performance HTTP server and reverse proxy",
            "tags": ["web", "server", "proxy"],
            "maintainer": "NGINX Team",
            "urls": {
                "website": "https://nginx.org",
                "documentation": "https://nginx.org/en/docs/"
            }
        }
        
        stats = await update_engine._merge_metadata_enhance(existing_metadata, fresh_metadata, False)
        
        # Should use longer description
        assert existing_metadata['description'] == "High-performance HTTP server and reverse proxy"
        
        # Should merge tags
        assert set(existing_metadata['tags']) == {"web", "server", "proxy"}
        
        # Should add new fields
        assert existing_metadata['maintainer'] == "NGINX Team"
        assert existing_metadata['urls']['website'] == "https://nginx.org"
        
        # Check stats
        assert stats['fields_added'] > 0
        assert stats['fields_updated'] > 0
    
    @pytest.mark.asyncio
    async def test_merge_providers_enhance(self, update_engine):
        """Test provider enhancement."""
        existing_providers = {
            "apt": {
                "packages": [{"name": "nginx", "version": "1.20.0"}]
            }
        }
        
        fresh_providers = {
            "apt": {
                "packages": [{"name": "nginx", "version": "1.22.0"}],
                "services": [{"name": "nginx", "enabled": True}]
            },
            "brew": {
                "packages": [{"name": "nginx", "version": "1.22.0"}]
            }
        }
        
        stats = await update_engine._merge_providers_enhance(existing_providers, fresh_providers, False)
        
        # Should add new provider
        assert "brew" in existing_providers
        
        # Should enhance existing provider
        assert "services" in existing_providers["apt"]
        
        # Check stats
        assert stats['fields_added'] > 0
    
    @pytest.mark.asyncio
    async def test_merge_list_by_name(self, update_engine):
        """Test merging lists by name."""
        existing_list = [
            {"name": "nginx", "version": "1.20.0"},
            {"name": "nginx-common", "version": "1.20.0"}
        ]
        
        fresh_list = [
            {"name": "nginx", "version": "1.22.0"},
            {"name": "nginx-extras", "version": "1.22.0"}
        ]
        
        merged_list = await update_engine._merge_list_by_name(
            existing_list, fresh_list, False, "packages"
        )
        
        # Should keep existing items and add new ones
        names = {item['name'] for item in merged_list}
        assert names == {"nginx", "nginx-common", "nginx-extras"}
        
        # Should preserve existing versions (not update them)
        nginx_item = next(item for item in merged_list if item['name'] == 'nginx')
        assert nginx_item['version'] == "1.20.0"  # Preserved existing
    
    def test_get_nested_field(self, update_engine):
        """Test getting nested field values."""
        data = {
            "metadata": {
                "name": "nginx",
                "urls": {
                    "website": "https://nginx.org"
                }
            }
        }
        
        assert update_engine._get_nested_field(data, "metadata.name") == "nginx"
        assert update_engine._get_nested_field(data, "metadata.urls.website") == "https://nginx.org"
        assert update_engine._get_nested_field(data, "metadata.nonexistent") is None
        assert update_engine._get_nested_field(data, "nonexistent.field") is None
    
    def test_set_nested_field(self, update_engine):
        """Test setting nested field values."""
        data = {}
        
        update_engine._set_nested_field(data, "metadata.name", "nginx")
        assert data["metadata"]["name"] == "nginx"
        
        update_engine._set_nested_field(data, "metadata.urls.website", "https://nginx.org")
        assert data["metadata"]["urls"]["website"] == "https://nginx.org"
    
    def test_get_update_stats(self, update_engine):
        """Test getting update statistics."""
        # Simulate some updates
        update_engine._updates_performed = 5
        update_engine._total_conflicts_resolved = 10
        update_engine._total_fields_added = 25
        update_engine._total_fields_updated = 15
        
        stats = update_engine.get_update_stats()
        
        assert stats["total_updates"] == 5
        assert stats["total_conflicts_resolved"] == 10
        assert stats["total_fields_added"] == 25
        assert stats["total_fields_updated"] == 15
        assert stats["average_conflicts_per_update"] == 2.0
        assert stats["average_fields_added_per_update"] == 5.0
    
    @pytest.mark.asyncio
    async def test_update_saidata_generation_failure(self, update_engine, sample_existing_saidata, mock_generation_engine):
        """Test handling of generation failure during update."""
        # Mock generation failure
        mock_generation_engine.generate_saidata.return_value = GenerationResult(
            success=False,
            saidata=None,
            validation_errors=[],
            warnings=["Generation failed"],
            generation_time=0.5,
            llm_provider_used="openai",
            repository_sources_used=[]
        )
        
        result = await update_engine.update_saidata(
            existing_saidata=sample_existing_saidata,
            llm_provider=LLMProvider.OPENAI
        )
        
        assert not result.success
        assert result.saidata is None
        assert len(result.validation_errors) == 0  # Should return the failed generation result
    
    @pytest.mark.asyncio
    async def test_update_saidata_with_user_hints(self, update_engine, sample_existing_saidata, sample_fresh_saidata, mock_generation_engine):
        """Test update with user hints."""
        user_hints = {
            "focus_on": "security",
            "add_monitoring": True
        }
        
        mock_generation_engine.generate_saidata.return_value = GenerationResult(
            success=True,
            saidata=sample_fresh_saidata,
            validation_errors=[],
            warnings=[],
            generation_time=1.0,
            llm_provider_used="openai",
            repository_sources_used=["apt"]
        )
        
        result = await update_engine.update_saidata(
            existing_saidata=sample_existing_saidata,
            llm_provider=LLMProvider.OPENAI,
            user_hints=user_hints
        )
        
        assert result.success
        
        # Verify user hints were passed to generation
        call_args = mock_generation_engine.generate_saidata.call_args[0][0]
        assert call_args.user_hints == user_hints


class TestUpdateEngineIntegration:
    """Integration tests for UpdateEngine."""
    
    @pytest.mark.asyncio
    async def test_full_update_workflow(self, sample_existing_saidata, sample_fresh_saidata):
        """Test complete update workflow with real generation engine."""
        # Create a real generation engine with mocked LLM provider
        config = {}
        generation_engine = GenerationEngine(config)
        
        # Mock the LLM provider
        mock_provider = AsyncMock()
        mock_provider.generate_saidata.return_value = Mock(
            content="""
version: "0.2"
metadata:
  name: nginx
  display_name: NGINX Web Server
  description: High-performance HTTP server and reverse proxy
  version: "1.22.0"
  category: web
  subcategory: http-server
  tags:
    - web
    - server
    - proxy
    - load-balancer
  license: BSD-2-Clause
  maintainer: NGINX Team
providers:
  apt:
    packages:
      - name: nginx
        version: "1.22.0"
  brew:
    packages:
      - name: nginx
        version: "1.22.0"
ports:
  - port: 80
    protocol: tcp
    service: http
  - port: 443
    protocol: tcp
    service: https
            """.strip(),
            tokens_used=1500,
            cost_estimate=0.03
        )
        
        generation_engine._llm_providers = {"openai": mock_provider}
        
        # Create update engine
        update_engine = UpdateEngine(config, generation_engine)
        
        # Perform update
        result = await update_engine.update_saidata(
            existing_saidata=sample_existing_saidata,
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.OPENAI,
            merge_strategy="enhance",
            interactive=False
        )
        
        assert result.success
        assert result.saidata is not None
        assert result.saidata.metadata.name == "nginx"
        assert "brew" in result.saidata.providers
        assert result.saidata.ports is not None
        assert len(result.saidata.ports) == 2