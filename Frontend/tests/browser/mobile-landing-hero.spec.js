import { test, expect } from '@playwright/test'

const phoneWidths = [320, 360, 375, 390, 430]

for (const [route, role] of [['/drive-with-us', 'driver'], ['/for-owners', 'owner']]) {
  for (const language of ['en', 'ta', 'si']) {
    test(`${role} mobile hero keeps the supplied scene complete and reachable in ${language}`, async ({ page }) => {
      await page.addInitScript(value => localStorage.setItem('travelly-language', value), language)
      for (const width of phoneWidths) {
        await page.setViewportSize({ width, height: width === 375 ? 498 : 800 })
        await page.goto(route)
        await page.evaluate(() => document.fonts.ready)
        await expect(page.locator('html')).toHaveAttribute('lang', language)
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)

        const state = await page.locator('.lr-hero').evaluate(hero => {
          const art = hero.querySelector('.lr-hero-art')
          const copy = hero.querySelector('.lr-hero-copy')
          const menu = document.querySelector('.lr-header .lr-menu')
          const logo = document.querySelector('.lr-header .brand.travelly-brand')
          const heroBox = hero.getBoundingClientRect()
          const artBox = art.getBoundingClientRect()
          const menuBox = menu.getBoundingClientRect()
          return {
            artPosition: getComputedStyle(art).position,
            artFollowsCopy: artBox.top >= copy.getBoundingClientRect().bottom - 1,
            artRatio: artBox.width / artBox.height,
            artFillsViewport: Math.abs(artBox.width - innerWidth) < 1,
            copyFitsHero: copy.getBoundingClientRect().bottom <= heroBox.bottom + 1,
            logoWidth: logo.getBoundingClientRect().width,
            menuUsable: menuBox.width >= 44 && menuBox.height >= 44
          }
        })
        expect(state.artPosition).toBe('relative')
        expect(state.artFollowsCopy).toBe(true)
        expect(state.artRatio).toBeCloseTo(1672 / 941, 2)
        expect(state.artFillsViewport).toBe(true)
        expect(state.copyFitsHero).toBe(true)
        expect(state.menuUsable).toBe(true)
        expect(state.logoWidth).toBeGreaterThanOrEqual(128)
        await page.locator('.lr-menu').click()
        await page.waitForTimeout(300) // LandingHeader's ResizeObserver updates the hero offset after the in-flow menu expands.
        await expect.poll(() => page.locator('.lr-page').evaluate(root => {
          const menu = root.querySelector('.lr-nav-open').getBoundingClientRect()
          const title = root.querySelector('.lr-hero h1').getBoundingClientRect()
          return title.top >= menu.bottom + 16
        })).toBe(true)
        const menuState = await page.locator('.lr-nav-open').evaluate(menu => {
          const links = [...menu.querySelectorAll('.lr-nav-link')]
          return {
            withinViewport: menu.getBoundingClientRect().left >= -1 && menu.getBoundingClientRect().right <= innerWidth + 1,
            readable: links.every(link => {
              const box = link.getBoundingClientRect()
              return getComputedStyle(link).whiteSpace === 'nowrap' && box.left >= menu.getBoundingClientRect().left - 1 && box.right <= menu.getBoundingClientRect().right + 1
            }),
            aligned: links.every(link => getComputedStyle(link).display === 'flex' && link.getBoundingClientRect().height >= 44)
          }
        })
        expect(menuState).toEqual({ withinViewport: true, readable: true, aligned: true })
        await page.locator('.lr-menu').click()
        await page.locator('.lr-hero-actions').scrollIntoViewIfNeeded()
        await expect(page.locator('.lr-hero-actions a, .lr-hero-actions button').first()).toBeVisible()
      }
    })
  }

  test(`${role} desktop hero remains the desktop background layout`, async ({ page }) => {
    for (const width of [1280, 1366]) {
      await page.setViewportSize({ width, height: 585 })
      await page.goto(route)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await expect(page.locator('.lr-hero-art')).toHaveCSS('position', 'absolute')
    }
  })
}

for (const path of ['/login', '/register']) {
  test(`auth header keeps a readable logo at phone widths: ${path}`, async ({ page }) => {
    for (const width of phoneWidths) {
      await page.setViewportSize({ width, height: width === 375 ? 498 : 800 })
      await page.goto(path)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      const brand = page.getByRole('link', { name: 'Travelly home', exact: true })
      await expect(brand).toBeVisible()
      expect(await brand.evaluate(el => el.getBoundingClientRect().width)).toBeGreaterThanOrEqual(130)
    }
  })
}

test('Passenger public header keeps the landing logo and menu usable on phones', async ({ page }) => {
  for (const width of phoneWidths) {
    await page.setViewportSize({ width, height: width === 375 ? 498 : 800 })
    await page.goto('/')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const headerState = await page.locator('.lr-header').evaluate(header => {
      const logo = header.querySelector('.brand.travelly-brand').getBoundingClientRect()
      const menu = header.querySelector('.lr-menu').getBoundingClientRect()
      return { logoWidth: logo.width, menuUsable: menu.width >= 44 && menu.height >= 44 }
    })
    expect(headerState.logoWidth).toBeGreaterThanOrEqual(128)
    expect(headerState.menuUsable).toBe(true)
  }
})
