# AGENTIC_HARNESS_SPEC.md — Nexus Prime Agent Harness

## Starting point (what already exists — preserve)

- `coding-agent-service`: Postgres-backed jobs, prompt policy (mode allowlist, repo allowlist, dangerous-pattern screen), git-worktree isolation, env scrubbing, `CODING_AGENT_EXECUTE=false` default, Claude Code `-p` runner, artifacts (prompt, diff_stat).
- `automation-service`: DAG validation, scheduler, executor policy gates, approvals, outbox.
- `command-bus`: signed command requests + templates + approvals.
- `audit_log` table and approvals tables.

The harness **generalizes** these into one model rather than replacing them. Coding agent becomes `AgentJob(kind="coding")`; automation runs remain their own engine but emit `agent_run` objects into the graph.

## Object model

(Tables in PERSONAL_GRAPH_SCHEMA.md §agentic-harness.)

- **AgentJob** — user intent: kind, title, prompt, policy, project link, status machine `queued → planning → awaiting_approval → running → succeeded|failed|cancelled`.
- **AgentPlan** — machine-readable step list produced before execution; the *only* thing the user must approve for medium-risk jobs.
- **ToolCall** — every tool invocation, `proposed → approved|denied → executed|failed`, with args and result summary. High-risk tools require per-call approval even after plan approval.
- **ApprovalRequest** — unified inbox item (plan-level or tool-level), with risk, reason, expiry (default 24h → expired = denied).
- **AgentMemory** — scoped (`global`, `project:<id>`, `skill:<name>`) facts/preferences/procedures/outcomes with embeddings and confidence; retrieved into context packs; written only via an explicit `remember` tool call (auditable), never silently.
- **Skill** — named instruction+tool bundle, versioned, enable/disable; stored in DB, exported to `/skills/<name>/SKILL.md` for the coding agent.
- **EvalCase** — input/expectation pairs per skill; run on skill change and nightly; failing evals flip skill to `degraded` (usable with warning) not disabled.
- **ArtifactOutput** — every job must end with ≥1 artifact (diff, file in MinIO, note, report, handoff). "Ran successfully with no artifact" is a failed contract.
- **HandoffFile** — coding jobs write `HANDOFF.md` into the worktree (task, constraints, acceptance, files touched) — formalizing the existing `.agents/reports` pattern.
- **AuditEvent** — reuse `audit_log`; every status transition, approval, and tool execution appends one row.

## Tool registry

Declarative registry (DB + `packages/harness/tools/*.py`), each tool declares:

```yaml
name: obsidian.export_note
risk: medium            # low | medium | high
side_effects: filesystem
approval: plan          # none | plan | per_call
rate_limit: 30/hour
schema: {relative_path: str, content: str}
executor: connector-service POST /api/connectors/obsidian/export
```

Initial tool set (all mapping to **existing** endpoints — no new capability surface):

| Tool | Risk | Approval | Backing |
|---|---|---|---|
| graph.search / graph.read | low | none | gateway graph API |
| memory.retrieve | low | none | agent_memory vector query |
| memory.remember | medium | plan | insert w/ audit |
| capture.create / task.create / note.create | low | plan | capture-service, module-service |
| task.update / task.complete | medium | plan | capture-service |
| research.search / research.read_source | low | none | research-service |
| obsidian.export_note | medium | plan | connector-service (create-only semantics kept) |
| obsidian.read_note | low | none | new vault indexer (read path) |
| coding.run_job | high | per_call | coding-agent-service |
| automation.trigger | high | per_call | automation-service |
| connector.send_notification (ntfy) | medium | plan | connector-service |
| backup.run / backup.verify | medium | plan | ops runner (script wrapper, allowlisted) |
| web.search / web.fetch | medium | plan | SearXNG (already in compose), readability extraction |

**Hard rules** (enforced in executor, not in prompts):
- No raw shell. The only process-spawning path is `coding.run_job` inside a git worktree with the existing runner; everything else is HTTP to internal services.
- Tool args validated against schema before execution; unknown tools = job fails.
- Per-job budget: max tool calls (default 50), max wall time, max artifact bytes.
- Coding jobs additionally get execution-side controls: `claude -p --allowedTools "Edit,Read,Write,Bash(git *),Bash(pytest *)"` (configurable per repo), network disabled by default in the worktree env, diff-size cap → auto `awaiting_approval` if exceeded. This closes risk R-09 (prompt-side-only filtering).

## Execution flow

```
POST /api/agents/jobs {kind, title, prompt, project_id?}
  → planner (model-runtime: local model if configured, else the job pauses
    with status=planning_blocked and an honest "no model configured" state —
    never a fake plan)
  → AgentPlan persisted → risk roll-up → ApprovalRequest (unless all-low-risk)
  → owner approves in /agents or via ntfy action link
  → executor loop: ToolCall rows, streaming status via NATS subject nexus.agents.<job_id>
  → artifacts registered in graph (produced_by edges), memory writes if approved
  → job report note optionally exported to Obsidian /Agent Runs/
```

Service placement: a new thin `agent-orchestrator` module **inside automation-service** (it already has scheduler/executor/approval machinery) rather than a 15th service. Coding-agent-service stays as the specialized executor for `coding.run_job`.

## Context packs

`GET /api/agents/context-pack?project_id=…` assembles, deterministically and with size budget:
1. Project README note + pinned decisions
2. Open tasks (top 20 by priority)
3. Top-k memory (project scope, k=10)
4. Top-k related chunks (vector search over object_chunks)
5. Repo map (if repository linked): `git ls-files` summary + HANDOFF conventions
Output: a single markdown file (also writable to the worktree as `CONTEXT_PACK.md`) with source attribution per section. This is both the agent input and the human-auditable record.

## Evals

- `POST /api/agents/skills/{id}/evals/run` executes all EvalCases in dry-run tool mode (tools return recorded fixtures where side effects exist).
- Graders: exact/JSON-subset match, regex, or "artifact exists + passes validator" — no LLM-as-judge until a local judge model is configured, and then labeled as such.
- CI job runs evals for enabled skills nightly; failures create Attention chips on the Command Center.

## UI (in /agents surface)

Queue table → job detail (plan with per-step risk chips, live tool-call log, artifacts, memory writes highlighted) → Approval inbox (also fed to ntfy with approve/deny action URLs signed with short-lived tokens through the gateway).

## Test plan

- Unit: tool schema validation, risk roll-up, state machine transitions, budget enforcement, plan-approval gating (deny path!).
- Integration: end-to-end job with fixture tools against real Postgres in compose lane.
- Contract: "every succeeded job has ≥1 artifact", "no ToolCall executed without approved plan", "expired approvals deny".
- Security: attempt registry-unknown tool, attempt path traversal in obsidian tool args, attempt oversized prompt — all must fail closed with audit rows.
