CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS connector_device_flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL CHECK (provider IN ('google','microsoft')),
    device_code TEXT NOT NULL,
    user_code TEXT,
    verification_uri TEXT,
    verification_uri_complete TEXT,
    scopes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    status TEXT NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMPTZ NOT NULL,
    interval_seconds INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    consumed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_connector_device_flows_status ON connector_device_flows(provider, status, expires_at);

CREATE TABLE IF NOT EXISTS coding_agent_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'feature',
    repo_path TEXT NOT NULL,
    branch_name TEXT NOT NULL,
    requester_device_key TEXT,
    status TEXT NOT NULL DEFAULT 'pending_approval',
    requires_approval BOOLEAN NOT NULL DEFAULT true,
    approved_at TIMESTAMPTZ,
    approved_by TEXT,
    last_run_at TIMESTAMPTZ,
    policy JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_coding_agent_jobs_status ON coding_agent_jobs(status, created_at DESC);

CREATE TABLE IF NOT EXISTS coding_agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES coding_agent_jobs(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    command TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    worktree_path TEXT,
    stdout TEXT,
    stderr TEXT,
    exit_code INTEGER,
    artifacts JSONB NOT NULL DEFAULT '[]',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_coding_agent_runs_job ON coding_agent_runs(job_id, started_at DESC);

CREATE TABLE IF NOT EXISTS coding_agent_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES coding_agent_jobs(id) ON DELETE CASCADE,
    run_id UUID REFERENCES coding_agent_runs(id) ON DELETE SET NULL,
    artifact_type TEXT NOT NULL,
    uri TEXT,
    content JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO modules(
  id, name, version, description, manifest, installed, health, routes, permissions, publishes, subscribes, sync_enabled, storage_tables, updated_at
)
VALUES(
  'coding-agent',
  'Coding Agent',
  '0.14.0',
  'Approval-gated Claude Code worktree runner for remote coding jobs.',
  '{"id":"coding-agent","name":"Coding Agent","version":"0.14.0","routes":{"web":"/coding-agent","api":"/api/coding-agent"},"permissions":["coding_agent:read","coding_agent:write","command:request"],"events":{"publishes":["coding-agent.job.created","coding-agent.run.completed"],"subscribes":["command.approved"]},"storage":{"tables":["coding_agent_jobs","coding_agent_runs","coding_agent_artifacts"]},"sync":{"enabled":true,"strategy":"local-first"}}'::jsonb,
  true,
  'ok',
  '{"web":"/coding-agent","api":"/api/coding-agent"}'::jsonb,
  ARRAY['coding_agent:read','coding_agent:write','command:request'],
  ARRAY['coding-agent.job.created','coding-agent.run.completed'],
  ARRAY['command.approved'],
  true,
  ARRAY['coding_agent_jobs','coding_agent_runs','coding_agent_artifacts'],
  now()
)
ON CONFLICT(id) DO UPDATE SET
  version=EXCLUDED.version,
  description=EXCLUDED.description,
  manifest=EXCLUDED.manifest,
  routes=EXCLUDED.routes,
  permissions=EXCLUDED.permissions,
  publishes=EXCLUDED.publishes,
  subscribes=EXCLUDED.subscribes,
  sync_enabled=EXCLUDED.sync_enabled,
  storage_tables=EXCLUDED.storage_tables,
  installed=true,
  health='ok',
  updated_at=now();
