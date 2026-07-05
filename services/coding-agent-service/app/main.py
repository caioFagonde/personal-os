from __future__ import annotations

import json
import os
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import graph
from .policy import evaluate_prompt, safe_branch_slug
from .runner import claude_available, git_available, run_coding_job

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
DEFAULT_REPO_PATH = os.environ.get("CODING_AGENT_REPO_PATH", "/workspace")
WORKTREE_ROOT = os.environ.get("CODING_AGENT_WORKTREE_ROOT", "/workspace/.agent-worktrees")
CLAUDE_CODE_COMMAND = os.environ.get("CLAUDE_CODE_COMMAND", "claude")
CODING_AGENT_EXECUTE = os.environ.get("CODING_AGENT_EXECUTE", "false").lower() in {"1", "true", "yes"}
ALLOWED_REPO_ROOTS = [p for p in os.environ.get("CODING_AGENT_ALLOWED_REPO_ROOTS", DEFAULT_REPO_PATH).split(":") if p]

app = FastAPI(title="Personal OS Coding Agent Service", version="0.14.0")
# CORS origins are configurable via env (comma-separated). "*" is the local-dev
# default; restrict to the gateway origin(s) on any non-tailnet deployment.
CORS_ALLOW_ORIGINS = [o.strip() for o in os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()] or ["*"]
app.add_middleware(CORSMiddleware, allow_origins=CORS_ALLOW_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_pool: asyncpg.Pool | None = None


class CodingJobCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    prompt: str = Field(min_length=8, max_length=20_000)
    mode: str = Field(default="feature", pattern="^(analyze|fix|feature|tests|docs|refactor)$")
    repo_path: str | None = None
    requester_device_key: str = "web"
    auto_approve: bool = False


class ApprovalRequest(BaseModel):
    approved_by: str = "web"
    reason: str | None = None


class RunRequest(BaseModel):
    execute: bool | None = None
    timeout_seconds: int = Field(default=900, ge=30, le=7200)


async def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("database pool not initialized")
    return _pool


@app.on_event("startup")
async def startup() -> None:
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)


@app.on_event("shutdown")
async def shutdown() -> None:
    if _pool:
        await _pool.close()


@app.get("/health")
async def health() -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok", "service": "coding-agent-service", "claude_available": claude_available(CLAUDE_CODE_COMMAND), "execute": CODING_AGENT_EXECUTE}


@app.get("/api/coding-agent/status")
async def status() -> dict[str, Any]:
    return {
        "service": "coding-agent-service",
        "execute_enabled": CODING_AGENT_EXECUTE,
        "claude_command": CLAUDE_CODE_COMMAND,
        "claude_available": claude_available(CLAUDE_CODE_COMMAND),
        "git_available": git_available(),
        "default_repo_path": DEFAULT_REPO_PATH,
        "worktree_root": WORKTREE_ROOT,
        "allowed_repo_roots": ALLOWED_REPO_ROOTS,
        "safety": {
            "worktree_isolation": True,
            "approval_required": True,
            "secrets_scrubbed_from_env": True,
            "no_commit_or_push_without_explicit_prompt": True,
        },
    }


@app.post("/api/coding-agent/jobs")
async def create_job(payload: CodingJobCreate) -> dict[str, Any]:
    repo_path = payload.repo_path or DEFAULT_REPO_PATH
    decision = evaluate_prompt(prompt=payload.prompt, mode=payload.mode, repo_path=repo_path, allowed_roots=ALLOWED_REPO_ROOTS)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail={"status": "blocked", "reason": decision.reason})
    status_value = "queued" if payload.auto_approve else "pending_approval"
    branch_name = f"agent/{safe_branch_slug(payload.title)}"
    p = await pool()
    async with p.acquire() as conn:
        job_id = await conn.fetchval(
            """
            INSERT INTO coding_agent_jobs(title, prompt, mode, repo_path, branch_name, requester_device_key, status, requires_approval, approved_at, policy)
            VALUES($1,$2,$3,$4,$5,$6,$7,true,CASE WHEN $8 THEN now() ELSE NULL END,$9::jsonb)
            RETURNING id
            """,
            payload.title,
            payload.prompt,
            payload.mode,
            repo_path,
            branch_name,
            payload.requester_device_key,
            status_value,
            payload.auto_approve,
            json.dumps({"decision": decision.reason, "allowed_roots": ALLOWED_REPO_ROOTS}),
        )
        job_obj = await graph.register_object(
            conn, kind="agent_run", domain_table="coding_agent_jobs", domain_id=job_id,
            title=payload.title, status=status_value, meta={"mode": payload.mode, "branch": branch_name},
        )
        await graph.upsert_chunks(conn, job_obj, [f"{payload.title}\n\n{payload.prompt}"])
    return {"id": str(job_id), "status": status_value, "requires_approval": not payload.auto_approve, "branch_name": branch_name}


@app.get("/api/coding-agent/jobs")
async def list_jobs(limit: int = 25) -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, title, mode, repo_path, branch_name, status, requester_device_key, created_at, updated_at, approved_at, last_run_at
            FROM coding_agent_jobs ORDER BY created_at DESC LIMIT $1
            """,
            min(max(limit, 1), 100),
        )
    return [dict(r) for r in rows]


@app.get("/api/coding-agent/jobs/{job_id}")
async def get_job(job_id: UUID) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        job = await conn.fetchrow("SELECT * FROM coding_agent_jobs WHERE id=$1", job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        runs = await conn.fetch("SELECT * FROM coding_agent_runs WHERE job_id=$1 ORDER BY started_at DESC LIMIT 10", job_id)
    out = dict(job)
    out["id"] = str(out["id"])
    out["runs"] = [serialize_run(r) for r in runs]
    return out


@app.post("/api/coding-agent/jobs/{job_id}/approve")
async def approve_job(job_id: UUID, payload: ApprovalRequest) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("UPDATE coding_agent_jobs SET status='queued', approved_at=now(), approved_by=$2, updated_at=now() WHERE id=$1 RETURNING id::text, status", job_id, payload.approved_by)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    return dict(row)


@app.post("/api/coding-agent/jobs/{job_id}/run")
async def run_job(job_id: UUID, payload: RunRequest) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        job = await conn.fetchrow("SELECT * FROM coding_agent_jobs WHERE id=$1", job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        if job["status"] == "pending_approval":
            raise HTTPException(status_code=409, detail="job requires approval before execution")
        await conn.execute("UPDATE coding_agent_jobs SET status='running', last_run_at=now(), updated_at=now() WHERE id=$1", job_id)
    execute = CODING_AGENT_EXECUTE if payload.execute is None else bool(payload.execute)
    result = run_coding_job(
        job_id=str(job_id),
        title=job["title"],
        prompt=job["prompt"],
        mode=job["mode"],
        repo_path=job["repo_path"],
        worktree_root=WORKTREE_ROOT,
        execute=execute,
        timeout_seconds=payload.timeout_seconds,
        command=CLAUDE_CODE_COMMAND,
    )
    p = await pool()
    async with p.acquire() as conn:
        run_id = await conn.fetchval(
            """
            INSERT INTO coding_agent_runs(job_id, status, command, worktree_path, stdout, stderr, exit_code, artifacts, started_at, finished_at)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8::jsonb,now(),now()) RETURNING id
            """,
            job_id,
            result.status,
            result.command,
            result.worktree_path,
            result.stdout,
            result.stderr,
            result.exit_code,
            json.dumps(result.artifacts),
        )
        job_status = "completed" if result.status in {"succeeded", "dry_run"} else "failed"
        await conn.execute("UPDATE coding_agent_jobs SET status=$2, updated_at=now() WHERE id=$1", job_id, job_status)
        await graph.register_object(
            conn, kind="agent_run", domain_table="coding_agent_jobs", domain_id=job_id,
            title=job["title"], status=job_status, meta={"last_run_id": str(run_id), "last_run_status": result.status},
        )
    return {"run_id": str(run_id), "status": result.status, "execute": execute, "worktree_path": result.worktree_path, "stdout": result.stdout, "stderr": result.stderr, "artifacts": result.artifacts}


def serialize_run(row: asyncpg.Record) -> dict[str, Any]:
    out = dict(row)
    out["id"] = str(out["id"])
    out["job_id"] = str(out["job_id"])
    return out
