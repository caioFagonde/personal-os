from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.live

BASE_URL = os.environ.get('PERSONAL_OS_BASE_URL', 'http://localhost:8080')
RUN_LIVE = os.environ.get('RUN_LIVE_CONNECTOR_TESTS', '').lower() in {'1', 'true', 'yes'}


def _post_json(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f'{BASE_URL}{path}',
        data=json.dumps(payload).encode(),
        headers={'content-type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode() or '{}')
    except urllib.error.HTTPError as exc:  # pragma: no cover - depends on live server
        pytest.fail(f'{path} failed: {exc.code} {exc.read().decode(errors="ignore")}')


@pytest.mark.skipif(not RUN_LIVE, reason='set RUN_LIVE_CONNECTOR_TESTS=true to run live connector sandbox tests')
def test_ntfy_live_connector_can_publish_when_enabled():
    result = _post_json('/api/proxy/connectors/api/connectors/ntfy/test', {'execute': True, 'message': 'Personal OS live ntfy certification'})
    assert result.get('status') in {'sent', 'dry_run', 'ok'}


@pytest.mark.skipif(not RUN_LIVE, reason='set RUN_LIVE_CONNECTOR_TESTS=true to run live connector sandbox tests')
def test_twilio_live_connector_can_dry_run_or_send_when_enabled():
    payload = {'execute': os.environ.get('TWILIO_LIVE_SEND', '').lower() in {'1', 'true', 'yes'}, 'message': 'Personal OS live Twilio certification'}
    result = _post_json('/api/proxy/connectors/api/connectors/twilio/test', payload)
    assert result.get('status') in {'dry_run', 'sent'}
