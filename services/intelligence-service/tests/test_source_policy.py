from __future__ import annotations

import pytest

from app.source_policy import (
    ALLOWED_SOURCE_KINDS,
    SourceDecision,
    sanitize_query,
    validate_feed_url,
)


class TestValidateFeedUrl:
    def test_accepts_plain_https_feed(self):
        decision = validate_feed_url("https://example.org/feed.xml")
        assert decision.allowed
        assert decision.source_kind == "rss"
        assert decision.normalized_url == "https://example.org/feed.xml"

    def test_accepts_http(self):
        assert validate_feed_url("http://example.org/rss").allowed

    def test_rejects_non_http_schemes(self):
        for url in ("ftp://example.org/feed", "file:///etc/hosts", "javascript:alert(1)"):
            decision = validate_feed_url(url)
            assert not decision.allowed
            assert "http" in decision.reason

    def test_rejects_forbidden_host_patterns(self):
        decision = validate_feed_url("https://sci-hub.example/feed")
        assert not decision.allowed
        assert decision.source_kind == "blocked"

    def test_rejects_forbidden_pattern_anywhere_in_url(self):
        decision = validate_feed_url("https://mirror.example/libgen/rss")
        assert not decision.allowed

    def test_decision_is_frozen_dataclass(self):
        decision = validate_feed_url("https://example.org/feed")
        with pytest.raises(Exception):
            decision.allowed = False  # type: ignore[misc]

    def test_returns_decision_type(self):
        assert isinstance(validate_feed_url("https://example.org/x"), SourceDecision)


class TestSanitizeQuery:
    def test_passes_normal_query(self):
        assert sanitize_query("postgres pgvector hnsw") == "postgres pgvector hnsw"

    def test_strips_control_and_odd_characters(self):
        assert sanitize_query("hello\x00world;") == "helloworld"

    def test_rejects_too_short_after_sanitization(self):
        with pytest.raises(ValueError):
            sanitize_query(";;;")

    def test_truncates_overlong_queries(self):
        assert len(sanitize_query("a" * 1000)) == 512

    def test_keeps_useful_punctuation(self):
        assert sanitize_query('what is "RAG"?') == 'what is "RAG"?'


class TestAllowedSourceKinds:
    def test_expected_kinds_present(self):
        assert {"rss", "atom", "searxng", "public_web", "user_configured"} <= set(ALLOWED_SOURCE_KINDS)

    def test_no_shadow_library_kind(self):
        assert "shadow_library" not in ALLOWED_SOURCE_KINDS
