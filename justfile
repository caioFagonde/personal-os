set shell := ["bash", "-cu"]

install:
  ./scripts/bootstrap.sh

doctor:
  ./scripts/doctor.sh

up:
  docker compose --env-file .env --profile core up -d --build

down:
  docker compose --env-file .env down

logs:
  docker compose --env-file .env logs -f --tail=200

backup:
  ./scripts/backup.sh

restore:
  ./scripts/restore.sh

mobile:
  ./scripts/deploy-android.sh

desktop:
  ./scripts/deploy-desktop.sh

test:
  python -m pytest tests services/sync-engine/tests

nuke:
  read -rp "Type NUKE to delete containers and volumes: " confirm; [[ "$confirm" == "NUKE" ]]; docker compose --env-file .env down -v --remove-orphans
