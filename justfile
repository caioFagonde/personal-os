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
  just test-backend
  python -m pytest tests

test-backend:
  cd services/api-gateway && python -m pytest tests -q --cov=app.security --cov-branch --cov-fail-under=95
  cd services/sync-engine && python -m pytest tests -q --cov=app.conflict --cov-branch --cov-fail-under=95
  cd services/command-bus && python -m pytest tests -q --cov=app.signing --cov-branch --cov-fail-under=100

test-frontend:
  pnpm --dir apps/web test

test-mobile:
  pnpm --dir apps/mobile validate

test-desktop:
  pnpm --dir apps/desktop validate
  cd apps/desktop && cargo test --manifest-path src-tauri/Cargo.toml

nuke:
  read -rp "Type NUKE to delete containers and volumes: " confirm; [[ "$confirm" == "NUKE" ]]; docker compose --env-file .env down -v --remove-orphans
