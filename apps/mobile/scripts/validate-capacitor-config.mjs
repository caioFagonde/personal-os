import { existsSync, readFileSync } from 'node:fs'

const source = readFileSync(new URL('../capacitor.config.ts', import.meta.url), 'utf8')
const required = [
  "appId: 'io.personalos.mobile'",
  "webDir: '../web/dist/spa'",
  "@capacitor/cli",
  'allowNavigation',
  'shareTarget', // Phase E2: share-sheet capture must stay documented in config
  'MOBILE_SERVER_URL' // thin-shell: live web UI over Tailscale, no APK rebuild for web changes
]
for (const needle of required) {
  if (!source.includes(needle) && !readFileSync(new URL('../package.json', import.meta.url), 'utf8').includes(needle)) {
    throw new Error(`missing required mobile config marker: ${needle}`)
  }
}

// Thin-shell contract: when MOBILE_SERVER_URL is set the config must turn it into
// a live server.url and whitelist its host; unset, it must bundle the SPA offline.
if (!source.includes('url: serverUrl') || !source.includes('new URL(serverUrl).hostname')) {
  throw new Error('capacitor.config.ts must map MOBILE_SERVER_URL to server.url + allowNavigation host')
}

// Phase E2: the native share-target/shortcuts fragment must exist to apply
// after `npx cap add android`.
if (!existsSync(new URL('../android-share-target.xml', import.meta.url))) {
  throw new Error('missing android-share-target.xml (share-target + app shortcuts fragment)')
}
const fragment = readFileSync(new URL('../android-share-target.xml', import.meta.url), 'utf8')
for (const needle of ['android.intent.action.SEND', 'image/*', 'shortcutId="capture"']) {
  if (!fragment.includes(needle)) {
    throw new Error(`android-share-target.xml missing: ${needle}`)
  }
}
console.log('mobile capacitor config + share-target validated')
