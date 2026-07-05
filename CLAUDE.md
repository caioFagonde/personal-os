# CLAUDE.md — Personal OS / Nexus Core

## Mission

This repository implements a sovereign, modular, local-first personal operating system named Personal OS / Nexus Core.

It is not a generic dashboard. It is a control-plane plus specialized-module ecosystem for:

* capture
* tasks
* delegation
* study companion
* Zettelkasten
* research/PDF ingestion
* geospatial memory
* AR memory
* automation
* notifications
* connectors
* model runtime
* digital twin
* coding-agent workflows
* mobile/desktop/web access
* encrypted continuity and backup

The product must work on the user's PC and phone with a one-script install path, robust sync, and a premium mobile/desktop UX.

## Non-negotiable rules

Never read, print, edit, infer, or commit secrets.

Forbidden paths:

* `.env`
* `.env.*`
* `secrets/`
* `.private/`
* `data/`
* `backups/`
* `logs/`
* `node_modules/`
* `.git/`
* token files
* credentials files
* private keys
* OAuth client secrets

If a task requires secrets, produce instructions for the user instead of reading them.

Do not implement arbitrary unauthenticated remote shell execution.

Do not make destructive changes without explicit user approval.

Do not run:

* `sudo`
* `rm -rf /`
* `rm -rf ~`
* `docker volume rm`
* `docker system prune`
* force-push
* credential export
* secret scanning that prints secret values

## Architecture

The stack is a Docker Compose monorepo.

Primary technologies:

* Web/mobile shell: Quasar, Vue 3, Pinia, Capacitor
* Desktop shell: Tauri
* Backend: FastAPI
* Database: PostgreSQL + PostGIS + pgvector
* Object storage: MinIO
* Eventing: NATS JetStream
* Notifications: ntfy
* Automation: n8n plus internal automation service
* Research: SearXNG, PDF ingestion, local search
* Model runtime: OCR/object/audio fallback runtime
* Sync: local-first entity log, vector clocks, conflict resolution
* Connectors: Google, Microsoft, Twilio, ntfy, Tailscale, backup upload
* Coding agent: Claude Code through approval-gated command/coding-agent service

## Important directories

* `apps/web` — Quasar web shell and main UI
* `apps/mobile` — Capacitor mobile shell
* `apps/desktop` — Tauri desktop shell
* `services/api-gateway` — auth, proxy, module registry
* `services/sync-engine` — local-first sync and conflicts
* `services/connector-service` — OAuth, outbox, Twilio, ntfy, backups
* `services/coding-agent-service` — Claude Code job runner
* `services/module-service` — study/zettel/geospatial/AR APIs
* `services/capture-service` — capture, tasks, delegation
* `services/study-companion-service` — learning atoms, analog capture, retention
* `services/research-service` — metadata/PDF ingestion
* `services/model-runtime` — OCR/vision/audio runtime
* `infra/postgres/migrations` — idempotent migrations
* `scripts` — install, doctor, backup, certification
* `modules` — module manifests
* `tests` — scaffold and cross-service regression tests

## Bootstrap expectations

The command:

```bash
./scripts/bootstrap.sh --full --open
```

should:

1. generate `.env` if missing
2. create runtime directories
3. start Docker Compose profiles
4. run all migrations idempotently
5. seed modules
6. pass health checks
7. pass auth smoke test
8. open onboarding
9. never crash on optional missing tools
10. print actionable diagnostics

If bootstrap fails, fix the root cause and add a regression test.

## Migration standards

Every migration must be idempotent.

Use:

* `CREATE TABLE IF NOT EXISTS`
* `CREATE INDEX IF NOT EXISTS`
* `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
* `ON CONFLICT DO UPDATE`
* valid JSONB literals through `to_jsonb(...)` where needed

Avoid:

* inline `UNIQUE(...)` constraints using expressions like `COALESCE(...)`
* inserting into columns not guaranteed to exist
* non-idempotent schema operations
* bare text cast to JSONB when text is not valid JSON

## Docker Compose standards

Compose must parse under:

```bash
docker compose --env-file .env --profile full config
```

Rules:

* no brittle healthchecks relying on missing binaries inside upstream containers
* optional services must not block core boot unnecessarily
* no shared schema collisions with third-party services such as n8n
* bind mounts must not collide with read-only parent mounts
* web build context must be monorepo root, not isolated `apps/web`
* all service ports must avoid conflicts

## Web UX standards

The UI must be premium, readable, responsive, and operational.

Desktop:

* left navigation
* command center
* dense operational cards
* visible health/status
* no unreadable low-contrast surfaces
* no horizontal overflow unless intentional

Mobile:

* bottom navigation
* large tap targets
* capture-first workflow
* sync status visible
* offline queue accessible
* no broken cards or clipped content

Global visual standards:

* dark theme must be first-class
* `q-card`, `q-table`, `q-field`, menus, dialogs, buttons, and panels must be styled
* primary actions obvious
* destructive actions require confirmation
* error messages actionable

## Connector standards

Connectors must never expose raw backend failures to the UI.

Google/Microsoft:

* if OAuth app config is missing, return structured `409` with required env vars
* if configured, open consent flow
* store encrypted refresh tokens server-side
* do not store user refresh tokens in source
* provide disconnect/revoke/test states

Twilio:

* support dry-run
* support sandbox and production modes
* do not send unless explicitly enabled
* validate E.164 numbers
* never print auth token

ntfy:

* support dry-run
* support private/random topics
* show mobile subscription instructions

Tailscale:

* detect CLI state
* show auth-required state
* never expose auth keys

## Coding-agent standards

The coding agent must be safe by default.

Default:

```env
CODING_AGENT_EXECUTE=false
```

Execution requires:

* explicit job creation
* approval gate
* allowed repository root
* isolated git worktree
* secret-scrubbed environment
* logs and artifacts
* test output capture
* no automatic commit/push/deploy

The coding agent may run Claude Code only through an allowlisted command template.

Never allow arbitrary raw shell from mobile.

## Test commands

Always prefer these checks:

```bash
python3 -m pytest tests -q
./scripts/check-secrets.sh
bash -n scripts/*.sh
docker compose --env-file .env --profile full config
```

If dependencies are installed:

```bash
pnpm --dir apps/web test
pnpm --dir apps/web build
pnpm --dir apps/mobile validate
pnpm --dir apps/desktop validate
```

If Docker is available:

```bash
./scripts/bootstrap.sh --full --open
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=120 web api-gateway connector-service coding-agent-service
```

## Required behavior

Before editing:

1. inspect relevant files
2. state the diagnosis
3. list files to touch
4. define tests
5. identify risks

After editing:

1. summarize changed files
2. explain each fix
3. report tests run
4. list remaining risks
5. provide exact next command

## Product north star

The initial version is complete when:

* fresh clone installs with one script
* web UI opens reliably
* command center works
* phone can connect over Tailscale
* capture/tasks/Zettelkasten/study companion work
* connector onboarding is clear
* sync/conflicts/offline queue are visible
* backup/restore path works
* Claude Code can safely work through the coding-agent layer
* tests and CI catch regressions

# CLAUDE.md — Personal OS / Nexus Prime

Before doing anything, read NEW_AGENT_HANDOFF.md — it is the source of truth
for current state, doctrine, and next phase. Specs live in docs/.

Hard rules (non-negotiable):
- Never read, print, edit, or commit .env, .env.*, secrets/, .private/,
  data/, backups/, logs/, tokens, or keys.
- No sudo, no docker volume removal, no force-push, no broad rm -rf.
- No mocked implementations. Placeholders must be labeled (dry_run,
  demo:true, placeholder) and tested as such.
- Update contract tests in the same commit as any behavior change they
  guard. Never delete a contract test to make it pass.
- Every phase updates NEW_AGENT_HANDOFF.md and the docs/ living documents.

Verification before claiming done:
- python3 -m pytest tests/ --ignore=tests/live -q   (must be 100%)
- per-service: cd services/<name> && python3 -m pytest tests -q
- bash scripts/check-secrets.sh
- pnpm --dir apps/web test && pnpm --dir apps/web exec vue-tsc --noEmit
