<template>
  <q-layout view="hHh Lpr fFf" class="nexus-shell">
    <q-header class="app-header" bordered>
      <q-toolbar>
        <q-btn v-if="layout.drawer" flat round icon="mdi-menu" @click="drawer = !drawer" />
        <q-toolbar-title class="row items-center no-wrap q-gutter-sm">
          <div class="brand-mark">N</div>
          <div>
            <div class="brand-title">Nexus Core</div>
            <div class="brand-caption">Sovereign personal operating substrate</div>
          </div>
        </q-toolbar-title>
        <q-btn flat no-caps icon="mdi-magnify" :label="layout.commandPaletteShortcut" @click="openPalette" />
        <q-btn flat round icon="mdi-cog-outline" to="/settings" />
        <q-btn flat round icon="mdi-theme-light-dark" @click="toggleDark" />
      </q-toolbar>
    </q-header>

    <q-drawer v-if="layout.drawer" v-model="drawer" show-if-above :width="288" class="app-drawer">
      <ModuleDock />
    </q-drawer>

    <q-page-container :style="safeArea">
      <div class="page-shell">
        <SystemStatusRibbon :status="status" :online="online" :pending-mutations="pendingMutations" :conflicts="conflicts" />
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </q-page-container>

    <BottomNav v-if="layout.bottomNav" />
    <CommandPalette ref="palette" />
  </q-layout>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Dark } from 'quasar'
import BottomNav from './components/BottomNav.vue'
import CommandPalette from './components/CommandPalette.vue'
import ModuleDock from './components/ModuleDock.vue'
import SystemStatusRibbon from './components/SystemStatusRibbon.vue'
import { detectPlatform, preferredLayout, safeAreaStyle } from './services/platform'

const platform = detectPlatform()
const layout = preferredLayout(platform)
const drawer = ref(layout.drawer)
const palette = ref<InstanceType<typeof CommandPalette> | null>(null)
const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
const pendingMutations = ref(0)
const conflicts = ref(0)
const status = computed(() => (online.value ? 'ok' : 'offline'))
const safeArea = safeAreaStyle(platform)
function openPalette() { if (palette.value) palette.value.open = true }
function toggleDark() { Dark.set(!Dark.isActive) }
onMounted(() => {
  window.addEventListener('online', () => { online.value = true })
  window.addEventListener('offline', () => { online.value = false })
})
</script>
