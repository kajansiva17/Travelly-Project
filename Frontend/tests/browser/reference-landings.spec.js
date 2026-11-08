import { test, expect } from '@playwright/test'
import { landingContent } from '../../src/features/landing/landingContent.js'
import { messages } from '../../src/i18n/messages.js'
import { setup, visit } from './helpers/redesign.js'

const routes = [['home', '/'], ['driver', '/drive-with-us'], ['owner', '/for-owners']]
for (const [role, route] of routes) {
  test(`${role} approved reference content, real controls and full-page capture`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 948, height: 1659 })
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(route)
    await expect(page.locator('.lr-page')).toBeVisible()
    await expect(page.locator('.lr-hero-scene')).toHaveCount(1)
    await expect(page.locator('.lr-hero-regions')).toHaveCount(0)
    await page.evaluate(() => document.fonts.ready)
    await expect(page.locator('.lr-nav-link[aria-current=page]')).toHaveAttribute('href', route)
    await expect(page.locator('.lr-hero h1')).toHaveText(landingContent[role].title)
    for (const [question, answer] of landingContent[role].faq) {
      const button = page.getByRole('button', { name: question, exact: true })
      await expect(button).toHaveAttribute('aria-expanded', 'true')
      await expect(page.getByRole('region', { name: question, exact: true })).toHaveText(answer)
    }
    for (const [file, , title, copy] of [...landingContent[role].firstCards, ...landingContent[role].secondCards]) {
      await expect(page.locator('.lr-card').filter({ has: page.getByRole('heading', { name: title, exact: true }) })).toContainText(copy)
      const image = page.locator(`.lr-card-photo[data-artwork="${file}"]`)
      await image.scrollIntoViewIfNeeded()
      await expect.poll(() => image.evaluate(el => el.complete && el.naturalWidth > 0)).toBe(true)
    }
    await page.locator('.lr-footer').scrollIntoViewIfNeeded()
    await page.evaluate(() => scrollTo(0, 0))
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(948)
    const footer = await page.locator('.lr-footer').boundingBox()
    // The approved spacing follow-up intentionally grows the page beyond the
    // old 1659px screenshot canvas. The footer must follow all real content.
    const cta = await page.locator('.lr-cta').boundingBox()
    expect(footer.y - (cta.y + cta.height)).toBeGreaterThanOrEqual(35)
    await page.screenshot({ path: testInfo.outputPath(`${role}-948x1659.png`), fullPage: true })
    expect(errors).toEqual([])
    await expect(page.locator('main')).not.toHaveCSS('background-image', /reference/)
  })

  test(`${role} role-specific registration and sign-in preserve existing journey intent`, async ({ page }) => {
    await page.goto(route)
    const suffix = role === 'home' ? '' : `?journey=${role}`
    await expect(page.locator('.lr-signup')).toHaveAttribute('href', `/register${suffix}`)
    await expect(page.locator('.lr-login')).toHaveAttribute('href', `/login${suffix}`)
    await expect(page.locator('.lr-cta a').first()).toHaveAttribute('href', `/register${suffix}`)
    await expect(page.locator('.lr-cta a').last()).toHaveAttribute('href', `/login${suffix}`)
    await page.locator('.lr-cta a').last().click()
    await expect(page).toHaveURL(new RegExp(`/login${suffix.replace('?', '\\?')}$`))
  })

  test(`${role} FAQ initial state and keyboard navigation`, async ({ page }) => {
    await page.goto(route)
    const buttons = page.locator('.lr-faq h3 button')
    await buttons.first().focus()
    await page.keyboard.press('Enter')
    await expect(buttons.first()).toHaveAttribute('aria-expanded', 'false')
    await expect(page.locator('.lr-faq [role=region]').first()).toBeHidden()
    await page.keyboard.press('Space')
    await expect(buttons.first()).toHaveAttribute('aria-expanded', 'true')
    await page.keyboard.press('ArrowDown')
    await expect(buttons.nth(1)).toBeFocused()
    await page.keyboard.press('End')
    await expect(buttons.last()).toBeFocused()
    await page.keyboard.press('Home')
    await expect(buttons.first()).toBeFocused()
  })

  for (const language of ['en', 'ta', 'si']) test(`${role} ${language} responsive layout, navigation and language`, async ({ page }, testInfo) => {
    test.setTimeout(60000) // Five complete PNG-heavy page visits and a full-page capture.
    await page.addInitScript(code => localStorage.setItem('travelly-language', code), language)
    for (const width of [320, 390, 768, 948, 1366]) {
      await page.setViewportSize({ width, height: 900 })
      await page.goto(route)
      await expect(page.locator('.lr-page')).toBeVisible()
      await page.evaluate(() => document.fonts.ready)
      await expect(page.locator('html')).toHaveAttribute('lang', language)
      const title = landingContent[role].title
      await expect(page.locator('h1')).toHaveText(language === 'en' ? title : messages[title][language])
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      if (width < 761) await page.locator('.lr-menu').click()
      else await expect(page.locator('.lr-menu')).toBeHidden()
      await expect(page.locator('.lr-nav')).toBeVisible()
      const out = await page.locator('.lr-header').evaluate(header => [...header.querySelectorAll('a,button,select')].filter(el => el.getClientRects().length).filter(el => { const r = el.getBoundingClientRect(); return r.left < -1 || r.right > innerWidth + 1 }).map(el => el.textContent))
      expect(out).toEqual([])
      const overlaps = await page.locator('.lr-nav').evaluate(nav => { const boxes = [...nav.children].map(el => el.getBoundingClientRect()); return boxes.some((a, i) => boxes.slice(i + 1).some(b => a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1)) })
      expect(overlaps).toBe(false)
      const stepOverlaps=await page.locator('.lr-home .lr-steps li').evaluateAll(items=>items.some(item=>{const p=item.querySelector('p'),icon=item.querySelector('svg:not(.lr-step-arrow)');if(!p||!icon)return false;const a=p.getBoundingClientRect(),b=icon.getBoundingClientRect();return a.left<b.right-1&&b.left<a.right-1&&a.top<b.bottom-1&&b.top<a.bottom-1}))
      expect(stepOverlaps).toBe(false)
      const clippedControls = await page.locator('.lr-page').evaluate(root => [...root.querySelectorAll('.lr-tabs [role=tab],.lr-footer nav>*')].filter(control => { const r = control.getBoundingClientRect(); return r.left < -1 || r.right > innerWidth + 1 || control.scrollWidth > control.clientWidth + 2 }).map(control => control.textContent))
      expect(clippedControls).toEqual([])
      if (width >= 761) {
        await expect.poll(() => page.locator('.lr-page').evaluate(root => root.querySelector('.lr-header').getBoundingClientRect().bottom <= root.querySelector('.lr-hero-copy').getBoundingClientRect().top)).toBe(true)
        expect(await page.locator('.lr-page').evaluate(root => root.querySelector('.lr-hero-copy').getBoundingClientRect().bottom <= root.querySelector('.lr-search')?.getBoundingClientRect().top || !root.querySelector('.lr-search'))).toBe(true)
        expect(await page.locator('.lr-page').evaluate(root => root.querySelector('.lr-hero-copy').getBoundingClientRect().bottom <= root.querySelector('.lr-content').getBoundingClientRect().top)).toBe(true)
      }
      if (width < 761) await page.locator('.lr-menu').click()
      await page.locator('.lr-footer').scrollIntoViewIfNeeded()
      await page.evaluate(() => scrollTo(0, 0))
      if (width === 390) await page.screenshot({ path: testInfo.outputPath(`${role}-${language}-390.png`), fullPage: true })
    }
  })
}

test('Home search preserves values, swaps places, requires an actual departure and hands the existing seed to Hire', async ({ page }) => {
  await page.route('**/api/service-types', route => route.fulfill({ json: { items: [] } }))
  await page.goto('/')
  const form = page.locator('#lr-search-fields')
  await expect(page.locator('#lr-date-value')).toContainText('Select date & time')
  await form.locator('[name=pickup]').fill('Colombo')
  await form.locator('[name=destination]').fill('Kandy')
  await page.getByRole('button', { name: 'Swap pickup and destination', exact: true }).click()
  await expect(form.locator('[name=pickup]')).toHaveValue('Kandy')
  await expect(form.locator('[name=destination]')).toHaveValue('Colombo')
  await page.locator('.lr-search-submit').click()
  await expect(page.locator('.lr-date-picker')).toBeVisible()
  await expect(page.locator('[name=departure]')).toBeFocused()
  await page.locator('[name=departure]').fill('2020-01-01T12:30')
  await page.getByRole('button', { name: 'Apply', exact: true }).click()
  await expect(page.locator('.lr-date-picker')).toBeVisible()
  const future = new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 10) + 'T12:30'
  await page.locator('[name=departure]').fill(future)
  await page.getByRole('button', { name: 'Apply', exact: true }).click()
  await expect(page.locator('.lr-date-picker')).toBeHidden()
  await expect(page.locator('#lr-date-value')).toContainText('12:30')
  const menu = page.locator('.lr-menu')
  if (await menu.isVisible()) await menu.click()
  await page.locator('.lr-language select').selectOption('ta')
  if (await menu.isVisible()) await menu.click()
  await expect(form.locator('[name=pickup]')).toHaveValue('Kandy')
  await expect(form.locator('[name=departure]')).toHaveValue(future)
  await page.locator('.lr-search-submit').click()
  await expect(page).toHaveURL(/\/hire$/)
  const seed = await page.evaluate(() => history.state.usr.seed)
  expect(seed).toEqual({ pickup: 'Kandy', destination: 'Colombo', departure: future })
  await expect(page.locator('.trip-stop input[type=search]').nth(0)).toHaveValue('Kandy')
  await expect(page.locator('.trip-stop input[type=search]').nth(1)).toHaveValue('Colombo')
  await expect(page.locator('.trip-plan-form input[type=datetime-local]')).toHaveValue(future)
})

test('Tickets, Rentals and unavailable card actions show honest notices; tabs work with keyboard', async ({ page }) => {
  await page.goto('/')
  const tabs = page.locator('.lr-tabs [role=tab]')
  await tabs.first().focus()
  await page.keyboard.press('ArrowRight')
  await expect(tabs.nth(1)).toBeFocused()
  await expect(tabs.nth(1)).toHaveAttribute('aria-selected', 'true')
  await page.locator('.lr-search-submit').click()
  await expect(page.getByRole('dialog')).toContainText('Scheduled ticket search and checkout are not available yet.')
  await page.keyboard.press('Escape')
  await tabs.nth(1).focus()
  await page.keyboard.press('End')
  await expect(tabs.last()).toBeFocused()
  await page.locator('.lr-search-submit').click()
  await expect(page.getByRole('dialog')).toContainText('Rental checkout is not available yet.')
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Airport Pickup & Drop', exact: true }).click()
  await expect(page.getByRole('dialog')).toContainText('Only Long-distance private hire is currently available.')
})

test('landing module does not enter Passenger or operational workspace dashboards', async ({ page }) => {
  await setup(page)
  for (const path of ['/dashboard', '/owner/dashboard', '/driver/dashboard', '/admin/dashboard']) {
    await visit(page, path)
    await expect(page.locator('.lr-page')).toHaveCount(0)
    await expect(page.locator(path === '/dashboard' ? '.passenger-dashboard' : '.workspace-shell')).toBeVisible()
  }
})
