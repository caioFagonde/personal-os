from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
import logging
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .analog import AnalogResult, process_analog_input
from .retention import ReviewState, desirable_difficulty, interleave_plan, reminder_schedule, sm2_plus
from .routines import recommended_routines

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
log = logging.getLogger("study-companion-service")
app = FastAPI(title="Personal OS Study Companion", version="0.9.0")
# CORS origins are configurable via env (comma-separated). "*" is the local-dev
# default; restrict to the gateway origin(s) on any non-tailnet deployment.
CORS_ALLOW_ORIGINS = [o.strip() for o in os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()] or ["*"]
app.add_middleware(CORSMiddleware, allow_origins=CORS_ALLOW_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_pool: asyncpg.Pool | None = None


@app.exception_handler(asyncpg.exceptions.PostgresError)
async def _pg_error(_request: Request, exc: asyncpg.exceptions.PostgresError) -> JSONResponse:
    log.exception("database error: %s", exc)
    return JSONResponse(status_code=500, content={
        "error": {"code": "database_error", "message": f"Database operation failed: {type(exc).__name__}"}
    })


@app.exception_handler(Exception)
async def _generic_error(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        raise exc
    log.exception("unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={
        "error": {"code": "internal_error", "message": "An unexpected error occurred. Check study-companion-service logs."}
    })


class TextCapture(BaseModel):
    device_key: str = "study-companion"
    title: str | None = None
    text: str
    tags: list[str] = Field(default_factory=list)
    create_zettel: bool = True
    create_learning_atoms: bool = True


class ReviewRequest(BaseModel):
    atom_id: UUID
    quality: int = Field(ge=0, le=5)
    confidence: float = Field(default=0.5, ge=0, le=1)
    time_seconds: int | None = Field(default=None, ge=0)


class LookupRequest(BaseModel):
    query: str
    source_capture_id: UUID | None = None
    spatial: dict[str, Any] = Field(default_factory=dict)


@app.on_event("startup")
async def startup() -> None:
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)


@app.on_event("shutdown")
async def shutdown() -> None:
    if _pool:
        await _pool.close()


async def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("database pool not initialized")
    return _pool


@app.get("/health")
async def health() -> dict[str, str]:
    p = await pool()
    async with p.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok", "service": "study-companion-service"}


@app.post("/api/study-companion/text")
async def ingest_text(payload: TextCapture) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, payload.device_key)
        title = payload.title or infer_title(payload.text)
        zettel_id = None
        if payload.create_zettel:
            zettel_id = await create_zettel(conn, device_id, title, payload.text, payload.tags + ["study", "capture"])
        atoms = []
        if payload.create_learning_atoms:
            for concept in extract_learning_atoms(payload.text):
                atoms.append(await create_learning_atom(conn, concept, payload.text[:500], zettel_id, payload.tags))
        reminders = [dt.isoformat() for dt in reminder_schedule(datetime.now(timezone.utc), "normal")]
    return {"title": title, "note_id": str(zettel_id) if zettel_id else None, "atoms": atoms, "reminders": reminders}


@app.post("/api/study-companion/analog")
async def ingest_analog(
    file: UploadFile = File(...),
    device_key: str = Form("study-companion"),
    text_hint: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
) -> dict[str, Any]:
    data = await file.read()
    if len(data) > int(os.environ.get("ANALOG_CAPTURE_MAX_BYTES", "52428800")):
        raise HTTPException(status_code=413, detail="capture too large")
    result = process_analog_input(file.filename or "capture.bin", data, file.content_type, text_hint)
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, device_key)
        row = await persist_analog_result(conn, device_id, result, file.filename or "capture.bin", latitude, longitude)
        note_id = await create_zettel(conn, device_id, result.zettel_candidate["title"], result.zettel_candidate["body"], result.zettel_candidate["tags"], latitude, longitude)
        atoms = []
        for query in result.lookup_queries[:3]:
            atoms.append(await create_learning_atom(conn, query, result.summary, note_id, result.suggested_tags))
        reading_item = None
        if result.reading_candidate:
            reading_item = await create_reading_item(conn, device_id, result.reading_candidate, row["id"])
    return {"capture": dict(row), "note_id": str(note_id), "learning_atoms": atoms, "reading_item": reading_item, "popup_note": result.summary, "lookup_queries": result.lookup_queries}


@app.post("/api/study-companion/reviews")
async def review_atom(payload: ReviewRequest) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        atom = await conn.fetchrow("SELECT * FROM learning_atoms WHERE id=$1", payload.atom_id)
        if not atom:
            raise HTTPException(status_code=404, detail="learning atom not found")
        state = ReviewState(atom["interval_days"], float(atom["ease_factor"]), atom["repetitions"], float(atom["stability"]), float(atom["difficulty"]))
        result = sm2_plus(payload.quality, state)
        mode = desirable_difficulty(payload.quality, payload.confidence, payload.time_seconds)
        row = await conn.fetchrow(
            """
            UPDATE learning_atoms SET interval_days=$2, ease_factor=$3, repetitions=$4, stability=$5, difficulty=$6, due_at=$7, updated_at=now()
            WHERE id=$1
            RETURNING id::text, concept, interval_days, ease_factor, repetitions, stability, difficulty, due_at
            """,
            payload.atom_id,
            result.interval_days,
            result.ease_factor,
            result.repetitions,
            result.stability,
            result.difficulty,
            result.due_at,
        )
        await conn.execute(
            "INSERT INTO review_events(atom_id, quality, confidence, time_seconds, mode, payload) VALUES($1,$2,$3,$4,$5,$6::jsonb)",
            payload.atom_id,
            payload.quality,
            payload.confidence,
            payload.time_seconds,
            mode,
            json.dumps(result.__dict__, default=str),
        )
    out = dict(row)
    out["mode"] = mode
    out["retention_probability"] = result.retention_probability
    out["rationale"] = result.rationale
    return out


@app.get("/api/study-companion/due")
async def due_reviews(limit: int = 100) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, concept, source_excerpt, tags, due_at, repetitions, stability, difficulty
            FROM learning_atoms WHERE due_at <= now() ORDER BY due_at ASC LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]


@app.post("/api/study-companion/lookup")
async def create_lookup(payload: LookupRequest) -> dict[str, Any]:
    summary = f"Lookup seed for: {payload.query}. Expand through Research for sources, citations, and related notes."
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO lookup_cards(query, source_capture_id, summary, spatial, status)
            VALUES($1,$2,$3,$4::jsonb,'queued')
            RETURNING id::text, query, source_capture_id::text, summary, spatial, status, created_at
            """,
            payload.query,
            payload.source_capture_id,
            summary,
            json.dumps(payload.spatial),
        )
    return dict(row)


@app.get("/api/study-companion/routines")
async def routines() -> list[dict[str, str]]:
    return recommended_routines()


@app.get("/api/study-companion/interleave-plan")
async def plan(tags: str = "", due_count: int = 5, new_count: int = 3) -> dict[str, Any]:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    return {"plan": interleave_plan(tag_list, due_count, new_count)}


async def persist_analog_result(conn: asyncpg.Connection, device_id: UUID, result: AnalogResult, filename: str, latitude: float | None, longitude: float | None) -> asyncpg.Record:
    row = await conn.fetchrow(
        """
        INSERT INTO analog_captures(device_id, filename, media_type, sha256, summary, suggested_tags, lookup_queries, geom, payload)
        VALUES($1,$2,$3,$4,$5,$6,$7,
          CASE WHEN $8::double precision IS NULL OR $9::double precision IS NULL THEN NULL ELSE ST_SetSRID(ST_MakePoint($9,$8),4326)::geography END,
          $10::jsonb)
        ON CONFLICT(sha256) DO UPDATE SET updated_at=now()
        RETURNING id::text, filename, media_type, sha256, summary, suggested_tags, lookup_queries, created_at, updated_at
        """,
        device_id,
        filename,
        result.media_type,
        result.sha256,
        result.summary,
        result.suggested_tags,
        result.lookup_queries,
        latitude,
        longitude,
        json.dumps({
            "detections": [d.__dict__ for d in result.detections],
            "ocr_blocks": [b.__dict__ for b in result.ocr_blocks],
            "zettel_candidate": result.zettel_candidate,
            "reading_candidate": result.reading_candidate,
        }),
    )
    for d in result.detections:
        await conn.execute("INSERT INTO vision_detections(capture_id,label,confidence,bbox) VALUES($1,$2,$3,$4::jsonb)", row["id"], d.label, d.confidence, json.dumps(d.bbox))
    for b in result.ocr_blocks:
        await conn.execute("INSERT INTO ocr_blocks(capture_id,text,confidence,bbox) VALUES($1,$2,$3,$4::jsonb)", row["id"], b.text, b.confidence, json.dumps(b.bbox))
    return row


async def create_zettel(conn: asyncpg.Connection, device_id: UUID, title: str, body: str, tags: list[str], latitude: float | None = None, longitude: float | None = None) -> UUID:
    entity_id = await create_entity(conn, "zettelkasten", "note", device_id)
    slug = await unique_slug(conn, title)
    return await conn.fetchval(
        """
        INSERT INTO notes(entity_id, title, slug, body, note_type, tags, geom, frontmatter)
        VALUES($1,$2,$3,$4,'literature',$5,
          CASE WHEN $6::double precision IS NULL OR $7::double precision IS NULL THEN NULL ELSE ST_SetSRID(ST_MakePoint($7,$6),4326)::geography END,
          $8::jsonb)
        RETURNING id
        """,
        entity_id,
        title,
        slug,
        body,
        tags,
        latitude,
        longitude,
        json.dumps({"created_by": "study-companion", "sync_strategy": "crdt_text"}),
    )


async def create_learning_atom(conn: asyncpg.Connection, concept: str, excerpt: str, note_id: UUID | None, tags: list[str]) -> dict[str, Any]:
    due = datetime.now(timezone.utc)
    row = await conn.fetchrow(
        """
        INSERT INTO learning_atoms(concept, source_excerpt, note_id, tags, due_at)
        VALUES($1,$2,$3,$4,$5)
        ON CONFLICT(concept, COALESCE(note_id, '00000000-0000-0000-0000-000000000000'::uuid)) DO UPDATE SET updated_at=now()
        RETURNING id::text, concept, due_at, tags
        """,
        concept[:240],
        excerpt,
        note_id,
        tags,
        due,
    )
    return dict(row)


async def create_reading_item(conn: asyncpg.Connection, device_id: UUID, candidate: dict[str, Any], capture_id: str) -> dict[str, Any]:
    entity_id = await create_entity(conn, "study", "study_item", device_id)
    row = await conn.fetchrow(
        """
        INSERT INTO study_items(entity_id,title,kind,source_ref,status,tags,payload)
        VALUES($1,$2,$3,$4,$5,$6,$7::jsonb)
        RETURNING id::text, title, kind, source_ref, status, tags, payload
        """,
        entity_id,
        candidate["title"],
        candidate.get("kind", "analog_reading"),
        f"analog_capture:{capture_id}",
        candidate.get("status", "queued"),
        ["analog", "reading"],
        json.dumps(candidate),
    )
    return dict(row)


async def create_entity(conn: asyncpg.Connection, module_id: str, entity_type: str, device_id: UUID) -> UUID:
    return await conn.fetchval(
        """
        INSERT INTO entities(module_id, entity_type, created_by_device)
        VALUES($1,$2,$3) RETURNING id
        """,
        module_id,
        entity_type,
        device_id,
    )


async def ensure_device(conn: asyncpg.Connection, device_key: str) -> UUID:
    profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
    if not profile_id:
        profile_id = await conn.fetchval("INSERT INTO profiles(handle, display_name) VALUES('default','Default') RETURNING id")
    return await conn.fetchval(
        """
        INSERT INTO devices(profile_id, device_key, name, kind, platform, last_seen_at)
        VALUES($1,$2,$2,'server','server',now())
        ON CONFLICT(device_key) DO UPDATE SET last_seen_at=now()
        RETURNING id
        """,
        profile_id,
        device_key,
    )


def extract_learning_atoms(text: str) -> list[str]:
    import re

    candidates = re.findall(r"\b[A-Z][a-zA-Z]{3,}(?:\s+[A-Z][a-zA-Z]{3,}){0,2}\b", text)
    lower_terms = re.findall(r"\b(?:retention|learning curve|spaced repetition|memory|concept|theorem|definition|algorithm|framework)\b", text, re.I)
    result = []
    for item in candidates + lower_terms:
        cleaned = " ".join(item.split())[:120]
        if cleaned and cleaned.lower() not in {r.lower() for r in result}:
            result.append(cleaned)
    return result[:12] or [infer_title(text)]


def infer_title(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        return lines[0][:120]
    return text[:80] or "Study capture"


async def unique_slug(conn: asyncpg.Connection, title: str) -> str:
    import re

    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80] or "note"
    slug = base
    i = 2
    while await conn.fetchval("SELECT 1 FROM notes WHERE slug=$1", slug):
        slug = f"{base}-{i}"
        i += 1
    return slug
