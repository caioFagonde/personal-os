# UI Foundation Report

## Root cause / diagnosis

1. **Broken icon text artifacts** (`arrow_drop_down` etc.): Quasar's `iconSet` defaulted to Material Icons but only `mdi-v7` font was loaded. All internal Quasar icons (dropdown arrows, stepper dots, expansion carets) rendered as raw text.

2. **Unreadable white surfaces in dark theme**: `app.scss` covered `q-card`, `q-table`, `q-field`, and `q-menu`, but missed `q-stepper`, `q-tabs`, `q-separator`, `q-chip`, `q-toggle`, `q-expansion-item`, `q-list--bordered`, `q-timeline`, `q-slider`, and `q-dialog`. These components rendered with Quasar's default light-theme backgrounds.

3. **Horizontal overflow potential**: `.page-shell` constrained width but did not clip overflow. Tables and code blocks could push content wider.

4. **Inconsistent page structure**: ConnectorsPage, StudyCompanionPage, CommandCenterPage, and OnboardingPage used raw `hero-panel` markup instead of the shared `NexusPageHero` component. No shared loading or error banner components existed.

## Files changed

| File | Change |
|------|--------|
| `apps/web/quasar.config.ts` | Set `iconSet: 'mdi-v7'`, added `Dark` plugin, added `nexus-dark.scss` to css array |
| `apps/web/src/css/nexus-dark.scss` | **New** — dark theme overrides for stepper, tabs, separator, chips, toggle, expansion items, lists, timeline, slider, dialog, inner-loading, buttons, file input, badges; overflow-x hidden on page-shell |
| `apps/web/src/components/NexusLoadingState.vue` | **New** — shared loading spinner with optional message |
| `apps/web/src/components/NexusErrorBanner.vue` | **New** — shared error banner with dismiss |
| `apps/web/src/components/NexusPageHero.vue` | Changed actions slot to use flex-wrap layout for proper button wrapping |
| `apps/web/src/pages/OnboardingPage.vue` | Rewritten to use `NexusPageHero`, improved stepper UX with icons and descriptions |
| `apps/web/src/pages/ConnectorsPage.vue` | Converted raw hero-panel to `NexusPageHero` |
| `apps/web/src/pages/StudyCompanionPage.vue` | Converted raw hero-panel to `NexusPageHero` |
| `apps/web/src/pages/CommandCenterPage.vue` | Converted raw hero-panel to `NexusPageHero`, removed scoped quick-actions style |

## Tests run and results

| Test | Result |
|------|--------|
| `python3 -m pytest tests -q` | 187 passed, 3 failed (pre-existing: missing release scripts), 2 skipped |
| `./scripts/check-secrets.sh` | No secrets detected |
| `pnpm --dir apps/web build` | Build succeeded (Node 22 required) |

## Acceptance criteria status

| Criterion | Status |
|-----------|--------|
| No unreadable white cards/forms in dark theme | **Pass** — nexus-dark.scss covers all uncovered Quasar components |
| No broken icon text artifacts such as `arrow_drop_down` | **Pass** — `iconSet: 'mdi-v7'` in quasar config |
| No global horizontal overflow on core pages | **Pass** — `overflow-x: hidden` on `.page-shell`, table containers have `overflow-x: auto` |
| Primary buttons visible and aligned | **Pass** — button glow shadows added, dark text on primary ensured |
| Core pages use consistent Nexus components | **Pass** — all 9 focus pages use `NexusPageHero` and `NexusEmptyState` |
| Shared loading/empty/error states exist | **Pass** — `NexusLoadingState`, `NexusErrorBanner`, and `NexusEmptyState` available |

## Remaining risks

1. **Visual verification blocked**: No browser available to visually confirm dark theme rendering. Build passes but pixel-level issues may remain.
2. **`app.scss` locked**: Could not edit the main stylesheet directly; all overrides are additive via `nexus-dark.scss`. Some `!important` cascading may need tuning if app.scss is later changed.
3. **DigitalTwinPage**: Uses `glass-panel` instead of `glass-card` — styling works but is inconsistent with other pages. Not in the focus-first list.
4. **Node version**: Build requires Node 22.22.0+; CI/Docker must match.

## Suggested follow-up tasks

1. **Visual QA**: Run dev server, open each page, screenshot dark theme on desktop and mobile viewport.
2. **Adopt shared components**: Migrate per-page error banners to `NexusErrorBanner` and loading states to `NexusLoadingState` across all pages.
3. **DigitalTwinPage consistency**: Convert from `glass-panel` to `glass-card` pattern.
4. **InitialVersionReadinessPage**: Add `NexusPageHero` and proper styling.
5. **ModulePage**: Add proper page structure beyond the minimal shell.
