# PERSONAL_GRAPH_SCHEMA.md — Nexus Prime Object Model & Knowledge Graph

## Design principle

Do **not** rewrite the 107 existing tables. Add a thin, uniform **registry layer** on top:
every domain row that matters to the user gets one row in `objects`, relationships live in `edges`,
searchable text lives in `object_chunks` (pgvector). Existing services keep their rich tables and
**dual-write** the registry via a small shared helper (`packages/graph` py + ts). The existing
`entities`/`entity_versions` tables (already used by module-service and sync) are the ancestor of
this layer; migration 014 renames/extends rather than duplicates.

## Core objects (canonical `kind` values)

| Kind | Backing table(s) today | New? |
|---|---|---|
| `capture_item` | capture_items | exists |
| `task` | tasks, task_events | exists |
| `project` | — | **new table `projects`** |
| `note` | notes (+ zettel_links) | exists |
| `source` | research_documents, intelligence_sources | exists (unify kind) |
| `decision` | — | **new table `decisions`** |
| `event` | calendar_events, digital_twin_timeline_events | exists |
| `artifact` | build_artifacts, coding_agent_artifacts | exists (unify) |
| `agent_run` | coding_agent_runs, automation_runs | exists (unify view) |
| `automation` | automation_workflows | exists |
| `connector_account` | connector_accounts | exists |
| `backup_snapshot` | backup_manifests | exists |
| `sync_conflict` | sync_conflicts | exists |
| `daily_state` | — | **new table `daily_states`** |
| `goal` | digital_twin_goals | exists |
| `person` | contacts, contact_channels | exists |
| `repository` | — | **new table `repositories`** |
| `portfolio_case` | — | **new table `portfolio_cases`** |
| `habit` | routine_jobs (partial) | extend |
| `reminder` | notifications (partial) | extend |

## Migration 014 — registry layer (SQL sketch)

```sql
-- 014_nexus_graph.sql
CREATE TABLE IF NOT EXISTS objects (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind         text NOT NULL,                 -- canonical kinds above
  domain_table text NOT NULL,                 -- e.g. 'tasks'
  domain_id    uuid NOT NULL,                 -- FK into domain table (soft)
  title        text NOT NULL DEFAULT '',
  slug         text,                          -- stable, for Obsidian paths
  status       text,                          -- kind-specific lifecycle
  project_id   uuid REFERENCES objects(id),   -- fast path for the most common edge
  tags         text[] NOT NULL DEFAULT '{}',
  meta         jsonb NOT NULL DEFAULT '{}',
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  deleted_at   timestamptz,
  UNIQUE (domain_table, domain_id)
);
CREATE INDEX ON objects (kind, updated_at DESC);
CREATE INDEX ON objects USING gin (tags);
CREATE INDEX ON objects (project_id);

CREATE TABLE IF NOT EXISTS edges (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  src_id     uuid NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  dst_id     uuid NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  rel        text NOT NULL,   -- see relation vocabulary
  weight     real NOT NULL DEFAULT 1.0,
  meta       jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (src_id, dst_id, rel)
);
CREATE INDEX ON edges (src_id, rel);
CREATE INDEX ON edges (dst_id, rel);

CREATE TABLE IF NOT EXISTS object_chunks (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  object_id  uuid NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  seq        int  NOT NULL DEFAULT 0,
  text       text NOT NULL,
  embedding  vector(768),                    -- pgvector; dim set by embed model config
  model      text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (object_id, seq)
);
CREATE INDEX ON object_chunks USING hnsw (embedding vector_cosine_ops);
```

## Relation vocabulary (`edges.rel`)

`belongs_to_project`, `derived_from` (task←capture, note←source), `references`, `blocks`,
`decided_by` (artifact←decision), `about_person`, `logged_on` (x←daily_state),
`produced_by` (artifact←agent_run), `backs_up` (backup_snapshot→object set),
`synced_with` (note↔vault file), `supports_goal`, `evidence_for`, `case_of` (portfolio_case→repository/project),
`mentions`, `duplicate_of`, `follows` (habit streak chain).

## New domain tables

```sql
CREATE TABLE IF NOT EXISTS projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL, slug text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'active',      -- active|paused|done|archived
  pitch text NOT NULL DEFAULT '',
  north_star text NOT NULL DEFAULT '',
  vault_path text,                             -- Obsidian mapping override
  meta jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS decisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL, slug text NOT NULL,
  context text NOT NULL DEFAULT '', decision text NOT NULL,
  consequences text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'accepted',     -- proposed|accepted|superseded
  decided_at timestamptz NOT NULL DEFAULT now(),
  project_id uuid, meta jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS daily_states (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  day date NOT NULL UNIQUE,
  intention text NOT NULL DEFAULT '',
  highlights jsonb NOT NULL DEFAULT '[]',
  energy int, mood int,                        -- 1..5, nullable, user-entered only
  review text NOT NULL DEFAULT '',
  closed boolean NOT NULL DEFAULT false,
  meta jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS repositories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL, path text NOT NULL UNIQUE,
  remote_url text, default_branch text DEFAULT 'main',
  allowed_for_agent boolean NOT NULL DEFAULT false,
  meta jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS portfolio_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL, slug text NOT NULL UNIQUE,
  summary text NOT NULL DEFAULT '',
  problem text NOT NULL DEFAULT '', approach text NOT NULL DEFAULT '',
  outcome text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'draft',
  meta jsonb NOT NULL DEFAULT '{}'
);
```

## Agentic-harness objects (see AGENTIC_HARNESS_SPEC.md for behavior)

```sql
CREATE TABLE IF NOT EXISTS agent_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind text NOT NULL,                 -- coding|research|writing|ops|custom-skill
  title text NOT NULL, prompt text NOT NULL,
  status text NOT NULL DEFAULT 'queued', -- queued|planning|awaiting_approval|running|succeeded|failed|cancelled
  policy jsonb NOT NULL DEFAULT '{}',
  project_id uuid, created_by text NOT NULL DEFAULT 'owner',
  created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS agent_plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid NOT NULL REFERENCES agent_jobs(id) ON DELETE CASCADE,
  steps jsonb NOT NULL,               -- [{n, tool, args_summary, risk}]
  approved boolean, approved_at timestamptz, approver text
);
CREATE TABLE IF NOT EXISTS tool_calls (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid NOT NULL REFERENCES agent_jobs(id) ON DELETE CASCADE,
  tool text NOT NULL, args jsonb NOT NULL,
  status text NOT NULL,               -- proposed|approved|denied|executed|failed
  result_summary text, started_at timestamptz, finished_at timestamptz
);
CREATE TABLE IF NOT EXISTS approval_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid REFERENCES agent_jobs(id) ON DELETE CASCADE,
  tool_call_id uuid REFERENCES tool_calls(id),
  reason text NOT NULL, risk text NOT NULL DEFAULT 'medium',
  status text NOT NULL DEFAULT 'pending',  -- pending|approved|denied|expired
  decided_at timestamptz, decider text
);
CREATE TABLE IF NOT EXISTS agent_memory (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scope text NOT NULL,                -- global|project:<id>|skill:<name>
  kind text NOT NULL,                 -- fact|preference|procedure|outcome
  text text NOT NULL, embedding vector(768),
  source_job uuid, confidence real DEFAULT 0.7,
  created_at timestamptz DEFAULT now(), expires_at timestamptz
);
CREATE TABLE IF NOT EXISTS skills (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE, description text NOT NULL,
  instructions text NOT NULL, tools text[] NOT NULL DEFAULT '{}',
  enabled boolean NOT NULL DEFAULT true, version int NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS eval_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_id uuid REFERENCES skills(id),
  input jsonb NOT NULL, expectation jsonb NOT NULL,
  last_status text, last_run_at timestamptz
);
CREATE TABLE IF NOT EXISTS artifact_outputs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid NOT NULL REFERENCES agent_jobs(id) ON DELETE CASCADE,
  kind text NOT NULL,                 -- diff|file|note|report|handoff
  path text, content_ref text,        -- MinIO key or repo path
  sha256 text, meta jsonb NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS handoff_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid REFERENCES agent_jobs(id),
  repository_id uuid REFERENCES repositories(id),
  path text NOT NULL, sha256 text, created_at timestamptz DEFAULT now()
);
-- AuditEvent: reuse existing audit_log; add index (actor, created_at).
```

## Dual-write helper contract

`packages/graph` exposes (Python + TS):

```
register_object(kind, domain_table, domain_id, title, *, slug=None, project_id=None, tags=(), meta=None) -> object_id
link(src_object_id, dst_object_id, rel, weight=1.0, meta=None)
upsert_chunks(object_id, [texts]) -> queues embedding job (NATS subject nexus.embed)
```

Rules:
- Registry writes are **best-effort but logged** — a domain write must never fail because the registry insert failed; failures go to `service_events` for repair.
- Backfill script `scripts/graph/backfill.py` registers all existing rows (idempotent via the UNIQUE constraint).
- Graph read API lives in api-gateway: `GET /api/graph/objects`, `GET /api/graph/objects/{id}/neighbors?rel=...`, `POST /api/graph/search {text, kinds[], k}` (vector + trigram hybrid).

## Obsidian slug discipline

`objects.slug` is the single source for vault paths (see OBSIDIAN_INTEGRATION_SPEC.md). Slugs are immutable once a vault file exists; renames create a `duplicate_of`-style alias edge and a frontmatter `aliases:` entry rather than moving files silently.
