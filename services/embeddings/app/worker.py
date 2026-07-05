"""Embedding worker (Phase B3).

Fills `object_chunks.embedding` from three complementary signals:

1. NATS subject `nexus.embed` — real-time pushes ({"object_id": ...}).
2. The `service_events` transactional outbox (topic `nexus.embed`) written by
   the graph helper in every dual-writing service — survives NATS outages.
3. A periodic sweep of chunks with NULL embeddings — repairs anything missed.

When no embedding model is available the worker leaves chunks NULL and events
unpublished; graph search then degrades to trigram ("lexical search"). Nothing
is faked.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any
from uuid import UUID

import asyncpg

from .provider import EmbeddingUnavailable, OllamaEmbedder

log = logging.getLogger("embeddings")

NATS_URL = os.environ.get("NATS_URL", "nats://nats:4222")
EMBED_SUBJECT = "nexus.embed"
POLL_SECONDS = float(os.environ.get("EMBED_POLL_SECONDS", "10"))
SWEEP_BATCH = int(os.environ.get("EMBED_SWEEP_BATCH", "64"))


def vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


class EmbedWorker:
    def __init__(self, pool: asyncpg.Pool, embedder: OllamaEmbedder) -> None:
        self.pool = pool
        self.embedder = embedder
        self._nats: Any = None
        self._task: asyncio.Task | None = None
        self.processed = 0
        self.last_error: str | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="embed-worker")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._nats:
            try:
                await self._nats.drain()
            except Exception:  # pragma: no cover - shutdown best-effort
                pass

    async def _run(self) -> None:
        await self._connect_nats()
        while True:
            try:
                await self._drain_outbox()
                await self._sweep_null_chunks()
                self.last_error = None
            except EmbeddingUnavailable as exc:
                # Honest degradation: keep chunks NULL, try again next tick.
                self.last_error = str(exc)
            except Exception as exc:  # pragma: no cover - worker must survive
                self.last_error = str(exc)
                log.exception("embed worker tick failed")
            await asyncio.sleep(POLL_SECONDS)

    async def _connect_nats(self) -> None:
        try:
            import nats

            self._nats = await nats.connect(NATS_URL, connect_timeout=5)

            async def on_message(msg: Any) -> None:
                try:
                    payload = json.loads(msg.data.decode())
                    object_id = payload.get("object_id")
                    if object_id:
                        await self.embed_object(UUID(object_id))
                except EmbeddingUnavailable as exc:
                    self.last_error = str(exc)
                except Exception:  # pragma: no cover
                    log.exception("nexus.embed message failed")

            await self._nats.subscribe(EMBED_SUBJECT, cb=on_message)
            log.info("subscribed to NATS %s at %s", EMBED_SUBJECT, NATS_URL)
        except Exception as exc:
            # Outbox polling still drives progress without NATS.
            log.warning("NATS unavailable (%s); relying on outbox polling only", exc)
            self._nats = None

    async def _drain_outbox(self) -> None:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, payload FROM service_events
                WHERE topic=$1 AND published=false
                ORDER BY id LIMIT $2
                """,
                EMBED_SUBJECT,
                SWEEP_BATCH,
            )
        for row in rows:
            payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])
            object_id = payload.get("object_id")
            if object_id:
                await self.embed_object(UUID(object_id))
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE service_events SET published=true, published_at=now() WHERE id=$1",
                    row["id"],
                )

    async def _sweep_null_chunks(self) -> None:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT object_id FROM object_chunks WHERE embedding IS NULL LIMIT $1",
                SWEEP_BATCH,
            )
        for row in rows:
            await self.embed_object(row["object_id"])

    async def embed_object(self, object_id: UUID) -> int:
        """Embed all NULL chunks of one object. Raises EmbeddingUnavailable when degraded."""
        async with self.pool.acquire() as conn:
            chunks = await conn.fetch(
                "SELECT id, text FROM object_chunks WHERE object_id=$1 AND embedding IS NULL ORDER BY seq",
                object_id,
            )
        if not chunks:
            return 0
        vectors = await self.embedder.embed([c["text"] for c in chunks])
        async with self.pool.acquire() as conn:
            for chunk, vec in zip(chunks, vectors):
                await conn.execute(
                    "UPDATE object_chunks SET embedding=$2::vector, model=$3 WHERE id=$1",
                    chunk["id"],
                    vector_literal(vec),
                    self.embedder.model,
                )
        self.processed += len(chunks)
        return len(chunks)
