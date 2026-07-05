-- Nexus Prime graph & memory spine (Phase B / PERSONAL_GRAPH_SCHEMA.md)
-- Registry layer over existing domain tables: objects + edges + object_chunks,
-- plus new domain tables: projects, decisions, daily_states, repositories,
-- portfolio_cases. All statements idempotent.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ---------------------------------------------------------------------------
-- Registry: one row per user-meaningful domain row
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS objects (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind         TEXT NOT NULL,                 -- canonical kinds (PERSONAL_GRAPH_SCHEMA.md)
    domain_table TEXT NOT NULL,                 -- e.g. 'tasks'
    domain_id    UUID NOT NULL,                 -- soft FK into domain table
    title        TEXT NOT NULL DEFAULT '',
    slug         TEXT,                          -- stable; source for Obsidian vault paths
    status       TEXT,                          -- kind-specific lifecycle
    project_id   UUID REFERENCES objects(id),   -- fast path for the most common edge
    tags         TEXT[] NOT NULL DEFAULT '{}',
    meta         JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ,
    UNIQUE (domain_table, domain_id)
);
CREATE INDEX IF NOT EXISTS idx_objects_kind_updated ON objects (kind, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_objects_tags ON objects USING gin (tags);
CREATE INDEX IF NOT EXISTS idx_objects_project ON objects (project_id);
-- Lexical fallback path: trigram index over titles (used when no embedding model).
CREATE INDEX IF NOT EXISTS idx_objects_title_trgm ON objects USING gin (title gin_trgm_ops);

CREATE TABLE IF NOT EXISTS edges (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    src_id     UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    dst_id     UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    rel        TEXT NOT NULL,                   -- relation vocabulary (PERSONAL_GRAPH_SCHEMA.md)
    weight     REAL NOT NULL DEFAULT 1.0,       -- future ranking/decay
    meta       JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (src_id, dst_id, rel)
);
CREATE INDEX IF NOT EXISTS idx_edges_src_rel ON edges (src_id, rel);
CREATE INDEX IF NOT EXISTS idx_edges_dst_rel ON edges (dst_id, rel);

CREATE TABLE IF NOT EXISTS object_chunks (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id  UUID NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
    seq        INT  NOT NULL DEFAULT 0,
    text       TEXT NOT NULL,
    embedding  vector(768),                     -- null until the embed worker fills it
    model      TEXT,                            -- embed model id; enables re-embedding
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (object_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_object_chunks_object ON object_chunks (object_id);
CREATE INDEX IF NOT EXISTS idx_object_chunks_embedding ON object_chunks USING hnsw (embedding vector_cosine_ops);
-- Lexical fallback path: trigram index over chunk text.
CREATE INDEX IF NOT EXISTS idx_object_chunks_text_trgm ON object_chunks USING gin (text gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- New domain tables
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT NOT NULL,
    slug       TEXT NOT NULL UNIQUE,
    status     TEXT NOT NULL DEFAULT 'active',  -- active|paused|done|archived
    pitch      TEXT NOT NULL DEFAULT '',
    north_star TEXT NOT NULL DEFAULT '',
    vault_path TEXT,                            -- Obsidian mapping override
    meta       JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (status, updated_at DESC);

CREATE TABLE IF NOT EXISTS decisions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title        TEXT NOT NULL,
    slug         TEXT NOT NULL,
    context      TEXT NOT NULL DEFAULT '',
    decision     TEXT NOT NULL,
    consequences TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'accepted', -- proposed|accepted|superseded
    decided_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    project_id   UUID,
    meta         JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions (project_id, decided_at DESC);

CREATE TABLE IF NOT EXISTS daily_states (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    day        DATE NOT NULL UNIQUE,
    intention  TEXT NOT NULL DEFAULT '',
    highlights JSONB NOT NULL DEFAULT '[]',
    energy     INT,                             -- 1..5, user-entered only
    mood       INT,                             -- 1..5, user-entered only
    review     TEXT NOT NULL DEFAULT '',
    closed     BOOLEAN NOT NULL DEFAULT false,
    meta       JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS repositories (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              TEXT NOT NULL,
    path              TEXT NOT NULL UNIQUE,
    remote_url        TEXT,
    default_branch    TEXT DEFAULT 'main',
    allowed_for_agent BOOLEAN NOT NULL DEFAULT false, -- DB-driven agent allowlist (Phase F)
    meta              JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS portfolio_cases (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title    TEXT NOT NULL,
    slug     TEXT NOT NULL UNIQUE,
    summary  TEXT NOT NULL DEFAULT '',
    problem  TEXT NOT NULL DEFAULT '',
    approach TEXT NOT NULL DEFAULT '',
    outcome  TEXT NOT NULL DEFAULT '',
    status   TEXT NOT NULL DEFAULT 'draft',
    meta     JSONB NOT NULL DEFAULT '{}'
);
