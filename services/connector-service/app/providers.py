from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Any

import httpx

E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


@dataclass(frozen=True)
class ProviderStatus:
    id: str
    configured: bool
    actionable: bool
    status: str
    message: str
    next_action_url: str | None = None


def normalize_whatsapp_address(number: str) -> str:
    cleaned = number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if cleaned.startswith("whatsapp:"):
        cleaned = cleaned.removeprefix("whatsapp:")
    if not E164_RE.fullmatch(cleaned):
        raise ValueError("WhatsApp number must be E.164, e.g. +5511999999999")
    return f"whatsapp:{cleaned}"


def twilio_auth_header(account_sid: str, auth_token: str) -> dict[str, str]:
    if not account_sid or not auth_token:
        raise ValueError("Twilio account SID and auth token are required")
    token = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    return {"authorization": f"Basic {token}"}


def twilio_message_payload(*, to: str, body: str, from_: str | None = None, messaging_service_sid: str | None = None) -> dict[str, str]:
    if not to or not body.strip():
        raise ValueError("recipient and message body are required")
    payload = {"To": normalize_whatsapp_address(to), "Body": body.strip()}
    if messaging_service_sid:
        payload["MessagingServiceSid"] = messaging_service_sid
    elif from_:
        payload["From"] = from_ if from_.startswith("whatsapp:") else normalize_whatsapp_address(from_)
    else:
        raise ValueError("Twilio requires either From or MessagingServiceSid")
    return payload


async def send_twilio_whatsapp(*, account_sid: str, auth_token: str, payload: dict[str, str], base_url: str = "https://api.twilio.com") -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/2010-04-01/Accounts/{account_sid}/Messages.json"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, data=payload, headers=twilio_auth_header(account_sid, auth_token))
    if resp.status_code >= 400:
        raise RuntimeError(f"Twilio send failed: {resp.status_code} {resp.text[:500]}")
    return resp.json()


async def publish_ntfy(*, base_url: str, topic: str, message: str, title: str | None = None) -> dict[str, Any]:
    if not base_url or not topic or not message:
        raise ValueError("ntfy base_url, topic, and message are required")
    headers = {"title": title} if title else {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{base_url.rstrip('/')}/{topic}", content=message.encode("utf-8"), headers=headers)
    if resp.status_code >= 400:
        raise RuntimeError(f"ntfy publish failed: {resp.status_code} {resp.text[:500]}")
    try:
        return resp.json()
    except Exception:
        return {"status_code": resp.status_code, "text": resp.text}


def provider_status_from_env(env: dict[str, str], provider: str) -> ProviderStatus:
    provider = provider.lower()
    if provider == "twilio":
        configured = bool(env.get("TWILIO_ACCOUNT_SID") and env.get("TWILIO_AUTH_TOKEN") and (env.get("TWILIO_WHATSAPP_FROM") or env.get("TWILIO_MESSAGING_SERVICE_SID")))
        return ProviderStatus("twilio", configured, configured, "ready" if configured else "needs_configuration", "Twilio WhatsApp configured" if configured else "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM or TWILIO_MESSAGING_SERVICE_SID")
    if provider == "ntfy":
        configured = bool(env.get("NTFY_BASE_URL") and env.get("NTFY_TOPIC"))
        return ProviderStatus("ntfy", configured, configured, "ready" if configured else "needs_configuration", "ntfy configured" if configured else "Set NTFY_BASE_URL and NTFY_TOPIC")
    if provider == "tailscale":
        configured = bool(env.get("TAILSCALE_AUTHKEY"))
        return ProviderStatus("tailscale", configured, True, "ready" if configured else "manual_authorization_required", "Tailscale auth key configured" if configured else "Sign in with Tailscale CLI/app or set TAILSCALE_AUTHKEY")
    if provider == "google":
        configured = bool(env.get("GOOGLE_CLIENT_ID") and env.get("GOOGLE_CLIENT_SECRET") and env.get("GOOGLE_REDIRECT_URI"))
        return ProviderStatus("google", configured, configured, "ready" if configured else "needs_oauth_client", "Google OAuth client configured" if configured else "Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI")
    if provider == "microsoft":
        configured = bool(env.get("MICROSOFT_CLIENT_ID") and env.get("MICROSOFT_CLIENT_SECRET") and env.get("MICROSOFT_REDIRECT_URI"))
        return ProviderStatus("microsoft", configured, configured, "ready" if configured else "needs_oauth_client", "Microsoft OAuth client configured" if configured else "Set MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_REDIRECT_URI")
    raise ValueError(f"unknown provider: {provider}")
