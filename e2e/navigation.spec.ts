import { expect, test } from '@playwright/test'

const routes = [
  ['/', 'Nexus Core'],
  ['/capture', 'Capture'],
  ['/tasks', 'Tasks'],
  ['/study-companion', 'Study'],
  ['/zettelkasten', 'Zettel'],
  ['/research', 'Research'],
  ['/geospatial', 'Geo'],
  ['/ar-memory', 'AR'],
  ['/automation', 'Automation'],
  ['/digital-twin', 'Digital'],
  ['/connectors', 'Connector'],
  ['/connector-worker', 'Worker'],
  ['/offline-queue', 'Offline'],
  ['/conflicts', 'Conflict'],
  ['/device-pairing', 'Pair'],
  ['/backup-restore', 'Backup'],
  ['/certification', 'Certification'],
  ['/release-center', 'Release'],
] as const

test.describe('premium shell navigation', () => {
  for (const [path, marker] of routes) {
    test(`renders ${path}`, async ({ page }) => {
      await page.goto(path)
      await expect(page.locator('body')).toContainText(new RegExp(marker, 'i'))
      await expect(page.locator('body')).toContainText(/Nexus Core|Personal OS/i)
    })
  }
})
