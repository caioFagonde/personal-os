# Connector contracts

Personal OS connectors are setup-first and dry-run by default. Provider credentials and secret values belong only in the connector service environment. The web UI displays required field names and status, but never stores connector secrets in browser storage.

## Common status and errors

`GET /api/connectors` lists marketplace providers, configuration metadata, capabilities, and setup status. `GET /api/connectors/{provider}/setup/status` returns the same contract for one provider.

Operations with missing setup return HTTP `409` with a structured detail:

```json
{
  "code": "connector_missing_configuration",
  "provider": "trello",
  "status": "needs_configuration",
  "missing_config": ["TRELLO_API_KEY", "TRELLO_API_TOKEN", "TRELLO_BOARD_ID", "TRELLO_LIST_ID"],
  "action": "configure_server_environment"
}
```

No configured values are returned by status or missing-configuration responses.

## Obsidian

Configure `OBSIDIAN_VAULT_PATH` as an absolute path to an existing vault directory.

- `POST /api/connectors/obsidian/export` validates a relative Markdown path and previews an export. It writes only when `execute=true`.
- `POST /api/connectors/obsidian/import` validates a relative Markdown path and previews an import. Import execution is intentionally unavailable in this skeleton.
- `POST /api/connectors/obsidian/path/validate` validates a proposed relative note path without reading or writing a note.
- Absolute paths, traversal outside the vault, symlink escapes, and non-Markdown extensions are rejected.
- The connector never writes outside the configured vault and refuses to overwrite an existing note.

Exports preserve plain Markdown. Obsidian-compatible `[[wikilinks]]`, standard Markdown links, `#tags`, YAML frontmatter, and embeds can remain in note content. For Zettelkasten workflows, use stable timestamp-prefixed filenames such as `Zettelkasten/202606081200 Connector contracts.md` and durable note IDs in frontmatter.

## Notion

Configuration metadata:

- `NOTION_API_TOKEN`: required server-side secret.
- `NOTION_DATABASE_ID`: optional default page-creation target.
- `NOTION_PAGE_ID`: optional default page target and export source.

At least one default database or page ID is required for provider readiness.

- `POST /api/connectors/notion/pages/dry-run` previews page creation.
- `POST /api/connectors/notion/export/dry-run` previews structured Markdown export.

These endpoints never call Notion or perform external writes. Passing `execute=true` returns a structured `409` dry-run-only response.

## Trello

Configuration metadata:

- `TRELLO_API_KEY`: required server-side secret.
- `TRELLO_API_TOKEN`: required server-side secret.
- `TRELLO_BOARD_ID`: required board target.
- `TRELLO_LIST_ID`: required list target.

`POST /api/connectors/trello/cards/dry-run` previews card creation without calling Trello. Passing `execute=true` returns a structured `409` dry-run-only response.

## Example dry-run bodies

```json
{"relative_path":"Zettelkasten/202606081200 Export.md","content":"# Export","execute":false}
```

```json
{"title":"Personal OS page","content":"Dry-run only","execute":false}
```

```json
{"title":"Personal OS card","description":"Dry-run only","labels":[],"execute":false}
```
