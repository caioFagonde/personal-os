"""Nexus graph registry helper (canonical copy).

Thin dual-write layer over the Phase B registry tables (objects, edges,
object_chunks — migration 014). Every domain row that matters to the user gets
one `objects` row; relationships live in `edges`; searchable text lives in
`object_chunks` with embeddings filled asynchronously by the embeddings
service (NATS subject `nexus.embed`, transactional outbox in `service_events`).

Delivery model: Python services build from isolated Docker contexts, so each
dual-writing service carries an identical copy of this file at
`services/<name>/app/graph.py`. The canonical source lives at
`packages/graph/py/nexus_graph.py`; a root contract test asserts every copy is
byte-identical to it. Edit the canonical file, then re-copy.

Registry writes are best-effort by contract: a domain write must never fail
because a registry write failed. Callers invoke these helpers outside any
open transaction where possible; failures are logged and recorded in
`service_events` (topic `graph.write_failed`) for later repair by the
backfill script.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Sequence
from uuid import UUID

log = logging.getLogger("nexus-graph")

# Canonical object kinds (PERSONAL_GRAPH_SCHEMA.md). Kept here so services and
# the backfill script share one vocabulary.
KINDS = {
    "capture_item", "task", "project", "note", "source", "decision", "event",
    "artifact", "agent_run", "automation", "connector_account",
    "backup_snapshot", "sync_conflict", "daily_state", "goal", "person",
    "repository", "portfolio_case", "habit", "reminder",
}

# Relation vocabulary (edges.rel).
RELS = {
    "belongs_to_project", "derived_from", "references", "blocks", "decided_by",
    "about_person", "logged_on", "produced_by", "backs_up", "synced_with",
    "supports_goal", "evidence_for", "case_of", "mentions", "duplicate_of",
    "follows",
}

EMBED_SUBJECT = "nexus.embed"
CHUNK_CHARS = 1200
MAX_CHUNKS = 32


def slugify(text: str, fallback: str = "object") -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (base or fallback)[:120]


def chunk_text(text: str, chunk_chars: int = CHUNK_CHARS, max_chunks: int = MAX_CHUNKS) -> list[str]:
    """Split text into chunks on paragraph boundaries, hard-wrapping long runs."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        while len(para) > chunk_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(para[:chunk_chars])
            para = para[chunk_chars:]
        if len(current) + len(para) + 2 > chunk_chars and current:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks[:max_chunks]


async def _record_failure(conn: Any, op: str, detail: dict[str, Any]) -> None:
    try:
        await conn.execute(
            "INSERT INTO service_events(topic, payload) VALUES('graph.write_failed', $1::jsonb)",
            json.dumps({"op": op, **detail}, default=str),
        )
    except Exception:  # pragma: no cover - repair channel itself unavailable
        log.exception("graph: could not record write failure for %s", op)


async def register_object(
    conn: Any,
    *,
    kind: str,
    domain_table: str,
    domain_id: str | UUID,
    title: str,
    slug: str | None = None,
    status: str | None = None,
    project_id: str | UUID | None = None,
    tags: Sequence[str] = (),
    meta: dict[str, Any] | None = None,
) -> str | None:
    """Upsert the registry row for a domain row. Returns objects.id or None on failure."""
    if kind not in KINDS:
        log.warning("graph: unknown object kind %r (registering anyway)", kind)
    try:
        object_id = await conn.fetchval(
            """
            INSERT INTO objects(kind, domain_table, domain_id, title, slug, status, project_id, tags, meta)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
            ON CONFLICT(domain_table, domain_id) DO UPDATE SET
              title=EXCLUDED.title,
              status=COALESCE(EXCLUDED.status, objects.status),
              project_id=COALESCE(EXCLUDED.project_id, objects.project_id),
              tags=EXCLUDED.tags,
              meta=objects.meta || EXCLUDED.meta,
              updated_at=now(),
              deleted_at=NULL
            RETURNING id::text
            """,
            kind,
            domain_table,
            UUID(str(domain_id)),
            title or "",
            slug,
            status,
            UUID(str(project_id)) if project_id else None,
            list(tags),
            json.dumps(meta or {}, default=str),
        )
        return object_id
    except Exception as exc:
        log.warning("graph: register_object(%s/%s) failed: %s", domain_table, domain_id, exc)
        await _record_failure(conn, "register_object", {
            "kind": kind, "domain_table": domain_table, "domain_id": str(domain_id), "error": str(exc),
        })
        return None


async def object_id_for(conn: Any, domain_table: str, domain_id: str | UUID) -> str | None:
    try:
        return await conn.fetchval(
            "SELECT id::text FROM objects WHERE domain_table=$1 AND domain_id=$2",
            domain_table,
            UUID(str(domain_id)),
        )
    except Exception as exc:
        log.warning("graph: object_id_for(%s/%s) failed: %s", domain_table, domain_id, exc)
        return None


async def link(
    conn: Any,
    src_object_id: str | UUID | None,
    dst_object_id: str | UUID | None,
    rel: str,
    weight: float = 1.0,
    meta: dict[str, Any] | None = None,
) -> bool:
    """Upsert an edge between two registry objects. Missing endpoints are a no-op."""
    if not src_object_id or not dst_object_id:
        return False
    if rel not in RELS:
        log.warning("graph: unknown relation %r (linking anyway)", rel)
    try:
        await conn.execute(
            """
            INSERT INTO edges(src_id, dst_id, rel, weight, meta)
            VALUES($1,$2,$3,$4,$5::jsonb)
            ON CONFLICT(src_id, dst_id, rel) DO UPDATE SET weight=EXCLUDED.weight, meta=EXCLUDED.meta
            """,
            UUID(str(src_object_id)),
            UUID(str(dst_object_id)),
            rel,
            weight,
            json.dumps(meta or {}, default=str),
        )
        return True
    except Exception as exc:
        log.warning("graph: link(%s -%s-> %s) failed: %s", src_object_id, rel, dst_object_id, exc)
        await _record_failure(conn, "link", {
            "src": str(src_object_id), "dst": str(dst_object_id), "rel": rel, "error": str(exc),
        })
        return False


async def set_project(conn: Any, object_id: str | UUID | None, project_object_id: str | UUID | None) -> bool:
    """Set the fast-path project pointer and the belongs_to_project edge together."""
    if not object_id or not project_object_id:
        return False
    try:
        await conn.execute(
            "UPDATE objects SET project_id=$2, updated_at=now() WHERE id=$1",
            UUID(str(object_id)),
            UUID(str(project_object_id)),
        )
    except Exception as exc:
        log.warning("graph: set_project(%s) failed: %s", object_id, exc)
        await _record_failure(conn, "set_project", {"object_id": str(object_id), "error": str(exc)})
        return False
    return await link(conn, object_id, project_object_id, "belongs_to_project")


async def upsert_chunks(conn: Any, object_id: str | UUID | None, texts: Sequence[str], queue: bool = True) -> int:
    """Replace an object's searchable chunks (embedding left NULL) and queue the
    embedding job via the service_events outbox (consumed as NATS nexus.embed)."""
    if not object_id:
        return 0
    chunks = [t.strip() for t in texts if t and t.strip()][:MAX_CHUNKS]
    try:
        await conn.execute(
            "DELETE FROM object_chunks WHERE object_id=$1 AND seq >= $2",
            UUID(str(object_id)),
            len(chunks),
        )
        for seq, text in enumerate(chunks):
            await conn.execute(
                """
                INSERT INTO object_chunks(object_id, seq, text)
                VALUES($1,$2,$3)
                ON CONFLICT(object_id, seq) DO UPDATE SET
                  text=EXCLUDED.text,
                  embedding=CASE WHEN object_chunks.text IS DISTINCT FROM EXCLUDED.text THEN NULL ELSE object_chunks.embedding END,
                  model=CASE WHEN object_chunks.text IS DISTINCT FROM EXCLUDED.text THEN NULL ELSE object_chunks.model END
                """,
                UUID(str(object_id)),
                seq,
                text[: CHUNK_CHARS * 2],
            )
        if queue and chunks:
            await conn.execute(
                "INSERT INTO service_events(topic, payload) VALUES($1, $2::jsonb)",
                EMBED_SUBJECT,
                json.dumps({"object_id": str(object_id)}),
            )
        return len(chunks)
    except Exception as exc:
        log.warning("graph: upsert_chunks(%s) failed: %s", object_id, exc)
        await _record_failure(conn, "upsert_chunks", {"object_id": str(object_id), "error": str(exc)})
        return 0
