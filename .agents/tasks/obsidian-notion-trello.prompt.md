You are the Obsidian/Notion/Trello connector worker for Personal OS.

Read CLAUDE.md and SKILLS.md. Obey all security rules.

Task:
Add safe connector skeletons and UX/contracts for Obsidian, Notion, and Trello.

Do not read .env, secrets, credentials, tokens, data, backups, or logs.
Do not store secrets in frontend localStorage.
Do not perform real external writes by default.

Implement:
Obsidian:
- vault path config
- path validation
- dry-run export/import contract
- safe writes only inside configured vault
- Markdown/Zettelkasten compatibility docs

Notion:
- token/database/page config metadata
- dry-run page creation/export contract
- structured missing config errors

Trello:
- API key/token/board/list config metadata
- dry-run card creation contract
- structured missing config errors

Also:
- UI setup cards
- backend provider status/dry-run endpoints if appropriate
- tests
- docs/connectors.md updates

Acceptance:
- Obsidian/Notion/Trello appear in connector/marketplace UI
- missing config is structured
- dry-run paths exist
- tests pass
- .agents/reports/obsidian-notion-trello/report.md is written

Run:
python3 -m pytest tests -q
./scripts/check-secrets.sh
docker compose --env-file .env --profile full config

Write report to:
.agents/reports/obsidian-notion-trello/report.md
