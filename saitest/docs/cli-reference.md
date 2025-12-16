# Saitest CLI Reference

Complete reference for saitest command-line interface.

## Installation

```bash
# Install with saitest support
pip install sai-suite[saitest]

# Or install from source
cd sai-suite/saitest
pip install -e .
```

## Configuration

Set your LLM API key:

```bash
# OpenAI
export OPENAI_API_KEY="your-key-here"

# Or Anthropic
export ANTHROPIC_API_KEY="your-key-here"
```

## Commands

### verify

Verify software and generate saidata by testing installations across platforms.

```bash
saitest verify <software> [OPTIONS]
```

**Arguments:**
- `software` - Name of the software to verify (required)

**Options:**
- `--platforms, -p TEXT` - Comma-separated list of platforms to test (e.g., "ubuntu:22.04,debian:12")
- `--output-dir, -o PATH` - Directory to save generated saidata files
- `--format, -f [yaml|json]` - Output format (default: yaml)
- `--verbose, -v` - Display detailed progress messages
- `--config, -c PATH` - Custom configuration file
- `--help` - Show help message

**Examples:**

```bash
# Basic verification (auto-selects platforms)
saitest verify nginx

# Specify platforms
saitest verify nginx --platforms ubuntu:22.04,debian:12,fedora:40

# Save output to directory
saitest verify apache --output-dir ./saidata

# Verbose output
saitest verify postgresql --verbose

# JSON format
saitest verify redis --format json --output-dir ./output

# Multiple options
saitest verify mysql \
  --platforms ubuntu:22.04,debian:12 \
  --output-dir ./saidata \
  --verbose
```

**Output:**

Without `--output-dir`, displays results to stdout:

```
Verifying nginx...
✓ Discovery complete: Found 3 providers (apt, snap, source)
✓ Selected platforms: ubuntu:22.04, debian:12
✓ Testing ubuntu:22.04 with apt... Success
✓ Testing ubuntu:22.04 with snap... Success
✓ Testing debian:12 with apt... Success
✓ Analysis complete: 15 observations
✓ Generated saidata with 3 provider overrides
✓ Quality check: 0.92 confidence

Results:
- Platforms tested: 2
- Providers tested: 3
- Observations: 15
- Confidence: 0.92
- Needs review: No
```

With `--output-dir`, writes files:

```
./saidata/nginx/
├── default.yaml
├── ubuntu/
│   └── 22.04.yaml
└── debian/
    └── 12.yaml
```

### test

Test existing saidata by verifying it matches actual installation behavior.

```bash
saitest test <saidata_file> [OPTIONS]
```

**Arguments:**
- `saidata_file` - Path to saidata file to test (required)

**Options:**
- `--platforms, -p TEXT` - Comma-separated list of platforms to test
- `--verbose, -v` - Display detailed progress messages
- `--config, -c PATH` - Custom configuration file
- `--help` - Show help message

**Examples:**

```bash
# Test saidata file
saitest test software/nginx/default.yaml

# Test with specific platforms
saitest test software/nginx/default.yaml --platforms ubuntu:22.04,debian:12

# Verbose output
saitest test software/apache/default.yaml --verbose
```

**Output:**

```
Testing software/nginx/default.yaml...
✓ Loaded saidata for nginx
✓ Testing ubuntu:22.04 with apt... Match
✓ Testing debian:12 with apt... Match
✓ Analysis complete

Results:
- Platforms tested: 2
- Match confidence: 0.95
- Discrepancies: 0
- Status: PASS
```

## Platform Identifiers

Saitest supports the following platform formats:

**Ubuntu:**
- `ubuntu:22.04` - Ubuntu 22.04 LTS
- `ubuntu:24.04` - Ubuntu 24.04 LTS
- `ubuntu:20.04` - Ubuntu 20.04 LTS

**Debian:**
- `debian:12` - Debian 12 (Bookworm)
- `debian:11` - Debian 11 (Bullseye)
- `debian:10` - Debian 10 (Buster)

**Fedora:**
- `fedora:40` - Fedora 40
- `fedora:39` - Fedora 39
- `fedora:38` - Fedora 38

**Rocky Linux:**
- `rockylinux:9` - Rocky Linux 9
- `rockylinux:8` - Rocky Linux 8

**CentOS:**
- `centos:stream9` - CentOS Stream 9
- `centos:stream8` - CentOS Stream 8

**Alpine:**
- `alpine:3.19` - Alpine 3.19
- `alpine:3.18` - Alpine 3.18

## Provider Support

Saitest automatically detects and tests all providers with valid providerdata definitions:

**Package Managers:**
- `apt` - Debian/Ubuntu package manager
- `dnf` - Fedora/Rocky/CentOS package manager
- `yum` - Legacy RHEL package manager
- `pacman` - Arch Linux package manager
- `zypper` - openSUSE package manager
- `apk` - Alpine package manager
- `brew` - Homebrew (macOS/Linux)
- `snap` - Snap packages
- `flatpak` - Flatpak packages

**Language Package Managers:**
- `pip` - Python packages
- `npm` - Node.js packages
- `gem` - Ruby gems
- `cargo` - Rust packages
- `go` - Go modules

**Other Providers:**
- `source` - Build from source
- `binary` - Pre-compiled binaries
- `script` - Installation scripts

**Note:** Saitest tests any provider with a valid providerdata file in the `providers/` directory. New providers are automatically supported when providerdata is added.

## Output Formats

### YAML Format (default)

```yaml
version: "0.3"
metadata:
  name: nginx
  description: "High-performance HTTP server"
  homepage: "https://nginx.org"
  license: "BSD-2-Clause"

packages:
  - name: nginx
    package_name: nginx
    version: "1.24.0"

services:
  - name: nginx
    type: systemd
    enabled: true

files:
  - path: /usr/sbin/nginx
    purpose: binary
  - path: /etc/nginx/nginx.conf
    purpose: config

commands:
  - name: nginx
    path: /usr/sbin/nginx

ports:
  - number: 80
    protocol: tcp
  - number: 443
    protocol: tcp

providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx-full
```

### JSON Format

```json
{
  "version": "0.3",
  "metadata": {
    "name": "nginx",
    "description": "High-performance HTTP server",
    "homepage": "https://nginx.org",
    "license": "BSD-2-Clause"
  },
  "packages": [
    {
      "name": "nginx",
      "package_name": "nginx",
      "version": "1.24.0"
    }
  ],
  "services": [
    {
      "name": "nginx",
      "type": "systemd",
      "enabled": true
    }
  ]
}
```

## Configuration File

Create a `saitest.yaml` configuration file:

```yaml
# LLM Configuration
llm:
  provider: openai  # or anthropic
  model: gpt-4o
  temperature: 0.0

# Container Configuration
containers:
  cpu_limit: 2
  memory_limit: 2g
  timeout: 600
  max_concurrent: 4

# Verification Configuration
verification:
  max_retries: 2
  confidence_threshold: 0.7
  default_platforms:
    - ubuntu:22.04
    - debian:12

# Output Configuration
output:
  format: yaml
  include_metadata: true
  include_confidence_scores: true
```

Use with `--config`:

```bash
saitest verify nginx --config saitest.yaml
```

## Environment Variables

- `OPENAI_API_KEY` - OpenAI API key (required if using OpenAI)
- `ANTHROPIC_API_KEY` - Anthropic API key (required if using Anthropic)
- `SAITEST_CONFIG` - Default configuration file path
- `SAITEST_OUTPUT_DIR` - Default output directory
- `DOCKER_HOST` - Docker daemon host (default: unix:///var/run/docker.sock)

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Invalid arguments
- `3` - Docker not available
- `4` - LLM API error
- `5` - Validation error
- `6` - Low confidence (needs human review)

## Troubleshooting

### Docker not available

```
Error: Docker is not available. Please install Docker and ensure it's running.
```

**Solution:** Install Docker and start the Docker daemon.

### LLM API error

```
Error: Failed to connect to OpenAI API. Check your API key.
```

**Solution:** Verify your API key is set correctly:

```bash
echo $OPENAI_API_KEY
```

### Low confidence warning

```
Warning: Generated saidata has low confidence (0.65). Human review recommended.
```

**Solution:** Review the generated saidata manually and verify observations.

### Platform not supported

```
Error: Platform 'custom:1.0' is not supported.
```

**Solution:** Use a supported platform identifier or add custom platform mapping.

### Provider not found

```
Warning: Provider 'custom-pkg' not found in providerdata. Skipping.
```

**Solution:** Ensure providerdata file exists in `providers/` directory.

## Best Practices

### Platform Selection

- Test at least 2 platforms for good coverage
- Include different package managers (apt, dnf, etc.)
- Test both LTS and current versions
- Consider your target deployment environments

### Output Organization

- Use `--output-dir` to organize saidata by software
- Follow the structure: `software/{name}/default.yaml`
- Keep OS-specific overrides in subdirectories
- Version control your generated saidata

### Quality Assurance

- Review saidata with confidence < 0.8
- Verify provider-specific overrides
- Test generated saidata with `saitest test`
- Validate against schema before committing

### Performance

- Limit platforms to 3-4 for faster results
- Use cached Docker images
- Run during off-peak hours for large batches
- Consider parallel testing (future feature)

## Integration Examples

### CI/CD Pipeline

```yaml
# .github/workflows/verify-saidata.yml
name: Verify Saidata

on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install saitest
        run: pip install sai-suite[saitest]
      - name: Verify saidata
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          saitest verify nginx --platforms ubuntu:22.04,debian:12
```

### Batch Verification Script

```bash
#!/bin/bash
# verify-all.sh

SOFTWARE_LIST="nginx apache postgresql redis mysql"
PLATFORMS="ubuntu:22.04,debian:12"
OUTPUT_DIR="./saidata"

for software in $SOFTWARE_LIST; do
  echo "Verifying $software..."
  saitest verify "$software" \
    --platforms "$PLATFORMS" \
    --output-dir "$OUTPUT_DIR" \
    --verbose
done
```

### Python Integration

```python
from saitest.core.orchestrator import run_verification

# Run verification programmatically
result = run_verification(
    software="nginx",
    platforms=["ubuntu:22.04", "debian:12"],
    config={"llm": {"model": "gpt-4o"}}
)

print(f"Confidence: {result['overall_confidence']}")
print(f"Platforms tested: {len(result['platform_results'])}")
```

## Related Documentation

- [Architecture](architecture.md) - Design details
- [Examples](examples/) - Usage examples
- [Main README](README.md) - Overview
