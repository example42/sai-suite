# SAI Software Management Suite Makefile

.PHONY: help install install-dev test test-cov lint format type-check security clean build publish docker docs pre-commit validate-providers validate-providers-verbose

# Default target
help:
	@echo "SAI Software Management Suite - Development Commands"
	@echo "=================================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  install       Install package in current environment"
	@echo "  install-dev   Install package with development dependencies"
	@echo "  install-all   Install package with all optional dependencies"
	@echo ""
	@echo "Development Commands:"
	@echo "  test          Run test suite"
	@echo "  test-cov      Run tests with coverage report"
	@echo "  lint          Run linting checks"
	@echo "  format        Format code with black and isort"
	@echo "  type-check    Run type checking with mypy"
	@echo "  security      Run security checks"
	@echo "  pre-commit    Run all pre-commit hooks"
	@echo ""
	@echo "Build Commands:"
	@echo "  clean         Clean build artifacts"
	@echo "  build         Build package for distribution"
	@echo "  publish       Publish to PyPI"
	@echo "  publish-test  Publish to Test PyPI"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-run    Run Docker container"
	@echo "  docker-test   Test Docker image"
	@echo ""
	@echo "Documentation:"
	@echo "  docs          Generate documentation"
	@echo "  docs-serve    Serve documentation locally"
	@echo ""
	@echo "Validation Commands:"
	@echo "  validate-providers    Validate provider files against schema"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all]"

# Testing
test:
	pytest

test-cov:
	pytest --cov=sai --cov=saigen --cov-report=html --cov-report=term-missing

test-integration:
	pytest tests/integration/

# Code Quality
lint:
	flake8 sai saigen tests
	black --check --diff sai saigen tests
	isort --check-only --diff sai saigen tests

format:
	black sai saigen tests
	isort sai saigen tests

type-check:
	mypy sai saigen

security:
	bandit -r sai saigen
	safety check

pre-commit:
	pre-commit run --all-files

# Build and Distribution
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

build: clean
	python -m build

publish: build
	twine upload dist/*

publish-test: build
	twine upload --repository testpypi dist/*

# Docker
docker-build:
	docker build -t sai:latest .

docker-run:
	docker run --rm -it sai:latest

docker-test:
	docker run --rm sai:latest sai --version
	docker run --rm sai:latest saigen --version

# Documentation
docs:
	@echo "Documentation generation not yet implemented"

docs-serve:
	@echo "Documentation serving not yet implemented"

# Release Management
release-patch:
	python scripts/release.py patch

release-minor:
	python scripts/release.py minor

release-major:
	python scripts/release.py major

# Development Environment
dev-setup: install-all
	pre-commit install
	@echo "Development environment setup complete!"

# CI/CD Simulation
ci: lint type-check security test

# Cleanup Development Environment
dev-clean:
	pre-commit uninstall
	pip uninstall -y sai
	$(MAKE) clean

# Version Information
version:
	@python -c "from sai.version import get_version; print(f'SAI Version: {get_version()}')"

# Quick Development Cycle
dev: format lint type-check test
	@echo "Development cycle complete!"

# Provider Validation
validate-providers:
	@echo "Validating provider files against schema..."
	./scripts/validate_providers.sh

validate-providers-verbose:
	@echo "Validating provider files against schema (verbose)..."
	./scripts/validate_providers.sh --verbose

# All Quality Checks
quality: lint type-check security test-cov validate-providers
	@echo "All quality checks passed!"