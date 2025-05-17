.PHONY: lint format isort typecheck test all

lint:
	uv run flake8

format:
	uv run black src

isort:
	uv run python -m isort src

typecheck:
	uv run mypy src

test:
	uv run pytest $(ARGS)

# Run all tools
all: lint format isort typecheck test 