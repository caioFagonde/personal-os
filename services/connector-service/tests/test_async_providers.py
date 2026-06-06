import json

import pytest

from app import providers


class FakeResponse:
    def __init__(self, status_code=200, body=None, text='ok'):
        self.status_code = status_code
        self._body = body if body is not None else {"sid": "SM123"}
        self.text = text
    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class FakeClient:
    response = FakeResponse()
    calls = []
    def __init__(self, *args, **kwargs):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return False
    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


@pytest.mark.asyncio
async def test_send_twilio_whatsapp_success(monkeypatch):
    FakeClient.response = FakeResponse(200, {"sid": "SM123"})
    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeClient)
    result = await providers.send_twilio_whatsapp(account_sid="AC", auth_token="tok", payload={"To":"whatsapp:+5511999999999", "From":"whatsapp:+14155238886", "Body":"hi"}, base_url="https://example.test")
    assert result["sid"] == "SM123"


@pytest.mark.asyncio
async def test_send_twilio_whatsapp_failure(monkeypatch):
    FakeClient.response = FakeResponse(400, {"error": "bad"}, "bad")
    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeClient)
    with pytest.raises(RuntimeError):
        await providers.send_twilio_whatsapp(account_sid="AC", auth_token="tok", payload={}, base_url="https://example.test")


@pytest.mark.asyncio
async def test_publish_ntfy_success_and_text_fallback(monkeypatch):
    FakeClient.response = FakeResponse(200, ValueError("not json"), "published")
    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeClient)
    result = await providers.publish_ntfy(base_url="http://ntfy", topic="topic", message="hello", title="Title")
    assert result["status_code"] == 200


@pytest.mark.asyncio
async def test_publish_ntfy_validation_and_failure(monkeypatch):
    with pytest.raises(ValueError):
        await providers.publish_ntfy(base_url="", topic="", message="")
    FakeClient.response = FakeResponse(500, {}, "boom")
    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeClient)
    with pytest.raises(RuntimeError):
        await providers.publish_ntfy(base_url="http://ntfy", topic="topic", message="hello")
