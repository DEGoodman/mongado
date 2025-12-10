.PHONY: help up down restart rebuild logs logs-backend logs-frontend shell-backend shell-frontend
.PHONY: test test-backend test-backend-unit test-backend-cov test-frontend test-e2e test-all
.PHONY: lint lint-backend lint-frontend format format-backend format-frontend typecheck typecheck-backend typecheck-frontend
.PHONY: build-frontend security ci clean
.PHONY: backup backup-force backup-auto restore restore-auto backup-list

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'

##@ Docker Operations

up: ## Start all services in detached mode
	docker compose up -d

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

restart-backend: ## Restart backend service only
	docker compose restart backend

restart-frontend: ## Restart frontend service only
	docker compose restart frontend

rebuild: ## Rebuild and start all services
	docker compose up -d --build

rebuild-backend: ## Rebuild and restart backend only
	docker compose up -d --build backend

rebuild-frontend: ## Rebuild and restart frontend only
	docker compose up -d --build frontend

logs: ## View logs from all services (follow mode)
	docker compose logs -f

logs-backend: ## View backend logs (follow mode)
	docker compose logs -f backend

logs-frontend: ## View frontend logs (follow mode)
	docker compose logs -f frontend

logs-neo4j: ## View Neo4j logs (follow mode)
	docker compose logs -f neo4j

shell-backend: ## Open bash shell in backend container
	docker compose exec backend bash

shell-frontend: ## Open shell in frontend container
	docker compose exec frontend sh

##@ Backend Testing

test-backend: ## Run all backend tests
	docker compose exec backend pytest tests/ -v

test-backend-unit: ## Run backend unit tests only
	docker compose exec backend pytest tests/unit/ -v

test-backend-integration: ## Run backend integration tests only
	docker compose exec backend pytest tests/integration/ -v

test-backend-cov: ## Run backend tests with coverage
	docker compose exec backend pytest tests/ --cov --cov-report=html --cov-report=term

test-backend-watch: ## Run backend tests in watch mode
	docker compose exec backend pytest tests/ --watch

##@ Frontend Testing

test-frontend: ## Run frontend unit tests
	docker compose exec frontend npm test

test-frontend-ui: ## Run frontend tests with UI
	docker compose exec frontend npm run test:ui

test-e2e: ## Run frontend E2E tests
	docker compose exec frontend npm run test:e2e

##@ Combined Testing

test: test-backend test-frontend ## Run all tests (backend + frontend)

test-all: ## Run full test suite with coverage
	docker compose exec backend pytest tests/ --cov --cov-report=html --cov-report=term
	docker compose exec frontend npm run test:all

##@ Backend Code Quality

lint-backend: ## Run backend linter (ruff)
	docker compose exec backend ruff check .

format-backend: ## Format backend code (ruff)
	docker compose exec backend ruff format .
	docker compose exec backend ruff check --fix .

typecheck-backend: ## Run backend type checker (mypy)
	docker compose exec backend mypy .

security: ## Run backend security checks (bandit)
	docker compose exec backend bandit -r . -c pyproject.toml

##@ Frontend Code Quality

lint-frontend: ## Run frontend linter (ESLint)
	docker compose exec frontend npm run lint

lint-frontend-fix: ## Run frontend linter with auto-fix
	docker compose exec frontend npm run lint:fix

typecheck-frontend: ## Run frontend type checker (TypeScript)
	docker compose exec frontend npm run type-check

build-frontend: ## Build frontend for production
	docker compose exec frontend npm run build

build-frontend-analyze: ## Build frontend with bundle analysis
	docker compose exec frontend npm run build:analyze

##@ Combined Code Quality

lint: lint-backend lint-frontend ## Run all linters

format: format-backend ## Format all code

typecheck: typecheck-backend typecheck-frontend ## Run all type checkers

##@ CI/CD

ci: ## Run full CI pipeline (lint, typecheck, security, tests)
	@echo "=== Backend CI ==="
	docker compose exec backend ruff check .
	docker compose exec backend mypy .
	docker compose exec backend bandit -r . -c pyproject.toml
	docker compose exec backend pytest tests/ --cov
	@echo "\n=== Frontend CI ==="
	docker compose exec frontend npm run type-check
	docker compose exec frontend npm run lint
	docker compose exec frontend npm test

ci-full: ci test-e2e ## Run full CI including E2E tests

##@ Utilities

clean: ## Clean up generated files and containers
	docker compose down
	rm -rf backend/.pytest_cache
	rm -rf backend/.mypy_cache
	rm -rf backend/.ruff_cache
	rm -rf backend/htmlcov
	rm -rf backend/.coverage
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find frontend -type d -name .next -exec rm -rf {} + 2>/dev/null || true

clean-volumes: ## Clean up containers and volumes (WARNING: deletes data)
	docker compose down -v

status: ## Show status of all services
	docker compose ps

##@ Database

db-shell: ## Open Neo4j browser shell
	@echo "Opening Neo4j browser at http://localhost:7474"
	@echo "Default credentials: neo4j/password (check docker-compose.yml for actual password)"

##@ Database Backup/Restore

backup: ## Create Neo4j backup (skips if unchanged, ~30-60s downtime)
	@./backend/scripts/backup_neo4j.sh

backup-force: ## Create Neo4j backup even if unchanged
	@FORCE_BACKUP=true ./backend/scripts/backup_neo4j.sh

backup-auto: ## Create Neo4j backup non-interactively (for CI/CD, skips if unchanged)
	@NON_INTERACTIVE=true ./backend/scripts/backup_neo4j.sh

restore: ## Restore Neo4j from latest backup (~1-2min downtime)
	@./backend/scripts/restore_neo4j.sh $(BACKUP)

restore-auto: ## Restore Neo4j non-interactively (for CI/CD)
	@FORCE=true ./backend/scripts/restore_neo4j.sh $(BACKUP)

backup-list: ## List available backups
	@echo "Available backups in ./backups/:"
	@ls -1dt backups/neo4j_backup_* 2>/dev/null | while read d; do \
		size=$$(du -sh "$$d" 2>/dev/null | cut -f1); \
		echo "  $$(basename $$d) ($$size)"; \
	done || echo "  (no backups found)"

##@ Production

prod-up: ## Start production services
	docker compose -f docker-compose.prod.yml up -d --build

prod-down: ## Stop production services
	docker compose -f docker-compose.prod.yml down

prod-logs: ## View production logs
	docker compose -f docker-compose.prod.yml logs -f

prod-logs-backend: ## View production backend logs
	docker compose -f docker-compose.prod.yml logs -f backend

prod-logs-frontend: ## View production frontend logs
	docker compose -f docker-compose.prod.yml logs -f frontend

prod-backup: ## Create Neo4j backup in production (interactive)
	@COMPOSE_FILE=docker-compose.prod.yml ./backend/scripts/backup_neo4j.sh

prod-backup-auto: ## Create Neo4j backup in production (non-interactive, for CI/CD)
	@COMPOSE_FILE=docker-compose.prod.yml NON_INTERACTIVE=true ./backend/scripts/backup_neo4j.sh

prod-backup-force: ## Force Neo4j backup in production even if unchanged
	@COMPOSE_FILE=docker-compose.prod.yml FORCE_BACKUP=true ./backend/scripts/backup_neo4j.sh

prod-restore: ## Restore Neo4j in production from backup (interactive)
	@COMPOSE_FILE=docker-compose.prod.yml ./backend/scripts/restore_neo4j.sh $(BACKUP)

prod-restore-auto: ## Restore Neo4j in production (non-interactive, for CI/CD)
	@COMPOSE_FILE=docker-compose.prod.yml FORCE=true ./backend/scripts/restore_neo4j.sh $(BACKUP)

prod-backup-list: ## List available production backups
	@echo "Available backups in /var/mongado-backups/:"
	@ls -1dt /var/mongado-backups/neo4j_backup_* 2>/dev/null | while read d; do \
		size=$$(du -sh "$$d" 2>/dev/null | cut -f1); \
		echo "  $$(basename $$d) ($$size)"; \
	done || echo "  (no backups found)"
