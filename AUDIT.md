# AUDIT.md — Personal OS / Nexus Core Repository Audit

Audit date: 2026-07-02
Audited artifact: `personalos.zip` (805 files, ~8.9 MB), version `0.7.0-alpha` per `pyproject.toml` / memory notes.
Method: full extraction (excluding `node_modules/`, `dist/`, `.quasar/`, secrets paths), static reading of all service source, migration inspection, and execution of the Python test suites in a clean sandbox. No secrets were read; none were present in the archive.

---

## 1. Verdict in one paragraph

This is **not** vaporware. The repo contains ~10,800 lines of real FastAPI service code across 14 services, 13 SQL migration files defining **107 tables**, a Quasar/Vue 3 web app with 30 routed pages, Capacitor and Tauri shells with config validators, and a genuinely defensible safety posture (dry-run-by-default connectors, allowlisted coding-agent execution, prompt policy filters, device-token auth). Per-service unit tests pass (166/172 in sandbox; the 6 failures are a missing `pytest-asyncio`/anyio plugin, not code defects). Root suite: 259 pass, 34 fail — **every root failure traces to files absent from the archive** (`.github/workflows`, `.env.example`, `.agents/`) **or to UI drift** (the new `BigPictureHome` and Marketplace-style `ConnectorsPage` broke Phase 14/15 test contracts). The gap to "Nexus Prime" is not raw plumbing — it is: (a) a unified object model over the fragmented per-module tables, (b) a real Obsidian sync (current one is write-only, import is permanently dry-run), (c) a general agent harness (only a coding-agent vertical exists), (d) real embeddings/retrieval (embeddings service is an honest placeholder), and (e) product-grade UX coherence (two competing home screens, 30 flat routes, no information architecture).

---

## 2. Repository map

### Apps (`apps/`)
| Path | What it is | Reality |
|---|---|---|
| `apps/web` | Quasar + Vue 3 SPA. 30 pages, 20 components, services layer (`api.ts`, `auth.ts`, `offline-queue.ts`, `background-sync.ts`, `platform.ts`) each with a vitest file. Design tokens in `src/design/tokens.ts`. Two visual systems: `nexus-dark.scss` (panel UI) and `big-picture.scss` (console/TV-style carousel home). | Real, builds against gateway proxy URLs. Frontend tests exist but pnpm build unverified in sandbox. |
| `apps/mobile` | Capacitor shell: `capacitor.config.ts`, `runtime-policy.ts` (+ test), config validators, preflight script. No native project checked in. | Config-level real; packaging unverified. |
| `apps/desktop` | Tauri 2 shell: `src-tauri` Rust main/lib, `tauri.conf.json` with CSP, config validator. | Config-level real; no custom Rust commands beyond boilerplate. |
| `apps/admin-console` | README only. | Empty placeholder. |

### Services (`services/`) — all FastAPI + asyncpg unless noted
| Service | LOC (py) | Persistence | Tests | Notes |
|---|---|---|---|---|
| api-gateway | 1,217 | yes | 21 pass | Device registration, JWT access + opaque refresh, key rotation, settings, audit log, module seeding, `/api/proxy/*` fan-out, observability, release info. |
| sync-engine | ~700 | yes | 12 pass | Vector-clock compare/merge, LWW, field-merge with conflict list, set-union, minimal op-log text CRDT, sync_log append, conflicts workflow. |
| command-bus | 236 | yes | 2 pass | Signed command requests, templates, approvals. Thin. |
| module-service | 743 | yes | 5 pass | Study items/sessions/flashcards, zettel notes/links, geospatial memories, AR anchors (`ar_math.py` tested). One service, three module APIs. |
| capture-service | ~600 | yes | 18 pass | capture_items → tasks pipeline, frontmatter parser, capture command parser, task fingerprinting, delegation to contacts via WhatsApp/email outbox. **Hardcoded personal email/phone as env defaults — must be removed.** |
| research-service | ~900 | yes | 27 pass | PDF ingestion (`pdf_ingest.py`), chunking, citations, acquisition adapters w/ normalization, source policy. |
| automation-service | ~1,100 | yes | 25 pass | Workflow DAG validation, scheduler, executor with policy gates, approvals, outbox, notifications, n8n bridge. |
| digital-twin-service | ~900 | yes | 23 pass | Ontology, timeline, recommender, privacy/memory policies, model evaluations. |
| connector-service | ~1,300 | yes | 28 pass (6 env-only fails) | OAuth flows + encrypted token storage (crypto.py), providers: google, microsoft, twilio, ntfy, tailscale, obsidian, notion, trello. Obsidian export **actually writes markdown** (create-only, path-contained); import is dry-run-only. Notion/Trello dry-run-only. Backup upload worker. |
| model-runtime | ~500 | yes | 13 pass | Heuristic/disabled/external modes, provider state machine, honest `demo: true` flags, invocation logging. No real Ollama call path wired. |
| coding-agent-service | 350 | yes | 7 pass | Job queue in Postgres, prompt policy (dangerous-pattern regexes, repo allowlist, mode allowlist), git worktree isolation, Claude Code `-p` runner, `CODING_AGENT_EXECUTE=false` default, env scrubbing of TOKEN/SECRET/PASSWORD. |
| study-companion-service | ~450 | yes | 13 pass | Retention scheduling, analog capture, routines. |
| intelligence-service | 440 | yes | none | Sources/monitors/briefings CRUD + run endpoint, service auth middleware, source policy. **Zero tests.** |
| embeddings | 14 | no | none | **Honest placeholder** — deterministic fake vectors, labeled `mode: placeholder`. |

### Modules (`modules/`)
12 manifests conforming to `packages/module-manifest/schema/module-manifest.schema.json`. Three (study, zettelkasten, geospatial) carry their own SQL migrations. Manifests are real contract files, validated by tests.

### Packages (`packages/`)
`config`, `design-system` (+test), `module-manifest` (JSON schema), `schemas` (sync types), `sdk`. Thin but real TypeScript.

### Infra (`infra/`)
Postgres Dockerfile + 13 migrations (107 tables — full inventory in `PERSONAL_GRAPH_SCHEMA.md`), Grafana dashboards + provisioning, Prometheus, OTEL collector, Loki (via compose), SearXNG settings, Tailscale sidecar README.

### Compose
`docker-compose.yml`: 24 services incl. postgres, nats, minio, qdrant, ollama, tileserver, n8n, ntfy, searxng, otel/prometheus/grafana/loki, tailscale, plus all app services.

### Scripts
`bootstrap.sh/.ps1`, `doctor.sh`, `doctor-full.sh`, `backup.sh` (pg_dump + tar), `restore.sh`, `restore-drill.sh`, `update.sh` + `rollback-last-update.sh` + `preflight-update.sh`, `generate-env.py`, `validate-env.py`, `check-secrets.sh`, release signing/publish scripts, certification smokes (`scripts/certify/`), agent-ops harness (`scripts/agents/agentctl.py`, report collection, auto-repair).

### Tests
- Root `tests/`: 47 files, mostly **contract/scaffold tests** (file existence, invariants of scripts, UI text contracts) plus capture e2e and certification suites.
- Per-service `tests/`: behavioral unit tests (conflict math, policy, PDF ingest, providers, recommender, etc.).
- `e2e/`: 3 Playwright specs (navigation, offline-conflicts, live-stack).

### Docs
26 files: per-phase implementation notes (phases 1–15), architecture, sync protocol, security, backup, connectors, module contract, roadmap, troubleshooting, install.

### Missing from the archive (README claims vs. reality)
- `.github/workflows/*` — **absent**. CI is claimed everywhere (docs, tests assert workflow files); cannot verify. 12+ root test failures are workflow-file-existence assertions.
- `.env.example` — **absent**. Several tests and `bootstrap.sh` depend on it.
- `.agents/active.json` — **absent** (agent-ops task registry).
- `apps/web` dist/.quasar/node_modules were shipped inside the zip (archive hygiene failure — its own test `test_phase12_archive_hygiene_excludes_runtime_artifacts` fails, correctly).

---

## 3. Test & build audit (executed)

| Command | Result |
|---|---|
| `python3 -m pytest tests/ --ignore=tests/live` | 259 passed, 34 failed. All 34 failures = missing `.github`/`.env.example`/`.agents` files, archive hygiene, or BigPicture/Connectors UI drift vs. phase-14/15 contracts. |
| Per-service `pytest` (12 services) | 166 passed, 6 failed (connector-service async tests need `pytest-asyncio`/`anyio` plugin — dependency, not logic). |
| `pnpm --dir apps/web test` / typecheck | Not runnable in sandbox (network-restricted install of full Quasar toolchain not attempted). Marked unverified. |
| `docker compose config` | Not runnable (no Docker in sandbox). Compose YAML parses cleanly with PyYAML. |
| Shell scripts `bash -n` | All pass syntax check. |

**Safe local commands** (owner machine): see `IMPLEMENTATION_PLAN.md` §"Verification commands".

---

## 4. Security & privacy findings

1. **P0 — Personal PII hardcoded as defaults**: `services/capture-service/app/main.py` ships a real-looking Gmail address and phone number as `SECRETARY_EMAIL`/`SECRETARY_WHATSAPP` defaults. Remove defaults; require env; scrub git history if this repo is ever published.
2. **P1 — CORS `allow_origins=["*"]` with `allow_credentials=True`** on every service. Fine on Tailscale-only, dangerous if any port is exposed. Restrict to gateway origin(s).
3. **P1 — Offline queue in `localStorage`**: unencrypted mutation bodies (may include captured text) persisted in plain localStorage with ~5MB ceiling; `localforage` is initialized (`boot/localdb.ts`) but the queue doesn't use it. Migrate queue to IndexedDB via localforage; add size/eviction policy.
4. **P2 — Coding-agent prompt regex filter is bypassable** (regexes on prompts, not on executed commands). Acceptable only because `CODING_AGENT_EXECUTE=false` default + worktree isolation exist; the real control must be an execution-side allowlist (see AGENTIC_HARNESS_SPEC).
5. **P2 — No `.env.example` in archive** → bootstrap path broken for fresh clones; also weakens the "no hardcoded secrets" test line.
6. **P2 — Single-user trust model**: device registration issues tokens to anyone who can reach port 8080. Correct for Tailscale-only; must be documented as a hard requirement and enforced (bind to tailnet interface or require pairing code — `device_pairing_codes` table already exists but registration doesn't require it).
7. **P3 — Obsidian import permanently dry-run** means no untrusted vault content enters the system yet; when implemented, add frontmatter sanitization and size limits.

---

## 5. What is genuinely good (preserve)

- **Dry-run-first doctrine** across connectors and coding agent, with honest `status: dry_run` payloads and `demo: true` flags in model-runtime. This is exactly the "no mocked implementation pretending to work" posture — keep and generalize it.
- **Sync engine math is real and tested**: vector clocks, field-level merge with explicit conflict surfacing, op-log text CRDT with a documented upgrade path.
- **Obsidian export safety**: vault-path containment validation + create-only (`open("x")`) no-overwrite semantics.
- **Coding-agent isolation**: git worktrees per job, env scrubbing, repo allowlist, mode allowlist, Postgres-backed job records.
- **Migration discipline**: 13 ordered migrations, per-module migrations for study/zettel/geo, entities/entity_versions as a proto-graph spine.
- **Contract tests as regression armor**: the phase-N scaffold tests caught the BigPicture drift — the mechanism works; the contracts just need updating deliberately, not deleted.
- **Ops scripts**: doctor-full, restore-drill, update/rollback pipeline, release manifest builder.

## 6. What is honestly weak or missing

Summarized here; full classification in `FEATURE_REALITY_MATRIX.md`, risks in `ARCHITECTURE_RISK_REGISTER.md`, plan in `IMPLEMENTATION_PLAN.md`.

- Embeddings/retrieval: placeholder → no semantic memory anywhere.
- Obsidian: export-only; no frontmatter schema, daily notes, backlinks, conflict-safe sync, or vault watcher.
- Agent harness: only the coding vertical; no tool registry, skill registry, agent memory, evals, or generic AgentJob.
- Knowledge graph: 107 tables but no unified object/edge layer; `entities`/`entity_versions` under-used by newer modules.
- UX: two home screens (BigPictureHome vs CommandCenterPage), 30 flat routes, ops/dev pages (certification, release-center, live-stack) mixed into user nav; CommandPalette is a 44-line stub.
- Backup: local pg_dump/tar only; no rclone/Drive template, no encryption, `remote_backup_uploads` table exists but no wired remote path.
- CI: claimed, absent from archive.
- Intelligence service: 440 LOC, zero tests.
- Mobile: no capture-first UX, no share-target intent, offline queue fragile.

## 7. Cross-references

- Feature-by-feature classification → `docs/FEATURE_REALITY_MATRIX.md`
- Risk register → `docs/ARCHITECTURE_RISK_REGISTER.md`
- Target object model → `docs/PERSONAL_GRAPH_SCHEMA.md`
- Plan and maturity levels → `docs/IMPLEMENTATION_PLAN.md`, `docs/ROADMAP_NEXUS_PRIME.md`
- Product surfaces → `docs/UX_PRODUCT_SPEC.md`
- Agent harness → `docs/AGENTIC_HARNESS_SPEC.md`
- Obsidian → `docs/OBSIDIAN_INTEGRATION_SPEC.md`
- Continuity → `docs/MOBILE_DESKTOP_CONTINUITY.md`
- Backup → `docs/BACKUP_RESTORE_SPEC.md`
- Agent handoff → `NEW_AGENT_HANDOFF.md`

---

## Addendum — Phase A (Truth & Hygiene) completed, 2026-07-02

Executed against this audit's findings. Verified state: **root suite 312/312 passed** (was 259/293), **all 13 service suites green** including connector-service async tests (pytest-asyncio) and intelligence-service's first 20 tests.

| Finding | Resolution |
|---|---|
| §4.1 P0 PII defaults (R-01) | Defaults removed from capture-service; startup warning + fail-closed structured 409 at delegation; second PII-adjacent phone fixture replaced in connector tests; check-secrets.sh now scans emails/phones and passes clean. |
| §2 Missing `.github/`, `.env.example`, `.agents/` (R-02) | Recreated: 10 workflows (all historical CI contracts honored: no `cache: pnpm`, NODE24 flag, pip install+pytest in named phase lanes), comprehensive `.env.example` (generated env validates 0 errors), `.agents/active.json`, `.gitignore`. |
| §2 marketplace tests un-importable | Root `conftest.py` aliases hyphenated service dirs as `services.<underscore>` packages — the missing mechanism, now explicit and Windows-safe. |
| R-03 two homes / broken contracts | `/` → CommandCenterPage, `/ambient` → BigPictureHome (linked from home), `/intelligence` routed (was orphaned). ConnectorsPage: Marketplace layout kept, legacy contract content restored (setup instructions, ntfy help, tailscaleDetail, obsidian/notion/trello dry-runs, configured-gating, secrets note). |
| §4.2 CORS `*` hardcoded (R-07a) | All services read `CORS_ALLOW_ORIGINS` from env. |
| §4.6 registration without pairing (R-07b) | Gateway enforces single-use pgcrypto-verified pairing codes when `AUTH_REQUIRED=true` (`REQUIRE_DEVICE_PAIRING`, default true); first-device bootstrap; codes consumed atomically + audited; web pairing entry flow added (sessionStorage only). |
| R-12 intelligence untested | 20 behavioral tests (source policy, JWT verification). |
| R-20 archive hygiene | `make package` via `git archive`; CI job asserts archives are clean. |
| New | `tests/test_phase_a_hygiene.py` (12 tests) locks Phase A invariants. |

Risk register status: R-01, R-02, R-03 closed; R-07 partially closed (residual: device_key re-issue path, tracked for Phase E); R-12, R-20 closed. Next: Phase B per IMPLEMENTATION_PLAN.md.
