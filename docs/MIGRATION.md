# Migration Guide - Monorepo Structure

## Overview

The SAI Python repository has been restructured into a monorepo with separate pip packages. This guide helps you understand what changed and how to migrate.

## What Changed?

### Before (Single Package)

```bash
pip install sai  # Installed everything
```

One package with all features bundled together.

### After (Monorepo with Separate Packages)

```bash
pip install sai       # Lightweight execution only
pip install saigen    # Generation tool only
pip install sai[generation]  # Both
```

Two separate packages that can be installed independently.

## For End Users

### No Breaking Changes

**Good news**: Your existing code and workflows continue to work without changes!

- ✅ All imports remain the same
- ✅ CLI commands unchanged
- ✅ Configuration files compatible
- ✅ Existing scripts work as-is

### What You Need to Do

**If you only use SAI (execution):**

```bash
# Your current installation
pip install sai

# Still works! Now installs lightweight version
# No action needed
```

**If you only use SAIGEN (generation):**

```bash
# Install the new saigen package
pip install saigen

# Your existing commands work the same
saigen generate nginx
```

**If you use both:**

```bash
# Option 1: Install both separately
pip install sai saigen

# Option 2: Install SAI with generation support
pip install sai[generation]
```

### Upgrade Path

```bash
# Uninstall old version (if needed)
pip uninstall sai

# Install new version(s)
pip install sai        # For execution only
pip install saigen     # For generation only
pip install sai[generation]  # For both
```

## For Developers

### Repository Structure Changed

**Before:**
```
sai/
├── sai/
├── saigen/
├── pyproject.toml  # Single config
└── ...
```

**After:**
```
sai-suite/
├── sai/
│   ├── sai/
│   └── pyproject.toml  # SAI config
├── saigen/
│   ├── saigen/
│   └── pyproject.toml  # SAIGEN config
├── pyproject.toml      # Workspace config
└── ...
```

### Development Installation Changed

**Before:**
```bash
pip install -e .
```

**After:**
```bash
# Install both in editable mode
pip install -e ./sai[dev]
pip install -e ./saigen[dev]

# Or use the helper script
./scripts/install-local.sh both

# Or use make
make install-both
```

### Building Changed

**Before:**
```bash
python -m build
```

**After:**
```bash
# Build both packages
./scripts/build-packages.sh

# Or use make
make build

# Or build individually
python -m build sai
python -m build saigen
```

### Testing Unchanged

```bash
# Still works the same
pytest

# Or use make
make test
```

## For CI/CD Pipelines

### GitHub Actions

**Before:**
```yaml
- name: Install dependencies
  run: pip install sai
```

**After (no change needed):**
```yaml
# Still works! Now installs lightweight version
- name: Install dependencies
  run: pip install sai

# Or be explicit
- name: Install SAI
  run: pip install sai

- name: Install SAIGEN
  run: pip install saigen
```

### Docker

**Before:**
```dockerfile
RUN pip install sai
```

**After (choose what you need):**
```dockerfile
# For execution only (smaller image)
RUN pip install sai

# For generation
RUN pip install saigen

# For both
RUN pip install sai[generation]
```

## Benefits of Migration

### For Production Users

1. **Smaller footprint**: SAI without AI/ML dependencies
2. **Faster installation**: Fewer packages to download
3. **Better security**: Fewer dependencies to audit

### For Development Users

1. **Flexibility**: Install only what you need
2. **Clearer separation**: Execution vs generation
3. **Better organization**: Easier to navigate

### For Contributors

1. **Independent releases**: SAI and SAIGEN can version separately
2. **Shared code**: Common utilities in one place
3. **Better testing**: Package-specific test suites

## Common Questions

### Q: Do I need to change my code?

**A:** No! All imports and APIs remain the same.

### Q: Will my existing installation break?

**A:** No! Upgrading is seamless. Just `pip install --upgrade sai`.

### Q: Can I still install everything together?

**A:** Yes! Use `pip install sai[generation]` or install both packages.

### Q: What if I'm not sure which package I need?

**A:** See [When to Use What](when-to-use-what.md) guide.

### Q: Do I need to update my requirements.txt?

**A:** Only if you want to be explicit:

```txt
# Before
sai

# After (choose one)
sai              # Execution only
saigen           # Generation only
sai[generation]  # Both
```

### Q: What about version numbers?

**A:** Both packages will maintain version compatibility. Install matching versions for best results.

## Troubleshooting

### Issue: Import errors after upgrade

**Solution:**
```bash
# Reinstall in correct environment
pip uninstall sai saigen
pip install sai saigen
```

### Issue: Missing saigen command

**Solution:**
```bash
# Install saigen package
pip install saigen
```

### Issue: Dependency conflicts

**Solution:**
```bash
# Use virtual environment
python -m venv venv
source venv/bin/activate
pip install sai saigen
```

## Timeline

- **Current**: Monorepo structure implemented
- **Next Release**: Both packages published to PyPI
- **Future**: Independent versioning and releases

## Getting Help

- **Questions?** Open a [discussion](https://github.com/example42/sai-suite/discussions)
- **Issues?** Report a [bug](https://github.com/example42/sai-suite/issues)
- **Documentation**: See [docs/](.)

## Summary

✅ **No breaking changes** - Your code continues to work  
✅ **Seamless upgrade** - Just `pip install --upgrade`  
✅ **More flexibility** - Install only what you need  
✅ **Better organization** - Clearer package structure  

The migration is designed to be transparent. Most users won't need to change anything!
