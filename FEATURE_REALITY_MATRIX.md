# FEATURE_REALITY_MATRIX.md

Classification legend:
- **REAL+TESTED** — working code path with behavioral tests
- **REAL/WEAK-TEST** — working code, thin or contract-only tests
- **SCAFFOLD** — explicit interface/placeholder, honestly labeled
- **UI-ONLY** — page exists, backend absent or not wired for the promised behavior
- **BROKEN** — code exists but contradicts its own tests/contracts
- **MISSING** — not present
- **GEN-ARTIFACT** — build output, ignore
- **UNCLEAR** — cannot verify from archive

| # | Feature | Classification | Evidence & notes |
|---|---|---|---|
| 1 | Capture (text → capture_items → tasks) | **REAL+TESTED** | `capture-service` 18 tests: parser, frontmatter, fingerprints, delegation msgs; `tests/test_capture_e2e.py`, `test_v1_capture_hardening.py`. Gaps: no voice, screenshot, file, or URL capture pipelines (text only). |
| 2 | Tasks (CRUD, status, priority, delegation) | **REAL+TESTED** | tasks/task_events tables, TaskPatch, filter tabs in TasksPage; delegation via contacts + message_outbox. Delegation delivery = dry-run/outbox only (no live Twilio send verified). |
| 3 | Zettelkasten (notes, links) | **REAL/WEAK-TEST** | module-service notes + zettel_links APIs + migration; only contract-level tests, no link-graph behavioral tests. |
| 4 | Study (items/sessions/flashcards) | **REAL/WEAK-TEST** | module-service APIs + migration; SRS logic minimal. |
| 5 | Study companion (retention, analog capture, routines) | **REAL+TESTED** | 13 tests over retention/analog/routines; OCR path depends on model-runtime heuristic mode. |
| 6 | Research / PDF ingestion | **REAL+TESTED** | 27 tests: pdf_ingest, chunking, acquisition adapters, normalization, source policy. Embedding/semantic search over chunks = missing (blocked on embeddings service). |
| 7 | Geospatial | **REAL/WEAK-TEST** | geospatial_memories, map_datasets/import_jobs, routing_profiles tables; module-service endpoints; tileserver in compose. No behavioral tests on PostGIS queries. |
| 8 | AR memory | **SCAFFOLD**/REAL-MATH | `ar_math.py` tested (anchor math real); ar_anchors tables exist; no device pipeline; page is thin. |
| 9 | Digital twin | **REAL+TESTED** (logic) | 23 tests: ontology, timeline, recommender, privacy. But inputs are manual — no automatic signal ingestion from other modules yet, so "twin" is a well-tested engine with sparse fuel. |
| 10 | Automation (workflows, DAG, scheduler, approvals) | **REAL+TESTED** | 25 tests; policy gates + approvals + outbox. Action library is small; n8n bridge unverified live. |
| 11 | Connectors: OAuth core (google/microsoft) | **REAL/WEAK-TEST** | oauth.py + encrypted token storage + tests (test_oauth.py); live flows untestable in sandbox. |
| 12 | Connector: Obsidian | **REAL (export) / SCAFFOLD (import)** | Export writes real markdown, vault-contained, create-only. Import returns dry-run always (`409` on execute). No frontmatter schema, daily notes, backlinks, or bidirectional sync. |
| 13 | Connector: Notion | **SCAFFOLD** | Dry-run endpoints only, honest labels. |
| 14 | Connector: Trello | **SCAFFOLD** | Dry-run endpoints only. |
| 15 | Connectors: ntfy / Twilio / Tailscale | **REAL/WEAK-TEST** | Provider modules + worker + health checks; async provider tests fail in sandbox for plugin reasons only; live delivery unverified. |
| 16 | Model runtime | **SCAFFOLD+** (honest) | Real state machine, invocation logging, `demo:true` flags; heuristic OCR/detection paths exist; **no wired Ollama/whisper call path** despite ollama in compose. |
| 17 | Embeddings / vector search | **SCAFFOLD** (explicit) | 14-line placeholder returning deterministic fake vectors; labeled `mode: placeholder`. Qdrant + pgvector provisioned but unused. |
| 18 | Coding agent | **REAL+TESTED** (dry-run) / **UNCLEAR** (live) | Policy, worktrees, job persistence, Claude Code `-p` runner all real; live execution gated behind `CODING_AGENT_EXECUTE` and untested here. No approval UI round-trip test. |
| 19 | Sync engine (vector clocks, conflicts, CRDT) | **REAL+TESTED** | 12 tests incl. phase-2/4 conflict coverage. Attachment content flow via MinIO claimed, weakly tested. |
| 20 | Offline queue (web) | **REAL/WEAK-TEST + risky** | localStorage-backed queue + tests; fragile (5MB, plaintext, no backoff jitter, replay ordering per-item not causal). |
| 21 | Background sync | **REAL/WEAK-TEST** | background-sync.ts + test; policy primitive (interval), no network/battery awareness. |
| 22 | Mobile shell (Capacitor) | **SCAFFOLD+** | Config + runtime-policy + validators + preflight; no native project, no share-target, no verified APK pipeline in archive. |
| 23 | Desktop shell (Tauri) | **SCAFFOLD+** | Valid Tauri 2 config, CSP, validator script; no custom commands (no tray, no global hotkey, no local FS bridge for vault). |
| 24 | Backup/restore | **REAL/WEAK-TEST (local)** / **MISSING (remote)** | backup.sh (pg_dump+tar), restore.sh, restore-drill.sh, certify smokes, backup_manifests + remote_backup_uploads tables. No rclone/Drive template, no encryption, no scheduled job wiring. |
| 25 | Update pipeline | **REAL/WEAK-TEST** | update.sh, preflight, rollback, tests in test_backup_update_pipeline.py. |
| 26 | CI/CD | **MISSING from archive / UNCLEAR upstream** | No `.github/` in zip; 12+ tests assert workflows exist and fail. Treat as must-recreate. |
| 27 | Security/auth | **REAL+TESTED** (single-user) | Device JWT + refresh + rotation, service identity, command approvals, audit_log. Findings: CORS `*`, registration without pairing-code enforcement, PII defaults in capture-service (**P0**). |
| 28 | Observability | **REAL/WEAK-TEST** | OTEL collector, Prometheus, Grafana dashboards, service_health_snapshots; gateway observability.py tested. |
| 29 | Command Center page | **REAL/UI drift** | Rebuilt with Today/Knowledge/Ops sections + live counts, but **no longer the default route** — BigPictureHome is. Phase-14 contract test fails. Decide the canonical home. |
| 30 | Big Picture home | **UI-ONLY (new, untested)** | Carousel/hero console UI with module metadata; visually rich; not covered by any test; module "blurbs" are static copy. |
| 31 | Command palette | **UI-ONLY (stub)** | 44 lines; route jump list only; no actions, no capture, no search. |
| 32 | Connectors page (Marketplace rewrite) | **BROKEN vs contract** | New page dropped setup instructions/ntfy help/Tailscale IP that phase-15 tests assert. Either restore content or update contracts. |
| 33 | Conflict resolution / Sync health / Offline queue pages | **REAL/WEAK-TEST** | Wired to real endpoints; e2e offline-conflicts spec exists. |
| 34 | Onboarding / Device pairing pages | **REAL/WEAK-TEST** | pairing codes table + page; registration doesn't require pairing (gap). |
| 35 | Certification / Release center / Live stack / Initial-readiness pages | **REAL (ops)** | Belong in an "Operations" area, not primary user nav. |
| 36 | Intelligence center | **REAL/NO TESTS** | 440 LOC CRUD + monitors + briefings; zero tests; UI page exists. |
| 37 | Personal knowledge graph (unified) | **MISSING** | entities/entity_versions exist as spine but capture/tasks/research/twin do not register edges; no graph query API. |
| 38 | Agent harness (generic jobs/tools/skills/evals/memory) | **MISSING** | Only coding-agent vertical + automation DAG; no ToolRegistry, SkillRegistry, AgentMemory, EvalCase. |
| 39 | Voice capture / transcription | **MISSING** | No audio ingestion; whisper not wired. |
| 40 | Screenshot/file/URL capture | **MISSING** (attachments partial) | attachments table + MinIO exist; no capture UX or extraction pipeline. |
| 41 | People/contacts as graph objects | **REAL/WEAK-TEST** | contacts + contact_channels used by delegation only. |
| 42 | Goals | **REAL/WEAK-TEST** | digital_twin_goals table + twin APIs; not surfaced in Today/Focus UX. |
| 43 | Portfolio cases / repositories objects | **MISSING** | coding_agent tables reference repos by path only. |
| 44 | `apps/web/dist`, `.quasar`, `node_modules` in zip | **GEN-ARTIFACT** | Should be excluded from archives (its own test says so). |
