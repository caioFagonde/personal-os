from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
MICROSOFT_AUTH_BASE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_BASE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
GOOGLE_DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
MICROSOFT_DEVICE_CODE_BASE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode"

DEFAULT_GOOGLE_SCOPES = (
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.file",
)
DEFAULT_MICROSOFT_SCOPES = (
    "openid",
    "profile",
    "offline_access",
    "User.Read",
    "Mail.Send",
    "Calendars.ReadWrite",
    "Files.ReadWrite",
)


@dataclass(frozen=True)
class OAuthConfig:
    provider: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: tuple[str, ...]
    tenant: str = "common"


@dataclass(frozen=True)
class OAuthStart:
    provider: str
    authorization_url: str
    state: str
    code_verifier: str
    code_challenge: str
    scopes: tuple[str, ...]


def make_state(prefix: str = "pos") -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def make_code_verifier() -> str:
    # RFC 7636 permits 43-128 chars from unreserved charset. token_urlsafe(64) is enough.
    return secrets.token_urlsafe(64)[:128]


def code_challenge_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def normalize_scopes(provider: str, requested: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if requested:
        scopes = tuple(dict.fromkeys(s.strip() for s in requested if s and s.strip()))
    elif provider == "google":
        scopes = DEFAULT_GOOGLE_SCOPES
    elif provider == "microsoft":
        scopes = DEFAULT_MICROSOFT_SCOPES
    else:
        raise ValueError(f"unsupported provider: {provider}")
    if provider == "microsoft" and "offline_access" not in scopes:
        scopes = (*scopes, "offline_access")
    if provider == "google" and "openid" not in scopes:
        scopes = ("openid", "email", "profile", *scopes)
    return tuple(dict.fromkeys(scopes))


def build_authorization_start(config: OAuthConfig, *, state: str | None = None, code_verifier: str | None = None) -> OAuthStart:
    if not config.client_id:
        raise ValueError(f"{config.provider} client_id is required")
    if not config.redirect_uri:
        raise ValueError(f"{config.provider} redirect_uri is required")
    provider = config.provider.lower()
    scopes = normalize_scopes(provider, config.scopes)
    st = state or make_state(provider)
    verifier = code_verifier or make_code_verifier()
    challenge = code_challenge_s256(verifier)
    if provider == "google":
        query = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": st,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        url = f"{GOOGLE_AUTH_URL}?{urlencode(query)}"
    elif provider == "microsoft":
        tenant = config.tenant or "common"
        query = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "response_mode": "query",
            "scope": " ".join(scopes),
            "state": st,
            "prompt": "select_account",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        url = f"{MICROSOFT_AUTH_BASE.format(tenant=tenant)}?{urlencode(query)}"
    else:
        raise ValueError(f"unsupported provider: {config.provider}")
    return OAuthStart(provider=provider, authorization_url=url, state=st, code_verifier=verifier, code_challenge=challenge, scopes=scopes)


def token_endpoint(provider: str, tenant: str = "common") -> str:
    provider = provider.lower()
    if provider == "google":
        return GOOGLE_TOKEN_URL
    if provider == "microsoft":
        return MICROSOFT_TOKEN_BASE.format(tenant=tenant or "common")
    raise ValueError(f"unsupported provider: {provider}")


def token_exchange_payload(config: OAuthConfig, *, code: str, code_verifier: str) -> dict[str, str]:
    if not code:
        raise ValueError("authorization code is required")
    data = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
    }
    if config.client_secret:
        data["client_secret"] = config.client_secret
    return data


def refresh_payload(config: OAuthConfig, *, refresh_token: str) -> dict[str, str]:
    data = {
        "client_id": config.client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    if config.provider == "microsoft":
        data["scope"] = " ".join(normalize_scopes("microsoft", config.scopes))
    if config.client_secret:
        data["client_secret"] = config.client_secret
    return data


def device_authorization_endpoint(provider: str, tenant: str = "common") -> str:
    provider = provider.lower()
    if provider == "google":
        return GOOGLE_DEVICE_CODE_URL
    if provider == "microsoft":
        return MICROSOFT_DEVICE_CODE_BASE.format(tenant=tenant or "common")
    raise ValueError(f"unsupported provider: {provider}")


def device_authorization_payload(config: OAuthConfig) -> dict[str, str]:
    scopes = normalize_scopes(config.provider, config.scopes)
    data = {"client_id": config.client_id, "scope": " ".join(scopes)}
    if config.provider == "google" and config.client_secret:
        data["client_secret"] = config.client_secret
    return data


def device_token_payload(config: OAuthConfig, *, device_code: str) -> dict[str, str]:
    data = {
        "client_id": config.client_id,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }
    if config.provider == "google" and config.client_secret:
        data["client_secret"] = config.client_secret
    if config.provider == "microsoft" and config.client_secret:
        data["client_secret"] = config.client_secret
    return data
