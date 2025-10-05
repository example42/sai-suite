# URL Validation Filter - Quick Reference

## What It Does
Validates all URLs in generated saidata and removes unreachable ones.

## Quick Start

### Enable/Disable
```yaml
# In saigen config
enable_url_filter: true  # default
```

### Configuration
```yaml
enable_url_filter: true
url_filter_timeout: 5        # seconds
url_filter_max_concurrent: 10  # parallel checks
```

## What Gets Validated

✅ All HTTP/HTTPS URLs in:
- `metadata.urls.*` (website, docs, source, etc.)
- `metadata.security.*` (sbom_url, signing_key, etc.)
- `packages[].download_url`
- `sources[].url`
- `binaries[].url`
- `scripts[].url`
- All provider-specific URLs

❌ Not validated:
- Non-HTTP URLs (git://, ftp://, file paths)
- Empty/null URLs

## Filtering Behavior

| Field Type | Invalid URL Behavior |
|------------|---------------------|
| Optional fields (metadata.urls.*) | Set to `null` |
| Required fields (sources[].url) | Entire entry removed |
| Package download_url | Set to `null` |
| Repository URLs | Set to `null` |

## Valid vs Invalid

**Valid URLs** (kept):
- HTTP status 200-399
- Responds within timeout

**Invalid URLs** (filtered):
- HTTP status 400-599
- Timeout
- Connection error
- DNS failure

## Common Use Cases

### Disable for Development
```python
config = {'enable_url_filter': False}
engine = GenerationEngine(config)
```

### Increase Timeout for Slow Networks
```yaml
url_filter_timeout: 10
```

### More Concurrent Checks
```yaml
url_filter_max_concurrent: 20
```

## Performance

- **Time**: +5-15 seconds per generation
- **Network**: HEAD requests only (minimal data)
- **Default**: 10 concurrent checks, 5s timeout

## Testing

```bash
# Run test script
python scripts/development/test_url_filter.py

# Run unit tests
pytest tests/test_url_filter.py -v
```

## Logging

```
INFO: Starting URL validation for saidata: nginx
DEBUG: Found 12 URLs to validate
DEBUG: URL valid: https://nginx.org (status: 200)
WARNING: URL invalid: https://bad-url.com (status: 404)
INFO: URL validation complete: 10/12 URLs are reachable
```

## When to Disable

- Development/testing (faster iteration)
- Limited network access
- Known valid URLs
- CI/CD with network restrictions

## Full Documentation

See `docs/url-validation-filter.md` for complete details.
