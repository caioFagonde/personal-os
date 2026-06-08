<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="1-click operational setup" title="Onboarding Wizard" subtitle="Run the bootstrap script, register this device, connect providers, test sync, subscribe to notifications, pair mobile, then create a backup." />

    <q-stepper v-model="step" vertical color="primary" animated class="nexus-stepper">
      <q-step :name="1" title="Install core" icon="mdi-console" :done="step > 1">
        <p>Run the one-liner bootstrap to start all services:</p>
        <pre class="code-block">./scripts/bootstrap.sh --full</pre>
        <q-stepper-navigation>
          <q-btn color="primary" unelevated label="Continue" @click="step = 2" />
        </q-stepper-navigation>
      </q-step>
      <q-step :name="2" title="Connect providers" icon="mdi-connection" :done="step > 2">
        <p>Open Connectors and authorize Google/Microsoft, test Twilio/ntfy, and verify Tailscale.</p>
        <q-btn to="/connectors" color="primary" unelevated label="Open connectors" icon="mdi-open-in-new" class="q-mb-md" />
        <q-stepper-navigation>
          <q-btn outline color="primary" label="Continue" @click="step = 3" />
        </q-stepper-navigation>
      </q-step>
      <q-step :name="3" title="Pair devices" icon="mdi-cellphone-link" :done="step > 3">
        <p>Generate a pairing code for your mobile device.</p>
        <q-btn to="/device-pairing" color="primary" unelevated label="Create pairing code" icon="mdi-qrcode" class="q-mb-md" />
        <q-stepper-navigation>
          <q-btn outline color="primary" label="Continue" @click="step = 4" />
        </q-stepper-navigation>
      </q-step>
      <q-step :name="4" title="Backup and restore drill" icon="mdi-backup-restore">
        <p>Verify that backup/restore works before relying on it.</p>
        <q-btn to="/backup-restore" color="primary" unelevated label="Open backup" icon="mdi-cloud-upload-outline" />
      </q-step>
    </q-stepper>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
const step = ref(1)
</script>
<style scoped>
.nexus-stepper {
  background: var(--nexus-panel) !important;
}
</style>
