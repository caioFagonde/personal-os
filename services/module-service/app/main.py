from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
app = FastAPI(title="Personal OS Module Service", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_pool: asyncpg.Pool | None = None


class StudyItemIn(BaseModel):
    device_key: str = "module-service"
    title: str
    kind: str = "reading"
    source_ref: str | None = None
    status: str = "queued"
    due_at: datetime | None = None
    priority: int = Field(default=3, ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class StudyItemPatch(BaseModel):
    device_key: str = "module-service"
    title: str | None = None
    status: str | None = None
    due_at: datetime | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    progress: float | None = Field(default=None, ge=0, le=100)
    tags: list[str] | None = None
    payload: dict[str, Any] | None = None


class StudySessionIn(BaseModel):
    device_key: str = "module-service"
    item_id: UUID | None = None
    duration_minutes: int = Field(ge=0)
    notes: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class FlashcardIn(BaseModel):
    device_key: str = "module-service"
    item_id: UUID | None = None
    note_id: UUID | None = None
    concept: str
    question: str
    answer: str


class FlashcardReview(BaseModel):
    device_key: str = "module-service"
    quality: int = Field(ge=0, le=5)


class NoteIn(BaseModel):
    device_key: str = "module-service"
    title: str
    body: str = ""
    note_type: str = "permanent"
    tags: list[str] = Field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None
    frontmatter: dict[str, Any] = Field(default_factory=dict)


class NotePatch(BaseModel):
    device_key: str = "module-service"
    title: str | None = None
    body: str | None = None
    note_type: str | None = None
    tags: list[str] | None = None
    latitude: float | None = None
    longitude: float | None = None
    frontmatter: dict[str, Any] | None = None


class GeoMemoryIn(BaseModel):
    device_key: str = "module-service"
    title: str
    description: str | None = None
    memory_type: str = "poi"
    latitude: float
    longitude: float
    altitude: float | None = None
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


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
    return {"status": "ok", "service": "module-service"}


# Study -----------------------------------------------------------------------
@app.get("/api/study/items")
async def list_study_items(status: str | None = None, due_before: datetime | None = None) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, entity_id::text, title, kind, source_ref, status, due_at, priority, tags, progress, payload, created_at, updated_at
            FROM study_items
            WHERE ($1::text IS NULL OR status=$1) AND ($2::timestamptz IS NULL OR due_at <= $2)
            ORDER BY COALESCE(due_at, now() + interval '100 years'), priority ASC, updated_at DESC
            """,
            status,
            due_before,
        )
    return [dict(r) for r in rows]


@app.post("/api/study/items")
async def create_study_item(payload: StudyItemIn) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, payload.device_key)
        entity_id = await create_entity(conn, "study", "study_item", None, device_id)
        row = await conn.fetchrow(
            """
            INSERT INTO study_items(entity_id, title, kind, source_ref, status, due_at, priority, tags, payload)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
            RETURNING id::text, entity_id::text, title, kind, source_ref, status, due_at, priority, tags, progress, payload, created_at, updated_at
            """,
            entity_id,
            payload.title,
            payload.kind,
            payload.source_ref,
            payload.status,
            payload.due_at,
            payload.priority,
            payload.tags,
            json.dumps(payload.payload),
        )
        await record_change(conn, device_id, "study", "study_item", entity_id, "create", dict(row))
    return dict(row)


@app.patch("/api/study/items/{item_id}")
async def patch_study_item(item_id: UUID, patch: StudyItemPatch) -> dict[str, Any]:
    updates: dict[str, Any] = {k: v for k, v in patch.model_dump().items() if k != "device_key" and v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="no changes supplied")
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, patch.device_key)
        current = await conn.fetchrow("SELECT * FROM study_items WHERE id=$1", item_id)
        if not current:
            raise HTTPException(status_code=404, detail="study item not found")
        merged = dict(current)
        merged.update(updates)
        row = await conn.fetchrow(
            """
            UPDATE study_items SET title=$2, status=$3, due_at=$4, priority=$5, progress=$6, tags=$7, payload=$8::jsonb, updated_at=now()
            WHERE id=$1
            RETURNING id::text, entity_id::text, title, kind, source_ref, status, due_at, priority, tags, progress, payload, created_at, updated_at
            """,
            item_id,
            merged["title"],
            merged["status"],
            merged["due_at"],
            merged["priority"],
            merged["progress"],
            merged["tags"],
            json.dumps(merged["payload"]),
        )
        await record_change(conn, device_id, "study", "study_item", row["entity_id"], "update", dict(row))
    return dict(row)


@app.post("/api/study/sessions")
async def create_study_session(payload: StudySessionIn) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, payload.device_key)
        row = await conn.fetchrow(
            """
            INSERT INTO study_sessions(item_id, device_id, ended_at, duration_minutes, notes, metrics)
            VALUES($1,$2,now(),$3,$4,$5::jsonb)
            RETURNING id::text, item_id::text, device_id::text, started_at, ended_at, duration_minutes, notes, metrics
            """,
            payload.item_id,
            device_id,
            payload.duration_minutes,
            payload.notes,
            json.dumps(payload.metrics),
        )
    return dict(row)


@app.post("/api/study/flashcards")
async def create_flashcard(payload: FlashcardIn) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        await ensure_device(conn, payload.device_key)
        row = await conn.fetchrow(
            """
            INSERT INTO flashcards(item_id, note_id, concept, question, answer)
            VALUES($1,$2,$3,$4,$5)
            RETURNING id::text, item_id::text, note_id::text, concept, question, answer, interval_days, ease_factor, repetitions, due_at
            """,
            payload.item_id,
            payload.note_id,
            payload.concept,
            payload.question,
            payload.answer,
        )
    return dict(row)


@app.post("/api/study/flashcards/{card_id}/review")
async def review_flashcard(card_id: UUID, payload: FlashcardReview) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        await ensure_device(conn, payload.device_key)
        card = await conn.fetchrow("SELECT * FROM flashcards WHERE id=$1", card_id)
        if not card:
            raise HTTPException(status_code=404, detail="flashcard not found")
        interval, ef, reps = sm2(payload.quality, int(card["interval_days"]), float(card["ease_factor"]), int(card["repetitions"]))
        due = datetime.now(timezone.utc) + timedelta(days=interval)
        row = await conn.fetchrow(
            """
            UPDATE flashcards SET interval_days=$2, ease_factor=$3, repetitions=$4, due_at=$5, updated_at=now()
            WHERE id=$1
            RETURNING id::text, concept, interval_days, ease_factor, repetitions, due_at
            """,
            card_id,
            interval,
            ef,
            reps,
            due,
        )
    return dict(row)


# Zettelkasten ----------------------------------------------------------------
@app.get("/api/zettelkasten/notes")
async def list_notes(tag: str | None = None, search: str | None = None) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, entity_id::text, title, slug, note_type, body, tags, frontmatter, ST_Y(geom::geometry) AS latitude, ST_X(geom::geometry) AS longitude, created_at, updated_at
            FROM notes
            WHERE ($1::text IS NULL OR $1 = ANY(tags))
              AND ($2::text IS NULL OR title ILIKE '%' || $2 || '%' OR body ILIKE '%' || $2 || '%')
            ORDER BY updated_at DESC LIMIT 200
            """,
            tag,
            search,
        )
    return [dict(r) for r in rows]


@app.post("/api/zettelkasten/notes")
async def create_note(payload: NoteIn) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, payload.device_key)
        entity_id = await create_entity(conn, "zettelkasten", "note", None, device_id)
        slug = await unique_slug(conn, payload.title)
        row = await conn.fetchrow(
            """
            INSERT INTO notes(entity_id, title, slug, body, note_type, tags, geom, frontmatter)
            VALUES(
              $1,$2,$3,$4,$5,$6,
              CASE WHEN $7::double precision IS NULL OR $8::double precision IS NULL
                   THEN NULL
                   ELSE ST_SetSRID(ST_MakePoint($7,$8),4326)::geography
              END,
              $9::jsonb
            )
            RETURNING id::text, entity_id::text, title, slug, note_type, body, tags, frontmatter, ST_Y(geom::geometry) AS latitude, ST_X(geom::geometry) AS longitude, created_at, updated_at
            """,
            entity_id,
            payload.title,
            slug,
            payload.body,
            payload.note_type,
            payload.tags,
            payload.longitude,
            payload.latitude,
            json.dumps(payload.frontmatter),
        )
        await refresh_links(conn, UUID(row["id"]), payload.body)
        await record_change(conn, device_id, "zettelkasten", "note", entity_id, "create", dict(row), strategy="crdt_text")
    return dict(row)


@app.get("/api/zettelkasten/notes/{note_id}")
async def get_note(note_id: UUID) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id::text, entity_id::text, title, slug, note_type, body, tags, frontmatter, ST_Y(geom::geometry) AS latitude, ST_X(geom::geometry) AS longitude, created_at, updated_at
            FROM notes WHERE id=$1
            """,
            note_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="note not found")
        links = await conn.fetch("SELECT target_note_id::text, target_title, link_type FROM zettel_links WHERE source_note_id=$1", note_id)
    out = dict(row)
    out["links"] = [dict(link) for link in links]
    return out


@app.get("/api/zettelkasten/notes/{note_id}/obsidian")
async def export_obsidian(note_id: UUID) -> dict[str, str]:
    note = await get_note(note_id)
    fm = {"id": note["id"], "title": note["title"], "tags": note["tags"], **(note.get("frontmatter") or {})}
    frontmatter = "---\n" + "\n".join(f"{k}: {json.dumps(v) if isinstance(v, (list, dict)) else v}" for k, v in fm.items()) + "\n---\n\n"
    return {"filename": f"{note['slug']}.md", "markdown": frontmatter + note["body"]}


# Geospatial ------------------------------------------------------------------
@app.get("/api/geospatial/memories")
async def list_geo_memories(tag: str | None = None) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, entity_id::text, title, description, memory_type, tags, properties, ST_Y(geom::geometry) AS latitude, ST_X(geom::geometry) AS longitude, ST_Z(geom::geometry) AS altitude, created_at, updated_at
            FROM geospatial_memories
            WHERE ($1::text IS NULL OR $1 = ANY(tags))
            ORDER BY updated_at DESC LIMIT 500
            """,
            tag,
        )
    return [dict(r) for r in rows]


@app.post("/api/geospatial/memories")
async def create_geo_memory(payload: GeoMemoryIn) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, payload.device_key)
        entity_id = await create_entity(conn, "geospatial", "geospatial_memory", None, device_id)
        row = await conn.fetchrow(
            """
            INSERT INTO geospatial_memories(entity_id, title, description, memory_type, geom, tags, properties)
            VALUES($1,$2,$3,$4,ST_SetSRID(ST_MakePoint($5,$6,COALESCE($7,0)),4326)::geography,$8,$9::jsonb)
            RETURNING id::text, entity_id::text, title, description, memory_type, tags, properties, ST_Y(geom::geometry) AS latitude, ST_X(geom::geometry) AS longitude, ST_Z(geom::geometry) AS altitude, created_at, updated_at
            """,
            entity_id,
            payload.title,
            payload.description,
            payload.memory_type,
            payload.longitude,
            payload.latitude,
            payload.altitude,
            payload.tags,
            json.dumps(payload.properties),
        )
        await record_change(conn, device_id, "geospatial", "geospatial_memory", entity_id, "create", dict(row))
    return dict(row)


@app.get("/api/geospatial/nearby")
async def nearby(latitude: float = Query(...), longitude: float = Query(...), radius_m: int = Query(1000, ge=1, le=100000)) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, title, description, memory_type, tags, properties,
                   ST_Y(geom::geometry) AS latitude, ST_X(geom::geometry) AS longitude,
                   ST_Distance(geom, ST_SetSRID(ST_MakePoint($1,$2),4326)::geography) AS distance_m
            FROM geospatial_memories
            WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint($1,$2),4326)::geography, $3)
            ORDER BY distance_m ASC LIMIT 100
            """,
            longitude,
            latitude,
            radius_m,
        )
    return [dict(r) for r in rows]


# Helpers ---------------------------------------------------------------------
def sm2(quality: int, interval: int, ef: float, reps: int) -> tuple[int, float, int]:
    if quality >= 3:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = max(1, round(interval * ef))
        reps += 1
    else:
        reps = 0
        interval = 1
    ef = max(1.3, ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    return interval, round(ef, 2), reps


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
        RETURNING id
        """,
        module_id,
        entity_type,
        external_id,
        device_id,
    )


async def record_change(conn: asyncpg.Connection, device_id: UUID, module_id: str, entity_type: str, entity_id: str | UUID, action: str, payload: dict[str, Any], strategy: str = "field_merge") -> None:
    payload = jsonable(payload)
    checksum = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    version_id = await conn.fetchval(
        """
        INSERT INTO entity_versions(entity_id, device_id, operation, merge_strategy, payload, checksum, version_clock)
        VALUES($1,$2,$3,$4,$5::jsonb,$6,$7::jsonb) RETURNING id
        """,
        UUID(str(entity_id)),
        device_id,
        action,
        strategy,
        json.dumps(payload, default=str),
        checksum,
        json.dumps({str(device_id): int(datetime.now(timezone.utc).timestamp())}),
    )
    await conn.execute("UPDATE entities SET current_version=$1, updated_at=now() WHERE id=$2", version_id, UUID(str(entity_id)))
    await conn.execute(
        """
        INSERT INTO sync_log(module_id, entity_id, entity_type, version_id, device_id, action, payload, vector_clock, lamport)
        VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,COALESCE((SELECT MAX(lamport)+1 FROM sync_log),1))
        """,
        module_id,
        UUID(str(entity_id)),
        entity_type,
        version_id,
        device_id,
        action,
        json.dumps(payload, default=str),
        json.dumps({str(device_id): int(datetime.now(timezone.utc).timestamp())}),
    )


async def unique_slug(conn: asyncpg.Connection, title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "note"
    slug = base
    i = 2
    while await conn.fetchval("SELECT 1 FROM notes WHERE slug=$1", slug):
        slug = f"{base}-{i}"
        i += 1
    return slug


async def refresh_links(conn: asyncpg.Connection, note_id: UUID, body: str) -> None:
    await conn.execute("DELETE FROM zettel_links WHERE source_note_id=$1", note_id)
    for title in sorted(set(re.findall(r"\[\[([^\]]+)\]\]", body))):
        target = await conn.fetchval("SELECT id FROM notes WHERE lower(title)=lower($1) LIMIT 1", title)
        await conn.execute(
            """
            INSERT INTO zettel_links(source_note_id, target_note_id, target_title)
            VALUES($1,$2,$3) ON CONFLICT DO NOTHING
            """,
            note_id,
            target,
            title,
        )


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    if isinstance(value, (datetime, UUID)):
        return str(value)
    return value
