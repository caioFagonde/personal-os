# Phase 8 — Digital Twin Intelligence

Phase 8 adds the privacy-aware intelligence layer: a unified ontology, timeline, state model, memory policy, and deterministic recommendation engine.

## Service

`services/digital-twin-service` exposes:

```txt
GET  /health
GET  /api/digital-twin/ontology
POST /api/digital-twin/entities
GET  /api/digital-twin/entities
POST /api/digital-twin/relationships
POST /api/digital-twin/events
GET  /api/digital-twin/timeline
GET  /api/digital-twin/state/infer
POST /api/digital-twin/state
POST /api/digital-twin/goals
GET  /api/digital-twin/goals
POST /api/digital-twin/recommendations
GET  /api/digital-twin/memory/policy
PUT  /api/digital-twin/memory/policy
POST /api/digital-twin/memory
GET  /api/digital-twin/memory
GET  /api/digital-twin/evaluations/golden
```

## Model boundaries

The digital twin is not an unconstrained agent. It produces recommendations with explicit rationale and action payloads. Side effects remain delegated to the automation service and command bus, where approval gates and command policies already apply.

## Privacy policy

Memory records are classified as `public`, `personal`, `sensitive`, or `restricted`. The default policy excludes sensitive/restricted memories from recommendation generation unless explicitly enabled. External outputs are redacted by default.

Default retention:

```txt
ephemeral: 7 days
working:   90 days
long_term: 3650 days
archival:  indefinite
```

## Evaluation harness

The service includes deterministic golden tests for expected recommendation behavior:

- Low cognitive energy prioritizes recovery.
- Learning goals with weak learning momentum produce study actions.
- High ops pressure creates an approval-gated checkpoint.

Run:

```bash
make test-phase8
```

## Local startup

```bash
make up-digital-twin
```

The web app exposes the module at `/digital-twin`.
