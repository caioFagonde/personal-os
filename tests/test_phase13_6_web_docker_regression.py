from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_web_compose_uses_monorepo_build_context():
    compose = (ROOT / 'docker-compose.yml').read_text()
    assert '  web:\n    build:\n      context: .\n      dockerfile: apps/web/Dockerfile' in compose
    assert '  web:\n    build:\n      context: ./apps/web' not in compose


def test_web_dockerfile_installs_from_monorepo_root():
    dockerfile = (ROOT / 'apps/web/Dockerfile').read_text()
    assert 'WORKDIR /app' in dockerfile
    assert 'COPY . .' in dockerfile
    assert 'WORKDIR /app/apps/web' in dockerfile
    assert 'pnpm install --no-frozen-lockfile' in dockerfile
