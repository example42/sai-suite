# API-Based Repository Support

## Problem Statement

Not all package managers provide bulk downloadable package lists. Many modern package registries (npm, pip, cargo, winget, rubygems, maven, nuget) only provide HTTP APIs for querying packages individually.

## Two Repository Types

### Type 1: Bulk Download Repositories

**Characteristics**:
- Download complete package list as a file
- Parse locally
- Cache entire list
- Fast for multiple queries
- Works offline after download

**Examples**: apt, dnf, zypper, pacman, apk, emerge

**Workflow**:
```
1. Download Packages.gz (or equivalent)
2. Decompress and parse
3. Cache entire package list
4. Query locally for any package
```

### Type 2: API-Based Repositories

**Characteristics**:
- Query per package via HTTP API
- No bulk download available
- Cache individual results
- Requires network for each query
- Subject to rate limits
- May require authentication

**Examples**: npm, pip, cargo, winget, rubygems, maven, nuget

**Workflow**:
```
1. Query API for specific package: GET /package/{name}
2. Parse JSON/XML response
3. Cache individual result
4. Repeat for each package
```

## Configuration Differences

### Bulk Download Repository Example (apt)

```yaml
- name: "apt-ubuntu-jammy"
  type: "apt"
  query_type: "bulk_download"
  platform: "linux"
  distribution: ["ubuntu"]
  os_version: "22.04"
  
  endpoints:
    packages: "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-{arch}/Packages.gz"
  
  parsing:
    format: "debian_packages"
    compression: "gzip"
    encoding: "utf-8"
  
  cache:
    ttl_hours: 24  # Cache full list for 24 hours
    max_size_mb: 100
  
  limits:
    timeout_seconds: 300
```

### API-Based Repository Example (npm)

```yaml
- name: "npm-registry"
  type: "npm"
  query_type: "api"
  platform: "universal"
  
  endpoints:
    search: "https://registry.npmjs.org/-/v1/search?text={query}&size=20"
    info: "https://registry.npmjs.org/{package}"
    versions: "https://registry.npmjs.org/{package}/{version}"
  
  parsing:
    format: "json"
    encoding: "utf-8"
  
  cache:
    ttl_hours: 1  # Cache individual package results for 1 hour
  
  rate_limiting:
    requests_per_minute: 60
    concurrent_requests: 5
    retry_attempts: 3
    retry_backoff_seconds: 2
  
  limits:
    timeout_seconds: 30
  
  auth:
    type: "none"  # npm registry is public
    # For private registries:
    # type: "bearer"
    # token: "${NPM_TOKEN}"
```

### API-Based Repository Example (pip/PyPI)

```yaml
- name: "pypi"
  type: "pip"
  query_type: "api"
  platform: "universal"
  
  endpoints:
    search: "https://pypi.org/search/?q={query}"
    info: "https://pypi.org/pypi/{package}/json"
    versions: "https://pypi.org/pypi/{package}/{version}/json"
  
  parsing:
    format: "json"
    encoding: "utf-8"
  
  cache:
    ttl_hours: 2
  
  rate_limiting:
    requests_per_minute: 100
    concurrent_requests: 10
    retry_attempts: 3
    retry_backoff_seconds: 1
  
  limits:
    timeout_seconds: 30
```

### API-Based Repository Example (cargo/crates.io)

```yaml
- name: "crates-io"
  type: "cargo"
  query_type: "api"
  platform: "universal"
  
  endpoints:
    search: "https://crates.io/api/v1/crates?q={query}&per_page=20"
    info: "https://crates.io/api/v1/crates/{package}"
    versions: "https://crates.io/api/v1/crates/{package}/{version}"
  
  parsing:
    format: "json"
    encoding: "utf-8"
  
  cache:
    ttl_hours: 6
  
  rate_limiting:
    requests_per_minute: 60
    concurrent_requests: 5
    retry_attempts: 3
    retry_backoff_seconds: 2
  
  limits:
    timeout_seconds: 30
  
  auth:
    type: "none"  # crates.io is public
```

### API-Based Repository Example (winget)

```yaml
- name: "winget-msstore"
  type: "winget"
  query_type: "api"
  platform: "windows"
  
  endpoints:
    search: "https://storeedgefd.dsx.mp.microsoft.com/v9.0/manifestSearch"
    info: "https://storeedgefd.dsx.mp.microsoft.com/v9.0/packageManifests/{package}"
  
  parsing:
    format: "json"
    encoding: "utf-8"
  
  cache:
    ttl_hours: 12
  
  rate_limiting:
    requests_per_minute: 30
    concurrent_requests: 3
    retry_attempts: 3
    retry_backoff_seconds: 5
  
  limits:
    timeout_seconds: 60
```

## Implementation Considerations

### 1. Query Strategy

**For Bulk Download**:
```python
# Download once
packages = download_and_parse(repo.endpoints.packages)
cache.store(repo.name, packages, ttl=24h)

# Query many times (fast)
nginx = find_package(packages, "nginx")
apache = find_package(packages, "apache")
```

**For API-Based**:
```python
# Query each package individually
nginx = api_query(repo.endpoints.info.format(package="nginx"))
cache.store(f"{repo.name}:nginx", nginx, ttl=1h)

apache = api_query(repo.endpoints.info.format(package="apache"))
cache.store(f"{repo.name}:apache", apache, ttl=1h)
```

### 2. Rate Limiting

**Implementation**:
```python
class RateLimiter:
    def __init__(self, requests_per_minute, concurrent_requests):
        self.rpm = requests_per_minute
        self.concurrent = concurrent_requests
        self.semaphore = asyncio.Semaphore(concurrent_requests)
        self.last_requests = deque()
    
    async def acquire(self):
        # Wait for semaphore (concurrent limit)
        await self.semaphore.acquire()
        
        # Check rate limit
        now = time.time()
        minute_ago = now - 60
        
        # Remove old requests
        while self.last_requests and self.last_requests[0] < minute_ago:
            self.last_requests.popleft()
        
        # Wait if at limit
        if len(self.last_requests) >= self.rpm:
            sleep_time = 60 - (now - self.last_requests[0])
            await asyncio.sleep(sleep_time)
        
        self.last_requests.append(now)
    
    def release(self):
        self.semaphore.release()
```

### 3. Caching Strategy

**Bulk Download Cache**:
- Cache key: `{repo_name}_packages`
- TTL: 24 hours (long, since full list)
- Size: Large (100+ MB)

**API-Based Cache**:
- Cache key: `{repo_name}:{package_name}`
- TTL: 1-6 hours (shorter, per package)
- Size: Small (few KB per package)

### 4. Error Handling

**Rate Limit Exceeded**:
```python
try:
    response = await api_query(url)
except RateLimitError as e:
    # Exponential backoff
    wait_time = 2 ** attempt  # 2, 4, 8 seconds
    await asyncio.sleep(wait_time)
    retry()
```

**Timeout**:
```python
try:
    response = await asyncio.wait_for(
        api_query(url),
        timeout=30
    )
except asyncio.TimeoutError:
    log_warning(f"Timeout querying {url}")
    return None
```

### 5. Authentication

**Bearer Token**:
```python
headers = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "saigen/1.0"
}
```

**API Key**:
```python
headers = {
    "X-API-Key": api_key,
    "User-Agent": "saigen/1.0"
}
```

## Refresh Command Implications

### For Bulk Download Repositories

```bash
saigen refresh-versions nginx.yaml --providers apt,dnf

# Behavior:
# 1. Download apt package list (once)
# 2. Download dnf package list (once)
# 3. Query locally for nginx in both
# Fast: ~5-10 seconds
```

### For API-Based Repositories

```bash
saigen refresh-versions nginx.yaml --providers npm,pip,cargo

# Behavior:
# 1. Query npm API for nginx
# 2. Query PyPI API for nginx
# 3. Query crates.io API for nginx
# Slower: ~2-5 seconds per provider (network latency)
```

### Mixed Repositories

```bash
saigen refresh-versions nginx.yaml --providers apt,npm

# Behavior:
# 1. Download apt package list (bulk)
# 2. Query npm API (per package)
# Mixed performance
```

## Performance Optimization

### 1. Concurrent API Queries

```python
# Query multiple packages concurrently
async def refresh_multiple_packages(packages, repo):
    tasks = [
        query_api(repo, pkg)
        for pkg in packages
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### 2. Cache Reuse

```python
# Check cache first
cached = cache.get(f"{repo}:{package}")
if cached and not expired(cached):
    return cached.version

# Query API only if cache miss
result = await api_query(repo, package)
cache.store(f"{repo}:{package}", result)
```

### 3. Batch Operations

For API-based repositories that support batch queries:
```python
# Some APIs support batch queries
# npm: GET /packages?names=nginx,apache,redis
if repo.supports_batch:
    results = await batch_query(repo, packages)
else:
    results = await concurrent_queries(repo, packages)
```

## Configuration Schema Updates

Add `query_type` field to repository schema:

```json
{
  "query_type": {
    "type": "string",
    "enum": ["bulk_download", "api"],
    "description": "How the repository provides package data"
  },
  "rate_limiting": {
    "type": "object",
    "properties": {
      "requests_per_minute": {"type": "integer"},
      "concurrent_requests": {"type": "integer"},
      "retry_attempts": {"type": "integer"},
      "retry_backoff_seconds": {"type": "number"}
    }
  }
}
```

## Testing Considerations

### Bulk Download Tests
- Test download and parsing
- Test cache behavior
- Test offline operation

### API-Based Tests
- Test rate limiting
- Test retry logic
- Test authentication
- Test timeout handling
- Mock API responses for unit tests

## Summary

Supporting API-based repositories requires:
1. ✅ Per-package query logic
2. ✅ Rate limiting implementation
3. ✅ Request throttling and backoff
4. ✅ Per-package caching
5. ✅ Authentication support
6. ✅ Timeout and retry handling
7. ✅ Concurrent request management

This enables SAIGEN to work with modern package registries (npm, pip, cargo, winget) that don't provide bulk downloads, while maintaining efficient operation through caching and rate limiting.
