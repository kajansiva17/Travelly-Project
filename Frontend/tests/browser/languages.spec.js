import { test, expect } from '@playwright/test'
import { setup, visit } from './helpers/redesign.js'
import { translate } from '../../src/i18n/language.js'
import { workspaceMenu } from '../../src/routes/workspaceRoutes.js'
test.use({ screenshot: 'only-on-failure' })

async function selectLanguage(page, code) {
  const selector = page.locator('.language select')
  if (!await selector.isVisible() && await page.locator('.menu-toggle').isVisible()) await page.locator('.menu-toggle').click()
  await expect(selector).toBeVisible()
  await selector.selectOption(code)
  await expect(page.locator('html')).toHaveAttribute('lang', code)
}

async function fits(page) {
  const result = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth, offenders: [...document.querySelectorAll('main *')].filter(node => node.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(node => ({ tag: node.tagName, className: node.className, text: node.textContent.slice(0, 80), right: node.getBoundingClientRect().right })) }))
  expect(result.scroll, JSON.stringify(result)).toBeLessThanOrEqual(result.width + 1)
  const headerOverflow=await page.locator('.site-header .brand,.site-header .navigation,.site-header .navigation > *').evaluateAll(nodes=>nodes.filter(n=>{const r=n.getBoundingClientRect();return r.width&&(r.left<0||r.right>innerWidth+1)}).map(n=>n.className))
  expect(headerOverflow).toEqual([])
}

test('public pages switch immediately and retain search inputs and language after navigation and reload', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[name="pickup"]').fill('Colombo private fixture')
  for (const code of ['ta', 'si', 'en']) {
    await selectLanguage(page, code)
    await expect(page.locator('h1')).toContainText(translate('One account.', code))
    await expect(page.locator('input[name="pickup"]')).toHaveValue('Colombo private fixture')
    await fits(page)
  }
  await selectLanguage(page, 'ta')
  for (const path of ['/for-owners', '/drive-with-us', '/login']) {
    await visit(page, path)
    await expect(page.locator('html')).toHaveAttribute('lang', 'ta')
    await expect(page.locator('main')).toContainText(/[\u0B80-\u0BFF]/)
    await fits(page)
  }
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('lang', 'ta')
  await expect(page.locator('h1')).toHaveText(translate('Welcome back', 'ta'))
})

for (const code of ['ta', 'si']) {
  test(`${code} registration retains field values while switching and submits the original API codes`, async ({ page }) => {
    let payload
    await page.route('**/api/v1/auth/google/challenge', route => route.fulfill({ status: 503, json: { code: 'GOOGLE_NOT_CONFIGURED' } }))
    await page.route('**/api/v1/auth/register', route => { payload = route.request().postDataJSON(); return route.fulfill({ status: 201, json: { status: 'verification_required', email: 'language@example.com' } }) })
    await page.goto('/register')
    await page.locator('#full_name').fill('Language Test Person')
    await page.locator('#email').fill('language@example.com')
    await page.locator('#national_phone').fill('77 123 4567')
    await page.locator('#password').fill('BrowserTravelly1!')
    await page.locator('#confirm_password').fill('BrowserTravelly1!')
    await page.locator('input[name="accept_terms"]').check()
    await selectLanguage(page, code)
    await expect(page.locator('#full_name')).toHaveValue('Language Test Person')
    await expect(page.locator('#password')).toHaveValue('BrowserTravelly1!')
    await expect(page.locator('input[name="accept_terms"]')).toBeChecked()
    if (await page.locator('.menu-toggle').isVisible() && await page.locator('.navigation').evaluate(node => node.classList.contains('open'))) await page.locator('.menu-toggle').click()
    await fits(page)
    await page.locator('.auth-submit').click()
    await expect.poll(() => payload?.preferred_language).toBe(code)
    expect(payload).toMatchObject({ full_name: 'Language Test Person', email: 'language@example.com', phone_e164: '+94771234567', password: 'BrowserTravelly1!', preferred_language: code, accept_terms: true })
    expect(payload).not.toHaveProperty('confirm_password')
  })

  test(`${code} all workspaces translate, preserve names and routes, and keep operational menus usable`, async ({ page }) => {
    test.setTimeout(60000)
    await setup(page)
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    for (const role of ['OWNER', 'DRIVER', 'ADMIN', 'PASSENGER']) {
      await visit(page, role === 'PASSENGER' ? '/dashboard' : `/${role.toLowerCase()}/dashboard`)
      await expect(page.locator(role==='PASSENGER'?'.passenger-dashboard':`.workspace-shell[data-workspace="${role.toLowerCase()}"] .dashboard-overview`)).toBeVisible()
      await selectLanguage(page, code)
      await expect(page.locator('main')).toContainText(code === 'ta' ? /[\u0B80-\u0BFF]/ : /[\u0D80-\u0DFF]/)
      await expect(page.locator('header')).toContainText('Kasun Perera')
      await fits(page)
      if (role !== 'PASSENGER') {
        const trigger = page.locator('.workspace-menu-toggle')
        if (await trigger.isVisible()) await trigger.click()
        const sidebar = page.locator('.workspace-sidebar-links:visible')
        for (const item of workspaceMenu(role)) await expect(sidebar.getByRole('link', { name: translate(item.label, code), exact: true })).toHaveAttribute('href', item.path)
        const overflows = await sidebar.locator('.workspace-sidebar-link > span').evaluateAll(nodes => nodes.filter(node => node.scrollWidth > node.clientWidth + 1).map(node => node.textContent))
        expect(overflows).toEqual([])
        if (await page.locator('.workspace-drawer').isVisible()) await page.keyboard.press('Escape')
      }
      await selectLanguage(page, 'en')
    }
    expect(errors).toEqual([])
  })

  test(`${code} Admin filters retain enum values and selected filters across language changes`, async ({ page }) => {
    const state = await setup(page)
    await visit(page, '/admin/applications')
    await expect(page.locator('.workspace-shell[data-workspace="admin"] .language select')).toBeVisible()
    await selectLanguage(page, code)
    const status = page.locator('select').filter({ has: page.locator('option[value="REJECTED"]') })
    await status.selectOption('REJECTED')
    await expect(status).toHaveValue('REJECTED')
    await selectLanguage(page, 'en')
    await expect(status).toHaveValue('REJECTED')
    expect(state.requests.filter(([method, path]) => method !== 'GET' && !path.startsWith('/auth/'))).toEqual([])
  })
}
