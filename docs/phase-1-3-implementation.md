# Phase 1-3 Implementation Notes

This scaffold now implements the next three engineering phases after the initial foundation.

## Phase 1 — Core substrate hardening

Implemented:

- Device registration and bearer-token issuance in `services/api-gateway`.
- Optional auth enforcement through `AUTH_REQUIRED`.
- Device registry API.
- Settings API backed by the `settings` table.
- Encrypted OAuth refresh-token storage with Fernet in `cloud_tokens`.
- Cloud-account metadata tables and API endpoints for Google/Microsoft placeholders.
- Audit logging for device, setting, cloud, and command operations.
- Command bus approval/deny/result lifecycle.
- HMAC signature verification for command payloads when a signature is supplied.
- Idempotent migration `002_phase_1_2_3.sql`.

Security posture:

- No refresh token is printed by API responses.
- OAuth tokens are stored only as encrypted bytes.
- Command templates enforce scope allowlists.
- Destructive/local commands remain approval-gated by default.
- `AUTH_REQUIRED=false` is local-dev only; production must set it to `true`.

## Phase 2 — Sync engine

Implemented:

- Idempotent sync event ingestion.
- Entity/version/sync-log writes per change.
- Vector-clock comparison.
- Merge strategies: `lww`, `field_merge`, `set_union`, `counter`, `crdt_text`, `manual`.
- Open conflict persistence in `sync_conflicts`.
- Conflict listing and explicit resolution endpoints.
- Attachment metadata initiation and local content upload endpoint.
- Service event outbox table for future NATS publication workers.
- Sync health dashboard data: latest cursor and open-conflict count.

MVP CRDT note:

`crdt_text` currently supports deterministic append/set operation logs. It is deliberately minimal but preserves the data-model boundary required to replace it with Yjs/Automerge later.

## Phase 3 — First real modules

Implemented in `services/module-service`:

- `study`
  - Study item CRUD.
  - Study sessions.
  - Flashcard creation.
  - SM-2 review scheduling.
- `zettelkasten`
  - Markdown note creation/list/read.
  - Tags and note types.
  - Wiki-link extraction with `[[Title]]` links.
  - Obsidian-compatible Markdown export.
  - Optional georeferenced notes.
- `geospatial`
  - Geospatial memory creation/listing.
  - PostGIS-backed nearby query.
  - Tags, memory types, arbitrary JSON properties.

Implemented in `apps/web`:

- Home control plane health/module cards.
- Study module page.
- Zettelkasten module page.
- Geospatial module page.
- Sync dashboard with round-trip and conflict workflow.

## Run

```bash
cp .env.example .env
python3 scripts/generate-env.py .env
./scripts/bootstrap.sh
```

Then open:

- API gateway: http://localhost:8080
- Sync engine: http://localhost:8081
- Command bus: http://localhost:8082
- Module API: http://localhost:8083
- Web shell: http://localhost:9000

## Validation

```bash
python3 -m compileall -q services/api-gateway services/sync-engine services/command-bus services/module-service
python3 -m pytest tests services/sync-engine/tests -q
./scripts/check-secrets.sh
```
