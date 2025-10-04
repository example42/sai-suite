# Saidata 0.3 Prompt Refinement Summary

## Issue Identified
The `saigen generate` command was producing incomplete saidata files that were missing critical top-level sections (packages, services, files, directories, commands, ports) and only generating minimal provider configurations.

## Root Cause
The LLM prompt template in `saigen/llm/prompts.py` contained an **incomplete example structure** that showed only:
- metadata
- sources/binaries/scripts (new 0.3 features)
- providers

This caused the LLM to follow the example rather than the full schema description, resulting in incomplete output.

## Changes Made

### 1. Post-Processing Deduplication (NEW)
**Location:** `saigen/core/generation_engine.py` - `_deduplicate_provider_configs()`

Added comprehensive automatic deduplication of provider configurations to remove redundant entries that exactly match top-level definitions. This works across ALL resource types.

**Resource Types Handled:**
- Packages
- Services
- Files
- Directories
- Commands
- Ports

**Logic:**
- Compares each provider resource with corresponding top-level resources
- Removes provider resources that are identical (same key fields, no additional config)
- Keeps provider resources that have differences (different values, additional config)
- Logs removed duplicates for debugging

**Key Comparison:**
- Packages: (name, package_name)
- Services: (name, service_name)
- Files: (name, path)
- Directories: (name, path)
- Commands: (name, path)
- Ports: (port, protocol)

**Example:**
```yaml
# Before deduplication
packages:
  - name: nginx
    package_name: nginx

providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx  # Duplicate - will be removed
  dnf:
    packages:
      - name: nginx
        package_name: nginx  # Duplicate - will be removed

# After deduplication
packages:
  - name: nginx
    package_name: nginx

providers:
  apt:
    packages: []  # Empty, removed
  dnf:
    packages: []  # Empty, removed
```

### 2. Provider Override Guidance (NEW)
**Location:** `saigen/llm/prompts.py` - Added "WHEN TO USE PROVIDER OVERRIDES" section

Added explicit guidance and examples for when provider overrides are needed, using Apache as a real-world example.

**Key Scenarios:**
- Different package names (apache2 vs httpd)
- Different paths (/etc/apache2 vs /etc/httpd)
- Different service names (apache2 vs httpd)
- Different directory structures

**Example Provided:**
Shows complete Apache configuration with Debian/Ubuntu as top-level and RHEL/CentOS overrides in dnf provider, demonstrating:
- Top-level uses most common conventions
- Provider overrides for platform-specific differences
- All resource types (packages, services, files, directories, commands)

### 3. Enhanced Example Structure (SAIDATA_GENERATION_TEMPLATE)
**Location:** `saigen/llm/prompts.py` lines ~570-680

**Before:**
```yaml
version: "0.3"
metadata: {...}
sources: [...]
binaries: [...]
scripts: [...]
providers:
  apt:
    packages: [...]
```

**After:**
```yaml
version: "0.3"
metadata: {...}

# TOP-LEVEL SECTIONS (define defaults/common config)
packages: [...]
services: [...]
files: [...]
directories: [...]
commands: [...]
ports: [...]

# OPTIONAL: Only include if you have valid, verified data
sources: [...]

# PROVIDER SECTIONS (overrides and provider-specific configs)
providers:
  apt:
    packages: [...]
    repositories: [...]  # Only if upstream repos exist
```

### 2. Reorganized Schema Requirements
**Location:** `saigen/llm/prompts.py` lines ~487-520 and ~844-877

Restructured the schema documentation into clear categories:
- **Top-Level Resource Sections** - marked as "IMPORTANT - include when relevant"
- **Optional Installation Method Sections** - marked as "only include with valid, verified data"
- **Provider and Compatibility Sections**

This makes it clear that:
- Top-level sections define defaults/common configuration
- Provider sections contain overrides
- New 0.3 sections (sources/binaries/scripts) are optional

### 3. Updated Output Instructions
**Location:** `saigen/llm/prompts.py` lines ~690-705

Added explicit instructions:
- "ALWAYS include top-level sections: packages, services, files, directories, commands, ports (when relevant)"
- "Only include sources/binaries/scripts if you have valid, verified data (don't guess)"
- "Follow the structure pattern from the reference samples provided"

### 4. Improved Sample Saidata Formatting
**Location:** `saigen/llm/prompts.py` lines ~256-310

Enhanced the `_format_sample_saidata()` function to:
- Show structure overview (counts of packages, services, files, etc.)
- Display example top-level package and service
- Add explanatory note about the correct pattern
- Limit to 2 full examples instead of 3 to save token space

## Correct Saidata 0.3 Pattern

### Structure Pattern
1. **Top-level sections** define the default/common configuration that applies across all providers
2. **Provider sections** contain provider-specific overrides or additional configurations (like upstream repositories)
3. **New 0.3 sections** (sources, binaries, scripts) are optional and should only be included when you have valid, verified data

### When to Include Sections

**Always Include (when relevant):**
- `packages` - Almost always needed
- `services` - For daemon/service software
- `files` - For config files, logs, etc.
- `directories` - For data/config directories
- `commands` - For CLI tools
- `ports` - For network services

**Optional (only with verified data):**
- `sources` - Only if you have verified build information
- `binaries` - Only if you have verified download URLs
- `scripts` - Only if you have verified installation scripts

**Provider Overrides:**
- Use provider sections to override top-level defaults
- Include `repositories` only for upstream/third-party repos
- Don't duplicate top-level data in provider sections unless overriding

## Testing

Created test script: `scripts/development/test_prompt_improvements.py`

Test results:
- ✅ All required phrases present in schema requirements
- ✅ Example structure includes all top-level sections
- ✅ Output instructions emphasize top-level sections
- ✅ Template structure is correct

## Expected Impact

After these changes, `saigen generate` should produce saidata files that:
1. Include all relevant top-level sections (packages, services, files, directories, commands, ports)
2. Have provider sections with appropriate overrides (duplicates automatically removed)
3. Only include sources/binaries/scripts when valid data is available
4. Match the structure of sample files in `docs/saidata_samples/`
5. No redundant provider package entries that duplicate top-level definitions

## Next Steps

1. **Test with real generation**: Run `saigen generate nginx` and compare output with `docs/saidata_samples/ng/nginx/default.yaml`
2. **Verify other software**: Test with docker, redis, etc. to ensure consistent results
3. **Monitor quality**: Check that sources/binaries/scripts are only included when appropriate
4. **Update documentation**: If needed, update user-facing docs to reflect the correct pattern

## Files Modified

- `saigen/core/generation_engine.py` - Added deduplication logic
- `saigen/llm/prompts.py` - Multiple sections updated
- `docs/summaries/saidata-generation-issue-analysis.md` - Analysis document
- `docs/summaries/prompt-refinement-summary.md` - This summary
- `scripts/development/test_prompt_improvements.py` - Prompt structure test
- `scripts/development/test_deduplication.py` - Deduplication test

## References

- Sample files: `docs/saidata_samples/`
- Schema: `schemas/saidata-0.3.json`
- Generation engine: `saigen/core/generation_engine.py`
