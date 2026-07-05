// GREEN GLASS anti-slop contract tests (docs/DESIGN_LANGUAGE.md §R2.6).
// These read theme/config/component source as text: they lock the material
// system so it cannot silently regress into modern design-system idioms.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(__dirname, '../..')
const crt = readFileSync(resolve(root, 'src/css/nexus-crt.scss'), 'utf-8')
const quasarConfig = readFileSync(resolve(root, 'quasar.config.ts'), 'utf-8')
const fkeyBar = readFileSync(resolve(root, 'src/components/FKeyBar.vue'), 'utf-8')
const biosBoot = readFileSync(resolve(root, 'src/components/BiosBoot.vue'), 'utf-8')
const appVue = readFileSync(resolve(root, 'src/App.vue'), 'utf-8')

describe('theme layer (R2.1/R2.2)', () => {
  it('nexus-crt.scss loads after app.scss in the quasar css array', () => {
    const cssArray = quasarConfig.match(/css:\s*\[([^\]]*)\]/)?.[1] ?? ''
    const entries = cssArray.split(',').map((s) => s.replace(/['"\s]/g, ''))
    expect(entries.indexOf('nexus-crt.scss')).toBeGreaterThan(entries.indexOf('app.scss'))
  })

  it('remaps Quasar brand colors to the GREEN GLASS tokens', () => {
    expect(quasarConfig).toContain("primary: '#5DFF86'")
    expect(quasarConfig).toContain("warning: '#FFB347'")
    expect(quasarConfig).toContain("negative: '#FF6B5E'")
    expect(quasarConfig).toContain("dark: '#0A140C'")
  })

  it('uses exactly one font-family declaration chain (single face on glass)', () => {
    const declarations = (crt.match(/font-family:\s*[^;]+;/g) ?? [])
      .filter((d) => !d.includes('inherit')) // `inherit` re-points, it is not a second face
    expect(declarations).toHaveLength(1)
    expect(declarations[0]).toContain('VT323')
  })

  it('has zero box-shadow and zero border-radius on the glass (only resets)', () => {
    for (const match of crt.match(/box-shadow:\s*[^;]+;/g) ?? []) {
      expect(match).toContain('none')
    }
    for (const match of crt.match(/border-radius:\s*[^;]+;/g) ?? []) {
      expect(match).toMatch(/border-radius:\s*0/)
    }
  })

  it('never uses backdrop-filter except to disable it', () => {
    for (const match of crt.match(/backdrop-filter:\s*[^;]+;/g) ?? []) {
      expect(match).toContain('none')
    }
  })

  it('renders the raster overlay at a pitch of 4px or less', () => {
    const raster = crt.match(/repeating-linear-gradient\(0deg[\s\S]*?transparent\s+\d+px\s+(\d+)px/)
    expect(raster, 'raster overlay must exist').toBeTruthy()
    expect(Number(raster![1])).toBeLessThanOrEqual(4)
  })

  it('keeps the amber ≥2px focus-visible ring', () => {
    expect(crt).toMatch(/:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--nexus-warn\)/)
  })

  it('defines a prefers-reduced-motion block', () => {
    expect(crt).toContain('@media (prefers-reduced-motion: reduce)')
  })
})

describe('function-key bar (R2.3)', () => {
  it('renders at least 5 live-backed segments with no hardcoded metric values', () => {
    const keys = fkeyBar.match(/key:\s*'F\d+'/g) ?? []
    expect(keys.length).toBeGreaterThanOrEqual(5)
    // every non-static segment label is computed from fetched state
    expect(fkeyBar).toContain('syncState.value')
    expect(fkeyBar).toContain('queueCount.value')
    expect(fkeyBar).toContain('backupAge.value')
    expect(fkeyBar).toContain('agentCount.value')
    expect(fkeyBar).toContain('conflictCount.value')
  })

  it('is backed by the five live endpoints', () => {
    expect(fkeyBar).toContain('/api/sync/health')
    expect(fkeyBar).toContain('/api/sync/conflicts')
    expect(fkeyBar).toContain('/api/connectors/backup/manifests')
    expect(fkeyBar).toContain('/api/coding-agent/jobs')
    expect(fkeyBar).toContain('loadQueue') // Phase E: durable IndexedDB queue (was loadOfflineQueue)
  })

  it('binds working F-keys via a keydown handler and navigates on click', () => {
    expect(fkeyBar).toContain("window.addEventListener('keydown', onKeydown)")
    expect(fkeyBar).toContain('F_KEY_PATHS[event.key]')
    expect(fkeyBar).toContain('router.push')
    expect(appVue).toContain('<FKeyBar')
  })
})

describe('BIOS boot (R2.4)', () => {
  it('plays once per session and any key skips it', () => {
    expect(biosBoot).toContain('sessionStorage.getItem(SESSION_KEY)')
    expect(biosBoot).toContain("window.addEventListener('keydown', onKeydown)")
    expect(biosBoot).toMatch(/function onKeydown\(\)\s*\{\s*skip\(\)/)
  })

  it('bypasses entirely under prefers-reduced-motion', () => {
    expect(biosBoot).toContain('(prefers-reduced-motion: reduce)')
    expect(biosBoot).toMatch(/if \(reducedMotion\) return/)
  })

  it('reports honest service states from the gateway, never invented ones', () => {
    expect(biosBoot).toContain('/api/control/health')
    expect(biosBoot).toContain('DEGRADED')
    expect(biosBoot).toContain('DOWN')
    // no fabricated OK lines: every OK/DEGRADED string flows from state.ok
    expect(biosBoot).toContain("state.ok ? 'OK' : 'DEGRADED'")
    expect(appVue).toContain('<BiosBoot')
  })
})
