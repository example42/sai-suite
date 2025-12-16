"""API-based repository downloader with rate limiting and caching."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from saigen.models.repository import RepositoryInfo, RepositoryPackage
from saigen.repositories.downloaders.universal import UniversalRepositoryDownloader
from saigen.utils.errors import RepositoryError

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for API requests with exponential backoff."""
    
    def __init__(self, requests_per_minute: int = 60, concurrent_requests: int = 5):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute
            concurrent_requests: Maximum concurrent requests
        """
        self.requests_per_minute = requests_per_minute
        self.concurrent_requests = concurrent_requests
        self.semaphore = asyncio.Semaphore(concurrent_requests)
        self.request_times: List[float] = []
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to make a request, waiting if necessary."""
        async with self.semaphore:
            async with self.lock:
                now = time.time()
                
                # Remove requests older than 1 minute
                cutoff = now - 60
                self.request_times = [t for t in self.request_times if t > cutoff]
                
                # Check if we've hit the rate limit
                if len(self.request_times) >= self.requests_per_minute:
                    # Calculate wait time until oldest request expires
                    oldest = self.request_times[0]
                    wait_time = 60 - (now - oldest)
                    
                    if wait_time > 0:
                        logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                        await asyncio.sleep(wait_time)
                        now = time.time()
                        
                        # Clean up again after waiting
                        cutoff = now - 60
                        self.request_times = [t for t in self.request_times if t > cutoff]
                
                # Record this request
                self.request_times.append(now)


class APICache:
    """Simple in-memory cache for API responses."""
    
    def __init__(self, ttl_seconds: int = 3600):
        """Initialize cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, tuple[Any, datetime]] = {}
        self.lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self.lock:
            if key in self.cache:
                value, expires_at = self.cache[key]
                if datetime.utcnow() < expires_at:
                    return value
                else:
                    # Remove expired entry
                    del self.cache[key]
            return None
    
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL."""
        async with self.lock:
            expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
            self.cache[key] = (value, expires_at)
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self.lock:
            self.cache.clear()
    
    async def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry."""
        async with self.lock:
            if key in self.cache:
                del self.cache[key]


class APIRepositoryDownloader(UniversalRepositoryDownloader):
    """API-based repository downloader with rate limiting and caching."""
    
    def __init__(
        self,
        repository_info: RepositoryInfo,
        config: Dict[str, Any],
        parser_registry: Any,
    ):
        """Initialize API downloader.
        
        Args:
            repository_info: Repository metadata
            config: Full repository configuration from YAML
            parser_registry: Registry of parsing functions
        """
        super().__init__(repository_info, config, parser_registry)
        
        # Initialize rate limiter
        requests_per_minute = self.limits_config.get("requests_per_minute", 60)
        concurrent_requests = self.limits_config.get("concurrent_requests", 5)
        self.rate_limiter = RateLimiter(requests_per_minute, concurrent_requests)
        
        # Initialize API cache
        cache_ttl = self.cache_config.get("api_cache_ttl_seconds", 3600)
        self.api_cache = APICache(ttl_seconds=cache_ttl)
        
        # Retry configuration
        self.max_retries = self.limits_config.get("max_retries", 3)
        self.retry_delay = self.limits_config.get("retry_delay_seconds", 1)
        self.exponential_backoff = self.limits_config.get("exponential_backoff", True)
    
    async def _make_api_request(
        self,
        url: str,
        use_cache: bool = True,
        retry_count: int = 0
    ) -> bytes:
        """Make an API request with rate limiting, caching, and retry logic.
        
        Args:
            url: URL to request
            use_cache: Whether to use cached response
            retry_count: Current retry attempt number
            
        Returns:
            Response content as bytes
            
        Raises:
            RepositoryError: If request fails after all retries
        """
        # Check cache first
        if use_cache:
            cached_response = await self.api_cache.get(url)
            if cached_response is not None:
                logger.debug(f"Cache hit for {url}")
                return cached_response
        
        # Acquire rate limit permission
        await self.rate_limiter.acquire()
        
        try:
            session = await self._get_session()
            
            logger.debug(f"API request to: {url}")
            async with session.get(url, ssl=True) as response:
                if response.status == 429:  # Rate limit exceeded
                    # Exponential backoff
                    if retry_count < self.max_retries:
                        delay = self.retry_delay * (2 ** retry_count) if self.exponential_backoff else self.retry_delay
                        logger.warning(f"Rate limit exceeded (429), retrying in {delay}s (attempt {retry_count + 1}/{self.max_retries})")
                        await asyncio.sleep(delay)
                        return await self._make_api_request(url, use_cache=False, retry_count=retry_count + 1)
                    else:
                        raise RepositoryError(f"Rate limit exceeded after {self.max_retries} retries")
                
                if response.status != 200:
                    # Retry on server errors (5xx)
                    if 500 <= response.status < 600 and retry_count < self.max_retries:
                        delay = self.retry_delay * (2 ** retry_count) if self.exponential_backoff else self.retry_delay
                        logger.warning(f"Server error {response.status}, retrying in {delay}s (attempt {retry_count + 1}/{self.max_retries})")
                        await asyncio.sleep(delay)
                        return await self._make_api_request(url, use_cache=False, retry_count=retry_count + 1)
                    
                    raise RepositoryError(f"HTTP {response.status} from {url}")
                
                # Check content length
                max_size_mb = self.limits_config.get("max_response_size_mb", 50)
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                    raise RepositoryError(f"Response too large: {content_length} bytes from {url}")
                
                # Read content
                content = await response.read()
                
                # Cache the response
                if use_cache:
                    await self.api_cache.set(url, content)
                
                return content
                
        except aiohttp.ClientError as e:
            # Retry on network errors
            if retry_count < self.max_retries:
                delay = self.retry_delay * (2 ** retry_count) if self.exponential_backoff else self.retry_delay
                logger.warning(f"Network error: {e}, retrying in {delay}s (attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(delay)
                return await self._make_api_request(url, use_cache=False, retry_count=retry_count + 1)
            else:
                raise RepositoryError(f"Network error after {self.max_retries} retries: {e}")
        
        except Exception as e:
            # Close session on error
            if self._session:
                try:
                    await self._session.close()
                    self._session = None
                except BaseException:
                    pass
            raise RepositoryError(f"Failed to make API request to {url}: {e}")
    
    async def query_package(
        self,
        package_name: str,
        use_cache: bool = True
    ) -> Optional[RepositoryPackage]:
        """Query API for a specific package.
        
        Args:
            package_name: Name of package to query
            use_cache: Whether to use cached response
            
        Returns:
            RepositoryPackage if found, None otherwise
        """
        info_url = self.endpoints.get("info")
        if not info_url:
            # Fall back to search if no info endpoint
            logger.debug(f"No info endpoint, falling back to search for {package_name}")
            return await self.get_package_details(package_name)
        
        try:
            # Build URL
            url = info_url.replace("{package}", package_name)
            url = url.replace("{query}", package_name)
            
            logger.debug(f"Querying package {package_name} from {url}")
            
            # Make request
            content = await self._make_api_request(url, use_cache=use_cache)
            
            logger.debug(f"Received {len(content)} bytes of content")
            
            # Parse response
            packages = await self._parse_content(content, {})
            
            logger.debug(f"Parsed {len(packages)} packages from response")
            
            # Return first matching package
            for package in packages:
                if package.name.lower() == package_name.lower():
                    logger.debug(f"Found matching package: {package.name} v{package.version}")
                    return package
            
            if packages:
                logger.debug(f"No exact match, returning first package: {packages[0].name}")
                return packages[0]
            else:
                logger.debug(f"No packages found in response")
                return None
            
        except Exception as e:
            logger.error(f"Failed to query package {package_name}: {e}", exc_info=True)
            return None
    
    async def query_packages_batch(
        self,
        package_names: List[str],
        use_cache: bool = True
    ) -> Dict[str, Optional[RepositoryPackage]]:
        """Query API for multiple packages concurrently.
        
        Args:
            package_names: List of package names to query
            use_cache: Whether to use cached responses
            
        Returns:
            Dict mapping package names to RepositoryPackage (or None if not found)
        """
        results = {}
        
        # Create tasks for all packages
        tasks = []
        for package_name in package_names:
            task = asyncio.create_task(
                self.query_package(package_name, use_cache=use_cache),
                name=f"query_{package_name}"
            )
            tasks.append((package_name, task))
        
        # Collect results
        for package_name, task in tasks:
            try:
                package = await task
                results[package_name] = package
            except Exception as e:
                logger.error(f"Failed to query package {package_name}: {e}")
                results[package_name] = None
        
        return results
    
    async def download_package_list(self) -> List[RepositoryPackage]:
        """Download package list - not recommended for API-based repositories.
        
        For API-based repositories, use query_package() or query_packages_batch() instead.
        This method will attempt to use the packages endpoint if available, but may
        return incomplete results or fail for large registries.
        """
        logger.warning(
            f"download_package_list() called on API-based repository {self.repository_info.name}. "
            "Consider using query_package() or query_packages_batch() instead."
        )
        
        packages_url = self.endpoints.get("packages")
        if not packages_url:
            raise RepositoryError(
                f"No packages URL configured for API repository {self.repository_info.name}"
            )
        
        try:
            # Make request with caching
            content = await self._make_api_request(packages_url, use_cache=True)
            
            # Parse content
            packages = await self._parse_content(content, {})
            
            logger.info(f"Downloaded {len(packages)} packages from {self.repository_info.name}")
            return packages
            
        except Exception as e:
            raise RepositoryError(
                f"Failed to download package list from {self.repository_info.name}: {str(e)}"
            )
    
    async def search_package(self, name: str) -> List[RepositoryPackage]:
        """Search for specific package using API."""
        search_url = self.endpoints.get("search")
        
        if search_url:
            try:
                # Build search URL
                url = search_url.replace("{query}", name).replace("{package}", name)
                
                # Make request
                content = await self._make_api_request(url, use_cache=True)
                
                # Parse response
                packages = await self._parse_content(content, {})
                
                # Filter results to match search query
                name_lower = name.lower()
                matching_packages = []
                for package in packages:
                    if name_lower in package.name.lower() or (
                        package.description and name_lower in package.description.lower()
                    ):
                        matching_packages.append(package)
                
                return matching_packages
                
            except Exception as e:
                logger.debug(f"Search failed for {name}: {e}")
                return []
        
        # Fall back to info endpoint
        package = await self.query_package(name)
        return [package] if package else []
    
    async def get_package_details(
        self,
        name: str,
        version: Optional[str] = None
    ) -> Optional[RepositoryPackage]:
        """Get detailed information for a specific package."""
        # Try info endpoint first
        package = await self.query_package(name)
        if package:
            if version is None or package.version == version:
                return package
        
        # Fall back to search
        packages = await self.search_package(name)
        
        # Find exact match
        for package in packages:
            if package.name.lower() == name.lower():
                if version is None or package.version == version:
                    return package
        
        # Return first match if no exact match
        return packages[0] if packages else None
    
    async def clear_cache(self) -> None:
        """Clear the API cache."""
        await self.api_cache.clear()
        logger.info(f"Cleared API cache for {self.repository_info.name}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Clear cache on exit
        await self.api_cache.clear()
        await super().__aexit__(exc_type, exc_val, exc_tb)
