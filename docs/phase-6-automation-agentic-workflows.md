# Phase 6 — Automation and Agentic Workflows

Phase 6 introduces the bounded automation substrate for Personal OS. It is intentionally not an unconstrained autonomous agent. It is a policy-driven DAG runtime with explicit approval gates for external side effects.

## Architecture

```txt
Events / schedules / n8n webhooks
        │
        ▼
automation-service
  ├─ workflow registry
  ├─ DAG validator
  ├─ policy evaluator
  ├─ deterministic executor
  ├─ approval manager
  ├─ side-effect outbox
  ├─ schedule detector
  └─ n8n webhook bridge
        │
        ├─ command-bus          approval-gated remote commands
        ├─ module-service       module API calls
        ├─ research-service     document/research events
        ├─ ntfy                 notifications
        └─ n8n                  external workflow interop
```

## Safety model

The runtime classifies nodes before execution. These actions require approval:

- `command_request`
- `n8n_webhook`
- external HTTP destinations
- non-GET HTTP requests
- destructive module API calls
- explicit `approval_gate` nodes
- any node declaring `config.destructive=true`

These scopes are denied outright:

```txt
shell:raw
filesystem:host-write
network:scan
privileged:container
secrets:read
```

Command execution remains mediated by the command bus. The automation service queues side effects into `automation_outbox`; it does not execute arbitrary shell commands.

## Node types

| Type | Purpose |
|---|---|
| `noop` | No-op checkpoint. |
| `transform` | Deterministic payload transformation. |
| `emit_event` | Emits an internal event payload. |
| `http_request` | Policy-gated HTTP call descriptor. |
| `module_api` | Policy-gated module API call descriptor. |
| `command_request` | Creates a command-bus request through an approved template. |
| `notification` | Queues a notification delivery. |
| `n8n_webhook` | Bridges to n8n through signed/approved webhooks. |
| `artifact` | Records an artifact-generation instruction. |
| `approval_gate` | Forces human approval before downstream nodes run. |

## Database tables

Migration:

```txt
infra/postgres/migrations/005_phase_6_automation.sql
```

Tables:

```txt
automation_workflows
automation_events
automation_runs
automation_run_steps
automation_approvals
automation_schedules
automation_outbox
n8n_connections
notification_routes
notification_deliveries
```

## API

```txt
GET  /health
GET  /api/automation/policy
POST /api/automation/workflows
GET  /api/automation/workflows
GET  /api/automation/workflows/{workflow_id}
PATCH /api/automation/workflows/{workflow_id}
POST /api/automation/workflows/{workflow_id}/runs
GET  /api/automation/runs
GET  /api/automation/runs/{run_id}
POST /api/automation/runs/{run_id}/approve
POST /api/automation/events
GET  /api/automation/events
POST /api/automation/schedules
GET  /api/automation/schedules/due
POST /api/automation/n8n/webhook
```

Gateway proxy:

```txt
/api/proxy/automation/{path}
```

Required scopes:

```txt
automation:read
automation:write
```

## Example workflow

```json
{
  "spec": {
    "name": "Study session notification",
    "triggers": [{ "type": "event", "topic": "study.session.completed" }],
    "nodes": [
      { "id": "format", "type": "transform", "config": { "output": { "title": "Study complete" } } },
      {
        "id": "notify",
        "type": "notification",
        "scopes": ["notifications:send"],
        "config": {
          "topic": "personal-os-dev",
          "title": "Study complete",
          "message": "Logged study session."
        }
      }
    ],
    "edges": [{ "from": "format", "to": "notify" }]
  },
  "active": true
}
```

## n8n webhook signing

n8n payloads can be signed with an `x-personal-os-signature` header:

```txt
t=<unix_timestamp>,v1=<hmac_sha256(timestamp + '.' + canonical_json_payload)>
```

The shared secret is stored in `N8N_WEBHOOK_SECRET`. Do not commit it.

## Local commands

```bash
make up-automation
make test-phase6
```

## CI

Phase 6 adds:

```txt
.github/workflows/phase6-automation.yml
```

It runs:

- automation unit tests
- 96% branch coverage gate for DAG/policy/executor/scheduler/n8n/notifications
- Docker Compose contract validation
- Postgres migration smoke test
