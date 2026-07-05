# IMPLEMENTATION_PLAN.md — Nexus Prime

Maturity levels (per feature, tracked in FEATURE_REALITY_MATRIX):
- **L0** scaffold · **L1** imports/builds · **L2** real local data flow · **L3** tested vertical slice · **L4** PC/mobile continuity · **L5** Obsidian + backup integration · **L6** agentic harness w/ approvals · **L7** portfolio-grade UX · **L8** daily-use release candidate

Doctrine reminders binding every phase: no mocked implementations (dry-run/degraded states must be honest and labeled); do not rewrite working services; never touch secrets/data dirs; no destructive ops; **every phase updates the eight living docs** (NEW_AGENT_HANDOFF.md + the docs/ set).

---

## Phase A — Truth & Hygiene (repo health to L1 everywhere) — ✅ COMPLETE 2026-07-02

Goal: green tests, working CI, zero PII, one canonical home.

1. **A1 PII purge (R-01)**: remove secretary email/phone defaults from `capture-service/app/main.py` (require env, fail closed with clear error); extend `scripts/check-secrets.sh` with email/phone regexes; verify no other occurrences (`grep -rE "[a-z0-9._%+-]+@gmail|(\+?[0-9]{10,})"` across source). If repo will ever be public: history rewrite checklist documented (not executed by agents).
2. **A2 Restore missing scaffolding**: recreate `.env.example` (from `generate-env.py` + validate-env expectations), `.agents/active.json`, and `.github/workflows/`: `backend.yml` (ruff + root pytest + per-service pytest incl. pytest-asyncio dep — fixes the 6 connector async fails), `frontend.yml` (pnpm install, vitest, vue-tsc, quasar build), `compose.yml` (docker compose config + secret scan + archive hygiene), `evals.yml` (placeholder lane, activated Phase F).
3. **A3 Resolve UI drift (R-03)**: `/` → CommandCenterPage, `/ambient` → BigPictureHome; restore ConnectorsPage setup content into the Marketplace layout; update phase-14/15 contract tests deliberately in the same PRs.
4. **A4 Security quickies (R-07)**: CORS origins from env (default gateway origin), pairing-code enforcement on device register when `AUTH_REQUIRED=true`, intelligence-service test suite bootstrap (R-12), command-bus test expansion (R-19).
5. **A5 Packaging**: `git archive`-based zip target in Makefile; hygiene test in CI.

Exit criteria (MET — 312/312 root, 13/13 service suites): root pytest 100% (or explicitly-skipped-with-reason), all service suites green in CI, `pnpm test` + typecheck green in CI, no PII patterns.

## Phase B — Graph & Memory spine (L2→L3 for the object model) — ~2 weeks

1. **B1 Migration 014** (`objects`, `edges`, `object_chunks`, new domain tables: projects, decisions, daily_states, repositories, portfolio_cases) per PERSONAL_GRAPH_SCHEMA.md.
2. **B2 `packages/graph`** helper (py+ts) + dual-write from capture, tasks, notes, research, twin, coding-agent; `scripts/graph/backfill.py` idempotent backfill.
3. **B3 Real embeddings (R-05)**: replace placeholder service body with provider chain — Ollama `nomic-embed-text` (or `bge-m3`) via model-runtime provider states; NATS `nexus.embed` consumer fills `object_chunks.embedding`; **honest degradation**: no model → chunks stored, embedding null, search falls back to Postgres trigram (`pg_trgm`), UI labels "lexical search (no embedding model)".
4. **B4 Graph API in gateway**: objects list/neighbors/hybrid search; palette + Notes backlinks consume it.
5. **B5 Projects & Daily verticals**: minimal Projects CRUD + DailyState open/close-day flow (backend + pages), because Phases C–F all hang off them.

Exit: create capture → triage to task under a project → find it via hybrid search → see it as a neighbor of the project. One Playwright spec proves the loop.

## Phase C — Command surface & UX IA (L7 groundwork) — ~2 weeks

1. C1 IA regroup per UX_PRODUCT_SPEC (13 surfaces, /ops area, redirects for old routes).
2. C2 Command Center rebuild on live queries (Attention chips: approvals, conflicts, backup age, failed jobs).
3. C3 Command palette v2 (actions + graph search + navigation, keyboard complete).
4. C4 Capture Inbox triage UX (keyboard + swipe), Today/Focus surface.
5. C5 Contract tests updated; density toggle; empty/error-state enforcement test.

## Phase D — Obsidian integration (L5) — ~2–3 weeks

Per OBSIDIAN_INTEGRATION_SPEC delivery order: frontmatter renderer/parser → vault indexer + read → outbound Project/Daily/Decision → inbound 3-way merge + conflict UI → task-line round trip → canvas export. Settings vault UX + per-note sync chips. Vault write stays opt-in with pre-enable vault backup.

## Phase E — Continuity & Backup (L4 + L5) — ~2 weeks

1. E1 Offline queue v2 (IndexedDB, per-entity ordering, backoff, dead-letter, optional encryption) + background sync policy object.
2. E2 Android share-target + quick-capture; voice capture queue (transcription honest-degraded until whisper configured); pairing QR flow enforced.
3. E3 Tauri global hotkey + tray + quick-capture window.
4. E4 Backup v2 per BACKUP_RESTORE_SPEC: pg_dump -Fc + MinIO + vault, age encryption, rclone template + remote upload + prune, verify + monthly drill automation, preflight-update gate.
5. E5 `/continuity` surface with the four health tiles.

## Phase F — Agentic harness (L6) — ~3 weeks

Per AGENTIC_HARNESS_SPEC: migration tables → tool registry + executor (budgets, fail-closed) → orchestrator in automation-service → planner via model-runtime (blocked-honest without model) → approvals (UI + ntfy action links) → context packs → coding-agent execution-side hardening (`--allowedTools`, diff caps) → skills + evals + nightly CI lane → agent-run reports to Obsidian.

## Phase G — Portfolio-grade polish & daily-driver RC (L7→L8) — ~2 weeks

Ambient mode live-bound or trimmed; FSRS for study (R-24); intelligence briefing → morning-briefing automation recipe; a11y + keyboard audit; performance pass (route-level code splitting, list virtualization); `docs/` index; three shipped automation recipes (morning briefing, inbox sweep, backup verify); **7-day self-dogfood checklist** with issue capture into the system itself; release via signed pipeline.

---

## Latent/proactive capabilities designed-in now (cheap later)

- `object_chunks.model` column → multi-model re-embedding without schema change.
- `edges.weight` → future ranking/decay ("memory strength") without new tables.
- `agent_memory.expires_at` → forgetting policy from day one.
- Habit chain via `follows` edges → streaks computable without a habit engine.
- ntfy signed action URLs → phone-side approvals before any mobile-native approval UI exists.
- SearXNG already in compose → `web.search` agent tool costs ~0 infra.
- `repositories.allowed_for_agent` → DB-driven agent allowlist replaces env lists.
- Vault-as-capture-source (untagged notes → CaptureItems) → Obsidian mobile becomes a free capture client on day one of Phase D.

## Verification commands (safe, no secrets)

```bash
# Python
python3 -m pytest tests/ --ignore=tests/live -q
for d in services/*/tests; do (cd $(dirname $d) && python3 -m pytest -q); done
ruff check services

# Frontend
pnpm --dir apps/web install && pnpm --dir apps/web test
pnpm --dir apps/web exec vue-tsc --noEmit

# Config & scripts
docker compose config -q
bash -n scripts/*.sh
python3 scripts/validate-env.py .env.example
node apps/desktop/scripts/validate-tauri-config.mjs
node apps/mobile/scripts/validate-capacitor-config.mjs

# E2E (needs running stack)
pnpm exec playwright test e2e/navigation.spec.ts
```
