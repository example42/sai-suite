"""Tests for batch generation engine."""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from saigen.core.batch_engine import (
    BatchGenerationEngine,
    SoftwareListParser,
    BatchProgressReporter
)
from saigen.core.generation_engine import GenerationEngine
from saigen.models.generation import (
    BatchGenerationRequest,
    BatchGenerationResult,
    GenerationRequest,
    GenerationResult,
    LLMProvider
)
from saigen.models.saidata import SaiData


class TestSoftwareListParser:
    """Test software list parsing functionality."""
    
    def test_parse_simple_list(self):
        """Test parsing a simple software list."""
        content = """# Test software list
nginx
postgresql
redis
# Comment line
docker
"""
        result = SoftwareListParser.parse_string(content)
        assert result == ["nginx", "postgresql", "redis", "docker"]
    
    def test_parse_with_categories(self):
        """Test parsing with category headers."""
        content = """# Software list with categories

## Web Servers
nginx
apache

## Databases  
postgresql
mysql

## Cache
redis
memcached
"""
        result = SoftwareListParser.parse_string(content)
        expected = ["nginx", "apache", "postgresql", "mysql", "redis", "memcached"]
        assert result == expected
    
    def test_parse_with_category_filter(self):
        """Test parsing with category filtering."""
        content = """# Software list with categories

## Web Servers
nginx
apache

## Databases  
postgresql
mysql

## Cache Systems
redis
memcached
"""
        # Filter for databases only
        result = SoftwareListParser.parse_string(content, category_filter="database")
        assert result == ["postgresql", "mysql"]
        
        # Filter for web or cache
        result = SoftwareListParser.parse_string(content, category_filter="web|cache")
        assert result == ["nginx", "apache", "redis", "memcached"]
    
    def test_parse_with_inline_comments(self):
        """Test parsing with inline comments."""
        content = """nginx  # Web server
postgresql  # Database
redis # Cache system
"""
        result = SoftwareListParser.parse_string(content)
        assert result == ["nginx", "postgresql", "redis"]
    
    def test_validate_software_names(self):
        """Test software name validation."""
        names = [
            "nginx",           # Valid
            "postgresql-13",   # Valid with dash and number
            "node.js",         # Valid with dot
            "my_app",          # Valid with underscore
            "invalid name",    # Invalid - space
            "invalid@name",    # Invalid - special char
            "",                # Invalid - empty
            "valid-name_2.0"   # Valid complex name
        ]
        
        result = SoftwareListParser.validate_software_names(names)
        expected = ["nginx", "postgresql-13", "node.js", "my_app", "valid-name_2.0"]
        assert result == expected
    
    def test_parse_file(self, tmp_path):
        """Test parsing from file."""
        test_file = tmp_path / "software_list.txt"
        test_file.write_text("""# Test list
nginx
postgresql
redis
""")
        
        result = SoftwareListParser.parse_file(test_file)
        assert result == ["nginx", "postgresql", "redis"]
    
    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            SoftwareListParser.parse_file(Path("nonexistent.txt"))


class TestBatchProgressReporter:
    """Test batch progress reporting."""
    
    def test_progress_tracking(self):
        """Test progress counter updates."""
        reporter = BatchProgressReporter(total_items=10)
        
        assert reporter.completed == 0
        assert reporter.successful == 0
        assert reporter.failed == 0
        
        reporter.update(True, "nginx")
        assert reporter.completed == 1
        assert reporter.successful == 1
        assert reporter.failed == 0
        
        reporter.update(False, "invalid")
        assert reporter.completed == 2
        assert reporter.successful == 1
        assert reporter.failed == 1
    
    def test_get_summary(self):
        """Test summary statistics."""
        reporter = BatchProgressReporter(total_items=5)
        
        # Simulate some progress
        reporter.update(True, "nginx")
        reporter.update(True, "redis")
        reporter.update(False, "invalid")
        
        summary = reporter.get_summary()
        
        assert summary["total"] == 5
        assert summary["completed"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert abs(summary["success_rate"] - (200/3)) < 0.01  # 66.67%
        assert "elapsed_time" in summary
        assert "average_time_per_item" in summary


class TestBatchGenerationEngine:
    """Test batch generation engine."""
    
    @pytest.fixture
    def mock_generation_engine(self):
        """Create mock generation engine."""
        engine = Mock(spec=GenerationEngine)
        engine.generate_saidata = AsyncMock()
        engine.save_saidata = AsyncMock()
        return engine
    
    @pytest.fixture
    def batch_engine(self, mock_generation_engine):
        """Create batch generation engine with mock."""
        return BatchGenerationEngine(mock_generation_engine)
    
    @pytest.fixture
    def sample_saidata(self):
        """Create sample saidata for testing."""
        from saigen.models.saidata import Metadata
        return SaiData(
            version="0.2",
            metadata=Metadata(
                name="nginx",
                description="Web server"
            ),
            providers={
                "apt": {
                    "packages": [{"name": "nginx"}]
                }
            }
        )
    
    @pytest.mark.asyncio
    async def test_generate_batch_success(self, batch_engine, mock_generation_engine, sample_saidata):
        """Test successful batch generation."""
        # Setup mock to return successful results
        mock_result = GenerationResult(
            success=True,
            saidata=sample_saidata,
            validation_errors=[],
            warnings=[],
            generation_time=1.0,
            llm_provider_used="openai",
            repository_sources_used=["apt"]
        )
        mock_generation_engine.generate_saidata.return_value = mock_result
        
        # Create batch request
        request = BatchGenerationRequest(
            software_list=["nginx", "redis", "postgresql"],
            target_providers=["apt"],
            llm_provider=LLMProvider.OPENAI,
            max_concurrent=2,
            continue_on_error=True
        )
        
        # Execute batch generation
        result = await batch_engine.generate_batch(request)
        
        # Verify results
        assert result.total_requested == 3
        assert result.successful == 3
        assert result.failed == 0
        assert len(result.results) == 3
        assert len(result.failed_software) == 0
        assert result.total_time > 0
        
        # Verify generation engine was called for each software
        assert mock_generation_engine.generate_saidata.call_count == 3
    
    @pytest.mark.asyncio
    async def test_generate_batch_with_failures(self, batch_engine, mock_generation_engine):
        """Test batch generation with some failures."""
        # Setup mock to return mixed results
        def mock_generate(request):
            if request.software_name == "invalid":
                return GenerationResult(
                    success=False,
                    saidata=None,
                    validation_errors=[],
                    warnings=["Generation failed"],
                    generation_time=0.5,
                    llm_provider_used="openai",
                    repository_sources_used=[]
                )
            else:
                return GenerationResult(
                    success=True,
                    saidata=Mock(spec=SaiData),
                    validation_errors=[],
                    warnings=[],
                    generation_time=1.0,
                    llm_provider_used="openai",
                    repository_sources_used=["apt"]
                )
        
        mock_generation_engine.generate_saidata.side_effect = mock_generate
        
        # Create batch request with one invalid software
        request = BatchGenerationRequest(
            software_list=["nginx", "invalid", "redis"],
            target_providers=["apt"],
            llm_provider=LLMProvider.OPENAI,
            max_concurrent=2,
            continue_on_error=True
        )
        
        # Execute batch generation
        result = await batch_engine.generate_batch(request)
        
        # Verify results
        assert result.total_requested == 3
        assert result.successful == 2
        assert result.failed == 1
        assert len(result.results) == 3
        assert "invalid" in result.failed_software
    
    @pytest.mark.asyncio
    async def test_generate_batch_stop_on_error(self, batch_engine, mock_generation_engine):
        """Test batch generation stopping on first error."""
        # Setup mock to raise exception
        mock_generation_engine.generate_saidata.side_effect = Exception("Generation failed")
        
        # Create batch request with stop on error
        request = BatchGenerationRequest(
            software_list=["nginx", "redis"],
            target_providers=["apt"],
            llm_provider=LLMProvider.OPENAI,
            max_concurrent=1,
            continue_on_error=False
        )
        
        # Execute batch generation - should raise exception
        from saigen.core.generation_engine import GenerationEngineError
        with pytest.raises(GenerationEngineError, match="Batch processing failed"):
            await batch_engine.generate_batch(request)
    
    @pytest.mark.asyncio
    async def test_generate_from_file(self, batch_engine, mock_generation_engine, tmp_path):
        """Test generating from file."""
        # Create test file
        test_file = tmp_path / "software_list.txt"
        test_file.write_text("""# Test software
nginx
redis
postgresql
""")
        
        # Setup mock
        mock_result = GenerationResult(
            success=True,
            saidata=Mock(spec=SaiData),
            validation_errors=[],
            warnings=[],
            generation_time=1.0,
            llm_provider_used="openai",
            repository_sources_used=["apt"]
        )
        mock_generation_engine.generate_saidata.return_value = mock_result
        
        # Execute generation from file
        result = await batch_engine.generate_from_file(
            file_path=test_file,
            target_providers=["apt"],
            llm_provider=LLMProvider.OPENAI,
            max_concurrent=2
        )
        
        # Verify results
        assert result.total_requested == 3
        assert result.successful == 3
        assert result.failed == 0
    
    @pytest.mark.asyncio
    async def test_generate_from_list(self, batch_engine, mock_generation_engine):
        """Test generating from software list."""
        # Setup mock
        mock_result = GenerationResult(
            success=True,
            saidata=Mock(spec=SaiData),
            validation_errors=[],
            warnings=[],
            generation_time=1.0,
            llm_provider_used="openai",
            repository_sources_used=["apt"]
        )
        mock_generation_engine.generate_saidata.return_value = mock_result
        
        # Execute generation from list
        result = await batch_engine.generate_from_list(
            software_names=["nginx", "redis"],
            target_providers=["apt"],
            llm_provider=LLMProvider.OPENAI,
            max_concurrent=2
        )
        
        # Verify results
        assert result.total_requested == 2
        assert result.successful == 2
        assert result.failed == 0
    
    @pytest.mark.asyncio
    async def test_generate_with_output_directory(self, batch_engine, mock_generation_engine, tmp_path, sample_saidata):
        """Test batch generation with output directory."""
        # Setup mock
        mock_result = GenerationResult(
            success=True,
            saidata=sample_saidata,
            validation_errors=[],
            warnings=[],
            generation_time=1.0,
            llm_provider_used="openai",
            repository_sources_used=["apt"]
        )
        mock_generation_engine.generate_saidata.return_value = mock_result
        
        # Create batch request with output directory
        output_dir = tmp_path / "output"
        request = BatchGenerationRequest(
            software_list=["nginx"],
            target_providers=["apt"],
            llm_provider=LLMProvider.OPENAI,
            output_directory=output_dir,
            max_concurrent=1
        )
        
        # Execute batch generation
        result = await batch_engine.generate_batch(request)
        
        # Verify results
        assert result.successful == 1
        
        # Verify save_saidata was called
        mock_generation_engine.save_saidata.assert_called_once()
        call_args = mock_generation_engine.save_saidata.call_args
        assert call_args[0][0] == sample_saidata  # saidata argument
        assert call_args[0][1] == output_dir / "nginx.yaml"  # path argument
    
    def test_get_statistics_summary(self, batch_engine):
        """Test statistics summary formatting."""
        result = BatchGenerationResult(
            total_requested=10,
            successful=8,
            failed=2,
            results=[],
            failed_software=["invalid1", "invalid2"],
            total_time=30.0,
            average_time_per_item=3.0
        )
        
        summary = batch_engine.get_statistics_summary(result)
        
        assert "Total Requested: 10" in summary
        assert "Successful: 8" in summary
        assert "Failed: 2" in summary
        assert "Success Rate: 80.0%" in summary
        assert "Total Time: 30.00s" in summary
        assert "Average Time per Item: 3.00s" in summary
        assert "invalid1" in summary
        assert "invalid2" in summary
    
    @pytest.mark.asyncio
    async def test_empty_software_list_error(self, batch_engine):
        """Test error handling for empty software list."""
        request = BatchGenerationRequest(
            software_list=[],
            target_providers=["apt"],
            llm_provider=LLMProvider.OPENAI
        )
        
        with pytest.raises(Exception, match="Software list cannot be empty"):
            await batch_engine.generate_batch(request)
    
    @pytest.mark.asyncio
    async def test_invalid_software_names_filtered(self, batch_engine, mock_generation_engine):
        """Test that invalid software names are filtered out."""
        # Setup mock
        mock_result = GenerationResult(
            success=True,
            saidata=Mock(spec=SaiData),
            validation_errors=[],
            warnings=[],
            generation_time=1.0,
            llm_provider_used="openai",
            repository_sources_used=["apt"]
        )
        mock_generation_engine.generate_saidata.return_value = mock_result
        
        # Create request with mix of valid and invalid names
        request = BatchGenerationRequest(
            software_list=["nginx", "invalid name", "redis", ""],
            target_providers=["apt"],
            llm_provider=LLMProvider.OPENAI
        )
        
        # Execute batch generation
        result = await batch_engine.generate_batch(request)
        
        # Should only process valid names
        assert result.total_requested == 2  # Only nginx and redis
        assert mock_generation_engine.generate_saidata.call_count == 2
    
    @pytest.mark.asyncio
    async def test_progress_callback(self, batch_engine, mock_generation_engine):
        """Test progress callback functionality."""
        # Setup mock
        mock_result = GenerationResult(
            success=True,
            saidata=Mock(spec=SaiData),
            validation_errors=[],
            warnings=[],
            generation_time=1.0,
            llm_provider_used="openai",
            repository_sources_used=["apt"]
        )
        mock_generation_engine.generate_saidata.return_value = mock_result
        
        # Create progress callback mock
        progress_callback = Mock()
        
        # Create batch request
        request = BatchGenerationRequest(
            software_list=["nginx", "redis"],
            target_providers=["apt"],
            llm_provider=LLMProvider.OPENAI,
            max_concurrent=1
        )
        
        # Execute with progress callback
        await batch_engine.generate_batch(request, progress_callback)
        
        # Verify callback was called for each software
        assert progress_callback.call_count == 2
        progress_callback.assert_any_call("nginx", True)
        progress_callback.assert_any_call("redis", True)