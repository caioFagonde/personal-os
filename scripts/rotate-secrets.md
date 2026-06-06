# Credential rotation checklist

Treat every credential found in old annexed projects as compromised.

1. Revoke exposed Google API keys in Google Cloud Console.
2. Revoke exposed Gemini/Anthropic/OpenAI keys from their provider dashboards.
3. Rotate all Postgres, SurrealDB, MinIO, n8n, ntfy, SMTP, and admin passwords.
4. Delete old `.env`, `.env.local`, generated token files, OAuth refresh-token caches, and SQLite prototype databases from working trees.
5. Run `./scripts/check-secrets.sh` and provider-side secret scanning before any commit.
6. Recreate `.env` from `.env.example` using `python3 scripts/generate-env.py .env`.
7. Re-authorize Google/Microsoft accounts only through OAuth flows.
8. Verify `cloud_tokens.encrypted_token` contains encrypted payloads only; never plaintext refresh tokens.
9. Rotate Tailscale auth keys; prefer ephemeral or tagged reusable keys with least privilege.
10. Record rotation in `audit_log` with `action='credential.rotated'`, excluding secret values.
