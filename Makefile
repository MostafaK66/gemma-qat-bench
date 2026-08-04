.PHONY: help install test lint format typecheck build-llama download bench all clean

PYTHON ?= python

help:
	@echo "Targets:"
	@echo "  install     Install the package with dev extras (editable)"
	@echo "  test        Run the offline test suite"
	@echo "  lint        Run ruff checks"
	@echo "  format      Auto-format with ruff"
	@echo "  typecheck   Run mypy"
	@echo "  build-llama Build llama.cpp via the CLI"
	@echo "  download    Download the configured models"
	@echo "  bench       Run the benchmark (requires a built server binary)"
	@echo "  all         Build llama.cpp then run the benchmark"
	@echo "  clean       Remove caches and build artifacts"

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests

format:
	$(PYTHON) -m ruff format src tests
	$(PYTHON) -m ruff check --fix src tests

typecheck:
	$(PYTHON) -m mypy

build-llama:
	$(PYTHON) -m gemma_qat_bench build

download:
	$(PYTHON) -m gemma_qat_bench download

bench:
	$(PYTHON) -m gemma_qat_bench --config configs/tutorial.toml bench

all:
	$(PYTHON) -m gemma_qat_bench --config configs/tutorial.toml all

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
