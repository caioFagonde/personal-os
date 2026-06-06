-- Phase 8: Digital twin intelligence, ontology, recommendations, and privacy policy.

ALTER TABLE modules ADD COLUMN IF NOT EXISTS storage_tables TEXT[] NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS digital_twin_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    external_id TEXT,
    natural_key TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    name TEXT,
    properties JSONB NOT NULL DEFAULT '{}',
    sensitivity TEXT NOT NULL DEFAULT 'personal' CHECK (sensitivity IN ('public','personal','sensitive','restricted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(profile_id, fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_digital_twin_entities_type ON digital_twin_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_digital_twin_entities_props ON digital_twin_entities USING gin(properties);

CREATE TABLE IF NOT EXISTS digital_twin_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    relation_type TEXT NOT NULL,
    from_entity_id UUID NOT NULL REFERENCES digital_twin_entities(id) ON DELETE CASCADE,
    to_entity_id UUID NOT NULL REFERENCES digital_twin_entities(id) ON DELETE CASCADE,
    weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    properties JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(relation_type, from_entity_id, to_entity_id)
);
CREATE INDEX IF NOT EXISTS idx_digital_twin_relationships_from ON digital_twin_relationships(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_digital_twin_relationships_to ON digital_twin_relationships(to_entity_id);

CREATE TABLE IF NOT EXISTS digital_twin_timeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    event_uid TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    domains TEXT[] NOT NULL DEFAULT '{}',
    importance DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload JSONB NOT NULL DEFAULT '{}',
    sensitivity TEXT NOT NULL DEFAULT 'personal' CHECK (sensitivity IN ('public','personal','sensitive','restricted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(profile_id, event_uid)
);
CREATE INDEX IF NOT EXISTS idx_digital_twin_timeline_occurred ON digital_twin_timeline_events(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_digital_twin_timeline_type ON digital_twin_timeline_events(event_type);
CREATE INDEX IF NOT EXISTS idx_digital_twin_timeline_domains ON digital_twin_timeline_events USING gin(domains);
CREATE INDEX IF NOT EXISTS idx_digital_twin_timeline_payload ON digital_twin_timeline_events USING gin(payload);

CREATE TABLE IF NOT EXISTS digital_twin_state_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    state_type TEXT NOT NULL DEFAULT 'daily',
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    state JSONB NOT NULL DEFAULT '{}',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.7 CHECK (confidence >= 0 AND confidence <= 1),
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_digital_twin_state_captured ON digital_twin_state_snapshots(captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_digital_twin_state_gin ON digital_twin_state_snapshots USING gin(state);

CREATE TABLE IF NOT EXISTS digital_twin_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    domain TEXT NOT NULL DEFAULT 'planning',
    priority INTEGER NOT NULL DEFAULT 50 CHECK (priority >= 0 AND priority <= 100),
    progress DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 1),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','done','archived')),
    properties JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_digital_twin_goals_status_priority ON digital_twin_goals(status, priority DESC);

CREATE TABLE IF NOT EXISTS digital_twin_recommendation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    state JSONB NOT NULL DEFAULT '{}',
    goals JSONB NOT NULL DEFAULT '[]',
    preferences JSONB NOT NULL DEFAULT '{}',
    recommendation_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS digital_twin_recommendation_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES digital_twin_recommendation_runs(id) ON DELETE CASCADE,
    recommendation_uid TEXT NOT NULL,
    title TEXT NOT NULL,
    rationale TEXT NOT NULL,
    domain TEXT NOT NULL,
    priority INTEGER NOT NULL,
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    action_type TEXT NOT NULL,
    action JSONB NOT NULL DEFAULT '{}',
    requires_approval BOOLEAN NOT NULL DEFAULT false,
    user_feedback TEXT CHECK (user_feedback IN ('accepted','dismissed','deferred','irrelevant') OR user_feedback IS NULL),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_digital_twin_recommendation_run ON digital_twin_recommendation_items(run_id);

CREATE TABLE IF NOT EXISTS digital_twin_memory_policies (
    profile_id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
    policy JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS digital_twin_memory_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    memory_class TEXT NOT NULL DEFAULT 'working' CHECK (memory_class IN ('ephemeral','working','long_term','archival')),
    content TEXT NOT NULL,
    summary TEXT,
    tags TEXT[] NOT NULL DEFAULT '{}',
    sensitivity TEXT NOT NULL DEFAULT 'personal' CHECK (sensitivity IN ('public','personal','sensitive','restricted')),
    source TEXT NOT NULL DEFAULT 'manual',
    properties JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_accessed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_digital_twin_memory_class ON digital_twin_memory_records(memory_class, sensitivity);
CREATE INDEX IF NOT EXISTS idx_digital_twin_memory_tags ON digital_twin_memory_records USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_digital_twin_memory_fts ON digital_twin_memory_records USING gin(to_tsvector('simple', coalesce(content,'') || ' ' || coalesce(summary,'')));

CREATE TABLE IF NOT EXISTS digital_twin_preference_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    signal_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    context JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS digital_twin_model_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluator TEXT NOT NULL,
    version TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL CHECK (score >= 0 AND score <= 1),
    metrics JSONB NOT NULL DEFAULT '{}',
    cases JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS digital_twin_intervention_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_item_id UUID REFERENCES digital_twin_recommendation_items(id) ON DELETE SET NULL,
    outcome_type TEXT NOT NULL,
    outcome_score DOUBLE PRECISION CHECK (outcome_score >= 0 AND outcome_score <= 1),
    notes TEXT,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO modules(id, name, version, health, routes, permissions, publishes, subscribes, storage_tables, sync_enabled, manifest, installed)
VALUES(
  'digital-twin',
  'Digital Twin Intelligence',
  '0.8.0',
  'ok',
  '{"web":"/digital-twin","api":"/api/digital-twin"}'::jsonb,
  ARRAY['digital_twin:read','digital_twin:write','recommendations:write','digital_twin:export'],
  ARRAY['digital_twin.recommendation.created','digital_twin.state.updated','digital_twin.memory.recorded'],
  ARRAY['study.session.completed','automation.run.completed','research.document.ingested','geospatial.memory.created','mindfulness.session.completed'],
  ARRAY['digital_twin_entities','digital_twin_relationships','digital_twin_timeline_events','digital_twin_state_snapshots','digital_twin_goals','digital_twin_memory_records'],
  true,
  '{"id":"digital-twin","name":"Digital Twin Intelligence","version":"0.8.0","description":"Unified personal ontology, timeline, state model, memory policy, and recommendation engine.","routes":{"web":"/digital-twin","api":"/api/digital-twin"},"permissions":["digital_twin:read","digital_twin:write","recommendations:write","digital_twin:export"],"events":{"publishes":["digital_twin.recommendation.created","digital_twin.state.updated","digital_twin.memory.recorded"],"subscribes":["study.session.completed","automation.run.completed","research.document.ingested","geospatial.memory.created","mindfulness.session.completed"]},"storage":{"tables":["digital_twin_entities","digital_twin_relationships","digital_twin_timeline_events","digital_twin_state_snapshots","digital_twin_goals","digital_twin_memory_records"]},"sync":{"enabled":true,"strategy":"local-first"}}'::jsonb,
  true
)
ON CONFLICT(id) DO UPDATE SET
  version=EXCLUDED.version,
  routes=EXCLUDED.routes,
  permissions=EXCLUDED.permissions,
  publishes=EXCLUDED.publishes,
  subscribes=EXCLUDED.subscribes,
  storage_tables=EXCLUDED.storage_tables,
  manifest=EXCLUDED.manifest,
  installed=true;
