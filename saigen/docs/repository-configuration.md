# Repository Configuration and Authentication Guide

## Overview

SAI uses a configurable git repository system to fetch software definitions (saidata) automatically. This guide covers repository configuration, authentication methods, and troubleshooting for the repository-based saidata system.

## Default Repository

SAI uses the following default repository configuration:
- **Repository URL**: `https://github.com/example42/saidata`
- **Branch**: `main`
- **Structure**: Hierarchical (`software/{first_two_letters}/{software_name}/default.yaml`)
- **Cache Location**: `~/.sai/cache/repositories/`

## Repository Configuration

### Configuration File Settings

Add repository settings to your SAI configuration file (`~/.sai/config.yaml`):

```yaml
# Repository Configuration
saidata_repository_url: "https://github.com/example42/saidata"
saidata_repository_branch: "main"
saidata_repository_auth: null  # Authentication configuration (see below)
saidata_auto_update: true
saidata_update_interval: 86400  # 24 hours in seconds
saidata_offline_mode: false
saidata_repository_cache_dir: null  # Defaults to ~/.sai/cache/repositories/
saidata_repository_timeout: 300  # 5 minutes
saidata_shallow_clone: true  # Use shallow clones for performance
```

### Command Line Configuration

Use the `sai repository configure` command to manage settings:

```bash
# Show current configuration
sai repository configure --show

# Set repository URL
sai repository configure --url https://github.com/myorg/custom-saidata

# Set repository branch
sai repository configure --branch develop

# Enable/disable auto-update
sai repository configure --auto-update
sai repository configure --no-auto-update

# Set update interval (in seconds)
sai repository configure --update-interval 43200  # 12 hours

# Enable offline mode
sai repository configure --offline-mode
```

### Environment Variable Overrides

Override repository settings using environment variables:

```bash
export SAI_REPOSITORY_URL="https://github.com/myorg/custom-saidata"
export SAI_REPOSITORY_BRANCH="develop"
export SAI_OFFLINE_MODE="true"
export SAI_AUTO_UPDATE="false"
```

## Authentication Methods

### SSH Key Authentication

For private repositories using SSH keys:

1. **Generate SSH Key** (if not already done):
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. **Add SSH Key to SSH Agent**:
   ```bash
   ssh-add ~/.ssh/id_ed25519
   ```

3. **Configure Repository with SSH URL**:
   ```bash
   sai repository configure --url git@github.com:myorg/private-saidata.git
   ```

4. **Test SSH Connection**:
   ```bash
   ssh -T git@github.com
   ```

### Personal Access Token (HTTPS)

For private repositories using personal access tokens:

1. **Create Personal Access Token**:
   - GitHub: Settings → Developer settings → Personal access tokens
   - GitLab: User Settings → Access Tokens
   - Required permissions: `repo` (full repository access)

2. **Configure Authentication in SAI Config**:
   ```yaml
   saidata_repository_auth:
     type: "token"
     token: "${GITHUB_TOKEN}"  # Use environment variable
   ```

3. **Set Environment Variable**:
   ```bash
   export GITHUB_TOKEN="ghp_your_token_here"
   ```

4. **Alternative: URL with Token**:
   ```bash
   sai repository configure --url https://token:${GITHUB_TOKEN}@github.com/myorg/private-saidata.git
   ```

### Username/Password Authentication

For repositories requiring username/password:

```yaml
saidata_repository_auth:
  type: "basic"
  username: "${REPO_USERNAME}"
  password: "${REPO_PASSWORD}"
```

```bash
export REPO_USERNAME="your_username"
export REPO_PASSWORD="your_password"
```

### Git Credential Helper

Use git's credential helper for automatic authentication:

```bash
# Store credentials in git credential helper
git config --global credential.helper store

# Or use system keychain (macOS)
git config --global credential.helper osxkeychain

# Or use Windows Credential Manager
git config --global credential.helper manager-core
```

## Repository Operations

### Manual Repository Management

```bash
# Check repository status
sai repository status

# Get detailed repository information
sai repository status --detailed

# Update repository (respects cache TTL)
sai repository update

# Force repository update (ignores cache TTL)
sai repository update --force

# Clear repository cache
sai repository clear

# Clear all repository caches
sai repository clear --all

# Clean up old repository caches
sai repository cleanup --keep-days 7
```

### Automatic Repository Updates

SAI automatically updates the repository when:
- Cache is older than `saidata_update_interval` (default: 24 hours)
- Repository has never been cached
- `--no-cache` flag is used with commands
- `saidata_auto_update` is enabled (default: true)

### Offline Mode

Enable offline mode to use only cached repository data:

```bash
# Enable offline mode for single command
sai --offline install nginx

# Configure persistent offline mode
sai repository configure --offline-mode

# Environment variable
export SAI_OFFLINE_MODE=true
```

## Hierarchical Saidata Structure

### Directory Structure

The repository uses a hierarchical structure for better organization:

```
software/
├── ap/
│   ├── apache/
│   │   └── default.yaml
│   └── apt/
│       └── default.yaml
├── ng/
│   └── nginx/
│       └── default.yaml
├── do/
│   └── docker/
│       └── default.yaml
└── my/
    └── mysql/
        └── default.yaml
```

### Path Resolution

SAI resolves saidata paths as follows:

1. **Primary Path**: `software/{first_two_letters}/{software_name}/default.yaml`
   - Example: `nginx` → `software/ng/nginx/default.yaml`
   - Example: `apache` → `software/ap/apache/default.yaml`

2. **Custom Paths**: User-configured saidata paths (highest precedence)
3. **Repository Cache**: Cached repository data
4. **Error**: Clear error message if saidata not found

### Multiple Saidata Files

When multiple saidata files exist for the same software:

1. **Custom paths** take highest precedence
2. **Repository data** is used as fallback
3. **Files are merged** according to precedence rules
4. **Conflicts** are resolved with higher precedence winning

## Troubleshooting

### Common Issues

#### Repository Not Accessible

**Symptoms**:
- "Repository not found" errors
- Authentication failures
- Network timeouts

**Solutions**:
```bash
# Check repository URL and credentials
sai repository configure --show

# Test network connectivity
ping github.com

# Test git access directly
git ls-remote https://github.com/example42/saidata

# Check authentication
ssh -T git@github.com  # For SSH
```

#### Git Not Available

**Symptoms**:
- "git command not found" errors
- Automatic fallback to tarball downloads

**Solutions**:
```bash
# Install git
# Ubuntu/Debian
sudo apt install git

# macOS
brew install git

# Windows
winget install Git.Git

# Verify installation
git --version
```

#### Cache Issues

**Symptoms**:
- Stale saidata being used
- "Cache corrupted" errors
- Disk space issues

**Solutions**:
```bash
# Clear repository cache
sai repository clear

# Force repository update
sai repository update --force

# Clean up old caches
sai repository cleanup --keep-days 3

# Check cache status
sai repository status --detailed
```

#### Authentication Problems

**Symptoms**:
- "Authentication failed" errors
- "Permission denied" errors
- Token/credential issues

**Solutions**:
```bash
# For SSH keys
ssh-add -l  # List loaded keys
ssh-add ~/.ssh/id_ed25519  # Add key to agent

# For tokens
echo $GITHUB_TOKEN  # Verify token is set
# Regenerate token if expired

# For credential helper
git config --global --list | grep credential
```

#### Offline Mode Issues

**Symptoms**:
- "No cached repository" errors
- Network requests in offline mode
- Stale data warnings

**Solutions**:
```bash
# Ensure repository is cached first
sai repository update
sai repository configure --offline-mode

# Check cache status
sai repository status

# Verify offline mode is enabled
sai repository configure --show
```

### Network Connectivity

#### Proxy Configuration

For environments behind corporate proxies:

```bash
# Configure git proxy
git config --global http.proxy http://proxy.company.com:8080
git config --global https.proxy https://proxy.company.com:8080

# Or use environment variables
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=https://proxy.company.com:8080
```

#### Firewall Issues

Ensure the following ports are accessible:
- **HTTPS (443)**: For HTTPS git operations and tarball downloads
- **SSH (22)**: For SSH git operations
- **HTTP (80)**: For HTTP git operations (not recommended)

### Performance Optimization

#### Repository Size

For large repositories:

```yaml
# Enable shallow clones (default)
saidata_shallow_clone: true

# Reduce timeout for faster failures
saidata_repository_timeout: 120

# Increase update interval to reduce network usage
saidata_update_interval: 172800  # 48 hours
```

#### Cache Management

```bash
# Monitor cache size
sai repository status --detailed

# Regular cleanup
sai repository cleanup --keep-days 7

# Clear unused caches
sai repository clear --all
```

## Security Considerations

### Authentication Security

1. **Use SSH Keys**: Preferred over passwords for better security
2. **Token Permissions**: Use minimal required permissions for tokens
3. **Environment Variables**: Store credentials in environment variables, not config files
4. **Credential Rotation**: Regularly rotate tokens and SSH keys

### Repository Validation

1. **Signature Verification**: Git signatures are verified when available
2. **Checksum Validation**: Tarball checksums are verified when provided
3. **URL Validation**: Repository URLs are validated for security
4. **Path Traversal Protection**: Repository extraction is protected against path traversal

### Local Security

1. **Cache Permissions**: Repository cache uses secure file permissions
2. **Temporary Files**: Temporary download files are handled securely
3. **Configuration Security**: Configuration files should have restricted permissions (600)

## Advanced Configuration

### Custom Repository Structure

For organizations with custom saidata structures:

```yaml
# Custom saidata paths (searched in order)
saidata_paths:
  - "./custom-saidata"           # Local override
  - "~/.sai/saidata"            # User saidata
  - "~/.sai/cache/repositories/" # Repository cache
```

### Multiple Repositories

While SAI currently supports one primary repository, you can use custom paths to include multiple sources:

```yaml
saidata_paths:
  - "./local-saidata"                    # Highest precedence
  - "~/.sai/cache/repositories/main/"    # Primary repository
  - "~/.sai/cache/repositories/custom/"  # Custom repository
```

### Repository Mirroring

For high availability, consider setting up repository mirrors:

```bash
# Primary repository
sai repository configure --url https://github.com/example42/saidata

# If primary fails, manually switch to mirror
sai repository configure --url https://gitlab.com/example42/saidata-mirror
```

## Best Practices

### Development Workflow

1. **Fork Repository**: Create organization fork for customizations
2. **Branch Strategy**: Use feature branches for saidata updates
3. **Testing**: Test saidata changes before merging to main
4. **Documentation**: Document custom saidata and provider mappings

### Production Deployment

1. **Private Repository**: Use private repository for organization-specific saidata
2. **Authentication**: Use SSH keys or tokens with minimal permissions
3. **Monitoring**: Monitor repository update success and cache health
4. **Backup**: Maintain backup of critical saidata files

### Performance

1. **Shallow Clones**: Keep shallow clones enabled for performance
2. **Cache Management**: Regular cache cleanup and monitoring
3. **Update Intervals**: Balance freshness with network usage
4. **Offline Capability**: Ensure offline mode works for critical environments

## Migration Guide

### From Local Saidata to Repository

1. **Backup Local Files**:
   ```bash
   cp -r ~/.sai/saidata ~/.sai/saidata.backup
   ```

2. **Configure Repository**:
   ```bash
   sai repository configure --url https://github.com/example42/saidata
   ```

3. **Test Repository Access**:
   ```bash
   sai repository update
   sai repository status
   ```

4. **Verify Saidata Loading**:
   ```bash
   sai info nginx  # Should use repository data
   ```

5. **Remove Local Files** (optional):
   ```bash
   rm -rf ~/.sai/saidata
   ```

### From Flat to Hierarchical Structure

The migration is automatic - SAI will:
1. Search hierarchical structure first
2. Fall back to flat structure if needed
3. Provide clear error messages for missing files

## Support and Resources

### Getting Help

1. **Status Commands**: Use `sai repository status --detailed` for diagnostics
2. **Verbose Mode**: Use `--verbose` flag for detailed error information
3. **Log Files**: Check SAI log files for detailed operation logs
4. **GitHub Issues**: Report issues with repository operations

### Useful Commands

```bash
# Complete repository health check
sai repository status --detailed --json

# Force complete repository refresh
sai repository clear && sai repository update --force

# Test repository access without SAI
git ls-remote https://github.com/example42/saidata

# Monitor repository operations
sai --verbose repository update
```