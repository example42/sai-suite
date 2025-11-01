# Basic Verification Example

This example demonstrates the basic workflow for verifying software and generating saidata.

## Prerequisites

- Docker installed and running
- Saitest installed (`pip install sai-suite[saitest]`)
- OpenAI or Anthropic API key configured

## Simple Verification

### Step 1: Verify Software

```bash
saitest verify nginx
```

**What happens:**
1. Discovery Agent researches nginx installation methods
2. Platform Selection Agent chooses 2-4 representative platforms
3. Installation Agent tests each platform in Docker containers
4. Analysis Agent identifies patterns across platforms
5. Generation Agent creates saidata
6. Quality Check Agent validates and scores results

**Output:**

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

Generated saidata:
---
version: "0.3"
metadata:
  name: nginx
  description: "High-performance HTTP server"
...
```

### Step 2: Save to File

```bash
saitest verify nginx --output-dir ./saidata
```

**Output structure:**

```
./saidata/nginx/
├── default.yaml          # Common configuration
├── ubuntu/
│   └── 22.04.yaml       # Ubuntu 22.04 specific
└── debian/
    └── 12.yaml          # Debian 12 specific
```

### Step 3: Review Generated Files

**default.yaml** (common across all platforms):

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
```

**ubuntu/22.04.yaml** (Ubuntu-specific):

```yaml
version: "0.3"

packages:
  - name: nginx
    package_name: nginx-full  # Different package name
    version: "1.18.0"         # Specific version

providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx-full
```

**debian/12.yaml** (Debian-specific):

```yaml
version: "0.3"

packages:
  - name: nginx
    package_name: nginx-light  # Different package name
    version: "1.22.1"          # Specific version

providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx-light
```

## Specify Platforms

### Choose Specific Platforms

```bash
saitest verify apache --platforms ubuntu:22.04,debian:12,fedora:40
```

**Why specify platforms:**
- Test specific deployment targets
- Ensure coverage of different package managers
- Verify behavior on specific OS versions

### Platform Options

**Ubuntu:**
```bash
--platforms ubuntu:22.04,ubuntu:24.04
```

**Debian:**
```bash
--platforms debian:11,debian:12
```

**RHEL Family:**
```bash
--platforms rockylinux:8,rockylinux:9,fedora:40
```

**Mixed:**
```bash
--platforms ubuntu:22.04,debian:12,rockylinux:9
```

## Verbose Output

### See Detailed Progress

```bash
saitest verify postgresql --verbose
```

**Verbose output shows:**

```
Verifying postgresql...

[Discovery Agent]
→ Querying saigen repository cache...
→ Found postgresql in apt repository (version 14.5)
→ Found postgresql in dnf repository (version 15.1)
→ Scanning providerdata directory...
→ Available providers: apt, dnf, snap, source
→ Using LLM to research installation methods...
✓ Discovery complete

[Platform Selection Agent]
→ Using LLM to select representative platforms...
→ Selected: ubuntu:22.04, debian:12, rockylinux:9
✓ Platform selection complete

[Installation Agent - ubuntu:22.04 with apt]
→ Spawning container: ubuntu:22.04
→ Pulling image ubuntu:22.04... Done
→ Container started: abc123def456
→ Capturing filesystem baseline...
→ Executing: apt-get update && apt-get install -y postgresql
→ Installation complete (45.2s)
→ Capturing filesystem changes...
→ Found 127 new files
→ Found 1 service: postgresql.service
→ Found 15 binaries in /usr/bin
→ Testing installation: dpkg -l postgresql
✓ Installation successful

[Installation Agent - ubuntu:22.04 with snap]
→ Spawning container: ubuntu:22.04
→ Container started: def456ghi789
→ Executing: snap install postgresql
→ Installation complete (32.1s)
✓ Installation successful

[Analysis Agent]
→ Aggregating 245 observations across 3 platforms
→ Using LLM to identify patterns...
→ Common patterns: 15 files, 1 service, 5 commands, 1 port
→ Platform variations: 3 package names, 2 config locations
→ Calculating confidence scores...
✓ Analysis complete

[Generation Agent]
→ Generating default.yaml...
→ Generating ubuntu/22.04.yaml override...
→ Generating debian/12.yaml override...
→ Generating rockylinux/9.yaml override...
✓ Generation complete

[Quality Check Agent]
→ Validating against schema 0.3...
→ Schema validation: PASS
→ Using LLM to assess quality...
→ Completeness score: 0.95
→ Accuracy score: 0.89
→ Overall confidence: 0.92
✓ Quality check complete

Results:
- Platforms tested: 3
- Providers tested: 4
- Observations: 245
- Confidence: 0.92
- Needs review: No
```

## Test Generated Saidata

### Verify Accuracy

```bash
saitest test ./saidata/nginx/default.yaml
```

**What happens:**
1. Loads existing saidata
2. Extracts software name (nginx)
3. Runs verification workflow
4. Compares observed behavior with saidata
5. Reports match confidence

**Output:**

```
Testing ./saidata/nginx/default.yaml...
✓ Loaded saidata for nginx
✓ Testing ubuntu:22.04 with apt... Match (0.98)
✓ Testing debian:12 with apt... Match (0.96)
✓ Analysis complete

Results:
- Platforms tested: 2
- Match confidence: 0.97
- Discrepancies: 0
- Status: PASS

Discrepancies: None
```

### Test with Specific Platforms

```bash
saitest test ./saidata/nginx/default.yaml --platforms ubuntu:22.04
```

## JSON Output

### Generate JSON Format

```bash
saitest verify redis --format json --output-dir ./output
```

**Output:**

```json
{
  "version": "0.3",
  "metadata": {
    "name": "redis",
    "description": "In-memory data structure store",
    "homepage": "https://redis.io",
    "license": "BSD-3-Clause"
  },
  "packages": [
    {
      "name": "redis",
      "package_name": "redis-server",
      "version": "7.0.0"
    }
  ],
  "services": [
    {
      "name": "redis",
      "type": "systemd",
      "enabled": true
    }
  ],
  "ports": [
    {
      "number": 6379,
      "protocol": "tcp"
    }
  ]
}
```

## Common Patterns

### 1. Quick Verification

```bash
# Auto-select platforms, display to stdout
saitest verify software-name
```

### 2. Production Verification

```bash
# Specific platforms, save to directory, verbose
saitest verify software-name \
  --platforms ubuntu:22.04,debian:12 \
  --output-dir ./saidata \
  --verbose
```

### 3. Test and Verify

```bash
# Generate saidata
saitest verify nginx --output-dir ./saidata

# Test it
saitest test ./saidata/nginx/default.yaml

# If match confidence is high, commit
git add ./saidata/nginx/
git commit -m "Add saidata for nginx"
```

## Understanding Results

### Confidence Scores

- **0.9 - 1.0**: Excellent - Ready to use
- **0.8 - 0.9**: Good - Minor review recommended
- **0.7 - 0.8**: Fair - Review recommended
- **< 0.7**: Low - Human review required

### Observations

Observations are data points collected during installation:

- **Files**: Binaries, configs, libraries
- **Services**: Systemd units, init scripts
- **Ports**: Listening ports
- **Commands**: Executable commands
- **Packages**: Installed packages

### Provider Overrides

Provider-specific configurations for different installation methods:

```yaml
providers:
  apt:
    packages:
      - name: nginx
        package_name: nginx-full
  
  snap:
    packages:
      - name: nginx
        package_name: nginx
```

## Next Steps

- [Multi-Platform Testing](multi-platform-testing.md) - Test across many platforms
- [Multi-Provider Testing](multi-provider-testing.md) - Test multiple installation methods
- [CI/CD Integration](ci-cd-integration.md) - Automate verification
- [CLI Reference](../cli-reference.md) - Complete command documentation

## Troubleshooting

### Docker not running

```
Error: Docker is not available
```

**Solution:**
```bash
# Start Docker
sudo systemctl start docker

# Or on macOS
open -a Docker
```

### Low confidence warning

```
Warning: Generated saidata has low confidence (0.65)
```

**Solution:**
- Review generated saidata manually
- Check observations for accuracy
- Test on additional platforms
- Verify provider-specific overrides

### API key not set

```
Error: OpenAI API key not found
```

**Solution:**
```bash
export OPENAI_API_KEY="your-key-here"
```
