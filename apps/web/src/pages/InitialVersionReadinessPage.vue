<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Initial Version" title="Release Readiness Gate" subtitle="The initial version is complete when every gate below passes on the real stack, real phone, and configured connector sandbox." />

    <q-card class="glass-card">
      <q-card-section>
        <q-list separator>
          <q-item v-for="gate in gates" :key="gate">
            <q-item-section avatar><q-icon name="mdi-checkbox-marked-circle-outline" color="positive" /></q-item-section>
            <q-item-section>{{ gate }}</q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import NexusPageHero from '../components/NexusPageHero.vue'

const gates = [
  'Fresh clone installs with ./scripts/bootstrap.sh --full --open --certify',
  'Full Docker stack passes health checks',
  'Playwright passes against live services',
  'Physical Android device can pair, capture offline, reconnect, and sync',
  'Twilio/ntfy/Gmail/Microsoft connector sandbox tests pass when secrets are present',
  'Encrypted backup exports, uploads, restores, and verifies continuity',
  'Model runtime processes text/image/audio fallback and exposes readiness',
  'Signed Android and Tauri artifacts are generated or explicitly skipped with evidence'
]
</script>
