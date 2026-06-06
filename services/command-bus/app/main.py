from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .security import optional_principal, require_scope
from .signing import verify_signature as verify_command_signature

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
COMMAND_SIGNING_SECRET = os.environ.get("COMMAND_SIGNING_SECRET", "local-dev-only-change-me")
app = FastAPI(title="Personal OS Command Bus", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def require_service_auth(request: Request, call_next):
    if request.url.path in {"/health", "/openapi.json"} or request.url.path.startswith(("/docs", "/redoc")):
        return await call_next(request)
    principal = optional_principal(request.headers.get("authorization"))
    require_scope(principal, "command:read" if request.method == "GET" else "command:request")
    request.state.principal = principal
    return await call_next(request)
_pool: asyncpg.Pool | None = None


class CommandRequestIn(BaseModel):
    requester_device_key: str
    target_device_key: str
    template_id: str
    scopes: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    signed_payload: str | None = None


class ApprovalDecision(BaseModel):
    device_key: str
    reason: str | None = None


class CommandResultIn(BaseModel):
    device_key: str
    status: str = Field(pattern="^(running|succeeded|failed|cancelled)$")
    stdout_ref: str | None = None
    stderr_ref: str | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    exit_code: int | None = None


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


@app.get("/api/commands/templates")
async def templates() -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT id, name, description, command_kind, allowed_scopes, requires_approval, local_only, template FROM command_templates ORDER BY id")
    return [dict(r) for r in rows]


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
        if req.signed_payload and not verify_signature(req.params, req.signed_payload):
            raise HTTPException(status_code=401, detail="invalid command signature")
        requester = await ensure_device(conn, req.requester_device_key, "mobile")
        target = await ensure_device(conn, req.target_device_key, "desktop")
        status = "pending_approval" if template["requires_approval"] else "queued"
        command_id = await conn.fetchval(
            """
            INSERT INTO command_requests(requester_device_id, target_device_id, template_id, status, scopes, signed_payload, params, expires_at)
            VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8)
            RETURNING id
            """,
            requester,
            target,
            req.template_id,
            status,
            req.scopes,
            req.signed_payload,
            json.dumps(req.params),
            datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        if status == "pending_approval":
            profile_id = await conn.fetchval("SELECT profile_id FROM devices WHERE id=$1", requester)
            await conn.execute(
                """
                INSERT INTO approvals(profile_id, request_type, request_id, status, reason)
                VALUES($1,'command',$2,'pending','Command requires human approval')
                """,
                profile_id,
                command_id,
            )
        await audit(conn, requester, "command.requested", "command_request", str(command_id), {"template_id": req.template_id, "scopes": req.scopes})
    return {"id": str(command_id), "status": status}


@app.post("/api/commands/{command_id}/approve")
async def approve_command(command_id: UUID, decision: ApprovalDecision) -> dict[str, str]:
    return await decide(command_id, decision, "approved", "queued")


@app.post("/api/commands/{command_id}/deny")
async def deny_command(command_id: UUID, decision: ApprovalDecision) -> dict[str, str]:
    return await decide(command_id, decision, "denied", "denied")


@app.get("/api/commands/pending/{target_device_key}")
async def pending(target_device_key: str) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await conn.fetchval("SELECT id FROM devices WHERE device_key=$1", target_device_key)
        if not device_id:
            return {"commands": []}
        rows = await conn.fetch(
            """
            SELECT id::text, template_id, status, scopes, params, requested_at, expires_at
            FROM command_requests
            WHERE target_device_id=$1 AND status IN ('approved','queued') AND (expires_at IS NULL OR expires_at > now())
            ORDER BY requested_at ASC LIMIT 25
            """,
            device_id,
        )
    return {"commands": [dict(r) for r in rows]}


@app.post("/api/commands/{command_id}/results")
async def post_result(command_id: UUID, result: CommandResultIn) -> dict[str, str]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await conn.fetchval("SELECT id FROM devices WHERE device_key=$1", result.device_key)
        if not device_id:
            raise HTTPException(status_code=404, detail="device not registered")
        command = await conn.fetchrow("SELECT * FROM command_requests WHERE id=$1 AND target_device_id=$2", command_id, device_id)
        if not command:
            raise HTTPException(status_code=404, detail="command not found for target device")
        await conn.execute(
            """
            INSERT INTO command_results(command_request_id, status, stdout_ref, stderr_ref, artifacts, exit_code, started_at, finished_at)
            VALUES($1,$2,$3,$4,$5::jsonb,$6,CASE WHEN $2='running' THEN now() ELSE NULL END,CASE WHEN $2 <> 'running' THEN now() ELSE NULL END)
            """,
            command_id,
            result.status,
            result.stdout_ref,
            result.stderr_ref,
            json.dumps(result.artifacts),
            result.exit_code,
        )
        new_status = result.status if result.status != "running" else "running"
        await conn.execute("UPDATE command_requests SET status=$2 WHERE id=$1", command_id, new_status)
        await audit(conn, device_id, "command.result", "command_request", str(command_id), {"status": result.status})
    return {"status": "recorded"}


async def decide(command_id: UUID, decision: ApprovalDecision, approval_status: str, command_status: str) -> dict[str, str]:
    p = await pool()
    async with p.acquire() as conn:
        decider = await ensure_device(conn, decision.device_key, "desktop")
        row = await conn.fetchrow("SELECT * FROM approvals WHERE request_type='command' AND request_id=$1 AND status='pending'", command_id)
        if not row:
            raise HTTPException(status_code=404, detail="pending approval not found")
        await conn.execute("UPDATE approvals SET status=$2, reason=$3, decided_by_device_id=$4, decided_at=now() WHERE id=$1", row["id"], approval_status, decision.reason, decider)
        await conn.execute("UPDATE command_requests SET status=$2 WHERE id=$1", command_id, command_status)
        await audit(conn, decider, f"command.{approval_status}", "command_request", str(command_id), {"reason": decision.reason})
    return {"id": str(command_id), "status": command_status}


async def ensure_device(conn: asyncpg.Connection, device_key: str, kind: str):
    profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
    return await conn.fetchval(
        """
        INSERT INTO devices(profile_id, device_key, name, kind, platform, trust_level, last_seen_at)
        VALUES($1,$2,$2,$3,'unknown','trusted',now())
        ON CONFLICT(device_key) DO UPDATE SET last_seen_at=now()
        RETURNING id
        """,
        profile_id,
        device_key,
        kind,
    )


async def audit(conn: asyncpg.Connection, device_id: UUID, action: str, target_type: str, target_id: str, metadata: dict[str, Any]) -> None:
    await conn.execute(
        """
        INSERT INTO audit_log(device_id, action, target_type, target_id, metadata)
        VALUES($1,$2,$3,$4,$5::jsonb)
        """,
        device_id,
        action,
        target_type,
        target_id,
        json.dumps(metadata),
    )


def verify_signature(params: dict[str, Any], signature: str) -> bool:
    return verify_command_signature(params, signature, COMMAND_SIGNING_SECRET)
