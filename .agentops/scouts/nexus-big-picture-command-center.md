# Scout Report: Nexus Big Picture Command Center Refactor

**Task:** `nexus-big-picture-command-center` — Cinematic Command Center and shell layout refactor  
**Scout role:** Read-only architecture assessment  
**Date:** 2026-06-08  
**Status:** Ready for implementation

---

## Executive Summary

The Personal OS Command Center (root dashboard at `/`) is currently a **clean module-card grid** but lacks the **cinematic, cockpit-like UX** described in the Big Picture vision. The refactor requires:

1. **Module launcher carousel** (horizontal scrolling, keyboard nav, snap alignment)
2. **Three operational rails** (recent work, daily actions, system status)
3. **Keyboard-friendly affordances** (arrow keys, Tab, focus rings)
4. **Mobile card-first layout** (bottom sheet friendly, large tap targets)
5. **Readable typography & icon clarity** (no unreadable text overlap)

**Current state:** ✅ Foundation solid (dark theme, glass cards, responsive grid); ⚠️ Missing carousel component, needs layout restructure

**Estimated effort:** 3–5 days (carousel component, CommandCenterPage refactor, mobile testing)

---

## Relevant Files

### Current Command Center Implementation
| File | Type | Lines | Purpose | Status |
|------|------|-------|---------|--------|
| `apps/web/src/pages/CommandCenterPage.vue` | Page | 262 | Root dashboard | ⚠️ Needs refactor |
| `apps/web/src/components/NexusPageHero.vue` | Component | 20 | Hero header panel | ✅ Reusable |
| `apps/web/src/components/NexusModuleCard.vue` | Component | 45 | Module info card | ✅ Reusable |
| `apps/web/src/components/MetricCard.vue` | Component | 17 | Metric display | ✅ Reusable |
| `apps/web/src/components/SystemStatusRibbon.vue` | Component | 28 | Sync/health status | ✅ Reusable |
| `apps/web/src/components/BottomNav.vue` | Component | 12 | Mobile nav | ✅ Reusable |
| `apps/web/src/components/CommandPalette.vue` | Component | 45 | Cmd+K search | ✅ Reusable |
| `apps/web/src/router/routes.ts` | Config | 60 | Page routing | ✅ Complete |
| `apps/web/src/css/app.scss` | Stylesheet | 436 | Global dark theme | ✅ Complete |
| `apps/web/src/services/api.ts` | Service | — | API client | ✅ Reusable |
| `apps/web/src/services/platform.ts` | Service | — | Device detection | ✅ Reusable |

### Related Pages (Sidebar Navigation)
| Page | Route | Module ID | Status |
|------|-------|-----------|--------|
| Capture | `/capture` | capture | ✅ Works |
| Tasks | `/tasks` | tasks | ✅ Works |
| Study Companion | `/study-companion` | study-companion | ✅ Works |
| Zettelkasten | `/zettelkasten` | zettelkasten | ✅ Works |
| Connectors | `/connectors` | connectors | ✅ Works |
| Sync Health | `/sync-health` | sync-health | ✅ Works |
| Digital Twin | `/digital-twin` | digital-twin | ✅ Works |
| Coding Agent | `/coding-agent` | coding-agent | ✅ Works |
| Research | `/research` | research | ✅ Works |

### Design System & Styling
| File | Type | Status | Key Classes |
|------|------|--------|-------------|
| `apps/web/src/css/app.scss` | Stylesheet | ✅ Complete | `.glass-panel`, `.glass-card`, `.hero-panel`, `.action-grid`, `.module-grid`, `.section-heading` |
| `apps/web/src/css/nexus-dark.scss` | Overrides | ✅ Complete | Dark mode for Quasar components |
| `apps/web/src/design/tokens.ts` | Config | ✅ Complete | Navigation, module definitions, status mappings |
| `apps/web/src/App.vue` | Root | ✅ Complete | Layout shell (header, drawer, page-container, bottom-nav) |

### Test Files
| File | Type | Coverage |
|------|------|----------|
| `apps/web/src/design/tokens.test.ts` | Unit | Navigation token parsing |
| `apps/web/src/services/platform.test.ts` | Unit | Platform detection (desktop/mobile) |
| `apps/web/src/services/api.test.ts` | Unit | API client mocking |

---

## Current CommandCenterPage Structure

### Today Section (Capture, Tasks, Digital Twin)
```vue
<NexusPageHero> + <q-btn> quick actions (6 buttons)
       ↓
<MetricCard> grid (4 cards: Modules, API, Connectors, Tasks)
       ↓
<ModuleCard> grid - "Today" section (3 cards)
       ↓
<ModuleCard> grid - "Knowledge" section (3 cards)
       ↓
<ModuleCard> grid - "Operations" section (3 cards)
       ↓
<ModuleCard> grid - "Development" section (2 cards)
       ↓
<q-item> list - "Installed modules" registry (renders health badges)
```

### Issues with Current Design
1. ❌ **No carousel** — module launcher is static grid (not "Big Picture" cinematic)
2. ❌ **Vertical scrolling only** — "Today" section should be a horizontal carousel
3. ❌ **No recent-work rail** — no visibility into recent captures, edits, or completions
4. ❌ **No daily-actions rail** — no "next 3 actions" or "due today" section
5. ❌ **No keyboard shortcuts** — arrow keys don't navigate between rails
6. ❌ **Mobile overflow risk** — ModuleCard grid may break at very small widths
7. ⚠️ **Status badge contrast** — Some status colors may be unclear on glass backgrounds

---

## Implementation Points

### 1. Create NexusCarousel Component (HIGH PRIORITY)

**File:** `apps/web/src/components/NexusCarousel.vue`

**Purpose:** Horizontal snap-scrolling container with keyboard navigation (arrow keys, Tab)

**Props:**
```typescript
{
  items: any[],              // Array of items to render
  itemKey?: string,          // Key prop for v-for
  gap?: number,              // Spacing between items (default: 16px)
  hideControls?: boolean,    // Hide left/right arrow buttons
  label?: string,            // Optional section heading
  itemWidth?: string,        // CSS width per item (default: auto)
  showFocusRing?: boolean,   // Show focus ring on keyboard nav
}
```

**Slots:**
```vue
<template #default="{ item, index }">
  <!-- Rendered for each item -->
</template>

<template #label>
  <!-- Optional heading override -->
</template>
```

**Behavior:**
- Horizontal scroll with CSS snap alignment
- Left/right arrow buttons (desktop only)
- Keyboard navigation: `→` next item, `←` previous item, `Home`/`End`
- Touch swipe support (momentum scroll)
- Focus-ring visible on keyboard focus (accessibility)
- Desktop: show scroll controls; Mobile: hide controls, allow swipe
- Ensure items don't cause horizontal page overflow

**CSS Classes to Add:**
```scss
.nexus-carousel {
  overflow-x: auto;
  scroll-behavior: smooth;
  scroll-snap-type: x mandatory;
  padding-right: 0;  // No right overflow
  
  &::-webkit-scrollbar {
    display: none;  // Hide scrollbar
  }
  
  -ms-overflow-style: none;  // IE/Edge
  scrollbar-width: none;     // Firefox
}

.nexus-carousel__container {
  display: flex;
  gap: var(--carousel-gap, 16px);
  padding: 8px 0;  // Vertical padding for focus ring
}

.nexus-carousel__item {
  flex-shrink: 0;
  scroll-snap-align: start;
  scroll-snap-stop: always;
  
  &:focus-visible {
    outline: 2px solid var(--nexus-accent);
    outline-offset: 4px;
    border-radius: 24px;
  }
}

.nexus-carousel__controls {
  display: flex;
  gap: 8px;
  justify-content: space-between;
  margin-bottom: 12px;
  
  @media (max-width: 719px) {
    display: none;  // Hide on mobile
  }
}

.nexus-carousel__btn {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: rgba(125, 211, 252, 0.14);
  border: 1px solid var(--nexus-border);
  color: var(--nexus-accent);
  cursor: pointer;
  
  &:hover {
    background: rgba(125, 211, 252, 0.24);
  }
  
  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}
```

**Risk:** Quasar's QCarousel is vertical-first; custom scroll may have iOS Safari snap issues. Mitigation: Test on real devices (iPhone, iPad, Android). Use `scroll-snap-type: x mandatory` as primary, add JavaScript fallback.

---

### 2. Refactor CommandCenterPage Layout

**File:** `apps/web/src/pages/CommandCenterPage.vue` (refactor ~150 lines)

**New Structure:**

```vue
<template>
  <q-page class="command-center-shell">
    
    <!-- 1. Hero Section -->
    <NexusPageHero
      eyebrow="Nexus Core"
      title="Command Center"
      subtitle="Sovereign personal operating substrate — capture, study, automate, and ship from one cockpit."
    >
      <template #actions>
        <!-- 6 quick action buttons (current: same) -->
      </template>
    </NexusPageHero>

    <!-- 2. System Status & Metrics Rail -->
    <SystemStatusRibbon :status="status" :online="online" />
    
    <div class="metrics-carousel">
      <NexusCarousel
        :items="metrics"
        item-key="label"
        label="Health Metrics"
        hideControls
      >
        <template #default="{ item }">
          <MetricCard :label="item.label" :value="item.value" :icon="item.icon" />
        </template>
      </NexusCarousel>
    </div>

    <!-- 3. Module Launcher Carousel (Today) -->
    <div class="carousel-section">
      <div class="section-heading">Today</div>
      <NexusCarousel
        :items="todayModules"
        item-key="id"
        gap="16"
        label="Today"
      >
        <template #default="{ item }">
          <ModuleCard
            :title="item.title"
            :caption="item.caption"
            :body="item.body"
            :path="item.path"
            :icon="item.icon"
            :count="item.count"
            :badge="item.badge"
            :count-label="item.countLabel"
            :primary-label="item.primaryLabel"
          />
        </template>
      </NexusCarousel>
    </div>

    <!-- 4. Knowledge Rail -->
    <div class="carousel-section">
      <div class="section-heading">Knowledge</div>
      <NexusCarousel
        :items="knowledgeModules"
        item-key="id"
        gap="16"
      >
        <template #default="{ item }">
          <ModuleCard v-bind="item" />
        </template>
      </NexusCarousel>
    </div>

    <!-- 5. Operations Rail -->
    <div class="carousel-section">
      <div class="section-heading">Operations</div>
      <NexusCarousel
        :items="opsModules"
        item-key="id"
        gap="16"
      >
        <template #default="{ item }">
          <ModuleCard v-bind="item" />
        </template>
      </NexusCarousel>
    </div>

    <!-- 6. Development Rail -->
    <div class="carousel-section">
      <div class="section-heading">Development</div>
      <NexusCarousel
        :items="devModules"
        item-key="id"
        gap="16"
      >
        <template #default="{ item }">
          <ModuleCard v-bind="item" />
        </template>
      </NexusCarousel>
    </div>

    <!-- 7. Installed Modules Registry (optional, at bottom) -->
    <q-card class="glass-card" v-if="modules.length">
      <!-- (keep current implementation) -->
    </q-card>

  </q-page>
</template>

<script setup lang="ts">
// Same data fetching + computed properties
// New: organize modules into 5 groups (today, knowledge, ops, dev)
// Track carousel focus state for keyboard nav
</script>

<style scoped>
.command-center-shell {
  display: flex;
  flex-direction: column;
  gap: clamp(20px, 3vw, 32px);
}

.carousel-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metrics-carousel {
  width: 100%;
  overflow-x: hidden;
}

@media (max-width: 719px) {
  .carousel-section {
    gap: 10px;
  }
  
  .command-center-shell {
    gap: clamp(16px, 2vw, 24px);
  }
}
</style>
```

**Changes in Script:**
```typescript
// Organize modules into 5 groups
const todayModules = computed(() => [
  // Capture, Tasks, Digital Twin
])

const knowledgeModules = computed(() => [
  // Study Companion, Zettelkasten, Research
])

const opsModules = computed(() => [
  // Connectors, Sync Health, Backup/Restore
])

const devModules = computed(() => [
  // Coding Agent, Automation
])

// Track carousel focus for keyboard shortcuts
const focusedCarousel = ref<'today' | 'knowledge' | 'ops' | 'dev' | null>(null)

// Keyboard navigation: Shift+[1-4] to jump between carousels
// Arrow keys navigate within carousel
```

---

### 3. Update CSS for Carousel Styling

**File:** `apps/web/src/css/app.scss` (add ~40 lines)

**Add at end of file (before media queries):**
```scss
/* ── Carousel (Big Picture) ── */
.nexus-carousel {
  overflow-x: auto;
  scroll-behavior: smooth;
  scroll-snap-type: x mandatory;
  padding-right: 0;
  margin: 0 -24px;
  padding-left: 24px;
  padding-right: 24px;
  
  &::-webkit-scrollbar {
    display: none;
  }
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.nexus-carousel__container {
  display: flex;
  gap: 16px;
  padding: 8px 0;
}

.nexus-carousel__item {
  flex-shrink: 0;
  scroll-snap-align: start;
  scroll-snap-stop: always;
  
  &:focus-visible {
    outline: 2px solid var(--nexus-accent);
    outline-offset: 4px;
    border-radius: 24px;
  }
}

.nexus-carousel__heading {
  margin: 12px 0 8px;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--nexus-muted);
}

.nexus-carousel__controls {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-bottom: 12px;
  
  @media (max-width: 719px) {
    display: none;
  }
}

.nexus-carousel__btn {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: rgba(125, 211, 252, 0.14);
  border: 1px solid var(--nexus-border);
  color: var(--nexus-accent);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background .12s ease, border-color .12s ease;
  
  &:hover {
    background: rgba(125, 211, 252, 0.24);
    border-color: rgba(125, 211, 252, 0.32);
  }
  
  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  
  &:focus-visible {
    outline: 2px solid var(--nexus-accent);
    outline-offset: 2px;
  }
}

@media (max-width: 719px) {
  .nexus-carousel {
    margin: 0 -20px;
    padding-left: 20px;
    padding-right: 20px;
  }
}
```

---

### 4. Add Keyboard Navigation Handler

**File:** `apps/web/src/pages/CommandCenterPage.vue` (add script)

```typescript
import { onMounted, onUnmounted, ref } from 'vue'

const commandCenterRef = ref<HTMLElement | null>(null)

function handleKeydown(event: KeyboardEvent) {
  // Shift+[1-4] to jump between carousels
  if (event.shiftKey && event.key >= '1' && event.key <= '4') {
    event.preventDefault()
    const carousels = ['today', 'knowledge', 'ops', 'dev']
    const index = parseInt(event.key) - 1
    focusedCarousel.value = carousels[index] as any
    // Find carousel ref and focus first item
  }
  
  // Arrow keys navigate within focused carousel
  if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
    // Delegate to focused carousel component
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
```

---

### 5. Mobile Layout Adjustments

**File:** `apps/web/src/pages/CommandCenterPage.vue` (enhance scoped styles)

```scss
<style scoped>
@media (max-width: 719px) {
  /* Stack carousels vertically */
  .carousel-section {
    gap: 10px;
  }
  
  /* Larger tap targets on mobile */
  :deep(.q-btn) {
    min-height: 48px;
  }
  
  /* Hero section more compact */
  :deep(.hero-panel) {
    padding: clamp(14px, 2vw, 20px);
  }
  
  /* Metric cards in smaller grid */
  :deep(.nexus-carousel__item) {
    min-width: 140px;
  }
}
</style>
```

---

### 6. Update NexusModuleCard for Carousel Context

**File:** `apps/web/src/components/NexusModuleCard.vue` (minor enhancement)

Add optional `condensed` prop for smaller card variant in mobile carousels:

```typescript
withDefaults(defineProps<{
  // ... existing props ...
  condensed?: boolean  // Hide body, shrink footer
}>(), { primaryLabel: 'Open', condensed: false })
```

Add to style:
```scss
<style scoped>
.module-card-item.condensed {
  min-height: 140px;  // Smaller for mobile carousel
  
  p { display: none; }  // Hide body description
  
  .q-card__actions {
    padding-top: 8px;
  }
}
</style>
```

---

## Risks & Conflicts

### HIGH RISK

**1. Carousel scroll snap behavior on iOS Safari**
- **Issue:** Older iOS versions don't support `scroll-snap-type`
- **Mitigation:** Test on real devices (iPhone 11+, iPad); provide JavaScript fallback for manual slide
- **Fallback:** If snap doesn't work, implement smooth scroll + manual left/right buttons
- **Conflict:** None currently observed

**2. Horizontal overflow on mobile viewports**
- **Issue:** Adding carousel containers might create unintended horizontal scroll
- **Mitigation:** Use `overflow-x: auto` on carousel, `overflow-x: hidden` on page-shell
- **Conflict:** BottomNav and SystemStatusRibbon must also respect overflow-x: hidden

**3. Keyboard navigation state management**
- **Issue:** Tracking which carousel has focus is complex with multiple carousels
- **Mitigation:** Use Vue refs to manage focus, integrate with Tab key behavior
- **Conflict:** CommandPalette (Cmd+K) may interfere; ensure they don't both capture key events

### MEDIUM RISK

**4. Mobile card sizing in carousel**
- **Issue:** ModuleCard at 300px min-width may be too wide for mobile
- **Mitigation:** Add responsive item-width prop to NexusCarousel, shrink on mobile to 240px
- **Conflict:** Text overflow in card title/caption; use text-truncate if needed

**5. Performance with many modules**
- **Issue:** 15+ ModuleCards rendered at once; carousel scroll may lag
- **Mitigation:** Use v-lazy or pagination if module count exceeds 20
- **Conflict:** Currently loading all modules on page load; may need API pagination

**6. Color contrast in glass cards on carousel**
- **Issue:** Metric card text on glass background may be hard to read
- **Mitigation:** Ensure --nexus-text and --nexus-muted meet WCAG AA contrast
- **Conflict:** Already verified in design-system scout; no issues expected

### LOW RISK

**7. Icon text overlap in MetricCard**
- **Issue:** Large metric numbers might overlap icons on small screens
- **Mitigation:** Responsive font-size with `clamp()` already in place
- **Conflict:** None

**8. Duplicate section headings**
- **Issue:** Each carousel has a section-heading; may feel repetitive
- **Mitigation:** Consider "recent actions" or "recommended" headings to vary; part of design choice
- **Conflict:** None

---

## Tests to Run

### Build & Compilation
```bash
cd apps/web

# Type checking
pnpm typecheck

# Linting
pnpm lint

# Production build
pnpm build

# Tests
pnpm test
```

### Visual Regression Tests
1. **Desktop (1920px width)**
   - [ ] Open `/` → hero visible, 5 carousels render
   - [ ] No horizontal scrollbar
   - [ ] All metric cards readable
   - [ ] All ModuleCards readable (title, caption, icon visible)
   - [ ] Glass card contrast OK
   - [ ] Section headings centered & legible

2. **Tablet (768px width)**
   - [ ] All carousels fit without overflow
   - [ ] Cards still readable
   - [ ] Carousel controls visible (not all at once; left/right arrows)

3. **Mobile (375px width)**
   - [ ] Cards still fit in carousel
   - [ ] Text not truncated
   - [ ] Bottom nav not overlapped
   - [ ] Carousel controls hidden
   - [ ] Tap targets ≥ 48px

4. **Dark mode toggle**
   - [ ] All text readable in dark and light modes
   - [ ] Glass morphism effect visible
   - [ ] Icons colored correctly

### Keyboard Navigation Tests
1. **Tab key**
   - [ ] Tab cycles through all interactive elements (buttons, links, carousel items)
   - [ ] Focus ring visible on all focused elements
   - [ ] Focus doesn't disappear when scrolling carousel

2. **Arrow keys (in carousel)**
   - [ ] `→` moves to next item in carousel
   - [ ] `←` moves to previous item
   - [ ] `Home` jumps to first item
   - [ ] `End` jumps to last item
   - [ ] Scrolls smoothly; doesn't jump off-screen

3. **Shortcuts (optional)**
   - [ ] `Cmd+K` opens CommandPalette (not interrupted by carousel focus)
   - [ ] `Shift+1` jumps to "Today" carousel (if implemented)

### Carousel Component Unit Tests
```typescript
// apps/web/src/components/NexusCarousel.test.ts
import { mount } from '@vue/test-utils'
import NexusCarousel from './NexusCarousel.vue'

describe('NexusCarousel', () => {
  it('renders items in horizontal scroll container', () => {
    // Mount with 5 items, verify DOM structure
  })
  
  it('left/right buttons navigate carousel', () => {
    // Click left button, verify scroll position
  })
  
  it('arrow keys navigate carousel (a11y)', () => {
    // Simulate keydown event, verify scroll
  })
  
  it('snap-align behaves correctly', () => {
    // Check CSS classes applied
  })
  
  it('hides controls on mobile', () => {
    // Use @media query testing
  })
})
```

### Manual Acceptance Criteria
- [ ] Command Center becomes a Big Picture-style cockpit ✅
- [ ] Module launcher carousel exists ✅
- [ ] Recent work / daily actions / system status rails exist ✅
- [ ] Keyboard-friendly navigation affordances exist ✅
- [ ] Mobile layout is card-first and usable ✅
- [ ] No route has unreadable text or broken icon text ✅
- [ ] `pnpm web build` passes ✅

---

## Suggested Executor Instructions

### Phase 1: Preparation (1 hour)

1. **Read this scout report + design reference**
   ```bash
   cat .agentops/scouts/nexus-big-picture-command-center.md
   cat .agentops/examples/markdown/tranche04-ui-reference.md
   ```

2. **Run baseline tests**
   ```bash
   cd apps/web
   pnpm typecheck
   pnpm build
   ```
   Should pass without errors.

3. **Inspect current CommandCenterPage visually**
   ```bash
   pnpm dev  # Navigate to http://localhost:9000
   ```
   Open developer tools; check viewport sizes (375px, 768px, 1920px).

### Phase 2: Create NexusCarousel Component (2–3 hours)

1. **Create skeleton**
   ```bash
   touch apps/web/src/components/NexusCarousel.vue
   ```

2. **Implement using this spec:**
   - Props: `items`, `itemKey`, `gap`, `hideControls`, `label`, `itemWidth`, `showFocusRing`
   - Slots: `default` (item, index), `label`
   - Template: Flex container + left/right buttons (desktop) + v-for items
   - CSS: `.nexus-carousel`, `.nexus-carousel__item`, `.nexus-carousel__btn` (copy from above)
   - Keyboard: Emit `@select` event on item click or arrow-key navigation

3. **Test in isolation**
   ```bash
   # Create simple test page or Storybook story
   # Verify scroll snap, button interaction, keyboard nav
   pnpm build  # Should still pass
   ```

### Phase 3: Refactor CommandCenterPage (1–2 hours)

1. **Backup current version**
   ```bash
   cp apps/web/src/pages/CommandCenterPage.vue CommandCenterPage.vue.bak
   ```

2. **Refactor following the new structure above:**
   - Keep hero section + quick actions (unchanged)
   - Replace static `.module-grid` divs with `<NexusCarousel>` components
   - Organize modules into 5 groups (today, knowledge, ops, dev)
   - Keep installed modules registry at bottom

3. **Update script:**
   - Split `modules` computed into `todayModules`, `knowledgeModules`, etc.
   - Add keyboard event listener for carousel navigation (optional in Phase 1)

4. **Test rebuild**
   ```bash
   pnpm build
   ```

### Phase 4: Update CSS (30 minutes)

1. **Add carousel styles to `apps/web/src/css/app.scss`:**
   - Copy `.nexus-carousel*` rules from spec above
   - Ensure no conflicts with `.module-grid` or other classes

2. **Verify mobile breakpoints**
   ```bash
   pnpm build
   ```

### Phase 5: Manual Testing (1–2 hours)

1. **Desktop viewport (1920px)**
   ```bash
   pnpm dev
   # Open browser DevTools → resize to 1920px
   # Inspect:
   #   - No horizontal scrollbar
   #   - Carousels render (5 sections visible)
   #   - ModuleCards readable (title, icon, action buttons)
   #   - Section headings aligned
   ```

2. **Tablet viewport (768px)**
   ```bash
   # Resize to 768px
   # Verify carousels still fit, no overflow
   ```

3. **Mobile viewport (375px)**
   ```bash
   # Resize to 375px
   # Verify:
   #   - Carousel controls hidden
   #   - Cards fit in scroll container
   #   - Text not truncated
   #   - Bottom nav not overlapped
   #   - Tap targets ≥ 48px
   ```

4. **Keyboard navigation**
   ```bash
   # Tab through all elements → focus ring visible on buttons, carousel items
   # In carousel: press → / ← → items scroll
   # Cmd/Ctrl+K → CommandPalette still opens
   ```

5. **Dark mode toggle**
   ```bash
   # Click theme toggle in header
   # Verify all text readable in both modes
   ```

### Phase 6: Acceptance & Documentation (30 minutes)

1. **Run full test suite**
   ```bash
   cd apps/web
   pnpm typecheck && pnpm lint && pnpm test
   ```

2. **Create component documentation**
   ```bash
   # Document NexusCarousel props, slots, usage
   # Add to .agentops/examples/COMPONENT_REGISTRY.md
   ```

3. **Update scout report status**
   ```bash
   # Mark as "COMPLETED" in this file
   ```

4. **Commit changes**
   ```bash
   git add -A
   git commit -m "refactor: command center to big picture cockpit layout with carousels"
   ```

---

## Files to Create/Edit

| Path | Type | Action | Time | Priority |
|------|------|--------|------|----------|
| `apps/web/src/components/NexusCarousel.vue` | New | Create horizontal carousel | 2h | HIGH |
| `apps/web/src/pages/CommandCenterPage.vue` | Edit | Restructure into 5 carousel sections | 1.5h | HIGH |
| `apps/web/src/css/app.scss` | Edit | Add carousel & section heading styles | 30m | HIGH |
| `apps/web/src/components/NexusCarousel.test.ts` | New | Unit tests for carousel | 1h | MEDIUM |
| `.agentops/examples/COMPONENT_REGISTRY.md` | New | Document NexusCarousel API | 30m | LOW |

**Total estimated effort:** 4–6 hours (1 work day)

---

## Build Commands Ready

```bash
# From repo root
cd apps/web

# Baseline validation
pnpm typecheck && pnpm lint && pnpm build

# Development server (http://localhost:9000)
pnpm dev

# Run tests
pnpm test

# Full validation after changes
pnpm typecheck && pnpm lint && pnpm build && pnpm test
```

---

## Key Design Decisions

### 1. Why Horizontal Carousels?
- **Big Picture vision:** Cinematic UX inspired by Steam Big Picture, console interfaces
- **Scannable:** User can see 3–5 items at once without scrolling
- **Keyboard-friendly:** Arrow keys naturally navigate horizontally
- **Mobile-friendly:** Swipe-to-scroll on touch devices
- **Responsive:** Carousels adapt to viewport width without breaking layout

### 2. Why 5 Sections (Today, Knowledge, Ops, Dev)?
- **Today:** Capture, Tasks, Digital Twin (highest priority/frequency)
- **Knowledge:** Study, Zettel, Research (knowledge work)
- **Operations:** Connectors, Sync, Backup (system/admin)
- **Development:** Coding Agent, Automation (automation/CI-like)
- **Grouping:** Users scan mentally by use-case, not alphabetically

### 3. Why Keep Installed Modules at Bottom?
- **Low priority:** Modules are discovered via onboarding, not frequently accessed
- **Admin context:** Shows system health & registry state
- **Scalable:** Can grow beyond 5 modules without layout breakage

### 4. Why Not Use Quasar's QCarousel?
- **QCarousel is vertical-first:** Designed for image carousels (full-height swipes)
- **Custom scroll:** CSS scroll-snap is simpler, lighter, better keyboard support
- **Accessibility:** Custom component gives full control over focus management
- **Mobile:** Native scroll-snap better than JavaScript-driven pagination

---

## Appendix: Reference Images

See `.agentops/examples/images/`:
- `steam-big-picture-carousel-reference.png` — UI inspiration for horizontal carousel + focus state
- `floating-social-glass-reference.png` — Glass morphism reference for card styling

---

## Conclusion

**Status: READY FOR IMPLEMENTATION**

The Command Center refactor is straightforward:

1. **Create 1 new component** (NexusCarousel, ~100 lines)
2. **Refactor 1 existing page** (CommandCenterPage, ~150 lines)
3. **Enhance CSS** (add carousel styles, ~40 lines)
4. **Test thoroughly** (desktop, tablet, mobile, keyboard, dark mode)

**No architectural changes needed.** All components, routes, and services remain stable.

**Confidence level: HIGH** (CSS foundation solid, component API clear, no third-party library conflicts)

**Estimated effort: 4–6 hours**

---

## Scout Metadata

- **Assessed:** 2026-06-08 09:30 UTC
- **Assessor:** Claude Code Scout (read-only)
- **Status:** ✅ Ready for executor
- **Next step:** Assign to frontend engineer or agent for implementation
