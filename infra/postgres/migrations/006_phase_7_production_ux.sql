-- Phase 7: production hardening, observability, release metadata, and UX preferences.

CREATE TABLE IF NOT EXISTS service_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name TEXT UNIQUE NOT NULL,
    audience TEXT NOT NULL DEFAULT 'personal-os-internal',
    scopes TEXT[] NOT NULL DEFAULT '{}',
    public_key TEXT,
    signing_key_id TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','rotating','revoked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    rotated_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS durable_event_consumers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consumer_name TEXT UNIQUE NOT NULL,
    stream_name TEXT NOT NULL,
    durable_name TEXT NOT NULL,
    filter_subject TEXT NOT NULL,
    ack_policy TEXT NOT NULL DEFAULT 'explicit',
    max_deliver INT NOT NULL DEFAULT 5,
    backoff_seconds INT[] NOT NULL DEFAULT ARRAY[1,5,30,120],
    last_sequence BIGINT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(stream_name, durable_name)
);

CREATE TABLE IF NOT EXISTS release_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel TEXT NOT NULL CHECK (channel IN ('dev','nightly','alpha','beta','rc','stable')),
    platform TEXT NOT NULL CHECK (platform IN ('web','android','desktop','server')),
    version TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    artifact_url TEXT,
    checksum_sha256 TEXT,
    rollout_percent INT NOT NULL DEFAULT 0 CHECK (rollout_percent BETWEEN 0 AND 100),
    mandatory BOOLEAN NOT NULL DEFAULT false,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(channel, platform, version)
);

CREATE TABLE IF NOT EXISTS client_sync_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    last_foreground_sync_at TIMESTAMPTZ,
    last_background_sync_at TIMESTAMPTZ,
    pending_mutations INT NOT NULL DEFAULT 0,
    conflict_count INT NOT NULL DEFAULT 0,
    battery_hint TEXT,
    network_hint TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(device_id, platform)
);

CREATE TABLE IF NOT EXISTS ux_preferences (
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    theme TEXT NOT NULL DEFAULT 'system' CHECK (theme IN ('system','light','dark','ultra-dark')),
    density TEXT NOT NULL DEFAULT 'comfortable' CHECK (density IN ('compact','comfortable','spacious')),
    accent TEXT NOT NULL DEFAULT 'aurora',
    reduced_motion BOOLEAN NOT NULL DEFAULT false,
    high_contrast BOOLEAN NOT NULL DEFAULT false,
    dashboard_layout JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(profile_id, device_id)
);

CREATE TABLE IF NOT EXISTS telemetry_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
    service_name TEXT,
    event_name TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info' CHECK (severity IN ('debug','info','warning','error','critical')),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS service_health_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ok','degraded','down','unknown')),
    latency_ms DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_events_device_time ON telemetry_events(device_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_service_health_time ON service_health_snapshots(service_name, checked_at DESC);

INSERT INTO service_identities(service_name, scopes, signing_key_id)
VALUES
  ('api-gateway', ARRAY['health:write','events:publish','proxy:internal'], 'service-v1'),
  ('sync-engine', ARRAY['events:publish','sync:write'], 'service-v1'),
  ('automation-service', ARRAY['events:consume','command:request','notifications:send'], 'service-v1'),
  ('module-service', ARRAY['module:read','module:write','events:publish'], 'service-v1'),
  ('research-service', ARRAY['research:read','research:write','events:publish'], 'service-v1')
ON CONFLICT(service_name) DO UPDATE SET scopes=EXCLUDED.scopes, status='active';

INSERT INTO durable_event_consumers(consumer_name, stream_name, durable_name, filter_subject)
VALUES
  ('automation-workflow-trigger', 'PERSONAL_OS_EVENTS', 'automation-workflow-trigger', 'event.*'),
  ('sync-audit-writer', 'PERSONAL_OS_EVENTS', 'sync-audit-writer', 'sync.*'),
  ('notification-router', 'PERSONAL_OS_EVENTS', 'notification-router', 'notification.*')
ON CONFLICT(consumer_name) DO NOTHING;
