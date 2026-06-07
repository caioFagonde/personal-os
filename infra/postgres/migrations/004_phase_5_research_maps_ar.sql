-- Phase 5: research acquisition, PDF ingestion, offline maps, routing, and AR anchors.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS research_search_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
    query TEXT NOT NULL,
    requested_sources TEXT[] NOT NULL DEFAULT '{}',
    policy JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS research_search_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES research_search_runs(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    authors TEXT[] NOT NULL DEFAULT '{}',
    year INT,
    venue TEXT,
    doi TEXT,
    landing_url TEXT,
    pdf_url TEXT,
    is_open_access BOOLEAN NOT NULL DEFAULT false,
    license TEXT,
    abstract TEXT,
    raw JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_research_search_results_dedupe
    ON research_search_results (run_id, source, COALESCE(doi, ''), COALESCE(landing_url, ''), title);

CREATE TABLE IF NOT EXISTS research_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,
    profile_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    source_kind TEXT NOT NULL DEFAULT 'upload',
    source_url TEXT,
    doi TEXT,
    authors TEXT[] NOT NULL DEFAULT '{}',
    year INT,
    license TEXT,
    object_uri TEXT,
    content_sha256 TEXT NOT NULL,
    mime_type TEXT NOT NULL DEFAULT 'application/pdf',
    page_count INT,
    text_status TEXT NOT NULL DEFAULT 'pending' CHECK (text_status IN ('pending','extracted','needs_ocr','failed')),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(content_sha256)
);

CREATE TABLE IF NOT EXISTS research_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES research_documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    page_start INT,
    page_end INT,
    content TEXT NOT NULL,
    token_estimate INT NOT NULL DEFAULT 0,
    embedding vector(768),
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(document_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_research_chunks_tsv ON research_chunks USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_research_chunks_doc ON research_chunks(document_id, chunk_index);

CREATE TABLE IF NOT EXISTS research_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES research_documents(id) ON DELETE CASCADE,
    citation_key TEXT,
    raw_text TEXT NOT NULL,
    doi TEXT,
    url TEXT,
    authors TEXT[] NOT NULL DEFAULT '{}',
    year INT,
    title TEXT,
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_research_citations_doc ON research_citations(document_id);

CREATE TABLE IF NOT EXISTS research_ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','succeeded','failed','blocked')),
    source_url TEXT,
    document_id UUID REFERENCES research_documents(id) ON DELETE SET NULL,
    reason TEXT,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS map_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    dataset_type TEXT NOT NULL CHECK (dataset_type IN ('mbtiles','pmtiles','osm_pbf','geojson','raster','other')),
    local_path TEXT NOT NULL,
    bounds GEOMETRY(POLYGON, 4326),
    min_zoom INT,
    max_zoom INT,
    attribution TEXT,
    status TEXT NOT NULL DEFAULT 'registered' CHECK (status IN ('registered','indexed','failed','archived')),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(local_path)
);

CREATE TABLE IF NOT EXISTS map_import_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES map_datasets(id) ON DELETE SET NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','succeeded','failed')),
    command_preview TEXT,
    logs TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS routing_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    mode TEXT NOT NULL DEFAULT 'walk',
    cost_expression TEXT NOT NULL DEFAULT 'length_m',
    reverse_cost_expression TEXT NOT NULL DEFAULT 'length_m',
    restrictions JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO routing_profiles(name, mode, cost_expression, reverse_cost_expression)
VALUES ('walking-default','walk','length_m','length_m')
ON CONFLICT(name) DO NOTHING;

CREATE TABLE IF NOT EXISTS ar_anchors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,
    note_id UUID REFERENCES notes(id) ON DELETE SET NULL,
    geospatial_memory_id UUID REFERENCES geospatial_memories(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    anchor_type TEXT NOT NULL DEFAULT 'note' CHECK (anchor_type IN ('note','memory','waypoint','reference_marker','custom')),
    geom GEOGRAPHY(POINTZ, 4326),
    local_x DOUBLE PRECISION NOT NULL DEFAULT 0,
    local_y DOUBLE PRECISION NOT NULL DEFAULT 0,
    local_z DOUBLE PRECISION NOT NULL DEFAULT 0,
    yaw DOUBLE PRECISION NOT NULL DEFAULT 0,
    pitch DOUBLE PRECISION NOT NULL DEFAULT 0,
    roll DOUBLE PRECISION NOT NULL DEFAULT 0,
    reference_marker TEXT,
    drift_state JSONB NOT NULL DEFAULT '{}',
    properties JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ar_anchors_geom ON ar_anchors USING GIST(geom);

CREATE TABLE IF NOT EXISTS ar_anchor_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchor_id UUID NOT NULL REFERENCES ar_anchors(id) ON DELETE CASCADE,
    device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    altitude DOUBLE PRECISION,
    alpha DOUBLE PRECISION,
    beta DOUBLE PRECISION,
    gamma DOUBLE PRECISION,
    distance_m DOUBLE PRECISION,
    local_x DOUBLE PRECISION,
    local_y DOUBLE PRECISION,
    local_z DOUBLE PRECISION,
    quality NUMERIC(4,3) NOT NULL DEFAULT 0.5,
    payload JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_ar_observations_anchor ON ar_anchor_observations(anchor_id, observed_at DESC);
