# Saidata 0.3 Generation Issue Analysis

## Problem
Recent `saigen generate` outputs are missing critical top-level sections and producing incomplete saidata files.

### What's Wrong
Generated files only contain:
- metadata
- sources/binaries/scripts (often with invalid data)
- providers (with minimal package lists)

Missing sections:
- packages (top-level)
- services
- files
- directories
- commands
- ports

### Root Cause
The LLM prompt example in `saigen/llm/prompts.py` (lines 570-608) shows an **incomplete structure** that omits the critical top-level sections. The LLM follows this example rather than the full schema description.

**Current Example (WRONG):**
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

**Should Be:**
```yaml
version: "0.3"
metadata: {...}
packages: [...]      # TOP-LEVEL
services: [...]      # TOP-LEVEL
files: [...]         # TOP-LEVEL
directories: [...]   # TOP-LEVEL
commands: [...]      # TOP-LEVEL
ports: [...]         # TOP-LEVEL
sources: [...]       # Optional, only if valid data
binaries: [...]      # Optional, only if valid data
scripts: [...]       # Optional, only if valid data
providers:
  apt:
    packages: [...]  # Provider-specific overrides only when needed
```

### Correct Pattern (from sample files)
The sample files in `docs/saidata_samples/` show the correct structure:
1. **Top-level sections** define the default/common configuration
2. **Provider sections** only override when needed (e.g., upstream repositories)
3. **New 0.3 sections** (sources/binaries/scripts) are optional and only included when valid data exists

## Solution
1. Fix the example structure in the prompt to show all top-level sections
2. Clarify that sources/binaries/scripts are optional and should only be included with valid data
3. Emphasize the pattern: top-level defaults + provider-specific overrides
4. Improve sample saidata formatting to highlight structure

## Changes Made

### 1. Updated Example Structure (lines ~570-680)
Added comprehensive example showing:
- All top-level sections (packages, services, files, directories, commands, ports)
- Clear comments explaining the pattern
- Provider sections with overrides
- Notes about when to include optional sections

### 2. Updated Schema Requirements (lines ~487-520 and ~844-877)
Reorganized the schema documentation to:
- Separate top-level resource sections from optional installation methods
- Mark important sections with "IMPORTANT - include when relevant"
- Clarify that sources/binaries/scripts are optional and need verified data

### 3. Updated Output Instructions (lines ~690-705)
Added explicit instruction to:
- "ALWAYS include top-level sections: packages, services, files, directories, commands, ports (when relevant)"
- "Only include sources/binaries/scripts if you have valid, verified data (don't guess)"

### 4. Improved Sample Formatting (lines ~256-310)
Enhanced `_format_sample_saidata()` to:
- Show top-level structure counts
- Display example packages and services
- Add note about the correct pattern

## Testing Recommendations
1. Test generation with nginx to verify it produces the correct structure
2. Compare output with sample files in `docs/saidata_samples/`
3. Verify that sources/binaries/scripts are only included when appropriate
4. Check that provider sections contain overrides, not duplicates

## Files Updated
- `saigen/llm/prompts.py` - Multiple sections updated
- `docs/summaries/saidata-generation-issue-analysis.md` - This document
