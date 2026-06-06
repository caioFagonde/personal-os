# Phase 9.1 — CI Stabilization and Twilio Messaging Option

This patch stabilizes the GitHub Actions pipeline after the Phase 8/9 expansion.

## Fixed CI classes

1. **Node/pnpm workflows**
   - Removed `actions/setup-node` pnpm cache assumptions because the generated scaffold does not commit a `pnpm-lock.yaml` yet.
   - Set Node 24 for all Node workflows.
   - Added `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` to reduce Node 20 deprecation risk.
   - Standardized installs to `pnpm install --frozen-lockfile=false` until the project commits a lockfile.

2. **Compose profile contracts**
   - Enabled shared infrastructure services in every profile that depends on them.
   - Added a scaffold test that validates each service dependency is active inside every profile that activates the dependent service.

3. **Migration replay/smoke test**
   - Phase 8 now adds the `modules.storage_tables` column before inserting the Digital Twin module record.

4. **Python service imports**
   - Service-local coverage workflows now run with `PYTHONPATH=.` so `from app...` imports are stable under GitHub Actions pytest root discovery.

5. **Tauri tests**
   - Pure Rust desktop logic was moved into `src/lib.rs`.
   - CI runs `cargo test --lib`, avoiding accidental compilation of the full Tauri runtime macro during unit tests.

## Twilio WhatsApp option

The capture/delegation service now supports three WhatsApp provider modes:

- `WHATSAPP_PROVIDER=cloud_api` — default Meta WhatsApp Cloud API route.
- `WHATSAPP_PROVIDER=twilio_sandbox` — Twilio Sandbox prototyping route.
- `WHATSAPP_PROVIDER=twilio` — Twilio production WhatsApp sender route.

Secrets and personal phone numbers must remain in `.env` or `.env.local`; they are not committed to source.

Required Twilio placeholders:

```env
WHATSAPP_PROVIDER=twilio_sandbox
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_MESSAGING_SERVICE_SID=
```

For Brazil numbers, use E.164 format: `+55` + area code + number, with no spaces or punctuation.
