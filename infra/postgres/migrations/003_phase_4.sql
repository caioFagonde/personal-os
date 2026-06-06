-- Phase 4: mobile/desktop packaging support, auth rotation, API boundary metadata.
-- Idempotent; safe for local dev re-runs.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS jti TEXT;
ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS key_id TEXT NOT NULL DEFAULT 'local-v1';
ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS token_type TEXT NOT NULL DEFAULT 'access' CHECK (token_type IN ('access','service'));
ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS user_agent TEXT;
ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS rotated_from UUID REFERENCES auth_sessions(id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_sessions_jti_unique ON auth_sessions(jti) WHERE jti IS NOT NULL;

CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES auth_sessions(id) ON DELETE CASCADE,
  profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL,
  scopes TEXT[] NOT NULL DEFAULT '{}',
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  rotated_at TIMESTAMPTZ,
  replaced_by UUID REFERENCES auth_refresh_tokens(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_refresh_token_hash ON auth_refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_device ON auth_refresh_tokens(device_id, expires_at DESC);

CREATE TABLE IF NOT EXISTS api_boundary_routes (
  id TEXT PRIMARY KEY,
  service_name TEXT NOT NULL,
  upstream_url TEXT NOT NULL,
  read_scope TEXT NOT NULL,
  write_scope TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO api_boundary_routes(id, service_name, upstream_url, read_scope, write_scope)
VALUES
  ('sync', 'sync-engine', 'http://sync-engine:8081', 'sync:read', 'sync:write'),
  ('modules', 'module-service', 'http://module-service:8083', 'module:read', 'module:write'),
  ('commands', 'command-bus', 'http://command-bus:8082', 'command:read', 'command:request')
ON CONFLICT (id) DO UPDATE SET
  upstream_url = EXCLUDED.upstream_url,
  read_scope = EXCLUDED.read_scope,
  write_scope = EXCLUDED.write_scope,
  updated_at = now();

ALTER TABLE devices ADD COLUMN IF NOT EXISTS app_version TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS build_channel TEXT NOT NULL DEFAULT 'dev';
ALTER TABLE devices ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS build_artifacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform TEXT NOT NULL CHECK (platform IN ('android','desktop','web')),
  version TEXT NOT NULL,
  channel TEXT NOT NULL DEFAULT 'dev',
  commit_sha TEXT,
  artifact_ref TEXT,
  checksum TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO settings(key, value)
VALUES
  ('security.access_token_ttl_seconds', '900'::jsonb),
  ('security.refresh_token_ttl_days', '30'::jsonb),
  ('security.auth_required_recommended', 'true'::jsonb),
  ('apps.mobile.package_id', 'io.personalos.mobile'::jsonb),
  ('apps.desktop.bundle_id', 'io.personalos.desktop'::jsonb),
  ('ci.coverage.backend_pure_gate', '100'::jsonb),
  ('ci.coverage.frontend_gate', '90'::jsonb)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now();
