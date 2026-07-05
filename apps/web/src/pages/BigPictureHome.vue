<template>
  <div class="bp-home">
    <!-- Hero: the focused module speaks -->
    <section class="bp-hero" :style="heroStyle" aria-live="polite">
      <transition name="bp-hero-swap" mode="out-in">
        <div :key="focusedModule.id" class="bp-hero__inner">
          <div class="bp-hero__eyebrow">
            <q-icon :name="focusedModule.icon" size="18px" />
            <span>{{ focusedModule.group }}</span>
          </div>
          <h1 class="bp-hero__title">{{ focusedModule.label }}</h1>
          <p class="bp-hero__blurb">{{ focusedModule.blurb }}</p>
          <div class="bp-hero__actions">
            <button class="bp-action bp-action--primary" type="button" @click="open(focusedModule)">
              <q-icon name="mdi-arrow-right" size="18px" />
              {{ primaryActionLabel }}
            </button>
            <button
              v-for="action in extraActions"
              :key="action.path"
              class="bp-action"
              type="button"
              @click="router.push(action.path)"
            >
              <q-icon :name="action.icon" size="16px" />
              {{ action.label }}
            </button>
          </div>
        </div>
      </transition>
    </section>

    <!-- Featured carousel -->
    <section class="bp-row">
      <ModuleCarousel
        v-model:index="featuredIndex"
        :modules="featured"
        :active="row === 0"
        :badges="badges"
        @open="open"
      />
    </section>

    <!-- System strip -->
    <section class="bp-row bp-row--system">
      <ModuleCarousel
        v-model:index="systemIndex"
        :modules="system"
        :active="row === 1"
        size="small"
        @open="open"
      />
    </section>

    <!-- Controller hints -->
    <footer class="bp-hints" aria-hidden="true">
      <span class="bp-hints__item"><kbd>←→</kbd> Browse</span>
      <span class="bp-hints__item"><kbd>↑↓</kbd> Row</span>
      <span class="bp-hints__item"><kbd>⏎</kbd> Open</span>
      <span class="bp-hints__item"><kbd>⌘K</kbd> Search</span>
      <span v-if="gamepadSeen" class="bp-hints__item bp-hints__item--pad">
        <q-icon name="mdi-gamepad-variant-outline" size="15px" /> Controller connected
      </span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ModuleCarousel from '../components/bigpicture/ModuleCarousel.vue'
import { featuredModules, systemModules, type BigPictureModule } from '../design/bigpicture'
import { setAmbience, setDim } from '../composables/useAmbience'
import { useInputNav, type NavAction } from '../composables/useInputNav'
import { captureUrl, jsonFetch } from '../services/api'

const router = useRouter()
const featured = featuredModules
const system = systemModules

const row = ref(0)
const featuredIndex = ref(0)
const systemIndex = ref(0)
const gamepadSeen = ref(false)
const badges = ref<Record<string, string | number>>({})

const focusedModule = computed<BigPictureModule>(() =>
  row.value === 0 ? featured[featuredIndex.value] : system[systemIndex.value],
)

const primaryActionLabel = computed(
  () => focusedModule.value.actions?.[0]?.label ?? `Open ${focusedModule.value.label}`,
)
const extraActions = computed(() => focusedModule.value.actions?.slice(1) ?? [])

const heroStyle = computed(() => ({
  '--bp-accent': focusedModule.value.accent,
  '--bp-accent2': focusedModule.value.accent2,
}))

watch(
  focusedModule,
  (mod) => setAmbience(mod.accent, mod.accent2),
  { immediate: true },
)

function open(mod: BigPictureModule) {
  router.push(mod.actions?.[0]?.path ?? mod.path)
}

useInputNav((action: NavAction, source) => {
  if (source === 'gamepad') gamepadSeen.value = true
  const list = row.value === 0 ? featured : system
  const index = row.value === 0 ? featuredIndex : systemIndex
  switch (action) {
    case 'left':
      index.value = Math.max(0, index.value - 1)
      break
    case 'right':
      index.value = Math.min(list.length - 1, index.value + 1)
      break
    case 'up':
      row.value = 0
      break
    case 'down':
      row.value = 1
      break
    case 'confirm':
      open(focusedModule.value)
      break
    case 'menu':
      // App shell owns the command palette; re-dispatch as the shortcut it listens for.
      window.dispatchEvent(new CustomEvent('bp:open-palette'))
      break
  }
})

async function loadBadges() {
  try {
    const tasks = await jsonFetch<unknown[]>(`${captureUrl}/api/tasks?status=inbox`)
    if (Array.isArray(tasks) && tasks.length) badges.value = { ...badges.value, tasks: tasks.length }
  } catch {
    /* offline-first: badges are decoration, never a failure state */
  }
}

onMounted(() => {
  setDim(0)
  loadBadges()
})
</script>

<style lang="scss" scoped>
.bp-home {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding-bottom: clamp(56px, 7vh, 96px);
  overflow: hidden;
}

/* ---- Hero ---- */
.bp-hero {
  padding: 0 0 clamp(20px, 4vh, 44px) 16vw;
  min-height: clamp(220px, 32vh, 340px);
  display: flex;
  align-items: flex-end;
}
.bp-hero__inner {
  max-width: 680px;
}
.bp-hero__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--bp-font-mono);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--bp-accent);
  margin-bottom: 14px;
}
.bp-hero__title {
  font-family: var(--bp-font-display);
  font-size: clamp(40px, 5.4vw, 76px);
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 0.98;
  margin: 0 0 14px;
  color: var(--bp-text);
  text-shadow: 0 8px 60px rgba(0, 0, 0, 0.6);
}
.bp-hero__blurb {
  font-size: clamp(15px, 1.2vw, 18px);
  line-height: 1.55;
  color: var(--bp-muted);
  margin: 0 0 22px;
  max-width: 54ch;
}
.bp-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.bp-action {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  height: 44px;
  padding: 0 20px;
  border-radius: 12px;
  border: 1px solid rgba(160, 190, 255, 0.18);
  background: rgba(12, 18, 34, 0.6);
  backdrop-filter: blur(12px);
  color: var(--bp-text);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.15s ease;

  &:hover,
  &:focus-visible {
    border-color: var(--bp-accent);
    transform: translateY(-1px);
  }

  &--primary {
    border-color: transparent;
    background: linear-gradient(135deg, var(--bp-accent), var(--bp-accent2));
    color: #05070d;
    box-shadow: 0 8px 36px color-mix(in srgb, var(--bp-accent) 40%, transparent);
  }
}

/* ---- Rows ---- */
.bp-row {
  margin-bottom: clamp(18px, 3vh, 30px);
}
.bp-row--system {
  margin-bottom: 0;
}

/* ---- Hero swap transition ---- */
.bp-hero-swap-enter-active,
.bp-hero-swap-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.bp-hero-swap-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.bp-hero-swap-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ---- Hints ---- */
.bp-hints {
  position: fixed;
  right: max(28px, env(safe-area-inset-right));
  bottom: max(18px, env(safe-area-inset-bottom));
  display: flex;
  gap: 18px;
  font-size: 12.5px;
  color: var(--bp-muted);
  z-index: 5;

  kbd {
    font-family: var(--bp-font-mono);
    font-size: 11px;
    padding: 2px 6px;
    margin-right: 5px;
    border-radius: 6px;
    border: 1px solid rgba(160, 190, 255, 0.2);
    background: rgba(255, 255, 255, 0.04);
  }

  &__item {
    display: inline-flex;
    align-items: center;
  }
  &__item--pad {
    color: var(--bp-accent, #7dd3fc);
  }
}

@media (max-width: 719px) {
  .bp-hero {
    padding-left: 20px;
    padding-right: 20px;
    min-height: clamp(180px, 28vh, 260px);
  }
  .bp-hints {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .bp-hero-swap-enter-active,
  .bp-hero-swap-leave-active {
    transition: none;
  }
}
</style>
