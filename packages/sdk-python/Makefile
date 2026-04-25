.PHONY: test typecheck lint build clean install-dev integration

PYTHON := python3
VENV := .venv

test:
	$(PYTHON) -m pytest tests/test_sdk.py tests/test_sync.py -v

integration:
	$(PYTHON) -m pytest tests/integration/ -v

typecheck:
	$(PYTHON) -m mypy citadel_governance tests --ignore-missing-imports

lint:
	$(PYTHON) -m ruff check citadel_governance tests
	$(PYTHON) -m ruff format --check citadel_governance tests

fmt:
	$(PYTHON) -m ruff format citadel_governance tests

build:
	$(PYTHON) -m build

clean:
	rm -rf dist/ *.egg-info .pytest_cache .mypy_cache __pycache__

install-dev:
	pip install -e ".[dev]"

all: typecheck test lint
