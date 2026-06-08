-- Intelligence Center: public OSINT / news / RSS / SearXNG monitoring & briefings
-- All tables idempotent via IF NOT EXISTS

CREATE TABLE IF NOT EXISTS intelligence_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('rss','atom','searxng','news_api','public_web','user_configured')),
    url TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_intelligence_sources_name ON intelligence_sources(name);

CREATE TABLE IF NOT EXISTS intelligence_monitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    keywords TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    source_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    schedule TEXT NOT NULL DEFAULT 'daily',
    enabled BOOLEAN NOT NULL DEFAULT true,
    last_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_intelligence_monitors_name ON intelligence_monitors(name);

CREATE TABLE IF NOT EXISTS intelligence_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    monitor_id UUID NOT NULL REFERENCES intelligence_monitors(id) ON DELETE CASCADE,
    source_id UUID REFERENCES intelligence_sources(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    url TEXT,
    snippet TEXT,
    relevance DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    starred BOOLEAN NOT NULL DEFAULT false,
    dismissed BOOLEAN NOT NULL DEFAULT false,
    raw JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_intelligence_findings_monitor ON intelligence_findings(monitor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_intelligence_findings_source ON intelligence_findings(source_id);

CREATE TABLE IF NOT EXISTS intelligence_briefings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    finding_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_intelligence_briefings_created ON intelligence_briefings(created_at DESC);

CREATE TABLE IF NOT EXISTS intelligence_briefing_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    briefing_id UUID NOT NULL REFERENCES intelligence_briefings(id) ON DELETE CASCADE,
    finding_id UUID REFERENCES intelligence_findings(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    url TEXT,
    snippet TEXT,
    relevance DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_intelligence_briefing_items_briefing ON intelligence_briefing_items(briefing_id);
