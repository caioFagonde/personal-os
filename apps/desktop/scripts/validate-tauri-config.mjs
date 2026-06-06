import { readFileSync } from 'node:fs'

const config = JSON.parse(readFileSync(new URL('../src-tauri/tauri.conf.json', import.meta.url), 'utf8'))
if (config.identifier !== 'io.personalos.desktop') throw new Error('unexpected desktop bundle identifier')
if (config.build.frontendDist !== '../web/dist/spa') throw new Error('desktop must reuse the shared Quasar build')
if (!config.app.security.csp.includes('connect-src')) throw new Error('desktop CSP must define connect-src')
console.log('desktop tauri config validated')
