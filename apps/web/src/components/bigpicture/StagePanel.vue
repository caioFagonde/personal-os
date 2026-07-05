<template>
  <div class="bp-stage">
    <div class="bp-stage__chrome">
      <button class="bp-stage__back" type="button" @click="$emit('back')">
        <q-icon name="mdi-arrow-left" size="18px" />
        <span>Home</span>
        <kbd>Esc</kbd>
      </button>
      <div v-if="module" class="bp-stage__crumb" :style="{ '--bp-accent': module.accent }">
        <q-icon :name="module.icon" size="16px" />
        <span>{{ module.label }}</span>
      </div>
    </div>
    <div class="bp-stage__panel">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { BigPictureModule } from '../../design/bigpicture'

defineProps<{ module?: BigPictureModule | null }>()
defineEmits<{ (e: 'back'): void }>()
</script>

<style lang="scss" scoped>
.bp-stage {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  min-height: 100dvh;
  padding: calc(72px + env(safe-area-inset-top)) clamp(16px, 3vw, 48px) clamp(20px, 4vh, 48px);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.bp-stage__chrome {
  display: flex;
  align-items: center;
  gap: 14px;
}

.bp-stage__back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 14px;
  border-radius: 10px;
  border: 1px solid rgba(160, 190, 255, 0.18);
  background: rgba(10, 15, 28, 0.6);
  backdrop-filter: blur(12px);
  color: var(--bp-muted);
  font-size: 13.5px;
  font-weight: 600;
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
  }
}

.bp-stage__crumb {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--bp-font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--bp-text);

  .q-icon {
    color: var(--bp-accent, #7dd3fc);
  }
}

.bp-stage__panel {
  flex: 1;
  border-radius: 24px;
  border: 1px solid rgba(160, 190, 255, 0.13);
  background: rgba(8, 12, 23, 0.78);
  backdrop-filter: blur(22px);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.5);
  padding: clamp(14px, 2vw, 28px);
  overflow: auto;
  animation: bp-stage-in 0.34s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes bp-stage-in {
  from {
    opacity: 0;
    transform: translateY(22px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .bp-stage__panel {
    animation: none;
  }
}

@media (max-width: 719px) {
  .bp-stage {
    padding-left: 10px;
    padding-right: 10px;
  }
  .bp-stage__panel {
    border-radius: 18px;
  }
}
</style>
