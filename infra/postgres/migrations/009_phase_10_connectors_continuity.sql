-- Phase 10: connector onboarding, OAuth continuity, backup manifests, and device pairing.
-- Idempotent and safe to replay.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE cloud_accounts DROP CONSTRAINT IF EXISTS cloud_accounts_provider_check;
ALTER TABLE cloud_accounts ADD CONSTRAINT cloud_accounts_provider_check CHECK (provider IN ('google','microsoft','twilio','ntfy','tailscale','smtp','backup'));

CREATE TABLE IF NOT EXISTS connector_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL CHECK(provider IN ('google','microsoft','twilio','ntfy','tailscale','smtp','backup')),
  display_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'needs_configuration' CHECK(status IN ('needs_configuration','manual_authorization_required','pending','active','degraded','error','revoked')),
  settings JSONB NOT NULL DEFAULT '{}',
  last_checked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(provider, display_name)
);

CREATE TABLE IF NOT EXISTS connector_oauth_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL CHECK(provider IN ('google','microsoft')),
  state TEXT NOT NULL UNIQUE,
  code_verifier TEXT NOT NULL,
  scopes TEXT[] NOT NULL DEFAULT '{}',
  redirect_uri TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_connector_oauth_states_valid ON connector_oauth_states(provider, state, expires_at) WHERE consumed_at IS NULL;

CREATE TABLE IF NOT EXISTS connector_health_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  status TEXT NOT NULL,
  message TEXT NOT NULL DEFAULT '',
  details JSONB NOT NULL DEFAULT '{}',
  checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_connector_health_provider ON connector_health_checks(provider, checked_at DESC);

CREATE TABLE IF NOT EXISTS connector_test_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  target TEXT,
  dry_run BOOLEAN NOT NULL DEFAULT true,
  status TEXT NOT NULL,
  response JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backup_manifests (
  backup_id TEXT PRIMARY KEY,
  archive_path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  included_paths TEXT[] NOT NULL DEFAULT '{}',
  encrypted BOOLEAN NOT NULL DEFAULT false,
  remote_uri TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  verified_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS restore_drills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  backup_id TEXT REFERENCES backup_manifests(backup_id) ON DELETE SET NULL,
  status TEXT NOT NULL CHECK(status IN ('planned','running','passed','failed')),
  checks JSONB NOT NULL DEFAULT '{}',
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS device_pairing_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  code_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_by_device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  consumed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_device_pairing_codes_open ON device_pairing_codes(expires_at) WHERE consumed_at IS NULL;

INSERT INTO connector_accounts(provider, display_name, status, settings)
VALUES
  ('google', 'Google Workspace', 'needs_configuration', '{"auth":"oauth2","capabilities":["gmail","drive","calendar"]}'),
  ('microsoft', 'Microsoft 365', 'needs_configuration', '{"auth":"oauth2","capabilities":["outlook","onedrive","calendar"]}'),
  ('twilio', 'Twilio WhatsApp', 'needs_configuration', '{"auth":"basic","capabilities":["whatsapp"]}'),
  ('ntfy', 'ntfy Local Push', 'needs_configuration', '{"auth":"topic","capabilities":["push"]}'),
  ('tailscale', 'Tailscale Mesh', 'manual_authorization_required', '{"auth":"tailnet","capabilities":["mesh","device-discovery"]}'),
  ('backup', 'Encrypted Backup', 'needs_configuration', '{"auth":"local-key","capabilities":["export","restore"]}')
ON CONFLICT(provider, display_name) DO NOTHING;

INSERT INTO api_boundary_routes(id, service_name, upstream_url, read_scope, write_scope)
VALUES ('connectors', 'connector-service', 'http://connector-service:8094', 'connectors:read', 'connectors:write')
ON CONFLICT (id) DO UPDATE SET upstream_url=EXCLUDED.upstream_url, read_scope=EXCLUDED.read_scope, write_scope=EXCLUDED.write_scope, updated_at=now();

INSERT INTO modules(id, name, version, description, manifest, installed, health, routes, permissions, publishes, subscribes, sync_enabled, updated_at)
VALUES(
  'connectors',
  'Connector Onboarding',
  '0.1.0',
  'OAuth, messaging, push, mesh, backup, restore, and device-pairing onboarding.',
  '{"id":"connectors","name":"Connector Onboarding","version":"0.1.0","routes":{"web":"/connectors","api":"/api/proxy/connectors"},"permissions":["connectors:read","connectors:write"],"events":{"publishes":["connector.connected","backup.created"],"subscribes":["message.queued"]},"sync":{"enabled":true,"strategy":"local-first"}}'::jsonb,
  true,
  'ok',
  '{"web":"/connectors","api":"/api/proxy/connectors"}'::jsonb,
  ARRAY['connectors:read','connectors:write'],
  ARRAY['connector.connected','backup.created'],
  ARRAY['message.queued'],
  true,
  now()
)
ON CONFLICT(id) DO UPDATE SET version=EXCLUDED.version, manifest=EXCLUDED.manifest, routes=EXCLUDED.routes, permissions=EXCLUDED.permissions, health='ok', updated_at=now();
