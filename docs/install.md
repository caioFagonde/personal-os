# Install

Linux:

```bash
./scripts/bootstrap.sh
```

Windows:

```powershell
.\scripts\bootstrap.ps1
```

Profiles:

```bash
docker compose --env-file .env --profile core up -d
docker compose --env-file .env --profile apps up -d
docker compose --env-file .env --profile ai up -d
docker compose --env-file .env --profile maps up -d
docker compose --env-file .env --profile automation up -d
docker compose --env-file .env --profile research up -d
docker compose --env-file .env --profile observability up -d
docker compose --env-file .env --profile full up -d
```
