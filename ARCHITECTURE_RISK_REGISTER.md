# ARCHITECTURE_RISK_REGISTER.md

Severity: P0 (fix before anything else) → P3 (track). Each risk lists impact, evidence, and mitigation. Mitigations map to phases in `IMPLEMENTATION_PLAN.md`.

## P0

| ID | Risk | Evidence | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | **PII hardcoded as env defaults** (owner-adjacent email + phone in `capture-service/app/main.py`) | `DEFAULT_SECRETARY_EMAIL`, `DEFAULT_SECRETARY_WHATSAPP` | Privacy leak if repo shared/published; violates own doctrine | Remove defaults, require env, add `check-secrets.sh` pattern for emails/phones, history scrub before any publication (Phase A). |
| R-02 | **CI absent from archive while tests assert it** | No `.github/`; 12+ failing workflow tests | No automated regression net; "certified" claims unverifiable | Recreate workflows (backend, frontend, compose-config, secret-scan, archive-hygiene) in Phase A; make `git archive`-based packaging the only release path. |
| R-03 | **Two competing home screens + broken UI contracts** | BigPictureHome default vs CommandCenterPage; phase-14/15 tests failing against live code | Test suite loses authority; UX incoherent; every future change ambiguous | Decide IA (see UX spec: Command Center = default; Big Picture = optional ambient mode), update contract tests in the same commit (Phase A). |

## P1

| ID | Risk | Evidence | Impact | Mitigation |
|---|---|---|---|---|
| R-04 | **Data-model fragmentation — no unified graph** | 107 tables; notes/tasks/research/twin don't write `entities`/edges; no link table beyond zettel_links | "Personal knowledge graph" impossible; every cross-module feature becomes a bespoke join | Introduce `objects` + `edges` registry layer (PERSONAL_GRAPH_SCHEMA.md), dual-write from services, backfill migration (Phase B). |
| R-05 | **Embeddings placeholder blocks all semantic features** | 14-line fake-vector service; pgvector+Qdrant provisioned, unused | Memory retrieval, related-notes, agent context packs all blocked | Wire Ollama embed model via model-runtime provider path; pgvector column on `object_chunks`; honest degradation when model absent (Phase B). |
| R-06 | **Obsidian import permanently dry-run; no sync loop** | `obsidian_import` raises 409 on execute | "Deep Obsidian integration" is one-way file drops | Implement vault indexer + frontmatter schema + 3-way merge using existing sync-engine conflict math (Phase D, OBSIDIAN_INTEGRATION_SPEC). |
| R-07 | **Device registration without pairing enforcement + CORS `*` w/ credentials** | gateway register endpoint; every service CORS config | On any non-tailnet exposure, arbitrary device enrollment | Require pairing code (table exists) when `AUTH_REQUIRED=true`; restrict CORS to configured origins (Phase A). |
| R-08 | **Offline queue on localStorage** | offline-queue.ts | Data loss >5MB, plaintext captures at rest, no causal ordering | Move to localforage/IndexedDB, per-entity ordering keys reusing vector-clock ids, encrypt-at-rest option via WebCrypto (Phase E). |
| R-09 | **Coding-agent safety is prompt-side, not execution-side** | regex prompt filter; runner executes whatever Claude Code does inside worktree | Prompt filters are bypassable; blast radius = worktree + network | Execution-side policy: tool allowlist config for Claude Code, `--allowedTools`, no-network default, diff-size caps, mandatory approval gate before merge (Phase F, AGENTIC_HARNESS_SPEC). |
| R-10 | **Backups are local-only and unencrypted; restore drill not scheduled** | backup.sh; no rclone anywhere; remote_backup_uploads unwired | Single-disk failure loses everything | rclone template + age encryption + manifest verification + monthly drill automation (Phase E, BACKUP_RESTORE_SPEC). |

## P2

| ID | Risk | Evidence | Impact | Mitigation |
|---|---|---|---|---|
| R-11 | Services without integration tests against real Postgres | unit tests mock/skip DB; no testcontainers | SQL drift undetected until runtime | Add compose-based integration lane in CI (`pytest -m integration`), smoke per service. |
| R-12 | Intelligence-service untested (440 LOC) | no tests dir | Regressions invisible | Add unit tests for source_policy + monitor run; wire into pyproject testpaths. |
| R-13 | Static/demo UI data in Big Picture module blurbs & MetricCard usage | static copy in `providers/manifests.ts`, bigpicture design file | Violates "no decorative widgets" doctrine if shipped as-is | Bind badges to live health/queue endpoints or remove (Phase C/G). |
| R-14 | Sync attachment flow (MinIO) weakly tested | attachments endpoints; few tests | Mobile photo capture unreliable | Vertical-slice test: upload → sync → restore (Phase E). |
| R-15 | n8n/Twilio live bridges unverified | bridge code; live tests require secrets | Automation actions may silently no-op | Keep dry-run default; add `tests/live` gated smokes + doctor checks. |
| R-16 | 30 flat routes, ops pages in user nav | routes.ts | Cognitive overload; daily-driver friction | IA regroup into 13 surfaces + /ops area (UX spec, Phase C). |
| R-17 | Mobile shell lacks share-target & native capture | capacitor config only | "Capture anything" fails on phone | Android share-target + quick-capture activity (Phase E). |
| R-18 | Desktop shell has no local capabilities | boilerplate Tauri | Vault access, global hotkey, tray capture missing | Tauri commands: vault FS bridge (scoped), global shortcut, tray (Phase E). |
| R-19 | Command bus thin (2 tests) while being the security choke point | command-bus 236 LOC | Approval bypass bugs would be invisible | Expand tests: signature verification, template allowlist, approval state machine. |
| R-20 | Generated artifacts shipped in archive | dist/.quasar/node_modules in zip | Bloated, hygiene test fails | `git archive` packaging + hygiene test in CI. |

## P3

| ID | Risk | Mitigation |
|---|---|---|
| R-21 | Op-log text CRDT won't scale to real notes | Planned upgrade path exists; adopt Yjs/Automerge for note bodies when Obsidian sync lands. |
| R-22 | Qdrant + pgvector both provisioned (two vector stores) | Pick pgvector as source of truth for v1; drop Qdrant from default profile. |
| R-23 | admin-console app is empty | Delete or fold into /ops surface. |
| R-24 | Study SRS algorithm naive | Adopt FSRS (free spaced repetition scheduler) — pure-python, testable. |
| R-25 | Docs sprawl (26 phase docs) | Keep as history; new canonical docs (this set) supersede; add index. |
