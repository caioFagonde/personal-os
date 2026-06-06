# Security

Non-negotiables:

- No committed `.env`, refresh tokens, private keys, local databases, runtime data, or generated artifacts.
- No unauthenticated remote shell.
- No offensive scanning or credential extraction.
- No Docker socket exposure to app services.
- Privileged containers are prohibited in the core profile.
- Command bus accepts only signed, scoped, allowlisted command templates.
- Human approvals are required for destructive, external-send, cloud-write, and local-code-execution requests.
- Every external side effect is written to `audit_log`.

Use `scripts/rotate-secrets.md` before migrating any old prototype credentials.
