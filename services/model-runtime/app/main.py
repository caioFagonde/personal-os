from __future__ import annotations

import os
from typing import Any

import asyncpg
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .runtime import detect_runtime_health, get_provider_catalog, process_asset

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
app = FastAPI(title="Personal OS Model Runtime", version="0.13.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_pool: asyncpg.Pool | None = None


class RuntimeTextRequest(BaseModel):
    filename: str = "capture.txt"
    text: str = Field(min_length=1)
    content_type: str = "text/plain"


@app.on_event("startup")
async def startup() -> None:
    global _pool
    try:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)
    except Exception:  # pragma: no cover - allows standalone certification without DB
        _pool = None


@app.on_event("shutdown")
async def shutdown() -> None:
    if _pool:
        await _pool.close()


@app.get("/health")
async def health() -> dict[str, Any]:
    h = detect_runtime_health()
    h["service"] = "model-runtime"
    if _pool:
        async with _pool.acquire() as conn:
            h["db"] = bool(await conn.fetchval("SELECT 1"))
    else:
        h["db"] = False
    return h


@app.get("/api/model-runtime/runtimes")
async def runtimes() -> dict[str, Any]:
    return detect_runtime_health()


@app.get("/api/model-runtime/providers")
async def providers() -> dict[str, Any]:
    return {"providers": get_provider_catalog()}


@app.post("/api/model-runtime/process-text")
async def process_text(payload: RuntimeTextRequest) -> dict[str, Any]:
    result = process_asset(payload.filename, payload.text.encode("utf-8"), payload.content_type, payload.text)
    await log_invocation("process-text", result)
    return result


@app.post("/api/model-runtime/process-file")
async def process_file(file: UploadFile = File(...), text_hint: str | None = Form(None)) -> dict[str, Any]:
    data = await file.read()
    try:
        result = process_asset(file.filename or "capture.bin", data, file.content_type, text_hint)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    await log_invocation("process-file", result)
    return result


async def log_invocation(kind: str, result: dict[str, Any]) -> None:
    if not _pool:
        return
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO model_runtime_invocations(kind, sha256, media_type, result)
            VALUES($1,$2,$3,$4::jsonb)
            """,
            kind,
            result.get("sha256"),
            result.get("media_type"),
            __import__("json").dumps(result),
        )
