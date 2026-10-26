import { test, expect } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

async function captured(email, route) {
  const root = path.resolve('../.tools/auth-browser-mail')
  for (const name of await fs.readdir(root)) {
    const content = (await fs.readFile(path.join(root, name), 'utf8')).replace(/=\r?\n/g, '').replace(/=3D/g, '=')
    if (content.includes(`To: ${email}`) && content.includes(`/${route}#token=`)) return content.match(/#token=([A-Za-z0-9_-]+)/)[1]
  }
  throw new Error('Expected locally captured email was not found')
}

async function login(page, email, password) {
  await page.goto('/login')
  await page.getByLabel('Email address', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Log in', exact: true }).click()
}

test('real API: validation, capture, verification, login, recovery and new-password login', async ({ page }, info) => {
  const email = `browser-${info.project.name}-${Date.now()}@example.com`
  const phone = '77' + String(Date.now() % 10000000).padStart(7, '0')
  await page.goto('/register')
  await page.getByLabel('Full name', { exact: true }).fill('Browser Passenger')
  await page.getByLabel('Email address', { exact: true }).fill('.bad@example.com')
  await page.getByLabel('Mobile number', { exact: true }).fill(phone)
  await page.getByLabel('Password', { exact: true }).fill('weak password')
  await page.locator('[name="accept_terms"]').check()
  await page.getByRole('button', { name: 'Create account', exact: true }).click()
  await expect(page.locator('#email-error')).toContainText('valid public email')
  await expect(page.locator('#password-error')).toContainText('uppercase')
  await expect(page.locator('#password-error')).toContainText('whitespace')
  await page.getByLabel('Email address', { exact: true }).fill(`  ${email.toUpperCase()}  `)
  await page.getByLabel('Password', { exact: true }).fill('BrowserTravelly1!')
  await page.screenshot({ path: info.outputPath('register.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('button', { name: 'Create account', exact: true }).click()
  await expect(page).toHaveURL(/\/check-email$/)
  await expect(page.getByText('Development email captured locally.', { exact: false })).toBeVisible()
  const token = await captured(email, 'verify-email')
  await login(page, email, 'BrowserTravelly1!')
  await expect(page).toHaveURL(/\/check-email$/)
  await page.goto('/verify-email#token=' + token)
  await expect(page).toHaveURL(/\/verify-email$/)
  await page.getByRole('button', { name: 'Verify email', exact: true }).click()
  await expect(page.getByText('Your email is verified.', { exact: false })).toBeVisible()
  await login(page, email, 'BrowserTravelly1!')
  await expect(page).toHaveURL(/\/dashboard$/)
  await page.evaluate(() => { history.pushState({}, '', '/account'); dispatchEvent(new PopStateEvent('popstate')) })
  await expect(page.getByRole('heading', { name: 'Sign-in and email verification' })).toBeVisible()
  await expect(page.getByText('Google: Not connected', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await page.getByRole('link', { name: 'Forgot password?' }).click()
  await page.getByLabel('Email address', { exact: true }).fill(email)
  await page.getByRole('button', { name: 'Request reset link' }).click()
  await expect(page.getByText('If this email belongs', { exact: false })).toBeVisible()
  const resetToken = await captured(email, 'reset-password')
  await page.goto('/reset-password#token=' + resetToken)
  await page.getByLabel('New password', { exact: true }).fill('NewBrowserTravelly2!')
  await page.getByRole('button', { name: 'Save new password' }).click()
  await expect(page.getByText('Your password has been changed', { exact: false })).toBeVisible()
  await login(page, email, 'NewBrowserTravelly2!')
  await expect(page).toHaveURL(/\/dashboard$/)
})

test('legacy account keeps old password login and gets verification path', async ({ page }, info) => {
  await login(page, `legacy-${info.project.name}@example.com`, 'old password with spaces')
  await expect(page).toHaveURL(/\/dashboard$/)
  await page.evaluate(() => { history.pushState({}, '', '/account'); dispatchEvent(new PopStateEvent('popstate')) })
  await page.getByRole('button', { name: 'Verify my email' }).click()
  await expect(page).toHaveURL(/\/check-email$/)
  await expect(page.getByText('your existing account remains available', { exact: false })).toBeVisible()
})

test('login layout, Google configuration fallback and expired-link guidance', async ({ page }, info) => {
  await page.goto('/login')
  await expect(page.getByText('Google sign-in is not configured yet.', { exact: false })).toBeVisible()
  await page.screenshot({ path: info.outputPath('login.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.goto('/verify-email#token=' + 'x'.repeat(43))
  await page.getByRole('button', { name: 'Verify email', exact: true }).click()
  await expect(page.getByText('This link is invalid, expired or already used.', { exact: false })).toBeVisible()
  await page.screenshot({ path: info.outputPath('expired-link.png'), fullPage: true })
})
