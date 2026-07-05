# ROADMAP_NEXUS_PRIME.md

Maturity ladder applied to the whole product. Each level has a **demo you can run** and a **gate** that must be true before advancing. Current overall position: **between L1 and L3 depending on feature** (see FEATURE_REALITY_MATRIX).

| Level | Name | Demo | Gate (all must hold) | Phase |
|---|---|---|---|---|
| **L0** | Scaffold | Repo maps to docs | Honest labels on every placeholder | done (mostly honest today) |
| **L1** | Imports/builds | CI green: pytest, vitest, typecheck, compose config | No missing-file test failures; no PII; archive hygiene | **Phase A** |
| **L2** | Real local data flow | Capture → task → project → search, all persisted | Graph registry live; embeddings real-or-honestly-degraded | Phase B |
| **L3** | Tested vertical slices | Playwright loop test passes; per-slice behavioral tests | Every primary surface backed by live endpoints; contract tests updated, green | Phase B/C |
| **L4** | PC/mobile continuity | Edit same task offline on phone + desktop, reconcile in UI | Queue v2, share-target capture, pairing enforced, per-device sync health visible | Phase E |
| **L5** | Obsidian + backup | Edit project README in Obsidian → merged in app; restore drill passes from encrypted remote snapshot | 3-way merge w/ conflict UI; 3-2-1 backup verified; drill < 35 d | Phases D+E |
| **L6** | Agentic harness | Agent job: plan → approval → tools → artifact → Obsidian report | No unapproved tool executes (test-proven); budgets enforced; evals lane in CI | Phase F |
| **L7** | Portfolio-grade UX | 10-minute unscripted walkthrough with zero dead ends or fake data | Palette complete; a11y/keyboard audit; no decorative metrics; ambient mode live-bound | Phase G |
| **L8** | Daily-use RC | Owner runs it as primary system for 7 consecutive days | Dogfood checklist: 0 data-loss events, <2 blocking bugs, backup+drill green, capture P50 < 3 s from pocket-to-saved | Phase G exit |

## Per-feature target levels for v1.0 (RC)

| Feature | Now | v1.0 target |
|---|---|---|
| Capture (text) | L3 | L4 |
| Capture (voice/screenshot/file/URL) | L0/missing | L4 (voice honest-degraded w/o whisper) |
| Tasks | L3 | L5 (Obsidian task lines) |
| Projects / DailyState / Decisions | missing | L5 |
| Notes/Zettel | L2 | L5 |
| Research | L3 | L3 (+ promote-to-note) |
| Knowledge graph | missing | L3 |
| Embedding search | L0 | L2 (real or labeled-lexical) |
| Obsidian sync | L1 (export-only) | L5 |
| Agent harness | missing | L6 |
| Coding agent | L3 (dry-run) | L6 |
| Automations | L3 | L6 (3 real recipes) |
| Digital twin | L3 (engine) | L3 + signal ingestion from graph |
| Sync/offline | L2 | L4 |
| Backup/restore | L2 (local) | L5 (3-2-1, encrypted, drilled) |
| Mobile shell | L1 | L4 |
| Desktop shell | L1 | L4 (hotkey, tray) |
| Connectors | L2/L3 mixed | keep; Notion/Trello stay honest dry-run unless needed |
| Geospatial / AR / Study | L2 | park at L2/L3 under "Labs" — do not block RC |
| Intelligence | L2 untested | L3 (tests + briefing recipe) |
| CI/CD | missing in archive | L1 from Phase A, evals lane by F |

## Sequencing rationale

Hygiene first because every later claim depends on a trustworthy test suite. Graph+embeddings second because Obsidian mapping, palette search, context packs, and twin signals all consume it. UX IA before Obsidian/harness so new features land in their final homes. Continuity before harness so approvals can reach the phone. Harness before polish so the RC demo includes the flagship capability.

## Explicit non-goals for v1.0

Multi-user/auth federation; Notion/Trello live writes; AR device pipeline; cloud-hosted deployment; LLM-as-judge evals; iOS (Android first, per owner's devices).
