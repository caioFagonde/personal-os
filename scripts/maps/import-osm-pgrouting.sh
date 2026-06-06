#!/usr/bin/env bash
set -euo pipefail
OSM_PBF="${1:-}"
DB_CONTAINER="${DB_CONTAINER:-personal-os-postgres}"
DB_NAME="${POSTGRES_DB:-personal_os}"
DB_USER="${POSTGRES_USER:-personal_os}"
if [[ -z "$OSM_PBF" ]]; then
  echo "Usage: $0 <path-to-region.osm.pbf>" >&2
  exit 2
fi
if [[ ! -f "$OSM_PBF" ]]; then
  echo "File not found: $OSM_PBF" >&2
  exit 1
fi
cat >&2 <<'NOTE'
This script imports OpenStreetMap data you are authorized to use into PostGIS/pgRouting.
It expects osm2pgsql and osmium inside the database image or installed by an operator-managed extension image.
NOTE
docker cp "$OSM_PBF" "$DB_CONTAINER:/tmp/region.osm.pbf"
docker exec -i "$DB_CONTAINER" bash -lc "set -euo pipefail
  osmium sort /tmp/region.osm.pbf -o /tmp/region.sorted.osm.pbf --overwrite
  osm2pgsql -c -d '$DB_NAME' -U '$DB_USER' -H localhost /tmp/region.sorted.osm.pbf
  psql -U '$DB_USER' -d '$DB_NAME' -v ON_ERROR_STOP=1 <<'SQL'
DROP TABLE IF EXISTS ways_noded CASCADE;
CREATE TABLE ways_noded AS
SELECT row_number() OVER () as id, geom as the_geom
FROM (
  SELECT (ST_Dump(ST_Node(ST_MakeValid(ST_Collect(ST_Transform(way, 4326)))))).geom as geom
  FROM planet_osm_line
  WHERE highway IS NOT NULL
) dumped;
ALTER TABLE ways_noded ADD COLUMN length_m double precision;
UPDATE ways_noded SET length_m = ST_Length(the_geom::geography);
ALTER TABLE ways_noded ADD COLUMN source integer;
ALTER TABLE ways_noded ADD COLUMN target integer;
ALTER TABLE ways_noded ADD PRIMARY KEY (id);
SELECT pgr_createTopology('ways_noded', 0.00001, 'the_geom', 'id');
SQL"
