from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
app = FastAPI(title="Personal OS Sync Engine", version="0.1.0")
_pool: asyncpg.Pool | None = None

class SyncChange(BaseModel):
    event_id: str | None = None
    module_id: str
    entity_type: str
    entity_id: str | None = None
    external_id: str | None = None
    action: str = Field(pattern="^(create|update|delete|merge)$")
    merge_strategy: str = "lww"
    payload: dict[str, Any]
    vector_clock: dict[str, int] = Field(default_factory=dict)
    occurred_at: datetime | None = None

class PushRequest(BaseModel):
    device_key: str
    changes: list[SyncChange]

class PullRequest(BaseModel):
    device_key: str
    since_id: int = 0
    modules: list[str] | None = None

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
    return {"status": "ok", "service": "sync-engine"}

@app.get("/api/sync/health")
async def sync_health() -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        latest = await conn.fetchval("SELECT COALESCE(MAX(id),0) FROM sync_log")
    return {"status": "ok", "latest_sync_id": latest}

@app.post("/api/sync/push")
async def push(req: PushRequest) -> dict[str, Any]:
    p = await pool()
    accepted: list[int] = []
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, req.device_key)
        async with conn.transaction():
            for change in req.changes:
                checksum = hashlib.sha256(json.dumps(change.payload, sort_keys=True).encode()).hexdigest()
                entity_id = await upsert_entity(conn, change, device_id)
                version_id = await conn.fetchval("""
                    INSERT INTO entity_versions(entity_id, device_id, operation, merge_strategy, payload, checksum, version_clock, created_at)
                    VALUES($1,$2,$3,$4,$5::jsonb,$6,$7::jsonb,$8)
                    RETURNING id
                """, entity_id, device_id, change.action, change.merge_strategy, json.dumps(change.payload), checksum,
                    json.dumps(change.vector_clock), change.occurred_at or datetime.now(timezone.utc))
                await conn.execute("UPDATE entities SET current_version=$1, updated_at=now() WHERE id=$2", version_id, entity_id)
                sync_id = await conn.fetchval("""
                    INSERT INTO sync_log(module_id, entity_id, entity_type, version_id, device_id, action, payload, vector_clock, lamport, occurred_at)
                    VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,COALESCE((SELECT MAX(lamport)+1 FROM sync_log),1),$9)
                    RETURNING id
                """, change.module_id, entity_id, change.entity_type, version_id, device_id, change.action,
                    json.dumps(change.payload), json.dumps(change.vector_clock), change.occurred_at or datetime.now(timezone.utc))
                accepted.append(sync_id)
    return {"accepted": accepted, "count": len(accepted)}

@app.post("/api/sync/pull")
async def pull(req: PullRequest) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, req.device_key)
        if req.modules:
            rows = await conn.fetch("""
                SELECT id, module_id, entity_id, entity_type, action, payload, vector_clock, occurred_at
                FROM sync_log
                WHERE id > $1 AND module_id = ANY($2::text[]) AND (device_id IS NULL OR device_id <> $3)
                ORDER BY id ASC
                LIMIT 500
            """, req.since_id, req.modules, device_id)
        else:
            rows = await conn.fetch("""
                SELECT id, module_id, entity_id, entity_type, action, payload, vector_clock, occurred_at
                FROM sync_log
                WHERE id > $1 AND (device_id IS NULL OR device_id <> $2)
                ORDER BY id ASC
                LIMIT 500
            """, req.since_id, device_id)
    changes = [dict(r) for r in rows]
    cursor = max([req.since_id, *[r["id"] for r in rows]])
    return {"changes": changes, "cursor": cursor}

async def ensure_device(conn: asyncpg.Connection, device_key: str) -> UUID:
    profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
    return await conn.fetchval("""
        INSERT INTO devices(profile_id, device_key, name, kind, platform, trust_level, last_seen_at)
        VALUES($1,$2,$2,'other','unknown','trusted',now())
        ON CONFLICT(device_key) DO UPDATE SET last_seen_at=now()
        RETURNING id
    """, profile_id, device_key)

async def upsert_entity(conn: asyncpg.Connection, change: SyncChange, device_id: UUID) -> UUID:
    if change.entity_id:
        existing = await conn.fetchval("SELECT id FROM entities WHERE id=$1", UUID(change.entity_id))
        if existing:
            return existing
    return await conn.fetchval("""
        INSERT INTO entities(module_id, entity_type, external_id, created_by_device)
        VALUES($1,$2,$3,$4)
        ON CONFLICT(module_id, entity_type, external_id) DO UPDATE SET updated_at=now()
        RETURNING id
    """, change.module_id, change.entity_type, change.external_id, device_id)
