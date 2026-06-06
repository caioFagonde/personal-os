# Phase 10 — Connector Onboarding and Continuity

Phase 10 turns setup into an operator-facing onboarding flow:

- Google OAuth start/callback with offline access and encrypted refresh-token storage.
- Microsoft OAuth start/callback with `offline_access` and encrypted refresh-token storage.
- Twilio WhatsApp dry-run/test support.
- ntfy dry-run/test support.
- Tailscale status detection and setup hints.
- Message outbox draining with safe dry-run mode by default.
- Backup manifest creation and restore-drill metadata.
- Short-lived device pairing codes.
- Web pages for onboarding, connectors, backup/restore, sync health, and device pairing.

## One-script install

```bash
cp .env.example .env
python3 scripts/generate-env.py .env
./scripts/bootstrap.sh --full --open
```

The script starts core, apps, automation, research, AI, connectors, and observability profiles. It opens `/onboarding` when `xdg-open` is available.

## OAuth behavior

OAuth flows cannot be silent. The connector service returns an authorization URL. The UI opens it. After consent, provider callbacks enter through:

- `/api/proxy/connectors/api/connectors/google/callback`
- `/api/proxy/connectors/api/connectors/microsoft/callback`

Refresh tokens are encrypted with `TOKEN_ENCRYPTION_KEY` and stored in `cloud_tokens`.

## Messaging behavior

By default, connector tests are dry-runs. Set `SEND_CONNECTOR_TESTS=true` or pass `execute=true` to actually send messages.

## Backup behavior

The backup endpoint creates a deterministic manifest bundle and refuses to include `.env`.

## Local tests

```bash
make test-phase10
python3 -m pytest tests -q
./scripts/check-secrets.sh
```
