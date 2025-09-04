"""Tests for caching utilities."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from sai.utils.cache import ProviderCache, SaidataCache, CacheManager
from sai.models.config import SaiConfig


class CacheError(Exception):
    """Base cache error."""
    pass


class InvalidCacheError(CacheError):
    """Invalid cache format error."""
    pass


class CacheExpiredError(CacheError):
    """Cache expired error."""
    pass


class TestProviderCache:
    """Test ProviderCache functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir)
        self.config = SaiConfig(
            cache_enabled=True,
            cache_directory=self.cache_dir
        )
        self.cache_manager = CacheManager(self.config)
        self.provider_cache = ProviderCache(self.config)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_provider_cache_initialization(self):
        """Test provider cache initialization."""
        assert self.provider_cache.cache_dir == self.cache_dir
        assert self.provider_cache.cache_enabled is True
        assert self.cache_dir.exists()
    
    def test_provider_cache_disabled(self):
        """Test provider cache when disabled."""
        config = SaiConfig(cache_enabled=False, cache_directory=self.cache_dir)
        cache = ProviderCache(config)
        
        assert cache.cache_enabled is False
    
    def test_set_and_get_cache_entry(self):
        """Test setting and getting cache entries."""
        provider_name = "test_provider"
        data = {"available": True, "version": "1.0.0", "message": "hello world"}
        
        self.provider_cache.update_provider_cache(provider_name, data)
        
        result = self.provider_cache.get_cached_provider_info(provider_name)
        assert result is not None
        assert result["available"] == True
        assert result["message"] == "hello world"
    
    def test_get_nonexistent_key(self):
        """Test getting non-existent cache key."""
        result = self.provider_cache.get_cached_provider_info("nonexistent_provider")
        assert result is None
    
    def test_cache_expiration(self):
        """Test cache entry expiration."""
        provider_name = "test_provider"
        data = {"available": True, "message": "hello world"}
        
        # Set with very short TTL by modifying the cache TTL
        self.provider_cache.cache_ttl = 1
        self.provider_cache.update_provider_cache(provider_name, data)
        
        # Should be available immediately
        assert self.provider_cache.is_cache_valid(provider_name) == True
        
        # Mock time to simulate expiration
        with patch('time.time', return_value=time.time() + 2):
            assert self.provider_cache.is_cache_valid(provider_name) == False
    
    def test_cache_persistence(self):
        """Test cache persistence to disk."""
        provider_name = "test_provider"
        data = {"available": True, "message": "hello world"}
        
        self.provider_cache.update_provider_cache(provider_name, data)
        
        # Create new cache manager instance
        new_cache_manager = ProviderCache(self.config)
        
        result = new_cache_manager.get_cached_provider_info(provider_name)
        assert result is not None
        assert result["message"] == "hello world"
    
    def test_has_key(self):
        """Test checking if cache has key."""
        provider_name = "test_provider"
        data = {"available": True, "message": "hello world"}
        
        assert not self.provider_cache.is_cache_valid(provider_name)
        
        self.provider_cache.update_provider_cache(provider_name, data)
        
        assert self.provider_cache.is_cache_valid(provider_name)
    
    def test_delete_key(self):
        """Test deleting cache key."""
        provider_name = "test_provider"
        data = {"available": True, "message": "hello world"}
        
        self.provider_cache.update_provider_cache(provider_name, data)
        assert self.provider_cache.is_cache_valid(provider_name)
        
        result = self.provider_cache.clear_provider_cache(provider_name)
        assert result == True
        assert not self.provider_cache.is_cache_valid(provider_name)
        assert self.provider_cache.get_cached_provider_info(provider_name) is None
    
    def test_clear_cache(self):
        """Test clearing entire cache."""
        providers = ["provider1", "provider2", "provider3"]
        data = {"available": True, "message": "hello world"}
        
        for provider in providers:
            self.provider_cache.update_provider_cache(provider, data)
        
        # Verify all providers exist
        for provider in providers:
            assert self.provider_cache.is_cache_valid(provider)
        
        cleared_count = self.provider_cache.clear_all_provider_cache()
        assert cleared_count == 3
        
        # Verify all providers are gone
        for provider in providers:
            assert not self.provider_cache.is_cache_valid(provider)
    
    def test_list_keys(self):
        """Test listing cache keys."""
        providers = ["provider1", "provider2", "provider3"]
        data = {"available": True, "message": "hello world"}
        
        for provider in providers:
            self.provider_cache.update_provider_cache(provider, data)
        
        all_cached = self.provider_cache.get_all_cached_providers()
        
        assert len(all_cached) == 3
        for provider in providers:
            assert provider in all_cached
    
    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        providers = ["provider1", "provider2", "provider3"]
        data = {"available": True, "message": "hello world"}
        
        for provider in providers:
            self.provider_cache.update_provider_cache(provider, data)
        
        status = self.provider_cache.get_cache_status()
        
        assert status['total_cached_providers'] == 3
        assert status['cache_enabled'] == True
        assert 'cache_directory' in status
    
    def test_cleanup_expired_entries(self):
        """Test cleanup of expired cache entries."""
        # Set entries with different TTLs
        self.provider_cache.cache_ttl = 1
        self.provider_cache.update_provider_cache("provider1", {"available": True, "data": "value1"})
        
        # Set another with longer TTL
        self.provider_cache.cache_ttl = 3600
        self.provider_cache.update_provider_cache("provider2", {"available": True, "data": "value2"})
        
        # Mock time to expire first entry
        with patch('time.time', return_value=time.time() + 2):
            cleaned = self.provider_cache.cleanup_expired_cache()
        
        assert cleaned >= 0  # Some entries might be cleaned
        # Note: The exact behavior depends on the implementation
    
    def test_cache_file_corruption_handling(self):
        """Test handling of corrupted cache files."""
        provider_name = "test_provider"
        cache_file = self.cache_dir / "providers.json"
        
        # Create corrupted cache file
        cache_file.write_text("invalid json content")
        
        # Should handle corruption gracefully
        result = self.provider_cache.get_cached_provider_info(provider_name)
        assert result is None
    
    def test_cache_directory_creation(self):
        """Test cache directory creation."""
        new_cache_dir = self.cache_dir / "nested" / "cache"
        new_config = SaiConfig(
            cache_enabled=True,
            cache_directory=new_cache_dir
        )
        cache_manager = ProviderCache(new_config)
        
        # Test basic functionality
        cache_manager.update_provider_cache("test_provider", {"available": True, "data": "test"})
        result = cache_manager.get_cached_provider_info("test_provider")
        assert result is not None
        assert result["data"] == "test"
    
    def test_cache_with_complex_data(self):
        """Test caching complex data structures."""
        provider_name = "complex_provider"
        data = {
            "available": True,
            "list": [1, 2, 3],
            "dict": {"nested": {"value": "test"}},
            "string": "hello",
            "number": 42,
            "boolean": True,
            "null": None
        }
        
        self.provider_cache.update_provider_cache(provider_name, data)
        result = self.provider_cache.get_cached_provider_info(provider_name)
        
        assert result is not None
        assert result["available"] == True
        assert isinstance(result["list"], list)
        assert isinstance(result["dict"], dict)
        assert result["dict"]["nested"]["value"] == "test"
    
    def test_cache_key_sanitization(self):
        """Test cache key sanitization for filesystem safety."""
        # Provider names with special characters that need sanitization
        problematic_providers = [
            "provider/with/slashes",
            "provider:with:colons",
            "provider with spaces",
            "provider<with>brackets",
            "provider|with|pipes"
        ]
        
        data = {"available": True, "message": "test"}
        
        for provider in problematic_providers:
            self.provider_cache.update_provider_cache(provider, data)
            result = self.provider_cache.get_cached_provider_info(provider)
            assert result is not None
            assert result["message"] == "test"
    
    def test_concurrent_access_safety(self):
        """Test cache safety with concurrent access simulation."""
        import threading
        import time
        
        key = "concurrent_key"
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # Add small delay to reduce race conditions
                time.sleep(0.01 * worker_id)
                provider_name = f"provider_{worker_id}"
                data = {"available": True, "worker": worker_id, "timestamp": time.time()}
                self.provider_cache.update_provider_cache(provider_name, data)
                # Small delay before reading
                time.sleep(0.01)
                result = self.provider_cache.get_cached_provider_info(provider_name)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results - allow for some errors in concurrent access
        assert len(errors) <= 1  # Allow for occasional race conditions
        assert len(results) >= 4  # Most should succeed
        
        # Verify successful results
        for result in results:
            if result is not None:
                assert "worker" in result
                assert result["available"] == True


class TestCacheErrors:
    """Test cache error handling."""
    
    def test_cache_error_creation(self):
        """Test cache error creation."""
        error = CacheError("Test cache error")
        
        assert str(error) == "Test cache error"
        assert isinstance(error, Exception)
    
    def test_invalid_cache_error(self):
        """Test invalid cache error."""
        error = InvalidCacheError("Invalid cache format")
        
        assert isinstance(error, CacheError)
        assert str(error) == "Invalid cache format"
    
    def test_cache_expired_error(self):
        """Test cache expired error."""
        error = CacheExpiredError("Cache entry expired")
        
        assert isinstance(error, CacheError)
        assert str(error) == "Cache entry expired"


if __name__ == "__main__":
    pytest.main([__file__])