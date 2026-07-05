import { test, expect } from '@playwright/test'

// Phase B exit criterion: capture → triage to task under a project →
// hybrid/lexical search finds it → neighbors shows the project edge.
// Runs against a live stack (same convention as live-stack.spec.ts).

const api = process.env.E2E_API_URL || 'http://127.0.0.1:8080'
const stamp = Date.now()
const needle = `graphloop-${stamp}`

async function register(request: import('@playwright/test').APIRequestContext): Promise<string> {
  const res = await request.post(`${api}/api/devices/register`, {
    data: { device_key: 'e2e-graph-loop', name: 'E2E Graph Loop', kind: 'web', platform: 'playwright' },
  })
  expect(res.status()).toBeLessThan(400)
  return (await res.json()).access_token
}

test.describe('graph & memory spine loop', () => {
  test('capture → task → project → search → neighbors', async ({ request }) => {
    const token = await register(request)
    const auth = { authorization: `Bearer ${token}` }

    // 1. Capture lands in the inbox and mints a task (capture-service dual-writes both).
    const captureRes = await request.post(`${api}/api/proxy/capture/api/capture`, {
      headers: auth,
      data: { text: `Review the pgvector index strategy ${needle}`, source_kind: 'quick_capture' },
    })
    expect(captureRes.status()).toBeLessThan(400)
    const captureBody = await captureRes.json()
    const taskId: string = captureBody.task.id
    expect(taskId).toBeTruthy()

    // 2. Create a project and triage the task under it.
    const projectRes = await request.post(`${api}/api/proxy/modules/api/projects`, {
      headers: auth,
      data: { name: `Graph Spine ${needle}`, pitch: 'Prove the Phase B loop end to end.' },
    })
    expect(projectRes.status()).toBeLessThan(400)
    const project = await projectRes.json()

    const patchRes = await request.patch(`${api}/api/proxy/capture/api/tasks/${taskId}`, {
      headers: auth,
      data: { project_id: project.id },
    })
    expect(patchRes.status()).toBeLessThan(400)

    // 3. Graph search finds the task; the response declares its mode honestly.
    const searchRes = await request.post(`${api}/api/graph/search`, {
      headers: auth,
      data: { text: needle, k: 10 },
    })
    expect(searchRes.status()).toBeLessThan(400)
    const search = await searchRes.json()
    expect(['hybrid', 'lexical']).toContain(search.mode)
    expect(search.label.length).toBeGreaterThan(0)
    if (search.mode === 'lexical') {
      expect(search.label).toContain('no embedding model')
    }
    const taskHit = search.hits.find((h: { object: { kind: string; domain_id: string } }) =>
      h.object.kind === 'task' && h.object.domain_id === taskId)
    expect(taskHit, 'graph search must find the triaged task').toBeTruthy()

    // 4. Neighbors of the task include the project (belongs_to_project edge)
    //    and the capture it was derived from.
    const neighborsRes = await request.get(`${api}/api/graph/objects/${taskHit.object.id}/neighbors`, {
      headers: auth,
    })
    expect(neighborsRes.status()).toBeLessThan(400)
    const neighbors = await neighborsRes.json()
    const rels = neighbors.map((n: { rel: string; object: { kind: string } }) => `${n.rel}:${n.object.kind}`)
    expect(rels).toContain('belongs_to_project:project')
    expect(rels).toContain('derived_from:capture_item')

    // 5. And from the project side, the task is visible as an inbound neighbor.
    const projectObjRes = await request.get(
      `${api}/api/graph/objects?kind=project&domain_id=${project.id}`, { headers: auth })
    const projectObjects = await projectObjRes.json()
    expect(projectObjects.length).toBe(1)
    const projectNeighborsRes = await request.get(
      `${api}/api/graph/objects/${projectObjects[0].id}/neighbors?rel=belongs_to_project`, { headers: auth })
    const projectNeighbors = await projectNeighborsRes.json()
    const inboundTask = projectNeighbors.find((n: { direction: string; object: { domain_id: string } }) =>
      n.direction === 'in' && n.object.domain_id === taskId)
    expect(inboundTask, 'project neighbors must include the triaged task').toBeTruthy()
  })

  test('daily state opens and closes through the vertical', async ({ request }) => {
    const token = await register(request)
    const auth = { authorization: `Bearer ${token}` }
    const openRes = await request.post(`${api}/api/proxy/modules/api/daily-state/open`, {
      headers: auth,
      data: { intention: `E2E intention ${needle}` },
    })
    expect(openRes.status()).toBeLessThan(400)
    const todayRes = await request.get(`${api}/api/proxy/modules/api/daily-state/today`, { headers: auth })
    const today = await todayRes.json()
    expect(today.opened).toBe(true)
  })
})
