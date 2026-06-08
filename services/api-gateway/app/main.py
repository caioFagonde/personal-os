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
import yaml
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config_validation import is_sensitive_key, public_setting, validate_setting
from .crypto import encrypt_text
from .observability import RedMetrics
from .release import release_manifest
from .security import (
    ACTIVE_JWT_KID,
    Principal,
    extract_bearer_token,
    issue_token,
    optional_principal,
    require_scope,
    token_hash,
)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
MODULES_DIR = Path(os.environ.get("MODULES_DIR", "/workspace/modules"))
SYNC_ENGINE_URL = os.environ.get("SYNC_ENGINE_URL", "http://sync-engine:8081")
MODULE_SERVICE_URL = os.environ.get("MODULE_SERVICE_URL", "http://module-service:8083")
COMMAND_BUS_URL = os.environ.get("COMMAND_BUS_URL", "http://command-bus:8082")
RESEARCH_SERVICE_URL = os.environ.get("RESEARCH_SERVICE_URL", "http://research-service:8084")
AUTOMATION_SERVICE_URL = os.environ.get("AUTOMATION_SERVICE_URL", "http://automation-service:8085")
DIGITAL_TWIN_SERVICE_URL = os.environ.get("DIGITAL_TWIN_SERVICE_URL", "http://digital-twin-service:8086")
CAPTURE_SERVICE_URL = os.environ.get("CAPTURE_SERVICE_URL", "http://capture-service:8087")
STUDY_COMPANION_SERVICE_URL = os.environ.get("STUDY_COMPANION_SERVICE_URL", "http://study-companion-service:8088")
CONNECTOR_SERVICE_URL = os.environ.get("CONNECTOR_SERVICE_URL", "http://connector-service:8094")
MODEL_RUNTIME_SERVICE_URL = os.environ.get("MODEL_RUNTIME_SERVICE_URL", "http://model-runtime:8095")
CODING_AGENT_SERVICE_URL = os.environ.get("CODING_AGENT_SERVICE_URL", "http://coding-agent-service:8096")
ACCESS_TOKEN_TTL_SECONDS = int(os.environ.get("ACCESS_TOKEN_TTL_SECONDS", "900"))
REFRESH_TOKEN_TTL_DAYS = int(os.environ.get("REFRESH_TOKEN_TTL_DAYS", "30"))
DEFAULT_DEVICE_SCOPES = [
    "device",
    "modules:read",
    "module:read",
    "module:write",
    "sync:read",
    "sync:write",
    "command:read",
    "command:request",
    "notifications:read",
    "research:read",
    "research:write",
    "automation:read",
    "automation:write",
    "digital_twin:read",
    "digital_twin:write",
    "recommendations:write",
    "capture:read",
    "capture:write",
    "tasks:read",
    "tasks:write",
    "delegation:write",
    "study_companion:read",
    "study_companion:write",
    "connectors:read",
    "connectors:write",
    "model_runtime:read",
    "model_runtime:write",
    "coding_agent:read",
    "coding_agent:write",
]

app = FastAPI(title="Personal OS API Gateway", version="0.7.0")
red_metrics = RedMetrics()
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
_pool: asyncpg.Pool | None = None


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> Response:
    from fastapi.responses import JSONResponse
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "http_error", "message": exc.detail}},
        )
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "An unexpected error occurred"}},
    )


class ModuleHealth(BaseModel):
    id: str
    name: str
    version: str
    health: str
    routes: dict[str, Any]
    permissions: list[str]
    events: dict[str, list[str]]
    sync: dict[str, Any]


class DeviceRegistration(BaseModel):
    device_key: str = Field(min_length=3, max_length=160)
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(default="other", pattern="^(mobile|desktop|web|server|other)$")
    platform: str = "unknown"
    public_key: str | None = None
    tailscale_ip: str | None = None
    app_version: str | None = None
    build_channel: str = "dev"
    requested_scopes: list[str] = Field(default_factory=list)


class AuthRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class AuthRevokeRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=32)
    revoke_device: bool = False


class CloudAccountCreate(BaseModel):
    provider: str = Field(pattern="^(google|microsoft)$")
    account_email: str | None = None
    scopes: list[str] = Field(default_factory=list)


class CloudTokenStore(BaseModel):
    refresh_token: str = Field(min_length=12)
    expires_at: datetime | None = None
    key_version: str = "local-v1"


class SettingPatch(BaseModel):
    value: Any


def json_value(value: Any, default: Any = None) -> Any:
    """Decode asyncpg JSON/JSONB values defensively.

    asyncpg commonly returns json/jsonb as strings unless a custom codec is
    registered. Some tests/future drivers may return decoded dict/list values.
    API handlers should tolerate both forms.
    """
    if value is None:
        return default
    if isinstance(value, (dict, list, bool, int, float)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default if default is not None else value
    return value


def list_value(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return list(value) if not isinstance(value, str) else [value]


async def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("database pool not initialized")
    return _pool


@app.on_event("startup")
async def startup() -> None:
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    await seed_modules_from_manifests()


@app.on_event("shutdown")
async def shutdown() -> None:
    if _pool:
        await _pool.close()


async def active_principal(authorization: str | None = Header(default=None)) -> Principal:
    principal = optional_principal(authorization)
    if principal.subject == "local-dev":
        return principal
    bearer = extract_bearer_token(authorization)
    p = await pool()
    async with p.acquire() as conn:
        session = await conn.fetchrow(
            """
            SELECT id FROM auth_sessions
            WHERE token_hash=$1 AND revoked_at IS NULL AND expires_at > now()
            """,
            token_hash(bearer or ""),
        )
        device_revoked = False
        if principal.device_id:
            device_revoked = bool(await conn.fetchval("SELECT revoked_at IS NOT NULL FROM devices WHERE id=$1", UUID(principal.device_id)))
    if not session or device_revoked:
        raise HTTPException(status_code=401, detail="session revoked or expired")
    return principal




@app.middleware("http")
async def collect_red_metrics(request: Request, call_next):
    import time

    started = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    route_path = getattr(route, "path", request.url.path)
    red_metrics.observe(str(route_path), response.status_code, (time.perf_counter() - started) * 1000.0)
    response.headers["x-personal-os-service"] = "api-gateway"
    return response


@app.get("/metrics")
async def metrics() -> Response:
    return Response(red_metrics.prometheus(service_name="api-gateway"), media_type="text/plain; version=0.0.4")


@app.get("/api/release")
async def release_info() -> dict[str, Any]:
    return release_manifest(
        os.environ.get("APP_VERSION", "0.7.0"),
        os.environ.get("GIT_COMMIT_SHA", "0000000"),
        os.environ.get("RELEASE_CHANNEL") or None,
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    try:
        p = await pool()
        async with p.acquire() as conn:
            db_ok = await conn.fetchval("SELECT 1")
            modules = await conn.fetchval("SELECT COUNT(*) FROM modules WHERE installed = true")
        return {"status": "ok", "service": "api-gateway", "db": bool(db_ok), "modules": modules}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/control/health")
async def control_health(principal: Principal = Depends(active_principal)) -> dict[str, Any]:
    require_scope(principal, "modules:read")
    async with httpx.AsyncClient(timeout=5.0) as client:
        results = {}
        for name, url in {
            "api": "http://localhost:8080/health",
            "sync": f"{SYNC_ENGINE_URL}/health",
            "modules": f"{MODULE_SERVICE_URL}/health",
            "commands": f"{COMMAND_BUS_URL}/health",
            "automation": f"{AUTOMATION_SERVICE_URL}/health",
            "digital_twin": f"{DIGITAL_TWIN_SERVICE_URL}/health",
            "connectors": f"{CONNECTOR_SERVICE_URL}/health",
            "model_runtime": f"{MODEL_RUNTIME_SERVICE_URL}/health",
            "coding_agent": f"{CODING_AGENT_SERVICE_URL}/health",
        }.items():
            try:
                resp = await client.get(url)
                results[name] = {"ok": resp.status_code < 400, "status_code": resp.status_code}
            except Exception as exc:  # pragma: no cover - network-specific
                results[name] = {"ok": False, "error": str(exc)}
    return {"status": "ok" if all(v.get("ok") for v in results.values()) else "degraded", "services": results}


@app.post("/api/devices/register")
async def register_device(payload: DeviceRegistration, request: Request) -> dict[str, Any]:
    scopes = sorted(set(DEFAULT_DEVICE_SCOPES + payload.requested_scopes))
    # Do not let self-registration mint admin/cloud scopes.
    denied_prefixes = ("cloud:", "settings:", "admin:")
    scopes = [s for s in scopes if not s.startswith(denied_prefixes)]
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
        device_id = await conn.fetchval(
            """
            INSERT INTO devices(profile_id, device_key, name, kind, platform, public_key, tailscale_ip, trust_level, last_seen_at, app_version, build_channel)
            VALUES($1,$2,$3,$4,$5,$6,$7::inet,'trusted',now(),$8,$9)
            ON CONFLICT(device_key) DO UPDATE SET
              name=EXCLUDED.name,
              kind=EXCLUDED.kind,
              platform=EXCLUDED.platform,
              public_key=COALESCE(EXCLUDED.public_key, devices.public_key),
              tailscale_ip=COALESCE(EXCLUDED.tailscale_ip, devices.tailscale_ip),
              app_version=COALESCE(EXCLUDED.app_version, devices.app_version),
              build_channel=EXCLUDED.build_channel,
              last_seen_at=now(),
              revoked_at=NULL
            RETURNING id
            """,
            profile_id,
            payload.device_key,
            payload.name,
            payload.kind,
            payload.platform,
            payload.public_key,
            payload.tailscale_ip,
            payload.app_version,
            payload.build_channel,
        )
        token_pair = await create_token_pair(conn, profile_id, device_id, scopes, request.headers.get("user-agent"))
        await audit(conn, profile_id, device_id, None, "device.register", "device", str(device_id), {"device_key": payload.device_key, "kind": payload.kind})
    return {"device_id": str(device_id), **token_pair, "token_type": "bearer", "expires_in": ACCESS_TOKEN_TTL_SECONDS}


@app.post("/api/auth/refresh")
async def refresh_auth(payload: AuthRefreshRequest, request: Request) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM auth_refresh_tokens
            WHERE token_hash=$1 AND revoked_at IS NULL AND expires_at > now()
            """,
            token_hash(payload.refresh_token),
        )
        if not row:
            raise HTTPException(status_code=401, detail="invalid refresh token")
        async with conn.transaction():
            token_pair = await create_token_pair(conn, row["profile_id"], row["device_id"], list(row["scopes"]), request.headers.get("user-agent"))
            replacement = await conn.fetchval("SELECT id FROM auth_refresh_tokens WHERE token_hash=$1", token_hash(token_pair["refresh_token"]))
            await conn.execute(
                """
                UPDATE auth_refresh_tokens SET revoked_at=now(), rotated_at=now(), replaced_by=$2 WHERE id=$1
                """,
                row["id"],
                replacement,
            )
            await audit(conn, row["profile_id"], row["device_id"], None, "auth.refresh", "device", str(row["device_id"]), {})
    return {**token_pair, "token_type": "bearer", "expires_in": ACCESS_TOKEN_TTL_SECONDS}


@app.post("/api/auth/revoke")
async def revoke_auth(payload: AuthRevokeRequest, authorization: str | None = Header(default=None), principal: Principal = Depends(active_principal)) -> dict[str, Any]:
    p = await pool()
    access_token = extract_bearer_token(authorization)
    async with p.acquire() as conn:
        if access_token:
            await conn.execute("UPDATE auth_sessions SET revoked_at=now() WHERE token_hash=$1", token_hash(access_token))
        if payload.refresh_token:
            await conn.execute("UPDATE auth_refresh_tokens SET revoked_at=now() WHERE token_hash=$1", token_hash(payload.refresh_token))
        if payload.revoke_device and principal.device_id:
            await conn.execute("UPDATE devices SET revoked_at=now() WHERE id=$1", UUID(principal.device_id))
        await audit(conn, uuid_or_none(principal.subject), uuid_or_none(principal.device_id), None, "auth.revoke", "device", principal.device_id or "unknown", {"revoke_device": payload.revoke_device})
    return {"status": "revoked"}


@app.get("/api/auth/session")
async def session(principal: Principal = Depends(active_principal)) -> dict[str, Any]:
    return {"subject": principal.subject, "device_id": principal.device_id, "scopes": principal.scopes, "token_id": principal.token_id}


@app.get("/api/devices")
async def list_devices(principal: Principal = Depends(active_principal)) -> list[dict[str, Any]]:
    require_scope(principal, "modules:read")
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, device_key, name, kind, platform, tailscale_ip::text AS tailscale_ip, trust_level, last_seen_at, created_at, app_version, build_channel, revoked_at
            FROM devices ORDER BY last_seen_at DESC NULLS LAST, created_at DESC
            """
        )
    return [dict(r) for r in rows]


@app.get("/api/modules", response_model=list[ModuleHealth])
async def list_modules(principal: Principal = Depends(active_principal)) -> list[ModuleHealth]:
    require_scope(principal, "modules:read")
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, version, health, routes, permissions, publishes, subscribes, sync_enabled, manifest
            FROM modules
            WHERE installed = true
            ORDER BY id
            """
        )
    out: list[ModuleHealth] = []
    for row in rows:
        manifest = json_value(row["manifest"], {}) or {}
        routes = json_value(row["routes"], {}) or {}
        sync_manifest = manifest.get("sync", {}) if isinstance(manifest, dict) else {}
        out.append(
            ModuleHealth(
                id=row["id"],
                name=row["name"],
                version=row["version"],
                health=row["health"],
                routes=routes if isinstance(routes, dict) else {},
                permissions=list_value(row["permissions"]),
                events={"publishes": list_value(row["publishes"]), "subscribes": list_value(row["subscribes"])},
                sync={"enabled": row["sync_enabled"], "strategy": sync_manifest.get("strategy", "local-first")},
            )
        )
    return out


@app.get("/api/modules/{module_id}")
async def get_module(module_id: str, principal: Principal = Depends(active_principal)) -> dict[str, Any]:
    require_scope(principal, "modules:read")
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT manifest FROM modules WHERE id = $1", module_id)
    if not row:
        raise HTTPException(status_code=404, detail="module not found")
    manifest = json_value(row["manifest"], {}) or {}
    return manifest if isinstance(manifest, dict) else {"raw": manifest}


@app.post("/api/modules/rescan")
async def rescan_modules(principal: Principal = Depends(active_principal)) -> dict[str, int]:
    require_scope(principal, "modules:read")
    return {"seeded": await seed_modules_from_manifests()}


@app.get("/api/settings")
async def settings(principal: Principal = Depends(active_principal)) -> dict[str, Any]:
    require_scope(principal, "modules:read")
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT key, value FROM settings ORDER BY key")
    return {
        "control_plane": "nexus-core",
        "local_first": True,
        "mesh_supported": True,
        "modules_dir": str(MODULES_DIR),
        "settings": {r["key"]: public_setting(r["key"], json_value(r["value"])) for r in rows},
    }


@app.patch("/api/settings/{key}")
async def patch_setting(key: str, payload: SettingPatch, principal: Principal = Depends(active_principal)) -> dict[str, Any]:
    require_scope(principal, "settings:write")
    validate_setting(key, payload.value)
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO settings(key, value, updated_at)
            VALUES($1,$2::jsonb,now())
            ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()
            RETURNING key, value
            """,
            key,
            json.dumps(payload.value),
        )
        await audit(conn, None, uuid_or_none(principal.device_id), None, "setting.patch", "setting", key, {"configured": payload.value not in (None, ""), "sensitive": is_sensitive_key(key)})
    return {"key": row["key"], "value": public_setting(row["key"], json_value(row["value"])), "restart_required": True}


@app.post("/api/cloud/accounts")
async def create_cloud_account(payload: CloudAccountCreate, principal: Principal = Depends(active_principal)) -> dict[str, Any]:
    require_scope(principal, "cloud:write")
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
        row = await conn.fetchrow(
            """
            INSERT INTO cloud_accounts(profile_id, provider, account_email, scopes, status)
            VALUES($1,$2,$3,$4,'pending')
            RETURNING id, provider, account_email, scopes, status
            """,
            profile_id,
            payload.provider,
            payload.account_email,
            payload.scopes,
        )
        await audit(conn, profile_id, uuid_or_none(principal.device_id), None, "cloud.account.create", "cloud_account", str(row["id"]), {"provider": payload.provider})
    return dict(row)


@app.post("/api/cloud/accounts/{account_id}/tokens")
async def store_cloud_token(account_id: UUID, payload: CloudTokenStore, principal: Principal = Depends(active_principal)) -> dict[str, str]:
    require_scope(principal, "cloud:write")
    encrypted = encrypt_text(payload.refresh_token)
    p = await pool()
    async with p.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM cloud_accounts WHERE id=$1", account_id)
        if not exists:
            raise HTTPException(status_code=404, detail="cloud account not found")
        token_id = await conn.fetchval(
            """
            INSERT INTO cloud_tokens(cloud_account_id, token_type, encrypted_token, key_version, expires_at, rotated_at)
            VALUES($1,'oauth_refresh',$2,$3,$4,now())
            RETURNING id
            """,
            account_id,
            encrypted,
            payload.key_version,
            payload.expires_at,
        )
        await conn.execute("UPDATE cloud_accounts SET status='active', updated_at=now() WHERE id=$1", account_id)
        await audit(conn, None, uuid_or_none(principal.device_id), None, "cloud.token.store", "cloud_account", str(account_id), {"key_version": payload.key_version})
    return {"token_id": str(token_id), "status": "stored_encrypted"}


@app.api_route("/api/proxy/sync/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_sync(path: str, request: Request, principal: Principal = Depends(active_principal)) -> Response:
    require_scope(principal, "sync:read" if request.method == "GET" else "sync:write")
    return await proxy_request(SYNC_ENGINE_URL, path, request)


@app.api_route("/api/proxy/modules/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_modules(path: str, request: Request, principal: Principal = Depends(active_principal)) -> Response:
    require_scope(principal, "module:read" if request.method == "GET" else "module:write")
    return await proxy_request(MODULE_SERVICE_URL, path, request)


@app.api_route("/api/proxy/commands/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_commands(path: str, request: Request, principal: Principal = Depends(active_principal)) -> Response:
    require_scope(principal, "command:read" if request.method == "GET" else "command:request")
    return await proxy_request(COMMAND_BUS_URL, path, request)


@app.api_route("/api/proxy/research/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_research(path: str, request: Request, principal: Principal = Depends(active_principal)) -> Response:
    require_scope(principal, "research:read" if request.method == "GET" else "research:write")
    return await proxy_request(RESEARCH_SERVICE_URL, path, request)


@app.api_route("/api/proxy/automation/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_automation(path: str, request: Request, principal: Principal = Depends(active_principal)) -> Response:
    require_scope(principal, "automation:read" if request.method == "GET" else "automation:write")
    return await proxy_request(AUTOMATION_SERVICE_URL, path, request)


@app.api_route("/api/proxy/digital-twin/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_digital_twin(path: str, request: Request, principal: Principal = Depends(active_principal)) -> Response:
    if request.method == "GET":
        require_scope(principal, "digital_twin:read")
    elif "recommendations" in path:
        require_scope(principal, "recommendations:write")
    else:
        require_scope(principal, "digital_twin:write")
    return await proxy_request(DIGITAL_TWIN_SERVICE_URL, path, request)


@app.api_route("/api/proxy/capture/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_capture(path: str, request: Request, principal: Principal = Depends(active_principal)) -> Response:
    if request.method == "GET":
        require_scope(principal, "capture:read")
    elif "delegations" in path:
        require_scope(principal, "delegation:write")
    elif "tasks" in path:
        require_scope(principal, "tasks:write")
    else:
        require_scope(principal, "capture:write")
    return await proxy_request(CAPTURE_SERVICE_URL, path, request)


@app.api_route("/api/proxy/study-companion/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_study_companion(path: str, request: Request, principal: Principal = Depends(active_principal)) -> Response:
    require_scope(principal, "study_companion:read" if request.method == "GET" else "study_companion:write")
    return await proxy_request(STUDY_COMPANION_SERVICE_URL, path, request)


@app.api_route("/api/proxy/connectors/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_connectors(path: str, request: Request, principal: Principal = Depends(active_principal)) -> Response:
    require_scope(principal, "connectors:read" if request.method == "GET" else "connectors:write")
    return await proxy_request(CONNECTOR_SERVICE_URL, path, request)


@app.api_route("/api/proxy/model-runtime/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_model_runtime(path: str, request: Request, principal: Principal = Depends(active_principal)) -> Response:
    require_scope(principal, "model_runtime:read" if request.method == "GET" else "model_runtime:write")
    return await proxy_request(MODEL_RUNTIME_SERVICE_URL, path, request)


@app.api_route("/api/proxy/coding-agent/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_coding_agent(path: str, request: Request, principal: Principal = Depends(active_principal)) -> Response:
    require_scope(principal, "coding_agent:read" if request.method == "GET" else "coding_agent:write")
    return await proxy_request(CODING_AGENT_SERVICE_URL, path, request)


async def proxy_request(base_url: str, path: str, request: Request) -> Response:
    body = await request.body()
    excluded = {"host", "content-length"}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded}
    url = f"{base_url.rstrip('/')}/{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream = await client.request(request.method, url, content=body, headers=headers)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return Response(
            content=json.dumps({"error": {"code": "service_unavailable", "message": f"Backend service at {base_url} is not reachable", "action": "Run 'make up' to start all services"}}),
            status_code=503,
            headers={"content-type": "application/json"},
        )
    except httpx.ReadTimeout:
        return Response(
            content=json.dumps({"error": {"code": "gateway_timeout", "message": "Backend service did not respond in time"}}),
            status_code=504,
            headers={"content-type": "application/json"},
        )
    response_headers = {}
    if upstream.headers.get("content-type"):
        response_headers["content-type"] = upstream.headers["content-type"]
    return Response(content=upstream.content, status_code=upstream.status_code, headers=response_headers)


async def create_token_pair(conn: asyncpg.Connection, profile_id: UUID, device_id: UUID, scopes: list[str], user_agent: str | None) -> dict[str, str]:
    access_token = issue_token(str(profile_id), str(device_id), scopes, ACCESS_TOKEN_TTL_SECONDS)
    session_id = await conn.fetchval(
        """
        INSERT INTO auth_sessions(profile_id, device_id, token_hash, scopes, expires_at, jti, key_id, token_type, user_agent)
        VALUES($1,$2,$3,$4,$5,$6,$7,'access',$8)
        RETURNING id
        """,
        profile_id,
        device_id,
        token_hash(access_token),
        scopes,
        datetime.now(timezone.utc) + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS),
        _token_id(access_token),
        ACTIVE_JWT_KID,
        user_agent,
    )
    refresh_token = secrets.token_urlsafe(48)
    await conn.execute(
        """
        INSERT INTO auth_refresh_tokens(session_id, profile_id, device_id, token_hash, scopes, expires_at)
        VALUES($1,$2,$3,$4,$5,$6)
        """,
        session_id,
        profile_id,
        device_id,
        token_hash(refresh_token),
        scopes,
        datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
    )
    return {"access_token": access_token, "refresh_token": refresh_token}


def _token_id(token: str) -> str | None:
    from .security import decode_token_parts

    _header, payload, _sig = decode_token_parts(token)
    return payload.get("jti")


async def seed_modules_from_manifests() -> int:
    if not MODULES_DIR.exists():
        return 0
    p = await pool()
    count = 0
    async with p.acquire() as conn:
        for manifest_path in sorted(MODULES_DIR.glob("*/manifest.yaml")):
            manifest = yaml.safe_load(manifest_path.read_text()) or {}
            events = manifest.get("events", {})
            sync = manifest.get("sync", {})
            await conn.execute(
                """
                INSERT INTO modules(id, name, version, description, manifest, installed, health, routes, permissions, publishes, subscribes, sync_enabled, updated_at)
                VALUES($1,$2,$3,$4,$5::jsonb,true,'ok',$6::jsonb,$7,$8,$9,$10,now())
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    version = EXCLUDED.version,
                    description = EXCLUDED.description,
                    manifest = EXCLUDED.manifest,
                    routes = EXCLUDED.routes,
                    permissions = EXCLUDED.permissions,
                    publishes = EXCLUDED.publishes,
                    subscribes = EXCLUDED.subscribes,
                    sync_enabled = EXCLUDED.sync_enabled,
                    health = 'ok',
                    updated_at = now()
                """,
                manifest["id"],
                manifest["name"],
                manifest["version"],
                manifest.get("description"),
                json.dumps(manifest),
                json.dumps(manifest.get("routes", {})),
                manifest.get("permissions", []),
                events.get("publishes", []),
                events.get("subscribes", []),
                bool(sync.get("enabled", True)),
            )
            count += 1
    return count


async def audit(conn: asyncpg.Connection, profile_id: UUID | None, device_id: UUID | None, module_id: str | None, action: str, target_type: str, target_id: str, metadata: dict[str, Any]) -> None:
    await conn.execute(
        """
        INSERT INTO audit_log(profile_id, device_id, module_id, action, target_type, target_id, metadata)
        VALUES($1,$2,$3,$4,$5,$6,$7::jsonb)
        """,
        profile_id,
        device_id,
        module_id,
        action,
        target_type,
        target_id,
        json.dumps(metadata),
    )


def uuid_or_none(value: str | None) -> UUID | None:
    return UUID(value) if value else None
