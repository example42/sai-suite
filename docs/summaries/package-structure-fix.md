# Package Structure Fix - The Real Solution

## The Actual Problem

The issue was NOT a broken virtual environment or wrong directory structure. The real problem was in the `pyproject.toml` configuration.

### What Was Wrong

The `[tool.setuptools.packages.find]` configuration was looking for packages but couldn't find them correctly:

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["sai*"]
exclude = ["tests*", "docs*", "examples*"]
```

This configuration told setuptools to:
1. Look in the current directory (`.`)
2. Find packages matching `sai*`
3. But it found the FILES directly, not as a package

### Evidence of the Problem

1. **Empty top_level.txt**:
   ```
   sai/sai.egg-info/top_level.txt
   (empty file)
   ```
   This should have contained `sai` but was empty.

2. **Wrong SOURCES.txt**:
   ```
   __init__.py
   cli/__init__.py
   core/__init__.py
   ```
   Files were listed without the `sai/` prefix, meaning they weren't recognized as part of the `sai` package.

3. **Installation appeared successful but imports failed**:
   ```bash
   $ pip list | grep sai
   sai  0.0.post57+dirty /Users/al/saitest/sai-suite/sai
   
   $ sai --version
   ModuleNotFoundError: No module named 'sai'
   ```

## The Solution

Changed from automatic package discovery to explicit package declaration:

### Before (Broken):
```toml
[tool.setuptools]
zip-safe = false
include-package-data = true

[tool.setuptools.packages.find]
where = ["."]
include = ["sai*"]
exclude = ["tests*", "docs*", "examples*"]
```

### After (Fixed):
```toml
[tool.setuptools]
zip-safe = false
include-package-data = true
# Explicitly list the package - flat layout where package root is current dir
packages = ["sai"]

[tool.setuptools.package-dir]
# Map the package name to the directory containing it
# Empty string means current directory
sai = "."
```

## Why This Works

The explicit configuration tells setuptools:
1. **`packages = ["sai"]`** - There is one package named `sai`
2. **`sai = "."`** - The `sai` package's root is the current directory

This is the correct way to configure a "flat layout" where:
```
sai/                    # Package directory (contains pyproject.toml)
├── pyproject.toml      # Package configuration
├── __init__.py         # Package root (this IS the sai package)
├── cli/                # Subpackage
├── core/               # Subpackage
└── ...
```

## Verification

After the fix:

### 1. top_level.txt is correct:
```
$ cat sai/sai.egg-info/top_level.txt
sai
```

### 2. Commands work:
```bash
$ sai --version
sai, version 0.0.post57+dirty

$ saigen --version
saigen, version 0.0.post57+dirty
```

### 3. Imports work:
```bash
$ python -c "import sai; print(sai.__file__)"
/path/to/sai-suite/sai/__init__.py

$ python -c "import saigen; print(saigen.__file__)"
/path/to/sai-suite/saigen/__init__.py
```

## Why the Confusion

### Flat Layout vs Src Layout

There are two common Python package layouts:

#### Flat Layout (What we have):
```
package-dir/
├── pyproject.toml
├── __init__.py       # Package root
├── module1.py
└── subpackage/
```

Requires explicit configuration:
```toml
[tool.setuptools]
packages = ["mypackage"]

[tool.setuptools.package-dir]
mypackage = "."
```

#### Src Layout (Alternative):
```
package-dir/
├── pyproject.toml
└── mypackage/        # Nested
    ├── __init__.py
    ├── module1.py
    └── subpackage/
```

Works with automatic discovery:
```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["mypackage*"]
```

### Why Automatic Discovery Failed

The `packages.find` configuration works when:
- You have a nested structure (`sai/sai/`)
- The package is in a subdirectory

But fails when:
- You have a flat structure (`sai/` with `__init__.py` directly in it)
- The package root IS the current directory

## Installation Instructions (Updated)

### For Fresh Install:

```bash
# Clone repository
git clone https://github.com/example42/sai-suite.git
cd sai-suite

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install both packages
pip install -e ./sai[dev]
pip install -e ./saigen[dev]

# Verify
sai --version
saigen --version
```

### Using Makefile:

```bash
make clean
make install-both
```

The Makefile commands now work correctly.

## Setting Version to 0.1.0

To get rid of the `0.0.post57+dirty` version:

### Option 1: Create Git Tag
```bash
git tag v0.1.0
pip uninstall -y sai saigen
make install-both
sai --version  # Shows: sai, version 0.1.0
```

### Option 2: Commit Changes (Removes +dirty)
```bash
git add .
git commit -m "Package structure fix"
pip uninstall -y sai saigen
make install-both
sai --version  # Shows: sai, version 0.0.post58 (no +dirty)
```

### Option 3: Both (Clean Release)
```bash
git add .
git commit -m "Release 0.1.0"
git tag v0.1.0
pip uninstall -y sai saigen
make install-both
sai --version  # Shows: sai, version 0.1.0
```

## Files Changed

### sai/pyproject.toml
- Removed `[tool.setuptools.packages.find]`
- Added explicit `packages = ["sai"]`
- Added `[tool.setuptools.package-dir]` with `sai = "."`

### saigen/pyproject.toml
- Removed `[tool.setuptools.packages.find]`
- Added explicit `packages = ["saigen"]`
- Added `[tool.setuptools.package-dir]` with `saigen = "."`

## Testing

To test in a fresh environment:

```bash
# Create test directory
cd /tmp
git clone https://github.com/example42/sai-suite.git test-sai
cd test-sai

# Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ./sai[dev]
pip install -e ./saigen[dev]

# Test
sai --version
saigen --version
python -c "import sai; import saigen; print('Success!')"
```

## Lessons Learned

1. **Automatic package discovery doesn't work for flat layouts** - Need explicit configuration
2. **Empty top_level.txt is a red flag** - Means no packages were found
3. **Flat layout requires explicit package mapping** - Can't rely on `packages.find`
4. **Documentation was misleading** - Suggested nested structure when flat was used
5. **setuptools_scm is fine** - The version "issue" was just misunderstanding

## Related Documentation

- Python Packaging Guide: https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/
- Setuptools Package Discovery: https://setuptools.pypa.io/en/latest/userguide/package_discovery.html
- Flat vs Src Layout: https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/

## Conclusion

The package structure was correct all along. The issue was that `pyproject.toml` was configured for automatic package discovery, which doesn't work with flat layouts. The fix was to explicitly declare the packages and their locations.

This is now working correctly and users can install and use both `sai` and `saigen` packages without issues.
