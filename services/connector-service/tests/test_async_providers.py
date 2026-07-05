
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

@pytest.mark.asyncio
async def test_refresh_gmail_microsoft_and_uploads(monkeypatch):
    from app.oauth import OAuthConfig
    FakeClient.calls = []
    FakeClient.response = FakeResponse(200, {"access_token": "at", "id": "file123", "webUrl": "https://one"})
    async def put(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response
    FakeClient.put = put
    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeClient)
    cfg = OAuthConfig(provider="google", client_id="cid", client_secret="sec", redirect_uri="http://local", scopes=tuple())
    token = await providers.refresh_access_token(config=cfg, refresh_token="rt")
    assert token["access_token"] == "at"
    gmail = await providers.send_gmail(access_token="at", to="a@example.com", subject="S", body="B")
    assert gmail["id"] == "file123"
    ms = await providers.send_microsoft_mail(access_token="at", to="a@example.com", subject="S", body="B")
    assert ms["accepted"] is True
    gup = await providers.upload_google_drive_file(access_token="at", filename="b.tar.gz", content=b"abc")
    assert gup["id"] == "file123"
    oup = await providers.upload_onedrive_file(access_token="at", filename="b.tar.gz", content=b"abc")
    assert oup["webUrl"] == "https://one"


@pytest.mark.asyncio
async def test_provider_http_failures(monkeypatch):
    from app.oauth import OAuthConfig
    FakeClient.response = FakeResponse(401, {}, "nope")
    async def put(self, url, **kwargs):
        return self.response
    FakeClient.put = put
    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeClient)
    cfg = OAuthConfig(provider="google", client_id="cid", client_secret="sec", redirect_uri="http://local", scopes=tuple())
    with pytest.raises(RuntimeError):
        await providers.refresh_access_token(config=cfg, refresh_token="rt")
    with pytest.raises(RuntimeError):
        await providers.send_gmail(access_token="bad", to="a@example.com", subject="S", body="B")
    with pytest.raises(RuntimeError):
        await providers.send_microsoft_mail(access_token="bad", to="a@example.com", subject="S", body="B")
    with pytest.raises(RuntimeError):
        await providers.upload_google_drive_file(access_token="bad", filename="b", content=b"x")
    with pytest.raises(RuntimeError):
        await providers.upload_onedrive_file(access_token="bad", filename="b", content=b"x")


def test_gmail_raw_message_validation():
    with pytest.raises(ValueError):
        providers.gmail_raw_message(to="", subject="", body="")
