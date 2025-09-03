"""Provider cache management utilities."""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ..models.config import SaiConfig


logger = logging.getLogger(__name__)


class ProviderCache:
    """Manages provider detection cache for performance optimization."""
    
    def __init__(self, config: SaiConfig):
        """Initialize provider cache.
        
        Args:
            config: SAI configuration object
        """
        self.config = config
        self.cache_dir = config.cache_directory
        self.cache_enabled = config.cache_enabled
        self.cache_ttl = getattr(config, 'cache_ttl', 3600)  # Default 1 hour
        self.provider_cache_file = self.cache_dir / "providers.json"
        
        # Ensure cache directory exists
        if self.cache_enabled:
            self._ensure_cache_directory()
    
    def _ensure_cache_directory(self) -> None:
        """Ensure cache directory exists and is writable."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = self.cache_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            
        except (OSError, PermissionError) as e:
            logger.warning(f"Cannot create or write to cache directory {self.cache_dir}: {e}")
            self.cache_enabled = False
    
    def _load_cache_data(self) -> Dict[str, Any]:
        """Load cache data from disk.
        
        Returns:
            Dictionary containing cache data, empty if not found or invalid
        """
        if not self.cache_enabled or not self.provider_cache_file.exists():
            return {}
        
        try:
            with open(self.provider_cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate cache structure
            if not isinstance(data, dict) or 'providers' not in data:
                logger.warning("Invalid cache file structure, ignoring cache")
                return {}
            
            return data
            
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load provider cache: {e}")
            return {}
    
    def _save_cache_data(self, data: Dict[str, Any]) -> None:
        """Save cache data to disk.
        
        Args:
            data: Cache data to save
        """
        if not self.cache_enabled:
            return
        
        try:
            # Add metadata
            data['cache_version'] = '1.0'
            data['last_updated'] = time.time()
            
            # Write atomically by writing to temp file first
            temp_file = self.provider_cache_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Atomic move
            temp_file.replace(self.provider_cache_file)
            
            logger.debug(f"Saved provider cache to {self.provider_cache_file}")
            
        except (OSError, json.JSONEncodeError) as e:
            logger.error(f"Failed to save provider cache: {e}")
    
    def is_cache_valid(self, provider_name: str) -> bool:
        """Check if cached data for a provider is still valid.
        
        Args:
            provider_name: Name of the provider to check
            
        Returns:
            True if cache is valid and not expired
        """
        if not self.cache_enabled:
            return False
        
        cache_data = self._load_cache_data()
        
        if 'providers' not in cache_data or provider_name not in cache_data['providers']:
            return False
        
        provider_cache = cache_data['providers'][provider_name]
        
        # Check if cache entry has timestamp
        if 'cached_at' not in provider_cache:
            return False
        
        # Check if cache is expired
        cached_at = provider_cache['cached_at']
        current_time = time.time()
        
        if current_time - cached_at > self.cache_ttl:
            logger.debug(f"Cache for provider '{provider_name}' has expired")
            return False
        
        return True
    
    def get_cached_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get cached information for a provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Cached provider information if valid, None otherwise
        """
        if not self.is_cache_valid(provider_name):
            return None
        
        cache_data = self._load_cache_data()
        return cache_data['providers'][provider_name].copy()
    
    def update_provider_cache(self, provider_name: str, provider_info: Dict[str, Any]) -> None:
        """Update cache for a specific provider.
        
        Args:
            provider_name: Name of the provider
            provider_info: Provider information to cache
        """
        if not self.cache_enabled:
            return
        
        cache_data = self._load_cache_data()
        
        if 'providers' not in cache_data:
            cache_data['providers'] = {}
        
        # Add timestamp
        provider_info['cached_at'] = time.time()
        cache_data['providers'][provider_name] = provider_info
        
        self._save_cache_data(cache_data)
        logger.debug(f"Updated cache for provider '{provider_name}'")
    
    def clear_provider_cache(self, provider_name: str) -> bool:
        """Clear cache for a specific provider.
        
        Args:
            provider_name: Name of the provider to clear
            
        Returns:
            True if cache was cleared, False if no cache existed
        """
        if not self.cache_enabled:
            return False
        
        cache_data = self._load_cache_data()
        
        if 'providers' not in cache_data or provider_name not in cache_data['providers']:
            return False
        
        del cache_data['providers'][provider_name]
        self._save_cache_data(cache_data)
        
        logger.debug(f"Cleared cache for provider '{provider_name}'")
        return True
    
    def clear_all_provider_cache(self) -> int:
        """Clear all provider cache.
        
        Returns:
            Number of providers that were cached
        """
        if not self.cache_enabled:
            return 0
        
        cache_data = self._load_cache_data()
        
        if 'providers' not in cache_data:
            return 0
        
        cleared_count = len(cache_data['providers'])
        cache_data['providers'] = {}
        self._save_cache_data(cache_data)
        
        logger.debug(f"Cleared cache for {cleared_count} providers")
        return cleared_count
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get comprehensive cache status information.
        
        Returns:
            Dictionary with cache status information
        """
        cache_data = self._load_cache_data()
        
        # Calculate cache size
        cache_size_bytes = 0
        if self.provider_cache_file.exists():
            try:
                cache_size_bytes = self.provider_cache_file.stat().st_size
            except OSError:
                pass
        
        cache_size_mb = cache_size_bytes / (1024 * 1024)
        
        # Get provider information
        cached_providers = []
        if 'providers' in cache_data:
            current_time = time.time()
            
            for provider_name, provider_info in cache_data['providers'].items():
                cached_at = provider_info.get('cached_at', 0)
                age_seconds = current_time - cached_at
                age_hours = age_seconds / 3600
                age_days = age_hours / 24
                
                cached_providers.append({
                    'name': provider_name,
                    'available': provider_info.get('available', False),
                    'cached_at': datetime.fromtimestamp(cached_at).isoformat() if cached_at else None,
                    'age_seconds': age_seconds,
                    'age_hours': age_hours,
                    'age_days': age_days,
                    'expired': age_seconds > self.cache_ttl
                })
        
        # Sort by name
        cached_providers.sort(key=lambda x: x['name'])
        
        return {
            'cache_enabled': self.cache_enabled,
            'cache_directory': str(self.cache_dir),
            'cache_file': str(self.provider_cache_file),
            'cache_ttl_seconds': self.cache_ttl,
            'cache_ttl_hours': self.cache_ttl / 3600,
            'cache_size_bytes': cache_size_bytes,
            'cache_size_mb': cache_size_mb,
            'total_cached_providers': len(cached_providers),
            'cached_providers': cached_providers,
            'last_updated': cache_data.get('last_updated'),
            'cache_version': cache_data.get('cache_version', 'unknown')
        }
    
    def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries.
        
        Returns:
            Number of expired entries removed
        """
        if not self.cache_enabled:
            return 0
        
        cache_data = self._load_cache_data()
        
        if 'providers' not in cache_data:
            return 0
        
        current_time = time.time()
        expired_providers = []
        
        for provider_name, provider_info in cache_data['providers'].items():
            cached_at = provider_info.get('cached_at', 0)
            if current_time - cached_at > self.cache_ttl:
                expired_providers.append(provider_name)
        
        # Remove expired entries
        for provider_name in expired_providers:
            del cache_data['providers'][provider_name]
        
        if expired_providers:
            self._save_cache_data(cache_data)
            logger.debug(f"Cleaned up {len(expired_providers)} expired cache entries")
        
        return len(expired_providers)
    
    def get_all_cached_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached provider information.
        
        Returns:
            Dictionary mapping provider names to their cached information
        """
        cache_data = self._load_cache_data()
        return cache_data.get('providers', {}).copy()