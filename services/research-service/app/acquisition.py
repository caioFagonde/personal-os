from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from typing import Any

import httpx

from .source_policy import sanitize_query, validate_discovery_source


@dataclass(frozen=True)
class SearchResult:
    source: str
    title: str
    authors: list[str]
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    landing_url: str | None = None
    pdf_url: str | None = None
    is_open_access: bool = False
    license: str | None = None
    abstract: str | None = None
    raw: dict[str, Any] | None = None

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["raw"] = self.raw or {}
        return record


async def search_sources(query: str, sources: list[str], limit: int = 10) -> list[SearchResult]:
    clean_query = sanitize_query(query)
    normalized_sources = []
    for source in sources:
        decision = validate_discovery_source(source)
        if not decision.allowed:
            continue
        normalized_sources.append(decision.source_kind)
    if not normalized_sources:
        normalized_sources = ["arxiv", "openalex", "crossref"]

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers={"User-Agent": "PersonalOSResearch/0.5"}) as client:
        tasks = []
        for source in normalized_sources:
            if source == "arxiv":
                tasks.append(search_arxiv(client, clean_query, limit))
            elif source == "openalex":
                tasks.append(search_openalex(client, clean_query, limit))
            elif source == "crossref":
                tasks.append(search_crossref(client, clean_query, limit))
            elif source == "semantic_scholar":
                tasks.append(search_semantic_scholar(client, clean_query, limit))
        results: list[SearchResult] = []
        for task in tasks:
            try:
                results.extend(await task)
            except Exception:
                # Search degradation is non-fatal; health/UI should show partial results.
                continue
    return dedupe_results(results)[: max(1, min(limit * max(1, len(normalized_sources)), 100))]


async def search_arxiv(client: httpx.AsyncClient, query: str, limit: int) -> list[SearchResult]:
    resp = await client.get(
        "https://export.arxiv.org/api/query",
        params={"search_query": f"all:{query}", "start": 0, "max_results": limit, "sortBy": "relevance"},
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out: list[SearchResult] = []
    for entry in root.findall("a:entry", ns):
        title = normalize_space((entry.findtext("a:title", default="Untitled", namespaces=ns)))
        authors = [normalize_space(a.findtext("a:name", default="", namespaces=ns)) for a in entry.findall("a:author", ns)]
        landing = entry.findtext("a:id", default="", namespaces=ns)
        arxiv_id = landing.rsplit("/", 1)[-1] if landing else None
        published = entry.findtext("a:published", default="", namespaces=ns)
        year = int(published[:4]) if published[:4].isdigit() else None
        summary = normalize_space(entry.findtext("a:summary", default="", namespaces=ns))
        out.append(
            SearchResult(
                source="arxiv",
                title=title,
                authors=[a for a in authors if a],
                year=year,
                venue="arXiv",
                landing_url=landing,
                pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None,
                is_open_access=True,
                license="arXiv license varies by paper",
                abstract=summary,
                raw={"arxiv_id": arxiv_id},
            )
        )
    return out


async def search_openalex(client: httpx.AsyncClient, query: str, limit: int) -> list[SearchResult]:
    resp = await client.get(
        "https://api.openalex.org/works",
        params={"search": query, "per-page": limit, "select": "id,title,authorships,publication_year,primary_location,open_access,doi,abstract_inverted_index"},
    )
    resp.raise_for_status()
    out: list[SearchResult] = []
    for item in resp.json().get("results", []):
        authors = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])]
        loc = item.get("primary_location") or {}
        source = loc.get("source") or {}
        oa = item.get("open_access") or {}
        out.append(
            SearchResult(
                source="openalex",
                title=item.get("title") or "Untitled",
                authors=[a for a in authors if a],
                year=item.get("publication_year"),
                venue=source.get("display_name"),
                doi=normalize_doi(item.get("doi")),
                landing_url=item.get("id"),
                pdf_url=oa.get("oa_url") if oa.get("is_oa") else None,
                is_open_access=bool(oa.get("is_oa")),
                license=oa.get("license"),
                abstract=reconstruct_openalex_abstract(item.get("abstract_inverted_index") or {}),
                raw={"openalex_id": item.get("id")},
            )
        )
    return out


async def search_crossref(client: httpx.AsyncClient, query: str, limit: int) -> list[SearchResult]:
    resp = await client.get("https://api.crossref.org/works", params={"query": query, "rows": limit})
    resp.raise_for_status()
    out: list[SearchResult] = []
    for item in resp.json().get("message", {}).get("items", []):
        authors = []
        for author in item.get("author", []):
            name = " ".join([author.get("given", ""), author.get("family", "")]).strip()
            if name:
                authors.append(name)
        year = None
        issued = item.get("issued", {}).get("date-parts", [[]])
        if issued and issued[0] and isinstance(issued[0][0], int):
            year = issued[0][0]
        links = item.get("link", []) or []
        pdf_url = next((lnk.get("URL") for lnk in links if "pdf" in (lnk.get("content-type") or "").lower()), None)
        out.append(
            SearchResult(
                source="crossref",
                title=(item.get("title") or ["Untitled"])[0],
                authors=authors,
                year=year,
                venue=(item.get("container-title") or [None])[0],
                doi=normalize_doi(item.get("DOI")),
                landing_url=item.get("URL"),
                pdf_url=pdf_url,
                is_open_access=bool(pdf_url),
                license=(item.get("license") or [{}])[0].get("URL") if item.get("license") else None,
                abstract=strip_html(item.get("abstract")),
                raw={"publisher": item.get("publisher"), "type": item.get("type")},
            )
        )
    return out


async def search_semantic_scholar(client: httpx.AsyncClient, query: str, limit: int) -> list[SearchResult]:
    resp = await client.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={"query": query, "limit": limit, "fields": "title,authors,year,venue,externalIds,openAccessPdf,abstract,url"},
    )
    resp.raise_for_status()
    out: list[SearchResult] = []
    for item in resp.json().get("data", []):
        oa = item.get("openAccessPdf") or {}
        external = item.get("externalIds") or {}
        authors = [a.get("name", "") for a in item.get("authors", [])]
        out.append(
            SearchResult(
                source="semantic_scholar",
                title=item.get("title") or "Untitled",
                authors=[a for a in authors if a],
                year=item.get("year"),
                venue=item.get("venue"),
                doi=normalize_doi(external.get("DOI")),
                landing_url=item.get("url"),
                pdf_url=oa.get("url"),
                is_open_access=bool(oa.get("url")),
                abstract=item.get("abstract"),
                raw={"paper_id": item.get("paperId"), "arxiv": external.get("ArXiv")},
            )
        )
    return out


def dedupe_results(results: list[SearchResult]) -> list[SearchResult]:
    seen: set[str] = set()
    out: list[SearchResult] = []
    for result in results:
        key = (result.doi or result.landing_url or result.title).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(result)
    return out


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = value.replace("https://doi.org/", "").replace("http://dx.doi.org/", "").strip()
    return value or None


def strip_html(value: str | None) -> str | None:
    if not value:
        return None
    return normalize_space(re.sub(r"<[^>]+>", " ", html.unescape(value)))


def reconstruct_openalex_abstract(index: dict[str, list[int]]) -> str | None:
    if not index:
        return None
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        words.extend((pos, word) for pos in positions)
    return " ".join(word for _pos, word in sorted(words))
