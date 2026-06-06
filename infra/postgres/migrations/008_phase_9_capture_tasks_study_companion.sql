-- Phase 9: Capture, tasks, delegation, study companion, analog-to-digital.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS contacts (
  key TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  role TEXT DEFAULT 'contact',
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS contact_channels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_key TEXT NOT NULL REFERENCES contacts(key) ON DELETE CASCADE,
  channel TEXT NOT NULL CHECK (channel IN ('email','whatsapp','ntfy','calendar','phone')),
  address TEXT NOT NULL,
  verified BOOLEAN NOT NULL DEFAULT false,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(contact_key, channel, address)
);

CREATE TABLE IF NOT EXISTS capture_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  source_kind TEXT NOT NULL DEFAULT 'quick_capture',
  source_id TEXT,
  raw_text TEXT NOT NULL,
  parsed JSONB NOT NULL DEFAULT '{}',
  fingerprint TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_capture_items_created ON capture_items(created_at DESC);

CREATE TABLE IF NOT EXISTS tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'inbox' CHECK (status IN ('inbox','active','waiting','delegated','scheduled','completed','cancelled')),
  assignee_key TEXT REFERENCES contacts(key) ON DELETE SET NULL,
  due_at TIMESTAMPTZ,
  follow_up_at TIMESTAMPTZ,
  priority INT NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
  tags TEXT[] NOT NULL DEFAULT '{}',
  source_kind TEXT NOT NULL DEFAULT 'manual',
  source_id TEXT,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(source_kind, source_id)
);
CREATE INDEX IF NOT EXISTS idx_tasks_status_due ON tasks(status, due_at);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_key, status);

CREATE TABLE IF NOT EXISTS task_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id, created_at DESC);

CREATE TABLE IF NOT EXISTS delegation_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  target_key TEXT NOT NULL REFERENCES contacts(key) ON DELETE CASCADE,
  trigger_kind TEXT NOT NULL DEFAULT 'note_frontmatter',
  channels TEXT[] NOT NULL DEFAULT '{whatsapp,email}',
  requires_approval BOOLEAN NOT NULL DEFAULT true,
  allowed_start TIME NOT NULL DEFAULT '07:00',
  allowed_end TIME NOT NULL DEFAULT '21:00',
  metadata JSONB NOT NULL DEFAULT '{}',
  enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS message_outbox (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
  channel TEXT NOT NULL CHECK(channel IN ('email','whatsapp','ntfy')),
  connector TEXT NOT NULL,
  recipient TEXT NOT NULL,
  subject TEXT,
  body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('pending_approval','queued','sending','sent','failed','cancelled')),
  requires_approval BOOLEAN NOT NULL DEFAULT false,
  attempts INT NOT NULL DEFAULT 0,
  next_attempt_at TIMESTAMPTZ DEFAULT now(),
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_message_outbox_status ON message_outbox(status, next_attempt_at);

CREATE TABLE IF NOT EXISTS message_deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  outbox_id UUID NOT NULL REFERENCES message_outbox(id) ON DELETE CASCADE,
  provider_message_id TEXT,
  status TEXT NOT NULL,
  response JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analog_captures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
  filename TEXT NOT NULL,
  media_type TEXT NOT NULL,
  sha256 TEXT NOT NULL UNIQUE,
  summary TEXT NOT NULL,
  suggested_tags TEXT[] NOT NULL DEFAULT '{}',
  lookup_queries TEXT[] NOT NULL DEFAULT '{}',
  geom GEOGRAPHY(Point, 4326),
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_analog_captures_geom ON analog_captures USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_analog_captures_created ON analog_captures(created_at DESC);

CREATE TABLE IF NOT EXISTS vision_detections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  capture_id UUID NOT NULL REFERENCES analog_captures(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  bbox JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_vision_detections_capture ON vision_detections(capture_id);

CREATE TABLE IF NOT EXISTS ocr_blocks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  capture_id UUID NOT NULL REFERENCES analog_captures(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  bbox JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ocr_blocks_capture ON ocr_blocks(capture_id);

CREATE TABLE IF NOT EXISTS learning_atoms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  concept TEXT NOT NULL,
  source_excerpt TEXT NOT NULL DEFAULT '',
  note_id UUID REFERENCES notes(id) ON DELETE SET NULL,
  tags TEXT[] NOT NULL DEFAULT '{}',
  interval_days INT NOT NULL DEFAULT 1,
  ease_factor DOUBLE PRECISION NOT NULL DEFAULT 2.5,
  repetitions INT NOT NULL DEFAULT 0,
  stability DOUBLE PRECISION NOT NULL DEFAULT 1.0,
  difficulty DOUBLE PRECISION NOT NULL DEFAULT 5.0,
  due_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_learning_atoms_concept_note ON learning_atoms(concept, COALESCE(note_id, '00000000-0000-0000-0000-000000000000'::uuid));
CREATE INDEX IF NOT EXISTS idx_learning_atoms_due ON learning_atoms(due_at);

CREATE TABLE IF NOT EXISTS review_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  atom_id UUID NOT NULL REFERENCES learning_atoms(id) ON DELETE CASCADE,
  quality INT NOT NULL CHECK(quality BETWEEN 0 AND 5),
  confidence DOUBLE PRECISION NOT NULL CHECK(confidence BETWEEN 0 AND 1),
  time_seconds INT,
  mode TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_review_events_atom ON review_events(atom_id, created_at DESC);

CREATE TABLE IF NOT EXISTS lookup_cards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query TEXT NOT NULL,
  source_capture_id UUID REFERENCES analog_captures(id) ON DELETE SET NULL,
  summary TEXT NOT NULL,
  spatial JSONB NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'queued',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS routine_jobs (
  id TEXT PRIMARY KEY,
  service TEXT NOT NULL,
  cron TEXT NOT NULL,
  purpose TEXT NOT NULL,
  priority TEXT NOT NULL DEFAULT 'normal',
  enabled BOOLEAN NOT NULL DEFAULT true,
  last_run_at TIMESTAMPTZ,
  next_run_hint TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO contacts(key, display_name, role)
VALUES ('secretary', 'Secretary', 'assistant')
ON CONFLICT(key) DO NOTHING;

INSERT INTO delegation_rules(target_key, trigger_kind, channels, requires_approval)
VALUES ('secretary', 'note_frontmatter', ARRAY['whatsapp','email'], false)
ON CONFLICT DO NOTHING;

INSERT INTO routine_jobs(id, service, cron, purpose, priority) VALUES
('study.due_reviews','study-companion','*/20 * * * *','queue due flashcard and reading reviews','high'),
('study.retention_rebalance','study-companion','0 5 * * *','rebalance intervals using recall outcomes and fatigue signals','normal'),
('analog.ocr_backlog','study-companion','*/10 * * * *','process unparsed camera/audio/file captures','high'),
('analog.deep_lookup','study-companion','*/15 * * * *','expand object/passage lookup cards into related research candidates','normal'),
('tasks.followups','capture-service','*/30 * * * *','remind about delegated tasks without acknowledgement','high'),
('sync.health','sync-engine','*/5 * * * *','verify device sync lag and conflict count','high'),
('backup.encrypted','ops','0 3 * * *','run encrypted database/object-store backup','high')
ON CONFLICT(id) DO UPDATE SET service=EXCLUDED.service, cron=EXCLUDED.cron, purpose=EXCLUDED.purpose, priority=EXCLUDED.priority, updated_at=now();
