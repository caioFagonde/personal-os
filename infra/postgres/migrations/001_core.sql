CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  handle TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'America/Sao_Paulo',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS devices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  device_key TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('mobile','desktop','web','server','tablet','other')),
  platform TEXT,
  public_key TEXT,
  tailscale_ip INET,
  last_seen_at TIMESTAMPTZ,
  trust_level TEXT NOT NULL DEFAULT 'pending' CHECK (trust_level IN ('pending','trusted','revoked')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS modules (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  description TEXT,
  manifest JSONB NOT NULL,
  installed BOOLEAN NOT NULL DEFAULT true,
  health TEXT NOT NULL DEFAULT 'unknown',
  routes JSONB NOT NULL DEFAULT '{}',
  permissions TEXT[] NOT NULL DEFAULT '{}',
  publishes TEXT[] NOT NULL DEFAULT '{}',
  subscribes TEXT[] NOT NULL DEFAULT '{}',
  sync_enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  module_id TEXT REFERENCES modules(id) ON DELETE SET NULL,
  entity_type TEXT NOT NULL,
  external_id TEXT,
  current_version UUID,
  deleted_at TIMESTAMPTZ,
  created_by_device UUID REFERENCES devices(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(module_id, entity_type, external_id)
);

CREATE TABLE IF NOT EXISTS entity_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  device_id UUID REFERENCES devices(id),
  parent_version_id UUID REFERENCES entity_versions(id),
  version_clock JSONB NOT NULL DEFAULT '{}',
  operation TEXT NOT NULL CHECK (operation IN ('create','update','delete','merge')),
  merge_strategy TEXT NOT NULL DEFAULT 'lww' CHECK (merge_strategy IN ('lww','field_merge','crdt_text','set_union','counter','manual')),
  payload JSONB NOT NULL,
  checksum TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE entities
  DROP CONSTRAINT IF EXISTS entities_current_version_fkey;
ALTER TABLE entities
  ADD CONSTRAINT entities_current_version_fkey FOREIGN KEY (current_version) REFERENCES entity_versions(id);

CREATE TABLE IF NOT EXISTS sync_log (
  id BIGSERIAL PRIMARY KEY,
  event_id UUID NOT NULL DEFAULT gen_random_uuid(),
  module_id TEXT REFERENCES modules(id) ON DELETE SET NULL,
  entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,
  entity_type TEXT NOT NULL,
  version_id UUID REFERENCES entity_versions(id) ON DELETE SET NULL,
  device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  payload JSONB NOT NULL,
  vector_clock JSONB NOT NULL DEFAULT '{}',
  lamport BIGINT NOT NULL DEFAULT 0,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(event_id)
);
CREATE INDEX IF NOT EXISTS idx_sync_log_module_id ON sync_log(module_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_received_at ON sync_log(received_at);
CREATE INDEX IF NOT EXISTS idx_sync_log_lamport ON sync_log(lamport);

CREATE TABLE IF NOT EXISTS attachments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
  module_id TEXT REFERENCES modules(id) ON DELETE SET NULL,
  object_key TEXT NOT NULL,
  filename TEXT NOT NULL,
  content_type TEXT,
  size_bytes BIGINT NOT NULL DEFAULT 0,
  checksum TEXT NOT NULL,
  sync_state TEXT NOT NULL DEFAULT 'pending' CHECK (sync_state IN ('pending','local','remote','synced','conflict','deleted')),
  encrypted BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cloud_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  provider TEXT NOT NULL CHECK (provider IN ('google','microsoft')),
  account_email TEXT,
  scopes TEXT[] NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','active','revoked','error')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cloud_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cloud_account_id UUID NOT NULL REFERENCES cloud_accounts(id) ON DELETE CASCADE,
  token_type TEXT NOT NULL DEFAULT 'oauth_refresh',
  encrypted_token BYTEA NOT NULL,
  key_version TEXT NOT NULL,
  expires_at TIMESTAMPTZ,
  rotated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS calendar_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cloud_account_id UUID REFERENCES cloud_accounts(id) ON DELETE SET NULL,
  provider_event_id TEXT,
  module_id TEXT REFERENCES modules(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ,
  location TEXT,
  payload JSONB NOT NULL DEFAULT '{}',
  sync_state TEXT NOT NULL DEFAULT 'local',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS command_templates (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  command_kind TEXT NOT NULL CHECK (command_kind IN ('coding_harness','workflow','file_generation','notification','local_script')),
  allowed_scopes TEXT[] NOT NULL DEFAULT '{}',
  requires_approval BOOLEAN NOT NULL DEFAULT true,
  local_only BOOLEAN NOT NULL DEFAULT true,
  template JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS command_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  requester_device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  target_device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  template_id TEXT REFERENCES command_templates(id),
  status TEXT NOT NULL DEFAULT 'pending_approval' CHECK (status IN ('pending_approval','approved','queued','running','succeeded','failed','denied','cancelled')),
  scopes TEXT[] NOT NULL DEFAULT '{}',
  signed_payload TEXT,
  params JSONB NOT NULL DEFAULT '{}',
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS command_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  command_request_id UUID NOT NULL REFERENCES command_requests(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('running','succeeded','failed','cancelled')),
  stdout_ref TEXT,
  stderr_ref TEXT,
  artifacts JSONB NOT NULL DEFAULT '[]',
  exit_code INT,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  module_id TEXT REFERENCES modules(id) ON DELETE SET NULL,
  device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  channel TEXT NOT NULL CHECK (channel IN ('local','ntfy','email','calendar','push')),
  severity TEXT NOT NULL DEFAULT 'info' CHECK (severity IN ('debug','info','warning','critical')),
  title TEXT NOT NULL,
  body TEXT,
  payload JSONB NOT NULL DEFAULT '{}',
  delivered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS approvals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  request_type TEXT NOT NULL CHECK (request_type IN ('command','cloud_write','delete','external_send','workflow')),
  request_id UUID NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','denied','expired')),
  reason TEXT,
  decided_by_device_id UUID REFERENCES devices(id),
  decided_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGSERIAL PRIMARY KEY,
  profile_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
  device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  module_id TEXT REFERENCES modules(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  metadata JSONB NOT NULL DEFAULT '{}',
  ip INET,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL DEFAULT '',
  tags TEXT[] NOT NULL DEFAULT '{}',
  backlinks UUID[] NOT NULL DEFAULT '{}',
  geom GEOGRAPHY(Point, 4326),
  embedding VECTOR(768),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS study_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  source_ref TEXT,
  status TEXT NOT NULL DEFAULT 'queued',
  due_at TIMESTAMPTZ,
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS geospatial_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  description TEXT,
  geom GEOGRAPHY(Geometry, 4326),
  properties JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO profiles(handle, display_name)
VALUES ('default', 'Default Local Profile')
ON CONFLICT (handle) DO NOTHING;

INSERT INTO command_templates(id, name, description, command_kind, allowed_scopes, requires_approval, local_only, template)
VALUES
  ('cursor.open_project', 'Open project in Cursor', 'Requests the trusted desktop agent to open an allowlisted workspace.', 'coding_harness', ARRAY['projects.open'], true, true, '{"executor":"desktop-agent","allowlist":"projects"}'),
  ('codex.run_task', 'Run Codex task', 'Queues a local coding-harness task with artifacts returned to mobile.', 'coding_harness', ARRAY['code.read','code.write_sandbox'], true, true, '{"executor":"coding-harness","mode":"sandbox"}')
ON CONFLICT (id) DO NOTHING;
