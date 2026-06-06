# Personal OS — Sovereign Modular Control Plane

A production-oriented scaffold for a sovereign, modular, offline-first personal operating system.

## Default stack

- Apps: Quasar + Vue 3 + Pinia + Capacitor; Tauri desktop shell.
- Backend: FastAPI services.
- Data: PostgreSQL 16 + PostGIS + pgvector.
- Eventing: NATS JetStream.
- Object storage: MinIO.
- Sync: append-only sync log, entity versions, device identity, conflict-aware merges.
- Optional: Qdrant, Ollama, TileServer GL, n8n, ntfy, SearXNG, Prometheus/Grafana/Loki.
- Private networking: Tailscale-compatible sidecar profile.

## First-run

```bash
cp .env.example .env
./scripts/bootstrap.sh
```

Then open:

- API gateway: http://localhost:8080
- Sync engine: http://localhost:8081
- Command bus: http://localhost:8082
- MinIO console: http://localhost:9001
- NATS monitor: http://localhost:8222

## Safety posture

This scaffold intentionally excludes credentials, hardcoded tokens, credential extraction, offensive scanning, daemon persistence, and unauthenticated remote shell execution. Remote commands are mediated through signed requests, allowlisted templates, scopes, approvals, and audit logs.
