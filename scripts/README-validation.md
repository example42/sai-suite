# Repository Configuration Validation

This directory contains scripts for validating repository configurations used by the saigen tool.

## Validation Script

### `validate_repository_configs.py`

Comprehensive validation script that checks all repository configurations in `saigen/repositories/configs/` against the requirements specified in the provider-version-refresh-enhancement spec.

#### Features

- **Structure Validation**: Validates required fields and data types
- **version_mapping Validation**: Checks format and content of OS version mappings
- **Endpoint Validation**: Validates URL format and structure
- **Parsing Configuration**: Checks parsing rules and field mappings
- **Query Type Validation**: Validates bulk_download vs api configuration
- **EOL Status**: Identifies end-of-life repositories
- **Rate Limiting**: Validates API rate limiting configuration
- **Authentication**: Checks authentication configuration
- **Endpoint Connectivity**: Tests actual endpoint URLs (optional)

#### Usage

```bash
# Run validation (from project root)
python scripts/validate_repository_configs.py

# Results are displayed in terminal and saved to:
# scripts/repository_validation_results.json
```

#### Output

The script provides:

1. **Console Output**: Real-time validation progress with color-coded results
   - ✓ Success indicators
   - ⚠ Warning indicators  
   - ✗ Error indicators

2. **JSON Results**: Detailed validation data saved to `repository_validation_results.json`
   - Validation results per repository
   - Endpoint connectivity test results
   - Error and warning details

3. **Summary Report**: High-level statistics
   - Total repositories validated
   - Valid/invalid counts
   - EOL repository list
   - Endpoint test results

#### Validation Criteria

##### Required Fields
- `name`: Repository identifier
- `type`: Provider type (apt, dnf, brew, etc.)
- `platform`: Target platform (linux, macos, windows, universal)
- `endpoints`: URL endpoints for package data
- `parsing`: Parsing configuration

##### Optional Fields (Validated if Present)
- `version_mapping`: OS version to codename mapping
- `eol`: End-of-life status (boolean)
- `query_type`: Query method (bulk_download or api)
- `limits`: Rate limiting configuration (recommended for API repos)
- `auth`: Authentication configuration

##### version_mapping Format
- Must be a dictionary
- Keys: OS version strings (e.g., "22.04", "11", "39")
- Values: Codename strings (e.g., "jammy", "bullseye", "f39")
- Keys should be numeric (e.g., "22.04", not "v22.04")
- Values should be lowercase alphanumeric with hyphens

##### Endpoint Validation
- URLs must have valid scheme (http/https)
- URLs must have valid netloc (domain)
- HTTPS is preferred over HTTP
- Bulk download repos must have 'packages' endpoint
- API repos must have 'search' or 'info' endpoint

##### Query Type Validation
- Must be either "bulk_download" or "api"
- API repos should have rate limiting configuration
- Bulk download repos should have cache configuration

#### Example Output

```
================================================================================
Repository Configuration Validation
================================================================================

Found 22 configuration files

Validating apt.yaml...
  - apt-ubuntu-jammy
    ✓ version_mapping: 1 mapping(s)
    ✓ endpoints: 3 endpoint(s)
    ✓ parsing: format=debian_packages
    ✓ query_type: bulk_download
  - apt-debian-bookworm
    ✓ version_mapping: 1 mapping(s)
    ✓ endpoints: 3 endpoint(s)
    ✓ parsing: format=debian_packages
    ✓ query_type: bulk_download

...

================================================================================
Validation Summary
================================================================================

Total repositories: 65
Valid repositories: 65
Invalid repositories: 0
EOL repositories: 5

Warnings (36):
  [WARNING] brew-macos: No version_mapping defined (OS-specific queries not supported)
  [WARNING] choco-windows: API repo should have rate limiting configuration
  ...

EOL Repositories (5):
  - apt-debian-stretch
  - dnf-rhel-7
  - dnf-centos-stream-8
  - apt-ubuntu-focal
  - zypper-sles-12

Endpoint Tests:
  Total: 157
  Success: 94
  Warnings: 2
  Errors: 61
```

#### Exit Codes

- `0`: All validations passed (warnings are acceptable)
- `1`: Validation errors found (invalid configurations)

#### Requirements

- Python 3.8+
- aiohttp (for endpoint testing)
- pyyaml
- saigen package (for RepositoryInfo model)

#### Related Documentation

- [Repository Validation Results](../docs/summaries/repository-validation-results.md) - Latest validation results and analysis
- [Repository Configuration Guide](../saigen/docs/repository-configuration.md) - How to configure repositories
- [Provider Version Refresh Enhancement Spec](../.kiro/specs/provider-version-refresh-enhancement/) - Requirements and design

#### Troubleshooting

**Import Errors**
```bash
# Ensure you're in the project root and virtual environment is activated
source .venv/bin/activate
python scripts/validate_repository_configs.py
```

**Endpoint Timeouts**
- Some endpoints may timeout due to large datasets or slow servers
- This is expected for bulk package lists (packagist, maven-central)
- Timeouts don't indicate configuration errors

**Authentication Errors**
- Some repositories require authentication (RHEL, SLES, rubygems)
- These will show as errors but are expected
- Authentication is configured but not tested by this script

**404 Errors**
- Some endpoints use placeholder values ({query}, {package})
- 404 errors for these are expected during testing
- The configuration is still valid

#### Future Enhancements

- [ ] Add option to skip endpoint connectivity tests
- [ ] Add option to test with real authentication credentials
- [ ] Add validation for repository schema against JSON schema
- [ ] Add performance benchmarking for endpoint response times
- [ ] Add option to validate specific repository files only
- [ ] Add automated fixing of common issues (e.g., version_mapping format)
