.PHONY: lint format isort typecheck test test-coverage run run-dev all

# Set PYTHONPATH for test and runtime commands only
export PYTHONPATH := $(shell pwd)/src

lint:
	uv run flake8 src

format:
	uv run black src

isort:
	uv run python -m isort src

typecheck:
	PYTHONPATH= uv run mypy src

test:
	uv run pytest $(ARGS)

test-coverage:
	uv run pytest --cov=feptm --cov-report=term-missing --cov-report=html $(ARGS)

# Run server (production)
run:
	uv run python -m bin.run_api

# Run server (development with auto-reload)
run-dev:
	uv run uvicorn feptm.main:app --reload --host 0.0.0.0 --port 8000

# Run all tools
all: lint format isort typecheck test 