# Requirements Document

## Introduction

The SAI CLI tool needs to be updated to support the saidata-0.3-schema.json format. This update introduces new capabilities including sources, binaries, and scripts installation methods, enhanced package structure with package_name field, and updated provider configurations. The SAI tool must be able to load, validate, and process saidata files in the 0.3 format, and the template engine must support the new field names and structures.

**Note**: Backward compatibility with schema 0.2 is not required. All saidata files will use schema 0.3.

## Glossary

- **SAI**: the CLI tool for executing software management actions
- **Saidata**: YAML/JSON files containing software metadata and installation instructions
- **Template Engine**: The Jinja2-based system that resolves template variables in provider actions
- **Provider**: A package manager or installation method (apt, brew, source, binary, script, etc.)
- **Schema 0.3**: The new saidata schema version with enhanced installation methods
- **Package Name**: The actual package name used by package managers (new in 0.3)
- **Logical Name**: The internal reference name used for cross-referencing (name field in 0.3)

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want SAI to load and validate saidata files using the 0.3 schema, so that I can use saidata files with the latest format.

#### Acceptance Criteria

1. WHEN loading saidata files THEN the SaidataLoader SHALL use the saidata-0.3-schema.json for validation
2. WHEN validating saidata THEN the system SHALL accept version "0.3" in saidata files
3. WHEN validating saidata THEN the system SHALL validate the new top-level sections: sources, binaries, scripts
4. WHEN validating saidata THEN the system SHALL validate provider-specific sources, binaries, scripts arrays
5. WHEN validation fails THEN the system SHALL provide clear error messages indicating schema 0.3 requirements

### Requirement 2

**User Story:** As a developer, I want the SAI data models to support the 0.3 schema structure, so that saidata files with new fields can be properly loaded and processed.

#### Acceptance Criteria

1. WHEN defining Package model THEN the system SHALL include both name (logical name) and package_name (actual package name) fields
2. WHEN defining Package model THEN the system SHALL require both name and package_name fields
3. WHEN defining ProviderConfig model THEN the system SHALL include sources, binaries, scripts arrays
4. WHEN defining Repository model THEN the system SHALL include sources, binaries, scripts arrays
5. WHEN defining SaiData model THEN the system SHALL include top-level sources, binaries, scripts arrays

### Requirement 3

**User Story:** As a developer, I want new Pydantic models for sources, binaries, and scripts, so that these installation methods can be properly validated and processed.

#### Acceptance Criteria

1. WHEN defining Source model THEN the system SHALL include fields: name, url, version, build_system, build_dir, source_dir, install_prefix
2. WHEN defining Source model THEN the system SHALL include arrays: configure_args, build_args, install_args, prerequisites
3. WHEN defining Source model THEN the system SHALL include custom_commands object with download, extract, configure, build, install, uninstall, validation, version
4. WHEN defining Binary model THEN the system SHALL include fields: name, url, version, architecture, platform, checksum, install_path, executable, permissions
5. WHEN defining Binary model THEN the system SHALL include archive object with format, strip_prefix, extract_path
6. WHEN defining Binary model THEN the system SHALL include custom_commands object
7. WHEN defining Script model THEN the system SHALL include fields: name, url, version, interpreter, checksum, timeout, working_dir
8. WHEN defining Script model THEN the system SHALL include arrays: arguments and environment object
9. WHEN defining Script model THEN the system SHALL include custom_commands object

### Requirement 4

**User Story:** As a system administrator, I want the template engine to support the new package_name field, so that provider actions can reference the correct package names.

#### Acceptance Criteria

1. WHEN using sai_package template function THEN the system SHALL support a field parameter to specify which field to extract
2. WHEN using sai_package with field='package_name' THEN the system SHALL return the package_name field value
3. WHEN using sai_package with field='name' THEN the system SHALL return the logical name field value
4. WHEN using sai_package without field parameter THEN the system SHALL default to 'package_name' for backward compatibility
5. WHEN package_name is not available THEN the system SHALL fall back to the name field

### Requirement 5

**User Story:** As a provider maintainer, I want updated provider YAML files to use the new sai_package function signature, so that actions reference the correct package names from saidata.

#### Acceptance Criteria

1. WHEN provider actions use sai_package function THEN the system SHALL support the signature: sai_package(index_or_wildcard, field, provider_name)
2. WHEN provider actions specify field='package_name' THEN the system SHALL extract the package_name field
3. WHEN provider actions use wildcard '*' as index THEN the system SHALL return all package names joined with space
4. WHEN provider actions use numeric index THEN the system SHALL return the package name at that index
5. WHEN provider_name is specified THEN the system SHALL look up provider-specific packages first before falling back to general packages

### Requirement 6

**User Story:** As a developer, I want the template context builder to include sources, binaries, and scripts in the context, so that template functions can access these new installation methods.

#### Acceptance Criteria

1. WHEN building template context THEN the system SHALL include sources array from saidata
2. WHEN building template context THEN the system SHALL include binaries array from saidata
3. WHEN building template context THEN the system SHALL include scripts array from saidata
4. WHEN building template context THEN the system SHALL include provider-specific sources, binaries, scripts
5. WHEN sources/binaries/scripts are not present THEN the system SHALL provide empty arrays

### Requirement 7

**User Story:** As a system administrator, I want new template functions for accessing sources, binaries, and scripts, so that provider actions can reference these installation methods.

#### Acceptance Criteria

1. WHEN using sai_source template function THEN the system SHALL return source configuration by index and field
2. WHEN using sai_binary template function THEN the system SHALL return binary configuration by index and field
3. WHEN using sai_script template function THEN the system SHALL return script configuration by index and field
4. WHEN using these functions with provider_name THEN the system SHALL look up provider-specific configurations first
5. WHEN configurations are not found THEN the system SHALL return empty string

### Requirement 8

**User Story:** As a provider maintainer, I want the source, binary, and script providers to be functional, so that software can be installed using these new methods.

#### Acceptance Criteria

1. WHEN using source provider THEN the system SHALL download source code from URL with template variable substitution
2. WHEN using source provider THEN the system SHALL extract source archives and execute build commands based on build_system
3. WHEN using binary provider THEN the system SHALL download binaries from URL with platform/architecture template substitution
4. WHEN using binary provider THEN the system SHALL extract archives and install binaries to install_path
5. WHEN using script provider THEN the system SHALL download and execute installation scripts with security validation
6. WHEN using script provider THEN the system SHALL verify checksums before execution

### Requirement 9

**User Story:** As a developer, I want comprehensive tests for the 0.3 schema support, so that the SAI tool correctly handles all new features.

#### Acceptance Criteria

1. WHEN testing saidata loading THEN the system SHALL verify 0.3 schema files load correctly
2. WHEN testing template functions THEN the system SHALL verify sai_package with package_name field works correctly
3. WHEN testing template functions THEN the system SHALL verify sai_source, sai_binary, sai_script functions work correctly
4. WHEN testing provider actions THEN the system SHALL verify source, binary, script providers execute correctly
5. WHEN testing validation THEN the system SHALL verify schema 0.3 validation catches errors correctly

