-- Phase 1-3 substrate hardening, sync expansion, and first real modules.
-- Idempotent by design; safe to re-run during local development.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS auth_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL,
  scopes TEXT[] NOT NULL DEFAULT '{}',
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_device ON auth_sessions(device_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_token_hash ON auth_sessions(token_hash);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_by_device_id UUID REFERENCES devices(id),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS service_events (
  id BIGSERIAL PRIMARY KEY,
  topic TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  published BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  published_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_service_events_topic ON service_events(topic);
CREATE INDEX IF NOT EXISTS idx_service_events_unpublished ON service_events(published, id);

CREATE TABLE IF NOT EXISTS sync_conflicts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  module_id TEXT REFERENCES modules(id) ON DELETE SET NULL,
  entity_type TEXT NOT NULL,
  local_version_id UUID REFERENCES entity_versions(id),
  remote_version_id UUID REFERENCES entity_versions(id),
  local_payload JSONB NOT NULL DEFAULT '{}',
  remote_payload JSONB NOT NULL DEFAULT '{}',
  local_clock JSONB NOT NULL DEFAULT '{}',
  remote_clock JSONB NOT NULL DEFAULT '{}',
  strategy TEXT NOT NULL DEFAULT 'manual',
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','resolved','ignored')),
  resolution JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sync_conflicts_status ON sync_conflicts(status);
CREATE INDEX IF NOT EXISTS idx_sync_conflicts_entity ON sync_conflicts(entity_id);

ALTER TABLE attachments ADD COLUMN IF NOT EXISTS storage_provider TEXT NOT NULL DEFAULT 'minio';
ALTER TABLE attachments ADD COLUMN IF NOT EXISTS uploaded_by_device_id UUID REFERENCES devices(id);
ALTER TABLE attachments ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMPTZ;

ALTER TABLE notes ADD COLUMN IF NOT EXISTS slug TEXT;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS note_type TEXT NOT NULL DEFAULT 'permanent' CHECK (note_type IN ('fleeting','literature','permanent','map','reference'));
ALTER TABLE notes ADD COLUMN IF NOT EXISTS source_path TEXT;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS frontmatter JSONB NOT NULL DEFAULT '{}';
CREATE UNIQUE INDEX IF NOT EXISTS idx_notes_slug ON notes(slug) WHERE slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notes_tags ON notes USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_notes_geom ON notes USING GIST(geom);

CREATE TABLE IF NOT EXISTS zettel_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_note_id UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  target_note_id UUID REFERENCES notes(id) ON DELETE CASCADE,
  target_title TEXT NOT NULL,
  link_type TEXT NOT NULL DEFAULT 'wiki',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(source_note_id, target_title, link_type)
);
CREATE INDEX IF NOT EXISTS idx_zettel_links_source ON zettel_links(source_note_id);
CREATE INDEX IF NOT EXISTS idx_zettel_links_target ON zettel_links(target_note_id);

ALTER TABLE study_items ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'reading' CHECK (kind IN ('reading','course','paper','flashcard_set','practice','project'));
ALTER TABLE study_items ADD COLUMN IF NOT EXISTS priority INT NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5);
ALTER TABLE study_items ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE study_items ADD COLUMN IF NOT EXISTS progress NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100);
CREATE INDEX IF NOT EXISTS idx_study_items_status ON study_items(status);
CREATE INDEX IF NOT EXISTS idx_study_items_due_at ON study_items(due_at);

CREATE TABLE IF NOT EXISTS study_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID REFERENCES study_items(id) ON DELETE SET NULL,
  device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  duration_minutes INT NOT NULL DEFAULT 0,
  notes TEXT,
  metrics JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_study_sessions_item ON study_sessions(item_id);

CREATE TABLE IF NOT EXISTS flashcards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID REFERENCES study_items(id) ON DELETE SET NULL,
  note_id UUID REFERENCES notes(id) ON DELETE SET NULL,
  concept TEXT NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  interval_days INT NOT NULL DEFAULT 1,
  ease_factor NUMERIC(4,2) NOT NULL DEFAULT 2.50,
  repetitions INT NOT NULL DEFAULT 0,
  due_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  suspended BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_flashcards_due ON flashcards(due_at) WHERE suspended = false;

ALTER TABLE geospatial_memories ADD COLUMN IF NOT EXISTS memory_type TEXT NOT NULL DEFAULT 'poi' CHECK (memory_type IN ('poi','route','area','field_note','anchor'));
ALTER TABLE geospatial_memories ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';
CREATE INDEX IF NOT EXISTS idx_geospatial_memories_geom ON geospatial_memories USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_geospatial_memories_tags ON geospatial_memories USING GIN(tags);

CREATE TABLE IF NOT EXISTS cloud_sync_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cloud_account_id UUID REFERENCES cloud_accounts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL CHECK (provider IN ('google','microsoft')),
  job_kind TEXT NOT NULL CHECK (job_kind IN ('drive_pull','drive_push','calendar_pull','calendar_push','contacts_pull','mail_hook')),
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
  payload JSONB NOT NULL DEFAULT '{}',
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ
);

INSERT INTO settings(key, value)
VALUES
  ('sync.default_strategy', '"field_merge"'::jsonb),
  ('security.auth_required', 'false'::jsonb),
  ('storage.artifact_bucket', '"artifacts"'::jsonb),
  ('modules.enabled', '["study","zettelkasten","geospatial"]'::jsonb)
ON CONFLICT (key) DO NOTHING;
