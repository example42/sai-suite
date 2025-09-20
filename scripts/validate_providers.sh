#!/bin/bash
#
# Provider Data Validation Script (Shell Wrapper)
#
# Simple shell wrapper for the Python validation script.
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Check if Python script exists
if [[ ! -f "scripts/validate_providers.py" ]]; then
    echo "❌ Python validation script not found: scripts/validate_providers.py"
    exit 1
fi

# Check if required Python packages are available
if ! python3 -c "import jsonschema, yaml" 2>/dev/null; then
    echo "❌ Required Python packages not found. Installing..."
    echo "   Installing jsonschema and PyYAML..."
    
    # Try to install with pip
    if command -v pip3 >/dev/null 2>&1; then
        pip3 install jsonschema PyYAML
    elif command -v pip >/dev/null 2>&1; then
        pip install jsonschema PyYAML
    else
        echo "❌ pip not found. Please install jsonschema and PyYAML manually:"
        echo "   pip install jsonschema PyYAML"
        exit 1
    fi
fi

# Run the Python validation script with all arguments
python3 scripts/validate_providers.py "$@"