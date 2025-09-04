#!/bin/bash
# SAI Build Script
# This script builds the SAI Software Management Suite for distribution

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"

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

check_dependencies() {
    log_info "Checking build dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required for building"
        exit 1
    fi
    
    # Check build tools
    if ! python3 -c "import build" 2>/dev/null; then
        log_info "Installing build dependencies..."
        pip install build twine
    fi
    
    log_success "Build dependencies available"
}

clean_build() {
    log_info "Cleaning previous builds..."
    
    # Remove build directories
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
    fi
    
    if [ -d "$DIST_DIR" ]; then
        rm -rf "$DIST_DIR"
    fi
    
    # Remove egg-info directories
    find "$PROJECT_ROOT" -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Remove __pycache__ directories
    find "$PROJECT_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    log_success "Build directories cleaned"
}

run_tests() {
    log_info "Running test suite..."
    
    cd "$PROJECT_ROOT"
    
    if command -v pytest &> /dev/null; then
        python3 -m pytest -v
        log_success "All tests passed"
    else
        log_warning "pytest not available, skipping tests"
    fi
}

run_linting() {
    log_info "Running code quality checks..."
    
    cd "$PROJECT_ROOT"
    
    # Run black
    if command -v black &> /dev/null; then
        black --check --diff sai saigen tests || {
            log_error "Code formatting issues found. Run 'black sai saigen tests' to fix."
            exit 1
        }
        log_success "Code formatting check passed"
    else
        log_warning "black not available, skipping formatting check"
    fi
    
    # Run isort
    if command -v isort &> /dev/null; then
        isort --check-only --diff sai saigen tests || {
            log_error "Import sorting issues found. Run 'isort sai saigen tests' to fix."
            exit 1
        }
        log_success "Import sorting check passed"
    else
        log_warning "isort not available, skipping import check"
    fi
    
    # Run flake8
    if command -v flake8 &> /dev/null; then
        flake8 sai saigen tests
        log_success "Linting check passed"
    else
        log_warning "flake8 not available, skipping linting"
    fi
}

build_package() {
    log_info "Building package..."
    
    cd "$PROJECT_ROOT"
    
    # Build source distribution and wheel
    python3 -m build
    
    log_success "Package built successfully"
    
    # List built files
    log_info "Built files:"
    ls -la "$DIST_DIR"
}

validate_package() {
    log_info "Validating package..."
    
    cd "$PROJECT_ROOT"
    
    # Check package with twine
    if command -v twine &> /dev/null; then
        twine check "$DIST_DIR"/*
        log_success "Package validation passed"
    else
        log_warning "twine not available, skipping package validation"
    fi
}

show_package_info() {
    log_info "Package information:"
    
    # Show package metadata
    if [ -f "$DIST_DIR"/*.whl ]; then
        wheel_file=$(ls "$DIST_DIR"/*.whl | head -n1)
        log_info "Wheel file: $(basename "$wheel_file")"
        
        # Extract and show metadata
        python3 -c "
import zipfile
import sys
with zipfile.ZipFile('$wheel_file', 'r') as z:
    metadata_files = [f for f in z.namelist() if f.endswith('METADATA')]
    if metadata_files:
        with z.open(metadata_files[0]) as f:
            content = f.read().decode('utf-8')
            for line in content.split('\n'):
                if line.startswith(('Name:', 'Version:', 'Summary:', 'Author:')):
                    print(f'  {line}')
"
    fi
    
    if [ -f "$DIST_DIR"/*.tar.gz ]; then
        tarball_file=$(ls "$DIST_DIR"/*.tar.gz | head -n1)
        log_info "Source distribution: $(basename "$tarball_file")"
    fi
}

# Main build process
main() {
    echo "SAI Software Management Suite Build Script"
    echo "=========================================="
    echo
    
    check_dependencies
    clean_build
    
    # Run quality checks if not skipped
    if [ "${SKIP_TESTS:-}" != "1" ]; then
        run_tests
    fi
    
    if [ "${SKIP_LINT:-}" != "1" ]; then
        run_linting
    fi
    
    build_package
    validate_package
    show_package_info
    
    log_success "Build completed successfully!"
    echo
    echo "Built packages are available in: $DIST_DIR"
    echo
    echo "To publish to PyPI:"
    echo "  twine upload dist/*"
    echo
    echo "To publish to Test PyPI:"
    echo "  twine upload --repository testpypi dist/*"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "SAI Build Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --help, -h       Show this help message"
        echo "  --clean-only     Only clean build directories"
        echo "  --skip-tests     Skip running tests"
        echo "  --skip-lint      Skip linting checks"
        echo
        echo "Environment variables:"
        echo "  SKIP_TESTS=1     Skip running tests"
        echo "  SKIP_LINT=1      Skip linting checks"
        echo
        exit 0
        ;;
    --clean-only)
        check_dependencies
        clean_build
        log_success "Clean completed"
        exit 0
        ;;
    --skip-tests)
        export SKIP_TESTS=1
        main
        ;;
    --skip-lint)
        export SKIP_LINT=1
        main
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