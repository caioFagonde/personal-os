from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SUPPORTED_CHANNELS = {"email", "whatsapp", "ntfy"}
EMAIL_CONNECTOR = "email.oauth_or_smtp"
NTFY_CONNECTOR = "ntfy.local"
WHATSAPP_CONNECTORS = {
    "cloud_api": "whatsapp.cloud_api",
    "meta_cloud_api": "whatsapp.cloud_api",
    "twilio": "whatsapp.twilio",
    "twilio_sandbox": "whatsapp.twilio_sandbox",
}
DEFAULT_CONNECTORS = {"email": EMAIL_CONNECTOR, "ntfy": NTFY_CONNECTOR}


@dataclass(frozen=True)
class ContactChannel:
    channel: str
    address: str
    verified: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Contact:
    key: str
    display_name: str
    channels: list[ContactChannel]


@dataclass(frozen=True)
class DelegationRule:
    target: str
    channels: list[str]
    requires_approval: bool = True
    allowed_hours: tuple[int, int] = (7, 21)
    fallback_channel: str | None = "email"


@dataclass(frozen=True)
class OutboxMessage:
    channel: str
    connector: str
    recipient: str
    subject: str | None
    body: str
    requires_approval: bool
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_channel(channel: str) -> str:
    value = channel.lower().strip()
    if value in {"wa", "zap"}:
        return "whatsapp"
    if value == "mail":
        return "email"
    return value


def normalize_whatsapp_provider(provider: str | None) -> str:
    value = (provider or "cloud_api").lower().strip().replace("-", "_")
    if value not in WHATSAPP_CONNECTORS:
        raise ValueError(f"unsupported WhatsApp provider: {provider}")
    return value


def connector_for_channel(channel: str, whatsapp_provider: str | None = None) -> str:
    normalized = normalize_channel(channel)
    if normalized == "whatsapp":
        return WHATSAPP_CONNECTORS[normalize_whatsapp_provider(whatsapp_provider)]
    connector = DEFAULT_CONNECTORS.get(normalized)
    if not connector:
        raise ValueError(f"unsupported channel: {channel}")
    return connector


def resolve_channels(requested: list[str], rule: DelegationRule) -> list[str]:
    raw = requested or rule.channels or []
    resolved: list[str] = []
    for c in raw:
        normalized = normalize_channel(c)
        if normalized not in SUPPORTED_CHANNELS:
            raise ValueError(f"unsupported channel: {c}")
        if normalized not in resolved:
            resolved.append(normalized)
    return resolved


def select_contact_channel(contact: Contact, channel: str) -> ContactChannel:
    normalized = normalize_channel(channel)
    for item in contact.channels:
        if normalize_channel(item.channel) == normalized:
            return item
    raise ValueError(f"contact {contact.key} does not have channel {channel}")


def build_delegation_messages(
    *,
    task_id: str,
    title: str,
    body: str,
    contact: Contact,
    rule: DelegationRule,
    requested_channels: list[str],
    source_note_id: str | None = None,
    whatsapp_provider: str | None = None,
) -> list[OutboxMessage]:
    channels = resolve_channels(requested_channels, rule)
    messages: list[OutboxMessage] = []
    for channel in channels:
        contact_channel = select_contact_channel(contact, channel)
        connector = connector_for_channel(channel, whatsapp_provider)
        subject = f"Delegated task: {title}" if channel == "email" else None
        message_body = render_secretary_message(title=title, body=body, task_id=task_id, source_note_id=source_note_id, channel=channel)
        messages.append(
            OutboxMessage(
                channel=channel,
                connector=connector,
                recipient=contact_channel.address,
                subject=subject,
                body=message_body,
                requires_approval=rule.requires_approval,
                metadata={"task_id": task_id, "target": contact.key, "source_note_id": source_note_id, "provider": connector},
            )
        )
    return messages


def render_secretary_message(*, title: str, body: str, task_id: str, source_note_id: str | None, channel: str) -> str:
    prefix = "Please handle this task:" if channel == "email" else "Task:"
    lines = [prefix, title.strip(), "", body.strip()]
    if source_note_id:
        lines.extend(["", f"Source note: {source_note_id}"])
    lines.append(f"Tracking ID: {task_id}")
    return "\n".join(line for line in lines if line is not None).strip()


def validate_official_connector(channel: str, connector_name: str, whatsapp_provider: str | None = None) -> bool:
    try:
        return connector_name == connector_for_channel(channel, whatsapp_provider)
    except ValueError:
        return False
