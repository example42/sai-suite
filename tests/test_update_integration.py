"""Integration tests for update functionality."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from saigen.core.update_engine import UpdateEngine
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


class TestUpdateIntegration:
    """Integration tests for update functionality."""
    
    @pytest.mark.asyncio
    async def test_complete_update_workflow(self, sample_existing_saidata, sample_fresh_saidata):
        """Test complete update workflow with mocked LLM."""
        # Create a generation engine with mocked LLM provider
        config = {}
        generation_engine = GenerationEngine(config)
        
        # Mock the LLM provider with plain YAML content
        fresh_yaml_content = """
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
        """.strip()
        
        mock_provider = AsyncMock()
        mock_provider.generate_saidata.return_value = Mock(
            content=fresh_yaml_content,
            tokens_used=1500,
            cost_estimate=0.03
        )
        
        generation_engine._llm_providers = {"openai": mock_provider}
        
        # Create update engine
        update_engine = UpdateEngine(config, generation_engine)
        
        # Perform update with enhance strategy
        result = await update_engine.update_saidata(
            existing_saidata=sample_existing_saidata,
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.OPENAI,
            merge_strategy="enhance",
            interactive=False
        )
        
        # Verify result
        assert result.success
        assert result.saidata is not None
        assert result.saidata.metadata.name == "nginx"
        
        # Verify enhanced metadata
        assert result.saidata.metadata.subcategory == "http-server"
        assert result.saidata.metadata.maintainer == "NGINX Team"
        
        # Verify merged tags
        merged_tags = set(result.saidata.metadata.tags)
        expected_tags = {"web", "server", "proxy", "load-balancer"}
        assert expected_tags.issubset(merged_tags)
        
        # Verify new providers were added
        assert "brew" in result.saidata.providers
        
        # Verify new top-level fields were added
        assert result.saidata.ports is not None
        assert len(result.saidata.ports) == 2
    
    @pytest.mark.asyncio
    async def test_preserve_strategy_workflow(self, sample_existing_saidata, sample_fresh_saidata):
        """Test update workflow with preserve strategy."""
        # Create engines
        config = {}
        generation_engine = GenerationEngine(config)
        
        # Mock the LLM provider with plain YAML content
        fresh_yaml_content = """
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
        """.strip()
        
        mock_provider = AsyncMock()
        mock_provider.generate_saidata.return_value = Mock(
            content=fresh_yaml_content,
            tokens_used=1200,
            cost_estimate=0.024
        )
        
        generation_engine._llm_providers = {"openai": mock_provider}
        
        # Create update engine
        update_engine = UpdateEngine(config, generation_engine)
        
        # Perform update with preserve strategy
        result = await update_engine.update_saidata(
            existing_saidata=sample_existing_saidata,
            target_providers=["apt", "brew"],
            llm_provider=LLMProvider.OPENAI,
            merge_strategy="preserve",
            interactive=False
        )
        
        # Verify result
        assert result.success
        assert result.saidata is not None
        
        # Verify existing data was preserved
        assert result.saidata.metadata.description == "High-performance web server"  # Original preserved
        assert result.saidata.metadata.version == "1.20.0"  # Original preserved
        
        # Verify new fields were added
        assert "brew" in result.saidata.providers  # New provider added
        assert result.saidata.ports is not None  # New top-level field added
    
    @pytest.mark.asyncio
    async def test_file_based_update_workflow(self, sample_existing_saidata):
        """Test update workflow with actual file operations."""
        # Create temporary saidata file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_existing_saidata.model_dump(exclude_none=True), f)
            saidata_file = Path(f.name)
        
        try:
            # Load existing saidata from file
            from saigen.cli.commands.update import _load_existing_saidata
            loaded_saidata = _load_existing_saidata(saidata_file)
            
            # Verify loaded data matches original
            assert loaded_saidata.metadata.name == sample_existing_saidata.metadata.name
            assert loaded_saidata.metadata.description == sample_existing_saidata.metadata.description
            assert loaded_saidata.version == sample_existing_saidata.version
            
            # Test backup creation
            from saigen.cli.commands.update import _create_backup
            backup_path = _create_backup(saidata_file)
            
            # Verify backup was created
            assert backup_path.exists()
            assert backup_path != saidata_file
            assert backup_path.name.startswith("tmp")
            assert backup_path.name.endswith(".yaml")
            
            # Verify backup content matches original
            backup_saidata = _load_existing_saidata(backup_path)
            assert backup_saidata.metadata.name == sample_existing_saidata.metadata.name
            
            # Clean up backup
            backup_path.unlink()
            
        finally:
            # Clean up original file
            saidata_file.unlink()
    
    def test_update_statistics_tracking(self):
        """Test that update engine tracks statistics correctly."""
        config = {}
        generation_engine = GenerationEngine(config)
        update_engine = UpdateEngine(config, generation_engine)
        
        # Simulate some updates
        update_engine._updates_performed = 3
        update_engine._total_conflicts_resolved = 7
        update_engine._total_fields_added = 15
        update_engine._total_fields_updated = 9
        
        stats = update_engine.get_update_stats()
        
        assert stats["total_updates"] == 3
        assert stats["total_conflicts_resolved"] == 7
        assert stats["total_fields_added"] == 15
        assert stats["total_fields_updated"] == 9
        assert stats["average_conflicts_per_update"] == 7/3
        assert stats["average_fields_added_per_update"] == 15/3
    
    @pytest.mark.asyncio
    async def test_error_handling_in_update(self, sample_existing_saidata):
        """Test error handling during update process."""
        # Create engines
        config = {}
        generation_engine = GenerationEngine(config)
        
        # Mock the LLM provider to fail
        mock_provider = AsyncMock()
        mock_provider.generate_saidata.side_effect = Exception("LLM generation failed")
        
        generation_engine._llm_providers = {"openai": mock_provider}
        
        # Create update engine
        update_engine = UpdateEngine(config, generation_engine)
        
        # Attempt update (should handle error gracefully)
        result = await update_engine.update_saidata(
            existing_saidata=sample_existing_saidata,
            llm_provider=LLMProvider.OPENAI,
            merge_strategy="enhance"
        )
        
        # Verify error was handled
        assert not result.success
        assert result.saidata is None
        assert len(result.validation_errors) > 0
        assert "LLM generation failed" in str(result.validation_errors[0].message) or "Failed to generate fresh saidata" in str(result.validation_errors[0].message)