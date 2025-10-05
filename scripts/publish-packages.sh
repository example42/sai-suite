#!/bin/bash
# Publish packages to PyPI
# Usage: ./scripts/publish-packages.sh [test|prod] [sai|saigen|both]

set -e

ENVIRONMENT=${1:-test}
PACKAGE=${2:-both}

if [[ $ENVIRONMENT == "test" ]]; then
    REPO="testpypi"
    REPO_URL="https://test.pypi.org/simple/"
    echo "📤 Publishing to TestPyPI..."
elif [[ $ENVIRONMENT == "prod" ]]; then
    REPO="pypi"
    REPO_URL="https://pypi.org/simple/"
    echo "📤 Publishing to PyPI..."
    echo "⚠️  WARNING: This will publish to production PyPI!"
    read -p "Are you sure? (yes/NO) " -r
    if [[ ! $REPLY == "yes" ]]; then
        echo "Aborted."
        exit 1
    fi
else
    echo "❌ Invalid environment: $ENVIRONMENT"
    echo "Usage: $0 [test|prod] [sai|saigen|both]"
    exit 1
fi

# Check if twine is installed
if ! command -v twine &> /dev/null; then
    echo "❌ twine is not installed. Install it with: pip install twine"
    exit 1
fi

# Check if distributions exist
if [[ ! -d "dist" ]] || [[ -z "$(ls -A dist)" ]]; then
    echo "❌ No distributions found in dist/"
    echo "Run ./scripts/build-packages.sh first"
    exit 1
fi

echo ""

case $PACKAGE in
    sai)
        echo "📦 Publishing SAI package..."
        twine upload --repository $REPO dist/sai-*.whl dist/sai-*.tar.gz
        ;;
    saigen)
        echo "📦 Publishing SAIGEN package..."
        twine upload --repository $REPO dist/saigen-*.whl dist/saigen-*.tar.gz
        ;;
    both)
        echo "📦 Publishing both packages..."
        twine upload --repository $REPO dist/sai-*.whl dist/sai-*.tar.gz
        twine upload --repository $REPO dist/saigen-*.whl dist/saigen-*.tar.gz
        ;;
    *)
        echo "❌ Invalid package: $PACKAGE"
        echo "Usage: $0 [test|prod] [sai|saigen|both]"
        exit 1
        ;;
esac

echo ""
echo "✅ Publishing complete!"
echo ""
echo "Install from $ENVIRONMENT:"
if [[ $PACKAGE == "sai" || $PACKAGE == "both" ]]; then
    echo "  pip install --index-url $REPO_URL sai"
fi
if [[ $PACKAGE == "saigen" || $PACKAGE == "both" ]]; then
    echo "  pip install --index-url $REPO_URL saigen"
fi
