# Roadmap

## Phase 0: cleanup/security

Quarantine old projects, revoke all exposed credentials, add secret scanning, extract safe code only.

## Phase 1: core substrate — implemented

Bring up Postgres/PostGIS/pgvector, NATS, MinIO, API gateway, module registry, health checks.

## Phase 2: sync engine — implemented

Implement device identity, vector clocks, conflict resolution, attachment sync, sync dashboard.

## Phase 3: first three modules — implemented

Study, Zettelkasten, Geospatial.

## Phase 4: mobile/desktop packaging — implemented

Quasar/Capacitor Android and Tauri desktop shells with private-mesh URLs, auth hardening, and split CI.

## Phase 5: geospatial/AR/research expansion — implemented

TileServer, pgRouting helpers, AR anchors, lawful research acquisition, document cache, citations, and ingestion.

## Phase 6: automation and agentic workflows — implemented

Policy-driven DAG runtime, event triggers, schedules, n8n webhook bridge, approval gates, notification routing, and side-effect outbox.

## Phase 7: hardening and productionization — next

Service-to-service identities, OpenTelemetry traces, SLO dashboards, durable NATS consumers, MinIO presigned artifact routing, mobile background sync, encrypted local stores, and release automation.

## Phase 7 — Production hardening and premium UX

Status: implemented in scaffold.

- Production service identity.
- Release-channel metadata.
- Observability stack and dashboards.
- Mobile background-sync policy.
- Tauri runtime affordances.
- Premium responsive UI shell.
- Split CI coverage workflows.
