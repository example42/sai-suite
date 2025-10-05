#!/bin/bash
# Docker-based testing script for saidata files

set -e

echo "🧪 Testing saidata files with Docker"
echo ""

# Test on multiple OS
OS_LIST=("ubuntu" "debian" "fedora" "alpine")

for os in "${OS_LIST[@]}"; do
    echo "Testing on $os..."
    docker run --rm -v "$(pwd):/data" \
        "ghcr.io/example42/sai-test-${os}:latest" \
        saigen test-system /data/nginx-example.yaml
    echo ""
done

echo "✅ Docker tests complete!"
