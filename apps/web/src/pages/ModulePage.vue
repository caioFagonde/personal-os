<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero :eyebrow="'Module'" :title="id" subtitle="Module-specific UX. Data, sync, and eventing are provided by Nexus Core." />
    <NexusEmptyState icon="mdi-puzzle-outline" message="Module shell ready." :hint="`The ${id} module is registered. Add features here as the module matures.`" />
  </q-page>
</template>
<script setup lang="ts">
import NexusPageHero from '../components/NexusPageHero.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
defineProps<{ id: string }>()
</script>
