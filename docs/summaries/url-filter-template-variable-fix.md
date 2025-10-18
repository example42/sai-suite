# URL Filter Template Variable Fix

## Problem

During saidata generation with saigen, URLs containing template variables like `{{version}}`, `{{platform}}`, and `{{architecture}}` were being incorrectly filtered out during the URL validation phase. These are valid URLs according to the saidata-0.3 schema and should be preserved.

Examples of affected URLs:
- `https://nginx.org/download/nginx-{{version}}.tar.gz`
- `https://releases.example.com/{{version}}/app_{{platform}}_{{architecture}}.tar.gz`
- `https://dl.k8s.io/release/{{version}}/bin/{{platform}}/{{architecture}}/kubectl`

## Root Cause

The `URLValidationFilter` in `saigen/core/url_filter.py` was attempting to validate all HTTP/HTTPS URLs by making actual HTTP requests to them. Since template variables are placeholders that get resolved at runtime by the SAI execution engine, these URLs would fail validation and be filtered out.

## Solution

Added a `_has_template_variables()` method to detect URLs containing template placeholders (`{{` and `}}`), and modified the URL extraction and filtering logic to skip validation for URLs with template variables.

### Changes Made

1. **Added template variable detection** (`saigen/core/url_filter.py`):
   - New method `_has_template_variables()` to check if a URL contains `{{` and `}}`
   - Comprehensive documentation explaining why template URLs should not be validated

2. **Updated URL extraction** to skip template URLs:
   - Modified `_extract_urls()` to exclude URLs with template variables from validation
   - Applied to all URL sources: metadata, packages, sources, binaries, scripts, and provider configs

3. **Updated URL filtering** to preserve template URLs:
   - Modified `_filter_urls()` to keep URLs with template variables even if they weren't validated
   - Modified `_filter_provider_config()` similarly for provider-specific URLs

4. **Added comprehensive tests** (`tests/saigen/test_url_filter.py`):
   - `test_has_template_variables()` - Tests template variable detection
   - `test_extract_urls_skips_template_variables()` - Verifies template URLs are not extracted for validation
   - `test_filter_saidata_preserves_template_urls()` - Ensures template URLs are preserved during filtering

## Impact

- Template URLs in sources, binaries, and scripts are now correctly preserved during saidata generation
- LLM-generated URLs with proper template variables will no longer be filtered out
- URL validation still works for non-template URLs to catch broken links
- No breaking changes to existing functionality

## Testing

All 14 URL filter tests pass, including the 3 new tests specifically for template variable handling.

```bash
pytest tests/saigen/test_url_filter.py -v
```

## Related Files

- `saigen/core/url_filter.py` - Main implementation
- `tests/saigen/test_url_filter.py` - Test coverage
- `saigen/core/generation_engine.py` - Integration point
