# Saigen Testing Framework

System-level testing framework for validating saidata files on real systems.

## Overview

This framework validates saidata files by testing them on actual systems, checking:
- Package availability in repositories
- Installation capability
- Service availability
- File locations

## Components

- **`models.py`** - Data models for test results
- **`validator.py`** - Core validation logic
- **`runner.py`** - Test execution engine
- **`reporter.py`** - Result formatting and reporting

## Usage

### CLI

```bash
# Dry-run test (checks package existence only)
saigen test-system nginx.yaml

# Test with actual installation
saigen test-system --real-install nginx.yaml

# Batch test all files in directory
saigen test-system --batch packages/

# Generate JSON report
saigen test-system --format json -o report.json nginx.yaml
```

### Programmatic

```python
from pathlib import Path
from saigen.testing import TestRunner, TestReporter

# Create runner
runner = TestRunner(dry_run=True, verbose=True)

# Run tests
suite = runner.run_tests(Path("nginx.yaml"))

# Generate report
reporter = TestReporter(output_format="text")
report = reporter.report(suite)
print(report)
```

## Test Types

1. **Package Existence** - Verifies packages exist in repositories
2. **Installation** - Tests actual installation (with `--real-install`)
3. **Services** - Checks if services are available
4. **Files** - Validates file locations

## Output Formats

- **text** - Human-readable format (default)
- **json** - Machine-readable format for CI/CD
- **junit** - JUnit XML for test reporting

## Docker Testing

Test across different OS using Docker:

```bash
docker run --rm -v $(pwd):/data ghcr.io/example42/sai-test-ubuntu:latest \
  saigen test-system /data/nginx.yaml
```

## See Also

- [Testing Guide](../docs/testing-guide.md)
- [Docker Images](../../docker/README.md)
- [CI/CD Examples](../../examples/ci-cd/)
