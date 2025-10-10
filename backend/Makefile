.PHONY: help test test-unit test-integration test-e2e test-cov lint format typecheck security quality check install clean run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install development dependencies
	./venv/bin/pip install -r requirements-dev.txt

install-prod: ## Install production dependencies only
	./venv/bin/pip install -r requirements-prod.txt

test: ## Run all tests
	./venv/bin/pytest tests/ -v

test-unit: ## Run unit tests only
	./venv/bin/pytest tests/unit/ -v

test-integration: ## Run integration tests only
	./venv/bin/pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	./venv/bin/pytest tests/e2e/ -v

test-cov: ## Run tests with coverage report
	./venv/bin/pytest tests/ --cov --cov-report=html --cov-report=term

lint: ## Run ruff linter
	./venv/bin/ruff check .

format: ## Format code with ruff
	./venv/bin/ruff format .
	./venv/bin/ruff check --fix .

typecheck: ## Run mypy type checker
	./venv/bin/mypy *.py

security: ## Run bandit security checker
	./venv/bin/bandit -r . -c pyproject.toml

quality: ## Run radon complexity analysis
	./venv/bin/radon cc . -a
	./venv/bin/radon mi .

check: lint typecheck security ## Run all static analysis tools

ci: check test-cov ## Run full CI pipeline (lint, typecheck, security, tests)

clean: ## Clean up generated files
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

run: ## Run the development server
	./venv/bin/python main.py

profile: ## Profile the application with py-spy
	./venv/bin/py-spy record -o profile.svg -- ./venv/bin/python main.py

profile-viz: ## Profile with VizTracer (interactive)
	./venv/bin/python scripts/profile.py viztracer

benchmark: ## Run API benchmarks
	./venv/bin/python scripts/benchmark.py

debug: ## Run with IPython debugger on error
	./venv/bin/python -m ipdb main.py

memory: ## Profile memory usage
	./venv/bin/memray run main.py
	@echo "Generate report with: memray flamegraph memray-*.bin"
