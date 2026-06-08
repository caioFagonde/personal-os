You are the intelligence-layer worker for Personal OS.

Read CLAUDE.md and SKILLS.md. Obey all security rules.

Task:
Implement an ethical Intelligence Center for public OSINT/news/RSS/SearXNG keyword monitoring and daily briefings.

Hard boundaries:
- No unauthorized surveillance.
- No credential harvesting.
- No scraping private accounts unless explicitly connected through OAuth.
- No paywall bypassing.
- No offensive SIGINT tooling.
- No reading .env, secrets, data, backups, logs, credentials, tokens, or private keys.
- Do not implement anything that intercepts communications.

Allowed:
- public news/RSS/search
- user-configured sources
- SearXNG queries
- user-authorized connectors later
- source attribution
- save-to-note/task/research flow where safe

Implement:
- modules/intelligence/manifest.yaml
- service skeleton or endpoints if appropriate
- database migration if needed and idempotent
- /intelligence page
- source/monitor/finding/briefing concepts
- structured errors
- docs/intelligence.md
- tests and smoke contracts

Acceptance:
- /intelligence route exists and renders
- source registry/monitor UI exists
- public-source/search/RSS model is clear
- no unsafe surveillance language or code
- tests pass
- .agents/reports/intelligence-layer/report.md is written

Run:
python3 -m pytest tests -q
./scripts/check-secrets.sh
docker compose --env-file .env --profile full config

Write report to:
.agents/reports/intelligence-layer/report.md
