# Testing Setup for Saidata Repository

This guide helps you set up automated testing for the saidata repository.

## Quick Setup

### 1. Copy GitHub Actions Workflow

Copy the workflow file to your saidata repository:

```bash
# In saidata repo
mkdir -p .github/workflows
cp /path/to/sai-python/examples/ci-cd/github-actions-test-saidata.yml \
   .github/workflows/test-saidata.yml
```

### 2. Commit and Push

```bash
git add .github/workflows/test-saidata.yml
git commit -m "Add automated saidata testing"
git push
```

### 3. Verify Workflow

1. Go to your repository on GitHub
2. Click "Actions" tab
3. You should see the "Test Saidata" workflow
4. It will run automatically on PRs and pushes

## What Gets Tested

The workflow tests saidata files on:
- ✅ Ubuntu (apt packages)
- ✅ Debian (apt packages)
- ✅ Fedora (dnf packages)
- ✅ Alpine (apk packages)
- ✅ macOS (brew packages)
- ✅ Windows (winget packages)

## Test Types

### Dry-run Tests (Default)
- Checks if packages exist in repositories
- Fast and safe
- Runs on every PR

### Real Installation Tests (Optional)
- Actually installs packages
- Requires self-hosted runners
- Runs on schedule or manual trigger

## Setting Up Self-Hosted Runners (Optional)

For real installation tests on your lab machines:

### 1. Run Setup Script

On your lab machine:

```bash
curl -sSL https://raw.githubusercontent.com/example42/sai-python/main/scripts/development/setup-test-runner.sh | bash
```

### 2. Configure Runner

1. Go to your saidata repo on GitHub
2. Settings > Actions > Runners
3. Click "New self-hosted runner"
4. Follow the instructions
5. Use labels: `self-hosted`, `linux`, `bare-metal`

### 3. Start Runner

```bash
cd ~/actions-runner
./run.sh
```

Or install as a service:

```bash
cd ~/actions-runner
sudo ./svc.sh install
sudo ./svc.sh start
```

## Repository Structure

Your saidata repository should look like:

```
saidata/
├── .github/
│   └── workflows/
│       └── test-saidata.yml
├── packages/
│   ├── nginx.yaml
│   ├── apache.yaml
│   └── ...
└── README.md
```

## Testing Locally

Before pushing, test locally:

```bash
# Install saigen
pip install saigen

# Test a single file
saigen test-system packages/nginx.yaml

# Test all files
saigen test-system --batch packages/

# Test with Docker
docker run --rm -v $(pwd):/data \
  ghcr.io/example42/sai-test-ubuntu:latest \
  saigen test-system --batch /data/packages
```

## Workflow Configuration

### Trigger on Specific Paths

The workflow only runs when saidata files change:

```yaml
on:
  pull_request:
    paths:
      - 'packages/**/*.yaml'
      - 'packages/**/*.yml'
```

### Scheduled Tests

Full test suite runs daily:

```yaml
schedule:
  - cron: '0 2 * * *'  # 2 AM UTC
```

### Manual Trigger

You can also trigger manually:
1. Go to Actions tab
2. Select "Test Saidata" workflow
3. Click "Run workflow"

## Test Results

### PR Comments

Test results appear as:
- ✅ Check marks for passing tests
- ❌ X marks for failing tests
- Detailed logs available in Actions tab

### Artifacts

Test results are saved as artifacts:
- `test-results-ubuntu.json`
- `test-results-debian.json`
- `test-results-fedora.json`
- etc.

Download from Actions tab > Workflow run > Artifacts

## Troubleshooting

### Workflow Not Running

- Check if workflow file is in `.github/workflows/`
- Verify YAML syntax is correct
- Check repository Actions settings are enabled

### Tests Failing

- Check test logs in Actions tab
- Test locally to reproduce
- Verify package names are correct
- Check if packages exist in repositories

### Self-Hosted Runner Issues

- Verify runner is online (Settings > Actions > Runners)
- Check runner logs: `~/actions-runner/_diag/`
- Restart runner service if needed

## Best Practices

1. **Test Before Pushing** - Run local tests first
2. **Small PRs** - Test one or few files at a time
3. **Clear Commit Messages** - Describe what's being tested
4. **Monitor Results** - Check Actions tab regularly
5. **Update Runners** - Keep self-hosted runners updated

## Support

- Documentation: https://sai.software/docs/testing
- Issues: https://github.com/example42/sai-python/issues
- Discussions: https://github.com/example42/saidata/discussions

## Next Steps

1. ✅ Copy workflow file
2. ✅ Commit and push
3. ✅ Verify workflow runs
4. 🔲 Set up self-hosted runners (optional)
5. 🔲 Test some saidata files
6. 🔲 Monitor and iterate

Happy testing! 🧪
