#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description='Build a deterministic release artifact manifest.')
    parser.add_argument('--version', required=True)
    parser.add_argument('--channel', required=True)
    parser.add_argument('--platform', required=True, choices=['web', 'android', 'desktop', 'server'])
    parser.add_argument('--artifact', required=True, type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--out', type=Path, default=Path('release-manifest.json'))
    args = parser.parse_args()
    artifact = args.artifact
    if not artifact.exists() or not artifact.is_file():
        raise SystemExit(f'artifact file not found: {artifact}')
    manifest = {
        'version': args.version,
        'channel': args.channel,
        'platform': args.platform,
        'artifact': str(artifact),
        'size_bytes': artifact.stat().st_size,
        'sha256': sha256_file(artifact),
        'commit_sha': args.commit.lower(),
    }
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(args.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
