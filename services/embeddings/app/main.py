"""Embeddings service (Phase B3 — real provider chain, closes R-05).

Replaces the former placeholder (which returned deterministic fake vectors)
with an honest Ollama-backed provider. When no model is available, /api/embed
returns a structured 503 and stored chunks keep NULL embeddings so graph
search can degrade to trigram search with a truthful label.
"""
from __future__ import annotations

import os
from typing import Any

import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .provider import EMBED_DIM, EMBED_MODEL, OLLAMA_URL, SETUP_ACTION, EmbeddingUnavailable, OllamaEmbedder, status_detail
from .worker import EmbedWorker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://personal_os:personal_os@localhost:5432/personal_os")
EMBED_WORKER_ENABLED = os.environ.get("EMBED_WORKER_ENABLED", "true").lower() in {"1", "true", "yes"}

app = FastAPI(title="Personal OS Embeddings Service", version="0.8.0")
CORS_ALLOW_ORIGINS = [o.strip() for o in os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()] or ["*"]
app.add_middleware(CORSMiddleware, allow_origins=CORS_ALLOW_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

_pool: asyncpg.Pool | None = None
_embedder = OllamaEmbedder()
_worker: EmbedWorker | None = None


class EmbedRequest(BaseModel):
    text: str | None = None
    texts: list[str] = Field(default_factory=list)


@app.on_event("startup")
async def startup() -> None:
    global _pool, _worker
    try:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    except Exception:  # allows standalone /api/embed use without a database
        _pool = None
    if _pool and EMBED_WORKER_ENABLED:
        _worker = EmbedWorker(_pool, _embedder)
        _worker.start()


@app.on_event("shutdown")
async def shutdown() -> None:
    if _worker:
        await _worker.stop()
    if _pool:
        await _pool.close()


@app.get("/health")
async def health() -> dict[str, Any]:
    status = await _embedder.probe()
    pending = None
    if _pool:
        async with _pool.acquire() as conn:
            pending = await conn.fetchval("SELECT count(*) FROM object_chunks WHERE embedding IS NULL")
    return {
        "status": "ok" if status.available else "degraded",
        "service": "embeddings",
        "mode": "ollama" if status.available else "unavailable",
        "provider_state": status.state,
        "model": EMBED_MODEL,
        "dim": EMBED_DIM,
        "ollama_url": OLLAMA_URL,
        "detail": status_detail(status.state),
        "db": _pool is not None,
        "pending_chunks": pending,
        "worker": {
            "enabled": _worker is not None,
            "processed": _worker.processed if _worker else 0,
            "last_error": _worker.last_error if _worker else None,
        },
    }


@app.get("/api/embeddings/status")
async def embeddings_status() -> dict[str, Any]:
    return await health()


@app.post("/api/embed")
async def embed(payload: EmbedRequest) -> dict[str, Any]:
    texts = payload.texts or ([payload.text] if payload.text else [])
    texts = [t for t in texts if t and t.strip()]
    if not texts:
        raise HTTPException(status_code=422, detail="provide 'text' or a non-empty 'texts' list")
    try:
        vectors = await _embedder.embed(texts)
    except EmbeddingUnavailable as exc:
        raise HTTPException(status_code=503, detail={
            "code": "embedding_model_unavailable",
            "message": str(exc),
            "action": SETUP_ACTION,
            "fallback": "lexical search (no embedding model)",
        })
    return {"model": EMBED_MODEL, "dim": EMBED_DIM, "vectors": vectors, "count": len(vectors)}
