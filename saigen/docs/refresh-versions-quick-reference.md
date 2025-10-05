# refresh-versions Quick Reference

## One-Line Summary
Update package versions in saidata files from repository data without LLM costs.

## Basic Commands

```bash
# Check for updates
saigen refresh-versions --check-only nginx.yaml

# Apply updates
saigen refresh-versions nginx.yaml

# Specific providers
saigen refresh-versions --providers apt,brew nginx.yaml

# Save to new file
saigen refresh-versions -o nginx-new.yaml nginx.yaml

# Fresh data (skip cache)
saigen refresh-versions --no-cache nginx.yaml

# Verbose output
saigen --verbose refresh-versions nginx.yaml

# Dry run
saigen --dry-run refresh-versions nginx.yaml
```

## Common Options

| Option | Description |
|--------|-------------|
| `--check-only` | Preview changes without modifying |
| `--providers TEXT` | Target specific providers (apt, brew, etc.) |
| `--no-cache` | Skip cache, query repositories directly |
| `--output, -o PATH` | Save to different file |
| `--no-backup` | Disable automatic backup |
| `--show-unchanged` | Show packages already up-to-date |
| `--backup-dir PATH` | Custom backup directory |

## Global Options

| Option | Description |
|--------|-------------|
| `--verbose, -v` | Enable verbose output |
| `--dry-run` | Show what would happen |

## What Gets Updated

✅ Package versions  
✅ Binary versions  
✅ Source versions  
✅ Script versions  
❌ Descriptions (unchanged)  
❌ URLs (unchanged)  
❌ Other metadata (unchanged)  

## Workflow

```bash
# 1. Check what would change
saigen refresh-versions --check-only nginx.yaml

# 2. Apply updates
saigen refresh-versions nginx.yaml

# 3. Validate result
saigen validate nginx.yaml
```

## CI/CD Example

```yaml
# .github/workflows/check-versions.yml
- name: Check for outdated versions
  run: |
    saigen refresh-versions --check-only saidata/*.yaml
```

## Batch Processing

```bash
# Update all files in directory
for file in saidata/*.yaml; do
  saigen refresh-versions "$file"
done

# Or with find
find saidata -name "*.yaml" -exec saigen refresh-versions {} \;
```

## Troubleshooting

### Package not found
```
⚠ Could not find version for nginx in apt repository
```
**Solution**: Check package name, try `--no-cache`, or verify repository availability

### Version mismatch
```
Using closest match: nginx-full v1.24.0
```
**Solution**: Verify exact package name in repository

### Cache issues
```bash
# Force fresh queries
saigen refresh-versions --no-cache nginx.yaml

# Or clear cache
saigen cache clear
```

## Comparison

| Feature | refresh-versions | update | generate |
|---------|-----------------|--------|----------|
| LLM | ❌ | ✅ | ✅ |
| Cost | Free | $$ | $$ |
| Speed | Seconds | Minutes | Minutes |
| Updates | Versions | All | New file |

## Tips

💡 Use `--check-only` first  
💡 Keep backups enabled  
💡 Target specific providers for speed  
💡 Use `--no-cache` for latest data  
💡 Validate after updates  

## Help

```bash
saigen refresh-versions --help
```

## Documentation

- Full docs: `docs/refresh-versions-command.md`
- Implementation: `docs/summaries/refresh-versions-implementation.md`
