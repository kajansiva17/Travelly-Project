import {test, expect} from '@playwright/test'

test('Register actions use a subtle glass finish without changing layout', async ({page}, testInfo) => {
  for (const [size, width, height] of [['desktop', 1440, 900], ['mobile', 390, 844]]) {
    await page.setViewportSize({width, height})
    await page.goto('/register')

    const styles = await page.evaluate(() => {
      const read = selector => {
        const element = document.querySelector(selector)
        if (!element) return null
        const style = getComputedStyle(element)
        const box = element.getBoundingClientRect()
        return {background: style.backgroundImage + style.backgroundColor, backdrop: style.backdropFilter, width: box.width, height: box.height}
      }
      return {
        submit: read('.register-page .auth-submit'),
        google: read('.register-page .google-button-unavailable'),
        country: read('.register-page .phone-country-trigger'),
        visibility: read('.register-page .visibility'),
      }
    })

    expect(styles.submit.backdrop).toContain('blur')
    expect(styles.submit.background).toContain('rgba')
    expect(styles.submit.width).toBeGreaterThan(0)
    if (styles.google) expect(styles.google.backdrop).toContain('blur')
    expect(styles.country.backdrop).toContain('blur')
    expect(styles.visibility.backdrop).toContain('blur')
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
    await expect(page.locator('.register-page .auth-submit')).toBeVisible()
    if (styles.google) await expect(page.locator('.register-page .google-button-unavailable')).toBeVisible()

    await page.locator('.auth-page').screenshot({path: testInfo.outputPath(`register-glass-${size}.png`)})
  }
})
