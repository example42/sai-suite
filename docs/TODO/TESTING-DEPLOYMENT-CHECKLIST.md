# Testing Framework Deployment Checklist

This checklist guides you through deploying the testing framework to production.

## Phase 1: sai-python Repository

### Development
- [x] Implement testing framework (`saigen/testing/`)
- [x] Add CLI command (`saigen test-system`)
- [x] Create Docker images (Dockerfiles)
- [x] Write documentation
- [x] Create examples
- [x] Test locally

### Testing
- [ ] Add unit tests for testing framework
  ```bash
  # Create tests/test_testing_framework.py
  pytest tests/test_testing_framework.py
  ```

- [ ] Run full test suite
  ```bash
  make test
  ```

- [ ] Test CLI command
  ```bash
  saigen test-system examples/testing/python-example.yaml
  ```

- [ ] Verify diagnostics
  ```bash
  # Should show no errors
  ```

### Docker Images
- [ ] Build test images
  ```bash
  make docker-build-test
  ```

- [ ] Test images locally
  ```bash
  docker run --rm sai-test-ubuntu saigen test-system --help
  docker run --rm sai-test-fedora saigen test-system --help
  docker run --rm sai-test-debian saigen test-system --help
  docker run --rm sai-test-alpine saigen test-system --help
  ```

- [ ] Tag images
  ```bash
  make docker-tag-test
  ```

- [ ] Push to GitHub Container Registry
  ```bash
  # First, authenticate with GitHub
  echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
  
  # Then push
  make docker-push-test
  ```

### Release
- [ ] Update CHANGELOG.md
  ```markdown
  ## [X.Y.Z] - 2025-05-10
  
  ### Added
  - System-level testing framework for saidata validation
  - `saigen test-system` CLI command
  - Docker test images for multi-OS testing
  - CI/CD integration examples
  ```

- [ ] Update version
  ```bash
  # Update saigen/version.py
  ```

- [ ] Create git tag
  ```bash
  git add .
  git commit -m "Add testing framework for saidata validation"
  git tag -a vX.Y.Z -m "Release vX.Y.Z: Testing framework"
  git push origin main --tags
  ```

- [ ] Build and publish to PyPI
  ```bash
  make build
  make publish
  ```

## Phase 2: saidata Repository

### Setup
- [ ] Copy GitHub Actions workflow
  ```bash
  mkdir -p .github/workflows
  cp /path/to/sai-python/examples/ci-cd/github-actions-test-saidata.yml \
     .github/workflows/test-saidata.yml
  ```

- [ ] Review and customize workflow
  - [ ] Adjust paths if needed
  - [ ] Configure schedule
  - [ ] Set up notifications

- [ ] Commit and push
  ```bash
  git add .github/workflows/test-saidata.yml
  git commit -m "Add automated saidata testing"
  git push
  ```

### Verification
- [ ] Check Actions tab on GitHub
- [ ] Verify workflow runs successfully
- [ ] Check test results
- [ ] Review artifacts

### Documentation
- [ ] Add testing section to README
  ```markdown
  ## Testing
  
  Saidata files are automatically tested on multiple platforms.
  See [TESTING.md](TESTING.md) for details.
  ```

- [ ] Create TESTING.md
  ```bash
  cp /path/to/sai-python/examples/saidata-repo/TESTING-SETUP.md \
     TESTING.md
  ```

- [ ] Update CONTRIBUTING.md
  ```markdown
  ## Testing Your Changes
  
  Before submitting a PR, test your saidata files:
  
  \`\`\`bash
  saigen test-system your-package.yaml
  \`\`\`
  ```

## Phase 3: Lab Machines (Optional)

### Setup Self-Hosted Runners
- [ ] Choose lab machines
  - [ ] Ubuntu/Debian machine
  - [ ] Fedora/RHEL machine
  - [ ] Other OS as needed

- [ ] Run setup script on each machine
  ```bash
  curl -sSL https://raw.githubusercontent.com/example42/sai-python/main/scripts/development/setup-test-runner.sh | bash
  ```

- [ ] Configure runners
  ```bash
  cd ~/actions-runner
  ./config.sh --url https://github.com/example42/saidata --token YOUR_TOKEN
  ```

- [ ] Set labels
  - `self-hosted`
  - `linux` or `macos` or `windows`
  - `bare-metal`
  - OS-specific (e.g., `ubuntu`, `fedora`)

- [ ] Start runners
  ```bash
  # As service (recommended)
  cd ~/actions-runner
  sudo ./svc.sh install
  sudo ./svc.sh start
  
  # Or manually
  ./run.sh
  ```

### Verification
- [ ] Check runner status in GitHub
  - Settings > Actions > Runners
  - Should show "Idle" or "Active"

- [ ] Test runner with manual workflow run
  - Actions > Test Saidata > Run workflow

- [ ] Verify test results

### Maintenance
- [ ] Set up monitoring
- [ ] Schedule runner updates
- [ ] Document runner maintenance procedures

## Phase 4: Communication

### Internal
- [ ] Notify team about new testing framework
- [ ] Share documentation links
- [ ] Provide training if needed

### External
- [ ] Update website (sai.software)
- [ ] Write blog post about testing
- [ ] Update GitHub README
- [ ] Announce on social media/forums

### Documentation
- [ ] Ensure all docs are up to date
- [ ] Add examples to website
- [ ] Create video tutorial (optional)

## Verification Checklist

### sai-python
- [ ] `saigen test-system --help` works
- [ ] Can test example files
- [ ] Docker images build successfully
- [ ] Package published to PyPI
- [ ] Documentation is accessible

### saidata
- [ ] GitHub Actions workflow runs
- [ ] Tests pass on multiple OS
- [ ] PR checks work correctly
- [ ] Test results are visible
- [ ] Contributors can test locally

### Lab Machines
- [ ] Runners are online
- [ ] Can execute tests
- [ ] Results reported correctly
- [ ] No security issues

## Rollback Plan

If issues arise:

### sai-python
```bash
# Revert to previous version
git revert <commit-hash>
git push

# Unpublish from PyPI (if critical issue)
# Contact PyPI support
```

### saidata
```bash
# Disable workflow
# Edit .github/workflows/test-saidata.yml
# Set: if: false

git commit -m "Temporarily disable testing"
git push
```

### Lab Machines
```bash
# Stop runners
cd ~/actions-runner
sudo ./svc.sh stop

# Or remove runner
./config.sh remove --token YOUR_TOKEN
```

## Success Criteria

- [x] Testing framework implemented and working
- [ ] Docker images published and accessible
- [ ] PyPI package released
- [ ] saidata repository has automated testing
- [ ] At least 10 saidata files tested successfully
- [ ] Documentation complete and clear
- [ ] No critical bugs reported
- [ ] Team trained and comfortable with system

## Timeline

- **Week 1**: Complete sai-python testing and release
- **Week 2**: Deploy to saidata repository
- **Week 3**: Set up lab machines (optional)
- **Week 4**: Monitor, iterate, improve

## Support

- Issues: https://github.com/example42/sai-python/issues
- Discussions: https://github.com/example42/saidata/discussions
- Documentation: https://sai.software/docs/testing

## Notes

- Keep this checklist updated as you progress
- Mark items complete with [x]
- Add notes about any issues encountered
- Document any deviations from the plan

---

**Last Updated**: 2025-05-10  
**Status**: Ready to begin deployment
