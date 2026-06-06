#!/usr/bin/env python3
"""Tiny SPA static server for CI.

Serves static assets normally and falls back to index.html for history-mode routes.
"""
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
from pathlib import Path


class SPARequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        root = Path(os.environ.get('SPA_ROOT', 'apps/web/dist/spa')).resolve()
        rel = path.split('?', 1)[0].split('#', 1)[0].lstrip('/')
        candidate = (root / rel).resolve()
        if candidate.is_dir():
            candidate = candidate / 'index.html'
        if candidate.exists() and root in candidate.parents or candidate == root:
            return str(candidate)
        return str(root / 'index.html')

    def end_headers(self) -> None:
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='apps/web/dist/spa')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9000)
    args = parser.parse_args()
    os.environ['SPA_ROOT'] = args.root
    with socketserver.TCPServer((args.host, args.port), SPARequestHandler) as httpd:
        print(f'Serving {args.root} at http://{args.host}:{args.port}', flush=True)
        httpd.serve_forever()


if __name__ == '__main__':
    main()
