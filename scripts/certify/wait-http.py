#!/usr/bin/env python3
from __future__ import annotations
import sys, time, urllib.request
url = sys.argv[1]
timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 120
start = time.time()
last = None
while time.time() - start < timeout:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            if r.status < 500:
                print(f"ready: {url} -> {r.status}")
                raise SystemExit(0)
    except Exception as exc:
        last = exc
    time.sleep(3)
print(f"timed out waiting for {url}: {last}", file=sys.stderr)
raise SystemExit(1)
