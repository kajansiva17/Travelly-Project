import { test, expect } from '@playwright/test'

for (const [role, route] of [['home', '/'], ['driver', '/drive-with-us'], ['owner', '/for-owners']]) {
  for (const language of ['en', 'ta', 'si']) {
    test(`${role} ${language} cards stay equal, separated and readable`, async ({ page }) => {
      test.setTimeout(90000)
      await page.addInitScript(code => localStorage.setItem('travelly-language', code), language)
      for (const width of [320, 390, 768, 1280]) {
        await page.setViewportSize({ width, height: 900 })
        await page.goto(route)
        await page.locator('.lr-page').waitFor()
        await page.evaluate(() => document.fonts.ready)
        const result = await page.locator('.lr-cards').evaluateAll(grids => grids.map(grid => {
          const cards = [...grid.querySelectorAll('.lr-card')]
          const boxes = cards.map(card => {
            const box = card.getBoundingClientRect()
            const body = card.querySelector('.lr-card-body').getBoundingClientRect()
            const text = [...card.querySelectorAll('h3,p')].map(node => {
              const r = node.getBoundingClientRect()
              return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, overflow: node.scrollHeight > node.clientHeight + 2 || node.scrollWidth > node.clientWidth + 2 }
            })
            return { top: box.top, bottom: box.bottom, left: box.left, right: box.right, width: box.width, height: box.height, bodyTop: body.top, bodyBottom: body.bottom, text }
          })
          const css = getComputedStyle(grid)
          return { columnGap: parseFloat(css.columnGap), rowGap: parseFloat(css.rowGap), boxes }
        }))
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
        for (const grid of result) {
          expect(grid.columnGap).toBeGreaterThanOrEqual(24)
          expect(grid.rowGap).toBeGreaterThanOrEqual(24)
          const first = grid.boxes[0]
          for (const card of grid.boxes) {
            expect(Math.abs(card.width - first.width)).toBeLessThan(1)
            expect(Math.abs(card.height - first.height)).toBeLessThan(1)
            expect(card.bodyTop).toBeGreaterThanOrEqual(card.top - 1)
            expect(card.bodyBottom).toBeLessThanOrEqual(card.bottom + 1)
            for (const text of card.text) {
              expect(text.overflow).toBe(false)
              expect(text.top).toBeGreaterThanOrEqual(card.top - 1)
              expect(text.bottom).toBeLessThanOrEqual(card.bottom + 1)
              expect(text.left).toBeGreaterThanOrEqual(card.left - 1)
              expect(text.right).toBeLessThanOrEqual(card.right + 1)
            }
          }
          for (let i = 0; i < grid.boxes.length; i++) for (const other of grid.boxes.slice(i + 1)) {
            const card = grid.boxes[i]
            const verticalOverlap = card.top < other.bottom - 1 && other.top < card.bottom - 1
            const horizontalOverlap = card.left < other.right - 1 && other.left < card.right - 1
            expect(verticalOverlap && horizontalOverlap).toBe(false)
            if (verticalOverlap) expect(Math.max(card.left, other.left) - Math.min(card.right, other.right)).toBeGreaterThanOrEqual(23)
            if (horizontalOverlap) expect(Math.max(card.top, other.top) - Math.min(card.bottom, other.bottom)).toBeGreaterThanOrEqual(23)
          }
        }
      }
    })
  }
}
