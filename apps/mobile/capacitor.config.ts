import type { CapacitorConfig } from '@capacitor/cli'

// Phase E2: Android share-target + quick-capture.
// The share-sheet intent-filter and app shortcuts are native manifest entries
// applied from android-share-target.xml after `npx cap add android` (the archive
// ships no native project). The web routing/parsing lives in src/share-target.ts.
//
// THIN-SHELL MODE (first-usable deploy):
// Set MOBILE_SERVER_URL to the PC's Tailscale web URL (e.g.
// `https://nexus-pc.tailnet-name.ts.net`) before `pnpm cap:sync` / building the
// APK. When set, the WebView loads the LIVE web UI served by the PC instead of
// the bundled snapshot, so shipping web changes needs no new APK — only native
// (plugin/permission) changes do. Leave it unset to bundle the SPA offline.
const serverUrl = (process.env.MOBILE_SERVER_URL || '').trim()

const allowNavigation = ['localhost', '127.0.0.1', '*.ts.net']
if (serverUrl) {
  try {
    allowNavigation.push(new URL(serverUrl).hostname)
  } catch {
    throw new Error(`MOBILE_SERVER_URL is not a valid URL: ${serverUrl}`)
  }
}

const config: CapacitorConfig = {
  appId: 'io.personalos.mobile',
  appName: 'Personal OS',
  webDir: '../web/dist/spa',
  bundledWebRuntime: false,
  server: {
    androidScheme: 'https',
    cleartext: true,
    allowNavigation,
    // Thin shell: only present when MOBILE_SERVER_URL is set at build time.
    ...(serverUrl ? { url: serverUrl } : {})
  },
  plugins: {
    LocalNotifications: {
      smallIcon: 'ic_stat_name',
      iconColor: '#1976D2',
      sound: 'default'
    }
  },
  // shareTarget: text/plain, text/* and image/* → deep-link /capture (queue-first).
  // appShortcuts: Capture · New task · Today (long-press launcher icon).
  // Both are declared natively via android-share-target.xml.
}

export default config
