# Report: capture-e2e

## Summary

Fixed three bugs preventing reliable capture → task/delegation end-to-end flow:

1. **WhatsApp provider typo** — default was `"twillio"` (invalid), causing `ValueError` crash on any delegation. Fixed to `"cloud_api"`.
2. **Debug file write** — `open("debug.txt", "a")` in `load_contact()` would fail or pollute the filesystem. Removed.
3. **Unhandled ValueError on delegation** — invalid `WHATSAPP_PROVIDER` config produced raw 500. Now caught and returned as structured 409 with actionable hint.

Additionally improved the UI error display in CapturePage and TasksPage to parse structured error responses and show the `action` field as a hint.

## Files changed

| File | Change |
|------|--------|
| `services/capture-service/app/main.py` | Fix WHATSAPP_PROVIDER default, remove debug.txt write, wrap delegation `build_delegation_messages` in try/except for ValueError → 409 |
| `apps/web/src/pages/CapturePage.vue` | Parse structured error JSON to show `message` and `action` fields |
| `apps/web/src/pages/TasksPage.vue` | Same structured error parsing |
| `tests/test_capture_e2e.py` | New: 11 acceptance tests covering all criteria |

## Tests run and results

```
python3 -m pytest tests -q
198 passed, 3 failed (pre-existing: missing release scripts), 2 skipped

python3 -m pytest tests/test_capture_e2e.py -v
11 passed

./scripts/check-secrets.sh
No obvious secrets detected.

bash -n scripts/certify/v1-local-smoke.sh
OK (syntax valid)
```

## Acceptance criteria status

| Criterion | Status |
|-----------|--------|
| `/task Buy milk tomorrow` creates a task | PASS — parser routes to `target="self"`, `initial_task_status` returns `"inbox"` |
| `/note Some note` stores a note/capture | PASS — parser routes to non-delegation target |
| `/secretary ...` queues delivery or returns structured 409 | PASS — valid config queues messages; missing channels → 409 with `missing_channels`; invalid provider → 409 with `invalid_delegation_config` |
| UI catches and renders API errors | PASS — both pages parse structured errors and display action hints |
| Non-destructive smoke test exists | PASS — `scripts/certify/v1-local-smoke.sh` + `tests/test_capture_e2e.py` |

## Remaining risks

1. The `UNIQUE(source_kind, source_id)` constraint on `tasks` table doesn't deduplicate when `source_id` is NULL (SQL NULL != NULL). Multiple quick captures with no source_id will always insert, never upsert. Low severity — duplicates are harmless, but could be addressed with a partial unique index.
2. The capture-service internal test file (`services/capture-service/tests/test_parser_delegation_tasking.py`) has an import path issue when run from the repo root. Pre-existing, not blocking.
3. Live delegation delivery depends on connector-service being configured (email/WhatsApp providers). The structured 409 guides setup.

## Suggested follow-up tasks

- Add a partial unique index `CREATE UNIQUE INDEX ... ON tasks(source_kind) WHERE source_id IS NULL` or use `fingerprint` dedup strategy to avoid silent duplicates.
- Wire up Twilio sandbox credentials for integration testing of WhatsApp delegation.
- Add Playwright e2e test exercising the capture → error → action hint UI path.
