from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg
import yaml
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .crypto import encrypt_text
from .security import Principal, issue_token, optional_principal, require_scope, token_hash

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
MODULES_DIR = Path(os.environ.get("MODULES_DIR", "/workspace/modules"))

app = FastAPI(title="Personal OS API Gateway", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
_pool: asyncpg.Pool | None = None


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
    kind: str = "other"
    platform: str = "unknown"
    public_key: str | None = None
    tailscale_ip: str | None = None


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


@app.post("/api/devices/register")
async def register_device(payload: DeviceRegistration) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
        device_id = await conn.fetchval(
            """
            INSERT INTO devices(profile_id, device_key, name, kind, platform, public_key, tailscale_ip, trust_level, last_seen_at)
            VALUES($1,$2,$3,$4,$5,$6,$7::inet,'trusted',now())
            ON CONFLICT(device_key) DO UPDATE SET
              name=EXCLUDED.name,
              kind=EXCLUDED.kind,
              platform=EXCLUDED.platform,
              public_key=COALESCE(EXCLUDED.public_key, devices.public_key),
              tailscale_ip=COALESCE(EXCLUDED.tailscale_ip, devices.tailscale_ip),
              last_seen_at=now()
            RETURNING id
            """,
            profile_id,
            payload.device_key,
            payload.name,
            payload.kind,
            payload.platform,
            payload.public_key,
            payload.tailscale_ip,
        )
        token = issue_token(str(profile_id), str(device_id), ["device", "sync:read", "sync:write", "modules:read"], 86400 * 30)
        await conn.execute(
            """
            INSERT INTO auth_sessions(profile_id, device_id, token_hash, scopes, expires_at)
            VALUES($1,$2,$3,$4,$5)
            """,
            profile_id,
            device_id,
            token_hash(token),
            ["device", "sync:read", "sync:write", "modules:read"],
            datetime.now(timezone.utc) + timedelta(days=30),
        )
        await audit(conn, profile_id, device_id, None, "device.register", "device", str(device_id), {"device_key": payload.device_key})
    return {"device_id": str(device_id), "access_token": token, "token_type": "bearer"}


@app.get("/api/devices")
async def list_devices(principal: Principal = Depends(optional_principal)) -> list[dict[str, Any]]:
    require_scope(principal, "modules:read")
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, device_key, name, kind, platform, tailscale_ip::text AS tailscale_ip, trust_level, last_seen_at, created_at
            FROM devices ORDER BY last_seen_at DESC NULLS LAST, created_at DESC
            """
        )
    return [dict(r) for r in rows]


@app.get("/api/modules", response_model=list[ModuleHealth])
async def list_modules(principal: Principal = Depends(optional_principal)) -> list[ModuleHealth]:
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
        manifest = dict(row["manifest"])
        out.append(
            ModuleHealth(
                id=row["id"],
                name=row["name"],
                version=row["version"],
                health=row["health"],
                routes=dict(row["routes"]),
                permissions=list(row["permissions"]),
                events={"publishes": list(row["publishes"]), "subscribes": list(row["subscribes"])},
                sync={"enabled": row["sync_enabled"], "strategy": manifest.get("sync", {}).get("strategy", "local-first")},
            )
        )
    return out


@app.get("/api/modules/{module_id}")
async def get_module(module_id: str, principal: Principal = Depends(optional_principal)) -> dict[str, Any]:
    require_scope(principal, "modules:read")
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT manifest FROM modules WHERE id = $1", module_id)
    if not row:
        raise HTTPException(status_code=404, detail="module not found")
    return dict(row["manifest"])


@app.post("/api/modules/rescan")
async def rescan_modules(principal: Principal = Depends(optional_principal)) -> dict[str, int]:
    require_scope(principal, "modules:read")
    return {"seeded": await seed_modules_from_manifests()}


@app.get("/api/settings")
async def settings(principal: Principal = Depends(optional_principal)) -> dict[str, Any]:
    require_scope(principal, "modules:read")
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT key, value FROM settings ORDER BY key")
    return {
        "control_plane": "nexus-core",
        "local_first": True,
        "mesh_supported": True,
        "modules_dir": str(MODULES_DIR),
        "settings": {r["key"]: r["value"] for r in rows},
    }


@app.patch("/api/settings/{key}")
async def patch_setting(key: str, payload: SettingPatch, principal: Principal = Depends(optional_principal)) -> dict[str, Any]:
    require_scope(principal, "settings:write")
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
        await audit(conn, None, uuid_or_none(principal.device_id), None, "setting.patch", "setting", key, {"value": payload.value})
    return dict(row)


@app.post("/api/cloud/accounts")
async def create_cloud_account(payload: CloudAccountCreate, principal: Principal = Depends(optional_principal)) -> dict[str, Any]:
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
async def store_cloud_token(account_id: UUID, payload: CloudTokenStore, principal: Principal = Depends(optional_principal)) -> dict[str, str]:
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
