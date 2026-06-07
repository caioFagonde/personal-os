# SKILLS.md — Personal OS Claude Code Skill Catalog

This file defines repeatable skill protocols for improving Personal OS. Use these protocols when asked to diagnose, repair, extend, or polish the system.

## Skill: bootstrap-doctor

Use when bootstrap, Docker Compose, migrations, health checks, or service startup fail.

Protocol:

1. Inspect:

   * `scripts/bootstrap.sh`
   * `docker-compose.yml`
   * `.env.example`
   * `scripts/generate-env.py`
   * `infra/postgres/migrations/*.sql`
   * relevant service logs
2. Reproduce with the narrowest command possible.
3. Identify whether the failure is:

   * migration syntax
   * schema drift
   * bad Compose profile
   * healthcheck mismatch
   * port conflict
   * bad mount
   * missing env
   * service runtime exception
4. Patch root cause.
5. Add regression test in `tests/`.
6. Run:

   * `python3 -m pytest tests -q`
   * `./scripts/check-secrets.sh`
   * `docker compose --env-file .env --profile full config`

Never delete volumes unless user explicitly requests a destructive reset.

## Skill: migration-surgeon

Use when PostgreSQL migrations fail.

Rules:

* migrations must be idempotent
* never assume a column exists unless the migration creates it or guards it
* prefer `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
* prefer `CREATE INDEX IF NOT EXISTS`
* use `to_jsonb('text'::text)` for JSONB strings
* use expression indexes instead of inline unique constraints with expressions
* preserve existing data

Output must include:

* failing SQL
* reason it failed
* corrected SQL
* regression test

## Skill: full-stack-runtime-fixer

Use when containers restart or optional services fail.

Check:

* `docker compose logs --tail=200 <service>`
* service health endpoint
* mounts
* read-only filesystem issues
* third-party service defaults
* schema collisions
* upstream image changes
* deprecated config keys

Known fragile services:

* web / Quasar
* n8n
* SearXNG
* TileServer GL
* Grafana
* OpenTelemetry collector
* Qdrant
* Ollama

Patch defaults so `--profile full` does not collapse because of optional service brittleness.

## Skill: quasar-ux-repair

Use when the UI is blank, unreadable, broken, low-contrast, or non-responsive.

Inspect:

* `apps/web/index.html`
* `apps/web/quasar.config.ts`
* `apps/web/src/router/index.ts`
* `apps/web/src/router/routes.ts`
* `apps/web/src/App.vue`
* `apps/web/src/css/app.scss`
* relevant page/component

Checklist:

* Quasar entrypoint valid
* no manual `<div id="q-app"></div>` in `index.html`
* router index exists
* boot files export `boot(...)`
* dark surfaces readable
* cards/tables/forms styled
* desktop and mobile layouts sane
* no unhandled Promise errors in UI
* backend errors shown as actionable messages

Add or update UI regression tests when possible.

## Skill: command-center-designer

Use when improving the main dashboard.

The command center must expose:

* capture
* tasks
* study companion
* Zettelkasten
* research
* geospatial
* AR memory
* automation
* digital twin
* connectors
* coding agent
* sync health
* offline queue
* conflicts
* backup/restore
* certification/release

Each card should show:

* title
* one-sentence purpose
* status
* primary action
* secondary link
* pending count if available

Design goal:

A user should be able to open Personal OS on PC or phone and reach any important utility within two taps/clicks.

## Skill: connector-onboarding

Use when Google, Microsoft, Twilio, ntfy, Tailscale, or backup connectors fail.

Rules:

* no raw 500s in UI
* missing config returns structured 409
* UI must show required env vars
* OAuth should open browser automatically
* device-code fallback should be available when possible
* refresh tokens stored encrypted server-side
* `.env` stores app config only, not user tokens
* connector tests are dry-run by default
* real sends require explicit enable flags

Test:

* `/connectors` renders
* provider status loads
* missing config is readable
* configured provider returns authorization URL
* Twilio dry-run works
* ntfy dry-run works

## Skill: coding-agent-runner

Use when implementing or improving Claude Code remote execution.

Rules:

* default dry-run
* approval required before execution
* no raw shell from remote clients
* allowed repo root only
* create isolated worktree
* scrub secrets from environment
* capture stdout/stderr
* capture diff summary
* run tests
* notify user
* never auto-push
* never deploy without explicit approval

A safe Claude job must include:

* objective
* target repo
* allowed files/directories
* disallowed files/directories
* test command
* completion criteria
* approval requirement

## Skill: mobile-sync-certifier

Use when validating phone/mobile workflows.

Check:

* Tailscale access
* API URL
* device registration
* offline queue
* capture while offline
* sync after reconnect
* conflict visibility
* ntfy subscription
* mobile layout

Never assume USB/ADB is authorized; prompt and wait.

## Skill: security-hardening

Use for any change touching auth, commands, connectors, or secrets.

Checklist:

* no secrets in source
* no secret printing
* no destructive unauthenticated action
* no arbitrary remote shell
* approval gates preserved
* audit logs written
* tokens encrypted
* least privilege scopes
* tests cover failure states

Always run:

```bash
./scripts/check-secrets.sh
python3 -m pytest tests -q
```

## Skill: test-and-release-gate

Use before declaring work complete.

Run available checks:

```bash
python3 -m pytest tests -q
./scripts/check-secrets.sh
bash -n scripts/*.sh
docker compose --env-file .env --profile full config
```

If Node is available:

```bash
pnpm --dir apps/web test
pnpm --dir apps/web build
```

If Docker is available:

```bash
./scripts/bootstrap.sh --full --open
docker compose --env-file .env ps
```

Completion report must include:

* passed tests
* skipped tests
* unavailable tools
* known risks
* next command for user
