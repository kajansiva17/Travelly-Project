import { test, expect } from '@playwright/test'
import { setup, visit } from './helpers/redesign.js'

const roles = [['admin', '/admin/dashboard'], ['owner', '/owner/dashboard'], ['driver', '/driver/dashboard'], ['passenger', '/dashboard']]
for (const [width, height] of [[1600, 900], [1024, 900], [390, 844], [320, 640]]) {
  test(`four role dashboards use real-state glass layout at ${width}×${height}`, async ({ page }, info) => {
    test.setTimeout(120000)
    await page.setViewportSize({ width, height })
    await setup(page)
    // Anonymous, empty fixtures verify unavailable/empty states without putting
    // reference-image sample records, personal data or vehicle plates in captures.
    await page.route('**/api/v1/users/me', r => r.fulfill({ json: { id: '12222222-2222-4222-8222-222222222222', full_name: 'Test User', account_status: 'ACTIVE', email_verified_at: '2026-01-01T00:00:00Z', approved_roles: ['PASSENGER','OWNER','DRIVER','ADMIN'] } }))
    await page.route('**/api/v1/bookings', r => r.fulfill({ json: { items: [] } }))
    await page.route('**/api/v1/owners/me/vehicles**', r => r.fulfill({ json: { items: [], total: 0, page: 1, has_next: false } }))
    await page.route('**/api/v1/admin/role-requests**', r => r.fulfill({ json: { items: [], total: 0 } }))
    await page.route('**/api/v1/admin/vehicles**', r => r.fulfill({ json: { items: [], total: 0 } }))
    for (const [role, route] of roles) {
      await visit(page, route)
      const root = page.locator(role === 'passenger' ? '.reference-passenger' : `.reference-${role}`)
      await expect(root.locator('h1')).toBeVisible()
      await expect(root.locator('.workspace-loading')).toHaveCount(0)
      await page.evaluate(() => document.fonts.ready)
      const overflow = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: innerWidth, out: [...document.querySelectorAll('body *')].filter(el => { const r = el.getBoundingClientRect(); return r.width && (r.right > innerWidth + 1 || r.left < -1) }).slice(0, 12).map(el => ({ tag: el.tagName, cls: typeof el.className === 'string' ? el.className : '', right: Math.round(el.getBoundingClientRect().right), left: Math.round(el.getBoundingClientRect().left) })) }))
      expect(overflow, JSON.stringify({ role, ...overflow })).toMatchObject({ width, viewport: width })
      const cards = await root.locator('.workspace-card').evaluateAll(nodes => nodes.map(node => {
        const r = node.getBoundingClientRect(), css = getComputedStyle(node)
        return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, color: css.color, background: css.backgroundImage }
      }))
      expect(cards.length).toBeGreaterThan(2)
      for (const card of cards) {
        expect(card.left).toBeGreaterThanOrEqual(-1)
        expect(card.right).toBeLessThanOrEqual(width + 1)
        expect(card.color).toBe(role === 'admin' ? 'rgb(11, 23, 69)' : 'rgb(10, 23, 69)')
        expect(card.background).toContain('gradient')
      }
      for (let i = 0; i < cards.length; i++) for (const b of cards.slice(i + 1)) {
        const a = cards[i]
        expect(a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1).toBe(false)
      }
      await root.locator('.workspace-card').last().scrollIntoViewIfNeeded()
      await page.evaluate(() => scrollTo(0, 0))
      await page.screenshot({ path: info.outputPath(`${role}-${width}.png`), fullPage: true })
      if (role === 'passenger') {
        await expect(root.getByText('No upcoming trips in your latest records.', { exact: false })).toBeVisible()
        await expect(root.getByText('Personalised destination suggestions are not available yet.')).toBeVisible()
        await expect(root.locator('.reference-destinations')).toHaveCount(0)
        expect(await root.locator('.search-submit').evaluate(el => getComputedStyle(el).backgroundImage)).toContain('rgb(255, 119, 126)')
      } else {
        await expect(root.locator('.workspace-metric').first()).toBeVisible()
        if (role === 'admin') {
          await expect(root.locator('.ref-admin-ai')).toBeVisible()
          await expect(root.locator('.ref-admin-ai button')).toHaveCount(2)
          await expect(root.locator('.ref-admin-ai button').first()).toBeDisabled()
        }
      }
    }
  })
}

test('all dashboard profiles use supplied account image and retain initials fallback', async ({ page }) => {
  test.setTimeout(90000)
  await setup(page)
  let image = '/images/travelly/branding/approved-2026-11-07/standard-logo.png'
  await page.route('**/api/v1/users/me', r => r.fulfill({ json: { id: '12222222-2222-4222-8222-222222222222', full_name: 'Test User', account_status: 'ACTIVE', email_verified_at: '2026-01-01T00:00:00Z', approved_roles: ['PASSENGER','OWNER','DRIVER','ADMIN'], profile_image_url: image } }))
  for (const [role, route] of roles) {
    await visit(page, route)
    await expect(page.locator(role === 'passenger' ? '.reference-passenger h1' : `.reference-${role} h1`)).toBeVisible()
    await expect(page.locator('.dashboard-avatar img')).toHaveAttribute('src', image)
  }
  image = ''
  for (const [role, route] of roles) {
    await visit(page, route)
    await expect(page.locator(role === 'passenger' ? '.reference-passenger h1' : `.reference-${role} h1`)).toBeVisible()
    await expect(page.locator('.dashboard-avatar img')).toHaveCount(0)
    await expect(page.locator('.dashboard-avatar')).toHaveText('T')
  }
  image = '/__missing-dashboard-avatar__.png'
  await page.route('**/__missing-dashboard-avatar__.png', r => r.fulfill({ status: 404, body: '' }))
  for (const [role, route] of roles) {
    await visit(page, route)
    await expect(page.locator(role === 'passenger' ? '.reference-passenger h1' : `.reference-${role} h1`)).toBeVisible()
    await expect(page.locator('.dashboard-avatar')).toHaveText('T')
    await expect(page.locator('.dashboard-avatar img')).toHaveCount(0)
  }
})

test('nested workspace routes retain the approved light-glass shell', async ({ page }) => {
  test.setTimeout(90000)
  await page.setViewportSize({ width: 1366, height: 768 })
  await setup(page)
  await page.route('**/api/v1/users/me', r => r.fulfill({ json: { id: '12222222-2222-4222-8222-222222222222', full_name: 'Test User', account_status: 'ACTIVE', email_verified_at: '2026-01-01T00:00:00Z', approved_roles: ['PASSENGER', 'OWNER', 'DRIVER', 'ADMIN'] } }))
  await page.route('**/api/v1/admin/role-requests**', r => r.fulfill({ json: { items: [], total: 0, page: 1, has_next: false } }))
  await page.route('**/api/v1/bookings**', r => r.fulfill({ json: { items: [] } }))

  for (const route of ['/admin/applications', '/owner/settings', '/driver/assignments']) {
    await visit(page, route)
    const shell = page.locator('.workspace-shell')
    await expect(shell).toBeVisible()
    const colors = await shell.evaluate(element => {
      const header = element.querySelector('.workspace-topbar .header-inner')
      const sidebar = element.querySelector('.workspace-sidebar')
      return {
        shell: getComputedStyle(element).backgroundImage,
        header: getComputedStyle(header).backgroundImage,
        headerColor: getComputedStyle(header).color,
        sidebar: getComputedStyle(sidebar).backgroundImage,
      }
    })
    expect(colors.shell).toContain('travelly-dashboard-sigiriya-background.png')
    expect(colors.header).toContain('gradient')
    expect(['rgb(11, 23, 69)', 'rgb(10, 23, 69)', 'rgb(7, 22, 69)']).toContain(colors.headerColor)
    expect(colors.sidebar).toContain(route.startsWith('/admin/') || route.startsWith('/owner/') || route.startsWith('/driver/') ? 'rgba(40, 75, 58' : 'rgba(45, 78, 87')
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(1366)
    if (route === '/admin/applications') {
      const panel = page.locator('.review-panel')
      await expect(panel).toBeVisible()
      expect(await panel.evaluate(element => getComputedStyle(element).color)).toBe('rgb(11, 23, 69)')
      expect(await panel.evaluate(element => getComputedStyle(element).backgroundImage)).toContain('gradient')
    }
  }
})
