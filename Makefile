SHELL := /usr/bin/env bash
COMPOSE := docker compose --env-file .env

.PHONY: install doctor up down logs backup restore mobile desktop test lint format nuke migrate seed

install:
	./scripts/bootstrap.sh

doctor:
	./scripts/doctor.sh

up:
	$(COMPOSE) --profile core up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

migrate:
	$(COMPOSE) exec -T postgres psql -U $${POSTGRES_USER:-personal_os} -d $${POSTGRES_DB:-personal_os} < infra/postgres/migrations/001_core.sql

seed:
	$(COMPOSE) exec -T api-gateway python -m app.seed_modules

backup:
	./scripts/backup.sh

restore:
	./scripts/restore.sh

mobile:
	./scripts/deploy-android.sh

desktop:
	./scripts/deploy-desktop.sh

test:
	python -m pytest tests services/sync-engine/tests

lint:
	python -m ruff check services scripts || true
	pnpm lint || true

format:
	python -m ruff format services scripts || true
	pnpm format || true

nuke:
	@read -rp "Type NUKE to delete containers and volumes: " confirm; \
	[[ "$$confirm" == "NUKE" ]] || (echo "Aborted" && exit 1); \
	$(COMPOSE) down -v --remove-orphans; \
	rm -rf data/postgres data/minio data/nats data/qdrant data/ollama data/ntfy data/tailscale logs tmp cache
