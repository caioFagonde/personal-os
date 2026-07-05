# Big Picture Shell — Integration Guide

A full-bleed, console-style frontend shell for Personal OS, in the spirit of
Steam Big Picture Mode: a zero-dependency WebGL aurora background that
re-tints to whatever you're focused on, a carousel home screen with
keyboard / mouse / touch / **gamepad** navigation, and a glass "stage" that
hosts every existing page unchanged.

## What's in this drop

```
apps/web/
├── quasar.config.ts                                   (replaces) adds big-picture.scss
└── src/
    ├── App.vue                                        (replaces) full-bleed shell
    ├── css/big-picture.scss                           (new)      theme layer
    ├── design/bigpicture.ts                           (new)      per-module identity (accents, blurbs, actions)
    ├── composables/
    │   ├── useAmbience.ts                             (new)      shared accent/parallax/dim state
    │   └── useInputNav.ts                             (new)      keyboard + Gamepad API navigation
    ├── components/bigpicture/
    │   ├── AuroraBackground.vue                       (new)      WebGL shader background (no deps)
    │   ├── AmbientBar.vue                             (new)      brand · search · status · clock
    │   ├── ModuleCarousel.vue                         (new)      snap carousel with focus model
    │   ├── ModuleTile.vue                             (new)      module tile with accent art
    │   └── StagePanel.vue                             (new)      glass container for detail pages
    ├── pages/BigPictureHome.vue                       (new)      the new `/`
    └── router/routes.ts                               (replaces) `/` → BigPictureHome,
                                                                  legacy dashboard kept at /command-center
```

Nothing else changes. All 28 existing pages render inside the stage with
their current code; `CommandPalette`, `BottomNav` (mobile), and
`SystemStatusRibbon` are reused as-is.

## Install

1. Copy the files over the repo, preserving paths (only `App.vue`,
   `routes.ts`, and `quasar.config.ts` overwrite existing files — diff them
   first if you've changed them since this snapshot).
2. Optional but recommended — the display/mono faces:
   ```bash
   pnpm --filter web add @fontsource-variable/sora @fontsource/jetbrains-mono
   ```
   then uncomment the two `@use` lines at the top of
   `src/css/big-picture.scss`. Without them the shell falls back to
   Inter / system mono and still looks correct.
3. `pnpm --filter web dev` (or `make up`) and open `http://localhost:9000`.

## Controls

| Input            | Action                                      |
| ---------------- | ------------------------------------------- |
| ← →  / d-pad / left stick | Browse tiles (auto-repeat on hold) |
| ↑ ↓              | Switch between the featured row and the system strip |
| Enter / A        | Open the focused module                     |
| Esc / B          | Back to home from any page                  |
| ⌘/Ctrl+K / Start | Command palette                             |
| Mouse / touch    | Hover focuses, click opens, wheel & drag scroll the carousel |

Gamepads are detected via the Gamepad API; a "Controller connected" hint
appears bottom-right when one is active.

## How the pieces talk

- `useAmbience` is a tiny reactive store. The home screen (and the router,
  for deep links) calls `setAmbience(accent, accent2)`; the aurora shader
  tweens its two color uniforms toward those values every frame.
  `setDim(0.75)` is applied on detail pages so dense content stays readable.
- `useInputNav` merges keyboard and gamepad into one handler. The App shell
  registers one instance for global actions (back, palette); the home page
  registers another for spatial navigation. Right-stick / pointer movement
  feeds `setParallax`, which drifts the aurora field.
- `AuroraBackground` is ~150 lines of raw WebGL: one fullscreen triangle,
  one FBM fragment shader. It caps devicePixelRatio at 1.5 for TV/4K
  performance, renders a single still frame under `prefers-reduced-motion`,
  survives context loss, and falls back to a CSS gradient when WebGL is
  unavailable.

## Tuning

- **Module identity** — accents, hero blurbs, and quick actions all live in
  `src/design/bigpicture.ts`. Add a module there and it gets a tile, a hero,
  and an aurora hue for free (anything missing falls back to a muted slate).
- **Carousel geometry** — `--bp-tile-w`, `--bp-tile-w-sm`, `--bp-tile-gap`
  in `big-picture.scss`. The focused lane position is the `LANE` constant in
  `ModuleCarousel.vue` (0.16 = left sixth of the viewport, like Big Picture).
- **Shader mood** — band density, drift speed, star density, and the horizon
  glow are all plainly-named constants in `AuroraBackground.vue`'s fragment
  shader.

## Notes & known edges

- `color-mix()` is used in tile styling; it's supported everywhere the
  build target (es2022 browsers) is. If you must support older WebViews on
  mobile, replace those three usages with precomputed rgba values.
- The old Command Center dashboard is intact at `/command-center` and is
  the first quick action on the home hero, so nothing is lost while you
  decide its fate.
- E2E: `e2e/navigation.spec.ts` may assert on the old `/` layout — update
  selectors to `.bp-home` / `.bp-tile` where needed.
