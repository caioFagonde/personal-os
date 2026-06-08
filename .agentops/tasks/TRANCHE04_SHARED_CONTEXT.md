# Personal OS Tranche 04 Shared Context

You are working on Personal OS, a sovereign local-first modular operating substrate for personal productivity, research, study, geospatial memory, automation, mobile continuity, and agentic development.

This tranche has two simultaneous goals:

1. Full continuity implementation:
   - mobile offline queue
   - private phone pairing
   - Tailscale/private URL setup
   - ntfy notification setup
   - portable/capsule mode
   - AgentOps console inside Personal OS

2. UI/UX refactor:
   - Big Picture / cockpit shell
   - floating glass cards
   - horizontal carousels
   - mobile-first command deck
   - clean readable typography
   - no broken Quasar/icon artifacts
   - no white-on-white UI

## Visual references

Read:
- .agentops/examples/GENERATED_INDEX.md
- .agentops/examples/markdown/tranche04-ui-reference.md
- relevant files under .agentops/examples/images/

Use the images as inspiration only. Do not copy third-party copyrighted imagery or branding. Generate local abstract gradients, SVG backgrounds, glass cards, and system-native visual language.

## Hard constraints

- Do not read or modify .env, .env.*, secrets, private keys, credentials, tokens, backups, logs, or personal data.
- Do not weaken security.
- Do not add unauthenticated remote execution.
- Do not send real notifications, email, WhatsApp, or cloud operations during tests.
- Use dry-run/test routes for side effects.
- Do not remove meaningful tests to pass CI.
- Do not break bootstrap.
- Do not introduce public exposure.
- Do not create paid cloud resources.

## UX rules

Every user-facing flow must have:
- loading state
- empty state
- error state
- success state where applicable
- clear next action
- configuration guidance if setup is missing
- no raw stack traces
- responsive desktop/mobile layout

## Engineering rules

- Prefer small reusable components.
- Add or update tests.
- Keep module boundaries clear.
- Use typed interfaces where possible.
- Keep migrations idempotent.
- Use structured errors.
- Write a report at the required path.

## Required final checks

Run if available:
- scripts/agents/run-pytest.sh tests -q
- ./scripts/check-secrets.sh
- pnpm --dir apps/web build
- docker compose --env-file .env --profile full config >/tmp/personal-os-full.yml
