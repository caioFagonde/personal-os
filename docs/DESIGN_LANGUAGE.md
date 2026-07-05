# DESIGN_LANGUAGE.md — "NOSTROMO" Design System (Nexus Prime visual revamp)

Direction pinned by the owner: retro-vintage old-school-futurism — *Alien / Alien: Isolation*
(Semiotic Standard, amber warnings, green phosphor terminals, Eurostile-extended headers),
*Routine* (CRT station consoles), *Fallout* (Pip-Boy mono readouts). Cassette futurism.
Constraint that outranks the vibe: **this is a daily-use instrument.** The aesthetic lives in
the chrome — bezels, labels, lamps, type. The data itself stays clinical, high-contrast, quiet.

Codename: **NOSTROMO**. One sentence: *every surface is a labeled instrument panel on a
working ship; nothing glows unless it's telling the truth.*

---

## 1. What dies

Glassmorphism dies: no blur, no 24px radii, no violet/cyan gradients, no floating translucency.
Depth now comes from machined bezels and 1px inset shadows, the way hardware does it.
Decorative motion dies. Fake shine dies. The existing honest-status vocabulary
(`dry_run`, `demo:true`, degraded) survives and gets *promoted* — it becomes the amber channel.

## 2. Palette — six named values + semantics

| Token | Hex | Name | Role |
|---|---|---|---|
| `--nexus-bg` | `#0B0E0A` | **Hull** | App background. Olive-black, faint vignette. |
| `--nexus-panel` | `#151B14` | **Bulkhead** | Panel fill. Raised variant `#1C2419`. |
| `--nexus-border` | `#33402F` | **Bezel** | 1px panel edges + hairline rules. |
| `--nexus-accent` | `#7DF2A2` | **Phosphor** | Interactive, links, OK lamps, selection. Glows (subtly). |
| `--nexus-warn` | `#F5A83C` | **Signal Amber** | Attention: approvals, dry-run, degraded, focus rings. |
| `--nexus-tape` | `#EAE4CF` | **Label Tape** | Engraved plate labels, key caps, wordmark. |

Supporting: text `#D9E8D4` (desaturated phosphor-white — readable in paragraphs, unlike raw
green), muted `#8FA68C`, alarm `#FF5449` (failures/conflicts only — if everything is red,
nothing is), hull-deep `#070906` (input wells, code blocks).

**Semantic law:** green = verified truth, amber = needs a human or honestly degraded,
red = broken, tape = chrome/labels. Never use phosphor decoratively on non-interactive,
non-status elements. This maps 1:1 onto the doctrine: `dry_run`/`demo:true`/`placeholder`
chips are always amber lamps — the aesthetic now *enforces* honesty.

Contrast (verified): text on Bulkhead ≈ 11.9:1, Phosphor on Bulkhead ≈ 9.6:1, Amber on Hull
≈ 8.1:1 — AA/AAA clean. Amber small text only at ≥12px / weight ≥500.

## 3. Typography — three faces, three jobs

| Role | Face | Rules |
|---|---|---|
| **Display** | Michroma | Page titles + wordmark ONLY. Uppercase, `letter-spacing: .08em`, 20–28px. The Microgramma/Eurostile-extended lineage of the Alien titles. Used sparingly or it becomes a costume. |
| **Data / labels / inputs / numbers / code** | IBM Plex Mono | The workhorse. Tabular numerals (`font-variant-numeric: tabular-nums`) so counters don't jitter. All eyebrows, chips, table cells, timestamps, terminal output. |
| **Body prose** | IBM Plex Sans | Paragraphs, descriptions, empty states. Shares Plex Mono's skeleton so the pairing is seamless. |

Self-hosted via `@fontsource/michroma`, `@fontsource/ibm-plex-mono`, `@fontsource/ibm-plex-sans`
(local-first: zero runtime CDN). Fallback stack: `'IBM Plex Mono', ui-monospace, monospace`.

Scale (mono-biased): 11 label / 13 data / 14 body / 16 emphasized / 22 panel title / 28 page title.

## 4. Materials & component anatomy

**Panel ("instrument module")** — replaces glass-card/glass-panel:
1px Bezel border, 6px radius max, Bulkhead fill, inner `box-shadow: inset 0 1px 0 rgba(234,228,207,.05)`
(machined top highlight). Top-left **label plate**: a small tab, Label Tape text on hull-deep,
uppercase mono 11px `.14em` tracking — this is the panel's name, engraved, not a floating heading.

**Indicator lamp** — replaces status chips: 8px square LED (not round — Semiotic Standard is
rectilinear) + mono uppercase label. Lamp colors follow the semantic law. Steady = state;
a 1.2s soft pulse is reserved for `running` states only.

**Key cap** — replaces buttons: flat Bulkhead-raised fill, 1px Bezel, 2px darker bottom edge;
`:active` removes the bottom edge and shifts content down 1px (the key depresses). Primary =
Phosphor fill with hull-dark text; danger = alarm only for destructive confirms. Mono uppercase
labels, 12px, `.1em`.

**Input well**: hull-deep fill, inset bezel, phosphor caret, amber 2px focus ring (offset 2px,
always visible — this is also the keyboard-focus style app-wide).

**Table / list**: hairline Bezel row rules, mono numerals right-aligned, hover = 2px phosphor
left bar (a selection cursor, not a row highlight).

**Empty / error / loading**: keep the Nexus* components, restyle. Empty states speak in the
ship's voice: plain, directive — "No captures in the inbox. Press C to capture." Errors state
what broke and the next action; they do not apologize.

## 5. Signature element — the System Line

One bold thing, spent here: a persistent 28px **terminal strip docked to the bottom of the
desktop shell** — the Nostromo access-terminal readout as furniture:

```
NEXUS/OS ▮ SYNC OK 2m · QUEUE 0 · BACKUP 11h ✓ · AGENTS 1 RUNNING · CONFLICTS 0        07:42
```

Every segment is **live** (existing endpoints: sync-health, offline queue, backup manifests,
agent jobs, conflicts) and navigates to its surface on click. Amber segment = needs you; red =
broken; it types itself once per session (150ms, skipped under `prefers-reduced-motion`).
On mobile it collapses to a single lamp in the header that opens the Continuity sheet.
This is the doctrine ("status is honest, no decorative widgets") made into the most
characteristic pixel on screen.

## 6. CRT layer — restraint spec

A **user toggle** (`ux_preferences.crt_mode`; default ON desktop, OFF mobile):
- Scanlines: 2px repeating gradient at **3% opacity, hull only** — never over panel text.
- Phosphor glow: `text-shadow: 0 0 6px rgba(125,242,162,.35)` on interactive green only.
- Vignette: radial, 2%.
- Power-on: one 300ms horizontal wipe per session.
- **No flicker, ever.** Flicker in a daily tool is hostile. `prefers-reduced-motion` disables
  the wipe, the pulse, and the System Line typing. All effects are one CSS class (`.crt-on`)
  so the toggle is trivial and testable.

Motion elsewhere: 120–160ms linear-ish steps (mechanical, like relays), state-change only.

## 7. Why this isn't the generic "hacker green terminal"

Named deliberately, because black+green is a known AI default: (a) **Label Tape ivory** as a
first-class chrome channel — warm, physical, printed; (b) **Signal Amber** as a semantic layer
bound to the existing dry-run/demo honesty vocabulary, not a decoration; (c) Michroma display
type used at Eurostile-extended proportions; (d) bezel-plate **panel anatomy** instead of flat
cards; (e) the System Line grounded in real endpoints. Remove any two of these and it regresses
to the default; they're load-bearing.

## 8. Implementation strategy (no page rewrites)

Everything already flows through `--nexus-*` variables and ~20 shared classes in `app.scss`.
The revamp ships as **one additive file**, `apps/web/src/css/nexus-crt.scss`, loaded *after*
`app.scss` (add to the `css` array in `quasar.config.ts`). It re-points the variables and
overrides the shared classes. `app.scss` itself is untouched — the phase-14 contract strings
(`.glass-card`, `color: var(--nexus-text)`, `background: linear-gradient`) stay intact, and
`.glass-card`'s *rendered* appearance becomes a bezel panel via the override layer.

Rollout order: theme layer → fonts (@fontsource) → System Line component (new, live-backed) →
lamp/keycap refinements on the 5 daily surfaces (Command Center, Capture, Tasks, Connectors,
Continuity) → `/ambient` gets the full-drama pass last (it may keep more glow than the work
surfaces). Quasar brand colors (`primary` etc.) re-mapped in `quasar.config.ts` to Phosphor/
Amber/Alarm so `q-btn color="primary"` etc. inherit automatically.

## 9. Contract tests (add in the same commit)

- `nexus-crt.scss` exists and is listed in `quasar.config.ts` css array after app.scss.
- Variables `--nexus-warn` and `--nexus-tape` defined; no `backdrop-filter` in nexus-crt.scss.
- Scanline opacity token ≤ 0.04; a `prefers-reduced-motion` block exists.
- SystemLine component fetches ≥3 live endpoints and renders no hardcoded metric values.
- Focus-visible style defined once, amber, ≥2px.
- CRT effects gated behind a `.crt-on` class toggled by a stored preference.

## 10. Do / Don't

**Do**: mono numerals everywhere numbers live · label plates on every panel · amber for anything
awaiting a human · empty states that name the key to press · 44px touch targets on mobile.
**Don't**: scanlines over text · red for non-failures · phosphor glow on prose · more than one
Michroma element per view · any metric that isn't a click away from its source list.

---

# REVISION 2 — "GREEN GLASS" (supersedes §§2–6 above for the screen surface)

Owner reviewed v1 against reference imagery (WarGames CRT, green-screen TV TUI, AMI BIOS on
GoldStar, Routine, Sevastolink) and correctly called it too modern — a dashboard wearing green.
Root cause diagnosis, so we never regress: **panels-on-a-background, font pairing, soft shadows,
and subtle radii are contemporary design-system idioms.** The references are terminal idioms.
v2 keeps v1's semantic law (green=truth, amber=needs-a-human, red=broken) and all restraint/
a11y rules, and replaces the material system.

## R2.1 The two layers

1. **Chassis** (desktop only): the app frame is a piece of hardware — aged plastic bezel,
   screws, vents, model badge, power LED, grime texture. Rendered once, in the shell, never
   inside content. Mobile is full-bleed glass (a handheld terminal, no chassis).
2. **Glass**: everything inside is ONE raster surface. Dark **green** glass (`#0A140C`,
   center-brightened radial to `#122117`), visible raster pitch (1px dark line every 3px,
   multiply — part of the rendering, not a 3% garnish), phosphor bloom
   (`text-shadow: 0 0 1px currentColor, 0 0 7px rgba(93,255,134,.45)`), specular arc, two or
   three dust specks. CRT corner curvature is the ONLY border-radius in the system.

## R2.2 One face. Hierarchy without font pairing

Single bitmap face everywhere: **VT323** (self-host `@fontsource/vt323`) at 18–20px body — or,
for full authenticity, the Px437/MxPlus faces from int10h.org's Ultimate Oldschool PC Font Pack
(CC BY-SA 4.0; fine for a personal system — attribute in Settings→About). Michroma is retired
from the working surfaces (permitted only in `/ambient` and the chassis badge).
Hierarchy is expressed the way terminals express it:
- **Inverse video** for menu bars, selected rows, key caps (`background: phosphor; color: glass`).
- **Brightness levels**: bright `#5DFF86` / dim `#2F9A55` / faint `#1A5C33`.
- **Box drawing**: panels are fieldset-style boxes with 1px dim borders and the title sitting
  ON the border (`─── PROJECT RADAR ───`). No fills, no shadows, radius 0.

## R2.3 Component idioms (replaces v1 anatomy)

| v1 | v2 |
|---|---|
| Instrument panel w/ label plate | Box-drawn region, legend on the border |
| Key-cap button | Inverse-video block, `[ CAPTURE ]` affordance; `:active` = brief brightness dip |
| Indicator lamp | Inverse tag (`HOLD`/`DRY`/`OK`) or bright/amber text — square, character-cell sized |
| System Line strip | **Function-key bar**: `F2 CAPTURE · F4 APPROVE·2 · F5 SYNC OK 2m · F7 CONFLICT·1 · F9 BACKUP 11h✓` — same live endpoints, now the F-key idiom; the keys actually work |
| Hero + subtitle | Terminal header line: `NEXUS/OS 1.0 · COMMAND DECK · THU 02 JUL · OPERATOR: OWNER` + `INTENTION>` line |
| Capture bar | A prompt: `CAPTURE> _` with block cursor |

## R2.4 Boot & motion

One BIOS-style self-test on session start (memory count, service checks with honest states —
`MODEL RUNTIME .... HEURISTIC MODE` in amber), ~2.5s, **any key skips**, `prefers-reduced-motion`
skips entirely, never re-plays within a session. Block cursor blinks at 1s steps. Nothing else
animates. Still no flicker — wear lives in the chassis texture, not in eye strain.

## R2.5 Legibility floor (non-negotiable with a bitmap face)

VT323 body ≥18px (it's a light face); bright-on-glass ≈ 13:1, dim-on-glass ≈ 5.5:1 (dim is for
secondary only, never body prose); raster lines at 1/3 pitch keep x-height rows clean; inverse
video for anything that must be scanned fast. Amber focus ring rule carries over. If any screen
is ever hard to read, the fix is brightness/inverse — never a second typeface.

## R2.6 Anti-slop contract tests (add with the reskin commit)

- Exactly one `font-family` declaration chain in the theme (single face on glass).
- Zero `box-shadow` and zero `border-radius` inside `.glass` content (chassis exempt).
- No `backdrop-filter` anywhere; no hex outside the token set.
- Raster overlay present with pitch ≤4px; boot sequence has a skip handler and a
  reduced-motion bypass.
- Function-key bar renders ≥5 live-backed segments and its F-keys have keydown handlers.
