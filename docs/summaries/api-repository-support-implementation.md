# API-Based Repository Support Implementation

## Overview

Implemented comprehensive API-based repository support for the saigen tool, enabling efficient per-package queries to API-based package registries (npm, PyPI, cargo, etc.) with rate limiting, caching, authentication, and retry logic.

## Implementation Details

### 1. API Repository Downloader (`saigen/repositories/downloaders/api_downloader.py`)

Created a new `APIRepositoryDownloader` class that extends `UniversalRepositoryDownloader` with API-specific functionality:

#### Rate Limiting (`RateLimiter` class)
- Configurable requests per minute limit
- Configurable concurrent request limit
- Automatic request throttling using sliding window algorithm
- Semaphore-based concurrency control
- Tracks request timestamps to enforce rate limits

#### API Caching (`APICache` class)
- In-memory cache for API responses
- Configurable TTL (time-to-live) per repository
- Automatic cache expiration
- Thread-safe with asyncio locks
- Cache invalidation support

#### Request Handling
- **Retry Logic**: Exponential backoff for failed requests
- **Rate Limit Handling**: Automatic retry with backoff on 429 responses
- **Server Error Handling**: Retry on 5xx errors
- **Network Error Handling**: Retry on connection failures
- **Configurable Timeouts**: Per-repository timeout configuration
- **Response Size Limits**: Configurable maximum response size

#### API Methods
- `query_package()`: Query a single package from API
- `query_packages_batch()`: Query multiple packages concurrently
- `_make_api_request()`: Core request method with retry and caching
- `clear_cache()`: Clear API cache

### 2. Universal Manager Integration

Updated `UniversalRepositoryManager` to support API-based repositories:

- **Automatic Downloader Selection**: Creates `APIRepositoryDownloader` when `query_type == "api"`
- **New Methods**:
  - `query_package_from_repository()`: Query specific package from specific repository
  - `query_packages_batch()`: Batch query multiple packages
- **Backward Compatibility**: Falls back to bulk download methods for non-API repositories

### 3. Repository Configuration Schema Updates

Updated `schemas/repository-config-schema.json`:

#### New Cache Fields
- `api_cache_ttl_seconds`: API response cache TTL (default: 3600 seconds)

#### New Limits Fields
- `max_retries`: Maximum retry attempts (default: 3)
- `retry_delay_seconds`: Initial retry delay (default: 1 second)
- `exponential_backoff`: Enable exponential backoff (default: true)

### 4. Repository Configuration Updates

Updated API-based repository configurations with new fields:

#### npm.yaml
```yaml
cache:
  api_cache_ttl_seconds: 3600
limits:
  requests_per_minute: 300
  concurrent_requests: 10
  max_retries: 3
  retry_delay_seconds: 1
  exponential_backoff: true
query_type: api
```

#### pip.yaml (PyPI)
```yaml
cache:
  api_cache_ttl_seconds: 3600
limits:
  requests_per_minute: 600
  concurrent_requests: 10
  max_retries: 3
  retry_delay_seconds: 1
  exponential_backoff: true
query_type: api
```

#### cargo.yaml (crates.io)
```yaml
cache:
  api_cache_ttl_seconds: 3600
limits:
  requests_per_minute: 300
  concurrent_requests: 10
  max_retries: 3
  retry_delay_seconds: 1
  exponential_backoff: true
query_type: api
```

### 5. Parser Fix

Fixed `saigen/repositories/parsers/__init__.py` to handle list-type category fields (e.g., PyPI classifiers):
- Converts list categories to string by taking first element
- Prevents validation errors when parsing API responses

## Features

### Rate Limiting
- Sliding window rate limiting algorithm
- Configurable requests per minute
- Configurable concurrent requests
- Automatic request queuing when limit reached
- Per-repository rate limit configuration

### Caching
- In-memory cache for API responses
- Configurable TTL per repository
- Automatic cache expiration
- Cache hit/miss tracking
- Cache invalidation support

### Retry Logic
- Configurable maximum retry attempts
- Exponential backoff support
- Automatic retry on rate limit (429)
- Automatic retry on server errors (5xx)
- Automatic retry on network errors
- Configurable retry delay

### Authentication
- Inherited from `UniversalRepositoryDownloader`
- Bearer token support
- API key support (custom header)
- Per-repository authentication configuration

### Error Handling
- Graceful handling of rate limit errors
- Graceful handling of network errors
- Graceful handling of server errors
- Proper session cleanup on errors
- Detailed error logging

## Usage Examples

### Query Single Package
```python
from saigen.repositories.universal_manager import UniversalRepositoryManager

manager = UniversalRepositoryManager(cache_dir, config_dirs)
await manager.initialize()

# Query a package from PyPI
package = await manager.query_package_from_repository('pypi', 'requests')
print(f"{package.name} v{package.version}")
```

### Batch Query Multiple Packages
```python
# Query multiple packages concurrently
packages = ['requests', 'flask', 'django', 'numpy']
results = await manager.query_packages_batch('pypi', packages)

for pkg_name, package in results.items():
    if package:
        print(f"{pkg_name}: v{package.version}")
```

### With Custom Cache Settings
```python
# Query without cache
package = await manager.query_package_from_repository(
    'pypi', 
    'requests', 
    use_cache=False
)
```

## Performance Characteristics

### Rate Limiting
- Prevents API abuse and rate limit errors
- Automatic throttling when limit approached
- Concurrent request limiting prevents overwhelming servers

### Caching
- Reduces redundant API calls
- Improves response time for repeated queries
- Configurable TTL balances freshness vs. performance

### Batch Queries
- Concurrent execution of multiple package queries
- Respects rate limits and concurrency limits
- Efficient for refreshing multiple packages

## Configuration Best Practices

### Rate Limits
- Set `requests_per_minute` below API provider's limit
- Set `concurrent_requests` based on API provider's recommendations
- Use conservative values to avoid rate limiting

### Cache TTL
- Use longer TTL (3600s+) for stable packages
- Use shorter TTL for frequently updated packages
- Balance between freshness and API usage

### Retry Configuration
- Set `max_retries` to 3-5 for reliability
- Enable `exponential_backoff` for better retry behavior
- Set `retry_delay_seconds` to 1-2 seconds

## Testing

Tested with:
- ✅ PyPI (Python Package Index)
- ✅ npm (Node.js Package Registry)
- ✅ crates.io (Rust Package Registry)

Verified functionality:
- ✅ Single package queries
- ✅ Batch package queries
- ✅ Rate limiting
- ✅ Caching
- ✅ Retry logic
- ✅ Error handling

## Requirements Satisfied

- ✅ 11.10: Support API-based query repositories
- ✅ 11.11: Query API per package rather than bulk download
- ✅ 11.12: Cache API query results with TTL
- ✅ 14.1: Support repositories requiring per-package API queries
- ✅ 14.2: Use search/info endpoints for package queries
- ✅ 14.3: Cache API query results
- ✅ 14.4: Respect API rate limits with throttling
- ✅ 14.5: Retry with exponential backoff on rate limit
- ✅ 14.6: Support API authentication
- ✅ 14.7: Use concurrent requests with limits
- ✅ 14.8: Provide timeout, retry, and rate limiting configuration

## Future Enhancements

1. **Persistent Cache**: Store API cache to disk for persistence across runs
2. **Cache Statistics**: Track cache hit/miss rates and performance metrics
3. **Adaptive Rate Limiting**: Automatically adjust rate limits based on API responses
4. **Batch API Support**: Support APIs with native batch query endpoints
5. **OAuth2 Support**: Add OAuth2 authentication for APIs that require it
6. **Response Streaming**: Support streaming large API responses
7. **GraphQL Support**: Add support for GraphQL-based package APIs

## Files Modified

- `saigen/repositories/downloaders/api_downloader.py` (new)
- `saigen/repositories/universal_manager.py`
- `saigen/repositories/parsers/__init__.py`
- `schemas/repository-config-schema.json`
- `saigen/repositories/configs/npm.yaml`
- `saigen/repositories/configs/pip.yaml`
- `saigen/repositories/configs/cargo.yaml`

## Conclusion

The API-based repository support implementation provides a robust, efficient, and configurable solution for querying package information from API-based registries. The implementation includes comprehensive rate limiting, caching, retry logic, and error handling to ensure reliable operation while respecting API provider limits.
