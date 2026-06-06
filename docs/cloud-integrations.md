# Cloud integrations

Google and Microsoft integrations use explicit OAuth authorization only.

Google adapters:

- Drive file import/export
- Calendar event sync
- Contacts read, if authorized
- Gmail hooks only after explicit user authorization

Microsoft adapters:

- OneDrive import/export
- Outlook Calendar sync
- Contacts read, if authorized
- Outlook mail hooks only after explicit authorization

Token policy:

- refresh tokens are never logged
- refresh tokens are encrypted before storage in `cloud_tokens.encrypted_token`
- every remote write emits an `audit_log` row
- destructive operations require an `approvals` row
