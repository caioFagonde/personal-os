import asyncio

import pytest

from app import acquisition
from app.acquisition import search_arxiv, search_crossref, search_openalex, search_semantic_scholar, search_sources


class FakeResponse:
    def __init__(self, *, text=None, json_data=None):
        self.text = text or ""
        self._json = json_data or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._json


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def get(self, url, params=None):
        self.calls.append((url, params))
        return self.response


def run(coro):
    return asyncio.run(coro)


def test_search_arxiv_parses_atom_response():
    xml = '''<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>https://arxiv.org/abs/2401.12345</id>
        <title> Test Paper </title>
        <published>2024-01-01T00:00:00Z</published>
        <summary> A summary. </summary>
        <author><name>Ada Lovelace</name></author>
      </entry>
    </feed>'''
    results = run(search_arxiv(FakeClient(FakeResponse(text=xml)), "test", 1))
    assert results[0].source == "arxiv"
    assert results[0].pdf_url.endswith("2401.12345.pdf")
    assert results[0].year == 2024


def test_search_openalex_parses_json_response():
    response = {
        "results": [{
            "id": "https://openalex.org/W1",
            "title": "Open Work",
            "authorships": [{"author": {"display_name": "Grace Hopper"}}],
            "publication_year": 2023,
            "primary_location": {"source": {"display_name": "Journal"}},
            "open_access": {"is_oa": True, "oa_url": "https://example.edu/open.pdf", "license": "cc-by"},
            "doi": "https://doi.org/10.1000/open",
            "abstract_inverted_index": {"hello": [0], "world": [1]},
        }]
    }
    results = run(search_openalex(FakeClient(FakeResponse(json_data=response)), "open", 1))
    assert results[0].doi == "10.1000/open"
    assert results[0].abstract == "hello world"
    assert results[0].is_open_access


def test_search_crossref_parses_json_response():
    response = {"message": {"items": [{
        "title": ["Crossref Work"],
        "author": [{"given": "Alan", "family": "Turing"}],
        "issued": {"date-parts": [[1950]]},
        "container-title": ["Mind"],
        "DOI": "10.1000/cross",
        "URL": "https://doi.org/10.1000/cross",
        "link": [{"content-type": "application/pdf", "URL": "https://example.edu/cross.pdf"}],
        "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
        "abstract": "<jats:p>Hello</jats:p>",
        "publisher": "Publisher",
        "type": "journal-article",
    }]}}
    results = run(search_crossref(FakeClient(FakeResponse(json_data=response)), "cross", 1))
    assert results[0].authors == ["Alan Turing"]
    assert results[0].pdf_url.endswith("cross.pdf")
    assert results[0].abstract == "Hello"


def test_search_semantic_scholar_parses_json_response():
    response = {"data": [{
        "paperId": "abc",
        "title": "S2 Work",
        "authors": [{"name": "Katherine Johnson"}],
        "year": 2022,
        "venue": "Venue",
        "externalIds": {"DOI": "10.1000/s2", "ArXiv": "2201.1"},
        "openAccessPdf": {"url": "https://example.edu/s2.pdf"},
        "abstract": "Abstract",
        "url": "https://semanticscholar.org/paper/abc",
    }]}
    results = run(search_semantic_scholar(FakeClient(FakeResponse(json_data=response)), "s2", 1))
    assert results[0].doi == "10.1000/s2"
    assert results[0].is_open_access


def test_search_sources_filters_blocked_and_dedupes(monkeypatch):
    async def fake_arxiv(client, query, limit):
        return [acquisition.SearchResult(source="arxiv", title="A", authors=[], doi="10.1/a")]

    async def fake_openalex(client, query, limit):
        return [acquisition.SearchResult(source="openalex", title="A duplicate", authors=[], doi="10.1/a")]

    monkeypatch.setattr(acquisition, "search_arxiv", fake_arxiv)
    monkeypatch.setattr(acquisition, "search_openalex", fake_openalex)
    results = run(search_sources("query", ["arxiv", "openalex", "libgen"], 5))
    assert len(results) == 1
    assert results[0].source == "arxiv"


def test_search_result_to_record_uses_empty_raw():
    rec = acquisition.SearchResult(source="x", title="T", authors=[]).to_record()
    assert rec["raw"] == {}


def test_search_sources_defaults_when_all_sources_blocked(monkeypatch):
    async def fake_arxiv(client, query, limit):
        return [acquisition.SearchResult(source="arxiv", title="Default", authors=[])]

    async def fake_openalex(client, query, limit):
        return []

    async def fake_crossref(client, query, limit):
        return []

    monkeypatch.setattr(acquisition, "search_arxiv", fake_arxiv)
    monkeypatch.setattr(acquisition, "search_openalex", fake_openalex)
    monkeypatch.setattr(acquisition, "search_crossref", fake_crossref)
    results = run(search_sources("query", ["libgen"], 2))
    assert [r.title for r in results] == ["Default"]


def test_search_sources_degrades_when_adapter_raises(monkeypatch):
    async def failing(client, query, limit):
        raise RuntimeError("network down")

    async def fake_crossref(client, query, limit):
        return [acquisition.SearchResult(source="crossref", title="OK", authors=[])]

    monkeypatch.setattr(acquisition, "search_arxiv", failing)
    monkeypatch.setattr(acquisition, "search_crossref", fake_crossref)
    results = run(search_sources("query", ["arxiv", "crossref"], 1))
    assert len(results) == 1
    assert results[0].title == "OK"


def test_search_crossref_handles_missing_optional_fields():
    response = {"message": {"items": [{"title": ["Minimal"], "author": [{"given": "", "family": ""}], "issued": {"date-parts": [[]]}, "DOI": None}]}}
    results = run(search_crossref(FakeClient(FakeResponse(json_data=response)), "minimal", 1))
    assert results[0].authors == []
    assert results[0].year is None
    assert results[0].pdf_url is None


def test_strip_html_and_empty_abstract_helpers():
    assert acquisition.strip_html(None) is None
    assert acquisition.reconstruct_openalex_abstract({}) is None
