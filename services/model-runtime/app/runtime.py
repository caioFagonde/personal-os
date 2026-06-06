from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class RuntimeMode(str, Enum):
    disabled = "disabled"
    heuristic = "heuristic"
    external = "external"


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "heic", "bmp"}
AUDIO_EXTENSIONS = {"wav", "mp3", "m4a", "ogg", "flac"}
VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "mkv"}
PDF_EXTENSIONS = {"pdf"}
TEXT_EXTENSIONS = {"txt", "md", "csv", "json"}


@dataclass(frozen=True)
class RuntimeHealth:
    name: str
    mode: RuntimeMode
    available: bool
    version: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    bbox: tuple[float, float, float, float] | None = None
    source: str = "heuristic"


@dataclass(frozen=True)
class OCRBlock:
    text: str
    confidence: float
    bbox: tuple[float, float, float, float] | None = None
    source: str = "heuristic"


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start_seconds: float
    end_seconds: float
    confidence: float
    source: str = "heuristic"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def extension_for(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower().strip()


def classify_asset(filename: str, content_type: str | None = None) -> str:
    ext = extension_for(filename)
    ctype = (content_type or "").lower()
    if ext in IMAGE_EXTENSIONS or ctype.startswith("image/"):
        return "image"
    if ext in AUDIO_EXTENSIONS or ctype.startswith("audio/"):
        return "audio"
    if ext in VIDEO_EXTENSIONS or ctype.startswith("video/"):
        return "video"
    if ext in PDF_EXTENSIONS or ctype == "application/pdf":
        return "pdf"
    if ext in TEXT_EXTENSIONS or ctype.startswith("text/"):
        return "text"
    return "binary"


def detect_runtime_health(env: dict[str, str] | None = None) -> dict[str, Any]:
    env = env or os.environ
    ocr_provider = env.get("OCR_PROVIDER", "heuristic").lower()
    vision_provider = env.get("VISION_PROVIDER", "heuristic").lower()
    audio_provider = env.get("AUDIO_PROVIDER", "heuristic").lower()
    rows = [
        RuntimeHealth("ocr", _mode(ocr_provider), _available(ocr_provider), version=env.get("OCR_VERSION"), detail=_detail(ocr_provider)),
        RuntimeHealth("object_detection", _mode(vision_provider), _available(vision_provider), version=env.get("VISION_VERSION"), detail=_detail(vision_provider)),
        RuntimeHealth("audio_transcription", _mode(audio_provider), _available(audio_provider), version=env.get("AUDIO_VERSION"), detail=_detail(audio_provider)),
    ]
    return {
        "status": "ok" if all(r.available for r in rows) else "degraded",
        "runtimes": [asdict(r) for r in rows],
        "max_bytes": int(env.get("MODEL_RUNTIME_MAX_BYTES", "52428800")),
    }


def _mode(provider: str) -> RuntimeMode:
    if provider in {"none", "disabled", "off"}:
        return RuntimeMode.disabled
    if provider in {"heuristic", "mock", "fallback"}:
        return RuntimeMode.heuristic
    return RuntimeMode.external


def _available(provider: str) -> bool:
    if provider in {"none", "disabled", "off"}:
        return False
    if provider in {"heuristic", "mock", "fallback"}:
        return True
    # External providers are declared available only when explicitly certified.
    return os.environ.get(f"{provider.upper()}_READY", "false").lower() in {"1", "true", "yes"}


def _detail(provider: str) -> str:
    if provider in {"heuristic", "mock", "fallback"}:
        return "deterministic local fallback; replace with certified model provider for production inference"
    if provider in {"none", "disabled", "off"}:
        return "runtime disabled"
    return "external runtime declared; readiness controlled by provider-specific *_READY flag"


def heuristic_ocr(filename: str, payload: bytes, text_hint: str | None = None) -> list[OCRBlock]:
    text = text_hint or ""
    if not text and classify_asset(filename) == "text":
        text = payload.decode("utf-8", errors="ignore")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        sentence = sentence.strip()
        if sentence:
            chunks.append(sentence)
    return [OCRBlock(text=c, confidence=0.93) for c in chunks[:25]]


def heuristic_detect(filename: str, payload: bytes, text_hint: str | None = None) -> list[Detection]:
    material = f"{filename} {text_hint or ''}".lower()
    catalog = {
        "book": ["book", "chapter", "isbn", "page", "paragraph"],
        "paper": ["abstract", "doi", "arxiv", "journal", "references"],
        "equation": ["theorem", "proof", "equation", "integral", "derivative", "matrix"],
        "diagram": ["diagram", "figure", "graph", "plot", "flowchart"],
        "whiteboard": ["whiteboard", "board", "marker"],
        "document": ["contract", "invoice", "receipt", "letter", "document"],
    }
    results: list[Detection] = []
    for label, needles in catalog.items():
        if any(n in material for n in needles):
            results.append(Detection(label=label, confidence=0.72))
    if not results and classify_asset(filename) in {"image", "video"}:
        results.append(Detection(label="visual_capture", confidence=0.51))
    return results[:20]


def heuristic_transcribe(filename: str, payload: bytes, text_hint: str | None = None) -> list[TranscriptSegment]:
    if text_hint:
        text = re.sub(r"\s+", " ", text_hint).strip()
        if text:
            return [TranscriptSegment(text=text[:2000], start_seconds=0.0, end_seconds=max(1.0, len(text) / 14.0), confidence=0.85)]
    if classify_asset(filename) == "text":
        text = payload.decode("utf-8", errors="ignore").strip()
        if text:
            return [TranscriptSegment(text=text[:2000], start_seconds=0.0, end_seconds=max(1.0, len(text) / 14.0), confidence=0.75)]
    return []


def summarize_modal_result(filename: str, detections: list[Detection], ocr: list[OCRBlock], transcript: list[TranscriptSegment]) -> str:
    labels = ", ".join(d.label for d in detections) or classify_asset(filename)
    text = " ".join([b.text for b in ocr] + [s.text for s in transcript]).strip()
    if text:
        return f"Captured {labels}. Extracted excerpt: {text[:280]}{'…' if len(text) > 280 else ''}"
    return f"Captured {labels}. No readable text/transcript was extracted by the current runtime."


def lookup_queries(filename: str, detections: list[Detection], ocr: list[OCRBlock], transcript: list[TranscriptSegment]) -> list[str]:
    queries: list[str] = []
    for det in detections[:4]:
        queries.append(f"What should I know about {det.label} in this captured context?")
    text = " ".join([b.text for b in ocr] + [s.text for s in transcript]).strip()
    if text:
        nouns = re.findall(r"\b[A-Z][A-Za-z0-9\-]{3,}\b", text)[:6]
        if nouns:
            queries.append("Explain and contextualize: " + ", ".join(dict.fromkeys(nouns)))
        else:
            queries.append("Summarize and extract study concepts from: " + text[:180])
    if not queries:
        queries.append(f"Classify and summarize {filename}")
    return queries[:8]


def process_asset(filename: str, payload: bytes, content_type: str | None = None, text_hint: str | None = None) -> dict[str, Any]:
    if len(payload) > int(os.environ.get("MODEL_RUNTIME_MAX_BYTES", "52428800")):
        raise ValueError("asset exceeds MODEL_RUNTIME_MAX_BYTES")
    detections = heuristic_detect(filename, payload, text_hint)
    ocr = heuristic_ocr(filename, payload, text_hint)
    transcript = heuristic_transcribe(filename, payload, text_hint)
    return {
        "sha256": sha256_bytes(payload),
        "media_type": classify_asset(filename, content_type),
        "detections": [asdict(d) for d in detections],
        "ocr_blocks": [asdict(b) for b in ocr],
        "transcript_segments": [asdict(s) for s in transcript],
        "summary": summarize_modal_result(filename, detections, ocr, transcript),
        "lookup_queries": lookup_queries(filename, detections, ocr, transcript),
    }
