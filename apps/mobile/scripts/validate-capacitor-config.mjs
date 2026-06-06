import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('../capacitor.config.ts', import.meta.url), 'utf8')
const required = [
  "appId: 'io.personalos.mobile'",
  "webDir: '../web/dist/spa'",
  "@capacitor/cli",
  'allowNavigation'
]
for (const needle of required) {
  if (!source.includes(needle) && !readFileSync(new URL('../package.json', import.meta.url), 'utf8').includes(needle)) {
    throw new Error(`missing required mobile config marker: ${needle}`)
  }
}
console.log('mobile capacitor config validated')
