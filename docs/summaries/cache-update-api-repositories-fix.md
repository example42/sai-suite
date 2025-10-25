# Cache Update API Repositories Fix

## Date
October 22, 2025

## Issues Fixed

### 1. API-Based Repository Warnings
**Problem**: When running `saigen cache update`, warnings were displayed for all API-based repositories:
```
download_package_list() called on API-based repository <name>. 
Consider using query_package() or query_packages_batch() instead.
```

**Root Cause**: The cache update mechanism was calling `download_package_list()` on all repositories, including API-based ones. API-based repositories (npm, pypi, maven, winget, etc.) are designed for on-demand queries, not bulk downloads.

**Solution**: Modified the cache update logic to skip API-based repositories:
- Updated `RepositoryCache.get_or_fetch()` to detect API-based repositories and skip bulk downloads
- Updated `CacheManager.update_repository()` to skip API-based repositories entirely
- API-based repositories now return empty lists during cache updates with debug logging

**Files Modified**:
- `saigen/repositories/cache.py`

### 2. Brotli Compression Support
**Problem**: The nix-nixos repository uses brotli compression, but the `brotli` Python package was not installed, causing errors:
```
Network error: 400, message='Can not decode content-encoding: brotli (br). 
Please install `Brotli`'
```

**Root Cause**: 
- The nix repository configuration specifies `compression: brotli`
- The universal downloader didn't have brotli decompression support
- The brotli package was not installed in the environment

**Solution**:
1. Added brotli decompression support to `UniversalRepositoryDownloader._decompress_content()`
2. Added auto-detection of brotli from `content-encoding` headers
3. Added clear error message when brotli package is missing
4. Installed brotli package: `pip install brotli`

**Files Modified**:
- `saigen/repositories/downloaders/universal.py`

## Behavior Changes

### Cache Update
- **Before**: All repositories (including API-based) were bulk downloaded during cache updates
- **After**: Only bulk-download repositories are cached; API-based repositories are skipped

### API-Based Repositories
API-based repositories are now handled differently:
- **Cache Update**: Skipped (no bulk download)
- **Search**: Works normally via API queries
- **Package Info**: Works normally via API queries
- **Query Methods**: Use `query_package()` or `query_packages_batch()` for on-demand access

### Supported Compression Formats
The universal downloader now supports:
- gzip
- bzip2
- xz/lzma
- **brotli** (new)

## API-Based Repositories List
The following repositories use `query_type: api`:
- snapcraft (snap)
- rubygems (gem)
- nix-nixos (nix)
- npm-registry (npm)
- maven-central (maven)
- choco-windows (choco)
- winget-windows (winget)
- msstore-windows (msstore)
- flathub (flatpak)
- nuget-org (nuget)
- emerge-gentoo (emerge)
- crates-io (cargo)
- packagist (composer)
- pacman-arch (pacman)
- pypi (pip)

## Testing

### Verify Cache Update
```bash
saigen cache update
# Should complete without warnings
# Should show "0/57 repositories updated" (API repos skipped)
```

### Verify Cache Status
```bash
saigen cache status
# Should show cached packages from bulk-download repos only
```

### Verify API Repository Search
```bash
saigen repositories search "redis" --limit 5
# Should search across all repositories including API-based ones
```

### Verify Brotli Support
```bash
# Nix repository should work without errors
saigen repositories search "firefox" --limit 5
```

## Performance Impact

### Positive
- Faster cache updates (skips 15+ API-based repositories)
- Reduced network traffic during cache updates
- No unnecessary bulk downloads from API endpoints

### Neutral
- API-based repositories are queried on-demand (as designed)
- Search operations work the same way as before

## Future Considerations

1. **Optional API Caching**: Consider adding optional caching for frequently queried packages from API repositories
2. **Dependency Management**: Add brotli to package dependencies (requirements.txt or pyproject.toml)
3. **Documentation**: Update user documentation to explain the difference between bulk-download and API-based repositories
4. **Configuration**: Consider adding a flag to force API repository bulk downloads if needed

## Related Files
- `saigen/repositories/cache.py` - Cache management
- `saigen/repositories/downloaders/api_downloader.py` - API repository downloader
- `saigen/repositories/downloaders/universal.py` - Universal downloader with compression support
- `saigen/repositories/configs/*.yaml` - Repository configurations
