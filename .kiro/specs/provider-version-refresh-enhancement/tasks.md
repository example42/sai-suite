# Implementation Tasks: Provider Version Refresh Enhancement

## Overview

This document outlines the implementation tasks for enhancing the `saigen refresh-versions` command to support OS-specific saidata files and comprehensive repository configurations.

## Current Implementation Status

✅ **Completed:**
- Basic refresh-versions command exists and works for single files
- Repository manager with universal YAML-driven system
- Repository configurations exist for: Ubuntu 22.04 (jammy), Debian 12 (bookworm), Fedora 39
- Package version querying and updating works

❌ **Not Implemented:**
- Provider-specific repository configuration files (currently using platform-based files)
- OS-specific saidata file detection and processing
- version_mapping field in repository configurations
- Codename resolution from repository configs
- Directory-wide refresh with --all-variants flag
- OS-specific file creation with --create-missing flag
- Package name updates (currently only version updates)
- Repository configurations for most OS versions (20.04, 24.04, Rocky, Alma, Windows, macOS, etc.)
- Override validation command

## Task List

- [-] 1. Repository Configuration Expansion
  - [x] 1.0 Reorganize repository configuration files (PREREQUISITE - MUST DO FIRST)
    - Create new provider-specific files in saigen/repositories/configs/:
      - apt.yaml (for all apt-based distros)
      - dnf.yaml (for all dnf/yum-based distros)
      - brew.yaml (for macOS)
      - choco.yaml (for Windows Chocolatey)
      - winget.yaml (for Windows winget)
      - zypper.yaml (for SUSE-based distros)
      - pacman.yaml (for Arch-based distros)
      - apk.yaml (for Alpine)
      - emerge.yaml (for Gentoo)
      - npm.yaml, pip.yaml, cargo.yaml, etc. (for language package managers)
    - Migrate existing repository configurations from old files to new provider-specific files
    - Delete old files: linux-repositories.yaml, macos-repositories.yaml, windows-repositories.yaml, language-repositories.yaml
    - Update repository loader in saigen/repositories/universal_manager.py to load from new file structure
    - Update all code references to use new file names
    - Test that existing functionality works with new structure
    - _Requirements: 11.2_
  
  - [x] 1.1 Add Windows repository configurations (HIGH PRIORITY)
    - Add choco-windows configuration
    - Add winget-windows configuration
    - Include version_mapping field (if applicable)
    - Test endpoint connectivity
    - _Requirements: 2.1, 2.16, 2.17_
  
  - [x] 1.2 Add macOS repository configurations (HIGH PRIORITY)
    - Add brew-macos configuration
    - Include version_mapping field (if applicable)
    - Test endpoint connectivity
    - _Requirements: 2.2, 2.16, 2.17_
  
  - [x] 1.3 Add Ubuntu repository configurations (HIGH PRIORITY)
    - Add apt-ubuntu-focal (20.04) configuration
    - Add apt-ubuntu-noble (24.04) configuration
    - Add apt-ubuntu-oracular (26.04) configuration
    - Include version_mapping field: {20.04: focal, 22.04: jammy, 24.04: noble, 26.04: oracular}
    - Test endpoint connectivity
    - _Requirements: 2.3, 2.16, 2.17, 3.3_
  
  - [x] 1.4 Add Debian repository configurations (HIGH PRIORITY)
    - Add apt-debian-stretch (9) configuration
    - Add apt-debian-buster (10) configuration
    - Add apt-debian-bullseye (11) configuration
    - Add apt-debian-trixie (13) configuration
    - Include version_mapping field: {9: stretch, 10: buster, 11: bullseye, 12: bookworm, 13: trixie}
    - Test endpoint connectivity
    - _Requirements: 2.4, 2.16, 2.17, 3.4_
  
  - [x] 1.5 Add Rocky/Alma repository configurations (HIGH PRIORITY)
    - Add dnf-rocky-8, dnf-rocky-9, dnf-rocky-10 configurations
    - Add dnf-alma-8, dnf-alma-9, dnf-alma-10 configurations
    - Include version_mapping field: {8: 8, 9: 9, 10: 10}
    - Test endpoint connectivity
    - _Requirements: 2.5, 2.6, 2.16, 2.17, 3.6_
  
  - [x] 1.6 Add Fedora repository configurations (LOWER PRIORITY)
    - Add dnf-fedora-38, dnf-fedora-39, dnf-fedora-40, dnf-fedora-41, dnf-fedora-42 configurations
    - Include version_mapping field: {38: f38, 39: f39, 40: f40, 41: f41, 42: f42}
    - Test endpoint connectivity
    - _Requirements: 2.3, 2.16, 2.17, 3.5_
  
  - [x] 1.7 Add RHEL repository configurations (LOWER PRIORITY)
    - Add dnf-rhel-7, dnf-rhel-8, dnf-rhel-9, dnf-rhel-10 configurations
    - Include version_mapping field
    - Note: May require subscription/authentication
    - Test endpoint connectivity
    - _Requirements: 2.7, 2.16, 2.17_
  
  - [x] 1.8 Add CentOS Stream repository configurations (LOWER PRIORITY)
    - Add dnf-centos-8, dnf-centos-9, dnf-centos-10 configurations
    - Include version_mapping field
    - Test endpoint connectivity
    - _Requirements: 2.8, 2.16, 2.17_
  
  - [x] 1.9 Add SUSE repository configurations (LOWER PRIORITY)
    - Add zypper-sles-12, zypper-sles-15 configurations
    - Add zypper-opensuse-leap-15 configuration
    - Add zypper-opensuse-tumbleweed configuration
    - Include version_mapping field
    - Test endpoint connectivity
    - _Requirements: 2.9, 2.10, 2.11, 2.16, 2.17_
  
  - [x] 1.10 Add other Linux distribution configurations (LOWER PRIORITY)
    - Add pacman-arch configuration
    - Add emerge-gentoo configuration
    - Add apt-mint-22 configuration with version_mapping
    - Add nix-nixos configuration
    - Test endpoint connectivity
    - _Requirements: 2.12, 2.13, 2.14, 2.15, 2.16, 2.17_
  
  - [x] 1.11 Update repository schema for version_mapping
    - Update schemas/repository-config-schema.json to add three new optional properties to Repository definition:
      - version_mapping: object with patternProperties for version→codename mapping
      - eol: boolean (default: false)
      - query_type: enum ["bulk_download", "api"] (default: "bulk_download")
    - Add version_mapping field to RepositoryInfo model in saigen/models/repository.py (Optional[Dict[str, str]])
    - Add eol field to RepositoryInfo model (bool = False)
    - Add query_type field to RepositoryInfo model (str = "bulk_download")
    - Add runtime validation in universal_manager.py for version_mapping format
    - Update repository configuration loader to read and validate new fields
    - Test schema validation with example repository configs
    - _Requirements: 3.2, 3.9_
  
  - [x] 1.12 Add support for software-specific upstream repositories
    - Document pattern for vendor-specific repositories (e.g., hashicorp-apt-ubuntu)
    - Add example configurations for common upstream repos (HashiCorp, Docker, etc.)
    - Support multiple repositories per provider-OS combination
    - _Requirements: 10.3, 10.4_
  
  - [x] 1.13 Add API-based repository support
    - Add `query_type` field to repository configuration (bulk_download vs api)
    - Implement API query logic for per-package requests
    - Add rate limiting configuration (requests_per_minute, concurrent_requests)
    - Implement request throttling and exponential backoff
    - Add API authentication support (tokens, API keys)
    - Cache API query results with appropriate TTL
    - Add timeout and retry configuration
    - _Requirements: 11.10, 11.11, 11.12, 14.1-14.8_
  
  - [x] 1.14 Validate all repository configurations
    - Create validation script for repository configs
    - Test all repository endpoints (both bulk and API)
    - Verify parsing configurations
    - Verify version_mapping fields
    - Test API rate limiting and authentication
    - Document any endpoint issues
    - Mark EOL repositories in metadata
    - _Requirements: 11.6, 11.7, 12.3_a`

- [x] 2. Codename Resolution from Repository Configuration
  - [x] 2.1 Implement repository configuration loader with version_mapping (MERGED WITH 1.11)
    - This is now part of task 1.11
    - _Requirements: 3.2, 3.9_
  
  - [x] 2.2 Implement codename resolution from repository config
    - Create `saigen/repositories/codename_resolver.py`
    - Implement `resolve_codename(repository_info, version)` function
    - Implement `resolve_repository_name(provider, os, version, repositories)` function
    - Look up codename from repository's version_mapping field
    - Handle unknown versions gracefully
    - _Requirements: 3.7, 3.8_
  
  - [x] 2.3 Integrate codename resolver with repository manager
    - Modify RepositoryManager to use codename resolver
    - Update repository lookup logic to query version_mapping
    - Add logging for codename resolution
    - Cache resolved mappings for performance
    - _Requirements: 3.7_
  
  - [x] 2.4 Add tests for codename resolution
    - Test all OS/version combinations from repository configs
    - Test unknown version handling
    - Test repository name resolution
    - Test version_mapping validation
    - _Requirements: 3.1-3.9_

- [x] 3. OS Detection from File Paths
  - [x] 3.1 Implement file path parser
    - Create `saigen/utils/saidata_path.py` (or add to existing path_utils.py)
    - Implement `extract_os_info(file_path)` function
    - Support pattern: `{prefix}/{software}/{os}/{version}.yaml` (e.g., ng/nginx/ubuntu/22.04.yaml)
    - Support pattern: `{prefix}/{software}/default.yaml` (e.g., ng/nginx/default.yaml)
    - Handle `default.yaml` as OS-agnostic (return None for os/version)
    - Return structured OS info: dict with keys 'os', 'version', 'is_default'
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [x] 3.2 Add OS detection to refresh command
    - Modify `refresh_versions()` command in saigen/cli/commands/refresh_versions.py to detect OS from file path
    - Call `extract_os_info()` on saidata_file path
    - Pass OS context (os, version) to `_refresh_versions()` function
    - Log detected OS information when verbose mode enabled
    - _Requirements: 4.1, 5.1_
  
  - [x] 3.3 Add tests for path parsing
    - Test Ubuntu path patterns
    - Test Debian path patterns
    - Test default.yaml handling
    - Test invalid path patterns
    - _Requirements: 4.1-4.5_

- [x] 4. OS-Specific Repository Selection
  - [x] 4.1 Implement repository selection logic
    - Modify `_query_package_version()` in refresh_versions.py to accept OS context (os, version)
    - Use codename resolver to build repository name: `{provider}-{os}-{codename}`
    - Query OS-specific repository when OS context provided (e.g., apt-ubuntu-jammy)
    - Fall back to generic provider name when no OS context (e.g., apt)
    - Log which repository is being queried
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 4.2 Add repository availability checking
    - In `_query_package_version()`, check if resolved repository name exists in repo_manager
    - Log warning when OS-specific repository not found (e.g., "Repository apt-ubuntu-noble not configured")
    - Return None gracefully when repository missing (don't fail entire operation)
    - Add to result.warnings list for user visibility
    - _Requirements: 5.4, 6.4_
  
  - [x] 4.3 Handle default.yaml special case
    - When is_default=True from OS detection, pass None for OS context to `_refresh_versions()`
    - This ensures default.yaml queries generic repositories, not OS-specific ones
    - Add `--skip-default` flag to refresh_versions command
    - When --skip-default is set and file is default.yaml, skip processing
    - Document that default.yaml should contain upstream versions
    - _Requirements: 5.5, 9.1, 9.2, 9.3, 9.4_
  
  - [x] 4.4 Add tests for repository selection
    - Test OS-specific repository selection
    - Test missing repository handling
    - Test default.yaml handling
    - _Requirements: 5.1-5.5_

- [x] 5. Package Name Updates
  - [x] 5.1 Enhance package query to retrieve name
    - Modify `_query_package_version()` to return dict with 'name' and 'version' keys (instead of just version string)
    - Extract package name from RepositoryPackage.name field
    - Handle cases where repository name differs from queried name
    - Update all callers to handle new return format
    - _Requirements: 7.1_
  
  - [x] 5.2 Implement package name comparison
    - In `_refresh_versions()`, compare retrieved package_name with pkg_info['package_name']
    - Detect when package name differs (name_changed = retrieved_name != current_name)
    - Track name changes separately in result.updates (add 'old_name' and 'new_name' fields)
    - _Requirements: 7.2_
  
  - [x] 5.3 Update package name in saidata
    - Modify `_update_package_version()` to accept both new_version and new_package_name parameters
    - Update pkg_obj.package_name when new_package_name provided
    - Preserve pkg_obj.name (logical name) unchanged
    - Log package name changes when verbose mode enabled
    - _Requirements: 7.2, 7.3, 7.4_
  
  - [x] 5.4 Enhance result display for name changes
    - Update `_display_results()` to check for 'old_name' and 'new_name' in update dict
    - When name changed: format as "provider: old_name v1.0 → new_name v2.0"
    - When only version changed: keep current format "provider/package: v1.0 → v2.0"
    - Use different color/symbol for name changes vs version-only changes
    - _Requirements: 7.3_
  
  - [x] 5.5 Handle package not found gracefully
    - Log warning when package not found
    - Leave package_name unchanged
    - Continue processing other packages
    - _Requirements: 7.5_
  
  - [x] 5.6 Add tests for package name updates
    - Test name change detection
    - Test name update in saidata
    - Test display of name changes
    - Test not-found handling
    - _Requirements: 7.1-7.5_

- [x] 6. Directory-Wide Refresh
  - [x] 6.1 Implement directory scanning
    - Modify refresh_versions command to accept directory path (not just file)
    - Check if saidata_file argument is a directory using Path.is_dir()
    - Scan directory recursively for all .yaml files (including subdirectories like ubuntu/, debian/)
    - Filter for saidata files by checking for 'version' and 'metadata' fields
    - Return list of Path objects to process
    - _Requirements: 6.1_
  
  - [x] 6.2 Add `--all-variants` flag
    - Add `--all-variants` boolean flag to refresh_versions command
    - When flag is set and argument is directory, process all saidata files found
    - When flag is not set and argument is directory, show error message
    - Document flag in command help text
    - _Requirements: 6.2_
  
  - [x] 6.3 Implement multi-file processing
    - Create loop to process each file in the list
    - For each file: detect OS context, load saidata, run refresh, save results
    - Wrap each file processing in try-except to handle errors gracefully
    - Continue processing remaining files even if one fails
    - Collect VersionRefreshResult from each file into a list
    - _Requirements: 6.3, 6.5_
  
  - [x] 6.4 Add summary reporting
    - Create `_display_multi_file_results()` function
    - Display summary table with columns: File, Updates, Unchanged, Failed, Time
    - Show total updates across all files at bottom
    - List any files that failed with error messages
    - Show total execution time for all files
    - _Requirements: 6.4_
  
  - [x] 6.5 Handle backup for multiple files
    - Call `_create_backup()` for each file before modification (already implemented)
    - Use existing backup naming pattern: {filename}.backup.{timestamp}.yaml
    - Log backup location for each file when verbose mode enabled
    - Store backup paths in results for potential rollback
    - _Requirements: 10.1_
  
  - [x] 6.6 Add tests for directory refresh
    - Test directory scanning
    - Test multi-file processing
    - Test error handling (continue on failure)
    - Test summary reporting
    - _Requirements: 6.1-6.5_

- [x] 7. OS-Specific File Creation
  - [x] 7.1 Implement file existence checking
    - During directory scan, identify potential OS-specific files that don't exist
    - Check for pattern: if default.yaml exists, check for ubuntu/22.04.yaml, ubuntu/24.04.yaml, etc.
    - Build list of missing OS-specific files based on configured repositories
    - Log missing files with OS/version information when verbose
    - _Requirements: 8.7_
  
  - [x] 7.2 Add `--create-missing` flag
    - Add `--create-missing` boolean flag to refresh_versions command
    - When flag is set, create OS-specific files that don't exist
    - When flag is not set, skip missing files and log warning
    - Document flag in command help text
    - _Requirements: 8.1, 8.7_
  
  - [x] 7.3 Implement OS-specific file creation logic
    - Create `_create_os_specific_file()` function
    - Load default.yaml to get baseline data
    - Query OS-specific repository for package versions and names
    - Build minimal YAML with only providers section
    - Include provider-specific version (always)
    - Include package_name only if it differs from default.yaml
    - Use yaml.dump() to write file with proper formatting
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6_
  
  - [x] 7.4 Implement directory structure creation
    - In `_create_os_specific_file()`, use Path.mkdir(parents=True, exist_ok=True)
    - Create OS directory if it doesn't exist (e.g., software/ng/nginx/ubuntu/)
    - Set appropriate permissions (default is fine)
    - Log directory creation when verbose mode enabled
    - _Requirements: 8.8_
  
  - [x] 7.5 Add comparison with default.yaml during creation
    - In `_create_os_specific_file()`, load default.yaml first
    - Compare queried package_name with default.yaml package_name
    - Only include package_name in OS-specific file if different
    - Always include version (since it's OS-specific)
    - Document this logic in code comments
    - _Requirements: 8.3, 8.5_
  
  - [x] 7.6 Add tests for file creation
    - Test file creation with --create-missing
    - Test directory creation
    - Test minimal YAML structure
    - Test field comparison with default.yaml
    - Test behavior without --create-missing flag
    - _Requirements: 8.1-8.8_

- [x] 8. Enhanced Validation and Safety
  - [x] 8.1 Add schema validation after updates
    - After saving updated saidata, validate against saidata-0.3-schema.json
    - Use existing validator from saigen/core/validator.py
    - If validation fails, restore from backup using shutil.copy2()
    - Log validation errors with details
    - _Requirements: 10.3, 10.4_
  
  - [x] 8.2 Enhance check-only mode for multi-file
    - In multi-file processing, respect check_only flag for each file
    - Show what would be updated for each file (don't save)
    - Display total changes across all files in summary
    - Ensure no files are modified when check_only=True
    - _Requirements: 10.2_
  
  - [x] 8.3 Add interactive diff display
    - Add `--interactive` flag to refresh_versions command
    - When set, show diff of changes before applying
    - Use click.style() for color coding (green for additions, red for removals)
    - Prompt user with click.confirm() before saving changes
    - _Requirements: 10.5_
  
  - [x] 8.4 Add integration tests for safety features
    - Test backup creation
    - Test validation and rollback
    - Test check-only mode
    - _Requirements: 10.1-10.5_

- [x] 9. Saidata Override Validation
  - [x] 9.1 Implement saidata comparison logic
    - Create `saigen/core/override_validator.py` (or add to existing validator.py)
    - Implement `compare_saidata_files(os_specific_file, default_file)` function
    - Load both files and compare field by field
    - Identify fields that are identical between files (unnecessary duplicates)
    - Identify fields that differ (necessary overrides)
    - Return dict with 'identical_fields' and 'different_fields' lists
    - _Requirements: 13.2, 13.3_
  
  - [x] 9.2 Add validation command
    - Create new command in saigen/cli/commands/validate.py: `validate_overrides()`
    - Accept saidata file or directory path as argument
    - For each OS-specific file, compare with default.yaml
    - Report unnecessary duplications as warnings
    - Show which fields could be removed with their paths
    - Display summary of findings
    - _Requirements: 13.1, 13.4_
  
  - [x] 9.3 Add automatic cleanup option
    - Add `--remove-duplicates` flag to validate_overrides command
    - When set, automatically remove fields identical to default.yaml
    - Create backup before modification using existing `_create_backup()` function
    - Rebuild YAML file without duplicate fields
    - Report what was removed (field paths and values)
    - _Requirements: 13.5_
  
  - [x] 9.4 Add tests for override validation
    - Test comparison logic
    - Test duplicate detection
    - Test automatic cleanup
    - _Requirements: 13.1-13.6_

- [x] 10. Repository Listing Enhancement
  - [x] 10.1 Enhance list-repos command
    - Modify list_repos() in saigen/cli/repositories.py
    - Display version_mapping field for each repository
    - Show OS versions supported (from version_mapping keys)
    - Show codename mappings (version → codename pairs)
    - Add `--os` filter option to show only repos for specific OS
    - Add `--version` filter option to show only repos for specific version
    - _Requirements: 11.8, 11.9_
  
  - [x] 10.2 Add EOL status display
    - Add 'eol' boolean field to repository metadata in YAML configs
    - Display EOL status in list-repos output (e.g., "[EOL]" badge)
    - Add `--eol` filter flag to show only EOL repositories
    - Add `--active` filter flag to show only active (non-EOL) repositories
    - Document EOL repositories in repository configuration guide
    - _Requirements: 12.3, 12.4_
  
  - [x] 10.3 Add tests for enhanced listing
    - Test version_mapping display
    - Test EOL status display
    - Test filtering options
    - _Requirements: 11.7, 11.8, 12.3_

- [x] 11. Documentation Updates
  - [x] 11.1 Update refresh-versions command documentation
    - Update saigen/docs/refresh-versions-command.md (or create if missing)
    - Document new flags: --all-variants, --skip-default, --create-missing, --interactive
    - Add examples for single file refresh
    - Add examples for directory refresh with --all-variants
    - Add examples for creating missing OS-specific files
    - Document OS detection behavior from file paths
    - Explain default.yaml version policy (upstream versions)
    - Document EOL OS version support
    - _Requirements: 1.5, 9.1, 9.2, 9.3, 9.4, 12.1, 12.2_
  
  - [x] 11.2 Create repository configuration guide
    - Create saigen/docs/repository-configuration-guide.md
    - Document repository naming convention: {provider}-{os}-{codename}
    - Explain version_mapping field structure and purpose
    - Provide examples for adding new OS versions to existing configs
    - Document validation process for repository configs
    - Document software-specific upstream repositories (e.g., hashicorp-apt-ubuntu)
    - Provide template for new repository configuration
    - _Requirements: 2.16, 2.17, 3.2, 11.1, 11.2, 11.3_
  
  - [x] 11.3 Update saidata structure documentation
    - Update existing saidata documentation (likely in saigen/docs/)
    - Document default.yaml vs OS-specific files hierarchy
    - Explain merge behavior (OS-specific overrides default.yaml)
    - Provide examples of OS-specific overrides (package_name, version)
    - Document version policy (default.yaml = upstream, OS-specific = packaged)
    - Document override validation with validate-overrides command
    - Document OS-specific file creation with --create-missing
    - _Requirements: 1.5, 9.2, 9.3, 9.4, 13.1_
  
  - [x] 11.4 Create troubleshooting guide
    - Create saigen/docs/refresh-versions-troubleshooting.md
    - Document common issues: missing repositories, package not found, network errors
    - Provide solutions and workarounds for each issue
    - Include debugging tips (use --verbose, check repository configs)
    - Document EOL repository handling and warnings
    - Document how to add missing repository configurations
    - _Requirements: 11.6, 11.7, 12.5_
  
  - [x] 11.5 Update repository schema documentation
    - Update repository configuration schema documentation
    - Document version_mapping field structure: Dict[str, str]
    - Provide examples of version_mapping for Ubuntu, Debian, Fedora, Rocky/Alma
    - Document validation rules (must be dict, keys and values must be strings)
    - Add to repository configuration guide
    - _Requirements: 3.2, 3.9_

- [x] 12. Testing and Validation
  - [x] 12.1 Create integration test suite
    - Test end-to-end refresh for single file
    - Test directory-wide refresh
    - Test OS-specific repository selection
    - Test package name and version updates
    - Test Windows/macOS repository support
    - Test OS-specific file creation with --create-missing
    - _Requirements: All_
  
  - [x] 12.2 Test with real saidata files
    - Test with nginx saidata (multiple OS versions including Windows/macOS)
    - Test with apache saidata
    - Test with postgresql saidata
    - Test with HashiCorp software (upstream repo)
    - Test creating missing OS-specific files
    - Verify accuracy of updates
    - _Requirements: All_
  
  - [x] 12.3 Performance testing
    - Measure refresh time for single file
    - Measure refresh time for directory (10 files)
    - Verify <30s target for directory refresh
    - Test with 33+ repositories configured
    - Test file creation performance
    - Optimize if needed
    - _Requirements: Performance NFR_
  
  - [x] 12.4 Error handling testing
    - Test missing repository handling
    - Test package not found handling
    - Test invalid saidata handling
    - Test network errors
    - Test EOL repository access
    - Test file creation failures
    - _Requirements: 5.4, 6.5, 7.5, 8.7, 12.5_
  
  - [x] 12.5 Test override validation
    - Test duplicate detection
    - Test automatic cleanup
    - Test with various OS-specific files
    - _Requirements: 13.1-13.6_
  
  - [x] 12.6 Test file creation scenarios
    - Test creating single OS-specific file
    - Test creating multiple files in directory
    - Test directory structure creation
    - Test minimal YAML generation
    - Test field comparison with default.yaml
    - _Requirements: 8.1-8.8_

## Task Dependencies

```
1. Repository Configuration Expansion (1.1-1.12)
   ↓
2. Codename Resolution from Repository Configuration (2.1-2.4)
   ↓
3. OS Detection from File Paths (3.1-3.3)
   ↓
4. OS-Specific Repository Selection (4.1-4.4)
   ↓
5. Package Name Updates (5.1-5.6)
   ↓
6. Directory-Wide Refresh (6.1-6.6)
   ↓
7. OS-Specific File Creation (7.1-7.6)
   ↓
8. Enhanced Validation and Safety (8.1-8.4)
   ↓
9. Saidata Override Validation (9.1-9.4)
   ↓
10. Repository Listing Enhancement (10.1-10.3)
   ↓
11. Documentation Updates (11.1-11.5)
   ↓
12. Testing and Validation (12.1-12.6)
```

## Implementation Phases

### Phase 0: Repository File Reorganization (PREREQUISITE)
**Tasks:** 1.0
**Estimated:** 4-6 hours
**Goal:** Reorganize repository configs into provider-specific files
**Note:** MUST be completed before any other tasks

### Phase 1: Core Infrastructure (HIGH PRIORITY)
**Tasks:** 1.11, 2.2, 2.3, 3.1, 3.2, 4.1, 4.2, 4.3
**Estimated:** 12-16 hours
**Goal:** Enable OS-specific repository selection for single files

### Phase 2: Package Name Updates (HIGH PRIORITY)
**Tasks:** 5.1, 5.2, 5.3, 5.4, 5.5
**Estimated:** 4-6 hours
**Goal:** Support updating both package names and versions

### Phase 3: High-Priority Repository Configs (HIGH PRIORITY)
**Tasks:** 1.1, 1.2, 1.3, 1.4, 1.5
**Estimated:** 8-12 hours
**Goal:** Add Windows, macOS, Ubuntu, Debian, Rocky/Alma repositories

### Phase 4: Directory-Wide Refresh (MEDIUM PRIORITY)
**Tasks:** 6.1, 6.2, 6.3, 6.4, 6.5
**Estimated:** 6-8 hours
**Goal:** Enable processing multiple files at once

### Phase 5: OS-Specific File Creation (MEDIUM PRIORITY)
**Tasks:** 7.1, 7.2, 7.3, 7.4, 7.5
**Estimated:** 6-8 hours
**Goal:** Automatically create missing OS-specific files

### Phase 6: Enhanced Safety & Validation (MEDIUM PRIORITY)
**Tasks:** 8.1, 8.2, 8.3
**Estimated:** 3-4 hours
**Goal:** Add schema validation and interactive mode

### Phase 7: Override Validation (LOWER PRIORITY)
**Tasks:** 9.1, 9.2, 9.3
**Estimated:** 4-6 hours
**Goal:** Detect and remove unnecessary duplicates

### Phase 8: Additional Repository Configs (LOWER PRIORITY)
**Tasks:** 1.6, 1.7, 1.8, 1.9, 1.10, 1.12, 1.13, 1.14
**Estimated:** 12-16 hours
**Goal:** Add remaining OS versions and API-based repos

### Phase 9: Repository Listing & Documentation (LOWER PRIORITY)
**Tasks:** 10.1, 10.2, 11.1, 11.2, 11.3, 11.4, 11.5
**Estimated:** 10-14 hours
**Goal:** Enhance tooling and complete documentation

**Total Estimated Effort (excluding optional tests)**: 69-96 hours

## Recommended Implementation Order

1. **MUST START HERE:** Phase 0 (Repository Reorganization) - prerequisite for everything else
2. Phase 1 (Core Infrastructure) - enables basic OS-specific refresh
3. Phase 2 (Package Name Updates) - completes single-file functionality
4. Phase 3 (High-Priority Repos) - provides immediate value for common OSes
5. Phase 4 (Directory Refresh) - enables batch operations
6. Phase 5 (File Creation) - automates OS-specific file management
7. Remaining phases can be done as needed based on priority

## Notes

- Tasks marked with `*` are optional testing tasks that can be skipped for MVP
- Repository configuration expansion can be done incrementally (start with high-priority OSes)
- Core infrastructure (Phase 1-2) should be completed first to enable OS-specific refresh
- Directory-wide refresh (Phase 4) builds on single-file functionality
- File creation (Phase 5) is independent and can be done in parallel with other phases
- Documentation should be updated as features are implemented, not at the end
- The existing refresh-versions command provides a solid foundation - most changes are enhancements rather than rewrites
