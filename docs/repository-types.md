# Repository Types in SAIGEN

SAIGEN supports two types of package repositories, each optimized for different use cases.

## Bulk Download Repositories

These repositories provide complete package lists that can be downloaded and cached locally.

### Characteristics
- Full package list available via single endpoint
- Efficient for offline use and batch operations
- Cached locally for fast repeated access
- Updated periodically via `saigen cache update`

### Examples
- **apt** (Debian/Ubuntu)
- **dnf/yum** (RHEL/Fedora/CentOS)
- **apk** (Alpine Linux)
- **brew** (macOS Homebrew)
- **zypper** (openSUSE)

### Usage
```bash
# Update cache for all bulk-download repositories
saigen cache update

# Search cached packages (fast)
saigen repositories search "nginx"

# View cache statistics
saigen cache status
```

## API-Based Repositories

These repositories provide on-demand package queries via API endpoints.

### Characteristics
- No bulk package list available
- Optimized for real-time queries
- Not cached during `saigen cache update`
- Queried on-demand during search operations

### Examples
- **npm** (Node.js packages)
- **pypi** (Python packages)
- **maven** (Java packages)
- **cargo** (Rust crates)
- **rubygems** (Ruby gems)
- **winget** (Windows Package Manager)
- **chocolatey** (Windows packages)
- **nuget** (.NET packages)
- **flatpak** (Linux applications)
- **snapcraft** (Snap packages)
- **nix** (NixOS packages)
- **pacman** (Arch Linux)
- **composer** (PHP packages)

### Usage
```bash
# Search queries API repositories automatically
saigen repositories search "express"

# Get package info from specific repository
saigen repositories info "express" --repository npm-registry

# API repositories are NOT cached during updates
saigen cache update  # Skips API-based repositories
```

## How to Identify Repository Type

### In Configuration Files
Repository type is specified in the YAML configuration:

```yaml
# Bulk download repository
query_type: bulk_download  # or omitted (default)

# API-based repository
query_type: api
```

### Via CLI
```bash
# List all repositories with their types
saigen repositories list-repos

# Filter by platform
saigen repositories list-repos --platform linux
```

## Performance Considerations

### Bulk Download Repositories
- **Pros**: Fast repeated searches, offline capability, batch operations
- **Cons**: Requires periodic cache updates, storage space for cache
- **Best for**: Frequent searches, offline use, batch processing

### API-Based Repositories
- **Pros**: Always up-to-date, no cache storage needed, no bulk downloads
- **Cons**: Requires network access, rate limits may apply, slower for repeated queries
- **Best for**: Real-time queries, infrequent searches, latest package info

## Cache Management

### Update Cache
```bash
# Update all bulk-download repositories
saigen cache update

# Force update even if cache is valid
saigen cache update --force
```

### View Cache Status
```bash
# Show cache statistics
saigen cache status

# View detailed cache information
saigen cache status --verbose
```

### Clear Cache
```bash
# Clear all cached data
saigen cache clear --all

# Clear specific repository
saigen cache clear --repository apt-ubuntu-jammy
```

### Cleanup Expired Entries
```bash
# Remove expired cache entries
saigen cache cleanup
```

## Search Behavior

When you run a search command, SAIGEN:

1. **Bulk Download Repositories**: Searches cached package lists (fast)
2. **API-Based Repositories**: Queries APIs in real-time (slower but always current)
3. **Results**: Combined from both types, sorted by relevance

```bash
# Search across all repositories (both types)
saigen repositories search "redis" --limit 10

# Search specific platform
saigen repositories search "nginx" --platform linux

# Search specific repository type
saigen repositories search "python" --type package_manager
```

## Configuration

Repository configurations are stored in:
```
saigen/repositories/configs/*.yaml
```

Each configuration file specifies:
- Repository endpoints
- Query type (bulk_download or api)
- Parsing rules
- Cache settings
- Rate limits (for API repositories)

## Troubleshooting

### "download_package_list() called on API-based repository" Warning
This warning indicates code is trying to bulk download from an API repository. This is now handled automatically - API repositories are skipped during cache updates.

### Brotli Compression Error
Some repositories (like nix-nixos) use brotli compression. Install the required package:
```bash
pip install brotli
```

### Rate Limiting
API-based repositories may have rate limits. SAIGEN handles this automatically with:
- Exponential backoff
- Request queuing
- Concurrent request limits

### Cache Not Updating
If cache updates seem stuck:
```bash
# Clear cache and force update
saigen cache clear --all
saigen cache update --force
```

## Best Practices

1. **Regular Updates**: Run `saigen cache update` periodically for bulk-download repositories
2. **Cache Cleanup**: Run `saigen cache cleanup` to remove expired entries
3. **API Queries**: Use specific repository names when querying API-based repositories for better performance
4. **Offline Use**: Cache bulk-download repositories before going offline
5. **Rate Limits**: Be mindful of API rate limits when making frequent queries

## Related Documentation
- [Repository Configuration](repositories/README.md)
- [Cache Management](cache-management.md)
- [Search and Query](search-query.md)
