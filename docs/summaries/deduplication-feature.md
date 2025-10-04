# Provider Deduplication Feature

## Overview
Comprehensive automatic removal of redundant provider configurations that duplicate top-level definitions across ALL resource types (packages, services, files, directories, commands, ports).

## Problem
Even with improved prompts, LLMs sometimes generate provider sections that duplicate top-level definitions across multiple resource types:

```yaml
packages:
  - name: nginx
    package_name: nginx

providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx  # Redundant!
  dnf:
    packages:
      - name: nginx
        package_name: nginx  # Redundant!
```

## Solution
Post-process the LLM output to automatically remove redundant provider entries.

## Implementation

### Location
`saigen/core/generation_engine.py` - `_deduplicate_provider_configs()`

### Integration
Called automatically in `_parse_and_validate_yaml()` after validation, before returning the final SaiData object.

### Logic

1. **Build Top-Level Indexes**: Create lookups for all resource types:
   - Packages: indexed by (name, package_name)
   - Services: indexed by (name, service_name)
   - Files: indexed by (name, path)
   - Directories: indexed by (name, path)
   - Commands: indexed by (name, path)
   - Ports: indexed by (port, protocol)

2. **Compare Provider Resources**: For each provider resource, check if it exists in top-level

3. **Check for Differences**: Determine if provider resource has any different configuration:
   
   **Packages:**
   - Different version, alternatives, install_options, repository, checksum, signature, download_url
   
   **Services:**
   - Different type, enabled, config_files, start_command, stop_command
   
   **Files:**
   - Different type, owner, group, mode, backup, template
   
   **Directories:**
   - Different owner, group, mode, create
   
   **Commands:**
   - Different shell_completion, man_page, description
   
   **Ports:**
   - Different service, description

4. **Remove or Keep**:
   - **Remove**: If resource matches top-level exactly with no differences
   - **Keep**: If resource has any different configuration

5. **Clean Up**: Set provider resource lists to None if they become empty

### Example Scenarios

#### Scenario 1: Exact Duplicate (Removed)
```yaml
# Top-level
packages:
  - name: nginx
    package_name: nginx

# Provider (BEFORE)
providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx

# Provider (AFTER) - removed
providers:
  apt:
    packages: []
```

#### Scenario 2: Different Version (Kept)
```yaml
# Top-level
packages:
  - name: nginx
    package_name: nginx
    version: "1.20.1"

# Provider (BEFORE)
providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx
        version: "1.24.0"  # Different version

# Provider (AFTER) - kept because version differs
providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx
        version: "1.24.0"
```

#### Scenario 3: Apache Cross-Platform (Kept)
```yaml
# Top-level (Debian/Ubuntu conventions)
packages:
  - name: main
    package_name: apache2

services:
  - name: main
    service_name: apache2
    config_files: ["/etc/apache2/apache2.conf"]

files:
  - name: config
    path: /etc/apache2/apache2.conf

directories:
  - name: config
    path: /etc/apache2

# Provider (BEFORE)
providers:
  dnf:
    packages:
      - name: main
        package_name: httpd  # Different package name
    services:
      - name: main
        service_name: httpd  # Different service name
        config_files: ["/etc/httpd/conf/httpd.conf"]
    files:
      - name: config
        path: /etc/httpd/conf/httpd.conf  # Different path
    directories:
      - name: config
        path: /etc/httpd  # Different path

# Provider (AFTER) - all kept because they differ
providers:
  dnf:
    packages:
      - name: main
        package_name: httpd
    services:
      - name: main
        service_name: httpd
        config_files: ["/etc/httpd/conf/httpd.conf"]
    files:
      - name: config
        path: /etc/httpd/conf/httpd.conf
    directories:
      - name: config
        path: /etc/httpd
```

#### Scenario 4: Has Repository (Kept)
```yaml
# Top-level
packages:
  - name: nginx
    package_name: nginx

# Provider (BEFORE)
providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx
        repository: "official"

# Provider (AFTER) - kept because has repository
providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx
        repository: "official"
```

## Benefits

1. **Cleaner Output**: No redundant provider entries
2. **Easier Maintenance**: Top-level changes don't need provider updates
3. **Better DRY**: Don't Repeat Yourself principle
4. **LLM Flexibility**: LLM can be verbose, we clean it up
5. **Backward Compatible**: Doesn't break existing saidata files

## Testing

### Unit Test
`scripts/development/test_deduplication.py`

Tests:
- Exact duplicates are removed
- Packages with different versions are kept
- Packages with additional config are kept
- Empty provider package lists are handled

### Integration Test
Generate real saidata and verify:
```bash
saigen generate nginx --output test-nginx.yaml
```

Check that provider sections don't duplicate top-level packages.

## Logging

The function logs removed duplicates at DEBUG level:
```
Removing duplicate package 'nginx' from provider 'apt'
```

Enable debug logging to see deduplication in action:
```bash
saigen generate nginx --log-level debug
```

## Future Enhancements

Potential improvements:
1. ✅ ~~Deduplicate services, files, directories similarly~~ (DONE)
2. Merge provider-specific config back to top-level if all providers have same override
3. Warn if provider resource references non-existent top-level resource
4. Statistics on deduplication (X resources removed from Y providers)
5. Detect when top-level should use different conventions (e.g., if most providers override, maybe top-level is wrong)

## Configuration

Currently automatic with no configuration needed. Could add:
- `--no-deduplicate` flag to disable
- `--deduplicate-aggressive` to also merge similar configs
- Config file option: `deduplication: enabled/disabled/aggressive`

## Performance

Minimal impact:
- O(n*m) where n = provider packages, m = top-level packages
- Typically n and m are small (< 10)
- Runs after validation, before file write
- No network calls or LLM queries

## Compatibility

- Works with all saidata versions (0.2, 0.3)
- Safe for existing workflows
- No breaking changes
- Can be disabled if needed (future enhancement)
