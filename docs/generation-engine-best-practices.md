# Generation Engine Best Practices

## Overview
The generation engine (`saigen/core/generation_engine.py`) orchestrates saidata creation using repository data and LLM providers. This guide outlines best practices for maintaining and extending the engine.

## Core Principles

### 1. No Hardcoded Repository Information
❌ **Don't do this:**
```python
if provider_name == "apt":
    url = "http://archive.ubuntu.com/ubuntu/"
```

✅ **Do this instead:**
```python
# Repository information comes from configs
for pkg in context.repository_data:
    if pkg.repository_type == provider_name:
        url = pkg.repository_url
```

### 2. No Hardcoded Provider Names
❌ **Don't do this:**
```python
default_providers = ["apt", "brew", "winget"]
```

✅ **Do this instead:**
```python
default_providers = self._get_default_providers()
# or
available_providers = self._get_available_providers()
```

### 3. No Hardcoded Software Names
❌ **Don't do this:**
```python
if software_name in ['nginx', 'apache']:
    return "web-server"
```

✅ **Do this instead:**
```python
# Check repository data for category
for pkg in context.repository_data:
    if pkg.category and 'web' in pkg.category.lower():
        return "web-server"
```

## Working with Repository Data

### Accessing Repository Information
```python
# Repository data is available in GenerationContext
for pkg in context.repository_data:
    # Package metadata
    name = pkg.name
    version = pkg.version
    description = pkg.description
    
    # Repository metadata
    repo_type = pkg.repository_type  # e.g., "apt", "brew"
    repo_name = pkg.repository_name
    
    # URLs and links
    homepage = pkg.homepage
    download_url = pkg.download_url
    
    # Dependencies and metadata
    dependencies = pkg.dependencies
    license = pkg.license
    category = pkg.category
```

### Getting Provider Information
```python
# Get default providers from config or repository manager
default_providers = self._get_default_providers()

# Get all available providers
available_providers = self._get_available_providers()

# Check if repository manager is available
if self.repository_cache and hasattr(self.repository_cache, 'manager'):
    supported_types = self.repository_cache.manager.get_supported_types()
```

## Adding New Features

### When Adding Provider Support
1. Add repository configuration to appropriate YAML file:
   - `saigen/repositories/configs/linux-repositories.yaml`
   - `saigen/repositories/configs/macos-repositories.yaml`
   - `saigen/repositories/configs/windows-repositories.yaml`

2. No code changes needed in generation_engine.py!

### When Adding Software Detection Logic
1. Use repository data first:
```python
def _detect_software_category(self, software_name: str, context: GenerationContext) -> str:
    # Check repository data
    for pkg in context.repository_data:
        if pkg.category:
            return self._map_category(pkg.category)
    
    # Fallback to generic keyword matching
    if 'server' in software_name.lower():
        return "server"
```

2. Avoid hardcoding specific software names

### When Generating Metadata
1. Extract from repository data:
```python
def _generate_urls(self, context: GenerationContext) -> Dict[str, str]:
    urls = {}
    for pkg in context.repository_data:
        if pkg.homepage:
            urls["website"] = pkg.homepage
        if hasattr(pkg, 'source_url') and pkg.source_url:
            urls["source"] = pkg.source_url
    return urls
```

2. Return empty/None if data not available:
```python
def _generate_security_metadata(self, context: GenerationContext) -> Dict[str, Any]:
    if hasattr(context, 'security_info') and context.security_info:
        return context.security_info
    return {}  # Don't generate fake data
```

## Testing

### Mock Repository Data
```python
# In tests, provide mock repository data
mock_package = RepositoryPackage(
    name="test-package",
    version="1.0.0",
    repository_type="apt",
    repository_name="ubuntu-main",
    homepage="https://example.org",
    category="web"
)

context = GenerationContext(
    software_name="test",
    target_providers=["apt"],
    repository_data=[mock_package]
)
```

### Mock Repository Manager
```python
# Mock the repository manager for provider queries
mock_manager = Mock()
mock_manager.get_supported_types.return_value = ["apt", "brew", "winget"]
engine.repository_cache.manager = mock_manager
```

## Common Patterns

### Pattern: Extract Data with Fallback
```python
def _get_license(self, context: GenerationContext) -> Optional[str]:
    # Try repository data first
    for pkg in context.repository_data:
        if pkg.license:
            return pkg.license
    
    # No data available
    return None
```

### Pattern: Build from Repository Data
```python
def _build_compatibility_matrix(self, context: GenerationContext) -> List[Dict]:
    matrix = []
    for pkg in context.repository_data:
        entry = {
            "provider": pkg.repository_type,
            "supported": True,
        }
        if hasattr(pkg, 'platform'):
            entry["platform"] = pkg.platform
        matrix.append(entry)
    return matrix
```

### Pattern: Dynamic Provider Handling
```python
def _process_providers(self, request: GenerationRequest) -> List[str]:
    # Use request providers if specified
    if request.target_providers:
        return request.target_providers
    
    # Otherwise get from config/repository manager
    return self._get_default_providers()
```

## Migration Checklist

When updating existing code:
- [ ] Remove hardcoded provider names
- [ ] Remove hardcoded repository URLs
- [ ] Remove hardcoded software names
- [ ] Use repository data from context
- [ ] Use repository manager for provider info
- [ ] Return None/empty for unavailable data
- [ ] Update tests to provide mock repository data
- [ ] Verify no diagnostics/linting errors

## Questions?

If you need to add provider-specific logic:
1. First check if it can be handled in repository configs
2. If code changes are needed, use dynamic lookups
3. Never hardcode provider names, URLs, or software names

For repository configuration help, see:
- `docs/repository-configuration.md`
- `saigen/repositories/configs/` for examples
