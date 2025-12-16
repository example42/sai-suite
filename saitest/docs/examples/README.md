# Saitest Examples

This directory contains usage examples and workflows for saitest.

## Examples

- [Basic Verification](basic-verification.md) - Simple verification workflow
- [Multi-Platform Testing](multi-platform-testing.md) - Testing across multiple platforms
- [Multi-Provider Testing](multi-provider-testing.md) - Testing multiple installation methods
- [CI/CD Integration](ci-cd-integration.md) - Integrating saitest into CI/CD pipelines
- [Custom Workflows](custom-workflows.md) - Advanced usage patterns

## Quick Examples

### Basic Verification

```bash
# Verify nginx with auto-selected platforms
saitest verify nginx

# Verify with specific platforms
saitest verify apache --platforms ubuntu:22.04,debian:12
```

### Save Output

```bash
# Save to directory
saitest verify postgresql --output-dir ./saidata

# Output structure:
# ./saidata/postgresql/
# ├── default.yaml
# ├── ubuntu/
# │   └── 22.04.yaml
# └── debian/
#     └── 12.yaml
```

### Test Existing Saidata

```bash
# Test saidata file
saitest test software/nginx/default.yaml

# Test with specific platforms
saitest test software/nginx/default.yaml --platforms ubuntu:22.04
```

### Verbose Output

```bash
# See detailed progress
saitest verify redis --verbose

# Output shows:
# - Discovery progress
# - Platform selection
# - Installation steps
# - Observations collected
# - Analysis results
# - Quality scores
```

## Common Workflows

### 1. Generate Saidata for New Software

```bash
# Step 1: Verify and generate
saitest verify newsoftware \
  --platforms ubuntu:22.04,debian:12,fedora:40 \
  --output-dir ./saidata \
  --verbose

# Step 2: Review generated files
cat ./saidata/newsoftware/default.yaml

# Step 3: Test the generated saidata
saitest test ./saidata/newsoftware/default.yaml

# Step 4: Commit to repository
git add ./saidata/newsoftware/
git commit -m "Add saidata for newsoftware"
```

### 2. Update Existing Saidata

```bash
# Step 1: Test current saidata
saitest test software/nginx/default.yaml --verbose

# Step 2: Re-verify with latest versions
saitest verify nginx \
  --platforms ubuntu:22.04,ubuntu:24.04,debian:12 \
  --output-dir ./updated

# Step 3: Compare results
diff software/nginx/default.yaml ./updated/nginx/default.yaml

# Step 4: Update if needed
cp ./updated/nginx/* software/nginx/
```

### 3. Multi-Provider Verification

```bash
# Verify software with multiple installation methods
saitest verify python \
  --platforms ubuntu:22.04,debian:12 \
  --verbose

# Saitest automatically tests:
# - apt (python3 package)
# - snap (python snap)
# - source (build from python.org)
# - binary (pre-compiled downloads)

# Result includes provider-specific overrides
```

### 4. Batch Verification

```bash
# Create list of software
cat > software-list.txt <<EOF
nginx
apache
postgresql
redis
mysql
EOF

# Verify all
while read software; do
  saitest verify "$software" \
    --platforms ubuntu:22.04,debian:12 \
    --output-dir ./saidata
done < software-list.txt
```

### 5. Platform-Specific Testing

```bash
# Test Ubuntu-specific behavior
saitest verify nginx --platforms ubuntu:22.04,ubuntu:24.04

# Test Debian-specific behavior
saitest verify nginx --platforms debian:11,debian:12

# Test RHEL-family behavior
saitest verify nginx --platforms rockylinux:8,rockylinux:9,fedora:40
```

## Integration Examples

### GitHub Actions

See [ci-cd-integration.md](ci-cd-integration.md) for complete CI/CD examples.

### Python Script

```python
from saitest.core.orchestrator import run_verification

# Verify software programmatically
result = run_verification(
    software="nginx",
    platforms=["ubuntu:22.04", "debian:12"]
)

if result["overall_confidence"] >= 0.8:
    print("✓ High confidence result")
else:
    print("⚠ Low confidence - needs review")
```

### Shell Script

```bash
#!/bin/bash
# verify-and-deploy.sh

SOFTWARE=$1
PLATFORMS="ubuntu:22.04,debian:12"
OUTPUT_DIR="./saidata"

# Verify
saitest verify "$SOFTWARE" \
  --platforms "$PLATFORMS" \
  --output-dir "$OUTPUT_DIR"

# Check exit code
if [ $? -eq 0 ]; then
  echo "✓ Verification successful"
  # Deploy to repository
  cp -r "$OUTPUT_DIR/$SOFTWARE" /path/to/saidata-repo/software/
else
  echo "✗ Verification failed"
  exit 1
fi
```

## Tips and Best Practices

### Platform Selection

- **Start small**: Test 2-3 platforms initially
- **Diverse coverage**: Include different package managers (apt, dnf, etc.)
- **LTS versions**: Prioritize long-term support releases
- **Target environments**: Match your deployment platforms

### Quality Assurance

- **Review low confidence**: Always review results with confidence < 0.8
- **Verify observations**: Check that detected files/services are correct
- **Test generated saidata**: Use `saitest test` to verify
- **Compare versions**: Check differences when updating

### Performance

- **Limit platforms**: 3-4 platforms is usually sufficient
- **Use cache**: Docker images are cached after first pull
- **Batch wisely**: Group similar software for efficiency
- **Monitor resources**: Watch Docker resource usage

### Output Organization

```
saidata/
├── nginx/
│   ├── default.yaml
│   ├── ubuntu/
│   │   ├── 22.04.yaml
│   │   └── 24.04.yaml
│   └── debian/
│       └── 12.yaml
├── apache/
│   ├── default.yaml
│   └── ubuntu/
│       └── 22.04.yaml
└── postgresql/
    ├── default.yaml
    ├── ubuntu/
    │   └── 22.04.yaml
    └── debian/
        └── 12.yaml
```

## Troubleshooting Examples

### Docker Issues

```bash
# Check Docker is running
docker ps

# Pull images manually if needed
docker pull ubuntu:22.04
docker pull debian:12

# Clean up old containers
docker container prune
```

### Low Confidence Results

```bash
# Re-run with verbose output
saitest verify software --verbose

# Test specific platform
saitest verify software --platforms ubuntu:22.04

# Review observations manually
cat output/software/default.yaml
```

### Provider Issues

```bash
# Check available providers
ls providers/

# Verify providerdata is valid
cat providers/apt.yaml

# Test specific provider
# (saitest automatically tests all available providers)
```

## Next Steps

- Read [CLI Reference](../cli-reference.md) for complete command documentation
- See [Architecture](../architecture.md) for design details
- Check [Main README](../README.md) for overview

## Contributing Examples

Have a useful example? Contribute it!

1. Create a new markdown file in this directory
2. Follow the existing format
3. Include clear explanations and code
4. Submit a pull request

See the main [sai-suite documentation](../../../docs/README.md) for contribution guidelines.
