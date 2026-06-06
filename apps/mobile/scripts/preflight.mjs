import fs from 'node:fs'
import path from 'node:path'

const configPath = path.resolve('capacitor.config.ts')
const config = fs.readFileSync(configPath, 'utf8')
const required = ['appId', 'appName', 'webDir', 'LocalNotifications', 'allowNavigation']
const missing = required.filter((needle) => !config.includes(needle))
if (missing.length) {
  console.error(`Missing mobile Capacitor config keys: ${missing.join(', ')}`)
  process.exit(1)
}
if (!config.includes('*.ts.net')) {
  console.error('Mobile config must allow Tailscale *.ts.net navigation for private mesh development.')
  process.exit(1)
}
console.log('Mobile preflight passed.')
