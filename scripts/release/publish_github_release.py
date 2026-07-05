#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, pathlib, urllib.request

def request(method: str, url: str, token: str, data=None, content_type='application/json'):
    body = None if data is None else (json.dumps(data).encode() if content_type == 'application/json' else data)
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('X-GitHub-Api-Version', '2022-11-28')
    req.add_header('Content-Type', content_type)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}

p=argparse.ArgumentParser()
p.add_argument('--repo', required=True)
p.add_argument('--token', required=True)
p.add_argument('--tag', required=True)
p.add_argument('--manifest', required=True)
args=p.parse_args()
release = request('POST', f'https://api.github.com/repos/{args.repo}/releases', args.token, {
    'tag_name': args.tag,
    'name': f'Personal OS {args.tag}',
    'body': pathlib.Path(args.manifest).read_text(),
    'draft': True,
    'prerelease': True,
})
print(json.dumps({'status':'created', 'html_url': release.get('html_url'), 'id': release.get('id')}, indent=2))
