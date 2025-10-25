# Requirements Document: Provider Version Refresh Enhancement

## Introduction

This specification defines enhancements to the existing `saigen refresh-versions` command to support OS-specific saidata files and comprehensive repository configurations. The goal is to enable accurate package name and version updates from package providers across different operating system versions, without LLM inference.

## Glossary

- **Saidata**: YAML files containing software metadata following the saidata 0.3 schema
- **Provider**: Package management system (apt, brew, dnf, etc.)
- **Repository**: Specific package repository instance (e.g., apt-ubuntu-jammy, apt-debian-bookworm)
- **OS-Specific Saidata**: Saidata files that override defaults for specific OS versions (e.g., ubuntu/22.04.yaml)
- **Default Saidata**: Base saidata file (default.yaml) containing generic/upstream information
- **Codename**: Distribution release codename (e.g., jammy for Ubuntu 22.04, bookworm for Debian 12)
- **Refresh-Versions Command**: Existing SAIGEN CLI command that updates package versions from repositories
- **Repository Configuration**: YAML files defining repository endpoints, parsing rules, and metadata

## Current State Analysis

### Existing Implementation

The `saigen refresh-versions` command currently:
- Loads a single saidata file
- Queries repositories by provider name (apt, brew, etc.)
- Updates version fields in packages, binaries, sources, scripts
- Does not distinguish between OS versions
- Uses generic repository configurations (e.g., "ubuntu-main" only supports jammy/22.04)

### Current Repository Configuration Gaps

From `saigen/repositories/configs/linux-repositories.yaml`:
- **Ubuntu**: Only jammy (22.04) configured as "ubuntu-main"
- **Debian**: Only bookworm (12) configured as "debian-main"
- **Fedora**: Only F39 configured
- **Missing**: Ubuntu 20.04, 24.04; Debian 10, 11; Fedora 38, 40; Rocky 8, 9; etc.

### Current Saidata Structure

Saidata files follow hierarchical structure:
```
software/ng/nginx/
  default.yaml           # Generic/upstream defaults
  ubuntu/
    22.04.yaml          # Ubuntu 22.04 specific overrides
    24.04.yaml          # Ubuntu 24.04 specific overrides
  debian/
    11.yaml             # Debian 11 specific overrides
```

**Merge behavior**: OS-specific files override default.yaml fields

## Requirements

### Requirement 1: Default Saidata Version Policy

**User Story**: As a saidata maintainer, I want default.yaml to contain upstream/official versions, so that it represents the canonical software version independent of OS packaging.

#### Acceptance Criteria

1. WHEN default.yaml is created or updated, THE System SHALL set the top-level packages version field to the latest official upstream release version
2. WHEN a package name is consistent across all OS versions for a provider, THE System SHALL include that package_name in default.yaml provider section
3. WHEN a package name differs for specific OS versions, THE System SHALL include the common package_name in default.yaml and only override in OS-specific files where it differs
4. THE System SHALL NOT include version information in default.yaml provider sections, as versions are OS-specific
5. THE System SHALL document that default.yaml top-level versions represent upstream releases, not OS-packaged versions

### Requirement 2: OS-Specific Repository Configuration

**User Story**: As a system administrator, I want repositories configured for all major OS versions I support, so that I can get accurate package information for each OS.

#### Acceptance Criteria

1. THE System SHALL provide repository configurations for Windows package managers (choco, winget)
2. THE System SHALL provide repository configurations for macOS package manager (brew)
3. THE System SHALL provide repository configurations for Ubuntu versions 20.04, 22.04, 24.04, and 26.04
4. THE System SHALL provide repository configurations for Debian versions 9, 10, 11, 12, and 13
5. THE System SHALL provide repository configurations for Rocky Linux versions 8, 9, and 10
6. THE System SHALL provide repository configurations for AlmaLinux versions 8, 9, and 10
7. THE System SHALL provide repository configurations for RHEL versions 7, 8, 9, and 10 (lower priority)
8. THE System SHALL provide repository configurations for CentOS Stream versions 8, 9, and 10 (lower priority)
9. THE System SHALL provide repository configurations for SLES versions 12 and 15 (lower priority)
10. THE System SHALL provide repository configurations for openSUSE Leap 15 (lower priority)
11. THE System SHALL provide repository configurations for openSUSE Tumbleweed (lower priority)
12. THE System SHALL provide repository configurations for Arch Linux (lower priority)
13. THE System SHALL provide repository configurations for Gentoo (lower priority)
14. THE System SHALL provide repository configurations for Linux Mint 22 (lower priority)
15. THE System SHALL provide repository configurations for NixOS (lower priority)
16. WHEN a repository configuration is defined, THE System SHALL include the OS version to codename mapping directly in the repository YAML file
17. THE System SHALL name repositories using the pattern: `{provider}-{os}-{codename}` (e.g., apt-ubuntu-jammy, apt-debian-bookworm, choco-windows, brew-macos)

### Requirement 3: Codename to Version Mapping in Repository Configuration

**User Story**: As a developer, I want OS version to codename mappings stored in repository configurations, so that the mapping is maintained alongside the repository definition.

#### Acceptance Criteria

1. THE System SHALL store OS version to codename mappings directly in repository YAML configuration files
2. WHEN a repository configuration is defined, THE System SHALL include a `version_mapping` field containing version-to-codename pairs
3. THE System SHALL support version mappings for Ubuntu (20.04→focal, 22.04→jammy, 24.04→noble, 26.04→oracular)
4. THE System SHALL support version mappings for Debian (9→stretch, 10→buster, 11→bullseye, 12→bookworm, 13→trixie)
5. THE System SHALL support version mappings for Fedora (38→f38, 39→f39, 40→f40, 41→f41, 42→f42)
6. THE System SHALL support version mappings for Rocky/Alma (8→8, 9→9, 10→10)
7. WHEN an OS version is provided, THE System SHALL look up the codename from the repository configuration
8. WHEN a codename cannot be resolved, THE System SHALL log a warning and skip that OS version
9. THE System SHALL validate version_mapping fields when loading repository configurations

### Requirement 4: OS-Specific File Detection

**User Story**: As a saidata maintainer, I want the refresh command to detect OS information from file paths, so that it queries the correct repository for each OS-specific file.

#### Acceptance Criteria

1. WHEN a saidata file path contains `{os}/{version}.yaml`, THE System SHALL extract the OS and version information
2. WHEN processing `ubuntu/22.04.yaml`, THE System SHALL identify OS as "ubuntu" and version as "22.04"
3. WHEN processing `debian/11.yaml`, THE System SHALL identify OS as "debian" and version as "11"
4. WHEN processing `default.yaml`, THE System SHALL treat it as OS-agnostic
5. WHEN OS information cannot be extracted from the path, THE System SHALL log a warning and treat the file as OS-agnostic

### Requirement 5: Repository Selection by OS

**User Story**: As a saidata maintainer, I want the refresh command to query OS-specific repositories, so that I get accurate package names and versions for each OS.

#### Acceptance Criteria

1. WHEN refreshing an OS-specific saidata file, THE System SHALL query the repository matching that OS and version
2. WHEN refreshing `ubuntu/22.04.yaml` with provider "apt", THE System SHALL query repository "apt-ubuntu-jammy"
3. WHEN refreshing `debian/11.yaml` with provider "apt", THE System SHALL query repository "apt-debian-bullseye"
4. WHEN the required repository is not configured, THE System SHALL log a warning and skip that file
5. WHEN refreshing `default.yaml`, THE System SHALL NOT query OS-specific repositories

### Requirement 6: Directory-Wide Refresh

**User Story**: As a saidata maintainer, I want to refresh all saidata files in a directory at once, so that I can efficiently update all OS variants.

#### Acceptance Criteria

1. WHEN a directory path is provided to refresh-versions, THE System SHALL discover all YAML files in that directory
2. WHEN the `--all-variants` flag is used, THE System SHALL process both default.yaml and all OS-specific files
3. WHEN processing multiple files, THE System SHALL query the appropriate repository for each file based on its OS context
4. THE System SHALL display a summary showing updates per file
5. WHEN a file fails to update, THE System SHALL continue processing remaining files and report errors at the end

### Requirement 7: Package Name Updates

**User Story**: As a saidata maintainer, I want to update both package names and versions, so that OS-specific package naming differences are captured.

#### Acceptance Criteria

1. WHEN querying a repository for a package, THE System SHALL retrieve both the package name and version
2. WHEN the repository package name differs from the saidata package_name, THE System SHALL update the package_name field
3. WHEN updating package_name, THE System SHALL log the change (old_name → new_name)
4. THE System SHALL preserve the logical name field unchanged
5. WHEN a package is not found in the repository, THE System SHALL log a warning and leave the package_name unchanged

### Requirement 8: OS-Specific File Creation

**User Story**: As a saidata maintainer, I want the refresh command to create OS-specific files when they don't exist, so that I can populate version information for new OS versions.

#### Acceptance Criteria

1. WHEN an OS-specific file does not exist and the `--create-missing` flag is used, THE System SHALL create the file
2. WHEN creating an OS-specific file, THE System SHALL query the appropriate repository for that OS version
3. WHEN creating an OS-specific file, THE System SHALL only include fields that differ from default.yaml
4. WHEN creating an OS-specific file, THE System SHALL always include provider-specific version information
5. WHEN creating an OS-specific file, THE System SHALL include package_name only if it differs from default.yaml
6. WHEN creating an OS-specific file, THE System SHALL use the minimal YAML structure (only providers section with necessary overrides)
7. WHEN the `--create-missing` flag is not used, THE System SHALL skip non-existent files and log a warning
8. THE System SHALL create the necessary directory structure (e.g., `ubuntu/` directory) if it doesn't exist

### Requirement 9: Default.yaml Refresh Policy

**User Story**: As a saidata maintainer, I want clear guidance on when to refresh default.yaml, so that I maintain accurate upstream version information.

#### Acceptance Criteria

1. WHEN refreshing default.yaml, THE System SHALL only update the top-level packages version field
2. THE System SHALL NOT update provider-specific version fields in default.yaml
3. WHEN the `--skip-default` flag is used, THE System SHALL skip default.yaml and only process OS-specific files
4. THE System SHALL document that default.yaml versions should represent upstream releases
5. WHEN default.yaml is refreshed, THE System SHALL query a configurable "default OS" repository (e.g., latest Ubuntu LTS)

### Requirement 10: Validation and Safety

**User Story**: As a saidata maintainer, I want the refresh operation to be safe and reversible, so that I can recover from incorrect updates.

#### Acceptance Criteria

1. WHEN refreshing multiple files, THE System SHALL create backups for each file before modification
2. WHEN the `--check-only` flag is used, THE System SHALL show what would be updated without modifying any files
3. WHEN updates are applied, THE System SHALL validate the updated saidata against the schema
4. WHEN schema validation fails, THE System SHALL restore from backup and report the error
5. THE System SHALL display a diff summary showing all changes before applying them in interactive mode

### Requirement 11: Repository Configuration Completeness

**User Story**: As a system administrator, I want comprehensive repository configurations, so that I can refresh saidata for all supported OS versions.

#### Acceptance Criteria

1. THE System SHALL provide repository configurations for all OS versions listed in Requirement 2
2. THE System SHALL organize repository configurations by provider type (e.g., apt.yaml, dnf.yaml, brew.yaml)
3. WHEN a repository configuration is added, THE System SHALL include endpoint URLs, parsing rules, cache settings, and version_mapping
4. THE System SHALL support software-specific upstream repositories (e.g., HashiCorp repository for HashiCorp packages)
5. THE System SHALL allow multiple repositories per provider-OS combination to support upstream vendor repositories
6. THE System SHALL validate repository configurations on startup
7. WHEN a repository configuration is invalid, THE System SHALL log an error and disable that repository
8. THE System SHALL provide a command to list all available repositories (saigen repositories list-repos)
9. WHEN listing repositories, THE System SHALL show OS version support and codename mappings
10. THE System SHALL support both bulk download repositories (apt, dnf) and API-based query repositories (npm, pip, cargo, winget)
11. WHEN a repository uses API-based queries, THE System SHALL query the API per package rather than downloading full package lists
12. THE System SHALL cache API-based query results with appropriate TTL to minimize redundant API calls

### Requirement 14: API-Based Repository Support

**User Story**: As a developer, I want the system to support API-based package repositories, so that I can query packages from registries that don't provide bulk downloads.

#### Acceptance Criteria

1. THE System SHALL support repositories that require per-package API queries (npm, pip, cargo, winget, rubygems, maven, nuget)
2. WHEN a repository is configured as API-based, THE System SHALL use the search or info endpoint for each package query
3. THE System SHALL cache API query results to avoid redundant requests during the same refresh operation
4. THE System SHALL respect API rate limits by implementing request throttling
5. WHEN an API rate limit is exceeded, THE System SHALL log a warning and retry with exponential backoff
6. THE System SHALL support API authentication for repositories that require it (tokens, API keys)
7. WHEN querying API-based repositories, THE System SHALL use concurrent requests with configurable concurrency limits
8. THE System SHALL provide configuration options for API timeout, retry attempts, and rate limiting per repository

## Non-Functional Requirements

### Performance

1. THE System SHALL complete directory-wide refresh operations in under 30 seconds for 10 files
2. THE System SHALL use cached repository data by default to minimize network requests
3. THE System SHALL support concurrent repository queries for improved performance

### Usability

1. THE System SHALL provide clear progress indicators during multi-file refresh operations
2. THE System SHALL display human-readable diffs showing package name and version changes
3. THE System SHALL use color coding to distinguish updates, warnings, and errors

### Maintainability

1. THE System SHALL store OS-to-codename mappings in a centralized, easily updatable configuration
2. THE System SHALL use consistent naming conventions for repositories across all OS types
3. THE System SHALL provide clear error messages when repositories are missing or misconfigured

### Requirement 12: EOL OS Version Support

**User Story**: As a saidata maintainer, I want to keep repository configurations for EOL (end-of-life) OS versions, so that I can maintain historical saidata files.

#### Acceptance Criteria

1. THE System SHALL retain repository configurations for EOL OS versions
2. THE System SHALL retain saidata files for EOL OS versions
3. THE System SHALL mark EOL repositories in configuration metadata
4. WHEN querying an EOL repository, THE System SHALL log an informational message indicating EOL status
5. THE System SHALL continue to support refresh operations for EOL OS versions if repositories remain accessible

### Requirement 13: Saidata Override Validation

**User Story**: As a saidata maintainer, I want to validate that OS-specific files only override necessary fields, so that I avoid unnecessary duplication.

#### Acceptance Criteria

1. THE System SHALL provide a validation command to check OS-specific saidata files
2. WHEN validating an OS-specific file, THE System SHALL compare it against default.yaml
3. THE System SHALL identify fields that are identical to default.yaml and could be removed
4. THE System SHALL report unnecessary duplications as warnings
5. THE System SHALL provide an option to automatically remove unnecessary overrides
6. WHEN a field value differs from default.yaml, THE System SHALL consider it a necessary override

## Out of Scope

The following are explicitly out of scope for this enhancement:

1. Updating fields other than package_name and version (descriptions, URLs, etc.)
2. LLM-based generation or inference
3. Creating new saidata files (only updating existing files)
4. Automatic detection of which OS versions to create files for
5. Merging or consolidating OS-specific files
6. Updating providerdata or applydata files
7. Automatic removal of EOL OS versions or repositories

## Success Criteria

The enhancement will be considered successful when:

1. All major OS versions (Ubuntu 20.04/22.04/24.04, Debian 10/11/12, Fedora 38/39/40, Rocky 8/9) have repository configurations
2. The refresh-versions command can process directory structures with default.yaml and OS-specific files
3. Package names and versions are accurately updated for each OS-specific file
4. Default.yaml maintains upstream version information
5. The system gracefully handles missing repositories with clear warnings
6. Documentation clearly explains the default.yaml version policy and OS-specific refresh behavior

## Dependencies

- Existing refresh-versions command implementation
- Repository manager and cache system
- Saidata 0.3 schema validation
- YAML parsing and serialization

## Assumptions

1. Saidata files follow the hierarchical structure: `software/{prefix}/{name}/[{os}/{version}.yaml|default.yaml]`
2. Repository endpoints are publicly accessible or authentication is configured
3. Package names in repositories match or are discoverable via search
4. OS-specific files only override fields that differ from default.yaml
