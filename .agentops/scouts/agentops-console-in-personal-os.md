# Scout Report: AgentOps Console in Personal OS

**Date**: 2026-06-08  
**Scout**: Haiku (read-only analysis)  
**Task ID**: agentops-console-in-personal-os  
**Status**: Scouting complete

---

## 1. Diagnosis: Current State

### AgentOps Infrastructure
The project has **two parallel AgentOps systems**:

1. **Local swarm in `.agents/` and `.agent-worktrees/`** (CLAUDE.md & AGENTS.md)
   - Manages local Git worktrees for Claude Code / Codex workers
   - Stores task definitions in `.agents/active.json`
   - Collects reports in `.agents/reports/<task-id>/report.md`
   - Provides CLI control via `scripts/agents/agentctl.py`
   - No UI exposure yet

2. **AgentOps SaaS integration in `.agentops/`** (Tranche 04)
   - Active project config in `.agentops/active.json` (tasks, profiles, budgets)
   - Event log in `.agentops/events.jsonl` (scout/executor/integration events)
   - Task prompts in `.agentops/tasks/<id>.prompt.md`
   - Reports staged in `.agentops/reports/<id>/report.md`
   - Examples and references in `.agentops/examples/`

### Current UI Gaps
- **No AgentOps control page** in the web UI
- Coding Agent page (`CodingAgentPage.vue`) exists for remote job queue approval, but does not expose local swarm state
- No route for `/agentops` or similar
- No backend endpoint for reading agent status/reports
- No components for worktree/branch/report visualization

### Web App Architecture (Ready)
- **Router**: `apps/web/src/router/routes.ts` (26 routes registered)
- **Pages**: `apps/web/src/pages/` (29 existing pages follow consistent patterns)
- **Components**: Reusable Nexus UI set (`NexusPageHero`, `NexusEmptyState`, `NexusErrorBanner`, `NexusLoadingState`)
- **API layer**: `apps/web/src/services/api.ts` (with auth, device key, refresh token handling)
- **Theme**: Dark theme stable (nexus-dark.scss covers all Quasar components)

### API Gateway Architecture (Partial Readiness)
- **Proxy pattern**: `/api/proxy/<service>/{path:path}` for all backend services
- **Auth**: Bearer token + device key scopes (see `DEFAULT_DEVICE_SCOPES` in `services/api-gateway/app/main.py`)
- **No agent scope yet**: Would need `agentops:read` scope added
- **No agent endpoint**: Could proxy to a new service or handle local file reads

---

## 2. Files to Read / Modify

### Critical files for implementation

#### Web UI (must create)
| Path | Action | Purpose |
|------|--------|---------|
| `apps/web/src/pages/AgentOpsConsolePage.vue` | **Create** | Main control page for task list, worktree status, reports, events |
| `apps/web/src/components/AgentOpsTaskCard.vue` | **Create** | Reusable card for task status + links to reports |
| `apps/web/src/components/AgentOpsWorktreeStatus.vue` | **Create** | Shows branch/worktree isolation + diffs |
| `apps/web/src/components/AgentOpsModelAvailability.vue` | **Create** | Status badges for Claude, Codex, Antigravity tools |
| `apps/web/src/components/AgentOpsEventLog.vue` | **Create** | Timeline summary of scout/executor/integrator events |
| `apps/web/src/services/agentops.ts` | **Create** | Fetches local JSON files through safe backend endpoint |
| `apps/web/src/router/routes.ts` | **Edit** | Add `/agentops` route pointing to `AgentOpsConsolePage` |

#### Backend (may need)
| Path | Action | Purpose |
|------|--------|---------|
| `services/api-gateway/app/main.py` | **Edit** | Add `agentops:read` scope; optionally add `/api/proxy/agentops/...` endpoint or `GET /api/agentops/status` for local file reads |
| `services/api-gateway/tests/test_security.py` | **Edit** | Add test for agentops scope + endpoint authorization |

#### Tests (must create)
| Path | Action | Purpose |
|------|--------|---------|
| `tests/test_agentops_console.py` | **Create** | Verify route exists, JSON file read safety, no secrets exposed |

#### Docs (optional but recommended)
| Path | Action | Purpose |
|------|--------|---------|
| `docs/agentops-console-ui.md` | **Create** | User guide for the AgentOps console (status states, limitations) |

### Do NOT read/edit
- `.env`, `.env.*`, `secrets/`, `.private/`, `data/`, `backups/`, `logs/`
- `.git/` (except for status/branch detection)
- `node_modules/`

---

## 3. Architecture & Integration Points

### Data Flow

```
Local filesystem
  ├─ .agents/active.json  (task defs, constraints, workers)
  ├─ .agents/reports/<task>/report.md  (detailed reports)
  ├─ .agent-worktrees/<task>/  (git worktrees + commits)
  └─ .agents/state/<task>.json  (optional: worktree branch/status cache)

.agentops/ (SaaS integration)
  ├─ active.json  (project config, task specs, budgets)
  ├─ events.jsonl  (event log: scout.start, executor.start, integrator.merge)
  ├─ reports/<task>/report.md  (staged reports from agents)
  └─ <task>/*/  (other artifacts)

Web UI (Frontend)
  └─ AgentOpsConsolePage
     ├─ Fetches /api/agentops/status (backend safe read)
     ├─ Displays task list (from .agents/active.json or .agentops/active.json)
     ├─ Shows worktree/branch status
     ├─ Shows report summaries
     ├─ Shows event log
     └─ Links to detailed task reports (read-only)
```

### Backend Endpoint Design (Recommended)

Add to `services/api-gateway/app/main.py`:

```python
@app.get("/api/agentops/status")
async def get_agentops_status(
    principal: Principal = Depends(active_principal)
) -> dict:
    require_scope(principal, "agentops:read")
    # Return structured status object:
    return {
        "local_swarm": {
            "tasks_from_agents_active": [...],  # from .agents/active.json
            "reports": {...},  # from .agents/reports/
            "worktrees": [...]  # from .agent-worktrees/ (branch/status)
        },
        "saas_integration": {
            "tasks": [...],  # from .agentops/active.json
            "events": [...],  # from .agentops/events.jsonl (last N)
            "budgets": {...}
        }
    }
```

**Safety**: Read files using `Path.read_text()` with explicit allow-lists; never execute shell commands from the UI; no user filesystem browsing.

### Naming Conventions

- Page: `AgentOpsConsolePage.vue`
- Components: `AgentOps*` prefix
- Service: `agentops.ts` in `services/`
- Scope: `agentops:read` (read-only by default)
- Route: `/agentops`

---

## 4. Risks & Conflicts

### High-Risk Areas

1. **File access from UI**
   - Risk: Exposing local filesystem or secrets through JSON responses
   - Mitigation: Backend endpoint reads files only from known safe paths (`.agents/`, `.agentops/`) with explicit JSON parsing; no glob patterns; no raw path input from client

2. **Scope creep to deployment/merge/push**
   - Risk: UI accidentally invokes agentctl commands that modify git state
   - Mitigation: AgentOps console is **read-only by default**. No approval UI. No "merge this branch" buttons. Dry-run jobs only unless user opens terminal.

3. **Secrets exposure in task definitions**
   - Risk: `.agents/active.json` might list allowed paths; if misconfigured, console could display secret paths or contents
   - Mitigation: Backend filter + test (`test_agentops_console.py`) verify that task path allow-lists are validated before returning; check `.env*`, `token`, `credential` patterns

4. **Missing or changed local files**
   - Risk: `.agents/active.json` deleted or `.agentops/` not initialized; UI breaks or hangs
   - Mitigation: Graceful fallback states ("local AgentOps files not available", "SaaS integration not active"); never return 500 for missing optional files

5. **Performance of large event logs**
   - Risk: `.agentops/events.jsonl` grows unbounded; UI loads all events and UI freezes
   - Mitigation: Read only last N events (e.g., 100); paginate or summarize older events

6. **Conflict with Coding Agent page**
   - Risk: Both pages compete for "agent task" UX; user confusion
   - Mitigation: **Distinguish clearly**: AgentOps = local swarm (worktrees, reports, events). Coding Agent = remote approval queue (command-bus jobs). Link between pages.

### Medium-Risk Areas

1. **Worktree state consistency**: If worktree is deleted externally, UI shows stale status
   - Mitigation: Backend detects missing worktrees and returns `{ status: "missing" }`

2. **Report file encoding**: Report markdown may contain non-UTF-8 or malformed JSON
   - Mitigation: Use safe JSON parsing (error handling); render markdown as-is (browser escapes)

3. **No admin controls**: Can't kill hung agents from UI
   - Mitigation: Document that terminal control (`agentctl.py status`, `agentctl.py cancel`) is required for advanced ops. Not a blocker for MVP.

---

## 5. Testing Strategy

### Route existence
```python
def test_agentops_console_route_exists():
    routes = (WEB / "router" / "routes.ts").read_text()
    assert "/agentops" in routes
    assert "AgentOpsConsolePage" in routes
```

### Component render states
```python
def test_agentops_page_components_exist():
    page = (WEB / "pages" / "AgentOpsConsolePage.vue").read_text()
    assert "AgentOpsTaskCard" in page
    assert "AgentOpsWorktreeStatus" in page
    assert "AgentOpsModelAvailability" in page
    assert "AgentOpsEventLog" in page
```

### Security: No secrets in path allow-lists
```python
def test_agentops_active_json_allowed_paths_are_safe():
    active = json.loads((ROOT / ".agents" / "active.json").read_text())
    for task in active.get("tasks", []):
        for path in task.get("allowed_paths", []):
            assert not _is_secret_path(path), f"Task {task['id']} allows forbidden path {path}"
```

### Backend endpoint authorization
```python
async def test_agentops_status_requires_scope():
    # Unauthenticated request → 401
    # Authenticated request without agentops:read scope → 403
    # Authenticated request with agentops:read scope → 200 + valid JSON
```

### Graceful degradation
```python
def test_agentops_missing_local_files_handled():
    # If .agents/active.json missing, UI shows "local swarm unavailable"
    # If .agentops/active.json missing, UI shows "SaaS integration not active"
    # Page still loads; no error state
```

### Secrets validation
```python
def test_check_secrets_sh_passes():
    # Existing: ./scripts/check-secrets.sh
    # Ensure no new code adds token/credentials to repo
```

---

## 6. Likely Implementation Points

### Frontend Page Structure
```vue
<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Orchestration" title="AgentOps Console" subtitle="...">
      <template #actions>
        <q-btn @click="refresh" icon="mdi-refresh" label="Refresh" :loading="loading" />
      </template>
    </NexusPageHero>

    <!-- Error banner -->
    <q-banner v-if="error" class="bg-negative" ...>...</q-banner>

    <!-- Model availability cards -->
    <div class="row q-col-gutter-md">
      <AgentOpsModelAvailability :status="status" class="col-12 col-md-6" />
    </div>

    <!-- Local swarm vs SaaS tabs -->
    <q-tabs v-model="tab">
      <q-tab name="local" label="Local Swarm" />
      <q-tab name="saas" label="SaaS Integration" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated>
      <q-tab-panel name="local">
        <!-- Task list from .agents/active.json -->
        <div v-for="task in localTasks" :key="task.id">
          <AgentOpsTaskCard :task="task" :report="reports[task.id]" />
          <AgentOpsWorktreeStatus :task="task" />
        </div>
      </q-tab-panel>

      <q-tab-panel name="saas">
        <!-- Task list from .agentops/active.json + event log -->
        <AgentOpsEventLog :events="events" />
      </q-tab-panel>
    </q-tab-panels>
  </q-page>
</template>

<script setup lang="ts">
const { status, localTasks, saasTasks, reports, events, loading, error } = await fetchAgentOpsStatus()
</script>
```

### Backend Endpoint (Pseudocode)
```python
@app.get("/api/agentops/status")
async def get_agentops_status(...):
    result = {
        "local_swarm": {
            "active_json": read_json(".agents/active.json"),
            "reports": list_reports(".agents/reports/"),
            "worktrees": list_worktrees(".agent-worktrees/"),
            "tools": {
                "git_available": shutil.which("git") is not None,
                "python_available": shutil.which("python3") is not None,
                "claude_available": shutil.which("claude") is not None,
                "codex_available": shutil.which("codex") is not None,
            }
        },
        "saas_integration": {
            "active_json": read_json(".agentops/active.json"),
            "events": read_jsonl(".agentops/events.jsonl", limit=100),
            "budgets": read_json(".agentops/budgets/*.json"),
        }
    }
    return result
```

---

## 7. Acceptance Criteria (From Task Spec)

| Criterion | Implementation Notes |
|-----------|---------------------|
| **AgentOps control page exists** | `/agentops` route + `AgentOpsConsolePage.vue` |
| **Task list visible** | Cards from `.agents/active.json` + `.agentops/active.json` |
| **Branch/worktree status shown** | `AgentOpsWorktreeStatus` component; git branch + diff indicator |
| **Reports summary readable and linked** | Report cards with snippet preview; links to full markdown (read-only) |
| **Event log summary visible** | Timeline of last N events from `.agentops/events.jsonl` |
| **Budget/time summary if available** | Show `.agentops/budgets/` if present |
| **Claude/Codex/Antigravity availability visible** | Status badges from `which claude`, `which codex`, etc. |
| **No worker launch without scope display** | Task card shows allowed_paths + locked_paths before any action; no "run" button in read-only MVP |
| **No automatic merge/push from UI** | Read-only page; no git commands from client; link to terminal instructions |
| **Destructive actions require approval** | N/A for read-only MVP; future scope |
| **Tests cover route/page existence** | `test_agentops_console.py` verifies routes, components, JSON safety |

---

## 8. Executor Instructions

### Phase 1: Scaffolding (15 min)

1. **Create page component**
   ```bash
   touch apps/web/src/pages/AgentOpsConsolePage.vue
   ```
   - Copy structure from `CodingAgentPage.vue` or `AutomationPage.vue`
   - Use `NexusPageHero`, `q-page`, `q-gutter-lg`

2. **Register route**
   - Add to `apps/web/src/router/routes.ts`:
     ```typescript
     import AgentOpsConsolePage from '../pages/AgentOpsConsolePage.vue'
     { path: '/agentops', component: AgentOpsConsolePage }
     ```

3. **Create stub service**
   - `apps/web/src/services/agentops.ts` with typed interfaces for tasks, reports, events

### Phase 2: Components (20 min)

Create reusable components in `apps/web/src/components/`:

- `AgentOpsTaskCard.vue` — display task, priority, executor, branch, report link
- `AgentOpsWorktreeStatus.vue` — show branch, commits ahead, diff stat, isolation badge
- `AgentOpsModelAvailability.vue` — status badges for `which claude`, `which codex`, etc.
- `AgentOpsEventLog.vue` — timeline of last N events (scout.start, executor.complete, etc.)

Each component should handle loading + empty + error states.

### Phase 3: Backend (10 min)

Option A: **Lightweight** (MVP — no new endpoint)
- Web service reads `.agents/` and `.agentops/` files directly via `fetch()` with explicit URLs
- Risk: Requires CORS or CORS proxy; may not work in all environments

Option B: **Recommended** (Safe + Structured)
- Add `GET /api/agentops/status` endpoint to `services/api-gateway/app/main.py`
- Reads files server-side; returns structured JSON
- Requires `agentops:read` scope (add to `DEFAULT_DEVICE_SCOPES`)
- Write test in `services/api-gateway/tests/test_security.py`

### Phase 4: Page Logic (15 min)

In `AgentOpsConsolePage.vue`:

```typescript
const { status, localTasks, saasTasks, reports, events } = ref({...})
const loading = ref(false)
const error = ref('')

async function load() {
  try {
    loading.value = true
    const response = await jsonFetch<AgentOpsStatus>(`${apiUrl}/api/agentops/status`)
    status.value = response
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
```

- Separate "Local Swarm" and "SaaS Integration" tabs or panels
- Graceful fallbacks if either JSON is missing
- Refresh button re-runs `load()`

### Phase 5: Tests (10 min)

Create `tests/test_agentops_console.py`:

```python
def test_agentops_route_exists():
    routes = (WEB / "router" / "routes.ts").read_text()
    assert "/agentops" in routes and "AgentOpsConsolePage" in routes

def test_agentops_components_exist():
    for comp in ["AgentOpsTaskCard", "AgentOpsWorktreeStatus", "AgentOpsModelAvailability", "AgentOpsEventLog"]:
        assert (WEB / "components" / f"{comp}.vue").exists()

def test_agentops_page_imports_services():
    page = (WEB / "pages" / "AgentOpsConsolePage.vue").read_text()
    assert "agentops" in page  # imports or uses service

def test_agentops_task_paths_are_safe():
    # Validate .agents/active.json paths
    pass
```

### Phase 6: Manual Testing (10 min)

```bash
pnpm --dir apps/web build
# Open browser: http://localhost:8080 → navigate to /agentops
# Verify:
#   - Page loads
#   - Tasks display (or "no tasks" state)
#   - Tool badges show correctly
#   - Worktree links work (if worktrees exist)
```

### Phase 7: Final Checks

```bash
scripts/agents/run-pytest.sh tests -q
./scripts/check-secrets.sh
pnpm --dir apps/web build
docker compose --env-file .env --profile full config
```

---

## 9. Remaining Unknowns / Questions for Executor

1. **Should worktree diffs be editable from the UI?**
   - Scout: No. Read-only console. Real edits happen in terminal or through approval gate.

2. **Should report markdown be syntax-highlighted or just rendered as-is?**
   - Scout: Recommend Quasar's `q-markdown` or similar for prettier rendering. XSS-safe.

3. **Should the page auto-refresh or require manual "Refresh" button?**
   - Scout: Manual refresh (safer). Auto-refresh could be added later with a toggle.

4. **Should SaaS event log paginate or show "load more"?**
   - Scout: Show last 100 events; add "load more" button if needed. Keep initial load fast.

5. **Where should links to detailed reports go — internal markdown viewer or external?**
   - Scout: Internal read-only viewer (avoid exposing raw filesystem paths to browser). Could be a modal or new page route `/agentops/report/:task_id`.

---

## 10. Summary

The **AgentOps console page is straightforward to implement**:

- No new backend service needed (use existing API gateway proxy pattern)
- Frontend uses proven Nexus UI component patterns
- Data sources are local JSON files (safe to read server-side)
- Read-only UX removes security complexity
- Clear separation from Coding Agent (remote queue)

**Critical success factors**:
1. Validate task allowed_paths for secrets before returning to UI
2. Handle missing/corrupt files gracefully (no 500 errors)
3. Distinguish local swarm from SaaS integration visually
4. Keep tool availability badges accurate and fast
5. Never expose raw filesystem or allow user-driven git commands

**Estimated effort**: 60–90 minutes for a minimal viable console (task list + status badges + event log).

---

## 11. Files Summary

### To Create
- `apps/web/src/pages/AgentOpsConsolePage.vue`
- `apps/web/src/components/AgentOpsTaskCard.vue`
- `apps/web/src/components/AgentOpsWorktreeStatus.vue`
- `apps/web/src/components/AgentOpsModelAvailability.vue`
- `apps/web/src/components/AgentOpsEventLog.vue`
- `apps/web/src/services/agentops.ts`
- `tests/test_agentops_console.py`
- (Optional) `services/api-gateway/app/agentops_handler.py` if new endpoint

### To Edit
- `apps/web/src/router/routes.ts` — add `/agentops` route
- `services/api-gateway/app/main.py` — add `agentops:read` scope + endpoint
- `services/api-gateway/tests/test_security.py` — test agentops authorization

### To Read (reference)
- `CLAUDE.md` — project rules
- `.agents/active.json` — task definitions
- `.agentops/active.json` — SaaS task config
- `.agentops/events.jsonl` — event log format
- `apps/web/src/pages/CodingAgentPage.vue` — pattern for similar pages
- `apps/web/src/components/NexusPageHero.vue` — hero component

---

**Scout Report Complete**  
**Recommended Executor**: Sonnet or Claude Code (UI specialist)  
**Recommended Timeframe**: 1 hour for MVP
