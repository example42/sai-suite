# Repository Parser Improvements Needed

## Overview
Many repositories are returning 0 packages because they require specialized parsers that understand their specific API formats.

## GitHub-Based Repositories

### Issue
Repositories hosted on GitHub (winget, scoop) return directory listings via GitHub API, not direct package data.

### Affected Repositories
- winget-community
- scoop-main (currently shows 1000 packages - likely hitting pagination limit)
- scoop-extras (currently shows 1000 packages - likely hitting pagination limit)

### Current Response Format
```json
[
  {
    "name": "package-name.json",
    "path": "bucket/package-name.json",
    "download_url": "https://raw.githubusercontent.com/.../package-name.json",
    "type": "file"
  }
]
```

### Required Implementation
1. **GitHub Directory Parser**
   - Parse GitHub API directory listing
   - Extract package names from filenames (remove .json/.yaml extension)
   - Handle pagination (GitHub API returns max 1000 items per page)
   - Optionally fetch individual files for full package details

2. **Configuration Updates**
   - Add `parser_type: github_directory` to parsing config
   - Add pagination support
   - Add rate limiting (GitHub API: 60 req/min unauthenticated, 5000/hr authenticated)

### Implementation Priority: HIGH
These are popular Windows package managers.

## XML-Based Repositories

### Issue
Some repositories return XML/Atom feeds that need specialized parsing.

### Affected Repositories
- chocolatey-community (returns 0 packages)
- fedora-updates (returns 0 packages)
- opensuse-oss (returns 0 packages)

### Required Implementation
1. **OData/Atom Feed Parser**
   - Parse XML/Atom feed format
   - Extract package information from XML elements
   - Handle namespaces correctly

2. **Configuration Updates**
   - Verify XPath expressions in parsing config
   - Test with actual responses

### Implementation Priority: MEDIUM

## API-Specific Repositories

### NPM Registry
**Issue**: Endpoint `https://registry.npmjs.org/-/all` returns 404

**Solutions**:
1. Use replicate database: `https://replicate.npmjs.com/_all_docs`
2. Use search API: `https://registry.npmjs.org/-/v1/search?text=*&size=250`
3. Use CouchDB view: `https://skimdb.npmjs.com/registry/_all_docs`

**Implementation**: Update endpoint and add pagination support

### PyPI
**Issue**: Expecting JSON but getting HTML

**Solutions**:
1. Use Simple API: `https://pypi.org/simple/` (HTML index)
2. Use JSON API per package: `https://pypi.org/pypi/{package}/json`
3. Use BigQuery public dataset
4. Use PyPI's XML-RPC API (deprecated but still works)

**Implementation**: 
- Option 1: Parse HTML simple index
- Option 2: Fetch package list from another source, then use JSON API
- Option 3: Use warehouse database dumps

### Crates.io
**Issue**: Returns 0 packages despite successful connection

**Current Endpoint**: Likely returning empty or wrong format

**Solutions**:
1. Use crates.io API: `https://crates.io/api/v1/crates?page=1&per_page=100`
2. Use database dump: `https://static.crates.io/db-dump.tar.gz`
3. Use index: `https://github.com/rust-lang/crates.io-index`

**Implementation**: Update endpoint and add pagination

### Conda-forge
**Issue**: Returns 0 packages

**Current Endpoint**: Needs verification

**Solutions**:
1. Use repodata.json: `https://conda.anaconda.org/conda-forge/linux-64/repodata.json`
2. Use channeldata.json: `https://conda.anaconda.org/conda-forge/channeldata.json`

**Implementation**: Update endpoint and parser

### Packagist (Composer)
**Issue**: Returns 0 packages

**Solutions**:
1. Use packages.json: `https://packagist.org/packages/list.json`
2. Use metadata: `https://repo.packagist.org/packages.json`

**Implementation**: Update endpoint

### RubyGems
**Issue**: HTTP 401 Unauthorized

**Solutions**:
1. Use versions endpoint: `https://rubygems.org/api/v1/versions.json`
2. Use gems endpoint without auth: `https://rubygems.org/api/v1/gems.json` (may need API key)
3. Use database dump: `https://rubygems.org/pages/data`

**Implementation**: Update endpoint or add authentication

### NuGet
**Issue**: HTTP 404 on endpoint

**Solutions**:
1. Use catalog: `https://api.nuget.org/v3/catalog0/index.json`
2. Use search: `https://azuresearch-usnc.nuget.org/query?q=*&take=1000`
3. Use service index: `https://api.nuget.org/v3/index.json`

**Implementation**: Update endpoint and add pagination

### Snapcraft
**Issue**: HTTP 400 Bad Request

**Current Endpoint**: `https://api.snapcraft.io/v2/snaps/find`

**Solution**: Add required query parameters
```
https://api.snapcraft.io/v2/snaps/find?q=*&fields=*
```

**Implementation**: Update endpoint with query parameters

## Recommendations

### Phase 1: Quick Wins (1-2 days)
1. Fix snapcraft query parameters
2. Update npm-registry endpoint
3. Update packagist endpoint
4. Update conda-forge endpoint
5. Update crates.io endpoint
6. Update nuget endpoint

### Phase 2: Parser Development (3-5 days)
1. Implement GitHub directory parser
2. Implement XML/Atom feed parser
3. Implement HTML parser for PyPI simple index
4. Add pagination support for all parsers

### Phase 3: Advanced Features (1 week)
1. Add authentication support for APIs requiring it
2. Implement rate limiting and retry logic
3. Add caching for individual package details
4. Implement incremental updates

## Testing Strategy

1. **Unit Tests**: Test each parser with sample responses
2. **Integration Tests**: Test against live APIs (with rate limiting)
3. **Validation**: Verify package counts match expected values
4. **Performance**: Ensure parsers handle large responses efficiently

## Configuration Schema Updates

Add new parser types to support specialized formats:
```yaml
parsing:
  format: "json"  # or "xml", "html", "yaml"
  parser_type: "github_directory"  # or "odata", "simple_index", etc.
  pagination:
    enabled: true
    type: "link_header"  # or "page_number", "cursor"
    max_pages: 100
  fields:
    # Field mappings
```
