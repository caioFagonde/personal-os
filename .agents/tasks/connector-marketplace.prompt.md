You are the connector-marketplace worker for Personal OS.

Read CLAUDE.md and SKILLS.md. Obey all security rules.

Task:
Build a modular connector marketplace / install-connect UX.

Do not read .env or secrets.

Implement:
- Marketplace route/page if missing
- Improve ConnectorsPage if needed
- Provider card component if useful
- manifests/config metadata for:
  Google, Microsoft, Twilio, ntfy, Tailscale, AWS, Azure, Google Cloud, GitHub, Claude Code, Ollama, Qdrant, SearXNG, n8n, MinIO, TileServer, model providers
- provider states:
  not installed, needs config, malformed config, ready to authorize, connected, degraded, dry-run only, failed
- cost/privacy metadata:
  local, private mesh, external provider, free-tier possible, paid external, verify pricing
- no raw backend errors in UI
- tests and docs

For AWS/Azure/GCP:
- no automatic paid provisioning
- no root credentials
- dry-run plan only
- explicit approval for future cloud actions

Acceptance:
- /marketplace exists or /connectors clearly serves as marketplace
- provider cards are readable and responsive
- config missing/malformed states are visible
- tests pass
- .agents/reports/connector-marketplace/report.md is written

Run:
python3 -m pytest tests -q
./scripts/check-secrets.sh
docker compose --env-file .env --profile full config
pnpm --dir apps/web build || true

Write report to:
.agents/reports/connector-marketplace/report.md
