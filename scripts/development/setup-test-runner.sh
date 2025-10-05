#!/bin/bash
# Setup script for self-hosted GitHub Actions runner for saidata testing

set -e

echo "🔧 Setting up self-hosted GitHub Actions runner for saidata testing"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
  echo "⚠️  Please don't run this script as root"
  exit 1
fi

# Detect OS
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

echo "Detected OS: $OS"
echo "Detected Architecture: $ARCH"
echo ""

# Install dependencies based on OS
echo "📦 Installing dependencies..."
case "$OS" in
  linux)
    if command -v apt-get &> /dev/null; then
      sudo apt-get update
      sudo apt-get install -y python3 python3-pip curl jq
    elif command -v dnf &> /dev/null; then
      sudo dnf install -y python3 python3-pip curl jq
    elif command -v yum &> /dev/null; then
      sudo yum install -y python3 python3-pip curl jq
    else
      echo "❌ Unsupported package manager"
      exit 1
    fi
    ;;
  darwin)
    if ! command -v brew &> /dev/null; then
      echo "❌ Homebrew not found. Please install it first: https://brew.sh"
      exit 1
    fi
    brew install python3 curl jq
    ;;
  *)
    echo "❌ Unsupported OS: $OS"
    exit 1
    ;;
esac

# Install saigen
echo ""
echo "📦 Installing saigen..."
pip3 install --user saigen

# Verify installation
if ! command -v saigen &> /dev/null; then
  echo "⚠️  saigen not found in PATH. You may need to add ~/.local/bin to your PATH"
  echo "Add this to your ~/.bashrc or ~/.zshrc:"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Download GitHub Actions runner
echo ""
echo "📥 Downloading GitHub Actions runner..."

RUNNER_VERSION="2.311.0"
RUNNER_DIR="$HOME/actions-runner"

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

case "$OS-$ARCH" in
  linux-x86_64)
    RUNNER_FILE="actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
    ;;
  linux-aarch64)
    RUNNER_FILE="actions-runner-linux-arm64-${RUNNER_VERSION}.tar.gz"
    ;;
  darwin-x86_64)
    RUNNER_FILE="actions-runner-osx-x64-${RUNNER_VERSION}.tar.gz"
    ;;
  darwin-arm64)
    RUNNER_FILE="actions-runner-osx-arm64-${RUNNER_VERSION}.tar.gz"
    ;;
  *)
    echo "❌ Unsupported platform: $OS-$ARCH"
    exit 1
    ;;
esac

if [ ! -f "$RUNNER_FILE" ]; then
  curl -o "$RUNNER_FILE" -L "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_FILE}"
  tar xzf "$RUNNER_FILE"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Go to your saidata repository on GitHub"
echo "2. Navigate to Settings > Actions > Runners"
echo "3. Click 'New self-hosted runner'"
echo "4. Follow the instructions to configure the runner"
echo "5. Use these labels: self-hosted, $OS, bare-metal"
echo ""
echo "To configure the runner, run:"
echo "  cd $RUNNER_DIR"
echo "  ./config.sh --url https://github.com/example42/saidata --token YOUR_TOKEN"
echo ""
echo "To start the runner:"
echo "  cd $RUNNER_DIR"
echo "  ./run.sh"
echo ""
echo "To install as a service (Linux):"
echo "  cd $RUNNER_DIR"
echo "  sudo ./svc.sh install"
echo "  sudo ./svc.sh start"
echo ""
