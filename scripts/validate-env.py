#!/usr/bin/env python3
"""Validate dotenv configuration without exposing configured values."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


SECRET_MARKERS = ("SECRET", "TOKEN", "PASSWORD", "PRIVATE_KEY", "API_KEY", "AUTH_KEY", "CREDENTIAL")
PLACEHOLDER_RE = re.compile(r"^(?:<[^>]+>|your[-_ ].*|change[-_ ]?me|example)$", re.IGNORECASE)
PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")
AWS_REGION_RE = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-\d$")
AWS_ARN_RE = re.compile(r"^arn:(aws|aws-us-gov|aws-cn):[a-z0-9-]+:[a-z0-9-]*:\d{0,12}:.+$")
AZURE_CONNECTION_PARTS = {"DefaultEndpointsProtocol", "AccountName", "AccountKey", "EndpointSuffix"}


@dataclass(frozen=True)
class Finding:
    level: str
    key: str
    message: str


def parse_dotenv(path: Path) -> tuple[dict[str, str], list[Finding]]:
    values: dict[str, str] = {}
    findings: list[Finding] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            findings.append(Finding("error", f"line {line_number}", "expected KEY=VALUE syntax"))
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            findings.append(Finding("error", f"line {line_number}", "invalid variable name"))
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values, findings


def is_secret_key(key: str) -> bool:
    return any(marker in key.upper() for marker in SECRET_MARKERS)


def is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_RE.fullmatch(value.strip()))


def validate_url(value: str, *, redirect: bool = False) -> str | None:
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        return "must be a valid URL with a valid port"
    allowed_schemes = {"http", "https"} if redirect else {"http", "https", "postgres", "postgresql", "nats", "redis", "amqp", "amqps"}
    if parsed.scheme not in allowed_schemes or not parsed.hostname:
        return "must be an absolute URL with a supported scheme"
    if port is not None and not 1 <= port <= 65535:
        return "contains a port outside 1-65535"
    if redirect and (parsed.fragment or parsed.username or parsed.password):
        return "OAuth redirect URI must not contain credentials or a fragment"
    return None


def validate_value(key: str, value: str, *, example: bool = False) -> list[Finding]:
    upper = key.upper()
    if not value:
        return []
    if is_placeholder(value):
        if not example:
            return [Finding("error", key, "still contains a placeholder; complete guided setup")]
        return []

    message: str | None = None
    if upper.endswith("_PORT") or upper == "PORT":
        if not value.isdigit() or not 1 <= int(value) <= 65535:
            message = "must be an integer from 1 to 65535"
    elif "TWILIO" in upper and "WHATSAPP" in upper and ("FROM" in upper or "SENDER" in upper):
        if not value.startswith("whatsapp:") or not PHONE_RE.fullmatch(value.removeprefix("whatsapp:")):
            message = "must use whatsapp:+<E.164 number> format"
    elif "PHONE" in upper or upper.endswith(("_TO_NUMBER", "_FROM_NUMBER")):
        if not PHONE_RE.fullmatch(value):
            message = "must be an E.164 phone number such as +15551234567"
    elif "REDIRECT_URI" in upper or "CALLBACK_URI" in upper:
        message = validate_url(value, redirect=True)
    elif upper.endswith(("_URL", "_URI", "_ENDPOINT")):
        message = validate_url(value)
    elif upper in {"AWS_REGION", "AWS_DEFAULT_REGION"} and not AWS_REGION_RE.fullmatch(value):
        message = "must be an AWS region such as us-east-1"
    elif upper.endswith("_ARN") and upper.startswith("AWS_") and not AWS_ARN_RE.fullmatch(value):
        message = "must be a valid AWS ARN"
    elif upper == "AZURE_STORAGE_CONNECTION_STRING":
        parts = {part.split("=", 1)[0] for part in value.split(";") if "=" in part}
        if not ({"UseDevelopmentStorage"} <= parts or AZURE_CONNECTION_PARTS <= parts):
            message = "must be an Azure storage connection string"
    elif upper == "AZURE_TENANT_ID" and value.lower() != "common":
        try:
            import uuid

            uuid.UUID(value)
        except ValueError:
            message = "must be a UUID or common"

    return [Finding("error", key, message)] if message else []


OPTIONAL_GROUPS = {
    "Google OAuth": ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"),
    "Microsoft OAuth": ("MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET", "MICROSOFT_REDIRECT_URI"),
    "Twilio WhatsApp": ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM"),
    "AWS": ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"),
}


def validate_values(values: dict[str, str], *, example: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    for key, value in values.items():
        findings.extend(validate_value(key, value, example=example))
    if not example:
        for label, keys in OPTIONAL_GROUPS.items():
            configured = [key for key in keys if values.get(key) and not is_placeholder(values[key])]
            missing = [key for key in keys if not values.get(key) or is_placeholder(values[key])]
            if configured and missing:
                findings.append(Finding("warning", label, f"optional setup is incomplete; configure: {', '.join(missing)}"))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".env", help="dotenv file to validate")
    parser.add_argument("--example", metavar="PATH", help="validate a distributable example file")
    args = parser.parse_args(argv)
    path = Path(args.example or args.path)
    if not path.is_file():
        print(f"ERROR {path.name}: file not found; run guided setup", file=sys.stderr)
        return 1
    values, findings = parse_dotenv(path)
    findings.extend(validate_values(values, example=bool(args.example)))
    for finding in findings:
        print(f"{finding.level.upper()} {finding.key}: {finding.message}")
    errors = sum(item.level == "error" for item in findings)
    warnings = sum(item.level == "warning" for item in findings)
    print(f"Config validation: {errors} error(s), {warnings} warning(s); values were not printed.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
