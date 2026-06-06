-- Phase 6: automation and agentic workflow substrate.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS automation_workflows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  spec JSONB NOT NULL,
  active BOOLEAN NOT NULL DEFAULT false,
  requires_approval BOOLEAN NOT NULL DEFAULT false,
  policy JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by_device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_automation_workflows_active ON automation_workflows(active);
CREATE INDEX IF NOT EXISTS idx_automation_workflows_spec_gin ON automation_workflows USING gin(spec);

CREATE TABLE IF NOT EXISTS automation_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual',
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  idempotency_key TEXT NOT NULL UNIQUE,
  seen_count INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_automation_events_topic ON automation_events(topic, last_seen_at DESC);

CREATE TABLE IF NOT EXISTS automation_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id UUID NOT NULL REFERENCES automation_workflows(id) ON DELETE CASCADE,
  trigger_event_id UUID REFERENCES automation_events(id) ON DELETE SET NULL,
  status TEXT NOT NULL CHECK (status IN ('queued','running','pending_approval','succeeded','failed','cancelled')),
  input JSONB NOT NULL DEFAULT '{}'::jsonb,
  output JSONB NOT NULL DEFAULT '{}'::jsonb,
  idempotency_key TEXT NOT NULL UNIQUE,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_automation_runs_workflow ON automation_runs(workflow_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_status ON automation_runs(status, created_at DESC);

CREATE TABLE IF NOT EXISTS automation_run_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES automation_runs(id) ON DELETE CASCADE,
  node_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','running','pending_approval','succeeded','failed','skipped')),
  output JSONB NOT NULL DEFAULT '{}'::jsonb,
  error TEXT,
  requires_approval BOOLEAN NOT NULL DEFAULT false,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(run_id, node_id)
);
CREATE INDEX IF NOT EXISTS idx_automation_run_steps_run ON automation_run_steps(run_id, created_at ASC);

CREATE TABLE IF NOT EXISTS automation_approvals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES automation_runs(id) ON DELETE CASCADE,
  node_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','approved','denied','expired')) DEFAULT 'pending',
  reason TEXT,
  decided_by_device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  decided_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(run_id, node_id)
);
CREATE INDEX IF NOT EXISTS idx_automation_approvals_pending ON automation_approvals(status, created_at ASC);

CREATE TABLE IF NOT EXISTS automation_schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id UUID NOT NULL REFERENCES automation_workflows(id) ON DELETE CASCADE,
  every_seconds INT NOT NULL CHECK (every_seconds BETWEEN 10 AND 31536000),
  enabled BOOLEAN NOT NULL DEFAULT true,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  last_run_at TIMESTAMPTZ,
  next_due_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_automation_schedules_due ON automation_schedules(enabled, next_due_at ASC);

CREATE TABLE IF NOT EXISTS automation_outbox (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES automation_runs(id) ON DELETE CASCADE,
  node_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL CHECK (status IN ('queued','dispatched','failed','cancelled')) DEFAULT 'queued',
  attempts INT NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  dispatched_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_automation_outbox_status ON automation_outbox(status, created_at ASC);

CREATE TABLE IF NOT EXISTS n8n_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  webhook_secret_ref TEXT,
  enabled BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notification_routes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  route_key TEXT NOT NULL UNIQUE,
  provider TEXT NOT NULL CHECK (provider IN ('ntfy','email','local','webhook')),
  target TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT true,
  policy JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notification_deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  route_id UUID REFERENCES notification_routes(id) ON DELETE SET NULL,
  run_id UUID REFERENCES automation_runs(id) ON DELETE SET NULL,
  topic TEXT NOT NULL,
  title TEXT,
  message TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued','sent','failed','cancelled')) DEFAULT 'queued',
  provider_response JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at TIMESTAMPTZ
);

INSERT INTO modules(id, name, version, description, manifest, installed, health, routes, permissions, publishes, subscribes, sync_enabled, updated_at)
VALUES(
  'automation',
  'Automation Engine',
  '0.6.0',
  'DAG workflows, event triggers, schedules, n8n bridge, approvals, and notification routing.',
  '{"id":"automation","name":"Automation Engine","version":"0.6.0"}'::jsonb,
  true,
  'ok',
  '{"web":"/automation","api":"/api/automation"}'::jsonb,
  ARRAY['automation:read','automation:write','command:request','notifications:send'],
  ARRAY['automation.workflow.started','automation.workflow.completed','automation.approval.requested'],
  ARRAY['study.session.completed','file.ingested','sync.entity.changed','research.document.ingested'],
  true,
  now()
)
ON CONFLICT(id) DO NOTHING;
