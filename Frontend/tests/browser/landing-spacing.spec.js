import { test, expect } from '@playwright/test'

for (const [role, route] of [['home', '/'], ['driver', '/drive-with-us'], ['owner', '/for-owners']]) {
  test(`${role} safe hero, search and section spacing at desktop and mobile sizes`, async ({ page }) => {
    test.setTimeout(60000)
    for (const [width, height] of [[948, 1659], [1260, 588], [1280, 900], [1880, 900], [390, 844], [320, 640]]) {
      await page.setViewportSize({ width, height })
      await page.goto(route)
      await page.locator('.lr-page').waitFor()
      await page.evaluate(() => document.fonts.ready)
      await expect.poll(() => page.locator('.lr-page').evaluate(root => {
        const header = root.querySelector('.lr-header').getBoundingClientRect()
        const copy = root.querySelector('.lr-hero-copy').getBoundingClientRect()
        return copy.top - header.bottom
      })).toBeGreaterThanOrEqual(31)
      const layout = await page.locator('.lr-page').evaluate(root => {
        const rect = selector => root.querySelector(selector).getBoundingClientRect()
        const header = rect('.lr-header'), hero = rect('.lr-hero'), copy = rect('.lr-hero-copy')
        const first = rect('.lr-first-section'), footer = rect('.lr-footer'), cta = rect('.lr-cta')
        const search = root.querySelector('.lr-search')?.getBoundingClientRect()
        return {
          overflow: document.documentElement.scrollWidth > innerWidth,
          zoom: getComputedStyle(root).zoom, scale: visualViewport.scale,
          top: header.top, centered: Math.abs(header.left - (innerWidth - header.right)), headerWidth: header.width,
          heroClearance: hero.bottom - copy.bottom, nextClearance: first.top - hero.bottom,
          footerGap: footer.top - cta.bottom,
          ownerArrowGaps: innerWidth >= 761 && root.classList.contains('lr-owner') ? [...root.querySelectorAll('.lr-steps li')].filter(el => el.querySelector('.lr-step-arrow')).map(el => el.querySelector('.lr-step-arrow').getBoundingClientRect().left - el.querySelector('h3').getBoundingClientRect().right) : [],
          search: search && { top: search.top, bottom: search.bottom, heroBottom: hero.bottom, copyBottom: copy.bottom },
          sections: [...root.querySelectorAll('.lr-content>section')].map(el => {
            const css = getComputedStyle(el)
            return { top: parseFloat(css.paddingTop), bottom: parseFloat(css.paddingBottom) }
          }),
          faq: [...root.querySelectorAll('.lr-faq-item')].map(el => {
            const card = el.getBoundingClientRect(), icon = el.querySelector('.lr-faq-icon').getBoundingClientRect()
            const arrow = el.querySelector('h3 button svg').getBoundingClientRect()
            const q = el.querySelector('h3').getBoundingClientRect(), a = el.querySelector('p').getBoundingClientRect()
            return { height: card.height, textGap: a.top - q.bottom, iconCenter: Math.abs(icon.y + icon.height / 2 - card.y - card.height / 2), arrowCenter: Math.abs(arrow.y + arrow.height / 2 - card.y - card.height / 2) }
          })
        }
      })
      expect(layout.overflow).toBe(false)
      expect(layout.zoom).toBe('1')
      expect(layout.scale).toBe(1)
      expect(layout.top).toBeGreaterThanOrEqual(16)
      expect(layout.centered).toBeLessThan(1)
      expect(layout.headerWidth).toBeLessThanOrEqual(1320)
      expect(layout.heroClearance).toBeGreaterThanOrEqual(23)
      expect(layout.nextClearance).toBeGreaterThanOrEqual(0)
      expect(layout.footerGap).toBeGreaterThanOrEqual(35)
      for (const gap of layout.ownerArrowGaps) expect(gap).toBeGreaterThanOrEqual(8)
      for (const section of layout.sections) {
        expect(section.top).toBeGreaterThanOrEqual(28)
        expect(section.bottom).toBeGreaterThanOrEqual(28)
      }
      for (const faq of layout.faq) {
        expect(faq.height).toBeGreaterThanOrEqual(108)
        expect(faq.textGap).toBeGreaterThanOrEqual(9)
        expect(faq.iconCenter).toBeLessThan(1)
        expect(faq.arrowCenter).toBeLessThan(2)
      }
      if (layout.search) {
        expect(layout.search.top - layout.search.copyBottom).toBeGreaterThanOrEqual(31)
        expect(layout.search.heroBottom - layout.search.bottom).toBeGreaterThanOrEqual(width >= 761 ? 19 : 23)
        if (width >= 761 && width / height > 1.25) expect(layout.search.heroBottom).toBeGreaterThanOrEqual(height)
        if (width === 1260 || width === 1280 || width === 1880) expect(layout.search.bottom).toBeLessThan(height)
      }
      if (width < 761) {
        await page.locator('.lr-menu').click()
        await expect(page.locator('.lr-nav')).toBeVisible()
        await expect.poll(() => page.locator('.lr-page').evaluate(root => {
          const nav = root.querySelector('.lr-nav').getBoundingClientRect()
          const copy = root.querySelector('.lr-hero-copy').getBoundingClientRect()
          return copy.top - nav.bottom
        })).toBeGreaterThan(30)
        await page.locator('.lr-menu').click()
      }
    }
  })
}
