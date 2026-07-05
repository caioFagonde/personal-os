# UX_PRODUCT_SPEC.md — Nexus Prime Product & Interface Specification

## Product stance

Nexus Prime is a **calm, high-density personal command surface**, not a dashboard zoo. Every pixel must be backed by a real query or a real action. Doctrine:

1. **Capture is never more than one gesture away** (global hotkey on desktop, share-target + FAB on mobile, `c` in web).
2. **The default screen answers "what now?"** — not "what modules exist?"
3. **Status is honest**: demo/dry-run/degraded states are labeled with the existing `demo:true` / `status:dry_run` vocabulary, surfaced as amber chips, never hidden.
4. **Ops ≠ daily use**: certification, release-center, live-stack, initial-readiness move under `/ops`, reachable but out of daily nav.
5. **No decorative metrics.** A number appears only if (a) it's queryable live and (b) tapping it navigates to the underlying list.

## Resolving the two-home conflict (R-03)

- **`/` → Command Center** (daily cockpit). This restores the phase-14 contract.
- **Big Picture** becomes `/ambient` — an optional, gorgeous, TV/idle "overview mode" launched from the Command Center ("Enter ambient mode") and from Tauri fullscreen. Its module badges must bind to live health/queue counts or be removed. Contract tests updated in the same commit that lands this.

## Information architecture — 13 primary surfaces

| # | Surface | Route | Content (all live-backed) |
|---|---|---|---|
| 1 | **Home / Command Center** | `/` | Today strip (date, intention from DailyState, top-3 focus tasks), Capture bar (inline quick capture), Attention row (pending approvals, sync conflicts, failed agent jobs, backup age — each a chip that navigates), Project radar (active projects w/ momentum = tasks closed 7d), Agent activity feed. |
| 2 | **Capture Inbox** | `/capture` | Unified inbox of CaptureItems (text/voice/screenshot/file/url) with triage actions: → Task, → Note, → Project idea, → Source, → Person, Archive. Keyboard-first triage (j/k/t/n/a). |
| 3 | **Today / Focus** | `/today` | DailyState editor (intention, review, close-day ritual), due+overdue tasks, habit/routine checklist, calendar events, "shutdown" flow writing the Obsidian daily note. |
| 4 | **Projects** | `/projects`, `/projects/:slug` | Project list w/ status + momentum; detail = README (note), open tasks, decisions, sources, artifacts, agent runs, portfolio-case link. "Context pack" button (see harness spec). |
| 5 | **Tasks** | `/tasks` | Existing page upgraded: saved filters (inbox/today/delegated/blocked/by-project), bulk triage, delegation flow with approval state. |
| 6 | **Notes / Obsidian** | `/notes` | Zettel list + backlink panel, vault sync status per note (synced/pending/conflict), "open in Obsidian" (obsidian:// URI), daily-notes timeline. |
| 7 | **Research** | `/research` | Existing ingestion + search; add source reader w/ chunk highlights and "promote chunk → note/task". |
| 8 | **Agents** | `/agents` | AgentJob queue (all kinds incl. coding), plan viewer, approval inbox, run transcripts, artifacts, evals tab. Supersedes `/coding-agent` (redirect). |
| 9 | **Automations** | `/automation` | Existing workflows + run history; add "recipes" gallery (real, shippable ones only: morning briefing, inbox sweep, backup verify). |
| 10 | **Digital Twin** | `/twin` | Timeline, goals, recommendations w/ accept/dismiss feeding preference_signals. Only user-entered or explicitly derived data; every inference labeled with its source. |
| 11 | **Connectors** | `/connectors` | Marketplace layout kept, but restore per-provider setup instructions, ntfy help, Tailscale IP (fixes phase-15 contract), plus health + last-worker-run columns. |
| 12 | **Backup & Sync** | `/continuity` | Merges backup-restore, sync-health, conflicts, offline-queue, device-pairing into tabs. Headline = four health tiles: Last backup (age + verified?), Remote copy (rclone status), Sync lag per device, Conflicts pending. |
| 13 | **Settings** | `/settings` | Vault path (validated via existing endpoint), model runtime providers, agent policies, theme, danger zone. Every setting explains its effect in one sentence. |

Secondary: `/ambient` (Big Picture), `/ops/*` (certification, release, live-stack, readiness), `/modules/:id` (kept), `/study`, `/study-companion`, `/zettelkasten` (folded into Notes over time), `/geospatial`, `/ar-memory` (labs section under Projects nav group "Labs").

## Command palette (rebuild — currently a 44-line stub)

`Ctrl/Cmd-K` everywhere. Sections, in ranked order:
1. **Actions**: "Capture…", "New task…", "Start agent job…", "Approve pending (n)", "Close the day", "Run backup", "Open vault".
2. **Objects**: hybrid search over `objects` (trigram now, vector when embeddings land) — tasks, notes, projects, sources, people.
3. **Navigate**: the 13 surfaces.
4. **Ops** (prefixed `>`): doctor, certification, release.
Implementation: palette queries `GET /api/graph/search`; actions dispatch through the same client functions pages use (no duplicated logic). Fully keyboard operable; `Enter` executes, `Ctrl-Enter` executes-and-keeps-open for triage bursts.

## Mobile UX (capture-first)

- Bottom nav (5): Capture, Today, Tasks, Inbox, More.
- **App opens on Capture** if last session > 30 min ago, else restores last surface.
- Capture screen: big text field, mic button (voice → local queue → whisper when reachable), camera/screenshot attach, share-target lands here pre-filled.
- Everything queue-first: capture writes locally, syncs opportunistically; UI shows "queued (n)" chip, never blocks on network.
- One-thumb triage: swipe right = task, left = archive, hold = full triage sheet.

## Desktop UX (command-center)

- Tauri: global hotkey `Ctrl+Shift+Space` → floating quick-capture window (Tauri command + always-on-top mini window); tray icon with capture/approvals badge.
- Keyboard: `c` capture, `g` then letter = go-to surface, `.` = actions on focused row.
- Project radar and Agent feed side-by-side at ≥1440px (already the min window is 1024).

## Visual system — GREEN GLASS (docs/DESIGN_LANGUAGE.md Revision 2, shipped)

The working surfaces render as one sheet of dark green glass (`#0A140C`), single bitmap face
(VT323, self-hosted), hierarchy via inverse video + brightness levels + box drawing — no
shadows, no radii, no backdrop-filter on the glass. The theme ships as one additive override
layer, `apps/web/src/css/nexus-crt.scss`, loaded after `app.scss` in `quasar.config.ts`
(`app.scss` untouched; phase-14 contract strings intact). Quasar brand colors are remapped
(primary `#5DFF86`, warning `#FFB347`, negative `#FF6B5E`, dark `#0A140C`) so stock Quasar
components inherit the semantic law: green = verified truth, amber = needs-a-human/degraded,
red = broken.

Shipped R2 furniture:
- **Function-key bar** (`FKeyBar.vue`, `.fkey-bar`, desktop only): F2 CAPTURE · F4 AGENTS ·
  F5 SYNC · F6 QUEUE · F7 CONFLICT · F9 BACKUP. Every segment is live-backed (sync-health,
  offline queue, backup manifests, coding-agent jobs, sync conflicts), navigates on click,
  and the F-keys work via a real keydown handler. No hardcoded metric values.
- **BIOS boot** (`BiosBoot.vue`): one self-test per session, any key skips, `prefers-reduced-motion`
  bypasses entirely; service lines come live from `/api/control/health` (fallback `/health`) —
  states are OK/DEGRADED/DOWN as reported, never invented.
- **Anti-slop contract tests** (`apps/web/src/design/green-glass.test.ts`, §R2.6): single
  font-family chain, zero box-shadow/border-radius/backdrop-filter on glass, raster pitch ≤4px,
  amber ≥2px focus-visible ring, reduced-motion block, live-backed FKeyBar/BiosBoot invariants.

Base rules carry over: 4px spacing grid, motion only on state change, density toggle in
ux_preferences. Big Picture aesthetic reserved for `/ambient` (may keep more glow).

## Empty, loading, degraded states

Reuse `NexusEmptyState`, `NexusLoadingState`, `NexusErrorBanner` everywhere (they exist — enforce via contract test). Degraded chip pattern: `⚠ heuristic mode` on OCR results, `dry-run` on connector actions, `placeholder` never shown to user without an enable-me CTA ("Install embedding model to unlock related notes").

## UX contract tests (update, don't delete)

- `/` renders CommandCenterPage; `/ambient` renders BigPictureHome.
- ConnectorsPage contains setup instructions per provider, ntfy help, Tailscale IP.
- Every primary surface fetches at least one live endpoint and renders NexusErrorBanner on failure.
- No page imports static demo data outside `/ambient` copy text.
- Palette: opens on Ctrl-K, executes "New task" end-to-end (vitest + one Playwright spec).
