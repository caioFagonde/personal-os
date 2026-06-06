import { test, expect } from '@playwright/test'

const base = process.env.E2E_BASE_URL || 'http://127.0.0.1:9000'
const api = process.env.E2E_API_URL || 'http://127.0.0.1:8080'

test.describe('live stack certification', () => {
  test('gateway health is reachable', async ({ request }) => {
    const res = await request.get(`${api}/health`)
    expect(res.status()).toBeLessThan(500)
    const body = await res.json()
    expect(body.service || body.status).toBeTruthy()
  })

  test('all critical UI surfaces render against running stack', async ({ page }) => {
    for (const path of ['/', '/capture', '/tasks', '/study-companion', '/zettelkasten', '/connectors', '/connector-worker', '/offline-queue', '/conflicts', '/model-runtime', '/live-stack', '/initial-readiness']) {
      await page.goto(`${base}${path}`)
      await expect(page.locator('body')).toContainText(/Nexus|Capture|Tasks|Runtime|Readiness|Stack|Connectors|Queue|Conflicts/i)
    }
  })

  test('model runtime proxy can process sample text when stack is live', async ({ request }) => {
    const tokenResponse = await request.post(`${api}/api/devices/register`, {
      data: { device_key: 'e2e-live-stack', name: 'E2E Live Stack', kind: 'web', platform: 'playwright' }
    })
    expect(tokenResponse.status()).toBeLessThan(400)
    const token = (await tokenResponse.json()).access_token
    const res = await request.post(`${api}/api/proxy/model-runtime/api/model-runtime/process-text`, {
      headers: { authorization: `Bearer ${token}` },
      data: { filename: 'e2e.txt', text: 'A diagram explains retrieval practice and spaced repetition.' }
    })
    expect(res.status()).toBeLessThan(500)
    const body = await res.json()
    expect(body.summary).toContain('Captured')
    expect(body.lookup_queries.length).toBeGreaterThan(0)
  })
})
