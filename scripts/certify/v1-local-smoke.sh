#!/usr/bin/env bash
set -euo pipefail

# ── V1 Local Smoke Tests ─────────────────────────────────────────────────────
# Non-destructive validation that Personal OS is running correctly.
# Assumes stack is up: make up or ./scripts/bootstrap.sh --full
# ──────────────────────────────────────────────────────────────────────────────

API=${API_GATEWAY_URL:-http://localhost:8080}
WEB=${WEB_URL:-http://localhost:9000}
PASS=0 FAIL=0 SKIP=0

ok()   { PASS=$((PASS+1)); printf "  ✓ %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); printf "  ✗ %s\n" "$1"; }
skip() { SKIP=$((SKIP+1)); printf "  ○ %s\n" "$1"; }

check_http() {
  local label="$1" url="$2" expected="${3:-200}"
  code=$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000")
  if [ "$code" = "$expected" ]; then ok "$label ($code)"; else fail "$label (got $code, expected $expected)"; fi
}

check_json_field() {
  local label="$1" url="$2" field="$3"
  body=$(curl -s "$url" 2>/dev/null || echo "")
  if echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); assert $field" 2>/dev/null; then
    ok "$label"
  else
    fail "$label"
  fi
}

# ── 1. Core service health ────────────────────────────────────────────────────
echo "── Core services ──"
check_http "API gateway /health"           "$API/health"
check_http "Sync engine"                   "http://localhost:8081/health"
check_http "Command bus"                   "http://localhost:8082/health"
check_http "Module service"                "http://localhost:8083/health"

# ── 2. Optional service health ────────────────────────────────────────────────
echo "── Optional services ──"
for svc_pair in \
  "Research:http://localhost:8084/health" \
  "Automation:http://localhost:8085/health" \
  "Digital twin:http://localhost:8086/health" \
  "Capture:http://localhost:8092/health" \
  "Study companion:http://localhost:8093/health" \
  "Connectors:http://localhost:8094/health" \
  "Model runtime:http://localhost:8095/health" \
  "Coding agent:http://localhost:8096/health"; do
  label="${svc_pair%%:*}"
  url="${svc_pair#*:}"
  code=$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000")
  if [ "$code" = "200" ]; then ok "$label"; elif [ "$code" = "000" ]; then skip "$label (not running)"; else fail "$label ($code)"; fi
done

# ── 3. Web UI reachable ───────────────────────────────────────────────────────
echo "── Web UI ──"
check_http "Web UI home" "$WEB"

# ── 4. Module registry ───────────────────────────────────────────────────────
echo "── Module registry ──"
check_json_field "Modules registered (≥1)" "$API/api/modules" "len(d) >= 1"

# ── 5. Capture → task creation ────────────────────────────────────────────────
echo "── Capture ──"
capture_resp=$(curl -s -X POST "$API/api/proxy/capture/api/capture" \
  -H 'content-type: application/json' \
  -d '{"text":"/task Smoke test task from v1-local-smoke","source_kind":"smoke_test"}' 2>/dev/null)
if echo "$capture_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['task']['status'] == 'inbox'" 2>/dev/null; then
  ok "Capture creates task"
else
  fail "Capture creates task"
fi

# ── 6. Task list ──────────────────────────────────────────────────────────────
echo "── Tasks ──"
check_json_field "Task list accessible" "$API/api/proxy/capture/api/tasks" "isinstance(d, list)"

# ── 7. Zettelkasten ───────────────────────────────────────────────────────────
echo "── Zettelkasten ──"
check_json_field "Zettelkasten notes list" "$API/api/proxy/modules/api/zettelkasten/notes" "isinstance(d, list)"

# ── 8. Study companion ───────────────────────────────────────────────────────
echo "── Study companion ──"
study_resp=$(curl -s -X POST "$API/api/proxy/study-companion/api/study-companion/text" \
  -H 'content-type: application/json' \
  -d '{"text":"Smoke test: the quick brown fox.","source":"smoke","title":"Smoke"}' 2>/dev/null)
if echo "$study_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'atoms' in d or 'note_id' in d" 2>/dev/null; then
  ok "Study companion text capture"
else
  fail "Study companion text capture"
fi

# ── 9. Connector status ──────────────────────────────────────────────────────
echo "── Connectors ──"
check_json_field "Connector status" "$API/api/proxy/connectors/api/connectors/status" "isinstance(d, dict)"

# ── 10. Sync health ──────────────────────────────────────────────────────────
echo "── Sync ──"
check_json_field "Sync health" "$API/api/proxy/sync/api/sync/health" "'status' in d"
check_json_field "Sync conflicts" "$API/api/proxy/sync/api/sync/conflicts" "isinstance(d, list)"

# ── 11. Coding agent ─────────────────────────────────────────────────────────
echo "── Coding agent ──"
check_json_field "Coding agent status" "$API/api/proxy/coding-agent/api/coding-agent/status" "'execute_enabled' in d"

# ── 12. Model runtime ────────────────────────────────────────────────────────
echo "── Model runtime ──"
check_json_field "Model runtime runtimes" "$API/api/proxy/model-runtime/health" "len(d.get('runtimes',[])) >= 1"

# ── 13. No restart loops ─────────────────────────────────────────────────────
echo "── Stability ──"
restarts=$(docker compose --env-file .env ps 2>/dev/null | grep -ci "restart" || echo "0")
if [ "$restarts" = "0" ] || [ "$restarts" = "1" ]; then
  ok "No restart loops (tileserver allowed)"
else
  fail "Restart loops detected ($restarts services)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
printf "  PASS: %d  FAIL: %d  SKIP: %d\n" "$PASS" "$FAIL" "$SKIP"
echo "═══════════════════════════════════════════"
if [ "$FAIL" -gt 0 ]; then exit 1; fi
