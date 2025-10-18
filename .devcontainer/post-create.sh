#!/bin/bash
set -e

echo "🚀 Setting up SAI development environment..."

# Install the package in editable mode with all dependencies
echo "📦 Installing SAI packages in editable mode..."
pip install -e ".[dev]"

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Create SAI directories
echo "📁 Creating SAI directories..."
mkdir -p ~/.sai/{saidata,providers,cache}

# Create default configuration
echo "⚙️  Creating default SAI configuration..."
cat > ~/.sai/config.yaml << 'EOF'
config_version: "0.1.0"
log_level: info

saidata_paths:
  - "/workspace/saidata"
  - "~/.sai/saidata"

provider_paths:
  - "/workspace/providers"
  - "~/.sai/providers"

provider_priorities:
  apt: 1
  dnf: 2
  apk: 3

max_concurrent_actions: 3
action_timeout: 300
require_confirmation: false
dry_run_default: false
EOF

# Run tests to verify setup
echo "🧪 Running tests to verify setup..."
pytest tests/ -v --tb=short || echo "⚠️  Some tests failed, but setup is complete"

echo "✅ Development environment setup complete!"
echo ""
echo "Available commands:"
echo "  sai --help       - SAI CLI tool"
echo "  saigen --help    - SAIGEN CLI tool"
echo "  pytest           - Run tests"
echo "  black .          - Format code"
echo "  flake8 .         - Lint code"
echo "  pre-commit run --all-files - Run all pre-commit hooks"
echo ""
echo "Happy coding! 🎉"
