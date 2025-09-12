#!/bin/bash
# SAI Installation Script
# This script installs the SAI Software Management Suite

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_MIN_VERSION="3.8"
PACKAGE_NAME="sai"
VENV_DIR="$HOME/.sai/venv"
CONFIG_DIR="$HOME/.sai"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_python() {
    log_info "Checking Python version..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    required_version=$(echo -e "$python_version\n$PYTHON_MIN_VERSION" | sort -V | head -n1)
    
    if [ "$required_version" != "$PYTHON_MIN_VERSION" ]; then
        log_error "Python $PYTHON_MIN_VERSION or higher is required. Found: $python_version"
        exit 1
    fi
    
    log_success "Python $python_version found"
}

check_pip() {
    log_info "Checking pip..."
    
    if ! python3 -m pip --version &> /dev/null; then
        log_error "pip is not available. Please install pip."
        exit 1
    fi
    
    log_success "pip is available"
}

create_venv() {
    log_info "Creating virtual environment at $VENV_DIR..."
    
    # Create config directory
    mkdir -p "$CONFIG_DIR"
    
    # Remove existing venv if it exists
    if [ -d "$VENV_DIR" ]; then
        log_warning "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    fi
    
    # Create new virtual environment
    python3 -m venv "$VENV_DIR"
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    log_success "Virtual environment created"
}

install_sai() {
    log_info "Installing SAI Software Management Suite..."
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Install SAI with all optional dependencies
    pip install "$PACKAGE_NAME[all]"
    
    log_success "SAI installed successfully"
}

create_symlinks() {
    log_info "Creating command symlinks..."
    
    # Create local bin directory
    mkdir -p "$HOME/.local/bin"
    
    # Create symlinks
    ln -sf "$VENV_DIR/bin/sai" "$HOME/.local/bin/sai"
    ln -sf "$VENV_DIR/bin/saigen" "$HOME/.local/bin/saigen"
    
    log_success "Command symlinks created in $HOME/.local/bin"
}

setup_shell_completion() {
    log_info "Setting up shell completion..."
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Install shell completion
    if command -v sai &> /dev/null; then
        sai completion install 2>/dev/null || log_warning "Could not install shell completion automatically"
    fi
    
    log_info "Shell completion setup attempted"
}

create_config() {
    log_info "Creating default configuration..."
    
    config_file="$CONFIG_DIR/config.yaml"
    
    if [ ! -f "$config_file" ]; then
        cat > "$config_file" << 'EOF'
config_version: "0.1.0"
log_level: info

# Saidata search paths (repository cache has highest priority)
saidata_paths:
  - "~/.sai/cache/repositories/saidata-main"
  - "~/.sai/saidata"
  - "/usr/local/share/sai/saidata"

provider_paths:
  - "providers"
  - "~/.sai/providers"
  - "/usr/local/share/sai/providers"

# Provider priorities (lower number = higher priority)
provider_priorities:
  apt: 1
  brew: 2
  winget: 3

# Execution settings
max_concurrent_actions: 3
action_timeout: 300
require_confirmation: true
dry_run_default: false
EOF
        log_success "Default configuration created at $config_file"
    else
        log_info "Configuration file already exists at $config_file"
    fi
}

print_usage() {
    log_success "SAI Software Management Suite installed successfully!"
    echo
    echo "To use SAI commands, make sure $HOME/.local/bin is in your PATH:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
    echo "Add this line to your shell profile (~/.bashrc, ~/.zshrc, etc.) to make it permanent."
    echo
    echo "Available commands:"
    echo "  sai --help      # Show SAI CLI help"
    echo "  saigen --help   # Show SAIGEN CLI help"
    echo
    echo "Example usage:"
    echo "  sai install nginx"
    echo "  sai providers list"
    echo "  saigen generate nginx"
    echo
    echo "Configuration file: $CONFIG_DIR/config.yaml"
    echo "Virtual environment: $VENV_DIR"
}

# Main installation process
main() {
    echo "SAI Software Management Suite Installer"
    echo "======================================="
    echo
    
    check_python
    check_pip
    create_venv
    install_sai
    create_symlinks
    setup_shell_completion
    create_config
    print_usage
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "SAI Installation Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --uninstall    Uninstall SAI"
        echo
        exit 0
        ;;
    --uninstall)
        log_info "Uninstalling SAI..."
        rm -rf "$VENV_DIR"
        rm -f "$HOME/.local/bin/sai"
        rm -f "$HOME/.local/bin/saigen"
        log_success "SAI uninstalled successfully"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac