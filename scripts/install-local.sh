#!/bin/bash
# Install packages locally in editable mode for development

set -e

echo "🔧 Installing SAI packages in development mode..."
echo ""

# Check if virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Consider activating a virtual environment first:"
    echo "   python -m venv venv && source venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Parse arguments
INSTALL_MODE=${1:-all}

case $INSTALL_MODE in
    sai)
        echo "📦 Installing SAI only..."
        pip install -e ./sai[dev]
        echo "✅ SAI installed in editable mode"
        ;;
    saigen)
        echo "📦 Installing SAIGEN only..."
        pip install -e ./saigen[dev]
        echo "✅ SAIGEN installed in editable mode"
        ;;
    saitest)
        echo "📦 Installing SAITEST only..."
        pip install -e ./saitest[dev]
        echo "✅ SAITEST installed in editable mode"
        ;;
    all)
        echo "📦 Installing all packages (SAI, SAIGEN, SAITEST)..."
        pip install -e ./sai[dev]
        pip install -e ./saigen[dev]
        pip install -e ./saitest[dev]
        echo "✅ All packages installed in editable mode"
        ;;
    *)
        echo "❌ Invalid argument: $INSTALL_MODE"
        echo "Usage: $0 [sai|saigen|saitest|all]"
        exit 1
        ;;
esac

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Verify installation:"
if [[ $INSTALL_MODE == "sai" || $INSTALL_MODE == "all" ]]; then
    echo "  sai --version"
fi
if [[ $INSTALL_MODE == "saigen" || $INSTALL_MODE == "all" ]]; then
    echo "  saigen --version"
fi
if [[ $INSTALL_MODE == "saitest" || $INSTALL_MODE == "all" ]]; then
    echo "  saitest --version"
fi
