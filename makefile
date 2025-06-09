.PHONY: sync clean test docs

# Virtual environment directory
VENV_DIR := .venv
PYTHON_VERSION := 3.12
PROJECT_SRC_DIR := codantix

# Install uv if not already installed
install-uv:
	@if ! command -v uv &> /dev/null; then \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi

# Create virtual environment and install dependencies
install: install-uv
	uv init --python $(PYTHON_VERSION)
	uv venv --python $(PYTHON_VERSION)

# Sync dependencies
sync: install-uv
	uv sync

# Run tests with coverage reporting
test:
	uv run pytest --cov=. --cov-report=html --cov-report=term-missing --cov-report=xml --junitxml=report.xml --cov-branch -vvv

# Build documentation
docs:
	sphinx-apidoc -f -o ./docs/source ./$(PROJECT_SRC_DIR) && sphinx-build -b html docs/source docs/build

show-docs: docs
	python -m http.server 8000 --directory docs/build

# Build package for local installation
build: clean
	uv build

local-run:
	uvicorn finzup_api.main:app --reload --host 0.0.0.0 --port 8000

# Clean up build artifacts, docs and tests
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf docs/build/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Show help
help:
	@echo "Available commands:"
	@echo "  make install     - Install uv and create virtual environment with dependencies"
	@echo "  make sync       - Sync dependencies"
	@echo "  make test       - Run tests with coverage reporting"
	@echo "  make docs       - Build documentation"
	@echo "  make show-docs  - Show documentation in browser (localhost:8000)"
	@echo "  make clean      - Clean up build artifacts and virtual environment"
	@echo "  make build      - Build the package for local installation"
	@echo "  make local-run  - Run the API locally"
	@echo "  make help       - Show this help message" 