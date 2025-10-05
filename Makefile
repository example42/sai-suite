.PHONY: help install install-sai install-saigen install-both build build-sai build-saigen clean test test-sai test-saigen lint format publish-test publish-prod

help:
	@echo "SAI Monorepo - Available Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install-sai      Install SAI in editable mode"
	@echo "  make install-saigen   Install SAIGEN in editable mode"
	@echo "  make install-both     Install both packages in editable mode"
	@echo ""
	@echo "Building:"
	@echo "  make build            Build both packages"
	@echo "  make build-sai        Build SAI package only"
	@echo "  make build-saigen     Build SAIGEN package only"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-sai         Run SAI tests only"
	@echo "  make test-saigen      Run SAIGEN tests only"
	@echo "  make coverage         Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linters (flake8, mypy)"
	@echo "  make format           Format code (black, isort)"
	@echo "  make format-check     Check code formatting"
	@echo ""
	@echo "Publishing:"
	@echo "  make publish-test     Publish to TestPyPI"
	@echo "  make publish-prod     Publish to PyPI (production)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove build artifacts"
	@echo "  make clean-all        Remove all generated files"

# Installation targets
install-sai:
	pip install -e ./sai[dev]

install-saigen:
	pip install -e ./saigen[dev]

install-both: install-sai install-saigen

install: install-both

# Build targets
build-sai:
	cd sai && python -m build

build-saigen:
	cd saigen && python -m build

build: clean
	./scripts/build-packages.sh

# Test targets
test:
	pytest

test-sai:
	pytest tests/sai/

test-saigen:
	pytest tests/saigen/

coverage:
	pytest --cov=sai --cov=saigen --cov-report=html --cov-report=term

# Code quality targets
lint:
	flake8 sai saigen tests
	mypy sai saigen

format:
	black sai saigen tests
	isort sai saigen tests

format-check:
	black --check sai saigen tests
	isort --check-only sai saigen tests

# Publishing targets
publish-test:
	./scripts/publish-packages.sh test both

publish-test-sai:
	./scripts/publish-packages.sh test sai

publish-test-saigen:
	./scripts/publish-packages.sh test saigen

publish-prod:
	./scripts/publish-packages.sh prod both

publish-prod-sai:
	./scripts/publish-packages.sh prod sai

publish-prod-saigen:
	./scripts/publish-packages.sh prod saigen

# Cleanup targets
clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf sai/build/ sai/dist/ sai/*.egg-info
	rm -rf saigen/build/ saigen/dist/ saigen/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

clean-all: clean
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov/
	rm -rf .tox/
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
