# URL Features - Quick Start

## What's New?

Two complementary features to improve URL quality in generated saidata:

1. **URL Validation Filter** - Automatically validates and removes unreachable URLs
2. **Enhanced Prompts** - LLM generates more comprehensive URLs

## Quick Start

### It Just Works™

No configuration needed! The features are enabled by default:

```bash
# Generate saidata - URLs are automatically validated
saigen generate nginx -o output/
```

### What Happens

```
1. LLM generates saidata with many URLs
   ↓
2. Schema validation passes
   ↓
3. URL filter validates all HTTP/HTTPS URLs
   ↓
4. Invalid URLs are removed
   ↓
5. Clean saidata with only valid URLs
```

## Configuration

### Disable URL Filtering

**Config file:**
```yaml
enable_url_filter: false
```

**Programmatically:**
```python
config = {'enable_url_filter': False}
engine = GenerationEngine(config)
```

### Adjust Timeout/Concurrency

```yaml
enable_url_filter: true
url_filter_timeout: 10        # seconds (default: 5)
url_filter_max_concurrent: 20  # parallel (default: 10)
```

## Expected Results

### Before
```yaml
metadata:
  urls:
    website: https://example.com
    documentation: https://docs.example.com
    source: https://github.com/example/repo
```

### After
```yaml
metadata:
  urls:
    website: https://example.com
    documentation: https://docs.example.com
    source: https://github.com/example/repo
    issues: https://github.com/example/repo/issues
    support: https://example.com/support
    download: https://example.com/download
    changelog: https://example.com/changelog
    license: https://example.com/LICENSE
```

## Performance

- **Time**: +5-15 seconds per generation
- **Network**: Minimal (HEAD requests only)
- **Worth it**: Yes! 200-300% more URLs

## Testing

```bash
# Test URL filter
python scripts/development/test_url_filter.py

# Test prompt enhancement
python scripts/development/test_url_prompt_enhancement.py

# Run unit tests
pytest tests/test_url_filter.py -v
```

## When to Disable

- Development/testing (faster iteration)
- Limited network access
- Known valid URLs
- CI/CD with network restrictions

## Troubleshooting

### URLs Being Filtered Out?

Check logs:
```bash
cat ~/.saigen/logs/saigen_generate_*.json | grep -i url
```

### Too Slow?

Reduce timeout or increase concurrency:
```yaml
url_filter_timeout: 3
url_filter_max_concurrent: 20
```

### Want More URLs?

The LLM is already prompted to be generous. If you're not getting enough URLs:
1. Check if they're being filtered (see logs)
2. Provide hints in generation request
3. Manually add URLs after generation

## Documentation

- **Full Guide**: `docs/url-validation-filter.md`
- **Quick Reference**: `docs/url-filter-quick-reference.md`
- **Best Practices**: `docs/generation-engine-best-practices.md`
- **Summaries**: `docs/summaries/url-*.md`

## Key Points

✅ Enabled by default  
✅ No configuration needed  
✅ Automatic validation  
✅ More comprehensive URLs  
✅ Better data quality  
✅ Can be disabled  
✅ Backward compatible  

## Questions?

See full documentation in `docs/url-validation-filter.md`
