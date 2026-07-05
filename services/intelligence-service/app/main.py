from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .security import optional_principal, require_scope
from .source_policy import sanitize_query, validate_feed_url, ALLOWED_SOURCE_KINDS

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://searxng:8080")

app = FastAPI(title="Personal OS Intelligence Service", version="0.1.0")
# CORS origins are configurable via env (comma-separated). "*" is the local-dev
# default; restrict to the gateway origin(s) on any non-tailnet deployment.
CORS_ALLOW_ORIGINS = [o.strip() for o in os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()] or ["*"]
app.add_middleware(CORSMiddleware, allow_origins=CORS_ALLOW_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_pool: asyncpg.Pool | None = None


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    kind: str = Field(min_length=1, max_length=64)
    url: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    keywords: list[str] = Field(min_length=1, max_items=50)
    source_ids: list[str] = Field(default_factory=list)
    schedule: str = Field(default="daily")
    enabled: bool = True


class BriefingGenerate(BaseModel):
    monitor_ids: list[str] = Field(default_factory=list)
    title: str | None = None


@app.middleware("http")
async def require_service_auth(request: Request, call_next):
    if request.url.path in {"/health", "/openapi.json"} or request.url.path.startswith(("/docs", "/redoc")):
        return await call_next(request)
    principal = optional_principal(request.headers.get("authorization"))
    require_scope(principal, "intelligence:read" if request.method == "GET" else "intelligence:write")
    request.state.principal = principal
    return await call_next(request)


@app.on_event("startup")
async def startup() -> None:
    global _pool
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
    return {"status": "ok", "service": "intelligence-service"}


@app.get("/api/intelligence/policy")
async def policy() -> dict[str, Any]:
    return {
        "allowed_source_kinds": sorted(ALLOWED_SOURCE_KINDS),
        "policy": (
            "Public OSINT only: RSS/Atom feeds, SearXNG queries, public news APIs, "
            "and user-configured public web sources. No unauthorized surveillance, "
            "credential harvesting, private-account scraping, paywall bypassing, "
            "offensive SIGINT, or communication interception."
        ),
    }


# --- Sources ---

@app.post("/api/intelligence/sources")
async def create_source(payload: SourceCreate) -> dict[str, Any]:
    if payload.kind not in ALLOWED_SOURCE_KINDS:
        raise HTTPException(status_code=422, detail=f"source kind '{payload.kind}' is not allowed; permitted: {sorted(ALLOWED_SOURCE_KINDS)}")
    if payload.url:
        decision = validate_feed_url(payload.url)
        if not decision.allowed:
            raise HTTPException(status_code=422, detail=decision.reason)
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO intelligence_sources(name, kind, url, config)
            VALUES($1, $2, $3, $4::jsonb)
            ON CONFLICT(name) DO UPDATE SET kind=EXCLUDED.kind, url=EXCLUDED.url, config=EXCLUDED.config, updated_at=now()
            RETURNING id::text, name, kind, url, enabled, created_at
            """,
            payload.name, payload.kind, payload.url, json.dumps(payload.config),
        )
    return dict(row)


@app.get("/api/intelligence/sources")
async def list_sources() -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id::text, name, kind, url, enabled, created_at, updated_at FROM intelligence_sources ORDER BY name"
        )
    return [dict(r) for r in rows]


@app.delete("/api/intelligence/sources/{source_id}")
async def delete_source(source_id: UUID) -> dict[str, str]:
    p = await pool()
    async with p.acquire() as conn:
        deleted = await conn.fetchval("DELETE FROM intelligence_sources WHERE id=$1 RETURNING id::text", source_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="source not found")
    return {"deleted": deleted}


# --- Monitors ---

@app.post("/api/intelligence/monitors")
async def create_monitor(payload: MonitorCreate) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO intelligence_monitors(name, keywords, source_ids, schedule, enabled)
            VALUES($1, $2, $3::uuid[], $4, $5)
            RETURNING id::text, name, keywords, schedule, enabled, created_at
            """,
            payload.name,
            payload.keywords,
            [UUID(s) for s in payload.source_ids] if payload.source_ids else [],
            payload.schedule,
            payload.enabled,
        )
    return dict(row)


@app.get("/api/intelligence/monitors")
async def list_monitors() -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id::text, name, keywords, schedule, enabled, last_run_at, created_at, updated_at FROM intelligence_monitors ORDER BY name"
        )
    return [dict(r) for r in rows]


@app.delete("/api/intelligence/monitors/{monitor_id}")
async def delete_monitor(monitor_id: UUID) -> dict[str, str]:
    p = await pool()
    async with p.acquire() as conn:
        deleted = await conn.fetchval("DELETE FROM intelligence_monitors WHERE id=$1 RETURNING id::text", monitor_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="monitor not found")
    return {"deleted": deleted}


# --- Findings ---

@app.post("/api/intelligence/monitors/{monitor_id}/run")
async def run_monitor(monitor_id: UUID) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        monitor = await conn.fetchrow("SELECT * FROM intelligence_monitors WHERE id=$1", monitor_id)
        if not monitor:
            raise HTTPException(status_code=404, detail="monitor not found")

        keywords = list(monitor["keywords"])
        source_ids = list(monitor["source_ids"]) if monitor["source_ids"] else []

        sources = []
        if source_ids:
            sources = await conn.fetch("SELECT * FROM intelligence_sources WHERE id = ANY($1::uuid[]) AND enabled=true", source_ids)
        else:
            sources = await conn.fetch("SELECT * FROM intelligence_sources WHERE enabled=true")

    findings = []
    for source in sources:
        try:
            new_findings = await _fetch_source(source, keywords)
            findings.extend(new_findings)
        except Exception:
            pass

    p = await pool()
    async with p.acquire() as conn:
        for f in findings:
            await conn.execute(
                """
                INSERT INTO intelligence_findings(monitor_id, source_id, title, url, snippet, relevance, raw)
                VALUES($1, $2, $3, $4, $5, $6, $7::jsonb)
                ON CONFLICT DO NOTHING
                """,
                monitor_id, f["source_id"], f["title"], f["url"], f["snippet"], f["relevance"], json.dumps(f.get("raw", {})),
            )
        await conn.execute("UPDATE intelligence_monitors SET last_run_at=now(), updated_at=now() WHERE id=$1", monitor_id)

    return {"monitor_id": str(monitor_id), "findings_count": len(findings), "findings": findings}


@app.get("/api/intelligence/findings")
async def list_findings(
    monitor_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        if monitor_id:
            rows = await conn.fetch(
                """
                SELECT f.id::text, f.monitor_id::text, f.source_id::text, f.title, f.url, f.snippet,
                       f.relevance, f.starred, f.dismissed, f.created_at
                FROM intelligence_findings f WHERE f.monitor_id=$1
                ORDER BY f.created_at DESC LIMIT $2
                """,
                UUID(monitor_id), limit,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT f.id::text, f.monitor_id::text, f.source_id::text, f.title, f.url, f.snippet,
                       f.relevance, f.starred, f.dismissed, f.created_at
                FROM intelligence_findings f ORDER BY f.created_at DESC LIMIT $1
                """,
                limit,
            )
    return [dict(r) for r in rows]


# --- Briefings ---

@app.post("/api/intelligence/briefings/generate")
async def generate_briefing(payload: BriefingGenerate) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        if payload.monitor_ids:
            monitor_uuids = [UUID(m) for m in payload.monitor_ids]
            findings = await conn.fetch(
                """
                SELECT f.* FROM intelligence_findings f
                WHERE f.monitor_id = ANY($1::uuid[]) AND f.dismissed = false
                ORDER BY f.created_at DESC LIMIT 100
                """,
                monitor_uuids,
            )
        else:
            findings = await conn.fetch(
                """
                SELECT f.* FROM intelligence_findings f
                WHERE f.dismissed = false
                ORDER BY f.created_at DESC LIMIT 100
                """,
            )

        title = payload.title or f"Briefing — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        briefing_id = await conn.fetchval(
            """
            INSERT INTO intelligence_briefings(title, finding_count, status)
            VALUES($1, $2, 'complete')
            RETURNING id
            """,
            title, len(findings),
        )
        for f in findings:
            await conn.execute(
                """
                INSERT INTO intelligence_briefing_items(briefing_id, finding_id, title, url, snippet, relevance)
                VALUES($1, $2, $3, $4, $5, $6)
                """,
                briefing_id, f["id"], f["title"], f["url"], f["snippet"], f["relevance"],
            )

    return {
        "briefing_id": str(briefing_id),
        "title": title,
        "finding_count": len(findings),
    }


@app.get("/api/intelligence/briefings")
async def list_briefings(limit: int = Query(default=25, ge=1, le=100)) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id::text, title, finding_count, status, created_at FROM intelligence_briefings ORDER BY created_at DESC LIMIT $1",
            limit,
        )
    return [dict(r) for r in rows]


@app.get("/api/intelligence/briefings/{briefing_id}")
async def get_briefing(briefing_id: UUID) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        briefing = await conn.fetchrow(
            "SELECT id::text, title, finding_count, status, created_at FROM intelligence_briefings WHERE id=$1",
            briefing_id,
        )
        if not briefing:
            raise HTTPException(status_code=404, detail="briefing not found")
        items = await conn.fetch(
            """
            SELECT id::text, finding_id::text, title, url, snippet, relevance, created_at
            FROM intelligence_briefing_items WHERE briefing_id=$1 ORDER BY relevance DESC, created_at ASC
            """,
            briefing_id,
        )
    return {**dict(briefing), "items": [dict(i) for i in items]}


# --- SearXNG search ---

@app.post("/api/intelligence/search")
async def search_public(payload: dict[str, Any]) -> dict[str, Any]:
    query = payload.get("query", "")
    try:
        query = sanitize_query(query)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    categories = payload.get("categories", "general,news")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{SEARXNG_URL}/search",
                params={"q": query, "format": "json", "categories": categories},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"SearXNG search failed: {type(exc).__name__}")

    results = []
    for r in data.get("results", [])[:50]:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
            "source": r.get("engine", "searxng"),
            "published": r.get("publishedDate"),
        })
    return {"query": query, "result_count": len(results), "results": results}


# --- Internal helpers ---

async def _fetch_source(source: asyncpg.Record, keywords: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    kind = source["kind"]
    url = source["url"]

    if kind in ("rss", "atom") and url:
        findings = await _fetch_rss(source, keywords)
    elif kind == "searxng":
        findings = await _fetch_searxng(source, keywords)

    return findings


async def _fetch_rss(source: asyncpg.Record, keywords: list[str]) -> list[dict[str, Any]]:
    import feedparser

    findings = []
    try:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "PersonalOS-Intelligence/0.1"}) as client:
            resp = await client.get(source["url"])
            resp.raise_for_status()
    except httpx.HTTPError:
        return []

    feed = feedparser.parse(resp.text)
    for entry in feed.entries[:100]:
        title = getattr(entry, "title", "")
        summary = getattr(entry, "summary", "")
        link = getattr(entry, "link", "")
        combined = f"{title} {summary}".lower()
        matched = [kw for kw in keywords if kw.lower() in combined]
        if matched:
            findings.append({
                "source_id": source["id"],
                "title": title[:512],
                "url": link[:2048],
                "snippet": summary[:1024],
                "relevance": min(len(matched) / max(len(keywords), 1), 1.0),
                "raw": {"matched_keywords": matched, "feed_title": feed.feed.get("title", "")},
            })
    return findings


async def _fetch_searxng(source: asyncpg.Record, keywords: list[str]) -> list[dict[str, Any]]:
    findings = []
    query = " ".join(keywords[:10])
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{SEARXNG_URL}/search",
                params={"q": query, "format": "json", "categories": "general,news"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError:
        return []

    for r in data.get("results", [])[:30]:
        title = r.get("title", "")
        content = r.get("content", "")
        combined = f"{title} {content}".lower()
        matched = [kw for kw in keywords if kw.lower() in combined]
        relevance = len(matched) / max(len(keywords), 1) if matched else 0.3
        findings.append({
            "source_id": source["id"],
            "title": title[:512],
            "url": r.get("url", "")[:2048],
            "snippet": content[:1024],
            "relevance": min(relevance, 1.0),
            "raw": {"engine": r.get("engine", ""), "matched_keywords": matched},
        })
    return findings
