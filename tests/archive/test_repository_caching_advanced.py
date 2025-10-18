"""Advanced tests for repository caching and cleanup logic."""

import json
import shutil
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from sai.core.repository_cache import RepositoryCache, RepositoryMetadata
from sai.models.config import SaiConfig


class TestRepositoryCacheAdvanced:
    """Advanced tests for repository cache functionality."""

    @pytest.fixture
    def temp_dir(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def config(self, temp_dir):
        return SaiConfig(
            cache_directory=temp_dir / "cache",
            cache_enabled=True,
            saidata_update_interval=3600,
            saidata_repository_cache_dir=temp_dir / "cache" / "repositories",
        )

    @pytest.fixture
    def cache(self, config):
        return RepositoryCache(config)

    def test_cache_eviction_policies(self, cache, temp_dir):
        """Test different cache eviction policies."""
        # Configure cache with size limit
        cache.max_cache_size_mb = 5  # 5MB limit
        cache.eviction_policy = "lru"  # Least Recently Used

        # Create repositories with different access patterns
        repos = []
        for i in range(5):
            url = f"https://github.com/test/repo{i}"
            repo_path = cache._get_repository_path(url, "main")
            repo_path.mkdir(parents=True)

            # Create 2MB file in each repo
            large_file = repo_path / "large_file.txt"
            large_file.write_text("x" * 2000000)

            cache.mark_repository_updated(url, "main")
            repos.append((url, repo_path))

        # Access some repositories to establish LRU order
        cache.mark_repository_accessed(repos[0][0], "main")  # Most recent
        cache.mark_repository_accessed(repos[1][0], "main")
        time.sleep(0.1)  # Ensure different timestamps
        cache.mark_repository_accessed(repos[0][0], "main")  # Most recent again

        # Trigger eviction
        cleaned = cache.enforce_cache_size_limits()

        # Should have evicted least recently used repositories
        assert cleaned > 0

        # Most recently used should still exist
        assert repos[0][1].exists()

        # Some least recently used should be evicted
        evicted_count = sum(1 for _, path in repos if not path.exists())
        assert evicted_count > 0

    def test_cache_warming_strategies(self, cache):
        """Test cache warming strategies."""
        # Define popular repositories for warming
        popular_repos = [
            "https://github.com/example42/saidata",
            "https://github.com/popular/repo1",
            "https://github.com/popular/repo2",
        ]

        # Mock successful repository updates
        with patch.object(cache, "_download_and_cache_repository") as mock_download:
            mock_download.return_value = True

            # Warm cache with popular repositories
            warmed_count = cache.warm_cache(popular_repos)

            assert warmed_count == len(popular_repos)
            assert mock_download.call_count == len(popular_repos)

    def test_cache_statistics_collection(self, cache, temp_dir):
        """Test collection of detailed cache statistics."""
        # Create repositories with different characteristics
        repos_data = [
            ("https://github.com/small/repo", 100000),  # 100KB
            ("https://github.com/medium/repo", 1000000),  # 1MB
            ("https://github.com/large/repo", 5000000),  # 5MB
        ]

        for url, size in repos_data:
            repo_path = cache._get_repository_path(url, "main")
            repo_path.mkdir(parents=True)

            # Create file of specified size
            test_file = repo_path / "data.txt"
            test_file.write_text("x" * size)

            cache.mark_repository_updated(url, "main")

        # Collect statistics
        stats = cache.get_detailed_statistics()

        assert stats["total_repositories"] == 3
        assert stats["total_size_mb"] > 6  # Should be > 6MB total
        assert "size_distribution" in stats
        assert "access_patterns" in stats
        assert "cache_efficiency" in stats

    def test_cache_integrity_verification(self, cache, temp_dir):
        """Test cache integrity verification and repair."""
        # Create repository with metadata
        url = "https://github.com/test/repo"
        repo_path = cache._get_repository_path(url, "main")
        repo_path.mkdir(parents=True)
        (repo_path / "test_file.txt").write_text("test content")

        cache.mark_repository_updated(url, "main")

        # Corrupt the repository (delete file but keep metadata)
        (repo_path / "test_file.txt").unlink()

        # Run integrity check
        integrity_report = cache.verify_cache_integrity()

        assert not integrity_report["is_healthy"]
        assert len(integrity_report["corrupted_repositories"]) == 1
        assert url in integrity_report["corrupted_repositories"][0]["url"]

        # Repair cache
        repaired_count = cache.repair_cache_integrity()
        assert repaired_count == 1

        # Repository should be removed from cache
        assert not cache.is_repository_valid(url, "main")

    def test_cache_compression_optimization(self, cache, temp_dir):
        """Test cache compression optimization."""
        # Create repository with compressible content
        url = "https://github.com/test/repo"
        repo_path = cache._get_repository_path(url, "main")
        repo_path.mkdir(parents=True)

        # Create highly compressible content
        compressible_file = repo_path / "compressible.txt"
        compressible_content = "This is repeated content. " * 10000
        compressible_file.write_text(compressible_content)

        cache.mark_repository_updated(url, "main")

        # Enable compression
        original_size = cache._calculate_directory_stats(repo_path)[0]

        compressed_size = cache.compress_repository(url, "main")

        # Should achieve significant compression
        assert compressed_size < original_size * 0.5  # At least 50% compression

    def test_cache_synchronization_across_processes(self, cache, temp_dir):
        """Test cache synchronization across multiple processes."""
        import multiprocessing

        def cache_operation(cache_dir, result_queue):
            """Function to run in separate process."""
            try:
                # Create new cache instance in separate process
                config = SaiConfig(
                    cache_directory=cache_dir, cache_enabled=True, saidata_update_interval=3600
                )
                process_cache = RepositoryCache(config)

                # Perform cache operation
                url = "https://github.com/test/multiprocess"
                process_cache.mark_repository_updated(url, "main")
                is_valid = process_cache.is_repository_valid(url, "main")

                result_queue.put(is_valid)
            except Exception:
                result_queue.put(False)

        # Start process
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=cache_operation, args=(cache.cache_dir, result_queue)
        )
        process.start()
        process.join()

        # Check result
        result = result_queue.get()
        assert result is True

        # Verify cache is synchronized in main process
        assert cache.is_repository_valid("https://github.com/test/multiprocess", "main")

    def test_cache_performance_monitoring(self, cache):
        """Test cache performance monitoring and metrics."""
        # Perform various cache operations
        operations = [
            ("mark_updated", "https://github.com/test/repo1", "main"),
            ("is_valid", "https://github.com/test/repo1", "main"),
            ("mark_updated", "https://github.com/test/repo2", "main"),
            ("is_valid", "https://github.com/test/repo2", "main"),
            ("is_valid", "https://github.com/test/nonexistent", "main"),
        ]

        # Enable performance monitoring
        cache.enable_performance_monitoring()

        for operation, url, branch in operations:
            if operation == "mark_updated":
                cache.mark_repository_updated(url, branch)
            elif operation == "is_valid":
                cache.is_repository_valid(url, branch)

        # Get performance metrics
        metrics = cache.get_performance_metrics()

        assert "total_operations" in metrics
        assert "cache_hit_rate" in metrics
        assert "average_operation_time" in metrics
        assert metrics["total_operations"] == len(operations)
        assert 0 <= metrics["cache_hit_rate"] <= 1

    def test_cache_backup_and_restore(self, cache, temp_dir):
        """Test cache backup and restore functionality."""
        # Create repositories in cache
        repos = [
            "https://github.com/test/repo1",
            "https://github.com/test/repo2",
            "https://github.com/test/repo3",
        ]

        for url in repos:
            repo_path = cache._get_repository_path(url, "main")
            repo_path.mkdir(parents=True)
            (repo_path / "data.txt").write_text(f"data for {url}")
            cache.mark_repository_updated(url, "main")

        # Create backup
        backup_path = temp_dir / "cache_backup"
        backup_result = cache.create_backup(backup_path)

        assert backup_result.success
        assert backup_path.exists()
        assert (backup_path / "metadata.json").exists()

        # Clear cache
        cache.clear_all_repository_cache()

        # Verify cache is empty
        for url in repos:
            assert not cache.is_repository_valid(url, "main")

        # Restore from backup
        restore_result = cache.restore_from_backup(backup_path)

        assert restore_result.success

        # Verify repositories are restored
        for url in repos:
            assert cache.is_repository_valid(url, "main")

    def test_cache_migration_between_versions(self, cache, temp_dir):
        """Test cache migration between different versions."""
        # Create old version cache structure
        old_metadata = {
            "version": "1.0",
            "repositories": {
                "repo1": {
                    "url": "https://github.com/test/repo1",
                    "branch": "main",
                    "local_path": str(cache.cache_dir / "repo1"),
                    "last_updated": time.time() - 3600,
                    "is_git_repo": True,
                }
            },
        }

        # Write old format metadata
        cache.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        cache.metadata_file.write_text(json.dumps(old_metadata))

        # Create corresponding repository directory
        old_repo_path = cache.cache_dir / "repo1"
        old_repo_path.mkdir(parents=True)
        (old_repo_path / "old_data.txt").write_text("old format data")

        # Trigger migration by loading metadata
        metadata = cache._load_metadata()

        # Should have migrated to new format
        assert len(metadata) > 0
        migrated_repo = list(metadata.values())[0]
        assert isinstance(migrated_repo, RepositoryMetadata)
        assert migrated_repo.url == "https://github.com/test/repo1"
        assert migrated_repo.branch == "main"

    def test_cache_cleanup_strategies(self, cache, temp_dir):
        """Test different cache cleanup strategies."""
        # Create repositories with different ages and sizes
        now = time.time()
        repos_config = [
            ("https://github.com/old/small", now - 86400 * 10, 100000),  # 10 days old, 100KB
            ("https://github.com/old/large", now - 86400 * 8, 5000000),  # 8 days old, 5MB
            ("https://github.com/recent/small", now - 3600, 100000),  # 1 hour old, 100KB
            ("https://github.com/recent/large", now - 7200, 5000000),  # 2 hours old, 5MB
        ]

        for url, timestamp, size in repos_config:
            repo_path = cache._get_repository_path(url, "main")
            repo_path.mkdir(parents=True)

            # Create file of specified size
            data_file = repo_path / "data.txt"
            data_file.write_text("x" * size)

            # Manually set timestamp
            repositories = cache._load_metadata()
            key = cache._get_repository_key(url, "main")
            repositories[key] = RepositoryMetadata(
                url=url,
                branch="main",
                local_path=repo_path,
                last_updated=timestamp,
                is_git_repo=True,
                size_bytes=size,
                file_count=1,
            )
            cache._save_metadata(repositories)

        # Test age-based cleanup
        cleaned_by_age = cache.cleanup_old_repositories(max_age_days=7)
        assert cleaned_by_age == 2  # Should clean 2 old repositories

        # Test size-based cleanup
        cache.max_cache_size_mb = 3  # 3MB limit
        cleaned_by_size = cache.cleanup_by_size()
        assert cleaned_by_size > 0  # Should clean some large repositories

    def test_cache_health_monitoring(self, cache, temp_dir):
        """Test cache health monitoring and alerting."""
        # Create repositories with various health issues
        healthy_repo = cache._get_repository_path("https://github.com/healthy/repo", "main")
        healthy_repo.mkdir(parents=True)
        (healthy_repo / "data.txt").write_text("healthy data")
        cache.mark_repository_updated("https://github.com/healthy/repo", "main")

        # Create corrupted repository (metadata exists but files missing)
        corrupted_repo = cache._get_repository_path("https://github.com/corrupted/repo", "main")
        cache.mark_repository_updated("https://github.com/corrupted/repo", "main")
        # Don't create actual files - this simulates corruption

        # Run health check
        health_report = cache.get_health_report()

        assert "total_repositories" in health_report
        assert "healthy_repositories" in health_report
        assert "corrupted_repositories" in health_report
        assert "warnings" in health_report

        assert health_report["total_repositories"] == 2
        assert health_report["healthy_repositories"] == 1
        assert health_report["corrupted_repositories"] == 1

        # Should have warnings about corrupted repository
        assert len(health_report["warnings"]) > 0

    def test_cache_concurrent_cleanup(self, cache, temp_dir):
        """Test concurrent cleanup operations safety."""
        # Create multiple repositories
        for i in range(10):
            url = f"https://github.com/test/repo{i}"
            repo_path = cache._get_repository_path(url, "main")
            repo_path.mkdir(parents=True)
            (repo_path / "data.txt").write_text(f"data {i}")
            cache.mark_repository_updated(url, "main")

        # Start concurrent cleanup operations
        results = []

        def cleanup_operation():
            try:
                cleaned = cache.cleanup_expired_repositories()
                results.append(cleaned)
            except Exception:
                results.append(-1)  # Error indicator

        threads = []
        for _ in range(3):
            thread = threading.Thread(target=cleanup_operation)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Should handle concurrent cleanup without errors
        assert len(results) == 3
        assert all(result >= 0 for result in results)  # No errors

        # Cache should still be in consistent state
        status = cache.get_cache_status()
        assert isinstance(status["total_repositories"], int)
        assert status["total_repositories"] >= 0
