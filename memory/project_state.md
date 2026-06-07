---
name: project-state
description: Personal OS / Nexus Core current phase, what has been fixed, what is known to work
metadata:
  type: project
---

Personal OS is a sovereign modular personal OS at v0.7.0-alpha, targeting v0.1 daily-driver quality. It's a Docker Compose monorepo: FastAPI services + Quasar/Vue 3 web + Capacitor mobile + Tauri desktop.

**Why:** Building toward daily use by the owner on PC + Android phone.

**How to apply:** When suggesting next steps, prioritize reliability and daily-driver UX over new features.

## What has been completed (Phases 1-15)

- Core services: api-gateway (8080), sync-engine (8081), command-bus (8082), module-service (8083), connector-service (8094), model-runtime (8095), coding-agent-service (8096)
- All 101+ scaffold tests pass
- Ruff lint clean on all service source files
- Docker Compose full-profile validates cleanly
- Shell scripts all pass syntax check

## Phase 15 changes (2026-06-07)

- `scripts/doctor-full.sh` — new comprehensive health check (Compose config, ports, endpoints, auth smoke, connector status, restart-loop detection, URL summary)
- `Makefile` — added `make doctor-full` target
- `scripts/bootstrap.sh` — TTY-gated interactive auth (no longer blocks CI), better summary with grouped URL output
- `apps/web/src/pages/CommandCenterPage.vue` — restructured with Today/Knowledge/Operations/Development sections, quick-action strip, live task-inbox count, safe() API wrappers, load-error banner
- `apps/web/src/pages/CapturePage.vue` — error handling, keyboard shortcut (Ctrl+Enter), template buttons, hero-panel layout
- `apps/web/src/pages/TasksPage.vue` — error handling, new-task form with priority selector, filter tabs (inbox/delegated/all), complete action
- `apps/web/src/pages/StudyCompanionPage.vue` — error handling, structured result panel (no more raw JSON dump), atoms/queries/OCR text display
- `apps/web/src/pages/ConnectorsPage.vue` — setup instructions per provider, ntfy subscription help, Tailscale IP display, structured result rendering
- `apps/web/src/components/BottomNav.vue` — swapped coding-agent → study-companion for mobile bottom-5 (daily-driver choice)
- `apps/web/src/css/app.scss` — fixed mobile grid overflow with min(100%, 260px)
- `tests/test_bootstrap_invariants.py` — 17 new tests for bootstrap script invariants
- `tests/test_phase15_ux_polish.py` — 35 new tests for UX contracts, CSS, mobile layout, page safety

## Test baseline

154 passed, 2 skipped — as of 2026-06-07

## Known remaining gaps

- pnpm not available in this shell environment — frontend type-check and build cannot be verified locally
- `make up` requires Docker with data volumes — not verified in this session
- OAuth redirect URIs use intentional path-doubling through the gateway proxy (correct by design)
- `CODING_AGENT_EXECUTE=false` is safe default — no actual Claude Code runs without explicit env override
