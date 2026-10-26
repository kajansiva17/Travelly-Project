import { test, expect } from '@playwright/test'

async function setup(page, { mode = 'completion', authoritative = true } = {}) {
  const requests = []
  const user = { id: 'd59140a1-f9fb-4a37-9717-f97fc3e64f73', full_name: 'Google Test Passenger', email: 'member@example.com', account_status: 'ACTIVE', email_verified_at: '2026-10-26T01:00:00Z', approved_roles: ['PASSENGER'] }
  await page.route('https://accounts.google.com/gsi/client', route => route.fulfill({ contentType: 'application/javascript', body: `window.google={accounts:{id:{initialize(c){this.config=c},renderButton(host){const b=document.createElement('button');b.textContent='Continue with Google';b.style.cssText='width:100%;min-height:44px';b.onclick=()=>this.config.callback({credential:'test-google-credential'});host.appendChild(b)}}}};` }))
  await page.route('**/api/v1/**', async route => {
    const req = route.request(), path = new URL(req.url()).pathname
    const data = req.method() === 'POST' ? req.postDataJSON() : null
    requests.push({ path, data })
    let result, code = 200
    if (path.endsWith('/challenge')) result = { client_id: 'test-client', nonce: 'n'.repeat(43), challenge: 'c'.repeat(43) }
    else if (path === '/api/v1/auth/google') {
      if (mode === 'invalid') { code = 401; result = { message: 'Google sign-in could not be verified. Try again.' } }
      else result = mode === 'conflict' ? { status: 'link_required', message: 'A Travelly account already uses this email. Sign in using its existing method, then connect Google in Profile.' } : { status: 'completion_required', ticket: 't'.repeat(43), email: 'new@example.com', full_name: 'New Google Passenger' }
    } else if (path === '/api/v1/auth/google/complete') result = authoritative ? { access_token: 'test-access', refresh_token: 'test-refresh' } : { status: 'verification_required', verification_ticket: 'v'.repeat(43), email_delivery: 'captured', message: 'Development email captured locally. No message was sent to an inbox.' }
    else if (path === '/api/v1/auth/login') result = { access_token: 'test-access', refresh_token: 'test-refresh' }
    else if (path === '/api/v1/users/me') result = user
    else if (path === '/api/v1/users/me/roles') result = { items: [{ role_code: 'PASSENGER', approval_status: 'APPROVED' }] }
    else if (path === '/api/v1/users/me/auth-methods') result = { password: true, google: false, email_verified: true }
    else if (path === '/api/v1/users/me/google') result = { message: 'Google is connected to this same Travelly account. Your roles and records are unchanged.' }
    else if (path === '/api/v1/documents') result = { items: [], page: 1, has_next: false }
    else { code = 404; result = { message: 'Unavailable test endpoint.' } }
    return route.fulfill({ status: code, json: result })
  })
  return requests
}

for (const start of ['/login', '/register']) test(`Google on ${start} requires completion and terms before account creation`, async ({ page }) => {
  const requests = await setup(page)
  await page.goto(start)
  await page.getByRole('button', { name: 'Continue with Google', exact: true }).click()
  await expect(page).toHaveURL(/\/google-complete$/)
  expect(requests.filter(r => r.path.endsWith('/google/complete'))).toHaveLength(0)
  await page.getByRole('button', { name: 'Create Passenger account' }).click()
  await expect(page.getByText('Enter your mobile number.')).toBeVisible()
  await page.getByLabel('Mobile number', { exact: true }).fill('771234567')
  await page.getByRole('button', { name: 'Create Passenger account' }).click()
  await expect(page.getByText('Agree to the Terms and Privacy Policy to continue.')).toBeVisible()
  await page.locator('[name="accept_terms"]').check()
  await page.screenshot({ path: test.info().outputPath('google-completion.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('button', { name: 'Create Passenger account' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  const body = requests.find(r => r.path.endsWith('/google/complete')).data
  expect(body.phone_e164).toBe('+94771234567'); expect(body.accept_terms).toBe(true)
  expect(body).not.toHaveProperty('email'); expect(body).not.toHaveProperty('role_code')
})

test('third-party Google email requires Travelly verification', async ({ page }) => {
  await setup(page, { authoritative: false })
  await page.goto('/login'); await page.getByRole('button', { name: 'Continue with Google', exact: true }).click()
  await page.getByLabel('Mobile number', { exact: true }).fill('771234567')
  await page.locator('[name="accept_terms"]').check()
  await page.getByRole('button', { name: 'Create Passenger account' }).click()
  await expect(page).toHaveURL(/\/check-email$/)
  await expect(page.getByText('No message was sent to an inbox.', { exact: false })).toBeVisible()
})

test('matching email never creates or links an account; invalid Google token shows an error', async ({ page }) => {
  const requests = await setup(page, { mode: 'conflict' })
  await page.goto('/login'); await page.getByRole('button', { name: 'Continue with Google', exact: true }).click()
  await expect(page.getByText('then connect Google in Profile.', { exact: false })).toBeVisible()
  await expect(page).toHaveURL(/\/login$/)
  expect(requests.filter(r => r.path.endsWith('/google/complete') || r.path === '/api/v1/users/me/google')).toHaveLength(0)
  await page.route('**/api/v1/auth/google', route => route.fulfill({ status: 401, json: { message: 'Google sign-in could not be verified. Try again.' } }))
  await page.getByRole('button', { name: 'Continue with Google', exact: true }).click()
  await expect(page.getByText('Google sign-in could not be verified. Try again.')).toBeVisible()
})

test('Profile linking needs current method and explicit confirmation', async ({ page }) => {
  const requests = await setup(page)
  await page.goto('/login')
  await page.getByLabel('Email address', { exact: true }).fill('member@example.com')
  await page.getByLabel('Password', { exact: true }).fill('existing password')
  await page.getByRole('button', { name: 'Log in', exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await page.evaluate(() => { history.pushState({}, '', '/account'); dispatchEvent(new PopStateEvent('popstate')) })
  await expect(page.getByLabel('Current password', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Continue with Google', exact: true })).toHaveCount(0)
  await page.getByLabel('Current password', { exact: true }).fill('existing password')
  await page.getByLabel('I confirm that I want to connect my Google sign-in to this account.').check()
  await page.getByRole('button', { name: 'Continue with Google', exact: true }).click()
  await expect(page.getByText('Google: Connected to this Travelly account')).toBeVisible()
  const link = requests.find(r => r.path === '/api/v1/users/me/google')
  expect(link.data.confirm).toBe(true); expect(link.data.current_password).toBe('existing password')
})
