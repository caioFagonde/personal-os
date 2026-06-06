<template>
  <q-page padding>
    <h1>{{ id }}</h1>
    <p>This is the first shell for the {{ id }} module. Module-specific UX lives here, but data/sync/eventing come from Nexus Core.</p>
  </q-page>
</template>
<script setup lang="ts">
defineProps<{ id: string }>()
</script>
