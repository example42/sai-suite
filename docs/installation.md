# Installation Guide

This guide covers various methods to install the SAI Software Management Suite.

## Quick Installation

### PyPI (Recommended)

Install the latest stable version from PyPI:

```bash
pip install sai
```

This installs both `sai` and `saigen` commands with core dependencies.

### With Optional Dependencies

Install with all optional dependencies for full functionality:

```bash
pip install "sai[all]"
```

Or install specific feature sets:

```bash
# For AI generation features
pip install "sai[llm,rag]"

# For development
pip install "sai[dev]"

# For testing only
pip install "sai[test]"
```

## Installation Methods

### 1. Automated Installation Script

#### Linux/macOS

Download and run the installation script:

```bash
curl -fsSL https://raw.githubusercontent.com/example42/sai/main/scripts/install.sh | bash
```

Or download and inspect first:

```bash
curl -fsSL https://raw.githubusercontent.com/example42/sai/main/scripts/install.sh -o install.sh
chmod +x install.sh
./install.sh
```

#### Windows (PowerShell)

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/example42/sai/main/scripts/install.ps1" -OutFile "install.ps1"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install.ps1
```

The installation script will:
- Check Python version (3.8+ required)
- Create a virtual environment in `~/.sai/venv`
- Install SAI with all dependencies
- Create command symlinks in `~/.local/bin`
- Set up shell completion
- Create default configuration

### 2. Manual Installation

#### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

#### Step-by-step Installation

1. **Create a virtual environment (recommended):**

```bash
python -m venv sai-env
source sai-env/bin/activate  # On Windows: sai-env\Scripts\activate
```

2. **Install SAI:**

```bash
pip install sai[all]
```

3. **Verify installation:**

```bash
sai --version
saigen --version
```

### 3. Development Installation

For contributing to SAI or using the latest development version:

```bash
# Clone the repository
git clone https://github.com/example42/sai.git
cd sai

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install in development mode
pip install -e ".[dev,llm,rag]"

# Install pre-commit hooks (optional)
pre-commit install
```

### 4. Docker Installation

#### Using Pre-built Image

```bash
# Pull the latest image
docker pull ghcr.io/example42/sai:latest

# Run SAI
docker run --rm -it ghcr.io/example42/sai:latest sai --help

# Run SAIGEN
docker run --rm -it ghcr.io/example42/sai:latest saigen --help
```

#### Building from Source

```bash
# Clone repository
git clone https://github.com/example42/sai.git
cd sai

# Build image
docker build -t sai:local .

# Run container
docker run --rm -it sai:local sai --help
```

#### Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  sai:
    image: ghcr.io/example42/sai:latest
    volumes:
      - ./saidata:/home/sai/.sai/saidata
      - ./config.yaml:/home/sai/.sai/config.yaml
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

Run with:

```bash
docker-compose run --rm sai sai install nginx
```

### 5. Package Manager Installation

#### Homebrew (macOS/Linux)

```bash
# Add tap (if not already added)
brew tap example42/sai

# Install SAI
brew install sai
```

#### Chocolatey (Windows)

```powershell
# Install SAI
choco install sai
```

#### Scoop (Windows)

```powershell
# Add bucket
scoop bucket add sai https://github.com/example42/scoop-sai

# Install SAI
scoop install sai
```

## Post-Installation Setup

### 1. Shell Completion

Enable shell completion for better CLI experience:

```bash
# Install completion for current shell
sai completion install

# Or manually add to your shell profile
echo 'eval "$(_SAI_COMPLETE=bash_source sai)"' >> ~/.bashrc  # Bash
echo 'eval "$(_SAI_COMPLETE=zsh_source sai)"' >> ~/.zshrc    # Zsh
```

### 2. Configuration

Create a configuration file at `~/.sai/config.yaml`:

```yaml
config_version: "0.1.0"
log_level: info

# Provider search paths
saidata_paths:
  - "."
  - "~/.sai/saidata"
  - "/usr/local/share/sai/saidata"

provider_paths:
  - "providers"
  - "~/.sai/providers"
  - "/usr/local/share/sai/providers"

# Provider priorities (lower number = higher priority)
provider_priorities:
  apt: 1      # Linux (Debian/Ubuntu)
  brew: 2     # macOS
  winget: 3   # Windows

# Execution settings
max_concurrent_actions: 3
action_timeout: 300
require_confirmation: true
dry_run_default: false
```

### 3. Environment Variables

For SAIGEN AI features, set up API keys:

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# Anthropic
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Add to your shell profile for persistence
echo 'export OPENAI_API_KEY="your-openai-api-key"' >> ~/.bashrc
```

## Verification

Test your installation:

```bash
# Check versions
sai --version
saigen --version

# List available providers
sai providers list

# Show configuration
sai config show

# Test SAIGEN (requires API key)
saigen config --show
```

## Troubleshooting

### Common Issues

#### Python Version Error

```
Error: Python 3.8 or higher is required
```

**Solution:** Install Python 3.8+ from [python.org](https://python.org) or use your system package manager.

#### Permission Denied

```
Permission denied: '/usr/local/bin/sai'
```

**Solution:** Use `--user` flag or virtual environment:

```bash
pip install --user sai
```

#### Command Not Found

```
sai: command not found
```

**Solution:** Add to PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

#### Import Errors

```
ModuleNotFoundError: No module named 'sai'
```

**Solution:** Ensure you're in the correct virtual environment or reinstall:

```bash
pip install --force-reinstall sai
```

### Getting Help

- Check the [troubleshooting guide](troubleshooting.md)
- Open an issue on [GitHub](https://github.com/example42/sai/issues)
- Join our [Discord community](https://discord.gg/sai-software)

## Uninstallation

### PyPI Installation

```bash
pip uninstall sai
```

### Script Installation

```bash
# Linux/macOS
~/.sai/uninstall.sh

# Windows
~/.sai/uninstall.ps1
```

### Manual Cleanup

```bash
# Remove virtual environment
rm -rf ~/.sai/venv

# Remove configuration
rm -rf ~/.sai

# Remove symlinks
rm ~/.local/bin/sai ~/.local/bin/saigen
```

## Next Steps

- Read the [Configuration Guide](configuration-guide.md)
- Check out [Usage Examples](../examples/)
- Explore the [API Reference](api-reference.md)
- Learn about [Provider Development](provider-development.md)