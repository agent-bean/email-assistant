.DEFAULT_GOAL := help
.PHONY: help install install-backend install-web api web stores-up stores-down lint typecheck build api-generate api-check test-unit test-integration test-e2e test check
# ponytail: shared environments require serial checks; isolate them before parallelizing.
.NOTPARALLEL:

ENV_FILE ?=
COMPOSE = docker compose --env-file "$(ENV_FILE)" -f deploy/compose.yaml -p email-assistant-dev

help:
	@echo 'Setup: install'
	@echo 'Run: api | web | stores-up | stores-down (stores require ENV_FILE)'
	@echo 'Check: lint | typecheck | build | api-check | check'
	@echo 'Tests: test-unit | test-integration | test-e2e | test (all scopes)'
	@echo 'Contract update: api-generate'

install: install-backend install-web

install-backend:
	cd apps/backend && uv sync --locked

install-web:
	cd apps/web && npm ci

api:
	cd apps/backend && uv run --locked uvicorn email_assistant.api.main:app --host 127.0.0.1 --port 8000

web:
	cd apps/web && npm run dev

stores-up:
	@test -n "$(ENV_FILE)" || { echo 'Set ENV_FILE to your private configuration path'; exit 1; }
	APP_ENV_FILE="$(ENV_FILE)" uv run --locked --project apps/backend python -m email_assistant.config $(COMPOSE)
	$(COMPOSE) up -d --wait --wait-timeout 180

stores-down:
	@test -n "$(ENV_FILE)" || { echo 'Set ENV_FILE to your private configuration path'; exit 1; }
	$(COMPOSE) down

lint:
	cd apps/backend && uv run --locked ruff check . ../../scripts --config pyproject.toml
	cd apps/web && npm run lint

typecheck:
	cd apps/backend && uv run --locked mypy src
	cd apps/web && npm run typecheck

build:
	cd apps/web && npm run build

api-generate:
	cd apps/web && npm run api:generate

api-check:
	cd apps/web && npm run api:check

test-unit:
	cd apps/backend && uv run --locked pytest -m unit

test-integration:
	python3 scripts/check-stores.py

test-e2e:
	cd apps/web && npm run test:e2e

test: test-unit test-integration test-e2e

check: lint typecheck api-check build test
