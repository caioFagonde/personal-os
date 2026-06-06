# Tailscale mesh design

Use the `mesh` Compose profile only after creating a least-privilege auth key. Prefer ephemeral keys for development and tagged reusable keys for permanent nodes.

Recommended ACL posture:

- phone may reach api-gateway, sync-engine, command-bus, ntfy, and web ports only.
- phone may not reach Postgres, MinIO internals, Docker socket, or host shell.
- desktop command agent registers as a trusted device and only executes allowlisted command templates after approval.
