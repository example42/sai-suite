# Scripts Directory

This directory contains build, validation, and development scripts for the SAI Software Management Suite.

## Build and Deployment Scripts

### build-packages.sh
Builds both SAI and SAIGEN packages for distribution. Cleans previous builds, creates wheel and source distributions for each package, and copies them to a root `dist/` folder.

**Usage:**
```bash
./scripts/build-packages.sh
```

**Output:**
- `sai/dist/` - SAI package distributions
- `saigen/dist/` - SAIGEN package distributions  
- `dist/` - Combined distributions for convenience

### publish-packages.sh
Publishes packages to PyPI or TestPyPI. Supports publishing individual packages or both together.

**Usage:**
```bash
./scripts/publish-packages.sh test both    # Publish both to TestPyPI
./scripts/publish-packages.sh prod sai     # Publish SAI to PyPI
./scripts/publish-packages.sh prod saigen  # Publish SAIGEN to PyPI
```

**Note:** Requires `twine` to be installed and PyPI credentials configured.

## Weekly Version Update Scripts

Automated scripts for updating package versions across all saidata files using locally present repositories.

### weekly-version-update.sh
Bash script that scans a saidata directory and updates all package versions by querying local repository caches. Designed to run as a weekly cronjob.

**Usage:**
```bash
./scripts/weekly-version-update.sh [OPTIONS]
```

**Options:**
- `--saidata-dir PATH` - Path to saidata directory (default: ~/saidata)
- `--backup-dir PATH` - Path to backup directory (default: ~/saidata-backups)
- `--log-dir PATH` - Path to log directory (default: ~/logs/saidata-updates)
- `--skip-default` - Skip default.yaml files
- `--no-cache` - Don't use cached repository data
- `--dry-run` - Show what would be done without executing
- `--verbose` - Enable verbose output

### weekly_version_update.py
Python script with advanced features including parallel processing, comprehensive logging, and backup management. **Recommended** for production use.

**Usage:**
```bash
./scripts/weekly_version_update.py [OPTIONS]
```

**Additional Options:**
- `--sequential` - Disable parallel processing
- `--max-workers N` - Maximum parallel workers (default: 4)
- `--no-cleanup` - Don't clean up old backups
- `--retention-days N` - Backup retention in days (default: 30)

### setup-cronjob.sh
Interactive script to configure and install a cronjob for automated version updates.

**Usage:**
```bash
./scripts/setup-cronjob.sh
```

**Features:**
- Interactive configuration
- Schedule selection (weekly, daily, monthly, custom)
- Path configuration
- Test run before installation
- Automatic cronjob installation

**See:** [README-weekly-updates.md](README-weekly-updates.md) for comprehensive documentation

## Development Scripts

### install-local.sh
Installs packages in editable mode for local development. Recommended for contributors working on the codebase.

**Usage:**
```bash
# Activate virtual environment first (recommended)
python -m venv venv && source venv/bin/activate

# Install packages
./scripts/install-local.sh        # Install both packages in editable mode
./scripts/install-local.sh sai    # Install only SAI
./scripts/install-local.sh saigen # Install only SAIGEN
```

**What it does:**
- Installs packages with `pip install -e` for live code changes
- Includes `[dev]` dependencies for development tools
- Warns if no virtual environment is active

## Validation Scripts

### validate_providers.py
Validates provider YAML files against the providerdata-0.1-schema.json schema. Checks all provider files for schema compliance and reports detailed validation errors.

**Usage:**
```bash
./scripts/validate_providers.py                    # Validate all providers
./scripts/validate_providers.py --verbose          # Show all files
./scripts/validate_providers.py --file path.yaml   # Validate single file
./scripts/validate_providers.py --providers-dir custom/path
./scripts/validate_providers.py --schema custom-schema.json
```

**Requirements:** `jsonschema`, `PyYAML`

### validate_providers.sh
Shell wrapper for validate_providers.py. Automatically installs required Python dependencies if missing.

**Usage:**
```bash
./scripts/validate_providers.sh [options]  # Same options as Python script
```

### validate_repository_configs.py
Comprehensive validation script for repository configurations. Validates structure, endpoints, version mappings, parsing rules, and tests endpoint connectivity.

**Usage:**
```bash
python scripts/validate_repository_configs.py
```

**Output:**
- Console: Real-time validation progress with color-coded results
- JSON: Detailed results saved to `scripts/repository_validation_results.json`
- Summary: Statistics and error/warning reports

**See:** [README-validation.md](README-validation.md) for detailed documentation

## Testing Scripts

### test_universal_repositories.py
Test suite for the universal repository management system. Tests parser registry, universal manager, repository manager, and configuration validation.

**Usage:**
```bash
./scripts/test_universal_repositories.py
```

**Tests:**
- Parser registry functionality
- Universal repository manager
- Enhanced repository manager
- Configuration validation

## Development Subdirectory

Development tools and demo scripts are organized in the `development/` subdirectory:

- **Code analysis tools** - Find unused methods and analyze code quality
- **SAI demos** - Showcase SAI execution engine features
- **SAIGEN demos** - Showcase SAIGEN generation engine features

See [development/README.md](development/README.md) for details.

**Note:** These are demo scripts for learning and development. For automated testing, use the proper test suite in `tests/`.

## Installation and Release Process

### For Users
Install from PyPI (recommended):
```bash
pip install sai
pip install saigen
```

### For Contributors
1. Clone the repository
2. Create a virtual environment
3. Install in editable mode:
```bash
./scripts/install-local.sh
```

### For Maintainers
The project uses **setuptools-scm** for automatic versioning from git tags and **GitHub Actions** for CI/CD:

1. **Development:** Work on feature branches, CI runs automatically
2. **Release:** Create a git tag (e.g., `v0.1.0`), GitHub Actions handles:
   - Running tests and linting
   - Building packages
   - Publishing to PyPI
   - Creating GitHub release

**Manual build for testing:**
```bash
./scripts/build-packages.sh
./scripts/publish-packages.sh test both  # Publish to TestPyPI
```

## Quick Reference

**Local development setup:**
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
./scripts/install-local.sh
```

**Build packages:**
```bash
./scripts/build-packages.sh
```

**Validate providers:**
```bash
./scripts/validate_providers.sh
```

**Run tests:**
```bash
pytest tests/
```

**Test repository system:**
```bash
./scripts/test_universal_repositories.py
```
