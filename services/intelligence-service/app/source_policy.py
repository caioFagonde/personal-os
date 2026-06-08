from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

FORBIDDEN_PATTERNS: list[str] = [
    p.strip()
    for p in os.environ.get(
        "INTELLIGENCE_FORBIDDEN_PATTERNS",
        "libgen,library genesis,z-library,zlibrary,z-lib,sci-hub,annas-archive,annasarchive",
    ).split(",")
    if p.strip()
]

ALLOWED_SOURCE_KINDS = frozenset({
    "rss",
    "atom",
    "searxng",
    "news_api",
    "public_web",
    "user_configured",
})


@dataclass(frozen=True)
class SourceDecision:
    allowed: bool
    source_kind: str
    reason: str
    normalized_url: str | None = None


def validate_feed_url(url: str) -> SourceDecision:
    try:
        parsed = urlparse(url)
    except Exception:
        return SourceDecision(allowed=False, source_kind="unknown", reason="invalid URL")

    if parsed.scheme not in ("http", "https"):
        return SourceDecision(allowed=False, source_kind="unknown", reason="only http/https URLs are allowed")

    host_lower = (parsed.hostname or "").lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in host_lower or pattern.lower() in url.lower():
            return SourceDecision(allowed=False, source_kind="blocked", reason=f"source matches forbidden pattern: {pattern}")

    return SourceDecision(allowed=True, source_kind="rss", reason="public feed URL accepted", normalized_url=url)


def sanitize_query(query: str) -> str:
    cleaned = re.sub(r"[^\w\s\-.,!?@#&()\"':/]", "", query).strip()
    if len(cleaned) < 2:
        raise ValueError("query too short after sanitization")
    if len(cleaned) > 512:
        cleaned = cleaned[:512]
    return cleaned
