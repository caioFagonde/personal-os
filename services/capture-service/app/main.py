from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .delegation import Contact, ContactChannel, DelegationRule, build_delegation_messages
from .graph import link, object_id_for, register_object, set_project, upsert_chunks
from .parser import parse_capture_command, parse_note_frontmatter, task_title_from_body
from .tasking import follow_up_at, initial_task_status, priority_to_rank, stable_task_fingerprint

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
# Privacy invariant: no personal addresses are ever shipped as code defaults.
# Delegation to the 'secretary' contact fails closed with a structured 409
# (code=missing_channels, required_env=[SECRETARY_EMAIL, SECRETARY_WHATSAPP])
# until these are provided via the environment.
DEFAULT_SECRETARY_EMAIL = os.environ.get("SECRETARY_EMAIL", "")
DEFAULT_SECRETARY_WHATSAPP = os.environ.get("SECRETARY_WHATSAPP", "")
WHATSAPP_PROVIDER = os.environ.get("WHATSAPP_PROVIDER", "cloud_api")
log = logging.getLogger("capture-service")
app = FastAPI(title="Personal OS Capture Service", version="0.9.0")
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
        "error": {"code": "internal_error", "message": "An unexpected error occurred. Check capture-service logs."}
    })


class CaptureCreate(BaseModel):
    device_key: str = "capture-service"
    text: str
    source_kind: str = "quick_capture"
    source_id: str | None = None
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    create_note: bool = False


class TaskCreate(BaseModel):
    device_key: str = "capture-service"
    title: str
    body: str = ""
    status: str = "inbox"
    assignee_key: str | None = None
    due_at: datetime | None = None
    priority: int = Field(default=3, ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    source_kind: str = "manual"
    source_id: str | None = None


class TaskPatch(BaseModel):
    status: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    due_at: datetime | None = None
    completed_at: datetime | None = None
    project_id: UUID | None = None  # projects.id — links the task into the graph registry


class DelegationRequest(BaseModel):
    task_id: UUID
    target: str = "secretary"
    channels: list[str] = Field(default_factory=lambda: ["whatsapp", "email"])
    requires_approval: bool = False


class CaptureItemPatch(BaseModel):
    status: str = Field(pattern="^(inbox|triaged|archived)$")
    triaged_note_id: UUID | None = None


@app.on_event("startup")
async def startup() -> None:
    global _pool
    if not DEFAULT_SECRETARY_EMAIL and not DEFAULT_SECRETARY_WHATSAPP:
        log.warning(
            "SECRETARY_EMAIL / SECRETARY_WHATSAPP are not set. "
            "Delegation to the 'secretary' contact will fail closed with a structured 409 "
            "(code=missing_channels) until they are configured in .env and capture-service is restarted."
        )
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
    return {"status": "ok", "service": "capture-service"}


@app.post("/api/capture")
async def create_capture(payload: CaptureCreate) -> dict[str, Any]:
    command = parse_note_frontmatter(payload.frontmatter, payload.text) if payload.frontmatter else parse_capture_command(payload.text)
    title = task_title_from_body(command.body or payload.text)
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, payload.device_key)
        fingerprint = stable_task_fingerprint(payload.source_kind, payload.source_id, command.body or payload.text)
        capture = await conn.fetchrow(
            """
            INSERT INTO capture_items(device_id, source_kind, source_id, raw_text, parsed, fingerprint)
            VALUES($1,$2,$3,$4,$5::jsonb,$6)
            ON CONFLICT(fingerprint) DO UPDATE SET updated_at=now()
            RETURNING id::text, raw_text, parsed, source_kind, source_id, fingerprint, created_at
            """,
            device_id,
            payload.source_kind,
            payload.source_id,
            payload.text,
            json.dumps(command.__dict__, default=str),
            fingerprint,
        )
        task = await upsert_task_from_capture(conn, device_id, capture["id"], title, command)
        messages: list[dict[str, Any]] = []
        if command.is_delegation:
            messages = await delegate_task(conn, UUID(task["id"]), command.target or "secretary", command.channels or ["whatsapp", "email"], requires_approval=False)
        # Graph registry dual-write (best-effort; must never fail the capture).
        capture_obj = await register_object(
            conn, kind="capture_item", domain_table="capture_items", domain_id=capture["id"],
            title=title, status="inbox", tags=command.tags or [], meta={"source_kind": payload.source_kind},
        )
        await upsert_chunks(conn, capture_obj, [payload.text])
        task_obj = await register_object(
            conn, kind="task", domain_table="tasks", domain_id=task["id"],
            title=task["title"], status=task["status"], tags=list(task["tags"] or []), meta={"source_kind": "capture"},
        )
        await upsert_chunks(conn, task_obj, [f"{task['title']}\n\n{task['body'] or ''}".strip()])
        await link(conn, task_obj, capture_obj, "derived_from")
    return {"capture": dict(capture), "task": dict(task), "messages": messages}


@app.get("/api/capture/items")
async def list_capture_items(status: str = "inbox", limit: int = 200) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.id::text, c.raw_text, c.source_kind, c.status, c.triaged_note_id::text, c.created_at,
                   t.id::text AS task_id, t.status AS task_status, t.title AS task_title
            FROM capture_items c
            LEFT JOIN tasks t ON t.source_kind='capture' AND t.source_id = c.id::text
            WHERE ($1::text IS NULL OR $1 = 'all' OR c.status = $1)
            ORDER BY c.created_at DESC LIMIT $2
            """,
            status,
            min(max(limit, 1), 500),
        )
    return [dict(r) for r in rows]


@app.patch("/api/capture/items/{item_id}")
async def patch_capture_item(item_id: UUID, patch: CaptureItemPatch) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE capture_items SET status=$2, triaged_note_id=COALESCE($3, triaged_note_id), updated_at=now()
            WHERE id=$1
            RETURNING id::text, raw_text, source_kind, status, triaged_note_id::text, created_at
            """,
            item_id,
            patch.status,
            patch.triaged_note_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="capture item not found")
        # Keep the graph registry lifecycle in step (best-effort).
        await register_object(
            conn, kind="capture_item", domain_table="capture_items", domain_id=item_id,
            title=(row["raw_text"] or "").strip().splitlines()[0][:200] if row["raw_text"] else "Capture",
            status=row["status"],
        )
    return dict(row)


@app.get("/api/tasks")
async def list_tasks(status: str | None = None, assignee_key: str | None = None) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, title, body, status, assignee_key, due_at, follow_up_at, priority, tags, source_kind, source_id, created_at, updated_at, completed_at
            FROM tasks
            WHERE ($1::text IS NULL OR status=$1) AND ($2::text IS NULL OR assignee_key=$2)
            ORDER BY COALESCE(due_at, now() + interval '100 years'), priority ASC, updated_at DESC
            LIMIT 500
            """,
            status,
            assignee_key,
        )
    return [dict(r) for r in rows]


@app.post("/api/tasks")
async def create_task(payload: TaskCreate) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, payload.device_key)
        row = await conn.fetchrow(
            """
            INSERT INTO tasks(device_id,title,body,status,assignee_key,due_at,follow_up_at,priority,tags,source_kind,source_id)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            RETURNING id::text, title, body, status, assignee_key, due_at, follow_up_at, priority, tags, source_kind, source_id, created_at, updated_at
            """,
            device_id,
            payload.title,
            payload.body,
            payload.status,
            payload.assignee_key,
            payload.due_at,
            follow_up_at(payload.due_at),
            payload.priority,
            payload.tags,
            payload.source_kind,
            payload.source_id,
        )
        await record_task_event(conn, UUID(row["id"]), "task.created", {"status": payload.status})
        task_obj = await register_object(
            conn, kind="task", domain_table="tasks", domain_id=row["id"],
            title=row["title"], status=row["status"], tags=list(row["tags"] or []), meta={"source_kind": payload.source_kind},
        )
        await upsert_chunks(conn, task_obj, [f"{row['title']}\n\n{row['body'] or ''}".strip()])
    return dict(row)


@app.patch("/api/tasks/{task_id}")
async def patch_task(task_id: UUID, patch: TaskPatch) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        current = await conn.fetchrow("SELECT * FROM tasks WHERE id=$1", task_id)
        if not current:
            raise HTTPException(status_code=404, detail="task not found")
        status = patch.status or current["status"]
        priority = patch.priority or current["priority"]
        due_at = patch.due_at if patch.due_at is not None else current["due_at"]
        completed_at = patch.completed_at if patch.completed_at is not None else current["completed_at"]
        if status == "completed" and completed_at is None:
            completed_at = datetime.now(timezone.utc)
        row = await conn.fetchrow(
            """
            UPDATE tasks SET status=$2, priority=$3, due_at=$4, completed_at=$5, updated_at=now()
            WHERE id=$1
            RETURNING id::text, title, body, status, assignee_key, due_at, follow_up_at, priority, tags, source_kind, source_id, created_at, updated_at, completed_at
            """,
            task_id,
            status,
            priority,
            due_at,
            completed_at,
        )
        await record_task_event(conn, task_id, "task.updated", {"status": status, "priority": priority})
        # Keep the graph registry in step (best-effort).
        task_obj = await register_object(
            conn, kind="task", domain_table="tasks", domain_id=task_id,
            title=row["title"], status=row["status"], tags=list(row["tags"] or []),
        )
        if patch.project_id is not None:
            project_obj = await object_id_for(conn, "projects", patch.project_id)
            if project_obj is None:
                raise HTTPException(status_code=404, detail={
                    "code": "project_not_found",
                    "message": f"Project {patch.project_id} has no graph registry entry.",
                    "action": "Create the project first (POST /api/projects on module-service).",
                })
            await set_project(conn, task_obj, project_obj)
            await record_task_event(conn, task_id, "task.project_assigned", {"project_id": str(patch.project_id)})
    return dict(row)


@app.post("/api/delegations")
async def create_delegation(payload: DelegationRequest) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        messages = await delegate_task(conn, payload.task_id, payload.target, payload.channels, payload.requires_approval)
    return {"queued": len(messages), "messages": messages}


@app.get("/api/outbox")
async def list_outbox(status: str | None = None) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, task_id::text, channel, connector, recipient, subject, body, status, requires_approval, attempts, metadata, created_at, updated_at
            FROM message_outbox WHERE ($1::text IS NULL OR status=$1)
            ORDER BY created_at DESC LIMIT 500
            """,
            status,
        )
    return [dict(r) for r in rows]


@app.get("/api/routines")
async def routines() -> list[dict[str, str]]:
    return [
        {"id": "capture.followups", "cron": "*/30 * * * *", "purpose": "queue follow-up reminders for delegated tasks without acknowledgement"},
        {"id": "capture.outbox_retry", "cron": "*/5 * * * *", "purpose": "retry transient email/WhatsApp/ntfy failures with backoff"},
        {"id": "capture.daily_digest", "cron": "0 18 * * 1-5", "purpose": "send end-of-day task digest to the user"},
        {"id": "capture.weekly_review", "cron": "0 9 * * 6", "purpose": "prepare GTD-style weekly review from tasks, notes, and timeline"},
    ]


async def upsert_task_from_capture(conn: asyncpg.Connection, device_id: UUID, capture_id: str, title: str, command) -> asyncpg.Record:
    status = initial_task_status(command.target)
    non_contact_targets = {"self", "me", "note", "task", "todo", "capture"}
    assignee = command.target if command.target and command.target not in non_contact_targets else None
    row = await conn.fetchrow(
        """
        INSERT INTO tasks(device_id,title,body,status,assignee_key,due_at,follow_up_at,priority,tags,source_kind,source_id)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,'capture',$10)
        ON CONFLICT(source_kind, source_id) DO UPDATE SET updated_at=now()
        RETURNING id::text, title, body, status, assignee_key, due_at, follow_up_at, priority, tags, source_kind, source_id, created_at, updated_at
        """,
        device_id,
        title,
        command.body,
        status,
        assignee,
        command.due_at,
        follow_up_at(command.due_at),
        priority_to_rank(command.priority),
        command.tags,
        capture_id,
    )
    await record_task_event(conn, UUID(row["id"]), "task.captured", {"capture_id": capture_id, "status": status})
    return row


async def delegate_task(conn: asyncpg.Connection, task_id: UUID, target: str, channels: list[str], requires_approval: bool) -> list[dict[str, Any]]:
    task = await conn.fetchrow("SELECT * FROM tasks WHERE id=$1", task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    contact = await load_contact(conn, target)
    rule = DelegationRule(target=target, channels=channels or ["whatsapp", "email"], requires_approval=requires_approval)
    try:
        built = build_delegation_messages(
            task_id=str(task_id),
            title=task["title"],
            body=task["body"] or task["title"],
            contact=contact,
            rule=rule,
            requested_channels=channels,
            source_note_id=task["source_id"] if task["source_kind"] == "note" else None,
            whatsapp_provider=WHATSAPP_PROVIDER,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={
            "code": "invalid_delegation_config",
            "message": str(exc),
            "action": "Check WHATSAPP_PROVIDER env var. Supported: cloud_api, twilio, twilio_sandbox."
        })
    rows = []
    for msg in built:
        row = await conn.fetchrow(
            """
            INSERT INTO message_outbox(task_id, channel, connector, recipient, subject, body, status, requires_approval, metadata)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
            RETURNING id::text, task_id::text, channel, connector, recipient, subject, body, status, requires_approval, metadata, created_at
            """,
            task_id,
            msg.channel,
            msg.connector,
            msg.recipient,
            msg.subject,
            msg.body,
            "pending_approval" if msg.requires_approval else "queued",
            msg.requires_approval,
            json.dumps(msg.metadata),
        )
        rows.append(dict(row))
    await conn.execute("UPDATE tasks SET status='delegated', assignee_key=$2, updated_at=now() WHERE id=$1", task_id, target)
    await record_task_event(conn, task_id, "task.delegated", {"target": target, "channels": channels})
    return rows


async def load_contact(conn: asyncpg.Connection, key: str) -> Contact:
    row = await conn.fetchrow("SELECT key, display_name FROM contacts WHERE key=$1", key)
    if not row and key == "secretary":
        await conn.execute(
            """
            INSERT INTO contacts(key, display_name, role) VALUES('secretary','Secretary','assistant')
            ON CONFLICT(key) DO NOTHING
            """
        )
        if DEFAULT_SECRETARY_EMAIL:
            await conn.execute(
                "INSERT INTO contact_channels(contact_key, channel, address, verified) VALUES($1,$2,$3,true) ON CONFLICT DO NOTHING",
                "secretary",
                "email",
                DEFAULT_SECRETARY_EMAIL,
            )
        if DEFAULT_SECRETARY_WHATSAPP:
            await conn.execute(
                "INSERT INTO contact_channels(contact_key, channel, address, verified) VALUES($1,$2,$3,true) ON CONFLICT DO NOTHING",
                "secretary",
                "whatsapp",
                DEFAULT_SECRETARY_WHATSAPP,
            )
        row = await conn.fetchrow("SELECT key, display_name FROM contacts WHERE key=$1", key)
    if not row:
        raise HTTPException(status_code=404, detail={
            "code": "contact_not_found",
            "message": f"Contact '{key}' not found.",
            "action": "Create the contact in the database or set SECRETARY_EMAIL / SECRETARY_WHATSAPP in .env and restart capture-service."
        })
    channel_rows = await conn.fetch("SELECT channel, address, verified, metadata FROM contact_channels WHERE contact_key=$1", key)
    if not channel_rows:
        env_hint = []
        if key == "secretary":
            env_hint = ["SECRETARY_EMAIL", "SECRETARY_WHATSAPP"]
        raise HTTPException(status_code=409, detail={
            "code": "missing_channels",
            "message": f"Contact '{key}' has no communication channels configured.",
            "required_env": env_hint,
            "action": f"Set {' and/or '.join(env_hint) if env_hint else 'channel addresses'} in .env and restart capture-service."
        })
    return Contact(key=row["key"], display_name=row["display_name"], channels=[ContactChannel(c["channel"], c["address"], c["verified"], c["metadata"] or {}) for c in channel_rows])


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


async def record_task_event(conn: asyncpg.Connection, task_id: UUID, event_type: str, payload: dict[str, Any]) -> None:
    await conn.execute("INSERT INTO task_events(task_id, event_type, payload) VALUES($1,$2,$3::jsonb)", task_id, event_type, json.dumps(payload))
