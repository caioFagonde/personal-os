<template>
  <button
    class="bp-tile"
    :class="{ 'bp-tile--focused': focused, 'bp-tile--small': size === 'small' }"
    :style="tileStyle"
    type="button"
    :aria-label="`Open ${module.label}`"
    :tabindex="focused ? 0 : -1"
    @click="$emit('select')"
    @pointerenter="$emit('focus')"
  >
    <div class="bp-tile__art">
      <q-icon :name="module.icon" class="bp-tile__icon" />
      <div class="bp-tile__sheen" />
    </div>
    <div class="bp-tile__meta">
      <span class="bp-tile__label">{{ module.label }}</span>
      <span v-if="badge" class="bp-tile__badge">{{ badge }}</span>
    </div>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BigPictureModule } from '../../design/bigpicture'

const props = withDefaults(
  defineProps<{
    module: BigPictureModule
    focused?: boolean
    size?: 'large' | 'small'
    badge?: string | number | null
  }>(),
  { focused: false, size: 'large', badge: null },
)

defineEmits<{ (e: 'select'): void; (e: 'focus'): void }>()

const tileStyle = computed(() => ({
  '--tile-accent': props.module.accent,
  '--tile-accent2': props.module.accent2,
}))
</script>

<style lang="scss" scoped>
.bp-tile {
  position: relative;
  flex: 0 0 auto;
  width: var(--bp-tile-w);
  border: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
  color: var(--bp-text);
  text-align: left;
  outline: none;
  scroll-snap-align: center;
  transition: transform 0.32s cubic-bezier(0.22, 1, 0.36, 1);
  transform: scale(0.92) translateY(6px);
  will-change: transform;

  &--small {
    width: var(--bp-tile-w-sm);
  }

  &--focused {
    transform: scale(1) translateY(0);
    z-index: 2;
  }
}

.bp-tile__art {
  position: relative;
  aspect-ratio: 16 / 10;
  border-radius: 18px;
  overflow: hidden;
  display: grid;
  place-items: center;
  background:
    radial-gradient(130% 120% at 18% 0%, color-mix(in srgb, var(--tile-accent) 38%, transparent), transparent 62%),
    radial-gradient(120% 130% at 92% 100%, color-mix(in srgb, var(--tile-accent2) 26%, transparent), transparent 58%),
    linear-gradient(150deg, rgba(16, 23, 42, 0.92), rgba(8, 12, 24, 0.94));
  border: 1px solid rgba(160, 190, 255, 0.14);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.45);
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.bp-tile--focused .bp-tile__art {
  border-color: color-mix(in srgb, var(--tile-accent) 75%, white 10%);
  box-shadow:
    0 0 0 2px color-mix(in srgb, var(--tile-accent) 65%, transparent),
    0 0 64px color-mix(in srgb, var(--tile-accent) 35%, transparent),
    0 26px 70px rgba(0, 0, 0, 0.55);
}

.bp-tile__icon {
  font-size: clamp(40px, 4.6vw, 72px);
  color: color-mix(in srgb, var(--tile-accent) 82%, white 18%);
  filter: drop-shadow(0 6px 24px color-mix(in srgb, var(--tile-accent) 55%, transparent));
}

.bp-tile__sheen {
  position: absolute;
  inset: 0;
  background: linear-gradient(115deg, transparent 30%, rgba(255, 255, 255, 0.07) 48%, transparent 62%);
  transform: translateX(-120%);
  transition: transform 0.7s ease;
  pointer-events: none;
}
.bp-tile--focused .bp-tile__sheen {
  transform: translateX(120%);
}

.bp-tile__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 4px 0;
  min-height: 38px;
}
.bp-tile__label {
  font-family: var(--bp-font-display);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--bp-muted);
  transition: color 0.25s ease;
}
.bp-tile--focused .bp-tile__label {
  color: var(--bp-text);
}
.bp-tile__badge {
  font-family: var(--bp-font-mono);
  font-size: 11px;
  line-height: 1;
  padding: 4px 8px;
  border-radius: 999px;
  color: #05070d;
  background: var(--tile-accent);
  font-weight: 700;
}
</style>
