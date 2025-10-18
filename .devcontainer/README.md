# SAI Development Container

This devcontainer provides a complete development environment for the SAI Software Management Suite.

## Features

- **Python 3.11** with all development dependencies
- **Pre-configured tools**: pytest, black, flake8, isort, mypy, pre-commit
- **VS Code extensions**: Python, Pylance, formatters, linters, Git tools
- **Oh My Zsh** for enhanced terminal experience
- **Docker-in-Docker** support for testing containerized workflows
- **GitHub CLI** for repository management
- **Persistent cache** volume for SAI data

## Getting Started

1. **Open in VS Code**: Click "Reopen in Container" when prompted, or use Command Palette → "Dev Containers: Reopen in Container"

2. **Wait for setup**: The post-create script will automatically:
   - Install SAI packages in editable mode
   - Set up pre-commit hooks
   - Create SAI configuration directories
   - Run initial tests

3. **Start developing**: All tools are ready to use!

## Available Commands

### SAI Tools
```bash
sai --help       # SAI CLI tool
saigen --help    # SAIGEN CLI tool
```

### Development Tools
```bash
pytest                          # Run all tests
pytest tests/sai/              # Run SAI tests only
pytest tests/saigen/           # Run SAIGEN tests only
pytest -v --cov                # Run tests with coverage

black .                        # Format code
isort .                        # Sort imports
flake8 .                       # Lint code
mypy sai saigen                # Type checking

pre-commit run --all-files     # Run all pre-commit hooks
```

### Package Management
```bash
pip install -e ".[dev]"        # Reinstall in editable mode
pip list                       # List installed packages
```

## Configuration

### SAI Configuration
Default configuration is created at `~/.sai/config.yaml` with workspace paths pre-configured.

### VS Code Settings
- Auto-formatting on save with Black
- Import sorting with isort
- Pytest integration
- Flake8 linting
- Type checking with Pylance

## Customization

### Add VS Code Extensions
Edit `.devcontainer/devcontainer.json` and add extension IDs to the `extensions` array.

### Install Additional Tools
Edit `.devcontainer/Dockerfile` to add system packages or `.devcontainer/post-create.sh` for Python packages.

### Modify Python Version
Change the base image in `.devcontainer/Dockerfile` (e.g., `python:3.12-slim`).

## Troubleshooting

### Container won't start
- Check Docker is running
- Ensure you have enough disk space
- Try rebuilding: Command Palette → "Dev Containers: Rebuild Container"

### Tests failing
- Ensure all dependencies are installed: `pip install -e ".[dev]"`
- Check if saidata repository is accessible
- Review test output for specific errors

### Pre-commit hooks failing
- Reinstall hooks: `pre-commit install`
- Update hooks: `pre-commit autoupdate`
- Run manually: `pre-commit run --all-files`

## Volumes

- **sai-cache**: Persistent volume for SAI cache data (survives container rebuilds)
- **.git**: Mounted from host for Git operations

## User

The container runs as user `sai` (non-root) with sudo access for security and compatibility.
