from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - import-time environment fallback
    PdfReader = None  # type: ignore

from .source_policy import extract_doi

REFERENCE_HEADER_RE = re.compile(r"(?im)^\s*(references|bibliography|works cited)\s*$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
URL_RE = re.compile(r"https?://[^\s)>\]]+")


@dataclass(frozen=True)
class ExtractedPdf:
    text: str
    page_count: int
    status: str


@dataclass(frozen=True)
class CitationCandidate:
    raw_text: str
    doi: str | None
    url: str | None
    year: int | None
    confidence: float


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def extract_pdf_text(content: bytes) -> ExtractedPdf:
    if PdfReader is None:
        return ExtractedPdf(text="", page_count=0, status="failed")
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = "\n\n".join(pages).strip()
        status = "extracted" if len(text) >= 20 else "needs_ocr"
        return ExtractedPdf(text=text, page_count=len(reader.pages), status=status)
    except Exception:
        return ExtractedPdf(text="", page_count=0, status="failed")


def chunk_text(text: str, target_chars: int = 2400, overlap_chars: int = 250) -> list[str]:
    normalized = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + target_chars)
        if end < len(normalized):
            boundary = normalized.rfind("\n\n", start, end)
            if boundary <= start + target_chars // 3:
                boundary = normalized.rfind(". ", start, end)
            if boundary > start:
                end = boundary + 1
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(0, end - overlap_chars)
    return chunks


def extract_citations(text: str, limit: int = 80) -> list[CitationCandidate]:
    if not text:
        return []
    ref_start = None
    for match in REFERENCE_HEADER_RE.finditer(text):
        ref_start = match.end()
    reference_block = text[ref_start:] if ref_start is not None else text[-16000:]
    lines = [re.sub(r"\s+", " ", line).strip() for line in reference_block.splitlines()]
    merged: list[str] = []
    buffer = ""
    for line in lines:
        if not line:
            if buffer:
                merged.append(buffer.strip())
                buffer = ""
            continue
        starts_new = bool(re.match(r"^(\[\d+\]|\d+\.|[A-Z][A-Za-z'\-]+,\s+[A-Z])", line))
        if starts_new and buffer:
            merged.append(buffer.strip())
            buffer = line
        else:
            buffer = f"{buffer} {line}".strip()
    if buffer:
        merged.append(buffer.strip())
    out: list[CitationCandidate] = []
    seen: set[str] = set()
    for raw in merged:
        if len(raw) < 20 or raw in seen:
            continue
        seen.add(raw)
        doi = extract_doi(raw)
        url_match = URL_RE.search(raw)
        year_match = YEAR_RE.search(raw)
        confidence = 0.45 + (0.25 if doi else 0) + (0.15 if year_match else 0) + (0.1 if url_match else 0)
        out.append(
            CitationCandidate(
                raw_text=raw[:2000],
                doi=doi,
                url=url_match.group(0).rstrip(".,") if url_match else None,
                year=int(year_match.group(0)) if year_match else None,
                confidence=min(confidence, 0.95),
            )
        )
        if len(out) >= limit:
            break
    return out


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text.split()) * 1.35)) if text else 0
