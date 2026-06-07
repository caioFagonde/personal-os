from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .executor import execute_workflow_plan, outcome_to_dict
from .models import WorkflowSpec
from .n8n_bridge import normalize_n8n_webhook, verify_payload_signature
from .policy import evaluate_workflow_policy
from .scheduler import is_interval_due, next_interval_due
from .security import optional_principal, require_scope

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
N8N_WEBHOOK_SECRET = os.environ.get("N8N_WEBHOOK_SECRET", "local-dev-only-change-me")

app = FastAPI(title="Personal OS Automation Service", version="0.6.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_pool: asyncpg.Pool | None = None


@app.middleware("http")
async def require_service_auth(request: Request, call_next):
    if request.url.path in {"/health", "/openapi.json"} or request.url.path.startswith(("/docs", "/redoc")):
        return await call_next(request)
    principal = optional_principal(request.headers.get("authorization"))
    read_methods = {"GET", "HEAD", "OPTIONS"}
    require_scope(principal, "automation:read" if request.method in read_methods else "automation:write")
    request.state.principal = principal
    return await call_next(request)


class WorkflowCreate(BaseModel):
    spec: WorkflowSpec
    active: bool = False


class WorkflowPatch(BaseModel):
    spec: WorkflowSpec | None = None
    active: bool | None = None


class WorkflowRunCreate(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    approved_nodes: list[str] = Field(default_factory=list)
    idempotency_key: str | None = None
    trigger_event_id: str | None = None


class AutomationEventIn(BaseModel):
    topic: str = Field(min_length=1, max_length=240)
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="manual", max_length=120)
    idempotency_key: str | None = Field(default=None, max_length=160)


class ScheduleCreate(BaseModel):
    workflow_id: UUID
    every_seconds: int = Field(ge=10, le=31_536_000)
    enabled: bool = True
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    node_id: str | None = None
    approved: bool
    reason: str | None = None


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
    return {"status": "ok", "service": "automation-service"}


@app.get("/api/automation/policy")
async def policy_capabilities() -> dict[str, Any]:
    return {
        "max_nodes": 64,
        "max_timeout_seconds": 300,
        "forbidden_scopes": ["shell:raw", "filesystem:host-write", "network:scan", "privileged:container", "secrets:read"],
        "approval_required_for": ["command_request", "n8n_webhook", "external_http", "destructive", "approval_gate"],
    }


@app.post("/api/automation/workflows")
async def create_workflow(payload: WorkflowCreate, request: Request) -> dict[str, Any]:
    decision = evaluate_workflow_policy(payload.spec)
    if not decision.allowed:
        raise HTTPException(status_code=422, detail={"denials": decision.denials, "warnings": decision.warnings})
    p = await pool()
    async with p.acquire() as conn:
        workflow_id = await conn.fetchval(
            """
            INSERT INTO automation_workflows(name, description, spec, active, requires_approval, policy, created_by_device_id)
            VALUES($1,$2,$3::jsonb,$4,$5,$6::jsonb,$7::uuid)
            RETURNING id
            """,
            payload.spec.name,
            payload.spec.description,
            payload.spec.model_dump_json(by_alias=True),
            payload.active,
            decision.requires_approval,
            json.dumps(workflow_policy_to_dict(decision)),
            getattr(request.state, "principal", None).device_id if getattr(request.state, "principal", None) and getattr(request.state.principal, "device_id", None) else None,
        )
    return {"id": str(workflow_id), "active": payload.active, "policy": workflow_policy_to_dict(decision)}


@app.get("/api/automation/workflows")
async def list_workflows() -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, name, description, active, requires_approval, policy, created_at, updated_at
            FROM automation_workflows ORDER BY updated_at DESC, created_at DESC
            """
        )
    return [json_ready(dict(row)) for row in rows]


@app.get("/api/automation/workflows/{workflow_id}")
async def get_workflow(workflow_id: UUID) -> dict[str, Any]:
    row = await fetch_workflow_row(workflow_id)
    return json_ready(dict(row))


@app.patch("/api/automation/workflows/{workflow_id}")
async def patch_workflow(workflow_id: UUID, payload: WorkflowPatch) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM automation_workflows WHERE id=$1", workflow_id)
        if not row:
            raise HTTPException(status_code=404, detail="workflow not found")
        spec = payload.spec or parse_spec(row["spec"])
        decision = evaluate_workflow_policy(spec)
        if not decision.allowed:
            raise HTTPException(status_code=422, detail={"denials": decision.denials, "warnings": decision.warnings})
        active = row["active"] if payload.active is None else payload.active
        await conn.execute(
            """
            UPDATE automation_workflows
            SET name=$2, description=$3, spec=$4::jsonb, active=$5, requires_approval=$6, policy=$7::jsonb, updated_at=now()
            WHERE id=$1
            """,
            workflow_id,
            spec.name,
            spec.description,
            spec.model_dump_json(by_alias=True),
            active,
            decision.requires_approval,
            json.dumps(workflow_policy_to_dict(decision)),
        )
    return {"id": str(workflow_id), "active": active, "policy": workflow_policy_to_dict(decision)}


@app.post("/api/automation/workflows/{workflow_id}/runs")
async def run_workflow(workflow_id: UUID, payload: WorkflowRunCreate) -> dict[str, Any]:
    row = await fetch_workflow_row(workflow_id)
    spec = parse_spec(row["spec"])
    decision = evaluate_workflow_policy(spec)
    if not decision.allowed:
        raise HTTPException(status_code=422, detail={"denials": decision.denials})
    idem = payload.idempotency_key or hash_idempotency(workflow_id, payload.input)
    p = await pool()
    async with p.acquire() as conn:
        existing = await conn.fetchrow("SELECT id::text, status FROM automation_runs WHERE idempotency_key=$1", idem)
        if existing:
            return {"id": existing["id"], "status": existing["status"], "idempotent_replay": True}
        outcome = execute_workflow_plan(spec, payload.input, approved_nodes=set(payload.approved_nodes))
        run_id = await conn.fetchval(
            """
            INSERT INTO automation_runs(workflow_id, status, input, output, idempotency_key, trigger_event_id, started_at, finished_at)
            VALUES($1,$2,$3::jsonb,$4::jsonb,$5,$6::uuid,now(),CASE WHEN $2 IN ('succeeded','failed','cancelled') THEN now() ELSE NULL END)
            RETURNING id
            """,
            workflow_id,
            outcome.status,
            json.dumps(payload.input),
            json.dumps(outcome.output),
            idem,
            UUID(payload.trigger_event_id) if payload.trigger_event_id else None,
        )
        for step in outcome.steps:
            await insert_step(conn, run_id, step.node_id, step.status.value, step.output, step.error, step.requires_approval)
            if step.requires_approval:
                await conn.execute(
                    """
                    INSERT INTO automation_approvals(run_id, node_id, status, reason)
                    VALUES($1,$2,'pending',$3)
                    """,
                    run_id,
                    step.node_id,
                    step.output.get("reason", "approval required"),
                )
        await enqueue_side_effects(conn, run_id, outcome)
    return {"id": str(run_id), "status": outcome.status, "steps": [outcome_to_dict(step) for step in outcome.steps]}


@app.get("/api/automation/runs")
async def list_runs(workflow_id: UUID | None = None) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        if workflow_id:
            rows = await conn.fetch("SELECT id::text, workflow_id::text, status, input, output, started_at, finished_at FROM automation_runs WHERE workflow_id=$1 ORDER BY started_at DESC LIMIT 100", workflow_id)
        else:
            rows = await conn.fetch("SELECT id::text, workflow_id::text, status, input, output, started_at, finished_at FROM automation_runs ORDER BY started_at DESC LIMIT 100")
    return [json_ready(dict(r)) for r in rows]


@app.get("/api/automation/runs/{run_id}")
async def get_run(run_id: UUID) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        run = await conn.fetchrow("SELECT id::text, workflow_id::text, status, input, output, started_at, finished_at FROM automation_runs WHERE id=$1", run_id)
        if not run:
            raise HTTPException(status_code=404, detail="run not found")
        steps = await conn.fetch("SELECT node_id, status, output, error, requires_approval, started_at, finished_at FROM automation_run_steps WHERE run_id=$1 ORDER BY created_at ASC", run_id)
        approvals = await conn.fetch("SELECT node_id, status, reason, decided_at FROM automation_approvals WHERE run_id=$1 ORDER BY created_at ASC", run_id)
    return {"run": json_ready(dict(run)), "steps": [json_ready(dict(s)) for s in steps], "approvals": [json_ready(dict(a)) for a in approvals]}


@app.post("/api/automation/runs/{run_id}/approve")
async def approve_run_step(run_id: UUID, payload: ApprovalDecision) -> dict[str, str]:
    p = await pool()
    async with p.acquire() as conn:
        approval = await conn.fetchrow(
            """
            SELECT * FROM automation_approvals
            WHERE run_id=$1 AND status='pending' AND ($2::text IS NULL OR node_id=$2)
            ORDER BY created_at ASC LIMIT 1
            """,
            run_id,
            payload.node_id,
        )
        if not approval:
            raise HTTPException(status_code=404, detail="pending approval not found")
        new_status = "approved" if payload.approved else "denied"
        await conn.execute("UPDATE automation_approvals SET status=$2, reason=$3, decided_at=now() WHERE id=$1", approval["id"], new_status, payload.reason)
        await conn.execute(
            "UPDATE automation_run_steps SET status=$3, finished_at=now() WHERE run_id=$1 AND node_id=$2 AND status='pending_approval'",
            run_id,
            approval["node_id"],
            "succeeded" if payload.approved else "failed",
        )
        remaining = await conn.fetchval("SELECT COUNT(*) FROM automation_approvals WHERE run_id=$1 AND status='pending'", run_id)
        if remaining == 0:
            failed = await conn.fetchval("SELECT COUNT(*) FROM automation_approvals WHERE run_id=$1 AND status='denied'", run_id)
            await conn.execute("UPDATE automation_runs SET status=$2, finished_at=now() WHERE id=$1", run_id, "failed" if failed else "succeeded")
    return {"id": str(run_id), "approval": new_status}


@app.post("/api/automation/events")
async def ingest_event(payload: AutomationEventIn) -> dict[str, Any]:
    idem = payload.idempotency_key or hashlib.sha256(json.dumps({"topic": payload.topic, "payload": payload.payload}, sort_keys=True).encode()).hexdigest()
    p = await pool()
    async with p.acquire() as conn:
        event_id = await conn.fetchval(
            """
            INSERT INTO automation_events(topic, source, payload, idempotency_key)
            VALUES($1,$2,$3::jsonb,$4)
            ON CONFLICT(idempotency_key) DO UPDATE SET seen_count=automation_events.seen_count+1, last_seen_at=now()
            RETURNING id
            """,
            payload.topic,
            payload.source,
            json.dumps(payload.payload),
            idem,
        )
        workflows = await conn.fetch("SELECT id::text, spec FROM automation_workflows WHERE active=true")
    triggered = []
    for workflow in workflows:
        spec = parse_spec(workflow["spec"])
        if any(t.enabled and t.type.value == "event" and t.topic == payload.topic for t in spec.triggers):
            triggered.append(workflow["id"])
    return {"id": str(event_id), "triggered_workflows": triggered}


@app.get("/api/automation/events")
async def list_events(topic: str | None = None) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        if topic:
            rows = await conn.fetch("SELECT id::text, topic, source, payload, seen_count, created_at, last_seen_at FROM automation_events WHERE topic=$1 ORDER BY last_seen_at DESC LIMIT 100", topic)
        else:
            rows = await conn.fetch("SELECT id::text, topic, source, payload, seen_count, created_at, last_seen_at FROM automation_events ORDER BY last_seen_at DESC LIMIT 100")
    return [json_ready(dict(r)) for r in rows]


@app.post("/api/automation/schedules")
async def create_schedule(payload: ScheduleCreate) -> dict[str, Any]:
    row = await fetch_workflow_row(payload.workflow_id)
    p = await pool()
    async with p.acquire() as conn:
        schedule_id = await conn.fetchval(
            """
            INSERT INTO automation_schedules(workflow_id, every_seconds, enabled, payload, next_due_at)
            VALUES($1,$2,$3,$4::jsonb,now()) RETURNING id
            """,
            payload.workflow_id,
            payload.every_seconds,
            payload.enabled,
            json.dumps(payload.payload),
        )
    return {"id": str(schedule_id), "workflow_id": str(row["id"]), "enabled": payload.enabled}


@app.get("/api/automation/schedules/due")
async def due_schedules() -> list[dict[str, Any]]:
    p = await pool()
    due: list[dict[str, Any]] = []
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT id, workflow_id, every_seconds, payload, last_run_at FROM automation_schedules WHERE enabled=true")
        for row in rows:
            if is_interval_due(row["last_run_at"], row["every_seconds"]):
                next_due = next_interval_due(datetime.now(timezone.utc), row["every_seconds"])
                await conn.execute("UPDATE automation_schedules SET last_run_at=now(), next_due_at=$2 WHERE id=$1", row["id"], next_due)
                due.append({"id": str(row["id"]), "workflow_id": str(row["workflow_id"]), "payload": parse_json(row["payload"])})
    return due


@app.post("/api/automation/n8n/webhook")
async def n8n_webhook(request: Request) -> dict[str, Any]:
    payload = await request.json()
    signature = request.headers.get("x-personal-os-signature")
    if signature and not verify_payload_signature(payload, signature, N8N_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="invalid webhook signature")
    envelope = normalize_n8n_webhook(payload)
    event = AutomationEventIn(topic=envelope.event_type, payload=envelope.payload, source=envelope.source, idempotency_key=envelope.idempotency_key)
    result = await ingest_event(event)
    return {"event": result, "idempotency_key": envelope.idempotency_key}


async def fetch_workflow_row(workflow_id: UUID) -> asyncpg.Record:
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM automation_workflows WHERE id=$1", workflow_id)
    if not row:
        raise HTTPException(status_code=404, detail="workflow not found")
    return row


async def insert_step(conn: asyncpg.Connection, run_id: UUID, node_id: str, status: str, output: dict[str, Any], error: str | None, requires_approval: bool) -> None:
    await conn.execute(
        """
        INSERT INTO automation_run_steps(run_id, node_id, status, output, error, requires_approval, started_at, finished_at)
        VALUES($1,$2,$3,$4::jsonb,$5,$6,now(),CASE WHEN $3 <> 'pending_approval' THEN now() ELSE NULL END)
        """,
        run_id,
        node_id,
        status,
        json.dumps(output),
        error,
        requires_approval,
    )


async def enqueue_side_effects(conn: asyncpg.Connection, run_id: UUID, outcome) -> None:
    for step in outcome.steps:
        if step.status.value == "succeeded" and step.output.get("queued_side_effect"):
            await conn.execute(
                """
                INSERT INTO automation_outbox(run_id, node_id, kind, payload, status)
                VALUES($1,$2,$3,$4::jsonb,'queued')
                """,
                run_id,
                step.node_id,
                step.output.get("type", "side_effect"),
                json.dumps(step.output.get("config", {})),
            )


def parse_spec(raw: Any) -> WorkflowSpec:
    return WorkflowSpec.model_validate(parse_json(raw))


def parse_json(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def json_ready(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat()
        else:
            out[key] = parse_json(value)
    return out


def workflow_policy_to_dict(decision) -> dict[str, Any]:
    return {
        "allowed": decision.allowed,
        "requires_approval": decision.requires_approval,
        "denials": decision.denials,
        "warnings": decision.warnings,
        "required_scopes": decision.required_scopes,
        "nodes": [node.__dict__ for node in decision.node_decisions],
    }


def hash_idempotency(workflow_id: UUID, payload: dict[str, Any]) -> str:
    return hashlib.sha256(f"{workflow_id}:{json.dumps(payload, sort_keys=True, separators=(',', ':'))}".encode()).hexdigest()
