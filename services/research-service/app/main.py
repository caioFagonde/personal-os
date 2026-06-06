from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg
import httpx
from fastapi import FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .acquisition import search_sources
from .pdf_ingest import chunk_text, estimate_tokens, extract_citations, extract_pdf_text, sha256_bytes
from .security import optional_principal, require_scope
from .source_policy import classify_url, sanitize_query, validate_discovery_source

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
RESEARCH_CACHE_DIR = Path(os.environ.get("RESEARCH_CACHE_DIR", "/data/research/pdf-cache"))
FETCH_MAX_BYTES = int(os.environ.get("RESEARCH_FETCH_MAX_BYTES", "52428800"))

app = FastAPI(title="Personal OS Research Service", version="0.5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_pool: asyncpg.Pool | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=512)
    sources: list[str] = Field(default_factory=lambda: ["arxiv", "openalex", "crossref"])
    limit: int = Field(default=10, ge=1, le=50)
    device_key: str = "research-service"


class UrlFetchRequest(BaseModel):
    url: str
    title: str | None = None
    device_key: str = "research-service"
    source_kind: str = "authorized_url"
    metadata: dict[str, Any] = Field(default_factory=dict)


class UrlPolicyRequest(BaseModel):
    url: str


@app.middleware("http")
async def require_service_auth(request: Request, call_next):
    if request.url.path in {"/health", "/openapi.json"} or request.url.path.startswith(("/docs", "/redoc")):
        return await call_next(request)
    principal = optional_principal(request.headers.get("authorization"))
    require_scope(principal, "research:read" if request.method == "GET" else "research:write")
    request.state.principal = principal
    return await call_next(request)


@app.on_event("startup")
async def startup() -> None:
    global _pool
    RESEARCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=8)


@app.on_event("shutdown")
async def shutdown() -> None:
    if _pool:
        await _pool.close()


async def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("database pool not initialized")
    return _pool


@app.get("/health")
async def health() -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok", "service": "research-service", "cache_dir": str(RESEARCH_CACHE_DIR)}


@app.get("/api/research/sources")
async def sources() -> dict[str, Any]:
    return {
        "supported": ["arxiv", "openalex", "crossref", "semantic_scholar", "user_url", "upload"],
        "policy": "open-access, public metadata, user-authorized URLs, and user uploads only; pirate-library and paywall-circumvention sources are blocked",
    }


@app.post("/api/research/policy/check-url")
async def check_url(payload: UrlPolicyRequest) -> dict[str, Any]:
    decision = classify_url(payload.url)
    return decision.__dict__


@app.post("/api/research/search")
async def research_search(payload: SearchRequest) -> dict[str, Any]:
    try:
        query = sanitize_query(payload.query)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    source_decisions = [validate_discovery_source(s) for s in payload.sources]
    blocked = [d.__dict__ for d in source_decisions if not d.allowed]
    allowed = [d.source_kind for d in source_decisions if d.allowed]
    results = await search_sources(query, allowed, payload.limit)
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, payload.device_key)
        profile_id = await conn.fetchval("SELECT profile_id FROM devices WHERE id=$1", device_id)
        run_id = await conn.fetchval(
            """
            INSERT INTO research_search_runs(profile_id, device_id, query, requested_sources, policy)
            VALUES($1,$2,$3,$4,$5::jsonb) RETURNING id
            """,
            profile_id,
            device_id,
            query,
            allowed,
            json.dumps({"blocked": blocked}),
        )
        for result in results:
            record = result.to_record()
            await conn.execute(
                """
                INSERT INTO research_search_results(run_id, source, title, authors, year, venue, doi, landing_url, pdf_url, is_open_access, license, abstract, raw)
                VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb)
                ON CONFLICT DO NOTHING
                """,
                run_id,
                record["source"],
                record["title"],
                record["authors"],
                record["year"],
                record["venue"],
                record["doi"],
                record["landing_url"],
                record["pdf_url"],
                record["is_open_access"],
                record["license"],
                record["abstract"],
                json.dumps(record["raw"]),
            )
    return {"run_id": str(run_id), "blocked_sources": blocked, "results": [r.to_record() for r in results]}


@app.get("/api/research/search-runs")
async def list_search_runs(limit: int = Query(default=25, ge=1, le=100)) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT r.id::text, r.query, r.requested_sources, r.policy, r.created_at, COUNT(s.id)::int AS result_count
            FROM research_search_runs r LEFT JOIN research_search_results s ON s.run_id = r.id
            GROUP BY r.id ORDER BY r.created_at DESC LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]


@app.post("/api/research/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    device_key: str = Form(default="research-service"),
    metadata: str = Form(default="{}"),
) -> dict[str, Any]:
    content = await file.read()
    if len(content) > FETCH_MAX_BYTES:
        raise HTTPException(status_code=413, detail="file exceeds configured maximum size")
    mime_type = file.content_type or "application/pdf"
    if mime_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="only PDF upload is supported in Phase 5")
    meta = safe_json(metadata)
    return await ingest_pdf_bytes(content, title or file.filename or "Untitled PDF", device_key, "upload", None, mime_type, meta)


@app.post("/api/research/documents/fetch-url")
async def fetch_url(payload: UrlFetchRequest) -> dict[str, Any]:
    decision = classify_url(payload.url)
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, payload.device_key)
        job_id = await conn.fetchval(
            """
            INSERT INTO research_ingestion_jobs(device_id, status, source_url, reason, payload)
            VALUES($1,$2,$3,$4,$5::jsonb) RETURNING id
            """,
            device_id,
            "queued" if decision.allowed else "blocked",
            decision.normalized_url or payload.url,
            decision.reason,
            json.dumps(payload.model_dump()),
        )
    if not decision.allowed:
        return {"job_id": str(job_id), "status": "blocked", "policy": decision.__dict__}
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers={"User-Agent": "PersonalOSResearch/0.5"}) as client:
        resp = await client.get(decision.normalized_url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "").split(";", 1)[0].lower()
        content = resp.content
    if len(content) > FETCH_MAX_BYTES:
        raise HTTPException(status_code=413, detail="remote file exceeds configured maximum size")
    if content_type != "application/pdf" and not decision.normalized_url.lower().split("?", 1)[0].endswith(".pdf"):
        raise HTTPException(status_code=415, detail="authorized URL fetch currently accepts direct PDF URLs only")
    document = await ingest_pdf_bytes(content, payload.title or decision.normalized_url.rsplit("/", 1)[-1], payload.device_key, payload.source_kind, decision.normalized_url, "application/pdf", payload.metadata)
    async with (await pool()).acquire() as conn:
        await conn.execute("UPDATE research_ingestion_jobs SET status='succeeded', document_id=$2, updated_at=now() WHERE id=$1", job_id, UUID(document["document_id"]))
    return {"job_id": str(job_id), **document}


@app.get("/api/research/documents")
async def list_documents(query: str | None = None, limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, title, source_kind, source_url, doi, authors, year, license, object_uri, content_sha256, mime_type, page_count, text_status, metadata, created_at, updated_at
            FROM research_documents
            WHERE ($1::text IS NULL OR title ILIKE '%' || $1 || '%' OR doi ILIKE '%' || $1 || '%')
            ORDER BY updated_at DESC LIMIT $2
            """,
            query,
            limit,
        )
    return [dict(r) for r in rows]


@app.get("/api/research/documents/{document_id}")
async def get_document(document_id: UUID) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id::text, title, source_kind, source_url, doi, authors, year, license, object_uri, content_sha256, mime_type, page_count, text_status, metadata, created_at, updated_at
            FROM research_documents WHERE id=$1
            """,
            document_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="document not found")
        chunk_count = await conn.fetchval("SELECT COUNT(*) FROM research_chunks WHERE document_id=$1", document_id)
        citation_count = await conn.fetchval("SELECT COUNT(*) FROM research_citations WHERE document_id=$1", document_id)
    out = dict(row)
    out["chunk_count"] = chunk_count
    out["citation_count"] = citation_count
    return out


@app.get("/api/research/documents/{document_id}/chunks")
async def get_chunks(document_id: UUID, limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, chunk_index, page_start, page_end, content, token_estimate, created_at
            FROM research_chunks WHERE document_id=$1 ORDER BY chunk_index ASC LIMIT $2
            """,
            document_id,
            limit,
        )
    return [dict(r) for r in rows]


@app.get("/api/research/documents/{document_id}/citations")
async def get_citations(document_id: UUID) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, citation_key, raw_text, doi, url, authors, year, title, confidence, created_at
            FROM research_citations WHERE document_id=$1 ORDER BY confidence DESC, created_at ASC
            """,
            document_id,
        )
    return [dict(r) for r in rows]


@app.get("/api/research/local-search")
async def local_search(q: str = Query(..., min_length=2), limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT d.id::text AS document_id, d.title, c.id::text AS chunk_id, c.chunk_index,
                   ts_rank(c.tsv, plainto_tsquery('simple', $1)) AS rank,
                   ts_headline('simple', c.content, plainto_tsquery('simple', $1), 'MaxFragments=2, MaxWords=28') AS snippet
            FROM research_chunks c JOIN research_documents d ON d.id = c.document_id
            WHERE c.tsv @@ plainto_tsquery('simple', $1)
            ORDER BY rank DESC LIMIT $2
            """,
            q,
            limit,
        )
    return [dict(r) for r in rows]


async def ingest_pdf_bytes(content: bytes, title: str, device_key: str, source_kind: str, source_url: str | None, mime_type: str, metadata: dict[str, Any]) -> dict[str, Any]:
    digest = sha256_bytes(content)
    pdf_path = RESEARCH_CACHE_DIR / f"{digest}.pdf"
    if not pdf_path.exists():
        pdf_path.write_bytes(content)
    extracted = extract_pdf_text(content)
    chunks = chunk_text(extracted.text)
    citations = extract_citations(extracted.text)
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, device_key)
        profile_id = await conn.fetchval("SELECT profile_id FROM devices WHERE id=$1", device_id)
        entity_id = await create_entity(conn, "research", "research_document", digest, device_id)
        row = await conn.fetchrow(
            """
            INSERT INTO research_documents(entity_id, profile_id, device_id, title, source_kind, source_url, doi, authors, year, license, object_uri, content_sha256, mime_type, page_count, text_status, metadata)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16::jsonb)
            ON CONFLICT(content_sha256) DO UPDATE SET updated_at=now()
            RETURNING id::text, title, object_uri, content_sha256, page_count, text_status
            """,
            entity_id,
            profile_id,
            device_id,
            title,
            source_kind,
            source_url,
            metadata.get("doi"),
            metadata.get("authors", []),
            metadata.get("year"),
            metadata.get("license"),
            str(pdf_path),
            digest,
            mime_type,
            extracted.page_count,
            extracted.status,
            json.dumps(metadata),
        )
        document_id = UUID(row["id"])
        await conn.execute("DELETE FROM research_chunks WHERE document_id=$1", document_id)
        for idx, chunk in enumerate(chunks):
            await conn.execute(
                """
                INSERT INTO research_chunks(document_id, chunk_index, content, token_estimate)
                VALUES($1,$2,$3,$4)
                """,
                document_id,
                idx,
                chunk,
                estimate_tokens(chunk),
            )
        await conn.execute("DELETE FROM research_citations WHERE document_id=$1", document_id)
        for citation in citations:
            await conn.execute(
                """
                INSERT INTO research_citations(document_id, raw_text, doi, url, year, confidence)
                VALUES($1,$2,$3,$4,$5,$6)
                """,
                document_id,
                citation.raw_text,
                citation.doi,
                citation.url,
                citation.year,
                citation.confidence,
            )
        await record_change(conn, device_id, "research", "research_document", entity_id, "create", {"document_id": str(document_id), "title": title, "sha256": digest})
    return {"document_id": row["id"], "title": row["title"], "object_uri": row["object_uri"], "sha256": row["content_sha256"], "page_count": row["page_count"], "text_status": row["text_status"], "chunks": len(chunks), "citations": len(citations)}


async def ensure_device(conn: asyncpg.Connection, device_key: str) -> UUID:
    profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
    return await conn.fetchval(
        """
        INSERT INTO devices(profile_id, device_key, name, kind, platform, trust_level, last_seen_at)
        VALUES($1,$2,$2,'other','unknown','trusted',now())
        ON CONFLICT(device_key) DO UPDATE SET last_seen_at=now()
        RETURNING id
        """,
        profile_id,
        device_key,
    )


async def create_entity(conn: asyncpg.Connection, module_id: str, entity_type: str, external_id: str | None, device_id: UUID) -> UUID:
    return await conn.fetchval(
        """
        INSERT INTO entities(module_id, entity_type, external_id, created_by_device)
        VALUES($1,$2,COALESCE($3, gen_random_uuid()::text),$4)
        ON CONFLICT(module_id, entity_type, external_id) DO UPDATE SET updated_at=now()
        RETURNING id
        """,
        module_id,
        entity_type,
        external_id,
        device_id,
    )


async def record_change(conn: asyncpg.Connection, device_id: UUID, module_id: str, entity_type: str, entity_id: UUID, action: str, payload: dict[str, Any]) -> None:
    checksum = sha256_bytes(json.dumps(payload, sort_keys=True, default=str).encode())
    version_id = await conn.fetchval(
        """
        INSERT INTO entity_versions(entity_id, device_id, operation, merge_strategy, payload, checksum, version_clock)
        VALUES($1,$2,$3,'field_merge',$4::jsonb,$5,$6::jsonb) RETURNING id
        """,
        entity_id,
        device_id,
        action,
        json.dumps(payload, default=str),
        checksum,
        json.dumps({str(device_id): int(datetime.now(timezone.utc).timestamp())}),
    )
    await conn.execute("UPDATE entities SET current_version=$1, updated_at=now() WHERE id=$2", version_id, entity_id)
    await conn.execute(
        """
        INSERT INTO sync_log(module_id, entity_id, entity_type, version_id, device_id, action, payload, vector_clock, lamport)
        VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,COALESCE((SELECT MAX(lamport)+1 FROM sync_log),1))
        """,
        module_id,
        entity_id,
        entity_type,
        version_id,
        device_id,
        action,
        json.dumps(payload, default=str),
        json.dumps({str(device_id): int(datetime.now(timezone.utc).timestamp())}),
    )


def safe_json(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}
