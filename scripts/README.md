# SAI Scripts Directory

This directory contains various scripts for building, installing, and managing the SAI Software Management Suite.

## Installation Scripts

### `install.sh` (Linux/macOS)

Automated installation script for Unix-like systems.

**Usage:**
```bash
# Direct installation
curl -fsSL https://raw.githubusercontent.com/example42/sai/main/scripts/install.sh | bash

# Download and inspect first
curl -fsSL https://raw.githubusercontent.com/example42/sai/main/scripts/install.sh -o install.sh
chmod +x install.sh
./install.sh

# Uninstall
./install.sh --uninstall
```

**Features:**
- Checks Python version (3.8+ required)
- Creates isolated virtual environment in `~/.sai/venv`
- Installs SAI with all optional dependencies
- Creates command symlinks in `~/.local/bin`
- Sets up shell completion
- Creates default configuration file

### `install.ps1` (Windows)

PowerShell installation script for Windows systems.

**Usage:**
```powershell
# Download and run
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/example42/sai/main/scripts/install.ps1" -OutFile "install.ps1"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install.ps1

# Uninstall
.\install.ps1 -Uninstall
```

**Features:**
- Checks Python version and pip availability
- Creates virtual environment in `%USERPROFILE%\.sai\venv`
- Creates batch file wrappers in `%USERPROFILE%\.local\bin`
- Sets up Windows-specific configuration

## Build Scripts

### `build.sh`

Comprehensive build script for creating distribution packages.

**Usage:**
```bash
# Full build with all checks
./scripts/build.sh

# Skip tests
SKIP_TESTS=1 ./scripts/build.sh

# Skip linting
SKIP_LINT=1 ./scripts/build.sh

# Clean only
./scripts/build.sh --clean-only
```

**Features:**
- Dependency checking
- Code quality checks (linting, formatting)
- Test suite execution
- Package building (wheel and source distribution)
- Package validation with twine
- Build artifact information

## Release Management

### `release.py`

Automated release management script for version bumping and publishing.

**Usage:**
```bash
# Patch release (0.1.0 -> 0.1.1)
python scripts/release.py patch

# Minor release (0.1.0 -> 0.2.0)
python scripts/release.py minor

# Major release (0.1.0 -> 1.0.0)
python scripts/release.py major

# Publish to Test PyPI
python scripts/release.py patch --test

# Skip tests
python scripts/release.py patch --skip-tests

# Skip publishing
python scripts/release.py patch --skip-publish

# Dry run (show what would be done)
python scripts/release.py patch --dry-run
```

**Features:**
- Semantic version bumping
- Changelog updates
- Git tag creation
- Package building
- PyPI publishing (production and test)
- Git push automation

**Prerequisites:**
- Clean git working directory
- PyPI/Test PyPI credentials configured
- `build` and `twine` packages installed

## Script Dependencies

### Required Python Packages

For development and release scripts:
```bash
pip install build twine setuptools-scm
```

### System Dependencies

#### Linux/macOS
- `bash` (for shell scripts)
- `git` (for version control operations)
- `curl` or `wget` (for downloads)

#### Windows
- PowerShell 5.1+ (for PowerShell scripts)
- Git for Windows (for version control)

## Configuration

### Environment Variables

Scripts respect the following environment variables:

- `SKIP_TESTS=1` - Skip test execution in build scripts
- `SKIP_LINT=1` - Skip linting checks in build scripts
- `PYPI_TOKEN` - PyPI API token for publishing
- `TESTPYPI_TOKEN` - Test PyPI API token for testing

### PyPI Configuration

For automated publishing, configure your PyPI credentials:

**Option 1: API Tokens (Recommended)**
```bash
# ~/.pypirc
[distutils]
index-servers = pypi testpypi

[pypi]
username = __token__
password = pypi-your-api-token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-api-token
```

**Option 2: Environment Variables**
```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-your-api-token
```

## Usage Examples

### Complete Release Workflow

```bash
# 1. Ensure clean working directory
git status

# 2. Run quality checks
make ci

# 3. Create release (patch version)
python scripts/release.py patch

# 4. Verify release
pip install sai==<new-version>
sai --version
```

### Development Build

```bash
# Quick development build
./scripts/build.sh --skip-tests

# Full build with all checks
./scripts/build.sh

# Install built package
pip install dist/*.whl
```

### Testing Installation Scripts

```bash
# Test installation script in Docker
docker run --rm -it python:3.11-slim bash -c "
  apt-get update && apt-get install -y curl &&
  curl -fsSL https://raw.githubusercontent.com/example42/sai/main/scripts/install.sh | bash &&
  sai --version
"
```

## Troubleshooting

### Common Issues

#### Permission Errors
```bash
# Make scripts executable
chmod +x scripts/*.sh scripts/release.py
```

#### Python Version Issues
```bash
# Check Python version
python --version
python3 --version

# Use specific Python version
python3.11 scripts/release.py patch
```

#### Build Failures
```bash
# Clean and retry
make clean
./scripts/build.sh
```

#### Git Issues
```bash
# Ensure clean working directory
git status
git stash  # if needed

# Check git configuration
git config --list
```

### Getting Help

- Check script help: `./script.sh --help`
- Review error messages and logs
- Open an issue on GitHub with error details
- Check the main [troubleshooting guide](../docs/troubleshooting.md)

## Contributing

When adding new scripts:

1. Follow existing naming conventions
2. Include comprehensive help text
3. Add error handling and validation
4. Update this README
5. Test on multiple platforms (if applicable)
6. Make scripts executable: `chmod +x script.sh`