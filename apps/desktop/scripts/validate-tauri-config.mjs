import { existsSync, readFileSync } from 'node:fs'

const config = JSON.parse(readFileSync(new URL('../src-tauri/tauri.conf.json', import.meta.url), 'utf8'))
if (config.identifier !== 'io.personalos.desktop') throw new Error('unexpected desktop bundle identifier')
if (config.build.frontendDist !== '../web/dist/spa') throw new Error('desktop must reuse the shared Quasar build')
if (!config.app.security.csp.includes('connect-src')) throw new Error('desktop CSP must define connect-src')

// Phase E3: tray icon + global-shortcut quick-capture wiring.
if (!config.app.trayIcon) throw new Error('desktop must declare a tray icon (Phase E3)')

const cargo = readFileSync(new URL('../src-tauri/Cargo.toml', import.meta.url), 'utf8')
for (const dep of ['tauri-plugin-global-shortcut', 'tauri-plugin-single-instance']) {
  if (!cargo.includes(dep)) throw new Error(`Cargo.toml missing ${dep}`)
}
if (!cargo.includes('tray-icon')) throw new Error('tauri crate must enable the tray-icon feature')

const mainRs = readFileSync(new URL('../src-tauri/src/main.rs', import.meta.url), 'utf8')
for (const needle of ['toggle_quick_capture', 'TrayIconBuilder', 'global_shortcut', 'single_instance']) {
  if (!mainRs.includes(needle)) throw new Error(`main.rs missing ${needle} wiring`)
}

if (!existsSync(new URL('../src-tauri/capabilities/default.json', import.meta.url))) {
  throw new Error('missing Tauri capabilities file for global-shortcut permissions')
}
const caps = readFileSync(new URL('../src-tauri/capabilities/default.json', import.meta.url), 'utf8')
if (!caps.includes('global-shortcut:allow-register')) throw new Error('capabilities missing global-shortcut register permission')

console.log('desktop tauri config + quick-capture/tray validated')
