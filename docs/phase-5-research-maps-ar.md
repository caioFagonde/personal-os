# Phase 5 — Geospatial, AR, and Research Expansion

Phase 5 adds three major surfaces:

1. **Research acquisition and PDF ingestion**
2. **Offline maps and pgRouting preparation**
3. **AR memory anchors and spatial projection utilities**

## Research acquisition policy

The research subsystem supports:

- Public metadata search via `arxiv`, `openalex`, `crossref`, and optional `semantic_scholar`.
- Open-access PDF URLs returned by those catalogs.
- Direct user-authorized PDF URLs.
- Local PDF uploads.
- PDF text extraction, chunking, full-text search, and citation candidate extraction.

It intentionally does **not** include connectors for pirate libraries, paywall circumvention, credential sharing, or source scraping designed to bypass access controls. The backend blocks common pirate-library host patterns through `FORBIDDEN_SOURCE_HOST_PATTERNS`.

## Research endpoints

```txt
GET  /api/research/sources
POST /api/research/search
POST /api/research/policy/check-url
POST /api/research/documents/upload
POST /api/research/documents/fetch-url
GET  /api/research/documents
GET  /api/research/documents/{document_id}
GET  /api/research/documents/{document_id}/chunks
GET  /api/research/documents/{document_id}/citations
GET  /api/research/local-search?q=...
```

Run:

```bash
docker compose --profile research up -d --build research-service searxng qdrant embeddings
```

## Offline maps

Map datasets are registered in `map_datasets`. The TileServer profile serves files under `data/maps`.

```bash
mkdir -p data/maps
cp region.mbtiles data/maps/region.mbtiles
ACCESS_TOKEN=... scripts/maps/register-mbtiles.sh "Region" "maps/region.mbtiles"
docker compose --profile maps up -d tileserver
```

For routing, import OSM data into `ways_noded` with:

```bash
scripts/maps/import-osm-pgrouting.sh data/maps/region.osm.pbf
```

The module API can plan a route. Until `ways_noded` exists, it returns a straight-line GeoJSON fallback so the UI remains deterministic.

## AR memory

AR memory stores anchors in `ar_anchors` and observations in `ar_anchor_observations`.

Projection endpoint:

```txt
POST /api/ar/project
```

Payload:

```json
{
  "alpha": 0,
  "beta": 0,
  "gamma": 0,
  "distance_m": 2
}
```

Response:

```json
{
  "local_x": 0,
  "local_y": 0,
  "local_z": -2,
  "billboard_yaw_rad": 0
}
```

## Testing

Phase 5 adds isolated tests for:

- Research source policy
- PDF chunking and citation extraction
- Acquisition normalization/deduplication
- AR orientation projection math
- Scaffold-level Phase 5 file presence

Run:

```bash
python3 -m pytest tests services/research-service/tests services/module-service/tests -q
```
