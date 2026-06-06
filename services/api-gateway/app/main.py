from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import asyncpg
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
MODULES_DIR = Path(os.environ.get("MODULES_DIR", "/workspace/modules"))

app = FastAPI(title="Personal OS API Gateway", version="0.1.0")
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
async def health() -> dict[str, str]:
    try:
        p = await pool()
        async with p.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "ok", "service": "api-gateway"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

@app.get("/api/modules", response_model=list[ModuleHealth])
async def list_modules() -> list[ModuleHealth]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, name, version, health, routes, permissions, publishes, subscribes, sync_enabled, manifest
            FROM modules
            WHERE installed = true
            ORDER BY id
        """)
    out: list[ModuleHealth] = []
    for row in rows:
        manifest = dict(row["manifest"])
        out.append(ModuleHealth(
            id=row["id"],
            name=row["name"],
            version=row["version"],
            health=row["health"],
            routes=dict(row["routes"]),
            permissions=list(row["permissions"]),
            events={"publishes": list(row["publishes"]), "subscribes": list(row["subscribes"])},
            sync={"enabled": row["sync_enabled"], "strategy": manifest.get("sync", {}).get("strategy", "local-first")},
        ))
    return out

@app.get("/api/modules/{module_id}")
async def get_module(module_id: str) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT manifest FROM modules WHERE id = $1", module_id)
    if not row:
        raise HTTPException(status_code=404, detail="module not found")
    return dict(row["manifest"])

@app.get("/api/settings")
async def settings() -> dict[str, Any]:
    return {
        "control_plane": "nexus-core",
        "local_first": True,
        "mesh_supported": True,
        "modules_dir": str(MODULES_DIR),
    }

async def seed_modules_from_manifests() -> None:
    if not MODULES_DIR.exists():
        return
    p = await pool()
    async with p.acquire() as conn:
        for manifest_path in sorted(MODULES_DIR.glob("*/manifest.yaml")):
            manifest = yaml.safe_load(manifest_path.read_text()) or {}
            events = manifest.get("events", {})
            sync = manifest.get("sync", {})
            await conn.execute("""
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
            """, manifest["id"], manifest["name"], manifest["version"], manifest.get("description"),
                __import__('json').dumps(manifest), __import__('json').dumps(manifest.get("routes", {})), manifest.get("permissions", []),
                events.get("publishes", []), events.get("subscribes", []), bool(sync.get("enabled", True)))
