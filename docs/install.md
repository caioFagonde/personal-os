# Install

Linux:

```bash
python3 scripts/validate-env.py --example .env.example
./scripts/bootstrap.sh
```

Before starting services, validate local configuration with
`python3 scripts/validate-env.py .env`. The validator reports variable names
and remediation only; it never prints configured values. Incomplete optional
providers are warnings and do not prevent core services from starting.

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
