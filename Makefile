.PHONY: lint format isort typecheck test all

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

# Run all tools
all: lint format isort typecheck test 