from __future__ import annotations

import asyncio
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field

from .backup import BackupConfigurationError, backup_setup_status, create_backup_bundle
from .crypto import encrypt_text
from .oauth import (
    OAuthConfig,
    build_authorization_start,
    device_authorization_endpoint,
    device_authorization_payload,
    device_token_payload,
    normalize_scopes,
    token_endpoint,
    token_exchange_payload,
)
from .providers import (
    provider_status_from_env,
    publish_ntfy,
    send_twilio_whatsapp,
    twilio_message_payload,
    validate_obsidian_vault_path,
)
from .worker import ConnectorWorker, WorkerConfig, run_worker_forever

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
ROOT_DIR = Path(os.environ.get("PERSONAL_OS_ROOT", "/workspace"))
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/workspace/backups"))
CONNECTOR_PUBLIC_BASE_URL = os.environ.get("CONNECTOR_PUBLIC_BASE_URL", os.environ.get("VITE_API_URL", "http://localhost:8080"))
CONNECTOR_INTERNAL_BASE_URL = os.environ.get("CONNECTOR_INTERNAL_BASE_URL", "http://connector-service:8094")
OUTBOX_DRAIN_LIMIT = int(os.environ.get("OUTBOX_DRAIN_LIMIT", "25"))
SEND_CONNECTOR_TESTS = os.environ.get("SEND_CONNECTOR_TESTS", "false").lower() in {"1", "true", "yes"}
CONNECTOR_WORKER_ENABLED = os.environ.get("CONNECTOR_WORKER_ENABLED", "false").lower() in {"1", "true", "yes"}
CONNECTOR_WORKER_EXECUTE = os.environ.get("CONNECTOR_WORKER_EXECUTE", "false").lower() in {"1", "true", "yes"}
CONNECTOR_WORKER_INTERVAL_SECONDS = float(os.environ.get("CONNECTOR_WORKER_INTERVAL_SECONDS", "20"))
PROVIDERS = ("google", "microsoft", "twilio", "ntfy", "tailscale", "obsidian", "notion", "trello")

app = FastAPI(title="Personal OS Connector Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_pool: asyncpg.Pool | None = None
_worker_task: asyncio.Task | None = None
_worker_stop: asyncio.Event | None = None


class ConnectorTestRequest(BaseModel):
    recipient: str | None = None
    message: str = "Personal OS connector test"
    execute: bool = False


class OutboxDrainRequest(BaseModel):
    execute: bool = False
    limit: int = Field(default=25, ge=1, le=100)


class BackupExportRequest(BaseModel):
    include_runtime: bool = False


class DeviceFlowPollRequest(BaseModel):
    device_code: str = Field(min_length=8)


class ObsidianExportRequest(BaseModel):
    relative_path: str = Field(min_length=3, examples=["Zettelkasten/202606081200 Example.md"])
    content: str = Field(default="", max_length=2_000_000)
    execute: bool = False


class ObsidianImportRequest(BaseModel):
    relative_path: str = Field(min_length=3, examples=["Zettelkasten/202606081200 Example.md"])
    execute: bool = False


class ObsidianPathValidationRequest(BaseModel):
    relative_path: str = Field(min_length=3, examples=["Zettelkasten/202606081200 Example.md"])


class NotionPageCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(default="", max_length=100_000)
    execute: bool = False


class NotionPageExportRequest(BaseModel):
    page_id: str | None = None
    execute: bool = False


class TrelloCardCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=100_000)
    labels: list[str] = Field(default_factory=list, max_length=50)
    execute: bool = False



@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import json
    from fastapi.responses import JSONResponse
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            return JSONResponse(status_code=exc.status_code, content={"error": detail})
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": "http_error", "message": str(detail)}})
    if isinstance(exc, asyncpg.exceptions.PostgresError):
        return JSONResponse(status_code=500, content={"error": {"code": "database_error", "message": "A database error occurred"}})
    return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "An unexpected error occurred"}})


async def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("database pool not initialized")
    return _pool


@app.on_event("startup")
async def startup() -> None:
    global _pool, _worker_task, _worker_stop
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    if CONNECTOR_WORKER_ENABLED:
        _worker_stop = asyncio.Event()
        worker = ConnectorWorker(_pool, root_dir=ROOT_DIR, backup_dir=BACKUP_DIR)
        _worker_task = asyncio.create_task(run_worker_forever(worker, execute=CONNECTOR_WORKER_EXECUTE, interval_seconds=CONNECTOR_WORKER_INTERVAL_SECONDS, stop_event=_worker_stop))


@app.on_event("shutdown")
async def shutdown() -> None:
    global _worker_task, _worker_stop
    if _worker_stop:
        _worker_stop.set()
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    if _pool:
        await _pool.close()


@app.get("/health")
async def health() -> dict[str, str]:
    p = await pool()
    async with p.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok", "service": "connector-service"}


@app.get("/api/connectors")
async def list_connectors() -> dict[str, Any]:
    env = dict(os.environ)
    statuses = [provider_status_from_env(env, p).__dict__ for p in PROVIDERS]
    p = await pool()
    async with p.acquire() as conn:
        accounts = await conn.fetch("SELECT provider, account_email, scopes, status, updated_at FROM cloud_accounts ORDER BY provider, updated_at DESC")
        stored = await conn.fetch("SELECT provider, status, settings FROM connector_accounts ORDER BY provider")
    return {
        "connectors": statuses,
        "cloud_accounts": [dict(r) for r in accounts],
        "connector_accounts": [dict(r) for r in stored],
        "requires_user_action": [s["id"] for s in statuses if not s["configured"]],
    }


@app.get("/api/connectors/status")
async def connector_status() -> dict[str, Any]:
    env = dict(os.environ)
    return {p: provider_status_from_env(env, p).__dict__ for p in PROVIDERS}


def missing_connector_config_detail(provider: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    current_env = dict(os.environ) if env is None else env
    status = provider_status_from_env(current_env, provider)
    missing = [key for key in status.required_env if not current_env.get(key)]
    missing_any_of = [list(group) for group in status.required_any_of if not any(current_env.get(key) for key in group)]
    return {
        "code": "connector_missing_configuration",
        "provider": provider,
        "status": "needs_configuration",
        "configured": False,
        "missing_config": missing,
        "missing_any_of": missing_any_of,
        "required_env": list(status.required_env),
        "required_any_of": [list(group) for group in status.required_any_of],
        "message": status.message,
        "action": "configure_server_environment",
    }


def require_connector_config(provider: str) -> dict[str, str]:
    env = dict(os.environ)
    if not provider_status_from_env(env, provider).configured:
        raise HTTPException(status_code=409, detail=missing_connector_config_detail(provider, env))
    return env


def dry_run_only_detail(provider: str, operation: str) -> dict[str, Any]:
    return {
        "code": "connector_dry_run_only",
        "provider": provider,
        "operation": operation,
        "status": "dry_run_only",
        "message": f"{provider.title()} {operation} is a contract-only dry-run and does not perform external writes.",
        "action": "review_dry_run",
    }


@app.get("/api/connectors/{provider}/setup/status")
async def provider_setup_status(provider: str) -> dict[str, Any]:
    try:
        status = provider_status_from_env(dict(os.environ), provider)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "unknown_connector", "provider": provider}) from exc
    return status.__dict__


def missing_oauth_client_detail(provider: str) -> dict[str, Any]:
    provider = provider.lower()
    if provider == "google":
        required = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"]
    elif provider == "microsoft":
        required = ["MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET", "MICROSOFT_REDIRECT_URI"]
    else:
        required = []
    return {
        "provider": provider,
        "status": "needs_oauth_client",
        "configured": False,
        "required_env": required,
        "message": f"{provider.title()} OAuth client is not configured. Set {', '.join(required)} in .env and restart connector-service.",
        "action": "configure_env",
    }



async def store_oauth_token_response(conn: asyncpg.Connection, *, provider: str, scopes: list[str], token_response: dict[str, Any]) -> dict[str, Any]:
    refresh_token = token_response.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=502, detail="provider did not return refresh_token; re-run consent with offline access")
    profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
    account_email = token_response.get("id_token_email") or token_response.get("email")
    account_id = await conn.fetchval(
        """
        INSERT INTO cloud_accounts(profile_id, provider, account_email, scopes, status)
        VALUES($1,$2,$3,$4,'active')
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        profile_id,
        provider,
        account_email,
        scopes,
    )
    if account_id is None:
        account_id = await conn.fetchval(
            """
            SELECT id FROM cloud_accounts WHERE profile_id=$1 AND provider=$2
            ORDER BY updated_at DESC LIMIT 1
            """,
            profile_id,
            provider,
        )
    await conn.execute(
        """
        INSERT INTO cloud_tokens(cloud_account_id, token_type, encrypted_token, key_version, expires_at, rotated_at)
        VALUES($1,'oauth_refresh',$2,$3,$4,now())
        """,
        account_id,
        encrypt_text(refresh_token),
        os.environ.get("TOKEN_ENCRYPTION_KEY_VERSION", "local-v1"),
        None,
    )
    await conn.execute("UPDATE cloud_accounts SET status='active', updated_at=now() WHERE id=$1", account_id)
    await conn.execute(
        """
        INSERT INTO connector_health_checks(provider, status, message, checked_at)
        VALUES($1,'active','OAuth credential stored',now())
        """,
        provider,
    )
    return {"status": "connected", "provider": provider, "cloud_account_id": str(account_id), "scopes": scopes}

@app.get("/api/connectors/{provider}/start")
async def oauth_start(provider: str, scopes: str | None = Query(default=None)) -> dict[str, Any]:
    provider = provider.lower()
    try:
        config = oauth_config(provider, requested_scopes=scopes.split(",") if scopes else None)
        start = build_authorization_start(config)
    except ValueError as exc:
        if provider in {"google", "microsoft"}:
            raise HTTPException(status_code=409, detail=missing_oauth_client_detail(provider)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO connector_oauth_states(provider, state, code_verifier, scopes, redirect_uri, expires_at)
            VALUES($1,$2,$3,$4,$5,$6)
            ON CONFLICT(state) DO UPDATE SET code_verifier=EXCLUDED.code_verifier, expires_at=EXCLUDED.expires_at
            """,
            provider,
            start.state,
            start.code_verifier,
            list(start.scopes),
            config.redirect_uri,
            datetime.now(timezone.utc) + timedelta(minutes=15),
        )
    return {
        "provider": provider,
        "authorization_url": start.authorization_url,
        "state": start.state,
        "expires_in_seconds": 900,
        "action": "open_browser",
    }


@app.get("/api/connectors/{provider}/open")
async def oauth_open(provider: str, scopes: str | None = Query(default=None)) -> RedirectResponse:
    start = await oauth_start(provider, scopes)
    return RedirectResponse(start["authorization_url"], status_code=302)


@app.get("/api/connectors/{provider}/callback")
async def oauth_callback(provider: str, code: str | None = None, state: str | None = None, error: str | None = None, error_description: str | None = None) -> dict[str, Any]:
    provider = provider.lower()
    if error:
        raise HTTPException(status_code=400, detail={"error": error, "description": error_description})
    if not code or not state:
        raise HTTPException(status_code=400, detail="code and state are required")
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM connector_oauth_states
            WHERE provider=$1 AND state=$2 AND consumed_at IS NULL AND expires_at > now()
            """,
            provider,
            state,
        )
        if not row:
            raise HTTPException(status_code=400, detail="invalid or expired OAuth state")
        config = oauth_config(provider, requested_scopes=list(row["scopes"]))
        token_response = await exchange_code(config, code=code, code_verifier=row["code_verifier"])
        result = await store_oauth_token_response(conn, provider=provider, scopes=list(row["scopes"]), token_response=token_response)
        await conn.execute("UPDATE connector_oauth_states SET consumed_at=now() WHERE id=$1", row["id"])
    return result


@app.get("/api/connectors/{provider}/device/start")
async def oauth_device_start(provider: str, scopes: str | None = Query(default=None)) -> dict[str, Any]:
    provider = provider.lower()
    try:
        config = oauth_config(provider, requested_scopes=scopes.split(",") if scopes else None)
    except ValueError as exc:
        if provider in {"google", "microsoft"}:
            raise HTTPException(status_code=409, detail=missing_oauth_client_detail(provider)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not config.client_id:
        raise HTTPException(status_code=409, detail=missing_oauth_client_detail(provider))
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            device_authorization_endpoint(config.provider, config.tenant),
            data=device_authorization_payload(config),
            headers={"accept": "application/json"},
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail={"provider": provider, "status": resp.status_code, "body": resp.text[:1000]})
    data = resp.json()
    expires_in = int(data.get("expires_in", 900))
    interval = int(data.get("interval", 5))
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO connector_device_flows(provider, device_code, user_code, verification_uri, verification_uri_complete, scopes, interval_seconds, expires_at)
            VALUES($1,$2,$3,$4,$5,$6,$7,now() + ($8 || ' seconds')::interval)
            ON CONFLICT DO NOTHING
            """,
            provider,
            data.get("device_code"),
            data.get("user_code"),
            data.get("verification_uri") or data.get("verification_url"),
            data.get("verification_uri_complete"),
            list(normalize_scopes(provider, config.scopes)),
            interval,
            expires_in,
        )
    return {
        "provider": provider,
        "device_code": data.get("device_code"),
        "user_code": data.get("user_code"),
        "verification_uri": data.get("verification_uri") or data.get("verification_url"),
        "verification_uri_complete": data.get("verification_uri_complete"),
        "expires_in_seconds": expires_in,
        "interval_seconds": interval,
        "action": "open_device_code",
        "poll_url": f"/api/connectors/{provider}/device/poll",
    }


@app.post("/api/connectors/{provider}/device/poll")
async def oauth_device_poll(provider: str, payload: DeviceFlowPollRequest) -> dict[str, Any]:
    provider = provider.lower()
    config = oauth_config(provider)
    p = await pool()
    async with p.acquire() as conn:
        flow = await conn.fetchrow(
            """
            SELECT * FROM connector_device_flows
            WHERE provider=$1 AND device_code=$2 AND status='pending' AND expires_at > now()
            ORDER BY created_at DESC LIMIT 1
            """,
            provider,
            payload.device_code,
        )
        if not flow:
            raise HTTPException(status_code=404, detail="device flow not found or expired")
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            token_endpoint(config.provider, config.tenant),
            data=device_token_payload(config, device_code=payload.device_code),
            headers={"accept": "application/json"},
        )
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        error = data.get("error") if isinstance(data, dict) else None
        if error in {"authorization_pending", "slow_down"}:
            return {"status": error, "provider": provider, "interval_seconds": flow["interval_seconds"] + (5 if error == "slow_down" else 0)}
        raise HTTPException(status_code=502, detail={"provider": provider, "status": resp.status_code, "body": data})
    async with p.acquire() as conn:
        result = await store_oauth_token_response(conn, provider=provider, scopes=list(flow["scopes"]), token_response=data)
        await conn.execute("UPDATE connector_device_flows SET status='connected', consumed_at=now() WHERE id=$1", flow["id"])
    return result

@app.post("/api/connectors/twilio/test")
async def test_twilio(payload: ConnectorTestRequest) -> dict[str, Any]:
    env = os.environ
    status = provider_status_from_env(dict(env), "twilio")
    recipient = payload.recipient or env.get("SECRETARY_WHATSAPP")
    if not status.configured:
        return {"status": "needs_configuration", "configured": False, "message": status.message}
    if not recipient:
        return {"status": "needs_recipient", "configured": True, "message": "Set SECRETARY_WHATSAPP or pass recipient"}
    msg_payload = twilio_message_payload(
        to=recipient,
        body=payload.message,
        from_=env.get("TWILIO_WHATSAPP_FROM"),
        messaging_service_sid=env.get("TWILIO_MESSAGING_SERVICE_SID") or None,
    )
    if not payload.execute and not SEND_CONNECTOR_TESTS:
        return {"status": "dry_run", "provider": "twilio", "payload": {k: ("***" if k in {"Body"} else v) for k, v in msg_payload.items()}}
    result = await send_twilio_whatsapp(account_sid=env["TWILIO_ACCOUNT_SID"], auth_token=env["TWILIO_AUTH_TOKEN"], payload=msg_payload)
    return {"status": "sent", "provider": "twilio", "sid": result.get("sid"), "response": result}


@app.post("/api/connectors/ntfy/test")
async def test_ntfy(payload: ConnectorTestRequest) -> dict[str, Any]:
    env = os.environ
    status = provider_status_from_env(dict(env), "ntfy")
    if not status.configured:
        return {"status": "needs_configuration", "configured": False, "message": status.message}
    if not payload.execute and not SEND_CONNECTOR_TESTS:
        return {"status": "dry_run", "provider": "ntfy", "topic": env.get("NTFY_TOPIC")}
    result = await publish_ntfy(base_url=env["NTFY_BASE_URL"], topic=env["NTFY_TOPIC"], message=payload.message, title="Personal OS")
    return {"status": "sent", "provider": "ntfy", "response": result}


def validate_obsidian_request_path(env: dict[str, str], relative_path: str) -> Path:
    try:
        _, target = validate_obsidian_vault_path(env["OBSIDIAN_VAULT_PATH"], relative_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_obsidian_path",
                "provider": "obsidian",
                "status": "invalid_path",
                "message": str(exc),
                "action": "choose_relative_markdown_path",
            },
        ) from exc
    return target


@app.post("/api/connectors/obsidian/path/validate")
async def obsidian_path_validate(payload: ObsidianPathValidationRequest) -> dict[str, Any]:
    env = require_connector_config("obsidian")
    validate_obsidian_request_path(env, payload.relative_path)
    return {
        "status": "valid",
        "provider": "obsidian",
        "relative_path": payload.relative_path,
        "format": "markdown",
        "contained_in_vault": True,
    }


@app.post("/api/connectors/obsidian/export")
async def obsidian_export(payload: ObsidianExportRequest) -> dict[str, Any]:
    env = require_connector_config("obsidian")
    target = validate_obsidian_request_path(env, payload.relative_path)
    result = {
        "status": "dry_run",
        "provider": "obsidian",
        "operation": "export",
        "relative_path": payload.relative_path,
        "format": "markdown",
        "content_bytes": len(payload.content.encode("utf-8")),
        "contained_in_vault": True,
    }
    if not payload.execute:
        return result
    target.parent.mkdir(parents=True, exist_ok=True)
    target = validate_obsidian_request_path(env, payload.relative_path)
    try:
        with target.open("x", encoding="utf-8") as note:
            note.write(payload.content)
    except FileExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "obsidian_note_exists",
                "provider": "obsidian",
                "relative_path": payload.relative_path,
                "message": "Refusing to overwrite an existing Obsidian note.",
                "action": "choose_new_relative_path",
            },
        ) from exc
    return {**result, "status": "written"}


@app.post("/api/connectors/obsidian/import")
async def obsidian_import(payload: ObsidianImportRequest) -> dict[str, Any]:
    env = require_connector_config("obsidian")
    validate_obsidian_request_path(env, payload.relative_path)
    if payload.execute:
        raise HTTPException(status_code=409, detail=dry_run_only_detail("obsidian", "import"))
    return {
        "status": "dry_run",
        "provider": "obsidian",
        "operation": "import",
        "relative_path": payload.relative_path,
        "format": "markdown",
        "contained_in_vault": True,
        "would_read": True,
    }


@app.post("/api/connectors/notion/pages/dry-run")
async def notion_page_create_dry_run(payload: NotionPageCreateRequest) -> dict[str, Any]:
    env = require_connector_config("notion")
    if payload.execute:
        raise HTTPException(status_code=409, detail=dry_run_only_detail("notion", "page_create"))
    target_key = "NOTION_DATABASE_ID" if env.get("NOTION_DATABASE_ID") else "NOTION_PAGE_ID"
    return {
        "status": "dry_run",
        "provider": "notion",
        "operation": "page_create",
        "title": payload.title,
        "content_bytes": len(payload.content.encode("utf-8")),
        "target": {"kind": "database" if target_key == "NOTION_DATABASE_ID" else "page", "source": target_key},
        "external_write": False,
    }


@app.post("/api/connectors/notion/export/dry-run")
async def notion_page_export_dry_run(payload: NotionPageExportRequest) -> dict[str, Any]:
    env = require_connector_config("notion")
    if payload.execute:
        raise HTTPException(status_code=409, detail=dry_run_only_detail("notion", "page_export"))
    if not payload.page_id and not env.get("NOTION_PAGE_ID"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "connector_missing_operation_configuration",
                "provider": "notion",
                "operation": "page_export",
                "missing_config": ["NOTION_PAGE_ID"],
                "message": "Pass page_id or set NOTION_PAGE_ID before exporting a Notion page.",
                "action": "configure_server_environment",
            },
        )
    return {
        "status": "dry_run",
        "provider": "notion",
        "operation": "page_export",
        "source": "request" if payload.page_id else "NOTION_PAGE_ID",
        "format": "structured_markdown",
        "external_read": False,
    }


@app.post("/api/connectors/trello/cards/dry-run")
async def trello_card_create_dry_run(payload: TrelloCardCreateRequest) -> dict[str, Any]:
    require_connector_config("trello")
    if payload.execute:
        raise HTTPException(status_code=409, detail=dry_run_only_detail("trello", "card_create"))
    return {
        "status": "dry_run",
        "provider": "trello",
        "operation": "card_create",
        "title": payload.title,
        "description_bytes": len(payload.description.encode("utf-8")),
        "label_count": len(payload.labels),
        "target": {"board": "TRELLO_BOARD_ID", "list": "TRELLO_LIST_ID"},
        "external_write": False,
    }


@app.get("/api/connectors/worker/status")
async def worker_status() -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        message_counts = await conn.fetch("SELECT status, COUNT(*) count FROM message_outbox GROUP BY status")
        automation_counts = await conn.fetch("SELECT status, COUNT(*) count FROM automation_outbox GROUP BY status")
        notification_counts = await conn.fetch("SELECT status, COUNT(*) count FROM notification_deliveries GROUP BY status")
    return {
        "enabled": CONNECTOR_WORKER_ENABLED,
        "execute": CONNECTOR_WORKER_EXECUTE,
        "interval_seconds": CONNECTOR_WORKER_INTERVAL_SECONDS,
        "message_outbox": {r["status"]: r["count"] for r in message_counts},
        "automation_outbox": {r["status"]: r["count"] for r in automation_counts},
        "notification_deliveries": {r["status"]: r["count"] for r in notification_counts},
    }


@app.post("/api/connectors/worker/tick")
async def worker_tick(payload: OutboxDrainRequest) -> dict[str, Any]:
    worker = ConnectorWorker(await pool(), root_dir=ROOT_DIR, backup_dir=BACKUP_DIR)
    result = await worker.tick(WorkerConfig(execute=payload.execute, limit=min(payload.limit, OUTBOX_DRAIN_LIMIT)))
    return {"count": result.count, "message_outbox": result.message_outbox, "automation_outbox": result.automation_outbox, "notifications": result.notifications, "execute": payload.execute}


@app.get("/api/connectors/tailscale/status")
async def tailscale_status() -> dict[str, Any]:
    status = provider_status_from_env(dict(os.environ), "tailscale")
    return {**status.__dict__, "hostname": os.environ.get("TAILSCALE_HOSTNAME", "personal-os-dev")}


@app.post("/api/connectors/outbox/drain")
async def drain_outbox(payload: OutboxDrainRequest) -> dict[str, Any]:
    worker = ConnectorWorker(await pool(), root_dir=ROOT_DIR, backup_dir=BACKUP_DIR)
    result = await worker.tick(WorkerConfig(execute=payload.execute, limit=min(payload.limit, OUTBOX_DRAIN_LIMIT)))
    return {
        "processed": result.message_outbox,
        "automation_outbox": result.automation_outbox,
        "notifications": result.notifications,
        "count": result.count,
        "execute": payload.execute,
    }


async def process_outbox_row(row: dict[str, Any], *, execute: bool) -> dict[str, Any]:
    connector = row["connector"]
    if connector in {"whatsapp.twilio", "whatsapp.twilio_sandbox"}:
        req = ConnectorTestRequest(recipient=row["recipient"], message=row["body"], execute=execute)
        return await test_twilio(req)
    if connector == "ntfy.local":
        req = ConnectorTestRequest(message=row["body"], execute=execute)
        return await test_ntfy(req)
    if connector in {"email.oauth_or_smtp", "gmail.oauth", "microsoft.mail"}:
        if not execute:
            return {"status": "dry_run", "provider": connector, "recipient": row["recipient"]}
        return {"status": "failed", "provider": connector, "message": "Email connector send worker requires Google/Microsoft OAuth account selection in Phase 10.1"}
    return {"status": "failed", "message": f"unsupported connector: {connector}"}


@app.post("/api/connectors/backup/export")
async def export_backup(payload: BackupExportRequest) -> dict[str, Any]:
    include = [".env.example", "modules", "docs", "scripts", "infra/postgres/migrations"]
    if payload.include_runtime:
        include += ["data/.gitkeep"]
    try:
        manifest = create_backup_bundle(ROOT_DIR, BACKUP_DIR, include=include)
    except BackupConfigurationError as exc:
        raise HTTPException(status_code=409, detail={"code": "backup_encryption_required", "message": str(exc), "action": "configure_backup_encryption"}) from exc
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO backup_manifests(backup_id, archive_path, sha256, included_paths, created_at)
            VALUES($1,$2,$3,$4,now())
            ON CONFLICT(backup_id) DO NOTHING
            """,
            manifest.backup_id,
            manifest.archive_path,
            manifest.sha256,
            list(manifest.included_paths),
        )
    return manifest.__dict__




class BackupUploadRequest(BaseModel):
    provider: str = Field(pattern="^(google|microsoft)$")
    include_runtime: bool = False


@app.post("/api/connectors/backup/export-upload")
async def export_and_upload_backup(payload: BackupUploadRequest) -> dict[str, Any]:
    include = [".env.example", "modules", "docs", "scripts", "infra/postgres/migrations"]
    if payload.include_runtime:
        include += ["data/.gitkeep"]
    try:
        manifest = create_backup_bundle(ROOT_DIR, BACKUP_DIR, include=include)
    except BackupConfigurationError as exc:
        raise HTTPException(status_code=409, detail={"code": "backup_encryption_required", "message": str(exc), "action": "configure_backup_encryption"}) from exc
    p = await pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO backup_manifests(backup_id, archive_path, sha256, included_paths, created_at)
            VALUES($1,$2,$3,$4,now())
            ON CONFLICT(backup_id) DO NOTHING
            """,
            manifest.backup_id,
            manifest.archive_path,
            manifest.sha256,
            list(manifest.included_paths),
        )
    worker = ConnectorWorker(p, root_dir=ROOT_DIR, backup_dir=BACKUP_DIR)
    upload = await worker.upload_backup(manifest, provider=payload.provider)
    return {"manifest": manifest.__dict__, "upload": upload}

@app.get("/api/connectors/backup/status")
async def backup_status() -> dict[str, Any]:
    return backup_setup_status(dict(os.environ))


@app.get("/api/connectors/backup/manifests")
async def backup_manifests() -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT backup_id, archive_path, sha256, included_paths, created_at FROM backup_manifests ORDER BY created_at DESC LIMIT 50")
    return [dict(r) for r in rows]


@app.post("/api/connectors/device-pairing")
async def create_pairing_code() -> dict[str, Any]:
    code = secrets.token_urlsafe(18)
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
        pairing_id = await conn.fetchval(
            """
            INSERT INTO device_pairing_codes(profile_id, code_hash, expires_at)
            VALUES($1, crypt($2, gen_salt('bf')), now() + interval '15 minutes')
            RETURNING id
            """,
            profile_id,
            code,
        )
    return {"pairing_id": str(pairing_id), "pairing_code": code, "expires_in_seconds": 900, "url": f"{CONNECTOR_PUBLIC_BASE_URL.rstrip('/')}/device-pairing?code={code}"}


@app.get("/api/connectors/device-pairing/qr")
async def pairing_qr(url: str) -> Response:
    import io
    import qrcode
    import qrcode.image.svg
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory)
    buf = io.BytesIO()
    img.save(buf)
    return Response(content=buf.getvalue(), media_type="image/svg+xml")


def oauth_config(provider: str, requested_scopes: list[str] | None = None) -> OAuthConfig:
    provider = provider.lower()
    if provider == "google":
        return OAuthConfig(provider="google", client_id=os.environ.get("GOOGLE_CLIENT_ID", ""), client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""), redirect_uri=os.environ.get("GOOGLE_REDIRECT_URI", f"{CONNECTOR_PUBLIC_BASE_URL}/api/proxy/connectors/api/connectors/google/callback"), scopes=tuple(requested_scopes or ()))
    if provider == "microsoft":
        return OAuthConfig(provider="microsoft", client_id=os.environ.get("MICROSOFT_CLIENT_ID", ""), client_secret=os.environ.get("MICROSOFT_CLIENT_SECRET", ""), redirect_uri=os.environ.get("MICROSOFT_REDIRECT_URI", f"{CONNECTOR_PUBLIC_BASE_URL}/api/proxy/connectors/api/connectors/microsoft/callback"), scopes=tuple(requested_scopes or ()), tenant=os.environ.get("MICROSOFT_TENANT", "common"))
    raise HTTPException(status_code=404, detail=f"unsupported connector provider: {provider}")


async def exchange_code(config: OAuthConfig, *, code: str, code_verifier: str) -> dict[str, Any]:
    data = token_exchange_payload(config, code=code, code_verifier=code_verifier)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(token_endpoint(config.provider, config.tenant), data=data, headers={"accept": "application/json"})
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail={"provider": config.provider, "token_endpoint_status": resp.status_code, "body": resp.text[:1000]})
    return resp.json()
