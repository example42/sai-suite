# Requirements Document

## Introduction

The saidata generation system needs to be updated to support the new saidata-0.3-schema.json format. This update introduces significant new capabilities including sources, binaries, and scripts installation methods, enhanced security metadata, and improved provider configuration structure. The update must ensure backward compatibility is not a concern as the saidata tools are not yet published.

## Requirements

### Requirement 1

**User Story:** As a developer, I want the saidata generation system to support the new 0.3 schema structure, so that generated saidata files include the latest installation methods and metadata fields.

#### Acceptance Criteria

1. WHEN generating saidata THEN the system SHALL use version "0.3" in the output files
2. WHEN generating saidata THEN the system SHALL include the new top-level sections: sources, binaries, scripts
3. WHEN generating metadata THEN the system SHALL include security metadata with fields like cve_exceptions, security_contact, vulnerability_disclosure, sbom_url, signing_key
4. WHEN generating metadata THEN the system SHALL include enhanced URLs section with website, documentation, source, issues, support, download, changelog, license, sbom, icon
5. WHEN generating saidata THEN the system SHALL follow the new provider configuration structure with provider-specific overrides

### Requirement 2

**User Story:** As a system administrator, I want the generation system to create comprehensive source build configurations, so that software can be compiled from source code with proper build system support.

#### Acceptance Criteria

1. WHEN generating source configurations THEN the system SHALL include build_system field with values: autotools, cmake, make, meson, ninja, custom
2. WHEN generating source configurations THEN the system SHALL include URL templating with {{version}}, {{platform}}, {{architecture}} placeholders
3. WHEN generating source configurations THEN the system SHALL include configure_args, build_args, install_args arrays
4. WHEN generating source configurations THEN the system SHALL include prerequisites array for required build dependencies
5. WHEN generating source configurations THEN the system SHALL include checksum field with format "algorithm:hash"
6. WHEN generating source configurations THEN the system SHALL include custom_commands object for overriding default build behavior

### Requirement 3

**User Story:** As a DevOps engineer, I want the generation system to create binary download configurations, so that pre-compiled executables can be installed with proper platform and architecture support.

#### Acceptance Criteria

1. WHEN generating binary configurations THEN the system SHALL include URL templating with {{version}}, {{platform}}, {{architecture}} placeholders
2. WHEN generating binary configurations THEN the system SHALL include platform and architecture fields with auto-detection support
3. WHEN generating binary configurations THEN the system SHALL include install_path field defaulting to "/usr/local/bin"
4. WHEN generating binary configurations THEN the system SHALL include archive configuration with format, strip_prefix, extract_path
5. WHEN generating binary configurations THEN the system SHALL include permissions field in octal format
6. WHEN generating binary configurations THEN the system SHALL include custom_commands for download, extract, install, uninstall, validation, version

### Requirement 4

**User Story:** As a security engineer, I want the generation system to create script installation configurations with security measures, so that installation scripts can be executed safely with proper validation.

#### Acceptance Criteria

1. WHEN generating script configurations THEN the system SHALL include checksum field for security verification
2. WHEN generating script configurations THEN the system SHALL include interpreter field with auto-detection from shebang
3. WHEN generating script configurations THEN the system SHALL include timeout field with default 300 seconds and maximum 3600 seconds
4. WHEN generating script configurations THEN the system SHALL include arguments array for script parameters
5. WHEN generating script configurations THEN the system SHALL include environment object for script execution variables
6. WHEN generating script configurations THEN the system SHALL include working_dir field for execution directory

### Requirement 5

**User Story:** As a software maintainer, I want the generation system to create enhanced provider configurations, so that different providers can have specific overrides and extensions for all resource types.

#### Acceptance Criteria

1. WHEN generating provider configurations THEN the system SHALL support provider-specific overrides for packages, services, files, directories, commands, ports, containers
2. WHEN generating provider configurations THEN the system SHALL support provider-specific sources, binaries, scripts arrays
3. WHEN generating provider configurations THEN the system SHALL include prerequisites and build_commands for source compilation
4. WHEN generating provider configurations THEN the system SHALL include package_sources array with priority and recommended fields
5. WHEN generating provider configurations THEN the system SHALL include repositories array with type, priority, recommended, and maintainer fields

### Requirement 6

**User Story:** As a quality engineer, I want the generation system to create comprehensive compatibility matrices, so that software compatibility across providers, platforms, and architectures is clearly documented.

#### Acceptance Criteria

1. WHEN generating compatibility information THEN the system SHALL include compatibility matrix with provider, platform, architecture, os_version fields
2. WHEN generating compatibility information THEN the system SHALL include supported, tested, recommended boolean fields
3. WHEN generating compatibility information THEN the system SHALL support both string and array values for platform, architecture, os_version
4. WHEN generating compatibility information THEN the system SHALL include versions object with latest, minimum, latest_lts, latest_minimum
5. WHEN generating compatibility information THEN the system SHALL include notes field for additional compatibility information

### Requirement 7

**User Story:** As a developer, I want the LLM prompts and generation logic to be updated for the new schema, so that AI-generated saidata files follow the 0.3 format correctly.

#### Acceptance Criteria

1. WHEN using LLM generation THEN the system SHALL update prompts to include examples of sources, binaries, scripts configurations
2. WHEN using LLM generation THEN the system SHALL include security metadata fields in generation prompts
3. WHEN using LLM generation THEN the system SHALL provide examples of URL templating with placeholders
4. WHEN using LLM generation THEN the system SHALL include provider-specific configuration examples
5. WHEN using LLM generation THEN the system SHALL validate generated content against the 0.3 schema

### Requirement 8

**User Story:** As a system integrator, I want the validation system to be updated for the new schema, so that generated saidata files are properly validated against the 0.3 format requirements.

#### Acceptance Criteria

1. WHEN validating saidata THEN the system SHALL use the saidata-0.3-schema.json for validation
2. WHEN validating saidata THEN the system SHALL check required fields: version, metadata with name field
3. WHEN validating saidata THEN the system SHALL validate URL templating syntax in sources, binaries, scripts
4. WHEN validating saidata THEN the system SHALL validate checksum format as "algorithm:hash"
5. WHEN validating saidata THEN the system SHALL validate enum values for build_system, service types, file types, etc.