#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECKS = [
    ('env example', ROOT/'.env.example'),
    ('docker compose', ROOT/'docker-compose.yml'),
    ('model runtime service', ROOT/'services/model-runtime/app/runtime.py'),
    ('live stack e2e', ROOT/'e2e/live-stack.spec.ts'),
    ('physical sync script', ROOT/'scripts/certify/physical-sync.sh'),
    ('publish release script', ROOT/'scripts/release/publish-github-release.sh'),
    ('phase13 workflow', ROOT/'.github/workflows/phase13-live-stack-model-release.yml'),
]
failures=[]
for name, path in CHECKS:
    if not path.exists(): failures.append(f'{name} missing: {path}')
if (ROOT/'.env').exists():
    failures.append('.env is present in repository root; do not include it in release archives')
try:
    subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_phase13_scaffold.py', '-q'], cwd=ROOT, check=True)
except Exception as exc:
    failures.append(f'phase13 scaffold tests failed: {exc}')
result = {'status':'passed' if not failures else 'failed', 'failures':failures}
print(json.dumps(result, indent=2))
sys.exit(0 if not failures else 1)
