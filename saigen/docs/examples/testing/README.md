# Testing Examples

Example saidata files and testing scenarios.

## Files

- **`nginx-example.yaml`** - Simple example for testing nginx
- **`test-local.sh`** - Script for local testing
- **`test-docker.sh`** - Script for Docker-based testing

## Quick Start

### Test Locally

```bash
# Dry-run test (safe, checks package existence only)
saigen test-system nginx-example.yaml

# Verbose output
saigen test-system -v nginx-example.yaml

# JSON output
saigen test-system --format json nginx-example.yaml
```

### Test with Docker

```bash
# Ubuntu
docker run --rm -v $(pwd):/data ghcr.io/example42/sai-test-ubuntu:latest \
  saigen test-system /data/nginx-example.yaml

# Fedora
docker run --rm -v $(pwd):/data ghcr.io/example42/sai-test-fedora:latest \
  saigen test-system /data/nginx-example.yaml

# Alpine
docker run --rm -v $(pwd):/data ghcr.io/example42/sai-test-alpine:latest \
  saigen test-system /data/nginx-example.yaml
```

### Real Installation Test

⚠️ **Warning**: This will install packages on your system!

```bash
sudo saigen test-system --real-install nginx-example.yaml
```

## Expected Results

### Dry-run Mode

```
============================================================
Test Suite: nginx-example.yaml
============================================================
Duration: 1.23s
Total: 4 | Passed: 3 | Failed: 0 | Skipped: 1 | Errors: 0
------------------------------------------------------------
✓ package_exists (0.45s)
  All packages exist in repositories
✓ services (0.12s)
  All services exist
✓ files (0.08s)
  All files exist
○ installation (0.00s)
  Skipped in dry-run mode
============================================================
```

### Real Installation Mode

```
============================================================
Test Suite: nginx-example.yaml
============================================================
Duration: 15.67s
Total: 4 | Passed: 4 | Failed: 0 | Skipped: 0 | Errors: 0
------------------------------------------------------------
✓ package_exists (0.45s)
  All packages exist in repositories
✓ installation (14.23s)
  Installation successful
✓ services (0.12s)
  All services exist
✓ files (0.08s)
  All files exist
============================================================
```

## Creating Your Own Tests

1. Create a saidata YAML file
2. Test it locally with dry-run
3. Test with Docker for multi-OS validation
4. Optionally test with real installation
5. Add to CI/CD pipeline

## See Also

- [Testing Guide](../../docs/testing-guide.md)
- [Docker Images](../../docker/README.md)
