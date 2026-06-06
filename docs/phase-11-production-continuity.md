# Phase 11 — Production Connector Worker and Continuity

Phase 11 turns connector onboarding into operational delivery.

## Implemented

- Durable connector worker with manual tick endpoint and optional background loop.
- Real Twilio WhatsApp send path through Twilio REST API.
- Real Gmail send path using OAuth refresh tokens and `users.messages.send`.
- Real Microsoft Graph mail send path using OAuth refresh tokens and `sendMail`.
- ntfy delivery worker for notification deliveries and queued messages.
- Google Drive and OneDrive backup upload after local backup export.
- QR device-pairing interface and SVG QR endpoint.
- Conflict-resolution UI at `/conflicts`.
- Offline queue UI at `/offline-queue`.
- Connector worker UI at `/connector-worker`.
- Interactive bootstrap handoff for Tailscale, ADB, and OAuth consent windows.
- Restore-drill script and GitHub Actions workflow.

## Safety defaults

`CONNECTOR_WORKER_EXECUTE=false` by default. This means the worker can run without sending external messages. Set it to `true` only after connector tests pass.

```env
CONNECTOR_WORKER_ENABLED=true
CONNECTOR_WORKER_EXECUTE=false
CONNECTOR_WORKER_INTERVAL_SECONDS=20
```

For real delivery:

```env
CONNECTOR_WORKER_EXECUTE=true
SEND_CONNECTOR_TESTS=true
```

## Manual tick

```bash
curl -X POST http://localhost:8080/api/proxy/connectors/api/connectors/worker/tick \
  -H 'content-type: application/json' \
  -d '{"execute":false,"limit":25}'
```

## Remote backup upload

Google Drive:

```bash
curl -X POST http://localhost:8080/api/proxy/connectors/api/connectors/backup/export-upload \
  -H 'content-type: application/json' \
  -d '{"provider":"google","include_runtime":false}'
```

OneDrive:

```bash
curl -X POST http://localhost:8080/api/proxy/connectors/api/connectors/backup/export-upload \
  -H 'content-type: application/json' \
  -d '{"provider":"microsoft","include_runtime":false}'
```

## Restore drill

```bash
make restore-drill
```

The CI restore drill boots the stack, applies migrations, inserts sample continuity data, exports a backup manifest, and verifies sample records.

## Unavoidable authorization prompts

These cannot be silently automated:

- Google OAuth consent.
- Microsoft OAuth consent.
- Tailscale account/device authorization if no auth key is configured.
- Android ADB RSA authorization prompt.
- Mobile notification permission.
- Twilio WhatsApp sandbox join flow.

The bootstrap script opens or waits for these where possible, then continues.
