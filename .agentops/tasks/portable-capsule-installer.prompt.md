You are the Tranche 04 Portable Capsule and Installer worker.

Read:
- .agentops/tasks/TRANCHE04_SHARED_CONTEXT.md

Mission:
Design and implement the safe foundations for "use anywhere" mode.

Implement:
1. Portable mode docs and scripts
   - explain USB/external drive usage
   - explain what is portable vs what requires host Docker
   - explain no host credentials by default
   - explain encrypted backup/restore strategy

2. Runtime directory configuration
   - runtime data path can be configured
   - bootstrap respects configured runtime base where practical
   - generated/local runtime files remain ignored by git

3. Install/update workflow
   - preflight checks Docker, Compose, Git, Python, Node/pnpm, disk space
   - update should recommend/perform backup first
   - restore-drill command or documentation exists
   - Windows/WSL caveats documented

4. Safety
   - no secrets in repo
   - no root-owned files from scripts
   - no destructive nuke without explicit confirmation

5. Tests
   - script syntax tests
   - docs/scaffold tests where appropriate
   - compose config remains valid

Do not:
- promise true plug-and-play on locked-down PCs without Docker
- persist credentials on host silently
- auto-provision paid cloud resources
- weaken secret hygiene

Acceptance:
- Portable capsule mode is documented and partially automated
- Bootstrap/update paths are safer
- Runtime folder policy is clear
- Restore drill path exists or is documented
- Report written to .agentops/reports/portable-capsule-installer/report.md

Run:
scripts/agents/run-pytest.sh tests -q
./scripts/check-secrets.sh
docker compose --env-file .env --profile full config >/tmp/personal-os-full.yml
