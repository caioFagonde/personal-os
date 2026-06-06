import pytest

from app.source_policy import classify_url, extract_doi, sanitize_query, validate_discovery_source


def test_blocks_pirate_discovery_sources():
    decision = validate_discovery_source("libgen")
    assert decision.allowed is False
    assert "pirate" in decision.reason


def test_allows_open_metadata_sources():
    assert validate_discovery_source("arxiv").allowed
    assert validate_discovery_source("OpenAlex").source_kind == "openalex"


def test_blocks_forbidden_hosts():
    decision = classify_url("https://example-libgen.test/book.pdf")
    assert not decision.allowed
    assert "blocked" in decision.reason


def test_allows_direct_pdf_url():
    decision = classify_url("https://example.edu/papers/file.pdf?download=1")
    assert decision.allowed
    assert decision.source_kind == "pdf"


def test_rejects_non_http_scheme():
    decision = classify_url("file:///etc/passwd")
    assert not decision.allowed


def test_extract_doi_and_sanitize_query():
    assert extract_doi("See DOI 10.1145/1234567.890123.") == "10.1145/1234567.890123"
    assert sanitize_query("  spectral   graph theory  ") == "spectral graph theory"
    with pytest.raises(ValueError):
        sanitize_query(" ")


def test_rejects_unsupported_discovery_source():
    decision = validate_discovery_source('random unsupported source')
    assert not decision.allowed
    assert 'unsupported' in decision.reason
