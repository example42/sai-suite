# Saidata Testing Guide

This guide explains how to test saidata files on real systems using the `saigen test-system` command.

## Overview

The testing framework validates saidata files by:
- Checking package existence in repositories
- Testing installation (optional)
- Verifying service availability
- Validating file locations

## Quick Start

### Basic Testing (Dry-run)

Test a single saidata file without modifying the system:

```bash
saigen test-system nginx.yaml
```

This checks if packages exist in repositories but doesn't install anything.

### Real Installation Testing

Test with actual installation (requires appropriate permissions):

```bash
sudo saigen test-system --real-install nginx.yaml
```

⚠️ **Warning**: This will modify your system by installing packages.

### Batch Testing

Test all saidata files in a directory:

```bash
saigen test-system --batch packages/
```

## Output Formats

### Text Output (Default)

Human-readable format:

```bash
saigen test-system nginx.yaml
```

### JSON Output

Machine-readable format for CI/CD:

```bash
saigen test-system --format json nginx.yaml
```

### JUnit XML

For CI/CD integration:

```bash
saigen test-system --format junit -o results.xml nginx.yaml
```

## Docker Testing

Test across different operating systems using Docker:

### Ubuntu/Debian

```bash
docker run --rm -v $(pwd):/data ghcr.io/example42/sai-test-ubuntu:latest \
  saigen test-system /data/nginx.yaml
```

### Fedora

```bash
docker run --rm -v $(pwd):/data ghcr.io/example42/sai-test-fedora:latest \
  saigen test-system /data/nginx.yaml
```

### Alpine

```bash
docker run --rm -v $(pwd):/data ghcr.io/example42/sai-test-alpine:latest \
  saigen test-system /data/nginx.yaml
```

### With Real Installation

```bash
docker run --rm --privileged -v $(pwd):/data ghcr.io/example42/sai-test-ubuntu:latest \
  saigen test-system --real-install /data/nginx.yaml
```

## CI/CD Integration

### GitHub Actions

Example workflow for testing saidata files:

```yaml
name: Test Saidata

on: [pull_request, push]

jobs:
  test-linux:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        os: [ubuntu, debian, fedora, alpine]
    steps:
      - uses: actions/checkout@v4
      
      - name: Test saidata
        run: |
          docker run --rm -v $PWD:/data \
            ghcr.io/example42/sai-test-${{ matrix.os }}:latest \
            saigen test-system --batch /data/packages

  test-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install saigen
        run: pip install saigen
      
      - name: Test saidata
        run: saigen test-system --batch packages/

  test-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install saigen
        run: pip install saigen
      
      - name: Test saidata
        run: saigen test-system --batch packages/
```

## Self-Hosted Runners

For testing on specific hardware or OS versions, use self-hosted runners:

### Setup

1. Register a self-hosted runner on your lab machine
2. Label it appropriately (e.g., `self-hosted`, `linux`, `bare-metal`)
3. Configure the workflow to use it

### Example Workflow

```yaml
test-lab:
  runs-on: [self-hosted, linux, bare-metal]
  steps:
    - uses: actions/checkout@v4
    - run: saigen test-system --real-install packages/nginx.yaml
```

## Test Results

### Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed
- `2` - Tests passed with warnings

### Test Types

The framework runs these validation tests:

1. **Package Existence** - Verifies packages exist in repositories
2. **Installation** - Tests actual installation (with `--real-install`)
3. **Services** - Checks if services are available
4. **Files** - Validates file locations

### Example Output

```
============================================================
Test Suite: nginx.yaml
============================================================
Duration: 2.34s
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

## Best Practices

### Development

- Use dry-run mode during development
- Test locally with Docker before pushing
- Use verbose mode (`-v`) for debugging

### CI/CD

- Run dry-run tests on every PR
- Use matrix strategy for multi-OS testing
- Generate JUnit XML for test reporting
- Use self-hosted runners for real installation tests

### Production

- Schedule periodic full-suite tests
- Test on actual target systems
- Monitor test results and trends
- Keep test environments up to date

## Troubleshooting

### Package Not Found

If a package isn't found:
- Verify the package name is correct
- Check if the package manager is available
- Ensure repositories are up to date

### Permission Denied

For installation tests:
- Use `sudo` on Linux/macOS
- Run as Administrator on Windows
- Use `--privileged` flag with Docker

### Timeout Issues

If tests timeout:
- Check network connectivity
- Verify repository availability
- Increase timeout if needed

## Advanced Usage

### Custom Test Scripts

Create custom test scripts for complex scenarios:

```bash
#!/bin/bash
# test-all.sh

for file in packages/*.yaml; do
  echo "Testing $file..."
  saigen test-system "$file" || exit 1
done
```

### Integration with Other Tools

Combine with other validation tools:

```bash
# Validate schema first
saigen validate nginx.yaml

# Then test on system
saigen test-system nginx.yaml
```

### Parallel Testing

Test multiple files in parallel:

```bash
find packages/ -name "*.yaml" | \
  xargs -P 4 -I {} saigen test-system {}
```

## See Also

- [CLI Reference](cli-reference.md)
- [Docker Images](../docker/README.md)
- [CI/CD Examples](../examples/ci-cd/)
