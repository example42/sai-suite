# Refresh Versions Troubleshooting Guide

## Overview

This guide provides solutions to common issues encountered when using the `saigen refresh-versions` command. It covers repository configuration problems, network errors, package resolution issues, and OS-specific challenges.

## Common Issues

### 1. Missing Repository Configuration

**Symptom:**
```
⚠ Repository apt-ubuntu-noble not configured. Skipping ubuntu/24.04.yaml
```

**Cause:**
The repository configuration for the specified OS version doesn't exist in the repository configuration files.

**Solutions:**

#### Solution 1: Add Repository Configuration

Add the missing repository to the appropriate configuration file:

```bash
# Edit the provider configuration file
vim saigen/repositories/configs/apt.yaml
```

Add a new repository entry:

```yaml
repositories:
  # ... existing repositories ...
  
  - name: "apt-ubuntu-noble"
    type: "apt"
    platform: "linux"
    distribution: ["ubuntu"]
    architecture: ["amd64", "arm64", "armhf"]
    
    version_mapping:
      "24.04": "noble"
    
    eol: false
    query_type: "bulk_download"
    
    endpoints:
      packages: "http://archive.ubuntu.com/ubuntu/dists/noble/main/binary-{arch}/Packages.gz"
    
    parsing:
      format: "debian_packages"
      compression: "gzip"
    
    cache:
      ttl_hours: 24
      max_size_mb: 100
    
    metadata:
      description: "Ubuntu 24.04 (Noble) Main Repository"
      maintainer: "Ubuntu"
      priority: 90
      enabled: true
```

See [Repository Configuration Guide](repository-configuration-guide.md) for detailed instructions.

#### Solution 2: Use Different OS Version

If you don't need that specific OS version, skip it or use a different version:

```bash
# Skip the problematic file
saigen refresh-versions --all-variants --skip-default software/ng/nginx/

# Or manually refresh only configured OS versions
saigen refresh-versions software/ng/nginx/ubuntu/22.04.yaml
```

#### Solution 3: Verify Repository List

Check which repositories are configured:

```bash
# List all repositories
saigen repositories list-repos

# List repositories for specific provider
saigen repositories list-repos --provider apt

# Check if specific repository exists
saigen repositories list-repos | grep noble
```

### 2. Package Not Found in Repository

**Symptom:**
```
⚠ Package 'nginx' not found in apt-ubuntu-jammy
```

**Cause:**
The package name doesn't exist in the repository, or the repository cache is outdated.

**Solutions:**

#### Solution 1: Refresh Repository Cache

Clear the cache and query again:

```bash
# Refresh without cache
saigen refresh-versions --no-cache software/ng/nginx/ubuntu/22.04.yaml

# Or clear cache manually
rm -rf ~/.saigen/cache/repositories/apt-ubuntu-jammy
saigen refresh-versions software/ng/nginx/ubuntu/22.04.yaml
```

#### Solution 2: Verify Package Name

Check if the package name is correct:

```bash
# Search for the package in the repository
saigen repositories search --repository apt-ubuntu-jammy nginx

# Try alternative package names
saigen repositories search --repository apt-ubuntu-jammy nginx-core
saigen repositories search --repository apt-ubuntu-jammy nginx-full
```

#### Solution 3: Check Repository Availability

Verify the repository is accessible:

```bash
# Test repository endpoint
curl -I "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/Packages.gz"

# Check repository status
saigen repositories status --repository apt-ubuntu-jammy
```

#### Solution 4: Use Verbose Mode

Get more details about the search:

```bash
# Enable verbose output
saigen --verbose refresh-versions software/ng/nginx/ubuntu/22.04.yaml
```

### 3. Network Errors

**Symptom:**
```
✗ Failed to access repository apt-ubuntu-jammy: Connection timeout
```

**Cause:**
Network connectivity issues, repository server down, or firewall blocking access.

**Solutions:**

#### Solution 1: Check Network Connectivity

```bash
# Test internet connectivity
ping -c 3 archive.ubuntu.com

# Test repository URL
curl -I "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/Packages.gz"

# Check DNS resolution
nslookup archive.ubuntu.com
```

#### Solution 2: Use Cached Data

If you have cached data, use it instead of querying:

```bash
# Use cached repository data
saigen refresh-versions --use-cache software/ng/nginx/ubuntu/22.04.yaml
```

#### Solution 3: Configure Proxy

If behind a proxy, configure it:

```bash
# Set proxy environment variables
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"

# Run refresh-versions
saigen refresh-versions software/ng/nginx/ubuntu/22.04.yaml
```

#### Solution 4: Retry Later

Repository servers may be temporarily unavailable:

```bash
# Wait and retry
sleep 60
saigen refresh-versions software/ng/nginx/ubuntu/22.04.yaml
```

#### Solution 5: Use Alternative Mirror

Configure an alternative repository mirror:

```bash
# Edit repository configuration
vim saigen/repositories/configs/apt.yaml

# Change endpoint URL to alternative mirror
endpoints:
  packages: "http://mirror.example.com/ubuntu/dists/jammy/main/binary-{arch}/Packages.gz"
```

### 4. Missing Codename Mapping

**Symptom:**
```
⚠ Could not resolve codename for ubuntu 26.04
```

**Cause:**
The repository configuration doesn't have a `version_mapping` entry for that OS version.

**Solutions:**

#### Solution 1: Add Version Mapping

Add the version mapping to the repository configuration:

```bash
# Edit repository configuration
vim saigen/repositories/configs/apt.yaml
```

Add or update the version_mapping:

```yaml
- name: "apt-ubuntu-oracular"
  type: "apt"
  # ... other fields ...
  
  version_mapping:
    "26.04": "oracular"  # Add this mapping
```

#### Solution 2: Verify Codename

Check the official codename for the OS version:

- Ubuntu: https://wiki.ubuntu.com/Releases
- Debian: https://www.debian.org/releases/
- Fedora: https://fedoraproject.org/wiki/Releases

#### Solution 3: Check Repository Configuration

Verify the repository configuration is loaded:

```bash
# List repositories with version mappings
saigen repositories list-repos --show-mappings

# Check specific repository
saigen repositories info apt-ubuntu-oracular
```

### 5. Invalid File Path

**Symptom:**
```
⚠ Could not extract OS information from path: custom/nginx.yaml
```

**Cause:**
The file path doesn't follow the expected structure for OS detection.

**Solutions:**

#### Solution 1: Use Standard Structure

Reorganize files to follow the standard structure:

```bash
# Move file to standard location
mkdir -p software/ng/nginx/ubuntu
mv custom/nginx.yaml software/ng/nginx/ubuntu/22.04.yaml
```

#### Solution 2: Specify OS Manually

If you can't change the structure, specify OS context manually (if supported):

```bash
# Specify OS context explicitly
saigen refresh-versions --os ubuntu --os-version 22.04 custom/nginx.yaml
```

#### Solution 3: Accept Generic Behavior

If OS detection fails, the command treats the file as OS-agnostic:

```bash
# File will be refreshed using generic provider repositories
saigen refresh-versions custom/nginx.yaml
```

### 6. Schema Validation Failure

**Symptom:**
```
✗ Updated saidata failed validation. Restored from backup.
Error: Invalid field 'version' in packages[0]
```

**Cause:**
The updated saidata doesn't conform to the saidata 0.3 schema.

**Solutions:**

#### Solution 1: Check Backup

The command automatically restores from backup. Check the backup file:

```bash
# List backup files
ls -la software/ng/nginx/*.backup.*

# Compare with original
diff software/ng/nginx/ubuntu/22.04.yaml software/ng/nginx/ubuntu/22.04.backup.20250422_143022.yaml
```

#### Solution 2: Validate Manually

Validate the saidata file manually:

```bash
# Validate against schema
saigen validate software/ng/nginx/ubuntu/22.04.yaml

# Check for specific errors
saigen validate --verbose software/ng/nginx/ubuntu/22.04.yaml
```

#### Solution 3: Fix Schema Issues

Fix the schema validation errors:

```bash
# Edit the file
vim software/ng/nginx/ubuntu/22.04.yaml

# Validate again
saigen validate software/ng/nginx/ubuntu/22.04.yaml
```

#### Solution 4: Report Bug

If the validation failure seems incorrect, report it:

```bash
# Create issue with details
# Include: saidata file, error message, command used
```

### 7. Permission Errors

**Symptom:**
```
✗ Failed to create ubuntu/24.04.yaml: Permission denied
```

**Cause:**
Insufficient permissions to write to the directory.

**Solutions:**

#### Solution 1: Check Permissions

```bash
# Check directory permissions
ls -la software/ng/nginx/

# Check if directory exists
ls -la software/ng/nginx/ubuntu/
```

#### Solution 2: Fix Permissions

```bash
# Make directory writable
chmod u+w software/ng/nginx/ubuntu/

# Or change ownership
sudo chown $USER:$USER software/ng/nginx/ubuntu/
```

#### Solution 3: Create Directory

If the directory doesn't exist, create it:

```bash
# Create directory structure
mkdir -p software/ng/nginx/ubuntu

# Set appropriate permissions
chmod 755 software/ng/nginx/ubuntu
```

### 8. EOL Repository Warnings

**Symptom:**
```
ℹ Repository apt-ubuntu-focal is for EOL OS version Ubuntu 20.04
```

**Cause:**
The repository is marked as end-of-life (EOL) in the configuration.

**Solutions:**

#### Solution 1: Acknowledge and Continue

This is informational only. The command will continue normally:

```bash
# The refresh will proceed despite the warning
saigen refresh-versions software/ng/nginx/ubuntu/20.04.yaml
```

#### Solution 2: Upgrade to Supported Version

Consider upgrading to a supported OS version:

```bash
# Create file for newer OS version
saigen refresh-versions --create-missing software/ng/nginx/ubuntu/22.04.yaml

# Update your systems to use the newer version
```

#### Solution 3: Remove EOL Files

If you no longer need EOL OS versions:

```bash
# Remove EOL OS-specific files
rm software/ng/nginx/ubuntu/20.04.yaml

# Update documentation to reflect supported versions
```

### 9. Multiple Files Failing

**Symptom:**
```
Summary:
  Files processed: 5
  Successful: 2
  Failed: 3
  Errors: 3
```

**Cause:**
Multiple files encountered errors during processing.

**Solutions:**

#### Solution 1: Review Error Details

Check the detailed error messages:

```bash
# Run with verbose output
saigen --verbose refresh-versions --all-variants software/ng/nginx/
```

#### Solution 2: Process Files Individually

Process files one at a time to isolate issues:

```bash
# Process each file separately
for file in software/ng/nginx/*/*.yaml; do
  echo "Processing: $file"
  saigen refresh-versions "$file" || echo "Failed: $file"
done
```

#### Solution 3: Check Common Issues

Look for common problems across failed files:

```bash
# Check if repositories are configured
saigen repositories list-repos

# Check network connectivity
ping -c 3 archive.ubuntu.com

# Check file permissions
ls -la software/ng/nginx/*/
```

### 10. Incorrect Version Updates

**Symptom:**
Package version is updated to an incorrect or unexpected value.

**Cause:**
Repository returned wrong package, or package name matching is incorrect.

**Solutions:**

#### Solution 1: Verify Repository Data

Check what the repository actually contains:

```bash
# Search repository for the package
saigen repositories search --repository apt-ubuntu-jammy nginx

# Check package details
saigen repositories info --repository apt-ubuntu-jammy nginx
```

#### Solution 2: Use Check-Only Mode

Preview changes before applying:

```bash
# Check what would be updated
saigen refresh-versions --check-only software/ng/nginx/ubuntu/22.04.yaml
```

#### Solution 3: Restore from Backup

If incorrect update was applied:

```bash
# List backups
ls -la software/ng/nginx/*.backup.*

# Restore from backup
cp software/ng/nginx/ubuntu/22.04.backup.20250422_143022.yaml \
   software/ng/nginx/ubuntu/22.04.yaml
```

#### Solution 4: Manual Correction

Manually correct the version:

```bash
# Edit the file
vim software/ng/nginx/ubuntu/22.04.yaml

# Update version to correct value
# Save and validate
saigen validate software/ng/nginx/ubuntu/22.04.yaml
```

## Debugging Tips

### Enable Verbose Output

Always use verbose mode when troubleshooting:

```bash
saigen --verbose refresh-versions software/ng/nginx/ubuntu/22.04.yaml
```

### Check Repository Configuration

Verify repository configurations are loaded correctly:

```bash
# List all repositories
saigen repositories list-repos

# Show repository details
saigen repositories info apt-ubuntu-jammy

# Validate repository configuration
saigen repositories validate-config saigen/repositories/configs/apt.yaml
```

### Test Repository Connectivity

Test repository endpoints:

```bash
# Test HTTP endpoint
curl -I "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/Packages.gz"

# Download and inspect package list
curl "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/Packages.gz" | \
  gunzip | grep -A 10 "^Package: nginx$"
```

### Inspect Cache

Check cached repository data:

```bash
# List cache directory
ls -la ~/.saigen/cache/repositories/

# Check specific repository cache
ls -la ~/.saigen/cache/repositories/apt-ubuntu-jammy/

# Clear cache if needed
rm -rf ~/.saigen/cache/repositories/apt-ubuntu-jammy/
```

### Validate Saidata Files

Validate saidata files before and after refresh:

```bash
# Validate before refresh
saigen validate software/ng/nginx/ubuntu/22.04.yaml

# Refresh
saigen refresh-versions software/ng/nginx/ubuntu/22.04.yaml

# Validate after refresh
saigen validate software/ng/nginx/ubuntu/22.04.yaml
```

### Check OS Detection

Verify OS detection is working correctly:

```bash
# Show detected OS information
saigen config show-os

# Test OS detection for specific file
saigen debug extract-os-info software/ng/nginx/ubuntu/22.04.yaml
```

## Getting Help

### Check Documentation

- [Refresh Versions Command](refresh-versions-command.md)
- [Repository Configuration Guide](repository-configuration-guide.md)
- [Saidata Structure Guide](saidata-structure-guide.md)
- [Repository Management](repository-management.md)

### Report Issues

If you encounter a bug or unexpected behavior:

1. **Gather Information:**
   ```bash
   # Run with verbose output
   saigen --verbose refresh-versions software/ng/nginx/ubuntu/22.04.yaml > debug.log 2>&1
   
   # Collect system information
   saigen --version
   python --version
   uname -a
   ```

2. **Create Minimal Reproduction:**
   - Identify the smallest saidata file that reproduces the issue
   - Note the exact command used
   - Include any error messages

3. **Report Issue:**
   - Open an issue on GitHub: https://github.com/example42/sai
   - Include: command, error message, debug log, system info
   - Attach minimal reproduction case

### Community Support

- GitHub Discussions: https://github.com/example42/sai/discussions
- Documentation: https://sai.software/docs
- Examples: https://github.com/example42/saidata

## Preventive Measures

### Regular Maintenance

```bash
# Update repository cache regularly
saigen repositories update-cache

# Validate repository configurations
saigen repositories validate-all

# Check for outdated versions
saigen refresh-versions --check-only --all-variants software/
```

### Use Version Control

```bash
# Track saidata files in git
git add software/
git commit -m "Update saidata files"

# Review changes before committing
git diff software/ng/nginx/
```

### Automate Testing

```bash
# Create test script
cat > test-refresh.sh << 'EOF'
#!/bin/bash
set -e

# Test refresh on sample files
for file in software/ng/nginx/*/*.yaml; do
  echo "Testing: $file"
  saigen refresh-versions --check-only "$file"
done

echo "All tests passed!"
EOF

chmod +x test-refresh.sh
./test-refresh.sh
```

### Monitor Repository Health

```bash
# Check repository status
saigen repositories status --all

# Test repository connectivity
saigen repositories test-connectivity --all

# Report unhealthy repositories
saigen repositories status --unhealthy-only
```

## See Also

- [Refresh Versions Command](refresh-versions-command.md)
- [Repository Configuration Guide](repository-configuration-guide.md)
- [Repository Troubleshooting](repository-troubleshooting.md)
- [Saidata Structure Guide](saidata-structure-guide.md)
