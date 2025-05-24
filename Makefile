.PHONY: lint format isort typecheck test all

# Set PYTHONPATH for all commands
export PYTHONPATH := $(shell pwd):$(shell pwd)/src

lint:
	uv run flake8 src

format:
	uv run black src

isort:
	uv run python -m isort src

typecheck:
	uv run mypy src --ignore-missing-imports

test:
	uv run pytest $(ARGS)

# Run all tools
all: lint format isort typecheck test 