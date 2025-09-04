"""Simple tests for caching utilities."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from sai.utils.cache import ProviderCache
from sai.models.config import SaiConfig


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
        self.cache = ProviderCache(self.config)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_provider_cache_initialization(self):
        """Test provider cache initialization."""
        assert self.cache.cache_dir == self.cache_dir
        assert self.cache.cache_enabled is True
        assert self.cache_dir.exists()
    
    def test_provider_cache_disabled(self):
        """Test provider cache when disabled."""
        config = SaiConfig(cache_enabled=False, cache_directory=self.cache_dir)
        cache = ProviderCache(config)
        
        assert cache.cache_enabled is False
    
    def test_cache_directory_creation(self):
        """Test cache directory creation."""
        new_cache_dir = self.cache_dir / "nested" / "cache"
        config = SaiConfig(cache_enabled=True, cache_directory=new_cache_dir)
        cache = ProviderCache(config)
        
        assert new_cache_dir.exists()
    
    @patch('sai.utils.cache.Path.mkdir')
    def test_cache_directory_creation_failure(self, mock_mkdir):
        """Test handling of cache directory creation failure."""
        mock_mkdir.side_effect = PermissionError("Permission denied")
        
        config = SaiConfig(cache_enabled=True, cache_directory=Path("/invalid/path"))
        cache = ProviderCache(config)
        
        # Should disable cache on failure
        assert cache.cache_enabled is False


if __name__ == "__main__":
    pytest.main([__file__])