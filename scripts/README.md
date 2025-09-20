# Provider Validation Scripts

This directory contains scripts for validating provider files against the providerdata schema.

## Files

- `validate_providers.py` - Main Python validation script
- `validate_providers.sh` - Shell wrapper for easy execution
- `README.md` - This documentation

## Usage

### Using Make (Recommended)

```bash
# Validate all provider files
make validate-providers

# Validate with verbose output (shows all files, not just errors)
make validate-providers-verbose
```

### Using Python Script Directly

```bash
# Validate all provider files
python3 scripts/validate_providers.py

# Validate with verbose output
python3 scripts/validate_providers.py --verbose

# Validate a specific file
python3 scripts/validate_providers.py --file providers/apt.yaml

# Use custom schema or providers directory
python3 scripts/validate_providers.py --schema custom-schema.json --providers-dir custom-providers/
```

### Using Shell Script

```bash
# Validate all provider files
./scripts/validate_providers.sh

# Pass arguments to the Python script
./scripts/validate_providers.sh --verbose
./scripts/validate_providers.sh --file providers/apt.yaml
```

## Requirements

The validation script requires:
- Python 3.6+
- `jsonschema` package
- `PyYAML` package

The shell script will automatically attempt to install missing packages using pip.

## Output

The script provides:
- ✅ Success indicators for valid files
- ❌ Error indicators with detailed validation messages
- 📊 Summary statistics
- Clear error descriptions with JSON path information

## Integration

The validation is integrated into:
- `make quality` - Runs as part of overall quality checks
- CI/CD pipelines (via make targets)
- Pre-commit hooks (can be added)

## Schema

The validation uses the schema at `schemas/providerdata-0.1-schema.json` which defines:
- Required fields (version, provider, actions)
- Provider metadata structure
- Action definitions and templates
- Mapping configurations
- Data types and constraints