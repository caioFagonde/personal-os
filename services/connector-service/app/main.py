from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from .backup import create_backup_bundle
from .crypto import encrypt_text
from .oauth import OAuthConfig, build_authorization_start, token_endpoint, token_exchange_payload
from .providers import provider_status_from_env, publish_ntfy, send_twilio_whatsapp, twilio_message_payload

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
ROOT_DIR = Path(os.environ.get("PERSONAL_OS_ROOT", "/workspace"))
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/workspace/backups"))
CONNECTOR_PUBLIC_BASE_URL = os.environ.get("CONNECTOR_PUBLIC_BASE_URL", os.environ.get("VITE_API_URL", "http://localhost:8080"))
CONNECTOR_INTERNAL_BASE_URL = os.environ.get("CONNECTOR_INTERNAL_BASE_URL", "http://connector-service:8094")
OUTBOX_DRAIN_LIMIT = int(os.environ.get("OUTBOX_DRAIN_LIMIT", "25"))
SEND_CONNECTOR_TESTS = os.environ.get("SEND_CONNECTOR_TESTS", "false").lower() in {"1", "true", "yes"}

app = FastAPI(title="Personal OS Connector Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_pool: asyncpg.Pool | None = None


class ConnectorTestRequest(BaseModel):
    recipient: str | None = None
    message: str = "Personal OS connector test"
    execute: bool = False


class OutboxDrainRequest(BaseModel):
    execute: bool = False
    limit: int = Field(default=25, ge=1, le=100)


class BackupExportRequest(BaseModel):
    include_runtime: bool = False


async def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("database pool not initialized")
    return _pool


@app.on_event("startup")
async def startup() -> None:
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)


@app.on_event("shutdown")
async def shutdown() -> None:
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
    statuses = [provider_status_from_env(env, p).__dict__ for p in ["google", "microsoft", "twilio", "ntfy", "tailscale"]]
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
    return {p: provider_status_from_env(env, p).__dict__ for p in ["google", "microsoft", "twilio", "ntfy", "tailscale"]}


@app.get("/api/connectors/{provider}/start")
async def oauth_start(provider: str, scopes: str | None = Query(default=None)) -> dict[str, Any]:
    provider = provider.lower()
    config = oauth_config(provider, requested_scopes=scopes.split(",") if scopes else None)
    start = build_authorization_start(config)
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
            list(row["scopes"]),
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
        await conn.execute("UPDATE connector_oauth_states SET consumed_at=now() WHERE id=$1", row["id"])
        await conn.execute(
            """
            INSERT INTO connector_health_checks(provider, status, message, checked_at)
            VALUES($1,'active','OAuth callback succeeded',now())
            """,
            provider,
        )
    return {"status": "connected", "provider": provider, "cloud_account_id": str(account_id), "scopes": list(row["scopes"])}


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


@app.get("/api/connectors/tailscale/status")
async def tailscale_status() -> dict[str, Any]:
    status = provider_status_from_env(dict(os.environ), "tailscale")
    return {**status.__dict__, "hostname": os.environ.get("TAILSCALE_HOSTNAME", "personal-os-dev")}


@app.post("/api/connectors/outbox/drain")
async def drain_outbox(payload: OutboxDrainRequest) -> dict[str, Any]:
    p = await pool()
    processed: list[dict[str, Any]] = []
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, channel, connector, recipient, subject, body, attempts
            FROM message_outbox
            WHERE status='queued' AND next_attempt_at <= now()
            ORDER BY created_at ASC
            LIMIT $1
            """,
            min(payload.limit, OUTBOX_DRAIN_LIMIT),
        )
        for row in rows:
            outcome = await process_outbox_row(dict(row), execute=payload.execute)
            status = "sent" if outcome["status"] in {"sent", "dry_run"} else "failed"
            await conn.execute(
                """
                UPDATE message_outbox
                SET status=$2, attempts=attempts+1, updated_at=now(), metadata=metadata || $3::jsonb
                WHERE id=$1
                """,
                row["id"],
                status,
                json.dumps({"last_connector_result": outcome}),
            )
            await conn.execute(
                """
                INSERT INTO message_deliveries(outbox_id, provider_message_id, status, response)
                VALUES($1,$2,$3,$4::jsonb)
                """,
                row["id"],
                outcome.get("provider_message_id"),
                outcome["status"],
                json.dumps(outcome),
            )
            processed.append({"id": str(row["id"]), **outcome})
    return {"processed": processed, "count": len(processed), "execute": payload.execute}


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
    manifest = create_backup_bundle(ROOT_DIR, BACKUP_DIR, include=include)
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
