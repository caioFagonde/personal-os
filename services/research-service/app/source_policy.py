from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

FORBIDDEN_HOST_PATTERNS = tuple(
    p.strip().lower()
    for p in os.environ.get(
        "FORBIDDEN_SOURCE_HOST_PATTERNS",
        "libgen,library genesis,z-library,zlibrary,z-lib,sci-hub,annas-archive,annasarchive",
    ).split(",")
    if p.strip()
)

DEFAULT_ALLOWED_DISCOVERY_SOURCES = {
    "arxiv",
    "crossref",
    "openalex",
    "semantic_scholar",
    "pubmed",
    "doaj",
    "core",
    "unpaywall",
    "user_url",
    "upload",
}

SAFE_SCHEMES = {"http", "https"}
PDF_EXT_RE = re.compile(r"\.pdf($|[?#])", re.IGNORECASE)
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    normalized_url: str | None = None
    source_kind: str = "unknown"


def normalize_source_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", name.strip().lower()).strip("_")


def validate_discovery_source(name: str) -> PolicyDecision:
    source = normalize_source_name(name)
    if any(pattern.replace("-", "_") in source for pattern in FORBIDDEN_HOST_PATTERNS):
        return PolicyDecision(False, "pirate or paywall-circumvention sources are not supported", source_kind=source)
    if source not in DEFAULT_ALLOWED_DISCOVERY_SOURCES:
        return PolicyDecision(False, f"unsupported discovery source: {source}", source_kind=source)
    return PolicyDecision(True, "supported discovery source", source_kind=source)


def classify_url(url: str) -> PolicyDecision:
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in SAFE_SCHEMES or not parsed.netloc:
        return PolicyDecision(False, "URL must use http or https", normalized_url=None)
    host = parsed.netloc.lower()
    normalized = parsed.geturl()
    if any(pattern in host for pattern in FORBIDDEN_HOST_PATTERNS):
        return PolicyDecision(False, "blocked source host: pirate or paywall-circumvention source", normalized_url=normalized)
    kind = "pdf" if PDF_EXT_RE.search(parsed.path) else "web"
    return PolicyDecision(True, "URL is eligible for authorized/open ingestion", normalized_url=normalized, source_kind=kind)


def extract_doi(text: str) -> str | None:
    match = DOI_RE.search(text or "")
    return match.group(0).rstrip(".,);]") if match else None


def sanitize_query(query: str) -> str:
    cleaned = re.sub(r"\s+", " ", query).strip()
    if not cleaned or len(cleaned) < 2:
        raise ValueError("query must contain at least two non-space characters")
    return cleaned[:512]
