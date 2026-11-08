import {test,expect} from '@playwright/test'

test('registration phone field keeps a compact code selector and larger aligned number input', async ({page}, testInfo) => {
  for (const [size, width, height] of [['desktop', 1440, 900], ['mobile', 375, 812], ['mobile', 390, 844], ['mobile', 360, 640]]) {
    await page.setViewportSize({width, height})
    await page.goto('/register')

    const row = page.locator('.register-phone-row')
    const country = row.locator('.phone-country-trigger')
    const number = row.locator('#national_phone')
    const boxes = await Promise.all([country, number].map(locator => locator.evaluate(element => {
      const {x, y, width, height} = element.getBoundingClientRect()
      return {x, y, width, height}
    })))
    const ratio = await row.evaluate(element => {
      const bounds = element.getBoundingClientRect()
      const code = element.querySelector('.phone-country-trigger').getBoundingClientRect()
      const number = element.querySelector('#national_phone').getBoundingClientRect()
      return {country: code.width / bounds.width, number: number.width / bounds.width}
    })

    expect(boxes[1].width).toBeGreaterThan(boxes[0].width * 1.3)
    if (size === 'desktop') {
      expect(ratio.country).toBeGreaterThanOrEqual(0.34)
      expect(ratio.country).toBeLessThanOrEqual(0.36)
      expect(ratio.number).toBeGreaterThanOrEqual(0.64)
      expect(ratio.number).toBeLessThanOrEqual(0.66)
    } else {
      expect(ratio.country).toBeGreaterThanOrEqual(0.29)
      expect(ratio.country).toBeLessThanOrEqual(0.32)
      expect(ratio.number).toBeGreaterThan(0.68)
    }
    expect(Math.abs(boxes[0].height - boxes[1].height)).toBeLessThanOrEqual(1)
    expect(Math.abs(boxes[0].y - boxes[1].y)).toBeLessThanOrEqual(1)
    expect(boxes[1].x).toBeGreaterThan(boxes[0].x)
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
    await expect(country).toHaveAttribute('aria-haspopup', 'dialog')
    await expect(country).toHaveAttribute('aria-label', /Country code:/)
    await expect(country.locator('.phone-country-iso')).toBeHidden()
    await expect(country.locator('span').last()).toHaveText(/^\+\d+$/)
    await expect(country.locator('svg')).toBeVisible()
    await expect(number).toBeVisible()

    if (size === 'desktop') {
      await page.locator('.auth-page').screenshot({path: testInfo.outputPath('register-phone-desktop.png')})
    } else if (width === 390) {
      await page.locator('.auth-page').screenshot({path: testInfo.outputPath('register-phone-mobile.png')})
    }
  }
})
