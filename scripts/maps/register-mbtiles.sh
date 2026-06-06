#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <name> <relative-path-under-data/maps/file.mbtiles>" >&2
  exit 2
fi
NAME="$1"
PATH_IN_DATA="$2"
API="${MODULE_API_URL:-http://localhost:8080/api/proxy/modules}"
curl -fsS -X POST "$API/api/geospatial/map-datasets" \
  -H 'content-type: application/json' \
  ${ACCESS_TOKEN:+-H "authorization: Bearer $ACCESS_TOKEN"} \
  -d "{\"name\":\"$NAME\",\"dataset_type\":\"mbtiles\",\"local_path\":\"/data/$PATH_IN_DATA\",\"metadata\":{\"registered_by\":\"scripts/maps/register-mbtiles.sh\"}}"
