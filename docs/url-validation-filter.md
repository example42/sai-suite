# URL Validation Filter

## Overview

The URL Validation Filter is a post-LLM processing feature that validates all URLs in generated saidata by making HTTP requests to verify they are reachable. URLs that fail validation (timeout, connection error, or HTTP error status) are automatically filtered out from the final output.

## Purpose

LLMs can sometimes generate URLs that:
- Don't exist or are no longer available
- Have typos or formatting errors
- Point to incorrect domains
- Are temporarily or permanently unreachable

The URL validation filter ensures that only valid, reachable URLs are included in the generated saidata, improving data quality and reliability.

## How It Works

1. **URL Extraction**: After LLM generation and schema validation, all HTTP/HTTPS URLs are extracted from the saidata
2. **Concurrent Validation**: URLs are validated concurrently using async HTTP HEAD requests
3. **Filtering**: URLs that return errors or timeouts are removed from the saidata
4. **Result**: Clean saidata with only verified, reachable URLs

## Validated URL Fields

The filter checks URLs in the following locations:

### Metadata
- `metadata.urls.website`
- `metadata.urls.documentation`
- `metadata.urls.source`
- `metadata.urls.issues`
- `metadata.urls.support`
- `metadata.urls.download`
- `metadata.urls.changelog`
- `metadata.urls.license`
- `metadata.urls.sbom`
- `metadata.urls.icon`
- `metadata.security.vulnerability_disclosure`
- `metadata.security.sbom_url`
- `metadata.security.signing_key`

### Installation Methods
- `packages[].download_url`
- `sources[].url` (entire source entry removed if URL invalid)
- `binaries[].url` (entire binary entry removed if URL invalid)
- `scripts[].url` (entire script entry removed if URL invalid)

### Provider Configurations
- All URL fields within `providers.<provider_name>.*`
- Repository URLs and keys
- Nested packages, sources, binaries, and scripts

## Configuration

The URL filter can be configured in the saigen configuration:

```yaml
# Enable/disable URL filtering (default: true)
enable_url_filter: true

# Request timeout in seconds (default: 5)
url_filter_timeout: 5

# Maximum concurrent URL checks (default: 10)
url_filter_max_concurrent: 10
```

### Configuration Options

- **enable_url_filter**: Set to `false` to disable URL validation entirely
- **url_filter_timeout**: How long to wait for each URL before considering it unreachable
- **url_filter_max_concurrent**: Number of URLs to check simultaneously (higher = faster but more network load)

## Behavior

### Valid URLs
URLs are considered valid if they:
- Return HTTP status 2xx (success)
- Return HTTP status 3xx (redirect)
- Respond within the timeout period

### Invalid URLs
URLs are filtered out if they:
- Return HTTP status 4xx (client error)
- Return HTTP status 5xx (server error)
- Timeout after the configured period
- Fail with connection errors
- Have invalid format or protocol

### Filtering Strategy

- **Optional URL fields** (like `metadata.urls.*`): Set to `null` if invalid
- **Required URL fields** (like `sources[].url`): Entire entry is removed if URL is invalid
- **Non-HTTP URLs**: Not validated (e.g., `git://`, `ftp://`, file paths)

## Example

### Before Filtering

```yaml
version: "0.3"
metadata:
  name: example-software
  urls:
    website: https://example.com  # Valid
    documentation: https://invalid-docs-url.com  # Invalid
    source: https://github.com/example/repo  # Valid

sources:
  - name: source1
    url: https://github.com/example/repo/archive/main.tar.gz  # Valid
    build_system: cmake
  - name: source2
    url: https://nonexistent-site.com/source.tar.gz  # Invalid
    build_system: make
```

### After Filtering

```yaml
version: "0.3"
metadata:
  name: example-software
  urls:
    website: https://example.com
    documentation: null  # Filtered out
    source: https://github.com/example/repo

sources:
  - name: source1
    url: https://github.com/example/repo/archive/main.tar.gz
    build_system: cmake
  # source2 removed entirely
```

## Performance Considerations

- **Concurrent Requests**: The filter uses async HTTP requests to validate multiple URLs simultaneously
- **Timeout**: Default 5-second timeout balances speed vs. reliability
- **Network Impact**: Validation makes HEAD requests (minimal data transfer)
- **Generation Time**: Adds 5-15 seconds to generation depending on URL count

## Logging

The filter logs validation results:

```
INFO: Starting URL validation for saidata: example-software
DEBUG: Found 8 URLs to validate
DEBUG: URL valid: https://example.com (status: 200)
WARNING: URL invalid: https://invalid-docs-url.com (status: 404)
WARNING: URL timeout: https://slow-server.com
INFO: URL validation complete: 6/8 URLs are reachable
```

## Disabling the Filter

To disable URL validation:

**Via Configuration File:**
```yaml
enable_url_filter: false
```

**Via CLI (if supported):**
```bash
saigen generate nginx --no-url-filter
```

**Programmatically:**
```python
from saigen.core.generation_engine import GenerationEngine

config = {
    'enable_url_filter': False
}

engine = GenerationEngine(config)
```

## Testing

Test the URL filter with the provided test script:

```bash
python scripts/development/test_url_filter.py
```

This script creates sample saidata with both valid and invalid URLs and demonstrates the filtering behavior.

## Limitations

- Only validates HTTP/HTTPS URLs
- HEAD requests may not work for all servers (some require GET)
- Temporary network issues may cause false negatives
- Some servers may block automated requests
- Does not validate URL content, only reachability

## Best Practices

1. **Keep timeout reasonable**: 5-10 seconds balances speed and reliability
2. **Limit concurrency**: 10-20 concurrent requests prevents overwhelming the network
3. **Review filtered results**: Check logs to ensure important URLs weren't incorrectly filtered
4. **Disable for testing**: Turn off during development to speed up iteration
5. **Re-run if needed**: Network issues may require re-generation

## Future Enhancements

Potential improvements for future versions:

- Fallback to GET requests if HEAD fails
- URL content validation (check for expected content)
- Caching of URL validation results
- Retry logic for transient failures
- Custom validation rules per URL type
- Support for authentication/headers
- Validation of non-HTTP URLs (git, ftp, etc.)
