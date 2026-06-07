-- Phase 13: live-stack certification, model runtime, and release readiness.

CREATE TABLE IF NOT EXISTS model_runtime_invocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind TEXT NOT NULL,
    sha256 TEXT,
    media_type TEXT,
    result JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_model_runtime_invocations_created ON model_runtime_invocations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_model_runtime_invocations_sha ON model_runtime_invocations(sha256);

CREATE TABLE IF NOT EXISTS certification_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','passed','failed','skipped')),
    target TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    finished_at TIMESTAMPTZ,
    evidence JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_certification_runs_suite_created ON certification_runs(suite, created_at DESC);

CREATE TABLE IF NOT EXISTS release_publish_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel TEXT NOT NULL DEFAULT 'dev',
    tag TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','published','failed','skipped')),
    artifacts JSONB NOT NULL DEFAULT '[]',
    evidence JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_release_publish_jobs_status ON release_publish_jobs(status, created_at DESC);

INSERT INTO modules(
  id,
  name,
  version,
  description,
  manifest,
  installed,
  health,
  routes,
  permissions,
  publishes,
  subscribes,
  sync_enabled,
  storage_tables,
  updated_at
)
VALUES(
  'model-runtime',
  'Model Runtime',
  '0.13.0',
  'Certified OCR, object detection, transcription, and multimodal runtime bridge.',
  '{
    "id": "model-runtime",
    "name": "Model Runtime",
    "version": "0.13.0",
    "description": "Certified OCR, object detection, transcription, and multimodal runtime bridge.",
    "routes": {"web": "/model-runtime", "api": "/api/model-runtime"},
    "permissions": ["model_runtime:read", "model_runtime:write"],
    "events": {"publishes": ["model-runtime.asset.processed"], "subscribes": ["analog.capture.created"]},
    "storage": {"tables": ["model_runtime_invocations"]},
    "sync": {"enabled": true, "strategy": "local-first"}
  }'::jsonb,
  true,
  'ok',
  '{"web":"/model-runtime","api":"/api/model-runtime"}'::jsonb,
  ARRAY['model_runtime:read','model_runtime:write'],
  ARRAY['model-runtime.asset.processed'],
  ARRAY['analog.capture.created'],
  true,
  ARRAY['model_runtime_invocations'],
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
