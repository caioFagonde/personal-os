from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .oauth import OAuthConfig, refresh_payload, token_endpoint

E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


@dataclass(frozen=True)
class ProviderStatus:
    id: str
    configured: bool
    actionable: bool
    status: str
    message: str
    next_action_url: str | None = None
    required_env: tuple[str, ...] = ()
    required_any_of: tuple[tuple[str, ...], ...] = ()
    config_metadata: tuple[dict[str, Any], ...] = ()
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderSendResult:
    provider: str
    status: str
    provider_message_id: str | None
    response: dict[str, Any]


CONNECTOR_CONFIG_METADATA: dict[str, tuple[dict[str, Any], ...]] = {
    "obsidian": (
        {
            "key": "OBSIDIAN_VAULT_PATH",
            "label": "Vault path",
            "kind": "path",
            "required": True,
            "secret": False,
            "help": "Absolute path to an existing Obsidian vault.",
        },
    ),
    "notion": (
        {
            "key": "NOTION_API_TOKEN",
            "label": "Integration token",
            "kind": "secret",
            "required": True,
            "secret": True,
            "storage": "server_environment",
        },
        {"key": "NOTION_DATABASE_ID", "label": "Default database ID", "kind": "text", "required": False, "secret": False},
        {"key": "NOTION_PAGE_ID", "label": "Default page ID", "kind": "text", "required": False, "secret": False},
    ),
    "trello": (
        {"key": "TRELLO_API_KEY", "label": "API key", "kind": "secret", "required": True, "secret": True, "storage": "server_environment"},
        {"key": "TRELLO_API_TOKEN", "label": "API token", "kind": "secret", "required": True, "secret": True, "storage": "server_environment"},
        {"key": "TRELLO_BOARD_ID", "label": "Board ID", "kind": "text", "required": True, "secret": False},
        {"key": "TRELLO_LIST_ID", "label": "List ID", "kind": "text", "required": True, "secret": False},
    ),
}


def validate_obsidian_vault_path(vault_path: str, relative_path: str) -> tuple[Path, Path]:
    if not vault_path:
        raise ValueError("OBSIDIAN_VAULT_PATH is required")
    vault = Path(vault_path).expanduser()
    if not vault.is_absolute():
        raise ValueError("OBSIDIAN_VAULT_PATH must be an absolute path")
    vault = vault.resolve()
    if not vault.is_dir():
        raise ValueError("OBSIDIAN_VAULT_PATH must point to an existing directory")

    relative = Path(relative_path)
    if relative.is_absolute() or not relative.parts or relative.name in {"", ".", ".."}:
        raise ValueError("Obsidian note path must be a relative Markdown path")
    if relative.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError("Obsidian note path must use a Markdown .md or .markdown extension")

    target = (vault / relative).resolve()
    if target == vault or vault not in target.parents:
        raise ValueError("Obsidian note path must stay inside the configured vault")
    return vault, target


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


def gmail_raw_message(*, to: str, subject: str, body: str, sender: str = "me") -> str:
    if not to or not body:
        raise ValueError("email recipient and body are required")
    msg = EmailMessage()
    msg["To"] = to
    msg["From"] = sender
    msg["Subject"] = subject or "Personal OS"
    msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode().rstrip("=")


async def refresh_access_token(*, config: OAuthConfig, refresh_token: str) -> dict[str, Any]:
    if not refresh_token:
        raise ValueError("refresh token is required")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            token_endpoint(config.provider, config.tenant),
            data=refresh_payload(config, refresh_token=refresh_token),
            headers={"accept": "application/json"},
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"{config.provider} refresh failed: {resp.status_code} {resp.text[:500]}")
    return resp.json()


async def send_gmail(*, access_token: str, to: str, subject: str, body: str) -> dict[str, Any]:
    raw = gmail_raw_message(to=to, subject=subject, body=body)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"authorization": f"Bearer {access_token}", "content-type": "application/json"},
            json={"raw": raw},
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"Gmail send failed: {resp.status_code} {resp.text[:500]}")
    return resp.json()


async def send_microsoft_mail(*, access_token: str, to: str, subject: str, body: str) -> dict[str, Any]:
    payload = {
        "message": {
            "subject": subject or "Personal OS",
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}],
        },
        "saveToSentItems": True,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            headers={"authorization": f"Bearer {access_token}", "content-type": "application/json"},
            json=payload,
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"Microsoft sendMail failed: {resp.status_code} {resp.text[:500]}")
    return {"status_code": resp.status_code, "accepted": resp.status_code in {200, 202}}


async def upload_google_drive_file(*, access_token: str, filename: str, content: bytes, mime_type: str = "application/gzip") -> dict[str, Any]:
    metadata = {"name": filename}
    boundary = "personal_os_boundary"
    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers={"authorization": f"Bearer {access_token}", "content-type": f"multipart/related; boundary={boundary}"},
            content=body,
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"Google Drive upload failed: {resp.status_code} {resp.text[:500]}")
    return resp.json()


async def upload_onedrive_file(*, access_token: str, filename: str, content: bytes) -> dict[str, Any]:
    safe_name = quote(filename, safe="")
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/PersonalOSBackups/{safe_name}:/content"
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.put(url, headers={"authorization": f"Bearer {access_token}", "content-type": "application/octet-stream"}, content=content)
    if resp.status_code >= 400:
        raise RuntimeError(f"OneDrive upload failed: {resp.status_code} {resp.text[:500]}")
    return resp.json()


def provider_status_from_env(env: dict[str, str], provider: str) -> ProviderStatus:
    provider = provider.lower()
    if provider == "twilio":
        configured = bool(env.get("TWILIO_ACCOUNT_SID") and env.get("TWILIO_AUTH_TOKEN") and (env.get("TWILIO_WHATSAPP_FROM") or env.get("TWILIO_MESSAGING_SERVICE_SID")))
        return ProviderStatus("twilio", configured, configured, "ready" if configured else "needs_configuration", "Twilio WhatsApp configured" if configured else "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM or TWILIO_MESSAGING_SERVICE_SID")
    if provider == "ntfy":
        configured = bool(env.get("NTFY_BASE_URL") and env.get("NTFY_TOPIC"))
        return ProviderStatus("ntfy", configured, configured, "ready" if configured else "needs_configuration", "ntfy configured" if configured else "Set NTFY_BASE_URL and NTFY_TOPIC")
    if provider == "tailscale":
        configured = bool(env.get("TAILSCALE_AUTHKEY") or env.get("TAILSCALE_AUTHORIZED") == "true")
        return ProviderStatus("tailscale", configured, True, "ready" if configured else "manual_authorization_required", "Tailscale configured or authorized" if configured else "Sign in with Tailscale CLI/app or set TAILSCALE_AUTHKEY")
    if provider == "google":
        configured = bool(env.get("GOOGLE_CLIENT_ID") and env.get("GOOGLE_CLIENT_SECRET") and env.get("GOOGLE_REDIRECT_URI"))
        return ProviderStatus("google", configured, configured, "ready" if configured else "needs_oauth_client", "Google OAuth client configured" if configured else "Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI")
    if provider == "microsoft":
        configured = bool(env.get("MICROSOFT_CLIENT_ID") and env.get("MICROSOFT_CLIENT_SECRET") and env.get("MICROSOFT_REDIRECT_URI"))
        return ProviderStatus("microsoft", configured, configured, "ready" if configured else "needs_oauth_client", "Microsoft OAuth client configured" if configured else "Set MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_REDIRECT_URI")
    if provider == "obsidian":
        configured = bool(env.get("OBSIDIAN_VAULT_PATH"))
        return ProviderStatus(
            "obsidian",
            configured,
            True,
            "ready" if configured else "needs_configuration",
            "Obsidian vault path configured" if configured else "Set OBSIDIAN_VAULT_PATH to an absolute vault directory",
            required_env=("OBSIDIAN_VAULT_PATH",),
            config_metadata=CONNECTOR_CONFIG_METADATA["obsidian"],
            capabilities=("export_dry_run", "import_dry_run", "explicit_local_export"),
        )
    if provider == "notion":
        has_target = bool(env.get("NOTION_DATABASE_ID") or env.get("NOTION_PAGE_ID"))
        configured = bool(env.get("NOTION_API_TOKEN") and has_target)
        return ProviderStatus(
            "notion",
            configured,
            True,
            "ready" if configured else "needs_configuration",
            "Notion integration metadata configured" if configured else "Set NOTION_API_TOKEN and a default database or page ID",
            required_env=("NOTION_API_TOKEN",),
            required_any_of=(("NOTION_DATABASE_ID", "NOTION_PAGE_ID"),),
            config_metadata=CONNECTOR_CONFIG_METADATA["notion"],
            capabilities=("page_create_dry_run", "page_export_dry_run"),
        )
    if provider == "trello":
        required = ("TRELLO_API_KEY", "TRELLO_API_TOKEN", "TRELLO_BOARD_ID", "TRELLO_LIST_ID")
        configured = all(env.get(key) for key in required)
        return ProviderStatus(
            "trello",
            configured,
            True,
            "ready" if configured else "needs_configuration",
            "Trello board and list metadata configured" if configured else "Set Trello API key, token, board ID, and list ID",
            required_env=required,
            config_metadata=CONNECTOR_CONFIG_METADATA["trello"],
            capabilities=("card_create_dry_run",),
        )
    raise ValueError(f"unknown provider: {provider}")
