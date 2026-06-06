from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg"}
TEXT_EXTENSIONS = {".txt", ".md"}
PDF_EXTENSIONS = {".pdf"}


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class OCRBlock:
    text: str
    confidence: float = 0.7
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class AnalogResult:
    media_type: str
    sha256: str
    detections: list[Detection] = field(default_factory=list)
    ocr_blocks: list[OCRBlock] = field(default_factory=list)
    summary: str = ""
    suggested_tags: list[str] = field(default_factory=list)
    lookup_queries: list[str] = field(default_factory=list)
    zettel_candidate: dict[str, Any] = field(default_factory=dict)
    reading_candidate: dict[str, Any] = field(default_factory=dict)


def classify_media(filename: str, content_type: str | None = None) -> str:
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    ctype = (content_type or "").lower()
    if suffix in IMAGE_EXTENSIONS or ctype.startswith("image/"):
        return "image"
    if suffix in AUDIO_EXTENSIONS or ctype.startswith("audio/"):
        return "audio"
    if suffix in PDF_EXTENSIONS or ctype == "application/pdf":
        return "pdf"
    if suffix in TEXT_EXTENSIONS or ctype.startswith("text/"):
        return "text"
    if ctype.startswith("video/"):
        return "video"
    return "binary"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lightweight_ocr_from_text_hint(text_hint: str | None) -> list[OCRBlock]:
    if not text_hint:
        return []
    raw_lines = [line.strip() for line in text_hint.splitlines() if line.strip()]
    compact = re.sub(r"\s+", " ", text_hint).strip()
    if not compact:
        return []
    chunks: list[str] = []
    if len(raw_lines) > 1:
        chunks.extend(raw_lines)
    for sentence in re.split(r"(?<=[.!?])\s+", compact):
        sentence = sentence.strip()
        if sentence and sentence not in chunks:
            chunks.append(sentence)
    return [OCRBlock(text=c, confidence=0.93) for c in chunks[:20]]


def heuristic_detect_objects(filename: str, text_hint: str | None = None) -> list[Detection]:
    material = f"{filename} {text_hint or ''}".lower()
    detections: list[Detection] = []
    labels = {
        "book": ["book", "chapter", "isbn", "page"],
        "paper": ["abstract", "doi", "arxiv", "journal"],
        "equation": ["theorem", "proof", "equation", "∫", "sum"],
        "whiteboard": ["whiteboard", "board"],
        "diagram": ["diagram", "figure", "graph"],
    }
    for label, needles in labels.items():
        if any(n in material for n in needles):
            detections.append(Detection(label=label, confidence=0.72))
    if not detections and classify_media(filename) == "image":
        detections.append(Detection(label="image_capture", confidence=0.51))
    return detections


def summarize_analog_capture(media_type: str, detections: list[Detection], ocr_blocks: list[OCRBlock]) -> str:
    text = " ".join(block.text for block in ocr_blocks).strip()
    labels = ", ".join(d.label for d in detections) or media_type
    if text:
        return f"Captured {labels}. OCR excerpt: {text[:260]}{'…' if len(text) > 260 else ''}"
    return f"Captured {labels}. No reliable OCR text was extracted."


def extract_reading_candidate(ocr_blocks: list[OCRBlock], detections: list[Detection]) -> dict[str, Any]:
    text = " ".join(b.text for b in ocr_blocks)
    is_reading = any(d.label in {"book", "paper"} for d in detections) or bool(re.search(r"\b(chapter|isbn|abstract|doi|page)\b", text, re.I))
    if not is_reading:
        return {}
    title = infer_title(text) or "Analog reading capture"
    return {"title": title, "kind": "analog_reading", "status": "queued", "source_ref": "analog_capture", "excerpt": text[:1000]}


def infer_title(text: str) -> str | None:
    lines = [line.strip(" -:\t") for line in text.splitlines() if line.strip()]
    for line in lines[:8]:
        title_match = re.match(r"^(?:title|book)[:\s]+(.{4,100})$", line, re.I)
        if title_match:
            return title_match.group(1).strip()
        if 4 <= len(line) <= 120 and not line.lower().startswith(("page ", "chapter ")):
            return line
    match = re.search(r"(?:title|book)[:\s]+(.{4,100})", text, re.I)
    return match.group(1).strip() if match else None


def build_lookup_queries(detections: list[Detection], ocr_blocks: list[OCRBlock], max_queries: int = 5) -> list[str]:
    queries: list[str] = []
    text = "\n".join(b.text for b in ocr_blocks)
    title = infer_title(text)
    if title:
        queries.append(title)
    for d in sorted(detections, key=lambda x: x.confidence, reverse=True):
        if d.label not in {"image_capture"}:
            queries.append(d.label)
    noun_like = re.findall(r"\b[A-Z][a-zA-Z]{3,}(?:\s+[A-Z][a-zA-Z]{3,}){0,3}\b", text)
    for item in noun_like:
        if item not in queries:
            queries.append(item)
    return queries[:max_queries]


def process_analog_input(filename: str, data: bytes, content_type: str | None = None, text_hint: str | None = None) -> AnalogResult:
    media_type = classify_media(filename, content_type)
    digest = sha256_bytes(data)
    ocr_blocks = lightweight_ocr_from_text_hint(text_hint)
    detections = heuristic_detect_objects(filename, text_hint)
    summary = summarize_analog_capture(media_type, detections, ocr_blocks)
    tags = sorted({d.label for d in detections} | {media_type, "analog"})
    lookup_queries = build_lookup_queries(detections, ocr_blocks)
    text = "\n\n".join(block.text for block in ocr_blocks)
    zettel = {"title": infer_title(text) or f"Analog capture {digest[:8]}", "body": f"{summary}\n\n{text}".strip(), "tags": tags}
    reading = extract_reading_candidate(ocr_blocks, detections)
    return AnalogResult(media_type, digest, detections, ocr_blocks, summary, tags, lookup_queries, zettel, reading)
