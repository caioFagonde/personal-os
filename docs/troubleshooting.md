# Troubleshooting

## Configuration diagnostics

Run `python3 scripts/validate-env.py .env` before starting or restarting
services. Errors identify malformed URLs, ports, phone numbers, OAuth redirect
URIs, and cloud configuration shapes without printing configured values.

Warnings for incomplete optional providers do not prevent core services from
running. Complete setup in the Settings UI, then restart only the affected
service, for example:

```bash
docker compose --env-file .env restart connector-service
```

Use `./scripts/doctor-full.sh` for validation plus runtime health checks.
