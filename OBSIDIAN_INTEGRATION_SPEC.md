# OBSIDIAN_INTEGRATION_SPEC.md — Nexus Prime ⇄ Obsidian

## Current state (verified)

- `connector-service` exposes `POST /api/connectors/obsidian/{path/validate, export, import}`.
- Export **really writes** markdown, vault-path containment validated, create-only (`open("x")`, 409 on exists).
- Import is **permanently dry-run** (executes → 409). No vault reading exists.
- Vault path comes from `OBSIDIAN_VAULT_PATH` env; no UI configuration; no frontmatter schema, daily notes, backlinks, Dataview metadata, or sync loop.

## Target model

**The vault is a peer replica, not an export target.** The app's Postgres is the system of record for structure (ids, edges, status); the vault is the system of record for *prose the user edits in Obsidian*. Sync is bidirectional per-file with 3-way merge, reusing sync-engine conflict machinery.

### Path mapping (objects.slug is authoritative; configurable roots)

| Object | Vault path |
|---|---|
| Project | `Projects/{slug}/README.md` |
| DailyState | `Daily/YYYY-MM-DD.md` |
| Task | Markdown task line inside its project README (or `Tasks/{slug}.md` when body > 1 line) |
| Note (zettel) | `Notes/{slug}.md` |
| Source | `Sources/{slug}.md` |
| Decision | `Decisions/{YYYY-MM-DD}-{slug}.md` |
| AgentRun report | `Agent Runs/{YYYY-MM-DD}-{short_id}.md` |
| Artifact | `Artifacts/{project-slug}/{artifact-id}.md` (metadata note; binary stays in MinIO with a link) |
| Person | `People/{slug}.md` |
| PortfolioCase | `Portfolio/{slug}.md` |

### Frontmatter schema (Dataview-compatible)

Every synced file begins with:

```yaml
---
nexus_id: 018f3c…          # objects.id — the join key, never edited by hand
nexus_kind: project
nexus_rev: 42               # server revision at last sync
status: active
tags: [nexus, project]
created: 2026-07-02
updated: 2026-07-02T14:03:00Z
aliases: []
# kind-specific:
project: "[[Projects/nexus-prime/README]]"   # backlink to owning project
due: 2026-07-10             # tasks
priority: 3                 # tasks
source_url: https://…       # sources
decision_status: accepted   # decisions
---
```

Task lines inside notes use Obsidian Tasks-plugin-compatible syntax so both ecosystems parse them:

```
- [ ] Ship vault indexer 📅 2026-07-10 ⏫ [nexus:: task/018f3d…]
```

The `[nexus:: id]` inline field is Dataview-readable and our re-import key.

### Daily note template

```
---
nexus_id: …, nexus_kind: daily_state, day: 2026-07-02
---
## Intention
{intention}
## Focus
{top tasks as task lines}
## Log
{captures triaged today, agent runs}
## Review
{review — user-editable, syncs back}
```

## Sync engine design

New module `vault-sync` inside connector-service (worker.py already provides the worker pattern):

1. **Indexer**: on demand + filesystem watch (watchdog lib; polling fallback for network drives). Maintains `vault_files(path, nexus_id, sha256, mtime, last_synced_rev, base_snapshot_ref)`; base snapshots stored in MinIO for 3-way merge.
2. **Outbound**: object updated → render markdown → if vault file unchanged since base, write (atomic: temp file + rename); else mark conflict.
3. **Inbound**: file changed → parse frontmatter + body → diff against base → apply field merge using existing `merge_field`; body uses base/local/remote 3-way text merge (`merge3` lib); unresolved → `sync_conflicts` row surfacing in `/continuity` with side-by-side resolution UI (page exists).
4. **New files created in Obsidian** under mapped roots with no `nexus_id` → become CaptureItems (kind `obsidian_note`) for triage — the vault becomes another capture source.
5. **Deletes are never propagated automatically** in either direction; a delete becomes a conflict-style confirmation.

Safety rules (extend existing containment):
- Only operate under configured roots; refuse symlinked escapes (resolve + prefix check — already implemented, keep).
- Never touch `.obsidian/` config.
- Frontmatter size cap, YAML safe-load only.
- Dry-run mode remains the default until the user flips "Enable vault write" in Settings, which also runs a one-time backup of the vault roots (`Backups/vault-pre-nexus-<ts>.tar.gz`).

## Backlinks & graph

- `[[wikilinks]]` in synced bodies are parsed on import → `edges(rel='references')`.
- Outbound rendering converts `references` edges into wikilinks in a `## Related` footer (marked with `<!-- nexus:related -->` guards so user edits outside the block are preserved).
- **Canvas export (feasible)**: `GET /api/graph/projects/{id}/canvas` emits a `.canvas` JSON (nodes = file refs, edges = graph edges) into `Projects/{slug}/map.canvas`. One-way, regenerate-on-demand, guard-noted as machine-generated.

## Settings & status UX

- Settings: vault path field validated live via existing `/path/validate`; per-root toggles (Projects/Daily/Notes/…); "Open vault" button (obsidian:// URI); sync mode: manual / on-change / interval.
- Notes surface shows per-note sync chip: `synced | pending | conflict | vault-only | app-only`.
- Continuity surface shows vault sync lag + last indexer run.

## Delivery order & tests

1. Frontmatter renderer/parser (pure functions, golden-file tests) — no I/O.
2. Vault indexer + read path (`obsidian.read_note` tool unblocks harness).
3. Outbound sync for Project/Daily/Decision (create + safe update).
4. Inbound merge + conflict UI wiring.
5. Task-line round trip.
6. Canvas export.

Tests: golden markdown fixtures per object kind; path-traversal attempts; 3-way merge matrix (app-only change / vault-only / both-compatible / both-conflicting); watcher debounce; Windows path + emoji filename handling; a full e2e: create project in app → edit README in "vault" tmpdir → see merged result and edge extraction.
