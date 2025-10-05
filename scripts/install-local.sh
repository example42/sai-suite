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
INSTALL_MODE=${1:-both}

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
    both)
        echo "📦 Installing both SAI and SAIGEN..."
        pip install -e ./sai[dev]
        pip install -e ./saigen[dev]
        echo "✅ Both packages installed in editable mode"
        ;;
    *)
        echo "❌ Invalid argument: $INSTALL_MODE"
        echo "Usage: $0 [sai|saigen|both]"
        exit 1
        ;;
esac

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Verify installation:"
echo "  sai --version"
if [[ $INSTALL_MODE == "saigen" || $INSTALL_MODE == "both" ]]; then
    echo "  saigen --version"
fi
