# Requirements Document

## Introduction

This feature modifies the SAI (Software Action Interface) tool to use a configurable git repository as the source for saidata files instead of the current local directory approach. The default repository will be `https://github.com/example42/saidata`, with fallback to downloading release tarballs when git is unavailable. Additionally, the saidata structure will be reorganized to use a hierarchical directory structure where each software's data is stored in `software/{first_two_letters}/{software_name}/default.yaml` format.

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want SAI to automatically fetch saidata from a configurable git repository, so that I always have access to the latest software definitions without manual updates.

#### Acceptance Criteria

1. WHEN SAI needs saidata THEN the system SHALL attempt to clone or update from the configured git repository
2. WHEN the git repository URL is not configured THEN the system SHALL use `https://github.com/example42/saidata` as the default
3. WHEN git is available on the system THEN the system SHALL use git clone/pull operations to fetch saidata
4. WHEN git is not available on the system THEN the system SHALL download and extract the latest release tarball
5. WHEN the repository fetch fails THEN the system SHALL fall back to any existing cached saidata and log appropriate warnings

### Requirement 2

**User Story:** As a SAI user, I want to configure a custom saidata repository URL, so that I can use my organization's private saidata repository or a fork of the official repository.

#### Acceptance Criteria

1. WHEN I configure a custom repository URL in the SAI configuration THEN the system SHALL use that URL instead of the default
2. WHEN the custom repository URL is invalid or inaccessible THEN the system SHALL provide clear error messages and fallback options
3. WHEN I update the repository URL configuration THEN the system SHALL re-fetch saidata from the new repository on next use
4. IF the repository requires authentication THEN the system SHALL support standard git authentication methods (SSH keys, tokens)

### Requirement 3

**User Story:** As a SAI developer, I want saidata files to be organized in a hierarchical directory structure, so that the repository is more manageable and scalable as the number of software definitions grows.

#### Acceptance Criteria

1. WHEN looking for saidata for software "apache" THEN the system SHALL search in `software/ap/apache/default.yaml`
2. WHEN looking for saidata for software "nginx" THEN the system SHALL search in `software/ng/nginx/default.yaml`
3. WHEN the hierarchical path doesn't exist THEN the system SHALL fall back to legacy flat file locations for backward compatibility
4. WHEN generating new saidata THEN the system SHALL create files in the hierarchical structure format
5. WHEN multiple saidata files exist for the same software THEN the system SHALL merge them according to precedence rules

### Requirement 4

**User Story:** As a SAI user, I want the system to cache downloaded saidata locally, so that I can work offline and avoid repeated network requests.

#### Acceptance Criteria

1. WHEN saidata is fetched from a repository THEN the system SHALL cache it locally in the configured cache directory
2. WHEN the cache is older than the configured TTL THEN the system SHALL attempt to update from the repository
3. WHEN working offline or repository is unavailable THEN the system SHALL use cached saidata with appropriate warnings
4. WHEN cache is corrupted or invalid THEN the system SHALL re-fetch from the repository
5. IF cache directory is not writable THEN the system SHALL operate in read-only mode with appropriate warnings

### Requirement 5

**User Story:** As a system administrator, I want to control repository update behavior, so that I can ensure consistent environments and manage network usage.

#### Acceptance Criteria

1. WHEN I configure auto-update to false THEN the system SHALL only fetch repository data on explicit update commands
2. WHEN I configure update frequency THEN the system SHALL respect the configured interval for automatic updates
3. WHEN I run an explicit update command THEN the system SHALL force refresh from the repository regardless of cache status
4. WHEN running in offline mode THEN the system SHALL not attempt network operations and use only cached data
5. IF repository operations fail repeatedly THEN the system SHALL implement exponential backoff to avoid excessive network requests

### Requirement 6

**User Story:** As a SAI user, I want the system to use the new hierarchical saidata structure exclusively, so that the codebase is clean and maintainable without legacy complexity.

#### Acceptance Criteria

1. WHEN looking for saidata THEN the system SHALL only search the hierarchical structure in the repository
2. WHEN custom saidata paths are configured THEN the system SHALL search those paths using the hierarchical structure
3. WHEN saidata is not found in hierarchical structure THEN the system SHALL provide clear error messages
4. WHEN generating or creating saidata THEN the system SHALL always use the hierarchical structure format
5. IF local saidata files exist in custom paths THEN they SHALL take precedence over repository data for the same software

### Requirement 7

**User Story:** As a SAI developer, I want comprehensive error handling and logging for repository operations, so that I can troubleshoot issues and monitor system behavior.

#### Acceptance Criteria

1. WHEN repository operations fail THEN the system SHALL log detailed error messages including failure reasons
2. WHEN falling back to cached data THEN the system SHALL log warnings about using potentially outdated information
3. WHEN repository authentication fails THEN the system SHALL provide clear guidance on authentication setup
4. WHEN network connectivity issues occur THEN the system SHALL distinguish between temporary and permanent failures
5. WHEN repository structure is invalid THEN the system SHALL provide specific validation error messages

### Requirement 8

**User Story:** As a SAI user, I want the system to validate repository integrity, so that I can trust the saidata being used is authentic and uncorrupted.

#### Acceptance Criteria

1. WHEN fetching from a git repository THEN the system SHALL verify git signatures if available
2. WHEN downloading release tarballs THEN the system SHALL verify checksums if provided
3. WHEN repository content changes unexpectedly THEN the system SHALL detect and report integrity issues
4. WHEN saidata files are corrupted THEN the system SHALL identify specific files and attempt recovery
5. IF repository validation fails THEN the system SHALL refuse to use the data and maintain previous valid cache