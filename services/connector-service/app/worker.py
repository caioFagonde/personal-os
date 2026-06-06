from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg

from .backup import BackupManifest, create_backup_bundle
from .crypto import decrypt_text, encrypt_text
from .oauth import OAuthConfig
from .providers import (
    publish_ntfy,
    refresh_access_token,
    send_gmail,
    send_microsoft_mail,
    send_twilio_whatsapp,
    twilio_message_payload,
    upload_google_drive_file,
    upload_onedrive_file,
)


@dataclass(frozen=True)
class WorkerConfig:
    execute: bool
    limit: int = 25
    max_attempts: int = 5


@dataclass(frozen=True)
class WorkerTickResult:
    message_outbox: list[dict[str, Any]]
    automation_outbox: list[dict[str, Any]]
    notifications: list[dict[str, Any]]

    @property
    def count(self) -> int:
        return len(self.message_outbox) + len(self.automation_outbox) + len(self.notifications)


def retry_delay_sql() -> str:
    # Exponential-ish backoff, capped by CASE. Kept SQL-side so all workers behave identically.
    return """
    CASE
      WHEN attempts <= 0 THEN interval '1 minute'
      WHEN attempts = 1 THEN interval '5 minutes'
      WHEN attempts = 2 THEN interval '15 minutes'
      WHEN attempts = 3 THEN interval '1 hour'
      ELSE interval '6 hours'
    END
    """


class ConnectorWorker:
    def __init__(self, pool: asyncpg.Pool, *, root_dir: Path, backup_dir: Path, env: dict[str, str] | None = None):
        self.pool = pool
        self.root_dir = root_dir
        self.backup_dir = backup_dir
        self.env = env or dict(os.environ)

    async def tick(self, config: WorkerConfig) -> WorkerTickResult:
        msg = await self.drain_message_outbox(config)
        auto = await self.drain_automation_outbox(config)
        notes = await self.drain_notification_deliveries(config)
        return WorkerTickResult(message_outbox=msg, automation_outbox=auto, notifications=notes)

    async def drain_message_outbox(self, config: WorkerConfig) -> list[dict[str, Any]]:
        processed: list[dict[str, Any]] = []
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch(
                    """
                    SELECT id, channel, connector, recipient, subject, body, attempts, metadata
                    FROM message_outbox
                    WHERE status='queued' AND COALESCE(next_attempt_at, now()) <= now()
                    ORDER BY created_at ASC
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                    """,
                    config.limit,
                )
                for r in rows:
                    await conn.execute("UPDATE message_outbox SET status='sending', updated_at=now() WHERE id=$1", r["id"])
            for r in rows:
                outcome = await self._safe_process_message(dict(r), config=config)
                await self._complete_message(conn, UUID(str(r["id"])), outcome, config=config)
                processed.append({"id": str(r["id"]), **outcome})
        return processed

    async def _complete_message(self, conn: asyncpg.Connection, row_id: UUID, outcome: dict[str, Any], *, config: WorkerConfig) -> None:
        sent = outcome.get("status") in {"sent", "dry_run"}
        new_status = "sent" if sent else "failed"
        if not sent and outcome.get("attempts", 0) + 1 < config.max_attempts:
            new_status = "queued"
        if new_status == "queued":
            await conn.execute(
                f"""
                UPDATE message_outbox
                SET status='queued', attempts=attempts+1, next_attempt_at=now() + {retry_delay_sql()}, updated_at=now(), metadata=metadata || $2::jsonb
                WHERE id=$1
                """,
                row_id,
                json.dumps({"last_connector_result": outcome}),
            )
        else:
            await conn.execute(
                """
                UPDATE message_outbox
                SET status=$2, attempts=attempts+1, updated_at=now(), metadata=metadata || $3::jsonb
                WHERE id=$1
                """,
                row_id,
                new_status,
                json.dumps({"last_connector_result": outcome}),
            )
        await conn.execute(
            """
            INSERT INTO message_deliveries(outbox_id, provider_message_id, status, response)
            VALUES($1,$2,$3,$4::jsonb)
            """,
            row_id,
            outcome.get("provider_message_id"),
            outcome.get("status", "failed"),
            json.dumps(outcome),
        )

    async def _safe_process_message(self, row: dict[str, Any], *, config: WorkerConfig) -> dict[str, Any]:
        try:
            result = await self.process_message(row, execute=config.execute)
            result.setdefault("attempts", row.get("attempts", 0))
            return result
        except Exception as exc:
            return {"status": "failed", "provider": row.get("connector"), "message": str(exc), "attempts": row.get("attempts", 0)}

    async def process_message(self, row: dict[str, Any], *, execute: bool) -> dict[str, Any]:
        connector = row.get("connector") or ""
        if connector in {"whatsapp.twilio", "whatsapp.twilio_sandbox"}:
            payload = twilio_message_payload(
                to=row["recipient"],
                body=row["body"],
                from_=self.env.get("TWILIO_WHATSAPP_FROM"),
                messaging_service_sid=self.env.get("TWILIO_MESSAGING_SERVICE_SID") or None,
            )
            if not execute:
                return {"status": "dry_run", "provider": "twilio", "provider_message_id": None}
            result = await send_twilio_whatsapp(account_sid=self.env["TWILIO_ACCOUNT_SID"], auth_token=self.env["TWILIO_AUTH_TOKEN"], payload=payload)
            return {"status": "sent", "provider": "twilio", "provider_message_id": result.get("sid"), "response": result}
        if connector == "ntfy.local":
            if not execute:
                return {"status": "dry_run", "provider": "ntfy", "provider_message_id": None}
            result = await publish_ntfy(base_url=self.env["NTFY_BASE_URL"], topic=self.env["NTFY_TOPIC"], title=row.get("subject") or "Personal OS", message=row["body"])
            return {"status": "sent", "provider": "ntfy", "provider_message_id": result.get("id"), "response": result}
        if connector in {"gmail.oauth", "email.oauth_or_smtp"}:
            return await self._send_oauth_email(row, provider_preference=("google", "microsoft") if connector == "email.oauth_or_smtp" else ("google",), execute=execute)
        if connector == "microsoft.mail":
            return await self._send_oauth_email(row, provider_preference=("microsoft",), execute=execute)
        return {"status": "failed", "provider": connector, "message": f"unsupported connector: {connector}"}

    async def _send_oauth_email(self, row: dict[str, Any], *, provider_preference: tuple[str, ...], execute: bool) -> dict[str, Any]:
        if not execute:
            return {"status": "dry_run", "provider": provider_preference[0], "recipient": row["recipient"], "provider_message_id": None}
        for provider in provider_preference:
            token = await self._access_token(provider)
            if not token:
                continue
            if provider == "google":
                result = await send_gmail(access_token=token, to=row["recipient"], subject=row.get("subject") or "Personal OS", body=row["body"])
                return {"status": "sent", "provider": "gmail", "provider_message_id": result.get("id"), "response": result}
            if provider == "microsoft":
                result = await send_microsoft_mail(access_token=token, to=row["recipient"], subject=row.get("subject") or "Personal OS", body=row["body"])
                return {"status": "sent", "provider": "microsoft", "provider_message_id": None, "response": result}
        return {"status": "failed", "provider": "oauth-email", "message": "No active Google/Microsoft OAuth refresh token available"}

    async def _access_token(self, provider: str) -> str | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT ca.id account_id, ct.encrypted_token
                FROM cloud_accounts ca
                JOIN cloud_tokens ct ON ct.cloud_account_id = ca.id
                WHERE ca.provider=$1 AND ca.status='active' AND ct.token_type='oauth_refresh'
                ORDER BY ct.rotated_at DESC NULLS LAST, ct.created_at DESC
                LIMIT 1
                """,
                provider,
            )
        if not row:
            return None
        refresh_token = decrypt_text(bytes(row["encrypted_token"]))
        if provider == "google":
            cfg = OAuthConfig("google", self.env.get("GOOGLE_CLIENT_ID", ""), self.env.get("GOOGLE_CLIENT_SECRET", ""), self.env.get("GOOGLE_REDIRECT_URI", ""), tuple())
        else:
            cfg = OAuthConfig("microsoft", self.env.get("MICROSOFT_CLIENT_ID", ""), self.env.get("MICROSOFT_CLIENT_SECRET", ""), self.env.get("MICROSOFT_REDIRECT_URI", ""), tuple(), self.env.get("MICROSOFT_TENANT", "common"))
        token_response = await refresh_access_token(config=cfg, refresh_token=refresh_token)
        new_refresh = token_response.get("refresh_token")
        if new_refresh:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO cloud_tokens(cloud_account_id, token_type, encrypted_token, key_version, expires_at, rotated_at)
                    VALUES($1,'oauth_refresh',$2,$3,NULL,now())
                    """,
                    row["account_id"],
                    encrypt_text(new_refresh),
                    self.env.get("TOKEN_ENCRYPTION_KEY_VERSION", "local-v1"),
                )
        return token_response.get("access_token")

    async def drain_notification_deliveries(self, config: WorkerConfig) -> list[dict[str, Any]]:
        processed: list[dict[str, Any]] = []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, topic, title, message
                FROM notification_deliveries
                WHERE status='queued'
                ORDER BY created_at ASC LIMIT $1
                FOR UPDATE SKIP LOCKED
                """,
                config.limit,
            )
            for row in rows:
                try:
                    if not config.execute:
                        result = {"status": "dry_run", "provider": "ntfy", "topic": row["topic"]}
                    else:
                        result = await publish_ntfy(base_url=self.env["NTFY_BASE_URL"], topic=row["topic"] or self.env["NTFY_TOPIC"], title=row["title"], message=row["message"])
                    await conn.execute("UPDATE notification_deliveries SET status='sent', provider_response=$2::jsonb, sent_at=now() WHERE id=$1", row["id"], json.dumps(result))
                    processed.append({"id": str(row["id"]), "status": "sent", "response": result})
                except Exception as exc:
                    await conn.execute("UPDATE notification_deliveries SET status='failed', provider_response=$2::jsonb WHERE id=$1", row["id"], json.dumps({"error": str(exc)}))
                    processed.append({"id": str(row["id"]), "status": "failed", "message": str(exc)})
        return processed

    async def drain_automation_outbox(self, config: WorkerConfig) -> list[dict[str, Any]]:
        processed: list[dict[str, Any]] = []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, kind, payload, attempts
                FROM automation_outbox
                WHERE status='queued'
                ORDER BY created_at ASC LIMIT $1
                FOR UPDATE SKIP LOCKED
                """,
                config.limit,
            )
            for row in rows:
                try:
                    payload = dict(row["payload"] or {})
                    if row["kind"] == "notification":
                        await conn.execute(
                            """
                            INSERT INTO notification_deliveries(topic,title,message,status,provider_response)
                            VALUES($1,$2,$3,$4,$5::jsonb)
                            """,
                            payload.get("topic") or self.env.get("NTFY_TOPIC", "personal-os-dev"),
                            payload.get("title") or "Personal OS",
                            payload.get("message") or json.dumps(payload),
                            "queued" if config.execute else "sent",
                            json.dumps({"dry_run": not config.execute}),
                        )
                        await conn.execute("UPDATE automation_outbox SET status='dispatched', attempts=attempts+1, dispatched_at=now() WHERE id=$1", row["id"])
                        processed.append({"id": str(row["id"]), "status": "dispatched", "kind": row["kind"]})
                    else:
                        await conn.execute("UPDATE automation_outbox SET status='failed', attempts=attempts+1, last_error=$2 WHERE id=$1", row["id"], f"unsupported kind {row['kind']}")
                        processed.append({"id": str(row["id"]), "status": "failed", "kind": row["kind"]})
                except Exception as exc:
                    await conn.execute("UPDATE automation_outbox SET status='failed', attempts=attempts+1, last_error=$2 WHERE id=$1", row["id"], str(exc))
                    processed.append({"id": str(row["id"]), "status": "failed", "message": str(exc)})
        return processed

    async def upload_backup(self, manifest: BackupManifest, *, provider: str) -> dict[str, Any]:
        path = Path(manifest.archive_path)
        content = path.read_bytes()
        if provider == "google":
            token = await self._access_token("google")
            if not token:
                raise RuntimeError("No active Google OAuth refresh token available")
            result = await upload_google_drive_file(access_token=token, filename=path.name, content=content)
            remote_uri = f"google-drive://{result.get('id')}"
        elif provider == "microsoft":
            token = await self._access_token("microsoft")
            if not token:
                raise RuntimeError("No active Microsoft OAuth refresh token available")
            result = await upload_onedrive_file(access_token=token, filename=path.name, content=content)
            remote_uri = result.get("webUrl") or f"onedrive://{result.get('id')}"
        else:
            raise ValueError("provider must be google or microsoft")
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE backup_manifests SET remote_uri=$2, verified_at=now() WHERE backup_id=$1", manifest.backup_id, remote_uri)
        return {"provider": provider, "remote_uri": remote_uri, "response": result}


async def run_worker_forever(worker: ConnectorWorker, *, execute: bool, interval_seconds: float = 20.0, stop_event: asyncio.Event | None = None) -> None:
    event = stop_event or asyncio.Event()
    while not event.is_set():
        try:
            await worker.tick(WorkerConfig(execute=execute))
        except Exception:
            # Never let one provider outage kill the worker process.
            pass
        try:
            await asyncio.wait_for(event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass
