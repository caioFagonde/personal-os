<template>
  <div class="bp-carousel" :class="{ 'bp-carousel--active': active }">
    <div v-if="sectionLabel" class="bp-carousel__section">
      <span class="bp-carousel__section-tick" />
      {{ sectionLabel }}
    </div>
    <div ref="viewport" class="bp-carousel__viewport" @wheel.prevent="onWheel">
      <div class="bp-carousel__track" :style="trackStyle">
        <ModuleTile
          v-for="(mod, i) in modules"
          :key="mod.id"
          :module="mod"
          :focused="active && i === index"
          :size="size"
          :badge="badges?.[mod.id] ?? null"
          @select="$emit('open', mod)"
          @focus="onHover(i)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Console-style carousel: the focused tile stays at a fixed lane position
 * (left third of the screen, like Big Picture) and the track slides under it.
 * Mouse hover, wheel, touch drag, arrows, and d-pad all move the same index.
 */
import { computed, ref, watch } from 'vue'
import ModuleTile from './ModuleTile.vue'
import { carouselSections, type BigPictureModule } from '../../design/bigpicture'

const props = withDefaults(
  defineProps<{
    modules: BigPictureModule[]
    index: number
    active?: boolean
    size?: 'large' | 'small'
    badges?: Record<string, string | number> | null
  }>(),
  { active: true, size: 'large', badges: null },
)

const emit = defineEmits<{
  (e: 'update:index', value: number): void
  (e: 'open', mod: BigPictureModule): void
}>()

const viewport = ref<HTMLElement | null>(null)
const sections = computed(() => carouselSections(props.modules))
const sectionLabel = computed(() => {
  const current = props.modules[props.index]
  return current ? current.group : ''
})

// The focused tile sits at this fraction of the viewport width.
const LANE = 0.16

const trackStyle = computed(() => {
  const w = props.size === 'small' ? 'var(--bp-tile-w-sm)' : 'var(--bp-tile-w)'
  return {
    transform: `translateX(calc(${LANE * 100}vw - (${w} + var(--bp-tile-gap)) * ${props.index}))`,
  }
})

function clamp(i: number) {
  return Math.max(0, Math.min(props.modules.length - 1, i))
}

function onHover(i: number) {
  if (props.active) emit('update:index', clamp(i))
}

let wheelAccum = 0
let wheelLock = 0
function onWheel(event: WheelEvent) {
  const now = performance.now()
  if (now < wheelLock) return
  wheelAccum += Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY
  if (Math.abs(wheelAccum) > 60) {
    emit('update:index', clamp(props.index + (wheelAccum > 0 ? 1 : -1)))
    wheelAccum = 0
    wheelLock = now + 120
  }
}

// Touch drag
let touchStartX = 0
let touchStartIndex = 0
watch(viewport, (el, _old, onCleanup) => {
  if (!el) return
  const start = (e: TouchEvent) => {
    touchStartX = e.touches[0].clientX
    touchStartIndex = props.index
  }
  const move = (e: TouchEvent) => {
    const dx = touchStartX - e.touches[0].clientX
    const tileW = (el.querySelector('.bp-tile') as HTMLElement | null)?.offsetWidth || 280
    const delta = Math.round(dx / (tileW * 0.8))
    if (delta !== 0) emit('update:index', clamp(touchStartIndex + delta))
  }
  el.addEventListener('touchstart', start, { passive: true })
  el.addEventListener('touchmove', move, { passive: true })
  onCleanup(() => {
    el.removeEventListener('touchstart', start)
    el.removeEventListener('touchmove', move)
  })
}, { immediate: true })

defineExpose({ sections })
</script>

<style lang="scss" scoped>
.bp-carousel {
  width: 100%;
  opacity: 0.55;
  transition: opacity 0.3s ease;

  &--active {
    opacity: 1;
  }
}

.bp-carousel__section {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 14px calc(16vw + 2px);
  font-family: var(--bp-font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--bp-muted);
}
.bp-carousel__section-tick {
  width: 22px;
  height: 2px;
  border-radius: 2px;
  background: var(--bp-accent, #7dd3fc);
}

.bp-carousel__viewport {
  overflow: hidden;
  padding: 14px 0 6px;
  /* breathing room so the focused tile's glow isn't clipped */
  margin: -14px 0 -6px;
}

.bp-carousel__track {
  display: flex;
  gap: var(--bp-tile-gap);
  transition: transform 0.42s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
}

@media (max-width: 719px) {
  .bp-carousel__section {
    margin-left: 20px;
  }
}
</style>
