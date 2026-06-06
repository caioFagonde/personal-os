SHELL := /usr/bin/env bash
COMPOSE := docker compose --env-file .env

.PHONY: install doctor up down up-research up-maps up-automation up-digital-twin logs backup restore mobile desktop test test-backend test-phase5 test-phase6 test-phase8 test-frontend test-mobile test-desktop lint format nuke migrate seed

install:
	./scripts/bootstrap.sh

doctor:
	./scripts/doctor.sh

up:
	$(COMPOSE) --profile core up -d --build

down:
	$(COMPOSE) down

up-research:
	$(COMPOSE) --profile research up -d --build research-service searxng qdrant embeddings

up-maps:
	$(COMPOSE) --profile maps up -d --build tileserver

up-automation:
	$(COMPOSE) --profile automation up -d --build automation-service command-bus n8n ntfy

up-digital-twin:
	$(COMPOSE) --profile core --profile ai up -d --build digital-twin-service

logs:
	$(COMPOSE) logs -f --tail=200

migrate:
	for migration in infra/postgres/migrations/*.sql; do $(COMPOSE) exec -T postgres psql -v ON_ERROR_STOP=1 -U $${POSTGRES_USER:-personal_os} -d $${POSTGRES_DB:-personal_os} < $$migration; done

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

test: test-backend test-phase5 test-phase6 test-phase8
	python -m pytest tests


test-backend:
	cd services/api-gateway && python -m pytest tests -q --cov=app.security --cov-branch --cov-fail-under=95
	cd services/sync-engine && python -m pytest tests -q --cov=app.conflict --cov-branch --cov-fail-under=95
	cd services/command-bus && python -m pytest tests -q --cov=app.signing --cov-branch --cov-fail-under=100


test-phase5:
	cd services/research-service && python -m pytest tests -q --cov=app.source_policy --cov=app.pdf_ingest --cov=app.acquisition --cov-branch --cov-fail-under=92
	cd services/module-service && python -m pytest tests/test_ar_math.py -q --cov=app.ar_math --cov-branch --cov-fail-under=100

test-phase6:
	cd services/automation-service && python -m pytest tests -q --cov=app.dag --cov=app.policy --cov=app.executor --cov=app.scheduler --cov=app.n8n_bridge --cov=app.notifications --cov-branch --cov-fail-under=96

test-phase8:
	cd services/digital-twin-service && python -m pytest tests -q --cov=app.ontology --cov=app.privacy --cov=app.timeline --cov=app.recommender --cov=app.evaluation --cov-branch --cov-fail-under=96
	python -m pytest tests/test_phase8_scaffold.py -q

test-frontend:
	pnpm --dir apps/web test

test-mobile:
	pnpm --dir apps/mobile validate

test-desktop:
	pnpm --dir apps/desktop validate
	cd apps/desktop && cargo test --manifest-path src-tauri/Cargo.toml

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

.PHONY: up-observability test-phase7 release-web release-desktop release-android

up-observability:
	$(COMPOSE) --profile observability up -d --build prometheus grafana loki otel-collector

test-phase7:
	cd services/api-gateway && python -m pytest tests/test_service_identity.py tests/test_observability.py tests/test_release.py -q --cov=app.service_identity --cov=app.observability --cov=app.release --cov-branch --cov-fail-under=96
	python -m pytest tests/test_phase7_scaffold.py -q

release-web:
	pnpm --dir apps/web build

release-desktop:
	pnpm --dir apps/desktop build

release-android:
	pnpm --dir apps/mobile preflight
	pnpm --dir apps/web build
	pnpm --dir apps/mobile cap:sync
