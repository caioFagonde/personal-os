from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .evaluation import evaluate_golden_cases
from .ontology import ontology_snapshot, stable_fingerprint, validate_entity, validate_relationship
from .privacy import allowed_for_purpose, classify_sensitivity, normalize_policy, sanitize_memory_record
from .recommender import generate_recommendations
from .timeline import aggregate_timeline, infer_state_from_events, normalize_event
from .security import Principal, optional_principal, require_scope

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
AUTH_REQUIRED = os.environ.get("AUTH_REQUIRED", "false").lower() == "true"

app = FastAPI(title="Personal OS Digital Twin Service", version="0.8.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
_pool: asyncpg.Pool | None = None


class EntityCreate(BaseModel):
    entity_type: str
    external_id: str | None = None
    name: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    sensitivity: str | None = None


class RelationshipCreate(BaseModel):
    relation_type: str
    from_entity_id: UUID
    to_entity_id: UUID
    from_type: str = "*"
    to_type: str = "*"
    properties: dict[str, Any] = Field(default_factory=dict)


class TimelineEventCreate(BaseModel):
    event_type: str
    source: str = "manual"
    occurred_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    sensitivity: str | None = None


class StateSnapshotCreate(BaseModel):
    state_type: str = "daily"
    captured_at: datetime | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.7, ge=0, le=1)
    source: str = "manual"


class GoalCreate(BaseModel):
    title: str
    domain: str = "planning"
    priority: int = Field(default=50, ge=0, le=100)
    progress: float = Field(default=0.0, ge=0, le=1)
    status: str = "active"
    properties: dict[str, Any] = Field(default_factory=dict)


class RecommendationRequest(BaseModel):
    state: dict[str, Any] | None = None
    goals: list[dict[str, Any]] | None = None
    recent_events: list[dict[str, Any]] | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)
    persist: bool = False


class MemoryRecordCreate(BaseModel):
    memory_class: str = "working"
    content: str
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    sensitivity: str | None = None
    source: str = "manual"
    properties: dict[str, Any] = Field(default_factory=dict)


class MemoryPolicyPatch(BaseModel):
    policy: dict[str, Any]


async def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("database pool not initialized")
    return _pool


async def principal(authorization: str | None = Header(default=None)) -> Principal:
    # Downstream services share the gateway token contract. In local development AUTH_REQUIRED=false returns local-dev.
    return optional_principal(authorization)


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
    try:
        p = await pool()
        async with p.acquire() as conn:
            ok = await conn.fetchval("SELECT 1")
            events = await conn.fetchval("SELECT COUNT(*) FROM digital_twin_timeline_events")
        return {"status": "ok", "service": "digital-twin-service", "db": bool(ok), "timeline_events": events}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/digital-twin/ontology")
async def get_ontology(_principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:read")
    return ontology_snapshot()


@app.post("/api/digital-twin/entities")
async def create_entity(payload: EntityCreate, _principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:write")
    properties = dict(payload.properties)
    if payload.name and "name" not in properties:
        properties["name"] = payload.name
    errors = validate_entity(payload.entity_type, properties)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    fp = stable_fingerprint(payload.entity_type, {**properties, "id": payload.external_id or properties.get("id")})
    sensitivity = payload.sensitivity or ("sensitive" if ontology_snapshot()["entity_types"][payload.entity_type].get("sensitive") else "personal")
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await default_profile(conn)
        row = await conn.fetchrow(
            """
            INSERT INTO digital_twin_entities(profile_id, entity_type, external_id, natural_key, fingerprint, name, properties, sensitivity)
            VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8)
            ON CONFLICT(profile_id, fingerprint) DO UPDATE SET
              name=COALESCE(EXCLUDED.name, digital_twin_entities.name),
              properties=digital_twin_entities.properties || EXCLUDED.properties,
              updated_at=now()
            RETURNING id, entity_type, external_id, natural_key, fingerprint, name, properties, sensitivity, created_at, updated_at
            """,
            profile_id,
            payload.entity_type,
            payload.external_id,
            fp.natural_key,
            fp.fingerprint,
            payload.name,
            json.dumps(properties),
            sensitivity,
        )
    return json_row(row)


@app.get("/api/digital-twin/entities")
async def list_entities(entity_type: str | None = None, _principal: Principal = Depends(principal)) -> list[dict[str, Any]]:
    require_scope(_principal, "digital_twin:read")
    p = await pool()
    async with p.acquire() as conn:
        if entity_type:
            rows = await conn.fetch("SELECT * FROM digital_twin_entities WHERE entity_type=$1 ORDER BY updated_at DESC LIMIT 200", entity_type)
        else:
            rows = await conn.fetch("SELECT * FROM digital_twin_entities ORDER BY updated_at DESC LIMIT 200")
    return [json_row(r) for r in rows]


@app.post("/api/digital-twin/relationships")
async def create_relationship(payload: RelationshipCreate, _principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:write")
    errors = validate_relationship(payload.relation_type, payload.from_type, payload.to_type)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    p = await pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO digital_twin_relationships(relation_type, from_entity_id, to_entity_id, properties)
            VALUES($1,$2,$3,$4::jsonb)
            ON CONFLICT(relation_type, from_entity_id, to_entity_id) DO UPDATE SET properties=EXCLUDED.properties
            RETURNING *
            """,
            payload.relation_type,
            payload.from_entity_id,
            payload.to_entity_id,
            json.dumps(payload.properties),
        )
    return json_row(row)


@app.post("/api/digital-twin/events")
async def create_event(payload: TimelineEventCreate, _principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:write")
    normalized = normalize_event(payload.event_type, payload.payload, payload.occurred_at, payload.source)
    sensitivity = classify_sensitivity(json.dumps(payload.payload), payload.sensitivity, normalized["domains"])
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await default_profile(conn)
        row = await conn.fetchrow(
            """
            INSERT INTO digital_twin_timeline_events(profile_id, event_uid, event_type, source, domains, importance, occurred_at, payload, sensitivity)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9)
            ON CONFLICT(profile_id, event_uid) DO UPDATE SET payload=EXCLUDED.payload, updated_at=now()
            RETURNING *
            """,
            profile_id,
            normalized["event_uid"],
            normalized["event_type"],
            normalized["source"],
            normalized["domains"],
            normalized["importance"],
            normalized["occurred_at"],
            json.dumps(normalized["payload"]),
            sensitivity,
        )
    return json_row(row)


@app.get("/api/digital-twin/timeline")
async def timeline(limit: int = Query(100, ge=1, le=1000), domain: str | None = None, _principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:read")
    p = await pool()
    async with p.acquire() as conn:
        if domain:
            rows = await conn.fetch("SELECT * FROM digital_twin_timeline_events WHERE $1 = ANY(domains) ORDER BY occurred_at DESC LIMIT $2", domain, limit)
        else:
            rows = await conn.fetch("SELECT * FROM digital_twin_timeline_events ORDER BY occurred_at DESC LIMIT $1", limit)
    events = [json_row(r) for r in rows]
    # Convert strings back only for deterministic aggregation where DB returns datetimes already.
    return {"events": events, "summary": aggregate_timeline(events)}


@app.get("/api/digital-twin/state/infer")
async def inferred_state(limit: int = Query(200, ge=1, le=1000), _principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:read")
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT event_type, source, domains, importance, occurred_at, payload FROM digital_twin_timeline_events ORDER BY occurred_at DESC LIMIT $1", limit)
    events = [json_row(r) for r in rows]
    state = infer_state_from_events(events)
    return {"state": state, "source_event_count": len(events)}


@app.post("/api/digital-twin/state")
async def create_state_snapshot(payload: StateSnapshotCreate, _principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:write")
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await default_profile(conn)
        row = await conn.fetchrow(
            """
            INSERT INTO digital_twin_state_snapshots(profile_id, state_type, captured_at, state, confidence, source)
            VALUES($1,$2,$3,$4::jsonb,$5,$6) RETURNING *
            """,
            profile_id,
            payload.state_type,
            payload.captured_at or datetime.now(timezone.utc),
            json.dumps(payload.state),
            payload.confidence,
            payload.source,
        )
    return json_row(row)


@app.post("/api/digital-twin/goals")
async def create_goal(payload: GoalCreate, _principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:write")
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await default_profile(conn)
        row = await conn.fetchrow(
            """
            INSERT INTO digital_twin_goals(profile_id, title, domain, priority, progress, status, properties)
            VALUES($1,$2,$3,$4,$5,$6,$7::jsonb) RETURNING *
            """,
            profile_id,
            payload.title,
            payload.domain,
            payload.priority,
            payload.progress,
            payload.status,
            json.dumps(payload.properties),
        )
    return json_row(row)


@app.get("/api/digital-twin/goals")
async def list_goals(_principal: Principal = Depends(principal)) -> list[dict[str, Any]]:
    require_scope(_principal, "digital_twin:read")
    p = await pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM digital_twin_goals ORDER BY status, priority DESC, created_at DESC")
    return [json_row(r) for r in rows]


@app.post("/api/digital-twin/recommendations")
async def recommendations(payload: RecommendationRequest, _principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "recommendations:write")
    state = payload.state
    goals = payload.goals
    recent_events = payload.recent_events or []
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await default_profile(conn)
        if state is None:
            rows = await conn.fetch("SELECT event_type, source, domains, importance, occurred_at, payload FROM digital_twin_timeline_events ORDER BY occurred_at DESC LIMIT 200")
            recent_events = [json_row(r) for r in rows]
            state = infer_state_from_events(recent_events)
        if goals is None:
            rows = await conn.fetch("SELECT id::text AS id, title, domain, priority, progress, status, properties FROM digital_twin_goals WHERE status NOT IN ('done','archived')")
            goals = [json_row(r) for r in rows]
        recs = generate_recommendations(state or {}, goals or [], recent_events, payload.preferences)
        run_id = None
        if payload.persist:
            run_id = await conn.fetchval(
                "INSERT INTO digital_twin_recommendation_runs(profile_id, state, goals, preferences, recommendation_count) VALUES($1,$2::jsonb,$3::jsonb,$4::jsonb,$5) RETURNING id",
                profile_id,
                json.dumps(state or {}),
                json.dumps(goals or []),
                json.dumps(payload.preferences),
                len(recs),
            )
            for rec in recs:
                await conn.execute(
                    "INSERT INTO digital_twin_recommendation_items(run_id, recommendation_uid, title, rationale, domain, priority, confidence, action_type, action, requires_approval) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10)",
                    run_id,
                    rec["id"],
                    rec["title"],
                    rec["rationale"],
                    rec["domain"],
                    rec["priority"],
                    rec["confidence"],
                    rec["action_type"],
                    json.dumps(rec["action"]),
                    rec["requires_approval"],
                )
    return {"run_id": str(run_id) if run_id else None, "state": state, "recommendations": recs}


@app.get("/api/digital-twin/memory/policy")
async def get_memory_policy(_principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:read")
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await default_profile(conn)
        policy = await conn.fetchval("SELECT policy FROM digital_twin_memory_policies WHERE profile_id=$1 ORDER BY created_at DESC LIMIT 1", profile_id)
    return {"policy": normalize_policy(policy)}


@app.put("/api/digital-twin/memory/policy")
async def put_memory_policy(payload: MemoryPolicyPatch, _principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:write")
    policy = normalize_policy(payload.policy)
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await default_profile(conn)
        row = await conn.fetchrow(
            """
            INSERT INTO digital_twin_memory_policies(profile_id, policy) VALUES($1,$2::jsonb)
            ON CONFLICT(profile_id) DO UPDATE SET policy=EXCLUDED.policy, updated_at=now()
            RETURNING *
            """,
            profile_id,
            json.dumps(policy),
        )
    return json_row(row)


@app.post("/api/digital-twin/memory")
async def create_memory(payload: MemoryRecordCreate, _principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:write")
    sensitivity = classify_sensitivity(payload.content, payload.sensitivity, payload.tags)
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await default_profile(conn)
        row = await conn.fetchrow(
            """
            INSERT INTO digital_twin_memory_records(profile_id, memory_class, content, summary, tags, sensitivity, source, properties)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8::jsonb) RETURNING *
            """,
            profile_id,
            payload.memory_class,
            payload.content,
            payload.summary,
            payload.tags,
            sensitivity,
            payload.source,
            json.dumps(payload.properties),
        )
    return json_row(row)


@app.get("/api/digital-twin/memory")
async def list_memory(purpose: str = "search", _principal: Principal = Depends(principal)) -> list[dict[str, Any]]:
    require_scope(_principal, "digital_twin:read")
    scopes = set(_principal.scopes)
    p = await pool()
    async with p.acquire() as conn:
        profile_id = await default_profile(conn)
        policy = normalize_policy(await conn.fetchval("SELECT policy FROM digital_twin_memory_policies WHERE profile_id=$1", profile_id))
        rows = await conn.fetch("SELECT * FROM digital_twin_memory_records WHERE profile_id=$1 ORDER BY created_at DESC LIMIT 200", profile_id)
    out: list[dict[str, Any]] = []
    for row in rows:
        item = json_row(row)
        allowed, reason = allowed_for_purpose(scopes, purpose, item.get("sensitivity", "personal"), policy)
        if allowed:
            out.append(sanitize_memory_record(item, policy, external=True))
        else:
            out.append({"id": item["id"], "sensitivity": item.get("sensitivity"), "blocked": True, "reason": reason})
    return out


@app.get("/api/digital-twin/evaluations/golden")
async def golden_evaluations(_principal: Principal = Depends(principal)) -> dict[str, Any]:
    require_scope(_principal, "digital_twin:read")
    return evaluate_golden_cases()


async def default_profile(conn: asyncpg.Connection) -> UUID:
    profile_id = await conn.fetchval("SELECT id FROM profiles WHERE handle='default'")
    if not profile_id:
        profile_id = await conn.fetchval("INSERT INTO profiles(handle, display_name) VALUES('default','Default Profile') RETURNING id")
    return profile_id


def json_row(row: asyncpg.Record | dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    for key, value in list(data.items()):
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif isinstance(value, UUID):
            data[key] = str(value)
    return data
