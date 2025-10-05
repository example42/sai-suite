# Release Checklist - SAI Monorepo

Use this checklist before publishing packages to PyPI.

## Pre-Release Verification

### Code Quality
- [ ] All tests pass: `make test`
- [ ] Code is formatted: `make format`
- [ ] Linters pass: `make lint`
- [ ] Type checking passes: `mypy sai saigen`
- [ ] No security issues: `bandit -r sai saigen`

### Build Verification
- [ ] SAI builds successfully: `python -m build sai`
- [ ] SAIGEN builds successfully: `python -m build saigen`
- [ ] Both packages build: `make build`
- [ ] Wheel files created in `dist/`
- [ ] Twine check passes: `twine check dist/*`

### Documentation
- [ ] README.md is up to date
- [ ] CHANGELOG.md includes new changes
- [ ] Version numbers are correct
- [ ] All links work
- [ ] Examples are tested
- [ ] API docs are current

### Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Tested on Linux
- [ ] Tested on macOS
- [ ] Tested on Windows (if applicable)

## TestPyPI Release

### Publish to TestPyPI
- [ ] Clean previous builds: `make clean`
- [ ] Build packages: `make build`
- [ ] Publish to TestPyPI: `make publish-test`
- [ ] Verify packages appear on TestPyPI
  - [ ] https://test.pypi.org/project/sai/
  - [ ] https://test.pypi.org/project/saigen/

### Test Installation from TestPyPI
- [ ] Create fresh virtual environment
- [ ] Install SAI from TestPyPI:
  ```bash
  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ sai
  ```
- [ ] Install SAIGEN from TestPyPI:
  ```bash
  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ saigen
  ```
- [ ] Verify commands work:
  - [ ] `sai --version`
  - [ ] `sai --help`
  - [ ] `saigen --version`
  - [ ] `saigen --help`
- [ ] Test basic functionality:
  - [ ] SAI can load saidata
  - [ ] SAIGEN can generate metadata
  - [ ] Both tools work together

### Verify Package Metadata
- [ ] Package names correct
- [ ] Descriptions accurate
- [ ] Keywords appropriate
- [ ] Classifiers correct
- [ ] URLs work
- [ ] License specified
- [ ] Authors listed
- [ ] README displays correctly on TestPyPI

## Production Release

### Pre-Release
- [ ] All TestPyPI tests passed
- [ ] Version numbers finalized
- [ ] CHANGELOG.md updated
- [ ] Git tag created: `git tag v0.1.0`
- [ ] Tag pushed: `git push origin v0.1.0`

### Release Notes
- [ ] Create GitHub release
- [ ] Include changelog
- [ ] Highlight breaking changes (if any)
- [ ] Include upgrade instructions
- [ ] Link to documentation

### Publish to PyPI
- [ ] Clean builds: `make clean`
- [ ] Build packages: `make build`
- [ ] Final verification: `twine check dist/*`
- [ ] Publish to PyPI: `make publish-prod`
  - [ ] Confirm publication
  - [ ] Enter credentials (or use token)
- [ ] Verify packages on PyPI:
  - [ ] https://pypi.org/project/sai/
  - [ ] https://pypi.org/project/saigen/

### Post-Release Verification
- [ ] Install from PyPI in fresh environment:
  ```bash
  pip install sai
  pip install saigen
  ```
- [ ] Verify versions: `sai --version`, `saigen --version`
- [ ] Test basic functionality
- [ ] Check PyPI package pages display correctly
- [ ] Verify download statistics appear

## Post-Release Tasks

### Documentation
- [ ] Update website (if applicable)
- [ ] Update external documentation
- [ ] Announce on social media
- [ ] Update project status badges
- [ ] Close milestone on GitHub

### Communication
- [ ] Announce on GitHub Discussions
- [ ] Post to relevant forums/communities
- [ ] Update project homepage
- [ ] Send announcement email (if applicable)

### Monitoring
- [ ] Monitor PyPI download stats
- [ ] Watch for issues on GitHub
- [ ] Check for user feedback
- [ ] Monitor error reports (if applicable)

## Rollback Plan

If issues are discovered after release:

### Minor Issues
- [ ] Document workarounds
- [ ] Plan patch release
- [ ] Update documentation

### Critical Issues
- [ ] Yank problematic version from PyPI:
  ```bash
  # For SAI
  pip install twine
  twine upload --skip-existing --repository pypi dist/sai-*
  # Then yank: https://pypi.org/help/#yanked
  
  # For SAIGEN
  twine upload --skip-existing --repository pypi dist/saigen-*
  ```
- [ ] Publish hotfix release
- [ ] Notify users
- [ ] Update documentation

## Version-Specific Checklist

### First Release (v0.1.0)
- [ ] Verify package names available on PyPI
- [ ] Set up PyPI trusted publishing
- [ ] Configure GitHub Actions secrets
- [ ] Test complete workflow end-to-end

### Major Release (vX.0.0)
- [ ] Review breaking changes
- [ ] Update migration guide
- [ ] Deprecation warnings in place
- [ ] Backward compatibility tested

### Minor Release (vX.Y.0)
- [ ] New features documented
- [ ] Examples updated
- [ ] API additions noted

### Patch Release (vX.Y.Z)
- [ ] Bug fixes documented
- [ ] Regression tests added
- [ ] No breaking changes

## Automation Checklist

### GitHub Actions
- [ ] Build workflow passes
- [ ] Test workflow passes
- [ ] Publish workflow configured
- [ ] Secrets configured:
  - [ ] PYPI_API_TOKEN (for production)
  - [ ] TEST_PYPI_API_TOKEN (for testing)

### Pre-commit Hooks
- [ ] Hooks installed: `pre-commit install`
- [ ] Hooks pass: `pre-commit run --all-files`

## Emergency Contacts

- **PyPI Support**: https://pypi.org/help/
- **GitHub Support**: https://support.github.com/
- **Project Maintainers**: team@sai.software

## Notes

Add any release-specific notes here:

---

**Release Date**: _____________  
**Released By**: _____________  
**Version**: _____________  
**Notes**: _____________
