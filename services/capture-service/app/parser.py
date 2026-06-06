from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

CHANNEL_ALIASES = {
    "wa": "whatsapp",
    "zap": "whatsapp",
    "whatsapp": "whatsapp",
    "email": "email",
    "mail": "email",
    "ntfy": "ntfy",
}
KNOWN_TARGETS = {"secretary", "self", "me", "assistant", "team"}


@dataclass(frozen=True)
class CaptureCommand:
    raw: str
    target: str | None = None
    channels: list[str] = field(default_factory=list)
    due_at: datetime | None = None
    priority: str = "normal"
    tags: list[str] = field(default_factory=list)
    body: str = ""
    source: str = "note"

    @property
    def is_delegation(self) -> bool:
        return bool(self.target and self.target not in {"self", "me"})


def parse_capture_command(text: str, now: datetime | None = None) -> CaptureCommand:
    """Parse slash-command capture syntax without requiring an LLM.

    Examples:
        /secretary whatsapp email due today 17h high Ask João for the contract
        /task due tomorrow 09:30 #reading Finish chapter 3
    """
    now = now or datetime.now(timezone.utc)
    raw = text.strip()
    if not raw:
        return CaptureCommand(raw=text, body="")

    tokens = raw.split()
    target: str | None = None
    channels: list[str] = []
    due_at: datetime | None = None
    priority = "normal"
    tags: list[str] = []

    i = 0
    if tokens and tokens[0].startswith("/"):
        first = tokens[0][1:].strip().lower()
        i = 1
        target = "self" if first in {"task", "todo", "capture"} else first

    body_tokens: list[str] = []
    while i < len(tokens):
        tok = tokens[i]
        low = tok.lower().strip(",")
        if low in CHANNEL_ALIASES:
            normalized = CHANNEL_ALIASES[low]
            if normalized not in channels:
                channels.append(normalized)
            i += 1
            continue
        if low in {"high", "urgent", "low", "normal"}:
            priority = "high" if low == "urgent" else low
            i += 1
            continue
        if low.startswith("#") and len(low) > 1:
            tags.append(low[1:])
            i += 1
            continue
        if low == "to" and i + 1 < len(tokens):
            maybe_target = tokens[i + 1].lower().strip(",")
            if maybe_target in KNOWN_TARGETS or not target:
                target = maybe_target
                i += 2
                continue
        if low == "due":
            parsed, consumed = parse_due_tokens(tokens[i + 1 :], now)
            if parsed:
                due_at = parsed
                i += 1 + consumed
                continue
        body_tokens.extend(tokens[i:])
        break

    body = " ".join(body_tokens).strip()
    if target == "assistant":
        target = "secretary"
    return CaptureCommand(raw=raw, target=target, channels=channels, due_at=due_at, priority=priority, tags=tags, body=body)


def parse_note_frontmatter(frontmatter: dict, body: str, now: datetime | None = None) -> CaptureCommand:
    now = now or datetime.now(timezone.utc)
    note_type = str(frontmatter.get("type") or frontmatter.get("kind") or "").lower()
    target = frontmatter.get("to") or frontmatter.get("target")
    channels_raw = frontmatter.get("channels") or frontmatter.get("channel") or []
    if isinstance(channels_raw, str):
        channels_raw = [c.strip() for c in re.split(r"[, ]+", channels_raw) if c.strip()]
    channels = []
    for c in channels_raw:
        normalized = CHANNEL_ALIASES.get(str(c).lower(), str(c).lower())
        if normalized not in channels:
            channels.append(normalized)
    due_at = parse_due_value(frontmatter.get("due") or frontmatter.get("due_at"), now)
    priority = str(frontmatter.get("priority") or "normal").lower()
    tags = [str(t).lstrip("#") for t in frontmatter.get("tags", [])] if isinstance(frontmatter.get("tags"), list) else []
    inferred_target = str(target).lower() if target else ("secretary" if note_type == "delegation" else None)
    return CaptureCommand(raw=body, target=inferred_target, channels=channels, due_at=due_at, priority=priority, tags=tags, body=body.strip())


def parse_due_tokens(tokens: list[str], now: datetime) -> tuple[datetime | None, int]:
    if not tokens:
        return None, 0
    day_token = tokens[0].lower().strip(",")
    if day_token in {"today", "hoje"}:
        base = now
        consumed = 1
    elif day_token in {"tomorrow", "amanha", "amanhã"}:
        base = now + timedelta(days=1)
        consumed = 1
    else:
        value = parse_due_value(day_token, now)
        return (value, 1) if value else (None, 0)

    hour = 17
    minute = 0
    if len(tokens) > 1:
        match = re.match(r"^(\d{1,2})(?::(\d{2}))?h?$", tokens[1].lower().strip(","))
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            consumed += 1
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0), consumed


def parse_due_value(value: object, now: datetime) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip().lower()
    if text in {"today", "hoje"}:
        return now.replace(hour=17, minute=0, second=0, microsecond=0)
    if text in {"tomorrow", "amanha", "amanhã"}:
        return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    match = re.match(r"^(today|hoje|tomorrow|amanha|amanhã)\s+(\d{1,2})(?::(\d{2}))?h?$", text)
    if match:
        base = now + (timedelta(days=1) if match.group(1) in {"tomorrow", "amanha", "amanhã"} else timedelta())
        return base.replace(hour=int(match.group(2)), minute=int(match.group(3) or 0), second=0, microsecond=0)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def task_title_from_body(body: str, fallback: str = "Captured task") -> str:
    compact = re.sub(r"\s+", " ", body).strip()
    if not compact:
        return fallback
    sentence = re.split(r"(?<=[.!?])\s+", compact)[0]
    return sentence[:96].rstrip(" .") or fallback
