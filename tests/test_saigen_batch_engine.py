"""Tests for saigen batch processing engine."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from saigen.core.batch_engine import (
    BatchGenerationEngine,
    BatchProgressReporter,
    SoftwareListParser,
    BatchEngine
)
from saigen.models.generation import (
    BatchResult,
    BatchProgress,
    BatchError,
    BatchProcessingError
)
from saigen.models.generation import GenerationRequest, GenerationResult, LLMProvider
from saigen.models.saidata import SaiData, Metadata


class TestBatchEngine:
    """Test batch processing engine."""
    
    @pytest.fixture
    def mock_generation_engine(self):
        """Create mock generation engine."""
        engine = Mock()
        engine.generate_saidata = AsyncMock()
        return engine
    
    @pytest.fixture
    def batch_engine(self, mock_generation_engine):
        """Create batch engine with mock dependencies."""
        config = {
            "batch": {
                "max_concurrent": 3,
                "retry_attempts": 2,
                "timeout": 300
            }
        }
        return BatchEngine(config, mock_generation_engine)
    
    @pytest.fixture
    def sample_software_list(self):
        """Create sample software list."""
        return ["nginx", "apache2", "redis", "mysql", "postgresql"]
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_batch_engine_initialization(self, mock_generation_engine):
        """Test batch engine initialization."""
        config = {
            "batch": {
                "max_concurrent": 5,
                "retry_attempts": 3
            }
        }
        
        engine = BatchEngine(config, mock_generation_engine)
        
        assert engine.max_concurrent == 5
        assert engine.retry_attempts == 3
        assert engine.generation_engine == mock_generation_engine
    
    def test_batch_engine_default_config(self, mock_generation_engine):
        """Test batch engine with default configuration."""
        engine = BatchEngine({}, mock_generation_engine)
        
        assert engine.max_concurrent == 3
        assert engine.retry_attempts == 2
        assert engine.timeout == 300
    
    @pytest.mark.asyncio
    async def test_process_batch_success(self, batch_engine, sample_software_list, temp_output_dir):
        """Test successful batch processing."""
        # Mock successful generation results
        def mock_generate(request):
            return GenerationResult(
                success=True,
                saidata=SaiData(
                    version="0.2",
                    metadata=Metadata(name=request.software_name)
                ),
                validation_errors=[],
                warnings=[],
                generation_time=1.0,
                llm_provider_used="openai",
                tokens_used=100,
                cost_estimate=0.001
            )
        
        batch_engine.generation_engine.generate_saidata.side_effect = mock_generate
        
        # Process batch
        result = await batch_engine.process_batch(
            software_list=sample_software_list,
            output_directory=temp_output_dir,
            llm_provider=LLMProvider.OPENAI
        )
        
        # Verify results
        assert isinstance(result, BatchResult)
        assert result.total_processed == 5
        assert result.successful == 5
        assert result.failed == 0
        assert len(result.results) == 5
        assert result.total_time > 0
        
        # Verify all software was processed
        processed_names = [r.software_name for r in result.results]
        assert set(processed_names) == set(sample_software_list)
        
        # Verify files were created
        for software in sample_software_list:
            output_file = temp_output_dir / f"{software}.yaml"
            assert output_file.exists()
    
    @pytest.mark.asyncio
    async def test_process_batch_with_failures(self, batch_engine, temp_output_dir):
        """Test batch processing with some failures."""
        software_list = ["nginx", "invalid-software", "redis"]
        
        def mock_generate(request):
            if request.software_name == "invalid-software":
                return GenerationResult(
                    success=False,
                    saidata=None,
                    validation_errors=["Invalid software name"],
                    warnings=[],
                    generation_time=0.5,
                    llm_provider_used="openai",
                    tokens_used=50,
                    cost_estimate=0.0005
                )
            else:
                return GenerationResult(
                    success=True,
                    saidata=SaiData(
                        version="0.2",
                        metadata=Metadata(name=request.software_name)
                    ),
                    validation_errors=[],
                    warnings=[],
                    generation_time=1.0,
                    llm_provider_used="openai",
                    tokens_used=100,
                    cost_estimate=0.001
                )
        
        batch_engine.generation_engine.generate_saidata.side_effect = mock_generate
        
        result = await batch_engine.process_batch(
            software_list=software_list,
            output_directory=temp_output_dir,
            llm_provider=LLMProvider.OPENAI
        )
        
        assert result.total_processed == 3
        assert result.successful == 2
        assert result.failed == 1
        
        # Verify successful files were created
        assert (temp_output_dir / "nginx.yaml").exists()
        assert (temp_output_dir / "redis.yaml").exists()
        assert not (temp_output_dir / "invalid-software.yaml").exists()
    
    @pytest.mark.asyncio
    async def test_process_batch_with_retries(self, batch_engine, temp_output_dir):
        """Test batch processing with retry logic."""
        software_list = ["nginx"]
        call_count = 0
        
        def mock_generate(request):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call fails
                raise Exception("Temporary failure")
            else:
                # Second call succeeds
                return GenerationResult(
                    success=True,
                    saidata=SaiData(
                        version="0.2",
                        metadata=Metadata(name=request.software_name)
                    ),
                    validation_errors=[],
                    warnings=[],
                    generation_time=1.0,
                    llm_provider_used="openai",
                    tokens_used=100,
                    cost_estimate=0.001
                )
        
        batch_engine.generation_engine.generate_saidata.side_effect = mock_generate
        
        result = await batch_engine.process_batch(
            software_list=software_list,
            output_directory=temp_output_dir,
            llm_provider=LLMProvider.OPENAI
        )
        
        assert result.successful == 1
        assert result.failed == 0
        assert call_count == 2  # Verify retry occurred
    
    @pytest.mark.asyncio
    async def test_process_batch_max_retries_exceeded(self, batch_engine, temp_output_dir):
        """Test batch processing when max retries are exceeded."""
        software_list = ["nginx"]
        
        # Mock to always fail
        batch_engine.generation_engine.generate_saidata.side_effect = Exception("Persistent failure")
        
        result = await batch_engine.process_batch(
            software_list=software_list,
            output_directory=temp_output_dir,
            llm_provider=LLMProvider.OPENAI
        )
        
        assert result.successful == 0
        assert result.failed == 1
        
        # Verify retry attempts were made (original + 2 retries = 3 total)
        assert batch_engine.generation_engine.generate_saidata.call_count == 3
    
    @pytest.mark.asyncio
    async def test_process_batch_with_progress_callback(self, batch_engine, temp_output_dir):
        """Test batch processing with progress callback."""
        software_list = ["nginx", "redis"]
        progress_updates = []
        
        def progress_callback(progress: BatchProgress):
            progress_updates.append({
                'completed': progress.completed,
                'total': progress.total,
                'current_software': progress.current_software,
                'percentage': progress.percentage
            })
        
        # Mock successful generation
        batch_engine.generation_engine.generate_saidata.return_value = GenerationResult(
            success=True,
            saidata=SaiData(version="0.2", metadata=Metadata(name="test")),
            validation_errors=[],
            warnings=[],
            generation_time=1.0,
            llm_provider_used="openai",
            tokens_used=100,
            cost_estimate=0.001
        )
        
        await batch_engine.process_batch(
            software_list=software_list,
            output_directory=temp_output_dir,
            llm_provider=LLMProvider.OPENAI,
            progress_callback=progress_callback
        )
        
        # Verify progress updates were called
        assert len(progress_updates) >= 2  # At least start and end
        assert progress_updates[-1]['completed'] == 2
        assert progress_updates[-1]['total'] == 2
        assert progress_updates[-1]['percentage'] == 100.0
    
    @pytest.mark.asyncio
    async def test_process_batch_concurrency_limit(self, batch_engine, temp_output_dir):
        """Test that batch processing respects concurrency limits."""
        software_list = ["nginx", "apache2", "redis", "mysql", "postgresql"]
        concurrent_calls = 0
        max_concurrent_seen = 0
        
        async def mock_generate(request):
            nonlocal concurrent_calls, max_concurrent_seen
            concurrent_calls += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_calls)
            
            # Simulate some processing time
            await asyncio.sleep(0.1)
            
            concurrent_calls -= 1
            
            return GenerationResult(
                success=True,
                saidata=SaiData(
                    version="0.2",
                    metadata=Metadata(name=request.software_name)
                ),
                validation_errors=[],
                warnings=[],
                generation_time=0.1,
                llm_provider_used="openai",
                tokens_used=100,
                cost_estimate=0.001
            )
        
        batch_engine.generation_engine.generate_saidata.side_effect = mock_generate
        
        await batch_engine.process_batch(
            software_list=software_list,
            output_directory=temp_output_dir,
            llm_provider=LLMProvider.OPENAI
        )
        
        # Verify concurrency was limited
        assert max_concurrent_seen <= batch_engine.max_concurrent
    
    @pytest.mark.asyncio
    async def test_process_batch_with_filters(self, batch_engine, temp_output_dir):
        """Test batch processing with category filters."""
        software_list = ["nginx", "apache2", "redis", "mysql"]
        
        # Mock generation with categories
        def mock_generate(request):
            categories = {
                "nginx": "web-server",
                "apache2": "web-server", 
                "redis": "database",
                "mysql": "database"
            }
            
            return GenerationResult(
                success=True,
                saidata=SaiData(
                    version="0.2",
                    metadata=Metadata(
                        name=request.software_name,
                        category=categories.get(request.software_name, "other")
                    )
                ),
                validation_errors=[],
                warnings=[],
                generation_time=1.0,
                llm_provider_used="openai",
                tokens_used=100,
                cost_estimate=0.001
            )
        
        batch_engine.generation_engine.generate_saidata.side_effect = mock_generate
        
        # Process with category filter
        result = await batch_engine.process_batch(
            software_list=software_list,
            output_directory=temp_output_dir,
            llm_provider=LLMProvider.OPENAI,
            category_filter="web-server"
        )
        
        # Should only process web-server category
        assert result.successful == 2
        assert (temp_output_dir / "nginx.yaml").exists()
        assert (temp_output_dir / "apache2.yaml").exists()
        assert not (temp_output_dir / "redis.yaml").exists()
        assert not (temp_output_dir / "mysql.yaml").exists()
    
    def test_batch_result_statistics(self):
        """Test batch result statistics calculation."""
        results = [
            Mock(success=True, generation_time=1.0, tokens_used=100, cost_estimate=0.001),
            Mock(success=True, generation_time=2.0, tokens_used=200, cost_estimate=0.002),
            Mock(success=False, generation_time=0.5, tokens_used=50, cost_estimate=0.0005),
        ]
        
        batch_result = BatchResult(
            total_processed=3,
            successful=2,
            failed=1,
            results=results,
            total_time=10.0,
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        
        stats = batch_result.get_statistics()
        
        assert stats['success_rate'] == 2/3
        assert stats['average_generation_time'] == 1.5  # (1.0 + 2.0) / 2
        assert stats['total_tokens_used'] == 350
        assert stats['total_cost_estimate'] == 0.0035
        assert stats['average_tokens_per_success'] == 150  # (100 + 200) / 2
    
    def test_batch_progress_calculation(self):
        """Test batch progress percentage calculation."""
        progress = BatchProgress(
            completed=3,
            total=10,
            current_software="nginx",
            start_time=datetime.now()
        )
        
        assert progress.percentage == 30.0
        assert progress.current_software == "nginx"
        assert progress.remaining == 7
    
    def test_batch_error_handling(self):
        """Test batch error types."""
        # Test BatchProcessingError
        error = BatchProcessingError("Test error", software_name="nginx")
        assert error.software_name == "nginx"
        assert "nginx" in str(error)
        
        # Test BatchError
        error = BatchError("General batch error")
        assert "General batch error" in str(error)
    
    @pytest.mark.asyncio
    async def test_process_batch_empty_list(self, batch_engine, temp_output_dir):
        """Test batch processing with empty software list."""
        result = await batch_engine.process_batch(
            software_list=[],
            output_directory=temp_output_dir,
            llm_provider=LLMProvider.OPENAI
        )
        
        assert result.total_processed == 0
        assert result.successful == 0
        assert result.failed == 0
        assert len(result.results) == 0
    
    @pytest.mark.asyncio
    async def test_process_batch_invalid_output_directory(self, batch_engine):
        """Test batch processing with invalid output directory."""
        with pytest.raises(BatchProcessingError):
            await batch_engine.process_batch(
                software_list=["nginx"],
                output_directory=Path("/invalid/path/that/does/not/exist"),
                llm_provider=LLMProvider.OPENAI
            )
    
    @pytest.mark.asyncio
    async def test_process_batch_timeout_handling(self, batch_engine, temp_output_dir):
        """Test batch processing with timeout."""
        # Set very short timeout
        batch_engine.timeout = 0.1
        
        async def slow_generate(request):
            await asyncio.sleep(0.2)  # Longer than timeout
            return GenerationResult(
                success=True,
                saidata=SaiData(version="0.2", metadata=Metadata(name="test")),
                validation_errors=[],
                warnings=[],
                generation_time=0.2,
                llm_provider_used="openai",
                tokens_used=100,
                cost_estimate=0.001
            )
        
        batch_engine.generation_engine.generate_saidata.side_effect = slow_generate
        
        result = await batch_engine.process_batch(
            software_list=["nginx"],
            output_directory=temp_output_dir,
            llm_provider=LLMProvider.OPENAI
        )
        
        # Should fail due to timeout
        assert result.failed == 1
        assert result.successful == 0