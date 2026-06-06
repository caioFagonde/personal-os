-- Phase 11: durable connector worker, backup upload tracking, pairing and sync UX support.
-- Idempotent and safe to replay.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE message_outbox ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ;
ALTER TABLE message_outbox ADD COLUMN IF NOT EXISTS locked_by TEXT;
ALTER TABLE message_outbox ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_message_outbox_idempotency ON message_outbox(idempotency_key) WHERE idempotency_key IS NOT NULL;

ALTER TABLE automation_outbox ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ;
ALTER TABLE automation_outbox ADD COLUMN IF NOT EXISTS locked_by TEXT;

ALTER TABLE notification_deliveries ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ;
ALTER TABLE notification_deliveries ADD COLUMN IF NOT EXISTS locked_by TEXT;

CREATE TABLE IF NOT EXISTS connector_worker_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  worker_id TEXT NOT NULL,
  execute BOOLEAN NOT NULL DEFAULT false,
  message_count INT NOT NULL DEFAULT 0,
  automation_count INT NOT NULL DEFAULT 0,
  notification_count INT NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK(status IN ('running','passed','failed')) DEFAULT 'running',
  error TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_connector_worker_runs_started ON connector_worker_runs(started_at DESC);

CREATE TABLE IF NOT EXISTS remote_backup_uploads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  backup_id TEXT REFERENCES backup_manifests(backup_id) ON DELETE CASCADE,
  provider TEXT NOT NULL CHECK(provider IN ('google','microsoft')),
  remote_uri TEXT,
  status TEXT NOT NULL CHECK(status IN ('queued','uploading','uploaded','failed')) DEFAULT 'queued',
  response JSONB NOT NULL DEFAULT '{}',
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_remote_backup_uploads_status ON remote_backup_uploads(status, created_at);

CREATE TABLE IF NOT EXISTS mobile_offline_mutations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_key TEXT NOT NULL,
  module_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT,
  action TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  status TEXT NOT NULL CHECK(status IN ('pending','syncing','synced','failed','conflicted')) DEFAULT 'pending',
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_mobile_offline_mutations_status ON mobile_offline_mutations(device_key, status, created_at);

INSERT INTO modules(id, name, version, description, manifest, installed, health, routes, permissions, publishes, subscribes, sync_enabled, updated_at)
VALUES
('connector-worker','Connector Worker','0.11.0','Durable outbox worker for WhatsApp, email, push, and remote backup dispatch.','{"id":"connector-worker","name":"Connector Worker","routes":{"web":"/connector-worker","api":"/api/proxy/connectors/api/connectors/worker"}}'::jsonb,true,'ok','{"web":"/connector-worker","api":"/api/proxy/connectors/api/connectors/worker"}'::jsonb,ARRAY['connectors:read','connectors:write'],ARRAY['connector.delivery.sent'],ARRAY['message.queued','automation.notification.queued'],true,now()),
('offline-queue','Offline Queue','0.11.0','Mobile and desktop offline mutation queue with retry visibility.','{"id":"offline-queue","name":"Offline Queue","routes":{"web":"/offline-queue"}}'::jsonb,true,'ok','{"web":"/offline-queue"}'::jsonb,ARRAY['sync:read','sync:write'],ARRAY['sync.mutation.queued'],ARRAY['sync.conflict.created'],true,now()),
('conflict-resolution','Conflict Resolution','0.11.0','Manual merge UI for open sync conflicts.','{"id":"conflict-resolution","name":"Conflict Resolution","routes":{"web":"/conflicts","api":"/api/proxy/sync/api/sync/conflicts"}}'::jsonb,true,'ok','{"web":"/conflicts","api":"/api/proxy/sync/api/sync/conflicts"}'::jsonb,ARRAY['sync:read','sync:write'],ARRAY['sync.conflict.resolved'],ARRAY['sync.conflict.created'],true,now())
ON CONFLICT(id) DO UPDATE SET version=EXCLUDED.version, description=EXCLUDED.description, manifest=EXCLUDED.manifest, routes=EXCLUDED.routes, permissions=EXCLUDED.permissions, health='ok', updated_at=now();
