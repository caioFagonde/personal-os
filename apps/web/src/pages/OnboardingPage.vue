<template>
  <q-page class="q-pa-md column q-gutter-md">
    <section class="hero-panel">
      <div class="eyebrow">1-click operational setup</div>
      <h1>Onboarding Wizard</h1>
      <p>Run the bootstrap script, register this device, connect providers, test sync, subscribe to notifications, pair mobile, then create a backup.</p>
    </section>
    <q-stepper v-model="step" vertical color="primary" animated>
      <q-step :name="1" title="Install core" icon="mdi-console" :done="step > 1">
        <code>./scripts/bootstrap.sh --full</code>
        <q-stepper-navigation><q-btn color="primary" label="Continue" @click="step = 2" /></q-stepper-navigation>
      </q-step>
      <q-step :name="2" title="Connect providers" icon="mdi-connection" :done="step > 2">
        <p>Open Connectors and authorize Google/Microsoft, test Twilio/ntfy, and verify Tailscale.</p>
        <q-btn to="/connectors" color="primary" label="Open connectors" />
        <q-stepper-navigation><q-btn flat label="Continue" @click="step = 3" /></q-stepper-navigation>
      </q-step>
      <q-step :name="3" title="Pair devices" icon="mdi-cellphone-link" :done="step > 3">
        <q-btn to="/device-pairing" color="primary" label="Create pairing code" />
        <q-stepper-navigation><q-btn flat label="Continue" @click="step = 4" /></q-stepper-navigation>
      </q-step>
      <q-step :name="4" title="Backup and restore drill" icon="mdi-backup-restore">
        <q-btn to="/backup-restore" color="primary" label="Open backup" />
      </q-step>
    </q-stepper>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
const step = ref(1)
</script>
