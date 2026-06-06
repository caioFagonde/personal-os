from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
app = FastAPI(title="Personal OS Command Bus", version="0.1.0")
_pool: asyncpg.Pool | None = None

class CommandRequestIn(BaseModel):
    requester_device_key: str
    target_device_key: str
    template_id: str
    scopes: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    signed_payload: str | None = None

@app.on_event("startup")
async def startup() -> None:
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)

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
    return {"status": "ok", "service": "command-bus"}

@app.post("/api/commands")
async def request_command(req: CommandRequestIn) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        template = await conn.fetchrow("SELECT * FROM command_templates WHERE id=$1", req.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="unknown command template")
        allowed = set(template["allowed_scopes"])
        requested = set(req.scopes)
        if not requested.issubset(allowed):
            raise HTTPException(status_code=403, detail="requested scopes exceed template allowlist")
        requester = await ensure_device(conn, req.requester_device_key, 'mobile')
        target = await ensure_device(conn, req.target_device_key, 'desktop')
        status = 'pending_approval' if template['requires_approval'] else 'queued'
        command_id = await conn.fetchval("""
            INSERT INTO command_requests(requester_device_id, target_device_id, template_id, status, scopes, signed_payload, params, expires_at)
            VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8)
            RETURNING id
        """, requester, target, req.template_id, status, req.scopes, req.signed_payload,
            __import__('json').dumps(req.params), datetime.now(timezone.utc) + timedelta(minutes=30))
        if status == 'pending_approval':
            profile_id = await conn.fetchval("SELECT profile_id FROM devices WHERE id=$1", requester)
            await conn.execute("""
                INSERT INTO approvals(profile_id, request_type, request_id, status, reason)
                VALUES($1,'command',$2,'pending','Command requires human approval')
            """, profile_id, command_id)
        await conn.execute("""
            INSERT INTO audit_log(device_id, action, target_type, target_id, metadata)
            VALUES($1,'command.requested','command_request',$2,$3::jsonb)
        """, requester, str(command_id), __import__('json').dumps({'template_id': req.template_id, 'scopes': req.scopes}))
    return {"id": str(command_id), "status": status}

@app.get("/api/commands/pending/{target_device_key}")
async def pending(target_device_key: str) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await conn.fetchval("SELECT id FROM devices WHERE device_key=$1", target_device_key)
        if not device_id:
            return {"commands": []}
        rows = await conn.fetch("""
            SELECT id, template_id, status, scopes, params, requested_at
            FROM command_requests
            WHERE target_device_id=$1 AND status IN ('approved','queued')
            ORDER BY requested_at ASC
            LIMIT 25
        """, device_id)
    return {"commands": [dict(r) for r in rows]}

async def ensure_device(conn: asyncpg.Connection, device_key: str, kind: str):
    profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
    return await conn.fetchval("""
        INSERT INTO devices(profile_id, device_key, name, kind, platform, trust_level, last_seen_at)
        VALUES($1,$2,$2,$3,'unknown','trusted',now())
        ON CONFLICT(device_key) DO UPDATE SET last_seen_at=now()
        RETURNING id
    """, profile_id, device_key, kind)
