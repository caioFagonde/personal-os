# Architecture

The system is a control plane plus specialized modules.

Control plane: `nexus-core`.

Responsibilities:

- authentication and device identity
- module registry and auto-discovery
- sync engine and append-only sync log
- event bus over NATS JetStream
- permissions and approvals
- file/artifact service over MinIO
- cloud connectors for Google and Microsoft OAuth
- notification gateway over ntfy/mobile local notifications
- audit log and observability

Specialized modules own UX and domain tables, but they do not own identity, permissions, sync, events, or secrets.
