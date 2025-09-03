# SAI Provider-SaiData Mapping Standard

## Overview

This document defines the standard for mapping between saidata YAML files and provider YAML files in the SAI system. The goal is to create a consistent, flexible mapping that works across all providers and software packages.

## Current Issues

1. **Structure Mismatch**: Provider templates expect object-style access (`saidata.packages.server.name`) but saidata uses array format
2. **Provider Priority**: Platform-specific providers (like brew on macOS) should have higher priority than generic ones
3. **Template Resolution**: Need robust fallback mechanisms when expected fields don't exist

## Proposed Solution

### 1. Enhanced SaiData Structure

The saidata should support both array format (current) and provider-specific mappings:

```yaml
# Standard array format (current)
packages:
  - name: "terraform"
    version: "1.5.0"
    alternatives: ["terraform"]

# Provider-specific mappings (new)
providers:
  brew:
    packages:
      - name: "terraform"
        alternatives: ["terraform"]
  apt:
    packages:
      - name: "terraform"
        version: "1.5.0"
```

### 2. Provider Template Standards

#### Template Access Patterns

Providers should use these standardized template patterns:

```yaml
# Primary package (most common case)
template: "{{provider_name}} install {{saidata.packages[0].name}}"

# Multiple packages with fallback
template: "{{provider_name}} install {% for pkg in saidata.packages %}{{pkg.name}} {% endfor %}"

# Provider-specific package names
template: "{{provider_name}} install {% for pkg in saidata.providers[provider_name].packages %}{{pkg.name}} {% endfor %}"

# Fallback to metadata name if no packages
template: "{{provider_name}} install {{saidata.packages[0].name | default(saidata.metadata.name)}}"
```

#### Recommended Template Structure

```yaml
actions:
  install:
    description: "Install packages via {{provider_name}}"
    template: "{{provider_name}} install {% for pkg in saidata.packages %}{{pkg.name}} {% endfor %}"
    fallback_template: "{{provider_name}} install {{saidata.metadata.name}}"
    timeout: 300
```

### 3. Provider Priority System

Providers should include platform-specific priority:

```yaml
provider:
  name: "brew"
  platforms: ["macos"]
  priority:
    macos: 90  # High priority on macOS
    default: 10  # Low priority elsewhere
```

### 4. Template Engine Enhancements

The template engine should:

1. **Auto-detect array vs object access**: Convert `saidata.packages.server.name` to `saidata.packages[0].name`
2. **Provider-specific fallbacks**: Try provider-specific mappings first, then fall back to general structure
3. **Graceful degradation**: Use metadata.name as ultimate fallback

## Implementation Plan

### Phase 1: Fix Current Issues
1. Update provider templates to use array-based access
2. Implement provider priority system
3. Add template fallback mechanisms

### Phase 2: Enhanced Mapping
1. Add provider-specific sections to saidata
2. Implement smart template resolution
3. Add validation for mapping consistency

### Phase 3: Advanced Features
1. Dynamic provider detection and ranking
2. Cross-provider compatibility checks
3. Automated saidata generation with provider awareness