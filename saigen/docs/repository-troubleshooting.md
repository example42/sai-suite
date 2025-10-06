# Repository Operations Troubleshooting Guide

## Quick Diagnosis

Use these commands to quickly diagnose repository issues:

```bash
# Check overall repository health
sai repository status --detailed

# Test repository connectivity
sai repository update --force

# Verify saidata loading
sai info nginx --verbose

# Check configuration
sai repository configure --show
```

## Common Error Messages and Solutions

### Authentication Errors

#### "Authentication failed" or "Permission denied"

**Possible Causes**:
- Invalid SSH key or token
- Expired credentials
- Incorrect repository URL
- Missing repository permissions

**Diagnostic Steps**:
```bash
# Check current configuration
sai repository configure --show

# Test SSH connection (for SSH URLs)
ssh -T git@github.com

# Test HTTPS connection (for HTTPS URLs)
git ls-remote https://github.com/example42/saidata

# Verify environment variables
echo $GITHUB_TOKEN
echo $SSH_AUTH_SOCK
```

**Solutions**:

1. **SSH Key Issues**:
   ```bash
   # Check if SSH key is loaded
   ssh-add -l
   
   # Add SSH key to agent
   ssh-add ~/.ssh/id_ed25519
   
   # Generate new SSH key if needed
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. **Token Issues**:
   ```bash
   # Verify token is set
   echo $GITHUB_TOKEN
   
   # Set token if missing
   export GITHUB_TOKEN="your_token_here"
   
   # Update repository configuration
   sai repository configure --url https://token:${GITHUB_TOKEN}@github.com/org/repo.git
   ```

3. **Repository Access**:
   - Verify you have read access to the repository
   - Check if repository exists and is not private
   - Ensure token has correct permissions (repo scope for private repos)

#### "Repository not found"

**Possible Causes**:
- Incorrect repository URL
- Repository is private and authentication failed
- Repository has been moved or deleted
- Network connectivity issues

**Solutions**:
```bash
# Verify repository URL
curl -I https://github.com/example42/saidata

# Check if repository is accessible
git ls-remote https://github.com/example42/saidata

# Try with authentication
git ls-remote https://token:${GITHUB_TOKEN}@github.com/org/repo.git

# Update to correct URL
sai repository configure --url https://github.com/correct/repository.git
```

### Network and Connectivity Issues

#### "Connection timed out" or "Network unreachable"

**Possible Causes**:
- Network connectivity problems
- Firewall blocking git operations
- Proxy configuration issues
- DNS resolution problems

**Diagnostic Steps**:
```bash
# Test basic connectivity
ping github.com

# Test HTTPS connectivity
curl -I https://github.com

# Test DNS resolution
nslookup github.com

# Check proxy settings
env | grep -i proxy
git config --global --get http.proxy
```

**Solutions**:

1. **Proxy Configuration**:
   ```bash
   # Configure git proxy
   git config --global http.proxy http://proxy.company.com:8080
   git config --global https.proxy https://proxy.company.com:8080
   
   # Or use environment variables
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=https://proxy.company.com:8080
   ```

2. **Firewall Issues**:
   - Ensure ports 443 (HTTPS) and 22 (SSH) are accessible
   - Contact network administrator if behind corporate firewall
   - Try switching from SSH to HTTPS URLs or vice versa

3. **DNS Issues**:
   ```bash
   # Try alternative DNS servers
   echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
   
   # Or use IP address directly (temporary)
   git config --global url."https://140.82.112.3/".insteadOf "https://github.com/"
   ```

#### "SSL certificate problem"

**Possible Causes**:
- Outdated certificates
- Corporate proxy with SSL inspection
- System clock issues

**Solutions**:
```bash
# Update certificates (Ubuntu/Debian)
sudo apt update && sudo apt install ca-certificates

# Update certificates (macOS)
brew install ca-certificates

# Temporary workaround (not recommended for production)
git config --global http.sslVerify false

# Check system time
date
```

### Git Availability Issues

#### "git: command not found"

**Possible Causes**:
- Git is not installed
- Git is not in PATH
- Using minimal container image without git

**Solutions**:

1. **Install Git**:
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install git
   
   # CentOS/RHEL/Fedora
   sudo dnf install git
   
   # macOS
   brew install git
   
   # Windows
   winget install Git.Git
   ```

2. **Verify Installation**:
   ```bash
   git --version
   which git
   ```

3. **Fallback Behavior**:
   - SAI automatically falls back to tarball downloads when git is unavailable
   - Check if tarball fallback is working: `sai repository status --detailed`

### Cache and Storage Issues

#### "Permission denied" (cache directory)

**Possible Causes**:
- Insufficient permissions on cache directory
- Cache directory owned by different user
- Disk space issues

**Solutions**:
```bash
# Check cache directory permissions
ls -la ~/.sai/cache/

# Fix permissions
chmod 755 ~/.sai/cache/
chmod -R 644 ~/.sai/cache/repositories/

# Check disk space
df -h ~/.sai/cache/

# Clear cache if needed
sai repository clear --all
```

#### "No space left on device"

**Solutions**:
```bash
# Check disk usage
df -h

# Clean up old repository caches
sai repository cleanup --keep-days 3

# Clear all caches
sai repository clear --all

# Configure smaller cache directory
sai repository configure --cache-dir /tmp/sai-cache
```

#### "Cache corrupted" or "Invalid cache"

**Solutions**:
```bash
# Clear corrupted cache
sai repository clear

# Force fresh download
sai repository update --force

# Check cache status
sai repository status --detailed
```

### Saidata Loading Issues

#### "Saidata not found for software 'X'"

**Possible Causes**:
- Software not available in repository
- Incorrect software name
- Repository not updated
- Hierarchical path issues

**Diagnostic Steps**:
```bash
# Check if repository is up to date
sai repository status

# Search for similar software names
sai search "partial_name"

# Check repository contents manually
ls ~/.sai/cache/repositories/*/software/

# Try with verbose output
sai info software_name --verbose
```

**Solutions**:

1. **Update Repository**:
   ```bash
   sai repository update --force
   ```

2. **Check Software Name**:
   ```bash
   # Try variations of the name
   sai info nginx
   sai info nginx-full
   sai info nginx-core
   ```

3. **Verify Hierarchical Structure**:
   ```bash
   # Check expected path
   ls ~/.sai/cache/repositories/*/software/ng/nginx/
   
   # Check if file exists
   find ~/.sai/cache/repositories/ -name "*nginx*" -type f
   ```

#### "Failed to parse saidata file"

**Possible Causes**:
- Corrupted saidata file
- Invalid YAML syntax
- Encoding issues

**Solutions**:
```bash
# Clear cache and re-download
sai repository clear
sai repository update --force

# Check file manually
cat ~/.sai/cache/repositories/*/software/ng/nginx/default.yaml

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('file.yaml'))"
```

### Performance Issues

#### "Repository operations are slow"

**Possible Causes**:
- Large repository size
- Slow network connection
- Disabled shallow clones
- Frequent updates

**Solutions**:

1. **Enable Shallow Clones**:
   ```yaml
   # In ~/.sai/config.yaml
   saidata_shallow_clone: true
   ```

2. **Increase Update Interval**:
   ```bash
   # Update less frequently (48 hours)
   sai repository configure --update-interval 172800
   ```

3. **Use Offline Mode**:
   ```bash
   # Work offline when possible
   sai repository configure --offline-mode
   ```

4. **Monitor Cache Size**:
   ```bash
   sai repository status --detailed
   sai repository cleanup --keep-days 7
   ```

#### "High memory usage during repository operations"

**Solutions**:
```bash
# Enable shallow clones
sai repository configure --shallow-clone

# Reduce timeout to fail faster
sai repository configure --timeout 120

# Clear old caches
sai repository cleanup --keep-days 3
```

## Advanced Troubleshooting

### Debug Mode

Enable verbose logging for detailed troubleshooting:

```bash
# Enable debug logging
export SAI_LOG_LEVEL=debug

# Run command with verbose output
sai --verbose repository update

# Check log files
tail -f ~/.sai/logs/sai.log
```

### Manual Repository Operations

Test repository operations manually:

```bash
# Clone repository manually
git clone https://github.com/example42/saidata /tmp/test-repo

# Check repository structure
ls -la /tmp/test-repo/software/

# Test specific saidata file
cat /tmp/test-repo/software/ng/nginx/default.yaml

# Clean up
rm -rf /tmp/test-repo
```

### Network Debugging

Detailed network troubleshooting:

```bash
# Test with curl
curl -v https://github.com/example42/saidata

# Test with git
GIT_CURL_VERBOSE=1 git ls-remote https://github.com/example42/saidata

# Check routing
traceroute github.com

# Test different protocols
git ls-remote https://github.com/example42/saidata  # HTTPS
git ls-remote git@github.com:example42/saidata.git  # SSH
```

### Configuration Debugging

Verify configuration is loaded correctly:

```bash
# Show all configuration
sai repository configure --show --json

# Check environment variables
env | grep SAI_
env | grep -i proxy

# Verify configuration file location
find ~ -name "*.yaml" -o -name "*.json" | grep -E "(sai|\.sai)"
```

## Recovery Procedures

### Complete Repository Reset

If repository system is completely broken:

```bash
# 1. Backup current configuration
cp ~/.sai/config.yaml ~/.sai/config.yaml.backup

# 2. Clear all repository data
rm -rf ~/.sai/cache/repositories/

# 3. Reset to default configuration
sai repository configure --url https://github.com/example42/saidata
sai repository configure --branch main
sai repository configure --auto-update

# 4. Test repository access
sai repository update --force
sai repository status --detailed

# 5. Test saidata loading
sai info nginx
```

### Fallback to Local Saidata

If repository system cannot be fixed:

```bash
# 1. Download saidata manually
wget https://github.com/example42/saidata/archive/main.zip
unzip main.zip -d ~/.sai/

# 2. Configure local paths
echo "saidata_paths:" >> ~/.sai/config.yaml
echo "  - ~/.sai/saidata-main/software/" >> ~/.sai/config.yaml

# 3. Disable repository updates
sai repository configure --no-auto-update
sai repository configure --offline-mode

# 4. Test local saidata
sai info nginx
```

## Prevention and Monitoring

### Health Checks

Regular repository health monitoring:

```bash
#!/bin/bash
# Repository health check script

echo "=== Repository Health Check ==="
echo "Date: $(date)"
echo

# Check repository status
echo "Repository Status:"
sai repository status --detailed

# Check recent update success
echo -e "\nLast Update:"
sai repository status | grep "Last Updated"

# Check cache size
echo -e "\nCache Status:"
du -sh ~/.sai/cache/repositories/

# Test saidata loading
echo -e "\nSaidata Loading Test:"
sai info nginx >/dev/null 2>&1 && echo "✓ Success" || echo "✗ Failed"

echo -e "\n=== End Health Check ==="
```

### Automated Maintenance

Set up automated repository maintenance:

```bash
#!/bin/bash
# Weekly repository maintenance

# Clean up old caches (keep 7 days)
sai repository cleanup --keep-days 7

# Update repository
sai repository update

# Verify health
sai repository status --detailed
```

### Monitoring Alerts

Monitor for common issues:

1. **Repository Update Failures**: Check if updates are failing consistently
2. **Cache Growth**: Monitor cache directory size
3. **Authentication Expiry**: Monitor for authentication failures
4. **Network Issues**: Track network-related failures

## Getting Additional Help

### Information to Collect

When reporting repository issues, include:

```bash
# System information
uname -a
git --version

# SAI configuration
sai repository configure --show --json

# Repository status
sai repository status --detailed --json

# Network connectivity
ping -c 3 github.com
curl -I https://github.com

# Error logs
tail -50 ~/.sai/logs/sai.log
```

### Support Channels

1. **GitHub Issues**: Report bugs and feature requests
2. **Documentation**: Check latest documentation for updates
3. **Community**: Join community discussions for help
4. **Enterprise Support**: Contact for enterprise support options

### Useful Resources

- [Repository Configuration Guide](./repository-configuration.md)
- [Configuration Guide](./configuration-guide.md)
- [CLI Reference](./cli-reference.md)