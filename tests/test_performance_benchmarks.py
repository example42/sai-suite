"""Performance benchmarks and memory usage tests for saigen."""

import pytest
import asyncio
import time
import psutil
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any
import gc

from saigen.core.generation_engine import GenerationEngine
from saigen.core.batch_engine import BatchGenerationEngine, BatchEngine
from saigen.repositories.manager import RepositoryManager
from saigen.repositories.indexer import RAGIndexer
from saigen.models.generation import GenerationRequest, GenerationResult, LLMProvider
from saigen.models.saidata import SaiData, Metadata
from saigen.models.repository import RepositoryPackage


class PerformanceMonitor:
    """Monitor performance metrics during tests."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = None
        self.start_memory = None
        self.peak_memory = None
    
    def start(self):
        """Start monitoring."""
        gc.collect()  # Clean up before measurement
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss
        self.peak_memory = self.start_memory
    
    def update_peak_memory(self):
        """Update peak memory usage."""
        current_memory = self.process.memory_info().rss
        self.peak_memory = max(self.peak_memory, current_memory)
    
    def stop(self):
        """Stop monitoring and return metrics."""
        end_time = time.time()
        end_memory = self.process.memory_info().rss
        
        return {
            'duration': end_time - self.start_time,
            'start_memory_mb': self.start_memory / 1024 / 1024,
            'end_memory_mb': end_memory / 1024 / 1024,
            'peak_memory_mb': self.peak_memory / 1024 / 1024,
            'memory_delta_mb': (end_memory - self.start_memory) / 1024 / 1024
        }


@pytest.mark.slow
@pytest.mark.performance
class TestGenerationEnginePerformance:
    """Performance tests for generation engine."""
    
    @pytest.fixture
    def mock_generation_engine(self):
        """Create mock generation engine for performance testing."""
        config = {
            "llm_providers": {
                "openai": {
                    "api_key": "test-key",
                    "model": "gpt-3.5-turbo"
                }
            }
        }
        
        engine = GenerationEngine(config)
        
        # Mock LLM provider
        mock_provider = Mock()
        mock_provider.is_available.return_value = True
        mock_provider.get_provider_name.return_value = "openai"
        
        # Mock fast generation response
        async def mock_generate(context):
            await asyncio.sleep(0.01)  # Simulate minimal processing time
            return Mock(
                content="version: '0.2'\nmetadata:\n  name: test",
                tokens_used=100,
                cost_estimate=0.001,
                model_used="gpt-3.5-turbo",
                finish_reason="stop"
            )
        
        mock_provider.generate_saidata = mock_generate
        engine._llm_providers["openai"] = mock_provider
        
        return engine
    
    @pytest.mark.asyncio
    async def test_single_generation_performance(self, mock_generation_engine):
        """Test performance of single saidata generation."""
        monitor = PerformanceMonitor()
        monitor.start()
        
        request = GenerationRequest(
            software_name="nginx",
            llm_provider=LLMProvider.OPENAI
        )
        
        result = await mock_generation_engine.generate_saidata(request)
        
        metrics = monitor.stop()
        
        # Performance assertions
        assert result.success
        assert metrics['duration'] < 1.0  # Should complete in under 1 second
        assert metrics['memory_delta_mb'] < 50  # Should not use more than 50MB additional memory
        
        print(f"Single generation metrics: {metrics}")
    
    @pytest.mark.asyncio
    async def test_concurrent_generation_performance(self, mock_generation_engine):
        """Test performance of concurrent saidata generation."""
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Create multiple concurrent requests
        requests = [
            GenerationRequest(
                software_name=f"software-{i}",
                llm_provider=LLMProvider.OPENAI
            )
            for i in range(10)
        ]
        
        # Execute concurrently
        tasks = [
            mock_generation_engine.generate_saidata(request)
            for request in requests
        ]
        
        results = await asyncio.gather(*tasks)
        
        metrics = monitor.stop()
        
        # Performance assertions
        assert all(result.success for result in results)
        assert metrics['duration'] < 5.0  # Should complete in under 5 seconds
        assert metrics['memory_delta_mb'] < 100  # Should not use more than 100MB additional memory
        
        print(f"Concurrent generation metrics (10 requests): {metrics}")
    
    @pytest.mark.asyncio
    async def test_memory_usage_scaling(self, mock_generation_engine):
        """Test memory usage scaling with number of generations."""
        memory_usage = []
        
        for batch_size in [1, 5, 10, 20]:
            monitor = PerformanceMonitor()
            monitor.start()
            
            requests = [
                GenerationRequest(
                    software_name=f"software-{i}",
                    llm_provider=LLMProvider.OPENAI
                )
                for i in range(batch_size)
            ]
            
            tasks = [
                mock_generation_engine.generate_saidata(request)
                for request in requests
            ]
            
            await asyncio.gather(*tasks)
            
            metrics = monitor.stop()
            memory_usage.append({
                'batch_size': batch_size,
                'memory_delta_mb': metrics['memory_delta_mb'],
                'duration': metrics['duration']
            })
            
            # Clean up between batches
            gc.collect()
            await asyncio.sleep(0.1)
        
        # Memory usage should scale reasonably
        for i in range(1, len(memory_usage)):
            current = memory_usage[i]
            previous = memory_usage[i-1]
            
            # Memory usage should not grow exponentially
            memory_ratio = current['memory_delta_mb'] / max(previous['memory_delta_mb'], 1)
            batch_ratio = current['batch_size'] / previous['batch_size']
            
            assert memory_ratio <= batch_ratio * 2  # Allow some overhead but not exponential growth
        
        print(f"Memory scaling results: {memory_usage}")


@pytest.mark.slow
@pytest.mark.performance
class TestBatchEnginePerformance:
    """Performance tests for batch processing engine."""
    
    @pytest.fixture
    def mock_batch_engine(self):
        """Create mock batch engine for performance testing."""
        mock_generation_engine = Mock()
        
        async def mock_generate(request):
            await asyncio.sleep(0.01)  # Simulate processing time
            return GenerationResult(
                success=True,
                saidata=SaiData(
                    version="0.2",
                    metadata=Metadata(name=request.software_name)
                ),
                validation_errors=[],
                warnings=[],
                generation_time=0.01,
                llm_provider_used="openai",
                tokens_used=100,
                cost_estimate=0.001
            )
        
        mock_generation_engine.generate_saidata = mock_generate
        
        config = {
            "batch": {
                "max_concurrent": 5,
                "retry_attempts": 1,
                "timeout": 30
            }
        }
        
        return BatchEngine(config, mock_generation_engine)
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.mark.asyncio
    async def test_batch_processing_throughput(self, mock_batch_engine, temp_output_dir):
        """Test batch processing throughput."""
        software_list = [f"software-{i}" for i in range(50)]
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        result = await mock_batch_engine.process_batch(
            software_list=software_list,
            output_directory=temp_output_dir,
            llm_provider=LLMProvider.OPENAI
        )
        
        metrics = monitor.stop()
        
        # Performance assertions
        assert result.successful == 50
        assert result.failed == 0
        
        throughput = len(software_list) / metrics['duration']
        assert throughput > 5  # Should process at least 5 items per second
        
        print(f"Batch processing metrics (50 items): {metrics}")
        print(f"Throughput: {throughput:.2f} items/second")
    
    @pytest.mark.asyncio
    async def test_batch_memory_efficiency(self, mock_batch_engine, temp_output_dir):
        """Test batch processing memory efficiency."""
        # Test with different batch sizes
        batch_sizes = [10, 25, 50, 100]
        memory_results = []
        
        for batch_size in batch_sizes:
            software_list = [f"software-{i}" for i in range(batch_size)]
            
            monitor = PerformanceMonitor()
            monitor.start()
            
            result = await mock_batch_engine.process_batch(
                software_list=software_list,
                output_directory=temp_output_dir,
                llm_provider=LLMProvider.OPENAI
            )
            
            metrics = monitor.stop()
            
            memory_results.append({
                'batch_size': batch_size,
                'memory_per_item_mb': metrics['memory_delta_mb'] / batch_size,
                'duration': metrics['duration'],
                'successful': result.successful
            })
            
            # Clean up between tests
            gc.collect()
            await asyncio.sleep(0.1)
        
        # Memory per item should remain relatively constant
        memory_per_item_values = [r['memory_per_item_mb'] for r in memory_results]
        avg_memory_per_item = sum(memory_per_item_values) / len(memory_per_item_values)
        
        for memory_per_item in memory_per_item_values:
            # Memory per item should not vary by more than 50% from average
            assert abs(memory_per_item - avg_memory_per_item) / avg_memory_per_item < 0.5
        
        print(f"Batch memory efficiency results: {memory_results}")
    
    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self, mock_batch_engine, temp_output_dir):
        """Test concurrent batch processing performance."""
        # Create multiple smaller batches to process concurrently
        batch1 = [f"batch1-software-{i}" for i in range(10)]
        batch2 = [f"batch2-software-{i}" for i in range(10)]
        batch3 = [f"batch3-software-{i}" for i in range(10)]
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Process batches concurrently
        tasks = [
            mock_batch_engine.process_batch(
                software_list=batch,
                output_directory=temp_output_dir / f"batch{i}",
                llm_provider=LLMProvider.OPENAI
            )
            for i, batch in enumerate([batch1, batch2, batch3], 1)
        ]
        
        results = await asyncio.gather(*tasks)
        
        metrics = monitor.stop()
        
        # All batches should succeed
        assert all(result.successful == 10 for result in results)
        assert all(result.failed == 0 for result in results)
        
        # Concurrent processing should be faster than sequential
        total_items = sum(len(batch) for batch in [batch1, batch2, batch3])
        throughput = total_items / metrics['duration']
        
        assert throughput > 8  # Should be faster due to concurrency
        
        print(f"Concurrent batch processing metrics: {metrics}")
        print(f"Concurrent throughput: {throughput:.2f} items/second")


@pytest.mark.slow
@pytest.mark.performance
class TestRepositoryManagerPerformance:
    """Performance tests for repository manager."""
    
    @pytest.fixture
    def mock_repository_manager(self):
        """Create mock repository manager for performance testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "repositories": {
                    "test_repo": {
                        "enabled": True,
                        "priority": 80,
                        "cache_ttl": 3600
                    }
                },
                "cache_directory": temp_dir
            }
            
            manager = RepositoryManager(config)
            
            # Mock large package dataset
            large_package_list = [
                RepositoryPackage(
                    name=f"package-{i}",
                    version=f"1.{i % 10}.{i % 100}",
                    description=f"Test package {i}",
                    repository_name="test_repo",
                    platform="linux",
                    category=f"category-{i % 5}",
                    tags=[f"tag-{i % 3}", f"tag-{(i+1) % 3}"]
                )
                for i in range(10000)  # 10k packages
            ]
            
            # Mock cache
            mock_cache = Mock()
            mock_cache.get_cached_data.return_value = large_package_list
            mock_cache.is_expired.return_value = False
            mock_cache.store_data = AsyncMock()
            
            manager._cache = mock_cache
            
            return manager, large_package_list
    
    @pytest.mark.asyncio
    async def test_large_package_list_performance(self, mock_repository_manager):
        """Test performance with large package lists."""
        manager, package_list = mock_repository_manager
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Get all packages
        packages = await manager.get_packages("test_repo")
        
        metrics = monitor.stop()
        
        assert len(packages) == 10000
        assert metrics['duration'] < 2.0  # Should load 10k packages in under 2 seconds
        
        print(f"Large package list metrics (10k packages): {metrics}")
    
    @pytest.mark.asyncio
    async def test_package_search_performance(self, mock_repository_manager):
        """Test package search performance."""
        manager, package_list = mock_repository_manager
        
        search_terms = ["package-1", "package-100", "package-999", "nonexistent"]
        
        for search_term in search_terms:
            monitor = PerformanceMonitor()
            monitor.start()
            
            results = await manager.search_packages(search_term)
            
            metrics = monitor.stop()
            
            # Search should be fast even with large dataset
            assert metrics['duration'] < 0.5  # Under 500ms
            
            if search_term != "nonexistent":
                assert len(results) > 0
            
            print(f"Search '{search_term}' metrics: {metrics}, results: {len(results)}")
    
    @pytest.mark.asyncio
    async def test_concurrent_repository_access(self, mock_repository_manager):
        """Test concurrent repository access performance."""
        manager, package_list = mock_repository_manager
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Simulate concurrent access patterns
        tasks = []
        
        # Multiple get_packages calls
        for _ in range(5):
            tasks.append(manager.get_packages("test_repo"))
        
        # Multiple search calls
        for term in ["package", "test", "category"]:
            tasks.append(manager.search_packages(term))
        
        # Multiple get_package_info calls
        for i in range(10):
            tasks.append(manager.get_package_info(f"package-{i}", "test_repo"))
        
        results = await asyncio.gather(*tasks)
        
        metrics = monitor.stop()
        
        # All operations should succeed
        assert all(result is not None for result in results[:5])  # get_packages results
        assert all(isinstance(result, list) for result in results[5:8])  # search results
        
        # Concurrent access should be efficient
        assert metrics['duration'] < 3.0  # All operations in under 3 seconds
        
        print(f"Concurrent repository access metrics: {metrics}")


@pytest.mark.slow
@pytest.mark.performance
@pytest.mark.skipif(
    not pytest.importorskip("sentence_transformers", reason="RAG dependencies not available"),
    reason="RAG dependencies not available"
)
class TestRAGIndexerPerformance:
    """Performance tests for RAG indexer."""
    
    @pytest.fixture
    def temp_index_dir(self):
        """Create temporary index directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def large_package_dataset(self):
        """Create large package dataset for indexing."""
        return [
            RepositoryPackage(
                name=f"package-{i}",
                version=f"1.{i % 10}.0",
                description=f"This is test package {i} for category {i % 5}",
                repository_name="test_repo",
                platform="linux",
                category=f"category-{i % 5}",
                tags=[f"tag-{i % 3}", f"feature-{i % 4}"],
                homepage=f"https://example.com/package-{i}"
            )
            for i in range(1000)  # 1k packages for indexing
        ]
    
    @pytest.mark.asyncio
    async def test_indexing_performance(self, temp_index_dir, large_package_dataset):
        """Test RAG indexing performance."""
        with patch('saigen.repositories.indexer.RAG_AVAILABLE', True):
            indexer = RAGIndexer(temp_index_dir)
            
            # Mock the model to avoid downloading
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1] * 384 for _ in range(len(large_package_dataset))]
            
            with patch.object(indexer, '_get_model', return_value=mock_model), \
                 patch('saigen.repositories.indexer.faiss') as mock_faiss:
                
                mock_index = Mock()
                mock_faiss.IndexFlatIP.return_value = mock_index
                mock_faiss.normalize_L2 = Mock()
                mock_faiss.write_index = Mock()
                
                monitor = PerformanceMonitor()
                monitor.start()
                
                await indexer.index_repository_data(large_package_dataset)
                
                metrics = monitor.stop()
                
                # Indexing should complete in reasonable time
                assert metrics['duration'] < 10.0  # Under 10 seconds for 1k packages
                
                # Verify indexing was called
                mock_model.encode.assert_called_once()
                mock_index.add.assert_called_once()
                
                print(f"RAG indexing metrics (1k packages): {metrics}")
    
    @pytest.mark.asyncio
    async def test_search_performance(self, temp_index_dir, large_package_dataset):
        """Test RAG search performance."""
        with patch('saigen.repositories.indexer.RAG_AVAILABLE', True):
            indexer = RAGIndexer(temp_index_dir)
            
            # Mock the model and index
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1] * 384]
            
            mock_index = Mock()
            mock_index.search.return_value = ([[0.9, 0.8, 0.7]], [[0, 1, 2]])
            
            # Set up indexer state
            indexer._package_index = mock_index
            indexer._package_metadata = [
                {
                    'name': pkg.name,
                    'version': pkg.version,
                    'description': pkg.description,
                    'repository_name': pkg.repository_name,
                    'platform': pkg.platform,
                    'category': pkg.category,
                    'tags': pkg.tags,
                    'homepage': pkg.homepage,
                    'maintainer': None,
                    'license': None,
                    'last_updated': None
                }
                for pkg in large_package_dataset[:10]  # Only need a few for search test
            ]
            
            with patch.object(indexer, '_get_model', return_value=mock_model), \
                 patch('saigen.repositories.indexer.faiss') as mock_faiss:
                
                mock_faiss.normalize_L2 = Mock()
                
                search_queries = [
                    "web server",
                    "database management",
                    "development tools",
                    "system utilities"
                ]
                
                for query in search_queries:
                    monitor = PerformanceMonitor()
                    monitor.start()
                    
                    results = await indexer.search_similar_packages(query, limit=5)
                    
                    metrics = monitor.stop()
                    
                    # Search should be very fast
                    assert metrics['duration'] < 0.1  # Under 100ms
                    assert len(results) <= 5
                    
                    print(f"RAG search '{query}' metrics: {metrics}")


@pytest.mark.performance
class TestMemoryLeakDetection:
    """Tests to detect memory leaks in long-running operations."""
    
    @pytest.mark.asyncio
    async def test_repeated_generation_memory_leak(self):
        """Test for memory leaks in repeated generation operations."""
        config = {"llm_providers": {"openai": {"api_key": "test-key"}}}
        
        with patch('saigen.core.generation_engine.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_provider.get_provider_name.return_value = "openai"
            
            async def mock_generate(context):
                return Mock(
                    content="version: '0.2'\nmetadata:\n  name: test",
                    tokens_used=100,
                    cost_estimate=0.001
                )
            
            mock_provider.generate_saidata = mock_generate
            mock_provider_class.return_value = mock_provider
            
            engine = GenerationEngine(config)
            engine._llm_providers["openai"] = mock_provider
            
            # Measure memory before repeated operations
            gc.collect()
            initial_memory = psutil.Process().memory_info().rss
            
            # Perform many generation operations
            for i in range(100):
                request = GenerationRequest(
                    software_name=f"test-{i}",
                    llm_provider=LLMProvider.OPENAI
                )
                
                result = await engine.generate_saidata(request)
                assert result.success
                
                # Force garbage collection every 10 iterations
                if i % 10 == 0:
                    gc.collect()
            
            # Measure memory after operations
            gc.collect()
            final_memory = psutil.Process().memory_info().rss
            
            memory_increase_mb = (final_memory - initial_memory) / 1024 / 1024
            
            # Memory increase should be reasonable (less than 100MB for 100 operations)
            assert memory_increase_mb < 100
            
            print(f"Memory increase after 100 generations: {memory_increase_mb:.2f} MB")
    
    def test_large_data_structure_cleanup(self):
        """Test that large data structures are properly cleaned up."""
        # Create large package list
        large_package_list = [
            RepositoryPackage(
                name=f"package-{i}",
                version="1.0.0",
                description=f"Large description for package {i} " * 100,  # Make it large
                repository_name="test",
                platform="linux"
            )
            for i in range(1000)
        ]
        
        # Measure memory before
        gc.collect()
        initial_memory = psutil.Process().memory_info().rss
        
        # Process the large list
        processed_packages = []
        for pkg in large_package_list:
            # Simulate some processing
            processed_pkg = RepositoryPackage(
                name=pkg.name.upper(),
                version=pkg.version,
                description=pkg.description[:100],  # Truncate
                repository_name=pkg.repository_name,
                platform=pkg.platform
            )
            processed_packages.append(processed_pkg)
        
        # Clear references
        del large_package_list
        del processed_packages
        
        # Force garbage collection
        gc.collect()
        
        # Measure memory after cleanup
        final_memory = psutil.Process().memory_info().rss
        
        memory_delta_mb = (final_memory - initial_memory) / 1024 / 1024
        
        # Memory should not have increased significantly after cleanup
        assert memory_delta_mb < 50  # Less than 50MB residual
        
        print(f"Memory delta after large data processing: {memory_delta_mb:.2f} MB")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([
        __file__,
        "-v",
        "-m", "performance",
        "--tb=short"
    ])