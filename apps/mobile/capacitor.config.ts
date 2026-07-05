import type { CapacitorConfig } from '@capacitor/cli'

// Phase E2: Android share-target + quick-capture.
// The share-sheet intent-filter and app shortcuts are native manifest entries
// applied from android-share-target.xml after `npx cap add android` (the archive
// ships no native project). The web routing/parsing lives in src/share-target.ts.
const config: CapacitorConfig = {
  appId: 'io.personalos.mobile',
  appName: 'Personal OS',
  webDir: '../web/dist/spa',
  bundledWebRuntime: false,
  server: {
    androidScheme: 'https',
    cleartext: true,
    allowNavigation: ['localhost', '127.0.0.1', '*.ts.net']
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
