# Phase 9 — Capture, Tasks, Delegation, Study Companion, and Analog-to-Digital

Phase 9 turns the system into an operational capture surface. It adds first-class tasks, secretary delegation, official-message outbox routing, and a study companion that can accept text, photos, files, and OCR hints.

## Zettelkasten sync status

Zettelkasten notes are already written as sync entities with `sync_strategy='crdt_text'` and a `sync_log` record. Phase 9 extends this by allowing the study companion and analog-capture pipeline to create Zettelkasten notes from text/photo/file captures.

## Fast capture syntax

```txt
/secretary whatsapp email due today 17h Reschedule dentist appointment and ask João for signed contract PDF.
/task due tomorrow 09:30 #reading Finish chapter 3.
```

Frontmatter also works:

```yaml
type: delegation
to: secretary
channels: [whatsapp, email]
priority: high
due: today 17:00
```

## Delegation policy

Email and WhatsApp messages are queued in `message_outbox`; connectors must use official APIs:

- WhatsApp: WhatsApp Business Cloud API.
- Email: Gmail API, Microsoft Graph, or configured SMTP fallback.

The service does not automate WhatsApp Web or browser scraping.

## Study companion

Inputs:

- pasted text
- uploaded local files
- images/photos/screenshots
- OCR hints/transcripts
- spatial coordinates where available

Outputs:

- Zettelkasten note candidate
- learning atoms
- study item / reading-list item
- lookup card
- popup note summary
- due-review schedule

## Analog-to-digital pipeline

```txt
image/audio/file/text → media classification → OCR/object detection adapter → summary → lookup queries → zettel + reading item + learning atoms → reminders
```

The default provider is deterministic and lightweight. Later providers can enable `ultralytics` YOLO, Tesseract, Whisper, or phone-side MLKit without changing the data model.

## Routines to schedule

| Routine | Cron | Purpose |
|---|---:|---|
| `study.due_reviews` | `*/20 * * * *` | Queue due review notifications. |
| `study.retention_rebalance` | `0 5 * * *` | Rebalance intervals from review history. |
| `study.daily_plan` | `30 6 * * 1-6` | Generate daily learning plan. |
| `analog.ocr_backlog` | `*/10 * * * *` | Process unparsed captures. |
| `analog.deep_lookup` | `*/15 * * * *` | Expand lookup cards through research. |
| `zettel.backlinks` | `*/30 * * * *` | Refresh backlinks and orphan report. |
| `ar.spatial_recall` | `*/5 * * * *` | Match current location/pose to spatial notes. |
| `tasks.followups` | `*/30 * * * *` | Remind delegated tasks without acknowledgement. |
| `sync.health` | `*/5 * * * *` | Detect sync lag/conflicts. |
| `backup.encrypted` | `0 3 * * *` | Encrypted backup. |

## Local run

```bash
make up-capture
make up-study-companion
make test-phase9
```
