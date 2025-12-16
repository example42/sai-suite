# Scripts Directory Cleanup - October 2024

## Summary

Cleaned up the scripts directory by removing outdated and redundant scripts. The project now uses modern tooling (setuptools-scm, GitHub Actions) that makes several manual scripts unnecessary.

## Scripts Removed

### 1. install.sh (Removed)
**Reason:** Users should install via pip, not custom installation scripts.

**Replacement:**
```bash
# For users
pip install sai
pip install saigen

# For contributors
./scripts/install-local.sh
```

The custom installation script created virtual environments and symlinks, but this is non-standard and unnecessary. Standard pip installation is cleaner and more maintainable.

### 2. install.ps1 (Removed)
**Reason:** Same as install.sh - users should use pip.

**Replacement:**
```powershell
pip install sai
pip install saigen
```

### 3. build.sh (Removed)
**Reason:** Redundant with build-packages.sh and CI/CD workflows.

The comprehensive build.sh script included linting, testing, and validation. However:
- CI/CD workflows handle all quality checks automatically
- build-packages.sh provides simpler, focused package building
- Developers can run tests/linting directly with pytest, black, etc.

**Replacement:**
```bash
# Build packages
./scripts/build-packages.sh

# Run tests (if needed)
pytest tests/

# Run linting (if needed)
black sai saigen tests
isort sai saigen tests
flake8 sai saigen tests
```

### 4. release.py (Removed)
**Reason:** Project uses setuptools-scm and GitHub Actions for releases.

The manual release script handled:
- Version bumping
- Changelog updates
- Git tagging
- Package building
- PyPI publishing

**Modern approach:**
1. **Versioning:** setuptools-scm automatically derives version from git tags
2. **Releases:** GitHub Actions workflow (.github/workflows/release.yml) handles everything
3. **Process:** Just create a git tag, CI does the rest

```bash
# Old way (manual)
./scripts/release.py patch

# New way (automated)
git tag v0.1.0
git push origin v0.1.0
# GitHub Actions handles building, testing, and publishing
```

## Scripts Retained

### Build and Deployment
- **build-packages.sh** - Simple package building for both sai and saigen
- **publish-packages.sh** - Manual publishing to PyPI/TestPyPI when needed
- **install-local.sh** - Development installation in editable mode

### Validation
- **validate_providers.py** - Schema validation for provider files
- **validate_providers.sh** - Shell wrapper with dependency management
- **test_universal_repositories.py** - Repository system testing

### Development
- **development/** subdirectory - Code analysis, feature testing, and demos

## Benefits of Cleanup

1. **Simpler maintenance** - Fewer scripts to maintain and update
2. **Standard tooling** - Uses pip, setuptools-scm, GitHub Actions (industry standard)
3. **Less confusion** - Clear separation between user installation (pip) and development (install-local.sh)
4. **Automated releases** - No manual version bumping or changelog editing
5. **CI/CD integration** - All quality checks happen automatically in workflows

## Migration Guide

### For Users
**Before:**
```bash
curl -sSL https://example.com/install.sh | bash
```

**After:**
```bash
pip install sai saigen
```

### For Contributors
**Before:**
```bash
./scripts/build.sh
./scripts/release.py patch
```

**After:**
```bash
# Development setup
./scripts/install-local.sh

# Build packages
./scripts/build-packages.sh

# Releases are automated via GitHub Actions
git tag v0.1.0 && git push origin v0.1.0
```

### For Maintainers
**Before:**
- Manual version bumping in pyproject.toml
- Manual changelog updates
- Running release.py script
- Manual PyPI publishing

**After:**
- setuptools-scm handles versioning automatically
- Create git tag to trigger release workflow
- GitHub Actions handles testing, building, and publishing
- Trusted publishing to PyPI (no manual credentials)

## Documentation Updates

- Updated scripts/README.md with current scripts only
- Removed references to deleted scripts
- Added clear guidance on installation and release processes
- Documented the modern CI/CD approach

## Related Files

- `.github/workflows/release.yml` - Automated release workflow
- `.github/workflows/publish.yml` - PyPI publishing workflow
- `sai/pyproject.toml` - Uses setuptools-scm for versioning
- `saigen/pyproject.toml` - Uses setuptools-scm for versioning
