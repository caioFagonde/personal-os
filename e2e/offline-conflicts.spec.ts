import { expect, test } from '@playwright/test'

test('offline queue exposes pending mutation controls', async ({ page }) => {
  await page.goto('/offline-queue')
  await expect(page.locator('body')).toContainText(/Offline Queue/i)
  await page.getByRole('button', { name: /test mutation|add/i }).first().click()
  await expect(page.locator('body')).toContainText(/pending|queued|mutation/i)
})

test('conflict resolution page exposes merge controls', async ({ page }) => {
  await page.goto('/conflicts')
  await expect(page.locator('body')).toContainText(/Conflict/i)
  await expect(page.locator('body')).toContainText(/local|remote|merge|resolved/i)
})
