"""Vault sync engine (Phase D3): indexer, outbound render, inbound 3-way merge.

The vault is a peer replica: Postgres owns structure (ids, edges, status), the
vault owns prose the user edits in Obsidian. Safety model:

- dry-run is the default; writes require the `obsidian_vault_write` setting
  (flipped from Settings, which also triggers a one-time vault backup).
- only mapped roots are touched; `.obsidian/` never; traversal re-checked on
  every write via the same containment as the legacy export endpoint.
- deletes are never propagated — a missing counterpart becomes a conflict row.
- conflicts live in `vault_files.status='conflict'` (not sync_conflicts: that
  table FKs entities rows which projects/dailies don't have — deliberate
  deviation, resolution UI reads vault_files instead).
"""
from __future__ import annotations

import hashlib
import json
import logging
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg

from . import vault_paths, vault_schema
from .vault_merge import merge_bodies, merge_fields

log = logging.getLogger("vault-sync")

WRITE_SETTING_KEY = "obsidian_vault_write"
STATUS_SETTING_KEY = "obsidian_vault_status"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class VaultSync:
    def __init__(self, pool: asyncpg.Pool, vault_path: str) -> None:
        self.pool = pool
        self.vault = Path(vault_path).expanduser().resolve()

    # --- config ----------------------------------------------------------------

    async def write_enabled(self) -> bool:
        async with self.pool.acquire() as conn:
            value = await conn.fetchval("SELECT value FROM settings WHERE key=$1", WRITE_SETTING_KEY)
        if value is None:
            return False
        parsed = value if isinstance(value, bool) else json.loads(value) if isinstance(value, str) else value
        return parsed is True

    async def set_write_enabled(self, enabled: bool) -> dict[str, Any]:
        backup_path = None
        if enabled:
            backup_path = self.backup_vault_roots()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO settings(key, value, updated_at) VALUES($1, $2::jsonb, now())
                ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()
                """,
                WRITE_SETTING_KEY,
                json.dumps(enabled),
            )
        return {"enabled": enabled, "backup": str(backup_path) if backup_path else None}

    def backup_vault_roots(self) -> Path:
        """One-time tarball of the mapped roots before the first enabled write."""
        backups_dir = self.vault / "Backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = backups_dir / f"vault-pre-nexus-{stamp}.tar.gz"
        with tarfile.open(target, "w:gz") as tar:
            for root in vault_paths.SYNC_ROOTS:
                root_dir = self.vault / root
                if root_dir.is_dir():
                    tar.add(root_dir, arcname=root)
        return target

    # --- path safety --------------------------------------------------------------

    def resolve_contained(self, relative_path: str) -> Path:
        if vault_paths.is_protected(relative_path):
            raise ValueError("refusing to touch .obsidian configuration")
        target = (self.vault / relative_path).resolve()
        if target == self.vault or self.vault not in target.parents:
            raise ValueError("path escapes the configured vault")
        return target

    def atomic_write(self, relative_path: str, content: str) -> None:
        target = self.resolve_contained(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".nexus-tmp")
        temp.write_text(content, encoding="utf-8")
        temp.replace(target)  # atomic on POSIX

    # --- indexer ---------------------------------------------------------------------

    async def index(self) -> dict[str, Any]:
        """Scan mapped roots, upsert vault_files, turn unmapped notes into captures."""
        seen: list[str] = []
        new_captures = 0
        async with self.pool.acquire() as conn:
            for root in vault_paths.SYNC_ROOTS:
                root_dir = self.vault / root
                if not root_dir.is_dir():
                    continue
                for path in sorted(root_dir.rglob("*.md")):
                    rel = path.relative_to(self.vault).as_posix()
                    if vault_paths.is_protected(rel):
                        continue
                    try:
                        content = path.read_text(encoding="utf-8")
                    except (OSError, UnicodeDecodeError) as exc:
                        log.warning("vault: cannot read %s: %s", rel, exc)
                        continue
                    seen.append(rel)
                    digest = sha256_text(content)
                    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                    fields, _ = vault_schema.parse_frontmatter(content)
                    nexus_id = fields.get("nexus_id")
                    try:
                        nexus_uuid = UUID(str(nexus_id)) if nexus_id else None
                    except ValueError:
                        nexus_uuid = None
                    row = await conn.fetchrow("SELECT * FROM vault_files WHERE relative_path=$1", rel)
                    if row is None:
                        status = "pending" if nexus_uuid else "vault_only"
                        await conn.execute(
                            """
                            INSERT INTO vault_files(relative_path, nexus_id, kind, sha256, mtime, status)
                            VALUES($1,$2,$3,$4,$5,$6)
                            ON CONFLICT(relative_path) DO UPDATE SET sha256=EXCLUDED.sha256, mtime=EXCLUDED.mtime, updated_at=now()
                            """,
                            rel, nexus_uuid, fields.get("nexus_kind") or vault_paths.kind_for_relpath(rel), digest, mtime, status,
                        )
                        if nexus_uuid is None:
                            new_captures += await self._capture_vault_note(conn, rel, content)
                    elif row["sha256"] != digest:
                        await conn.execute(
                            "UPDATE vault_files SET sha256=$2, mtime=$3, status=CASE WHEN status='conflict' THEN 'conflict' ELSE 'pending' END, updated_at=now() WHERE relative_path=$1",
                            rel, digest, mtime,
                        )
            # files we tracked that vanished from disk: never auto-delete — flag.
            tracked = await conn.fetch("SELECT relative_path, status FROM vault_files")
            missing = [r["relative_path"] for r in tracked if r["relative_path"] not in seen]
            for rel in missing:
                await conn.execute(
                    "UPDATE vault_files SET status='conflict', detail='file deleted in vault — deletes are never propagated automatically', updated_at=now() "
                    "WHERE relative_path=$1 AND status != 'conflict' AND base_snapshot IS NOT NULL",
                    rel,
                )
            await self._stamp_status(conn, "index")
        return {"indexed": len(seen), "new_captures": new_captures, "missing": len(missing)}

    async def _capture_vault_note(self, conn: asyncpg.Connection, rel: str, content: str) -> int:
        """A vault file with no nexus_id becomes a CaptureItem — the vault is a capture source."""
        _, body = vault_schema.parse_frontmatter(content)
        text = body.strip()[:4000] or rel
        fingerprint = f"obsidian:{rel}"
        device_id = await conn.fetchval(
            """
            INSERT INTO devices(profile_id, device_key, name, kind, platform, last_seen_at)
            SELECT id, 'obsidian-vault', 'obsidian-vault', 'server', 'server', now() FROM profiles WHERE handle='default'
            ON CONFLICT(device_key) DO UPDATE SET last_seen_at=now() RETURNING id
            """
        )
        inserted = await conn.fetchrow(
            """
            INSERT INTO capture_items(device_id, source_kind, source_id, raw_text, parsed, fingerprint)
            VALUES($1, 'obsidian_note', $2, $3, '{}'::jsonb, $4)
            ON CONFLICT(fingerprint) DO NOTHING
            RETURNING id
            """,
            device_id, rel, text, fingerprint,
        )
        return 1 if inserted else 0

    # --- outbound ------------------------------------------------------------------------

    async def sync_outbound(self, execute: bool) -> dict[str, Any]:
        """Render Project/Daily/Decision/Note objects into the vault (create + safe update)."""
        write = execute and await self.write_enabled()
        plans: list[dict[str, Any]] = []
        async with self.pool.acquire() as conn:
            plans += await self._outbound_projects(conn)
            plans += await self._outbound_dailies(conn)
            plans += await self._outbound_decisions(conn)
            plans += await self._outbound_notes(conn)
            written = 0
            conflicts = 0
            for plan in plans:
                rel, content, nexus_id, kind, rev = plan["path"], plan["content"], plan["nexus_id"], plan["kind"], plan["rev"]
                row = await conn.fetchrow("SELECT * FROM vault_files WHERE relative_path=$1", rel)
                target = self.resolve_contained(rel)
                on_disk = target.read_text(encoding="utf-8") if target.exists() else None
                base = row["base_snapshot"] if row else None
                if on_disk is not None and base is not None and sha256_text(on_disk) != sha256_text(base):
                    # user edited since last sync → inbound merge decides; don't clobber
                    plan["action"] = "needs_merge"
                    conflicts += 1
                    continue
                if on_disk is not None and sha256_text(on_disk) == sha256_text(content):
                    plan["action"] = "unchanged"
                    await self._mark_synced(conn, rel, nexus_id, kind, content, rev)
                    continue
                plan["action"] = "write" if write else "dry_run"
                if write:
                    self.atomic_write(rel, content)
                    await self._mark_synced(conn, rel, nexus_id, kind, content, rev)
                    written += 1
            await self._stamp_status(conn, "outbound")
        return {
            "mode": "write" if write else "dry_run",
            "planned": len(plans),
            "written": written,
            "needs_merge": conflicts,
            "plans": [{k: p[k] for k in ("path", "kind", "action")} for p in plans],
        }

    async def _mark_synced(self, conn: asyncpg.Connection, rel: str, nexus_id: str | None, kind: str, content: str, rev: str) -> None:
        await conn.execute(
            """
            INSERT INTO vault_files(relative_path, nexus_id, kind, sha256, base_snapshot, last_synced_rev, status, detail, updated_at)
            VALUES($1,$2,$3,$4,$5,$6,'synced','',now())
            ON CONFLICT(relative_path) DO UPDATE SET
              nexus_id=EXCLUDED.nexus_id, kind=EXCLUDED.kind, sha256=EXCLUDED.sha256,
              base_snapshot=EXCLUDED.base_snapshot, last_synced_rev=EXCLUDED.last_synced_rev,
              status='synced', detail='', updated_at=now()
            """,
            rel, UUID(nexus_id) if nexus_id else None, kind, sha256_text(content), content, rev,
        )

    async def _project_tasks(self, conn: asyncpg.Connection, project_object_id: str) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            """
            SELECT t.id::text, t.title, t.status, t.due_at, t.priority
            FROM objects o JOIN tasks t ON t.id = o.domain_id
            WHERE o.kind='task' AND o.domain_table='tasks' AND o.project_id=$1 AND o.deleted_at IS NULL
            ORDER BY t.priority, t.created_at
            """,
            UUID(project_object_id),
        )
        return [dict(r) for r in rows]

    async def _related_links(self, conn: asyncpg.Connection, object_id: str) -> list[str]:
        rows = await conn.fetch(
            """
            SELECT o.kind, o.slug, o.title FROM edges e JOIN objects o ON o.id = e.dst_id
            WHERE e.src_id=$1 AND e.rel='references' AND o.deleted_at IS NULL AND o.slug IS NOT NULL
            """,
            UUID(object_id),
        )
        links = []
        for r in rows:
            try:
                links.append(vault_paths.vault_relpath(r["kind"], r["slug"]).removesuffix(".md"))
            except ValueError:
                continue
        return links

    async def _outbound_projects(self, conn: asyncpg.Connection) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            """
            SELECT p.*, o.id::text AS object_id, o.tags AS obj_tags FROM projects p
            JOIN objects o ON o.domain_table='projects' AND o.domain_id=p.id
            WHERE p.status IN ('active','paused') AND o.deleted_at IS NULL
            """
        )
        plans = []
        for r in rows:
            tasks = await self._project_tasks(conn, r["object_id"])
            related = await self._related_links(conn, r["object_id"])
            obj = {**dict(r), "nexus_id": r["object_id"], "rev": str(r["updated_at"]), "tags": list(r["obj_tags"] or [])}
            plans.append({
                "path": vault_paths.vault_relpath("project", r["slug"]),
                "content": vault_schema.render_project_readme(obj, tasks, related),
                "nexus_id": r["object_id"],
                "kind": "project",
                "rev": str(r["updated_at"]),
            })
        return plans

    async def _outbound_dailies(self, conn: asyncpg.Connection) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            """
            SELECT d.*, o.id::text AS object_id FROM daily_states d
            JOIN objects o ON o.domain_table='daily_states' AND o.domain_id=d.id
            WHERE d.day >= current_date - interval '14 days' AND o.deleted_at IS NULL
            """
        )
        plans = []
        for r in rows:
            focus = await conn.fetch(
                """
                SELECT id::text, title, status, due_at, priority FROM tasks
                WHERE status NOT IN ('completed','archived') AND (due_at::date <= $1 OR status='inbox')
                ORDER BY due_at NULLS LAST, priority LIMIT 8
                """,
                r["day"],
            )
            obj = {**dict(r), "nexus_id": r["object_id"], "rev": f"{r['day']}:{r['closed']}"}
            plans.append({
                "path": vault_paths.vault_relpath("daily_state", "", day=r["day"].isoformat()),
                "content": vault_schema.render_daily_note(obj, [dict(t) for t in focus], []),
                "nexus_id": r["object_id"],
                "kind": "daily_state",
                "rev": obj["rev"],
            })
        return plans

    async def _outbound_decisions(self, conn: asyncpg.Connection) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            """
            SELECT d.*, o.id::text AS object_id FROM decisions d
            JOIN objects o ON o.domain_table='decisions' AND o.domain_id=d.id
            WHERE o.deleted_at IS NULL
            """
        )
        plans = []
        for r in rows:
            obj = {**dict(r), "nexus_id": r["object_id"], "rev": str(r["decided_at"])}
            plans.append({
                "path": vault_paths.vault_relpath("decision", r["slug"], decided_at=str(r["decided_at"])),
                "content": vault_schema.render_decision_note(obj),
                "nexus_id": r["object_id"],
                "kind": "decision",
                "rev": str(r["decided_at"]),
            })
        return plans

    async def _outbound_notes(self, conn: asyncpg.Connection) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            """
            SELECT n.id, n.title, n.slug, n.body, n.note_type, n.tags, n.created_at, n.updated_at, o.id::text AS object_id
            FROM notes n JOIN objects o ON o.domain_table='notes' AND o.domain_id=n.id
            WHERE o.deleted_at IS NULL
            """
        )
        plans = []
        for r in rows:
            related = await self._related_links(conn, r["object_id"])
            obj = {**dict(r), "nexus_id": r["object_id"], "rev": str(r["updated_at"]), "status": r["note_type"], "tags": list(r["tags"] or [])}
            plans.append({
                "path": vault_paths.vault_relpath("note", r["slug"]),
                "content": vault_schema.render_zettel_note(obj, related),
                "nexus_id": r["object_id"],
                "kind": "note",
                "rev": str(r["updated_at"]),
            })
        return plans

    # --- inbound -------------------------------------------------------------------------

    async def sync_inbound(self, execute: bool) -> dict[str, Any]:
        """Apply vault edits back to the app: 3-way merge, conflicts flagged, never deleted."""
        write = execute and await self.write_enabled()
        applied, conflicts, skipped = 0, 0, 0
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM vault_files WHERE status='pending' AND nexus_id IS NOT NULL AND base_snapshot IS NOT NULL"
            )
            for row in rows:
                rel = row["relative_path"]
                try:
                    target = self.resolve_contained(rel)
                except ValueError:
                    skipped += 1
                    continue
                if not target.exists():
                    continue  # deletion handled by index() as conflict
                on_disk = target.read_text(encoding="utf-8")
                result = await self._merge_one(conn, dict(row), on_disk, write)
                if result == "conflict":
                    conflicts += 1
                elif result == "applied":
                    applied += 1
                else:
                    skipped += 1
            await self._stamp_status(conn, "inbound")
        return {"mode": "write" if write else "dry_run", "applied": applied, "conflicts": conflicts, "skipped": skipped}

    async def _merge_one(self, conn: asyncpg.Connection, row: dict[str, Any], on_disk: str, write: bool) -> str:
        base_fields, base_body = vault_schema.parse_frontmatter(row["base_snapshot"])
        vault_fields, vault_body = vault_schema.parse_frontmatter(on_disk)
        kind = row["kind"]
        obj = await conn.fetchrow("SELECT * FROM objects WHERE id=$1", row["nexus_id"])
        if obj is None:
            await conn.execute(
                "UPDATE vault_files SET status='conflict', detail='object deleted in app — deletes are never propagated', updated_at=now() WHERE relative_path=$1",
                row["relative_path"],
            )
            return "conflict"

        if kind == "note":
            return await self._merge_note(conn, row, obj, base_body, vault_body, vault_fields, write)
        if kind == "daily_state":
            return await self._merge_daily(conn, row, obj, base_body, vault_body, write)
        if kind == "project":
            return await self._merge_project_tasks(conn, row, obj, vault_body, write)
        # other kinds are outbound-only in v1
        return "skipped"

    async def _merge_note(self, conn, row, obj, base_body, vault_body, vault_fields, write: bool) -> str:
        note = await conn.fetchrow("SELECT * FROM notes WHERE id=$1", obj["domain_id"])
        if note is None:
            return "skipped"
        app_related = await self._related_links(conn, str(obj["id"]))
        app_obj = {**dict(note), "nexus_id": str(obj["id"]), "rev": str(note["updated_at"]), "status": note["note_type"], "tags": list(note["tags"] or [])}
        app_rendered = vault_schema.render_zettel_note(app_obj, app_related)
        _, app_body = vault_schema.parse_frontmatter(app_rendered)
        merge = merge_bodies(base_body, app_body, vault_body)
        if merge.conflict:
            await conn.execute(
                "UPDATE vault_files SET status='conflict', detail=$2, updated_at=now() WHERE relative_path=$1",
                row["relative_path"], "body conflict — resolve from Continuity → Vault",
            )
            return "conflict"
        if not write:
            return "skipped"
        # merged body minus rendered scaffolding becomes the note body
        new_body = merge.merged
        title_line = new_body.strip().splitlines()[0] if new_body.strip() else f"# {note['title']}"
        new_title = title_line.lstrip("# ").strip() or note["title"]
        prose = new_body.split("\n", 1)[1] if "\n" in new_body else ""
        prose = prose.split("<!-- nexus:related:start -->")[0].strip("\n")
        new_tags = [t for t in (vault_fields.get("tags") or []) if t not in ("nexus", "note")] or list(note["tags"] or [])
        await conn.execute(
            "UPDATE notes SET title=$2, body=$3, tags=$4, updated_at=now() WHERE id=$1",
            note["id"], new_title, prose.strip(), new_tags,
        )
        # wikilinks in the merged body become references edges
        for target_title in vault_schema.extract_wikilinks(prose):
            target_note = await conn.fetchval("SELECT id FROM notes WHERE lower(title)=lower($1) OR slug=$1 LIMIT 1", target_title.split("/")[-1])
            if target_note:
                target_obj = await conn.fetchval("SELECT id FROM objects WHERE domain_table='notes' AND domain_id=$1", target_note)
                if target_obj:
                    await conn.execute(
                        """
                        INSERT INTO edges(src_id, dst_id, rel) VALUES($1,$2,'references')
                        ON CONFLICT(src_id, dst_id, rel) DO NOTHING
                        """,
                        obj["id"], target_obj,
                    )
        await conn.execute("UPDATE objects SET title=$2, updated_at=now() WHERE id=$1", obj["id"], new_title)
        await self._refresh_base(conn, row["relative_path"])
        return "applied"

    async def _merge_daily(self, conn, row, obj, base_body, vault_body, write: bool) -> str:
        base_sections = vault_schema.parse_daily_sections(base_body)
        vault_sections = vault_schema.parse_daily_sections(vault_body)
        daily = await conn.fetchrow("SELECT * FROM daily_states WHERE id=$1", obj["domain_id"])
        if daily is None:
            return "skipped"
        app_sections = {"intention": daily["intention"] or "", "review": daily["review"] or ""}
        merge = merge_fields(
            {k: base_sections.get(k, "") for k in ("intention", "review")},
            app_sections,
            {k: vault_sections.get(k, "") for k in ("intention", "review")},
        )
        if merge.conflicts:
            await conn.execute(
                "UPDATE vault_files SET status='conflict', detail=$2, updated_at=now() WHERE relative_path=$1",
                row["relative_path"], f"conflicting sections: {', '.join(merge.conflicts)}",
            )
            return "conflict"
        if not write:
            return "skipped"
        await conn.execute(
            "UPDATE daily_states SET intention=$2, review=$3 WHERE id=$1",
            daily["id"], merge.merged.get("intention", ""), merge.merged.get("review", ""),
        )
        await self._apply_task_checkboxes(conn, vault_body)
        await self._refresh_base(conn, row["relative_path"])
        return "applied"

    async def _merge_project_tasks(self, conn, row, obj, vault_body, write: bool) -> str:
        if not write:
            return "skipped"
        await self._apply_task_checkboxes(conn, vault_body)
        await self._refresh_base(conn, row["relative_path"])
        return "applied"

    async def _apply_task_checkboxes(self, conn: asyncpg.Connection, body: str) -> None:
        """Task-line round trip: a checked box in the vault completes the task."""
        for parsed in vault_schema.parse_task_lines(body):
            if parsed["done"]:
                await conn.execute(
                    "UPDATE tasks SET status='completed', completed_at=COALESCE(completed_at, now()), updated_at=now() "
                    "WHERE id=$1 AND status != 'completed'",
                    UUID(parsed["id"]),
                )

    async def _refresh_base(self, conn: asyncpg.Connection, rel: str) -> None:
        target = self.resolve_contained(rel)
        content = target.read_text(encoding="utf-8") if target.exists() else ""
        await conn.execute(
            "UPDATE vault_files SET base_snapshot=$2, sha256=$3, status='synced', detail='', updated_at=now() WHERE relative_path=$1",
            rel, content, sha256_text(content),
        )

    # --- conflict resolution -----------------------------------------------------------------

    async def resolve(self, relative_path: str, resolution: str, execute: bool) -> dict[str, Any]:
        """Resolve a conflict by re-baselining, then let the next sync pass apply the winner.

        keep_app:   base := current vault file → outbound sees "vault unchanged" and
                    overwrites it with the app render.
        keep_vault: base := current app render → inbound sees "app unchanged" and
                    applies the vault edits cleanly.
        """
        if resolution not in ("keep_app", "keep_vault"):
            raise ValueError("resolution must be keep_app or keep_vault")
        write = execute and await self.write_enabled()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM vault_files WHERE relative_path=$1 AND status='conflict'", relative_path)
            if row is None:
                raise LookupError("no conflict recorded for that path")
            if not write:
                return {"status": "dry_run", "resolution": resolution, "path": relative_path}
            if resolution == "keep_app":
                target = self.resolve_contained(relative_path)
                on_disk = target.read_text(encoding="utf-8") if target.exists() else ""
                await conn.execute(
                    "UPDATE vault_files SET status='pending', detail='', base_snapshot=$2, sha256=$3, updated_at=now() WHERE relative_path=$1",
                    relative_path, on_disk, sha256_text(on_disk),
                )
            else:  # keep_vault
                app_render = await self._render_for(conn, row)
                if app_render is None:
                    raise LookupError("cannot render the app version for that path")
                await conn.execute(
                    "UPDATE vault_files SET status='pending', detail='', base_snapshot=$2, updated_at=now() WHERE relative_path=$1",
                    relative_path, app_render,
                )
        return {"status": "resolved", "resolution": resolution, "path": relative_path}

    async def _render_for(self, conn: asyncpg.Connection, row: dict[str, Any] | asyncpg.Record) -> str | None:
        """Current app-side render of the object mapped to a vault_files row."""
        renderers = {
            "project": self._outbound_projects,
            "daily_state": self._outbound_dailies,
            "decision": self._outbound_decisions,
            "note": self._outbound_notes,
        }
        renderer = renderers.get(row["kind"])
        if renderer is None:
            return None
        for plan in await renderer(conn):
            if plan["path"] == row["relative_path"]:
                return plan["content"]
        return None

    # --- status --------------------------------------------------------------------------------

    async def _stamp_status(self, conn: asyncpg.Connection, phase: str) -> None:
        await conn.execute(
            """
            INSERT INTO settings(key, value, updated_at) VALUES($1, $2::jsonb, now())
            ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()
            """,
            STATUS_SETTING_KEY,
            json.dumps({"last_phase": phase, "at": datetime.now(timezone.utc).isoformat()}),
        )

    async def status(self) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            counts = await conn.fetch("SELECT status, count(*) AS n FROM vault_files GROUP BY status")
            last = await conn.fetchval("SELECT value FROM settings WHERE key=$1", STATUS_SETTING_KEY)
        by_status = {r["status"]: r["n"] for r in counts}
        parsed_last = last if isinstance(last, dict) else json.loads(last) if isinstance(last, str) else None
        return {
            "vault_path": str(self.vault),
            "write_enabled": await self.write_enabled(),
            "files": by_status,
            "conflicts": by_status.get("conflict", 0),
            "last_run": parsed_last,
        }

    async def files(self, status: str | None = None) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT v.relative_path, v.nexus_id::text, v.kind, v.status, v.detail, v.updated_at,
                       o.domain_table, o.domain_id::text, o.title
                FROM vault_files v LEFT JOIN objects o ON o.id = v.nexus_id
                WHERE ($1::text IS NULL OR v.status=$1)
                ORDER BY v.updated_at DESC LIMIT 500
                """,
                status,
            )
        return [dict(r) for r in rows]

    # --- canvas export ----------------------------------------------------------------------------

    async def export_canvas(self, project_id: UUID, execute: bool) -> dict[str, Any]:
        write = execute and await self.write_enabled()
        async with self.pool.acquire() as conn:
            project = await conn.fetchrow(
                """
                SELECT p.*, o.id AS object_id FROM projects p
                JOIN objects o ON o.domain_table='projects' AND o.domain_id=p.id WHERE p.id=$1
                """,
                project_id,
            )
            if project is None:
                raise LookupError("project not found")
            neighbors = await conn.fetch(
                """
                SELECT o.id::text, o.kind, o.slug, o.title, e.rel FROM edges e
                JOIN objects o ON o.id = CASE WHEN e.src_id=$1 THEN e.dst_id ELSE e.src_id END
                WHERE (e.src_id=$1 OR e.dst_id=$1) AND o.deleted_at IS NULL
                """,
                project["object_id"],
            )
        nodes = [{"id": str(project["object_id"]), "file": vault_paths.vault_relpath("project", project["slug"])}]
        edges = []
        for n in neighbors:
            try:
                file = vault_paths.vault_relpath(n["kind"], n["slug"] or n["title"])
            except ValueError:
                continue
            nodes.append({"id": n["id"], "file": file})
            edges.append({"src": str(project["object_id"]), "dst": n["id"], "rel": n["rel"]})
        canvas = vault_schema.render_canvas({"slug": project["slug"]}, nodes, edges)
        rel = vault_paths.canvas_relpath(project["slug"])
        if write:
            self.atomic_write(rel, canvas)
        return {"status": "written" if write else "dry_run", "path": rel, "nodes": len(nodes), "edges": len(edges)}
