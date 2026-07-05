"""Graph read API (Phase B4): objects, neighbors, hybrid search.

Search is honest about its mode:
  - "hybrid"  → query embedded via the embeddings service, pgvector cosine
                results merged with trigram/ILIKE lexical results.
  - "lexical" → no embedding model available (or no embedded chunks yet);
                Postgres trigram only, labeled "lexical search (no embedding
                model)" so the UI never implies semantic search is running.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .security import Principal, require_scope

if TYPE_CHECKING:  # asyncpg/httpx only needed at runtime, keeps contract tests import-light
    import asyncpg

EMBEDDINGS_SERVICE_URL = os.environ.get("EMBEDDINGS_SERVICE_URL", "http://embeddings:8090")

LEXICAL_LABEL = "lexical search (no embedding model)"
HYBRID_LABEL = "hybrid search (vector + lexical)"

OBJECT_COLUMNS = (
    "o.id::text, o.kind, o.domain_table, o.domain_id::text, o.title, o.slug, o.status, "
    "o.project_id::text, o.tags, o.meta, o.created_at, o.updated_at"
)


class GraphSearchRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    kinds: list[str] = Field(default_factory=list)
    k: int = Field(default=12, ge=1, le=50)


def merge_hits(lexical: list[dict[str, Any]], vector: list[dict[str, Any]], k: int) -> list[dict[str, Any]]:
    """Merge lexical + vector hits by object id.

    Score is the best single-signal score, with a small bonus when both
    signals agree — bounded to 1.0 so ranking stays interpretable.
    """
    merged: dict[str, dict[str, Any]] = {}
    for hit in lexical + vector:
        obj_id = hit["object"]["id"]
        if obj_id not in merged:
            merged[obj_id] = dict(hit)
        else:
            existing = merged[obj_id]
            both_bonus = 0.05
            existing["score"] = min(1.0, max(existing["score"], hit["score"]) + both_bonus)
            if not existing.get("snippet") and hit.get("snippet"):
                existing["snippet"] = hit["snippet"]
    return sorted(merged.values(), key=lambda h: h["score"], reverse=True)[:k]


def vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


async def embed_query(text: str) -> list[float] | None:
    """Fetch a query embedding; None means degrade to lexical (never fake)."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{EMBEDDINGS_SERVICE_URL}/api/embed", json={"text": text})
        if resp.status_code != 200:
            return None
        vectors = resp.json().get("vectors") or []
        return vectors[0] if vectors else None
    except httpx.HTTPError:
        return None


def build_router(pool_getter: Any, principal_dep: Any) -> APIRouter:
    router = APIRouter()

    @router.get("/api/graph/objects")
    async def list_objects(
        kind: str | None = None,
        q: str | None = None,
        domain_id: UUID | None = None,
        limit: int = Query(default=50, ge=1, le=200),
        principal: Principal = Depends(principal_dep),
    ) -> list[dict[str, Any]]:
        require_scope(principal, "modules:read")
        pool: asyncpg.Pool = await pool_getter()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT {OBJECT_COLUMNS} FROM objects o
                WHERE o.deleted_at IS NULL
                  AND ($1::text IS NULL OR o.kind=$1)
                  AND ($2::text IS NULL OR o.title ILIKE '%' || $2 || '%')
                  AND ($4::uuid IS NULL OR o.domain_id=$4)
                ORDER BY o.updated_at DESC LIMIT $3
                """,
                kind,
                q,
                limit,
                domain_id,
            )
        return [dict(r) for r in rows]

    @router.get("/api/graph/objects/{object_id}/neighbors")
    async def neighbors(
        object_id: UUID,
        rel: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        principal: Principal = Depends(principal_dep),
    ) -> list[dict[str, Any]]:
        require_scope(principal, "modules:read")
        pool: asyncpg.Pool = await pool_getter()
        async with pool.acquire() as conn:
            exists = await conn.fetchval("SELECT 1 FROM objects WHERE id=$1", object_id)
            if not exists:
                raise HTTPException(status_code=404, detail="object not found")
            rows = await conn.fetch(
                f"""
                SELECT {OBJECT_COLUMNS}, e.rel, e.weight, 'out' AS direction
                FROM edges e JOIN objects o ON o.id = e.dst_id
                WHERE e.src_id=$1 AND ($2::text IS NULL OR e.rel=$2) AND o.deleted_at IS NULL
                UNION ALL
                SELECT {OBJECT_COLUMNS}, e.rel, e.weight, 'in' AS direction
                FROM edges e JOIN objects o ON o.id = e.src_id
                WHERE e.dst_id=$1 AND ($2::text IS NULL OR e.rel=$2) AND o.deleted_at IS NULL
                LIMIT $3
                """,
                object_id,
                rel,
                limit,
            )
        out = []
        for row in rows:
            item = dict(row)
            rel_value = item.pop("rel")
            weight = item.pop("weight")
            direction = item.pop("direction")
            out.append({"object": item, "rel": rel_value, "weight": weight, "direction": direction})
        return out

    @router.post("/api/graph/search")
    async def search(
        payload: GraphSearchRequest,
        principal: Principal = Depends(principal_dep),
    ) -> dict[str, Any]:
        require_scope(principal, "modules:read")
        pool: asyncpg.Pool = await pool_getter()
        kinds = payload.kinds or None
        async with pool.acquire() as conn:
            lexical_rows = await conn.fetch(
                f"""
                SELECT {OBJECT_COLUMNS},
                       CASE WHEN o.title ILIKE '%' || $1 || '%' THEN 1.0
                            ELSE GREATEST(similarity(o.title, $1), COALESCE(c.sim, 0)) END AS score,
                       c.snippet
                FROM objects o
                LEFT JOIN LATERAL (
                    SELECT GREATEST(similarity(cc.text, $1),
                                    CASE WHEN cc.text ILIKE '%' || $1 || '%' THEN 0.9 ELSE 0 END) AS sim,
                           left(cc.text, 240) AS snippet
                    FROM object_chunks cc WHERE cc.object_id = o.id
                    ORDER BY 1 DESC LIMIT 1
                ) c ON true
                WHERE o.deleted_at IS NULL
                  AND ($2::text[] IS NULL OR o.kind = ANY($2))
                  AND (o.title ILIKE '%' || $1 || '%' OR o.title % $1 OR COALESCE(c.sim, 0) > 0.1)
                ORDER BY score DESC LIMIT $3
                """,
                payload.text,
                kinds,
                payload.k * 2,
            )
            embedded_available = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM object_chunks WHERE embedding IS NOT NULL)")
            vector_rows: list[asyncpg.Record] = []
            query_vec = await embed_query(payload.text) if embedded_available else None
            if query_vec:
                vector_rows = await conn.fetch(
                    f"""
                    SELECT {OBJECT_COLUMNS},
                           1 - (c.embedding <=> $1::vector) AS score,
                           left(c.text, 240) AS snippet
                    FROM object_chunks c JOIN objects o ON o.id = c.object_id
                    WHERE c.embedding IS NOT NULL AND o.deleted_at IS NULL
                      AND ($2::text[] IS NULL OR o.kind = ANY($2))
                    ORDER BY c.embedding <=> $1::vector LIMIT $3
                    """,
                    vector_literal(query_vec),
                    kinds,
                    payload.k * 2,
                )
        def to_hits(rows: list[asyncpg.Record]) -> list[dict[str, Any]]:
            hits = []
            for row in rows:
                item = dict(row)
                score = float(item.pop("score") or 0)
                snippet = item.pop("snippet", None)
                hits.append({"object": item, "score": score, "snippet": snippet})
            return hits

        mode = "hybrid" if query_vec else "lexical"
        return {
            "mode": mode,
            "label": HYBRID_LABEL if mode == "hybrid" else LEXICAL_LABEL,
            "hits": merge_hits(to_hits(lexical_rows), to_hits(vector_rows), payload.k),
        }

    return router
