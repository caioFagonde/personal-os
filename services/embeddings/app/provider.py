"""Embedding provider chain (Phase B3, closes R-05).

Primary provider is Ollama (`nomic-embed-text` by default) reached over HTTP.
There is intentionally NO fake-vector fallback: when no model is available the
service reports its state honestly, chunks keep a NULL embedding, and graph
search degrades to Postgres trigram ("lexical search (no embedding model)").

Provider states reuse the model-runtime vocabulary:
  not_installed → Ollama unreachable
  installed     → Ollama reachable, embed model not pulled
  configured    → model present, no successful embed probe yet
  tested        → at least one successful embedding produced
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger("embeddings")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
EMBED_DIM = int(os.environ.get("EMBED_DIM", "768"))

SETUP_ACTION = (
    "Start Ollama and pull the embed model: "
    "docker compose --profile ai up -d ollama && "
    f"docker exec personal-os-ollama ollama pull {EMBED_MODEL}"
)


@dataclass
class ProviderStatus:
    reachable: bool
    model_present: bool
    probe_ok: bool

    @property
    def state(self) -> str:
        return provider_state(self.reachable, self.model_present, self.probe_ok)

    @property
    def available(self) -> bool:
        return self.reachable and self.model_present


def provider_state(reachable: bool, model_present: bool, probe_ok: bool) -> str:
    if not reachable:
        return "not_installed"
    if not model_present:
        return "installed"
    if not probe_ok:
        return "configured"
    return "tested"


def status_detail(state: str) -> str:
    return {
        "not_installed": f"Ollama unreachable at {OLLAMA_URL}. {SETUP_ACTION}",
        "installed": f"Ollama is up but model '{EMBED_MODEL}' is not pulled. {SETUP_ACTION}",
        "configured": f"Model '{EMBED_MODEL}' present; no successful embed yet.",
        "tested": f"Model '{EMBED_MODEL}' producing {EMBED_DIM}-dim embeddings.",
    }[state]


class OllamaEmbedder:
    """Thin async client around Ollama's /api/embed with cached probe state."""

    def __init__(self, base_url: str = OLLAMA_URL, model: str = EMBED_MODEL, dim: int = EMBED_DIM) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dim = dim
        self._probe_ok = False

    async def probe(self) -> ProviderStatus:
        reachable = False
        model_present = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                reachable = True
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                model_present = any(name == self.model or name.startswith(f"{self.model}:") for name in models)
        except Exception as exc:
            log.debug("embeddings: ollama probe failed: %s", exc)
        return ProviderStatus(reachable=reachable, model_present=model_present, probe_ok=self._probe_ok)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Raises EmbeddingUnavailable when the chain is down."""
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": texts},
                )
        except httpx.HTTPError as exc:
            raise EmbeddingUnavailable(f"Ollama unreachable at {self.base_url}: {type(exc).__name__}") from exc
        if resp.status_code == 404:
            raise EmbeddingUnavailable(f"model '{self.model}' not found in Ollama. {SETUP_ACTION}")
        if resp.status_code >= 400:
            raise EmbeddingUnavailable(f"Ollama embed failed with HTTP {resp.status_code}: {resp.text[:200]}")
        payload: dict[str, Any] = resp.json()
        vectors = payload.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise EmbeddingUnavailable("Ollama returned a malformed embeddings payload")
        for vec in vectors:
            if len(vec) != self.dim:
                raise EmbeddingUnavailable(
                    f"model '{self.model}' returned {len(vec)}-dim vectors but object_chunks.embedding is vector({self.dim}); "
                    f"set EMBED_DIM/EMBED_MODEL consistently"
                )
        self._probe_ok = True
        return vectors


class EmbeddingUnavailable(RuntimeError):
    """No embedding model is currently usable — callers must degrade honestly."""
