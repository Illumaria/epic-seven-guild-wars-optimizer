# Define variables
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

# Phony targets don't create actual files, they just run commands
.PHONY: all install format test run clean help

# Help target to display available commands
help:
	@echo "Available commands:"
	@echo "  make install         - Install dependencies in a virtual environment"
	@echo "  make format          - Run Python formatter"
	@echo "  make test            - Run tests"
	@echo "  make run             - Run the main application"
	@echo "  make clean           - Remove virtual environment and cache files"
	@echo "  make help            - Display this help message"

all: install test

# Target to create and update the virtual environment
$(VENV): pyproject.toml
	@echo "Creating virtual environment..."
	uv sync

# Target to install dependencies
install: $(VENV)
	@echo "Dependencies installed."

# Target to format Python code
format: $(VENV)
	@echo "Running formatter..."
	uv format

# Target to run tests
test: install
	@echo "Running tests..."
	uv run pytest --doctest-modules --cov=src -vv

# Target to run your application (adjust 'main.py' as needed)
run: install
	@echo "Running application..."
	$(PYTHON) run_optimizer.py

# Target to clean up cache files and the virtual environment
clean:
	@echo "Cleaning up..."
	rm -rf $(VENV)
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
