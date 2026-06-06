# Personal OS — Sovereign Modular Control Plane

A production-oriented scaffold for a sovereign, modular, offline-first personal operating system.

## Default stack

- Apps: Quasar + Vue 3 + Pinia + Capacitor; Tauri desktop shell.
- Backend: FastAPI services.
- Data: PostgreSQL 16 + PostGIS + pgvector.
- Eventing: NATS JetStream.
- Object storage: MinIO.
- Sync: append-only sync log, entity versions, device identity, conflict-aware merges.
- Optional: Qdrant, Ollama, TileServer GL, n8n, ntfy, SearXNG, Prometheus/Grafana/Loki.
- Private networking: Tailscale-compatible sidecar profile.


## Phase 1-3 status

This archive includes the implemented Phase 1-3 foundation:

- Phase 1: device registration, token issuance, encrypted cloud-token storage, settings, audit log, command approvals.
- Phase 2: expanded sync engine with vector-clock conflict detection, manual conflict workflow, attachment metadata/content flow, and sync dashboard.
- Phase 3: real `study`, `zettelkasten`, and `geospatial` module APIs plus Quasar pages.

See `docs/phase-1-3-implementation.md`.

## First-run

```bash
cp .env.example .env
./scripts/bootstrap.sh
```

Then open:

- API gateway: http://localhost:8080
- Sync engine: http://localhost:8081
- Command bus: http://localhost:8082
- MinIO console: http://localhost:9001
- NATS monitor: http://localhost:8222

## Safety posture

This scaffold intentionally excludes credentials, hardcoded tokens, credential extraction, offensive scanning, daemon persistence, and unauthenticated remote shell execution. Remote commands are mediated through signed requests, allowlisted templates, scopes, approvals, and audit logs.

## Phase 4: mobile, desktop, auth, and CI

Phase 4 adds:

- Capacitor Android packaging in `apps/mobile`.
- Tauri desktop packaging in `apps/desktop`.
- Gateway-first client URLs for sync, modules, and command bus.
- Short-lived access tokens, opaque refresh tokens, token revocation, and key-id rotation support.
- Downstream service auth middleware for direct local calls when `AUTH_REQUIRED=true`.
- GitHub Actions split by backend unit, backend integration, frontend web, mobile Android, desktop Tauri, Docker Compose, and security.

Local verification:

```bash
make test-backend
make test-mobile
make test-desktop
pnpm --dir apps/web test
```

Production-style local auth smoke:

```bash
cp .env.example .env
python3 scripts/generate-env.py .env
sed -i 's/AUTH_REQUIRED=false/AUTH_REQUIRED=true/' .env
make up
TOKEN=$(curl -fsS -X POST http://localhost:8080/api/devices/register \
  -H 'content-type: application/json' \
  -d '{"device_key":"cli","name":"CLI","kind":"desktop","platform":"linux"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
curl -H "authorization: Bearer $TOKEN" http://localhost:8080/api/modules
```

## Phase 5: geospatial, AR, and research expansion

Phase 5 adds:

- Research service for open/public metadata search, user-authorized PDF URL ingestion, local PDF upload, chunking, citation extraction, and local full-text search.
- Source-policy guardrails that block pirate-library and paywall-circumvention sources while preserving legitimate acquisition workflows.
- `research` and `ar-memory` module manifests.
- Quasar pages for `/research` and `/ar-memory`.
- Offline map dataset registration and TileServer-compatible data layout.
- pgRouting import script for operator-provided OSM extracts.
- AR anchor storage and orientation projection math.
- Separate Phase 5 GitHub workflow for research policy/extraction and AR math coverage.

Run research services:

```bash
make up-research
```

Run maps:

```bash
make up-maps
```

Run Phase 5 tests:

```bash
make test-phase5
python3 -m pytest tests/test_phase5_scaffold.py -q
```

See `docs/phase-5-research-maps-ar.md`.

## Phase 6: automation and agentic workflows

Phase 6 adds the bounded automation substrate:

- `automation-service` for DAG workflows, event triggers, interval schedules, n8n webhooks, approval gates, and side-effect outbox.
- `automation` module manifest and `/automation` Quasar page.
- Gateway proxy at `/api/proxy/automation/{path}`.
- New scopes: `automation:read` and `automation:write`.
- Policy engine that blocks raw shell, host filesystem writes, network scanning, privileged containers, and secret reads.
- Human approval for command requests, n8n calls, external HTTP, destructive nodes, and explicit approval gates.
- Separate Phase 6 GitHub workflow with 96% coverage gate and migration smoke test.

Run automation services:

```bash
make up-automation
```

Run Phase 6 tests:

```bash
make test-phase6
```

See `docs/phase-6-automation-agentic-workflows.md`.

## Phase 7 — production cockpit

Phase 7 adds production-oriented hardening and a premium cross-platform shell:

- Service-to-service identity tokens for internal calls.
- API gateway RED metrics at `/metrics` and release metadata at `/api/release`.
- OpenTelemetry Collector, Prometheus, Grafana provisioning, and Loki under the observability profile.
- Premium responsive web/mobile/desktop shell with command palette, adaptive navigation, glass-panel design language, accessibility tokens, and reduced-motion support.
- Mobile runtime policy for battery/network-aware background sync.
- Tauri desktop runtime commands and deep-link sanitization.
- Split GitHub workflows for Phase 7 backend hardening, UX tests, mobile preflight, desktop native tests, observability Compose validation, and release artifacts.

```bash
make up-observability
make test-phase7
pnpm --dir packages/design-system test
pnpm --dir apps/mobile preflight
```

## Phase 8 — digital twin intelligence

Phase 8 adds the personal intelligence layer:

- `digital-twin-service` for ontology, timeline events, inferred state, goals, privacy-aware memory, recommendations, and golden evaluation cases.
- `digital-twin` module manifest and `/digital-twin` Quasar page.
- Gateway proxy at `/api/proxy/digital-twin/{path}`.
- New scopes: `digital_twin:read`, `digital_twin:write`, `recommendations:write`, and `digital_twin:export`.
- Privacy policy controls for memory classes, sensitivity levels, retention, redaction, and recommendation eligibility.
- Deterministic recommender with explicit rationale and approval-aware action payloads.
- Separate Phase 8 GitHub workflow with a 96% coverage gate.

Run the service:

```bash
make up-digital-twin
```

Run Phase 8 tests:

```bash
make test-phase8
```

See `docs/phase-8-digital-twin-intelligence.md`.


## Phase 9 — Capture, Tasks, Delegation, Study Companion

Phase 9 adds the working-memory layer:

- `/capture` for slash-command quick capture.
- `/tasks` for task inbox, delegated work, and follow-ups.
- `/study-companion` for pasted text, photos/files, analog-to-digital capture, OCR/object-detection hooks, Zettelkasten note creation, learning atoms, and retention scheduling.
- `capture-service` for task/delegation/outbox workflows.
- `study-companion-service` for OCR/vision-adapter pipelines and scientific review scheduling.

Run:

```bash
make up-capture
make up-study-companion
make test-phase9
```
