# Encrypted backups

Personal OS disables plaintext connector backup export. Set `BACKUP_ENCRYPTION_KEY` to a Fernet key and keep it outside source control. Losing the key makes encrypted archives unrecoverable.

`GET /api/connectors/backup/status` reports encryption, Azure Blob, and AWS S3 setup states without returning credential values. Azure requires an existing storage account/container and a container-scoped SAS limited to write/create/list. AWS requires an existing bucket and a bucket-scoped role or profile. Never use Azure account keys, AWS root credentials, or broad administrator policies.

Cloud resources are never provisioned automatically. Review provider pricing and create resources manually before configuration.
