import type { CapacitorConfig } from '@capacitor/cli'

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
  }
}

export default config
