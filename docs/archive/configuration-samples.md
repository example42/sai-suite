# Configuration Samples

This directory contains comprehensive sample configuration files for both SAI and SAIGEN tools with all available settings and their default values.

## Available Sample Files

### SAIGEN Configuration Samples
- [`saigen-config-sample.yaml`](./saigen-config-sample.yaml) - YAML format (recommended)

### SAI Configuration Samples  
- [`sai-config-sample.yaml`](./sai-config-sample.yaml) - YAML format (recommended) with repository configuration

## Quick Start

### SAIGEN Configuration

1. Copy the sample configuration:
   ```bash
   cp docs/saigen-config-sample.yaml ~/.saigen/config.yaml
   ```

2. Edit the configuration file and add your API keys:
   ```yaml
   llm_providers:
     openai:
       api_key: "your-openai-api-key-here"
   ```

3. Or set environment variables:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"
   ```

### SAI Configuration

1. Copy the sample configuration:
   ```bash
   cp docs/sai-config-sample.yaml ~/.sai/config.yaml
   ```

2. Configure repository settings (optional - defaults work for most users):
   ```yaml
   # Use default repository
   saidata_repository_url: "https://github.com/example42/saidata"
   
   # Or configure custom repository
   saidata_repository_url: "https://github.com/myorg/custom-saidata"
   saidata_repository_branch: "main"
   ```

3. Set up authentication for private repositories (if needed):
   ```bash
   # For SSH authentication
   ssh-add ~/.ssh/id_ed25519
   
   # For token authentication
   export GITHUB_TOKEN="your_token_here"
   ```

4. Customize provider priorities and paths as needed.

## Configuration File Locations

### SAIGEN
Configuration files are searched in the following order:
1. `~/.saigen/config.yaml`
2. `~/.saigen/config.json`
3. `./.saigen.yaml`
4. `./.saigen.json`
5. `./saigen.yaml`
6. `./saigen.json`

### SAI
Configuration files are searched in the following order:
1. `~/.sai/config.yaml`
2. `~/.sai/config.json`
3. `./.sai.yaml`
4. `./.sai.json`
5. `./sai.yaml`
6. `./sai.json`

## Key Configuration Sections

### SAIGEN Configuration Sections

#### LLM Providers
Configure AI providers for metadata generation:
- **OpenAI**: GPT models for high-quality generation
- **Anthropic**: Claude models as alternative
- **Custom providers**: Extend with additional LLM providers

#### Repositories
Configure package repositories for metadata collection:
- **APT**: Debian/Ubuntu repositories
- **Homebrew**: macOS/Linux package manager
- **Winget**: Windows package manager
- **DNF/YUM**: Red Hat/Fedora repositories

#### RAG (Retrieval-Augmented Generation)
Enhance AI generation with example data:
- **Sample directory**: Reference saidata files for examples
- **Embedding model**: Semantic search for relevant examples
- **Context matching**: Similarity thresholds and limits

#### Cache & Performance
Optimize performance and resource usage:
- **Cache settings**: TTL, size limits, cleanup intervals
- **Concurrency**: Parallel requests and rate limiting
- **Timeouts**: Request and operation timeouts

### SAI Configuration Sections

#### Provider Management
Control how providers are selected and prioritized:
- **Provider priorities**: Numeric priorities for provider selection
- **Default provider**: Fallback when no provider specified
- **Search paths**: Directories to find provider implementations

#### Repository Configuration
Configure saidata repository settings:
- **Repository URL**: Git repository containing saidata files
- **Repository branch**: Branch to use from the repository
- **Authentication**: SSH keys, tokens, or credentials for private repositories
- **Update behavior**: Automatic updates, intervals, and offline mode
- **Cache settings**: Local repository caching for performance

#### Data Sources
Configure where to find saidata and providers:
- **Repository cache**: Primary source from configured git repository
- **Saidata paths**: Additional directories containing software metadata
- **Provider paths**: Directories containing provider implementations
- **Hierarchical structure**: `software/{prefix}/{name}/default.yaml` organization

#### Execution Control
Control how actions are executed:
- **Concurrency**: Maximum parallel actions
- **Timeouts**: Action execution timeouts
- **Safety**: Confirmation requirements and dry-run defaults

## Environment Variables

### SAIGEN Environment Variables
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `SAIGEN_LOG_LEVEL`: Override log level
- `SAIGEN_CACHE_DIR`: Override cache directory
- `SAIGEN_OUTPUT_DIR`: Override output directory

### SAI Environment Variables
- `SAI_LOG_LEVEL`: Override log level
- `SAI_CACHE_DIR`: Override cache directory
- `SAI_CONFIG_PATH`: Override config file path
- `SAI_REPOSITORY_URL`: Override repository URL
- `SAI_REPOSITORY_BRANCH`: Override repository branch
- `SAI_OFFLINE_MODE`: Force offline mode (true/false)
- `SAI_AUTO_UPDATE`: Enable/disable auto-update (true/false)
- `GITHUB_TOKEN`: GitHub personal access token for private repositories
- `SSH_AUTH_SOCK`: SSH agent socket for SSH key authentication

## Validation

### SAIGEN Configuration Validation
Use the built-in validation command:
```bash
saigen config validate
```

### SAI Configuration Validation
SAI validates configuration on startup and reports any issues.

## Security Considerations

1. **API Keys**: Store in environment variables or secure config files with restricted permissions
2. **File Permissions**: Configuration files should be readable only by the owner (600)
3. **Cache Security**: Cache directories should have appropriate permissions
4. **Confirmation**: Enable `require_confirmation` for production environments

## Troubleshooting

### Common Issues

1. **Missing API Keys**: Set environment variables or add to config file
2. **Permission Errors**: Check file and directory permissions
3. **Path Issues**: Verify saidata and provider paths exist
4. **Cache Problems**: Clear cache directory if corrupted

### Debug Mode
Enable debug logging for troubleshooting:
```yaml
log_level: "debug"
```

### Configuration Commands

#### SAIGEN
```bash
# Show current configuration
saigen config show

# Set configuration values
saigen config set llm_providers.openai.model gpt-4

# Initialize new configuration
saigen config init

# Configure sample directory
saigen config samples --auto-detect
```

#### SAI
```bash
# Show current configuration (if implemented)
sai config show

# Validate configuration
sai --dry-run list  # Test configuration
```