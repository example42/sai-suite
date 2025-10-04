# Quick Fixes Guide for Remaining Repositories

This guide provides specific fixes you can apply immediately to get more repositories working.

## Quick Wins (Can be fixed in minutes)

### 1. Snapcraft - Add Query Parameters

**File**: `saigen/repositories/configs/language-repositories.yaml`

**Find**:
```yaml
endpoints:
  packages: "https://api.snapcraft.io/v2/snaps/find"
```

**Replace with**:
```yaml
endpoints:
  packages: "https://api.snapcraft.io/v2/snaps/find?q=*&fields=name,version,summary,publisher"
```

### 2. NPM Registry - Update Endpoint

**File**: `saigen/repositories/configs/universal-repositories.yaml`

**Find**:
```yaml
endpoints:
  packages: "https://registry.npmjs.org/-/all"
```

**Replace with**:
```yaml
endpoints:
  packages: "https://replicate.npmjs.com/_all_docs?include_docs=true"
```

**Also update parsing**:
```yaml
parsing:
  format: "json"
  patterns:
    json_path: "rows"
  fields:
    name: "doc.name"
    version: "doc.dist-tags.latest"
    description: "doc.description"
```

### 3. Crates.io - Update Endpoint

**File**: `saigen/repositories/configs/universal-repositories.yaml`

**Find**:
```yaml
endpoints:
  packages: "https://crates.io/api/v1/crates"
```

**Replace with**:
```yaml
endpoints:
  packages: "https://crates.io/api/v1/crates?page=1&per_page=100&sort=alphabetical"
```

**Update parsing**:
```yaml
parsing:
  format: "json"
  patterns:
    json_path: "crates"
  fields:
    name: "name"
    version: "max_version"
    description: "description"
```

### 4. Packagist - Update Endpoint

**File**: `saigen/repositories/configs/universal-repositories.yaml`

**Find**:
```yaml
endpoints:
  packages: "https://packagist.org/packages/list.json"
```

**Replace with**:
```yaml
endpoints:
  packages: "https://packagist.org/packages/list.json?type=library"
```

**Update parsing**:
```yaml
parsing:
  format: "json"
  patterns:
    json_path: "packageNames"
  # Note: This returns just names, not full package data
```

### 5. Conda-forge - Update Endpoint

**File**: `saigen/repositories/configs/universal-repositories.yaml`

**Find**:
```yaml
endpoints:
  packages: "https://conda.anaconda.org/conda-forge/channeldata.json"
```

**Replace with**:
```yaml
endpoints:
  packages: "https://conda.anaconda.org/conda-forge/linux-64/repodata.json"
```

**Update parsing**:
```yaml
parsing:
  format: "json"
  patterns:
    json_path: "packages"
  fields:
    name: "name"
    version: "version"
    description: "summary"
```

### 6. NuGet - Update Endpoint

**File**: `saigen/repositories/configs/universal-repositories.yaml`

**Find**:
```yaml
endpoints:
  packages: "https://api.nuget.org/v3-flatcontainer/"
```

**Replace with**:
```yaml
endpoints:
  packages: "https://azuresearch-usnc.nuget.org/query?q=*&take=1000&prerelease=false"
```

**Update parsing**:
```yaml
parsing:
  format: "json"
  patterns:
    json_path: "data"
  fields:
    name: "id"
    version: "version"
    description: "description"
```

## Medium Complexity Fixes

### 7. PyPI - Use Simple Index

PyPI doesn't have a simple JSON API for all packages. Options:

**Option A: Use Simple Index (HTML)**
```yaml
endpoints:
  packages: "https://pypi.org/simple/"
parsing:
  format: "html"
  patterns:
    link_selector: "a"
  fields:
    name: "text"
```

**Option B: Use PyPI Stats API**
```yaml
endpoints:
  packages: "https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json"
parsing:
  format: "json"
  patterns:
    json_path: "rows"
  fields:
    name: "project"
```

### 8. RubyGems - Use Alternative Endpoint

```yaml
endpoints:
  packages: "https://rubygems.org/api/v1/versions.json"
parsing:
  format: "json"
  fields:
    name: "name"
    version: "number"
```

Or use the gems endpoint without authentication:
```yaml
endpoints:
  packages: "https://rubygems.org/api/v1/gems.json?page=1"
```

## Testing Your Fixes

After making changes:

```bash
# Test specific repository
saigen repositories stats --verbose 2>&1 | grep -A 2 "repository-name"

# Or test all
saigen repositories stats --verbose
```

## Common Patterns

### JSON with Nested Data
```yaml
parsing:
  format: "json"
  patterns:
    json_path: "data.packages"  # Navigate to nested array
  fields:
    name: "packageName"
    version: "latestVersion"
```

### Pagination
Most APIs use pagination. The current implementation doesn't handle this yet, so you'll get limited results (usually 100-1000 packages).

### Rate Limiting
GitHub API: 60 requests/hour (unauthenticated), 5000/hour (authenticated)
Most other APIs: Varies, usually 100-1000 requests/hour

## Next Steps After Quick Fixes

1. Implement pagination support in universal downloader
2. Add authentication support for APIs that require it
3. Implement caching for individual package details
4. Add retry logic with exponential backoff
5. Implement incremental updates

## Useful Commands

```bash
# Clear cache and test fresh
rm -rf cache/*
saigen repositories stats

# Test specific platform
saigen repositories stats --platform linux

# Export to JSON for analysis
saigen repositories stats --format json > repo-stats.json

# Count working repositories
saigen repositories stats | grep "| OK" | wc -l
```
