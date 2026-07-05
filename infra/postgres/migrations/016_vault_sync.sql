-- Phase D: Obsidian vault sync state.
-- One row per vault markdown file under the mapped roots. The base snapshot
-- is the 3-way merge ancestor; storing it inline (not MinIO) is a deliberate
-- v1 simplification — notes are small and merges must not depend on object
-- storage being up.

CREATE TABLE IF NOT EXISTS vault_files (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    relative_path  TEXT NOT NULL UNIQUE,
    nexus_id       UUID,                        -- objects.id join key; NULL = vault-only
    kind           TEXT,
    sha256         TEXT,                        -- content hash at last index
    mtime          TIMESTAMPTZ,
    base_snapshot  TEXT,                        -- content at last successful sync
    last_synced_rev TEXT,
    status         TEXT NOT NULL DEFAULT 'pending',  -- synced|pending|conflict|vault_only|app_only
    detail         TEXT NOT NULL DEFAULT '',
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_vault_files_nexus ON vault_files (nexus_id);
CREATE INDEX IF NOT EXISTS idx_vault_files_status ON vault_files (status, updated_at DESC);
