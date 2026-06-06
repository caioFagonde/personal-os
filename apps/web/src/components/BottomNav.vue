<template>
  <q-footer class="mobile-nav" reveal>
    <q-tabs dense align="justify" class="text-white">
      <q-route-tab v-for="item in items" :key="item.id" :to="item.path" :icon="item.icon" :label="item.label" />
    </q-tabs>
  </q-footer>
</template>
<script setup lang="ts">
import { navigationModules } from '../design/tokens'
const items = navigationModules.filter((m) => ['home', 'capture', 'tasks', 'study-companion', 'digital-twin'].includes(m.id))
</script>
