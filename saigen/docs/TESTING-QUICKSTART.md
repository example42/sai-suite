# Testing Quick Start

Get started with saidata testing in 5 minutes.

## For sai-suite Developers

### 1. Install Development Version

```bash
cd sai-suite
pip install -e ".[dev]"
```

### 2. Test the CLI

```bash
saigen test-system --help
```

### 3. Build Docker Images

```bash
make docker-build-test
```

### 4. Test an Example

```bash
cd examples/testing
saigen test-system nginx-example.yaml
```

## For saidata Repository Maintainers

### 1. Copy Workflow

```bash
# In saidata repo
mkdir -p .github/workflows
curl -o .github/workflows/test-saidata.yml \
  https://raw.githubusercontent.com/example42/sai-suite/main/examples/ci-cd/github-actions-test-saidata.yml
```

### 2. Commit and Push

```bash
git add .github/workflows/test-saidata.yml
git commit -m "Add automated testing"
git push
```

### 3. Watch It Run

Go to GitHub Actions tab and watch your tests run!

## For Contributors

### 1. Install saigen

```bash
pip install saigen
```

### 2. Test Your Saidata File

```bash
saigen test-system your-package.yaml
```

### 3. Test with Docker (Multi-OS)

```bash
# Ubuntu
docker run --rm -v $(pwd):/data ghcr.io/example42/sai-test-ubuntu:latest \
  saigen test-system /data/your-package.yaml

# Fedora
docker run --rm -v $(pwd):/data ghcr.io/example42/sai-test-fedora:latest \
  saigen test-system /data/your-package.yaml
```

### 4. Submit PR

Your PR will be automatically tested on multiple platforms!

## Common Commands

```bash
# Test single file (dry-run)
saigen test-system package.yaml

# Test with verbose output
saigen test-system -v package.yaml

# Test all files in directory
saigen test-system --batch packages/

# Generate JSON report
saigen test-system --format json -o report.json package.yaml

# Real installation test (WARNING: modifies system)
sudo saigen test-system --real-install package.yaml
```

## Docker Commands

```bash
# Build test images
make docker-build-test

# Test with Ubuntu
docker run --rm -v $(pwd):/data sai-test-ubuntu saigen test-system /data/package.yaml

# Test with Fedora
docker run --rm -v $(pwd):/data sai-test-fedora saigen test-system /data/package.yaml

# Batch test
docker run --rm -v $(pwd)/packages:/data sai-test-ubuntu \
  saigen test-system --batch /data
```

## What Gets Tested

✅ Package existence in repositories  
✅ Service availability  
✅ File locations  
✅ Installation (with --real-install)

## Output Formats

- **text** - Human-readable (default)
- **json** - Machine-readable for CI/CD
- **junit** - JUnit XML for test reporting

## Need Help?

- Full guide: [docs/testing-guide.md](testing-guide.md)
- Docker images: [docker/README.md](../docker/README.md)
- CI/CD examples: [examples/ci-cd/](../examples/ci-cd/)
- Setup for saidata repo: [examples/saidata-repo/TESTING-SETUP.md](../examples/saidata-repo/TESTING-SETUP.md)

## Next Steps

1. ✅ Test locally
2. ✅ Test with Docker
3. ✅ Set up CI/CD
4. 🔲 Set up self-hosted runners (optional)
5. 🔲 Monitor test results
6. 🔲 Iterate and improve

Happy testing! 🚀
