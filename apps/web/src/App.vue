<template>
  <q-layout view="hHh Lpr fFf" class="bp-shell">
    <!-- Signature layer: full-bleed WebGL aurora -->
    <AuroraBackground />

    <!-- Ambient chrome -->
    <AmbientBar
      :status="status"
      @home="goHome"
      @search="openPalette"
      @settings="router.push('/settings')"
    />

    <q-page-container class="bp-shell__pages" :style="safeArea">
      <router-view v-slot="{ Component, route: current }">
        <!-- Home renders bare over the aurora -->
        <component :is="Component" v-if="current.path === '/'" />

        <!-- Every other page lives on the stage -->
        <StagePanel v-else :module="currentModule" @back="goHome">
          <SystemStatusRibbon
            :status="status"
            :online="online"
            :pending-mutations="pendingMutations"
            :conflicts="conflicts"
          />
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </StagePanel>
      </router-view>
    </q-page-container>

    <BottomNav v-if="layout.bottomNav" />
    <CommandPalette ref="palette" />
    <FKeyBar v-if="!layout.bottomNav" />
    <BiosBoot />
  </q-layout>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BottomNav from './components/BottomNav.vue'
import CommandPalette from './components/CommandPalette.vue'
import FKeyBar from './components/FKeyBar.vue'
import BiosBoot from './components/BiosBoot.vue'
import SystemStatusRibbon from './components/SystemStatusRibbon.vue'
import AuroraBackground from './components/bigpicture/AuroraBackground.vue'
import AmbientBar from './components/bigpicture/AmbientBar.vue'
import StagePanel from './components/bigpicture/StagePanel.vue'
import { moduleByPath } from './design/bigpicture'
import { setAmbience, setDim } from './composables/useAmbience'
import { useInputNav } from './composables/useInputNav'
import { detectPlatform, preferredLayout, safeAreaStyle } from './services/platform'
import { initDensity } from './services/preferences'
import { startSyncWorker } from './services/sync-worker'

initDensity()

const router = useRouter()
const route = useRoute()

const platform = detectPlatform()
const layout = preferredLayout(platform)
const palette = ref<InstanceType<typeof CommandPalette> | null>(null)
const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
const pendingMutations = ref(0)
const conflicts = ref(0)
const status = computed(() => (online.value ? 'ok' : 'offline'))
const safeArea = safeAreaStyle(platform)

const currentModule = computed(() => moduleByPath(route.path) ?? null)

function goHome() {
  if (route.path !== '/') router.push('/')
}

function openPalette() {
  if (palette.value) palette.value.open = true
}

// Detail pages dim the aurora so dense content reads; their module re-tints it.
watch(
  () => route.path,
  (path) => {
    setDim(path === '/' ? 0 : 0.75)
    const mod = moduleByPath(path)
    if (mod) setAmbience(mod.accent, mod.accent2)
  },
  { immediate: true },
)

// Shell-level controls: B / Esc backs out to home, Start / ⌘K opens search.
useInputNav((action) => {
  if (action === 'back' && route.path !== '/') {
    const paletteOpen = !!palette.value?.open
    if (!paletteOpen) goHome()
  }
  if (action === 'menu') openPalette()
})

function onOpenPalette() {
  openPalette()
}
function onOnline() {
  online.value = true
}
function onOffline() {
  online.value = false
}

onMounted(() => {
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
  window.addEventListener('bp:open-palette', onOpenPalette)
  startSyncWorker() // Phase E: policy-gated queue drain + per-device heartbeat
})
onBeforeUnmount(() => {
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
  window.removeEventListener('bp:open-palette', onOpenPalette)
})
</script>
