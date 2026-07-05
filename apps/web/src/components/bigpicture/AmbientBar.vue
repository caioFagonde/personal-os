<template>
  <header class="bp-ambient">
    <button class="bp-ambient__brand" type="button" aria-label="Go home" @click="$emit('home')">
      <span class="bp-ambient__mark">N</span>
      <span class="bp-ambient__title">Nexus<span class="bp-ambient__title-dim"> · Personal OS</span></span>
    </button>

    <div class="bp-ambient__spacer" />

    <button class="bp-ambient__pill" type="button" @click="$emit('search')">
      <q-icon name="mdi-magnify" size="16px" />
      <span>Search</span>
      <kbd>⌘K</kbd>
    </button>

    <div class="bp-ambient__status" :class="`bp-ambient__status--${status}`">
      <q-icon :name="statusIcon" size="16px" />
      <span>{{ statusLabel }}</span>
    </div>

    <button class="bp-ambient__pill bp-ambient__pill--icon" type="button" aria-label="Settings" @click="$emit('settings')">
      <q-icon name="mdi-cog-outline" size="17px" />
    </button>

    <time class="bp-ambient__clock" :datetime="now.toISOString()">{{ clock }}</time>
  </header>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { statusTone, type StatusKey } from '../../design/tokens'

const props = withDefaults(defineProps<{ status?: StatusKey }>(), { status: 'ok' })
defineEmits<{ (e: 'home'): void; (e: 'search'): void; (e: 'settings'): void }>()

const now = ref(new Date())
let timer = 0
const clock = computed(() =>
  now.value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
)
const statusIcon = computed(() => statusTone[props.status].icon)
const statusLabel = computed(() => statusTone[props.status].label)

onMounted(() => {
  timer = window.setInterval(() => { now.value = new Date() }, 10_000)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<style lang="scss" scoped>
.bp-ambient {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px max(28px, env(safe-area-inset-right)) 12px max(28px, env(safe-area-inset-left));
  padding-top: calc(18px + env(safe-area-inset-top));
  background: linear-gradient(rgba(3, 5, 11, 0.55), transparent);
  pointer-events: none;

  > * {
    pointer-events: auto;
  }
}

.bp-ambient__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  color: var(--bp-text);
}
.bp-ambient__mark {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-weight: 900;
  font-size: 15px;
  color: #05070d;
  background: linear-gradient(135deg, var(--bp-accent, #7dd3fc), #a78bfa);
  box-shadow: 0 0 28px rgba(125, 211, 252, 0.3);
  transition: background 0.5s ease;
}
.bp-ambient__title {
  font-family: var(--bp-font-display);
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 0.01em;
}
.bp-ambient__title-dim {
  color: var(--bp-muted);
  font-weight: 500;
}

.bp-ambient__spacer {
  flex: 1;
}

.bp-ambient__pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(160, 190, 255, 0.16);
  background: rgba(10, 15, 28, 0.55);
  backdrop-filter: blur(14px);
  color: var(--bp-muted);
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s ease, border-color 0.2s ease;

  &:hover,
  &:focus-visible {
    color: var(--bp-text);
    border-color: rgba(160, 190, 255, 0.4);
  }

  kbd {
    font-family: var(--bp-font-mono);
    font-size: 10px;
    padding: 2px 5px;
    border-radius: 5px;
    border: 1px solid rgba(160, 190, 255, 0.2);
    background: rgba(255, 255, 255, 0.04);
  }

  &--icon {
    width: 34px;
    padding: 0;
    justify-content: center;
  }
}

.bp-ambient__status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 34px;
  padding: 0 13px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 600;
  border: 1px solid transparent;
  backdrop-filter: blur(14px);

  &--ok { color: #34d399; border-color: rgba(52, 211, 153, 0.25); background: rgba(52, 211, 153, 0.08); }
  &--degraded { color: #fbbf24; border-color: rgba(251, 191, 36, 0.25); background: rgba(251, 191, 36, 0.08); }
  &--offline { color: #fb7185; border-color: rgba(251, 113, 133, 0.25); background: rgba(251, 113, 133, 0.08); }
  &--unknown { color: var(--bp-muted); border-color: rgba(160, 190, 255, 0.16); background: rgba(10, 15, 28, 0.5); }
}

.bp-ambient__clock {
  font-family: var(--bp-font-mono);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--bp-text);
  min-width: 52px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 719px) {
  .bp-ambient__pill span,
  .bp-ambient__pill kbd,
  .bp-ambient__status span,
  .bp-ambient__title-dim {
    display: none;
  }
}
</style>
