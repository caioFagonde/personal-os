#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://localhost:8080}"
TOKEN="${ACCESS_TOKEN:-}"
if [[ -z "$TOKEN" ]]; then
  TOKEN=$(curl -fsS -X POST "$API/api/devices/register" -H 'content-type: application/json' -d '{"device_key":"connector-smoke","name":"Connector Smoke","kind":"desktop","platform":"linux"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
fi
curl -fsS -H "authorization: Bearer $TOKEN" "$API/api/proxy/connectors/api/connectors" | python3 -m json.tool
curl -fsS -X POST -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' "$API/api/proxy/connectors/api/connectors/ntfy/test" -d '{"execute":false}' | python3 -m json.tool
