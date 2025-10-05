#!/bin/bash
# Local testing script for saidata files

set -e

echo "🧪 Testing saidata files locally"
echo ""

# Check if saigen is installed
if ! command -v saigen &> /dev/null; then
    echo "❌ saigen not found. Please install it first:"
    echo "   pip install saigen"
    exit 1
fi

# Test example file
echo "Testing nginx-example.yaml..."
saigen test-system nginx-example.yaml

echo ""
echo "✅ Local tests complete!"
