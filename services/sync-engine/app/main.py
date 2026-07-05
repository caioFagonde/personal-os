from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .security import optional_principal, require_scope

from .conflict import resolve_payload

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
ARTIFACT_DIR = os.environ.get("LOCAL_ARTIFACT_DIR", "/tmp/personal-os-artifacts")
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local").lower()
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ROOT_USER", "")
MINIO_SECRET_KEY = os.environ.get("MINIO_ROOT_PASSWORD", "")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "artifacts")
app = FastAPI(title="Personal OS Sync Engine", version="0.2.0")
# CORS origins are configurable via env (comma-separated). "*" is the local-dev
# default; restrict to the gateway origin(s) on any non-tailnet deployment.
CORS_ALLOW_ORIGINS = [o.strip() for o in os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()] or ["*"]
app.add_middleware(CORSMiddleware, allow_origins=CORS_ALLOW_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def require_service_auth(request: Request, call_next):
    if request.url.path in {"/health", "/openapi.json"} or request.url.path.startswith(("/docs", "/redoc")):
        return await call_next(request)
    principal = optional_principal(request.headers.get("authorization"))
    require_scope(principal, "sync:read" if request.method == "GET" else "sync:write")
    request.state.principal = principal
    return await call_next(request)
_pool: asyncpg.Pool | None = None


class SyncChange(BaseModel):
    event_id: str | None = None
    module_id: str
    entity_type: str
    entity_id: str | None = None
    external_id: str | None = None
    action: str = Field(pattern="^(create|update|delete|merge)$")
    merge_strategy: str = "field_merge"
    payload: dict[str, Any]
    vector_clock: dict[str, int] = Field(default_factory=dict)
    changed_fields: list[str] | None = None
    occurred_at: datetime | None = None


class PushRequest(BaseModel):
    device_key: str
    changes: list[SyncChange]


class PullRequest(BaseModel):
    device_key: str
    since_id: int = 0
    modules: list[str] | None = None
    include_own: bool = False


class AttachmentInit(BaseModel):
    device_key: str
    module_id: str
    entity_id: str
    filename: str
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    checksum: str
    encrypted: bool = False


class ConflictResolve(BaseModel):
    device_key: str
    payload: dict[str, Any]
    vector_clock: dict[str, int] = Field(default_factory=dict)


class SyncHeartbeat(BaseModel):
    device_key: str
    platform: str = "web"
    pending_mutations: int = Field(default=0, ge=0)
    conflict_count: int = Field(default=0, ge=0)
    foreground: bool = True
    battery_hint: str | None = None
    network_hint: str | None = None


@app.on_event("startup")
async def startup() -> None:
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)


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
    return {"status": "ok", "service": "sync-engine"}


@app.get("/api/sync/health")
async def sync_health() -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        latest = await conn.fetchval("SELECT COALESCE(MAX(id),0) FROM sync_log")
        open_conflicts = await conn.fetchval("SELECT COUNT(*) FROM sync_conflicts WHERE status='open'")
    return {"status": "ok", "latest_sync_id": latest, "open_conflicts": open_conflicts}


@app.post("/api/sync/heartbeat")
async def sync_heartbeat(hb: SyncHeartbeat) -> dict[str, Any]:
    """Record a per-device sync heartbeat (Phase E). Drives the Continuity
    surface's "this device last synced / N queued" line — real state, no scores."""
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, hb.device_key)
        fg = "now()" if hb.foreground else "last_foreground_sync_at"
        bg = "last_background_sync_at" if hb.foreground else "now()"
        row = await conn.fetchrow(
            f"""
            INSERT INTO client_sync_state(device_id, platform, last_foreground_sync_at, last_background_sync_at,
                                          pending_mutations, conflict_count, battery_hint, network_hint, updated_at)
            VALUES($1,$2,{"now()" if hb.foreground else "NULL"},{"NULL" if hb.foreground else "now()"},$3,$4,$5,$6,now())
            ON CONFLICT(device_id, platform) DO UPDATE SET
              last_foreground_sync_at={fg}, last_background_sync_at={bg},
              pending_mutations=EXCLUDED.pending_mutations, conflict_count=EXCLUDED.conflict_count,
              battery_hint=EXCLUDED.battery_hint, network_hint=EXCLUDED.network_hint, updated_at=now()
            RETURNING id::text
            """,
            device_id, hb.platform, hb.pending_mutations, hb.conflict_count, hb.battery_hint, hb.network_hint,
        )
    return {"status": "recorded", "state_id": row["id"]}


@app.get("/api/sync/devices")
async def sync_devices() -> list[dict[str, Any]]:
    """Per-device continuity view: last seen, lag, queue depth (Phase E)."""
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT d.name, d.device_key, d.kind, c.platform,
                   c.last_foreground_sync_at, c.last_background_sync_at,
                   c.pending_mutations, c.conflict_count, c.battery_hint, c.network_hint, c.updated_at,
                   GREATEST(COALESCE(c.last_foreground_sync_at, 'epoch'), COALESCE(c.last_background_sync_at, 'epoch')) AS last_sync_at
            FROM client_sync_state c JOIN devices d ON d.id = c.device_id
            ORDER BY c.updated_at DESC LIMIT 100
            """
        )
    out = []
    for r in rows:
        item = dict(r)
        last = r["last_sync_at"]
        if last and last.year > 1970:
            item["lag_seconds"] = max(0, int((datetime.now(timezone.utc) - last).total_seconds()))
        else:
            item["lag_seconds"] = None
        out.append(item)
    return out


@app.post("/api/sync/push")
async def push(req: PushRequest) -> dict[str, Any]:
    p = await pool()
    accepted: list[int] = []
    conflicts: list[str] = []
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, req.device_key)
        async with conn.transaction():
            for change in req.changes:
                sync_id, conflict_id = await apply_change(conn, change, device_id)
                if sync_id:
                    accepted.append(sync_id)
                if conflict_id:
                    conflicts.append(str(conflict_id))
    return {"accepted": accepted, "conflicts": conflicts, "count": len(accepted)}


@app.post("/api/sync/pull")
async def pull(req: PullRequest) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, req.device_key)
        own_filter = "" if req.include_own else "AND (device_id IS NULL OR device_id <> $2)"
        if req.modules:
            rows = await conn.fetch(
                f"""
                SELECT id, event_id::text, module_id, entity_id::text, entity_type, action, payload, vector_clock, lamport, occurred_at
                FROM sync_log
                WHERE id > $1 {own_filter} AND module_id = ANY($3::text[])
                ORDER BY id ASC LIMIT 500
                """,
                req.since_id,
                device_id,
                req.modules,
            )
        else:
            rows = await conn.fetch(
                f"""
                SELECT id, event_id::text, module_id, entity_id::text, entity_type, action, payload, vector_clock, lamport, occurred_at
                FROM sync_log
                WHERE id > $1 {own_filter}
                ORDER BY id ASC LIMIT 500
                """,
                req.since_id,
                device_id,
            )
    changes = [dict(r) for r in rows]
    cursor = max([req.since_id, *[r["id"] for r in rows]])
    return {"changes": changes, "cursor": cursor}


@app.get("/api/sync/conflicts")
async def list_conflicts(status: str = "open") -> list[dict[str, Any]]:
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, entity_id::text, module_id, entity_type, local_payload, remote_payload, local_clock, remote_clock, strategy, status, created_at
            FROM sync_conflicts WHERE status=$1 ORDER BY created_at DESC LIMIT 200
            """,
            status,
        )
    return [dict(r) for r in rows]


@app.post("/api/sync/conflicts/{conflict_id}/resolve")
async def resolve_conflict(conflict_id: UUID, payload: ConflictResolve) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, payload.device_key)
        conflict = await conn.fetchrow("SELECT * FROM sync_conflicts WHERE id=$1 AND status='open'", conflict_id)
        if not conflict:
            raise HTTPException(status_code=404, detail="open conflict not found")
        entity_id = conflict["entity_id"]
        version_id, sync_id = await insert_version_and_log(
            conn,
            entity_id,
            device_id,
            conflict["module_id"],
            conflict["entity_type"],
            "merge",
            "manual",
            payload.payload,
            payload.vector_clock,
            datetime.now(timezone.utc),
        )
        await conn.execute("UPDATE entities SET current_version=$1, updated_at=now() WHERE id=$2", version_id, entity_id)
        await conn.execute("UPDATE sync_conflicts SET status='resolved', resolution=$2::jsonb, resolved_at=now() WHERE id=$1", conflict_id, json.dumps(payload.payload))
    return {"status": "resolved", "sync_id": sync_id}


@app.post("/api/attachments/initiate")
async def initiate_attachment(payload: AttachmentInit) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        device_id = await ensure_device(conn, payload.device_key)
        entity_uuid = UUID(payload.entity_id)
        object_key = f"{payload.module_id}/{entity_uuid}/{hashlib.sha256(payload.filename.encode()).hexdigest()[:16]}-{payload.filename}"
        attachment_id = await conn.fetchval(
            """
            INSERT INTO attachments(entity_id, module_id, object_key, filename, content_type, size_bytes, checksum, sync_state, encrypted, uploaded_by_device_id)
            VALUES($1,$2,$3,$4,$5,$6,$7,'pending',$8,$9)
            RETURNING id
            """,
            entity_uuid,
            payload.module_id,
            object_key,
            payload.filename,
            payload.content_type,
            payload.size_bytes,
            payload.checksum,
            payload.encrypted,
            device_id,
        )
    if STORAGE_BACKEND == "minio":
        return {
            "attachment_id": str(attachment_id),
            "object_key": object_key,
            "storage_provider": "minio",
            "upload_method": "PUT",
            "upload_url": presign_minio_put(object_key, payload.content_type),
        }
    return {
        "attachment_id": str(attachment_id),
        "object_key": object_key,
        "storage_provider": "local",
        "upload_method": "POST",
        "upload_url": f"/api/attachments/{attachment_id}/content",
    }


def presign_minio_put(object_key: str, content_type: str) -> str:
    try:
        import boto3
        from botocore.client import Config
    except Exception as exc:  # pragma: no cover - optional runtime dependency branch
        raise HTTPException(status_code=503, detail="boto3 is required for MinIO presigned uploads") from exc
    if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
        raise HTTPException(status_code=503, detail="MinIO credentials are not configured")
    client = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    try:
        client.head_bucket(Bucket=MINIO_BUCKET)
    except Exception:
        client.create_bucket(Bucket=MINIO_BUCKET)
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": MINIO_BUCKET, "Key": object_key, "ContentType": content_type},
        ExpiresIn=900,
        HttpMethod="PUT",
    )


@app.put("/api/attachments/{attachment_id}/content")
async def upload_attachment_content(attachment_id: UUID, file: UploadFile = File(...)) -> dict[str, Any]:
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT object_key FROM attachments WHERE id=$1", attachment_id)
        if not row:
            raise HTTPException(status_code=404, detail="attachment not found")
        target = os.path.join(ARTIFACT_DIR, row["object_key"])
        os.makedirs(os.path.dirname(target), exist_ok=True)
        h = hashlib.sha256()
        size = 0
        with open(target, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                h.update(chunk)
                size += len(chunk)
                out.write(chunk)
        await conn.execute("UPDATE attachments SET size_bytes=$2, checksum=$3, sync_state='local', uploaded_at=now() WHERE id=$1", attachment_id, size, h.hexdigest())
    return {"attachment_id": str(attachment_id), "size_bytes": size, "checksum": h.hexdigest(), "sync_state": "local"}


async def apply_change(conn: asyncpg.Connection, change: SyncChange, device_id: UUID) -> tuple[int | None, UUID | None]:
    entity_id = await upsert_entity(conn, change, device_id)
    current = await conn.fetchrow(
        """
        SELECT ev.id AS version_id, ev.payload, ev.version_clock, ev.created_at
        FROM entities e LEFT JOIN entity_versions ev ON e.current_version = ev.id
        WHERE e.id=$1
        """,
        entity_id,
    )
    if current and current["version_id"]:
        result = resolve_payload(
            dict(current["payload"]),
            change.payload,
            dict(current["version_clock"]),
            change.vector_clock,
            change.merge_strategy,
            set(current["payload"].keys()),
            set(change.changed_fields or change.payload.keys()),
        )
        if result.needs_manual_resolution:
            remote_version_id = await conn.fetchval(
                """
                INSERT INTO entity_versions(entity_id, device_id, operation, merge_strategy, payload, checksum, version_clock, created_at)
                VALUES($1,$2,$3,$4,$5::jsonb,$6,$7::jsonb,$8) RETURNING id
                """,
                entity_id,
                device_id,
                change.action,
                change.merge_strategy,
                json.dumps(change.payload),
                checksum(change.payload),
                json.dumps(change.vector_clock),
                change.occurred_at or datetime.now(timezone.utc),
            )
            conflict_id = await conn.fetchval(
                """
                INSERT INTO sync_conflicts(entity_id, module_id, entity_type, local_version_id, remote_version_id, local_payload, remote_payload, local_clock, remote_clock, strategy)
                VALUES($1,$2,$3,$4,$5,$6::jsonb,$7::jsonb,$8::jsonb,$9::jsonb,$10) RETURNING id
                """,
                entity_id,
                change.module_id,
                change.entity_type,
                current["version_id"],
                remote_version_id,
                json.dumps(dict(current["payload"])),
                json.dumps(change.payload),
                json.dumps(dict(current["version_clock"])),
                json.dumps(change.vector_clock),
                change.merge_strategy,
            )
            return None, conflict_id
        payload = result.payload
        clock = result.clock
    else:
        payload = change.payload
        clock = change.vector_clock
    version_id, sync_id = await insert_version_and_log(
        conn,
        entity_id,
        device_id,
        change.module_id,
        change.entity_type,
        change.action,
        change.merge_strategy,
        payload,
        clock,
        change.occurred_at or datetime.now(timezone.utc),
        change.event_id,
    )
    await conn.execute("UPDATE entities SET current_version=$1, deleted_at=CASE WHEN $3='delete' THEN now() ELSE deleted_at END, updated_at=now() WHERE id=$2", version_id, entity_id, change.action)
    return sync_id, None


async def insert_version_and_log(conn: asyncpg.Connection, entity_id: UUID, device_id: UUID, module_id: str, entity_type: str, action: str, strategy: str, payload: dict[str, Any], clock: dict[str, int], occurred_at: datetime, event_id: str | None = None) -> tuple[UUID, int]:
    version_id = await conn.fetchval(
        """
        INSERT INTO entity_versions(entity_id, device_id, operation, merge_strategy, payload, checksum, version_clock, created_at)
        VALUES($1,$2,$3,$4,$5::jsonb,$6,$7::jsonb,$8) RETURNING id
        """,
        entity_id,
        device_id,
        action,
        strategy,
        json.dumps(payload),
        checksum(payload),
        json.dumps(clock),
        occurred_at,
    )
    sync_id = await conn.fetchval(
        """
        INSERT INTO sync_log(event_id, module_id, entity_id, entity_type, version_id, device_id, action, payload, vector_clock, lamport, occurred_at)
        VALUES(COALESCE($1::uuid, gen_random_uuid()),$2,$3,$4,$5,$6,$7,$8::jsonb,$9::jsonb,COALESCE((SELECT MAX(lamport)+1 FROM sync_log),1),$10)
        ON CONFLICT(event_id) DO UPDATE SET received_at=sync_log.received_at
        RETURNING id
        """,
        event_id,
        module_id,
        entity_id,
        entity_type,
        version_id,
        device_id,
        action,
        json.dumps(payload),
        json.dumps(clock),
        occurred_at,
    )
    await conn.execute("INSERT INTO service_events(topic, payload) VALUES($1,$2::jsonb)", f"{module_id}.{entity_type}.{action}", json.dumps({"entity_id": str(entity_id), "sync_id": sync_id}))
    return version_id, sync_id


async def ensure_device(conn: asyncpg.Connection, device_key: str) -> UUID:
    profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
    return await conn.fetchval(
        """
        INSERT INTO devices(profile_id, device_key, name, kind, platform, trust_level, last_seen_at)
        VALUES($1,$2,$2,'other','unknown','trusted',now())
        ON CONFLICT(device_key) DO UPDATE SET last_seen_at=now()
        RETURNING id
        """,
        profile_id,
        device_key,
    )


async def upsert_entity(conn: asyncpg.Connection, change: SyncChange, device_id: UUID) -> UUID:
    if change.entity_id:
        existing = await conn.fetchval("SELECT id FROM entities WHERE id=$1", UUID(change.entity_id))
        if existing:
            return existing
    external_id = change.external_id or change.entity_id or hashlib.sha256(json.dumps(change.payload, sort_keys=True).encode()).hexdigest()
    return await conn.fetchval(
        """
        INSERT INTO entities(module_id, entity_type, external_id, created_by_device)
        VALUES($1,$2,$3,$4)
        ON CONFLICT(module_id, entity_type, external_id) DO UPDATE SET updated_at=now()
        RETURNING id
        """,
        change.module_id,
        change.entity_type,
        external_id,
        device_id,
    )


def checksum(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
