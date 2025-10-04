# New Feature: refresh-versions Command

## 🎉 What's New

We've added a new `refresh-versions` command to saigen that updates package versions in your saidata files **without using LLM services**. This means:

- ✅ **Zero cost** - No LLM API charges
- ✅ **Fast execution** - Completes in seconds
- ✅ **Safe updates** - Automatic backups
- ✅ **Selective updates** - Target specific providers

## Quick Start

```bash
# Check for version updates
saigen refresh-versions --check-only nginx.yaml

# Apply version updates
saigen refresh-versions nginx.yaml

# Update specific providers only
saigen refresh-versions --providers apt,brew nginx.yaml
```

## Why Use This?

### Before
To update versions in your saidata files, you had to:
1. Run `saigen update` (uses LLM, costs money, takes time)
2. Or manually edit each version field

### Now
```bash
saigen refresh-versions nginx.yaml
```

Done! All package versions updated from repository data in seconds.

## Use Cases

### 1. Routine Version Maintenance
Keep your saidata files up-to-date without LLM costs:
```bash
# Weekly cron job
0 0 * * 0 saigen refresh-versions /path/to/saidata/*.yaml
```

### 2. CI/CD Version Checks
Detect outdated versions in your pipeline:
```bash
# In your CI pipeline
saigen refresh-versions --check-only nginx.yaml
if [ $? -ne 0 ]; then
  echo "Versions are outdated!"
  exit 1
fi
```

### 3. Bulk Updates
Update multiple files quickly:
```bash
for file in saidata/*.yaml; do
  saigen refresh-versions "$file"
done
```

### 4. Safe Preview
Check what would change before applying:
```bash
saigen refresh-versions --check-only --show-unchanged nginx.yaml
```

## What Gets Updated

The command updates version fields in:
- Top-level packages
- Provider-specific packages
- Package sources
- Binaries
- Sources
- Scripts

**Everything else stays the same** - descriptions, URLs, configurations, etc.

## Example Output

```bash
$ saigen refresh-versions --check-only nginx.yaml

Check Results for nginx:
  Total packages checked: 5
  Updates available: 2
  Already up-to-date: 3
  Execution time: 1.23s

Available Updates:
  • apt/nginx: 1.20.1 → 1.24.0
  • brew/nginx: 1.20.1 → 1.25.3

💡 Run without --check-only to apply 2 update(s)
```

## Safety Features

### Automatic Backups
Every update creates a timestamped backup:
```
nginx.yaml
nginx.backup.20250410_143022.yaml
```

### Check-Only Mode
Preview changes without modifying files:
```bash
saigen refresh-versions --check-only nginx.yaml
```

### Dry Run
See what would happen without doing anything:
```bash
saigen --dry-run refresh-versions nginx.yaml
```

## Options Reference

```bash
saigen refresh-versions [OPTIONS] SAIDATA_FILE

Options:
  -o, --output PATH         Save to different file
  --providers TEXT          Target specific providers (apt, brew, etc.)
  --backup / --no-backup    Create backup (default: enabled)
  --backup-dir PATH         Custom backup directory
  --check-only              Preview changes only
  --show-unchanged          Show up-to-date packages
  --use-cache / --no-cache  Use repository cache (default: enabled)
```

## When to Use Each Command

| Command | Use When |
|---------|----------|
| `refresh-versions` | You just need version updates |
| `update` | You need full metadata refresh |
| `generate` | You're creating new saidata |

## Best Practices

1. **Always check first**
   ```bash
   saigen refresh-versions --check-only nginx.yaml
   ```

2. **Keep backups enabled**
   ```bash
   saigen refresh-versions nginx.yaml  # Backup created automatically
   ```

3. **Validate after updates**
   ```bash
   saigen refresh-versions nginx.yaml
   saigen validate nginx.yaml
   ```

4. **Use provider filters for speed**
   ```bash
   saigen refresh-versions --providers apt nginx.yaml
   ```

5. **Fresh data when needed**
   ```bash
   saigen refresh-versions --no-cache nginx.yaml
   ```

## Documentation

- Full documentation: `docs/refresh-versions-command.md`
- Implementation details: `docs/summaries/refresh-versions-implementation.md`
- Tests: `tests/test_refresh_versions.py`

## Feedback

This is a new feature! If you encounter any issues or have suggestions, please let us know.

---

**Happy version refreshing! 🚀**
