# Version Management Guide

## How Versioning Works

This project uses `setuptools_scm` for automatic version management based on git tags.

## Version Format

```
{tag}.post{distance}+{local}
```

- **tag**: Git tag (e.g., `v0.1.0` → `0.1.0`)
- **post{distance}**: Number of commits after the tag
- **+{local}**: Local modifications indicator (e.g., `+dirty`)

## Examples

| Git State | Version | Meaning |
|-----------|---------|---------|
| At tag `v0.1.0`, clean | `0.1.0` | Clean release |
| At tag `v0.1.0`, modified | `0.1.0+dirty` | Release with uncommitted changes |
| 5 commits after `v0.1.0`, clean | `0.1.0.post5` | Development version |
| 5 commits after `v0.1.0`, modified | `0.1.0.post5+dirty` | Development with changes |
| No tags, 57 commits | `0.0.post57` | Pre-release development |

## Creating a Release

### Step 1: Commit All Changes

```bash
# Check status
git status

# Commit everything
git add .
git commit -m "Release 0.1.0: Description of changes"
```

### Step 2: Create Git Tag

```bash
# Create annotated tag
git tag -a v0.1.0 -m "Release version 0.1.0"

# Or simple tag
git tag v0.1.0
```

### Step 3: Reinstall Packages

```bash
# Uninstall old versions
pip uninstall -y sai saigen

# Clean build artifacts
make clean

# Install fresh
make install-both
```

### Step 4: Verify Version

```bash
sai --version
# Output: sai, version 0.1.0

saigen --version
# Output: saigen, version 0.1.0
```

### Step 5: Push to Remote (Optional)

```bash
# Push commits
git push origin main

# Push tag
git push origin v0.1.0
```

## Updating a Tag

If you need to move a tag to a different commit:

```bash
# Delete local tag
git tag -d v0.1.0

# Create new tag at current commit
git tag v0.1.0

# Force push to remote (if already pushed)
git push origin v0.1.0 --force
```

## Understanding +dirty Suffix

The `+dirty` suffix appears when you have:
- Modified files (tracked or untracked)
- Staged but uncommitted changes
- Any difference from the tagged commit

### Why It's Useful

- **Safety**: Prevents confusion between released and development code
- **Traceability**: Shows the code doesn't exactly match the tag
- **Development**: Helps identify working copies vs releases

### To Remove +dirty

Simply commit your changes:

```bash
git add .
git commit -m "Your commit message"
pip uninstall -y sai saigen
make install-both
```

## Configuration

The versioning is configured in `pyproject.toml`:

```toml
[tool.setuptools_scm]
root = ".."                      # Look for git repo in parent dir
write_to = "sai/_version.py"     # Write version to this file
version_scheme = "post-release"  # Use post-release versioning
local_scheme = "dirty-tag"       # Add +dirty for uncommitted changes
```

### Important: _version.py Files

The `_version.py` files are **auto-generated** and should NOT be tracked in git:

```bash
# Already in .gitignore
*/_version.py
_version.py
```

These files are created during installation and contain the calculated version.

## Version Bumping Strategies

### Patch Release (0.1.0 → 0.1.1)

```bash
git add .
git commit -m "Fix: Description"
git tag v0.1.1
pip uninstall -y sai saigen && make install-both
```

### Minor Release (0.1.0 → 0.2.0)

```bash
git add .
git commit -m "Feature: Description"
git tag v0.2.0
pip uninstall -y sai saigen && make install-both
```

### Major Release (0.1.0 → 1.0.0)

```bash
git add .
git commit -m "Breaking: Description"
git tag v1.0.0
pip uninstall -y sai saigen && make install-both
```

## Using the Release Script

The project includes a release automation script:

```bash
# Patch bump (0.1.0 → 0.1.1)
python scripts/release.py patch

# Minor bump (0.1.0 → 0.2.0)
python scripts/release.py minor

# Major bump (0.1.0 → 1.0.0)
python scripts/release.py major

# Dry run (see what would happen)
python scripts/release.py patch --dry-run
```

The script automatically:
1. Runs tests
2. Updates changelog
3. Creates git tag
4. Builds packages
5. Optionally publishes to PyPI

## Troubleshooting

### Version Still Shows +dirty After Committing

Check if `_version.py` files are modified:

```bash
git status
# If you see sai/_version.py or saigen/_version.py modified:

# They should be in .gitignore
git rm --cached sai/_version.py saigen/_version.py
git commit -m "Remove auto-generated _version.py from tracking"
git tag -d v0.1.0
git tag v0.1.0
pip uninstall -y sai saigen && make install-both
```

### Version Shows 0.0.postXX

No git tags exist. Create one:

```bash
git tag v0.1.0
pip uninstall -y sai saigen && make install-both
```

### Version Shows Wrong Number

Check your tags:

```bash
# List all tags
git tag -l

# See which tag is most recent
git describe --tags

# Delete wrong tag
git tag -d v0.2.0

# Create correct tag
git tag v0.1.0
```

### Want to Disable +dirty Suffix

Change `local_scheme` in both `pyproject.toml` files:

```toml
[tool.setuptools_scm]
local_scheme = "no-local-version"  # Instead of "dirty-tag"
```

**Not recommended** - the +dirty suffix is useful for development.

## Best Practices

1. **Always commit before tagging** - Ensures clean version
2. **Use annotated tags** - `git tag -a v0.1.0 -m "Message"`
3. **Follow semantic versioning** - MAJOR.MINOR.PATCH
4. **Update changelog** - Document what changed
5. **Test before tagging** - Run `make test`
6. **Don't track _version.py** - Let setuptools_scm generate it

## Quick Reference

```bash
# Create release
git add . && git commit -m "Release 0.1.0" && git tag v0.1.0

# Reinstall
pip uninstall -y sai saigen && make install-both

# Check version
sai --version && saigen --version

# Push release
git push origin main && git push origin v0.1.0
```

## Related Files

- `sai/pyproject.toml` - SAI version configuration
- `saigen/pyproject.toml` - SAIGEN version configuration
- `scripts/release.py` - Automated release script
- `.gitignore` - Excludes `_version.py` files
- `CHANGELOG.md` - Version history

## Further Reading

- [setuptools_scm documentation](https://github.com/pypa/setuptools_scm)
- [Semantic Versioning](https://semver.org/)
- [Git Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
