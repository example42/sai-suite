#!/bin/bash
# Build script for SAI monorepo packages
# Builds sai, saigen, and saitest packages separately

set -e

echo "🏗️  Building SAI Software Management Suite packages..."
echo ""

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info
rm -rf sai/build/ sai/dist/ sai/*.egg-info
rm -rf saigen/build/ saigen/dist/ saigen/*.egg-info
rm -rf saitest/build/ saitest/dist/ saitest/*.egg-info

# Build SAI package
echo ""
echo "📦 Building SAI package..."
cd sai
python -m build
cd ..
echo "✅ SAI package built successfully"

# Build SAIGEN package
echo ""
echo "📦 Building SAIGEN package..."
cd saigen
python -m build
cd ..
echo "✅ SAIGEN package built successfully"

# Build SAITEST package
echo ""
echo "📦 Building SAITEST package..."
cd saitest
python -m build
cd ..
echo "✅ SAITEST package built successfully"

# Copy distributions to root dist folder for convenience
echo ""
echo "📋 Copying distributions to root dist/ folder..."
mkdir -p dist
cp sai/dist/* dist/
cp saigen/dist/* dist/
cp saitest/dist/* dist/

echo ""
echo "✅ All packages built successfully!"
echo ""
echo "📦 Built packages:"
ls -lh dist/
echo ""
echo "To install locally:"
echo "  pip install dist/sai-*.whl"
echo "  pip install dist/saigen-*.whl"
echo "  pip install dist/saitest-*.whl"
echo ""
echo "To publish to PyPI:"
echo "  twine upload dist/sai-*.whl dist/sai-*.tar.gz"
echo "  twine upload dist/saigen-*.whl dist/saigen-*.tar.gz"
echo "  twine upload dist/saitest-*.whl dist/saitest-*.tar.gz"
