#!/usr/bin/env python3
"""Idempotent graph registry backfill (Phase B2).

Registers every existing domain row in the `objects` registry, links the
obvious edges, and (re)queues embedding jobs for chunked text. Safe to run
repeatedly: object upserts key on (domain_table, domain_id), edges on
(src_id, dst_id, rel), chunks on (object_id, seq).

Usage:
    DATABASE_URL=postgresql://... python3 scripts/graph/backfill.py [--dry-run]

Requires: asyncpg (same dependency set as the services).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "graph" / "py"))

import asyncpg  # noqa: E402

import nexus_graph as graph  # noqa: E402

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")


async def table_exists(conn: asyncpg.Connection, table: str) -> bool:
    return bool(await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", table))


async def backfill_captures(conn: asyncpg.Connection) -> int:
    has_status = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='capture_items' AND column_name='status')"
    )
    status_col = "status" if has_status else "'inbox' AS status"
    rows = await conn.fetch(f"SELECT id, raw_text, {status_col}, created_at FROM capture_items ORDER BY created_at")
    for row in rows:
        title = (row["raw_text"] or "").strip().splitlines()[0][:200] if row["raw_text"] else "Capture"
        obj = await graph.register_object(
            conn, kind="capture_item", domain_table="capture_items", domain_id=row["id"],
            title=title or "Capture", status=row["status"],
        )
        await graph.upsert_chunks(conn, obj, [row["raw_text"] or ""])
    return len(rows)


async def backfill_tasks(conn: asyncpg.Connection) -> int:
    rows = await conn.fetch("SELECT id, title, body, status, tags, source_kind, source_id FROM tasks ORDER BY created_at")
    for row in rows:
        obj = await graph.register_object(
            conn, kind="task", domain_table="tasks", domain_id=row["id"],
            title=row["title"], status=row["status"], tags=list(row["tags"] or []),
        )
        await graph.upsert_chunks(conn, obj, [f"{row['title']}\n\n{row['body'] or ''}".strip()])
        if row["source_kind"] == "capture" and row["source_id"]:
            capture_obj = await graph.object_id_for(conn, "capture_items", row["source_id"])
            await graph.link(conn, obj, capture_obj, "derived_from")
    return len(rows)


async def backfill_notes(conn: asyncpg.Connection) -> int:
    rows = await conn.fetch("SELECT id, title, slug, body, note_type, tags FROM notes ORDER BY created_at")
    for row in rows:
        obj = await graph.register_object(
            conn, kind="note", domain_table="notes", domain_id=row["id"],
            title=row["title"], slug=row["slug"], status=row["note_type"], tags=list(row["tags"] or []),
        )
        await graph.upsert_chunks(conn, obj, graph.chunk_text(f"{row['title']}\n\n{row['body'] or ''}"))
    links = await conn.fetch(
        "SELECT source_note_id, target_note_id FROM zettel_links WHERE target_note_id IS NOT NULL"
    )
    for row in links:
        src = await graph.object_id_for(conn, "notes", row["source_note_id"])
        dst = await graph.object_id_for(conn, "notes", row["target_note_id"])
        await graph.link(conn, src, dst, "references")
    return len(rows)


async def backfill_research(conn: asyncpg.Connection) -> int:
    rows = await conn.fetch("SELECT id, title, source_kind, source_url, text_status FROM research_documents ORDER BY created_at")
    for row in rows:
        obj = await graph.register_object(
            conn, kind="source", domain_table="research_documents", domain_id=row["id"],
            title=row["title"], status=row["text_status"],
            meta={"source_kind": row["source_kind"], "source_url": row["source_url"]},
        )
        chunks = await conn.fetch(
            "SELECT content FROM research_chunks WHERE document_id=$1 ORDER BY chunk_index LIMIT $2",
            row["id"], graph.MAX_CHUNKS - 1,
        )
        await graph.upsert_chunks(conn, obj, [row["title"], *[c["content"] for c in chunks]])
    return len(rows)


async def backfill_twin(conn: asyncpg.Connection) -> int:
    count = 0
    if await table_exists(conn, "digital_twin_goals"):
        rows = await conn.fetch("SELECT id, title, domain, status FROM digital_twin_goals")
        for row in rows:
            obj = await graph.register_object(
                conn, kind="goal", domain_table="digital_twin_goals", domain_id=row["id"],
                title=row["title"], status=row["status"], tags=[row["domain"]] if row["domain"] else [],
            )
            await graph.upsert_chunks(conn, obj, [row["title"]])
        count += len(rows)
    if await table_exists(conn, "digital_twin_timeline_events"):
        rows = await conn.fetch("SELECT id, event_type, source, domains, sensitivity FROM digital_twin_timeline_events")
        for row in rows:
            await graph.register_object(
                conn, kind="event", domain_table="digital_twin_timeline_events", domain_id=row["id"],
                title=f"{row['event_type']} ({row['source']})", status=row["sensitivity"],
                tags=list(row["domains"] or []),
            )
        count += len(rows)
    return count


async def backfill_coding_agent(conn: asyncpg.Connection) -> int:
    if not await table_exists(conn, "coding_agent_jobs"):
        return 0
    rows = await conn.fetch("SELECT id, title, prompt, mode, status FROM coding_agent_jobs")
    for row in rows:
        obj = await graph.register_object(
            conn, kind="agent_run", domain_table="coding_agent_jobs", domain_id=row["id"],
            title=row["title"], status=row["status"], meta={"mode": row["mode"]},
        )
        await graph.upsert_chunks(conn, obj, [f"{row['title']}\n\n{row['prompt'] or ''}".strip()])
    return len(rows)


async def backfill_projects_daily(conn: asyncpg.Connection) -> int:
    count = 0
    rows = await conn.fetch("SELECT id, name, slug, status, pitch, north_star FROM projects")
    for row in rows:
        obj = await graph.register_object(
            conn, kind="project", domain_table="projects", domain_id=row["id"],
            title=row["name"], slug=row["slug"], status=row["status"],
        )
        await graph.upsert_chunks(conn, obj, [f"{row['name']}\n\n{row['pitch']}\n\n{row['north_star']}".strip()])
    count += len(rows)
    rows = await conn.fetch("SELECT id, day, intention, review, closed FROM daily_states")
    for row in rows:
        obj = await graph.register_object(
            conn, kind="daily_state", domain_table="daily_states", domain_id=row["id"],
            title=f"Daily {row['day'].isoformat()}", slug=f"daily-{row['day'].isoformat()}",
            status="closed" if row["closed"] else "open",
        )
        await graph.upsert_chunks(conn, obj, [f"Daily {row['day'].isoformat()}\n\n{row['intention']}\n\n{row['review']}".strip()])
    count += len(rows)
    return count


async def main(dry_run: bool) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        if not await table_exists(conn, "objects"):
            print("objects table missing — run migration 014 first (scripts/bootstrap.sh applies it).")
            raise SystemExit(1)
        if dry_run:
            for table in ("capture_items", "tasks", "notes", "research_documents", "projects", "daily_states"):
                if await table_exists(conn, table):
                    n = await conn.fetchval(f"SELECT count(*) FROM {table}")  # noqa: S608 - fixed identifiers
                    print(f"would register {n:>6} rows from {table}")
            return
        totals = {
            "capture_items": await backfill_captures(conn),
            "tasks": await backfill_tasks(conn),
            "notes": await backfill_notes(conn),
            "research_documents": await backfill_research(conn),
            "digital_twin": await backfill_twin(conn),
            "coding_agent_jobs": await backfill_coding_agent(conn),
            "projects+daily_states": await backfill_projects_daily(conn),
        }
        registered = await conn.fetchval("SELECT count(*) FROM objects")
        edges = await conn.fetchval("SELECT count(*) FROM edges")
        chunks = await conn.fetchval("SELECT count(*) FROM object_chunks")
        pending = await conn.fetchval("SELECT count(*) FROM object_chunks WHERE embedding IS NULL")
        for table, n in totals.items():
            print(f"backfilled {n:>6} rows from {table}")
        print(f"registry now: {registered} objects, {edges} edges, {chunks} chunks ({pending} awaiting embedding)")
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="count rows without writing")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
