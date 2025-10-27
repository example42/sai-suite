# Provider Version Refresh Enhancement Spec

## Overview

This specification defines enhancements to the existing `saigen refresh-versions` command to support OS-specific saidata files and comprehensive repository configurations, enabling accurate package name and version updates across different operating system versions without LLM inference.

## Spec Documents

- **[requirements.md](./requirements.md)** - Detailed requirements with user stories and acceptance criteria
- **[context.md](./context.md)** - Background, current state analysis, and design decisions
- **[tasks.md](./tasks.md)** - Implementation task breakdown with dependencies and estimates
- **[REPOSITORY-CONFIG-REORGANIZATION.md](./REPOSITORY-CONFIG-REORGANIZATION.md)** - Guide for reorganizing configs by provider
- **[FILE-CREATION-FEATURE.md](./FILE-CREATION-FEATURE.md)** - OS-specific file creation feature details
- **[CLARIFICATION.md](./CLARIFICATION.md)** - Default.yaml package name policy clarification

## Quick Summary

### Problem Statement

The current `refresh-versions` command:
- Only supports single OS version per provider (e.g., Ubuntu 22.04 only)
- Cannot distinguish between OS-specific saidata files
- Only updates versions, not package names
- Lacks repository configurations for most OS versions

### Solution

Enhance the command to:
1. Support multiple OS versions with dedicated repository configurations
2. Detect OS information from file paths (e.g., `ubuntu/22.04.yaml`)
3. Query OS-specific repositories for accurate package data
4. Update both package names and versions
5. Process entire directories with multiple OS variants
6. Maintain upstream versions in `default.yaml`

### Key Features

1. **Comprehensive OS-Specific Repository Configurations**
   - **High Priority**: Windows (choco, winget), macOS (brew), Ubuntu (4 versions), Debian (5 versions), Rocky/Alma (6 versions) = 18 repositories
   - **Lower Priority**: Fedora (5), RHEL (4), CentOS Stream (3), SLES (2), openSUSE (2), Arch, Gentoo, Mint, NixOS = 17 repositories
   - **Total**: 35+ repositories across all major platforms
   - **Organization**: Provider-based files (apt.yaml, dnf.yaml, brew.yaml) instead of platform-based
   - Version-to-codename mapping stored in repository YAML files
   - Support for software-specific upstream repositories (e.g., HashiCorp)
   - Consistent naming: `{provider}-{os}-{codename}`

2. **OS Detection**
   - Extract OS/version from file paths
   - Map to appropriate repository
   - Handle `default.yaml` specially

3. **Package Name Updates**
   - Update both `package_name` and `version` fields
   - Handle OS-specific naming differences
   - Log all changes clearly

4. **Directory-Wide Refresh**
   - Process all saidata files in directory
   - `--all-variants` flag for batch operations
   - Per-file error handling and reporting

5. **OS-Specific File Creation**
   - Create missing OS-specific files with `--create-missing` flag
   - Automatically query repositories for new OS versions
   - Generate minimal YAML (only fields that differ from default.yaml)
   - Create directory structure as needed

6. **Default.yaml Policy**
   - Maintain upstream/official versions
   - Include common provider package names
   - Skip provider-specific versions
   - `--skip-default` flag available

## Usage Examples

### Current (Single File)
```bash
saigen refresh-versions nginx.yaml
```

### Enhanced (OS-Specific)
```bash
# Refresh Ubuntu 22.04 specific file
saigen refresh-versions ng/nginx/ubuntu/22.04.yaml --provider apt

# Refresh all OS variants in directory
saigen refresh-versions ng/nginx/ --all-variants --providers apt,dnf

# Create missing OS-specific files (e.g., for new Ubuntu 26.04)
saigen refresh-versions ng/nginx/ --all-variants --create-missing --providers apt

# Check what would be updated
saigen refresh-versions ng/nginx/ --all-variants --check-only

# Skip default.yaml, only refresh OS-specific files
saigen refresh-versions ng/nginx/ --all-variants --skip-default
```

## Implementation Phases

1. **Repository Configuration Expansion** (20-28 hours)
   - **Reorganize** config files from platform-based to provider-based (apt.yaml, dnf.yaml, etc.)
   - Add 33+ OS-version repositories (Windows, macOS, Linux variants)
   - Include version_mapping in each repository config
   - Support software-specific upstream repositories

2. **Codename Resolution from Repository Config** (3-4 hours)
   - Load version_mapping from repository YAML files
   - Implement resolution logic using repository configs

3. **OS Detection & Repository Selection** (7-10 hours)
   - Parse file paths for OS info
   - Select appropriate repositories using version_mapping

4. **Package Name Updates** (4-6 hours)
   - Enhance query to retrieve names
   - Update both name and version fields

5. **Directory-Wide Refresh** (6-8 hours)
   - Implement multi-file processing
   - Add summary reporting

6. **OS-Specific File Creation** (6-8 hours)
   - Implement file creation with --create-missing
   - Generate minimal YAML structures
   - Compare with default.yaml

7. **Validation & Safety** (7-10 hours)
   - Enhanced validation and safety features
   - Saidata override validation
   - Repository listing enhancements

8. **Documentation & Testing** (18-23 hours)
   - Update all documentation
   - Comprehensive testing across all platforms
   - Test file creation scenarios

**Total Estimated Effort**: 73-100 hours

## Success Criteria

- ✅ 35+ OS-version-specific repositories configured (Windows, macOS, Linux variants)
- ✅ Version-to-codename mappings stored in repository configurations
- ✅ Accurate package name/version updates per OS
- ✅ Directory refresh completes in <30s for 10 files
- ✅ Graceful handling of missing repositories
- ✅ Support for EOL OS versions maintained
- ✅ Validation of unnecessary OS-specific overrides
- ✅ Support for software-specific upstream repositories
- ✅ Enhanced repository listing with version support
- ✅ Clear documentation of default.yaml policy

## Key Design Decisions

### 1. Default.yaml Version Policy
**Decision**: Include top-level upstream versions and common provider package names; never include provider-specific versions

**Rationale**: 
- Top-level version represents upstream/official release
- Provider package names should be included if consistent across OS versions (e.g., `apache2` for apt)
- Only override package names in OS-specific files when they differ
- Versions are always OS-specific and never in default.yaml provider sections

**Example**: Apache is `apache2` in apt across most OS versions → include in default.yaml. Only override in specific OS files if different (e.g., `apache2-bin` on Debian 9).

### 2. OS Detection Strategy
**Decision**: Extract OS info from file path pattern `{software}/{os}/{version}.yaml`

**Rationale**: Explicit, predictable, matches existing saidata structure

### 3. Repository Naming
**Decision**: Use pattern `{provider}-{os}-{codename}`

**Rationale**: Clear, consistent, supports multiple versions per OS

### 4. Codename Mapping Storage
**Decision**: Store version-to-codename mappings in repository YAML files using `version_mapping` field

**Rationale**: Keeps mapping with repository definition, easier maintenance, no separate config file needed

### 5. Missing Repository Handling
**Decision**: Skip with warning, continue processing

**Rationale**: Graceful degradation, allows partial updates

### 6. Package Name Updates
**Decision**: Update both package_name and version fields

**Rationale**: Package names differ across OS versions, both need accuracy

### 7. EOL OS Version Support
**Decision**: Keep repository configurations and saidata for EOL versions

**Rationale**: Maintains historical compatibility, users may still need EOL support

### 8. Override Validation
**Decision**: Provide validation to detect unnecessary duplications in OS-specific files

**Rationale**: Reduces maintenance burden, prevents confusion from duplicate data

### 9. Software-Specific Repositories
**Decision**: Support vendor-specific upstream repositories alongside distribution repositories

**Rationale**: Many vendors provide their own repositories (HashiCorp, Docker, etc.) with different versions than distributions

## Dependencies

- Existing `refresh-versions` command implementation
- Repository manager and cache system
- Saidata 0.3 schema validation
- YAML parsing and serialization

## Out of Scope

- Updating fields other than package_name and version
- LLM-based generation or inference
- Creating new saidata files
- Automatic OS version detection
- Merging or consolidating OS-specific files

## Next Steps

1. Review requirements with stakeholders
2. Validate design decisions
3. Begin Phase 1: Repository Configuration Expansion
4. Implement incrementally, testing each phase
5. Update documentation as features are completed

## Design Questions - RESOLVED

All design questions have been resolved:

1. ✅ **Codename mappings**: Store in repository YAML files using `version_mapping` field
2. ✅ **EOL OS versions**: Keep configurations and saidata, mark as EOL in metadata
3. ✅ **Override validation**: Yes, provide validation command to detect unnecessary duplications
4. ✅ **Repository listing**: Yes, enhance existing `saigen repositories list-repos` command
5. ✅ **Upstream repositories**: Yes, support software-specific vendor repositories

## References

- Existing implementation: `saigen/cli/commands/refresh_versions.py`
- Repository configs: `saigen/repositories/configs/*.yaml`
- Documentation: `saigen/docs/refresh-versions-command.md`
- Saidata schema: `schemas/saidata-0.3-schema.json`
- Tech documentation: `.kiro/steering/tech.md`
