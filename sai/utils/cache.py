"""Cache management utilities for providers and saidata."""

import json
import logging
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
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


class SaidataCache:
    """Manages saidata file parsing cache for performance optimization."""
    
    def __init__(self, config: SaiConfig):
        """Initialize saidata cache.
        
        Args:
            config: SAI configuration object
        """
        self.config = config
        self.cache_dir = config.cache_directory
        self.cache_enabled = config.cache_enabled
        self.cache_ttl = getattr(config, 'cache_ttl', 3600)  # Default 1 hour
        self.saidata_cache_file = self.cache_dir / "saidata.json"
        
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
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Get hash of file content for cache invalidation.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 hash of file content
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()
        except (OSError, IOError):
            return ""
    
    def _get_cache_key(self, software_name: str, file_paths: List[Path]) -> str:
        """Generate cache key for saidata.
        
        Args:
            software_name: Name of the software
            file_paths: List of saidata file paths used
            
        Returns:
            Cache key string
        """
        # Create a deterministic key based on software name and file paths
        path_str = "|".join(str(p) for p in sorted(file_paths))
        key_content = f"{software_name}:{path_str}"
        return hashlib.sha256(key_content.encode()).hexdigest()
    
    def _load_cache_data(self) -> Dict[str, Any]:
        """Load saidata cache data from disk.
        
        Returns:
            Dictionary containing cache data, empty if not found or invalid
        """
        if not self.cache_enabled or not self.saidata_cache_file.exists():
            return {}
        
        try:
            with open(self.saidata_cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate cache structure
            if not isinstance(data, dict) or 'saidata' not in data:
                logger.warning("Invalid saidata cache file structure, ignoring cache")
                return {}
            
            return data
            
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load saidata cache: {e}")
            return {}
    
    def _save_cache_data(self, data: Dict[str, Any]) -> None:
        """Save saidata cache data to disk.
        
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
            temp_file = self.saidata_cache_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Atomic move
            temp_file.replace(self.saidata_cache_file)
            
            logger.debug(f"Saved saidata cache to {self.saidata_cache_file}")
            
        except (OSError, json.JSONEncodeError) as e:
            logger.error(f"Failed to save saidata cache: {e}")
    
    def is_cache_valid(self, software_name: str, file_paths: List[Path]) -> bool:
        """Check if cached saidata is still valid.
        
        Args:
            software_name: Name of the software
            file_paths: List of saidata file paths
            
        Returns:
            True if cache is valid and not expired
        """
        if not self.cache_enabled:
            return False
        
        cache_key = self._get_cache_key(software_name, file_paths)
        cache_data = self._load_cache_data()
        
        if 'saidata' not in cache_data or cache_key not in cache_data['saidata']:
            return False
        
        cached_entry = cache_data['saidata'][cache_key]
        
        # Check if cache entry has timestamp
        if 'cached_at' not in cached_entry:
            return False
        
        # Check if cache is expired
        cached_at = cached_entry['cached_at']
        current_time = time.time()
        
        if current_time - cached_at > self.cache_ttl:
            logger.debug(f"Cache for saidata '{software_name}' has expired")
            return False
        
        # Check if any source files have been modified
        cached_file_hashes = cached_entry.get('file_hashes', {})
        for file_path in file_paths:
            file_path_str = str(file_path)
            current_hash = self._get_file_hash(file_path)
            cached_hash = cached_file_hashes.get(file_path_str, "")
            
            if current_hash != cached_hash:
                logger.debug(f"Cache for saidata '{software_name}' invalidated due to file change: {file_path}")
                return False
        
        return True
    
    def get_cached_saidata(self, software_name: str, file_paths: List[Path]) -> Optional[Dict[str, Any]]:
        """Get cached saidata if valid.
        
        Args:
            software_name: Name of the software
            file_paths: List of saidata file paths
            
        Returns:
            Cached saidata dictionary if valid, None otherwise
        """
        if not self.is_cache_valid(software_name, file_paths):
            return None
        
        cache_key = self._get_cache_key(software_name, file_paths)
        cache_data = self._load_cache_data()
        
        cached_entry = cache_data['saidata'][cache_key]
        return cached_entry.get('data', {}).copy()
    
    def update_saidata_cache(self, software_name: str, file_paths: List[Path], 
                           saidata: Dict[str, Any]) -> None:
        """Update cache for saidata.
        
        Args:
            software_name: Name of the software
            file_paths: List of saidata file paths used
            saidata: Parsed and validated saidata dictionary
        """
        if not self.cache_enabled:
            return
        
        cache_key = self._get_cache_key(software_name, file_paths)
        cache_data = self._load_cache_data()
        
        if 'saidata' not in cache_data:
            cache_data['saidata'] = {}
        
        # Calculate file hashes for invalidation
        file_hashes = {}
        for file_path in file_paths:
            file_hashes[str(file_path)] = self._get_file_hash(file_path)
        
        # Store cache entry
        cache_data['saidata'][cache_key] = {
            'software_name': software_name,
            'file_paths': [str(p) for p in file_paths],
            'file_hashes': file_hashes,
            'data': saidata,
            'cached_at': time.time()
        }
        
        self._save_cache_data(cache_data)
        logger.debug(f"Updated saidata cache for '{software_name}'")
    
    def clear_saidata_cache(self, software_name: Optional[str] = None) -> int:
        """Clear saidata cache.
        
        Args:
            software_name: Name of specific software to clear, or None for all
            
        Returns:
            Number of cache entries cleared
        """
        if not self.cache_enabled:
            return 0
        
        cache_data = self._load_cache_data()
        
        if 'saidata' not in cache_data:
            return 0
        
        if software_name is None:
            # Clear all saidata cache
            cleared_count = len(cache_data['saidata'])
            cache_data['saidata'] = {}
        else:
            # Clear cache for specific software
            cleared_count = 0
            keys_to_remove = []
            
            for cache_key, cached_entry in cache_data['saidata'].items():
                if cached_entry.get('software_name') == software_name:
                    keys_to_remove.append(cache_key)
                    cleared_count += 1
            
            for key in keys_to_remove:
                del cache_data['saidata'][key]
        
        if cleared_count > 0:
            self._save_cache_data(cache_data)
            logger.debug(f"Cleared {cleared_count} saidata cache entries")
        
        return cleared_count
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get comprehensive saidata cache status information.
        
        Returns:
            Dictionary with cache status information
        """
        cache_data = self._load_cache_data()
        
        # Calculate cache size
        cache_size_bytes = 0
        if self.saidata_cache_file.exists():
            try:
                cache_size_bytes = self.saidata_cache_file.stat().st_size
            except OSError:
                pass
        
        cache_size_mb = cache_size_bytes / (1024 * 1024)
        
        # Get saidata information
        cached_saidata = []
        if 'saidata' in cache_data:
            current_time = time.time()
            
            for cache_key, cached_entry in cache_data['saidata'].items():
                cached_at = cached_entry.get('cached_at', 0)
                age_seconds = current_time - cached_at
                age_hours = age_seconds / 3600
                age_days = age_hours / 24
                
                cached_saidata.append({
                    'software_name': cached_entry.get('software_name', 'unknown'),
                    'file_paths': cached_entry.get('file_paths', []),
                    'cached_at': datetime.fromtimestamp(cached_at).isoformat() if cached_at else None,
                    'age_seconds': age_seconds,
                    'age_hours': age_hours,
                    'age_days': age_days,
                    'expired': age_seconds > self.cache_ttl,
                    'cache_key': cache_key
                })
        
        # Sort by software name
        cached_saidata.sort(key=lambda x: x['software_name'])
        
        return {
            'cache_enabled': self.cache_enabled,
            'cache_directory': str(self.cache_dir),
            'cache_file': str(self.saidata_cache_file),
            'cache_ttl_seconds': self.cache_ttl,
            'cache_ttl_hours': self.cache_ttl / 3600,
            'cache_size_bytes': cache_size_bytes,
            'cache_size_mb': cache_size_mb,
            'total_cached_saidata': len(cached_saidata),
            'cached_saidata': cached_saidata,
            'last_updated': cache_data.get('last_updated'),
            'cache_version': cache_data.get('cache_version', 'unknown')
        }
    
    def cleanup_expired_cache(self) -> int:
        """Remove expired saidata cache entries.
        
        Returns:
            Number of expired entries removed
        """
        if not self.cache_enabled:
            return 0
        
        cache_data = self._load_cache_data()
        
        if 'saidata' not in cache_data:
            return 0
        
        current_time = time.time()
        expired_keys = []
        
        for cache_key, cached_entry in cache_data['saidata'].items():
            cached_at = cached_entry.get('cached_at', 0)
            if current_time - cached_at > self.cache_ttl:
                expired_keys.append(cache_key)
        
        # Remove expired entries
        for cache_key in expired_keys:
            del cache_data['saidata'][cache_key]
        
        if expired_keys:
            self._save_cache_data(cache_data)
            logger.debug(f"Cleaned up {len(expired_keys)} expired saidata cache entries")
        
        return len(expired_keys)


class CacheManager:
    """Unified cache manager for both provider and saidata caches."""
    
    def __init__(self, config: Union[SaiConfig, Path]):
        """Initialize cache manager.
        
        Args:
            config: SAI configuration object or cache directory path
        """
        if isinstance(config, Path):
            # Handle case where path is passed directly (for tests)
            from ..models.config import SaiConfig
            self.config = SaiConfig(cache_directory=config, cache_enabled=True)
        else:
            self.config = config
        self.provider_cache = ProviderCache(self.config)
        self.saidata_cache = SaidataCache(self.config)
        
        # Generic cache interface for tests
        self._generic_cache = {}
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Set a cache entry (generic interface for tests).
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (optional)
        """
        self._generic_cache[key] = {
            'data': data,
            'cached_at': time.time(),
            'ttl': ttl or self.config.cache_ttl
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get a cache entry (generic interface for tests).
        
        Args:
            key: Cache key
            
        Returns:
            Cached data if valid, None otherwise
        """
        if key not in self._generic_cache:
            return None
        
        entry = self._generic_cache[key]
        cached_at = entry['cached_at']
        ttl = entry['ttl']
        
        if time.time() - cached_at > ttl:
            del self._generic_cache[key]
            return None
        
        return entry['data']
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all caches.
        
        Returns:
            Dictionary with status of all cache systems
        """
        provider_status = self.provider_cache.get_cache_status()
        saidata_status = self.saidata_cache.get_cache_status()
        
        # Calculate total cache size
        total_size_bytes = provider_status['cache_size_bytes'] + saidata_status['cache_size_bytes']
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        return {
            'cache_enabled': self.config.cache_enabled,
            'cache_directory': str(self.config.cache_directory),
            'cache_ttl_seconds': self.config.cache_ttl,
            'cache_ttl_hours': self.config.cache_ttl / 3600,
            'total_cache_size_bytes': total_size_bytes,
            'total_cache_size_mb': total_size_mb,
            'provider_cache': provider_status,
            'saidata_cache': saidata_status
        }
    
    def cleanup_all_expired(self) -> Dict[str, int]:
        """Clean up expired entries from all caches.
        
        Returns:
            Dictionary with cleanup results for each cache type
        """
        provider_cleaned = self.provider_cache.cleanup_expired_cache()
        saidata_cleaned = self.saidata_cache.cleanup_expired_cache()
        
        return {
            'provider_cache_cleaned': provider_cleaned,
            'saidata_cache_cleaned': saidata_cleaned,
            'total_cleaned': provider_cleaned + saidata_cleaned
        }
    
    def clear_all_caches(self) -> Dict[str, int]:
        """Clear all cache data.
        
        Returns:
            Dictionary with clear results for each cache type
        """
        provider_cleared = self.provider_cache.clear_all_provider_cache()
        saidata_cleared = self.saidata_cache.clear_saidata_cache()
        
        return {
            'provider_cache_cleared': provider_cleared,
            'saidata_cache_cleared': saidata_cleared,
            'total_cleared': provider_cleared + saidata_cleared
        }