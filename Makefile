SHELL := /usr/bin/env bash
COMPOSE := docker compose --env-file .env

.PHONY: install doctor doctor-full up down up-research up-maps up-automation up-digital-twin up-capture up-study-companion up-connectors logs backup restore mobile desktop test test-backend test-phase5 test-phase6 test-phase8 test-phase9 test-phase10 test-frontend test-mobile test-desktop lint format nuke migrate seed

install:
	./scripts/bootstrap.sh

doctor:
	./scripts/doctor.sh

doctor-full:
	./scripts/doctor-full.sh

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

up-capture:
	$(COMPOSE) --profile automation --profile apps up -d --build capture-service

up-study-companion:
	$(COMPOSE) --profile ai --profile research --profile apps up -d --build study-companion-service

up-connectors:
	$(COMPOSE) --profile core --profile connectors --profile automation up -d --build connector-service

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

test: test-backend test-phase5 test-phase6 test-phase8 test-phase9 test-phase10
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


test-phase9:
	cd services/capture-service && python -m pytest tests -q --cov=app.parser --cov=app.delegation --cov=app.tasking --cov-branch --cov-fail-under=96
	cd services/study-companion-service && python -m pytest tests -q --cov=app.retention --cov=app.analog --cov=app.routines --cov-branch --cov-fail-under=96
	python -m pytest tests/test_phase9_scaffold.py -q

test-phase10:
	cd services/connector-service && python -m pytest tests -q --cov=app.oauth --cov=app.providers --cov=app.backup --cov-branch --cov-fail-under=96
	python -m pytest tests/test_phase10_scaffold.py -q

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

test-ci-stabilization:
	python -m pytest tests/test_ci_stabilization.py -q

.PHONY: test-phase11 restore-drill up-full

up-full:
	./scripts/bootstrap.sh --full --open

test-phase11:
	cd services/connector-service && python -m pytest tests -q --cov=app.providers --cov=app.backup --cov=app.oauth --cov-branch --cov-fail-under=96
	python -m pytest tests/test_phase11_scaffold.py -q

restore-drill:
	./scripts/restore-drill.sh

.PHONY: test-phase12 certify-local certify-android certify-live-connectors release-android-signed release-tauri-signed verify-release-artifacts

test-phase12:
	python -m pytest tests/test_phase12_scaffold.py -q
	python -m pytest tests/live -q -m "not live"

certify-local:
	./scripts/certify/full-local.sh

certify-android:
	./scripts/certify/physical-android.sh

certify-live-connectors:
	./scripts/certify/live-connectors.sh

release-android-signed:
	./scripts/release/build-android-signed.sh

release-tauri-signed:
	./scripts/release/build-tauri-signed.sh

verify-release-artifacts:
	./scripts/release/verify-release-artifacts.sh

.PHONY: test-phase13 certify-live-stack certify-physical-sync certify-model-runtime publish-release release-readiness up-model-runtime

up-model-runtime:
	$(COMPOSE) --profile ai --profile apps up -d --build model-runtime

test-phase13:
	cd services/model-runtime && python -m pytest tests -q --cov=app.runtime --cov-branch --cov-fail-under=96
	python -m pytest tests/test_phase13_scaffold.py -q

certify-live-stack:
	./scripts/certify/live-stack-e2e.sh

certify-physical-sync:
	./scripts/certify/physical-sync.sh

certify-model-runtime:
	./scripts/certify/model-runtime.sh

release-readiness:
	./scripts/certify/release-readiness.py

publish-release:
	./scripts/release/publish-github-release.sh

.PHONY: doctor-qdrant
doctor-qdrant:
	./scripts/doctor-qdrant.sh

.PHONY: up-coding-agent test-phase14
up-coding-agent:
	$(COMPOSE) --profile apps --profile automation up -d --build coding-agent-service

test-phase14:
	cd services/coding-agent-service && python -m pytest tests -q
	python -m pytest tests/test_phase14_scaffold.py -q
